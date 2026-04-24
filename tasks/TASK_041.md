# TASK_041 — 카드뉴스 제작 스킬 + 밀도 게이트 (channel_rewriter 구조화)

## 메타
- **status**: todo
- **prerequisites**: TASK_023 (channel_rewriter.py SNS 자산 배포), TASK_030 (.claude/skills/), TASK_025 (article_standards.yml)
- **예상 소요**: 90~120분
- **서브에이전트 분할**: 가능 (Phase 1~2 vs Phase 3~4 병렬)
- **Phase**: 5 확장 (SNS 카드뉴스 제작 자동화)

---

## 목적
현재 `channel_rewriter.py`는 **텍스트 재가공**에 그침. SNS 카드뉴스 **제작 파이프라인이 부재**.
노션 레퍼런스 "클로드로 카드뉴스 만드는 3단계" 가이드를 흡수해 **스크립트→디자인→자산 생성**을 구조화.

편집자 흐름 변화:
- Before: 기사 발행 → `channel_rewriter.py`가 4채널 텍스트 생성 → 수동 디자인 제작
- After: 기사 발행 → **"Hook→핵심→CTA" 구조화된 슬라이드 JSON** → 카드뉴스 자산 자동 생성

---

## 스코프 경계 (중요)

**TASK_040과 역할 분리**:
- TASK_040: 매거진 **내지** 시각화 (infographic, illustrator) — A4 PDF 포맷
- TASK_041 (본 태스크): **SNS 카드뉴스** (1080×1350) 제작 — Instagram 등 외부 채널

**포맷별 폰트 정책 분리**:
- 매거진 PDF/웹: Noto Serif KR (세리프) — 기존 유지
- SNS 카드뉴스: Pretendard / Noto Sans KR (산세리프) — **신규 토큰 분리**

**Figma MCP 커넥터**: 본 태스크에서는 **사용하지 않음**.
TASK_039 잔여(SKILL.md `mcpServers` 활성화)와 **외부 MCP 서버 구현 선행 조건 공통** — 별도 태스크로 분리.

---

## 구현 명세

### Phase 1: 카드뉴스 제작 스킬 (30분)

#### 1.1 `.claude/skills/card-news-builder/SKILL.md` (신규)
노션 가이드 전문을 내재화:
- **보편 제작 원칙 4종** (Hook·한 장 한 메시지·디자인 기본)
- **7 레이아웃 구조 패턴**:
  1. 상단 태그 / 중앙 메인 카피 / 보조 카피 / 하이라이트 박스 / 푸터
  2. 좌상단 태그 / 질문형 메인 / 3단 그래픽 / 번호순 설명 / 푸터
  3. 좌상단 태그 / 단계별 메인 / 보조 카피 / 아이콘+설명 리스트 / Tip 박스 / 푸터
  4. 좌상단 태그 / 좌정렬 메인 / 보조 카피 / 저장 유도 배지 / 푸터
  5. 좌상단 태그 / 메인 카피 / 핵심 공식 / 상황별 프롬프트 카드 2종 / 푸터
  6. 중앙 태그 / 중앙 정렬 메인 / 보조 카피 / 알약형 CTA / 액션 아이콘 / 푸터
  7. 카테고리 태그 / 메인 카피 / 보조 카피 / 그래픽 요소 / 푸터
