# AIHub 운영 서버 설치 가이드

## 📋 시스템 요구사항

- **OS**: Linux (RHEL/CentOS/Ubuntu)
- **Python**: 3.10 이상
- **Conda**: 권장
- **메모리**: 2GB 이상
- **디스크**: 1GB 이상

---

## 1️⃣ Conda 환경 설치

```bash
# conda 환경 생성
conda create -n aihub python=3.13 -y

# 환경 활성화
conda activate aihub

# 의존성 설치
pip install fastapi uvicorn python-multipart python-jose[cryptography] passlib[bcrypt] pyodbc
```

---

## 2️⃣ 소스 코드 설치

```bash
# 설치 위치 (예시)
sudo mkdir -p /opt/aihub
sudo chown devuser:devuser /opt/aihub

# 소스 코드 복사 (devuser 로 작업)
cd /home/devuser/wjkim
tar -czvf aihub_source.tar.gz aihub/

# 운영 서버로 이동
scp aihub_source.tar.gz devuser@10.27.210.71:/home/devuser/

# 운영 서버에서解压
ssh devuser@10.27.210.71
cd /home/devuser
tar -xzvf aihub_source.tar.gz
sudo mv aihub /opt/
sudo chown -R devuser:devuser /opt/aihub
```

---

## 3️⃣ 환경 변수 설정

```bash
# .env 파일 생성
cd /opt/aihub
cp backend/.env.example backend/.env

# 편집 (필요시 수정)
vi backend/.env
```

**기본 설정 (수정 불필요):**
```
PMS_HOST=10.27.210.26
PMS_PORT=1433
PMS_DATABASE=PMS
PMS_USER=pmsuser
PMS_PASSWORD=pms!@#$
SERVER_PORT=8000
```

---

## 4️⃣ 디렉터리 구조 확인

```bash
cd /opt/aihub
mkdir -p data backups logs

# 권한 설정
chmod 755 data backups logs
chmod +x scripts/*.sh
```

---

## 5️⃣ 데이터 마이그레이션 (기존 서버에서)

```bash
# 기존 서버에서 백업
cd /home/devuser/wjkim/aihub
tar -czvf aihub_data.tar.gz \
  data/aihub.db \
  data/uploads/ \
  image/ \
  backups/

# 운영 서버로 전송
scp aihub_data.tar.gz devuser@10.27.210.71:/opt/aihub/

# 운영 서버에서解压
ssh devuser@10.27.210.71
cd /opt/aihub
tar -xzvf aihub_data.tar.gz
rm aihub_data.tar.gz
```

---

## 6️⃣ 서버 시작

```bash
# 수동 시작 (테스트)
cd /opt/aihub
bash scripts/start.sh 8000

# 상태 확인
curl http://localhost:8000

# 로그 확인
tail -f logs/aihub_8000.log
```

---

## 7️⃣ 시스템 서비스로 등록 (선택)

```bash
# systemd 서비스 파일 생성
sudo vi /etc/systemd/system/aihub.service
```

**내용:**
```ini
[Unit]
Description=AIHub Service
After=network.target

[Service]
Type=simple
User=devuser
WorkingDirectory=/opt/aihub
Environment="CONDA_PREFIX=/home/devuser/conda_envs/aihub"
ExecStart=/home/devuser/conda_envs/aihub/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**서비스 시작:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable aihub
sudo systemctl start aihub
sudo systemctl status aihub
```

---

## 8️⃣ 방화벽 설정

```bash
# firewalld 사용 시
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# iptables 사용 시
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo service iptables save
```

---

## 🎯 접속 확인

브라우저에서 접속:
```
http://10.27.210.71:8000
```

**테스트 계정:**
- ID: `woojinny`
- Password: `dnwls7952*`

---

## 🔧 문제 해결

### 서버가 시작되지 않을 때
```bash
# 로그 확인
tail -100 logs/aihub_8000.log

# 포트 충돌 확인
sudo netstat -tlnp | grep 8000
sudo lsof -i :8000

# conda 환경 확인
conda activate aihub
python --version
```

### PMS 연결 오류
```bash
# 네트워크 연결 확인
telnet 10.27.210.26 1433

# ODBC 드라이버 확인
odbcinst -q -d

# 테스트 스크립트 실행
cd /opt/aihub
python aicredit/test_connection.py
```

### 데이터베이스 오류
```bash
# 백업에서 복구
cp backups/aihub_backup_YYYYMMDD_HHMMSS.db data/aihub.db

# 권한 확인
ls -la data/aihub.db
```

---

## 📊 모니터링

```bash
# 실시간 로그
tail -f logs/aihub_8000.log

# 서버 상태
systemctl status aihub

# 리소스 사용량
top -p $(pgrep -f uvicorn)

# 접근 로그
grep "200 OK" logs/aihub_8000.log | wc -l
```

---

## 🔄 업데이트 방법

```bash
# 기존 백업
cd /opt/aihub
tar -czvf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/

# 새 소스 다운로드
cd /home/devuser
tar -xzvf aihub_source.tar.gz

# 서버 중지
sudo systemctl stop aihub

# 백업 및 교체
cp -r /opt/aihub/data /opt/aihub/data.backup
cp -r aihub/* /opt/aihub/

# 서버 시작
sudo systemctl start aihub
```

---

## 📞 지원

문제가 발생하면 다음 정보를 수집하여 문의하세요:

```bash
# 시스템 정보
uname -a
python --version
conda --version

# 로그
tail -200 logs/aihub_8000.log

# 프로세스
ps aux | grep uvicorn

# 포트
netstat -tlnp | grep 8000
```
