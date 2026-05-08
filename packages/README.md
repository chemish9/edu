# Packages

AIHub 오프라인 설치를 위한 wheel 파일

## 설명

이 디렉터리에는 Python 3.13 + Linux x86_64 용 wheel 파일이 포함되어 있습니다.
폐쇄망 환경에서 AIHub 를 설치할 때 사용합니다.

## 설치 방법

```bash
pip install --no-index --find-links=packages -r config/packages.txt
```

## 패키지 업데이트

인터넷 연결 가능한 서버에서:

```bash
./scripts/download_packages.sh
```

## 파일 목록

```bash
ls -lh *.whl
```
