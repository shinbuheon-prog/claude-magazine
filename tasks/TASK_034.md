# TASK_034 — 매거진 추가 컴포넌트 (TOC·Editorial·Colophon)

## 메타
- **status**: todo
- **prerequisites**: TASK_009, TASK_022
- **예상 소요**: 40분
- **Phase**: 5 확장 (80p 매거진 지원)

## 목적
80페이지 월간 매거진 PDF에 필요한 **구조 페이지 3종**을 React 컴포넌트로 구현.
현재 기사 템플릿(Cover·Article·Insight·Interview·Review·Feature) 외에 **목차·편집자의 말·뒷면 정보**가 부재.

## 구현 명세

### 생성 파일
```
web/src/components/
├── TOCPage.jsx           ← 목차 (섹션별 꼭지 + 페이지 번호)
├── EditorialPage.jsx     ← 편집자의 말 (주제 소개·편집장 서명)
└── ColophonPage.jsx      ← 뒷면 정보 (발행인·편집진·라이선스·AI 고지)
```

### 컴포넌트 상세

#### TOCPage.jsx
- props: `tocData = { issue, month, sections: [{name, articles: [{title, page, slug}]}] }`
- 섹션별로 그룹: 특집·심층·인사이트·인터뷰·리뷰
- 각 꼭지: 제목 + 점선 리더 + 페이지 번호
- 2단 컬럼 레이아웃 (기사 많으면 자동)

#### EditorialPage.jsx
- props: `editorialData = { issue, theme, greeting, body, editorName, editorTitle }`
- 상단: 이슈 정보 (예: "VOL.01 · 2026년 5월")
- 본문: 편집장 인사말 (2~3단락)
- 하단: 편집장 서명 + 날짜

#### ColophonPage.jsx
- props: `colophonData = { issue, publisher, editorialTeam, contributors, copyright, aiNotice, corrections }`
- 발행 정보: 제호·발행인·편집장·연락처
- 편집진 목록 (이름·역할)
- 라이선스 / 저작권 문구
- AI 사용 종합 고지 (어느 모델·어느 공정)
- 정정 요청 정책 (24h·이메일)

### App.jsx 통합
- `PAGES` 배열: `['표지', '목차', '편집자의 말', '기사', ...]`
- Print 모드에서 순서: Cover → TOC → Editorial → (기사들) → Colophon

## 완료 조건
- [ ] 3개 컴포넌트 생성
- [ ] App.jsx에 탭·Print 순서 반영
- [ ] 샘플 데이터로 npm run build 성공
- [ ] THEME/TYPE 토큰만 사용 (신규 색 금지)

## 완료 처리
`python codex_workflow.py update TASK_034 merged`
