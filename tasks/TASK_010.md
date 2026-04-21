# TASK_010 — Puppeteer 기반 월간 PDF 생성 파이프라인

## 메타
- **status**: merged
- **prerequisites**: TASK_009
- **완료일**: 2026-04-21
- **커밋**: ba257ad (develop 브랜치)

---

## 목적
매월 발행하는 매거진을 A4 PDF 파일로 자동 생성하는 파이프라인 구축.
기존 React 컴포넌트(CoverPage, ArticlePage, InsightPage)를 그대로 활용.

---

## 구현 내용

### 아키텍처
```
web/src/App.jsx (?print=1 모드)
  → 모든 페이지 A4 크기로 순서대로 렌더링
  → Vite 빌드 (npm run build)
        ↓
scripts/generate_pdf.js
  → Node 내장 HTTP 서버로 dist/ 서빙 (port 4173)
  → Puppeteer headless 브라우저로 ?print=1 접근
  → page.pdf({ format: 'A4', printBackground: true })
  → output/claude-magazine-YYYY-MM.pdf 저장
```

### 생성된 파일
```
web/
├── index.html              ← Vite 진입점 (Noto Serif KR 폰트 포함)
├── package.json            ← Vite + Tailwind + React + Recharts
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── main.jsx            ← ReactDOM 진입점
    ├── index.css           ← @tailwind 지시문 + @media print A4 스타일
    └── App.jsx             ← ?print=1 분기 추가

scripts/
├── generate_pdf.js         ← Puppeteer PDF 생성 메인 스크립트
├── package.json            ← puppeteer + pdf-lib 의존성
└── build_and_pdf.ps1       ← 빌드→PDF 원스톱 PowerShell 스크립트
```

---

## 실행 방법

### 월간 PDF 생성
```powershell
# PowerShell (프로젝트 루트에서)
.\scripts\build_and_pdf.ps1 -Month 2026-05

# 또는 scripts/ 폴더에서 직접
node generate_pdf.js --month 2026-05
node generate_pdf.js --month 2026-05 --rebuild  # 강제 재빌드
```

### 출력
```
output/
└── claude-magazine-2026-05.pdf   (~1MB, A4 3페이지)
```

---

## 완료 조건 (달성)
- [x] `?print=1` 파라미터로 전체 페이지 순서 렌더링
- [x] A4 포맷 PDF 생성 (printBackground: true)
- [x] Puppeteer headless 실행 성공
- [x] `output/claude-magazine-2026-04.pdf` 생성 확인 (995KB)
- [x] `.gitignore`에 output/, dist/, node_modules/ 추가
- [x] develop 브랜치 push 완료
