# Logs

AIHub 서버 로그 파일

## 파일 목록

- `aihub_8000.log` - 포트 8000 서버 로그
- `aihub_8010.log` - 포트 8010 서버 로그
- `server.log` - 일반 서버 로그
- `aihub_*.pid` - 프로세스 ID 파일

## 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/aihub_8000.log

# 최근 100 줄 확인
tail -100 logs/aihub_8000.log

# 특정 키워드 검색
grep "ERROR" logs/aihub_8000.log
```

## 로그 회전

로그 파일이 너무 커지면 수동으로 정리하세요:

```bash
# 빈 파일로 초기화 (프로세스 실행 중)
> logs/aihub_8000.log

# 또는 백업 후 초기화
mv logs/aihub_8000.log logs/aihub_8000.log.old
touch logs/aihub_8000.log
```
