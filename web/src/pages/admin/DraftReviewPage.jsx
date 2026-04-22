import React, { useEffect, useState } from 'react';
import { approveDraft, getDiff, getDraft, getLint, rejectDraft } from '../../api/admin';

function LintBadge({ item }) {
  const statusClass = {
    pass: 'bg-emerald-100 text-emerald-700',
    fail: 'bg-red-100 text-red-700',
    warn: 'bg-amber-100 text-amber-700',
    skip: 'bg-stone-200 text-stone-600',
  };

  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-stone-900">{item.id}</span>
        <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${statusClass[item.status] || statusClass.skip}`}>
          {item.status}
        </span>
      </div>
      <p className="mt-2 text-sm text-stone-600">{item.message}</p>
    </div>
  );
}

export default function DraftReviewPage({ articleId, onBack, onOpenHistory }) {
  const [draft, setDraft] = useState(null);
  const [lint, setLint] = useState(null);
  const [diff, setDiff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const [draftData, lintData, diffData] = await Promise.all([
        getDraft(articleId),
        getLint(articleId),
        getDiff(articleId),
      ]);
      setDraft(draftData);
      setLint(lintData);
      setDiff(diffData.diff || []);
    } catch (err) {
      setError(err.message || '초안 상세를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [articleId]);

  async function handleApprove(sendNewsletter) {
    setBusy(sendNewsletter ? 'newsletter' : 'approve');
    setError('');
    setMessage('');
    try {
      const data = await approveDraft(articleId, {
        approver: 'web-admin',
        send_newsletter: sendNewsletter,
        disclosure_template: 'heavy',
      });
      setMessage(`승인 완료: ${data.result.post_id} (${data.result.mode})`);
      await load();
    } catch (err) {
      setError(err.message || '승인 처리에 실패했습니다.');
    } finally {
      setBusy('');
    }
  }

  async function handleReject() {
    const reason = window.prompt('반려 사유를 입력하세요.', '보강 취재 후 재제출');
    if (reason === null) {
      return;
    }
    setBusy('reject');
    setError('');
    setMessage('');
    try {
      await rejectDraft(articleId, { approver: 'web-admin', reason });
      setMessage('반려 기록을 저장했습니다.');
    } catch (err) {
      setError(err.message || '반려 처리에 실패했습니다.');
    } finally {
      setBusy('');
    }
  }

  if (loading) {
    return <div className="min-h-screen bg-stone-100 px-6 py-12 text-sm text-stone-500">초안 상세를 불러오는 중입니다.</div>;
  }

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <button
              type="button"
              onClick={onBack}
              className="mb-4 rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-700"
            >
              목록으로
            </button>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-orange-700">Draft Review</p>
            <h1 className="mt-2 text-4xl font-black tracking-tight">{draft?.draft?.title}</h1>
            <p className="mt-2 text-sm text-stone-600">
              article_id {articleId} · {draft?.draft?.draft_path}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={!!busy}
              onClick={handleReject}
              className="rounded-full border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 disabled:opacity-60"
            >
              반려
            </button>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => handleApprove(false)}
              className="rounded-full border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-800 disabled:opacity-60"
            >
              승인만
            </button>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => handleApprove(true)}
              className="rounded-full bg-stone-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              승인 + 뉴스레터
            </button>
            <button
              type="button"
              onClick={onOpenHistory}
              className="rounded-full bg-orange-600 px-4 py-2 text-sm font-semibold text-white"
            >
              발행 이력
            </button>
          </div>
        </div>

        {error ? <div className="mb-6 rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</div> : null}
        {message ? <div className="mb-6 rounded-3xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-700">{message}</div> : null}

        <div className="grid gap-6 lg:grid-cols-[1.1fr,1.4fr,1.1fr]">
          <section className="rounded-[2rem] border border-stone-200 bg-stone-50 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-black">Lint</h2>
              <span className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${lint?.can_publish ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                {lint?.can_publish ? 'ready' : 'blocked'}
              </span>
            </div>
            <div className="mb-4 grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-stone-400">pass</p>
                <p className="mt-2 text-2xl font-black">{lint?.passed ?? 0}</p>
              </div>
              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-stone-400">fail</p>
                <p className="mt-2 text-2xl font-black">{lint?.failed ?? 0}</p>
              </div>
              <div className="rounded-2xl bg-white p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-stone-400">warn</p>
                <p className="mt-2 text-2xl font-black">{lint?.warnings ?? 0}</p>
              </div>
            </div>
            <div className="grid gap-3">
              {(lint?.items || []).map((item) => (
                <LintBadge key={item.id} item={item} />
              ))}
            </div>
          </section>

          <section className="rounded-[2rem] border border-stone-200 bg-white p-5 shadow-[0_20px_60px_rgba(28,25,23,0.08)]">
            <h2 className="text-lg font-black">본문 미리보기</h2>
            <pre className="mt-4 max-h-[70vh] overflow-auto whitespace-pre-wrap rounded-3xl bg-stone-950 p-5 text-sm leading-7 text-stone-100">
              {draft?.markdown}
            </pre>
          </section>

          <section className="space-y-6">
            <div className="rounded-[2rem] border border-stone-200 bg-white p-5">
              <h2 className="text-lg font-black">원본 브리프</h2>
              <pre className="mt-4 max-h-[32vh] overflow-auto whitespace-pre-wrap rounded-3xl bg-stone-100 p-4 text-xs leading-6 text-stone-700">
                {JSON.stringify(draft?.brief || {}, null, 2)}
              </pre>
            </div>

            <div className="rounded-[2rem] border border-stone-200 bg-white p-5">
              <h2 className="text-lg font-black">Brief vs Draft Diff</h2>
              <pre className="mt-4 max-h-[32vh] overflow-auto whitespace-pre-wrap rounded-3xl bg-stone-950 p-4 text-xs leading-6 text-stone-100">
                {diff.join('\n') || 'diff 없음'}
              </pre>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
