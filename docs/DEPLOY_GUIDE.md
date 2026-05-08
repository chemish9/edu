# AIHub 73 번 서버 배포 가이드

## 📋 배포 절차

### 1. 파일 전송 (로컬에서 실행)

```bash
# PowerShell 또는 CMD 에서 실행
sftp devuser@10.27.210.73
# 비밀번호: dev2026!

# SFTP 프롬프트에서:
cd ~/
put -r aihub_20260414.zip
bye
```

---

### 2. 서버 접속 및 배포 (서버에서 실행)

```bash
# SSH 접속
ssh devuser@10.27.210.73
# 비밀번호: dev2026!

# 홈 디렉터리로 이동
cd ~/

# 배포 스크립트 실행
bash deploy.sh
```

---

### 3. 서버 시작

```bash
# 서버 시작
bash start.sh

# 또는 수동 시작
conda activate aihub
cd ~/aihub
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

### 4. 접속 확인

브라우저에서 접속:
```
http://10.27.210.73:8000
```

**데모 계정:**
- 관리자: `admin` / `admin1234`
- 일반: `E1001` / `test1234`

---

## 🔧 유용한 명령어

### 서버 상태 확인
```bash
# 실행 중인 프로세스
ps aux | grep uvicorn

# 로그 확인
tail -f ~/aihub/aihub.log

# 포트 확인
netstat -tulpn | grep 8000
```

### 서버 중지
```bash
# uvicorn 프로세스 종료
pkill -f uvicorn

# 또는 PID 확인 후 종료
ps aux | grep uvicorn
kill <PID>
```

### 서버 재시작
```bash
cd ~/aihub
conda activate aihub
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### DB 초기화
```bash
cd ~/aihub
rm aihub.db
conda activate aihub
python -m backend.seed
```

---

## ⚠️ 주의사항

1. **pydantic_core**는 Linux x86_64 + Python 3.13 전용입니다
2. 서버 아키텍처 확인: `uname -m` (x86_64 이어야 함)
3. Conda 경로가 다르면 `start.sh` 수정 필요
4. 포트 8000 이 사용 중이면 변경 필요

---

## 🐛 문제 해결

**Conda 를 찾을 수 없음**
```bash
# Conda 설치 경로 확인
which conda
# 또는
ls ~/miniconda3/bin/conda
ls ~/anaconda3/bin/conda
```

**포트 충돌**
```bash
# 사용 중인 프로세스 확인
lsof -i :8000
# 종료
kill -9 <PID>
```

**패키지 설치 실패**
```bash
# 수동으로 pip 설치
cd ~/aihub/target_packages
pip install *.whl
```
