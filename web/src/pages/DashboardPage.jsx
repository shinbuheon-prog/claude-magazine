import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { STATUS, THEME, TYPE } from '../theme';

const EMPTY_METRICS = {
  period: { days: 30 },
  sources: { ghost: false, langfuse: false },
  cost: { total_usd: 0, total_krw: 0, per_article_usd: 0, article_count: 0, model_distribution: [] },
  time: { ai_total_sec: 0, editor_total_sec: 0, ai_editor_ratio: null, editor_time_estimated: true },
  quality: { lint_pass_rate: null, lint_pass_count: 0, lint_checked_articles: 0, factcheck_failures: 0, corrections_total: 0 },
  reach: { published_articles: 0, newsletter_recipients: 0, available: { ghost: false } },
  operations: { publish_runs: 0, publish_failures: 0 },
  cache: {
    fact_checker: {
      runs: 0,
      runs_with_cache_enabled: 0,
      total_cache_creation_tokens: 0,
      total_cache_read_tokens: 0,
      cache_hit_rate: 0,
      estimated_saved_usd: 0,
      trend_14d: [],
    },
    other_pipelines: [],
  },
  citations: {
    article_runs_with_citations_check: 0,
    pass: 0,
    warn_missing: 0,
    warn_mismatch: 0,
    fail: 0,
    pass_rate: null,
    trend_14d: [],
  },
  illustration: {
    provider_distribution: {},
    monthly_cost_usd: 0,
    monthly_cost_by_provider: {},
    budget_cap_usd: 5,
    budget_utilization: 0,
  },
  per_article: [],
};

const METRIC_PATHS = [
  () => new URLSearchParams(window.location.search).get('metrics'),
  () => '/metrics.json',
  () => '/output/metrics.json',
  () => '/output/task028_metrics.json',
];

