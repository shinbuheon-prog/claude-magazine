# TASK_051 — 발행 실패 복구 플레이북 (stage 실패 진단·복구 가이드 자동 생성)

## 메타
- **status**: todo
- **prerequisites**: TASK_050 (status·reset-stage·from-stage)
- **예상 소요**: 60~90분
- **서브에이전트 분할**: 불필요
- **Phase**: 7 (발행 신뢰성·배포 자동화)

---

## 목적
월간 발행 중 특정 stage 실패 시, 편집자가 **다음에 무엇을 해야 할지 즉시 알 수 있도록** 자동 플레이북을 생성한다. 현재는 실패 메시지만 보고 직접 CLAUDE.md·스크립트를 뒤져 복구 경로를 찾아야 함.

### 해결하는 운영 상황
- "pdf_compile이 실패했다 — Puppeteer 문제? Node 의존성? disk 부족?"
- "ghost_publish가 401 — Admin API Key 재발급? JWT 만료?"
- "newsletter 이 실패했는데 — Ghost Content API 아니라 뉴스레터 전용 스코프 이슈?"

→ 각 stage의 **예상 실패 모드 + 1차 복구 명령**을 체크리스트화.

---

## 구현 명세

### Phase 1: 실패 분류 사전 (30분)

#### 1.1 `spec/failure_playbook.yml` (신규)
stage × 실패 클래스별 체크리스트:

```yaml
stages:
  plan_loaded:
    common_failures:
      - class: "plan_file_missing"
        detector: "FileNotFoundError.*drafts/issues"
        recovery:
          - "drafts/issues/<month>.yml 존재 확인"
          - "plan_issue.py --month <month> --init 로 재생성"
      - class: "yaml_parse_error"
        detector: "yaml.YAMLError"
        recovery:
          - "drafts/issues/<month>.yml 구문 검증"
          - "mojibake 스캔: python -c ..."

  quality_gate:
    common_failures:
      - class: "article_status_not_approved"
        detector: "status=(draft|lint)"
        recovery:
          - "편집자 승인 UI(TASK_029)에서 article status=approved 처리"
          - "또는 --force로 강행 (품질 책임 편집자)"
      - class: "editorial_lint_fail"
        detector: "lint_fail"
        recovery:
          - "python pipeline/editorial_lint.py --draft <path> --strict"
          - "source-id·ai-disclosure·correction-policy 3종 수정"

  pdf_compile:
    common_failures:
      - class: "puppeteer_timeout"
        detector: "TimeoutError.*puppeteer"
        recovery:
          - "cd scripts && npm install (puppeteer 재설치)"
          - "node scripts/generate_pdf.js --month <month> --verbose"
          - "디스크 여유 5GB 이상 확보"
      - class: "vite_build_fail"
        detector: "vite.*build failed"
        recovery:
          - "cd web && npm run build"
          - "에러 로그에서 jsx syntax·import 확인"

  ghost_publish:
    common_failures:
      - class: "jwt_401"
        detector: "401.*Unauthorized"
        recovery:
          - "GHOST_ADMIN_API_KEY 형식 확인 (kid:secret)"
          - "Ghost 대시보드 Integrations 페이지에서 키 재발급"
          - "scripts/check_env.py --only ghost"

  newsletter:
    common_failures:
      - class: "members_api_disabled"
        detector: "Members API.*disabled"
        recovery:
          - "Ghost 사이트 Settings > Members 활성화"
          - "Newsletter from 주소 + SMTP 설정 확인"

  sns:
    common_failures:
      - class: "channel_rewriter_timeout"
        detector: "timeout.*channel_rewriter"
        recovery:
          - "CLAUDE_PROVIDER=api 재시도"
          - "logs/channel_rewriter_*.json에서 마지막 request_id 확인"
```

#### 1.2 schema validation
- `spec/failure_playbook.schema.yml` 또는 코드 내 dataclass로 스펙 검증
- CI에서 YAML 문법 + 필수 필드 검사

### Phase 2: 실패 감지기 + 플레이북 렌더러 (30분)

#### 2.1 `pipeline/failure_playbook.py` (신규)
```python
def match_failure_class(stage: str, error_output: str) -> str | None:
    """playbook.yml의 detector 정규식을 순회해 매칭되는 class 반환"""

def render_playbook(stage: str, failure_class: str, context: dict) -> str:
    """recovery 체크리스트를 markdown으로 렌더"""
```

