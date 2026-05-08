"""PMS (MSSQL) 연결 관리 - 로그인 인증용."""
import os
import hashlib
import pymssql
from contextlib import contextmanager

# PMS 연결 설정 (로그인 인증 전용)
PMS_HOST = os.environ.get("PMS_HOST", "10.27.210.26")
PMS_PORT = int(os.environ.get("PMS_PORT", "1433"))
PMS_NAME = os.environ.get("PMS_NAME", "PMS")
PMS_USER = os.environ.get("PMS_USER", "pmsuser")
PMS_PASSWORD = os.environ.get("PMS_PASSWORD", "pms!@#$")


@contextmanager
def get_pms_conn():
	"""PMS 연결 컨텍스트 매니저 (로그인 인증용)."""
	conn = pymssql.connect(
		host=PMS_HOST,
		port=PMS_PORT,
		user=PMS_USER,
		password=PMS_PASSWORD,
		database=PMS_NAME,
		charset='cp949'  # 한국어 인코딩
	)
	cur = conn.cursor()
	try:
		yield cur
	except Exception as e:
		raise e
	finally:
		cur.close()
		conn.close()


def verify_pms_user(emp_no: str, password: str) -> dict | None:
	"""
	PMS 에서 사용자 인증 (MG_EMP_INFO 뷰 사용).

	Args:
		emp_no: 사번 (EMP_ID)
		password: 평문 비밀번호

	Returns:
		인증 성공 시 사용자 정보 dict, 실패 시 None
	"""
	try:
		with get_pms_conn() as cur:
			# MG_EMP_INFO 에서 사용자 조회
			cur.execute("""
				SELECT EMP_ID, EMP_PW, EMP_NM, DEPT_ID, POS_CD
				FROM MG_EMP_INFO
				WHERE EMP_ID = %s
			""", (emp_no,))

			row = cur.fetchone()
			if not row:
				return None

			# 비밀번호 비교 (PMS 는 MD5 해시 사용)
			pms_password_hash = row[1]  # EMP_PW
			input_hash = hashlib.md5(password.encode('utf-8')).hexdigest()

			if input_hash.upper() != str(pms_password_hash).upper():
				return None

			# 부서명 조회
			department = get_pms_department_name(row[3])

			return {
				'emp_no': row[0],      # EMP_ID
				'name': row[2],        # EMP_NM
				'department': department,
				'email': None,         # MG_EMP_INFO 에 없음
			}

	except Exception as e:
		print(f"PMS 인증 오류：{e}")
		return None


def get_pms_department_name(dept_code: str) -> str | None:
	"""PMS 에서 부서코드로 부서명 조회 (MG_DEPT_INFO 뷰 사용)."""
	try:
		with get_pms_conn() as cur:
			cur.execute("""
				SELECT DEPT_NM FROM MG_DEPT_INFO WHERE DEPT_ID = %s
			""", (dept_code,))
			row = cur.fetchone()
			return row[0] if row else dept_code  # 부서명 없음 시 DEPT_ID 반환
	except Exception as e:
		print(f"부서명 조회 오류：{e}")
		return dept_code  # 오류 시 DEPT_ID 반환
