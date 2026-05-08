#!/bin/bash
# aihub 서버 시작 스크립트 (자동 conda 환경 전환)
# 사용법：bash start.sh [포트번호]
# 예：bash start.sh 8080
#      bash start.sh (기본 포트 8000)

# 포트 번호 설정 (기본값 8000, 파라미터로 전달 가능)
PORT=${1:-8000}

echo "========================================"
echo "  AIHub 서버 시작"
echo "  포트：$PORT"
echo "========================================"

# 현재 사용자 확인
CURRENT_USER=$(whoami)
echo "현재 사용자：$CURRENT_USER"

# devuser 의 conda 환경 경로
CONDA_ENV_PATH="/home/devuser/conda_envs/aihub"

# 현재 사용자가 root 인지 확인
if [ "$CURRENT_USER" = "root" ]; then
    echo "⚠️  root 사용자입니다. devuser 의 conda 환경을 직접 사용합니다."
    
    # devuser 의 conda 환경이 있는지 확인
    if [ ! -d "$CONDA_ENV_PATH" ]; then
        echo "❌ devuser 의 conda 환경을 찾을 수 없습니다：$CONDA_ENV_PATH"
        exit 1
    fi
    
    # devuser 의 python 으로 uvicorn 직접 실행
    UVICORN_PATH="$CONDA_ENV_PATH/bin/uvicorn"
    
    if [ ! -f "$UVICORN_PATH" ]; then
        echo "❌ uvicorn 을 찾을 수 없습니다：$UVICORN_PATH"
        exit 1
    fi
    
    echo "✅ uvicorn 경로：$UVICORN_PATH"
else
    # 일반 사용자 (devuser) 일 경우 conda 환경 활성화
    
    # Conda 초기화 확인
    echo "Conda 초기화 확인..."
    if ! grep -q "conda initialize" ~/.bashrc 2>/dev/null; then
        echo "conda init 실행 중..."
        conda init bash
    fi
    
    # bashrc 로드
    echo "bashrc 로드 중..."
    source ~/.bashrc
    
    # aihub 환경 활성화
    echo "aihub 환경 활성화 중..."
    if ! conda activate aihub; then
        echo "❌ aihub 환경을 찾을 수 없습니다."
        echo "사용 가능한 conda 환경 목록:"
        conda env list
        exit 1
    fi
    
    echo "✅ 활성화된 환경：$CONDA_DEFAULT_ENV"
    
    # uvicorn 확인
    if ! command -v uvicorn &> /dev/null; then
        echo "❌ uvicorn 을 찾을 수 없습니다."
        exit 1
    fi
    
    UVICORN_PATH=$(which uvicorn)
    echo "✅ uvicorn 경로：$UVICORN_PATH"
fi

# 프로젝트 디렉터리 자동 감지
# 1. 현재 디렉터리가 aihub 루트인지 확인 (backend 폴더가 있는지)
# 2. 아니면 스크립트 위치에서 상위로 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
    PROJECT_DIR="$SCRIPT_DIR/.."
else
    PROJECT_DIR="$(pwd)"
fi

cd "$PROJECT_DIR" || exit 1
echo "✅ 현재 디렉터리：$(pwd)"

# 로그 및 PID 파일 경로 (프로젝트 디렉터리 기준)
LOGS_DIR="logs"
mkdir -p "$LOGS_DIR"
PID_FILE="$LOGS_DIR/aihub_${PORT}.pid"
LOG_FILE="$LOGS_DIR/aihub_${PORT}.log"

# ─────────────────────────────────────────────
# 데이터베이스 자동 백업 (매일 서버 시작 시)
# ─────────────────────────────────────────────
echo ""
echo "데이터베이스 백업 확인..."

BACKUP_SCRIPT="scripts/backup.sh"
BACKUP_DIR="backups"
YESTERDAY=$(date -d "yesterday" '+%Y-%m-%d' 2>/dev/null || date -v-1d '+%Y-%m-%d')

# 어제 백업이 있는지 확인
YESTERDAY_BACKUP=$(ls -1 "$BACKUP_DIR"/aihub_backup_${YESTERDAY}*.db 2>/dev/null | head -1)

if [ -z "$YESTERDAY_BACKUP" ]; then
    # 어제 백업이 없으면 새 백업 생성
    echo "📦 오늘 백업 생성 중..."
    if [ -x "$BACKUP_SCRIPT" ] || [ -f "$BACKUP_SCRIPT" ]; then
        bash "$BACKUP_SCRIPT" 7 > /dev/null 2>&1
        echo "✅ 백업 완료"
    else
        echo "⚠️  백업 스크립트 없음: $BACKUP_SCRIPT"
    fi
else
    echo "✅ 어제 백업 있음 ($(basename "$YESTERDAY_BACKUP"))"
fi

# 로그 및 PID 파일 경로
LOGS_DIR="logs"
mkdir -p "$LOGS_DIR"
PID_FILE="$LOGS_DIR/aihub_${PORT}.pid"
LOG_FILE="$LOGS_DIR/aihub_${PORT}.log"

# 기존 프로세스 종료 (같은 포트 사용 중일 경우)
echo "기존 프로세스 확인..."
fuser -k ${PORT}/tcp 2>/dev/null || true

# 기존 PID 파일이 있다면 해당 프로세스 확인
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️  기존 프로세스 ($OLD_PID) 를 종료합니다."
        kill $OLD_PID 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# 로그 파일 초기화
> "$LOG_FILE"

# 서버 시작 (백그라운드)
echo "서버 시작 중..."
nohup $UVICORN_PATH backend.main:app --host 0.0.0.0 --port $PORT > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# PID 파일 저장
echo $SERVER_PID > $PID_FILE

# 실행 확인
sleep 2

if ps aux | grep -v grep | grep -q "uvicorn.*$PORT"; then
    echo ""
    echo "========================================"
    echo "  ✅ 서버 시작 완료!"
    echo "========================================"
    echo ""
    echo "PID: $(ps aux | grep -v grep | grep "uvicorn.*$PORT" | awk '{print $2}')"
    echo "로그：tail -f $LOG_FILE"
    echo "접속：http://<서버 IP>:$PORT"
    echo ""
else
    echo ""
    echo "========================================"
    echo "  ❌ 서버 시작 실패!"
    echo "========================================"
    echo ""
    echo "로그 확인:"
    cat "$LOG_FILE" 2>/dev/null || echo "로그 파일을 읽을 수 없습니다."
    echo ""
    exit 1
fi
