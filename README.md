# AIHub — 사내 AI 활용사례 수집 플랫폼

FastAPI + SQLite + 단일 HTML SPA 로 구성된 사내 AI 활용사례 공유 플랫폼입니다.
PMS(MSSQL) 와 연동하여 사용자 인증을 지원하며, 관리자는 통계·사용자 관리를 담당합니다.

---

## 📁 프로젝트 구조

```
aihub/
├── backend/              # 백엔드 소스 코드
│   ├── auth.py          # JWT 인증, PMS 인증
│   ├── db.py            # SQLite 데이터베이스
│   ├── hrdb.py          # PMS(MSSQL) 연결
│   ├── main.py          # FastAPI 앱
│   ├── models.py        # Pydantic 모델
│   └── seed.py          # 데모 데이터
├── frontend/            # 프론트엔드
│   └── index.html       # 단일 파일 SPA
├── tests/               # 테스트 코드
├── scripts/             # 관리 스크립트
│   ├── start.sh         # 서버 시작
│   ├── stop.sh          # 서버 중지
│   ├── status.sh        # 서버 상태 확인
│   ├── deploy.sh        # 배포 스크립트
│   └── download_packages.sh
├── docs/                # 문서
│   ├── README.md        # 프로젝트 개요
│   ├── INSTALL.md       # 설치 가이드
│   └── DEPLOY_GUIDE.md  # 배포 가이드
├── data/                # 데이터베이스
│   └── aihub.db         # SQLite DB
├── logs/                # 로그 파일
├── packages/            # 오프라인 설치 패키지
├── config/              # 설정 파일
│   ├── requirements.txt
│   └── packages.txt
└── tools/               # 유틸리티
    ├── test_pms.py      # PMS 연결 테스트
    └── analyze_hrdb.py  # HRDB 분석
```

---

## 🚀 빠른 시작

상세한 설치 가이드는 [docs/INSTALL.md](docs/INSTALL.md) 를 참조하세요.

```bash
# 1. Conda 가상환경 생성
conda create -n aihub python=3.13 -y
conda activate aihub

# 2. 의존성 설치
pip install -r config/requirements.txt

# 3. 서버 실행
bash scripts/start.sh 8000
```

브라우저에서 접속：`http://<서버 IP>:8000`

---

## 📚 주요 문서

- [docs/README.md](docs/README.md) - 프로젝트 개요
- [docs/INSTALL.md](docs/INSTALL.md) - 상세 설치 가이드
- [docs/DEPLOY_GUIDE.md](docs/DEPLOY_GUIDE.md) - 배포 가이드

---

## 🔧 서버 관리

```bash
# 서버 시작
bash scripts/start.sh 8000

# 서버 상태 확인
bash scripts/status.sh 8000

# 서버 중지
bash scripts/stop.sh 8000

# 배포
bash scripts/deploy.sh

# 패키지 다운로드
bash scripts/download_packages.sh
```

---

## 👥 데모 계정

| 구분 | 아이디 | 비밀번호 |
|------|--------|----------|
| 관리자 | `admin` | `admin1234` |
| 일반 사용자 | `E1001` | `test1234` |

> PMS 연동 시 PMS 계정으로 로그인 가능합니다

---

## 📊 주요 기능

- **PMS 연동 인증**: PMS(MSSQL) 와 연동하여 사내 계정 로그인
- **사례 등록**: 로그인한 모든 사용자가 즉시 등록·공개
- **추천/댓글**: 사례 추천 및 댓글 기능
- **검색/필터**: 키워드 + 카테고리/태그/AI 도구/부서 필터
- **관리자 대시보드**: 통계, 랭킹, 사용자 관리
- **Excel 내보내기**: 4 개 시트 통계 내보내기
- **페이지네이션**: 한 페이지 20 건 표시

---

## 📦 오프라인 설치

폐쇄망 환경에서 설치하는 방법은 [docs/INSTALL.md](docs/INSTALL.md) 를 참조하세요.

1. `scripts/download_packages.sh` 로 wheel 파일 다운로드
2. `packages/` 디렉터리를 운영 서버로 이관
3. `scripts/deploy.sh` 실행

---

## 🛠️ 개발

```bash
# PMS 연결 테스트
conda activate aihub
python tools/test_pms.py

# 테스트 실행
pytest tests/ -v
```

---

## 📝 라이선스

사내 전용 소프트웨어입니다.
