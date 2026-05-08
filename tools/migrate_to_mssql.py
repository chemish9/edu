"""SQLite → MSSQL 데이터 마이그레이션 스크립트."""
import sqlite3
import pymssql
import json
from datetime import datetime

# SQLite 설정
SQLITE_DB = "/home/devuser/wjkim/aihub/aihub.db"

# MSSQL 설정
MSSQL_HOST = "10.27.210.26"
MSSQL_PORT = 1433
MSSQL_DB = "HRDB"
MSSQL_USER = "hruser"
MSSQL_PASSWORD = "hr!@#$"


def migrate_users():
    """사용자 데이터 마이그레이션."""
    print("📋 사용자 데이터 마이그레이션 시작...")
    
    # SQLite 에서 사용자 읽기
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT * FROM users WHERE is_deleted = 0")
    users = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    # MSSQL 에 삽입
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    count = 0
    for user in users:
        try:
            mssql_cur.execute("""
                INSERT INTO users (emp_no, name, department, position, email, password_hash, is_admin, created_at, updated_at)
                VALUES (%, %, %, %, %, %, %, %, %)
            """, (
                user['emp_no'], user['name'], user['department'],
                user['position'], user['email'], user['password_hash'],
                user['is_admin'], user['created_at'], user['updated_at']
            ))
            count += 1
        except Exception as e:
            print(f"  ✗ 사용자 {user['emp_no']} 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {count} 명 마이그레이션 완료")


def migrate_categories():
    """카테고리 데이터 마이그레이션."""
    print("📋 카테고리 데이터 마이그레이션 시작...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT * FROM categories WHERE is_deleted = 0 ORDER BY id")
    categories = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    # MSSQL 에 이미 있는 카테고리 삭제
    mssql_cur.execute("DELETE FROM categories")
    
    count = 0
    for cat in categories:
        try:
            mssql_cur.execute("""
                INSERT INTO categories (parent_id, name, sort_order, created_at, updated_at)
                VALUES (%, %, %, %, %)
            """, (
                cat['parent_id'], cat['name'], cat['sort_order'],
                cat['created_at'], cat['updated_at']
            ))
            count += 1
        except Exception as e:
            print(f"  ✗ 카테고리 {cat['name']} 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {count} 개 카테고리 마이그레이션 완료")


def migrate_use_cases():
    """활용사례 데이터 마이그레이션."""
    print("📋 활용사례 데이터 마이그레이션 시작...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT * FROM use_cases WHERE is_deleted = 0")
    cases = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    # MSSQL 에 이미 있는 데이터 삭제
    mssql_cur.execute("DELETE FROM use_cases")
    
    count = 0
    for case in cases:
        try:
            mssql_cur.execute("""
                INSERT INTO use_cases (user_id, category_id, title, summary, content, ai_tools, 
                                      target_task, effect, status, reject_reason, view_count, 
                                      recommend_count, comment_count, created_at, updated_at)
                VALUES (%, %, %, %, %, %, %, %, %, %, %, %, %, %, %)
            """, (
                case['user_id'], case['category_id'], case['title'], case['summary'],
                case['content'], case['ai_tools'], case['target_task'], case['effect'],
                case['status'], case['reject_reason'], case['view_count'],
                case['recommend_count'], case['comment_count'],
                case['created_at'], case['updated_at']
            ))
            count += 1
        except Exception as e:
            print(f"  ✗ 사례 {case['id']} ({case['title'][:30]}...) 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {count} 건 마이그레이션 완료")


