# TASK_022 — 매거진 템플릿 확장 (인터뷰·리뷰·기획 3종)

## 메타
- **status**: todo
- **prerequisites**: TASK_009
- **예상 소요**: 90분
- **서브에이전트 분할**: 가능 (A: InterviewPage / B: ReviewPage / C: FeaturePage)
- **Phase**: 3 (콘텐츠 다양성)

---

## 목적
기존 3종(Cover·Article·Insight)에 **매거진 저널리즘 표준 템플릿 3종**을 추가해 콘텐츠 표현력을 확장.
Claude Design으로 시안 제작 → 본 태스크에서 React 컴포넌트로 이식하는 구조.

우선순위 2: 매거진 콘텐츠 품질 향상에 직접 기여.

---

## 구현 명세

### 생성할 파일 (3개)
```
web/src/components/
├── InterviewPage.jsx        ← 인터뷰 기사 (Q&A 포맷)
├── ReviewPage.jsx           ← 제품/도구 리뷰 (평점 + 비교표)
└── FeaturePage.jsx          ← 기획 특집 (장문 에디토리얼 + 이미지 블록)
```

### 공통 원칙
- `theme.js`의 THEME/TYPE 토큰 재사용 (새 색 추가 금지)
- Tailwind 클래스 사용, 인라인 `style`는 THEME 색상에만
- `font-serif`, `max-w-[800px]`, `shadow-2xl`, `border-t-[10px]` 기본 레이아웃 통일
- `@media print` A4 대응 (기존 index.css 패턴 유지)

---

### A: InterviewPage.jsx

```jsx
const InterviewPage = ({ interviewData = {} }) => {
  const {
    interviewNum = "01",
    subject = "홍길동",
    role = "AI 프로덕트 리드",
    company = "Example Corp",
    quote = "핵심 발언 한 줄 인용",
    qa = [
      { q: "질문 1", a: "답변 본문...", sourceId: "src-..." },
    ],
    portraitUrl = "/covers/default.png",
    sourceId = "src-interview-001",
  } = interviewData;
  // ...
};
```

레이아웃 특징:
- 상단 좌측: 인물 포트레이트 (260×260, 원형 마스크)
- 상단 우측: 이름·직책·회사·핵심 인용문
- 본문: Q&A 반복 블록 (Q는 딥 네이비 굵게, A는 본문체)
- 각 A 블록 하단에 `[source_id]` 캡션 (있으면)
- 푸터: INTERVIEW 번호 + AI 사용 고지 (editorial_lint 연동용)

---

### B: ReviewPage.jsx

```jsx
const ReviewPage = ({ reviewData = {} }) => {
  const {
    category = "TOOLS",
    productName = "Claude Code",
    verdict = "에디터 추천",    // "에디터 추천" | "조건부 추천" | "대안 고려"
    overallScore = 8.5,          // 0~10
    criteria = [
      { name: "사용성",   score: 9, note: "직관적" },
      { name: "비용",     score: 7, note: "Pro 필요" },
      { name: "확장성",   score: 9, note: "MCP 지원" },
    ],
    prosText = ["장점 1", "장점 2"],
    consText = ["단점 1"],
    competitorTable = [
      { name: "A", price: "$20", rating: "8.5" },
      { name: "B", price: "$30", rating: "7.0" },
    ],
    sourceId = "src-review-001",
  } = reviewData;
  // ...
};
```

레이아웃 특징:
- 헤더: 카테고리 태그 + 제품명 + 큰 종합점수 (오른쪽)
- 좌측 8: 평가 기준별 점수 바 차트 (`Recharts BarChart` 또는 수평 바)
- 우측 4: 에디터 평결 배지 (verdict) + 한 줄 요약
- 중단: Pros/Cons 2컬럼 (녹색·코랄 배지)
- 하단: 경쟁 제품 비교 테이블
- 푸터: 리뷰 기준 + AI 사용 고지

---

### C: FeaturePage.jsx

```jsx
const FeaturePage = ({ featureData = {} }) => {
  const {
    category = "FEATURE",
    issueTag = "Cover Story",
    title = "특집 제목",
    lede = "리드 문장",
    sections = [
      { heading: "소제목 1", body: "본문...", pullQuote: "인용 블록", image: "/covers/..." },
    ],
    author = "편집팀",
    sourceIds = ["src-001", "src-002"],
  } = featureData;
  // ...
};
```

레이아웃 특징:
- 상단: 대형 헤드라인 + 리드 문장 (작가 크레딧)
- 섹션별 반복:
  - 소제목 (serif, bold)
  - 본문 (2단 컬럼 레이아웃, `columns-2`)
  - Pull quote (큰 따옴표 장식, 코랄 색)
  - 선택적 이미지 블록 (전폭 또는 좌우 정렬)
- 하단: 사용한 전체 `source_ids` 요약 + AI 사용 고지

---

### App.jsx 통합
기존 PAGES 배열 확장:
```jsx
const PAGES = ['표지', '기사', '인사이트', '인터뷰', '리뷰', '특집'];

// 샘플 데이터 추가 + 분기
const SAMPLE_INTERVIEW = { ... };
const SAMPLE_REVIEW = { ... };
const SAMPLE_FEATURE = { ... };

{page === '인터뷰' && <InterviewPage interviewData={SAMPLE_INTERVIEW} />}
{page === '리뷰'   && <ReviewPage reviewData={SAMPLE_REVIEW} />}
{page === '특집'   && <FeaturePage featureData={SAMPLE_FEATURE} />}
```

### Print 모드 (PDF) 통합
`?print=1` 분기에 3개 페이지 추가 — 월간 PDF에 신규 템플릿도 포함되도록.

---

## 완료 조건
- [ ] `InterviewPage.jsx` 생성, 샘플 데이터로 정상 렌더링
- [ ] `ReviewPage.jsx` 생성, 종합점수·Pros/Cons·비교표 렌더링
- [ ] `FeaturePage.jsx` 생성, 2단 컬럼 + pull quote 렌더링
- [ ] `App.jsx`에 3개 페이지 탭 추가
- [ ] `?print=1` PDF 모드에 3개 페이지 포함
- [ ] `theme.js`의 THEME/TYPE 토큰만 사용 (신규 색 추가 없음)
- [ ] `npm run build` 성공
- [ ] `npm run dev` 실행 시 6개 탭 (표지·기사·인사이트·인터뷰·리뷰·특집) 전환 정상
- [ ] `scripts/generate_pdf.js` 실행 시 6페이지 PDF 생성 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_022 implemented
```

---

## 주의사항
- 이미지 URL은 `/covers/default.png` 같은 `public/` 상대 경로 사용 (import 금지)
- Recharts는 기존 InsightPage.jsx가 이미 import 중이니 재사용 가능
- Pull quote 스타일: `border-l-4` + 코랄 색상 + 이탤릭 (기존 ArticlePage 패턴)
- 인쇄 시 배경색이 빠지는 문제 방지: `print-color-adjust: exact` 이미 설정됨 (index.css)
- 각 페이지에 editorial_lint `ai-disclosure` 블록 자동 적용되도록 disclosure 삽입 경로 열어둘 것
