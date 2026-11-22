// Personal-only browser records. Tokens and response bodies are never cached.
const PREFIX = '/api/personal-finance';
const allowedBase = value => {
  const url = new URL(value);
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
      !(url.origin === 'https://api.brettstehouwer.live' ||
        /^http:\/\/(127\.0\.0\.1|localhost):(8000|8080)$/.test(url.origin))) throw Error('Untrusted personal API origin');
  return url.origin;
};
const tx = (db, store, mode, action) => new Promise((resolve, reject) => {
  const t = db.transaction(store, mode), req = action(t.objectStore(store));
  let result;
  req.onsuccess = () => { result = req.result; };
  t.oncomplete = () => resolve(result);
  t.onerror = t.onabort = () => reject(t.error || Error('Local record was not saved'));
});
const openStore = uid => new Promise((resolve, reject) => {
  const request = indexedDB.open('aibs-personal-finance-v1:' + encodeURIComponent(uid), 1);
  request.onupgradeneeded = () => {
    request.result.createObjectStore('state');
    request.result.createObjectStore('uploads', { keyPath: 'id' });
  };
  request.onsuccess = () => resolve(request.result);
  request.onerror = () => reject(request.error);
  request.onblocked = () => reject(Error('Close older personal-finance tabs to open saved records'));
});

