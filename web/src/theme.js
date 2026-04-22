// Claude Magazine 디자인 시스템
// TASK_038: typeui.sh refined/clean 비교 후 선별 도입 항목 주석 표기
export const THEME = {
  // 브랜드 컬러
  primary:   "#1B1F3B",   // 딥 네이비 (권위·신뢰)
  accent:    "#C96442",   // Anthropic 코랄 (포인트)
  accentAlt: "#7C5CBF",   // 클로드 퍼플 (서브 포인트)

  // 배경
  bgLight:   "#F8F7F4",   // 따뜻한 오프화이트
  bgCard:    "#FFFFFF",
  bgDark:    "#1B1F3B",

  // 텍스트
  textMain:  "#1C1C1C",
  textSub:   "#6B7280",
  textLight: "#9CA3AF",

  // 차트
  lineA:     "#C96442",   // 메인 라인
  lineB:     "#7C5CBF",   // 보조 라인
  lineC:     "#059669",   // 세 번째 라인
};

// TASK_038: 시맨틱 상태 컬러 (editorial_lint·alert 배지용)
// typeui.sh 표준에서 차용
export const STATUS = {
  success:   "#16A34A",   // 팩트체크 통과·발행 완료
  warning:   "#D97706",   // 경고·승인 대기
  danger:    "#DC2626",   // 발행 차단·critical 오류
  info:      "#3B82F6",   // 정보·draft
  neutral:   "#6B7280",   // 기획·기본
};

// 타이포그래피 스케일
export const TYPE = {
  category:  "text-xs tracking-[0.3em] font-bold uppercase",
  headline:  "text-4xl font-extrabold tracking-tight leading-tight",
  subhead:   "text-xl font-bold tracking-tight",
  body:      "text-sm leading-relaxed text-gray-700",
  caption:   "text-[10px] tracking-widest text-gray-400",
  // TASK_038: 모노스페이스 (수치·코드·source_id 표시용)
  mono:      "font-mono text-xs tracking-tight",
};

// TASK_038: 폰트 스택 (index.html에서 로드)
export const FONTS = {
  serif:     "'Noto Serif KR', serif",       // 한국어 본문·제목 기본
  sans:      "'Noto Sans KR', system-ui, sans-serif",
  mono:      "'JetBrains Mono', ui-monospace, monospace",
};

// TASK_038: 명시적 타입 스케일 (typeui.sh 12/14/16/20/24/32 기반)
// Tailwind 클래스와 매칭: text-xs(12) / text-sm(14) / text-base(16) / text-xl(20) / text-2xl(24) / text-3xl(30~32)
export const TYPE_SCALE = {
  xs:   "12px",
  sm:   "14px",
  base: "16px",
  lg:   "20px",
  xl:   "24px",
  xxl:  "32px",
};
