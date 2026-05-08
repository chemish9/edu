"""통합 테스트 - 전체 API 흐름."""
import os
import tempfile
import pytest

# 테스트 전용 DB
TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TMP.close()
os.environ["AIHUB_DB"] = TMP.name

from fastapi.testclient import TestClient
from backend.main import app
from backend.db import reset_db

reset_db()
client = TestClient(app)

# startup 이벤트 강제 실행
with client:
	pass


def auth(token):
	return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token():
	r = client.post("/api/auth/login", json={"emp_no": "admin", "password": "admin1234"})
	assert r.status_code == 200, r.text
	return r.json()["data"]["token"]


@pytest.fixture(scope="module")
def user_token():
	r = client.post("/api/auth/login", json={"emp_no": "E1001", "password": "test1234"})
	assert r.status_code == 200, r.text
	return r.json()["data"]["token"]


def test_login_fail():
	r = client.post("/api/auth/login", json={"emp_no": "admin", "password": "wrong"})
	assert r.status_code == 401


def test_me(user_token):
	r = client.get("/api/auth/me", headers=auth(user_token))
	assert r.status_code == 200
	assert r.json()["data"]["emp_no"] == "E1001"


def test_categories():
	r = client.get("/api/categories")
	assert r.status_code == 200
	tree = r.json()["data"]
	assert len(tree) >= 6
	names = [c["name"] for c in tree]
	assert "업무자동화" in names


def test_case_lifecycle(user_token, admin_token):
	# 사례 생성 → 승인 과정 없이 즉시 approved
	body = {
		"title": "Claude로 회의록 자동 정리",
		"summary": "회의 녹취를 Claude에 넣어 액션아이템 추출까지 자동화",
		"content": "## 과정\n1. 녹취...\n2. 프롬프트...",
		"category_id": 1,
		"ai_tools": ["Claude", "ChatGPT"],
		"target_task": "회의록 정리",
		"effect": "주 5시간 절약",
		"tags": ["회의록", "자동화"],
		"status": "approved",
	}
	r = client.post("/api/cases", json=body, headers=auth(user_token))
	assert r.status_code == 200, r.text
	cid = r.json()["data"]["id"]

	# 등록 즉시 목록에 노출
	r = client.get("/api/cases?status=approved")
	items = r.json()["data"]["items"]
	assert any(c["id"] == cid for c in items)
	first = next(c for c in items if c["id"] == cid)
	assert first["author_name"] == "홍길동"
	assert "Claude" in first["ai_tools"]
	assert "회의록" in first["tags"]

	# 상세 - view_count 증가
	r = client.get(f"/api/cases/{cid}", headers=auth(user_token))
	assert r.status_code == 200
	assert r.json()["data"]["view_count"] >= 1
	assert "## 과정" in r.json()["data"]["content"]

	# 추천 토글
	r = client.post(f"/api/cases/{cid}/recommend", headers=auth(user_token))
	assert r.json()["data"]["recommended"] is True
	assert r.json()["data"]["count"] == 1
	# 다시 누르면 취소
	r = client.post(f"/api/cases/{cid}/recommend", headers=auth(user_token))
	assert r.json()["data"]["recommended"] is False
	assert r.json()["data"]["count"] == 0
	# 관리자도 추천
	client.post(f"/api/cases/{cid}/recommend", headers=auth(admin_token))
	client.post(f"/api/cases/{cid}/recommend", headers=auth(user_token))

	# 댓글
	r = client.post(
		f"/api/cases/{cid}/comments",
		json={"content": "정말 도움됐어요!"},
		headers=auth(admin_token),
	)
	assert r.status_code == 200
	r = client.get(f"/api/cases/{cid}/comments")
	assert len(r.json()["data"]) == 1

	# 작성자에게 댓글 알림
	r = client.get("/api/notifications", headers=auth(user_token))
	notifs = r.json()["data"]["items"]
	assert any(n["type"] == "comment" for n in notifs)

	# 검색
	r = client.get("/api/cases?keyword=회의록&status=approved")
	assert any(c["id"] == cid for c in r.json()["data"]["items"])

	# 태그 필터
	r = client.get("/api/cases?tag=자동화&status=approved")
	assert any(c["id"] == cid for c in r.json()["data"]["items"])

	# 인기 태그
	r = client.get("/api/tags/popular")
	assert any(t["name"] == "자동화" for t in r.json()["data"])


def test_case_edit(user_token):
	# 등록 후 바로 수정 가능 (approved 상태)
	r = client.post(
		"/api/cases",
		json={
			"title": "수정 테스트 사례",
			"summary": "수정 가능한지 확인",
			"content": "초기 내용",
			"ai_tools": ["GPT"],
			"effect": "x",
			"tags": [],
			"status": "approved",
		},
		headers=auth(user_token),
	)
	cid = r.json()["data"]["id"]
	r = client.put(
		f"/api/cases/{cid}",
		json={
			"title": "수정된 제목", "summary": "수정된 요약", "content": "보강된 내용",
			"ai_tools": ["GPT"], "effect": "개선됨", "tags": ["수정"], "status": "approved",
		},
		headers=auth(user_token),
	)
	assert r.status_code == 200


def test_permission(user_token):
	# 일반 사용자가 통계 호출 → 403
	r = client.get("/api/stats/overview", headers=auth(user_token))
	assert r.status_code == 403


def test_admin_stats(admin_token, user_token):
	r = client.get("/api/stats/overview", headers=auth(admin_token))
	assert r.status_code == 200
	d = r.json()["data"]
	assert d["total"] >= 1
	r = client.get("/api/stats/ranking", headers=auth(admin_token))
	assert r.status_code == 200


def test_weekly_report():
	r = client.get("/api/reports/weekly")
	assert r.status_code == 200
	assert r.json()["data"]["new_count"] >= 1


def test_sort_options():
	for sort in ("latest", "popular", "views", "trending"):
		r = client.get(f"/api/cases?sort={sort}&status=approved")
		assert r.status_code == 200


def test_register_and_login():
	r = client.post("/api/auth/register", json={
		"emp_no": "E9999", "name": "신규", "password": "newpass1234",
		"department": "신규팀", "position": "사원",
	})
	assert r.status_code == 200
	r = client.post("/api/auth/login", json={"emp_no": "E9999", "password": "newpass1234"})
	assert r.status_code == 200


def test_unauthenticated_protected():
	r = client.post("/api/cases", json={
		"title": "x", "summary": "y", "ai_tools": [], "tags": [], "status": "approved",
	})
	assert r.status_code == 401


def test_static_index():
	r = client.get("/")
	assert r.status_code == 200
	assert "AI Lab" in r.text


def test_pagination():
	r = client.get("/api/cases?page=1&page_size=2&status=approved")
	d = r.json()["data"]
	assert d["page"] == 1 and d["page_size"] == 2
	assert len(d["items"]) <= 2