function formatUsd(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function formatPercent(value) {
  if (value == null) return 'n/a';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatSeconds(value) {
  const seconds = Number(value || 0);
  if (seconds >= 3600) return `${(seconds / 3600).toFixed(1)}h`;
  if (seconds >= 60) return `${(seconds / 60).toFixed(1)}m`;
  return `${seconds.toFixed(0)}s`;
}

function availabilityLabel(enabled, yes = 'live', no = 'partial') {
  return enabled ? yes : no;
}

function StatCard({ label, value, hint, tone = 'default' }) {
  const toneClass =
    tone === 'accent'
      ? 'border-[#C96442] bg-[#FFF4EF]'
      : tone === 'warning'
        ? 'border-[#D97706] bg-[#FFF7ED]'
        : 'border-gray-200 bg-white';
  return (
    <div className={`rounded-3xl border p-6 shadow-sm ${toneClass}`}>
      <p className="text-xs font-bold uppercase tracking-[0.25em] text-gray-400">{label}</p>
      <p className="mt-4 text-4xl font-black tracking-tight text-[#1B1F3B]">{value}</p>
      <p className="mt-3 text-sm leading-relaxed text-gray-500">{hint}</p>
    </div>
  );
}

function Panel({ title, kicker, children, aside }) {
  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-[#C96442]">{kicker}</p>
          <h3 className="mt-2 text-2xl font-black tracking-tight text-[#1B1F3B]">{title}</h3>
        </div>
        {aside ? <div className="text-right text-xs text-gray-400">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

function ProgressBar({ value, color }) {
  const pct = Math.max(0, Math.min(Number(value || 0), 1));
  return (
    <div className="h-3 w-full overflow-hidden rounded-full bg-gray-100">
      <div className="h-full transition-all" style={{ width: `${pct * 100}%`, backgroundColor: color }} />
    </div>
  );
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(EMPTY_METRICS);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('No metrics file found. Export partial data first.');

  useEffect(() => {
    let cancelled = false;

    async function loadMetrics() {
      setLoading(true);
      const candidates = METRIC_PATHS.map((getPath) => getPath()).filter(Boolean);

      for (const path of candidates) {
        try {
          const response = await fetch(path, { cache: 'no-store' });
          if (!response.ok) continue;
          const data = await response.json();
          if (!cancelled) {
            setMetrics({ ...EMPTY_METRICS, ...data });
            setStatus(`Loaded from ${path}`);
          }
          return;
        } catch (_error) {
          // Try the next candidate.
        }
      }

      if (!cancelled) {
        setMetrics(EMPTY_METRICS);
      }
    }

    loadMetrics().finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const costTrend = useMemo(
    () =>
      (metrics.per_article || []).map((item, index) => ({
        name: item.topic || item.article_id || `Article ${index + 1}`,
        shortName: item.article_id ? item.article_id.slice(-6) : `#${index + 1}`,
        cost_usd: Number(item.cost_usd || 0),
        ai_time_sec: Number(item.ai_time_sec || 0),
      })),
    [metrics.per_article],
  );

  const qualityBars = useMemo(() => {
    const lintPassRate = metrics.quality?.lint_pass_rate;
    const lintPct = lintPassRate == null ? 0 : Math.round(lintPassRate * 100);
    const failPct = Math.max(0, 100 - lintPct);
    return [
      { name: 'Lint pass', value: lintPct, fill: THEME.lineC },
      { name: 'Lint fail', value: failPct, fill: THEME.accent },
      { name: 'Factcheck issues', value: Number(metrics.quality?.factcheck_failures || 0), fill: THEME.lineB },
    ];
  }, [metrics.quality]);

  const cacheTrend = useMemo(
    () =>
      (metrics.cache?.fact_checker?.trend_14d || []).map((row) => ({
        date: row.date?.slice(5) || '',
        hit_rate: Number(row.hit_rate || 0) * 100,
        total: Number(row.total || 0),
      })),
    [metrics.cache],
  );

  const citationsPie = useMemo(
    () => [
      { name: 'Pass', value: Number(metrics.citations?.pass || 0), fill: THEME.lineC },
      { name: 'Warn missing', value: Number(metrics.citations?.warn_missing || 0), fill: STATUS.warning },
      { name: 'Warn mismatch', value: Number(metrics.citations?.warn_mismatch || 0), fill: THEME.lineB },
      { name: 'Fail', value: Number(metrics.citations?.fail || 0), fill: STATUS.danger },
    ],
    [metrics.citations],
  );

  const citationsTrend = useMemo(
    () =>
      (metrics.citations?.trend_14d || []).map((row) => ({
        date: row.date?.slice(5) || '',
        pass: Number(row.pass || 0),
        warn: Number(row.warn_missing || 0) + Number(row.warn_mismatch || 0),
        fail: Number(row.fail || 0),
      })),
    [metrics.citations],
  );

  const illustrationProviders = useMemo(
    () =>
      Object.entries(metrics.illustration?.provider_distribution || {}).map(([provider, count]) => ({
        provider,
        count: Number(count || 0),
      })),
    [metrics.illustration],
  );

  const utilization = Number(metrics.illustration?.budget_utilization || 0);
  const utilizationTone = utilization >= 0.8 ? 'warning' : 'default';
  const utilizationColor = utilization >= 0.8 ? STATUS.warning : THEME.lineC;
  const ratioValue =
    metrics.time?.ai_editor_ratio == null ? 'n/a' : `1:${Number(metrics.time.ai_editor_ratio).toFixed(2)}`;

  return (
    <div className="mx-auto max-w-[1180px] px-4 py-10">
      <header className="mb-8 overflow-hidden rounded-[36px] border border-[#D8D1C4] bg-[linear-gradient(135deg,#f8f7f4_0%,#ece6da_48%,#f7efe5_100%)] p-8 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-2xl">
            <p className={`${TYPE.category} text-[#C96442]`}>Operations Dashboard</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight text-[#1B1F3B]">Claude Magazine 운영 대시보드</h1>
            <p className="mt-4 max-w-xl text-sm leading-7 text-gray-600">
              로그와 산출물만으로도 비용, 게이트 품질, 캐시 효율, citations 경고 추세, 일러스트 예산 상태를 한눈에 보도록
              정리했습니다.
            </p>
          </div>
          <div className="rounded-3xl border border-white/70 bg-white/70 px-5 py-4 text-right text-sm text-gray-600 backdrop-blur">
            <p className="font-semibold text-[#1B1F3B]">{metrics.period?.days || 30}일 보기</p>
            <p className="mt-1">{loading ? 'Loading...' : status}</p>
            <p className="mt-2 text-xs uppercase tracking-[0.22em] text-gray-400">
              Ghost {availabilityLabel(metrics.reach?.available?.ghost)}
              {' · '}
              Langfuse {availabilityLabel(metrics.sources?.langfuse)}
            </p>
          </div>
        </div>
      </header>

      <div className="grid gap-5 md:grid-cols-3">
        <StatCard
          label="Cost / Article"
          value={formatUsd(metrics.cost?.per_article_usd)}
          hint={`${metrics.cost?.article_count || 0} articles in window`}
        />
        <StatCard
          label="AI : Human"
          value={ratioValue}
          hint={`AI ${formatSeconds(metrics.time?.ai_total_sec)} vs editor ${formatSeconds(metrics.time?.editor_total_sec)}`}
          tone="accent"
        />
        <StatCard
          label="Monthly API Cost"
          value={formatUsd(metrics.cost?.total_usd)}
          hint={`₩${Number(metrics.cost?.total_krw || 0).toLocaleString('ko-KR')}`}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Panel title="기사별 비용 추이" kicker="Cost" aside={`${costTrend.length} articles`}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={costTrend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ECE7DC" />
                <XAxis dataKey="shortName" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                <Tooltip formatter={(value) => [formatUsd(value), 'Cost']} />
                <Legend />
                <Line type="monotone" dataKey="cost_usd" name="Cost (USD)" stroke={THEME.accent} strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="모델별 비용 분포" kicker="Model Mix" aside={metrics.cost?.estimated ? 'estimated pricing' : 'live pricing'}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={metrics.cost?.model_distribution || []}
                  dataKey="cost_usd"
                  nameKey="model"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                >
                  {(metrics.cost?.model_distribution || []).map((entry, index) => (
                    <Cell
                      key={entry.model}
                      fill={[THEME.accent, THEME.lineB, THEME.lineC, THEME.primary][index % 4]}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [formatUsd(value), 'Cost']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Panel title="품질 게이트" kicker="Quality" aside={`${metrics.quality?.lint_checked_articles || 0} checked`}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={qualityBars}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ECE7DC" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {qualityBars.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Reach + Operations" kicker="Signals" aside={metrics.reach?.available?.ghost ? 'ghost connected' : 'local logs only'}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl bg-[#F8F7F4] p-5">
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-gray-400">Reach</p>
              <p className="mt-3 text-3xl font-black text-[#1B1F3B]">{metrics.reach?.published_articles || 0}</p>
              <p className="mt-2 text-sm text-gray-500">published articles</p>
              <p className="mt-4 text-sm text-gray-500">Newsletter recipients: {metrics.reach?.newsletter_recipients || 0}</p>
            </div>
            <div className="rounded-2xl bg-[#FFF4EF] p-5">
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-gray-400">Operations</p>
              <p className="mt-3 text-3xl font-black text-[#1B1F3B]">{metrics.operations?.publish_runs || 0}</p>
              <p className="mt-2 text-sm text-gray-500">publish runs</p>
              <p className="mt-4 text-sm text-gray-500">Failures: {metrics.operations?.publish_failures || 0}</p>
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel
          title="Prompt Caching"
          kicker="Cache"
          aside={`${metrics.cache?.fact_checker?.runs_with_cache_enabled || 0}/${metrics.cache?.fact_checker?.runs || 0} cached`}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <StatCard
              label="Hit Rate"
              value={formatPercent(metrics.cache?.fact_checker?.cache_hit_rate)}
              hint={`${Number(metrics.cache?.fact_checker?.total_cache_read_tokens || 0).toLocaleString('ko-KR')} cache-read tokens`}
            />
            <StatCard
              label="Saved USD"
              value={formatUsd(metrics.cache?.fact_checker?.estimated_saved_usd)}
              hint={`${Number(metrics.cache?.fact_checker?.total_cache_creation_tokens || 0).toLocaleString('ko-KR')} cache-create tokens`}
            />
          </div>
          <div className="mt-5 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={cacheTrend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ECE7DC" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                <Tooltip formatter={(value, name) => [name === 'hit_rate' ? `${Number(value).toFixed(1)}%` : value, name]} />
                <Legend />
                <Line type="monotone" dataKey="hit_rate" name="Hit rate %" stroke={THEME.lineC} strokeWidth={3} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid gap-2 text-sm text-gray-500">
            {(metrics.cache?.other_pipelines || []).map((item) => (
              <p key={item.pipeline}>
                {item.pipeline}: {item.cache_enabled_runs}/{item.runs} cache-enabled runs
              </p>
            ))}
          </div>
        </Panel>

        <Panel
          title="Citations Cross-Check"
          kicker="Citations"
          aside={`${metrics.citations?.article_runs_with_citations_check || 0} article runs`}
        >
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={citationsPie} dataKey="value" nameKey="name" innerRadius={48} outerRadius={78} paddingAngle={2}>
                    {citationsPie.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={citationsTrend}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ECE7DC" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="pass" stackId="citations" fill={THEME.lineC} radius={[6, 6, 0, 0]} />
                  <Bar dataKey="warn" stackId="citations" fill={STATUS.warning} />
                  <Bar dataKey="fail" stackId="citations" fill={STATUS.danger} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <p className="mt-4 text-sm text-gray-500">Pass rate: {formatPercent(metrics.citations?.pass_rate)}</p>
        </Panel>
      </div>

      <div className="mt-6">
        <Panel
          title="Illustration Budget"
          kicker="Illustration"
          aside={utilization >= 0.8 ? 'budget warning' : 'within cap'}
        >
          <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
            <div className="space-y-4">
              <StatCard
                label="Monthly Cost"
                value={formatUsd(metrics.illustration?.monthly_cost_usd)}
                hint={`Cap ${formatUsd(metrics.illustration?.budget_cap_usd)}`}
                tone={utilizationTone}
              />
              <div className="rounded-3xl border border-gray-200 bg-white p-5">
                <div className="mb-2 flex items-center justify-between text-sm text-gray-500">
                  <span>Budget utilization</span>
                  <span style={{ color: utilizationColor }}>{formatPercent(metrics.illustration?.budget_utilization)}</span>
                </div>
                <ProgressBar value={metrics.illustration?.budget_utilization} color={utilizationColor} />
              </div>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={illustrationProviders}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ECE7DC" />
                  <XAxis dataKey="provider" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#6B7280' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#9CA3AF' }} />
                  <Tooltip />
                  <Bar dataKey="count" fill={utilizationColor} radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Panel>
      </div>

      <Panel
        title="기사별 상세"
        kicker="Per Article"
        aside={metrics.time?.editor_time_estimated ? 'editor time is estimated from git/file timestamps' : 'editor time from git'}
      >
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-y-2 text-left">
            <thead>
              <tr className="text-xs uppercase tracking-[0.18em] text-gray-400">
                <th className="pb-2 pr-4">Article</th>
                <th className="pb-2 pr-4">Cost</th>
                <th className="pb-2 pr-4">AI Time</th>
                <th className="pb-2 pr-4">Editor Time</th>
                <th className="pb-2 pr-4">Ratio</th>
                <th className="pb-2 pr-4">Lint</th>
                <th className="pb-2">Publish</th>
              </tr>
            </thead>
            <tbody>
              {(metrics.per_article || []).map((item) => (
                <tr key={item.article_id} className="rounded-2xl bg-[#FBFAF7] text-sm text-gray-700">
                  <td className="rounded-l-2xl px-4 py-3">
                    <p className="font-semibold text-[#1B1F3B]">{item.topic || item.article_id}</p>
                    <p className="text-xs text-gray-400">{item.article_id}</p>
                  </td>
                  <td className="px-4 py-3">{formatUsd(item.cost_usd)}</td>
                  <td className="px-4 py-3">{formatSeconds(item.ai_time_sec)}</td>
                  <td className="px-4 py-3">
                    {formatSeconds(item.editor_time_sec)}
                    {item.editor_time_estimated ? <span className="ml-2 text-xs text-gray-400">est.</span> : null}
                  </td>
                  <td className="px-4 py-3">{item.ai_editor_ratio == null ? 'n/a' : `1:${item.ai_editor_ratio}`}</td>
                  <td className="px-4 py-3">{item.lint_pass == null ? 'n/a' : item.lint_pass ? 'pass' : 'fail'}</td>
                  <td className="rounded-r-2xl px-4 py-3">{item.publish_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <MonthlyProgressWidget />
    </div>
  );
}

function MonthlyProgressWidget() {
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState(null);
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  useEffect(() => {
    fetch(`/issue/${month}.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status}`);
        return response.json();
      })
      .then(setPlan)
      .catch((err) => setError(err.message));
  }, [month]);

  const counts = useMemo(() => {
    if (!plan?.articles) return {};
    const next = {};
    plan.articles.forEach((article) => {
      const key = article.status || 'planning';
      next[key] = (next[key] || 0) + 1;
    });
    return next;
  }, [plan]);

  const total = plan?.articles?.length || 0;
  const published = counts.published || 0;
  const progressPct = total ? (published / total) * 100 : 0;

  const statusOrder = [
    ['published', '발행 완료', '#10B981'],
    ['approved', '승인 대기', '#059669'],
    ['lint', 'lint', '#FBBF24'],
    ['fact_check', '팩트체크', '#F97316'],
    ['draft', '초안', '#3B82F6'],
    ['brief', '브리프', '#9CA3AF'],
    ['planning', '기획', '#6B7280'],
  ];

  return (
    <Panel title={`월간 발행 진행률 · ${month}`} kicker="TASK_037">
      <div className="mb-4 flex items-center gap-3">
        <input
          type="text"
          value={month}
          onChange={(event) => setMonth(event.target.value)}
          placeholder="YYYY-MM"
          className="rounded-lg border border-gray-200 px-3 py-1 text-sm"
        />
        {plan && <span className="text-xs text-gray-500">{plan.theme}</span>}
      </div>

      {error && (
        <p className="text-sm text-gray-400">
          이슈 JSON이 없습니다 (<code>/issue/{month}.json</code>). 월간 계획을 먼저 생성해야 합니다.
        </p>
      )}

      {plan && (
        <>
          <div className="mb-6">
            <div className="mb-1 flex justify-between text-xs text-gray-500">
              <span>Progress</span>
              <span>
                {published}/{total} published · {progressPct.toFixed(1)}%
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-gray-100">
              <div className="h-full transition-all" style={{ width: `${progressPct}%`, backgroundColor: THEME.accent }} />
            </div>
          </div>

          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            {statusOrder.map(([key, label, color]) => (
              <div key={key} className="rounded-2xl border border-gray-100 p-3">
                <p className="text-xs text-gray-400">{label}</p>
                <p className="mt-1 text-2xl font-black" style={{ color }}>
                  {counts[key] || 0}
                </p>
              </div>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-gray-500">
                  <th className="px-3 py-2">Slug</th>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2">Pages</th>
                  <th className="px-3 py-2">Assignee</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {plan.articles.map((article) => (
                  <tr key={article.slug} className="border-t border-gray-100">
                    <td className="px-3 py-2 font-semibold">{article.slug}</td>
                    <td className="px-3 py-2">{article.category}</td>
                    <td className="px-3 py-2">{article.target_pages}p</td>
                    <td className="px-3 py-2 text-gray-500">{article.assignee || '-'}</td>
                    <td className="px-3 py-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs"
                        style={{
                          backgroundColor: `${statusOrder.find(([key]) => key === article.status)?.[2] || '#6B7280'}22`,
                          color: statusOrder.find(([key]) => key === article.status)?.[2] || '#6B7280',
                        }}
                      >
                        {article.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  );
}
