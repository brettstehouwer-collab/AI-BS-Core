import { FEExpressOfflineStore } from '../utils/feExpressOfflineStore.js';
// Review/journal storage is owner-separated from the legacy capture database.
// Cross-database writes use an immutable write-ahead intent and reconciliation;
// they are deliberately not represented as one atomic transaction.
const read = request => new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); });
function reviewDatabase(indexedDB,owner) {
  let opened;
  const database=()=>opened ||= new Promise((resolve,reject)=>{
    const request=indexedDB.open(`aibs-fe-driver-reviews-v1:${encodeURIComponent(owner)}`,1);
    request.onupgradeneeded=()=>{for(const name of ['reviews','journal','commits'])request.result.createObjectStore(name,{keyPath:'id'});};
    request.onsuccess=()=>resolve(request.result); request.onerror=()=>reject(request.error); request.onblocked=()=>reject(new Error('Review database blocked'));
  });
  return {
    async transaction(mode,action) {
      const db=await database(),tx=db.transaction(['reviews','journal','commits'],mode);
      const done=new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error||new Error('Review journal transaction aborted'));tx.onerror=()=>{};});
      const stores=Object.fromEntries(['reviews','journal','commits'].map(name=>[name,tx.objectStore(name)]));
      try{const result=await action(stores);await done;return result;}catch(error){try{tx.abort();}catch{}await done.catch(()=>{});throw error;}
    },
    async close(){if(opened)(await opened).close();},
  };
}
const fields = new Set('load_ref pickup_address delivery_address pickup_appointment delivery_appointment pickup_arrival pickup_departure delivery_arrival delivery_departure notes delays pay_issues expenses dispatch_text'.split(' '));
const validId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,100}$/.test(value);
function validateRemote(data) {
  if (!Array.isArray(data?.loads)) throw new Error('Invalid remote load catalogue');
  const ids = new Set();
  return data.loads.map(load => {
    if (!validId(load.load_id) || ids.has(load.load_id) || !Number.isSafeInteger(load.revision) || load.revision < 1 || !load.payload || typeof load.payload !== 'object' || Array.isArray(load.payload) || typeof load.updated_at !== 'string' || !Array.isArray(load.attachments)) throw new Error('Invalid remote load record');
    ids.add(load.load_id);
    for (const [key,value] of Object.entries(load.payload)) if (!fields.has(key) || typeof value !== 'string' || value.length > 16000) throw new Error('Invalid remote work field');
    const attachments = new Set();
    for (const item of load.attachments) {
      if (!validId(item.attachment_id) || attachments.has(item.attachment_id) || !/^[a-f0-9]{64}$/.test(item.sha256 || '') || !Number.isSafeInteger(item.size) || item.size < 1 || item.size > 10 * 1024 * 1024 || typeof item.media_type !== 'string' || !/^(image\/(jpeg|png)|application\/(pdf|octet-stream)|audio\/(webm|ogg|mp4|mpeg|wav))(;codecs=opus)?$/.test(item.media_type)) throw new Error('Invalid remote evidence metadata');
      attachments.add(item.attachment_id);
    }
    if (load.attachments.length > 20 || load.attachments.reduce((sum,item)=>sum+item.size,0)>50*1024*1024) throw new Error('Remote evidence limit exceeded');
    return structuredClone(load);
  });
}
const remoteEqual = (left,right) => JSON.stringify(left) === JSON.stringify(right);
async function combineRecords(store,loads) {
  const metadata=await store.reviews.transaction('readonly',async s=>({reviews:await read(s.reviews.getAll()),journal:await read(s.journal.getAll()),commits:await read(s.commits.getAll())}));
  return loads.map(load=>({...load,remote:metadata.reviews.find(item=>item.id===load.id)?.remote||null,journal:metadata.journal.filter(item=>item.loadId===load.id).map(item=>({...item,status:metadata.commits.some(commit=>commit.id===item.id)?'committed':'confirmation pending'}))}));
}
async function mergeRemote(store,records,guard) {
  const before=await store.transaction('readonly',async s=>({loads:await read(s.loads.getAll()),queue:await read(s.outbox.getAll())}));
  const plans=[];
  for(const record of records) {
    const prior=before.loads.find(load=>load.id===record.load_id);
    if(prior&&prior.revision>record.revision)continue;
    const pending=before.queue.some(op=>op.load_id===record.load_id);
    const load=pending?prior:{id:record.load_id,owner:store.owner,generation:prior?.generation||0,revision:record.revision,payload:record.payload};
    if(!load)throw new Error('Pending operation without local load');
    plans.push({record,prior,load,pending});
  }
  // Persist the whole review batch before the separate atomic capture merge.
  await store.reviews.transaction('readwrite',async s=>{
    guard();
    for(const {record,load} of plans)s.reviews.put({id:record.load_id,remote:{...record,reviewToken:crypto.randomUUID()},reviewGeneration:load.generation,reviewRevision:load.revision});
  });
  await store.transaction('readwrite',async s=>{
    const queue=await read(s.outbox.getAll());
    for(const {record,prior,load,pending} of plans) {
      if(pending||queue.some(op=>op.load_id===record.load_id))continue;
      const current=await read(s.loads.get(record.load_id));
      if(!remoteEqual(current,prior))continue;
      guard();s.loads.put(load);
    }
    guard();
  });
}
async function resolveRemote(store,loadId,token,decision,fresh,guard) {
  if(!['keep-local','use-server','new-copy'].includes(decision))throw new Error('Explicit conflict decision required');
  let entry=await store.reviews.transaction('readonly',s=>read(s.journal.get(token)));
  if(entry&&entry.decision!==decision)throw new Error('Review was already resolved differently');
  if(!entry) {
    const metadata=await store.reviews.transaction('readonly',s=>read(s.reviews.get(loadId)));
    const local=await store.transaction('readonly',async s=>({load:await read(s.loads.get(loadId)),outbox:(await read(s.outbox.getAll())).filter(op=>op.load_id===loadId),attachments:(await read(s.attachments.getAll())).filter(item=>item.load_id===loadId)}));
    if(!metadata?.remote||!local.load)throw new Error('Pull and review the server snapshot first');
    const {reviewToken,...reviewed}=metadata.remote;
    if(token!==reviewToken||local.load.generation!==metadata.reviewGeneration||local.load.revision!==metadata.reviewRevision||!remoteEqual(reviewed,fresh))throw new Error('Review is stale; pull and review current local/server versions');
    if(local.outbox.some(op=>op.state==='sending'))throw new Error('Wait for current synchronization before resolving');
    const copyId=decision==='new-copy'?crypto.randomUUID():null;
    const proposed={id:token,loadId,reviewToken:token,decision,local:structuredClone(local.load),remote:structuredClone(reviewed),outbox:structuredClone(local.outbox),attachmentIds:local.attachments.map(item=>item.id),at:new Date().toISOString(),result:{loadId,...(copyId?{copyId}:{})}};
    entry=await store.reviews.transaction('readwrite',async s=>{const prior=await read(s.journal.get(token));if(prior){if(prior.decision!==decision)throw new Error('Review already resolved differently');return prior;}guard();s.journal.add(proposed);return proposed;});
  }
  const committed=await store.reviews.transaction('readonly',s=>read(s.commits.get(entry.id)));
  if(committed)return entry.result;
  await store.transaction('readwrite',async s=>{
    const load=await read(s.loads.get(loadId)),copyId=entry.result.copyId,copy=copyId?await read(s.loads.get(copyId)):null;
    // A capture commit may outlive its separate journal confirmation. Never replay.
    if(load?.reviewResolutionId===entry.id||copy?.reviewResolutionId===entry.id)return;
    const outbox=(await read(s.outbox.getAll())).filter(op=>op.load_id===loadId);
    if(!remoteEqual(load,entry.local)||!remoteEqual(outbox,entry.outbox))throw new Error('Resolution needs attention: capture changed after journal preparation; no replay performed');
    const attachments=(await read(s.attachments.getAll())).filter(item=>item.load_id===loadId);
    if(!remoteEqual(attachments.map(item=>item.id),entry.attachmentIds))throw new Error('Resolution needs attention: evidence changed after journal preparation');
    const generation=load.generation+1,resolved={...load,generation,revision:entry.remote.revision,reviewResolutionId:entry.id};
    guard();
    for(const op of outbox)s.outbox.delete(op.id);
    if(decision==='keep-local') {
      s.loads.put(resolved);
      s.outbox.put({id:crypto.randomUUID(),owner:store.owner,kind:'load',load_id:loadId,generation,base_revision:entry.remote.revision,payload:load.payload,state:'pending',attempted:false});
      for(const item of attachments.filter(item=>item.state!=='synced'&&!item.archived))s.outbox.put({id:crypto.randomUUID(),owner:store.owner,kind:'attachment',load_id:loadId,attachment_id:item.id,generation,state:'pending',attempted:false});
    } else {
      s.loads.put({...resolved,payload:entry.remote.payload});
      for(const item of attachments.filter(item=>item.state!=='synced'))s.attachments.put({...item,state:'retained locally',archived:true});
      if(copyId) {
        s.loads.put({id:copyId,owner:store.owner,generation:1,revision:0,payload:load.payload,reviewResolutionId:entry.id});
        s.outbox.put({id:crypto.randomUUID(),owner:store.owner,kind:'load',load_id:copyId,generation:1,base_revision:0,payload:load.payload,state:'pending',attempted:false});
        for(const item of attachments.filter(item=>item.state!=='synced'&&!item.archived)) {
          const clone={...item,id:crypto.randomUUID(),load_id:copyId,state:'pending',archived:false};s.attachments.put(clone);
          s.outbox.put({id:crypto.randomUUID(),owner:store.owner,kind:'attachment',load_id:copyId,attachment_id:clone.id,generation:1,state:'pending',attempted:false});
        }
      }
    }
    guard();
  });
  try{await store.reviews.transaction('readwrite',async s=>{guard();s.commits.put({id:entry.id,at:new Date().toISOString()});});}
  catch(error){throw new Error('Resolution saved; journal confirmation pending. Retry the same reviewed decision; no duplicate copy will be created.',{cause:error});}
  return entry.result;
}
async function persistEvidence(store,loadId,metadata,blob,guard) {
  const review=await store.reviews.transaction('readonly',s=>read(s.reviews.get(loadId)));
  if(!remoteEqual(review?.remote?.attachments.find(item=>item.attachment_id===metadata.attachment_id),metadata))throw new Error('Evidence review changed; pull again');
  return store.transaction('readwrite',async s=>{
    const existing=await read(s.attachments.getAll()),cached=existing.find(item=>item.load_id===loadId&&remoteEqual(item.remote,metadata));
    if(cached)return cached;
    const attachment={id:crypto.randomUUID(),owner:store.owner,load_id:loadId,blob,state:'synced',remote:metadata};
    guard();s.attachments.put(attachment);return attachment;
  });
}

