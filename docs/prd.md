# 사내 AI 활용사례 수집 플랫폼 — PRD (Product Requirements Document)

> **현재 구현 상태 기준 문서입니다.**
> 이 문서는 실제 구현된 시스템의 기능 명세, 운영 환경, 확장 방안을 기술합니다.

---

## 1. 서비스 개요

| 항목 | 내용 |
|------|------|
| 서비스명 | AI Lab (사내 AI 활용사례 수집 플랫폼) |
| 목적 | 임직원의 AI 도구 활용 경험을 수집·공유하여 조직 전체의 AI 활용 역량을 향상 |
| 대상 | 전 임직원 (로그인 후 즉시 등록 및 열람 가능) |
| 기술 스택 | Python 3.13 / FastAPI / SQLite / 단일 HTML SPA |
| 운영 환경 | 폐쇄망 Linux 서버 (Air-Gapped) |

---

## 2. 운영 환경 명세

### 2-1. 서버 환경

| 항목 | 사양 |
|------|------|
| 운영체제 | Linux (x86_64) |
| 네트워크 | 폐쇄망 — 외부 인터넷 연결 불가 |
| Python | 3.13.9 |
| Conda | 25.11.1 (`/opt/anaconda3`) |
| DB | SQLite (단일 파일, `aihub.db`) |

### 2-2. 의존 패키지

**`target_packages/`에 포함된 오프라인 설치 패키지**

| 패키지 | 버전 | 역할 |
|--------|------|------|
| fastapi | 0.135.3 | 웹 프레임워크 |
| uvicorn | 0.44.0 | ASGI 서버 |
| starlette | 1.0.0 | FastAPI 내부 의존 |
| pydantic | 2.13.0 | 데이터 검증 |
| pydantic_core | 2.46.0 | pydantic 코어 (Linux x86_64 / cp313 전용) |
| annotated_types | 0.7.0 | pydantic 의존 |
| annotated_doc | 0.0.4 | fastapi 의존 |
| typing_extensions | 4.15.0 | 공통 의존 |
| typing_inspection | 0.4.2 | fastapi 의존 |
| anyio | 4.13.0 | starlette 의존 |
| idna | 3.11 | anyio 의존 |
| h11 | 0.16.0 | uvicorn HTTP/1.1 파서 |
| click | 8.3.2 | uvicorn CLI 의존 |
| colorama | 0.4.6 | click 터미널 색상 |

**conda 또는 사전 설치된 패키지**

| 패키지 | 버전 | 역할 |
|--------|------|------|
| PyJWT | 2.10.1 | JWT 토큰 생성·검증 |
| pydantic | 2.12.4 | (whl로 2.13.0 대체) |
| httpx | 0.28.1 | 테스트 HTTP 클라이언트 |
| pytest | 8.4.2 | 테스트 프레임워크 |
| bcrypt | 5.0.0 | (auth.py 미사용, conda 기설치) |

---

## 3. 시스템 아키텍처

```
Browser
  │  HTTP/REST
  ▼
FastAPI (backend/main.py)
  ├── 인증 레이어  (auth.py)  — JWT Bearer 토큰, PBKDF2 비밀번호 해시
  ├── 라우트 레이어           — 사례·추천·댓글·태그·통계·알림·리포트
  ├── 모델 레이어  (models.py) — Pydantic v2 요청/응답 스키마
  └── DB 레이어   (db.py)     — SQLite, contextmanager 기반 연결 관리

SQLite (aihub.db)
  ├── users
  ├── use_cases
  ├── categories
  ├── recommendations
  ├── comments
  ├── tags / case_tags
  └── notifications

Frontend (frontend/index.html)
  └── 단일 파일 SPA — FastAPI의 정적 파일 마운트로 서빙
```

---

## 4. 기능 명세

