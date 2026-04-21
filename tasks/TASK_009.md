# TASK_009 — 매거진 웹 레이아웃 컴포넌트

## 메타
- **status**: todo
- **prerequisites**: TASK_001
- **예상 소요**: 60분
- **서브에이전트 분할**: 가능 (컴포넌트 3개 독립 구현)

---

## 목적
`web/` 폴더에 React 기반 매거진 레이아웃을 구현한다.
Ghost CMS 콘텐츠를 받아 렌더링하는 프론트엔드 진입점.

---

## 파일 구조 (이미 생성됨)
```
web/
├── src/
│   ├── theme.js                 ← 디자인 시스템 (색상·타이포)
│   ├── App.jsx                  ← 페이지 전환 진입점
│   └── components/
│       ├── CoverPage.jsx        ← 매거진 표지
│       ├── ArticlePage.jsx      ← 기사 본문 (테이블+바차트)
│       └── InsightPage.jsx      ← 데이터 인사이트 (LineChart)
```

---

## 서브에이전트 A: 프로젝트 초기화

### 실행 커맨드
```bash
cd web
npm create vite@latest . -- --template react
npm install
npm install recharts tailwindcss @tailwindcss/typography
npx tailwindcss init
```

### tailwind.config.js 설정
```js
export default {
  content: ["./src/**/*.{js,jsx}"],
  theme: { extend: { fontFamily: { serif: ['Georgia', 'serif'] } } },
  plugins: [require('@tailwindcss/typography')],
}
```

---

## 서브에이전트 B: Ghost API 연동

### `web/src/api/ghost.js` 생성
```js
const GHOST_URL = import.meta.env.VITE_GHOST_URL;
const GHOST_KEY = import.meta.env.VITE_GHOST_CONTENT_KEY;

export async function getPosts(limit = 10) {
  const r = await fetch(
    `${GHOST_URL}/ghost/api/content/posts/?key=${GHOST_KEY}&limit=${limit}&include=tags,authors`
  );
  return r.json();
}

export async function getPost(slug) {
  const r = await fetch(
    `${GHOST_URL}/ghost/api/content/posts/slug/${slug}/?key=${GHOST_KEY}`
  );
  return r.json();
}
```

### `web/.env.local` (gitignore에 포함됨)
```
VITE_GHOST_URL=https://your-site.ghost.io
VITE_GHOST_CONTENT_KEY=your-content-key
```

---

## 서브에이전트 C: 데이터 연동

`App.jsx`의 SAMPLE_* 상수를 Ghost API 응답으로 교체:
- `ArticlePage`의 `pageData`를 Ghost post 메타데이터로 매핑
- `InsightPage`의 `chartData`를 post custom fields 또는 별도 JSON으로 주입

---

## 완료 조건
- [ ] `npm run dev` 실행 시 3개 페이지 탭 전환 정상 동작
- [ ] CoverPage, ArticlePage, InsightPage 각각 props 없이 기본값으로 렌더링
- [ ] InsightPage LineChart 정상 렌더링 (Recharts)
- [ ] THEME 컬러 (`#1B1F3B`, `#C96442`)가 시각적으로 적용 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_009 implemented
```
