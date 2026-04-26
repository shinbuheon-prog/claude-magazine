# 에이전트 아키텍처 (Agent Architecture)

매거진 자동화 파이프라인의 7 모듈을 "에이전트" 추상화 layer로 명문화. Claude Code 오케스트레이터 + Codex 서브에이전트 팀 + 인간 게이트의 통합 구조.

> **본 문서 작성 배경**: 외부 컨설팅 보고서에서 제시된 7 에이전트 + 5 인간 게이트 + 4축 분리 기준을 매거진 현재 자산과 매핑. 매거진 정체성(무료 발행·인간 편집·1인 편집자)에 맞게 적응한 결과.
> 상위: [CLAUDE.md](../CLAUDE.md) §"에이전트 역할 분담"
> 자매: [docs/integrations/external_curation_pipeline.md](integrations/external_curation_pipeline.md), [docs/governance.md](governance.md)

---

## 1. 매거진 7 에이전트 (= 7 pipeline 모듈)

매거진은 외부 보고서의 "7 에이전트" 구조와 거의 1:1 대응되는 pipeline 모듈을 이미 보유. 단 명시적으로 "에이전트"라 부르지 않고 pipeline 모듈로 운영.

| # | 에이전트 | 모델·effort | 매거진 모듈 | 입력 | 출력 | 트리거 |
|---:|---|---|---|---|---|---|
| 1 | **Scout** | Haiku 4.5 / low | [pipeline/source_ingester.py](../pipeline/source_ingester.py) + [scripts/curate_classmethodkr_best.py](../scripts/curate_classmethodkr_best.py) | feeds.yml + RSS · 외부 이벤트 · 편집장 수동 | SourceItem 등록 (source_registry.db) | cron 4시간 / 수동 |
| 2 | **Architect** | Sonnet 4.6 / medium | [scripts/plan_issue.py](../scripts/plan_issue.py) + brief_generator (계획) + `prompts/template_A_brief.txt` + `template_editor_in_chief.txt` | SignalCandidate · source_bundle | ArticleBrief (data/issues/YYYY-MM/plan.json) | Scout 완료 + 편집장 승인 |
| 3 | **Drafter** | Sonnet 4.6 / high | [pipeline/draft_writer.py](../pipeline/draft_writer.py) + `prompts/template_B_draft.txt` + `template_claude_trend_brief.txt` | approved_brief · source_bundle | ArticleDraft (drafts/) | Architect 완료 + brief_approved |
| 4 | **Verifier** | Opus 4.7 / high | [pipeline/fact_checker.py](../pipeline/fact_checker.py) + [pipeline/editorial_lint.py](../pipeline/editorial_lint.py) + `prompts/template_C_factcheck.txt` + `template_quality_review.txt` | ArticleDraft · source_bundle | ClaimVerdict + 13항 검수 결과 | Drafter 완료 |
| 5 | **Adapter** | Haiku 4.5 / low | [pipeline/channel_rewriter.py](../pipeline/channel_rewriter.py) + [.claude/skills/sns-distribution/](../.claude/skills/) | ApprovedArticle | 채널별 콘텐츠 (SNS·email·PDF·SEO meta) | 편집자 최종 승인 후 |
| 6 | **Visualizer** | Sonnet 4.6 / medium | [pipeline/illustration_hook.py](../pipeline/illustration_hook.py) + `pipeline/illustration_providers/` 5종 + mckinsey-pptx fork (검토 중) | DataExtract · brand_guide | VisualSpec + 렌더링 결과 | Drafter 완료 + 데이터 테이블 존재 / 수동 |
| 7 | **Auditor** | Haiku 4.5 일상 / Sonnet 4.6 주간 | [pipeline/weekly_improvement.py](../pipeline/weekly_improvement.py) + [pipeline/failure_repeat_detector.py](../pipeline/failure_repeat_detector.py) + [scripts/audit_budget.py](../scripts/audit_budget.py) | pipeline_logs · cost_records · quality_metrics | daily_digest · weekly_report | cron 매일 09시 / 매주 월요일 09시 |

**총평**: 매거진은 보고서 7 에이전트 구조를 약 90% 이미 구현. Visualizer만 외부 API 어댑터(Datawrapper/Flourish) 미연결, mckinsey-pptx fork로 보강 검토 중.

---

## 2. 분리 기준 4축 매트릭스