### 4-1. 인증

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 로그인 | `POST /api/auth/login` | 사번 + 비밀번호 → JWT 토큰 반환 |
| 회원가입 | `POST /api/auth/register` | 사번·이름·비밀번호·부서·직급 |
| 내 정보 | `GET /api/auth/me` | 토큰 기반 현재 사용자 정보 |

- 인증 방식: JWT Bearer 토큰 (유효기간 7일)
- 비밀번호 해시: `hashlib.pbkdf2_hmac` (SHA-256, 100,000회 반복, 정적 salt)
- 권한 구분: 일반 사용자 / 관리자 (`is_admin` 플래그)

### 4-2. 사례 (use_cases)

| 기능 | 엔드포인트 | 권한 | 설명 |
|------|-----------|------|------|
| 목록 조회 | `GET /api/cases` | 전체 | 페이지네이션, 필터, 정렬 |
| 상세 조회 | `GET /api/cases/{id}` | 전체 | 조회수 자동 증가 |
| 등록 | `POST /api/cases` | 로그인 | **즉시 `approved` 상태로 공개** |
| 수정 | `PUT /api/cases/{id}` | 본인·관리자 | `draft` 또는 `approved` 상태만 |
| 삭제 | `DELETE /api/cases/{id}` | 본인·관리자 | 소프트 삭제 |

**사례 상태**

| 상태 | 설명 |
|------|------|
| `draft` | 임시저장 — 본인만 열람 가능 |
| `approved` | 공개 — 전체 목록에 노출 (등록 즉시 부여) |

> 구 버전의 `submitted`(제출 대기) 및 `rejected`(반려) 상태는 제거되었습니다.
> 승인 절차 없이 로그인한 모든 사용자가 즉시 사례를 공개할 수 있습니다.

**목록 조회 파라미터**

| 파라미터 | 설명 |
|----------|------|
| `status` | `approved` (기본값) / `draft` / `all` |
| `keyword` | 제목·요약·내용 LIKE 검색 |
| `category_id` | 대분류 선택 시 소분류 포함 자동 필터 |
| `tag` | 태그명 일치 필터 |
| `ai_tool` | AI 도구명 필터 |
| `department` | 부서명 필터 |
| `sort` | `popular` / `latest` / `views` / `trending` |
| `page` / `page_size` | 페이지네이션 (기본 1 / 12) |

**인기순 정렬 공식**
```
score = (추천수 × 3) + (조회수 × 0.1) + (댓글수 × 2)
```

### 4-3. 추천

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 추천 토글 | `POST /api/cases/{id}/recommend` | 추천/취소 전환, 사용자당 1회 |
| 추천 여부 | `GET /api/cases/{id}/recommend/status` | 현재 사용자의 추천 여부 |

- 10 / 50 / 100회 달성 시 작성자에게 `milestone` 알림 자동 발송

### 4-4. 댓글

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 목록 | `GET /api/cases/{id}/comments` | 시간순 정렬 |
| 등록 | `POST /api/cases/{id}/comments` | 로그인 필요, 작성자에게 `comment` 알림 |
| 삭제 | `DELETE /api/comments/{id}` | 본인·관리자만 소프트 삭제 |

### 4-5. 태그 / 카테고리

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 카테고리 트리 | `GET /api/categories` | 대/소분류 2단계 트리 |
| 카테고리 추가 | `POST /api/categories` | 관리자 전용 |
| 카테고리 삭제 | `DELETE /api/categories/{id}` | 관리자 전용 |
| 태그 목록 | `GET /api/tags` | 사용빈도 포함 |
| 인기 태그 | `GET /api/tags/popular` | Top 20 |

**초기 카테고리 (6개 대분류)**

| 대분류 | 소분류 |
|--------|--------|
| 업무자동화 | 문서자동화, 이메일처리, 일정관리 |
| 데이터분석 | 리포트생성, 시각화, 예측모델 |
| 고객서비스 | 챗봇, 문의분류, 응대지원 |
| 문서작성 | 기획서, 보고서, 번역 |
| 코딩 | 코드리뷰, 테스트작성, 디버깅 |
| 기타 | — |

