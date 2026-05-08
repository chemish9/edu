# Tools

AIHub 유틸리티 스크립트

## 도구 목록

- `test_pms.py` - PMS(MSSQL) 연결 테스트
- `analyze_hrdb.py` - HRDB 데이터 분석
- `migrate_to_mssql.py` - MSSQL 마이그레이션 도구

## 사용법

### PMS 연결 테스트

```bash
conda activate aihub
python tools/test_pms.py
```

### HRDB 데이터 분석

```bash
conda activate aihub
python tools/analyze_hrdb.py
```

### MSSQL 마이그레이션

```bash
conda activate aihub
python tools/migrate_to_mssql.py
```

## 주의사항

- 각 스크립트는 aihub Conda 환경에서 실행해야 합니다
- 데이터베이스 연결 정보가 올바르게 설정되어 있는지 확인하세요
