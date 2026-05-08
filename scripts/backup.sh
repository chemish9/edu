#!/bin/bash
# AIHub 데이터베이스 백업 스크립트
# 사용법：bash backup.sh [백업 보관 일수]
# 예：bash backup.sh 7 (최근 7 일 분 백업만 보관)

# 스크립트 위치에서 aihub 루트 디렉터리 자동 감지
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
    PROJECT_DIR="$SCRIPT_DIR/.."
else
    PROJECT_DIR="$(pwd)"
fi

# 설정 (상대경로 사용)
DB_PATH="$PROJECT_DIR/data/aihub.db"
BACKUP_DIR="$PROJECT_DIR/backups"
LOG_FILE="$PROJECT_DIR/logs/backup.log"
RETENTION_DAYS=${1:-7}  # 기본 7 일 보관

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 백업 파일명 생성 (날짜_시간 포함)
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/aihub_backup_${TIMESTAMP}.db"

log "========================================"
log "데이터베이스 백업 시작"
log "========================================"

# 데이터베이스 파일 확인
if [ ! -f "$DB_PATH" ]; then
    log "❌ 오류: 데이터베이스 파일을 찾을 수 없습니다: $DB_PATH"
    exit 1
fi

# 데이터베이스 크기 확인
DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
log "📊 원본 DB 크기：$DB_SIZE"

# 백업 실행 (cp 로 복사)
if cp "$DB_PATH" "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "✅ 백업 완료: $BACKUP_FILE"
    log "📊 백업 파일 크기：$BACKUP_SIZE"
else
    log "❌ 오류: 백업 실패"
    exit 1
fi

# 구 백업 파일 정리 (지정 일수 초과 파일 삭제)
log "🧹 구 백업 파일 정리 ($RETENTION_DAYS 일 초과 삭제)..."
DELETED_COUNT=0

# 7 일 이상된 백업 파일 삭제
while IFS= read -r file; do
    if [ -n "$file" ]; then
        rm -f "$file"
        DELETED_COUNT=$((DELETED_COUNT + 1))
        log "  삭제：$(basename "$file")"
    fi
done < <(find "$BACKUP_DIR" -name "aihub_backup_*.db" -type f -mtime +${RETENTION_DAYS} 2>/dev/null)

if [ $DELETED_COUNT -eq 0 ]; then
    log "  삭제된 파일 없음"
else
    log "  총 $DELETED_COUNT 개 파일 삭제"
fi

# 현재 백업 상태
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "aihub_backup_*.db" -type f 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

log "========================================"
log "✅ 백업 완료!"
log "현재 백업 파일 수：$BACKUP_COUNT 개"
log "백업 디렉토리 총 크기：$TOTAL_SIZE"
log "========================================"

# 최근 5 개 백업 파일 목록
log "최근 5 개 백업 파일:"
find "$BACKUP_DIR" -name "aihub_backup_*.db" -type f -printf '%T+ %p\n' 2>/dev/null | sort -r | head -5 | while read timestamp file; do
    FILESIZE=$(du -h "$file" | cut -f1)
    log "  $(basename "$file") ($FILESIZE)"
done

exit 0