const PREFIX = '/api/v1/fe-express/driver-records';
// Enrollment only enables reopening this browser's work cache. It is not server
// authorization or encryption; every upload requires fresh Firebase admission.
export function createDriverClient({ auth, subscribeAuth, baseUrl = 'https://api.brettstehouwer.live', fetchImpl = globalThis.fetch.bind(globalThis), storage = globalThis.localStorage, indexedDB = globalThis.indexedDB, online = () => globalThis.navigator?.onLine !== false } = {}) {
  const base = new URL(baseUrl);
  if (base.username || base.password || base.pathname !== '/' || base.search || base.hash || !(base.origin === 'https://api.brettstehouwer.live' || (base.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(base.hostname) && ['8000', '8080'].includes(base.port)))) throw new Error('Unapproved driver API origin');
  let store, uid, owner, generation = 0, closed = false;
  let snapshot = { status: 'closed', error: null, owner: null, uid: null, conflicts: 0 };
  const listeners = new Set(), controllers = new Set();
  const publish = changes => { snapshot = { ...snapshot, ...changes }; for (const listener of listeners) listener(snapshot); };
  const revoke = () => {
    generation++; for (const controller of controllers) controller.abort(); controllers.clear();
    const prior = store; store = null; if (prior) { void prior.close().catch(() => {}); void prior.reviews?.close().catch(() => {}); }
    publish({ status: 'locked', owner: null, uid: null, error: 'Sign-in changed; reopen for the current account.' });
  };
  const unsubscribe = subscribeAuth?.(user => { if (uid && user?.uid !== uid) revoke(); });
  const guard = (version, expectedUid) => { if (closed || version !== generation || auth?.currentUser?.uid !== expectedUid) { if (version === generation && !closed) revoke(); throw new Error('Driver account binding changed'); } };
  const key = value => `aibs-fe-driver-enrollment-v1:${encodeURIComponent(value)}`;
  const request = async (path, { method = 'GET', body, headers = {}, evidence } = {}, version, expectedUid) => {
    guard(version, expectedUid);
    const user = auth.currentUser;
    const token = await user.getIdToken(true);
    guard(version, expectedUid);
    const controller = new AbortController(); controllers.add(controller);
    try {
      let response;
      try {
        response = await fetchImpl(`${base.origin}${path}`, { method, headers: { ...headers, Authorization: `Bearer ${token}`, ...(body && !(body instanceof Blob) ? { 'Content-Type': 'application/json' } : {}) }, body: body instanceof Blob ? body : body === undefined ? undefined : JSON.stringify(body), signal: controller.signal, redirect: 'error', credentials: 'omit', cache: 'no-store' });
      } catch (error) {
        guard(version, expectedUid);
        if (error instanceof TypeError && !controller.signal.aborted) throw Object.assign(new Error('Driver API network unavailable'), { code: 'driver/network-unavailable' });
        throw error;
      }
      guard(version, expectedUid);
      if (response.redirected || (response.url && new URL(response.url).origin !== base.origin)) throw new Error('Driver API redirect rejected');
      let data;
      if(evidence && response.status===200) {
        const declared=response.headers.get('content-length');
        if(declared!==null && Number(declared)!==evidence.size) throw new Error('Evidence length does not match metadata');
        if(response.headers.get('content-type')!==evidence.media_type) throw new Error('Evidence media type does not match metadata');
        const reader=response.body?.getReader();
        if(!reader) throw new Error('Bounded evidence stream required');
        const chunks=[]; let size=0;
        try { while(true) { const chunk=await reader.read(); guard(version,expectedUid); if(chunk.done) break; size+=chunk.value.byteLength; if(size>evidence.size || size>10*1024*1024) throw new Error('Evidence download exceeds bounded metadata'); chunks.push(chunk.value); } }
        catch(error) { await reader.cancel().catch(()=>{}); throw error; }
        if(size!==evidence.size) throw new Error('Evidence download was truncated');
        data=new Blob(chunks,{type:evidence.media_type});
        const digest=await crypto.subtle.digest('SHA-256',await data.arrayBuffer());
        const hash=Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');
        if(hash!==evidence.sha256) throw new Error('Evidence download hash mismatch');
      } else data = await response.json();
      guard(version, expectedUid);
      return { status: response.status, data };
    } finally { controllers.delete(controller); }
  };
  const identity = async (version, expectedUid) => {
    const result = await request(`${PREFIX}/identity`, {}, version, expectedUid);
    if (result.status !== 200 || result.data?.scope !== 'driver_work' || result.data.owner !== `firebase:ai-bs-dashboard:${expectedUid}`) throw new Error('Verified Firebase administrator identity required');
    return result.data.owner;
  };
  const run = async action => { try { return await action(); } catch (error) { publish({ status: store ? 'error' : 'locked', error: error.message }); throw error; } };
  const active = () => { guard(generation, uid); if (!store) throw new Error('Open the driver work cache first'); return store; };
  const list = () => run(async () => {
    const current = active(), version = generation;
    const [loads, outbox, attachments] = await Promise.all([current.listLoads(), current.listOutbox(), current.listAttachments()]);
    guard(version, uid); publish({ conflicts: outbox.filter(op => op.state === 'conflict').length });
    const combined=await combineRecords(current,loads); guard(version,uid);
    return { loads:combined, outbox, attachments };
  });
  const fetchRemote = async (version,expectedUid) => {
    if(!online()) throw new Error('Online verification required for remote work');
    if(await identity(version,expectedUid)!==owner) throw new Error('Driver owner changed');
    const response=await request(`${PREFIX}/loads`,{},version,expectedUid);
    if(response.status!==200) throw new Error(`Remote retrieval failed (${response.status})`);
    return validateRemote(response.data);
  };
  return {
    getSnapshot: () => snapshot,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    open: () => run(async () => {
      if (closed) throw new Error('Driver client closed');
      await auth?.authStateReady?.();
      const nextUid = auth?.currentUser?.uid;
      if (!nextUid) throw new Error('Sign in to open driver work');
      revoke(); uid = nextUid; const version = generation;
      publish({ status: 'opening', error: null, uid });
      let offlineCache = !online();
      if (!offlineCache) {
        try {
          owner = await identity(version, uid);
          guard(version, uid);
          storage.setItem(key(uid), JSON.stringify({ uid, owner, scope: 'driver_work' }));
        } catch (error) {
          guard(version, uid);
          if (!['driver/network-unavailable', 'auth/network-request-failed'].includes(error.code)) throw error;
          offlineCache = true;
        }
      }
      if (offlineCache) {
        const enrollment = JSON.parse(storage.getItem(key(uid)) || 'null');
        if (enrollment?.uid !== uid || enrollment.scope !== 'driver_work' || enrollment.owner !== `firebase:ai-bs-dashboard:${uid}`) throw new Error('Online identity enrollment required before offline use');
        owner = enrollment.owner;
      }
      guard(version, uid);
      store = new FEExpressOfflineStore({ owner, scope: 'driver_work', verified: true }, { indexedDB, transport: async operation => {
        guard(version, nextUid);
        if (!online()) throw new Error('Offline; work remains saved locally');
        if (await identity(version, nextUid) !== owner) throw new Error('Driver owner changed');
        const response = await request(operation.path, operation, version, nextUid);
        if (operation.body instanceof Blob && response.status >= 200 && response.status < 300) {
          const digest = await crypto.subtle.digest('SHA-256', await operation.body.arrayBuffer());
          guard(version, nextUid);
          const sha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
          if (response.data?.attachment_id !== operation.headers?.['X-Operation-Id'] || response.data?.sha256 !== sha256) throw new Error('Evidence acknowledgement does not match original attachment');
        }
        return response;
      } });
      store.reviews=reviewDatabase(indexedDB,owner);
      publish({ status: offlineCache ? 'offline' : 'ready', owner, uid, error: null });
      return list();
    }),
    list,
    truckProfile: (operation) => run(async () => {
      active(); const version = generation, expectedUid = uid;
      if (!online()) throw new Error('Offline; truck profile remains on this device');
      if (await identity(version, expectedUid) !== owner) throw new Error('Driver owner changed');
      return request(`${PREFIX}/truck-profile`, operation === undefined ? {} : { method: 'POST', body: operation }, version, expectedUid);
    }),
    pull: () => run(async()=>{
      const current=active(),version=generation,expectedUid=uid;
      const remote=await fetchRemote(version,expectedUid);
      guard(version,expectedUid);
      await mergeRemote(current,remote,()=>guard(version,expectedUid));
      const records=await list(); publish({status:records.outbox.some(op=>op.state==='conflict')?'conflict':'ready',error:null}); return records;
    }),
    resolveConflict: (loadId,reviewToken,decision) => run(async()=>{
      const current=active(),version=generation,expectedUid=uid;
      if(!validId(loadId) || typeof reviewToken!=='string') throw new Error('Load and reviewed snapshot required');
      if(current.running) throw new Error('Wait for synchronization before resolving');
      const remote=await fetchRemote(version,expectedUid),fresh=remote.find(load=>load.load_id===loadId);
      if(!fresh) throw new Error('Reviewed server load no longer exists');
      guard(version,expectedUid);
      const result=await resolveRemote(current,loadId,reviewToken,decision,fresh,()=>guard(version,expectedUid));
      await list(); publish({status:'saved locally',error:null}); return result;
    }),
    downloadRemoteEvidence: (loadId,attachmentId) => run(async()=>{
      const current=active(),version=generation,expectedUid=uid;
      if(!validId(loadId)||!validId(attachmentId)) throw new Error('Valid load and evidence IDs required');
      const records=await list(),load=records.loads.find(item=>item.id===loadId),metadata=load?.remote?.attachments.find(item=>item.attachment_id===attachmentId);
      if(!metadata) throw new Error('Pull remote evidence metadata first');
      const cached=records.attachments.find(item=>item.load_id===loadId&&remoteEqual(item.remote,metadata));
      if(cached) { guard(version,expectedUid); return cached; }
      if(!online()) throw new Error('Evidence is not cached; online verification required');
      if(await identity(version,expectedUid)!==owner) throw new Error('Driver owner changed');
      const response=await request(`${PREFIX}/loads/${encodeURIComponent(loadId)}/attachments/${encodeURIComponent(attachmentId)}`,{evidence:metadata},version,expectedUid);
      if(response.status!==200) throw new Error(`Evidence retrieval failed (${response.status})`);
      return persistEvidence(current,loadId,metadata,response.data,()=>guard(version,expectedUid));
    }),
    save: (payload, options) => run(async () => { const current = active(), version = generation; if(options?.loadId!==undefined&&!validId(options.loadId)) throw new Error('Valid work load ID required'); const result = await current.saveLoad(payload, options); guard(version, uid); publish({ status: 'saved locally', error: null }); return result; }),
    sync: () => run(async () => { const current = active(), version = generation; publish({ status: 'syncing', error: null }); const result = await current.sync(); guard(version, uid); const records = await list(); publish({ status: records.outbox.some(op => op.state === 'conflict') ? 'conflict' : 'ready' }); return result; }),
    async close() { closed = true; unsubscribe?.(); revoke(); publish({ status: 'closed', error: null }); listeners.clear(); },
  };
}
