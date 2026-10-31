/**
 * @typedef {{backendUrl: string; owner: string; conversationId?: string}} ConversationScope
 * @typedef {{ key: string; scope_key: string; conversation_id: string; local_revision: number; ack_local_revision: number; server_revision: number; closed: boolean }} ConversationHead
 * @typedef {{key: string; head_key: string; local_revision: number; request_id: string; snapshot_json: string; source_sha256: string; expected_revision: number | null; status: string; receipt?: Record<string, unknown>; snapshot?: {messages: {id: string}[]; title: string} }} ConversationEntry
 * @typedef {{durable: boolean; storage: string; conversation_id: string; request_id: string; expected_revision: number; revision: number; message_count: number; payload_sha256: string; [key: string]: unknown}} ConversationReceipt
 */
// Durable pending conversation revisions. No import-time storage initialization,
// HTTP calls, UI mutation, credential storage, deletion or memory-only fallback.
const MAX_BYTES = 16 * 1024 * 1024;
/** @param {unknown} value */
const id = value => {
  if (typeof value !== 'string' || !/^[a-f0-9]{32}$/.test(value)) throw Error('Invalid conversation identifier.');
  return value;
};
/** @param {number} value */
const integer = value => {
  if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid conversation revision.');
  return value;
};
/** @template T @param {IDBRequest<T>} operation @returns {Promise<T>} */
const request = operation => new Promise((resolve, reject) => {
  operation.onsuccess = () => resolve(operation.result);
  operation.onerror = () => reject(operation.error || Error('Browser storage request failed.'));
});
/** @param {string} text */
const hash = async text => {
  const bytes = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
};
/** @param {unknown} value @param {Set<object>} [seen] */
function finiteJSON(value, seen = new Set()) {
  if (value === null || typeof value === 'boolean') return;
  if (typeof value === 'string') {
    for (let i = 0; i < value.length; i++) {
      const code = value.charCodeAt(i);
      if (code >= 0xd800 && code <= 0xdbff) {
        const next = value.charCodeAt(++i);
        if (!(next >= 0xdc00 && next <= 0xdfff)) throw Error('Invalid Unicode in conversation.');
      } else if (code >= 0xdc00 && code <= 0xdfff) throw Error('Invalid Unicode in conversation.');
    }
    return;
  }
  if (typeof value === 'number' && Number.isFinite(value)) return;
  if (typeof value !== 'object' || seen.has(value) ||
      (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value)))) {
    throw Error('Conversation must contain finite plain JSON values.');
  }
  seen.add(value);
  const keys = Object.keys(value);
  if (Object.getOwnPropertySymbols(value).length || (Array.isArray(value) &&
      (keys.length !== value.length || keys.some((key, index) => key !== String(index))))) {
    throw Error('Sparse, decorated or symbol-bearing values are not plain JSON.');
  }
  for (const key of Object.keys(value)) { finiteJSON(key); finiteJSON(/** @type {Record<string, unknown>} */ (value)[key], seen); }
  seen.delete(value);
}
/** @param {unknown} messages @param {unknown} title */
function snapshot(messages, title) {
  finiteJSON({ messages, title });
  if (!Array.isArray(messages) || !messages.length || typeof title !== 'string' || Array.from(title).length > 2000) {
    throw Error('A complete nonempty conversation and valid title are required.');
  }
  const ids = messages.map(message => id(message?.id));
  if (new Set(ids).size !== ids.length) throw Error('Message identifiers must be unique.');
  const raw = JSON.stringify({ messages, title });
  if (new TextEncoder().encode(raw).length > MAX_BYTES) throw Error('Conversation exceeds 16 MiB; nothing was truncated.');
  return raw;
}
/** @param {ConversationScope} options @param {boolean} [withConversation] */
function scope({ backendUrl, owner, conversationId }, withConversation = true) {
  const url = new URL(backendUrl);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash ||
      typeof owner !== 'string' || !owner || Array.from(owner).length > 512) throw Error('Invalid conversation scope.');
  const backend = url.href.replace(/\/+$/, '');
  const scopeKey = JSON.stringify([backend, owner]);
  return { backend, owner, scopeKey, headKey: withConversation ? JSON.stringify([backend, owner, id(conversationId)]) : "" };
}
/** @param {ConversationHead | null | undefined} head */
function validateHead(head) {
  if (!head) return;
  integer(head.local_revision); integer(head.ack_local_revision); integer(head.server_revision);
  if (head.local_revision < 1 || head.ack_local_revision > head.local_revision || typeof head.closed !== 'boolean') throw Error('Browser conversation head is inconsistent.');
}
/** @param {ConversationEntry | null | undefined} entry */
async function verifyEntry(entry) {
  if (!entry) throw Error('Recorded pending conversation is missing.');
  const parsed = JSON.parse(entry.snapshot_json);
  if (snapshot(parsed.messages, parsed.title) !== entry.snapshot_json || await hash(entry.snapshot_json) !== entry.source_sha256) {
    throw Error('Stored conversation source cannot be confirmed.');
  }
  return { ...entry, snapshot: parsed };
}

