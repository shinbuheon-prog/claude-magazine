# Round 2.B — Gate 1 승인 템플릿 (2026-04 W3)

대상: [reports/monthly_digest_2026-04-W3.md](monthly_digest_2026-04-W3.md)

본 템플릿은 편집자가 W3 디제스트의 5개 클러스터에 대해 Gate 1 결정을 내릴 때 사용하는 가이드입니다. 결정 후 디제스트 상단의 `editor_approval` YAML 블록을 직접 수정하면 됩니다.

---

## 결정 가이드

각 클러스터마다 다음 4 질문을 자문:

| 질문 | 의미 |
|---|---|
| **1. 매거진 톤앤매너 정합?** | 한국어권 Claude 실무자 대상 콘텐츠로 적합한가 |
| **2. 외부 출처 cross-check 가능?** | AWS·Anthropic 공식 문서로 사실 확인할 수 있는가 |
| **3. 동일 slug 반복 패턴 해석?** | 누적 학습인가 단순 재발행인가 — 정본 1건 채택 가능한가 |
| **4. 매거진 섹션 매핑 가능?** | feature·deep_dive·interview·review·insight·skill·운영 트러블슈팅 중 어디에 |

→ 4 질문 모두 yes·명확이면 **approve**, 1~2개 불확실이면 **hold**, 부적합이면 **reject**.

---

## 클러스터별 사전 평가 (참고용)

### Cluster A — `bedrock-permission-403` (★★★ 5일)

| 질문 | 평가 |
|---|---|
| 톤앤매너 | ✅ Claude Code + Bedrock 운영 트러블슈팅, 매거진 정체성 정합 |
| 외부 cross-check | ✅ AWS Bedrock 공식 문서·IAM 가이드로 가능 |
| 정본 채택 | 🟡 5회 반복 — 04-15·16·17 동일 slug 3회는 누적 학습 가능성 / 04-20·21은 inference profile·built-in subagent로 변형. **3건은 통합, 2건은 별도 다룰 수 있음** |
| 섹션 매핑 | ✅ "운영 트러블슈팅" 또는 "기술 디프" |

**예상 결정**: `approve` — "Bedrock에서 Claude Code 운영 시 만나는 403의 5가지 얼굴" 통합 기사

### Cluster B — `bedrock-opus47-endpoint` (★★★)

| 질문 | 평가 |
|---|---|
| 톤앤매너 | ✅ Opus 4.7 라우팅·운영 — 매거진 모델 배치 규칙(CLAUDE.md)과 정합 |
| 외부 cross-check | ✅ Anthropic 공식 모델 명세 + Bedrock 모델 ID 카탈로그 |
| 정본 채택 | 🟡 04-17 동일 slug 2회 + opus47 명시 1회 — **opus47 명시판이 정본** |
| 섹션 매핑 | ✅ "기술 디프" 또는 "운영 의사결정" |

**예상 결정**: `approve` — "Opus 4.7을 Bedrock·Anthropic 양쪽으로 붙이는 운영 패턴"

### Cluster C — `claude-code-multi-agent` (★★)

| 질문 | 평가 |
|---|---|
| 톤앤매너 | ✅ 매거진 정체성 직접 정합 (Claude Code 멀티에이전트) |
| 외부 cross-check | 🟡 Claude Code 공식 docs는 일부만 보장 — multi-agent practice는 자체 사례 |
| 정본 채택 | ⚠️ 동일 slug 3회 (04-17·20·21) — **누적 학습이면 04-21이 정본**, 단순 재발행이면 1건만 |
| 섹션 매핑 | ✅ "Cover Story 후보" |

**예상 결정**: `approve` — 단, **04-21 정본 채택 + 04-17·20을 번호별 누적 변경점 비교 박스**로

### Cluster D — `autofix-pr-review` (★)

| 질문 | 평가 |
|---|---|
| 톤앤매너 | 🟡 Autofix·PR 리뷰는 매거진보다는 SNS 사이드바 적합 |
| 외부 cross-check | ✅ GitHub Actions·Claude Code Skills로 검증 |
| 정본 채택 | ✅ 2건만 — 통합 또는 후속편 분리 둘 다 가능 |
| 섹션 매핑 | 🟡 "사이드바 박스" 또는 "SNS 카드뉴스 재가공" — 본편 부적합 |

