# TASK_038 — typeui.sh 디자인 스킬 선별 도입

## 메타
- **status**: merged
- **prerequisites**: TASK_009 (theme.js)
- **실 소요**: ~30분
- **Phase**: 5 확장 (디자인 일관성 강화)

## 목적
typeui.sh의 MIT 오픈소스 디자인 스킬 57종 중 매거진 적합 후보 2종(**refined**, **clean**)을 pull하고, 우리 theme.js와 비교해 **선별 도입할 요소만 추출**.
완전 대체가 아닌 **레퍼런스 벤치마킹** 목적.

## 결과 요약

### 도입한 요소 (High 우선순위)
1. **JetBrains Mono 추가** — InsightPage 수치·fact_checker source_id 등 모노스페이스 표시용
2. **시맨틱 컬러 토큰 명시** (success/warning/danger) — editorial_lint 상태·알림 배지용
3. **타입 스케일 문서화** — 기존 암묵적 스케일을 명시적 상수로

### 무시한 요소 (매거진과 맞지 않음)
- `primary=#3B82F6` (파랑) — 매거진 테마는 #1B1F3B 네이비 유지
- 일반 UI 컴포넌트 계열 (buttons·inputs·forms) — 매거진 템플릿과 목적 다름
- Playfair Display — 한국어 매거진이라 Noto Serif KR 유지 (영문 제목에만 검토)

## 산출물
- `web/src/theme.js` — FONT_MONO, STATUS 토큰 추가
- `web/index.html` — JetBrains Mono 폰트 링크 추가
- `.claude/skills/design-system-refined/SKILL.md` — 참고용 보존
- `.claude/skills/design-system-clean/SKILL.md` — 참고용 보존
- `docs/typeui_analysis.md` — 비교 분석 리포트

## 완료 처리
`python codex_workflow.py update TASK_038 merged`
