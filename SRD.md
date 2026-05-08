# AIHub Software Requirements Specification (SRS)

## 1. Introduction

### 1.1 Purpose
본 문서는 AIHub(사내 AI 활용사례 수집 플랫폼)의 현재 구현 기준 요구사항을 정의한다.  
기획/운영 문서와 실제 코드 간 차이가 존재할 수 있으므로, 본 SRS는 코드 기반 사실을 우선한다.

### 1.2 Scope
AIHub는 사내 사용자가 AI 활용사례를 등록/조회/검색/추천/댓글로 공유하고, 관리자가 사용자/카테고리/통계를 관리하는 웹 애플리케이션이다.

### 1.3 Definitions
- Use case: 사용자가 등록하는 AI 활용사례 게시글
- PMS: 사내 인사/계정 정보가 존재하는 MSSQL 시스템
- Admin: `is_admin=1` 권한을 가진 사용자

### 1.4 References
- `/home/devuser/aihub/backend/main.py`
- `/home/devuser/aihub/backend/auth.py`
- `/home/devuser/aihub/backend/db.py`
- `/home/devuser/aihub/backend/hrdb.py`
- `/home/devuser/aihub/backend/models.py`
- `/home/devuser/aihub/frontend/index.html`
- `/home/devuser/aihub/config/requirements.txt`
- `/home/devuser/aihub/scripts/start.sh`
- `/home/devuser/aihub/tests/test_api.py`

## 2. Overall Description

### 2.1 Product Perspective
- 서버: FastAPI 단일 애플리케이션이 API와 정적 프론트엔드를 함께 제공
- 프론트엔드: 단일 HTML 파일(`frontend/index.html`) + 바닐라 JavaScript
- 데이터 저장소: SQLite(`data/aihub.db`, 환경변수 `AIHUB_DB`로 변경 가능)
- 외부 연동: PMS(MSSQL) 인증 연동, 실패 시 로컬 SQLite 인증 폴백

### 2.2 Product Functions (High-Level)
- 인증: 회원가입, 로그인, 내 정보 조회(JWT)
- 사례: 등록/수정/삭제, 목록/상세, 검색/필터/정렬/페이지네이션
- 상호작용: 추천 토글, 댓글 작성/삭제, 알림
- 관리: 사용자 목록/관리자 권한 토글, 카테고리 관리, 통계 조회, Excel 내보내기
- 첨부파일: 업로드/다운로드/삭제/사례 연결

### 2.3 User Classes
- 일반 사용자
  - 로그인 후 사례 등록, 본인 사례 수정/삭제, 댓글/추천 가능
- 관리자
  - 일반 사용자 기능 포함
  - 사용자 권한 관리, 카테고리 관리, 통계/랭킹/내보내기, 사례 상태 변경 가능

### 2.4 Operating Environment
- OS: Linux 서버 환경(운영 스크립트 기준 bash)
- Runtime: Python 3.13
- DB: SQLite, MSSQL(PMS)
- 브라우저: 최신 Chromium 계열 기준 SPA 사용

### 2.5 Design Constraints
- 프론트엔드 빌드 체인 없이 단일 정적 파일 구조
- 데이터 모델이 SQLite 스키마 중심으로 고정
- 인증 토큰 만료 시간 고정(`EXP_HOURS = 24*7`)
- 파일 업로드 용량 제한: 500MB

## 3. System Architecture

### 3.1 Logical Architecture
- Presentation Layer: `frontend/index.html` (뷰 렌더링 + `fetch('/api/...')`)
- API Layer: `backend/main.py` (라우팅/권한 검증/응답)
- Auth Layer: `backend/auth.py` (JWT, 관리자 권한, PMS 연동 래핑)
- Data Layer: `backend/db.py` (SQLite 연결/스키마/초기 시드)
- External Integration Layer: `backend/hrdb.py` (PMS 인증/부서 조회)

### 3.2 Data Flow
1. 브라우저에서 `/api/*` 호출
2. 필요 시 JWT 검증(`Authorization: Bearer`)
3. PMS 인증 우선 시도(`verify_pms_user`)
4. SQLite CRUD 및 집계 처리
5. JSON 응답(일부 파일/엑셀은 바이너리 응답)

### 3.3 Technology Stack
- Language: Python, HTML, CSS, JavaScript
- Backend: FastAPI, Uvicorn, Pydantic
- Auth: PyJWT, PBKDF2-SHA256(로컬 비밀번호)
- DB: SQLite (`sqlite3`), MSSQL (`pymssql`)
- Env: python-dotenv
- Upload: python-multipart
- Export: openpyxl
- Test: pytest, fastapi.testclient

## 4. Functional Requirements

