# Development Backlog

태스크 단위로 분리할 만큼 크지 않거나, 다음 관련 수정 시점에 함께 작업하면 효율적인 아이디어를 모아둔다. 정식 태스크로 승격되면 본 문서에서 제거하고 `tasks/TASK_*.md`로 이동한다.

---

## Durable 체크포인트 · resume 체계

**출처**: [vercel-labs/open-agents](https://github.com/vercel-labs/open-agents) 개념 차용
**규모**: 단일 파일 수정 수준

`scripts/publish_monthly.py`는 월간 80페이지 21꼭지 + 팩트체크 + `/ultrareview` + PDF 빌드로 수십 분~수 시간 단위 장시간 실행. 중간 실패 시 현재는 전체 재실행.

### 아이디어
- 각 스테이지 완료 시 `state/publish_monthly_<YYYY-MM>.json` 체크포인트 기록
- 재시작 시 마지막 완료 스테이지 이후부터 재개
- TASK_028 운영 투명성 대시보드에 단계별 진행 상태 노출

### 언제 착수
- `publish_monthly.py` 다음 수정 시 함께
- 또는 월간 발행 중 재시작이 실제로 고통이 될 때

### 스택 제약
- **Vercel Workflow SDK 도입 금지** — 스택 변경 + 호스팅 비용 발생 (무료 발행 원칙 충돌)
- Python 표준 라이브러리(json·pathlib)로 구현

---
