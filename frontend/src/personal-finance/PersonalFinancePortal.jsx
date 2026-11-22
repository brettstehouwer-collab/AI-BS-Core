import React, { useEffect, useRef, useState } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase.js';
import PersonalSignIn from './PersonalSignIn.jsx';
import { ADMIN_EMAILS, ADMIN_UIDS } from '../components/accessControl.js';
import { createPersonalClient } from './personalClient.js';
import FinancialFilings from './FinancialFilings.jsx';
import OfflineShell from './OfflineShell.jsx';
import MultipartExport from './MultipartExport.jsx';

const approved = user => Boolean(user?.emailVerified && (ADMIN_EMAILS.includes((user.email || '').toLowerCase().trim()) || ADMIN_UIDS.includes(user.uid)));
const blank = () => ({ payment_date: '', week_start: '', amount: '', source: '', payer: '', reference: '', notes: '', load_references: [], evidence_references: [] });
const labels = { payment_date: 'Payment date', week_start: 'Work week begins', amount: 'Amount received (USD)', source: 'Payment source', payer: 'Payer', reference: 'Transfer reference', notes: 'Original notes' };

function PersonalSession({ user }) {
  const [client, setClient] = useState(null), [locked, setLocked] = useState(false), [error, setError] = useState('');
  const [connection,setConnection]=useState('opening');
  const [draft, setDraft] = useState(blank), [pending, setPending] = useState(false), [saved, setSaved] = useState('Opening personal records…');
  const [payments, setPayments] = useState([]), [total, setTotal] = useState('0.00'), [selected, setSelected] = useState('');
  const [documents, setDocuments] = useState([]), [uploads, setUploads] = useState([]), [busy, setBusy] = useState(false), [year, setYear] = useState(String(new Date().getFullYear()));
  const queue = useRef(Promise.resolve()), instance = useRef(null), alive = useRef(true), urls = useRef(new Set());
  const refresh = async c => {
    const data = c.mode==='offline'?{payments:[],recorded_total:null}:await c.request('/payments');
    const files = await c.uploads();
    if (alive.current) { setPayments(data.payments); setTotal(data.recorded_total); setUploads(files.filter(row=>row.target!=='filing')); }
  };
  useEffect(() => {
    alive.current = true;
    createPersonalClient({ auth, base: window.location.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(window.location.hostname) ? 'http://127.0.0.1:8080' : 'https://api.brettstehouwer.live', onUnauthorized: () => { if (alive.current) setLocked(true); } }).then(async c => {
      if (!alive.current) { c.close(); return; } instance.current = c;
      const row = await c.draft();
      if (!alive.current) return;
      setDraft(row.fields || blank()); setPending(Boolean(row.pending));
      await refresh(c); if (alive.current) { setClient(c); setConnection(c.mode); setSaved(row.pending ? 'Saved retry waiting; review before retrying' : 'Personal draft ready'); }
    }).catch(e => { if (alive.current) setError(e.message); });
    return () => { alive.current = false; instance.current?.close(); urls.current.forEach(url => URL.revokeObjectURL(url)); };
  }, [user]);
  useEffect(() => {
    if (!client || !selected) { setDocuments([]); return; }
    let current = true; setDocuments([]);
    client.request(`/payments/${selected}/documents`).then(data => { if (current) setDocuments(data.documents); }).catch(e => { if (current) setError(e.message); });
    return () => { current = false; };
  }, [client, selected]);
  const edit = (key, value) => {
    const next = { ...draft, [key]: value }; setDraft(next); setSaved('Saving on this device…');
    queue.current = queue.current.catch(() => {}).then(() => client.saveDraft(next)).then(() => { if (alive.current) setSaved('Draft saved on this device'); }).catch(e => { if (alive.current) { setSaved('Draft not saved'); setError(e.message); } throw e; });
    queue.current.catch(() => {});
  };
  const run = async action => {
    setBusy(true); setError('');
    try { await queue.current; await action(); }
    catch (e) { if (alive.current) { setError(e.message); const row = await instance.current?.draft().catch(() => null); if (row) setPending(Boolean(row.pending)); } }
    finally { if (alive.current) setBusy(false); }
  };
  const offer = (blob, name) => {
    if (!alive.current) return;
    const url = URL.createObjectURL(blob); urls.current.add(url);
    const link = document.createElement('a'); link.href = url; link.download = name; link.click();
    setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url); }, 60000);
  };
  if (locked) return <p role="alert">Personal financial access denied. Local originals and drafts remain saved on this device.</p>;
  return <>
    {connection==='offline'&&<p role="status">Offline local records: prior owner admission only. Server records and totals are unavailable.<button disabled={busy} onClick={()=>run(async()=>{await client.reconnect();setConnection(client.mode);await refresh(client);})}>Reconnect personal access</button></p>}
    <p role="status">{saved}</p>{error && <p role="alert">{error}</p>}
    <section><h2>Record a payment</h2><p>Manual evidence only. Transfers are not automatically classified as income or reconciled with payroll.</p>
      <fieldset disabled={!client || busy || pending}>
        {Object.entries(labels).map(([key, label]) => <label key={key}>{label}{key === 'notes' ? <textarea aria-label={label} value={draft[key]} onChange={e => edit(key, e.target.value)} /> : <input aria-label={label} type={key.endsWith('date') || key === 'week_start' ? 'date' : 'text'} inputMode={key === 'amount' ? 'decimal' : undefined} value={draft[key]} onChange={e => edit(key, e.target.value)} />}</label>)}
        <label>Load references (one per line)<textarea value={draft.load_references.join('\n')} onChange={e => edit('load_references', e.target.value ? e.target.value.split('\n') : [])} /></label>
      </fieldset>
      <button disabled={!client || busy || connection!=='online'} onClick={() => run(async () => { await client.submit(); const row = await client.draft(); if (alive.current) { setDraft(row.fields || blank()); setPending(false); setSaved('Payment recorded'); } await refresh(client); })}>{pending ? 'Retry saved payment' : 'Record saved payment'}</button>
    </section>
    <section><h2>Recorded payments</h2><p>{total===null?'Offline: server totals unavailable.':`Recorded transfers: $${total} USD.`} Expected pay is unconfirmed.</p>
      <button disabled={!client || busy} onClick={() => run(() => refresh(client))}>Refresh payments</button>
      <label>Payment for documents<select aria-label="Payment for documents" value={selected} onChange={e => setSelected(e.target.value)} disabled={busy}><option value="">Choose a payment</option>{payments.map(row => <option key={row.id} value={row.id}>{row.payment_date} · ${row.amount} · {row.payer}</option>)}</select></label>
      {payments.map(row => <article key={row.id}><strong>{row.payment_date} · ${row.amount}</strong><p>{row.payer} · {row.source}</p><p>Work week begins {row.week_start}</p><p>{row.notes}</p></article>)}
    </section>
    <section><h2>Original documents</h2><p>Choose a payment, then save its receipt, payment evidence or paperwork. Originals stay unchanged; new files create separate records.</p>
      <label>Save original on this device<input type="file" disabled={!client || !selected || busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; if (file) run(async () => { await client.retainFile(Number(selected), file); setUploads((await client.uploads()).filter(row=>row.target!=='filing')); setSaved('Original saved on this device; upload pending'); }); }} /></label>
      {uploads.map(row => <article key={row.id}><span>{row.name} · payment {row.paymentId} · saved locally</span><button disabled={busy} onClick={() => run(async () => { await client.sendFile(row.id); await refresh(client); if (String(row.paymentId) === selected) setDocuments((await client.request(`/payments/${selected}/documents`)).documents); setSaved('Original uploaded and retained by server'); })}>Upload or retry {row.name}</button></article>)}
      {documents.map(row => <article key={row.document_id}><span>{row.filename} · {row.size} bytes</span><button disabled={busy} onClick={() => run(async () => offer(await client.download(Number(selected), row), row.filename))}>Download {row.filename}</button></article>)}
    </section>
    {client&&<FinancialFilings client={client} connection={connection} blocked={busy} offer={offer}/>}
    <section><h2>Yearly accounting export</h2><p>CSV contains accounting income/expense entries. Records ZIP adds payment originals; complete filing ZIP also includes documents assigned to your chosen filing year. These selections do not determine tax treatment.</p><label>Year<input type="number" min="1" max="9999" value={year} onChange={e => setYear(e.target.value)} /></label><button disabled={!client || busy || !/^[1-9]\d{0,3}$/.test(year)} onClick={() => run(async () => offer(await client.request(`/ledger/${year}.csv`, {}, true), `personal-ledger-${year}.csv`))}>Download ledger CSV</button><button disabled={!client || busy || !/^[1-9]\d{0,3}$/.test(year)} onClick={() => run(async () => offer(await client.request(`/exports/${year}.zip`, {}, true), `personal-records-${year}.zip`))}>Download records and originals ZIP</button><button disabled={!client || busy || !/^[1-9]\d{0,3}$/.test(year)} onClick={()=>run(async()=>offer(await client.request(`/exports/${year}/complete.zip`,{},true),`personal-complete-${year}.zip`))}>Download complete filing ZIP</button></section>
    {client&&<MultipartExport client={client} connection={connection} year={year} blocked={busy} offer={offer}/>}
  </>;
}

export default function PersonalFinancePortal() {
  const [identity, setIdentity] = useState(null);
  useEffect(() => onAuthStateChanged(auth, user => setIdentity(approved(user) ? { user, key: crypto.randomUUID() } : null)), []);
  return <main className="personal-finance"><header><h1>Personal finance</h1><p>Private records · separate from FE Express work</p>{identity && <button onClick={() => signOut(auth)}>Sign out</button>}</header><OfflineShell/>{identity ? <PersonalSession key={identity.key} user={identity.user} /> : <><p>Sign in with your authorized personal account.</p><PersonalSignIn /></>}</main>;
}
