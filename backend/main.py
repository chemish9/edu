"""FastAPI 애플리케이션 - 사내 AI 활용사례 수집 플랫폼."""
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from .db import init_db, get_conn
from .auth import (
	hash_password,
	verify_password,
	create_token,
	get_current_user,
	get_current_user_optional,
	require_admin,
	authenticate_pms_user,
	sync_user_to_sqlite,
)
from .models import LoginIn, RegisterIn, CaseIn, CommentIn, CategoryIn, StatusUpdateIn

@asynccontextmanager
async def lifespan(app: FastAPI):
	_startup()
	yield


app = FastAPI(title="AI Lab - 사내 AI 활용사례 허브", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"https://aihub.mginfo.co.kr",
		"http://aihub.mginfo.co.kr",
		"http://10.27.210.71:8000",  # 개발용
		"http://localhost:8000",      # 로컬 테스트용
	],
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
	allow_headers=["Authorization", "Content-Type"],
	max_age=600,
)


def _startup():
	init_db()
	# 시드: 관리자 + 데모 사용자
	with get_conn() as conn:
		row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
		if row[0] == 0:
			conn.execute(
				"INSERT INTO users (emp_no, name, department, position, email, password_hash, is_admin) VALUES (?,?,?,?,?,?,?)",
				("admin", "관리자", "AI추진팀", "팀장", "admin@example.com", hash_password("admin1234"), 1),
			)
			conn.execute(
				"INSERT INTO users (emp_no, name, department, position, email, password_hash, is_admin) VALUES (?,?,?,?,?,?,?)",
				("E1001", "홍길동", "마케팅팀", "대리", "hong@example.com", hash_password("test1234"), 0),
			)


def ok(data=None, message="ok"):
	return {"success": True, "data": data, "message": message}


def err(message: str, code: int = 400):
	raise HTTPException(code, message)


# ─────────────────────────── 인증 ───────────────────────────
@app.post("/api/auth/register")
def register(body: RegisterIn):
	with get_conn() as conn:
		exists = conn.execute("SELECT 1 FROM users WHERE emp_no=?", (body.emp_no,)).fetchone()
		if exists:
			err("이미 존재하는 사번")
		cur = conn.execute(
			"INSERT INTO users (emp_no, name, department, position, email, password_hash) VALUES (?,?,?,?,?,?)",
			(body.emp_no, body.name, body.department, body.position, body.email, hash_password(body.password)),
		)
		uid = cur.lastrowid
	return ok({"id": uid, "token": create_token(uid, False)})


@app.post("/api/auth/login")
def login(body: LoginIn):
	user_id = None
	is_admin = False
	user_info = None

	# 1. PMS 에서 먼저 인증 시도
	pms_user = authenticate_pms_user(body.emp_no, body.password)
	if pms_user:
		# PMS 인증 성공 - SQLite 에 동기화
		sync_result = sync_user_to_sqlite(pms_user)
		user_id = sync_result["user_id"]
		is_admin = sync_result["is_admin"]
		user_info = {
			"emp_no": pms_user['emp_no'],
			"name": pms_user['name'],
			"department": pms_user['department'],
			"position": "",
			"is_admin": bool(is_admin),
		}
	else:
		# 2. PMS 실패 시 SQLite 에서 인증 시도
		with get_conn() as conn:
			row = conn.execute(
				"SELECT * FROM users WHERE emp_no=? AND is_deleted=0",
				(body.emp_no,)
			).fetchone()
			if row:
				row_dict = dict(row)
				if verify_password(body.password, row_dict['password_hash']):
					user_id = row_dict['id']
					is_admin = row_dict['is_admin']
					user_info = {
						"emp_no": row_dict['emp_no'],
						"name": row_dict['name'],
						"department": row_dict['department'],
						"position": row_dict.get('position', '') or '',
						"is_admin": bool(is_admin),
					}

	# 3. 인증 실패
	if not user_info:
		err("아이디 또는 비밀번호를 확인해주세요", 401)

	# 4. 토큰 생성
	token = create_token(user_id, bool(is_admin))

	return ok({
		"token": token,
		"user": user_info,
	})


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
	return ok({
		"id": user["id"], "emp_no": user["emp_no"], "name": user["name"],
		"department": user["department"], "position": user["position"],
		"is_admin": bool(user["is_admin"]),
	})


# ─────────────────────────── 카테고리 ───────────────────────────
@app.get("/api/categories")
def list_categories(include_inactive: bool = False):
	with get_conn() as conn:
		query = "SELECT * FROM categories WHERE is_deleted=0"
		if not include_inactive:
			query += " AND is_active=1"
		query += " ORDER BY parent_id IS NOT NULL, sort_order, id"
		rows = conn.execute(query).fetchall()
	cats = [dict(r) for r in rows]
	# 트리 구성
	by_id = {c["id"]: {**c, "children": []} for c in cats}
	tree = []
	for c in cats:
		node = by_id[c["id"]]
		if c["parent_id"]:
			by_id[c["parent_id"]]["children"].append(node)
		else:
			tree.append(node)
	return ok(tree)


@app.post("/api/categories")
def create_category(body: CategoryIn, _: dict = Depends(require_admin)):
	with get_conn() as conn:
		cur = conn.execute(
			"INSERT INTO categories (parent_id, name, is_active) VALUES (?,?,1)", (body.parent_id, body.name)
		)
	return ok({"id": cur.lastrowid})


