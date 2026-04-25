# Roadmap 2026-05 — 정식 발행 1호 (Issue 1)

**목표**: 2026-05-31 (토) Claude Magazine 정식 발행 Issue 1 발행
**발행 형태**: 80p 월간 PDF + Ghost 게시 + SNS 4채널 재가공
**버전 표시**: v0.3.0 (정식 발행 첫 호)
**근거**: v0.2.1까지 Phase 1~8 완료, 자율 개선 루프·운영 관측·발행 신뢰성 모두 green. 이제 처음으로 "발행물"을 만든다.

---

## 운영 원칙 (필수 준수)

- **무료 발행 원칙** — 결제·유료 구독 시스템 도입 금지
- **인간 편집 책임** — 모든 게이트(Gate 1·Gate 2)에서 편집자 명시 승인
- **AI 보조 한계** — Claude는 brief·draft·factcheck·관측 보조. 발행 결정은 편집자
- **외부 cross-check** — 운영 이슈는 AWS·Anthropic 공식 문서 1차 소스 필수
- **5월 콘텐츠 부담 관리** — 갭 분석 6건 중 5월 호는 우선 후보 2~3건만, 나머지는 6월 이후

---

## 콘텐츠 후보 풀 (Round 2.B Gate 1 결과 기반)

### A. SNS 디제스트 approved 클러스터 (W3) — 정본 채택 후 4건

| 클러스터 | source 수 | 정본 후보 | 매거진 섹션 | 매거진 활용 각도 |
|---|---|---|---|---|
| `bedrock-permission-403` | 5 | 04-21 builtin-subagent (최신·통합) | 운영 트러블슈팅 / 기술 디프 | "Bedrock에서 Claude Code 운영 시 만나는 403의 5가지 얼굴" |
| `bedrock-opus47-endpoint` | 4 | 04-21 mantle-anthropic-endpoint | 기술 디프 / 운영 의사결정 | "Opus 4.7을 Bedrock·Anthropic 양쪽으로 붙이는 운영 패턴" |
| `claude-code-multi-agent` | 5 | 04-21 multi-agent-practice | 커버 스토리 후보 | "Claude Code 멀티에이전트 — 권한·토큰·세션 묶어 보는 운영 가이드" + 04-17·20 누적 비교 박스 |
| `drawio-skill-aws` | 1 | 단발 | 이번 달의 Skill | "Drawio Skill로 AWS 아키텍처를 그리는 한 꼭지" |

### B. 갭 분석 5월 우선 후보 — 본인 사례 2건

| 갭 영역 | 신규 brief | 출처 |
|---|---|---|
| 비개발자 페르소나 | "Cowork로 매거진 SOP를 운영한 한 달" | W3 backlog 승격 |
| 도입 ROI·정량 사례 | "Claude Max 구독 1팀 6개월 — API 비용 0원 운영기" | W3 backlog 승격 |

### C. 갭 분석 5월 신규 후보 — W4 anomaly 자가 사례 1건

| 갭 영역 | 신규 brief | 출처 |
|---|---|---|
| 운영 가시성 (W4 신규) | "Cowork·Claude Code 자동화 SLA — 가시성 없는 의존이 매거진 운영을 어떻게 깨는가" | W4 backlog 등록. 자매 시스템 회신 도착 후 데이터 보강 |

### D. Korea Spotlight — 자체 콘텐츠 (Classmethod Korea Tech Blog) 1코너

| 영역 | 코너 | 출처 |
|---|---|---|
| Review (3p) | "Korea Spotlight — Classmethod Korea 4월 베스트 기고 TOP 3" | [reports/classmethodkr_best_2026-04.md](classmethodkr_best_2026-04.md) (4월 시범 큐레이션 완료) |

→ 자체 콘텐츠 → 인용 한도 자유 + 블로그 트래픽 유입 효과. 편집장 자가 기고 포함 시 명시 표기 의무.

**5월 호 발행 분량 후보**: A(4) + B(2) + C(1) + D(1) = **8건**. 80페이지 매거진은 통상 5~7개 본 기사 적합. 1차 plan_issue에서 편집자가 우선순위 컷 + Cluster D(autofix-pr-review)는 SNS 카드뉴스로만 재가공.

