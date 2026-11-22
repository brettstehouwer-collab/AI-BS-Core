import { useEffect, useState } from 'react';

const panel = { padding: '18px', background: '#111827', border: '1px solid #334155', borderRadius: '10px', margin: '16px 0' };

export default function OutreachReceipts({ owner, brand, request }) {
  const scope = JSON.stringify([owner, brand]);
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [queueSearch, setQueueSearch] = useState('');
  const [queueStatus, setQueueStatus] = useState('all');
  const data = snapshot?.scope === scope ? snapshot.data : null;
  useEffect(() => {
    if (!owner) return;
    const controller = new AbortController();
    let timer;
    const load = async () => {
      try {
        const value = await request(`/outreach-records/${brand}`, { expectedUid: owner, signal: controller.signal });
        if (controller.signal.aborted) return;
        setSnapshot({ scope, data: value }); setError('');
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure.message || 'Receipt refresh failed.');
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(load, 30000);
      }
    };
    load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [owner, brand, request, refresh]);
  const records = Array.isArray(data?.messages) ? data.messages : [];
  const visible = records.filter(r => (status === 'all' || (status === 'held' ? r.status !== 'provider_accepted' : r.status === status)) &&
    `${r.business} ${r.to} ${r.subject}`.toLowerCase().includes(search.toLowerCase()));
  const queue = Array.isArray(data?.queue) ? data.queue : [];
  const queueVisible = queue.filter(r => (queueStatus === 'all' || r.status === queueStatus) && `${r.business} ${r.email} ${r.category} ${r.reason}`.toLowerCase().includes(queueSearch.toLowerCase()));
  function download() {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${brand}-outreach-receipts.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <section style={panel} aria-label="Outgoing outreach and receipts">
    <h3>Outgoing outreach &amp; receipts</h3>
    <p>Actual IONOS attempts from authorized batches. Refreshes every 30 seconds while this panel is open.</p>
    <button type="button" disabled={!owner} onClick={() => setRefresh(v => v + 1)}>Refresh receipts</button>{' '}
    <button type="button" disabled={!data?.available} onClick={download}>Download receipts</button>
    {error && <p role="alert" style={{ color: '#fca5a5' }}>{error} Previously loaded records may be stale.</p>}
    {!data ? <p>Loading receipts…</p> : !data.available ? <p>{data.reason}</p> : <>
      <p><strong>Accepted by IONOS: {data.summary.provider_accepted}</strong> · Confirmed delivery: {data.summary.delivery_confirmed} · Held/unresolved: {data.summary.held}</p>
      <p>SMTP acceptance is not proof of recipient delivery. No opens, clicks, replies or delivery events are inferred.</p>
      <p>Current outreach replies route to <strong>{data.incoming.reply_to}</strong>. Each receipt retains its original Reply-To. Incoming replies are not connected; this view currently shows outgoing messages and receipts only.</p>
      <p>Latest attempt: {data.updated_at ? new Date(data.updated_at).toLocaleString() : 'No attempts recorded'}</p>
      <label>Find recipient or subject <input value={search} onChange={e => setSearch(e.target.value)} style={{ color: '#111827', padding: '6px', maxWidth: '100%' }} /></label>{' '}
      <label>Status <select value={status} onChange={e => setStatus(e.target.value)} style={{ color: '#111827', padding: '6px' }}><option value="all">All</option><option value="provider_accepted">Accepted by IONOS</option><option value="held">Held / unresolved</option></select></label>
      <p>{visible.length} matching records. No resend action is available here.</p>
      <div style={{ maxHeight: '600px', overflowY: 'auto' }}>{visible.map(record => <details key={record.to} style={{ borderTop: '1px solid #475569', padding: '12px 0', overflowWrap: 'anywhere' }}>
        <summary><strong>{record.business || record.to}</strong> — {record.to} · {record.status === 'provider_accepted' ? 'Accepted by IONOS' : 'Held / unresolved'}</summary>
        <p>{record.status_detail}</p><p>From: {record.from}<br />Reply-To: {record.reply_to}<br />Batch: {record.batch}</p>
        <h4>{record.subject}</h4><pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{record.body}</pre>
        <p>Message ID: {record.message_id || 'Not recorded'}</p>
        <ul>{record.events.map((event, i) => <li key={i}>{new Date(event.utc).toLocaleString()} — {event.status}{event.error_class ? ` (${event.error_class})` : ''}</li>)}</ul>
      </details>)}</div>
      <details style={{ marginTop: '20px' }}><summary>Collected contacts, research holds &amp; exclusions ({queue.length})</summary>
        <p>Every collected contact is not necessarily eligible for outreach. This list records missing verification, unsuitable purpose, submission restrictions, missing materials and prior-contact holds.</p>
        {!data.queue_available ? <p>Qualification list is unavailable.</p> : <>
          <label>Find research contact <input value={queueSearch} onChange={e => setQueueSearch(e.target.value)} style={{ color: '#111827', padding: '6px', maxWidth: '100%' }} /></label>{' '}
          <label>Research status <select value={queueStatus} onChange={e => setQueueStatus(e.target.value)} style={{ color: '#111827', padding: '6px' }}><option value="all">All</option>{Object.entries(data.queue_summary || {}).map(([key, count]) => <option key={key} value={key}>{key.replaceAll('_', ' ')} ({count})</option>)}</select></label>
          <p>{queueVisible.length} matching research records. No sends or selections are enabled in this list.</p>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>{queueVisible.map((row, i) => <article key={`${row.email}-${row.business}-${i}`} style={{ borderTop: '1px solid #475569', padding: '10px 0', overflowWrap: 'anywhere' }}>
            <strong>{row.business}</strong> — {row.email || 'No verified shared email'}<br />{row.status.replaceAll('_', ' ')}<p>{row.reason}</p><small>{row.origin} · {row.category}</small>
          </article>)}</div>
        </>}
      </details>
    </>}
  </section>;
}
