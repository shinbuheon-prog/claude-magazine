# TASK_049 — editorial_lint pytest 스위트 정비

## 메타
- **status**: todo
- **prerequisites**: TASK_016 (editorial_lint 최초 구현), TASK_041 (card-news 모드), TASK_045 (citations-cross-check)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 가능 (article 모드 vs card-news 모드 테스트 분할)
- **Phase**: 6 (엔지니어링 성숙도 강화)

---

## 목적
[pipeline/editorial_lint.py](../pipeline/editorial_lint.py)는 article 모드 **11개 체크** + card-news 모드 **4개 체크** = **15 체크**로 성장. 현재 테스트는 **ad-hoc 스모크 스크립트**만 존재(`scripts/test_e2e.py`). 회귀 방지 위한 **pytest 기반 유닛 테스트 스위트** 부재.

### 해결할 리스크
- 체크 로직 수정 시 **다른 체크가 silent regression**되는 것 탐지 불가
- 신규 체크 추가 시 **기존 체크와 동일 입력 기대값이 바뀌어도** 알 수 없음
- CLAUDE.md 코딩 규칙(CLI `--dry-run` 옵션·request_id 로깅)을 **자동으로 강제할 수단 부재**

---

## 구현 명세

### Phase 0: pytest 인프라 구축 (15분)

#### 0.1 `requirements-dev.txt` (신규)
```
pytest>=8.0
pytest-cov>=5.0
```

#### 0.2 `pytest.ini` (신규)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -ra --strict-markers
markers =
    article: article 모드 체크
    card_news: card-news 모드 체크
    integration: 여러 체크 통합 (기사 전체 draft)
    slow: 네트워크 의존 (dry-run 권장)
```

#### 0.3 `tests/` 디렉터리 구조
```
tests/
├── __init__.py
├── conftest.py                        # 공통 fixture
├── fixtures/
│   ├── drafts/
│   │   ├── draft_pass.md              # 모든 체크 pass 목적
│   │   ├── draft_no_source_id.md      # source-id fail 유도
│   │   ├── draft_mojibake.md          # 보조
│   │   └── ...
│   ├── slides/
│   │   ├── slides_pass.json           # card-news pass
│   │   ├── slides_hook_missing.json   # hook 누락
│   │   └── slides_low_density.json    # density fail 유도
│   └── citations/
│       ├── art-pass.json              # citations 일치
│       └── art-mismatch.json          # citations 불일치
├── test_editorial_lint_article.py     # article 모드 11 체크
├── test_editorial_lint_card_news.py   # card-news 모드 4 체크
└── test_editorial_lint_integration.py # 혼합 시나리오
```

#### 0.4 `conftest.py` 공통 fixture
- `FIXTURES_DIR` 경로
- `mock_anthropic` fixture (실제 API 호출 차단)
- `tmp_citations_dir` fixture (data/citations를 tmp로 리다이렉트)
- `sample_draft` parametrized fixture (slug 기반)

---

### Phase 1: article 모드 테스트 (40분)

#### 1.1 파일: `tests/test_editorial_lint_article.py`
각 체크별 **최소 3 케이스** (pass / fail / edge):

| 체크 ID | 테스트 케이스 |
|---|---|
| `source-id` | 모든 문장에 source_id → pass / 절반 누락 → fail / 숫자만 있는 draft → edge |
| `citations-cross-check` | citations 일치 → pass / 파일 없음 → warn / 불일치 → warn |
| `translation-guard` | 인용 없음 → pass / 3줄 초과 인용 → fail |
| `title-body-match` | API 키 없음 → warn(skip) / mock 응답 match → pass |
| `quote-fidelity` | 인용 0건 → pass / 인용 mismatch → fail (mock) |
| `no-fabrication` | article_id 미지정 → warn / 수치/기업명 있음 → fabrication 판정 mock |
| `pii-check` | 주민번호 패턴 있음 → fail / 없음 → pass |
| `image-rights` | 이미지 없음 → pass / 라이선스 누락 이미지 → fail |
| `ai-disclosure` | 고지 존재 → pass / 누락 → fail |
| `correction-policy` | 3 요소 있음 → pass / 누락 → fail |
| `request-id-log` | logs/*.json 있음 → pass / 없음 → fail |

#### 1.2 helper
```python
def run_article_lint(draft_path, article_id=None, dry_run=True):
    """editorial_lint의 run_article_checks() 호출 래퍼."""
