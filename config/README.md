# Configuration

AIHub 설정 파일

## 파일 목록

- `requirements.txt` - 온라인 설치용 Python 의존성
- `packages.txt` - 오프라인 설치용 전체 패키지 목록

## 사용법

### 온라인 설치

```bash
pip install -r config/requirements.txt
```

### 오프라인 설치

```bash
pip install --no-index --find-links=../packages -r config/packages.txt
```

## 패키지 관리

새 패키지를 추가하려면:

1. `requirements.txt` 에 핵심 패키지 추가
2. `packages.txt` 에 의존성 포함 패키지 추가
3. `scripts/download_packages.sh` 로 wheel 파일 재다운로드
