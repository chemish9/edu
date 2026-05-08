# Scripts

AIHub 서버 관리 스크립트 모음

## 서버 관리

- `start.sh` - 서버 시작
- `stop.sh` - 서버 중지
- `status.sh` - 서버 상태 확인

## 배포

- `deploy.sh` - 자동 배포 스크립트
- `download_packages.sh` - 오프라인 패키지 다운로드

## Windows

- `start.bat` - Windows 서버 시작
- `deploy.bat` - Windows 배포 스크립트

## 사용법

```bash
# 서버 시작
./start.sh 8000

# 서버 상태 확인
./status.sh 8000

# 서버 중지
./stop.sh 8000

# 배포
./deploy.sh

# 패키지 다운로드
./download_packages.sh
```