@app.delete("/api/categories/{cid}")
def delete_category(cid: int, _: dict = Depends(require_admin)):
	with get_conn() as conn:
		conn.execute("UPDATE categories SET is_deleted=1 WHERE id=?", (cid,))
	return ok()


@app.patch("/api/categories/{cid}/toggle")
def toggle_category(cid: int, _: dict = Depends(require_admin)):
	with get_conn() as conn:
		# 현재 상태 확인
		cat = conn.execute("SELECT is_active FROM categories WHERE id=?", (cid,)).fetchone()
		if not cat:
			return error("카테고리를 찾을 수 없습니다.", 404)
		# 상태 반전
		new_status = 0 if cat["is_active"] else 1
		conn.execute("UPDATE categories SET is_active=? WHERE id=?", (new_status, cid))
		return ok({"id": cid, "is_active": new_status})


# ─────────────────────────── 사례 (use_cases) ───────────────────────────
def _row_to_case(row, conn, include_content=False):
	d = dict(row)
	d["ai_tools"] = json.loads(d.get("ai_tools") or "[]")
	# 작성자 이름/부서
	u = conn.execute("SELECT name, department FROM users WHERE id=?", (d["user_id"],)).fetchone()
	d["author_name"] = u["name"] if u else "?"
	d["author_department"] = u["department"] if u else ""
	# 카테고리명
	if d.get("category_id"):
		c = conn.execute("SELECT name, parent_id FROM categories WHERE id=?", (d["category_id"],)).fetchone()
		d["category_name"] = c["name"] if c else None
		if c and c["parent_id"]:
			p = conn.execute("SELECT name FROM categories WHERE id=?", (c["parent_id"],)).fetchone()
			d["category_parent"] = p["name"] if p else None
		else:
			d["category_parent"] = d["category_name"]
	else:
		d["category_name"] = None
		d["category_parent"] = None
	# 태그
	tag_rows = conn.execute(
		"SELECT t.name FROM tags t JOIN case_tags ct ON ct.tag_id=t.id WHERE ct.case_id=?",
		(d["id"],),
	).fetchall()
	d["tags"] = [t["name"] for t in tag_rows]
	if not include_content:
		d.pop("content", None)
	return d


def _upsert_tags(conn, case_id: int, tag_names: list[str]):
	conn.execute("DELETE FROM case_tags WHERE case_id=?", (case_id,))
	for raw in tag_names:
		name = raw.strip()
		if not name:
			continue
		conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
		tid = conn.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()["id"]
		conn.execute("INSERT OR IGNORE INTO case_tags (case_id, tag_id) VALUES (?,?)", (case_id, tid))
	# usage_count 갱신
	conn.execute("""
		UPDATE tags SET usage_count = (
			SELECT COUNT(*) FROM case_tags WHERE tag_id = tags.id
		)
	""")


@app.get("/api/cases")
def list_cases(
	category_id: int | None = None,
	status: str | None = "approved",
	keyword: str | None = None,
	ai_tool: str | None = None,
	department: str | None = None,
	tag: str | None = None,
	sort: str = "popular",  # latest|popular|views|trending
	page: int = 1,
	page_size: int = 12,
	user: dict | None = Depends(get_current_user_optional),
):
	where = ["c.is_deleted=0"]
	params: list = []
	if status and status != "all":
		where.append("c.status=?")
		params.append(status)
	if category_id:
		# 대분류 선택 시 하위 소분류 포함
		where.append("(c.category_id=? OR c.category_id IN (SELECT id FROM categories WHERE parent_id=?))")
		params += [category_id, category_id]
	if keyword:
		kw = f"%{keyword}%"
		where.append("(c.title LIKE ? OR c.summary LIKE ? OR c.content LIKE ?)")
		params += [kw, kw, kw]
	if ai_tool:
		where.append("c.ai_tools LIKE ?")
		params.append(f'%"{ai_tool}"%')
	if department:
		where.append("u.department=?")
		params.append(department)
	if tag:
		where.append("c.id IN (SELECT case_id FROM case_tags ct JOIN tags t ON ct.tag_id=t.id WHERE t.name=?)")
		params.append(tag)

	order = {
		"latest": "c.created_at DESC",
		"popular": "c.recommend_count DESC, c.view_count DESC",
		"views": "c.view_count DESC",
		"trending": "(c.recommend_count*3 + c.view_count*0.1 + c.comment_count*2) DESC, c.created_at DESC",
	}.get(sort, "c.recommend_count DESC")

	with get_conn() as conn:
		base = f"FROM use_cases c JOIN users u ON u.id=c.user_id WHERE {' AND '.join(where)}"
		total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
		offset = (page - 1) * page_size
		rows = conn.execute(
			f"SELECT c.* {base} ORDER BY {order} LIMIT ? OFFSET ?",
			params + [page_size, offset],
		).fetchall()
		items = [_row_to_case(r, conn) for r in rows]
	return ok({"items": items, "total": total, "page": page, "page_size": page_size})


