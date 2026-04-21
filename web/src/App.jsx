import React, { useState } from 'react';
import CoverPage from './components/CoverPage';
import ArticlePage from './components/ArticlePage';
import InsightPage from './components/InsightPage';
import InterviewPage from './components/InterviewPage';
import ReviewPage from './components/ReviewPage';
import FeaturePage from './components/FeaturePage';

const SAMPLE_COVER = {
  issue: "VOL.01",
  date: "2026년 5월",
  headline: "Claude 4 시대의\n실무 전략",
  subline: "에이전트·컨텍스트·비용 최적화 완전 분석",
  tag: "특집",
};

const SAMPLE_ARTICLE = {
  category: "DEEP DIVE",
  pageNum: "01",
  title: "Claude Sonnet 4.6, 실무에서 어떻게 쓸 것인가",
  infoTable: [
    { label: "모델 ID", value: "claude-sonnet-4-6" },
    { label: "입력 단가", value: "$3 / MTok" },
    { label: "출력 단가", value: "$15 / MTok" },
    { label: "컨텍스트", value: "200K (1M 베타)" },
    { label: "Batch 할인", value: "50%" },
  ],
  quote: "effort=medium 설정 하나로 비용을 절감하면서 품질을 유지할 수 있다.",
  barData: { leftLabel: "기사 브리프·초안", rightLabel: "심층 리포트", leftPct: 75 },
  bullets: [
    "기사 브리프·초안 생성에 최적화된 비용·속도 균형",
    "Batch API 활용 시 야간 대량 처리 비용 50% 절감",
    "1M 컨텍스트 베타: 대형 PDF 분석에 선택 적용",
  ],
  sourceId: "src-001",
  sourceNote: "Anthropic 공식 가격 문서, 2026-04-20",
};

const SAMPLE_INSIGHT = {
  insightNum: "01",
  title: "Claude API 비용 추이 분석 (2024-2026)",
  chartData: [
    { year: "'24 Q1", sonnet: 15, opus: 75 },
    { year: "'24 Q3", sonnet: 15, opus: 75 },
    { year: "'25 Q1", sonnet: 15, opus: 60 },
    { year: "'25 Q3", sonnet: 15, opus: 50 },
    { year: "'26 Q1", sonnet: 15, opus: 25 },
  ],
  statA: { label: "Sonnet 출력 단가", value: "$15", unit: "3년간 동결" },
  statB: { label: "Opus 출력 단가", value: "$25", unit: "↓ 지속 하락" },
  expertTip: "모델 비용보다 사람 시간과 구독 운영이 실제 병목입니다. Batch API와 effort 조절로 API 비용은 충분히 통제 가능합니다.",
  sourceId: "src-003",
};

const SAMPLE_INTERVIEW = {
  interviewNum: "01",
  subject: "김지우",
  role: "AI 엔지니어링 리드",
  company: "Classmethod Korea",
  quote: "Claude Code는 단순한 AI 비서가 아니라 시니어 엔지니어의 두 번째 두뇌입니다.",
  portraitUrl: "/covers/default.png",
  qa: [
    {
      q: "Claude Code를 실무에 도입하면서 가장 크게 바뀐 점은 무엇인가요?",
      a: "코드 리뷰 사이클이 절반으로 줄었습니다. 에이전트가 린트·타입·테스트 스모크를 먼저 통과시키기 때문에 사람 리뷰어는 설계와 트레이드오프에만 집중할 수 있어요. 결과적으로 PR 머지까지의 리드타임이 평균 3.2일에서 1.5일로 단축됐습니다.",
      sourceId: "src-interview-001",
    },
    {
      q: "하루 업무에서 Claude를 어떻게 활용하시나요?",
      a: "아침 스탠드업 직후 에이전트에게 어제 남은 PR·이슈 요약을 맡기고, 오후에는 MCP로 연결된 내부 문서를 기반으로 설계 초안을 씁니다. 긴 글쓰기보다 반복 구조가 있는 리팩터링에서 특히 생산성이 크게 올라갑니다.",
      sourceId: "src-interview-002",
    },
    {
      q: "주니어 엔지니어에게 추천하는 사용 습관이 있다면?",
      a: "명세를 먼저 쓰고, 에이전트에게 스켈레톤과 테스트부터 뽑게 하세요. 완성 코드를 받아쓰지 말고, 실패한 테스트를 보면서 '왜 실패했는가'를 직접 추적하는 훈련을 해야 실력이 늡니다. AI는 속도를 주지만 이해는 사람이 쌓아야 합니다.",
      sourceId: "src-interview-003",
    },
  ],
  sourceId: "src-interview-001",
};

const SAMPLE_REVIEW = {
  category: "DEV TOOLS",
  productName: "Claude Code",
  verdict: "에디터 추천",
  overallScore: 8.6,
  summary: "터미널 기반 AI 코딩 에이전트의 새로운 기준",
  criteria: [
    { name: "사용성",    score: 9, note: "직관적 CLI" },
    { name: "비용 효율", score: 7, note: "Pro 플랜 필요" },
    { name: "확장성",    score: 9, note: "MCP 서버 지원" },
    { name: "신뢰성",    score: 8, note: "롱런 세션 안정" },
    { name: "문서화",    score: 9, note: "공식 가이드 충실" },
  ],
  prosText: [
    "터미널 워크플로와 즉시 통합되는 네이티브 CLI 경험",
    "MCP 생태계로 외부 도구·DB·API까지 자연스럽게 확장",
    "롱 컨텍스트(1M) 지원으로 대형 코드베이스 분석 가능",
  ],
  consText: [
    "Pro 이상 구독이 사실상 필수 (월 $20~)",
    "고급 워크플로(에이전트 체이닝)는 학습 곡선이 존재",
  ],
  competitorTable: [
    { name: "Claude Code",    price: "$20/mo", rating: "8.6" },
    { name: "GitHub Copilot", price: "$10/mo", rating: "7.8" },
    { name: "Cursor",         price: "$20/mo", rating: "8.2" },
    { name: "Windsurf",       price: "$15/mo", rating: "7.5" },
  ],
  sourceId: "src-review-001",
};

