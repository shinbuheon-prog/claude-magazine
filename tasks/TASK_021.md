# TASK_021 — 월간 커버 일러스트 드롭인 시스템

## 메타
- **status**: todo
- **prerequisites**: TASK_009, TASK_010
- **예상 소요**: 30분
- **서브에이전트 분할**: 불필요
- **Phase**: 3 (시각 자산 통합)

---

## 목적
`CoverPage.jsx`의 플레이스홀더 `[ 커버 일러스트 영역 800×550px ]`를 **실제 이미지로 교체**할 수 있는 드롭인 경로 시스템 구축.
Claude Design(또는 다른 도구)으로 제작한 월간 커버 이미지를 특정 폴더에 저장하면 자동 참조된다.

우선순위 1: 가장 단순하며 매월 PDF 품질에 즉시 영향.

---

## 구현 명세

### 1. 폴더 컨벤션
```
web/public/covers/
├── README.md                     ← 파일명 규칙 문서
├── 2026-05.png                   ← 월별 기본 (YYYY-MM)
├── 2026-05@2x.png                ← retina 버전 (선택)
├── 2026-05-variant-tech.png      ← 테마 변형 (선택)
└── default.png                   ← fallback (필수)
```

### 2. CoverPage.jsx 수정
기존 플레이스홀더 `div` 블록을 다음 로직으로 교체:
```jsx
const COVER_BASE = '/covers';

function resolveCoverPath(issueDate) {
  // "2026년 5월" → "2026-05"
  const match = issueDate.match(/(\d{4})년\s*(\d{1,2})월/);
  if (!match) return `${COVER_BASE}/default.png`;
  const yyyy = match[1];
  const mm = String(match[2]).padStart(2, '0');
  return `${COVER_BASE}/${yyyy}-${mm}.png`;
}

// JSX 내부
<div className="absolute bottom-0 right-0 w-[75%] h-[50%] rounded-tl-[80px] overflow-hidden">
  <img
    src={resolveCoverPath(date)}
    alt={`${issue} 커버 일러스트`}
    className="w-full h-full object-cover"
    onError={(e) => { e.currentTarget.src = `${COVER_BASE}/default.png`; }}
  />
</div>
```

### 3. web/public/covers/README.md 생성
파일명 규칙·권장 사이즈·라이선스 기록 방법:
```markdown
# 월간 커버 이미지

## 파일명 규칙
- 월별 기본: `YYYY-MM.png` (예: `2026-05.png`)
- Retina: `YYYY-MM@2x.png` (2x 해상도, 선택)
- 변형: `YYYY-MM-variant-{name}.png` (선택)
- Fallback: `default.png` (필수, 삭제 금지)

## 권장 사이즈
- 표준: 800×550px
- Retina: 1600×1100px (@2x)
- 포맷: PNG 또는 WebP

## 라이선스 기록 (필수)
각 이미지 커밋 시 `web/public/covers/licenses.json`에 기록:
{
  "2026-05.png": {
    "source": "Claude Design / claude.ai/design",
    "created_at": "2026-04-22",
    "rights": "internal-use-only",
    "prompt": "...",
    "created_by": "editor-name"
  }
}
```

### 4. web/public/covers/licenses.json 생성 (빈 객체로 시작)
```json
{}
```

### 5. default.png 생성
Claude Magazine 브랜드 플레이스홀더 1장 생성 (800×550px, 딥 네이비 배경 + 코랄 강조색).
불가능하면 기존 플레이스홀더 디자인을 SVG로 변환해 PNG export.

### 6. 검증 스크립트: `scripts/check_covers.py`
```bash
python scripts/check_covers.py

# 동작:
# 1. web/public/covers/default.png 존재 확인
# 2. licenses.json의 모든 파일이 실제 존재하는지
# 3. 실제 파일 중 licenses.json에 누락된 것 경고
# 4. 다음 월(YYYY-MM)의 커버 존재 여부 체크
```

---

## 완료 조건
- [ ] `web/public/covers/` 폴더 생성
- [ ] `default.png` 생성 (800×550px 이상)
- [ ] `CoverPage.jsx`에 `resolveCoverPath()` + `<img>` 로직 적용
- [ ] `onError` fallback으로 `default.png` 표시 확인
- [ ] `web/public/covers/README.md` 작성
- [ ] `web/public/covers/licenses.json` 빈 객체로 생성
- [ ] `scripts/check_covers.py` 스크립트 생성 및 동작 확인
- [ ] 기존 PDF 생성 (`scripts/generate_pdf.js`) 재실행 시 커버 이미지 정상 임베드
- [ ] 존재하지 않는 월로 렌더링 시도 → `default.png`로 fallback 확인

---

## 완료 후 처리
```bash
python codex_workflow.py update TASK_021 implemented
```

---

## 주의사항
- PNG 크기가 너무 크면 PDF 생성 시간 증가 — 권장 500KB 이하
- Vite는 `public/` 하위 파일을 빌드 시 그대로 복사 → import 구문 불필요
- Puppeteer PDF 생성 시 이미지 로드를 기다리기 위해 기존 `networkidle0` 설정 유지
- 라이선스 미기록 이미지는 TASK_016 (editorial_lint)의 `image-rights` 체크에서 탐지됨
