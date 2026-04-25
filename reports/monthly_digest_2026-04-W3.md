# Monthly Digest — 2026-04 W3 (시범 큐레이션)

**대상 기간**: 2026-04-15 ~ 2026-04-21 (7일)
**입력**: `SNS運営（Threads）` Drive 폴더 — 평일 5일치 카드뉴스 5덱(32장) + 블로그 17건
**처리 모드**: 메타데이터 + 링크 참조 (본문 무복사)
**SOP**: [docs/integrations/sns_to_magazine_pipeline.md](../docs/integrations/sns_to_magazine_pipeline.md)
**source_registry_status**: `partial`  <!-- proposed | partial | registered. Gate 1 승인 후 partial, source_registry add 후 registered. 2026-04-26: 4 클러스터(A·B·C·E) 15건 registered, Cluster D(autofix-pr-review) hold로 미등록 → partial 유지. -->

---

## editor_approval (Gate 1)

```yaml
status: partial           # 5 클러스터 중 4 approve, 1 hold
reviewer: shin.buheon
reviewed_at: 2026-04-26T01:10+09:00
notes: |
  - 클러스터별 채택 여부:
      bedrock-permission-403:        [x] approve  [ ] reject  [ ] hold
      bedrock-opus47-endpoint:       [x] approve  [ ] reject  [ ] hold
      claude-code-multi-agent:       [x] approve  [ ] reject  [ ] hold
      autofix-pr-review:             [ ] approve  [ ] reject  [x] hold
      drawio-skill-aws:              [x] approve  [ ] reject  [ ] hold
  - 갭 분석 신규 brief 큐 이관: [x] yes  [ ] no
  - 비고:
      * Cluster D(autofix-pr-review)는 본편 부적합 → hold, SNS 카드뉴스 재가공만 진행.
      * 갭 분석 5건 중 "Cowork SOP 운영기"·"Claude Max 6개월 운영기" 2건은
        5월 plan_issue 우선 후보로 승격 (docs/backlog.md "SNS 디제스트 갭 분석" 섹션 기등록).
      * approved 클러스터 15건 source_id는 source_registry에 rights_status=free로 등록 완료
        (article_id=monthly_digest_2026-04-W3, language=ko, publisher=SNS-Threads-Drive).
      * Cluster C 동일 slug 3회는 발행 단계에서 04-21 정본 채택 + 04-17·20 누적 비교 박스로 처리.
```

---

## 0. 7일치 입력 인벤토리