### 4.1 Authentication
- FR-AUTH-001: 사용자는 사번/비밀번호로 로그인할 수 있어야 한다.
- FR-AUTH-002: 시스템은 로그인 시 PMS 인증을 먼저 시도해야 한다.
- FR-AUTH-003: PMS 인증 성공 시 사용자를 SQLite에 동기화해야 한다.
- FR-AUTH-004: PMS 인증 실패 시 SQLite 사용자 인증으로 폴백해야 한다.
- FR-AUTH-005: 인증 성공 시 JWT를 발급해야 한다.
- FR-AUTH-006: 인증이 필요한 API는 유효한 Bearer 토큰이 없으면 401을 반환해야 한다.
- FR-AUTH-007: 관리자 전용 API는 관리자 권한이 없으면 403을 반환해야 한다.

### 4.2 User Management
- FR-USER-001: 관리자는 전체 사용자 목록을 조회할 수 있어야 한다.
- FR-USER-002: 관리자는 본인을 제외한 사용자의 관리자 권한을 토글할 수 있어야 한다.
- FR-USER-003: 시스템은 최소 1명의 관리자를 유지해야 한다.

### 4.3 Category Management
- FR-CAT-001: 사용자는 활성 카테고리 트리를 조회할 수 있어야 한다.
- FR-CAT-002: 관리자는 카테고리를 생성할 수 있어야 한다.
- FR-CAT-003: 관리자는 카테고리 활성/비활성 상태를 토글할 수 있어야 한다.
- FR-CAT-004: 관리자는 카테고리를 소프트 삭제할 수 있어야 한다.

### 4.4 Use Case Management
- FR-CASE-001: 로그인 사용자는 사례를 등록할 수 있어야 한다.
- FR-CASE-002: 사례 등록 시 제목/요약/도구/태그/본문/효과를 저장할 수 있어야 한다.
- FR-CASE-003: 사례 목록은 상태/카테고리/키워드/도구/부서/태그/정렬/페이지 조건을 지원해야 한다.
- FR-CASE-004: 사례 상세 조회 시 조회수를 증가시켜야 한다.
- FR-CASE-005: 본인(또는 관리자)은 권한 조건을 만족할 경우 사례를 수정할 수 있어야 한다.
- FR-CASE-006: 작성자는 본인 사례만 삭제할 수 있어야 한다(소프트 삭제).
- FR-CASE-007: 관리자는 사례 상태(`approved`, `rejected`, `draft`)를 변경할 수 있어야 한다.

### 4.5 Recommendation & Comment
- FR-INT-001: 로그인 사용자는 사례 추천을 토글할 수 있어야 한다.
- FR-INT-002: 시스템은 추천 수 집계를 사례에 반영해야 한다.
- FR-INT-003: 임계치(10/50/100) 도달 시 작성자에게 알림을 생성해야 한다.
- FR-INT-004: 사용자는 댓글 목록을 조회할 수 있어야 한다.
- FR-INT-005: 로그인 사용자는 댓글을 작성할 수 있어야 한다.
- FR-INT-006: 댓글 작성자 또는 관리자는 댓글을 삭제할 수 있어야 한다.

### 4.6 Notifications
- FR-NOTI-001: 로그인 사용자는 본인 알림 목록(최대 50개)과 미확인 개수를 조회할 수 있어야 한다.
- FR-NOTI-002: 사용자는 개별 알림 읽음 처리할 수 있어야 한다.
- FR-NOTI-003: 사용자는 전체 알림 읽음 처리할 수 있어야 한다.

### 4.7 Attachments
- FR-ATT-001: 로그인 사용자는 첨부파일을 업로드할 수 있어야 한다.
- FR-ATT-002: 허용 확장자만 업로드할 수 있어야 하며 최대 500MB를 초과할 수 없어야 한다.
- FR-ATT-003: 첨부파일은 임시 업로드 후 사례와 연결할 수 있어야 한다.
- FR-ATT-004: 권한을 충족하는 사용자는 첨부파일 목록 조회/다운로드/삭제할 수 있어야 한다.

### 4.8 Reporting and Statistics
- FR-STAT-001: 관리자는 개요 통계를 조회할 수 있어야 한다.
- FR-STAT-002: 관리자는 부서/사용자 랭킹 통계를 조회할 수 있어야 한다.
- FR-STAT-003: 사용자는 주간 리포트를 조회할 수 있어야 한다.
- FR-STAT-004: 관리자는 통계를 Excel 파일로 내보낼 수 있어야 한다.

## 5. External Interface Requirements

### 5.1 User Interface
- 단일 페이지 UI(`frontend/index.html`)
- 주요 화면: 홈, 로그인 모달, 사례 상세 모달, 사례 등록 폼, 내 사례, 관리자 대시보드
- 관리자 탭: 대시보드, 사용자 관리, 사례 관리, 카테고리 관리, 통계

