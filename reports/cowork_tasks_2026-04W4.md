# Cowork 작업 요청 패키지 (2026-04 W4 → 5월 호 발행 사이클 시작 전)

**대상**: 사용자(편집장)가 Cowork 외부 시스템에 직접 입력하는 4건 작업
**시점**: 2026-04-27 ~ 2026-05-03 EOD
**목적**: 5/04 plan_issue init 시점에 모든 입력 자료 + 응답 확보

---

## Cowork-1: Round 2.D 자매 시스템 회신 (응답 기한 2026-04-29 EOD)

```
SNS運営（Threads） 자동화 W4 (2026-04-22·23·24) 평일 3일 0건 적재 사유 확인 부탁합니다.

확인 사항:
1. 시스템 다운인지 정책 변경인지
2. 차주(W5, 04-29 이후)부터 자동화 정상 가동 여부
3. 결락 일자 사후 보강 여부 (있다면 일자 명시)

응답 결과는 reports/sns_automation_w4_response.md로 매거진 저장소에 저장 부탁드립니다.
이 결과는 5월 호 Deep Dive #4 (Cowork·Claude Code 자동화 SLA 자가 사례)의 데이터로 활용됩니다.

응답 기한: 2026-04-29 EOD
담당: 코리아로컬팀 자동화 운영자
```

---

## Cowork-2: 5월 W1 SNS 디제스트 (2026-05-03 ~ 2026-05-04)

```
2026-04-29 ~ 05-05 W1 디제스트를 W3·W4와 동일 SOP로 생성 부탁합니다.

설계 결정 (W3·W4와 동일):
1. 산출물: 운영 SOP 체크리스트 + 시범 큐레이션
2. 집계: 주제·태그 클러스터링 + 갭 분석
3. Drive 자료: 참조만 (메타데이터 + 링크)
4. 편집자 승인 게이트: 2단계

저장 위치: reports/monthly_digest_2026-05-W1.md

W4 비교 분석 추가 요구:
- W4 0건 anomaly 회복 여부
- W3·W4·W5 클러스터 연속성 (bedrock-403·multi-agent 등)
- 5월 호 Issue 1 발행 직전 W1 시점 SNS 운영 정상성

source_id 명명: docs/integrations/sns_to_magazine_pipeline.md §1 따라
source_registry_status: proposed (Gate 1 미승인)
Gate 2 사전 체크 6건 첨부.
AI 사용 고지 명시.
```

---

## Cowork-3: classmethodkr 5월 1주 베스트 기고 (2026-05-05 ~ 2026-05-06)

```
classmethodkr 기술블로그 2026-05-01 ~ 05-07 기고 중 베스트 5건 큐레이션 부탁합니다.

기준 (4월 시범과 동일):
- claude·anthropic·openclaw·cowork·mcp 키워드 가중치
- 카테고리 Claude/AI 우선
- 본문 충실도 (description 길이)

저장 위치: reports/classmethodkr_best_2026-05-W1.md
형식: 4월 시범 (reports/classmethodkr_best_2026-04.md) 그대로

매거진 5월 호 Korea Spotlight 코너 (Review 3p)의 데이터 보강용입니다.
4월 14건 + 5월 W1 가산 = TOP 3~5 재선정 가능.
```

---

## Cowork-4: 5월 호 테마 1줄 결정 의견 (2026-05-03 EOD)

```
2026-05-31 발행 1호(Issue 1) 매거진 테마를 1줄로 결정하려고 합니다. 다음 3 후보 중 1건 선택 또는 새 안 제시 부탁합니다.

후보 A) "Claude 운영체계의 한 해 — 발행에서 정착까지" (창간호 정체성 강조)
후보 B) "Bedrock × Claude Code — 2026 봄의 운영 풍경" (W3 SNS 자료 정합)
후보 C) "AI 에이전트 시대의 매거진 — 자가 운영 사례로 시작하다" (자가 사례 비중)
후보 D) (새 안 제시)

선택 사유 1~2 문장 첨부 부탁합니다.
이 결정이 5/04 plan_issue.py init --theme 입력 필수.
```

---

## 일정 요약

| 일자 | Cowork 입력 | 응답 기한 | 매거진 시스템 활용 시점 |
|---|---|---|---|
| 2026-04-27 (월) | Cowork-1 (자매 시스템 회신) | 04-29 EOD | 5월 호 Deep Dive #4 brief 입력 |
| 2026-04-29 (수) | Cowork-4 (테마 결정 의견) | 05-03 EOD | 5/04 plan_issue init |
| 2026-05-03 (토) | Cowork-2 (W1 디제스트) | 05-04 09:00 | 5월 호 보강 source 등록 |
| 2026-05-05 (월) | Cowork-3 (5월 W1 베스트) | 05-06 EOD | Korea Spotlight 코너 보강 |

---

## 변경 이력

- 2026-04-27: 초안 작성. 5/04 plan_issue init 시점까지 4건 응답 확보 목표.
