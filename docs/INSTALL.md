# AIHub - 운영 서버 설치 가이드

## 개요

이 문서는 AIHub 를 새로운 운영 서버에 설치하는 방법을 안내합니다.

## 시스템 요구사항

| 항목 | 요구사항 |
|------|----------|
| OS | Linux (x86_64) |
| Python | 3.13 |
| Conda | 권장 (선택사항) |
| 네트워크 | 폐쇄망 지원 (오프라인 설치 가능) |
| 데이터베이스 | PMS(MSSQL) 연결 가능 |

---

## 설치 방법

### 방법 1: 온라인 설치 (인터넷 연결 가능)

#### 1. Conda 가상환경 생성 (권장)

```bash
conda create -n aihub python=3.13 -y
conda activate aihub
```

#### 2. 프로젝트 파일 복사

```bash
cd ~/
git clone <aihub-repository-url>  # 또는 tarball 에서解压
cd aihub
```

#### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

#### 4. PMS 연결 설정

`backend/hrdb.py` 파일을 편집하여 PMS 연결 정보를 수정합니다:

```python
PMS_CONFIG = {
    "host": "10.27.210.26",      # PMS 서버 IP
    "port": 1433,                 # MSSQL 포트
    "database": "PMS",            # 데이터베이스 이름
    "user": "pmsuser",            # 사용자명
    "password": "pms!@#$",        # 비밀번호
}
```

#### 5. 서버 시작

```bash
bash start.sh 8000
```

#### 6. 접속 확인

브라우저에서 `http://<서버 IP>:8000` 으로 접속합니다.

---

### 방법 2: 오프라인 설치 (폐쇄망 환경)

#### 사전 준비 (인터넷 연결 가능한 서버에서)

1. `target_packages/` 디렉터리가 이미 준비되어 있는지 확인합니다.
2. 없다면 다음 명령으로 다운로드합니다:

```bash
cd ~/aihub
bash download_packages.sh
```

3. `target_packages/` 디렉터리를 운영 서버로 이관합니다:

```bash
# 예: scp 사용
scp -r target_packages/ user@operating-server:~/aihub/

# 또는 USB 등 물리적 매체로 이관
```

#### 운영 서버에서 설치

1. **Conda 가상환경 생성**

```bash
conda create -n aihub python=3.13 -y
conda activate aihub
```

2. **프로젝트 파일 복사**

```bash
cd ~/
# aihub 프로젝트를 복사하거나解压
cd aihub
```

3. **오프라인 패키지 설치**

```bash
pip install --no-index --find-links=target_packages -r packages.txt
```

4. **설치 확인**

```bash
pip list | grep -E "fastapi|uvicorn|pydantic|PyJWT|pymssql|openpyxl"
```

예상 출력:

```
fastapi           0.135.3
openpyxl          3.1.5
pydantic          2.13.1
PyJWT             2.12.1
pymssql           2.3.11
uvicorn           0.44.0
```

5. **PMS 연결 설정**

`backend/hrdb.py` 파일을 편집하여 PMS 연결 정보를 수정합니다.

6. **서버 시작**

```bash
bash start.sh 8000
```

---

## 서버 관리

### 서버 시작

```bash
bash start.sh 8000      # 포트 8000 (기본)
bash start.sh 8080      # 포트 8080
```

### 서버 상태 확인

```bash
bash status.sh 8000     # 포트 8000 (기본)
```

출력 예시:

```
========================================
  AIHub 서버 상태
  포트：8000
========================================
✅ 서버가 실행 중입니다

PID: 12345
포트：8000
로그：aihub_8000.log

상세 정보:
12345  0.3  0.0       04:00 /home/devuser/conda_envs/aihub/bin/python3.13 ...

최근 로그:
INFO:     10.27.210.100:54321 - "GET / HTTP/1.1" 200 OK
```

### 서버 중지

```bash
bash stop.sh 8000       # 포트 8000 (기본)
```

---

## 환경변수 설정

### JWT 시크릿 키 변경 (필수)

운영 배포 시 반드시 `AIHUB_SECRET` 을 안전한 랜덤 문자열로 변경하세요:

