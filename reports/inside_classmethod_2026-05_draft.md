# Inside Classmethod — 2026-05호 초안 (Sponsored Content, 7p)

**코너 정체**: Sponsored Content (발행사 클래스메소드 그룹·관계사·사내 커뮤니티 소개)
**분량**: 7p (매거진 80p 중 8.75%, governance.md §"Sponsored Content" 10% 상한 ✅)
**위치**: 본문 중간 분리 게재 (예: Insight 코너 직후 / Review 코너 직전)
**광고 표기**: 매 페이지 우상단 "AD" 배지 + 첫 페이지 footer 1줄 고지
**디자인 톤**: 하이브리드 — 표지·커뮤니티 안내(p1·p7) 매거진 톤 / 본문(p2~p6) 발행사 코퍼레이트 톤
**근거**: [docs/governance.md](../docs/governance.md), [docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §13

> 본 파일은 매거진 발행 본문이 아닌 **편집장 작성 가이드용 초안**입니다. 실제 본문은 5월 1주차 plan_issue 단계에서 brief_generator + 편집자 수동 보강으로 생성.

---

## editor_approval (Inside Classmethod Gate)

```yaml
status: pending           # pending | approved | rejected | partial
reviewer: <편집자 서명>
reviewed_at: <YYYY-MM-DDTHH:MM+09:00>
notes: |
  - 7p 구성안 채택 여부:
      [ ] 그대로 7p / [ ] 5p로 압축 / [ ] 8p로 확장
  - 한국 시장 적용 옵션:
      [x] 일본 본사 사례로 명시 (기본) / [ ] 한국 가격·서비스로 변환 (한국 가격 정보 추가 필요)
  - 광고 표기 라벨:
      [x] "AD" 배지 + 코너명 "Inside Classmethod" / [ ] 변경
  - 디자인 톤:
      [x] 하이브리드 (표지·커뮤니티는 매거진 톤 / 본문은 발행사 톤) / [ ] 전부 매거진 톤 / [ ] 전부 발행사 톤
  - 정기화 결정 (5월 호 회고 후):
      [ ] 정기 매호 5~7p / [ ] 분기 1회 / [ ] 비정기
  - Claude 밋업 사진 사용:
      [ ] 첨부 (사용자가 별도 제공) / [ ] 미사용 (텍스트만)
```

---

## Page 1 — 코너 표지 (매거진 톤)

**우상단**: "AD" 배지 + "Inside Classmethod" 코너명
**제목**: "Inside Classmethod — Claude 도입과 커뮤니티"
**부제**: "발행사가 직접 운영하는 Claude 생태계: 일본 본사의 컨설팅 서비스부터 한국의 오프라인 밋업까지"
**Footer 1줄 고지**: "본 코너는 발행사 클래스메소드 그룹과 관계사·사내 커뮤니티 활동 소개입니다. 본 코너의 가격·서비스는 클래스메소드 일본 본사 기준입니다. 한국 시장 도입은 클래스메소드코리아 별도 문의(info@classmethod.kr)"

**Hero 카피 (편집자 작성 대기)**:
> _"매거진을 만드는 사람들이 어떤 회사인지, 그리고 우리가 어떤 Claude 활동을 하고 있는지 직접 보여드립니다."_

---

## Page 2 — 일본본사 ① 시장 진단 + 솔루션 (발행사 톤)

**출처**: 영업 자료 PDF p3 課題 + p4 Why Now + p6 솔루션 6제품

### 시장 진단 (좌측 1/3)
- **PoC의 72%가 본번화 못함** — 다수 기업이 직면하는 3대 벽
  - 도구 5+ 난립으로 통제 불가
  - 35% 실이용률 — 현장 정착 실패
- **일경225 94%가 Copilot 도입 완료** (Microsoft AI Tour Tokyo 2026.3 출처)
- **국내(일본) AI 시장 4.2조 엔 규모로** (3년 이내)
- **Anthropic 엔터프라이즈 기능 정비**: 2024 MCP / 2025 Skills+Cowork / 2026 Agent SDK+Teams

### Claude 5제품군 (우측 2/3)
| 제품 | 대상 | 용도 |
|---|---|---|
| Claude.ai | 전 사원 | 채팅·문서·분석·코드 |
| Claude Code | 개발자 | CLI 자율 코드 생성·리뷰·테스트 |
| Cowork | 비엔지니어 | 파일·데이터·태스크 자동화 (대화형) |
| Claude in Chrome (Beta) | 브라우저 | 정보 정리·요약 실시간 |
| Claude for Excel/PPTX | Office | 데이터 분석·자료 작성 |
| Claude Mobile | 외출 | 음성 입력 대응 |

---

## Page 3 — 일본본사 ② 차별화 + 신뢰성 (발행사 톤)

**출처**: 영업 자료 PDF p9 차별화 + p16 신뢰성

### 하네스 엔지니어링 = 업무 품질의 원천 (좌측)
> "비결정론적 LLM을 결정론적 업무 도구로 변환"

| 4 구성요소 | 역할 |
|---|---|
| CLAUDE.md | 프로젝트별 지시·제약 정의 |
| MCP | 외부 도구 표준 접속 프로토콜 |
| Skills | 업무별 전문 지식 패키지 |
| System Prompts | 출력 품질·형식 조직 통제 |

### 신뢰성 4축 (우측)
- **Anthropic 인증 리셀러** (2026.03 계약 체결) — AWS 지원 실적 4,000+사 노하우 활용
- **AWS Premier Tier Partner (아시아 Top Tier)** — 35,000+ 기술 지원 실적, Bedrock 폐쇄망 대응
- **자사 1,000명 Claude 전사 도입** — 사내 최다 활용 회사가 직접 지원
- **엔지니어 집단의 기술적 깊이** — 표면적 도구 도입이 아닌 아키텍처 레벨 최적화

---

## Page 4 — 일본본사 ③ 가격·서비스 + Bedrock 단가 (발행사 톤)

**출처**: 영업 자료 PDF p12 서비스 + p15 가격 + p20 Appendix Bedrock 단가

### 6 서비스 영역
1. **AI 활용 전략·기획 입안** (전략 / PoC 설계)
2. **도입 지원·각종 설정** (Bedrock / 인프라 설계)
3. **수탁 개발·시스템 구축** (RAG / 에이전트 / MCP)
4. **교육 연수·조직 전개** (연수 / 핸즈온)
5. **시스템 통합** (연계 개발 / 자동화)
6. **문의 지원·정보시스템 운영 대행** (운영 대행 / 지원)

### 가격 (일본 본사 기준)
- **¥30,000/시간 (세별)** | 최소 계약 시간 없음 | 월 단위 조정 | 실적 정산
- **추천 플랜 (Standard)**: 월 20시간 = **¥600,000/월** (도입 지원 + 온보딩)

### Bedrock API 단가 (참고)
| 모델 | 입력 / 1M tokens | 출력 / 1M tokens |
|---|---:|---:|
| Haiku 4.5 | $1 | $5 |
| Sonnet 4.6 | $3 | $15 |
| Opus 4.6 | $3.5 | $35 |

> Footer: "한국 시장 도입은 별도 가격·서비스 체계 적용. 클래스메소드코리아 문의."

---

## Page 5 — 클래스메소드코리아 회사 소개 + 운영진 (발행사 톤)

**출처**: 한국 밋업 자료 PDF p4 ABOUT US + p5·p6 운영진

### About Classmethod Korea
| 항목 | 내용 |
|---|---|
| 설립 | 2021년 |
| 매출 | 35억+ |
| 직원수 | 50명 |
| 사업영역 | AWS 리셀링·컨설팅 / Claude 리셀링·컨설팅 / 오프쇼어 비즈니스(일본인재 파견) |
| 본사와의 관계 | Classmethod, Inc.(2004 설립, 1조+ 매출, 1,000명, 6국 해외법인) 한국 법인 |

### 운영진 2인
| 이름 | 직책 | 배경 |
|---|---|---|
| **박동현** | Founding Member, HR·법인운영 총괄 | 일본 사이타마 거주 / Team J-Curve 일본 담당 / 한일 커뮤니티 "재팬인서울" 운영 / KOTRA 일본취업 어드바이저 / Threads 3.9k+ / LinkedIn 4.8k+ |
| **신부헌** | 영업·신규 비즈니스 (편집장) | 서울 송파구 거주 / 일본 거주 10년(도쿄·요코하마) / 유니클로 점장·풀무원·금호전기 IT계열사 일본담당·전문무역상사 일본 채널 세일즈 |

> Footer: "본 매거진의 편집장(신부헌)은 클래스메소드코리아 영업·신규 비즈니스 담당입니다. 본 코너는 발행사 자체 소개로 편집장 본인 소속을 명시합니다."

---

## Page 6 — 한국 Claude 오프라인 밋업 (발행사 톤)

**출처**: 한국 밋업 자료 PDF p1·p2·p7·p8

### 1회차 — 2025-04-23 (목) 18:00-21:00
- **장소**: 강남역 3분, 모임공간 세모네모
- **테마**: Classmethod Korea × Claude
- **식순**: 입장·웰컴(30분) → 오프닝(10분) → 피치 세션(30분, 5분×6) → 네트워킹·식사 피자&맥주(90분) → 만족도 조사(20분)

### 1회차 피치 세션 발표자 6 회사
| 회사 | 발표자 |
|---|---|
| 룸821 | 강정석 대표 |
| 코스콤 | 정경석 차장 |
| 대충영어 | 오승종 대표 |
| 스페시아이(Speciai) | 조사랑 대표 |
| 한국AI기술협회 | 박동혁 R&D기술교류위원장 |
| 엘리오앤컴퍼니 | 이의정 시니어플래너 |

### (사진 1~2장 별도 첨부 가능 — 사용자가 제공 시 추가)
> 추후 사용자가 1회차 현장 사진 1~2장 첨부 시 본 페이지에 임베드. 외부 공개 콘텐츠는 얼굴 블러 처리 (밋업 운영 정책에 따름).

### 다음 회차 안내 (편집자 작성 대기)
> **2회차 — (TBD)**: _<일자·장소·테마 결정 시 채움>_
> 운영 채널 안내: _<카카오톡 오픈채팅 / 이메일 / festa.io 등 결정 시 채움>_

---

## Page 7 — Claude 관련 커뮤니티 안내 (매거진 톤)

본 코너는 광고가 아닌 **커뮤니티 안내** ([docs/governance.md](../docs/governance.md) §"예외 사항"). 단 발행사 주최 커뮤니티(클래스메소드코리아 Claude 밋업)는 광고 코너로 분류해 위 p6에 게재.

### 사외 공식·반공식 커뮤니티

| 커뮤니티 | URL | 비고 |
|---|---|---|
| **Claude Code Korea** | https://www.claudecode.co.kr/ | 한국 사용자 뉴스레터·포스트 |
| **r/ClaudeAI** | https://reddit.com/r/ClaudeAI | 영문권 최대 Reddit 커뮤니티 |
| **Anthropic Discord (공식)** | (Anthropic 공식 채널 연결 시 추가) | 글로벌 공식 |
| **Claude Code Channels (Telegram·Discord)** | Anthropic 2026.03 리서치 프리뷰 | Claude Code 세션 원격 조작 |

### 사내 발행 채널

| 채널 | URL | 발행 빈도 |
|---|---|---|
| **DevelopersIO** (일본) | https://dev.classmethod.jp/ | 일 단위 |
| **Zenn** (일본, Classmethod 소속) | https://zenn.dev/ (5만+ 사용자) | 일 단위 |
| **Classmethod Korea Tech Blog** (한국) | https://blog.naver.com/classmethodkr | 주 3~5건 |

### 매거진 자체 채널

| 채널 | URL | 사용자 액션 |
|---|---|---|
| **Claude Magazine 무료 구독** | (구독 페이지 URL — 발행 시점 확정) | 이메일 입력 → 즉시 구독 |
| **GitHub 이슈** | https://github.com/shinbuheon-prog/claude-magazine | 버그 리포트·기능 제안 |
| **편집자 직접 연락** | docs/governance.md 정정·기여 정책 참조 | 콘텐츠 제안·정정 요청 |

### 매거진 다음 호 안내 (편집자 작성)
> **2026-06호 (Issue 2)**: _<6월 호 테마·주요 코너 결정 시 채움>_

---

## 매거진 코너 채택 후 다음 단계

1. 편집자가 위 `editor_approval` YAML을 `approved`로 갱신
2. plan_issue.py에 본 코너 등록:
   ```bash
   python scripts/plan_issue.py add-article --month 2026-05 \
       --slug inside-classmethod --category review --pages 7 \
       --title "Inside Classmethod — Claude 도입과 커뮤니티"
   ```
3. brief_generator + draft_writer가 본 초안을 입력으로 채택
4. publish-gate skill의 표준 체크리스트에 "Sponsored Content 6 의무 준수 확인" 추가 ([docs/governance.md](../docs/governance.md) §"검증")
5. Colophon에 "본 호 광고 페이지 7건 (P페이지)" 1줄 표기
6. Issue 1 발행 후(6/01-6/03) 회고에서 정기화 여부 결정 ([docs/integrations/external_curation_pipeline.md](../docs/integrations/external_curation_pipeline.md) §13-6)

---

## AI 사용 고지

본 코너 초안은 (1) 사용자 제공 PDF 자료 2건(일본본사 Claude 서비스 소개 20p + 한국 밋업 자료 10p), (2) 본사 공식 페이지(https://classmethod.jp/services/claude/) WebFetch 1회, (3) 외부 Claude 커뮤니티 검색 결과를 기반으로 휴리스틱 정리됐습니다. LLM 호출 0회. 본문 작성은 5월 1주차 plan_issue 시점에 brief_generator(Sonnet 4.6) + 편집자 수동 보강으로 진행 예정.

---

## 변경 이력

- 2026-04-26: 초안 자동 생성. 7p 구성 — 표지(매거진 톤) + 본사 서비스(발행사 톤 3p) + 한국법인·밋업(발행사 톤 2p) + 커뮤니티 안내(매거진 톤). 광고 비율 8.75% (≤10% 상한 준수). 정기화 여부는 6/01-6/03 회고 시점 결정.
