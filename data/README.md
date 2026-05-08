# Data

AIHub 데이터베이스 파일

## 파일 목록

- `aihub.db` - 현재 사용 중인 SQLite 데이터베이스
- `aihub.db.backup` - 가장 최근 백업
- `aihub.db.before_hrdb_integration.*` - HRDB 통합 이전 백업
- `aihub.db.sqlite.backup.*` - SQLite 백업

## 주의사항

- 운영 중인 서버에서는 `aihub.db` 를 직접 수정하지 마세요
- 정기적인 백업이 필요합니다
- DB 초기화가 필요하면 기존 파일을 백업 후 삭제

## 백업 방법

```bash
# 수동 백업
cp aihub.db aihub.db.backup.$(date +%Y%m%d_%H%M%S)

# DB 크기 확인
ls -lh aihub.db
```
