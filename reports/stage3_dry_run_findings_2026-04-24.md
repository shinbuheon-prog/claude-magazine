# Stage 3 Dry-Run Findings (2026-04-24)

v0.2.0 릴리즈 전 `publish_monthly.py --dry-run` 실전 검증에서 발견된 항목 정리.

## 발견 1: ROOT sys.path 누락 (실버그, 즉시 수정)

- **파일**: `scripts/publish_monthly.py`
- **증상**: `python scripts/publish_monthly.py --month 2026-05 --dry-run` 실행 시 `ModuleNotFoundError: No module named 'pipeline'`
- **원인**: TASK_051에서 `from pipeline.failure_playbook import generate_failure_report` 추가했으나, ROOT 정의·sys.path.insert 블록이 pipeline.* import **이후**에 위치
- **수정 커밋**: `a445ce1`
- **pytest에서 놓친 이유**: 테스트는 `from pipeline.failure_playbook import ...`를 직접 import하여 경로 문제 우회. CLI 직접 실행만 노출 가능한 상황.

## 발견 2: package-lock.json gitignore (예방적 수정)

- **파일**: `.gitignore` + `web/package-lock.json` + `scripts/package-lock.json`
- **증상 예상**: TASK_052 CI `npm ci` 실행 시 lock 파일 부재로 실패
- **원인**: `.gitignore` 13번 줄 `package-lock.json` 패턴이 두 앱의 lock 파일 모두 차단
- **수정 커밋**: `fe4aa69`
- **pytest에서 놓친 이유**: CI가 실제로 돌아가기 전이라 로컬 pytest에서는 감지 불가

## 검증된 기능 (TASK_050·051)

### TASK_050 publish_monthly UX
- ✅ `--status`: 7 stage 표 + last_updated
- ✅ `--reset-stage quality_gate --yes`: state에서 제거 성공
- ✅ `--from-stage pdf_compile --yes`: 앞 stage skip + 이미 완료된 stage에 경고
- ✅ Stage별 telemetry 누적 (duration_sec·cost_usd)
- ✅ state JSON 백업/복원 호환

### TASK_051 failure_playbook
- ✅ quality_gate 실패 → `reports/failure_2026-05_quality_gate.md` 자동 생성
- ✅ detector 매칭: `article_status_not_approved` 정확 판정
- ✅ Recovery Checklist + Retry Commands 자동 포함
- ✅ Error Output 섹션에 원본 에러 포함 (토큰 마스킹 대상 없음 확인)

## 검증 제한 (스코프 외)

- `ghost_publish` / `newsletter` / `sns` — `--publish` 플래그 필요, 외부 서비스 인증 요구. dry-run은 skip.
- `pdf_compile` — `compile_monthly_pdf.py`가 dry-run에서도 초기 검증은 돌지만 실제 PDF 출력은 스킵
- Langfuse·n8n 등 외부 관측·워크플로우 — dry-run에서 비활성

## 후속 권장 작업

### 즉시 (v0.2.0 릴리즈 일부)
없음 — 발견한 두 버그 이미 수정.

### 중기 (v0.2.1·v0.3.0 후보)
1. **check_env.py에 scripts 디렉터리 CLI 테스트 추가**
   - ROOT sys.path 같은 블로커를 pytest 이전에 탐지하도록
   - 각 스크립트 `--help` 호출 성공 체크
2. **CI에 "scripts_help" job 추가**
   - pytest와 별개로 각 CLI의 `--help` 호출이 ImportError 없이 동작하는지 보장
3. **docs/monthly_publish_runbook.md에 dry-run 시나리오 섹션 추가**
   - 발견 1 같은 케이스의 재현·진단 가이드

## 이번 실험 교훈

- **pytest 통과만으로 배포 안전 판단은 불충분** — CLI 직접 실행 경로가 별도 검증 필요
- **로컬 dry-run 실험이 CI 실패 pre-flight로 유효** — main 오염 전 두 개 버그 탐지
- **TASK_051 playbook이 설계대로 동작** — 실제 운영에서 편집자 복구 가이드 역할 가능

---

**작성**: Stage 3 실험 세션 (Claude Code)
**관련 태스크**: TASK_050, TASK_051, v0.2.0 릴리즈 준비
