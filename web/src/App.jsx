import React, { useState } from 'react';
import CoverPage from './components/CoverPage';
import ArticlePage from './components/ArticlePage';
import InsightPage from './components/InsightPage';

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

const PAGES = ['표지', '기사', '인사이트'];

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
      </div>
    );
  }

  const [page, setPage] = useState('표지');

  return (
    <div className="min-h-screen bg-gray-200 py-8">
      <div className="no-print flex justify-center gap-2 mb-6">
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

      {page === '표지'     && <CoverPage   coverData={SAMPLE_COVER} />}
      {page === '기사'     && <ArticlePage pageData={SAMPLE_ARTICLE} />}
      {page === '인사이트' && <InsightPage insightData={SAMPLE_INSIGHT} />}
    </div>
  );
}
