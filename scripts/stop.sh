#!/bin/bash
# aihub 서버 중지 스크립트
# 사용법：bash stop.sh [포트번호]
# 예：bash stop.sh 8080
#      bash stop.sh (기본 포트 8000)

PORT=${1:-8000}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$PROJECT_DIR/logs"
PID_FILE="$LOGS_DIR/aihub_${PORT}.pid"

echo "========================================"
echo "  AIHub 서버 중지"
echo "  포트：$PORT"
echo "========================================"

# PID 파일이 있는지 확인
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  PID 파일을 찾을 수 없습니다: $PID_FILE"
    echo "포트 $PORT 를 사용하는 프로세스를 확인합니다..."

    # 포트를 사용하는 프로세스 확인
    PID=$(lsof -t -i :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        echo "프로세스 $PID 를 종료합니다."
        kill $PID 2>/dev/null
        sleep 1
        echo "✅ 서버 중지 완료"
    else
        echo "❌ 실행 중인 서버가 없습니다."
    fi
    exit 0
fi

# PID 파일에서 프로세스 ID 읽기
PID=$(cat "$PID_FILE")

# 프로세스가 실행 중인지 확인
if ps -p $PID > /dev/null 2>&1; then
    echo "프로세스 $PID 를 종료합니다."
    kill $PID 2>/dev/null

    # 3 초 동안 대기 후 아직 실행 중이면 강제 종료
    sleep 3
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  강제 종료 중..."
        kill -9 $PID 2>/dev/null
    fi
else
    echo "⚠️  프로세스 $PID 는 이미 종료되었습니다."
fi

# PID 파일 삭제
rm -f "$PID_FILE"
echo "✅ 서버 중지 완료"
