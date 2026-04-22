---
name: pdf-compile
description: 월간 PDF 생성 자동화 (Vite 빌드 → Puppeteer 캡처 → A4 PDF). "월간 PDF", "pdf compile", "매거진 PDF" 트리거.
allowed-tools: Bash, Read
---

# 월간 PDF 컴파일 (PDF Compile)

## 언제 사용
- 사용자가 "이번 달 PDF 뽑아줘", "월간 매거진 PDF" 요청
- 매월 말일 자동 트리거 (n8n workflow_4 예정)
- 월간 커버 이미지 업데이트 후 재생성

## 절차 (Systematic)

### 1. 월 지정 확인
- 사용자 메시지에서 YYYY-MM 추출
- 없으면 현재월 사용

### 2. 커버 이미지 존재 확인
```bash
python scripts/check_covers.py --month {YYYY-MM}
```
- 해당 월 커버 없으면 `default.png`로 fallback됨을 편집자에게 안내
- 커버 추가 원하면 Claude Design 링크 제공: https://claude.ai/design

### 3. SNS 자산 체크 (선택)
```bash
python scripts/check_sns_assets.py --month {YYYY-MM}
```
- 참고용 — PDF 생성에는 직접 영향 없음

### 4. Vite 빌드
```bash
cd web && npm run build
```
- `dist/` 생성 확인
- 실패 시 빌드 에러 보고

### 5. Puppeteer PDF 생성
```bash
cd scripts && node generate_pdf.js --month {YYYY-MM}
```
- 또는 PowerShell 원스톱: `.\scripts\build_and_pdf.ps1 -Month {YYYY-MM}`
- 기존 빌드 재사용: 옵션 없이 실행 (빠름)
- 강제 재빌드: `--rebuild` 추가

### 6. 결과 확인
- 출력 경로: `output/claude-magazine-{YYYY-MM}.pdf`
- 파일 크기 · 페이지 수 보고
- 커버·기사·인사이트·인터뷰·리뷰·특집 6페이지 모두 포함 확인

## Verify before success
- [ ] `output/claude-magazine-{YYYY-MM}.pdf` 생성됨
- [ ] 파일 크기 500KB~5MB 범위 (너무 작거나 크면 경고)
- [ ] 빌드 에러 없음 (836+ modules transformed)
- [ ] Vite `dist/` 가 최신 상태
- [ ] 커버 이미지 PDF 내부에 임베드됨 (onError fallback 동작 확인)

## 주의
- PDF 생성은 `scripts/` 디렉토리에서 실행해야 함 (상대 경로 이슈)
- 글꼴 로딩 대기 1.2초 내장됨 (Noto Serif KR)
- Windows에서 포트 4173 이미 사용 중이면 서버 시작 실패

## 관련 스킬
- 발행 준비: publish-gate
- 기사 작성: brief-generation