### 5.2 API Interface (Representative)
- 인증: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- 사례: `/api/cases`, `/api/cases/{cid}`, `/api/my-cases`, `/api/cases/{cid}/status`
- 카테고리: `/api/categories`, `/api/categories/{cid}`, `/api/categories/{cid}/toggle`
- 상호작용: `/api/cases/{cid}/recommend`, `/api/cases/{cid}/comments`
- 알림: `/api/notifications`, `/api/notifications/{nid}/read`, `/api/notifications/read-all`
- 통계: `/api/stats/overview`, `/api/stats/ranking`, `/api/stats/export/excel`, `/api/reports/weekly`
- 첨부: `/api/attachments/upload`, `/api/attachments/{aid}/download`, `/api/cases/{cid}/attachments`

### 5.3 Database Interface
- SQLite 주요 테이블: `users`, `categories`, `use_cases`, `recommendations`, `comments`, `tags`, `case_tags`, `notifications`, `attachments`
- 외부 DB(PMS): `MG_EMP_INFO`, `MG_DEPT_INFO` 조회 기반 인증/부서명 매핑

## 6. Non-functional Requirements

### 6.1 Security
- JWT 기반 API 인증 필수
- 관리자 권한 분리(`require_admin`)
- 로컬 비밀번호는 PBKDF2-SHA256 해시 저장
- 파일 타입/크기 제한 적용

### 6.2 Performance
- 사례 목록은 페이지네이션 제공(`page`, `page_size`)
- 검색/정렬 주요 조건 인덱스 존재(`idx_cases_*`)

### 6.3 Reliability & Availability
- 시작 시 DB 자동 초기화 및 기본 데이터 시드
- 시작 스크립트에서 프로세스/PID/로그 관리
- 시작 시 백업 스크립트 호출 로직 포함

### 6.4 Maintainability
- 모듈 분리(`main/auth/db/hrdb/models`)
- 통합 API 테스트 파일 존재(`tests/test_api.py`)
- 다만 프론트엔드가 단일 파일이므로 UI 변경 영향 범위가 넓다.

### 6.5 Portability
- Bash 기반 운영 스크립트에 의존
- Conda 환경 및 Python 3.13 전제

## 7. Data Requirements

### 7.1 Core Entities
- User: 사번/이름/부서/권한/삭제 여부
- UseCase: 제목/요약/본문/상태/조회/추천/댓글 카운트
- Category: 계층 구조(parent-child), 활성/삭제 상태
- Tag: 사용 빈도 기반 관리
- Attachment: 파일 메타데이터 및 사례 연결
- Notification: 사용자별 이벤트 알림

### 7.2 Data Integrity Rules
- 추천은 `(case_id, user_id)` 유니크
- 태그명 유니크
- 첨부파일은 사례 FK 연결 가능(ON DELETE CASCADE)
- 소프트 삭제 필드(`is_deleted`)를 다수 엔티티에서 사용

## 8. Deployment & Operations

### 8.1 Startup
- 기본 실행: `bash scripts/start.sh [port]`
- 내부 실행: `uvicorn backend.main:app --host 0.0.0.0 --port <port>`
- 로그 파일: `logs/aihub_<port>.log`

### 8.2 Configuration
- `.env` 사용(`python-dotenv`)
- 주요 환경변수:
  - `AIHUB_SECRET`
  - `AIHUB_DB`
  - `PMS_HOST`, `PMS_PORT`, `PMS_NAME`, `PMS_USER`, `PMS_PASSWORD`

### 8.3 Backup & Monitoring
- 시작 스크립트에서 백업 스크립트(`scripts/backup.sh`) 호출 시도
- 프로세스 상태는 PID 파일과 포트 점유 기준으로 확인

## 9. Risks, Assumptions, Open Issues

### 9.1 Risks
- 문서와 코드 불일치:
  - 일부 문서에서 언급된 스크립트/설정이 실제 트리와 다를 수 있음
  - 상태값 설명(`submitted` vs `approved`)이 모델/로직에서 혼재
- 보안 리스크:
  - 기본 시크릿 fallback(`dev-secret-change-me`) 존재
  - 운영 문서 내 민감정보 기재 가능성
- 업로드 경로가 절대경로(`/data/aihub/data/uploads/attachments`)에 고정되어 환경 의존성이 높음

### 9.2 Assumptions
- 운영 환경에서 PMS 접근 가능
- `AIHUB_SECRET` 및 PMS 계정정보는 안전하게 환경변수로 관리
- 관리자 계정 최소 1명 유지 정책 준수

### 9.3 Open Issues
- 프론트엔드 단일 파일 구조의 분리 필요성(유지보수성 개선)
- CORS 허용 원본 정책의 환경별 분리 필요성
- 테스트 범위 확대 필요(첨부파일/에러 케이스/권한 경계)
