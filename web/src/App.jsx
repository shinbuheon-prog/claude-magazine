import React, { useState } from 'react';
import CoverPage from './components/CoverPage';
import ArticlePage from './components/ArticlePage';
import InsightPage from './components/InsightPage';
import InterviewPage from './components/InterviewPage';
import ReviewPage from './components/ReviewPage';
import FeaturePage from './components/FeaturePage';
import DashboardPage from './pages/DashboardPage';
import DraftListPage from './pages/admin/DraftListPage';
import DraftReviewPage from './pages/admin/DraftReviewPage';
import PublishHistoryPage from './pages/admin/PublishHistoryPage';

const SAMPLE_COVER = {
  issue: 'VOL.01',
  date: '2026년 5월',
  headline: 'Claude 4 시대, 실무는 어떻게 바뀌는가',
  subline: '에이전트, 컨텍스트, 비용 최적화의 실전 분석',
  tag: '특집',
};

const SAMPLE_ARTICLE = {
  category: 'DEEP DIVE',
  pageNum: '01',
  title: 'Claude Sonnet 4.6, 실무에서 무엇이 달라졌는가',
  infoTable: [
    { label: '모델 ID', value: 'claude-sonnet-4-6' },
    { label: '입력 단가', value: '$3 / MTok' },
    { label: '출력 단가', value: '$15 / MTok' },
    { label: '컨텍스트', value: '200K (1M 베타)' },
    { label: 'Batch 할인', value: '50%' },
  ],
  quote: 'effort=medium 설정 하나로 비용과 속도의 균형점을 잡을 수 있게 됐다.',
  barData: { leftLabel: '기사 브리프/초안', rightLabel: '사내 리포트', leftPct: 75 },
  bullets: [
    '기사 브리프/초안 생성에 최적화된 비용 대비 성능',
    'Batch API 사용 시 대량 처리 비용 50% 절감',
    '1M 컨텍스트 베타는 대형 PDF 분석에 유의미',
  ],
  sourceId: 'src-001',
  sourceNote: 'Anthropic 공식 가격 문서, 2026-04-20',
};

const SAMPLE_INSIGHT = {
  insightNum: '01',
  title: 'Claude API 비용 추이 분석 (2024-2026)',
  chartData: [
    { year: "'24 Q1", sonnet: 15, opus: 75 },
    { year: "'24 Q3", sonnet: 15, opus: 75 },
    { year: "'25 Q1", sonnet: 15, opus: 60 },
    { year: "'25 Q3", sonnet: 15, opus: 50 },
    { year: "'26 Q1", sonnet: 15, opus: 25 },
  ],
  statA: { label: 'Sonnet 출력 단가', value: '$15', unit: '3년간 동결' },
  statB: { label: 'Opus 출력 단가', value: '$25', unit: '큰 폭 인하' },
  expertTip: '모델 비용보다 병렬 실행과 구독 운영이 실제 병목이다. Batch API와 effort 조절로 비용을 충분히 제어할 수 있다.',
  sourceId: 'src-003',
};

const SAMPLE_INTERVIEW = {
  interviewNum: '01',
  subject: '김지훈',
  role: 'AI 프로덕트 엔지니어',
  company: 'Classmethod Korea',
  quote: 'Claude Code는 단순한 AI 비서가 아니라 협업 엔지니어에 가깝습니다.',
  portraitUrl: '/covers/default.png',
  qa: [
    {
      q: 'Claude Code를 실무에 넣으면서 가장 크게 바뀐 점은 무엇인가요?',
      a: '리뷰와 테스트 루프가 빨라졌고, PR 머지까지의 평균 시간이 크게 줄었습니다.',
      sourceId: 'src-interview-001',
    },
    {
      q: '하루 업무에서 Claude를 어떻게 쓰나요?',
      a: '스탠드업 직후 이슈와 PR을 요약시키고, MCP 기반으로 문서와 저장소를 같이 보게 합니다.',
      sourceId: 'src-interview-002',
    },
  ],
  sourceId: 'src-interview-001',
};

const SAMPLE_REVIEW = {
  category: 'DEV TOOLS',
  productName: 'Claude Code',
  verdict: '에디터 추천',
  overallScore: 8.6,
  summary: '협업형 AI 코딩 에이전트로서 강한 기본기',
  criteria: [
    { name: '사용성', score: 9, note: '직관적인 CLI' },
    { name: '비용 효율', score: 7, note: 'Pro 플랜 필요' },
    { name: '확장성', score: 9, note: 'MCP 서버 지원' },
    { name: '안정성', score: 8, note: '로그인 세션 이슈 적음' },
    { name: '문서성', score: 9, note: '공식 가이드 충실' },
  ],
  prosText: [
    '실제 워크플로우에 즉시 통합되는 라이브 CLI 경험',
    'MCP 생태계로 내부 도구와 데이터 연결이 자연스럽다',
    '대형 코드베이스 분석에 강하다',
  ],
  consText: [
    'Pro 이상 구독 전제가 필요하다',
    '고급 워크플로우는 학습곡선이 있다',
  ],
  competitorTable: [
    { name: 'Claude Code', price: '$20/mo', rating: '8.6' },
    { name: 'GitHub Copilot', price: '$10/mo', rating: '7.8' },
    { name: 'Cursor', price: '$20/mo', rating: '8.2' },
    { name: 'Windsurf', price: '$15/mo', rating: '7.5' },
  ],
  sourceId: 'src-review-001',
};

