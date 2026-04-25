# SNS 일일 산출물 → 월간 매거진 큐레이션 SOP

코리아로컬팀 `SNS運営（Threads）` Drive 폴더에 매일 자동으로 적재되는 카드뉴스·블로그 초안을 매월 매거진 콘텐츠로 재가공할 때 따르는 운영 절차서.

> **본 문서의 위치**: 운영 SOP. 자동 발행 스크립트가 아님. 모든 단계의 결과물은 편집자 승인 후에만 매거진에 반영된다. (CLAUDE.md `편집 검수 체크리스트` 10개 항목 위에 얹히는 보조 절차)

---

## 1. 입력 — Drive 폴더 구조와 식별자 규칙

자동화 시스템이 매일 적재하는 표준 구조 (변경 시 본 SOP 갱신 필요):

```
SNS運営（Threads）/
├── 2026-MM-DD/
│   ├── 01_cardnews/
│   │   └── card_NN.png         ← 1일 1덱(평균 6~7장)
│   └── 02_blog/
│       └── article_N_<slug>/   ← 1일 N건(평균 3건)
└── _workspace/                  ← 참조 전용, 매거진 미사용
```

### source_id 명명 규칙

매거진 측 source_registry 등록 시 다음 형식을 강제:

| 종류 | source_id 패턴 | 예시 |
|---|---|---|
| 카드뉴스 덱 | `sns-cardnews-YYYYMMDD` | `sns-cardnews-20260415` |
| 카드뉴스 개별 장면 | `sns-cardnews-YYYYMMDD-NN` | `sns-cardnews-20260415-03` |
| 블로그 단일 글 | `sns-blog-YYYYMMDD-<slug>` | `sns-blog-20260415-bedrock-subagent-403-fix` |

`<slug>`는 Drive 폴더명에서 `article_N_` 접두사를 제거한 부분을 그대로 사용 (대소문자·하이픈 보존).

### rights_status 기본값

`SNS運営（Threads）` 산하 산출물은 사내 자동화로 생성된 1차 자산이므로 `free` (사내 권리). 외부 인용·캡처가 포함된 경우 편집자가 `restricted`로 다운그레이드.

---

## 2. 처리 모드 — 참조만 (Drive 본문 무단 복사 금지)

본 파이프라인은 **메타데이터 + 링크 참조**만 매거진 repo에 들인다.

| 자료 | 매거진 측 처리 |
|---|---|
| Drive 카드뉴스 PNG | source_registry에 viewUrl만 등록. 매거진 web/public 복사는 발행 직전 편집자 승인 후. |
| Drive 블로그 본문 | source_registry에 viewUrl·제목·요약(편집자 작성)만 등록. 본문 캐시 금지. |
| `_workspace/scripts/` | 코드 자동 import 금지 (CLAUDE.md 금기 사항). 갭 분석 참조용에 한함. |

> **금지 사례**: Drive 블로그 본문을 매거진 `drafts/`에 복사 → channel_rewriter에 그대로 투입. 이는 원문 대체형 침해(`docs/source_policy.md`)에 해당.

---

## 3. 집계 단위 — 주제·태그 클러스터링 + 갭 분석

월간 매거진의 한 섹션을 채우는 단위로 묶을 때 다음 두 축을 동시에 본다.

### 3-1. 주제·태그 클러스터링

Drive 폴더명(slug)에서 토큰을 추출해 1차 클러스터를 만든다. 추출 규칙:

1. `_`, `-`로 split → 토큰 리스트 확보
2. 불용어 제거: `article`, `fix`, `tips` 등 일반 동사·접미사
3. 기술 키워드 매핑 (예: `bedrock`, `claude-code`, `langchain`, `opus`, `subagent`)
4. 토큰 동시출현 빈도 ≥ 2이면 1개 클러스터로 승격

각 클러스터는 다음 필드를 채워 매거진 편집자에게 제출:

```yaml
cluster_id: bedrock-permission-403
days_covered: [2026-04-15, 2026-04-16, 2026-04-17, 2026-04-20, 2026-04-21]
source_ids:
  - sns-blog-20260415-bedrock-subagent-403-fix
  - sns-blog-20260420-bedrock-inference-profile-403-fix
  - ...
proposed_angle: <편집자 작성용 빈칸>
magazine_section_candidate: 운영 트러블슈팅 / 기술 디프 / 등
```

### 3-2. 갭 분석 (다루지 못한 주제)

매거진 편집 방향과 비교해 SNS 산출물이 다루지 않은 영역을 추려낸다. 고정 비교 축:

