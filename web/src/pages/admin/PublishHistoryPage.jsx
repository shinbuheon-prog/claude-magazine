import React, { useEffect, useState } from 'react';
import { listPublished, unpublish } from '../../api/admin';

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

export default function PublishHistoryPage({ onBack }) {
  const [items, setItems] = useState([]);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await listPublished();
      setItems(data.items || []);
      setActions(data.actions || []);
    } catch (err) {
      setError(err.message || '발행 이력을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleUnpublish(postId) {
    setBusy(postId);
    setError('');
    try {
      await unpublish(postId);
      await load();
    } catch (err) {
      setError(err.message || '롤백 처리에 실패했습니다.');
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <button
              type="button"
              onClick={onBack}
              className="mb-4 rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-700"
            >
              초안 목록
            </button>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-orange-700">Publish Ledger</p>
            <h1 className="mt-2 text-4xl font-black tracking-tight">발행 이력</h1>
            <p className="mt-2 text-sm text-stone-600">Ghost 실환경이 없으면 로컬 publish 로그와 감사 로그를 그대로 보여줍니다.</p>
          </div>
          <button
            type="button"
            onClick={load}
            className="rounded-full bg-stone-900 px-4 py-2 text-sm font-semibold text-white"
          >
            새로고침
          </button>
        </div>

        {error ? <div className="mb-6 rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div> : null}

        <div className="grid gap-6 lg:grid-cols-[1.4fr,1fr]">
          <section className="overflow-hidden rounded-[2rem] border border-stone-200 bg-white shadow-[0_20px_60px_rgba(28,25,23,0.08)]">
            <div className="grid grid-cols-[1.1fr,0.8fr,0.7fr,0.8fr] gap-4 border-b border-stone-200 bg-stone-50 px-6 py-4 text-xs font-bold uppercase tracking-[0.2em] text-stone-500">
              <span>토픽</span>
              <span>상태</span>
              <span>모드</span>
              <span>액션</span>
            </div>
            {loading ? <div className="px-6 py-12 text-sm text-stone-500">발행 이력을 불러오는 중입니다.</div> : null}
            {!loading && items.length === 0 ? <div className="px-6 py-12 text-sm text-stone-500">발행 로그가 없습니다.</div> : null}
            {!loading &&
              items.map((item) => (
                <div
                  key={`${item.log_file}-${item.ghost_post_id}`}
                  className="grid grid-cols-[1.1fr,0.8fr,0.7fr,0.8fr] gap-4 border-b border-stone-100 px-6 py-5 last:border-b-0"
                >
                  <div>
                    <p className="text-base font-bold text-stone-900">{item.topic}</p>
                    <p className="mt-1 text-xs text-stone-500">
                      {formatDate(item.timestamp)} · {item.ghost_post_id || 'mock-post'}
                    </p>
                  </div>
                  <div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${
                      item.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-stone-200 text-stone-700'
                    }`}>
                      {item.status || 'draft'}
                    </span>
                    <p className="mt-2 text-xs text-stone-500">
                      newsletter {item.recipient_count || 0}
                    </p>
                  </div>
                  <div className="text-sm text-stone-600">{item.mode || '-'}</div>
                  <div className="flex justify-end">
                    <button
                      type="button"
                      disabled={!item.ghost_post_id || busy === item.ghost_post_id}
                      onClick={() => handleUnpublish(item.ghost_post_id)}
                      className="rounded-full border border-stone-300 px-4 py-2 text-sm font-semibold text-stone-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      롤백
                    </button>
                  </div>
                </div>
              ))}
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5">
            <h2 className="text-lg font-black">감사 로그</h2>
            <div className="mt-4 space-y-3">
              {actions.length === 0 ? <p className="text-sm text-stone-500">기록된 승인/반려 액션이 없습니다.</p> : null}
              {actions.map((action, index) => (
                <div key={`${action.timestamp}-${index}`} className="rounded-3xl bg-stone-100 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-bold text-stone-900">{action.action}</span>
                    <span className="text-xs text-stone-500">{formatDate(action.timestamp)}</span>
                  </div>
                  <p className="mt-2 text-xs text-stone-600">
                    article_id {action.article_id || '-'} · approver {action.approver || '-'}
                  </p>
                  {action.reason ? <p className="mt-2 text-sm text-stone-700">{action.reason}</p> : null}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
