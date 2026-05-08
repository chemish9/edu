#!/bin/bash
# AIHub 서버 배포 스크립트
# 사용법：bash deploy.sh 또는 scripts/deploy.sh

set -e  # 에러 발생 시 중단

# 스크립트 위치에서 aihub 루트 디렉터리 자동 감지
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "$(basename "$SCRIPT_DIR")" = "scripts" ]; then
    cd "$SCRIPT_DIR/.."
fi

# 현재 aihub 루트 디렉터리 저장 (backup 작업용)
AIHUB_ROOT="$(pwd)"

echo "========================================"
echo "  AIHub 서버 배포 시작"
echo "========================================"

# 1. 현재 디렉터리 확인
echo "[1/6] 현재 디렉터리 확인..."
pwd

# 2. backend 디렉터리 확인 (aihub 루트인지 확인)
echo ""
echo "[2/6] 프로젝트 구조 확인..."
if [ -d "backend" ]; then
    echo "✅ aihub 프로젝트 루트 디렉터리로 확인됨 ($AIHUB_ROOT)"
else
    echo "❌ aihub 프로젝트 루트 디렉터리가 아닙니다."
    echo "   backend/ 디렉터리가 있어야 합니다."
    exit 1
fi

# 3. 시스템 정보 확인
echo ""
echo "[3/6] 시스템 정보 확인..."
echo "OS 정보:"
cat /etc/os-release 2>/dev/null | head -2 || cat /etc/redhat-release 2>/dev/null || echo "알 수 없음"
echo ""
echo "Python 버전:"
python3 --version 2>/dev/null || python --version 2>/dev/null || echo "Python 이 설치되지 않았습니다."
echo ""
echo "아키텍처:"
uname -m

# 4. Conda 확인
echo ""
echo "[4/6] Conda 환경 확인..."

# Conda 경로 자동 감지
CONDA_PATH=""
if command -v conda &> /dev/null; then
    CONDA_PATH=$(which conda)
    echo "✅ Conda 설치됨: $CONDA_PATH"
    conda --version
elif [ -d "$HOME/miniconda3" ]; then
    CONDA_PATH="$HOME/miniconda3/bin/conda"
    echo "✅ Conda 발견: $CONDA_PATH"
elif [ -d "$HOME/anaconda3" ]; then
    CONDA_PATH="$HOME/anaconda3/bin/conda"
    echo "✅ Conda 발견: $CONDA_PATH"
elif [ -d "/opt/anaconda3" ]; then
    CONDA_PATH="/opt/anaconda3/bin/conda"
    echo "✅ Conda 발견: $CONDA_PATH"
elif [ -d "/opt/miniconda3" ]; then
    CONDA_PATH="/opt/miniconda3/bin/conda"
    echo "✅ Conda 발견: $CONDA_PATH"
else
    echo "❌ Conda 가 설치되지 않았습니다."
    echo "   설치 위치 확인:"
    echo "   - $HOME/miniconda3"
    echo "   - $HOME/anaconda3"
    echo "   - /opt/anaconda3"
    echo "   - /opt/miniconda3"
    exit 1
fi

# conda init 확인 및 실행
CONDA_BASE=$(dirname $(dirname "$CONDA_PATH"))
if ! grep -q "conda initialize" ~/.bashrc 2>/dev/null && ! grep -q "conda initialize" ~/.bash_profile 2>/dev/null; then
    echo "conda init 실행 중..."
    "$CONDA_PATH" init bash
fi

# 5. 가상환경 생성 및 패키지 설치
echo ""
echo "[5/6] Conda 가상환경 생성 및 패키지 설치..."

# conda init 확인 및 실행
if ! grep -q "conda initialize" ~/.bashrc 2>/dev/null && ! grep -q "conda initialize" ~/.bash_profile 2>/dev/null; then
    echo "conda init 실행 중..."
    conda init bash
fi

# 새 환경 생성 (이미 있으면 건너뜀)
if conda env list | grep -q "^aihub "; then
    echo "⚠️  aihub 환경이 이미 존재합니다. 기존 환경을 사용합니다."
else
    echo "새 Conda 환경 생성 중 (Python 3.13)..."
    conda create -n aihub python=3.13 -y
fi

# 가상환경 활성화
echo "가상환경 활성화..."
source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || true
conda activate aihub

# Wheel 패키지 또는 Nexus 를 통한 패키지 설치
echo "패키지 설치 중..."

# Nexus 환경 변수 확인 (폐쇄망 환경)
if [ -n "$NEXUS_URL" ]; then
    echo "→ Nexus 사용: $NEXUS_URL"
    pip install -r config/packages.txt --index-url "$NEXUS_URL"
elif [ -d "packages" ]; then
    echo "→ 오프라인 설치 (packages/ 사용)"
    pip install --no-index --find-links=packages -r config/packages.txt
else
    echo "⚠️  packages/ 디렉터리가 없고 Nexus 설정도 없습니다."
    echo ""
    echo "다음 중 하나로 설치해야 합니다:"
    echo ""
    echo "방법 1: Nexus 환경 변수 설정 후 재실행"
    echo "  export NEXUS_URL=http://10.27.210.114:8081/repository/pypi-simple/"
    echo "  bash scripts/deploy.sh"
    echo ""
    echo "방법 2: packages/ 디렉터리 준비 후 재실행"
    echo "  (인터넷 연결 서버에서 download_packages.sh 실행)"
    echo ""
    exit 1
