"""SQLite DB 연결 관리 (aihub 전용)."""
import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.environ.get("AIHUB_DB", os.path.join(os.path.dirname(__file__), "..", "data", "aihub.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	emp_no TEXT UNIQUE NOT NULL,
	name TEXT NOT NULL,
	department TEXT,
	position TEXT,
	email TEXT,
	password_hash TEXT NOT NULL,
	is_admin INTEGER DEFAULT 0,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP,
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
	is_deleted INTEGER DEFAULT 0,
	deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS categories (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	parent_id INTEGER,
	name TEXT NOT NULL,
	sort_order INTEGER DEFAULT 0,
	is_active INTEGER DEFAULT 1,
	is_deleted INTEGER DEFAULT 0,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP,
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (parent_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS use_cases (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	user_id INTEGER NOT NULL,
	category_id INTEGER,
	title TEXT NOT NULL,
	summary TEXT NOT NULL,
	content TEXT,
	ai_tools TEXT,
	target_task TEXT,
	effect TEXT,
	status TEXT DEFAULT 'submitted',
	reject_reason TEXT,
	view_count INTEGER DEFAULT 0,
	recommend_count INTEGER DEFAULT 0,
	comment_count INTEGER DEFAULT 0,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP,
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
	is_deleted INTEGER DEFAULT 0,
	deleted_at TEXT,
	FOREIGN KEY (user_id) REFERENCES users(id),
	FOREIGN KEY (category_id) REFERENCES categories(id)
);
CREATE INDEX IF NOT EXISTS idx_cases_status ON use_cases(status, is_deleted);
CREATE INDEX IF NOT EXISTS idx_cases_recommend ON use_cases(recommend_count DESC);
CREATE INDEX IF NOT EXISTS idx_cases_created ON use_cases(created_at DESC);

CREATE TABLE IF NOT EXISTS recommendations (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	case_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP,
	UNIQUE(case_id, user_id),
	FOREIGN KEY (case_id) REFERENCES use_cases(id),
	FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS comments (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	case_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	content TEXT NOT NULL,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP,
	is_deleted INTEGER DEFAULT 0,
	FOREIGN KEY (case_id) REFERENCES use_cases(id),
	FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tags (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT UNIQUE NOT NULL,
	usage_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS case_tags (
	case_id INTEGER NOT NULL,
	tag_id INTEGER NOT NULL,
	PRIMARY KEY (case_id, tag_id),
	FOREIGN KEY (case_id) REFERENCES use_cases(id),
	FOREIGN KEY (tag_id) REFERENCES tags(id)
);

CREATE TABLE IF NOT EXISTS notifications (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	user_id INTEGER NOT NULL,
	type TEXT NOT NULL,
	message TEXT NOT NULL,
	reference_id INTEGER,
	is_read INTEGER DEFAULT 0,
	created_at TEXT DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attachments (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	case_id INTEGER,
	file_name TEXT NOT NULL,
	file_path TEXT NOT NULL,
	file_size INTEGER NOT NULL,
	file_type TEXT,
	uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (case_id) REFERENCES use_cases(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_attachments_case_id ON attachments(case_id);
"""

INITIAL_CATEGORIES = [
	("업무자동화", ["문서자동화", "이메일처리", "일정관리"]),
	("데이터분석", ["리포트생성", "시각화", "예측모델"]),
	("고객서비스", ["챗봇", "문의분류", "응대지원"]),
	("문서작성", ["기획서", "보고서", "번역"]),
	("코딩", ["코드리뷰", "테스트작성", "디버깅"]),
	("기타", []),
]


@contextmanager
def get_conn():
	"""SQLite 연결 컨텍스트 매니저."""
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA foreign_keys = ON")
	try:
		yield conn
		conn.commit()
	finally:
		conn.close()


def init_db():
	"""DB 초기화 - 테이블 생성 및 초기 데이터 삽입."""
	with get_conn() as conn:
		conn.executescript(SCHEMA)
		# 초기 카테고리
		cur = conn.execute("SELECT COUNT(*) FROM categories")
		if cur.fetchone()[0] == 0:
			for i, (parent, children) in enumerate(INITIAL_CATEGORIES):
				cur = conn.execute(
					"INSERT INTO categories (parent_id, name, sort_order) VALUES (NULL, ?, ?)",
					(parent, i),
				)
				pid = cur.lastrowid
				for j, child in enumerate(children):
					conn.execute(
						"INSERT INTO categories (parent_id, name, sort_order) VALUES (?, ?, ?)",
						(pid, child, j),
					)


def reset_db():
	"""테스트용: DB 파일 삭제 후 재생성."""
	if os.path.exists(DB_PATH):
		os.remove(DB_PATH)
	init_db()