@app.get("/api/my-cases")
def get_my_cases(status: str = "all", user: dict = Depends(get_current_user)):
	"""사용자 본인의 사례 목록 조회 (임시저장 포함)"""
	with get_conn() as conn:
		where = ["c.user_id=? AND c.is_deleted=0"]
		params = [user["id"]]

		if status and status != "all":
			where.append("c.status=?")
			params.append(status)

		query = f"""SELECT c.*, cat.name as category_name
			FROM use_cases c
			LEFT JOIN categories cat ON cat.id = c.category_id
			WHERE {' AND '.join(where)}
			ORDER BY c.created_at DESC"""

		rows = conn.execute(query, params).fetchall()

		items = []
		for r in rows:
			case = dict(r)
			case["ai_tools"] = json.loads(r["ai_tools"]) if r["ai_tools"] else []
			items.append(case)

		return ok({"cases": items})


@app.get("/api/cases/{cid}")
def get_case(cid: int, user: dict | None = Depends(get_current_user_optional)):
	with get_conn() as conn:
		row = conn.execute(
			"SELECT * FROM use_cases WHERE id=? AND is_deleted=0", (cid,)
		).fetchone()
		if not row:
			err("사례 없음", 404)
		conn.execute("UPDATE use_cases SET view_count=view_count+1 WHERE id=?", (cid,))
		row = conn.execute("SELECT * FROM use_cases WHERE id=?", (cid,)).fetchone()
		data = _row_to_case(row, conn, include_content=True)
		# 추천 여부
		data["recommended_by_me"] = False
		if user:
			r = conn.execute(
				"SELECT 1 FROM recommendations WHERE case_id=? AND user_id=?", (cid, user["id"])
			).fetchone()
			data["recommended_by_me"] = bool(r)
	return ok(data)


