# 5월 호 plan_issue 가이드 — Issue 1 정식 발행 (80p 정확 도달)

**대상**: [reports/roadmap_2026-05.md](roadmap_2026-05.md) 5월 1주차 (5/04-5/10) 콘텐츠 생산 ① 단계
**산출**: `data/issues/2026-05/plan.json` (plan_issue.py가 생성)
**목표**: **15 본문 꼭지 + 광고 1 코너 + 구조 6p = 80p 정확 도달**
**근거**: [docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §10·§13 + [docs/governance.md](../docs/governance.md) §"Sponsored Content"
**Issue 표지**: v0.3.0 정식 발행 첫 호

---

## editor_approval (Issue 1 plan Gate)

```yaml
status: pending           # pending | approved | rejected | partial
reviewer: <편집자 서명>
reviewed_at: <YYYY-MM-DDTHH:MM+09:00>
notes: |
  - 15 본문 꼭지 + 광고 1 코너 채택 여부:
      [ ] 그대로 / [ ] 1~2 꼭지 컷 / [ ] 1~2 꼭지 추가
  - 80p 도달 — Editorial 확장 +3p 채택 여부:
      [x] 채택 (창간호 인사 4p) / [ ] 다른 옵션
  - sponsored 카테고리 신규 추가 (plan_issue.py VALID_CATEGORIES):
      [x] 'sponsored' 추가됨 — Inside Classmethod 본 카테고리 사용
  - 5월 호 테마 (편집장 결정 필요):
      → _<이번 달의 주제 1줄 입력>_
  - 5/04 plan_issue.py init 실행 시점:
      [ ] 5/04 (월) 09:00 / [ ] 다른 시점
```

---

## 1. 15 본문 꼭지 + 광고 1 코너 매핑 (80p 정확)

| # | slug | category | pages | title (잠정) | source 출처 | 우선순위 |
|---:|---|---|---:|---|---|---|
| 1 | `claude-code-multi-agent` | feature | **14** | "Claude Code 멀티에이전트 — 권한·토큰·세션 묶어 보는 운영 가이드" | W3 SNS A3 정본 (`sns-blog-20260421-claude-code-multi-agent-practice`) + 04-17·20 누적 비교 박스 + 04-16 allow-deny + 04-17 token-saving 사이드바 | A |
| 2 | `bedrock-403-five-faces` | deep_dive | 4 | "Bedrock 403의 5가지 얼굴 — Claude Code 운영 시 만나는 권한 오류 통합 가이드" | W3 SNS A1 5건 통합 (`sns-blog-2026041X·20·21-bedrock-*-403-fix`) | A |
| 3 | `bedrock-opus47-endpoint` | deep_dive | 4 | "Opus 4.7을 Bedrock·Anthropic 양쪽으로 붙이는 운영 패턴" | W3 SNS A2 4건 통합 (`sns-blog-2026041X·20·21-bedrock-mantle-*-opus*`) | A |
| 4 | `sns-automation-sla` | deep_dive | 4 | "Cowork·Claude Code 자동화 SLA — 가시성 없는 의존이 매거진 운영을 어떻게 깨는가" | W4 자가 사례 + 자매 시스템 회신 메모 (`reports/sns_automation_w4_response.md`, 5/03 도착 예정) | A |
| 5 | `arxiv-claude-research` | deep_dive | 4 | "이 달의 Claude 논문 — arXiv 4월 핵심 5선" | arXiv 외부 자동 수집 (Claude 키워드 필터, `pipeline/ingesters/arxiv.py` 신규) | B (PoC 의존) |
| 6 | `anthropic-engineering-deep` | deep_dive | 4 | "Anthropic Engineering 4월 핵심 — MCP·Skills·Agent SDK 신규 기능" | Anthropic News RSS 4월 항목 자동 큐레이션 | A (RSS 운영 중) |
| 7 | `external-monthly-digest` | deep_dive | 4 | "이 달의 외부 시그널 5선 — HF·Meta·DeepMind·OpenAI 신규" | ai-daily-digest fork (`pipeline/auto_summarizer.py` 신규) | B (PoC 의존) |
| 8 | `claude-max-6mo-roi` | insight | 3 | "Claude Max 구독 1팀 6개월 — API 비용 0원 운영기" | 자가 사례 (W3 backlog 우선 후보 승격) | A |
| 9 | `hn-reddit-april-topics` | insight | 3 | "4월 r/ClaudeAI·HN에서 가장 많이 언급된 문제 TOP 10" | HN/Reddit 외부 자동 수집 + mckinsey-pptx KPI dashboard | B (PoC 의존) |
| 10 | `anthropic-release-timeline` | insight | 3 | "Anthropic 1분기 릴리즈 타임라인 — 2026 Q1 정리" | Anthropic News RSS + mckinsey-pptx 타임라인 컴포넌트 | B (mckinsey 의존) |
| 11 | `cowork-drive-flow` | insight | 3 | "Cowork × Drive 데이터 흐름 — 매거진 SOP 인포그래픽" | 자가 인포그래픽 (mckinsey-pptx process flow 컴포넌트) | B (mckinsey 의존) |
| 12 | `cowork-sop-monthly` | interview | **5** | "Cowork로 매거진 SOP를 운영한 한 달 — 편집장 자가 인터뷰" | 자가 인터뷰 (W3 backlog 우선 후보 승격) | A |
| 13 | `drawio-skill-aws` | review | 3 | "이번 달의 Skill — Drawio Skill로 AWS 아키텍처를 그리다" | W3 SNS E (`sns-blog-20260415-drawio-skill-aws-architecture`) | A |
| 14 | `competitive-comparison` | review | 3 | "Claude vs Gemini 2.0 vs GPT-5 — 운영자 시점 비교" | OpenAI Blog + Google AI Blog RSS 자동 수집 + 자체 분석 | B (외부 RSS 운영 중) |
| 15 | `korea-spotlight` | review | 3 | "Korea Spotlight — Classmethod Korea 4월 베스트 기고 TOP 3" | [reports/classmethodkr_best_2026-04.md](classmethodkr_best_2026-04.md) (큐레이션 완료) | **A (즉시 가능)** |
| 16 | `inside-classmethod` | **sponsored** | **7** | "Inside Classmethod — Claude 도입과 커뮤니티" | [reports/inside_classmethod_2026-05_draft.md](inside_classmethod_2026-05_draft.md) | **A (초안 완료)** |
| **본문 합계** | | | **72** | **15 꼭지 + 광고 1 코너** | | |
| 구조 (cover·toc·editorial 4p·colophon) | | | **8** | 표지 1 + TOC 2 + Editorial **4** (창간호 확장) + Colophon 1 | 자체 | A |
| **총합** | | | **80** | | | **80p 정확 도달 ✅** |

### 1-A. 우선순위 의미

- **A**: 5/04 plan 등록 시점에 source_id가 모두 source_registry에 등록 완료 + 자체 콘텐츠 작성 가능
- **B**: 외부 PoC(mckinsey-pptx 폰트 검증 + ai-daily-digest fork + arXiv ingester)의 1주 차 PoC 결과에 의존. 미달성 시 본 꼭지를 자체 콘텐츠로 대체 또는 페이지 컷

### 1-B. PoC 미달성 시 폴백 (B 꼭지 7건 중)

| B 꼭지 | 폴백 옵션 | 영향 |
|---|---|---|
| #5 arXiv | Anthropic News로 대체 (#6 분량 8p로 확장) | 0p 영향 |
| #7 ai-daily-digest | OpenAI/Google 공식 RSS 수동 큐레이션 (1일 작업) | 0p 영향 |
| #9 HN/Reddit | HN Algolia API 수동 호출 (1일) + matplotlib 차트 (mckinsey 미사용) | -1p (3p→2p) |
| #10 Anthropic 타임라인 | Recharts 자체 컴포넌트 사용 (mckinsey 미사용) | 0p 영향 |
| #11 Cowork 인포그래픽 | Recharts 자체 컴포넌트 사용 | 0p 영향 |
| #14 Claude vs Gemini vs GPT | 사용자 경험 부재 시 컷 | -3p (Editorial +3p 추가 보강 필요) |

→ 최악의 경우 -4p (76p), Editorial +4p로 80p 보전 가능.

---

## 2. plan_issue.py 실행 명령 시퀀스 (5/04 월요일)

```bash
# Step 1: 5월 호 초기화 (편집장 명시 테마 입력 필요)
python scripts/plan_issue.py init \
  --month 2026-05 \
  --theme "Claude 운영체계의 한 해 — 발행에서 정착까지" \
  --editor "shin.buheon"

# Step 2: 16 꼭지 일괄 등록 (A 우선순위 → B 우선순위 순)
# A 우선순위 (즉시 등록 가능, 9건)
python scripts/plan_issue.py add-article --month 2026-05 --slug claude-code-multi-agent       --category feature   --title "Claude Code 멀티에이전트 — 권한·토큰·세션 묶어 보는 운영 가이드"     --pages 14 --source-ids sns-blog-20260421-claude-code-multi-agent-practice sns-blog-20260417-claude-code-multi-agent-practice sns-blog-20260420-claude-code-multi-agent-practice sns-blog-20260416-claude-code-allow-deny-priority sns-blog-20260417-claude-code-token-saving-tips
python scripts/plan_issue.py add-article --month 2026-05 --slug bedrock-403-five-faces        --category deep_dive --title "Bedrock 403의 5가지 얼굴 — Claude Code 운영 시 만나는 권한 오류 통합 가이드" --pages 4  --source-ids sns-blog-20260415-bedrock-subagent-403-fix sns-blog-20260416-bedrock-subagent-403-fix sns-blog-20260417-bedrock-subagent-403-fix sns-blog-20260420-bedrock-inference-profile-403-fix sns-blog-20260421-bedrock-builtin-subagent-403-fix
python scripts/plan_issue.py add-article --month 2026-05 --slug bedrock-opus47-endpoint       --category deep_dive --title "Opus 4.7을 Bedrock·Anthropic 양쪽으로 붙이는 운영 패턴" --pages 4  --source-ids sns-blog-20260417-bedrock-mantle-langchain-opus sns-blog-20260417-bedrock-mantle-langchain-opus47 sns-blog-20260420-bedrock-mantle-langchain-opus47 sns-blog-20260421-bedrock-mantle-anthropic-endpoint-opus47
python scripts/plan_issue.py add-article --month 2026-05 --slug sns-automation-sla            --category deep_dive --title "Cowork·Claude Code 자동화 SLA — 가시성 없는 의존이 매거진 운영을 어떻게 깨는가" --pages 4
python scripts/plan_issue.py add-article --month 2026-05 --slug anthropic-engineering-deep    --category deep_dive --title "Anthropic Engineering 4월 핵심 — MCP·Skills·Agent SDK 신규 기능" --pages 4
python scripts/plan_issue.py add-article --month 2026-05 --slug claude-max-6mo-roi            --category insight   --title "Claude Max 구독 1팀 6개월 — API 비용 0원 운영기" --pages 3
python scripts/plan_issue.py add-article --month 2026-05 --slug cowork-sop-monthly            --category interview --title "Cowork로 매거진 SOP를 운영한 한 달 — 편집장 자가 인터뷰" --pages 5
python scripts/plan_issue.py add-article --month 2026-05 --slug drawio-skill-aws              --category review    --title "이번 달의 Skill — Drawio Skill로 AWS 아키텍처를 그리다" --pages 3 --source-ids sns-blog-20260415-drawio-skill-aws-architecture
python scripts/plan_issue.py add-article --month 2026-05 --slug korea-spotlight               --category review    --title "Korea Spotlight — Classmethod Korea 4월 베스트 기고 TOP 3" --pages 3
python scripts/plan_issue.py add-article --month 2026-05 --slug inside-classmethod            --category sponsored --title "Inside Classmethod — Claude 도입과 커뮤니티" --pages 7

# B 우선순위 (PoC 결과 확인 후 5/05 이후 등록, 6건)
python scripts/plan_issue.py add-article --month 2026-05 --slug arxiv-claude-research         --category deep_dive --title "이 달의 Claude 논문 — arXiv 4월 핵심 5선" --pages 4
python scripts/plan_issue.py add-article --month 2026-05 --slug external-monthly-digest       --category deep_dive --title "이 달의 외부 시그널 5선 — HF·Meta·DeepMind·OpenAI 신규" --pages 4
python scripts/plan_issue.py add-article --month 2026-05 --slug hn-reddit-april-topics        --category insight   --title "4월 r/ClaudeAI·HN에서 가장 많이 언급된 문제 TOP 10" --pages 3
python scripts/plan_issue.py add-article --month 2026-05 --slug anthropic-release-timeline    --category insight   --title "Anthropic 1분기 릴리즈 타임라인 — 2026 Q1 정리" --pages 3
python scripts/plan_issue.py add-article --month 2026-05 --slug cowork-drive-flow             --category insight   --title "Cowork × Drive 데이터 흐름 — 매거진 SOP 인포그래픽" --pages 3
python scripts/plan_issue.py add-article --month 2026-05 --slug competitive-comparison        --category review    --title "Claude vs Gemini 2.0 vs GPT-5 — 운영자 시점 비교" --pages 3

# Step 3: 검증
python scripts/plan_issue.py validate --month 2026-05
# 기대: 16 꼭지, 누적 페이지 72p (구조 8p 별도) → 80p 정확
```

---

## 3. brief_generator 입력 스펙 (꼭지별)

각 꼭지에 대해 brief_generator 호출 시 입력 형식:

```python
brief_input = {
    "slug": "<위 표의 slug>",
    "title_draft": "<위 표의 title>",
    "category": "<위 표의 category>",
    "target_pages": <위 표의 pages>,
    "source_ids": [<위 표의 source_ids>],
    "magazine_section_candidate": "<예: 운영 트러블슈팅 / 기술 디프 / 커버 스토리>",
    "external_cross_check_required": True,  # Cluster A·B는 필수
    "ai_disclosure_required": True,  # 본문 하단 AI 사용 고지 (governance.md)
}
```

### 3-A. 꼭지별 brief_generator 추가 가이드

| # | 추가 가이드 |
|---:|---|
| 1 | 04-21 정본 우선 + 04-17·20 누적 변경점 비교 박스. Anthropic 공식 멀티에이전트 best practices 1차 cross-check 필수 |
| 2 | 5건의 차이를 fact_checker로 구분 (sub agent / inference profile / built-in subagent / 일반 권한). AWS Bedrock IAM 공식 문서 cross-check |
| 3 | 라우팅·비용·지연 비교 표. CLAUDE.md 모델 배치 규칙(`claude-opus-4-7`)과 모순 없는지 검증 |
| 4 | 자매 시스템 회신 메모 인용 (`reports/sns_automation_w4_response.md`, 5/03 도착 예정). 단일 장애 포인트(SPOF) 분석 강조 |
| 6 | Anthropic Engineering blog RSS 4월 항목 N건 자동 추출 → Sonnet 4.6 요약 → 핵심 5선 |
| 8 | 정량 데이터 — Max 구독 6개월 사용량 통계 (요청 수·토큰·비용 0원 입증). [tasks/TASK_033](../tasks/TASK_033.md) 정합 |
| 12 | 자가 인터뷰 형식 — 편집장이 본인에게 질문·답변 (5p). [docs/governance.md](../docs/governance.md) AI 사용 고지 + 자가 인터뷰 명시 표기 |
| 13 | "이번 달의 Skill" 코너 표준 — 1) Skill 소개 2) 실전 사용 사례 3) 한계·다음 단계 |
| 15 | [reports/classmethodkr_best_2026-04.md](classmethodkr_best_2026-04.md) TOP 3 채택 → 편집자 1줄 요약 + "블로그에서 더 보기 →" 링크 박스 |
| 16 | [reports/inside_classmethod_2026-05_draft.md](inside_classmethod_2026-05_draft.md) 7p 구성 그대로. governance.md §"Sponsored Content" 6 의무 검증 필수 |