| 일자 | 카드뉴스 | 블로그 | Drive 폴더 |
|---|---|---|---|
| 2026-04-15 (수) | 7장 (1덱) | 3건 | [폴더](https://drive.google.com/drive/folders/1_y4gEDmFQN5tVEoTJ1VeZqbyyPZNDMUq) |
| 2026-04-16 (목) | 6장 (1덱) | 3건 | [폴더](https://drive.google.com/drive/folders/10B1lmoVjJv1_lpaY-QwHmOmINFrwXqrD) |
| 2026-04-17 (금) | 6장 (1덱) | 5건 | [폴더](https://drive.google.com/drive/folders/1f3hMaRxf3tRccGey40AbokH2Clf0EnLQ) |
| 2026-04-18 (토) | — | — | (폴더 없음 — 주말 미적재) |
| 2026-04-19 (일) | — | — | (폴더 없음 — 주말 미적재) |
| 2026-04-20 (월) | 6장 (1덱) | 3건 | [폴더](https://drive.google.com/drive/folders/1NaHaxgwy7aqonbSRyS4CBNZnUAVWxVAU) |
| 2026-04-21 (화) | 7장 (1덱) | 3건 | [폴더](https://drive.google.com/drive/folders/1vT-lHjAd2Usj_VyUR1zc1y1dN1Z1mFlA) |

**합계**: 카드뉴스 5덱(32장) + 블로그 17건. 주말 2일 자동화 미가동 — gap이 아니라 운영 정책으로 추정 (편집자 확인 필요).

---

## 1. 주제·태그 클러스터링

토큰 동시출현 빈도 ≥ 2 기준으로 5개 클러스터 검출. 신뢰도 표기는 출현 빈도와 일자 분산 기준.

### Cluster A — `bedrock-permission-403` (★★★ 최다 반복)

Bedrock에서 서브에이전트·인퍼런스 프로필을 호출할 때 발생하는 권한 403 오류 해법 시리즈. 5일 중 5일 모두 등장.

| source_id | 일자 | 링크 |
|---|---|---|
| `sns-blog-20260415-bedrock-subagent-403-fix` | 04-15 | [폴더](https://drive.google.com/drive/folders/1flzhhG78AyIHikx1YUR1xi87gW7qGZUL) |
| `sns-blog-20260416-bedrock-subagent-403-fix` | 04-16 | [폴더](https://drive.google.com/drive/folders/1Yp0670L6tGhuTGRCa9ZY6W2fAZR_kSbU) |
| `sns-blog-20260417-bedrock-subagent-403-fix` | 04-17 | [폴더](https://drive.google.com/drive/folders/1eFjXKx1lFGwBjpSRekKZRy8Sg386y98S) |
| `sns-blog-20260420-bedrock-inference-profile-403-fix` | 04-20 | [폴더](https://drive.google.com/drive/folders/1FeylpfS9czXYfxA1eHiJYf823l_vg0SV) |
| `sns-blog-20260421-bedrock-builtin-subagent-403-fix` | 04-21 | [폴더](https://drive.google.com/drive/folders/1J3ecqUxImrnnnI0DL_pFHJBicELKm0hr) |

**매거진 활용 각도 후보**: "Bedrock에서 Claude Code 운영 시 만나는 403의 5가지 얼굴" — 단일 종합 기술 디프 기사. 주차 내 동일 slug가 3회 반복되므로 fact_checker로 차이를 구분 후 통합 가능.
**섹션 후보**: 운영 트러블슈팅
**검증 필수**: AWS 공식 IAM·Bedrock 문서 cross-check (Drive 본문 단독 채택 금지)

### Cluster B — `bedrock-opus47-endpoint` (★★★)

Bedrock 경유로 Opus 4.7을 호출하는 LangChain·Mantle·Anthropic endpoint 운영 노하우.

| source_id | 일자 | 링크 |
|---|---|---|
| `sns-blog-20260417-bedrock-mantle-langchain-opus` | 04-17 | [폴더](https://drive.google.com/drive/folders/1koYn7wbqL5BF_j9H68Omhk3WaIPnd89r) |
| `sns-blog-20260417-bedrock-mantle-langchain-opus47` | 04-17 | [폴더](https://drive.google.com/drive/folders/1_AYCnZg7CPFp_YBqJtPLrqaHSBI_Zcb-) |
| `sns-blog-20260420-bedrock-mantle-langchain-opus47` | 04-20 | [폴더](https://drive.google.com/drive/folders/1NNfnfBe6jzCujbDxjjgA0iQeO5VcInuq) |
| `sns-blog-20260421-bedrock-mantle-anthropic-endpoint-opus47` | 04-21 | [폴더](https://drive.google.com/drive/folders/1nKnSg2HgPi8kzwXqoC8zhGaZW2Fak0FC) |

**매거진 활용 각도 후보**: "Opus 4.7을 Bedrock·Anthropic 양쪽으로 붙이는 운영 패턴" — 라우팅·비용·지연 비교 기사.
**섹션 후보**: 기술 디프 / 운영 의사결정
**검증 필수**: Anthropic 공식 모델 명세(`claude-opus-4-7`) — CLAUDE.md 모델 배치 규칙과 모순 없는지 확인

### Cluster C — `claude-code-multi-agent` (★★)

Claude Code 멀티에이전트 실전 운영(권한 우선순위·토큰 절약 포함).

| source_id | 일자 | 링크 |
|---|---|---|
| `sns-blog-20260416-claude-code-allow-deny-priority` | 04-16 | [폴더](https://drive.google.com/drive/folders/1zL0VIm1-6Q3WZQpNZUEcb6O9n01Ur9ds) |
| `sns-blog-20260417-claude-code-multi-agent-practice` | 04-17 | [폴더](https://drive.google.com/drive/folders/1O5rufsuJPtuRwdIptcW-HLUBBAA8hl5c) |
| `sns-blog-20260417-claude-code-token-saving-tips` | 04-17 | [폴더](https://drive.google.com/drive/folders/1JXGxAzAQ0Twnsdc6wZlYNmzZ--LwcwJA) |
| `sns-blog-20260420-claude-code-multi-agent-practice` | 04-20 | [폴더](https://drive.google.com/drive/folders/1Mafoucl29kOej-CC2k7_3XrXzi3_Yx9y) |
| `sns-blog-20260421-claude-code-multi-agent-practice` | 04-21 | [폴더](https://drive.google.com/drive/folders/14fc7EqJ4lggBZcz_CPw5bjuhG--H1re2) |

**매거진 활용 각도 후보**: "Claude Code 멀티에이전트, 권한·토큰·세션을 묶어 보는 운영 가이드" — 본 매거진 정체성과 직접 정합.
**섹션 후보**: 커버 스토리 후보
**비고**: 동일 slug가 3회 반복 → 누적 학습이 있을 가능성. 편집자가 어느 회차를 정본으로 삼을지 선택 필요.

### Cluster D — `autofix-pr-review` (★)

Autofix·PR 자동 리뷰 자동화. 2일치만 등장 — 단일 사이드바 기사 또는 인포그래픽 후보.

| source_id | 일자 | 링크 |
|---|---|---|
| `sns-blog-20260415-autofix-pr-review-automation` | 04-15 | [폴더](https://drive.google.com/drive/folders/1qYv0v7EmUSTsiMO-Nw551yBWvdxd1Zoa) |
| `sns-blog-20260416-autofix-pr-auto-review-fix` | 04-16 | [폴더](https://drive.google.com/drive/folders/1TvwYE_MZ-35-U1myOL8Vr7I3HQQHQ_RD) |

**매거진 활용 각도 후보**: 사이드바 박스 또는 SNS 카드뉴스 재가공.
**섹션 후보**: 부록 / SNS 채널

### Cluster E — `drawio-skill-aws` (단발)

Drawio Skill로 AWS 아키텍처를 그리는 사례. 클러스터링 임계 미달이지만 매거진 "Skill 활용" 코너 단발 기사로 적합.

| source_id | 일자 | 링크 |
|---|---|---|
| `sns-blog-20260415-drawio-skill-aws-architecture` | 04-15 | [폴더](https://drive.google.com/drive/folders/1_YlCMVyGZFbSVuj8lGpq83CalMD60W-G) |

**매거진 활용 각도 후보**: "이번 달의 Skill" 코너 단발 한 꼭지.
**섹션 후보**: Skill 살펴보기

---

## 2. 카드뉴스 5덱 — SNS 채널 재가공 후보 풀

블로그와 같은 날 발행되므로 위 클러스터의 시각 자산 후보로 매핑된다. 본 디제스트는 **메타데이터만** 보유 — 카드 본문(텍스트)은 매거진 발행 직전 편집자가 Drive에서 직접 검수.

| 일자 | 카드 수 | 1번 카드 링크 | 추정 매핑 클러스터 |
|---|---|---|---|
| 2026-04-15 | 7장 | [card_01.png](https://drive.google.com/file/d/1F6WBvWxYKqKNyVjMSGBmydQ65TKW8kEl/view) | A 또는 C 추정 (편집자 확인) |
| 2026-04-16 | 6장 | [card_01.png](https://drive.google.com/file/d/15beOAixK611axI7A7zjyOWoWpLoC5aRr/view) | A 또는 C 추정 |
| 2026-04-17 | 6장 | [card_01.png](https://drive.google.com/file/d/1yVQn9tJjbECViwoMCu9c2yIOng2L0UxJ/view) | B 또는 C 추정 |
| 2026-04-20 | 6장 | [card_01.png](https://drive.google.com/file/d/15x5rgGMturLa_fQzruCmkGb17mx20VlT/view) | A·B·C 중 |
| 2026-04-21 | 7장 | [card_01.png](https://drive.google.com/file/d/1NATJmnZ0n2Up_CCV2aimd3rJZtEQTG73/view) | A·B·C 중 |

> 카드뉴스 PNG를 매거진 `web/public/`로 복사하려면 Gate 2 단계에서 라이선스·게재 경로를 PR에 명기.

---

## 3. 갭 분석 — 7일치에 빠진 매거진 관점 주제

본 주차 SNS 산출물은 **AWS Bedrock × Claude Code 운영 트러블슈팅**에 강하게 편중. 매거진 폭을 유지하려면 다음 주제를 brief_generator에 별도로 입력하길 제안.

| 갭 영역 | 점검 결과 | 신규 brief 제안 |
|---|---|---|
| 비개발자 페르소나 | 0건 — 전부 개발자 운영 글 | "Cowork로 매거진 SOP를 운영한 한 달" 본인 사례 |
| 거버넌스·법무 | 0건 | "AI 기본법 시행 100일, 매체사가 점검할 5가지" — `docs/governance.md` 실전판 |
| 한국어 편집 품질 | 0건 | "한국어 매체에서 Claude를 쓰는 편집 가이드 v1" |
| 외부 생태계 비교 | 0건 — Anthropic 단독 시점 | "Claude Code vs. Cursor vs. Replit Agent — 운영자 시점 비교" |
| 도입 ROI·정량 사례 | 0건 | "Claude Max 구독 1팀 6개월 — API 비용 0원 운영기" (매거진 무료 발행 정책과 정합) |

위 항목은 모두 SNS 자료에 의존하지 않는 신규 기획. brief_generator 큐의 별도 라벨(`gap_analysis`)로 분리.

---

## 4. 매거진 본문 채택 시 필수 검증 (Gate 2 사전 체크)

본 디제스트가 Gate 1 승인을 받아도 다음은 발행 직전 다시 점검:

1. Cluster A·B는 AWS·Anthropic 공식 문서로 cross-check (운영 이슈는 외부 1차 소스 필수)
2. 동일 slug 반복(A 5회, B 4회, C 3회 동일 패턴)이 SNS 측 누적 학습 결과인지 단순 재발행인지 확인 — 정본 1건 채택
3. 카드뉴스 PNG는 매거진 web/public 복사본의 라이선스·경로를 PR에 기재
4. 모든 채택 source_id가 source_registry에 `rights_status: free`로 등록되었는지 확인
5. AI 보조 사용 고지 문구가 매거진 본문 하단에 노출되는지 확인
6. **카드뉴스 PNG 본문(텍스트)과 §2의 추정 매핑 클러스터가 실제로 일치하는지 확인** — §2 매핑은 슬러그·날짜 동시출현 휴리스틱이라 mismatch 가능

---

## 5. AI 사용 고지

본 디제스트는 Drive 메타데이터를 기반으로 Claude(`claude-sonnet-4-6` 클러스터링, `claude-opus-4-7` 갭 분석)의 보조를 받아 작성됐습니다. 본문은 모두 슬러그·폴더명 기반의 형식적 분류이며, Drive 블로그 본문은 본 디제스트 작성 단계에서 열람·복사하지 않았습니다.

---

## 변경 이력

- 2026-04-25: 시범 큐레이션 1회분 초안 (Cowork 자동 생성, 편집자 미승인 상태). 매거진 repo commit 시점에 정합 fix 2건 추가 — `source_registry_status: proposed` 헤더, Gate 2 체크 6번(카드뉴스 매핑 검증).
- 2026-04-26: Round 2.B Gate 1 결정 — 4 클러스터(A·B·C·E) approve, Cluster D(autofix-pr-review) hold, 갭 분석 5건 중 2건 5월 plan_issue 우선 후보 승격. approved 15건 source_id를 `data/source_registry.db`에 `rights_status=free` / `language=ko` / `article_id=monthly_digest_2026-04-W3`로 등록. 헤더 `source_registry_status: proposed → partial`.