```

#### 1.3 격리 원칙
- 각 테스트는 **독립적 tmp_path** 사용
- `data/citations/`·`logs/`를 실제 디렉터리에 쓰지 않음

---

### Phase 2: card-news 모드 테스트 (25분)

#### 2.1 파일: `tests/test_editorial_lint_card_news.py`

| 체크 ID | 테스트 케이스 |
|---|---|
| `card-news-structure` | hook·cta 모두 존재 → pass / hook 누락 → fail / cta 누락 → fail |
| `card-news-density` | 슬라이드 텍스트 충분 → pass / 키워드만 나열 → fail |
| `source-fidelity` | 커버리지 ≥80% → pass / <80% → fail |
| `slide-count` | 원문 길이 대비 적정 → pass / 압축 과도 → fail |

#### 2.2 TASK_041 smoke JSON 재활용
`reports/task041_smoke_1.json` 등을 tests/fixtures/slides/에 복사해 레퍼런스로 활용.

---

### Phase 3: 통합 테스트 (15분)

#### 3.1 파일: `tests/test_editorial_lint_integration.py`
- `run_editorial_lint --mode article` 전체 실행 → items 개수 == 11
- `run_editorial_lint --mode card-news` 전체 실행 → items 개수 == 4
- `run_editorial_lint --only source-id citations-cross-check` → 선택 실행 2 체크만
- JSON 출력 스키마 validation (pydantic/dict 비교)
- exit code: `--strict` 모드에서 fail 시 1, 성공 시 0

#### 3.2 회귀 방지 스냅샷 (선택)
`tests/fixtures/drafts/draft_pass.md` → 기대 JSON 결과를 `tests/fixtures/snapshots/draft_pass.json`에 저장, 변경 시 diff 표시.

---

### Phase 4: CI 친화성 + 문서화 (15분)

#### 4.1 실행 문서
`docs/testing.md` (신규):
- 로컬 실행: `pytest -v`
- 커버리지: `pytest --cov=pipeline/editorial_lint --cov=pipeline/citations_store`
- 목표 커버리지: **editorial_lint 80%+, citations_store 70%+** (초기)

#### 4.2 CLAUDE.md 체크리스트 업데이트
"모든 파이프라인 수정 시 `pytest -v` 통과" 항목을 **권장**으로 추가 (강제 아님 — CI 미도입 상태).

#### 4.3 기존 ad-hoc 스크립트와 관계
- `scripts/test_e2e.py` — 유지 (E2E 스모크, pytest와 다른 층)
- `scripts/test_sdk_basic.py`, `test_sdk_brief.py` — 유지 (SDK 프로빙)
- 본 태스크는 **유닛 테스트 층 신설**, 기존 스크립트 대체 아님

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| pytest 도입으로 CI 비용 증가 | CI 자동화는 본 태스크 범위 외, 로컬 실행만 표준화 |
| fixture draft가 실제 발행 내용과 괴리 | `drafts/draft_20260421_*.md` 실 사례 기반으로 생성 |
| Mock Anthropic 응답이 실제 API 스키마와 어긋남 | CLAUDE.md 모델 배치 규칙 + claude_provider MockProvider 재활용 |
| citations_store 테스트가 실제 `data/citations/` 오염 | `conftest.py`에 `tmp_citations_dir` fixture로 격리 |
| 코드 커버리지 목표 미달 | 초기 목표 80%/70% — 점진 상승, 초기부터 100% 강요 안 함 |
| 한글 fixture 인코딩 문제 (Windows cp949) | 모든 fixture 파일 `encoding="utf-8"` 명시, pytest.ini에 `PYTHONIOENCODING=utf-8` 권장 주석 |

---

## 완료 조건 (Definition of Done)
- [ ] `requirements-dev.txt` + `pytest.ini` 신설, `pytest -v` 로컬 통과
- [ ] `tests/` 디렉터리 구조 완성 (fixtures 포함)
- [ ] article 모드 11 체크 각각 최소 3 케이스 (pass/fail/edge) 테스트
- [ ] card-news 모드 4 체크 각각 최소 2 케이스 테스트
- [ ] 통합 테스트로 `--mode`·`--only`·`--strict` 동작 검증
- [ ] `pytest --cov=pipeline/editorial_lint` 커버리지 **≥80%**
- [ ] `pytest --cov=pipeline/citations_store` 커버리지 **≥70%**
- [ ] `docs/testing.md` 작성
- [ ] 실제 API 호출 없음 (MockProvider·tmp_path 격리 확인)
- [ ] 기존 `scripts/test_e2e.py` 등 회귀 없음
- [ ] mojibake/한글 인코딩 회귀 없음

---

## 산출물
- `requirements-dev.txt` (신규)
- `pytest.ini` (신규)
- `tests/conftest.py` (신규)
- `tests/fixtures/` (신규, drafts·slides·citations)
- `tests/test_editorial_lint_article.py` (신규)
- `tests/test_editorial_lint_card_news.py` (신규)
- `tests/test_editorial_lint_integration.py` (신규)
- `docs/testing.md` (신규)
- `CLAUDE.md` (체크리스트 권장 항목 추가)

---

## 후속 태스크 후보
- **TASK_050 후보**: fact_checker pytest 스위트 (Citations·cache mock 체계)
- **TASK_051 후보**: GitHub Actions CI 도입 (pytest + npm run build)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_049 implemented
python codex_workflow.py update TASK_049 merged
```
