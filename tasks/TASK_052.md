# TASK_052 — GitHub Actions CI 확장 (pytest + npm build + check_env + playbook 검증)

## 메타
- **status**: todo
- **prerequisites**: TASK_049 (pytest 스위트), TASK_050 (publish_monthly UX), TASK_051 (failure_playbook)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 가능 (Phase 1-2 job 정의 vs Phase 3-4 문서화)
- **Phase**: 7 (발행 신뢰성·배포 자동화)

---

## 목적
[.github/workflows/ci.yml](../.github/workflows/ci.yml)이 이미 존재하지만 **최소 범위**:
- ruff lint
- codex_workflow.py list
- source_registry 스모크
- brief_generator·fact_checker import 확인

**부족**:
- TASK_049 pytest 스위트 미실행
- `web/npm run build` 미실행 (React 회귀 탐지 불가)
- check_env.py --strict (mock mode) 미실행
- failure_playbook.yml 스키마 검증 (TASK_051) 미포함
- editorial_lint·card-news-builder 스모크 미포함

본 태스크는 **기존 ci.yml을 확장**해 매거진 전체 파이프라인의 자동 회귀 검증 체계 완성.

### 무료 범위 확인
- **GitHub Actions**: public 레포 무제한, private 레포 월 2,000분 (무료 계정)
- 본 매거진 레포가 private이면 월 2,000분 한도 내 동작 확인 필요

---

## 구현 명세

### Phase 1: 기존 CI job 확장 (30분)

#### 1.1 `.github/workflows/ci.yml` 업데이트
기존 `lint-and-smoke` job을 **분할**하여 병렬 실행:

```yaml
jobs:
  python-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install ruff
      - run: ruff check pipeline/ scripts/ codex_workflow.py

  python-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: python codex_workflow.py list
      - run: python pipeline/source_registry.py
        env:
          SOURCE_DB_PATH: /tmp/test_registry.db
      - run: python -c "from pipeline.brief_generator import generate_brief; from pipeline.fact_checker import run_factcheck; print('OK')"

  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest -v --cov=pipeline/editorial_lint --cov=pipeline/citations_store
      - run: pytest --cov-report=xml:coverage.xml tests/
      - uses: actions/upload-artifact@v4
        with:
          name: pytest-coverage
          path: coverage.xml

  web-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: cd web && npm ci
      - run: cd web && npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: web-dist
          path: web/dist
          retention-days: 3

  env-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: python scripts/check_env.py --dry-run
        # --dry-run으로 네트워크 호출 없이 env 구조만 검증
        # --strict는 실제 API 키 필요 → CI에서 mock만 수행

  spec-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install pyyaml
      - run: |
          python -c "
          import yaml, pathlib, sys
          files = [
              'spec/article_standards.yml',
              'spec/card_news_standards.yml',
              'spec/failure_playbook.yml',   # TASK_051
              'config/feeds.yml',
          ]
          for f in files:
              if pathlib.Path(f).exists():
                  yaml.safe_load(open(f, encoding='utf-8'))
                  print(f'OK: {f}')
              else:
                  print(f'SKIP: {f} (not yet implemented)')
          "

  mojibake-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: |
          python -c "
          import pathlib
          bad = []
          for p in pathlib.Path('.').rglob('*'):
              if any(x in p.parts for x in ('node_modules', '.git', '__pycache__', 'dist')):
                  continue
              if p.suffix not in {'.md', '.py', '.yml', '.yaml', '.json', '.txt', '.jsx', '.js'}:
                  continue
              if not p.is_file():
                  continue
              data = p.read_bytes()
              txt = data.decode('utf-8', errors='replace')
              for marker in ['�', 'ê°€', 'ì¤']:
                  if marker in txt:
                      bad.append((str(p), marker)); break
          if bad:
              print('MOJIBAKE FOUND:', bad[:10])
              raise SystemExit(1)
          print('mojibake scan: CLEAN')
          "
```

#### 1.2 job 병렬화
- 6 job 동시 실행 → 전체 CI 시간 ~3~5분 이내 예상 (기존 대비 증가하지만 허용 범위)

### Phase 2: 무료 tier 사용량 모니터링 (10분)

