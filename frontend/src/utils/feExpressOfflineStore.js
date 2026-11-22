// Work-only local durability. Owner binding must come from authenticated identity
// verification; IndexedDB is neither encryption nor an access-control boundary.
const FIELDS = new Set('load_ref pickup_address delivery_address pickup_appointment delivery_appointment pickup_arrival pickup_departure delivery_arrival delivery_departure notes delays pay_issues expenses dispatch_text'.split(' '));
const TIMES = /_(appointment|arrival|departure)$/;
const id = () => crypto.randomUUID();
const request = r => new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });

export class FEExpressOfflineStore {
  constructor(binding, { indexedDB = globalThis.indexedDB, transport } = {}) {
    if (!binding?.verified || binding.scope !== 'driver_work' || typeof binding.owner !== 'string' || !binding.owner.trim()) throw new Error('Verified driver work owner required');
    Object.defineProperty(this, 'owner', { value: binding.owner, enumerable: true });
    this.transport = transport;
    this.active = true;
    this.running = null;
    this.db = new Promise((resolve, reject) => {
      const open = indexedDB.open(`aibs-fe-driver-work-v1:${encodeURIComponent(this.owner)}`, 1);
      open.onupgradeneeded = () => { for (const name of ['loads', 'attachments', 'outbox']) open.result.createObjectStore(name, { keyPath: 'id' }); };
      open.onsuccess = () => resolve(open.result);
      open.onerror = () => reject(open.error);
      open.onblocked = () => reject(new Error('Local work database blocked'));
    });
  }
  assertActive() { if (!this.active) throw new Error('Owner binding revoked'); }
  async transaction(mode, action) {
    this.assertActive();
    const db = await this.db;
    this.assertActive();
    const tx = db.transaction(['loads', 'attachments', 'outbox'], mode);
    const done = new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onabort = () => reject(tx.error || new Error('Local transaction aborted')); tx.onerror = () => {}; });
    const stores = Object.fromEntries(['loads', 'attachments', 'outbox'].map(name => [name, tx.objectStore(name)]));
    try { const value = await action(stores); await done; return value; }
    catch (error) { try { tx.abort(); } catch {} await done.catch(() => {}); throw error; }
  }
  async saveLoad(payload, { loadId = id(), attachments = [] } = {}) {
    this.assertActive();
    if (typeof loadId !== 'string' || !loadId.trim()) throw new Error('Load ID required');
    for (const [key, value] of Object.entries(payload)) {
      if (!FIELDS.has(key) || typeof value !== 'string') throw new Error('Invalid work payload field');
      if (TIMES.test(key) && value && (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value)))) throw new Error('Timestamp requires ISO offset');
    }
    for (const blob of attachments) if (!(blob instanceof Blob) || blob.size > 10 * 1024 * 1024) throw new Error('Attachment exceeds 10 MiB or is not a Blob');
    return this.transaction('readwrite', async s => {
      const previous = await request(s.loads.get(loadId));
      const existing = (await request(s.attachments.getAll())).filter(a => a.load_id === loadId);
      if (existing.length + attachments.length > 20 || [...existing.map(a => a.blob), ...attachments].reduce((sum, b) => sum + b.size, 0) > 50 * 1024 * 1024) throw new Error('Load attachment limit exceeded');
      const load = { id: loadId, owner: this.owner, generation: (previous?.generation || 0) + 1, revision: previous?.revision || 0, payload: { ...payload } };
      s.loads.put(load);
      s.outbox.put({ id: id(), owner: this.owner, kind: 'load', load_id: loadId, generation: load.generation, base_revision: load.revision, payload: load.payload, state: 'pending', attempted: false });
      for (const blob of attachments) {
        const attachment = { id: id(), owner: this.owner, load_id: loadId, blob, state: 'pending' };
        s.attachments.put(attachment);
        s.outbox.put({ id: id(), owner: this.owner, kind: 'attachment', load_id: loadId, attachment_id: attachment.id, generation: load.generation, state: 'pending', attempted: false });
      }
      return { ...load, status: 'saved locally' };
    });
  }
  listLoads() { return this.transaction('readonly', s => request(s.loads.getAll())); }
  listOutbox() { return this.transaction('readonly', s => request(s.outbox.getAll())); }
  listAttachments() { return this.transaction('readonly', s => request(s.attachments.getAll())); }
  sync() {
    this.assertActive();
    if (!this.transport) return Promise.reject(new Error('Authenticated transport required'));
    if (!this.running) this.running = this.syncPending().finally(() => { this.running = null; });
    return this.running;
  }
  async syncPending() {
    // Generations impose causal ordering; operation IDs and attempted bodies survive retries.
    const queue = (await this.listOutbox()).sort((a, b) => a.generation - b.generation || (a.kind === 'load' ? -1 : 1));
    let synced = 0;
    for (const candidate of queue) {
      this.assertActive();
      const op = await this.transaction('readwrite', async s => {
        const current = await request(s.outbox.get(candidate.id));
        if (!current || current.state === 'conflict') return null;
        const blockers = (await request(s.outbox.getAll())).some(other => other.load_id === current.load_id && other.id !== current.id && (other.generation < current.generation || (other.generation === current.generation && other.kind === 'load' && current.kind !== 'load')));
        if (blockers) return null;
        current.state = 'sending'; current.attempted = true; s.outbox.put(current); return current;
      });
      if (!op) continue;
      try {
        let body, path, headers;
        if (op.kind === 'load') {
          path = '/api/v1/fe-express/driver-records/sync';
          body = { op_id: op.id, load_id: op.load_id, base_revision: op.base_revision, payload: op.payload };
        } else {
          const attachment = (await this.listAttachments()).find(a => a.id === op.attachment_id);
          if (!attachment) throw new Error('Missing local attachment');
          body = attachment.blob;
          path = `/api/v1/fe-express/driver-records/loads/${encodeURIComponent(op.load_id)}/attachments`;
          headers = { 'X-Operation-Id': op.id, 'Content-Type': body.type || 'application/octet-stream' };
        }
        const response = await this.transport({ method: 'POST', path, body, headers });
        this.assertActive(); // A response from a revoked session cannot acknowledge local work.
        if (response.status === 409) {
          await this.transaction('readwrite', async s => { const current = await request(s.outbox.get(op.id)); if (current) { current.state = 'conflict'; s.outbox.put(current); } });
          continue;
        }
        if (response.status < 200 || response.status >= 300) throw new Error(`Sync failed (${response.status})`);
        if (op.kind === 'load' && (response.data?.load_id !== op.load_id || !Number.isInteger(response.data?.revision) || response.data.revision !== op.base_revision + 1)) throw new Error('Invalid revision acknowledgement');
        if (op.kind === 'attachment' && (!response.data?.attachment_id || !/^[a-f0-9]{64}$/i.test(response.data?.sha256 || '') || response.data.size !== body.size || response.data.media_type !== (body.type || 'application/octet-stream'))) throw new Error('Invalid attachment acknowledgement');
        await this.transaction('readwrite', async s => {
          const current = await request(s.outbox.get(op.id));
          if (!current || current.owner !== this.owner || current.generation !== op.generation) return;
          if (op.kind === 'load') {
            const load = await request(s.loads.get(op.load_id));
            if (load) { load.revision = response.data.revision; s.loads.put(load); }
            for (const next of await request(s.outbox.getAll())) if (next.load_id === op.load_id && next.kind === 'load' && next.generation > op.generation && !next.attempted) { next.base_revision = response.data.revision; s.outbox.put(next); }
          } else {
            const attachment = await request(s.attachments.get(op.attachment_id));
            if (attachment) { attachment.state = 'synced'; attachment.remote = response.data; s.attachments.put(attachment); }
          }
          s.outbox.delete(op.id);
        });
        synced++;
      } catch (error) {
        if (this.active) await this.transaction('readwrite', async s => { const current = await request(s.outbox.get(op.id)); if (current?.state === 'sending') { current.state = 'pending'; s.outbox.put(current); } });
        throw error;
      }
    }
    return { synced };
  }
  async close() { this.active = false; (await this.db).close(); }
}