export async function openConversationOutbox({ indexedDB = globalThis.indexedDB, name = 'aibs-conversation-outbox-v1' } = {}) {
  if (!indexedDB) throw Error('Durable browser storage is unavailable; pending chat was not saved.');
  const database = await /** @type {Promise<IDBDatabase>} */ (new Promise((resolve, reject) => {
    const opening = indexedDB.open(name, 1);
    let settled = false;
    /** @param {unknown} error */
    const fail = error => { settled = true; reject(error); };
    const timer = setTimeout(() => fail(Error('Opening browser storage timed out.')), 5000);
    opening.onupgradeneeded = () => {
      const db = opening.result;
      db.createObjectStore('heads', { keyPath: 'key' }).createIndex('by_scope', 'scope_key');
      db.createObjectStore('entries', { keyPath: 'key' }).createIndex('by_revision', ['head_key', 'local_revision'], { unique: true });
    };
    opening.onblocked = () => { clearTimeout(timer); fail(Error('Another browser context is blocking storage.')); };
    opening.onerror = () => { clearTimeout(timer); fail(opening.error || Error('Opening browser storage failed.')); };
    opening.onsuccess = () => {
      clearTimeout(timer);
      if (settled) { opening.result.close(); return; }
      settled = true;
      opening.result.onversionchange = () => opening.result.close();
      resolve(opening.result);
    };
  }));
  /** @template T @param {IDBTransactionMode} mode @param {(heads: IDBObjectStore, entries: IDBObjectStore) => Promise<T>} operation @returns {Promise<T>} */
  function transaction(mode, operation) {
    return new Promise((resolve, reject) => {
      /** @type {IDBTransaction} */
      let tx;
      try { tx = database.transaction(['heads', 'entries'], mode, mode === 'readwrite' ? { durability: 'strict' } : undefined); } catch (error) { reject(error); return; }
      /** @type {T} */
      let result;
      /** @type {unknown} */
      let failure;
      let ready = false;
      const timer = setTimeout(() => { failure = Error('Browser storage transaction timed out.'); try { tx.abort(); } catch { reject(failure); } }, 10000);
      tx.oncomplete = () => { clearTimeout(timer); ready && !failure ? resolve(result) : reject(failure || Error('Storage completed without confirmed work.')); };
      tx.onabort = () => { clearTimeout(timer); reject(failure || tx.error || Error('Browser storage transaction was aborted.')); };
      Promise.resolve().then(() => operation(tx.objectStore('heads'), tx.objectStore('entries')))
        .then(value => { result = value; ready = true; })
        .catch(error => { failure = error; try { tx.abort(); } catch { clearTimeout(timer); reject(error); } });
    });
  }
  /** @param {string} headKey @param {string} requestId */
  const entryKey = (headKey, requestId) => JSON.stringify([headKey, id(requestId)]);
  return {
    /** @param {ConversationScope & {conversationId: string; expectedLocalRevision: number; messages: unknown; title?: string; requestId: string; baseServerRevision?: number}} options */
    async queueSnapshot(options) {
      const selected = scope(options), expected = integer(options.expectedLocalRevision);
      const raw = snapshot(options.messages, options.title ?? 'Chat'), digest = await hash(raw);
      const key = entryKey(selected.headKey, options.requestId);
      return transaction('readwrite', async (heads, entries) => {
        const previous = await request(entries.get(key));
        if (previous) {
          if (previous.snapshot_json !== raw || previous.source_sha256 !== digest || previous.local_revision !== expected + 1) throw Error('Pending request ID belongs to different inputs.');
          return { local_revision: previous.local_revision, request_id: previous.request_id, source_sha256: digest };
        }
        let head = await request(heads.get(selected.headKey));
        validateHead(head);
        if (!head) head = { key: selected.headKey, scope_key: selected.scopeKey, conversation_id: options.conversationId,
          local_revision: 0, ack_local_revision: 0, server_revision: integer(options.baseServerRevision ?? 0), closed: false };
        if (head.closed || head.local_revision !== expected || expected >= Number.MAX_SAFE_INTEGER) throw Error('Browser conversation changed; preserve pending input and reload it.');
        const revision = expected + 1;
        await request(entries.add({ key, head_key: selected.headKey, local_revision: revision, request_id: options.requestId,
          snapshot_json: raw, source_sha256: digest, expected_revision: null, status: 'queued' }));
        head.local_revision = revision;
        await request(heads.put(head));
        return { local_revision: revision, request_id: options.requestId, source_sha256: digest };
      });
    },
    /** @param {ConversationScope} options */
    async loadConversation(options) {
      const selected = scope(options);
      const result = await transaction('readonly', async (heads, entries) => {
        const head = await request(heads.get(selected.headKey)); validateHead(head);
        if (!head) return null;
        const rows = await request(entries.index('by_revision').getAll(IDBKeyRange.bound([selected.headKey, 0], [selected.headKey, Number.MAX_SAFE_INTEGER])));
        if (rows.length !== head.local_revision || rows.some(/** @param {ConversationEntry} row @param {number} i */ (row, i) => row.local_revision !== i + 1)) throw Error('Browser conversation revisions are missing.');
        return { head, entries: rows };
      });
      if (result) result.entries = await Promise.all(result.entries.map(verifyEntry));
      return result;
    },
    /** @param {ConversationScope} options */
    async listConversations(options) {
      const selected = scope(options, false);
      return transaction('readonly', async heads => {
        const rows = await request(heads.index('by_scope').getAll(selected.scopeKey));
        rows.forEach(validateHead);
        return rows.map(/** @param {ConversationHead} row */ row => ({ conversation_id: row.conversation_id, local_revision: row.local_revision,
          ack_local_revision: row.ack_local_revision, server_revision: row.server_revision, closed: row.closed }));
      });
    },
    /** @param {ConversationScope} options */
    async prepareNext(options) {
      const selected = scope(options);
      const entry = await transaction('readwrite', async (heads, entries) => {
        const head = await request(heads.get(selected.headKey)); validateHead(head);
        if (!head || head.ack_local_revision === head.local_revision) return null;
        const row = await request(entries.index('by_revision').get([selected.headKey, head.ack_local_revision + 1]));
        if (!row || row.status === 'conflict' || !['queued', 'inflight'].includes(row.status)) throw Error('Pending conversation needs conflict/evidence review.');
        if (row.status === 'queued') {
          if (head.server_revision >= Number.MAX_SAFE_INTEGER) throw Error('Server revision limit reached.');
          row.expected_revision = head.server_revision; row.status = 'inflight';
          await request(entries.put(row));
        }
        if (row.expected_revision !== head.server_revision) throw Error('Pending server revision changed.');
        return row;
      });
      if (!entry) return null;
      const verified = await verifyEntry(entry);
      return { local_revision: entry.local_revision, source_sha256: entry.source_sha256,
        body: { request_id: entry.request_id, expected_revision: entry.expected_revision,
          messages: verified.snapshot.messages, title: verified.snapshot.title } };
    },
    /** @param {ConversationScope & {requestId: string; receipt: ConversationReceipt}} options */
    async acknowledge(options) {
      const selected = scope(options), key = entryKey(selected.headKey, options.requestId), receipt = options.receipt;
      const prior = await transaction('readonly', async (_, entries) => request(entries.get(key)));
      const verified = await verifyEntry(prior);
      if (receipt?.durable !== true || receipt.storage !== 'sqlite_vault' || receipt.conversation_id !== options.conversationId ||
          receipt.request_id !== options.requestId || receipt.expected_revision !== prior.expected_revision ||
          !Number.isSafeInteger(receipt.revision) || receipt.revision !== prior.expected_revision + 1 ||
          receipt.message_count !== verified.snapshot.messages.length || !/^[a-f0-9]{64}$/.test(receipt.payload_sha256 || '')) throw Error('Server did not confirm the complete pending revision.');
      const saved = Object.fromEntries(['conversation_id', 'request_id', 'revision', 'expected_revision', 'message_count', 'payload_sha256', 'storage', 'durable'].map(name => [name, receipt[name]]));
      return transaction('readwrite', async (heads, entries) => {
        const head = await request(heads.get(selected.headKey)), row = await request(entries.get(key));
        validateHead(head);
        if (!head || !row || row.snapshot_json !== prior.snapshot_json || row.source_sha256 !== prior.source_sha256) throw Error('Pending source changed before acknowledgement.');
        if (row.status === 'acknowledged') {
          if (JSON.stringify(row.receipt) !== JSON.stringify(saved)) throw Error('Confirmed receipt changed.');
          return row.receipt;
        }
        if (row.status !== 'inflight' || row.expected_revision !== prior.expected_revision ||
            row.local_revision !== head.ack_local_revision + 1 || head.server_revision !== row.expected_revision) throw Error('Pending acknowledgement is out of order.');
        row.status = 'acknowledged'; row.receipt = saved;
        head.ack_local_revision = row.local_revision; head.server_revision = saved.revision;
        await request(entries.put(row)); await request(heads.put(head));
        return saved;
      });
    },
    /** @param {ConversationScope & {requestId: string}} options */
    async markConflict(options) {
      const selected = scope(options), key = entryKey(selected.headKey, options.requestId);
      return transaction('readwrite', async (_, entries) => {
        const row = await request(entries.get(key));
        if (!row || row.status !== 'inflight') throw Error('Pending request cannot be marked conflicted.');
        row.status = 'conflict'; await request(entries.put(row));
      });
    },
    /** @param {ConversationScope & {expectedLocalRevision: number}} options */
    async closeConversation(options) {
      const selected = scope(options), expected = integer(options.expectedLocalRevision);
      return transaction('readwrite', async heads => {
        const head = await request(heads.get(selected.headKey)); validateHead(head);
        if (!head || head.local_revision !== expected) throw Error('Conversation changed before closing.');
        head.closed = true; await request(heads.put(head));
      });
    },
    close() { database.close(); },
  };
}