**예상 결정**: `hold` — 5월 매거진 본편 사용 보류, **SNS 카드뉴스로 재가공만**

### Cluster E — `drawio-skill-aws` (단발)

| 질문 | 평가 |
|---|---|
| 톤앤매너 | ✅ "이번 달의 Skill" 코너 정합 |
| 외부 cross-check | ✅ Drawio·AWS 공식 자료로 가능 |
| 정본 채택 | ✅ 단발 — 그대로 |
| 섹션 매핑 | ✅ "Skill 살펴보기" 코너 |

**예상 결정**: `approve` — 단발 한 꼭지

---

## 갭 분석 5건 결정

| 영역 | 신규 brief 제안 | 추천 |
|---|---|---|
| 비개발자 페르소나 | "Cowork로 매거진 SOP를 운영한 한 달" | ✅ **본인 사례 — 자기 회고로 fact-check 부담 적음, 5월 발행 1순위 후보** |
| 거버넌스·법무 | "AI 기본법 시행 100일" | 🟡 외부 자료 의존 — 5월 또는 6월 |
| 한국어 편집 품질 | "한국어 매체 Claude 편집 가이드 v1" | 🟡 매거진 자체 표준화 — 가치 高, 단 6월 적합 |
| 외부 생태계 비교 | "Claude Code vs Cursor vs Replit Agent" | 🟡 Cursor·Replit 사용 경험 필요 — 후순위 |
| 도입 ROI | "Claude Max 6개월 운영기 (API 비용 0원)" | ✅ **TASK_033 무료 발행 정책 직접 정합 — 5월 또는 6월** |

**예상 결정**: 갭 분석 이관 `yes`. 위 5건을 [docs/backlog.md](../docs/backlog.md) "SNS 디제스트 갭 분석" 섹션에 이미 등록 — Gate 1 승인 시 **5월 plan_issue 우선순위 1·5번 항목**으로 승격 검토.

---

## YAML 블록 작성 예시 (편집자 사용)

위 평가 그대로 따른다면:

```yaml
status: partial           # 5개 중 4개 approve, 1개 hold
reviewer: shin.buheon
reviewed_at: 2026-04-25T15:00+09:00
notes: |
  - 클러스터별 채택 여부:
      bedrock-permission-403:        [x] approve  [ ] reject  [ ] hold
      bedrock-opus47-endpoint:       [x] approve  [ ] reject  [ ] hold
      claude-code-multi-agent:       [x] approve  [ ] reject  [ ] hold
      autofix-pr-review:             [ ] approve  [ ] reject  [x] hold
      drawio-skill-aws:              [x] approve  [ ] reject  [ ] hold
  - 갭 분석 신규 brief 큐 이관: [x] yes  [ ] no
  - 비고: autofix-pr-review는 본편 부적합으로 hold,
    SNS 카드뉴스 재가공만 진행. 갭 분석 5건 중 "Cowork SOP 운영기"·"Claude Max 6개월"
    2건을 5월 plan_issue 우선 후보로 승격.
```

---

## 승인 이후 자동화 흐름

Gate 1 `partial` 또는 `approved` 작성 → commit 시 다음 후속 작업 가능:

| 단계 | 액션 | 자동화 가능 여부 |
|---|---|---|
| 1 | `editor_approval` YAML 작성 + commit | 편집자 수동 |
| 2 | approved 클러스터의 source_id를 source_registry에 add | Cowork 또는 Claude (편집자 명령) |
| 3 | `source_registry_status: registered` 갱신 | 자동 |
| 4 | 5월 plan_issue.py에 후보 기사 추가 | Cowork 또는 편집자 수동 |
| 5 | brief_generator → draft → factcheck → editorial_lint | 매거진 표준 파이프라인 |
| 6 | Gate 2 (publish_monthly stage_quality_gate) | 매거진 표준 파이프라인 |
| 7 | Ghost 발행 | 편집자 명시 명령 |

→ 본 템플릿은 단계 1을 위한 가이드. 단계 2 이후는 별도 작업.

---

## 변경 이력

- 2026-04-25: Round 2.B 사전 평가 작성. 편집자 결정 입력 대기.