#### 2.1 `docs/ci_usage.md` (신규)
- private 레포일 때 월 2,000분 무료 한도 설명
- 각 job 평균 소요 시간 기록
- 한도 임박 시 조치: job 통합·cache 최적화·main 브랜치만 실행 제한

#### 2.2 CI 비용 가드
- `paths-ignore`로 docs-only 변경 시 일부 job skip
- PR 이벤트는 실행, push 이벤트는 main/develop만 실행

### Phase 3: main 브랜치 보호 안내 (20분)

GitHub 레포 Settings에서 수동 설정 필요 — 코드 범위 외.
`docs/ci_usage.md`에 다음 단계 문서화:

1. **Settings → Branches → Branch protection rule** for `main`
   - Require a pull request before merging ✅
   - Require status checks to pass:
     - `python-lint`, `python-smoke`, `python-tests`, `web-build`, `spec-lint`, `mojibake-scan`
   - Require branches to be up to date ✅
   - Include administrators (선택)

2. `develop`은 보호 없이 유지 (활발한 작업 브랜치)

3. 예외: 긴급 수정 시 admin override 허용

### Phase 4: 기존 CI와 호환성 (15분)

#### 4.1 기존 `lint-and-smoke` job 제거 여부
- **제거 권장** — 신규 분할 job이 기능 대체
- 기존 ci.yml 주석으로 이전 버전 기록

#### 4.2 `.github/workflows/codex_sync.yml`은 **건드리지 않음**
- 본 태스크 범위 외
- 기존 codex sync 흐름 보존

#### 4.3 PR 템플릿 업데이트 (`.github/PULL_REQUEST_TEMPLATE.md`)
"CI 체크 통과 확인" 항목 추가.

### Phase 5: 스모크 (10분)
- PR을 생성해 전 job 동작 확인 (실제 테스트 PR)
- 일부 job 의도적 실패 주입 → 감지 확인
- cache hit 동작 확인 (2회 실행 시 속도 비교)

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| 무료 tier 월 2,000분 초과 (private 레포) | `paths-ignore`로 docs-only 변경 skip + `docs/ci_usage.md` 모니터링 |
| `requirements-dev.txt` 부재 (TASK_049 미완) | TASK_049 선행 또는 본 태스크에서 최소 pytest·coverage만 설치 |
| check_env.py가 --dry-run 모드로 충분히 의미 있는 검증을 제공하지 못함 | `docs/ci_usage.md`에 한계 명시, 실제 API 검증은 편집자 로컬에서 |
| 기존 CI 깨짐 (신규 job이 기존 기능 누락) | Phase 4.1에서 기능 매핑 체크리스트 확인 후 제거 |
| main 브랜치 보호 규칙 설정 누락 | Phase 3 안내문 + PR 머지 시 사용자 확인 요청 |
| CI 실패 시 Codex가 자동 머지하지 못함 | 의도된 동작 — 사람 개입 지점 유지 |

---

## 완료 조건 (Definition of Done)
- [ ] `.github/workflows/ci.yml`이 6 job으로 분할되어 병렬 실행
- [ ] python-tests job이 `pytest --cov=pipeline/editorial_lint --cov=pipeline/citations_store` 실행
- [ ] web-build job이 `npm ci + npm run build` 실행
- [ ] env-check job이 `check_env.py --dry-run` 실행
- [ ] spec-lint job이 yml 스키마 검증 실행
- [ ] mojibake-scan job이 UTF-8 회귀 감지
- [ ] `docs/ci_usage.md`에 무료 tier 한도 + 브랜치 보호 규칙 설정 가이드
- [ ] 기존 `lint-and-smoke` job 정리 (제거 또는 대체 확인)
- [ ] `codex_sync.yml` 미수정 (기존 흐름 보존)
- [ ] 테스트 PR에서 전 job 통과 확인

---

## 산출물
- `.github/workflows/ci.yml` (확장)
- `.github/PULL_REQUEST_TEMPLATE.md` (체크리스트 보강)
- `docs/ci_usage.md` (신규)

---

## 후속 태스크 후보
- **TASK_056 후보**: Ghost staging 자동 배포 (develop 브랜치 머지 시 staging으로 deploy)
- **TASK_057 후보**: CodeQL security scan 도입 (GitHub Advanced Security 무료 public 레포)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_052 implemented
python codex_workflow.py update TASK_052 merged
```
