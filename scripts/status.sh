#!/bin/bash
# aihub 서버 상태 확인 스크립트
# 사용법：bash status.sh [포트번호]
# 예：bash status.sh 8080
#      bash status.sh (기본 포트 8000)

PORT=${1:-8000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOGS_DIR/aihub_${PORT}.pid"
LOG_FILE="$LOGS_DIR/aihub_${PORT}.log"

echo "========================================"
echo "  AIHub 서버 상태"
echo "  포트：$PORT"
echo "========================================"

# PID 파일이 있는지 확인
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 서버가 실행 중이 아닙니다 (PID 파일 없음)"
    exit 1
fi

# PID 파일에서 프로세스 ID 읽기
PID=$(cat "$PID_FILE")

# 프로세스가 실행 중인지 확인
if ps -p $PID > /dev/null 2>&1; then
    echo "✅ 서버가 실행 중입니다"
    echo ""
    echo "PID: $PID"
    echo "포트：$PORT"
    echo "로그：$LOG_FILE"
    echo ""
    echo "상세 정보:"
    ps -p $PID -o pid,%cpu,%mem,etime,cmd --no-headers
    echo ""
    echo "최근 로그:"
    tail -5 "$LOG_FILE" 2>/dev/null || echo "로그 파일 없음"
else
    echo "❌ 서버가 종료되었습니다 (PID 파일만 존재)"
    echo "PID 파일 삭제하고 다시 시작하세요:"
    echo "  rm $PID_FILE"
    echo "  bash start.sh $PORT"
    exit 1
fi
