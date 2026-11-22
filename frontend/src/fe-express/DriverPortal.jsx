import React, { useEffect, useRef, useState } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase.js';
import LoginModal from '../components/LoginModal.jsx';
import { ADMIN_EMAILS, ADMIN_UIDS } from '../components/accessControl.js';
import { createDriverClient } from './driverClient.js';
import TruckProfile from './TruckProfile.jsx';

const FIELDS = { load_ref: 'Load reference', pickup_address: 'Pickup address', delivery_address: 'Delivery address', pickup_appointment: 'Pickup appointment', delivery_appointment: 'Delivery appointment', pickup_arrival: 'Pickup arrival', pickup_departure: 'Pickup departure', delivery_arrival: 'Delivery arrival', delivery_departure: 'Delivery departure', notes: 'Notes', delays: 'Delays', pay_issues: 'Pay issues', expenses: 'Expenses', dispatch_text: 'Original WhatsApp / dispatch text' };
const EMPTY = () => Object.fromEntries(Object.keys(FIELDS).map(key => [key, '']));
const approved = user => Boolean(user?.emailVerified && (ADMIN_EMAILS.includes((user.email || '').toLowerCase().trim()) || ADMIN_UIDS.includes(user.uid)));
const localTime = value => { if (!value) return ''; const stamp = new Date(value); if (!Number.isFinite(stamp.getTime())) return ''; return new Date(stamp.getTime() - stamp.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };

export default function DriverPortal() {
  const [user, setUser] = useState(undefined), [status, setStatus] = useState({ status: 'locked' });
  const [records, setRecords] = useState({ loads: [], outbox: [], attachments: [] });
  const [draft, setDraft] = useState(EMPTY), [selected, setSelected] = useState(''), [error, setError] = useState('');
  const [saveState, setSaveState] = useState('No changes'), [recording, setRecording] = useState(false), [previews, setPreviews] = useState([]), [offlineStatus, setOfflineStatus] = useState(''), [waiting, setWaiting] = useState(null);
  const [reviewBusy, setReviewBusy] = useState(false), [connected, setConnected] = useState(() => navigator.onLine !== false);
  const client = useRef(null), current = useRef(null), epoch = useRef(0), timer = useRef(null), queue = useRef(Promise.resolve()), recorder = useRef(null), stream = useRef(null), urls = useRef([]), pending = useRef(false), saving = useRef(0), recordingRequest = useRef(false);
  const stopCapture = () => { if (recorder.current?.state === 'recording') recorder.current.stop(); stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; };
  const refresh = async (instance = client.current, version = epoch.current) => { const next = await instance.list(); if (version === epoch.current) setRecords(next); return next; };
  const flush = () => {
    clearTimeout(timer.current);
    if (!current.current || !pending.current || !client.current) return queue.current;
    const item = { ...current.current, payload: { ...current.current.payload }, attachments: [...current.current.attachments] }, instance = client.current, version = epoch.current;
    current.current.attachments = []; pending.current = false; saving.current++; setSaveState('Saving…');
    const job = queue.current.catch(() => {}).then(async () => {
      try {
        await instance.save(item.payload, { loadId: item.id, attachments: item.attachments });
        if (version !== epoch.current) return;
        await refresh(instance, version); setSaveState(saving.current > 1 ? 'Saving…' : pending.current ? 'Changes waiting to save' : 'Saved locally');
      } catch (failure) {
        if (version === epoch.current) { pending.current = true; if (current.current?.id === item.id) current.current.attachments.unshift(...item.attachments); setSaveState('Save failed'); setError(failure.message); }
        throw failure;
      } finally { saving.current--; }
    });
    queue.current = job; return job;
  };
  const edit = (key, value) => {
    if (!current.current) return;
    current.current.payload = { ...current.current.payload, [key]: value }; setDraft(current.current.payload); pending.current = true; setSaveState('Changes waiting to save');
    clearTimeout(timer.current); timer.current = setTimeout(() => { void flush().catch(() => {}); }, 1200);
  };
  const run = async action => { setError(''); try { await action(); } catch (failure) { setError(failure.message); } };
  const pullRecords = async (sync = false) => {
    const instance = client.current, version = epoch.current;
    setReviewBusy(true);
    try {
      await flush();
      if (version !== epoch.current || instance !== client.current) throw new Error('Account changed before server review');
      if (sync) await instance.sync();
      await instance.pull();
      if (version === epoch.current) await refresh(instance, version);
      // Pull updates review snapshots, never the active form or pending edits.
    } finally { if (version === epoch.current) setReviewBusy(false); }
  };
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, next => {
      epoch.current++; const version = epoch.current; clearTimeout(timer.current); pending.current = false; current.current = null; queue.current = Promise.resolve();
      stopCapture(); setRecording(false); urls.current.forEach(URL.revokeObjectURL); urls.current = []; setPreviews([]); setSelected(''); setDraft(EMPTY()); setRecords({ loads: [], outbox: [], attachments: [] }); setSaveState('No changes'); setError('');
      const prior = client.current; client.current = null; if (prior) void prior.close();
      setUser(next); setStatus({ status: 'locked' }); setReviewBusy(false);
      if (!approved(next)) return;
      const instance = createDriverClient({ auth, subscribeAuth: callback => onAuthStateChanged(auth, callback) }); client.current = instance;
      instance.subscribe(snapshot => { if (version === epoch.current) setStatus(snapshot); });
      void instance.open().then(async data => {
        if (version !== epoch.current) return;
        setRecords(data);
        if (navigator.onLine !== false) { await flush(); if (version !== epoch.current) return; await instance.pull(); await refresh(instance, version); }
      }).catch(failure => { if (version === epoch.current) setError(failure.message); });
    });
    const reconnect = () => { setConnected(true); if (client.current) void run(() => pullRecords(true)); };
    const disconnect = () => setConnected(false);
    window.addEventListener('online', reconnect);
    window.addEventListener('offline', disconnect);
    const beforeUnload = event => { if (pending.current || saving.current || recordingRequest.current || recorder.current?.state === 'recording') { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', beforeUnload);
    return () => { epoch.current++; unsubscribe(); window.removeEventListener('online', reconnect); window.removeEventListener('offline', disconnect); window.removeEventListener('beforeunload', beforeUnload); clearTimeout(timer.current); stopCapture(); void client.current?.close(); urls.current.forEach(URL.revokeObjectURL); };
  }, []);
  useEffect(() => {
    urls.current.forEach(URL.revokeObjectURL);
    const next = records.attachments.filter(item => item.load_id === selected).map(item => ({ ...item, url: URL.createObjectURL(item.blob) }));
    urls.current = next.map(item => item.url); setPreviews(next);
    return () => { next.forEach(item => URL.revokeObjectURL(item.url)); };
  }, [records.attachments, selected]);
  const choose = async id => { const version = epoch.current; await flush(); const latest = await client.current.list(); if (version !== epoch.current) return; const load = latest.loads.find(item => item.id === id); const payload = load ? { ...EMPTY(), ...load.payload } : EMPTY(); current.current = { id, payload, attachments: [] }; setSelected(id); setDraft(payload); setSaveState(load ? 'Saved locally' : 'New load — not saved'); };
  const attach = async files => {
    if (!current.current) throw new Error('Create or select a load first');
    const version = epoch.current, id = current.current.id; await flush(); if (version !== epoch.current || current.current?.id !== id) throw new Error('Account or load changed');
    const latest = await client.current.list();
    if (version !== epoch.current || current.current?.id !== id) throw new Error('Account or load changed');
    const existing = latest.attachments.filter(item => item.load_id === id), added = Array.from(files);
    if (added.some(blob => !blob.size || blob.size > 10 * 1024 * 1024) || existing.length + added.length > 20 || [...existing.map(item => item.blob), ...added].reduce((sum, blob) => sum + blob.size, 0) > 50 * 1024 * 1024) throw new Error('Evidence limit: 10 MiB each, 20 files and 50 MiB per load');
    current.current.attachments.push(...added); pending.current = true; await flush();
  };
  const record = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder) throw new Error('Voice recording is unavailable in this browser');
    if (!current.current) throw new Error('Create or select a load first');
    const version = epoch.current, id = current.current.id;
    if (recordingRequest.current || recorder.current?.state === 'recording') return;
    recordingRequest.current = true;
    let media;
    try { media = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    finally { recordingRequest.current = false; }
    if (version !== epoch.current || current.current?.id !== id) { media.getTracks().forEach(track => track.stop()); return; }
    stream.current = media; let capture;
    try { capture = new MediaRecorder(media); }
    catch (failure) { media.getTracks().forEach(track => track.stop()); stream.current = null; throw failure; }
    const chunks = []; let size = 0, exceeded = false;
    recorder.current = capture;
    capture.ondataavailable = event => { size += event.data.size; if (size > 10 * 1024 * 1024) { exceeded = true; stopCapture(); } else chunks.push(event.data); };
    capture.onstop = async () => {
      media.getTracks().forEach(track => track.stop());
      if (version !== epoch.current) return;
      try {
        if (exceeded) throw new Error('Voice evidence exceeded 10 MiB; record a shorter note.');
        if (current.current?.id !== id) throw new Error('Load changed before voice evidence was saved');
        await attach([new Blob(chunks, { type: capture.mimeType || 'audio/webm' })]);
      } catch (failure) { if (version === epoch.current) setError(failure.message); }
      finally { if (version === epoch.current) setRecording(false); }
    };
    try { capture.start(1000); setRecording(true); }
    catch (failure) { media.getTracks().forEach(track => track.stop()); stream.current = null; throw failure; }
  };
  const prepareOffline = async () => {
    if (!('serviceWorker' in navigator)) throw new Error('Offline shell is unavailable in this browser');
    const persistence = navigator.storage?.persist ? navigator.storage.persist() : Promise.resolve(false);
    const registration = await navigator.serviceWorker.register('/driver/sw.js', { scope: '/driver/' });
    setWaiting(registration.waiting); registration.addEventListener('updatefound', () => { registration.installing?.addEventListener('statechange', () => setWaiting(registration.waiting)); });
    setOfflineStatus(`Offline shell requested. Storage persistence ${await persistence ? 'granted' : 'not granted'}. Enrollment and local work stay in this browser.`);
  };
  const resolve = async decision => {
    const instance = client.current, version = epoch.current, id = selected;
    const token = records.loads.find(load => load.id === id)?.remote?.reviewToken;
    setReviewBusy(true);
    try {
      await flush();
      if (version !== epoch.current || current.current?.id !== id) throw new Error('Account or load changed before resolution');
      const result = await instance.resolveConflict(id, token, decision);
      if (version !== epoch.current || current.current?.id !== id) return;
      const latest = await refresh(instance, version), nextId = result.copyId || id;
      const load = latest.loads.find(item => item.id === nextId);
      if (load && !pending.current) {
        const payload = { ...EMPTY(), ...load.payload };
        current.current = { id: nextId, payload, attachments: [] }; setSelected(nextId); setDraft(payload); setSaveState('Saved locally');
      }
    } finally { if (version === epoch.current) setReviewBusy(false); }
  };
  const downloadRemote = async attachmentId => {
    const instance = client.current, version = epoch.current, id = selected;
    await flush();
    if (version !== epoch.current || current.current?.id !== id) throw new Error('Account or load changed before evidence download');
    await instance.downloadRemoteEvidence(id, attachmentId);
    if (version === epoch.current) await refresh(instance, version);
  };
  if (user === undefined) return <main><h1>FE Express Driver Work</h1><p>Restoring sign-in…</p></main>;
  if (!user) return <main><h1>FE Express Driver Work</h1><p>Work records only. Sign in with your existing administrator account.</p><LoginModal onLoginSuccess={() => {}} backendUrl="https://api.brettstehouwer.live" /></main>;
  const ready = Boolean(status.owner), locked = !ready || recording || reviewBusy;
  const reviewed = records.loads.find(load => load.id === selected), remote = reviewed?.remote;
  return <main aria-busy={reviewBusy}>
    <header><div><p className="eyebrow">FE EXPRESS · WORK ONLY</p><h1>Driver work log</h1><p>{user.email}</p></div><button onClick={() => void signOut(auth)}>Sign out</button></header>
    {!approved(user) && <p role="alert">This verified account is not on the administrator allowlist.</p>}
    <section className="status" aria-live="polite"><strong>{status.status}</strong><span>{records.outbox.length} unsynced operations · {status.conflicts || 0} conflicts</span><span>{saveState}</span></section>
    {(error || status.error) && <p className="error" role="alert">{error || status.error}</p>}
    {!ready && approved(user) && <button onClick={() => void run(async () => { await client.current.open(); await refresh(); })}>Retry verified connection / offline enrollment</button>}
    <p className="notice">Local work and evidence remain in this browser. Browser storage is not encrypted; shared devices need separate accounts. Server synchronization requires current verified access.</p>
    <nav><button disabled={locked} onClick={() => void run(() => choose(crypto.randomUUID()))}>New load</button><button disabled={locked} onClick={() => void run(() => pullRecords(true))}>Sync now</button><button disabled={locked || !connected} onClick={() => void run(() => pullRecords())}>Pull records for review</button><button onClick={() => void run(prepareOffline)}>Prepare offline</button>{waiting && <button onClick={() => { waiting.postMessage({ type: 'ACTIVATE_DRIVER_UPDATE' }); setOfflineStatus('Update activation requested. Reopen when your local saves have finished.'); }}>Apply available shell update</button>}</nav>
    {offlineStatus && <p role="status">{offlineStatus}</p>}
    {records.loads.length > 0 && <label>Saved loads<select disabled={locked} value={selected} onChange={event => void run(() => choose(event.target.value))}><option value="">Choose a load</option>{records.loads.map(load => <option key={load.id} value={load.id}>{load.payload.load_ref || load.id}</option>)}</select></label>}
    {selected && <section><h2>{draft.load_ref || 'New load'}</h2><div className="quick">{[['pickup_arrival', 'Pickup arrived'], ['pickup_departure', 'Pickup departed'], ['delivery_arrival', 'Delivery arrived'], ['delivery_departure', 'Delivery departed']].map(([key, label]) => <button key={key} disabled={locked} onClick={() => { edit(key, new Date().toISOString()); void run(flush); }}>{label}</button>)}</div>
      <form onSubmit={event => { event.preventDefault(); void run(flush); }}><fieldset disabled={locked}>{Object.entries(FIELDS).map(([key, label]) => <label key={key}>{label}{/_(appointment|arrival|departure)$/.test(key) ? <><input type="datetime-local" value={localTime(draft[key])} onChange={event => edit(key, event.target.value ? new Date(event.target.value).toISOString() : '')}/>{draft[key] && <small>{draft[key]}</small>}</> : key === 'load_ref' ? <input value={draft[key]} maxLength={16000} onChange={event => edit(key, event.target.value)}/> : <textarea rows={key === 'dispatch_text' ? 5 : 3} maxLength={16000} value={draft[key]} onChange={event => edit(key, event.target.value)}/>}</label>)}<button type="submit">Save locally now</button></fieldset></form>
      <h2>Evidence</h2><p>Photos, PDF and voice: up to 10 MiB each, 20 files and 50 MiB per load.</p><input aria-label="Add photos or PDF evidence" disabled={locked} type="file" multiple accept="image/jpeg,image/png,application/pdf" onChange={event => { const files = Array.from(event.target.files || []); event.target.value = ''; void run(() => attach(files)); }}/>
      <div className="quick"><button disabled={locked} onClick={() => void run(record)}>Record voice note</button><button disabled={!recording} onClick={stopCapture}>Stop recording</button></div>
      {recording && <p role="status">Recording microphone… Stop to save this voice note locally.</p>}
      <div className="evidence">{previews.map(item => <article key={item.id}>{item.blob.type.startsWith('image/') ? <img src={item.url} alt="Saved work evidence"/> : item.blob.type.startsWith('audio/') ? <audio controls src={item.url}/> : <p>PDF / document evidence</p>}<p>{item.blob.type} · {item.blob.size} bytes · {item.state}</p><a href={item.url} download={`work-evidence-${item.id}`}>Download original evidence</a></article>)}</div>
    </section>}
    {selected && remote && <section className="review" aria-label="Local and server review"><h2>Review local and server records</h2>
      <p>Pull records before choosing a resolution. Cached snapshots can be read offline; resolutions require a fresh server check. Original local records, evidence and operations remain in the review journal.</p>
      <div className="review-columns"><article><h3>Local original</h3><p>Revision {reviewed.revision} · {records.attachments.filter(item => item.load_id === selected).length} cached evidence files</p><pre aria-label="Local raw fields">{JSON.stringify(reviewed.payload, null, 2)}</pre></article>
        <article><h3>Server snapshot</h3><p>Revision {remote.revision} · {remote.attachments?.length || 0} server evidence files</p><pre aria-label="Server raw fields">{JSON.stringify(remote.payload, null, 2)}</pre></article></div>
      <p>Keep local queues your local fields against the reviewed server revision. Use server adopts the reviewed fields locally without writing the server. Save as new copy keeps your local fields under a separate load ID. Each choice retains the originals in the journal.</p>
      <div className="quick"><button disabled={locked || !connected || !remote.reviewToken} onClick={() => void run(() => resolve('keep-local'))}>Keep local fields</button><button disabled={locked || !connected || !remote.reviewToken} onClick={() => void run(() => resolve('use-server'))}>Use server fields</button><button disabled={locked || !connected || !remote.reviewToken} onClick={() => void run(() => resolve('new-copy'))}>Save local as new copy</button></div>
      {!connected && <p role="status">Offline review only. Reconnect and pull a fresh server snapshot before resolving.</p>}
      {remote.attachments?.length > 0 && <div><h3>Server evidence</h3><p>Downloads are verified before being saved in this browser. Original local evidence is retained.</p>{remote.attachments.map(item => <p key={item.attachment_id}>{item.media_type} · {item.size} bytes <button disabled={locked || !connected} onClick={() => void run(() => downloadRemote(item.attachment_id))}>Download verified evidence {item.attachment_id}</button></p>)}</div>}
      {reviewed.journal?.length > 0 && <details><summary>Retained review journal ({reviewed.journal.length})</summary>{reviewed.journal.map(item => <article key={item.id}><h3>{item.decision} · {item.status || 'status unavailable'} · {item.at}</h3><pre>{JSON.stringify({ local: item.local, remote: item.remote, outbox: item.outbox }, null, 2)}</pre></article>)}</details>}
    </section>}
    {records.outbox.some(op => op.state === 'conflict') && <section className="error"><h2>Conflicts need review</h2><p>Local originals and evidence are retained. Select a load and pull records to compare before choosing a resolution.</p>{records.outbox.filter(op => op.state === 'conflict').map(op => <p key={op.id}>{op.load_id} · {op.kind} · {op.id}</p>)}</section>}
    {ready && <details className="truck-profile-entry"><summary>Truck profile and navigation readiness</summary><TruckProfile key={user.uid} instance={client.current} owner={status.owner}/></details>}
  </main>;
}
