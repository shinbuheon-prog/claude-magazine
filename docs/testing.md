# Testing

로컬 기본 실행:

```bash
pytest -v
```

커버리지 포함 실행:

```bash
pytest --cov=pipeline.editorial_lint --cov=pipeline.citations_store --cov-report=term-missing
```

현재 기준:

- `editorial_lint`는 article 11 체크와 card-news 4 체크를 pytest로 회귀 검증합니다.
- `citations_store`는 저장/로드와 citation 정규화 경로를 함께 검증합니다.
- 모든 테스트는 `tmp_path`와 monkeypatch를 사용해 `logs/`, `data/citations/`, 외부 HTTP/API 호출을 격리합니다.

권장 순서:

1. 변경 범위가 `pipeline/editorial_lint.py`, `pipeline/citations_store.py`에 걸리면 먼저 `pytest -v`
2. 배포 전에는 `pytest --cov=...`로 커버리지 확인
3. 대시보드/메트릭 변경이 있으면 `python scripts/export_metrics.py --format json`, `--format md`, `npm run build`까지 함께 확인