---

## 4. 1주차 일정 — Gate 체크 1주차 종료 (5/10)

[reports/roadmap_2026-05.md](roadmap_2026-05.md) §"5월 1주차" 일정 그대로:

| 일자 | 액션 |
|---|---|
| 5/04 (월) | `plan_issue init` + A 우선순위 9건 add-article + 5월 호 테마 확정 |
| 5/05 (화) | mckinsey-pptx 한국어 폰트 검증 PoC (1일) → 결과로 #10·#11 의존 결정 |
| 5/06 (수) | A 그룹 brief 4건 생성 (#1·#2·#3·#13) — `brief-generation` skill |
| 5/07 (목) | A 그룹 brief 5건 추가 (#4·#6·#8·#12·#15·#16) |
| 5/08 (금) | mckinsey-pptx OK 확정 후 B 우선순위 6건 add-article + brief 일부 시작 |
| 5/09 (토) | ai-daily-digest fork 시작 + arXiv ingester 1일 PoC |
| 5/10 (일) | 1주차 완료 점검 — 16 꼭지 brief 모두 생성 / source_id 누락 0건 / Editorial 확장 4p 골조 |

**Gate 체크 1주차 종료**: 16 brief × 각 source_id 모두 source_registry 등록. PoC B 꼭지 폴백 결정.

---

## 5. 누적 페이지 검증 스크립트 (수동 호출)

```python
# 5/04 add-article 일괄 등록 후 실행
python scripts/plan_issue.py validate --month 2026-05
# 기대 출력:
#   꼭지: 16개
#   카테고리 분포: {'feature': 1, 'deep_dive': 6, 'insight': 4, 'interview': 1, 'review': 3, 'sponsored': 1}
#   누적 페이지: 72p
#   ✅ 유효함
# (구조 8p는 plan_issue.py 외부 — Issue 정합 페이지)
```

---

## 6. AI 사용 고지

본 가이드는 (1) 이전 세션의 콘텐츠 후보 9건 매핑, (2) [docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §10·§13 시뮬레이션, (3) [docs/governance.md](../docs/governance.md) §"Sponsored Content" 6 의무, (4) [docs/monthly_magazine_workflow.md](../docs/monthly_magazine_workflow.md) §1.1 80p 표준 지면 배분을 종합해 휴리스틱 정리됐습니다. LLM 호출 0회. 5/04 plan_issue 실행은 편집장 수동 + plan_issue.py 자동.

---

## 변경 이력

- 2026-04-26: 초안 작성. 15 본문 + 광고 1 + 구조 8p = 80p 정확 도달 매핑. plan_issue.py VALID_CATEGORIES에 'sponsored' 신규 추가 (1줄 패치). 5/04 실행 명령 시퀀스 + 1주차 일정 + 폴백 옵션 6건 명시.
