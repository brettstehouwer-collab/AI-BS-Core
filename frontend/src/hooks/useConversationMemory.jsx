import React, { useEffect, useRef, useSyncExternalStore } from 'react';
import { conversationMemoryFor, conversationBackendMatches } from '../utils/conversationMemory.js';

export function useConversationMemory(store, backendUrl, onContextChange) {
  const manager = conversationMemoryFor(store);
  const actor = useSyncExternalStore(store.subscribe, manager.getActorSnapshot);
  const cancel = useRef(onContextChange); cancel.current = onContextChange;
  useEffect(() => {
    const [storeBackend, user] = JSON.parse(actor);
    manager.configure(backendUrl, user, storeBackend, () => cancel.current?.());
  }, [manager, actor, backendUrl]);
  const status = useSyncExternalStore(manager.subscribe, manager.getStatus);
  const binding = manager.getBinding();
  const viewReady = status.viewReady && manager.isCurrent(binding) && conversationBackendMatches(status.backendUrl, backendUrl);
  const labels = { connecting: 'Checking chat memory', ready: 'Chat memory ready', pending: 'Chat save pending',
    saving: 'Saving chat', saved: 'Chat saved locally and to SQLite', error: 'Chat save needs attention',
    conflict: 'Chat conflict retained', unassigned: 'Existing chat needs ownership confirmation' };
  return { ...status, viewReady, statusLabel: labels[status.phase] || 'Chat memory unavailable',
    setMessages: updater => manager.change(binding, 'messages', updater),
    setDraft: updater => manager.change(binding, 'draft', updater),
    isCurrent: () => manager.isCurrent(binding), beforeClear: options => manager.beforeClear(binding, options),
    retry: () => manager.retry(), flushLocal: () => manager.flushLocal(), recover: id => manager.recover(id),
    adoptExisting: () => manager.adoptExisting(), saveSeparateCopy: () => manager.saveSeparateCopy() };
}

export function ConversationMemoryStatus({ memory }) {
  const run = action => { Promise.resolve().then(action).catch(() => {}); };
  return <div role="status" aria-live="polite" style={{ padding: '6px 10px', fontSize: 12, flexShrink: 0, background: '#111827', color: '#cbd5e1' }}>
    <span>{memory.statusLabel}</span>
    {memory.error && <span> — {memory.error}</span>}
    {memory.phase === 'error' && <button type="button" onClick={() => run(memory.retry)}>Retry chat save</button>}
    {memory.phase === 'conflict' && <button type="button" onClick={() => run(memory.saveSeparateCopy)}>Save separate copy</button>}
    {memory.phase === 'unassigned' && <button type="button" onClick={() => run(memory.adoptExisting)}>Save existing chat as mine</button>}
    {memory.viewReady && memory.choices.length > 0 && <select aria-label="Recover saved conversation" value="" onChange={event => { const id = event.target.value; run(() => memory.recover(id)); }}>
      <option value="">Recover saved conversation…</option>
      {memory.choices.map(row => <option key={row.conversation_id} value={row.conversation_id}>{row.title || 'Local conversation'} · {row.conversation_id.slice(0, 8)}{row.closed ? ' (archived)' : ''}</option>)}
    </select>}
  </div>;
}
