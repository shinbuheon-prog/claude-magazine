# typeui.sh 디자인 스킬 비교 분석 (TASK_038)

> 2026-04-22 · typeui.sh v0.6.0

## 목적
typeui.sh의 MIT 오픈소스 디자인 스킬 중 매거진 도메인에 적합한 2종(**refined**, **clean**)을 pull해 현재 `theme.js`와 비교. **완전 대체가 아닌 선별 벤치마킹**.

---

## 실행 기록

```bash
npm install -g typeui.sh     # v0.6.0
typeui.sh list               # 전체 목록 (Agentic/Artistic/Bold/.../Refined/Clean)
typeui.sh pull refined --providers claude-code
typeui.sh pull clean --providers claude-code
# → .claude/skills/design-system/SKILL.md 생성 (매번 덮어쓰기)
# → design-system-refined, design-system-clean으로 rename 후 보존
```

---

## 비교 매트릭스

| 항목 | 우리 매거진 (theme.js) | refined | clean | 판단 |
|---|---|---|---|---|
| **primary 컬러** | `#1B1F3B` 딥 네이비 | `#3B82F6` 블루 | `#3B82F6` 블루 | ❌ 유지 (권위적 매거진 톤) |
| **accent 컬러** | `#C96442` 코랄 | `#8B5CF6` 퍼플 | `#8B5CF6` 퍼플 | ❌ 유지 (Anthropic 브랜드) |
| **본문 폰트** | Noto Serif KR | Playfair Display | Roboto | ❌ 한국어 매거진 — Noto Serif KR 필수 |
| **디스플레이 폰트** | Noto Serif KR | Playfair Display | Poppins | ⚠️ 영문 타이틀 한정 검토 |
| **모노 폰트** | 미지정 | **JetBrains Mono** | Inconsolata | ✅ **JetBrains Mono 채택** |
| **타입 스케일** | 암묵적 (Tailwind) | 12/14/16/20/24/32 | 12/14/16/20/24/32 | ✅ **명시적 문서화** |
| **스페이싱** | Tailwind 기본 (4/8/12...) | 4/8/12/16/24/32 | 8pt 베이스라인 | ✅ Tailwind 그대로 (이미 호환) |
| **success/warning/danger** | 미정의 | `#16A34A/#D97706/#DC2626` | 동일 | ✅ **시맨틱 컬러 3종 추가** |
| **컴포넌트 계열** | 매거진 전용 10종 | 일반 UI 30+ (buttons/inputs/...) | 동일 | ❌ 목적 다름 (매거진 템플릿 유지) |

---

## 선별 도입 결과

### ✅ 채택 (theme.js 반영)

**1. JetBrains Mono 모노스페이스**
- **위치**: `FONTS.mono`, `TYPE.mono`
- **활용**: InsightPage 수치, fact_checker의 source_id, 차트 라벨
- **index.html 추가**: `family=JetBrains+Mono:wght@400;500;700`

**2. STATUS 시맨틱 컬러**
- `success: #16A34A` — 팩트체크 통과·발행 완료
- `warning: #D97706` — 승인 대기·경고
- `danger: #DC2626` — 발행 차단·critical 오류
- `info: #3B82F6` — 정보·draft
- `neutral: #6B7280` — 기본·기획 단계
- **활용**: editorial_lint 결과 뱃지, DashboardPage 상태 표시, MonthlyProgressWidget

**3. 명시적 TYPE_SCALE 상수**
- `xs: 12px` ~ `xxl: 32px`
- Tailwind 클래스와 매칭되도록 주석 첨부
- 인쇄·PDF에서 크기 계산 시 참조용

### ❌ 무시 (매거진 도메인과 불일치)

- 일반 UI 컴포넌트 카탈로그 (buttons/forms/modals) — 매거진에 불필요
- `primary=#3B82F6` (블루) — 우리 브랜드 네이비(#1B1F3B)와 충돌
- Playfair Display — 한국어 본문에 부적합
- Roboto/Poppins — 영문 전용 산세리프, 매거진 세리프 방향성과 상반

### ⚠️ 보류 (나중에 재검토)

- **Playfair Display 혼용** — 영문 타이틀·서브타이틀에만 선택적 적용 가능. 현재 매거진은 대부분 한국어라 보류.

---

## 왜 "완전 대체"가 아니라 "선별 참고"인가

### 우리 매거진 디자인은 이미 특수 도메인
- **인쇄물(A4 PDF)** 지원 — 일반 웹 UI 시스템에는 없는 요구사항
- **한국어 타이포그래피** — Noto Serif KR은 영문 Playfair와 비교 불가
- **에디토리얼 레이아웃** — 8개의 구분된 매거진 템플릿(Cover·TOC·Article·Insight·Interview·Review·Feature·Colophon)

### typeui.sh는 일반 제품 UI 기준
- buttons/inputs/forms 같은 컴포넌트 카탈로그
- 매거진의 "목차·편집자의 말·콜로폰" 같은 개념 부재

### 결론
**우리 매거진은 공급자(supplier)에 가깝고, typeui.sh는 소비자(consumer) UI 시스템.**
→ 두 세계의 접점 중 **타이포 시스템·시맨틱 컬러** 영역만 유용. 나머지는 독립 유지.

---

## 파일 구성

```
.claude/skills/
├── editorial-review/       ← 우리 매거진 전용 skill (유지)
├── publish-gate/
├── ...                     ← 8개 기존 skill
├── design-system-refined/  ← 참고용 보존 (typeui.sh pull)
└── design-system-clean/    ← 참고용 보존

docs/
└── typeui_analysis.md      ← 본 문서

web/
├── index.html              ← JetBrains Mono 로드 추가
└── src/
    └── theme.js            ← STATUS, FONTS, TYPE_SCALE 추가
```

---

## 운영 가이드

### 새 skill 확인하고 싶을 때
```bash
typeui.sh list                           # 인터랙티브 목록
typeui.sh pull <slug> --dry-run --providers claude-code  # 미리보기
typeui.sh pull <slug> --providers claude-code            # 실제 pull
mv .claude/skills/design-system .claude/skills/design-system-<slug>
```

### 우리 theme.js로 반영 여부 판단
1. 해당 skill의 polish 수준·스코프 확인
2. 매거진 도메인(인쇄·한국어·에디토리얼)에 맞는지 판단
3. 맞으면 theme.js에 **토큰만 추가** (컴포넌트까지 가져오지 않음)
4. `docs/typeui_analysis.md`에 채택·무시 이유 기록

### 업데이트
```bash
# typeui.sh 새 버전이 나오면
npm install -g typeui.sh@latest
typeui.sh update --providers claude-code
# 기존 SKILL.md 유지하고 상단부만 갱신
```

---

## 라이선스
typeui.sh는 MIT. 우리 프로젝트에 포함된 `design-system-*/SKILL.md` 파일들도 MIT 원본 그대로 보존 (상단 frontmatter에 명시).

## 관련 문서
- [TASK_038.md](../tasks/TASK_038.md)
- [theme.js](../web/src/theme.js)
- [superpowers_integration.md](superpowers_integration.md) — 외부 skill 통합 일반 지침
