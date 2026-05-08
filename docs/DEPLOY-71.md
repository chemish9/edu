# AIHub 71 번 서버 배포 가이드

## 📋 배포 전 준비사항

### 1. 수정된 파일 목록
```
backend/db.py          - attachments 테이블 스키마, categories.is_active 컬럼 추가
backend/main.py        - 첨부파일 업로드/다운로드 API 추가 (220 행 추가)
frontend/index.html    - 첨부파일 UI 추가
config/requirements.txt - python-dotenv, python-multipart 추가
scripts/deploy.sh      - 자동 마이그레이션 스크립트 추가
```

### 2. 필수 소프트웨어
- Python 3.13
- Conda
- SQLite3
- OpenSSL (Secret 키 생성용)

---

## 🚀 배포 방법

### 방법 1: 자동 배포 스크립트 사용 (권장)

```bash
# 1. 71 번 서버에 접속
ssh user@10.27.210.71

# 2. 기존 aihub 디렉터리 백업 (선택사항)
cd /home/user
tar -czf aihub_backup_$(date +%Y%m%d).tar.gz aihub

# 3. 새로운 파일들 업로드
# 로컬에서 실행:
scp -r /path/to/aihub/{backend,frontend,config,scripts} user@10.27.210.71:/home/user/aihub/

# 4. 배포 스크립트 실행
cd /home/user/aihub
bash scripts/deploy.sh
```

**배포 스크립트가 자동으로 수행하는 작업:**
- ✅ Conda 가상환경 생성 (aihub)
- ✅ 의존성 패키지 설치 (python-dotenv, python-multipart 포함)
- ✅ `backend/.env` 파일 생성 (무작위 Secret 키)
- ✅ 업로드 디렉토리 생성 (`data/uploads/attachments/`)
- ✅ DB 마이그레이션 (attachments 테이블, is_active 컬럼)
- ✅ 서버 자동 시작 여부 확인

---

### 방법 2: 수동 배포

```bash
# 1. 의존성 설치
source ~/miniconda3/etc/profile.d/conda.sh
conda activate aihub
pip install python-dotenv python-multipart

# 2. 환경 변수 설정
cd /home/user/aihub/backend
echo "AIHUB_SECRET=$(openssl rand -hex 32)" > .env

# 3. 업로드 디렉토리 생성
mkdir -p /home/user/aihub/data/uploads/attachments
chmod 755 /home/user/aihub/data/uploads/attachments

# 4. DB 마이그레이션
sqlite3 /home/user/aihub/data/aihub.db <<EOF
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES use_cases(id)
);

-- is_active 컬럼이 없으면 추가
EOF

# is_active 컬럼 확인 및 추가
if ! sqlite3 /home/user/aihub/data/aihub.db ".schema categories" | grep -q "is_active"; then
    sqlite3 /home/user/aihub/data/aihub.db "ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1;"
fi

# 5. 서버 재시작
pkill -f "uvicorn backend.main:app"
cd /home/user/aihub
bash scripts/start.sh 8000
```

---

## ⚠️ 배포 시 주의사항

### 1. 환경 변수 (필수)
```bash
# backend/.env 파일 반드시 생성
AIHUB_SECRET=<64 자리 16 진수 랜덤 문자열>

# 예:
# AIHUB_SECRET=a1b2c3d4e5f6...
```

### 2. 디렉토리 권한
```bash
# 업로드 디렉토리에 쓰기 권한 필요
chmod 755 data/uploads/attachments
chown -R www-data:www-data data/uploads  # Nginx 사용 시
```

### 3. Nginx 설정 (사용 중일 경우)
```nginx
# /etc/nginx/sites-available/aihub

server {
    listen 80;
    server_name aihub.mginfo.co.kr;

    # 정적 파일
    location / {
        root /home/user/aihub/frontend;
        try_files $uri $uri/ /index.html;
    }

    # API 프록시
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 파일 업로드 크기 제한
        client_max_body_size 50M;
    }

    # 첨부파일 다운로드 (직접 접근 차단)
    location ~* ^/data/uploads/attachments/ {
        deny all;
    }
}
```

### 4. 방화벽 설정
```bash
# 8000 포트 개방 (Nginx 를 사용하지 않을 경우)
sudo ufw allow 8000/tcp
```

---

## ✅ 배포 후 확인사항

### 1. 서버 상태 확인
```bash
# 프로세스 확인
ps aux | grep uvicorn

# 로그 확인
tail -f /home/user/aihub/logs/aihub_8000.log

# 상태 스크립트
bash /home/user/aihub/scripts/status.sh 8000
```

### 2. API 테스트
```bash
# 카테고리 API
curl http://localhost:8000/api/categories

# 사례 목록
curl "http://localhost:8000/api/cases?status=approved"

# 로그인 테스트
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"emp_no":"admin","password":"admin1234"}'
```

### 3. 첨부파일 기능 테스트
```bash
# 1. 로그인 후 Token 획득
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"emp_no":"admin","password":"admin1234"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 2. 테스트 파일 업로드
echo "test content" > /tmp/test.txt
curl -X POST http://localhost:8000/api/attachments/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.txt"

# 3. 업로드된 파일 확인
ls -la /home/user/aihub/data/uploads/attachments/
```

### 4. 프론트엔드 확인
```
브라우저에서 다음 URL 접속:
- http://10.27.210.71:8000
- http://aihub.mginfo.co.kr (Nginx 사용 시)

확인 항목:
✅ 사례 목록 표시
✅ 카테고리 필터 작동
✅ 사례 등록 폼에서 첨부파일 업로드 UI 표시
✅ 사례 상세보기에서 첨부파일 목록 및 다운로드 버튼 표시
```

---

## 🔧 문제 해결

### 에러 1: `no such column: is_active`
```bash
# 해결 방법
sqlite3 /home/user/aihub/data/aihub.db \
  "ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1;"
```

### 에러 2: `No module named 'dotenv'`
```bash
# 해결 방법
conda activate aihub
pip install python-dotenv python-multipart
```

### 에러 3: 첨부파일 업로드 시 500 에러
```bash
# 디렉토리 권한 확인
ls -la /home/user/aihub/data/uploads/
chmod 755 /home/user/aihub/data/uploads/attachments
chown -R $USER:$USER /home/user/aihub/data/uploads
```

### 에러 4: 서버 시작 시 Port already in use
```bash
# 기존 프로세스 종료
pkill -f "uvicorn backend.main:app"
# 또는
sudo kill -9 $(lsof -t -i:8000)

# 서버 재시작
bash scripts/start.sh 8000
```

---

## 📞 지원

문제 발생 시 다음 정보를 수집하여 보고하세요:
```bash
# 1. 서버 로그
tail -100 /home/user/aihub/logs/aihub_8000.log

# 2. 설치된 패키지
conda activate aihub
pip list

# 3. DB 스키마
sqlite3 /home/user/aihub/data/aihub.db ".schema"

# 4. 환경 변수
cat /home/user/aihub/backend/.env
```