const SAMPLE_FEATURE = {
  category: 'FEATURE',
  issueTag: 'Cover Story',
  title: 'Claude 4 시대, 우리는 무엇을 다시 배워야 하는가',
  lede: '에이전트가 코드를 짜고, 컨텍스트가 창의력의 한계를 밀어내는 시대. 실무자는 무엇을 버리고 무엇을 새로 익혀야 할까.',
  author: 'Claude Magazine 편집팀',
  sections: [
    {
      heading: '1. 컨텍스트는 더 이상 희소 자원이 아니다',
      body: '중요한 것은 무엇을 넣느냐보다 무엇을 강조하느냐다. 이제 실무는 컨텍스트 큐레이션의 문제에 가깝다.',
      pullQuote: '문제를 더 많이 넣는 것이 아니라, 무엇을 강조할지 고르는 일이 중요해졌다.',
      image: '/covers/default.png',
    },
    {
      heading: '2. 에이전트는 주니어가 아니라 협업 파트너다',
      body: 'AI는 산출물을 내는 도구를 넘어 테스트, 리뷰, 요약을 병렬로 처리하는 작업자에 가깝다.',
      pullQuote: '위임이 아니라 공동 작업에 가깝다.',
    },
  ],
  sourceIds: ['src-001', 'src-003', 'src-interview-001', 'src-review-001'],
};

const PAGES = ['표지', '기사', '인사이트', '인터뷰', '리뷰', '특집', '대시보드'];

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const isPrint = params.has('print');
  const isAdmin = params.has('admin');

  const [page, setPage] = useState('표지');
  const [adminView, setAdminView] = useState(params.get('view') || 'drafts');
  const [activeArticleId, setActiveArticleId] = useState(params.get('article') || '');

  function navigateAdmin(nextView, nextArticleId = '') {
    const next = new URLSearchParams(window.location.search);
    next.set('admin', '1');
    next.set('view', nextView);
    if (nextArticleId) {
      next.set('article', nextArticleId);
    } else {
      next.delete('article');
    }
    window.history.replaceState({}, '', `${window.location.pathname}?${next.toString()}`);
    setAdminView(nextView);
    setActiveArticleId(nextArticleId);
  }

  if (isAdmin) {
    if (adminView === 'review' && activeArticleId) {
      return (
        <DraftReviewPage
          articleId={activeArticleId}
          onBack={() => navigateAdmin('drafts')}
          onOpenHistory={() => navigateAdmin('history')}
        />
      );
    }

    if (adminView === 'history') {
      return <PublishHistoryPage onBack={() => navigateAdmin('drafts')} />;
    }

    if (adminView === 'dashboard') {
      return <DashboardPage />;
    }

    return (
      <DraftListPage
        onOpenDraft={(articleId) => navigateAdmin('review', articleId)}
        onOpenHistory={() => navigateAdmin('history')}
        onOpenDashboard={() => navigateAdmin('dashboard')}
      />
    );
  }

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

  return (
    <div className="min-h-screen bg-gray-200 py-8">
      <div className="no-print mb-6 flex flex-wrap justify-center gap-2">
        {PAGES.map((p) => (
          <button
            key={p}
            onClick={() => setPage(p)}
            className={`rounded-full px-5 py-2 text-sm font-bold transition-all ${
              page === p ? 'bg-[#1B1F3B] text-white' : 'bg-white text-gray-500 hover:bg-gray-100'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {page === '표지' && <CoverPage coverData={SAMPLE_COVER} />}
      {page === '기사' && <ArticlePage pageData={SAMPLE_ARTICLE} />}
      {page === '인사이트' && <InsightPage insightData={SAMPLE_INSIGHT} />}
      {page === '인터뷰' && <InterviewPage interviewData={SAMPLE_INTERVIEW} />}
      {page === '리뷰' && <ReviewPage reviewData={SAMPLE_REVIEW} />}
      {page === '특집' && <FeaturePage featureData={SAMPLE_FEATURE} />}
      {page === '대시보드' && <DashboardPage />}
    </div>
  );
}