| 비교 축 | 점검 질문 |
|---|---|
| 사용자 페르소나 | 비개발자·관리직 사례가 빠지지 않았나 |
| 거버넌스 | AI 기본법·프라이버시·라이선스 주제 누락 여부 |
| 외부 생태계 | Anthropic 외 도구(Cursor, Replit, Cowork 등) 비교 누락 여부 |
| 한국어 편집 품질 | 번역 품질·국내 사례 부재 여부 |
| 도입 ROI | 정량 사례·비용 효과 부재 여부 |

갭 항목은 매거진 brief_generator에 별도 brief 후보로 입력 (Drive 산출물에 의존하지 않는 신규 기획 주제로 분류).

---

## 4. 승인 게이트 — 2단계

자동화는 디제스트 생성·소스 등록까지만 수행. 발행 결정은 두 번 사람이 끊는다.

### Gate 1 — 월간 디제스트 승인 (매월 25일 전후)

대상: `reports/monthly_digest_YYYY-MM-WN.md` (주차별) 또는 `reports/monthly_digest_YYYY-MM.md` (월말 종합)

편집자 점검 항목:

- [ ] 클러스터링 결과가 매거진 편집 방향과 정합한가
- [ ] source_id가 모두 source_registry에 등록되었는가 (`rights_status` 누락 0건)
- [ ] 갭 분석 후보가 신규 brief 큐로 분리되었는가
- [ ] 본문 무단 복사 흔적이 없는가 (메타데이터·링크만)
- [ ] AI 사용 고지가 디제스트 본문에 포함되었는가

승인 결과는 디제스트 파일 상단 `editor_approval` 블록에 서명·일자 기재. 미승인 항목은 클러스터 단위 또는 source_id 단위로 reject 표시.

### Gate 2 — 발행 직전 (매거진 PDF·Ghost 송고 직전)

대상: 디제스트에서 채택된 클러스터를 brief_generator → draft_writer → fact_checker로 돌린 결과물.

편집자 점검 항목 (CLAUDE.md 10개 체크리스트 위에 추가):

- [ ] Drive 원본의 카드뉴스 이미지·블로그 표현을 매거진 본문이 그대로 베끼지 않았는가 (해설·재구성 중심)
- [ ] Drive 산출물의 사실관계가 외부 1차 출처(공식 문서·릴리스 노트)로 재검증되었는가 — Bedrock 403 같은 운영 이슈는 AWS 공식 문서로 cross-check 필수
- [ ] 카드뉴스 PNG를 매거진에 게재하는 경우 `web/public/`로 복사한 정확한 경로가 PR 설명에 기록되었는가
- [ ] 매거진 발행본 하단에 SNS 원본 링크와 작성 일자가 노출되었는가

Gate 2 미통과 시 클러스터 단위로 발행 보류. 부분 발행 금지 (출처 일관성 유지).

---

## 5. 매월 운영 캘린더 (편집자 기준)

| D-day | 행위 | 산출물 | 책임 |
|---|---|---|---|
| 매일 자동 | Drive 일일 폴더 적재 | `2026-MM-DD/01_cardnews/`, `02_blog/` | 자매 시스템(자동) |
| 매주 일요일 | 주차 디제스트 초안 생성 | `reports/monthly_digest_YYYY-MM-WN.md` | Cowork(보조) |
| 월말 5일 전 | 주차 디제스트 통합·갭 분석 | `reports/monthly_digest_YYYY-MM.md` | 편집자 |
| 월말 3일 전 | **Gate 1 승인** | 디제스트 상단 승인 블록 | 편집자 |
| 월말 2일 전 | brief→draft→factcheck 실행 | `drafts/`, `logs/` | 편집자 + Codex |
| 월말 1일 전 | **Gate 2 승인** + 채널 재가공 | PR + Ghost 초안 | 편집자 |
| 월 1일 | 발행 (편집자 수동 트리거) | 매거진 PDF + Ghost 게시 | 편집자 |

---

## 6. AI 사용 고지

본 SOP에 따라 생성되는 모든 디제스트·brief 후보는 Claude(`claude-sonnet-4-6` 클러스터링, `claude-opus-4-7` 갭 분석, `claude-haiku-4-5-20251001` 태깅)의 보조를 받는다. `docs/governance.md` AI 고지 기준에 따라 매거진 발행본 하단에 "본 기사 기획 단계에서 AI 보조 분석을 사용했습니다"를 노출한다.

---

## 7. 관련 문서

- `docs/editorial_checklist.md` — 발행 전 10개 필수 체크
- `docs/source_policy.md` — rights_status·인용 한도
- `docs/governance.md` — AI 고지·개인정보 처리
- `CLAUDE.md` — 모델 배치 규칙·코딩 규칙

---

## 변경 이력

- 2026-04-25: 초안. 사용자 응답(참조만, 주제·태그 클러스터링 + 갭 분석, 2단계 승인) 기반으로 작성. 이후 변경은 commit 메시지에 사유 명기.
