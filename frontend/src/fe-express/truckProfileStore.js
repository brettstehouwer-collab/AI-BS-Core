// Separate from the frozen load-capture stores. Pending operations survive reloads.
const read = request => new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); });
export const emptyTruckProfile = () => ({ schema_version: 1, vehicle_configuration: 'unknown', hazmat_status: 'unknown', axles: [], dimensions_confirmed: false, weights_confirmed: false });
export const equalProfile = (a, b) => {
  const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
  return JSON.stringify(stable(a)) === JSON.stringify(stable(b));
};
export function validateTruckReply(data) {
  if (!data || data.routing_ready !== false || data.provider_qualified !== false || !Number.isSafeInteger(data.revision) || data.revision < 0 || !Array.isArray(data.missing_vehicle_fields)) throw new Error('Invalid truck-profile response');
  if (data.revision === 0 ? data.profile !== null : !data.profile || data.profile.revision !== data.revision || data.profile.payload?.schema_version !== 1 || typeof data.profile.updated_at !== 'string') throw new Error('Invalid truck-profile revision');
  return data;
}
export async function openTruckProfileStore(owner, guard, indexedDB = globalThis.indexedDB) {
  guard();
  if (typeof owner !== 'string' || !owner.startsWith('firebase:ai-bs-dashboard:')) throw new Error('Verified Firebase driver owner required');
  const request = indexedDB.open(`aibs-fe-truck-profile-v1:${encodeURIComponent(owner)}`, 1);
  request.onupgradeneeded = () => { request.result.createObjectStore('state'); request.result.createObjectStore('history', { autoIncrement: true }); };
  const db = await read(request);
  let closed = false;
  const check = () => { if (closed) throw new Error('Truck-profile cache closed'); guard(); };
  db.onversionchange = () => { closed = true; db.close(); };
  try { check(); } catch (error) { db.close(); throw error; }
  const transact = (mode, action) => new Promise((resolve, reject) => {
    try {
      check();
      const tx = db.transaction(['state', 'history'], mode), store = tx.objectStore('state');
      let result, failure;
      tx.oncomplete = () => resolve(result);
      tx.onabort = () => reject(failure || tx.error || new Error('Truck-profile transaction aborted'));
      tx.onerror = () => {};
      const query = store.get('profile');
      query.onsuccess = () => {
        try {
          check();
          const previous = query.result || { owner, generation: 0, revision: 0, draft: emptyTruckProfile(), dirty: false, server: null, pending: null, conflict: null };
          if (previous.owner !== owner) throw new Error('Truck-profile owner mismatch');
          result = action(structuredClone(previous));
          if (mode === 'readwrite') {
            check();
            tx.objectStore('history').add({ at: new Date().toISOString(), before: previous });
            result.generation = previous.generation + 1;
            store.put(result, 'profile');
          }
        } catch (error) { failure = error; tx.abort(); }
      };
    } catch (error) { reject(error); }
  });
  const snapshot = () => transact('readonly', state => state);
  const change = (payload, expected) => transact('readwrite', state => {
    if (state.generation !== expected) throw new Error('Profile changed in another view; reload saved draft');
    if (state.pending || state.conflict) throw new Error('Resolve or retry the saved upload before editing');
    if (JSON.stringify(payload).length > 30000) throw new Error('Truck-profile draft exceeds device limit');
    state.draft = structuredClone(payload); state.dirty = true; return state;
  });
  const pull = async transport => {
    check(); const response = await transport(); check();
    if (response.status !== 200) throw new Error(`Truck-profile retrieval failed (${response.status})`);
    const remote = validateTruckReply(response.data);
    return transact('readwrite', state => {
      if (remote.revision < state.revision) throw new Error('Server profile is older than the saved acknowledgement');
      if (state.pending) throw new Error('Retry the saved upload before pulling another version');
      if (state.dirty) state.conflict = remote;
      else { state.server = remote.profile; state.revision = remote.revision; state.draft = remote.profile?.payload || emptyTruckProfile(); state.conflict = null; }
      return state;
    });
  };
  const sync = async transport => {
    let state = await snapshot();
    if (state.conflict) throw new Error('Review the conflicting truck profile first');
    if (!state.pending) {
      if (!state.dirty) return state;
      state = await transact('readwrite', current => {
        if (current.generation !== state.generation || current.pending) throw new Error('Profile changed; reload saved draft before upload');
        current.pending = { op_id: crypto.randomUUID(), base_revision: current.revision, payload: structuredClone(current.draft) };
        return current;
      });
    }
    const operation = state.pending;
    const response = await transport(operation); check();
    if (response.status === 409) {
      const latest = await transport(); check();
      if (latest.status !== 200) throw new Error('Profile conflict retained; retry to retrieve the server version');
      const remote = validateTruckReply(latest.data);
      return transact('readwrite', current => {
        if (current.pending?.op_id !== operation.op_id) throw new Error('Profile operation changed in another view');
        current.conflict = remote; return current;
      });
    }
    if ([400, 413, 422].includes(response.status)) {
      await transact('readwrite', current => {
        if (current.pending?.op_id !== operation.op_id) throw new Error('Profile operation changed in another view');
        current.pending = null; return current;
      });
      throw new Error(`Truck-profile rejected (${response.status}); edit the saved draft and retry. Rejected operation retained in local history.`);
    }
    if (response.status !== 200) throw new Error(`Truck-profile upload unconfirmed (${response.status}); saved operation retained`);
    const result = validateTruckReply(response.data);
    if (result.revision !== operation.base_revision + 1 || !equalProfile(result.profile.payload, operation.payload)) throw new Error('Truck-profile acknowledgement mismatch; saved operation retained');
    return transact('readwrite', current => {
      if (!current.pending && current.revision >= result.revision) return current;
      if (current.pending?.op_id !== operation.op_id) throw new Error('Profile operation changed in another view');
      current.server = result.profile; current.revision = result.revision; current.pending = null; current.conflict = null; current.dirty = false; return current;
    });
  };
  const resolve = (decision, expected) => transact('readwrite', state => {
    if (state.generation !== expected || !state.conflict) throw new Error('Review changed; reload both saved versions');
    if (!['keep-local', 'use-server'].includes(decision)) throw new Error('Choose a profile explicitly');
    const remote = state.conflict;
    state.server = remote.profile; state.revision = remote.revision; state.pending = null; state.conflict = null;
    state.dirty = decision === 'keep-local';
    if (decision === 'use-server') state.draft = remote.profile?.payload || emptyTruckProfile();
    return state;
  });
  return { snapshot, change, pull, sync, resolve, close() { closed = true; db.close(); } };
}
