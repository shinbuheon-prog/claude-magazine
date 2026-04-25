# TASK_054 — 반복 실패 감지 + weekly_improvement 우선순위 큐 연계

## 메타
- **status**: todo
- **prerequisites**: TASK_051 (failure_playbook + reports/failure_*.md), TASK_053 (failure_collector 운영 신호)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 불필요
- **Phase**: 8 (자율성 강화 — 폐쇄 루프 강화)

---

## 목적
TASK_051이 stage 실패 시 `reports/failure_<month>_<stage>.md`를 자동 생성. 그러나 **같은 failure class가 반복 발생해도 알림·우선순위화가 없음**. TASK_051 문서가 이미 약속한 후속:

> "3회 이상 같은 class 실패 시 weekly_improvement 루프(TASK_027) 검토"

본 태스크는 이 약속을 **자동 감지 + 우선순위 큐**로 구현. 단, **즉시 실행은 안전 원칙상 금지** — weekly_improvement는 기존 스케줄대로 실행되되, 큐에 쌓인 우선순위 신호를 읽고 reports/improvement_*.md에 강조 표시.

### 해결하는 운영 상황
- "pdf_compile이 4월에 3번 같은 puppeteer_timeout으로 실패했다" → 편집자가 즉시 인지
- "ghost_publish jwt_401이 누적 6회" → 인증 키 만료 패턴 식별
- "quality_gate article_status_not_approved 7회" → 편집 워크플로우 병목

---

## 설계 원칙 (안전장치)

### 의도된 비-자동성
| 단계 | 자동 vs 수동 | 이유 |
|---|---|---|
| 실패 감지 | 자동 | publish_monthly 실패 hook 후속 |
| 반복 횟수 카운트 | 자동 | 결정론적 집계 |
| 알림·로그 기록 | 자동 | 편집자 인지 도움 |
| **우선순위 큐 마커 작성** | 자동 | 다음 weekly_improvement에 신호 전달 |
| **weekly_improvement 즉시 실행** | ❌ 차단 | 비용·false positive 위험 — 스케줄 유지 |
| 코드·SOP 변경 | ❌ 차단 | 편집자 승인 필수 (TASK_027 원칙 승계) |

`--trigger-improvement` 플래그로 **수동 즉시 실행은 허용** (운영자 명시 의지).

---

## 구현 명세

### Phase 1: failure_repeat_detector 모듈 신설 (35분)

#### 1.1 `pipeline/failure_repeat_detector.py` (신규)
```python
"""Detect repeated failure classes across reports/failure_*.md files."""

DEFAULT_WINDOW_DAYS = 14
DEFAULT_THRESHOLD = 3
QUEUE_DIR = ROOT / "reports" / "auto_trigger_queue"

def scan_failures(window_days: int = 14) -> list[dict]:
    """reports/failure_*.md 파일을 스캔해 (month, stage, failure_class, timestamp) 리스트 반환."""

def count_by_class(failures: list[dict]) -> dict[str, list[dict]]:
    """failure_class를 키로, 해당 클래스의 최근 발생 리스트 반환."""

def detect_repeats(
    failures: list[dict],
    threshold: int = 3,
    window_days: int = 14,
) -> list[dict]:
    """threshold 이상 반복된 class만 반환.
    각 entry: {class, count, occurrences[], stages[], first_seen, last_seen}"""

def write_queue_marker(repeats: list[dict]) -> Path | None:
    """반복 감지 시 reports/auto_trigger_queue/<date>.json 작성.
    weekly_improvement가 다음 실행에서 읽음.
    None 반환 = 마커 작성 안 함 (감지 결과 0건)."""

def acknowledge_marker(marker_path: Path) -> None:
    """편집자가 인지·해결 후 마커를 archived/로 이동 (수동 또는 weekly_improvement 처리 후)."""
```

