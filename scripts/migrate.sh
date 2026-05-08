#!/bin/bash
# AIHub 데이터 마이그레이션 스크립트
# 사용법：
#   백업 생성：bash migrate.sh backup
#   백업 적용：bash migrate.sh restore /path/to/backup.tar.gz

set -e

ACTION="${1:-backup}"
BACKUP_FILE="${2:-}"

echo "========================================"
echo "  AIHub 데이터 마이그레이션"
echo "  작업：$ACTION"
echo "========================================"

case $ACTION in
    backup)
        echo "📦 데이터 백업 생성 중..."
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_NAME="aihub_backup_${TIMESTAMP}.tar.gz"
        
        # 백업 생성
        tar -czvf "$BACKUP_NAME" \
            data/aihub.db \
            data/uploads/ \
            image/ \
            backups/ \
            --exclude='data/__pycache__' \
            2>/dev/null || true
        
        echo ""
        echo "✅ 백업 완료:"
        echo "   파일：$BACKUP_NAME"
        echo "   크기：$(du -h "$BACKUP_NAME" | cut -f1)"
        echo ""
        echo "운영 서버로 전송:"
        echo "   scp $BACKUP_NAME devuser@10.27.210.71:/home/devuser/"
        echo ""
        ;;
        
    restore)
        if [ -z "$BACKUP_FILE" ]; then
            echo "❌ 백업 파일 경로를 지정해주세요."
            echo "   사용법：bash migrate.sh restore /path/to/backup.tar.gz"
            exit 1
        fi
        
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "❌ 파일을 찾을 수 없습니다：$BACKUP_FILE"
            exit 1
        fi
        
        echo "📥 백업 파일 적용 중..."
        echo "   파일：$BACKUP_FILE"
        
        # 현재 데이터 백업
        if [ -f "data/aihub.db" ]; then
            echo "🔄 기존 데이터 백업..."
            cp data/aihub.db "data/aihub.db.backup_$(date +%Y%m%d_%H%M%S)"
        fi
        
        # 백업解压
        tar -xzvf "$BACKUP_FILE"
        
        echo ""
        echo "✅ 백업 적용 완료"
        echo ""
        echo "서버 재시작:"
        echo "  bash scripts/restart.sh"
        echo ""
        ;;
        
    *)
        echo "❌ 잘못된 명령입니다."
        echo ""
        echo "사용법:"
        echo "  bash migrate.sh backup                                    # 백업 생성"
        echo "  bash migrate.sh restore /path/to/backup.tar.gz            # 백업 적용"
        echo ""
        exit 1
        ;;
esac