def migrate_tags_and_case_tags():
    """태그 및 사례 - 태그 관계 마이그레이션."""
    print("📋 태그 데이터 마이그레이션 시작...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # 태그 읽기
    sqlite_cur.execute("SELECT * FROM tags")
    tags = sqlite_cur.fetchall()
    
    # 태그 - 사례 관계 읽기
    sqlite_cur.execute("SELECT * FROM case_tags")
    case_tags = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    # MSSQL 에 이미 있는 데이터 삭제
    mssql_cur.execute("DELETE FROM case_tags")
    mssql_cur.execute("DELETE FROM tags")
    
    # 태그 삽입
    tag_id_map = {}
    for tag in tags:
        try:
            mssql_cur.execute("""
                INSERT INTO tags (name, usage_count) VALUES (%, %)
            """, (tag['name'], tag['usage_count']))
            
            # 새 ID 조회
            mssql_cur.execute("SELECT CAST(SCOPE_IDENTITY() as int)")
            new_id = mssql_cur.fetchone()[0]
            tag_id_map[tag['id']] = new_id
        except Exception as e:
            print(f"  ✗ 태그 {tag['name']} 삽입 실패: {e}")
    
    # 태그 - 사례 관계 삽입
    for ct in case_tags:
        try:
            new_tag_id = tag_id_map.get(ct['tag_id'], ct['tag_id'])
            mssql_cur.execute("""
                INSERT INTO case_tags (case_id, tag_id) VALUES (%, %)
            """, (ct['case_id'], new_tag_id))
        except Exception as e:
            print(f"  ✗ case_tags 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {len(tags)} 개 태그, {len(case_tags)} 개 관계 마이그레이션 완료")


def migrate_recommendations():
    """추천 데이터 마이그레이션."""
    print("📋 추천 데이터 마이그레이션 시작...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT * FROM recommendations")
    recs = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    # MSSQL 에 이미 있는 데이터 삭제
    mssql_cur.execute("DELETE FROM recommendations")
    
    count = 0
    for rec in recs:
        try:
            mssql_cur.execute("""
                INSERT INTO recommendations (case_id, user_id, created_at)
                VALUES (%, %, %)
            """, (rec['case_id'], rec['user_id'], rec['created_at']))
            count += 1
        except Exception as e:
            print(f"  ✗ 추천 {rec['id']} 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {count} 건 추천 마이그레이션 완료")


def migrate_comments():
    """댓글 데이터 마이그레이션."""
    print("📋 댓글 데이터 마이그레이션 시작...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT * FROM comments WHERE is_deleted = 0")
    comments = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    # MSSQL 에 이미 있는 데이터 삭제
    mssql_cur.execute("DELETE FROM comments")
    
    count = 0
    for comment in comments:
        try:
            mssql_cur.execute("""
                INSERT INTO comments (case_id, user_id, content, created_at, is_deleted)
                VALUES (%, %, %, %, %)
            """, (comment['case_id'], comment['user_id'], comment['content'],
                  comment['created_at'], comment['is_deleted']))
            count += 1
        except Exception as e:
            print(f"  ✗ 댓글 {comment['id']} 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {count} 건 댓글 마이그레이션 완료")


def migrate_notifications():
    """알림 데이터 마이그레이션."""
    print("📋 알림 데이터 마이그레이션 시작...")
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    sqlite_cur.execute("SELECT * FROM notifications")
    notifs = sqlite_cur.fetchall()
    sqlite_conn.close()
    
    mssql_conn = pymssql.connect(
        host=MSSQL_HOST, port=MSSQL_PORT,
        user=MSSQL_USER, password=MSSQL_PASSWORD,
        database=MSSQL_DB, charset='utf8'
    )
    mssql_cur = mssql_conn.cursor()
    
    # MSSQL 에 이미 있는 데이터 삭제
    mssql_cur.execute("DELETE FROM notifications")
    
    count = 0
    for notif in notifs:
        try:
            mssql_cur.execute("""
                INSERT INTO notifications (user_id, type, message, reference_id, is_read, created_at)
                VALUES (%, %, %, %, %, %)
            """, (notif['user_id'], notif['type'], notif['message'],
                  notif['reference_id'], notif['is_read'], notif['created_at']))
            count += 1
        except Exception as e:
            print(f"  ✗ 알림 {notif['id']} 삽입 실패: {e}")
    
    mssql_conn.commit()
    mssql_cur.close()
    mssql_conn.close()
    
    print(f"  ✓ {count} 건 알림 마이그레이션 완료")


def main():
    """마이그레이션 메인 함수."""
    print("=" * 50)
    print("SQLite → MSSQL 데이터 마이그레이션")
    print("=" * 50)
    print(f"Source: {SQLITE_DB}")
    print(f"Target: {MSSQL_HOST}:{MSSQL_PORT}/{MSSQL_DB}")
    print("=" * 50)
    
    try:
        migrate_categories()
        migrate_users()
        migrate_use_cases()
        migrate_tags_and_case_tags()
        migrate_recommendations()
        migrate_comments()
        migrate_notifications()
        
        print("=" * 50)
        print("✅ 마이그레이션 완료!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 마이그레이션 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
