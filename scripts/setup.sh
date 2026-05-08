#!/bin/bash
# AIHub 운영 서버 설정 스크립트
# 사용법：bash setup.sh

set -e

echo "========================================"
echo "  AIHub 운영 서버 설정"
echo "========================================"

# 설치 경로 (기본값: /opt/aihub)
INSTALL_DIR="${INSTALL_DIR:-/opt/aihub}"
USER="${USER:-devuser}"
CONDA_ENV="aihub"
PYTHON_VERSION="3.13"

echo "설치 경로：$INSTALL_DIR"
echo "사용자：$USER"
echo ""

# 1. 디렉터리 생성
echo "📁 디렉터리 생성 중..."
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups" "$INSTALL_DIR/logs"
sudo chown -R $USER:$USER "$INSTALL_DIR"
echo "✅ 디렉터리 생성 완료"

# 2. Conda 환경 확인
echo ""
echo "🐍 Conda 환경 확인 중..."
if ! command -v conda &> /dev/null; then
    echo "❌ conda 가 설치되지 않았습니다."
    echo "conda 를 먼저 설치해주세요: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# 환경이 없으면 생성
if ! conda env list | grep -q "^$CONDA_ENV "; then
    echo "🔄 Conda 환경 생성 중 ($CONDA_ENV)..."
    conda create -n $CONDA_ENV python=$PYTHON_VERSION -y
    
    # 의존성 설치
    echo "📦 의존성 설치 중..."
    conda activate $CONDA_ENV
    pip install fastapi uvicorn python-multipart python-jose[cryptography] passlib[bcrypt] pyodbc
    echo "✅ 의존성 설치 완료"
else
    echo "✅ Conda 환경 이미 존재 ($CONDA_ENV)"
fi

# 3. 환경 변수 파일 생성
echo ""
echo "⚙️  환경 변수 파일 생성 중..."
if [ ! -f "$INSTALL_DIR/backend/.env" ]; then
    cat > "$INSTALL_DIR/backend/.env" << 'EOF'
# PMS 데이터베이스 설정
PMS_HOST=10.27.210.26
PMS_PORT=1433
PMS_DATABASE=PMS
PMS_USER=pmsuser
PMS_PASSWORD=pms!@#$

# 서버 설정
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# 애플리케이션 설정
APP_NAME=MG 신용정보 AI Hub
APP_ENV=production

# 세션 설정
TOKEN_EXPIRY_HOURS=168

# 업로드 설정
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=data/uploads

# 데이터베이스 설정
DB_PATH=data/aihub.db
BACKUP_DIR=backups
BACKUP_RETENTION_DAYS=7
EOF
    echo "✅ .env 파일 생성 완료"
else
    echo "⚠️  .env 파일 이미 존재 (스킵)"
fi

# 4. 스크립트 실행 권한 설정
echo ""
echo "🔧 스크립트 권한 설정 중..."
chmod +x "$INSTALL_DIR/scripts"/*.sh
echo "✅ 권한 설정 완료"

# 5. systemd 서비스 파일 생성 (선택)
echo ""
read -p "systemd 서비스로 등록하시겠습니까？(y/n): " register_service
if [ "$register_service" = "y" ]; then
    echo "📝 systemd 서비스 파일 생성 중..."
    CONDA_PATH="/home/$USER/conda_envs/$CONDA_ENV"
    
    sudo tee /etc/systemd/system/aihub.service > /dev/null << EOF
[Unit]
Description=AIHub Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="CONDA_PREFIX=$CONDA_PATH"
ExecStart=$CONDA_PATH/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable aihub
    echo "✅ systemd 서비스 등록 완료"
    echo ""
    echo "서비스 시작:"
    echo "  sudo systemctl start aihub"
    echo "서비스 상태 확인:"
    echo "  sudo systemctl status aihub"
else
    echo "⊘ systemd 서비스 등록 스킵"
fi

# 6. 방화벽 설정 (선택)
echo ""
read -p "방화벽에 8000 포트 를開放하시겠습니까？(y/n): " setup_firewall
if [ "$setup_firewall" = "y" ]; then
    echo "🔥 방화벽 설정 중..."
    if command -v firewall-cmd &> /dev/null; then
        # firewalld
        sudo firewall-cmd --permanent --add-port=8000/tcp
        sudo firewall-cmd --reload
        echo "✅ firewalld 설정 완료"
    elif command -v ufw &> /dev/null; then
        # UFW
        sudo ufw allow 8000/tcp
        echo "✅ UFW 설정 완료"
    else
        echo "⚠️  방화벽 관리자를 찾을 수 없습니다. 수동으로 설정해주세요."
    fi
else
    echo "⊘ 방화벽 설정 스킵"
fi

echo ""
echo "========================================"
echo "  ✅ 설정 완료!"
echo "========================================"
echo ""
echo "다음 단계:"
echo "1. 소스 코드를 $INSTALL_DIR 에 복사하세요"
echo "2. 데이터베이스 파일을 $INSTALL_DIR/data/ 에 복사하세요"
echo "3. 이미지 파일을 $INSTALL_DIR/image/ 에 복사하세요"
echo ""
echo "서버 시작:"
echo "  cd $INSTALL_DIR"
echo "  bash scripts/start.sh 8000"
echo ""
echo "또는 systemd 사용:"
echo "  sudo systemctl start aihub"
echo ""
echo "접속 URL: http://10.27.210.71:8000"
echo ""
