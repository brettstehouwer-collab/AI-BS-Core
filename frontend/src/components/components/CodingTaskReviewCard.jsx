import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { useAppStore } from './useAppStore';
import { readChatHttpResponse } from '/src/utils/chatHttpResponse.js';

/** @param {ReturnType<typeof useAppStore.getState>} state */
const contextStamp = state => JSON.stringify([state?.BACKEND_URL, state?.currentUser?.uid || '']);

function useCodingSession() {
  const [session] = useState(() => {
    let generation = 0;
    const snapshot = () => JSON.stringify([generation, contextStamp(useAppStore.getState())]);
    return { snapshot, /** @param {()=>void} notify */ subscribe(notify) {
      const unsubscribe = useAppStore.subscribe((next, previous) => {
        if (contextStamp(next) !== contextStamp(previous)) { generation++; notify(); }
      });
      return () => { generation++; unsubscribe(); };
    } };
  });
  const key = useSyncExternalStore(session.subscribe, session.snapshot, session.snapshot);
  // An ended login remains retired even when the same UID returns in one batch.
  return useMemo(() => ({ key, isCurrent: () => session.snapshot() === key }), [session, key]);
}

/** @typedef {{state:string, backup?:string}} Application */
/** @typedef {{argv:string[],returncode:number|null,stdout?:string,stderr?:string,error?:string}} Check */
/** @typedef {{path:string,content:string,truncated:boolean}} SubmittedFile */
/** @typedef {{can_apply:boolean,review_token?:string,state:string,execution_mode?:string,changed_files:string[],review_diff:string,checks:Check[],reason?:string|null,application?:Application|null,error?:string|null,error_stage?:string|null,submitted_files?:SubmittedFile[],input_preview_error?:string|null}} CodingReview */

/** Present recorded evidence only; backend review remains the apply authority.
 * @param {{checks?:Check[],executionMode?:string}} props
 */
export function CodingVerificationEvidence({ checks, executionMode }) {
  const recorded = Array.isArray(checks) ? checks : [];
  const failed = recorded.some(check => check?.error || (Number.isInteger(check?.returncode) && check.returncode !== 0));
  const complete = recorded.length > 0 && recorded.every(check => Number.isInteger(check?.returncode));
  const summary = !recorded.length ? 'No verification checks have run for this task.'
    : failed ? 'Verification checks failed or were interrupted.'
      : complete ? 'Recorded verification checks passed.'
        : 'Verification is incomplete; no passing result is confirmed.';
  const environment = executionMode === 'trusted_host'
    ? `${recorded.length ? 'Recorded' : 'Requested'} execution: trusted local host. These checks do not provide VM isolation.`
    : executionMode === 'windows_vm'
      ? `${recorded.length ? 'Recorded' : 'Requested'} execution: Windows VM.`
      : 'Execution environment is not recorded; isolation is unverified.';

  return <div className="mt-2">
    <div role="status">{summary}</div>
    <div className="mt-1 text-xs text-amber-300">{environment}</div>
    {!!recorded.length && <details className="mt-2">
      <summary className="cursor-pointer">Actual verification output</summary>
      {recorded.map((check, index) => <pre key={index} className="mt-2 max-h-60 overflow-auto whitespace-pre-wrap text-xs">{`Check ${index + 1}: exit ${check?.returncode ?? 'unknown'}\n${Array.isArray(check?.argv) ? check.argv.join(' ') : ''}\n${check?.error ? `Control error: ${check.error}\n` : ''}stdout:\n${check?.stdout || ''}\nstderr:\n${check?.stderr || ''}`}</pre>)}
    </details>}
  </div>;
}

/** @param {{taskId:string}} props */
export default function CodingTaskReviewCard({ taskId }) {
  const backendUrl = useAppStore(state => state.BACKEND_URL);
  const session = useCodingSession();
  return <ScopedCodingTaskReviewCard key={JSON.stringify([session.key, taskId])} backendUrl={backendUrl} taskId={taskId} isCurrent={session.isCurrent} />;
}