### 4-6. 관리자 기능

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 전체 통계 | `GET /api/stats/overview` | 총 사례수, 임시저장수, 추천수, 월별 추이, 부서별 현황 |
| 랭킹 | `GET /api/stats/ranking` | 부서별·개인별 등록수·추천수 |

### 4-7. 알림

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 목록 | `GET /api/notifications` | 최근 50건, 미읽음 카운트 |
| 읽음 처리 | `PATCH /api/notifications/{id}/read` | 단건 |
| 전체 읽음 | `POST /api/notifications/read-all` | 전체 |

**알림 발생 조건**

| 타입 | 발생 시점 |
|------|-----------|
| `comment` | 내 사례에 댓글 등록 시 |
| `milestone` | 내 사례 추천 10 / 50 / 100회 달성 시 |

### 4-8. 주간 리포트

| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 주간 리포트 | `GET /api/reports/weekly` | 최근 7일 신규 건수, TOP 3 사례, 활발한 부서, 누적 통계 |

---

## 5. 데이터베이스 스키마

### 핵심 테이블

```
users           — 사용자 (사번·이름·부서·직급·이메일·비밀번호해시·관리자여부)
use_cases       — 사례 (제목·요약·내용·AI도구·상태·조회수·추천수·댓글수)
categories      — 카테고리 (parent_id로 2단계 트리 구성)
recommendations — 추천 이력 (case_id + user_id UNIQUE)
comments        — 댓글
tags            — 태그 (usage_count 캐시)
case_tags       — 사례-태그 다대다 관계
notifications   — 알림 (type·message·is_read)
```

### 설계 원칙

- 모든 테이블 `created_at`, `updated_at` 자동 관리
- 소프트 삭제: `is_deleted = 1` + `deleted_at` 기록
- 추천수·조회수·댓글수는 `use_cases`에 캐시, `recommendations`가 원본
- `use_cases(status, is_deleted)`, `use_cases(recommend_count DESC)` 인덱스

---

## 6. API 응답 형식

```json
// 성공
{ "success": true,  "data": { ... }, "message": "ok" }

// 실패
{ "success": false, "data": null,   "message": "에러 메시지" }
```

---

## 7. 보안

- JWT 시크릿 키는 환경변수 `AIHUB_SECRET`으로 관리 (기본값은 개발용, **운영 배포 전 반드시 변경**)
- CORS: 현재 전체 허용 (`allow_origins=["*"]`) — 운영 시 서버 IP로 제한 권장
- 모든 쓰기 API는 JWT 인증 필수
- 관리자 전용 API는 `is_admin` 플래그 검사

---

## 8. 실행 방법 요약

```bash
# 1. 가상환경 생성 및 활성화
conda create -n aihub python=3.13 -y
conda activate aihub

# 2. 오프라인 패키지 설치
cd ~/aihub
pip install --no-index --find-links=target_packages -r requirements.txt

# 3. 데모 데이터 삽입 (최초 1회)
python -m backend.seed

# 4. 서버 실행
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 9. 향후 확장 방안

| 항목 | 내용 |
|------|------|
| DB 교체 | 운영 규모 확대 시 MySQL 8.0 으로 전환 (스키마 구조 동일) |
| 인증 연동 | 사내 SSO(LDAP/AD) 연동으로 별도 회원가입 불필요 |
| 파일 첨부 | `attachments` 테이블 스키마 추가 및 로컬 스토리지 연동 |
| 역방향 프록시 | nginx 앞단 배치 + HTTPS(내부 CA 인증서) 적용 |
| 컨테이너화 | Docker + 폐쇄망 레지스트리 기반 배포 자동화 |
| 전문 검색 | SQLite FTS5 확장 또는 내부 Elasticsearch 연동 |