#### 2.2 publish_monthly.py 통합
기존 실패 경로:
```python
if not ok:
    print(f"\n❌ {stage_fn.__name__} 실패 — 체크포인트 저장됨, 수정 후 재실행 가능")
    return 1
```

확장:
```python
if not ok:
    # 실패 시 playbook 자동 생성
    playbook_md = generate_failure_report(args.month, stage_fn.__name__, captured_error)
    playbook_path = REPORTS_DIR / f"failure_{args.month}_{stage_fn.__name__}.md"
    playbook_path.write_text(playbook_md, encoding="utf-8")
    print(f"\n❌ {stage_fn.__name__} 실패")
    print(f"   체크포인트: {_state_path(args.month)}")
    print(f"   복구 가이드: {playbook_path}")
    return 1
```

#### 2.3 출력 예시
`reports/failure_2026-05_stage_pdf_compile.md`:
```markdown
# 발행 실패 복구 가이드

- 월: 2026-05
- 실패 stage: pdf_compile
- 실패 시각: 2026-04-24T13:45:02Z
- 감지된 class: puppeteer_timeout

## 1차 복구 체크리스트

- [ ] cd scripts && npm install (puppeteer 재설치)
- [ ] node scripts/generate_pdf.js --month 2026-05 --verbose
- [ ] 디스크 여유 5GB 이상 확보

## 재실행 명령

```bash
python scripts/publish_monthly.py --month 2026-05 --reset-stage pdf_compile
python scripts/publish_monthly.py --month 2026-05
```

## 참고 로그

- reports/publish_state_2026-05.json
- logs/publish_monthly_2026-05-04_*.log
```

### Phase 3: docs + runbook 통합 (15분)

#### 3.1 `docs/monthly_publish_runbook.md` 업데이트 (TASK_050에서 생성)
- "실패했을 때" 섹션 추가
- `reports/failure_*.md`가 자동 생성됨을 명시

#### 3.2 `docs/failure_playbook_catalog.md` (신규)
playbook.yml을 사람이 읽기 쉬운 카탈로그로 렌더 (Codex 생성 스크립트 또는 수동).

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| playbook detector 정규식이 실제 에러 메시지와 매칭 안 됨 | 매칭 실패 시 generic fallback 플레이북 제공 (check_env.py·로그 확인 안내) |
| playbook.yml 오타·스펙 위반 | Phase 1.2 schema 검증 + CI 검사 |
| 플레이북이 오래된 복구 명령을 제안 | 정기 리뷰 대상 명시 (예: 6개월마다 CLAUDE.md 업데이트 시 동기화) |
| 편집자가 플레이북만 믿고 근본 원인 방치 | "3회 이상 같은 class 실패 시 weekly_improvement 루프(TASK_027) 검토" 안내 |
| 민감한 에러 스택이 리포트에 노출 | API 키·토큰 패턴 자동 마스킹 (TASK_017 pii_masker 재활용 고려) |

---

## 완료 조건 (Definition of Done)
- [ ] `spec/failure_playbook.yml` 7 stage × 각 2~4 failure class 카탈로그
- [ ] `pipeline/failure_playbook.py` detector·렌더러 구현
- [ ] `publish_monthly.py` 실패 시 자동 플레이북 생성 (기존 출력 회귀 없음)
- [ ] `reports/failure_<month>_<stage>.md` 포맷 일관
- [ ] API 키·토큰 마스킹 확인 (패턴: `sk-ant-*`, `figd_*`, `kid:secret` 등)
- [ ] `docs/monthly_publish_runbook.md` "실패했을 때" 섹션 추가
- [ ] `docs/failure_playbook_catalog.md` 카탈로그 문서
- [ ] 스모크: 각 stage별 모의 실패 → playbook 생성 확인
- [ ] playbook.yml 스키마 검증 (pytest에 포함 가능, TASK_049와 연계)

---

## 산출물
- `spec/failure_playbook.yml` (신규)
- `pipeline/failure_playbook.py` (신규)
- `scripts/publish_monthly.py` (실패 hook 추가)
- `docs/monthly_publish_runbook.md` (섹션 확장, TASK_050과 병행)
- `docs/failure_playbook_catalog.md` (신규)

---

## 후속 태스크 후보
- **TASK_054 후보**: 같은 failure class 3회 반복 시 weekly_improvement 루프 자동 트리거
- **TASK_055 후보**: 플레이북 성공률 측정 (복구 명령이 실제로 해결했는지 편집자 피드백 수집)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_051 implemented
python codex_workflow.py update TASK_051 merged
```