const SAMPLE_FEATURE = {
  category: "FEATURE",
  issueTag: "Cover Story",
  title: "Claude 4 시대, 우리는 무엇을 다시 배워야 하는가",
  lede: "에이전트가 코드를 쓰고, 컨텍스트가 책 한 권을 삼키는 시대. 실무자들은 지난 1년간 어떤 습관을 버리고 어떤 감각을 새로 갖추게 되었는가.",
  author: "Claude Magazine 편집팀",
  sections: [
    {
      heading: "1. 컨텍스트는 더 이상 희소 자원이 아니다",
      body: "2024년까지만 해도 프롬프트 엔지니어의 핵심 업무는 '무엇을 잘라낼 것인가'였다. 토큰은 비쌌고, 맥락은 부족했으며, 요약은 반드시 지불해야 할 세금이었다. 그러나 1M 컨텍스트가 일상이 된 지금, 문제는 반대가 되었다. 넣을 수 있는 모든 것을 넣었을 때, 모델이 정말로 중요한 몇 줄에 집중하도록 만드는 기술, 즉 '컨텍스트 큐레이션'이 새로운 핵심 역량으로 떠올랐다. 실무자들은 이제 무엇을 넣을지가 아니라 무엇을 강조할지를 고민한다.",
      pullQuote: "문제는 넣을 수 없는 것이 아니라, 넣은 것들 중 무엇에 주목시킬 것인가가 되었다.",
      image: "/covers/default.png",
    },
    {
      heading: "2. 에이전트는 주니어가 아니라 동료다",
      body: "초기의 AI 코딩 도구는 '빠른 주니어' 비유로 설명되었다. 시키면 하고, 실수하면 고치게 하는 존재. 그러나 Claude Code처럼 긴 세션을 유지하면서 테스트·린트·문서화를 스스로 연쇄 수행하는 에이전트가 등장하자 비유가 무너졌다. 실무자들은 에이전트를 '검토받을 산출물을 내는 동료'로 다루기 시작했다. 역할은 위임이 아니라 공동 저자에 가깝다. 코드 리뷰에서 사람이 찾아야 할 것은 버그가 아니라 트레이드오프다.",
      pullQuote: "위임이 아니다. 공동 저자다.",
    },
    {
      heading: "3. 비용은 모델 단가가 아니라 사람 시간이다",
      body: "Sonnet 출력 단가는 3년째 동결, Opus는 지속 하락. 그러나 조직의 월간 AI 지출은 오히려 늘었다. 이유는 단순하다. 사람들이 더 많이, 더 깊이 쓰기 때문이다. 실무팀이 추적해야 할 지표는 토큰 단가가 아니라 '한 명의 엔지니어가 일주일에 AI를 통해 절감한 반복 작업 시간'이다. 이 값이 구독료의 5배를 넘지 않는다면, 문제는 모델이 아니라 워크플로에 있다.",
      pullQuote: "구독료의 5배를 넘지 못하는 절감은, 모델이 아니라 워크플로의 실패다.",
    },
  ],
  sourceIds: ["src-001", "src-003", "src-interview-001", "src-review-001"],
};

const PAGES = ['표지', '기사', '인사이트', '인터뷰', '리뷰', '특집'];

export default function App() {
  // ?print=1 → 전체 페이지 순서대로 렌더 (Puppeteer PDF 전용)
  const isPrint = new URLSearchParams(window.location.search).has('print');

  if (isPrint) {
    return (
      <div>
        <div className="print-page">
          <CoverPage coverData={SAMPLE_COVER} />
        </div>
        <div className="print-page">
          <ArticlePage pageData={SAMPLE_ARTICLE} />
        </div>
        <div className="print-page">
          <InsightPage insightData={SAMPLE_INSIGHT} />
        </div>
        <div className="print-page">
          <InterviewPage interviewData={SAMPLE_INTERVIEW} />
        </div>
        <div className="print-page">
          <ReviewPage reviewData={SAMPLE_REVIEW} />
        </div>
        <div className="print-page">
          <FeaturePage featureData={SAMPLE_FEATURE} />
        </div>
      </div>
    );
  }

  const [page, setPage] = useState('표지');

  return (
    <div className="min-h-screen bg-gray-200 py-8">
      <div className="no-print flex justify-center gap-2 mb-6 flex-wrap">
        {PAGES.map((p) => (
          <button
            key={p}
            onClick={() => setPage(p)}
            className={`px-5 py-2 rounded-full text-sm font-bold transition-all ${
              page === p
                ? 'bg-[#1B1F3B] text-white'
                : 'bg-white text-gray-500 hover:bg-gray-100'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {page === '표지'     && <CoverPage     coverData={SAMPLE_COVER} />}
      {page === '기사'     && <ArticlePage   pageData={SAMPLE_ARTICLE} />}
      {page === '인사이트' && <InsightPage   insightData={SAMPLE_INSIGHT} />}
      {page === '인터뷰'   && <InterviewPage interviewData={SAMPLE_INTERVIEW} />}
      {page === '리뷰'     && <ReviewPage    reviewData={SAMPLE_REVIEW} />}
      {page === '특집'     && <FeaturePage   featureData={SAMPLE_FEATURE} />}
    </div>
  );
}
