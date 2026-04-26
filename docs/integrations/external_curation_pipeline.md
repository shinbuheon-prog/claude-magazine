# 외부 다채널 큐레이션 파이프라인 (External Curation Pipeline)

매거진 80p 분량 도달과 발행 품질 향상을 위한 외부 채널 자동 수집·요약·큐레이션 SOP.
기존 SNS Drive(Cowork) 디제스트 SOP의 상위 통합 설계.

> **본 문서의 위치**: 운영 SOP. 자동 발행 스크립트가 아님. 모든 채택은 편집자 Gate 1 승인 필수.
> 상위: [CLAUDE.md](../../CLAUDE.md), [docs/source_policy.md](../source_policy.md)
> 자매: [docs/integrations/sns_to_magazine_pipeline.md](sns_to_magazine_pipeline.md)

---

## 1. 5계층 파이프라인 개요

```
[L1 수집]  ──→  [L2 필터]  ──→  [L3 요약]  ──→  [L4 큐레이션]  ──→  [L5 매거진 채택]
 RSS/소셜       Claude 키워드   Sonnet/Haiku    Opus 클러스터링   plan_issue 후보
 어댑터 7종     + 다양성 룰     + 인용 한도     + 갭 분석         + Gate 1 승인
```

각 계층은 idempotent + dry-run 옵션 제공. 운영 비용 점검을 위해 매 단계 entries_count·llm_tokens·api_calls 기록.

---

## 2. 채널별 어댑터 우선순위 (2026-04 기준 결정)

### 2-1. 채택 (자동 크롤링)