export async function createPersonalClient({ auth, base = 'https://api.brettstehouwer.live', onUnauthorized = () => {} }) {
  const origin = allowedBase(base), user = auth.currentUser, uid = user?.uid;
  if (!uid) throw Error('Sign in to open personal finance');
  // One writer tab per personal owner; a second tab cannot replace its draft.
  if (!navigator.locks) throw Error('This browser cannot safely open personal drafts');
  let release;
  await new Promise((resolve, reject) => navigator.locks.request('aibs-personal-finance:' + uid,
    { mode: 'exclusive', ifAvailable: true }, async lock => {
      if (!lock) throw Error('Close the other personal-finance tab before opening this one');
      await new Promise(unlock => { release = unlock; resolve(); });
    }).catch(reject));
  let db;
  try { db = await openStore(uid); } catch (error) { release(); throw error; }
  const controllers = new Set();
  let active = true, busy = false, mode = 'opening';
  const guard = () => { if (!active || auth.currentUser !== user) throw Error('Personal account changed; saved records remain on this device'); };
  const close = () => { active = false; controllers.forEach(c => c.abort()); db.close(); release(); };
  const request = async (path, options = {}, binary = false, admissionProbe = false) => {
    guard();
    if (mode === 'offline' && !admissionProbe) throw Error('Offline: reconnect and verify personal access before server actions');
    const controller = new AbortController(); controllers.add(controller);
    const timer = setTimeout(() => controller.abort(), 30000);
    let responded = false;
    try {
      const token = await user.getIdToken(); guard();
      if (!token) throw Error('Sign in again');
      const response = await fetch(origin + PREFIX + path, { ...options, credentials: 'omit', redirect: 'error',
        cache: 'no-store', signal: controller.signal, headers: { ...options.headers, Authorization: 'Bearer ' + token } });
      responded = true;
      guard();
      if (response.status === 401 || response.status === 403) {
        try { await tx(db,'state','readwrite',s=>s.delete('admission')); }
        finally { close(); onUnauthorized(); }
        throw Error('Personal financial access denied; saved local records retained');
      }
      if (!response.ok) {
        const error = Error(`Personal request failed (${response.status}); keep the saved draft and review before retrying`);
        error.status = response.status; throw error;
      }
      const data = binary ? await response.blob() : await response.json(); guard();
      return data;
    } catch (error) {
      if (!responded && (error instanceof TypeError || error.name === 'AbortError' || error.code === 'auth/network-request-failed')) error.transportUnavailable = true;
      throw error;
    } finally { clearTimeout(timer); controllers.delete(controller); }
  };
  const put = (store, key, value) => { guard(); return tx(db, store, 'readwrite', s => key === undefined ? s.put(value) : s.put(value, key)); };
  const state = (key = 'draft') => { guard(); return tx(db, 'state', 'readonly', s => s.get(key)); };
  const exclusive = async action => {
    guard(); if (busy) throw Error('A personal update is already running'); busy = true;
    try { return await action(); } finally { busy = false; }
  };
  const retainLocalFile = async (target, parentId, file) => {
    guard();
    if (!Number.isSafeInteger(parentId) || parentId < 1 || !file.size || file.size > 10 * 1024 * 1024) throw Error('Choose a record and a nonempty file up to 10 MiB');
    const row = { id: crypto.randomUUID(), ...(target === 'filing' ? {target,filingId:parentId} : {paymentId:parentId}), name:file.name, type:file.type || 'application/octet-stream', blob:file };
    await put('uploads',undefined,row); guard(); return row;
  };
  const verifiedDownload = async (path, document) => {
    const blob = await request(path,{},true);
    if (blob.size !== document.size) throw Error('Original size mismatch; download withheld');
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))].map(b=>b.toString(16).padStart(2,'0')).join('');
    guard(); if (digest !== document.sha256) throw Error('Original checksum mismatch; download withheld');
    return blob;
  };
  const admit = async () => {
    const data = await request('/payments',{},false,true);
    if (data?.status !== 'success' || !Array.isArray(data.payments)) throw Error('Personal owner admission response is invalid');
    await put('state','admission',{uid,scope:'personal_finance'}); guard(); mode = 'online';
  };
  try {
    // Offline access exposes only this previously admitted UID's local drafts/files.
    // HTTP rejection, server errors and malformed responses never authorize fallback.
    try { await admit(); }
    catch (error) {
      if (!error.transportUnavailable) throw error;
      const previous = await state('admission'); guard();
      if (previous?.uid !== uid || previous.scope !== 'personal_finance') throw Error('An online personal-owner check is required before offline access');
      mode = 'offline';
    }
    guard();
    return {
      close, request: (path,options,binary) => request(path,options,binary),
      get mode() { return mode; },
      reconnect() { return exclusive(admit); },
      async draft() { const row = await state(); guard(); return row || { fields: null, pending: null }; },
      async saveDraft(fields) {
        return exclusive(async () => {
          const row = await state();
          if (row?.pending) throw Error('Resolve the saved payment retry before editing');
          await put('state', 'draft', { fields, pending: null }); guard();
        });
      },
      async submit() {
        return exclusive(async () => {
          let row = await state();
          if (!row?.fields) throw Error('Save a payment draft first');
          if (!row.pending) { row = { ...row, pending: { id: crypto.randomUUID(), payload: structuredClone(row.fields) } }; await put('state', 'draft', row); }
          let result;
          try { result = await request('/payments', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': row.pending.id }, body: JSON.stringify(row.pending.payload) }); }
          catch (error) {
            // A schema rejection is a known non-commit; preserve editable fields.
            if (error.status === 422) await put('state', 'draft', { fields: row.fields, pending: null });
            throw error;
          }
          await put('state', 'draft', { fields: null, pending: null }); guard();
          return result;
        });
      },
      async uploads() { guard(); const rows = await tx(db, 'uploads', 'readonly', s => s.getAll()); guard(); return rows; },
      async filingDraft() { const row=await state('filing'); guard(); return row || {fields:null,pending:null}; },
      async saveFilingDraft(fields) {
        return exclusive(async()=>{const row=await state('filing');if(row?.pending)throw Error('Resolve the saved filing retry before editing');await put('state','filing',{fields,pending:null});guard();});
      },
      async submitFiling() {
        return exclusive(async()=>{
          let row=await state('filing');if(!row?.fields)throw Error('Save a filing draft first');
          if(!row.pending){row={...row,pending:{id:crypto.randomUUID(),payload:{...structuredClone(row.fields),filing_year:Number(row.fields.filing_year)}}};await put('state','filing',row);}
          let result;
          try{result=await request('/filings',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':row.pending.id},body:JSON.stringify(row.pending.payload)});}
          catch(error){if(error.status===422)await put('state','filing',{fields:row.fields,pending:null});throw error;}
          await put('state','filing',{fields:null,pending:null});guard();return result;
        });
      },
      retainFilingFile(filingId,file) { return retainLocalFile('filing',filingId,file); },
      async retainFile(paymentId, file) {
        return retainLocalFile('payment',paymentId,file);
      },
      async sendFile(id) {
        return exclusive(async () => {
          const row = await tx(db, 'uploads', 'readonly', s => s.get(id)); guard();
          if (!row) throw Error('Saved original not found');
          // URI encoding avoids lossy HTTP-header conversion of Unicode names.
          const target=row.target==='filing'?`/filings/${row.filingId}/originals`:`/payments/${row.paymentId}/documents`;
          const result = await request(target, { method: 'POST',
            headers: { 'Content-Type': row.type, 'Idempotency-Key': row.id, 'X-Document-Name': encodeURIComponent(row.name), 'X-Document-Name-Encoding': 'uri' }, body: row.blob });
          await tx(db, 'uploads', 'readwrite', s => s.delete(id)); guard(); return result;
        });
      },
      async download(paymentId, document) {
        return verifiedDownload(`/payments/${paymentId}/documents/${encodeURIComponent(document.document_id)}`,document);
      },
      downloadFiling(filingId,document) { return verifiedDownload(`/filings/${filingId}/originals/${encodeURIComponent(document.document_id)}`,document); },
    };
  } catch (error) { close(); throw error; }
}
