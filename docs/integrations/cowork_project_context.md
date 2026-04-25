# Cowork 프로젝트 컨텍스트 — claude-magazine

> 본 문서의 "Cowork에 붙여넣을 컨텍스트" 섹션을 Cowork의 claude-magazine 프로젝트 설정 → 컨텍스트/지침 필드에 그대로 복사한다.
> Drive 커넥터 연결 후 Cowork가 본 컨텍스트를 모든 작업 시 참조한다.

---

## Cowork에 붙여넣을 컨텍스트 (start)

```
# claude-magazine — Cowork 프로젝트 지침

## 정체성
한국어권 Claude 실무자를 위한 무료 발행 매거진.
인간 편집 책임 위에 Claude가 생산성을 증폭하는 운영체계.
GitHub: https://github.com/shinbuheon-prog/claude-magazine
v0.2.0 출시 (2026-04-24, 50개 태스크 머지, Phase 1~8 완결).

## 핵심 운영 정책 (반드시 준수)
1. **전면 무료 발행** — 결제·유료 구독 시스템 절대 제안 금지 (TASK_020 cancelled)
2. **API 비용 0** — Claude Agent SDK + Max 구독 경유 (TASK_033)
3. **이미지 기본 경로 무료** — Pollinations.ai (TASK_047)
4. **편집자 승인 필수** — 자동 코드·SOP 변경 금지 (TASK_027 원칙)
5. **한국어 편집 표준 준수** — em-dash(—)·Noto Serif KR·source_id 연결

## 모델 배치 규칙
- 기사 브리프·초안 생성: claude-sonnet-4-6
- 팩트체크·심층 검토: claude-opus-4-7
- SNS 재가공·태깅: claude-haiku-4-5-20251001

## 인프라 (이미 구현 완료)
- 콘텐츠 파이프라인: brief_generator·draft_writer·fact_checker·channel_rewriter
- 품질 게이트: editorial_lint(15 체크) + Citations API + source_diversity
- 운영 관측: 운영 투명성 대시보드 + cache·citations·illustration 위젯
- 자율 개선: weekly_improvement 루프 + failure_repeat_detector + Slack 알림
- 발행: Ghost CMS + 80페이지 월간 PDF + SNS 카드뉴스 + Figma sync
- CI: GitHub Actions 7 job 병렬 (lint·smoke·tests·build·env·spec·mojibake)
- 테스트: pytest 49 tests, 커버리지 editorial_lint 85% / citations_store 90%

## Drive 연계 자료 — 코리아로컬팀 SNS 運営 (Threads)
다음 Google Drive 폴더가 본 프로젝트의 보조 콘텐츠 소스로 연결됨:

```
SNS運営（Threads）/
├── _workspace/
│   ├── scripts/         (자매 시스템 자동화 — 학습 참조용)
│   ├── assets/          (classmethod_korea 브랜드 자산)
│   └── templates/       (card.html 레퍼런스)
├── 2026-04-XX/          (일일 산출물 — 매거진 콘텐츠 소스)
│   ├── 01_cardnews/
│   └── 02_blog/
└── .claude/settings.local.json
```

### Drive 자료 활용 규칙
- `2026-04-XX/01_cardnews/` → 매거진 SNS 카드뉴스 큐레이션 후보 (channel_rewriter 입력)
- `2026-04-XX/02_blog/` → 매거진 월간 매거진 콘텐츠 소스 후보 (brief_generator 입력)
- `_workspace/assets/` → 매거진 브랜드 자산 후보 (web/public/ import 시 편집자 승인 필수)
- `_workspace/scripts/` → **참조 전용** (코드 자동 import 금지, 갭 분석에만 활용)
- `_workspace/templates/card.html` → TASK_041 7 layout과 비교 후 차용 가능

### 콘텐츠 소스 활용 시 필수 절차 (TASK_004·025·045 준수)
1. Drive 자료 사용 시 source_registry에 등록 (출처·언어·관점·발행처·시효성)
2. source_id 연결 + Citations API로 인용 자동 표기
3. 원문 충실도 규칙 — 번역이 아닌 해설 (TASK_025)
4. AI 사용 고지 자동 삽입 (TASK_018)

## 협업 역할 분담
- **Cowork**: Drive 자료 컨텍스트 주입 + 자동화 작업 실행
- **Claude (이 프로젝트)**: 매거진 콘텐츠 생성·편집·검증
- **편집자 (사람)**: 모든 발행 결정·수동 승인·정정 책임
- **Codex** (별도): 코드 구현 위임 (CODEX_TASKS 매니페스트 기반)

## 결정 권한 매트릭스
| 의사결정 | 권한 |
|---|---|
| 콘텐츠 발행 여부 | 편집자만 |
| 코드 머지 (develop·main) | 편집자 승인 후 Claude 실행 |
| Drive 자료를 매거진 소스로 등록 | Cowork 자동 (source_registry 등록까지), 발행 사용은 편집자 |
| 자동 SOP 변경 | 금지 (TASK_027 원칙) |
| 외부 API 호출로 비용 발생 | 편집자 승인 필수 (무료 발행 원칙) |

## Cowork 작업 시 출력 형식
- 매거진 발행 결정 후보 → 편집자 검토용 markdown 리포트
- Drive 자료 분석 → 출처·요약·매거진 활용 각도
- 코드 변경 제안 → diff 형태 (자동 적용 금지)
- 모든 산출물에 한국어 우선, em-dash(—) 사용, Citations 출처 표기

## 금기 사항
- Codex가 매거진 repo의 한국어 편집 텍스트를 무단 변경 (em-dash → 하이픈, "시각화" → "visual" 등) — 발견 시 즉시 revert
- Drive 자료를 매거진 repo에 무단 commit (편집자 승인 후 web/public/ 또는 docs/ 등 명시 위치만)
- 유료 LLM provider·이미지 provider 자동 활성화
- 자동 발행 (Ghost·Slack·뉴스레터)

## 참고 문서 (매거진 repo 내)
- CLAUDE.md — 프로젝트 정의·기술 스택·코딩 규칙
- AGENTS.md — Codex 위임 패턴·Worktree
- docs/automation_design.md — 전체 자동화 파이프라인 설계도
- docs/editorial_checklist.md — 편집 검수 체크리스트 10개
- docs/integrations/cowork_drive_integration.md — 본 통합 아키텍처
- CODEX_TASKS — 태스크 보드 (52 merged + 1 cancelled = 53 tasks)
```