#### 1.2 큐 마커 스키마
`reports/auto_trigger_queue/2026-04-25.json`:
```json
{
  "created_at": "2026-04-25T13:30:00Z",
  "window_days": 14,
  "threshold": 3,
  "detected_at_run": "publish_monthly:2026-05",
  "repeats": [
    {
      "class": "puppeteer_timeout",
      "stage": "pdf_compile",
      "count": 4,
      "first_seen": "2026-04-12T...",
      "last_seen": "2026-04-25T...",
      "occurrences": [
        {"month": "2026-04", "ts": "2026-04-12T...", "report_path": "reports/failure_2026-04_pdf_compile.md"},
        ...
      ]
    }
  ],
  "status": "queued"
}
```

#### 1.3 토큰 마스킹
- 큐 마커가 reports/failure_*.md 내용 일부를 인용할 경우 TASK_051의 `_redact_secrets()` 재사용 (sk-ant-*·figd_*·hf_*·kid:secret 등)

---

### Phase 2: publish_monthly 통합 (15분)

#### 2.1 failure hook 후속에 detector 호출
[scripts/publish_monthly.py](../scripts/publish_monthly.py) 의 stage 실패 처리 로직(`generate_failure_report` 호출 후) 다음에:

```python
# 기존
playbook_path = generate_failure_report(month, stage, error_output, _state_path(month))
print(f"Recovery guide: {playbook_path}")

# 신규
from pipeline.failure_repeat_detector import scan_failures, detect_repeats, write_queue_marker
failures = scan_failures(window_days=14)
repeats = detect_repeats(failures, threshold=3, window_days=14)
if repeats:
    marker = write_queue_marker(repeats)
    print(f"⚠️  반복 실패 {len(repeats)}건 감지 — weekly_improvement 큐 마커: {marker}")
```

- 기존 출력·return code 변경 없음
- 큐 마커 작성 실패해도 publish_monthly 자체는 영향 없음 (try/except 가드)

---

### Phase 3: weekly_improvement 큐 소비 (20분)

#### 3.1 `scripts/weekly_improvement.py` 확장
- 시작 시 `reports/auto_trigger_queue/*.json` 미처리(`status=queued`) 마커 모두 수집
- `reports/improvement_<date>.md` 헤드에 **"🔴 우선 처리 요청 (반복 실패)"** 섹션 신규 렌더
- 처리 완료 시 마커 `status=processed`로 갱신 + `archived/` 하위로 이동 (TASK_054 design 결정)

#### 3.2 sop_updater 프롬프트 힌트
- 큐 마커 존재 시 sop_updater system prompt에 "다음 반복 실패 클래스를 patterns 우선순위로 분석"이라는 지시 주입
- 기존 patterns/updates/checklist 스키마 유지 — 별도 카테고리 없음

---

### Phase 4: CLI + 수동 트리거 (15분)

#### 4.1 `pipeline/failure_repeat_detector.py` CLI
```bash
# 단독 스캔 (조회 전용, 기본)
python pipeline/failure_repeat_detector.py --window 14 --threshold 3

# JSON 출력
python pipeline/failure_repeat_detector.py --json

# 수동으로 weekly_improvement 즉시 실행
python pipeline/failure_repeat_detector.py --trigger-improvement
```

#### 4.2 `--trigger-improvement` 동작
- 큐 마커 작성 → `subprocess.run([sys.executable, "scripts/weekly_improvement.py", ...])`
- confirmation prompt 기본 활성, `--yes`로만 스킵
- 비용 안내 출력: "이 명령은 Opus 호출을 트리거합니다. 진행 (y/N)?"

---

### Phase 5: pytest 확장 (15분)

#### 5.1 `tests/test_failure_repeat_detector.py` (신규)
- scan_failures: mock failure_*.md 3건 → entries 3건 반환
- count_by_class: 클래스별 분류 검증
- detect_repeats: threshold 3, 윈도우 14일 기준 반복 추출 (포함 케이스 + 제외 케이스)
- write_queue_marker: 작성·기존 마커 idempotency
- 토큰 마스킹: 인용 영역에서 sk-ant-* 패턴 제거 검증
- CLI smoke (기본 모드 + --json)