/** @param {{taskId:string,backendUrl:string,isCurrent:()=>boolean}} props */
function ScopedCodingTaskReviewCard({ taskId, backendUrl, isCurrent }) {
  const [review, setReview] = useState(/** @type {CodingReview|null} */ (null));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);
  const current = () => mounted.current && isCurrent();
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const canApply = review?.can_apply === true && typeof review.review_token === 'string' && review.review_token.length > 0;

  useEffect(() => {
    if (!/^[0-9a-f]{32}$/.test(taskId || '')) {
      setError('Invalid coding task ID.');
      setLoading(false);
      return;
    }
    let active = true;
    const controller = new AbortController();
    fetch(`${backendUrl}/api/chat/coding-tasks/${taskId}/review`, { signal: controller.signal })
      .then(async response => {
        if (!active || !current()) return null;
        const data = await readChatHttpResponse(response);
        if (!active || !current()) return null;
        if (!response.ok) throw new Error(data.detail || `Review failed (${response.status})`);
        if (data?.task_id !== taskId || typeof data.can_apply !== 'boolean' || !Array.isArray(data.checks)) {
          throw new Error('Task review response did not match the requested task.');
        }
        return data;
      })
      .then(data => { if (active && current() && data) setReview(data); })
      .catch(err => { if (active && current()) setError(err.message); })
      .finally(() => { if (active && current()) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [backendUrl, taskId, isCurrent]);

  async function apply() {
    if (!current() || !canApply || busy || loading) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch(`${backendUrl}/api/chat/coding-tasks/${taskId}/apply`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_token: review.review_token }),
      });
      if (!current()) return;
      const data = await readChatHttpResponse(response);
      if (!current()) return;
      if (!response.ok) throw new Error(data.detail || `Apply failed (${response.status})`);
      setReview(previous => previous ? ({ ...previous, can_apply: false, application: data.application, reason: 'Already applied' }) : previous);
    } catch (err) {
      if (current()) setError(err instanceof Error ? err.message : 'Apply failed');
    } finally {
      if (current()) setBusy(false);
    }
  }

  return (
    <section className="mt-3 rounded-xl border border-blue-500/40 bg-slate-900/80 p-4 text-sm text-slate-100" aria-label="Coding task review">
      <div className="font-semibold text-blue-300">Coding task review</div>
      <div className="text-xs text-slate-400">Task {taskId}</div>
      {loading && <div role="status" className="mt-2 text-slate-400">Loading task review…</div>}
      {review && <>
        <div className="mt-2">Status: {review.application?.state || review.state}</div>
        {review.error && <div role="alert" className="mt-2 text-red-300">{review.error_stage ? `${review.error_stage}: ` : ''}{review.error}</div>}
        <div className="mt-2">Changed files: {(review.changed_files || []).join(', ') || 'None'}</div>
        {!!review.submitted_files?.length && <details className="mt-2"><summary className="cursor-pointer">Submitted source</summary>
          {review.submitted_files.map((file,index) => <div key={index} className="mt-2"><div className="text-xs text-slate-400">{file.path}</div><pre className="max-h-60 overflow-auto whitespace-pre-wrap text-xs">{file.content}</pre>{file.truncated && <div className="text-xs text-amber-300">Preview truncated; complete input is saved with the task.</div>}</div>)}
        </details>}
        {review.input_preview_error && <div className="mt-2 text-xs text-amber-300">{review.input_preview_error}</div>}
        <details className="mt-2"><summary className="cursor-pointer">Readable diff</summary><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-xs">{review.review_diff || 'No diff available'}</pre></details>
        <CodingVerificationEvidence checks={review.checks} executionMode={review.execution_mode} />
        {review.reason && <div className="mt-2 text-amber-300">{review.reason}</div>}
        {review.application?.backup && <div className="mt-2 text-xs text-slate-400">Original backup: {review.application.backup}</div>}
        <button type="button" onClick={apply} disabled={!canApply || busy || loading}
          className="mt-3 rounded border border-emerald-500/40 bg-emerald-900/40 px-3 py-2 disabled:cursor-not-allowed disabled:opacity-40">
          {busy ? 'Applying…' : 'Apply Verified Change'}
        </button>
      </>}
      {error && <div role="alert" className="mt-2 text-red-300">{error}</div>}
    </section>
  );
}