| 채널 | 어댑터 위치 | 라이선스 | 비용 | 우선순위 | 상태 |
|---|---|---|---|---|---|
| **Anthropic News** | `pipeline/source_ingester.py` (RSS) | RSS 자유 인용 | $0 | A | ✅ 운영 중 |
| **OpenAI Blog** | 동상 | RSS 자유 인용 | $0 | A | ✅ 운영 중 |
| **Google AI Blog** | 동상 | RSS 자유 인용 | $0 | A | ✅ 운영 중 |
| **Classmethod Korea Tech Blog** | RSS (자체 콘텐츠) | **자체 콘텐츠 — 풀 인용** | $0 | **A — 최우선** | ✅ 2026-04-26 추가 |
| KISA / 과기정통부 | 동상 (RSS) | 공공 | $0 | B | ✅ 운영 중 |
| TechCrunch AI | 동상 | RSS 자유 인용 | $0 | C | ✅ 운영 중 |
| **Hugging Face / Meta AI / DeepMind 공식** | RSS (`config/feeds.yml` 추가 예정) | RSS 자유 인용 | $0 | B | 📋 5월 PoC |
| **arXiv (cs.AI)** | 어댑터 신규 (Claude 키워드 필터 필수) | CC BY 4.0 | $0 | A | 📋 5월 PoC |
| **Hacker News** | 어댑터 신규 (Algolia API) | 댓글 fair use | $0 | B | 📋 5월 PoC (외부 OSS [santiagobasulto/python-hacker-news](https://github.com/santiagobasulto/python-hacker-news) 검토) |
| **Reddit** (r/ClaudeAI 등) | 어댑터 신규 (OAuth) | API ToS 준수 + 200자 인용 | $0 | B | 📋 5월 PoC ([dansholds/menshun](https://github.com/dansholds/menshun) Aho-Corasick 차용) |
| YouTube transcript | `baoyu-youtube-transcript` skill | YouTube ToS 회색 | $0 | C | ✅ skill 운영 중 |

### 2-2. 기각 (수동 큐레이션으로 대체)

| 채널 | 기각 사유 | 대안 |
|---|---|---|
| **X (Twitter)** | X ToS가 자동 크롤링을 명시 금지. Scweet/Twikit/Pnytter 모두 ToS 위반. IP ban + 법적 위험 + 무료 발행 정책의 신뢰성 침해 | 편집자가 중요 트윗 URL을 `data/manual_curation/x_urls_YYYY-MM.txt`에 저장 → `baoyu-url-to-markdown` skill로 변환 → source_registry 등록 |
| **Threads** | 공식 API 제한적, 비공식 우회는 X와 동일 위험 | Cowork SNS Drive 트랙(자매 시스템)이 이미 처리 중 — 중복 회피. 자매 시스템 SLA 회신 후 정합 검토 |

> **본 결정의 근거**: 매거진 운영 정책 3개 — (1) 무료 발행, (2) 인간 편집 책임, (3) 법적 신뢰성. 자동 크롤링이 ToS 위반인 채널은 매거진 신뢰도를 직접 훼손.

---

## 3. classmethodkr "Korea Spotlight" 코너 — 자체 콘텐츠 활용 SOP

### 3-1. 위치·정체성

- 매거진 카테고리: **Review** (3p) 또는 별도 신설 "Korea Spotlight" 코너
- 매거진 정체성과 100% 정합 (Claude·Cowork·MCP·비엔지니어 사례)
- 자체 콘텐츠 → 인용 한도·라이선스 부담 0
- **트래픽 유입 효과**: 매거진 본문에 블로그 링크 직접 노출 → classmethodkr 블로그 트래픽 + 매거진 권위 동시 강화

### 3-2. 큐레이션 흐름 (월 1회)

```
[1] RSS fetch         scripts/curate_classmethodkr_best.py
       ↓              → reports/classmethodkr_best_YYYY-MM.md
[2] 휴리스틱 점수     topic 가중치 (claude=5, anthropic=5, openclaw=4, cowork=4, mcp=4, ai=2, aws=1)
       ↓              + category 보너스 + 본인(편집장) 보너스 + 본문 충실도
[3] TOP N 선정         default 3건 (Review 3p에 맞춤)
       ↓
[4] 편집자 1줄 요약     원문 본문은 편집자가 블로그에서 직접 읽고 작성 (LLM 호출 0)
       ↓
[5] Gate 1 승인        editor_approval YAML 작성 → reports/ commit
       ↓
[6] plan_issue 등록    --slug korea-spotlight --category review --pages 3
       ↓
[7] 매거진 본문 생성    draft_writer가 본 보고서를 입력으로 채택
                       → "블로그에서 더 보기 →" 링크 박스 자동 삽입
```

### 3-3. 본인(편집장) 자가 홍보 표기 의무

- 편집장(Shin 부장) 본인 기고는 점수 보너스 +2 (description에 "Shin 부장" / "Shin부장" 매칭)
- 단, **본 코너 내에 "⭐ 편집장 기고" 배지 명시 표기 의무**
- 발행 시 매거진 governance.md "AI 사용 고지"와 같은 위치에 "본 코너 N건 중 M건은 편집장 본인 기고입니다" 1줄 고지

### 3-4. 트래픽 유입 측정 (선택)

- 매거진 PDF·Ghost 본문의 블로그 링크에 UTM 파라미터 부착 검토:
  `?utm_source=claude-magazine&utm_medium=korea-spotlight&utm_campaign=2026-05`
- 단, 자체 분석 도구가 없으므로 Naver Analytics 또는 Google Analytics가 블로그 측에 설정되어 있어야 측정 가능
- **5월 PoC에서는 UTM 미부착**, 6월 호부터 결정

---

## 4. L2 키워드 필터 — Claude 적합도 점수

### 4-1. 강 키워드 (각 항목 1+ 매칭 → 자동 채택)

| 키워드 | 가중치 | 비고 |
|---|---|---|
| `claude`, `anthropic` | 5 | 매거진 직결 |
| `constitutional ai`, `mcp`, `agent skill` | 4 | Anthropic 핵심 컨셉 |
| `sonnet 4`, `opus 4`, `haiku 4` | 4 | 모델 직접 언급 |
| `cowork`, `openclaw`, `claude code` | 4 | 매거진 정체성 |

### 4-2. 약 키워드 (2+ 동시 매칭 시 채택)

`llm`, `agent`, `tool use`, `rag`, `prompt`, `context`, `subagent`

### 4-3. 메타 키워드 (3+ 동시 매칭 + 강·약 키워드 1개 이상 시 채택)

`evaluation`, `benchmark`, `alignment`, `safety`, `policy`

### 4-4. 임계값

- 적합도 점수 ≥ 0.6 → 자동 등록 (`source_registry`)
- 0.3 ~ 0.6 → 보류 큐 (`data/curation_pending/`) → 편집자 수동 검토
- < 0.3 → 폐기 (state에만 기록)

`pipeline/keyword_filter.py` 신규 모듈 (5월 PoC). 알고리즘 효율화는 [dansholds/menshun](https://github.com/dansholds/menshun)의 Aho-Corasick 패턴 차용.

---

## 5. L3 자동 요약 — Sonnet/Haiku

| 단계 | 모델 | 입력 | 출력 컬럼 |
|---|---|---|---|
| 1차 1줄 요약 | **Haiku 4.5** | 제목 + 본문 첫 500자 | `source_registry.summary_oneliner` |
| 2차 3줄 요약 | **Sonnet 4.6** | 본문 전체 (인용 한도 200자 준수) | `source_registry.summary_3line` |
| 키 인용 추출 | **Sonnet 4.6** | 본문 전체 | `source_registry.key_quotes` (JSON list, 각 ≤ 200자) |

### 5-1. 비용

- 100건/주 × 평균 2K tokens × Haiku $0.80/M = **약 $0.16/주, 월 ~$0.64**
- Max 구독 경유 시 **$0**
- `audit_budget.py` cap 적용 — 월 $1 초과 시 차단

### 5-2. 인용 한도 자동 검증

- `key_quotes` 각 항목 길이 > 200자 ⇒ truncate + warning
- `pipeline/source_diversity.py`의 4 규칙(언어·관점·발행처·시효성)과 결합

### 5-3. 자체 콘텐츠 예외

- `rights_status: free` 인 source(예: classmethodkr)는 **풀 요약 가능** (200자 한도 미적용)
- `key_quotes`에 길이 제한 없음

---

## 6. L4 월간 통합 큐레이션

`pipeline/monthly_curator.py` (5월 PoC 신규):

```
입력: source_registry × 지난 30일 × claude_relevance ≥ 0.6
처리:
  1. 토픽·태그 1차 클러스터링 (TF-IDF 상위 N=20 토큰)
  2. Opus 4.7 의미적 그룹핑 (5~10 클러스터)
  3. 매거진 섹션(Cover Story / Deep Dive / Insight / Interview / Review) 매핑 후보 제시
  4. 갭 분석 (표준 80p 21꼭지 비교축)
출력: reports/monthly_external_digest_YYYY-MM.md (Cowork SNS 디제스트와 동일 형식)
```

Cowork SNS 디제스트 SOP([sns_to_magazine_pipeline.md](sns_to_magazine_pipeline.md)) §3-1·3-2와 **완전 호환**. 두 디제스트는 동일 Gate 1 승인 흐름.

---

## 7. L5 Gate 1 → plan_issue 자동 채택

기존 흐름 그대로:
- `editor_approval` YAML status `approved` 또는 `partial` → approved 클러스터의 source_id를 `plan_issue.py add-article` 호출에 자동 주입
- Gate 2: 기존 `publish-gate` skill 통합 실행

---

## 8. 외부 OSS 활용 결정 (2026-04-26 기준)

### 8-1. 채택

| OSS | 라이선스 | 활용 방식 | 매거진 기여 |
|---|---|---|---|
| **[HarrisHan/ai-daily-digest](https://github.com/HarrisHan/ai-daily-digest)** | (확인 후) | fork 후 feeds.yml 교체 + 한국어 출력 + source_registry hook | 5월 호 Insight 1꼭지 (3p) |
| **[seulee26/mckinsey-pptx](https://github.com/seulee26/mckinsey-pptx)** | MIT | 매거진 톤 테마 fork + 한국어 폰트 검증 + .pptx→PDF 변환 흐름 | 5월 호 Insight 2꼭지 (6p) + Review 1꼭지 (3p) = **9p** |
| **[santiagobasulto/python-hacker-news](https://github.com/santiagobasulto/python-hacker-news)** | (확인 후) | 그대로 import → `pipeline/ingesters/hackernews.py` | 5월 호 Insight 1꼭지 (3p) |
| **[dansholds/menshun](https://github.com/dansholds/menshun)** | (확인 후) | Aho-Corasick 알고리즘만 차용 → `pipeline/keyword_filter.py` | (간접) 모든 ingester 효율화 |
| **[camilleroux/tech-digest](https://github.com/camilleroux/tech-digest)** | (확인 후) | Skill 그대로 설치, 운영 신호 분석에 활용 | Editorial 보조 |

### 8-2. 참고만

| OSS | 활용 |
|---|---|
| **[jyoung105/future-slide-skill](https://github.com/jyoung105/future-slide-skill)** (Apache 2.0) | DESIGN.md 추출 로직 reference. backlog "design-extractor skill" 항목 구현 시 참조 |
| **[Percival-Labs/dialectic-digest](https://github.com/Percival-Labs/dialectic-digest)** | argument/counter-argument 패턴. Editorial 메타 분석 활용 가능 (6월 이후) |
| **[forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)** | CLAUDE.md 개선 가이드. 매거진 CLAUDE.md 보완 검토 |
| **[jimmc414/Kosmos](https://github.com/jimmc414/Kosmos)** | over-spec, arXiv 클라이언트 일부 차용 가능 |

### 8-3. 기각

- **Scweet / Twikit / Pnytter / ntscraper / TWINT** — X·Threads 자동 크롤링 기각 결정 (§ 2-2)

---

## 9. 5월 호 PoC 채택 범위 (B 균형)

| 작업 | 우선순위 | 작업량 | 5월 호 기여 |
|---|---|---|---|
| 1. classmethodkr feed + 베스트 큐레이터 | A (최우선) | ✅ 2026-04-26 완료 | Korea Spotlight 코너 3p |
| 2. mckinsey-pptx 한국어 폰트 검증 PoC | A (선결) | 1일 | (mckinsey 채택 전제) |
| 3. mckinsey-pptx fork + Insight 자동 생성 | B | 3~4일 | Insight 6p + Review 3p = 9p |
| 4. ai-daily-digest fork + 한국어 적용 | B | 2일 | Insight 1꼭지 3p |
| 5. HN ingester (santiagobasulto wrapper) | B | 1일 | Insight 1꼭지 (옵션) 3p |
| 6. arXiv ingester (자체 구현) | B | 1일 | Deep Dive 1꼭지 4p |
| 7. Reddit ingester (Menshun 알고리즘) | C | 2일 | Insight 1꼭지 (옵션) 3p |
| 8. monthly_curator.py + 외부 디제스트 통합 | C | 2일 | 디제스트 자동화 |

---

## 10. 5월 호 80p 도달 재시뮬레이션 (classmethodkr 포함)

| 카테고리 | 표준 | 자체 | mckinsey-pptx | ai-daily-digest | classmethodkr | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| Cover Story | 14 | 14 | — | — | — | **14** |
| Deep Dive | 24 | 16 | — | 4 (arXiv·anthropic) | — | **20** |
| Insight | 12 | 3 (Claude Max) | 6 (HN/Reddit + Anthropic 타임라인) | 3 (외부 디제스트) | — | **12** |
| Interview | 15 | 5 (Cowork SOP 자가) | — | — | — | **5** |
| Review | 9 | 3 (drawio Skill) | 3 (동종업계 비교) | — | **3 (Korea Spotlight)** | **9** |
| 운영 가시성 (W4 신규) | — | 4 (자가 사례) | — | — | — | **4** |
| 구조 페이지 | 6 | 6 | — | — | — | **6** |
| **합계** | **80** | **51** | **9** | **7** | **3** | **70p** |

→ **5월 호 도달 가능 분량 70p** (이전 67p에서 +3p, **classmethodkr Korea Spotlight 기여**).

### 10-1. 80p 도달 잔여 -10p 해소 옵션

| 옵션 | 추가 분량 | 부담 |
|---|---:|---|
| Interview 자가 인터뷰 1건 추가 (Claude Max 6개월 운영자 자기 인터뷰) | +5p | 낮음 |
| Insight KPI dashboard 1꼭지 (Anthropic 모델 출시 타임라인 시각화) | +3p | 낮음 (mckinsey-pptx 자동) |
| Editorial 확장 (창간호 인사 + 매거진 운영 모델 소개) | +2p | 낮음 |

→ 위 3개 모두 채택 시 **80p 정확 도달 가능**.

---

## 11. 운영 정책 정합성 점검표

| 정책 | 본 SOP 정합 |
|---|---|
| 무료 발행 | ✅ 모든 어댑터 OSS, LLM Max 구독 경유 시 $0 |
| 인간 편집 책임 | ✅ Gate 1·Gate 2 모두 편집자 명시 승인 |
| 외부 cross-check | ✅ Cluster A·B는 AWS·Anthropic 공식 문서 1차 소스 |
| 인용 한도 | ✅ `quote_limit: 200` + `key_quotes` 자동 truncate. 자체 콘텐츠 예외 |
| 라이선스 검증 | ✅ `rights_status` 필드 + RSS/CC BY 4.0/MIT/Apache 2.0 한정 |
| Korean 인코딩 | ✅ source_ingester UTF-8 강제. classmethodkr UTF-8 검증 완료 (2026-04-26) |
| Phase 마무리 직접 구현 | ✅ Phase 9 신규 TASK 명세 다수 추가 금지. 본 SOP는 직접 구현 PoC + 설계 문서만 |

---

## 13. Inside Classmethod 코너 — Sponsored Content 트랙

매거진 "Inside Classmethod" 코너(매호 5~7p, 본문 중간 분리 게재)는 발행사 그룹의 서비스·커뮤니티·이벤트를 소개하는 광고 코너입니다. [docs/governance.md](../governance.md) §"발행사·관계사 서비스 소개 코너 (Sponsored Content)" 6 의무 준수.

### 13-1. 콘텐츠 풀 3 트랙

| 트랙 | 출처 | 매거진 분량 |
|---|---|---|
| **A. 일본본사 Claude 컨설팅 서비스** | https://classmethod.jp/services/claude/ + 영업 자료 PDF | 3p (압축) |
| **B. 한국법인 회사 소개 + 이벤트** | 클래스메소드코리아 (35억+/50명, AWS·Claude 리셀링·컨설팅·오프쇼어) + 오프라인 밋업 운영 자료 | 2p |
| **C. Claude 관련 커뮤니티 안내** | 사외 (claudecode.co.kr, r/ClaudeAI, Anthropic Discord 등) + 사내 (클래스메소드코리아 Claude 밋업, DevelopersIO, Zenn) + 매거진 자체 (구독·GitHub) | 1~2p |

### 13-2. 표준 7p 구성 (5월 호 PoC)

| p | 내용 | 디자인 톤 | 광고 표기 |
|---|---|---|---|
| 1 | 코너 표지 — "Inside Classmethod" 브랜딩 + AD 배지 | 매거진 톤 (Noto Serif KR) | 우상단 "AD" 배지 + footer 1줄 고지 |
| 2 | 일본본사 ① 시장 진단 + 솔루션 (Claude 5제품) | 발행사 코퍼레이트 톤 (PDF 임베드) | 페이지 footer 1줄 |
| 3 | 일본본사 ② 차별화 + 신뢰성 (Anthropic 인증·1,000명 도입) | 동상 | 동상 |
| 4 | 일본본사 ③ 가격·서비스 (¥30,000/h·6 영역·Bedrock 단가표) + Korea 회사 소개 | 동상 | 동상 |
| 5 | 한국법인 — 회사 + 운영진 (박동현·신부헌) | 발행사 코퍼레이트 톤 | 동상 |
| 6 | 한국 Claude 오프라인 밋업 1회차 후기 + 다음 회차 안내 | 발행사 코퍼레이트 톤 | 동상 |
| 7 | Claude 관련 커뮤니티 안내 (사외 + 사내 + 매거진 자체) | 매거진 톤 | 동상 |

### 13-3. 한국 시장 적용 — 일본 본사 사례로 명시

일본본사 가격(¥30,000/h)·서비스는 한국 시장 동일 적용 보장 안 됨. 본 코너 footer에:
> "본 코너의 가격·서비스는 클래스메소드 일본 본사 기준입니다. 한국 시장 도입은 클래스메소드코리아 별도 문의(info@classmethod.kr)"

### 13-4. 콘텐츠 풀 갱신 주기

| 트랙 | 갱신 주기 | 다음 갱신 시점 |
|---|---|---|
| A 본사 서비스 | 분기 1회 (3·6·9·12월) | 2026-06 (Q2 자료) |
| B 한국법인·이벤트 | 이벤트 시점마다 | 2026-05 호 1회차 후기 (2025-04-23 개최) → 2회차 안내 |
| C 커뮤니티 안내 | 반기 1회 (1·7월) | 2026-07 호 갱신 |

### 13-5. 광고 비율 검증 (governance.md §6 의무)

| 호 | 발행 분량 | 광고 분량 | 비율 | 상한(10%) |
|---|---:|---:|---:|---|
| 2026-05 (Issue 1) | 80p | 7p | 8.75% | ✅ 준수 |
| 6월 이후 정기화 검토 시 | 80p | 5~7p | 6~9% | ✅ 가능 |

### 13-6. 정기화 결정 (5월 호 회고 후 결정 예정)

- **5월 호 1회만 운영**: Issue 1 발행 직후(6/01-6/03 회고 시점)에 정기화 여부 결정
- 정기화 시 6월 호부터 매호 5~7p 분량 정착, 콘텐츠 풀 갱신 주기(13-4) 준수
- 비정기화 시 다음 게재는 분기 1회 또는 신규 발행사 서비스 출시 시점

---

## 14. 변경 이력

- **2026-04-26**: 초안 작성. 5계층 파이프라인 + 채널별 어댑터 우선순위 + classmethodkr Korea Spotlight 코너 SOP + X·Threads 자동 크롤링 기각 정책 명문화. 5월 호 80p 도달 시뮬레이션 70p (Korea Spotlight +3p). [reports/classmethodkr_best_2026-04.md](../../reports/classmethodkr_best_2026-04.md) 시범 큐레이션 1회분 동시 생성.
- **2026-04-26 (2차)**: §13 "Inside Classmethod 코너" Sponsored Content 트랙 신규 추가. 일본본사 Claude 컨설팅 서비스 PDF + 클래스메소드코리아 회사·이벤트(2025-04-23 1회차 밋업) + Claude 커뮤니티 안내 통합 7p 구성. governance.md §"발행사·관계사 서비스 소개 코너" 6 의무 명문화. 5월 호 도달 분량 70p → **77p** (+7p).