```bash
# .bashrc 또는 환경 설정 파일에 추가
export AIHUB_SECRET="your-strong-random-secret-here"

# 또는 서버 시작 시 직접 지정
AIHUB_SECRET="your-strong-random-secret-here" bash start.sh 8000
```

시크릿 키 생성 예시:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### SQLite DB 경로 변경 (선택사항)

```bash
export AIHUB_DB="/var/lib/aihub/aihub.db"
bash start.sh 8000
```

---

## PMS 연결 테스트

PMS 연결이 제대로 설정되었는지 테스트합니다:

```bash
conda activate aihub
python test_pms.py
```

성공 시 출력:

```
✅ PMS 연결 성공!
사용자 수：356
부서 수：30
```

---

## 문제 해결

### 1. 패키지 설치 실패

**문제**: `ERROR: ... is not a supported wheel on this platform`

**원인**: 서버 아키텍처 또는 Python 버전이 맞지 않음

**해결**:

```bash
# 아키텍처 확인
uname -m

# Python 버전 확인
python3 --version

# 해당 플랫폼용 wheel 파일 재다운로드
bash download_packages.sh
```

### 2. 모듈을 찾을 수 없음

**문제**: `ModuleNotFoundError: No module named 'backend'`

**해결**: 반드시 프로젝트 루트 디렉터리에서 실행하세요

```bash
cd ~/aihub
bash start.sh 8000
```

### 3. 포트 충돌

**문제**: `Address already in use`

**해결**:

```bash
# 사용 중인 프로세스 확인
bash status.sh 8000

# 서버 중지
bash stop.sh 8000

# 다시 시작
bash start.sh 8000
```

### 4. PMS 연결 실패

**문제**: `pymssql.OperationalError: ...`

**해결**:

1. PMS 서버 네트워크 연결 확인
2. `backend/hrdb.py` 의 연결 정보 확인
3. `test_pms.py` 로 연결 테스트

### 5. DB 초기화

**문제**: DB 데이터가 손상되었거나 초기화가 필요함

**해결**:

```bash
# 기존 DB 백업
cp aihub.db aihub.db.backup

# 새 DB 생성
rm aihub.db
bash start.sh 8000
```

---

## 성능 최적화 (선택사항)

### uvicorn workers 증가

```bash
# backend/main.py 의 app.run() 수정
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### systemd 서비스로 실행

`/etc/systemd/system/aihub.service` 생성:

```ini
[Unit]
Description=AIHub Service
After=network.target

[Service]
Type=simple
User=devuser
WorkingDirectory=/home/devuser/aihub
Environment="PATH=/home/devuser/conda_envs/aihub/bin:%p"
ExecStart=/home/devuser/conda_envs/aihub/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

시작/중지:

```bash
sudo systemctl enable aihub
sudo systemctl start aihub
sudo systemctl status aihub
```

---

## 보안 권장사항

1. **JWT 시크릿 키 변경**: 반드시 고유한 시크릿 키 사용
2. **PMS 비밀번호 보호**: `backend/hrdb.py` 의 파일 권한 제한 (`chmod 600`)
3. **방화벽 설정**: 필요한 포트만 개방
4. **정기 백업**: `aihub.db` 정기 백업
5. **로그 모니터링**: `aihub_8000.log` 정기 확인

---

## 업데이트 방법

1. **새 버전 다운로드**

```bash
cd ~/
git clone <새 버전 repository> aihub-new
```

2. **DB 백업**

```bash
cp ~/aihub/aihub.db ~/aihub/aihub.db.backup
```

3. **기존 서버 중지**

```bash
cd ~/aihub
bash stop.sh 8000
```

4. **기존 프로젝트 백업**

```bash
mv ~/aihub ~/aihub-old
mv ~/aihub-new ~/aihub
```

5. **DB 복원**

```bash
cp ~/aihub.db.backup ~/aihub/aihub.db
```

6. **의존성 재설치**

```bash
conda activate aihub
pip install -r requirements.txt
```

7. **서버 재시작**

```bash
cd ~/aihub
bash start.sh 8000
```

---

## 지원

문제가 발생하면 다음 정보를 수집하여 문의하세요:

```bash
# 시스템 정보
uname -a
python3 --version

# 패키지 목록
pip list

# 로그 파일
cat ~/aihub/aihub_8000.log

# 상태 정보
bash ~/aihub/status.sh 8000
```