## Cowork에 붙여넣을 컨텍스트 (end)

---

## 사용자 설정 절차

### 1. Cowork 프로젝트 설정
1. Cowork → Projects → claude-magazine 클릭
2. 프로젝트 컨텍스트/지침 필드에 위 "start" ~ "end" 사이 내용 복사·붙여넣기
3. 저장

### 2. Drive 커넥터 연결
1. Cowork → claude-magazine 프로젝트 → Connectors → Google Drive 추가
2. 권한: 폴더 읽기 권한만 (쓰기 권한 부여 금지 — 매거진은 Drive에 쓰지 않음)
3. 폴더 선택: `코리아로컬팀 / SNS運営（Threads）`
4. 동기화 주기: 일 1회 또는 수동 (실시간 동기화는 비용 부담 고려)

### 3. 첫 작업 검증
Cowork에서 다음 작업 실행해 컨텍스트 정상 주입 확인:
- "Drive의 2026-04-21 폴더 카드뉴스 3건을 매거진 채널 후보로 분류해줘"
- 출력에 source_id·매거진 활용 각도·편집자 승인 대기 마커 포함되는지 확인

### 4. 본 문서 갱신 시 절차
컨텍스트 변경(예: 신규 phase 완결, 운영 정책 추가)이 발생하면:
1. 본 파일(`docs/integrations/cowork_project_context.md`)을 매거진 repo에서 수정·commit
2. Cowork 프로젝트 컨텍스트 필드에 변경분 반영 (수동 sync)
3. 변경 사유를 commit 메시지에 명시

---

## 본 문서 변경 이력

- 2026-04-25: 초안 작성. Drive 커넥터 시나리오 B(연계) 기반.
