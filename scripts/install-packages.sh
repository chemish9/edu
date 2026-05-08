#!/bin/bash
# AIHub - 수동 패키지 설치 스크립트 (폐쇄망 환경용)
# deploy.sh 실행 시 문제가 발생한 경우 사용

set -e

echo "========================================"
echo "  AIHub - 수동 패키지 설치 (폐쇄망)"
echo "========================================"

# Conda 경로 자동 감지
CONDA_PATH=""
if command -v conda &> /dev/null; then
    CONDA_PATH=$(which conda)
elif [ -d "$HOME/miniconda3" ]; then
    CONDA_PATH="$HOME/miniconda3/bin/conda"
elif [ -d "$HOME/anaconda3" ]; then
    CONDA_PATH="$HOME/anaconda3/bin/conda"
elif [ -d "/opt/anaconda3" ]; then
    CONDA_PATH="/opt/anaconda3/bin/conda"
elif [ -d "/opt/miniconda3" ]; then
    CONDA_PATH="/opt/miniconda3/bin/conda"
fi

if [ -z "$CONDA_PATH" ]; then
    echo "❌ Conda 를 찾을 수 없습니다."
    exit 1
fi

echo "✅ Conda 경로: $CONDA_PATH"

# Conda 초기화
source ~/.bashrc 2>/dev/null || source ~/.bash_profile 2>/dev/null || true

# 환경 활성화
echo "Conda 환경 활성화 중..."
conda activate aihub

# Python 버전 확인
echo "Python 버전: $(python --version)"

# Nexus 또는 packages/ 사용
echo ""
echo "패키지 설치 방법 확인..."

if [ -n "$NEXUS_URL" ]; then
    echo "→ Nexus 사용: $NEXUS_URL"
    pip install -r config/packages.txt --index-url "$NEXUS_URL"
elif [ -d "packages" ]; then
    echo "→ 오프라인 packages/ 사용"
    pip install --no-index --find-links=packages -r config/packages.txt
else
    echo "❌ packages/ 디렉터리가 없고 Nexus 설정도 없습니다."
    echo ""
    echo "설치 방법:"
    echo ""
    echo "방법 1: Nexus 환경 변수 설정"
    echo "  export NEXUS_URL=http://10.27.210.114:8081/repository/pypi-simple/"
    echo "  bash scripts/install-packages.sh"
    echo ""
    echo "방법 2: packages/ 디렉터리 준비"
    echo "  (인터넷 연결 서버에서 download_packages.sh 실행 후 packages/ 폴더 복사)"
    echo ""
    exit 1
fi

echo ""
echo "✅ 설치 완료!"
echo ""
echo "설치된 패키지 확인:"
pip list | grep -E "fastapi|uvicorn|pydantic|PyJWT|python-dotenv|python-multipart|pymssql|openpyxl"