**80p 도달 전략**: [docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §10 5월 호 시뮬레이션 — classmethodkr Korea Spotlight 3p + mckinsey-pptx 자동 인포그래픽 9p + ai-daily-digest 외부 디제스트 7p 결합 시 **70p 도달**. 추가 보강(Interview 자가 인터뷰 +5p, KPI dashboard +3p, Editorial 확장 +2p)으로 80p 정확 도달 가능.

---

## 4주 로드맵 — 1·2주차 콘텐츠 생산, 3·4주차 고도화

```
5월 1주차 (5/04-5/10)  ━━━━━━━━━━━━━━  콘텐츠 생산 ①  기획·brief
5월 2주차 (5/11-5/17)  ━━━━━━━━━━━━━━  콘텐츠 생산 ②  draft 작성
5월 3주차 (5/18-5/24)  ━━━━━━━━━━━━━━  고도화 ①        팩트·표준·다양성
5월 4주차 (5/25-5/31)  ━━━━━━━━━━━━━━  고도화 ② + 발행  시각·게이트·송고
```

> **사용자 요구**: "마지막 3·4주차에는 고도화로 퀄리티 개선" — 1·2주차에 콘텐츠를 모두 끝내고, 3·4주차는 검수·디자인·송고에 집중.

### 사전 준비 (5/01-5/03 주말)

| 태스크 | 산출물 | 담당 |
|---|---|---|
| 자매 시스템 회신 확인 (W4 점검 의뢰 결과) | 회신 메모 → `reports/sns_automation_w4_response.md` | 사용자 (외부 채널) |
| 5월 호 테마·표지 컨셉 잠정 결정 | `plan_issue.py init` 인자 준비 | 편집자 |
| Cluster C 정본 채택 검토 (04-17·20·21 비교) | 정본 1건 + 누적 비교 박스 메모 | Claude Code |

### 5월 1주차 (5/04-5/10) — 콘텐츠 생산 ① 기획·brief

**완료 정의**: 5월 호 brief JSON 7건 확정 + plan_issue 등록

| 일자 | 태스크 | 산출물 |
|---|---|---|
| 5/04 (월) | `plan_issue.py init --month 2026-05 --theme "<TBD>"` | `data/issues/2026-05/plan.json` |
| 5/04 (월) | 콘텐츠 후보 7건 확정 (A 4건 + B 2건 + C 1건), Cluster D는 SNS 트랙 분리 | plan.json articles 섹션 |
| 5/05-5/06 | A 그룹 brief 4건 생성 — `brief-generation` skill | `drafts/briefs/2026-05/article_*.json` |
| 5/07-5/08 | B 그룹 brief 2건 생성 (Cowork SOP, Claude Max ROI) | 상동 |
| 5/09-5/10 | C 그룹 brief 1건 (운영 가시성 SLA) — 자매 시스템 회신 데이터 결합 | 상동 |
| 5/10 (일) | 1주차 완료 점검 — 7 brief × source_id 모두 source_registry 등록 확인 | 검증 보고서 |

**Gate 체크 1주차 종료시**: brief 7건 × 각 brief의 `source_ids` 누락 0건. 미달 시 2주차로 1주 연장.

### 5월 2주차 (5/11-5/17) — 콘텐츠 생산 ② draft 작성

**완료 정의**: 7개 기사 draft 1차 완성 + 자체 1차 검수 완료

| 일자 | 태스크 | 산출물 |
|---|---|---|
| 5/11-5/12 | A 그룹 draft 4건 작성 — `draft_writer.py` (Sonnet 4.6) | `drafts/2026-05/article_*.md` |
| 5/13-5/14 | B 그룹 draft 2건 작성 | 상동 |
| 5/15 (목) | C 그룹 draft 1건 작성 | 상동 |
| 5/16 (금) | 카드뉴스 시각 자산 1차 매핑 — W3 Drive 카드뉴스 5덱 → 기사 매핑 후보표 | `reports/card_mapping_2026-05.md` |
| 5/17 (토) | 자체 1차 검수 — `editorial-review` skill 7회 실행 | 검수 보고서 |

**Gate 체크 2주차 종료시**: draft 7건 × `editorial_lint` 1차 통과(오류 0, 경고는 허용). 미달 시 발행 분량 컷 (7→6 또는 5).

### 5월 3주차 (5/18-5/24) — 고도화 ① 팩트·표준·다양성

**완료 정의**: factcheck → standards_checker → source_diversity 3개 게이트 모두 pass

| 일자 | 태스크 | 산출물 | 비고 |
|---|---|---|---|
| 5/18-5/19 | A 그룹 factcheck — `fact-check-cycle` skill (Opus 4.7) | factcheck 보고서 7건 | Bedrock·Anthropic 공식 문서 cross-check 필수 |
| 5/20 (수) | B 그룹 factcheck (자가 사례 — 본인 데이터 검증) | 상동 | 본인 사례 → cross-check 부담 적음 |
| 5/20 (수) | C 그룹 factcheck (운영 가시성 자가 사례) | 상동 | 자매 시스템 회신 메모 인용 정확성 확인 |
| 5/21 (목) | `standards_checker` 7회 — TASK_025 카테고리별 Pass/Fail | standards 보고서 | Fail 시 draft 수정 → 재실행 |
| 5/22 (금) | `source-validation` 7회 — 4 규칙(언어·관점·발행처·시효성) | diversity 보고서 | 관점 편중 발견 시 보완 brief 추가 |
| 5/23-5/24 | 3개 게이트 통합 보고서 작성 + 편집자 1차 승인 (Gate 2 사전 점검) | `reports/quality_gate_2026-05.md` | |

**Gate 체크 3주차 종료시**: 7개 기사 × (factcheck pass + standards pass + diversity pass). Fail 1건이라도 4주차 시작 전 fix.

### 5월 4주차 (5/25-5/31) — 고도화 ② + 발행

**완료 정의**: 5/31 토요일 19:00 KST Issue 1 정식 발행

| 일자 | 태스크 | 산출물 | 비고 |
|---|---|---|---|
| 5/25 (월) | 카드뉴스 PNG 매거진 `web/public/` 복사 — 라이선스·경로 PR 명기 | 복사된 PNG + PR | Cluster D autofix-pr-review 카드뉴스도 별도 SNS 트랙 |
| 5/26 (화) | 인포그래픽 (insight 페이지) 디자인 — `baoyu-infographic` skill | InsightPage 컴포넌트 prop 추가 | Cluster B 라우팅 비교 + Cluster C 멀티에이전트 권한표 |
| 5/27 (수) | 본문 일러스트 추가 (선택) — `baoyu-article-illustrator` skill | 기사별 상단 일러스트 | 무료 provider 우선 (Pollinations/HF) — `audit_budget.py --strict` |
| 5/27 (수) | AI 사용 고지 본문 하단 삽입 검토 (전 기사) | publish-gate 보고서 | TASK_026 |
| 5/28 (목) | `publish-gate` skill 통합 실행 — editorial_lint + standards + diversity + AI 고지 | 통합 보고서 | 1건이라도 fail 시 5/29 fix 마감 |
| 5/28 (목) | Gate 2 — `publish_monthly --month 2026-05 --status` 진행 상태 점검 | stage 보고서 | |
| 5/29 (금) | 마감 fix + Gate 2 통과 확정 + 편집자 최종 승인 서명 | plan.json `editor_signature` | |
| 5/30 (토) | `publish_monthly --month 2026-05 --dry-run` 시뮬레이션 | dry-run 보고서 | 모든 stage green 확인 |
| 5/30 (토) | PDF 빌드 — `pdf-compile` skill (Vite + Puppeteer 80p A4) | `output/claude-magazine-2026-05.pdf` | |
| 5/30 (토) | SNS 4채널 재가공 — `sns-distribution` skill | 채널별 카피·자산 | sns/instagram/linkedin/twitter |
| 5/31 (토) AM | 최종 점검 — PDF·Ghost 미리보기·SNS 카드 정합 | 점검 체크리스트 | 편집자 최종 OK |
| **5/31 (토) PM 19:00** | **`publish_monthly --month 2026-05 --publish --confirm` + Ghost 송고 + GitHub Release v0.3.0** | **Issue 1 발행** | 정식 발행 |

**Gate 체크 4주차 종료시**: PDF 발행 + Ghost 게시 + GitHub Release v0.3.0 + SNS 4채널 1차 송출 완료.

---

## 발행 후 (5월 마지막 + 6월 1주차 회고)

| 태스크 | 산출물 | 시점 |
|---|---|---|
| `weekly_improvement.py --since-days 7` 1 사이클 — Issue 1 발행 운영 신호 분석 | `reports/improvement_2026-06-01.md` | 6/01 |
| `failure_repeat_detector.py --window 14` — 발행 직전·직후 실패 패턴 점검 | failure 보고서 | 6/02 |
| Issue 1 회고 — 4주 로드맵 차이·정정 발생 여부·다음 호 개선점 | `reports/issue1_retro.md` | 6/03 |
| 6월 호(Issue 2) plan_issue init | `data/issues/2026-06/plan.json` | 6/04 |

---

## 위험·완충 장치

| 위험 | 대응 |
|---|---|
| W3 cluster 정본 결정이 어려움 (특히 C 동일 slug 3회) | 5/04 사전 준비에 비교 메모 작성. 결정 못 하면 04-21 정본 + 04-17·20 누적 변경점 비교 박스 자동 채택 |
| 자매 시스템 회신이 5/03까지 안 옴 | C(운영 가시성) 자체를 5월 호에서 빼고 6월 호로 미룸. 발행 분량 7→6건 |
| factcheck에서 Cluster A·B 외부 cross-check 불일치 발견 | 해당 기사 컷 또는 소규모 사이드바로 강등. 발행 분량 컷 |
| 카드뉴스 라이선스 검증 지연 | 본문 기사만 발행, SNS 카드 1주 후 후속 발행 |
| 5/29 마감 fix 미달 | 5/30 추가 1일 사용, 5/31 발행 시간을 19:00 → 21:00로 늦춤 |
| illustration 비용 $0 cap 초과 | `audit_budget.py --strict` 자동 차단. 무료 provider만 사용 |
| 5/31 발행 자체가 안 되는 경우 | 6/01-6/03 backup 윈도우. v0.3.0 → v0.3.0-rc 표기로 분리 |

---

## 5월 호 성공 정의 (KPI)

| 지표 | 최저 | 목표 |
|---|---|---|
| 본문 기사 수 | 5건 | 7건 |
| Cluster A·B·C·E 정본 채택 | 3개 | 4개 모두 |
| 갭 분석 자가 사례 기사 | 1건 | 2건 (Cowork SOP + Claude Max) |
| W4 anomaly 자가 사례 기사 | 0건 (생략 가능) | 1건 (운영 가시성) |
| factcheck pass 율 | 100% (모든 발행 기사) | 100% |
| editorial_lint 오류 | 0 | 0 |
| AI 사용 고지 누락 기사 | 0 | 0 |
| publish_monthly 자동화 stage 실패 | 0 | 0 |
| illustration 비용 | $0 | $0 (무료 provider 강제) |
| 발행 일정 준수 | 5/31 (당일) | 5/31 19:00 KST |

---

## 참조 문서

- [reports/monthly_digest_2026-04-W3.md](monthly_digest_2026-04-W3.md) — Round 2.B Gate 1 결과
- [reports/monthly_digest_2026-04-W4.md](monthly_digest_2026-04-W4.md) — W4 anomaly 점검 트리거
- [docs/integrations/sns_to_magazine_pipeline.md](../docs/integrations/sns_to_magazine_pipeline.md) — SNS → 매거진 SOP
- [docs/monthly_publish_runbook.md](../docs/monthly_publish_runbook.md) — 월간 발행 캘린더
- [docs/editorial_checklist.md](../docs/editorial_checklist.md) — 발행 전 10개 체크
- [docs/governance.md](../docs/governance.md) — AI 사용 고지·정정 책임
- [docs/source_policy.md](../docs/source_policy.md) — rights_status·인용 한도
- [docs/backlog.md](../docs/backlog.md) §"SNS 디제스트 갭 분석" — 6 신규 brief 후보
- [CLAUDE.md](../CLAUDE.md) — 모델 배치·코딩 규칙
- [README.md](../README.md) §"Phase 진행 현황" — Phase 1~8 완료 상태

---

## 변경 이력

- 2026-04-26: 초안 작성. v0.2.1 closure 직후, Round 2.B Gate 1 + Round 2.D Gate 1 결과를 받아 5월말 정식 발행 1호 4주 로드맵으로 정리. 사용자 명시 요구: "마지막 3·4주차에는 고도화로 퀄리티 개선". 콘텐츠 후보 7건(SNS 디제스트 4 + 갭 분석 자가 사례 2 + W4 anomaly 자가 사례 1).
- 2026-04-26: D 그룹 (Korea Spotlight) 1코너 추가 — 콘텐츠 후보 7건 → **8건**. classmethodkr 기술블로그 자체 콘텐츠 활용. [docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) 외부 큐레이션 파이프라인 5계층 설계 동시 작성. 5월 호 도달 분량 시뮬레이션 67p → **70p**.
