# Development Backlog

태스크 단위로 분리할 만큼 크지 않거나, 다음 관련 수정 시점에 함께 작업하면 효율적인 아이디어를 모아둔다. 정식 태스크로 승격되면 본 문서에서 제거하고 `tasks/TASK_*.md`로 이동한다.

---

## publish_monthly UX 보강 (`--status`, `--reset-stage`, `--from-stage`)

**규모**: 단일 파일 수정, 30~45분

[scripts/publish_monthly.py](../scripts/publish_monthly.py)는 이미 `reports/publish_state_<month>.json` 체크포인트 + stage별 idempotency가 구현됨(2026-04-24 확인). 따라서 "체크포인트 구축"은 불필요. 남은 UX 틈만 메우는 작은 개선.

### 아이디어
- `--status` 플래그: 상태만 출력하고 종료 (실행 없이 진행률 확인)
- `--reset-stage <name>`: 특정 stage를 `state`에서 제거해 강제 재실행
- `--from-stage <name>`: 지정 stage부터 시작 (앞 stage는 skip)
- Stage별 소요 시간·비용 텔레메트리 state에 누적 (TASK_048 대시보드와 연동 가능)

### 언제 착수
- `publish_monthly.py` 다음 수정 시 함께
- 또는 월간 발행 중 재실행 고통이 실제로 체감될 때

### 스택 제약
- Python 표준 라이브러리만 (Vercel Workflow SDK 도입 금지 — 무료 발행 원칙)

---

## 과거 엔트리 정리

### (무효) "publish_monthly 체크포인트·resume 체계" 신규 구현

2026-04-24 vercel-labs/open-agents 시너지 분석 시 기록한 항목이나, 기존 `publish_monthly.py` 코드에 이미 체크포인트가 구현되어 있어 **무효화**. 남은 UX 틈만 상단의 "publish_monthly UX 보강" 항목으로 축소.

---