- **디자인 기본 규칙**: Pretendard / Noto Sans KR, 행간 1.4~1.6, 자간 -0.02em, 대비(#111~#333)
- **구성요소 비율**: 상단 15% / 중앙 70% / 하단 15%

#### 1.2 frontmatter
```yaml
---
name: card-news-builder
description: SNS 카드뉴스 제작 — Hook→핵심→CTA 구조, 7 레이아웃 패턴, Pretendard 폰트. "카드뉴스 제작", "SNS 카드", "1080x1350" 등에 트리거.
---
```

#### 1.3 기존 `sns-distribution` 스킬과 관계
- `sns-distribution`: 발행된 기사 자산 체크·재가공 조율 (유지)
- `card-news-builder`: 실제 제작 규칙·레이아웃 (신규, `sns-distribution`이 호출)

---

### Phase 2: editorial_lint 카드뉴스 밀도 게이트 (30분)

#### 2.1 pipeline/editorial_lint.py 확장
기존 "기사 10개 체크"와 **별개 모드** `--mode=card-news` 추가.

신규 검증 룰 3종:
```python
def check_card_news_density(slides: list[dict]) -> list[LintIssue]:
    """규칙 1: 본문 텍스트 밀도
    - 리스트형: 항목당 1~2문장, 단순 키워드 나열 금지
    - 서술형: 최소 3~4문장
    - 숫자 언급 시: 맥락 설명 1문장 필수
    """

def check_source_fidelity(slides: list[dict], source_md: str) -> list[LintIssue]:
    """규칙 2: 원문 충실도
    - 슬라이드 장당 원문 정보 포인트 2~3개 이상
    - 원문의 사례·인용·수치 분산 배치 확인
    """

def check_slide_count(slides: list[dict], source_char_len: int) -> list[LintIssue]:
    """규칙 3: 슬라이드 수 결정 기준
    - 500자 이하: 5~6장
    - 500~1500자: 7~9장
    - 1500자 이상: 10~13장
    (정보 압축해 장수 줄이는 것 금지)
    """
```

#### 2.2 spec/card_news_standards.yml (신규)
TASK_025 `article_standards.yml` 자매 스펙. Pass/Fail 기준:
- `density_pass`: 모든 슬라이드가 밀도 규칙 충족
- `fidelity_pass`: 원문 포인트 커버리지 ≥ 80%
- `count_pass`: 원문 길이 대비 슬라이드 수 적정 범위

---

### Phase 3: channel_rewriter 구조화 (30분)

#### 3.1 pipeline/channel_rewriter.py
현재 채널별 텍스트 생성을 **슬라이드 JSON 스키마**로 승격.

```python
# 신규 출력 스키마
{
  "channel": "instagram",
  "format": "card-news",
  "slides": [
    {
      "idx": 1,
      "role": "hook",              # hook / body / cta
      "layout": "layout_6",         # 7 패턴 중 1
      "tag": "AI 활용",
      "main_copy": "...",
      "sub_copy": "...",
      "highlight": "...",
      "footer": "@claude_magazine_kr"
    },
    ...
  ],
  "meta": {
    "total_slides": 8,
    "source_char_len": 1240,
    "lint_result": "pass"          # editorial_lint --mode=card-news 통과 여부
  }
}
```

#### 3.2 Hook → 핵심 → CTA 구조 강제
- `slides[0].role == "hook"` 필수
- `slides[-1].role == "cta"` 필수
- 중간 `body` 슬라이드가 1개 이상

#### 3.3 모델 배치
CLAUDE.md 모델 규칙 준수:
```python
model = "claude-haiku-4-5-20251001"  # SNS 재가공은 Haiku
```

---

### Phase 4: 디자인 토큰 분리 (15분)

#### 4.1 web/src/theme.js
```javascript
// 기존 (유지)
export const FONT_SERIF = "'Noto Serif KR', serif";      // 매거진 본문
export const FONT_MONO  = "'JetBrains Mono', monospace"; // 수치·source_id

// 신규
export const FONT_SANS_SNS = "'Pretendard', 'Noto Sans KR', sans-serif";  // SNS 카드 전용

export const SNS_TOKENS = {
  font:          FONT_SANS_SNS,
  line_height:   1.5,        // 1.4~1.6 범위 중앙값
  letter_spacing: "-0.02em",
  text_primary:  "#111111",  // 본문
  text_secondary: "#333333", // 보조
  safe_zone:     { top: "15%", content: "70%", bottom: "15%" },
  size:          { w: 1080, h: 1350 },
};
```

#### 4.2 포맷별 토큰 사용 규칙 (docs)
`docs/typography_policy.md` 신규 — 포맷→폰트 매핑 명시.

---

## 리스크 및 완화

| 리스크 | 완화책 |
|---|---|
| 매거진 세리프 톤과 SNS 산세리프 톤 혼용으로 브랜드 일관성 저하 | `docs/typography_policy.md` 에 포맷별 정책 명문화, 금지 조합 리스트 |
| Pretendard 폰트 임베딩 라이선스 | SIL OFL 1.1 — 상업 재배포 허용, `docs/baoyu_skills_audit.md` 형식으로 라이선스 기록 |
| 이미지 생성 비용 (무료 발행 원칙) | 본 태스크는 **JSON 스키마까지만** — 실제 이미지 생성은 후속 태스크 |
| 슬라이드 밀도 룰이 너무 엄격해 pass 불가 | Phase 2 스모크 테스트에서 기존 발행 기사 3건으로 캘리브레이션 |
| 기존 `sns-distribution` 스킬과 역할 중복 | 1.3 섹션 명시대로 **제작(builder)** vs **조율(distribution)** 분리 |

---

## 완료 조건 (Definition of Done)
- [ ] `.claude/skills/card-news-builder/SKILL.md` 작성, `python scripts/validate_skills.py` 통과
- [ ] `editorial_lint.py --mode=card-news`가 밀도·원문·장수 3 룰 검증
- [ ] `spec/card_news_standards.yml` 작성, `article_standards.yml` 스키마 호환
- [ ] `channel_rewriter.py` 출력이 신규 슬라이드 JSON 스키마 준수
- [ ] `hook`/`cta` 슬라이드 필수 검증, 누락 시 에러
- [ ] `web/src/theme.js` `SNS_TOKENS` 추가, 매거진 토큰 회귀 없음
- [ ] `docs/typography_policy.md` 포맷→폰트 정책 명시
- [ ] 기존 발행 기사 3건으로 스모크 테스트 — 밀도 게이트 통과율 기록
- [ ] request_id 로깅 (`logs/card_news.jsonl`) — CLAUDE.md 코딩 규칙 준수

---

## 산출물
- `.claude/skills/card-news-builder/SKILL.md` (신규, 노션 가이드 전문 포팅)
- `pipeline/editorial_lint.py` (확장, `--mode=card-news`)
- `spec/card_news_standards.yml` (신규)
- `pipeline/channel_rewriter.py` (출력 스키마 구조화)
- `web/src/theme.js` (SNS_TOKENS 추가)
- `docs/typography_policy.md` (신규)
- `logs/card_news.jsonl` (런타임 생성)

---

## 후속 태스크 후보 (본 태스크 범위 외)
- **TASK_042 후보**: Figma MCP 커넥터 + 슬라이드 JSON → Figma 자동 생성 (TASK_039 MCP 활성화 선행 필요)
- **TASK_043 후보**: Claude 내장 이미지 생성으로 1080×1350 PNG 자동 렌더 (비용 통제 필요)

---

## 완료 처리
```bash
python codex_workflow.py update TASK_041 implemented   # Codex 구현 후
python codex_workflow.py update TASK_041 merged        # Claude Code 최종 머지 후
```