목표 커버리지: failure_repeat_detector ≥80%

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| False positive — 같은 class 3회지만 근본 원인 다름 | weekly_improvement가 sop_updater Opus 분석으로 수동 검토. 자동 코드 변경 금지 (TASK_027 원칙 유지) |
| 비용 폭발 — `--trigger-improvement` 남용 | confirmation prompt 기본 활성 + Slack 알림 (선택) |
| 윈도우·threshold 부적절 (14일/3회) | env 변수로 조정 가능: `CLAUDE_MAGAZINE_FAILURE_WINDOW_DAYS`·`CLAUDE_MAGAZINE_FAILURE_THRESHOLD` |
| 큐 마커 누적 (해결 후에도 잔류) | 처리 완료 시 archived/로 이동 + 30일 후 자동 삭제 정책 (선택) |
| publish_monthly 실패 hook의 추가 부담 | try/except 가드로 detector 실패가 publish 자체를 막지 않음 |
| 토큰 노출 | TASK_051 `_redact_secrets()` 패턴 재사용 |
| 기존 reports/failure_*.md 누락 (gitignore) | reports/는 commit 대상 — 누락 시 빈 리스트 반환 |

---

## 무료 발행 원칙 정합성
- 본 태스크는 **로컬 파일 스캔 + 마커 작성**만 — 외부 API 호출 없음
- weekly_improvement 즉시 실행은 **수동 트리거 + confirmation 필수** — 우발적 비용 발생 차단
- env 변수 기본값은 보수적 (window 14일, threshold 3회) — 빈번한 false positive 방지

---

## 완료 조건 (Definition of Done)
- [ ] `pipeline/failure_repeat_detector.py` 신규 — scan/count/detect/write_queue_marker/acknowledge 5 함수
- [ ] `scripts/publish_monthly.py` failure hook에 detector 통합 (기존 출력 회귀 없음)
- [ ] `scripts/weekly_improvement.py` 큐 마커 소비 + 우선 처리 섹션 렌더
- [ ] CLI 모드 3종 (조회/JSON/--trigger-improvement) + confirmation prompt
- [ ] env 변수 가드 (`CLAUDE_MAGAZINE_FAILURE_WINDOW_DAYS`·`_THRESHOLD`)
- [ ] 토큰 마스킹 적용
- [ ] `tests/test_failure_repeat_detector.py` 신규 — failure_repeat_detector ≥80%
- [ ] 전체 pytest 회귀 없음 (기존 43 + 신규 6~8 ≈ 49+)
- [ ] mojibake/한국어 인코딩 회귀 없음
- [ ] CLAUDE.md 코딩 규칙 준수 (UTF-8 Windows·dry-run·argparse·request_id 로깅)

---

## 산출물
- `pipeline/failure_repeat_detector.py` (신규)
- `scripts/publish_monthly.py` (failure hook 확장)
- `scripts/weekly_improvement.py` (큐 마커 소비)
- `tests/test_failure_repeat_detector.py` (신규)
- `reports/auto_trigger_queue/` (런타임 디렉터리, gitignore 또는 archived/ 분리)
- `reports/task054_smoke_<date>.md` — 스모크 결과

---

## 후속 태스크 후보
- **TASK_055**: editor_corrections 기반 editorial_lint heuristic 자동 학습 (안전장치 포함)
- **TASK_056**: failure_repeat_detector + Slack 실시간 알림 (운영 임계 초과 시)
- **TASK_057**: weekly_improvement 큐 처리 자동화 — `--auto-trigger` 모드 (운영자 명시 옵트인 후)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_054 implemented
python codex_workflow.py update TASK_054 merged
```
