# TASK_050 — publish_monthly UX 보강 (status·reset-stage·from-stage + 텔레메트리)

## 메타
- **status**: todo
- **prerequisites**: TASK_037 (publish_monthly 원스톱)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 7 (발행 신뢰성·배포 자동화)

---

## 목적
[scripts/publish_monthly.py](../scripts/publish_monthly.py)는 체크포인트 + stage idempotency가 이미 구현되어 있음. 실전 운영에서 아쉬운 **UX 틈만** 메운다.

### 해결할 불편
- 현재 상태만 알고 싶을 때도 **7 stage 모두 재검사** 필요
- 특정 stage만 다시 돌리고 싶을 때 `reports/publish_state_*.json`을 **수동 편집**해야 함
- stage별 소요 시간·비용을 **사후 추적 불가**
- 장시간 발행 중 "지금 어느 stage?"를 stdout 스크롤로 확인

---

## 구현 명세

### Phase 1: 신규 CLI 플래그 (30분)

#### 1.1 `--status`
- 실행 없이 `reports/publish_state_<month>.json` 읽고 진행률만 출력
- 포맷:
  ```
  === 월간 발행 상태: 2026-05 ===
  ✅ [1/7] plan_loaded          — 21 꼭지
  ✅ [2/7] quality_gate         — passed=21 failed=0
  ⏳ [3/7] disclosure           — 미시작
  ⏸  [4/7] pdf_compile          — 미시작
  ...
  last_updated: 2026-04-24T13:45:02Z
  ```
- exit 0 (읽기 전용), `--strict` 주면 미완료 stage 존재 시 exit 1

#### 1.2 `--reset-stage <name>`
- 지정 stage key를 state dict에서 제거
- 다음 실행 시 해당 stage부터 재진행
- stage name 검증 (화이트리스트: plan_loaded·quality_gate·disclosure_injected·pdf_compile·ghost_publish·newsletter·sns)
- 실행은 하지 않음 (state 파일만 수정), confirmation prompt 포함

#### 1.3 `--from-stage <name>`
- 지정 stage부터 시작, 앞 stage는 무조건 skip 가정
- 앞 stage가 미완료인 경우 경고 (편집자가 의도적으로 skip하는 것인지 확인)
- `--reset-stage`와 조합 가능: `--reset-stage pdf_compile --from-stage pdf_compile`

### Phase 2: 텔레메트리 누적 (20분)

#### 2.1 state 스키마 확장
기존:
```json
{ "stages": { "plan_loaded": true, "article_count": 21 } }
```

확장:
```json
{
  "stages": { "plan_loaded": true, "article_count": 21 },
  "telemetry": {
    "plan_loaded":     { "started": "...", "finished": "...", "duration_sec": 0.3, "cost_usd": 0.0 },
    "quality_gate":    { "started": "...", "finished": "...", "duration_sec": 42.1, "cost_usd": 0.0 },
    "pdf_compile":     { "started": "...", "finished": "...", "duration_sec": 820.5, "cost_usd": 0.0 },
    ...
  }
}
```

#### 2.2 비용 집계 (선택적)
- `pdf_compile` · `ghost_publish` 등 외부 API 호출 stage에서 발생하는 비용을 누적
- `logs/*.jsonl`의 `cost_usd` 필드가 있으면 집계 (TASK_044/045 체계 재사용)
- 없으면 `cost_usd: null`

### Phase 3: 대시보드 통합 (TASK_048 확장) (15분)

#### 3.1 metrics_collector 연동
- TASK_048에서 신설되는 metrics 수집 경로에 **publish_monthly telemetry**도 포함
- `metrics.operations.publish_monthly = { last_month, stages_duration_sec, stages_cost_usd }`

#### 3.2 DashboardPage에 stage 진행률 위젯 (선택)
- 7 stage 타임라인 시각화 (Recharts Timeline 또는 StackedBar)
- **우선순위 낮음** — TASK_048 머지 후 별도 후속 태스크로 분리해도 무방

### Phase 4: 스모크 + 문서화 (15분)

#### 4.1 `docs/monthly_publish_runbook.md` (신규)
실전 시나리오별 명령:
- "지난 달 어디서 멈췄는지 확인": `--status`
- "품질 게이트만 다시 돌리기": `--reset-stage quality_gate` → `python publish_monthly.py --month 2026-05`
- "PDF 단계만 재실행 (앞 확정)": `--from-stage pdf_compile`
- "처음부터 다시": state 파일 삭제 + 재실행

#### 4.2 docs/backlog.md 정리
[docs/backlog.md](../docs/backlog.md)의 "publish_monthly UX 보강" 엔트리 제거 (본 태스크가 흡수).

#### 4.3 스모크
- 기존 2026-04 state 파일(있다면) 백업 후 `--status` 동작 확인
- 실제 실행 없이 state 파일 수정만 있는 `--reset-stage` 드라이런
- `--from-stage pdf_compile` dry-run으로 앞 stage skip 동작 확인
- 기존 `publish_monthly.py --month 2026-05 --dry-run` 회귀 없음

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| 편집자가 `--reset-stage` 실수로 완료된 stage 삭제 | confirmation prompt (`[y/N]`) 기본 활성화, `--yes`로만 스킵 |
| state 파일 스키마 변경으로 기존 state 파일 읽기 실패 | telemetry 필드는 `.get(..., {})` 안전 접근, 기존 state 호환 |
| stage name 오타 | 화이트리스트 검증 + 유사 이름 제안 (`did you mean ...`) |
| 텔레메트리가 기존 출력 UI를 어지럽힘 | 기존 stdout 출력은 유지, telemetry는 state 파일에만 기록 |
| `--from-stage`로 앞 stage 건너뛰어 데이터 정합성 깨짐 | 경고 출력 + `--yes` 없으면 confirmation 요구 |

---

## 완료 조건 (Definition of Done)
- [ ] `--status` 플래그 동작, stage별 진행 상태 + last_updated 출력
- [ ] `--reset-stage <name>` 화이트리스트 검증 + confirmation + state 수정
- [ ] `--from-stage <name>` 앞 stage skip + 경고 + confirmation
- [ ] state JSON에 `telemetry` 섹션 추가 (기존 필드 호환)
- [ ] cost_usd는 logs에서 집계 가능한 경우 기록, 아니면 null
- [ ] `docs/monthly_publish_runbook.md` 편집자 가이드 신규
- [ ] `docs/backlog.md`의 publish_monthly UX 엔트리 제거
- [ ] 스모크: 각 플래그 단독 동작 + 기존 `--dry-run` 회귀 없음
- [ ] CLAUDE.md 코딩 규칙 준수 (argparse, UTF-8 Windows)

---

## 산출물
- `scripts/publish_monthly.py` (확장)
- `docs/monthly_publish_runbook.md` (신규)
- `docs/backlog.md` (엔트리 제거)

---

## 후속 태스크 후보
- **TASK_053 후보**: stage 진행률 위젯 (TASK_048 대시보드 확장)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_050 implemented
python codex_workflow.py update TASK_050 merged
```