@app.post("/api/cases")
def create_case(body: CaseIn, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		# status 가 없으면 default 로 'approved'
		status = getattr(body, 'status', None) or 'approved'
		if status not in ['draft', 'approved']:
			status = 'approved'
		
		cur = conn.execute(
			"""INSERT INTO use_cases
			(user_id, category_id, title, summary, content, ai_tools, target_task, effect, status)
			VALUES (?,?,?,?,?,?,?,?,?)""",
			(
				user["id"], body.category_id, body.title, body.summary, body.content or "",
				json.dumps(body.ai_tools, ensure_ascii=False),
				body.target_task or "", body.effect or "", status,
			),
		)
		cid = cur.lastrowid
		_upsert_tags(conn, cid, body.tags)
	return ok({"id": cid})


@app.put("/api/cases/{cid}/status")
def update_case_status(cid: int, body: StatusUpdateIn, user: dict = Depends(require_admin)):
	"""관리자 전용: 사례 상태 변경 (approved ↔ rejected)."""
	if not user.get("is_admin"):
		err("관리자 권한 필요", 403)
	
	new_status = body.status
	if new_status not in ["approved", "rejected", "draft"]:
		err("유효하지 않은 상태값입니다", 400)
	
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM use_cases WHERE id=?", (cid,)).fetchone()
		if not row:
			err("사례 없음", 404)
		
		reject_reason = body.reject_reason or ""
		conn.execute("""
			UPDATE use_cases 
			SET status=?, reject_reason=?, updated_at=CURRENT_TIMESTAMP 
			WHERE id=?
		""", (new_status, reject_reason, cid))
		
		return ok({
			"id": cid,
			"status": new_status,
			"reject_reason": reject_reason if new_status == "rejected" else None,
		})


@app.put("/api/cases/{cid}")
def update_case(cid: int, body: CaseIn, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM use_cases WHERE id=? AND is_deleted=0", (cid,)).fetchone()
		if not row:
			err("사례 없음", 404)
		if row["user_id"] != user["id"] and not user["is_admin"]:
			err("권한 없음", 403)
		if row["status"] not in ("draft", "approved") and not user["is_admin"]:
			err("수정 불가 상태", 400)
		conn.execute(
			"""UPDATE use_cases SET category_id=?, title=?, summary=?, content=?, ai_tools=?,
			target_task=?, effect=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
			(
				body.category_id, body.title, body.summary, body.content or "",
				json.dumps(body.ai_tools, ensure_ascii=False),
				body.target_task or "", body.effect or "", body.status, cid,
			),
		)
		_upsert_tags(conn, cid, body.tags)
	return ok()


@app.delete("/api/cases/{cid}")
def delete_case(cid: int, user: dict = Depends(get_current_user)):
	"""본인 게시글만 실제 삭제 가능 (관리자도 본인 게시글만 삭제)."""
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM use_cases WHERE id=?", (cid,)).fetchone()
		if not row:
			err("사례 없음", 404)
		if row["user_id"] != user["id"]:
			err("본인 게시글만 삭제 가능합니다", 403)
		conn.execute(
			"UPDATE use_cases SET is_deleted=1, deleted_at=CURRENT_TIMESTAMP WHERE id=?", (cid,)
		)
	return ok()


# ─────────────────────────── 추천 ───────────────────────────
@app.post("/api/cases/{cid}/recommend")
def toggle_recommend(cid: int, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		row = conn.execute("SELECT 1 FROM use_cases WHERE id=? AND is_deleted=0", (cid,)).fetchone()
		if not row:
			err("사례 없음", 404)
		existing = conn.execute(
			"SELECT 1 FROM recommendations WHERE case_id=? AND user_id=?", (cid, user["id"])
		).fetchone()
		if existing:
			conn.execute("DELETE FROM recommendations WHERE case_id=? AND user_id=?", (cid, user["id"]))
			recommended = False
		else:
			conn.execute(
				"INSERT INTO recommendations (case_id, user_id) VALUES (?,?)", (cid, user["id"])
			)
			recommended = True
		# 캐시 갱신
		count = conn.execute(
			"SELECT COUNT(*) FROM recommendations WHERE case_id=?", (cid,)
		).fetchone()[0]
		conn.execute("UPDATE use_cases SET recommend_count=? WHERE id=?", (count, cid))
		# 임계치 알림
		if recommended and count in (10, 50, 100):
			c = conn.execute("SELECT user_id, title FROM use_cases WHERE id=?", (cid,)).fetchone()
			conn.execute(
				"INSERT INTO notifications (user_id, type, message, reference_id) VALUES (?,?,?,?)",
				(c["user_id"], "milestone", f"'{c['title']}'가 추천 {count}회 달성!", cid),
			)
	return ok({"recommended": recommended, "count": count})


@app.get("/api/cases/{cid}/recommend/status")
def recommend_status(cid: int, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		r = conn.execute(
			"SELECT 1 FROM recommendations WHERE case_id=? AND user_id=?", (cid, user["id"])
		).fetchone()
	return ok({"recommended": bool(r)})


# ─────────────────────────── 댓글 ───────────────────────────
@app.get("/api/cases/{cid}/comments")
def list_comments(cid: int):
	with get_conn() as conn:
		rows = conn.execute(
			"""SELECT cm.*, u.name as author_name, u.department as author_department
			FROM comments cm JOIN users u ON u.id=cm.user_id
			WHERE cm.case_id=? AND cm.is_deleted=0 ORDER BY cm.created_at ASC""",
			(cid,),
		).fetchall()
	return ok([dict(r) for r in rows])


@app.post("/api/cases/{cid}/comments")
def add_comment(cid: int, body: CommentIn, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		case = conn.execute("SELECT * FROM use_cases WHERE id=? AND is_deleted=0", (cid,)).fetchone()
		if not case:
			err("사례 없음", 404)
		cur = conn.execute(
			"INSERT INTO comments (case_id, user_id, content) VALUES (?,?,?)",
			(cid, user["id"], body.content),
		)
		count = conn.execute(
			"SELECT COUNT(*) FROM comments WHERE case_id=? AND is_deleted=0", (cid,)
		).fetchone()[0]
		conn.execute("UPDATE use_cases SET comment_count=? WHERE id=?", (count, cid))
		# 작성자 알림
		if case["user_id"] != user["id"]:
			conn.execute(
				"INSERT INTO notifications (user_id, type, message, reference_id) VALUES (?,?,?,?)",
				(case["user_id"], "comment", f"'{case['title']}'에 새 댓글: {body.content[:30]}", cid),
			)
	return ok({"id": cur.lastrowid})


@app.delete("/api/comments/{cmid}")
def delete_comment(cmid: int, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM comments WHERE id=?", (cmid,)).fetchone()
		if not row:
			err("댓글 없음", 404)
		if row["user_id"] != user["id"] and not user["is_admin"]:
			err("권한 없음", 403)
		conn.execute("UPDATE comments SET is_deleted=1 WHERE id=?", (cmid,))
		count = conn.execute(
			"SELECT COUNT(*) FROM comments WHERE case_id=? AND is_deleted=0", (row["case_id"],)
		).fetchone()[0]
		conn.execute("UPDATE use_cases SET comment_count=? WHERE id=?", (count, row["case_id"]))
	return ok()


# ─────────────────────────── 태그 ───────────────────────────
@app.get("/api/tags")
def list_tags():
	with get_conn() as conn:
		rows = conn.execute(
			"SELECT * FROM tags WHERE usage_count>0 ORDER BY usage_count DESC"
		).fetchall()
	return ok([dict(r) for r in rows])


@app.get("/api/tags/popular")
def popular_tags():
	with get_conn() as conn:
		rows = conn.execute(
			"SELECT * FROM tags WHERE usage_count>0 ORDER BY usage_count DESC LIMIT 20"
		).fetchall()
	return ok([dict(r) for r in rows])


# ─────────────────────────── 통계 (관리자) ───────────────────────────
@app.get("/api/stats/overview")
def stats_overview(_: dict = Depends(require_admin)):
	with get_conn() as conn:
		total = conn.execute("SELECT COUNT(*) FROM use_cases WHERE is_deleted=0").fetchone()[0]
		draft_count = conn.execute(
			"SELECT COUNT(*) FROM use_cases WHERE status='draft' AND is_deleted=0"
		).fetchone()[0]
		total_recommend = conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
		# 월별 추이 (최근 6개월)
		monthly = conn.execute(
			"""SELECT substr(created_at,1,7) as ym, COUNT(*) as n
			FROM use_cases WHERE is_deleted=0
			GROUP BY ym ORDER BY ym DESC LIMIT 6"""
		).fetchall()
		# 부서별
		by_dept = conn.execute(
			"""SELECT u.department, COUNT(*) as n
			FROM use_cases c JOIN users u ON u.id=c.user_id
			WHERE c.is_deleted=0 GROUP BY u.department"""
		).fetchall()
	return ok({
		"total": total, "draft_count": draft_count,
		"total_recommend": total_recommend,
		"monthly": [dict(r) for r in monthly],
		"by_department": [dict(r) for r in by_dept],
	})


@app.get("/api/stats/ranking")
def stats_ranking(_: dict = Depends(require_admin)):
	with get_conn() as conn:
		dept = conn.execute(
			"""SELECT u.department, COUNT(*) as cases, SUM(c.recommend_count) as recs
			FROM use_cases c JOIN users u ON u.id=c.user_id
			WHERE c.is_deleted=0 GROUP BY u.department ORDER BY recs DESC"""
		).fetchall()
		users = conn.execute(
			"""SELECT u.id, u.name, u.department, COUNT(c.id) as cases,
			COALESCE(SUM(c.recommend_count),0) as recs
			FROM users u LEFT JOIN use_cases c ON c.user_id=u.id AND c.is_deleted=0
			GROUP BY u.id ORDER BY recs DESC LIMIT 10"""
		).fetchall()
	return ok({"by_department": [dict(r) for r in dept], "top_users": [dict(r) for r in users]})


# ─────────────────────────── 관리자 사례 처리 ───────────────────────────



# ─────────────────────────── 알림 ───────────────────────────
@app.get("/api/notifications")
def list_notifications(user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		rows = conn.execute(
			"SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
			(user["id"],),
		).fetchall()
		unread = conn.execute(
			"SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user["id"],)
		).fetchone()[0]
	return ok({"items": [dict(r) for r in rows], "unread": unread})


@app.patch("/api/notifications/{nid}/read")
def read_notification(nid: int, user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		conn.execute(
			"UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (nid, user["id"])
		)
	return ok()


@app.post("/api/notifications/read-all")
def read_all(user: dict = Depends(get_current_user)):
	with get_conn() as conn:
		conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
	return ok()


# ─────────────────────────── 주간 리포트 ───────────────────────────
@app.get("/api/reports/weekly")
def weekly_report():
	week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
	with get_conn() as conn:
		new_count = conn.execute(
			"SELECT COUNT(*) FROM use_cases WHERE created_at>=? AND is_deleted=0", (week_ago,)
		).fetchone()[0]
		top = conn.execute(
			"""SELECT id, title, summary, recommend_count FROM use_cases
			WHERE created_at>=? AND is_deleted=0
			ORDER BY recommend_count DESC LIMIT 3""",
			(week_ago,),
		).fetchall()
		dept = conn.execute(
			"""SELECT u.department, COUNT(*) as n FROM use_cases c JOIN users u ON u.id=c.user_id
			WHERE c.created_at>=? AND c.is_deleted=0 GROUP BY u.department ORDER BY n DESC LIMIT 1""",
			(week_ago,),
		).fetchone()
		total_cases = conn.execute("SELECT COUNT(*) FROM use_cases WHERE is_deleted=0").fetchone()[0]
		total_users = conn.execute("SELECT COUNT(DISTINCT user_id) FROM use_cases").fetchone()[0]
	return ok({
		"new_count": new_count,
		"top": [dict(r) for r in top],
		"top_department": dict(dept) if dept else None,
		"total_cases": total_cases,
		"total_contributors": total_users,
	})


# ─────────────────────────── 사용자 관리 (관리자) ───────────────────────────
@app.get("/api/users")
def list_users(_: dict = Depends(require_admin)):
	"""모든 사용자 목록 조회 (관리자 전용)"""
	with get_conn() as conn:
		rows = conn.execute(
			"SELECT * FROM users WHERE is_deleted=0 ORDER BY created_at DESC"
		).fetchall()
	return ok([dict(r) for r in rows])


@app.patch("/api/users/{uid}/admin")
def toggle_admin(uid: int, user: dict = Depends(require_admin)):
	"""사용자의 관리자 권한 토글 (관리자 전용)"""
	with get_conn() as conn:
		# 본인 확인
		if uid == user["id"]:
			err("본인의 관리자 권한은 직접 해제할 수 없습니다", 400)
		
		# 대상 사용자 확인
		target = conn.execute(
			"SELECT * FROM users WHERE id=? AND is_deleted=0", (uid,)
		).fetchone()
		if not target:
			err("사용자 없음", 404)
		
		# 마지막 관리자 확인 (최소 1 명 유지)
		if not target["is_admin"]:
			# 관리자로 부여하는 경우 - 항상 허용
			new_admin_status = 1
		else:
			# 관리자를 해제하는 경우 - 다른 관리자가 최소 1 명은 있어야 함
			admin_count = conn.execute(
				"SELECT COUNT(*) FROM users WHERE is_admin=1 AND id!=? AND is_deleted=0",
				(uid,)
			).fetchone()[0]
			if admin_count < 1:
				err("최소 1 명의 관리자는 유지되어야 합니다", 400)
			new_admin_status = 0
		
		# 권한 토글
		conn.execute(
			"UPDATE users SET is_admin=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
			(new_admin_status, uid),
		)
	
	return ok({
		"user_id": uid,
		"emp_no": target["emp_no"],
		"name": target["name"],
		"is_admin": bool(new_admin_status),
		"message": f"'{target['name']}'({target['emp_no']}) 의 관리자 권한이 {'부여' if new_admin_status else '해제'}되었습니다"
	})


# ─────────────────────────── 통계 내보내기 (관리자) ───────────────────────────
@app.get("/api/stats/export/excel")
def export_stats_excel(_: dict = Depends(require_admin)):
	"""통계 데이터를 Excel 형식으로 내보내기 (관리자 전용, 여러 시트)"""
	from openpyxl import Workbook
	from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
	from openpyxl.utils import get_column_letter
	
	with get_conn() as conn:
		# 1. 사례별 상세 데이터
		cases = conn.execute("""
			SELECT 
				c.id, c.title, c.summary, c.status, c.recommend_count, c.view_count,
				c.created_at, u.emp_no, u.name, u.department, u.position
			FROM use_cases c
			JOIN users u ON c.user_id = u.id
			WHERE c.is_deleted = 0
			ORDER BY c.created_at DESC
		""").fetchall()
		
		# 2. 카테고리별 통계
		category_stats = conn.execute("""
			SELECT cat.name, COUNT(c.id) as total, SUM(c.recommend_count) as total_recs
			FROM categories cat
			LEFT JOIN use_cases c ON cat.id = c.category_id AND c.is_deleted = 0 AND c.status = 'approved'
			GROUP BY cat.id, cat.name
		""").fetchall()
		
		# 3. 부서별 통계
		dept_stats = conn.execute("""
			SELECT u.department, COUNT(c.id) as total, SUM(c.recommend_count) as total_recs
			FROM users u
			LEFT JOIN use_cases c ON u.id = c.user_id AND c.is_deleted = 0 AND c.status = 'approved'
			GROUP BY u.department
			ORDER BY total DESC
		""").fetchall()
		
		# 4. 사용자별 통계 (TOP 50)
		user_stats = conn.execute("""
			SELECT u.name, u.emp_no, u.department, 
				COUNT(c.id) as cases, SUM(c.recommend_count) as recs
			FROM users u
			LEFT JOIN use_cases c ON u.id = c.user_id AND c.is_deleted = 0 AND c.status = 'approved'
			GROUP BY u.id, u.name, u.emp_no, u.department
			HAVING cases > 0
			ORDER BY recs DESC
			LIMIT 50
		""").fetchall()
	
	# Excel 워크북 생성
	wb = Workbook()
	
	# 스타일 정의
	header_font = Font(bold=True, color="FFFFFF")
	header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
	alignment_center = Alignment(horizontal="center", vertical="center")
	thin_border = Border(
		left=Side(style='thin'),
		right=Side(style='thin'),
		top=Side(style='thin'),
		bottom=Side(style='thin')
	)
	
	# 시트 1: 사례 상세
	sheet1 = wb.active
	sheet1.title = "사례 상세"
	
	# 헤더
	headers1 = ['ID', '제목', '요약', '상태', '추천', '조회', '등록일', '사번', '이름', '부서', '직급']
	for col, header in enumerate(headers1, 1):
		cell = sheet1.cell(row=1, column=col, value=header)
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = alignment_center
		cell.border = thin_border
	
	# 데이터
	for row_idx, row in enumerate(cases, 2):
		sheet1.cell(row=row_idx, column=1, value=row[0])
		sheet1.cell(row=row_idx, column=2, value=row[1])
		sheet1.cell(row=row_idx, column=3, value=row[2])
		sheet1.cell(row=row_idx, column=4, value=row[3])
		sheet1.cell(row=row_idx, column=5, value=row[4])
		sheet1.cell(row=row_idx, column=6, value=row[5])
		sheet1.cell(row=row_idx, column=7, value=(row[6] or '')[:10])
		sheet1.cell(row=row_idx, column=8, value=row[7])
		sheet1.cell(row=row_idx, column=9, value=row[8])
		sheet1.cell(row=row_idx, column=10, value=row[9] or '')
		sheet1.cell(row=row_idx, column=11, value=row[10] or '')
	
	# 열 너비 자동 조절
	sheet1.column_dimensions['A'].width = 6
	sheet1.column_dimensions['B'].width = 40
	sheet1.column_dimensions['C'].width = 50
	sheet1.column_dimensions['D'].width = 10
	sheet1.column_dimensions['E'].width = 8
	sheet1.column_dimensions['F'].width = 8
	sheet1.column_dimensions['G'].width = 12
	sheet1.column_dimensions['H'].width = 12
	sheet1.column_dimensions['I'].width = 15
	sheet1.column_dimensions['J'].width = 15
	sheet1.column_dimensions['K'].width = 10
	
	# 시트 2: 카테고리별 통계
	sheet2 = wb.create_sheet("카테고리별 통계")
	headers2 = ['카테고리', '등록수', '총 추천수']
	for col, header in enumerate(headers2, 1):
		cell = sheet2.cell(row=1, column=col, value=header)
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = alignment_center
		cell.border = thin_border
	
	for row_idx, row in enumerate(category_stats, 2):
		sheet2.cell(row=row_idx, column=1, value=row[0])
		sheet2.cell(row=row_idx, column=2, value=row[1] or 0)
		sheet2.cell(row=row_idx, column=3, value=row[2] or 0)
	
	sheet2.column_dimensions['A'].width = 20
	sheet2.column_dimensions['B'].width = 15
	sheet2.column_dimensions['C'].width = 15
	
	# 시트 3: 부서별 통계
	sheet3 = wb.create_sheet("부서별 통계")
	headers3 = ['부서', '등록수', '총 추천수']
	for col, header in enumerate(headers3, 1):
		cell = sheet3.cell(row=1, column=col, value=header)
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = alignment_center
		cell.border = thin_border
	
	for row_idx, row in enumerate(dept_stats, 2):
		sheet3.cell(row=row_idx, column=1, value=row[0] or '미입력')
		sheet3.cell(row=row_idx, column=2, value=row[1] or 0)
		sheet3.cell(row=row_idx, column=3, value=row[2] or 0)
	
	sheet3.column_dimensions['A'].width = 25
	sheet3.column_dimensions['B'].width = 15
	sheet3.column_dimensions['C'].width = 15
	
	# 시트 4: 사용자별 통계 (TOP 50)
	sheet4 = wb.create_sheet("사용자별 통계")
	headers4 = ['이름', '사번', '부서', '등록수', '총 추천수']
	for col, header in enumerate(headers4, 1):
		cell = sheet4.cell(row=1, column=col, value=header)
		cell.font = header_font
		cell.fill = header_fill
		cell.alignment = alignment_center
		cell.border = thin_border
	
	for row_idx, row in enumerate(user_stats, 2):
		sheet4.cell(row=row_idx, column=1, value=row[0])
		sheet4.cell(row=row_idx, column=2, value=row[1])
		sheet4.cell(row=row_idx, column=3, value=row[2] or '')
		sheet4.cell(row=row_idx, column=4, value=row[3])
		sheet4.cell(row=row_idx, column=5, value=row[4] or 0)
	
	sheet4.column_dimensions['A'].width = 18
	sheet4.column_dimensions['B'].width = 15
	sheet4.column_dimensions['C'].width = 20
	sheet4.column_dimensions['D'].width = 12
	sheet4.column_dimensions['E'].width = 12
	
	# 파일 저장
	import io
	output = io.BytesIO()
	wb.save(output)
	output.seek(0)
	
	filename = f"aihub_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
	
	return Response(
		content=output.getvalue(),
		media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		headers={"Content-Disposition": f"attachment; filename={filename}"}
	)


# ─────────────────────────── 첨부파일 ───────────────────────────
UPLOAD_DIR = "/data/aihub/data/uploads/attachments"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.rar', '.7z'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


def get_file_extension(filename: str) -> str:
	"""파일 확장자 추출 (소문자)."""
	return os.path.splitext(filename)[1].lower()


@app.post("/api/attachments/upload")
def upload_attachment(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
	"""첨부파일 업로드 (임시 저장, 사례 등록 시 연결)."""
	# 파일명 검증
	if not file.filename:
		err("파일명이 없습니다", 400)
	
	ext = get_file_extension(file.filename)
	if ext and ext not in ALLOWED_EXTENSIONS:
		err(f"허용되지 않은 파일 형식입니다：{ext}", 400)
	
	# 고유 파일명 생성
	unique_id = str(uuid.uuid4())
	original_name = file.filename
	safe_filename = f"{unique_id}{ext}" if ext else unique_id
	file_path = os.path.join(UPLOAD_DIR, safe_filename)
	
	# 파일 저장
	try:
		with open(file_path, "wb") as buffer:
			shutil.copyfileobj(file.file, buffer)
		file_size = os.path.getsize(file_path)
		
		if file_size > MAX_FILE_SIZE:
			os.remove(file_path)
			err("파일 크기가 너무 큽니다 (최대 500MB)", 400)
	except Exception as e:
		err(f"파일 저장 중 오류가 발생했습니다：{str(e)}", 500)
	
	# 임시 저장 (case_id=None)
	with get_conn() as conn:
		cur = conn.execute(
			"INSERT INTO attachments (case_id, file_name, file_path, file_size, file_type) VALUES (NULL, ?, ?, ?, ?)",
			(original_name, file_path, file_size, ext),
		)
		attachment_id = cur.lastrowid
	
	return ok({
		"id": attachment_id,
		"file_name": original_name,
		"file_size": file_size,
		"file_type": ext,
	})


@app.post("/api/cases/{cid}/attachments")
def add_attachment_to_case(
	cid: int,
	file: UploadFile = File(...),
	user: dict = Depends(get_current_user)
):
	"""사례에 첨부파일 추가."""
	# 사례 존재 확인 및 권한 체크
	with get_conn() as conn:
		case = conn.execute("SELECT * FROM use_cases WHERE id=? AND is_deleted=0", (cid,)).fetchone()
		if not case:
			err("사례 없음", 404)
		if case["user_id"] != user["id"] and not user["is_admin"]:
			err("권한 없음", 403)
	
	# 파일 업로드 로직
	ext = get_file_extension(file.filename)
	if ext and ext not in ALLOWED_EXTENSIONS:
		err(f"허용되지 않은 파일 형식입니다：{ext}", 400)
	
	unique_id = str(uuid.uuid4())
	original_name = file.filename
	safe_filename = f"{unique_id}{ext}" if ext else unique_id
	file_path = os.path.join(UPLOAD_DIR, safe_filename)
	
	try:
		with open(file_path, "wb") as buffer:
			shutil.copyfileobj(file.file, buffer)
		file_size = os.path.getsize(file_path)
		
		if file_size > MAX_FILE_SIZE:
			os.remove(file_path)
			err("파일 크기가 너무 큽니다 (최대 500MB)", 400)
	except Exception as e:
		err(f"파일 저장 중 오류가 발생했습니다：{str(e)}", 500)
	
	# DB 저장
	with get_conn() as conn:
		cur = conn.execute(
			"INSERT INTO attachments (case_id, file_name, file_path, file_size, file_type) VALUES (?, ?, ?, ?, ?)",
			(cid, original_name, file_path, file_size, ext),
		)
		attachment_id = cur.lastrowid
	
	return ok({
		"id": attachment_id,
		"file_name": original_name,
		"file_size": file_size,
		"file_type": ext,
	})


@app.get("/api/attachments/{aid}")
def get_attachment(aid: int, user: dict | None = Depends(get_current_user_optional)):
	"""첨부파일 정보 조회."""
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
		if not row:
			err("첨부파일 없음", 404)
		
		# case_id 가 있으면 해당 사례가 공개된 경우만 접근 허용
		if row["case_id"]:
			case = conn.execute("SELECT status, is_deleted FROM use_cases WHERE id=?", (row["case_id"],)).fetchone()
			if not case or case["is_deleted"] or case["status"] != "approved":
				err("접근할 수 없는 첨부파일입니다", 403)
		
		return ok(dict(row))


@app.get("/api/attachments/{aid}/download")
def download_attachment(aid: int, user: dict | None = Depends(get_current_user_optional)):
	"""첨부파일 다운로드."""
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
		if not row:
			err("첨부파일 없음", 404)
		
		# 권한 체크
		if row["case_id"]:
			case = conn.execute("SELECT status, is_deleted, user_id FROM use_cases WHERE id=?", (row["case_id"],)).fetchone()
			if not case or case["is_deleted"]:
				err("접근할 수 없는 첨부파일입니다", 403)
			if case["status"] != "approved" and not user:
				err("로그인이 필요합니다", 401)
			if case["status"] != "approved" and case["user_id"] != user["id"] and not user.get("is_admin"):
				err("권한이 없습니다", 403)
		
		file_path = row["file_path"]
		if not os.path.exists(file_path):
			err("파일이 존재하지 않습니다", 404)
		
		return FileResponse(
			file_path,
			filename=row["file_name"],
			media_type="application/octet-stream",
		)


@app.delete("/api/attachments/{aid}")
def delete_attachment(aid: int, user: dict = Depends(get_current_user)):
	"""첨부파일 삭제."""
	with get_conn() as conn:
		row = conn.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
		if not row:
			err("첨부파일 없음", 404)
		
		# 권한 체크 (본인 사례 또는 관리자)
		if row["case_id"]:
			case = conn.execute("SELECT user_id FROM use_cases WHERE id=?", (row["case_id"],)).fetchone()
			if not case or (case["user_id"] != user["id"] and not user["is_admin"]):
				err("권한 없음", 403)
		
		# 파일 삭제
		file_path = row["file_path"]
		if os.path.exists(file_path):
			os.remove(file_path)
		
		# DB 삭제
		conn.execute("DELETE FROM attachments WHERE id=?", (aid,))
	
	return ok()


@app.get("/api/cases/{cid}/attachments")
def list_case_attachments(cid: int, user: dict | None = Depends(get_current_user_optional)):
	"""사례의 첨부파일 목록 조회."""
	with get_conn() as conn:
		case = conn.execute("SELECT * FROM use_cases WHERE id=? AND is_deleted=0", (cid,)).fetchone()
		if not case:
			err("사례 없음", 404)
		
		# 권한 체크
		if case["status"] != "approved" and not user:
			err("로그인이 필요합니다", 401)
		if case["status"] != "approved" and case["user_id"] != user["id"] and not user.get("is_admin"):
			err("권한이 없습니다", 403)
		
		rows = conn.execute(
			"SELECT * FROM attachments WHERE case_id=? ORDER BY uploaded_at ASC", (cid,)
		).fetchall()
		return ok([dict(r) for r in rows])


@app.patch("/api/attachments/{aid}/update-case")
def update_attachment_case(aid: int, case_id: int = Form(...), user: dict = Depends(get_current_user)):
	"""첨부파일의 case_id 업데이트 (임시 저장 → 실제 사례 연결)."""
	with get_conn() as conn:
		# 첨부파일 존재 확인
		row = conn.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
		if not row:
			err("첨부파일 없음", 404)
		
		# 이미 case_id 가 있으면 해당 사례의 작성자여야 함
		if row["case_id"]:
			case = conn.execute("SELECT user_id FROM use_cases WHERE id=?", (row["case_id"],)).fetchone()
			if case and case["user_id"] != user["id"] and not user["is_admin"]:
				err("권한 없음", 403)
		
		# case_id 업데이트
		conn.execute("UPDATE attachments SET case_id=? WHERE id=?", (case_id, aid))
	
	return ok({"id": aid, "case_id": case_id})


# ─────────────────────────── 정적 프론트엔드 ───────────────────────────
FRONT_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(FRONT_DIR):
	@app.get("/")
	def index():
		return FileResponse(os.path.join(FRONT_DIR, "index.html"))

# Image 폴더를 먼저 마운트 (더 구체적인 경로가 먼저)
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "image")
if os.path.isdir(IMAGE_DIR):
	app.mount("/static/image", StaticFiles(directory=IMAGE_DIR), name="static-image")

# Frontend 폴더 마운트
	app.mount("/static", StaticFiles(directory=FRONT_DIR), name="static")

