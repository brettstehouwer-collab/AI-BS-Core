import { readChatHttpResponse } from './chatHttpResponse.js';

// One selected backend and one explicit save at a time. Keep retry identity until
// confirmed; a lost response must never cause a fallback-origin duplicate write.
export async function archiveChatAndClear({ state, backendUrl, getMessages, setMessages,
  isCurrentBackend, sessionTitle, source, beforeClear }) {
  if (state.busy) throw new Error('An archive save is already in progress.');
  state.busy = true;
  try {
    if (typeof backendUrl !== 'string') throw new Error('Select a backend before archiving.');
    const serialized = JSON.stringify(getMessages());
    const messages = JSON.parse(serialized);
    if (!Array.isArray(messages) || !messages.length) throw new Error('There are no messages to archive.');
    const base = backendUrl.replace(/\/+$/, '');
    const signature = JSON.stringify([base, source, sessionTitle, messages]);
    if (state.pending?.signature !== signature) {
      const random = new Uint8Array(16);
      globalThis.crypto.getRandomValues(random);
      const id = Array.from(random, byte => byte.toString(16).padStart(2, '0')).join('');
      state.pending = { signature, id, body: JSON.stringify({ archive_id:id,
        messages, source, session_title:sessionTitle }) };
    }
    const pending = state.pending;
    const response = await fetch(`${base}/api/memory/ingest-chat`, {
      method:'POST', headers:{ 'Content-Type':'application/json', 'X-Client-ID':'stehouwer_publishing' },
      body:pending.body,
      signal:typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined,
    });
    const data = await readChatHttpResponse(response);
    const receipt = data?.archive_receipt;
    if (data?.status !== 'success' || data.items_saved !== messages.length ||
        receipt?.durable !== true || receipt.storage !== 'sqlite_vault' ||
        typeof receipt.owner !== 'string' || !receipt.owner || receipt.owner.length > 512 ||
        receipt.archive_id !== pending.id || receipt.message_count !== messages.length ||
        !Number.isInteger(receipt.vault_item_id) || receipt.vault_item_id < 1 ||
        !/^[a-f0-9]{64}$/.test(receipt.payload_sha256 || '')) {
      throw new Error('The backend did not confirm this complete archive.');
    }
    if (beforeClear && await beforeClear({ serialized, backendUrl, receipt }) === false) return { receipt, cleared: false };
    let cleared = false;
    // The application's Zustand setter executes this comparison and update
    // together; later messages/edits or another backend must remain on screen.
    setMessages(current => {
      if (isCurrentBackend() && JSON.stringify(current) === serialized) {
        cleared = true;
        return [];
      }
      return current;
    });
    if (cleared) state.pending = null;
    return { receipt, cleared };
  } finally {
    state.busy = false;
  }
}
