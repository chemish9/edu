#!/usr/bin/env python3
"""PMS 연결 및 인증 테스트 스크립트."""
import sys
sys.path.insert(0, '/home/devuser/wjkim/aihub')

from backend.hrdb import verify_pms_user, get_pms_department_name, get_pms_conn

def test_connection():
    """PMS 연결 테스트."""
    print("=" * 60)
    print("PMS 연결 테스트")
    print("=" * 60)
    
    try:
        with get_pms_conn() as cur:
            cur.execute("SELECT @@VERSION")
            row = cur.fetchone()
            print(f"✓ MSSQL 연결 성공: {row[0][:100]}...")
            return True
    except Exception as e:
        print(f"✗ MSSQL 연결 실패: {e}")
        return False


def test_views():
    """뷰 존재 확인."""
    print("\n" + "=" * 60)
    print("뷰 존재 확인")
    print("=" * 60)
    
    try:
        with get_pms_conn() as cur:
            # MG_EMP_INFO 확인
            cur.execute("SELECT COUNT(*) FROM MG_EMP_INFO")
            count = cur.fetchone()[0]
            print(f"✓ MG_EMP_INFO: {count}명")
            
            # MG_DEPT_INFO 확인
            cur.execute("SELECT COUNT(*) FROM MG_DEPT_INFO")
            count = cur.fetchone()[0]
            print(f"✓ MG_DEPT_INFO: {count}개")
            
            return True
    except Exception as e:
        print(f"✗ 뷰 조회 실패: {e}")
        return False


def test_sample_data():
    """샘플 데이터 확인."""
    print("\n" + "=" * 60)
    print("샘플 데이터 확인")
    print("=" * 60)
    
    try:
        with get_pms_conn() as cur:
            # 사용자 샘플 (최대 5 명)
            cur.execute("SELECT TOP 5 EMP_ID, EMP_NM, DEPT_ID FROM MG_EMP_INFO")
            rows = cur.fetchall()
            print("\n사용자 샘플:")
            for row in rows:
                print(f"  - {row[0]}: {row[1]} ({row[2]})")
            
            # 부서 샘플 (최대 10 개)
            cur.execute("SELECT TOP 10 DEPT_ID, DEPT_NM FROM MG_DEPT_INFO")
            rows = cur.fetchall()
            print("\n부서 샘플:")
            for row in rows:
                print(f"  - {row[0]}: {row[1]}")
            
            return True
    except Exception as e:
        print(f"✗ 샘플 데이터 조회 실패: {e}")
        return False


def test_auth(emp_no: str, password: str):
    """인증 테스트."""
    print("\n" + "=" * 60)
    print(f"인증 테스트: {emp_no}")
    print("=" * 60)
    
    result = verify_pms_user(emp_no, password)
    if result:
        print(f"✓ 인증 성공")
        print(f"  - 사번: {result['emp_no']}")
        print(f"  - 이름: {result['name']}")
        print(f"  - 부서: {result['department']}")
    else:
        print(f"✗ 인증 실패")
    
    return result is not None


def test_department(dept_code: str):
    """부서명 조회 테스트."""
    print("\n" + "=" * 60)
    print(f"부서명 조회 테스트: {dept_code}")
    print("=" * 60)
    
    dept_name = get_pms_department_name(dept_code)
    print(f"  - 부서명: {dept_name}")
    return dept_name


if __name__ == "__main__":
    # 1. 연결 테스트
    if not test_connection():
        print("\n⚠ 연결 실패로 테스트 종료")
        sys.exit(1)
    
    # 2. 뷰 확인
    test_views()
    
    # 3. 샘플 데이터 확인
    test_sample_data()
    
    # 4. 인증 테스트 (테스트 계정 입력)
    print("\n" + "=" * 60)
    print("인증 테스트")
    print("=" * 60)
    print("테스트할 사번과 비밀번호를 입력해주세요 (스키프하려면 엔터)")
    emp_no = input("사번: ").strip()
    if emp_no:
        password = input("비밀번호: ").strip()
        if password:
            test_auth(emp_no, password)
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
