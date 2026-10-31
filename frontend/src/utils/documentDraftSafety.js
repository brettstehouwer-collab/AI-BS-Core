// Documents use the revision acknowledged by the server, never a fresh read to
// rebase an attempted save. This queue owns each path even while its UI is away.
/** @param {unknown} path */
export function documentPathIdentity(path) {
  return String(path || '').replace(/\\/g, '/').replace(/^C:\/AI-BS\/shared_cloud_drive\//i, '').replace(/^\.\//, '').toLowerCase();
}

/** @param {unknown} revision @returns {revision is string} */
export const isDocumentRevision = revision => typeof revision === 'string' && /^[a-f0-9]{64}$/i.test(revision);

/** @param {{write: (payload: import("/types/domain").DocumentSavePayload) => Promise<import("/types/domain").DocumentSaveAck>}} options */
export function createDocumentDraftCoordinator({ write }) {
  /** @type {Map<string, import("/types/domain").DocumentDraftState>} */
  const paths = new Map();
  /** @type {Map<string, Promise<unknown>>} */
  const pending = new Map();
  /** @param {string} path */
  const key = path => documentPathIdentity(path);
  return {
    /** @param {string} path @param {string} content @param {string} revision */
    load(path, content, revision) {
      if (!path || typeof content !== 'string' || !isDocumentRevision(revision)) {
        throw new Error('The document response has no valid revision. Saving is disabled; reload explicitly.');
      }
      paths.set(key(path), { revision, savedContent: content, isNew: false, blocked: false, error: null });
    },
    /** @param {string} path */
    registerNew(path) {
      if (!paths.has(key(path))) paths.set(key(path), { revision: null, savedContent: null, isNew: true, blocked: false, error: null });
    },
    /** @param {string} path */
    snapshot(path) { const state = paths.get(key(path)); return state ? { ...state } : null; },
    /** @param {string} path @param {string} content */
    isDirty(path, content) { return paths.get(key(path))?.savedContent !== content; },
    /** @param {string} path @param {string} content */
    save(path, content) {
      const identity = key(path);
      const operation = async () => {
        const state = paths.get(identity);
        if (!state) throw new Error('Load this document before saving. Its acknowledged revision is unavailable.');
        if (state.blocked) throw state.error;
        if (state.savedContent === content && state.revision) return { path, revision: state.revision, unchanged: true };
        const payload = state.isNew ? { path, content, create_only: true }
          : { path, content, expected_revision: state.revision };
        try {
          const result = await write(payload);
          if (!result?.path || key(result.path) !== identity || !isDocumentRevision(result.revision)) {
            throw new Error('The save acknowledgement is missing or identifies another document.');
          }
          // Advance even when the user has edited again or switched documents.
          state.revision = result.revision;
          state.savedContent = content;
          state.isNew = false;
          return result;
        } catch (cause) {
          state.blocked = true;
          state.error = new Error(`${cause instanceof Error ? cause.message : "Save failed"} Autosave is paused. Preserve your draft and reload latest explicitly before saving this path again.`);
          throw state.error;
        }
      };
      const result = (pending.get(identity) || Promise.resolve()).then(operation);
      pending.set(identity, result.catch(() => {}));
      return result;
    },
    idle() { return Promise.all([...pending.values()]); },
  };
}

const RECOVERY_PREFIX = 'aibs_document_recovery_v1_';
const LEGACY_PREFIX = 'aibs_doc_backup_';

// Each copy gets its own immutable key. Legacy copies remain in place, too.
/**
 * @param {Storage} storage
 * @param {{path:string,name?:string,content:string,reason?:string}} snapshot
 * @param {{now?:string,id?:string}} options
 */
export function retainDocumentRecovery(storage, { path, name, content, reason }, { now = new Date().toISOString(), id = globalThis.crypto.randomUUID() } = {}) {
  if (!path || typeof content !== 'string') return null;
  const copy = { version: 1, id, path, name: name || path.replace(/\\/g, '/').split('/').pop(), content, reason, savedAt: now };
  const storageKey = `${RECOVERY_PREFIX}${id}`;
  if (storage.getItem(storageKey) !== null) throw new Error('Recovery copy identity already exists.');
  const serialized = JSON.stringify(copy);
  storage.setItem(storageKey, serialized);
  if (storage.getItem(storageKey) !== serialized) throw new Error('Recovery storage did not retain the draft.');
  return { ...copy, storageKey };
}

/** @param {Storage} storage */
export function listDocumentRecovery(storage) {
  const copies = [];
  for (let index = 0; index < storage.length; index++) {
    const storageKey = storage.key(index);
    if (storageKey?.startsWith(RECOVERY_PREFIX)) {
      try {
        const copy = JSON.parse(storage.getItem(storageKey) ?? 'null');
        if (typeof copy?.content === 'string' && typeof copy.path === 'string') copies.push({
          version: 1, storageKey, path: copy.path, content: copy.content,
          id: typeof copy.id === 'string' ? copy.id : storageKey,
          name: typeof copy.name === 'string' ? copy.name : copy.path.replace(/\\/g, '/').split('/').pop(),
          reason: typeof copy.reason === 'string' ? copy.reason : 'saved copy',
          savedAt: typeof copy.savedAt === 'string' ? copy.savedAt : '',
        });
      } catch { /* A malformed copy never hides other intact copies. */ }
    } else if (storageKey?.startsWith(LEGACY_PREFIX) && !storageKey.startsWith(`${LEGACY_PREFIX}time_`)) {
      const path = storageKey.slice(LEGACY_PREFIX.length);
      const content = storage.getItem(storageKey);
      if (typeof content !== 'string') continue;
      const timestamp = Number(storage.getItem(`aibs_doc_backup_time_${path}`));
      const savedAt = timestamp > 0 && Number.isFinite(timestamp) && !Number.isNaN(new Date(timestamp).valueOf()) ? new Date(timestamp).toISOString() : '';
      copies.push({ id: storageKey, storageKey, path, name: path.replace(/\\/g, '/').split('/').pop(), content, reason: 'legacy backup', savedAt });
    }
  }
  return copies.sort((a, b) => String(b.savedAt || '').localeCompare(String(a.savedAt || '')));
}

/** @param {{content:string}} copy @param {string} [id] */
export function documentRecoveryDraft(copy, id = globalThis.crypto.randomUUID()) {
  if (typeof copy?.content !== 'string') throw new Error('This recovery copy has no text.');
  // Recovery is plain data in a new unsaved text document, including command-looking text.
  const name = `recovery-${id}.txt`;
  return { doc: { path: `Documents/${name}`, name, ext: 'txt', isNew: true, isRecovery: true }, content: copy.content };
}
