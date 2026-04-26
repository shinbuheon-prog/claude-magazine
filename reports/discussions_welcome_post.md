# GitHub Discussions Welcome Post 골조

**용도**: GitHub Discussions 활성화 직후 사용자가 Discussions 첫 게시로 등록할 환영 메시지
**카테고리**: General (또는 신설 "Announcements")
**제목**: `👋 Claude Magazine에 오신 것을 환영합니다 — 5월 31일 정식 발행 1호 준비 중`
**Pin 권장**: ✅ ON (Discussions 페이지 상단 고정)

---

## 게시 본문 (그대로 복사·붙여넣기 가능)

```markdown
# 👋 Claude Magazine 외부 피드백 환영합니다

**Anthropic 공식 리셀러 클래스메소드 그룹의 한국 법인(클래스메소드코리아)**이 운영하는 한국어권 Claude 실무자용 무료 발행 매거진입니다.

🗓 **2026-05-31 정식 발행 1호(Issue 1) 발행 목표.**
현재 v0.3.0-rc1 (release candidate) 상태이며, 외부 피드백을 5월 호 콘텐츠와 운영 방식에 반영하고 있습니다.

---

## 📖 매거진 정체성

- 한국어권 Claude 실무자를 위한 **무료 발행** (결제·유료 구독 시스템 도입 계획 없음)
- **인간 편집 책임** 위에 Claude AI가 생산성을 증폭하는 운영체계
- 80p 월간 PDF + Ghost 게시 + SNS 4채널 재가공
- 모든 본문 하단에 AI 사용 고지 (governance 정책)

자세한 정체성·기술 스택·Phase 진행 현황: [README.md](https://github.com/shinbuheon-prog/claude-magazine#readme)

---

## 💬 Discussions 카테고리 안내

| 카테고리 | 용도 | 누가 적합 |
|---|---|---|
| 💡 **Ideas** | 콘텐츠 주제 제안 — 어떤 Claude 주제를 매거진에서 보고 싶으신가요? | 모든 사용자 환영 |
| 💬 **General** | 매거진 운영 모델·정책 토론 — 무료 발행·인간 편집·외부 큐레이션 등 | 매거진 운영에 관심 있는 분 |
| ❓ **Q&A** | 사용 질문·도구 사용법·매거진 운영 관련 | 도구·운영 사용자 |
| 🎉 **Show and tell** | 본인의 Claude 활용 사례·블로그·GitHub 공유 | 콘텐츠 제공 가능자 |

> Issues는 **버그 리포트·기능 제안** (코드 변경)에만 사용해 주세요. 콘텐츠·운영 토론은 Discussions에서.

---

## 🤝 가장 환영하는 피드백 6가지

1. 어떤 Claude 주제를 매거진에서 보고 싶으신가요?
2. 한국어권 Claude 사용자 관점에서 부족한 콘텐츠 영역은?
3. 매거진 운영 모델(무료 발행·자가 사례·외부 큐레이션)에 대한 의견
4. AWS Bedrock·MCP·Cowork·Claude Code 운영 경험·트러블슈팅 사례 (매거진 본문 source 후보)
5. 디자인·레이아웃·페이지 구성 (80p PDF · Vite+React+Puppeteer 출력)
6. 발행 자동화 운영 정책 (무료 LLM 운영·Sponsored Content 표기 6 의무·소셜 채널 자동 크롤링 기각 등)

---

## 📅 5월 호 발행 일정

```
5월 1주차 (5/04-5/10)  ━━━━━  콘텐츠 생산 ① brief 16건 생성
5월 2주차 (5/11-5/17)  ━━━━━  콘텐츠 생산 ② draft 16건 작성
5월 3주차 (5/18-5/24)  ━━━━━  고도화 ① factcheck·standards·diversity
5월 4주차 (5/25-5/31)  ━━━━━  고도화 ② + 발행 (Issue 1, v0.3.0)
```

**5/03 (금)까지** 받은 외부 피드백을 5/04 plan_issue 시점에 반영합니다.

---

## 🔍 매거진 현재 상태

- **버전**: v0.3.0-rc1 (Phase 1~8 완료, Issue 1 발행 준비)
- **검증**: 97/97 pytest green / CI 7-job 병렬 / 무료 LLM 운영 (Max 구독 경유 $0)
- **콘텐츠 풀**: 9 본문 카테고리 + Inside Classmethod 광고 1코너 = **80p 정확 도달 매핑 확정**
- **외부 큐레이션**: arXiv·HN·Reddit·Anthropic·OpenAI·Google·HF·Meta RSS + Korea Spotlight 자체 콘텐츠

---

## 📬 다른 연락 경로

- **이메일** (협업·기고·Sponsored Content): info@classmethod.kr
- **GitHub Issues**: 버그·기능 제안 (코드 변경)
- **매거진 Threads 게시글 댓글**: 게시 시점 별도 안내
- **발행사**: Anthropic 공식 리셀러 클래스메소드 그룹의 한국 법인 (https://classmethod.jp · 050-1754-1651)

---

## 🤖 본 게시글 자체 AI 사용 고지

본 환영 메시지는 매거진 편집장이 작성·승인했습니다. 매거진 본문은 인간 편집장이 brief·draft·factcheck·publish-gate 모두 명시 승인하며, Claude AI는 보조 도구로 사용됩니다 ([docs/governance.md](https://github.com/shinbuheon-prog/claude-magazine/blob/main/docs/governance.md)).

---

> "AI는 편집자를 대체하지 않습니다. 편집자가 더 많은 것을 더 잘하게 합니다."

피드백·토론 환영합니다. 한국어 우선 (영어도 OK). 🙌
```

---

## 사용자 액션 — Welcome post 게시 단계

1. **GitHub Discussions 활성화** (이미 완료한 경우 skip)
   - https://github.com/shinbuheon-prog/claude-magazine/settings → Features → Discussions ON

2. **카테고리 4종 생성** (Discussions 페이지 → ⚙ → New category)
   - 💡 **Ideas** (Open-ended) — 콘텐츠 주제 제안
   - 💬 **General** (Open-ended) — 운영 모델 토론
   - ❓ **Q&A** (Q&A type) — 사용 질문
   - 🎉 **Show and tell** (Open-ended) — 활용 사례 공유

3. **Welcome post 게시**
   - https://github.com/shinbuheon-prog/claude-magazine/discussions/new
   - Category: **General** (또는 신설 Announcements)
   - Title: `👋 Claude Magazine에 오신 것을 환영합니다 — 5월 31일 정식 발행 1호 준비 중`
   - Body: 위 §"게시 본문" 그대로 복사·붙여넣기
   - **Pin discussion** ✅ ON

4. **(선택) Threads 게시글에 Discussions 링크 추가**
   - 본 Welcome post URL을 Threads 게시글 본문에 1줄 추가 검토
   - 또는 Threads 게시 후 Welcome post 댓글에 "Threads 게시: <URL>" 1줄 추가

---

## 변경 이력

- 2026-04-26: 초안 작성. Threads 게시 + GitHub Release v0.3.0-rc1 발행 직전 사전 작업으로 준비.
