"""데모용 시드 데이터 생성."""
import json
import random
import sys
import os

# 직접 실행 시 import 경로 추가
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_conn, init_db
from backend.auth import hash_password

USERS = [
	("admin", "관리자", "AI추진팀", "팀장", "admin1234", 1),
	("E1001", "홍길동", "마케팅팀", "대리", "test1234", 0),
	("E1002", "김영희", "개발팀", "과장", "test1234", 0),
	("E1003", "이철수", "데이터팀", "사원", "test1234", 0),
	("E1004", "박민지", "고객지원팀", "대리", "test1234", 0),
	("E1005", "최수현", "기획팀", "차장", "test1234", 0),
]

CASES = [
	("Claude로 고객 문의 자동 분류", "Claude를 활용해 매일 들어오는 고객 문의 1000건을 카테고리별로 자동 분류",
	 "## 도입 배경\n매일 1000건+ 문의 처리 어려움\n## 방법\nClaude API + 분류 프롬프트", 3, ["Claude"], "고객지원", "처리시간 70% 감소", ["고객지원", "분류", "자동화"]),
	("ChatGPT 주간 보고서 자동 생성", "팀 주간 보고서를 ChatGPT로 자동 생성", "각 팀원 업데이트를 입력 → 요약본 생성", 4, ["ChatGPT"], "주간보고", "주 3시간 절약", ["보고서", "자동화"]),
	("Copilot으로 코드 리뷰 가속화", "Github Copilot Chat을 활용한 PR 리뷰 보조", "PR 변경사항 요약 + 위험 포인트 검출", 5, ["Copilot"], "코드리뷰", "리뷰 시간 50% 단축", ["코드리뷰", "개발생산성"]),
	("Claude 데이터 분석 리포트 자동화", "월간 매출 데이터를 Claude에 넣어 인사이트 추출", "CSV 업로드 → 분석 → 시각화", 2, ["Claude"], "데이터분석", "분석 사이클 1일 → 1시간", ["데이터분석", "리포트"]),
	("Midjourney로 마케팅 비주얼 제작", "캠페인 비주얼을 Midjourney로 시안 생성", "프롬프트 라이브러리 구축", 1, ["Midjourney"], "디자인", "외주 비용 60% 절감", ["디자인", "마케팅"]),
	("Gemini로 회의록 요약", "Google Meet 녹취록을 Gemini로 요약 + 액션아이템 추출", "녹취 → Gemini → Notion", 4, ["Gemini"], "회의관리", "회의록 작성 시간 80% 절약", ["회의록", "요약"]),
	("ChatGPT 영문 이메일 작성 도우미", "해외 거래처와의 영문 이메일 작성", "한글 초안 → ChatGPT 번역/톤조절", 5, ["ChatGPT"], "이메일", "응답 속도 2배", ["번역", "이메일"]),
	("Claude로 SQL 쿼리 자동 생성", "비개발자도 자연어로 데이터 조회", "스키마 + 자연어 → SQL", 2, ["Claude"], "데이터조회", "데이터팀 의존도 감소", ["SQL", "데이터분석"]),
	("Copilot으로 단위 테스트 작성", "기존 코드에 대한 단위테스트를 Copilot으로 자동생성", "함수 선택 → 테스트 생성", 3, ["Copilot"], "테스트작성", "테스트 커버리지 40→75%", ["테스트", "개발생산성"]),
	("ChatGPT 사내 위키 검색 봇", "사내 매뉴얼을 RAG로 검색 가능하게", "Confluence + Embedding + ChatGPT", 5, ["ChatGPT"], "지식관리", "신입 온보딩 2주 → 3일", ["RAG", "지식관리"]),
	("Claude 계약서 검토 보조", "계약서 초안의 위험 조항 검토", "PDF 업로드 → 조항별 분석", 4, ["Claude"], "계약검토", "법무 1차 검토 시간 절감", ["법무", "계약"]),
	("ChatGPT 광고 카피 생성", "캠페인별 광고 카피 A/B 안 생성", "타겟/톤 입력 → 변형 카피 10개", 1, ["ChatGPT"], "마케팅", "카피 작성 시간 90% 단축", ["마케팅", "카피라이팅"]),
]


def seed():
	init_db()
	with get_conn() as conn:
		# 기존 시드 위 덮어쓰기 방지: 사례가 이미 있으면 종료
		if conn.execute("SELECT COUNT(*) FROM use_cases").fetchone()[0] > 0:
			return
		# 사용자
		for emp_no, name, dept, pos, pw, is_admin in USERS:
			exists = conn.execute("SELECT 1 FROM users WHERE emp_no=?", (emp_no,)).fetchone()
			if not exists:
				conn.execute(
					"INSERT INTO users (emp_no,name,department,position,email,password_hash,is_admin) VALUES (?,?,?,?,?,?,?)",
					(emp_no, name, dept, pos, f"{emp_no}@example.com", hash_password(pw), is_admin),
				)
		user_ids = [r["id"] for r in conn.execute("SELECT id FROM users WHERE is_admin=0").fetchall()]
		# 카테고리 ID 매핑
		cats = conn.execute("SELECT id FROM categories WHERE parent_id IS NULL ORDER BY sort_order").fetchall()
		cat_ids = [c["id"] for c in cats]

		for i, (title, summary, content, cat_idx, ai_tools, task, effect, tags) in enumerate(CASES):
			uid = random.choice(user_ids)
			cid_cat = cat_ids[min(cat_idx, len(cat_ids) - 1)]
			cur = conn.execute(
				"""INSERT INTO use_cases (user_id, category_id, title, summary, content, ai_tools, target_task, effect, status, view_count, recommend_count)
				VALUES (?,?,?,?,?,?,?,?,'approved',?,?)""",
				(uid, cid_cat, title, summary, content, json.dumps(ai_tools, ensure_ascii=False),
				 task, effect, random.randint(20, 2000), 0),
			)
			case_id = cur.lastrowid
			# 태그
			for t in tags:
				conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (t,))
				tid = conn.execute("SELECT id FROM tags WHERE name=?", (t,)).fetchone()["id"]
				conn.execute("INSERT OR IGNORE INTO case_tags (case_id, tag_id) VALUES (?,?)", (case_id, tid))
			# 추천 (랜덤)
			rec_users = random.sample(user_ids, k=random.randint(1, len(user_ids)))
			for ru in rec_users:
				try:
					conn.execute("INSERT INTO recommendations (case_id, user_id) VALUES (?,?)", (case_id, ru))
				except Exception:
					pass
			conn.execute(
				"UPDATE use_cases SET recommend_count=(SELECT COUNT(*) FROM recommendations WHERE case_id=?) WHERE id=?",
				(case_id, case_id),
			)
		conn.execute("UPDATE tags SET usage_count=(SELECT COUNT(*) FROM case_tags WHERE tag_id=tags.id)")


if __name__ == "__main__":
	seed()
	print("시드 완료")
