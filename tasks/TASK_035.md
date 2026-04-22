# TASK_035 — 80페이지 월간 PDF 컴파일러

## 메타
- **status**: todo
- **prerequisites**: TASK_010, TASK_034
- **예상 소요**: 75분
- **Phase**: 5 확장 (80p 매거진 지원)

## 목적
현재 `scripts/generate_pdf.js`는 6페이지만 처리. 80페이지 월간 매거진을 위해
**issue manifest 기반 다꼭지 PDF 컴파일러** 구현.

## 구현 명세

### 생성 파일
```
scripts/
└── compile_monthly_pdf.py       ← 월간 PDF 오케스트레이터

web/src/
└── PrintIssue.jsx                ← 이슈 전체 단일 렌더 (print 모드용)
```

### 동작 흐름
```
1. drafts/issues/YYYY-MM.yml 로드 (TASK_036 플랜 파일)
2. 섹션 순서: Cover → TOC → Editorial → 특집 → 심층 × N → 인사이트 × N → 인터뷰 × N → 리뷰 × N → Colophon
3. 각 꼭지 데이터 수집:
   - drafts/draft_art-{slug}.md → HTML 변환
   - 또는 Ghost Content API로 fetch
4. 단일 HTML 페이지에 모두 삽입 (React PrintIssue 컴포넌트)
5. Vite 빌드 → dist/
6. Puppeteer로 전체 PDF 생성
7. pypdf로 페이지 번호 오버레이 (선택)
8. output/claude-magazine-YYYY-MM.pdf 저장
```

### CLI
```bash
python scripts/compile_monthly_pdf.py --month 2026-05
python scripts/compile_monthly_pdf.py --month 2026-05 --dry-run    # 플랜 검증만
python scripts/compile_monthly_pdf.py --month 2026-05 --skip-build # 기존 dist 재사용
```

### 의존성 추가
- `pypdf>=4.0.0` (페이지 번호 오버레이·병합)

### PrintIssue.jsx
- URL 파라미터 `?issue=2026-05` 처리
- `fetch('/drafts/issues/2026-05.json')`로 이슈 데이터 로드
- 모든 컴포넌트를 A4 페이지 단위로 순서대로 렌더
- 각 `.print-page` 사이 `page-break-after: always`

## 완료 조건
- [ ] `scripts/compile_monthly_pdf.py` 생성
- [ ] `web/src/PrintIssue.jsx` 생성
- [ ] `requirements.txt`에 pypdf 추가
- [ ] `--dry-run` 모드: 플랜 파일 검증만
- [ ] 스모크 테스트: 가상 이슈 1건으로 컴파일 성공

## 완료 처리
`python codex_workflow.py update TASK_035 merged`