서브에이전트(또는 pipeline 모듈)를 나누는 기준은 단순히 "기능이 다르다"가 아니라 다음 4축을 동시에 평가해 분리 여부를 결정한다.

| 축 | 질문 | 같은 모듈로 합칠 조건 | 분리할 조건 |
|---|---|---|---|
| **실패 격리** | 이 모듈이 실패하면 다른 모듈도 멈추는가? | 실패해도 독립 재시도 가능 | 실패 시 후속 작업 전체 차단 |
| **모델 요구** | 같은 모델·같은 effort로 처리 가능한가? | 동일 모델·동일 effort | 모델이나 effort가 다름 (예: Haiku low vs Opus high) |
| **컨텍스트 크기** | 하나의 컨텍스트에 넣어도 되는가? | 합쳐도 50K 토큰 이내 | 합치면 컨텍스트 오버플로 |
| **책임 추적** | 출력 오류 시 원인을 즉시 특정할 수 있는가? | 출력 구조가 단순 | 출력이 복합적이라 원인 분리 필요 |

### 매거진 적용 사례

- Scout vs Architect: 4축 모두 분리 (모델 다름·실패 격리·컨텍스트 크기·책임 추적) → ✅ 분리
- editorial_lint vs fact_checker: 책임 추적 분리 (lint는 형식, factcheck는 사실) → ✅ 분리
- Adapter (SNS 4채널 = sns/instagram/linkedin/twitter): 같은 모듈 내 병렬 실행, 채널별 분리 안 함 → ✅ 합침
- channel_rewriter vs illustration_hook: 모델 요구 다름 + 책임 추적 분리 → ✅ 분리

---

## 3. 순차 vs 병렬 실행 토폴로지

```
[순차 실행 필수]                          [최종 승인 후 병렬 실행 가능]
                                          ┌─→ Adapter (이메일·SNS·PDF·SEO 4 변환)
Scout → Architect → Drafter → Verifier ──┤
                                          └─→ Visualizer (차트 생성)
```

| 단계 | 실행 패턴 | 사유 |
|---|---|---|
| Scout → Architect | 순차 | Architect는 Scout의 SignalCandidate 입력 필수 |
| Architect → Drafter | 순차 + **G1 인간 게이트** | 편집장 승인 없이 draft 생성 금지 |
| Drafter → Verifier | 순차 | Verifier는 완성된 draft 검증 |
| Verifier → 인간 편집 | 순차 + **G2/G3 인간 게이트** | confirmed_ratio < 0.85 자동 알림 또는 G3 최종 승인 |
| 인간 편집 → Adapter / Visualizer | 병렬 | 4 채널 + 차트 동시 생성 가능 |
| 모든 산출물 → publish | 순차 + **publish-gate skill 5단계** | 발행 직전 통합 검증 |

**Git Worktree 활용**: TASK_031에서 도입한 Git Worktree 병렬 위임 패턴을 Adapter·Visualizer 동시 실행에 적용 가능. 단 5월 호는 단일 워크트리로 진행 (1인 편집자 부담 관리).

---

## 4. 인간 게이트 G1~G5

| 게이트 | 위치 | 매거진 운영 상태 | SLA | Phase 9 후보 |
|---|---|---|---|---|
| **G1 브리프 검토** | Architect 완료 시 항상 | ✅ 운영 중 (plan_issue 단계 편집장 명시 승인) | 4시간 | SLA 명문화 (작은 closure) |
| **G2 검증 결과 검토** | Verifier 완료 + confirmed_ratio < 0.85 | 🟡 **부분** (publish-gate skill 검토 의무, 자동 강제 부재) | 2시간 | TASK_056: confirmed_ratio 자동 계산 + 게이트 자동 강제 |
| **G3 최종 편집 승인** | 인간 편집 완료 시 항상 | ✅ 운영 중 (publish-gate 5단계 통과 후 편집자 명시) | 8시간 | SLA 명문화 (작은 closure) |
| **G4 정정 승인** | 게시 후 오류 발견 시 | 🟡 **부분** (governance.md에 정정 책임자·24시간 명시, 자동화 부재) | 1시간 | TASK_057: 정정 게이트 자동 추적 |
| **G5 비용 초과 승인** | 단일 기사 비용 > 예산의 150% | 🟡 **부분** (audit_budget.py 자동 차단, 편집자 승인 흐름 부재) | 30분 | TASK_058: 차단 → 승인 흐름 |

