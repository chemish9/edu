"""HRDB 데이터베이스 테이블 분석 스크립트."""
import pymssql

conn = pymssql.connect(
    host='10.27.210.26', port=1433,
    user='hruser', password='hr!@#$',
    database='HRDB', charset='utf8'
)
cur = conn.cursor()

# 주요 HR 테이블 목록
target_tables = [
    'HR_USER', 'HR_DEPT', 'HR_DEPT_INFO', 'HR_USER_INFO',
    't_EMPINFO', 't_DEPTINFO', 'HR_USER_VALIDATION',
    'HR_DAILY_REPORT', 'HR_WEEKLY_REPORT',
]

print("=" * 80)
print("HRDB 데이터베이스 테이블 구조 분석")
print("=" * 80)

for table in target_tables:
    try:
        # 테이블 컬럼 조회
        cur.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table}'
            ORDER BY ORDINAL_POSITION
        """)
        columns = cur.fetchall()
        
        if columns:
            print(f"\n📋 {table}")
            print("-" * 60)
            for col in columns:
                col_name, col_type, nullable, max_len = col
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                len_str = f"({max_len})" if max_len else ""
                print(f"  {col_name:25} {col_type:15} {nullable_str:10} {len_str}")
    except Exception as e:
        print(f"\n✗ {table}: {e}")

conn.close()
