"""JWT 기반 인증 유틸 - HRDB 연동."""
import os
import jwt
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException, Depends

from .db import get_conn
from .hrdb import verify_pms_user, get_pms_department_name

SECRET = os.environ.get("AIHUB_SECRET", "dev-secret-change-me")
ALGO = "HS256"
EXP_HOURS = 24 * 7


def hash_password(pw: str) -> str:
	"""비밀번호 해시 (PBKDF2-SHA256)."""
	salt = b"aihub-static-salt-v1"
	return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000).hex()


def verify_password(pw: str, hashed: str) -> bool:
	"""비밀번호 검증 (SQLite 사용자용)."""
	return hash_password(pw) == hashed


def create_token(user_id: int, is_admin: bool) -> str:
	"""JWT 토큰 생성."""
	payload = {
		"sub": str(user_id),
		"admin": is_admin,
		"exp": datetime.now(timezone.utc) + timedelta(hours=EXP_HOURS),
	}
	return jwt.encode(payload, SECRET, algorithm=ALGO)


def decode_token(token: str) -> dict:
	"""JWT 토큰 디코딩."""
	try:
		return jwt.decode(token, SECRET, algorithms=[ALGO])
	except jwt.PyJWTError:
		raise HTTPException(401, "유효하지 않은 토큰")


def get_current_user(authorization: str = Header(None)) -> dict:
	"""현재 로그인 사용자 조회 (SQLite)."""
	if not authorization or not authorization.startswith("Bearer "):
		raise HTTPException(401, "인증 필요")
	token = authorization.split(" ", 1)[1]
	payload = decode_token(token)
	uid = int(payload["sub"])
	with get_conn() as conn:
		row = conn.execute(
			"SELECT * FROM users WHERE id=? AND is_deleted=0", (uid,)
		).fetchone()
	if not row:
		raise HTTPException(401, "사용자 없음")
	return dict(row)


def get_current_user_optional(authorization: str = Header(None)) -> dict | None:
	"""현재 로그인 사용자 조회 (옵션)."""
	if not authorization:
		return None
	try:
		return get_current_user(authorization)
	except HTTPException:
		return None


def require_admin(user: dict = Depends(get_current_user)) -> dict:
	"""관리자 권한 확인."""
	if not user.get("is_admin"):
		raise HTTPException(403, "관리자 권한 필요")
	return user


def authenticate_pms_user(emp_no: str, password: str) -> dict | None:
	"""
	PMS 로 사용자 인증.

	Args:
		emp_no: 사번
		password: 평문 비밀번호

	Returns:
		인증 성공 시 사용자 정보 dict, 실패 시 None
	"""
	return verify_pms_user(emp_no, password)


def sync_user_to_sqlite(pms_user: dict) -> int:
	"""
	PMS 사용자를 SQLite 에 동기화.
	존재하면 업데이트, 없으면 생성.

	Returns:
		user_id (SQLite)
	"""
	with get_conn() as conn:
		# 기존 사용자 확인
		row = conn.execute(
			"SELECT id, is_admin FROM users WHERE emp_no=? AND is_deleted=0",
			(pms_user['emp_no'],)
		).fetchone()

		if row:
			# 업데이트
			conn.execute("""
				UPDATE users SET
					name=?, department=?, email=?, updated_at=CURRENT_TIMESTAMP
				WHERE emp_no=?
			""", (
				pms_user['name'],
				pms_user['department'],
				pms_user.get('email'),
				pms_user['emp_no']
			))
			user_id = row[0]
			is_admin = row[1]
		else:
			# 신규 생성 (기본 비밀번호 설정)
			default_pw_hash = hash_password("temp1234")
			conn.execute("""
				INSERT INTO users (emp_no, name, department, email, password_hash, is_admin)
				VALUES (?, ?, ?, ?, ?, 0)
			""", (
				pms_user['emp_no'],
				pms_user['name'],
				pms_user['department'],
				pms_user.get('email'),
				default_pw_hash
			))
			user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
			is_admin = 0

		return {"user_id": user_id, "is_admin": is_admin}
