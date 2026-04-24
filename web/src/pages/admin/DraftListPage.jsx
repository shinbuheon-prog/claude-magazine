import React, { useEffect, useState } from 'react';
import { listDrafts } from '../../api/admin';

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

export default function DraftListPage({ onOpenDraft, onOpenHistory, onOpenDashboard }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await listDrafts();
      setItems(data.items || []);
    } catch (err) {
      setError(err.message || '초안 목록을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-orange-700">Editor Queue</p>
            <h1 className="mt-2 text-4xl font-black tracking-tight text-stone-900">검토 대기 초안</h1>
            <p className="mt-2 max-w-2xl text-sm text-stone-600">
              로컬 editor API가 drafts 디렉터리와 발행 로그를 합쳐 보여줍니다. Ghost 키가 없어도 목록과 검수는 그대로 동작합니다.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={load}
              className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm transition hover:border-stone-500"
            >
              새로고침
            </button>
            <button
              type="button"
              onClick={onOpenDashboard}
              className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-sm transition hover:border-stone-500"
            >
              대시보드
            </button>
            <button
              type="button"
              onClick={onOpenHistory}
              className="rounded-full bg-stone-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-stone-700"
            >
              발행 이력
            </button>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-[0_24px_80px_rgba(28,25,23,0.08)]">
          <div className="grid grid-cols-[1.8fr,0.9fr,0.8fr,0.9fr,0.7fr] gap-4 border-b border-stone-200 bg-stone-50 px-6 py-4 text-xs font-bold uppercase tracking-[0.2em] text-stone-500">
            <span>제목</span>
            <span>Lint</span>
            <span>분량</span>
            <span>갱신</span>
            <span>액션</span>
          </div>

          {loading ? (
            <div className="px-6 py-12 text-sm text-stone-500">초안 목록을 불러오는 중입니다.</div>
          ) : null}

          {!loading && items.length === 0 ? (
            <div className="px-6 py-12 text-sm text-stone-500">drafts/ 아래에 검토할 초안이 없습니다.</div>
          ) : null}

          {!loading &&
            items.map((item) => (
              <div
                key={item.article_id}
                className="grid grid-cols-[1.8fr,0.9fr,0.8fr,0.9fr,0.7fr] gap-4 border-b border-stone-100 px-6 py-5 last:border-b-0"
              >
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-bold text-stone-900">{item.title}</h2>
                    <span className="rounded-full bg-orange-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-orange-700">
                      {item.category}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-stone-500">
                    article_id {item.article_id} · source {item.source_count} · status {item.status}
                  </p>
                </div>

                <div>
                  <p className="text-sm font-semibold text-stone-800">
                    {item.lint.score}/{item.lint.total}
                  </p>
                  <p className="mt-1 text-xs text-stone-500">
                    fail {item.lint.failed} · warn {item.lint.warnings}
                  </p>
                  <p
                    className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${
                      item.lint.can_publish
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {item.lint.can_publish ? 'publishable' : 'needs work'}
                  </p>
                </div>

                <div className="text-sm text-stone-600">
                  <p>{item.word_count.toLocaleString()} words</p>
                </div>

                <div className="text-sm text-stone-600">
                  <p>{formatDate(item.updated_at)}</p>
                </div>

                <div className="flex items-start justify-end">
                  <button
                    type="button"
                    onClick={() => onOpenDraft(item.article_id)}
                    className="rounded-full border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 transition hover:border-stone-500 hover:bg-stone-50"
                  >
                    검토
                  </button>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
