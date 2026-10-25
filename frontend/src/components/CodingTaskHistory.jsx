import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { useAppStore } from './useAppStore';
import CodingTaskReviewCard from './CodingTaskReviewCard';
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
  // Store notifications retire callbacks even if logout and login are batched
  // back to the same UID before React renders. Unmount also retires the session.
  return useMemo(() => ({ key, isCurrent: () => session.snapshot() === key }), [session, key]);
}

/** @typedef {{kind:string,id:string,state:string,application_state?:string|null}} CodingRecord */
export default function CodingTaskHistory() {
  const backendUrl = useAppStore(state => state.BACKEND_URL);
  const session = useCodingSession();
  return <ScopedCodingTaskHistory key={session.key} backendUrl={backendUrl} isCurrent={session.isCurrent} />;
}

/** @param {{backendUrl:string,isCurrent:()=>boolean}} props */
function ScopedCodingTaskHistory({ backendUrl, isCurrent }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState(/** @type {CodingRecord[]} */ ([]));
  const [selected, setSelected] = useState(/** @type {string|null} */ (null));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reviewVersions, setReviewVersions] = useState(/** @type {Record<string,number>} */ ({}));
  const active = useRef(true);
  const reads = useRef(new Set());
  const current = () => active.current && isCurrent();
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; reads.current.forEach(controller => controller.abort()); reads.current.clear(); };
  }, []);

  /** @param {boolean} [refreshSelected] */
  async function load(refreshSelected = false) {
    if (!current()) return false;
    setBusy(true); setError('');
    const controller = new AbortController(); reads.current.add(controller);
    try {
      const response = await fetch(`${backendUrl}/api/chat/coding-tasks`, { signal: controller.signal });
      if (!current()) return false;
      const data = await readChatHttpResponse(response);
      if (!current()) return false;
      if (!response.ok) throw new Error(data.detail || `Saved tasks unavailable (${response.status})`);
      if (!Array.isArray(data?.items) || data.items.some(item => !item || !['task','request'].includes(item.kind) || !/^[0-9a-f]{32}$/.test(item.id || ''))) {
        throw new Error('Saved-task list response is invalid.');
      }
      setItems(data.items);
      if (refreshSelected && selected) refreshReview(selected);
      return true;
    } catch (err) {
      if (current()) {
        setItems([]); setSelected(null);
        setError(err instanceof Error ? err.message : 'Unable to load saved tasks');
      }
      return false;
    } finally { reads.current.delete(controller); if (current()) setBusy(false); }
  }

  /** @param {string} id */
  function refreshReview(id) {
    if (!current()) return;
    setReviewVersions(previous => ({ ...previous, [id]: (previous[id] || 0) + 1 }));
  }

  /** @param {string} id */
  async function recover(id) {
    if (!current() || busy) return;
    setBusy(true); setError('');
    try {
      const response = await fetch(`${backendUrl}/api/chat/coding-tasks/${id}/recover`, { method: 'POST' });
      if (!current()) return;
      const data = await readChatHttpResponse(response);
      if (!current()) return;
      if (!response.ok) throw new Error(data.detail || `Recovery inspection failed (${response.status})`);
      const loaded = await load();
      if (!current()) return;
      refreshReview(id);
      if (loaded && data.recovery?.note) setError(data.recovery.note);
    } catch (err) { if (current()) setError(err instanceof Error ? err.message : 'Recovery inspection failed'); }
    finally { if (current()) setBusy(false); }
  }

  /** @param {string} id */
  async function cancel(id) {
    if (!current() || busy) return;
    setBusy(true); setError('');
    try {
      const response = await fetch(`${backendUrl}/api/chat/coding-tasks/${id}/cancel`, { method: 'POST' });
      if (!current()) return;
      const data = await readChatHttpResponse(response);
      if (!current()) return;
      if (!response.ok) throw new Error(data.detail || `Cancellation request failed (${response.status})`);
      const loaded = await load();
      if (!current()) return;
      refreshReview(id);
      if (loaded) setError(data.cancel_requested ? 'Cancellation requested. Refresh saved tasks to confirm CANCELLED.' : `Task is already ${data.state}.`);
    } catch (err) { if (current()) setError(err instanceof Error ? err.message : 'Cancellation request failed'); }
    finally { if (current()) setBusy(false); }
  }

  return <div className="mb-2 text-xs text-slate-300">
    <button type="button" disabled={busy} onClick={() => { if (!current()) return; setOpen(!open); if (!open) load(); }}
      className="rounded border border-slate-600 px-2 py-1 disabled:opacity-40">Saved coding tasks</button>
    {open && <button type="button" disabled={busy} onClick={() => load(true)} className="ml-2 text-blue-300 disabled:opacity-40">Refresh</button>}
    {open && <div className="mt-2 max-h-64 overflow-auto rounded border border-slate-700 bg-slate-900 p-2">
      {busy && <div>Loading saved tasks…</div>}
      {!busy && !error && !items.length && <div>No saved coding tasks on this backend.</div>}
      {items.slice(0, 20).map(item => <div key={`${item.kind}-${item.id}`} className="flex flex-wrap items-center gap-2 border-b border-slate-700 py-1">
        <span>{item.kind} {item.id.slice(0, 8)} — {item.state}</span>
        {item.kind === 'task' && <button type="button" disabled={busy} onClick={() => { if (current()) setSelected(item.id); }} className="text-blue-300 disabled:opacity-40">Review</button>}
        {item.kind === 'task' && ['VALIDATING','CHECKING','WRITING','CREATING_WORKTREE'].includes(item.state) && <button type="button" disabled={busy} onClick={() => cancel(item.id)} className="text-red-300 disabled:opacity-40">Cancel task</button>}
        {item.kind === 'request' && ['GENERATING','REPAIRING','RUNNING'].includes(item.state) && <button type="button" disabled={busy} onClick={() => cancel(item.id)} className="text-red-300 disabled:opacity-40">Cancel request</button>}
        {(item.application_state === 'PARTIAL' || item.application_state === 'APPLYING' || !['VERIFIED','FAILED','CANCELLED'].includes(item.state)) && <button type="button" disabled={busy} onClick={() => recover(item.id)} className="text-amber-300 disabled:opacity-40">Recover Task</button>}
      </div>)}
      {selected && <CodingTaskReviewCard key={JSON.stringify([selected, reviewVersions[selected] || 0])} taskId={selected} />}
      {error && <div role="status" className="mt-2 text-amber-300">{error}</div>}
    </div>}
  </div>;
}