**현재 SLA 상태**: G1·G3는 운영 중, G2·G4·G5는 governance·audit_budget·publish-gate에 흩어져 있음. **5/31 발행 후 6월 호 작업으로 통합 자동화**.

---

## 5. 통합 상태 머신 (매거진 단순화)

외부 보고서의 14 상태를 매거진 1인 편집자·월간 발행 운영에 맞게 6 상태로 단순화:

```
todo → briefing → drafting → approved → published → archived
                                    ↓
                                 killed (편집장 폐기)
```

| 상태 | 의미 | 다음 액션 | 매거진 매핑 |
|---|---|---|---|
| `todo` | plan_issue 등록 직후 | Architect 할당 | plan_issue.py status |
| `briefing` | brief 작성 중 (Architect 실행 중) | brief 완성 후 G1 | drafts/briefs/ |
| `drafting` | brief 승인 후 draft 작성 중 (Drafter 실행 중) | draft 완성 후 Verifier | drafts/ |
| `approved` | publish-gate 5단계 통과 + G3 승인 | 발행 직전 Adapter·Visualizer 실행 | plan_issue editor_signature |
| `published` | 발행 완료 | 운영 모니터링 (G4 대기) | data/issues/YYYY-MM/published.json |
| `archived` | 다음 호 발행 후 아카이브 | 회고·운영 신호 분석 | reports/issue_retrospectives/ |
| `killed` | 편집장 폐기 결정 | 최종 — DLQ에 기록 | (Phase 9 — 현재는 단순 상태 변경) |

**자동화 layer**: 현재 매거진은 상태 전이를 수동(편집자 codex_workflow.py update)으로 진행. Phase 9에서 state_change 트리거 + 자동 next-agent 할당 검토 (TASK_055).

---

## 6. 트리거 분류

| 트리거 종류 | 매거진 운영 상태 | 사용 시점 |
|---|---|---|
| **정기 cron** | ✅ GitHub Actions (RSS 수집·weekly_improvement·audit_budget) | Scout 4시간 주기 / Auditor 매일·매주 |
| **외부 이벤트 webhook** | 🟡 일부 (failure_repeat_detector → Slack) | 릴리스 노트 감지·자매 시스템 anomaly |
| **편집장 수동 요청** | ✅ codex_workflow.py + plan_issue.py | 5/04 plan_issue init 등 |
| **state_change** | 🟡 부분 (수동 진행) | Phase 9 자동화 후보 |

---

## 7. 매거진 정체성 보호 결정 (외부 보고서 권장 일부 기각)

외부 보고서가 권장한 도구 중 매거진 정체성과 충돌해 **기각**한 항목:

| 보고서 권장 | 매거진 결정 | 사유 |
|---|---|---|
| Supabase 상태 저장소 | 🔴 **기각** | 매거진 SQLite 운영 — 무료·1인 운영에 적합. Supabase는 Scale 단계 후 재검토 |
| n8n 정기 스케줄러 | 🔴 **기각** | 매거진 GitHub Actions 사용 (이미 운영) — 별도 워크플로 엔진 도입 시 over-engineering |
| Sentry 애플리케이션 관측 | 🔴 **기각** | 매거진 자체 logs/ + failure_repeat_detector + weekly_improvement 사용 — 자체 자율 개선 루프가 더 강함 |
| Langfuse LLM 관측 | 🔴 **기각** | 매거진 Max 구독 경유 ($0) — 비용 추적 자체가 의미 작음. Anthropic API 직접 호출 시 재검토 |
| Cloudflare R2 스토리지 | 🔴 **기각** | 매거진 로컬 파일 + GitHub 저장소 사용 — Scale 단계 시점에 R2 또는 GitHub Releases 검토 |
| 정식 서킷 브레이커 | 🔴 **기각** | 1인 편집자 + 월간 발행 = 트래픽 적음. 현재 failure_repeat_detector (3회+ 14일 윈도우)로 충분 |
| Dead Letter Queue 테이블 | 🔴 **기각** | 동상 — Scale 단계 진입 시 재검토 |
| 비용 가드 3계층 | 🟡 **부분** | 매거진 Max 구독 = LLM 비용 $0이라 illustration만 cap (audit_budget.py). 외부 API (arXiv·Reddit·OpenAI 등) 도입 시 계층 2 확장 |

**결정 원칙**: 매거진은 **무료 발행 + 1인 편집자 + 월간 발행** 정체성을 유지. Scale 단계(매월 5+ Issue 또는 외부 트래픽 1k+ DAU 도달) 진입 시 위 항목 재검토.