fi

# 설치된 패키지 확인
echo ""
echo "설치된 핵심 패키지:"
pip list | grep -E "fastapi|uvicorn|pydantic|PyJWT|pymssql|openpyxl|python-dotenv|python-multipart"

# 5-1. 첨부파일 기능 준비
echo ""
echo "[5-1/6] 첨부파일 기능 준비..."

# .env 파일 생성 (존재하지 않을 경우)
if [ ! -f "backend/.env" ]; then
    echo "✅ backend/.env 파일 생성 중..."
    if command -v openssl &> /dev/null; then
        SECRET=$(openssl rand -hex 32)
    else
        SECRET=$(date +%s | sha256sum | base64 | head -c 64)
    fi
    echo "AIHUB_SECRET=$SECRET" > backend/.env
    echo "   AIHUB_SECRET 생성 완료"
else
    echo "ℹ️  backend/.env 파일이 이미 존재합니다."
fi

# 업로드 디렉토리 생성
echo "✅ 업로드 디렉토리 생성 중..."
mkdir -p data/uploads/attachments
chmod 755 data/uploads/attachments
chown -R $(whoami):$(whoami) data/uploads 2>/dev/null || true
echo "   data/uploads/attachments/ 생성 완료"

# 5-2. 데이터베이스 마이그레이션
echo ""
echo "[5-2/6] 데이터베이스 마이그레이션..."

if [ -f "data/aihub.db" ]; then
    echo "기존 DB 에 마이그레이션 적용 중..."
    
    # attachments 테이블 추가
    sqlite3 data/aihub.db "CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id INTEGER,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        file_type TEXT,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES use_cases(id)
    );" 2>/dev/null && echo "   ✅ attachments 테이블 확인 완료" || echo "   ⚠️  attachments 테이블 생성 실패"
    
    # categories.is_active 컬럼 추가 (존재하지 않을 경우)
    TABLE_SCHEMA=$(sqlite3 data/aihub.db ".schema categories" 2>/dev/null)
    if ! echo "$TABLE_SCHEMA" | grep -q "is_active"; then
        echo "   categories 테이블에 is_active 컬럼 추가 중..."
        sqlite3 data/aihub.db "ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1;" 2>/dev/null && \
            echo "   ✅ is_active 컬럼 추가 완료" || \
            echo "   ⚠️  is_active 컬럼 추가 실패 (이미 존재할 수 있음)"
    else
        echo "   ✅ categories.is_active 컬럼 이미 존재"
    fi
else
    echo "ℹ️  기존 DB 가 없으므로 마이그레이션 스킵"
fi

# 6. 데모 데이터 시드 (선택사항)
echo ""
echo "[6/6] 데모 데이터 시드..."

# 기존 DB 가 있으면 백업 (현재 디렉터리에서)
if [ -f "data/aihub.db" ]; then
    echo "⚠️  기존 DB(data/aihub.db) 가 있습니다."
    echo "   위치：$AIHUB_ROOT/data/aihub.db"
    read -p "기존 DB 를 백업하고 새 데모 데이터를 생성하시겠습니까？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 현재 디렉터리에서 backup 폴더 생성
        mkdir -p backups
        BACKUP_FILE="backups/aihub_backup_$(date +%Y%m%d_%H%M%S).db"
        echo "기존 DB 를 백업합니다：$BACKUP_FILE"
        cp data/aihub.db "$BACKUP_FILE"
        python -m backend.seed
        echo "✅ 데모 데이터 삽입 완료"
    else
        echo "기존 DB 를 유지합니다."
    fi
else
    echo "새 DB 생성 및 데모 데이터 삽입..."
    mkdir -p data
    python -m backend.seed
    echo "✅ 데모 데이터 삽입 완료"
fi

# 서버 자동 시작 여부 확인
echo ""
echo "========================================"
read -p "배포 완료! 이제 서버를 시작하시겠습니까？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "서버 시작 중..."
    bash scripts/start.sh 8000
else
    echo "서버 시작을 건너뜁니다."
    echo "필요시 'bash start.sh 8000' 명령으로 서버를 시작하세요."
fi

# 완료
echo ""
echo "========================================"
echo "  ✅ 배포 완료!"
echo "========================================"
echo ""
echo "서버 시작 방법:"
echo "  bash start.sh 8000"
echo ""
echo "서버 상태 확인:"
echo "  bash status.sh 8000"
echo ""
echo "서버 중지:"
echo "  bash stop.sh 8000"
echo ""
echo "접속 URL: http://<서버 IP>:8000"
echo ""
echo "데모 계정:"
echo "  관리자 : admin / admin1234"
echo "  일반   : E1001 / test1234"
echo ""
echo "PMS 연동 시 PMS 계정으로 로그인 가능합니다."
echo ""
echo "📎 첨부파일 기능:"
echo "  - 업로드 경로：data/uploads/attachments/"
echo "  - 최대 크기：50MB"
echo "  - 허용 형식：PDF, HWP, Excel, PPT, TXT, CSV, JPG, PNG, GIF, ZIP, RAR, 7Z"
echo ""