---

## 8. Phase 9 정식 명세 후보 (5/31 발행 후 결정)

| TASK | 분량 | 시점 | 보고서 매핑 |
|---|---|---|---|
| TASK_055: 통합 에이전트 명세 `agents/*.yaml` 7종 | 1일 | 6/01~ | 보고서 §"에이전트 명세" |
| TASK_056: G2 자동 게이트 (confirmed_ratio < 0.85 → 편집자 알림) | 1일 | 6/01~ | 보고서 §"G2" |
| TASK_057: G4 정정 게이트 (24시간 1차 응답 자동 추적) | 2일 | 6/01~ | 보고서 §"G4" + governance.md |
| TASK_058: G5 비용 초과 게이트 (자동 차단 → 편집자 승인 흐름) | 1일 | 6/01~ | 보고서 §"G5" + audit_budget.py 보강 |
| TASK_059: state_change 자동 트리거 + next-agent 할당 | 2일 | 6/01~ | 보고서 §"상태 머신" |
| TASK_060: Visualizer Datawrapper API 어댑터 | 2일 | 6월 호 검토 | 보고서 §"Visualizer" |
| TASK_061: 비용 가드 계층 2 (기사별 LLM·검색·기타 통합) | 2일 | 외부 API 도입 후 | 보고서 §"비용 가드" |
| TASK_062: 정식 서킷 브레이커 + DLQ | 3일 | Scale 단계 | 보고서 §"AgentCircuitBreaker" |

→ 8건 신규 TASK 후보. **5월 호 발행 사이클 동안 명세 추가 금지** (Phase 마무리 메모리 원칙). 5/31 발행 후 6/01~6/03 회고 시점에 우선순위 결정.

---

## 9. 모델 배치 규칙 (CLAUDE.md 강제)

| 에이전트 | 모델 | effort | 사유 |
|---|---|---|---|
| Scout | Haiku 4.5 | low | 시그널 수집·정규화 — 단순 분류 |
| Architect | Sonnet 4.6 | medium | 브리프 구조화 — 균형 |
| Drafter | Sonnet 4.6 | high | 초안 품질이 편집 시간 결정 |
| Verifier | Opus 4.7 | high | 검증·심층 검토 — 최고 추론 모델 |
| Adapter | Haiku 4.5 | low | 채널 재가공 — 빠르고 저렴 |
| Visualizer | Sonnet 4.6 | medium | 차트·인포그래픽 — 균형 |
| Auditor | Haiku 4.5 (일상) / Sonnet 4.6 (주간) | low / medium | 일상 감시는 Haiku, 주간 분석은 Sonnet |

**위반 시**: GitHub Actions CI에서 `pipeline/*.py` grep 검증 → PR 차단. 모든 호출 후 `request_id` 추출 → `logs/` 저장 의무 (CLAUDE.md 코딩 규칙).

---

## 10. 자율 개선 루프 (매거진 고유 — 보고서 미언급)

매거진은 보고서의 Auditor를 한 단계 확장한 **자율 개선 폐쇄 루프**를 운영 중 (Phase 8 종결 시점).

```
[운영 신호 4종]
cache · citations · illustration · publish
  ↓
[failure_repeat_detector] 14일 윈도우 3회+ 같은 failure_class 감지
  ↓
[weekly_improvement] Sonnet 4.6 분석 → SOP 업데이트 제안서
  ↓
[reports/improvement_YYYY-MM-DD.md]
  ↓
편집장 검토 → 채택 시 governance.md / SKILL.md / pipeline 모듈 갱신
```

이는 보고서의 Auditor (일일/주간 리포트)보다 한 단계 위 — **자율적 SOP 개선 제안**까지 진행. 매거진 정체성(인간 편집 + AI 보조)에 정합.

---

## 11. 변경 이력

- **2026-04-26**: 초안 작성. 외부 컨설팅 보고서(7 에이전트 + 5 게이트 + 4축 분리 기준 + 회복력 + 비용 가드)를 매거진 현재 자산(7 pipeline 모듈 + Codex 위임 + 자율 개선 루프)에 매핑. 매거진 정체성(무료 발행 + 1인 편집자 + 월간 발행) 보호 결정 8건 명시. Phase 9 정식 명세 후보 TASK_055~062 8건 등록. 본 문서는 5월 호 발행 사이클에 영향 없음 — Phase 마무리 직접 구현 메모리 준수.
