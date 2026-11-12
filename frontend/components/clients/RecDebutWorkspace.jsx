import { useCallback, useEffect, useState } from 'react';
import './RecDebutWorkspace.css';
import RecDebutIntake from './RecDebutIntake.jsx';

/** @typedef {{id:string, kind:string, revision:number, updated_at?:string, payload:Record<string, any>}} WorkRecord */
/** @typedef {{records:WorkRecord[], suppressions:{destination:string, reason:string, actor:string}[], events:{sequence:number, actor:string, action:string, created_at:string}[]}} Snapshot */
/** @typedef {{draft_id:string, revision:number, digest:string, reviewable:boolean, audience:{person_id:string,name:string,destination:string,message:string,reasons:string[]}[]}} Preview */
const SECTIONS = [
  ['inbox', 'Registration inbox'], ['today', 'Today & follow-ups'], ['families', 'Families & athletes'],
  ['messages', 'Messages & review'], ['services', 'Registrations & services'],
  ['delivery', 'Media & delivery'], ['results', 'Results & work log'],
];
/** @type {Record<string,string[]>} */
const TYPES = { inbox: [], today: ['followup'], families: ['family', 'person'], messages: ['draft'], services: ['service'], delivery: ['delivery'], results: ['worklog'] };
/** @type {Record<string,string>} */
const LABELS = { family: 'Family / athlete', person: 'Contact', followup: 'Follow-up', draft: 'Message draft', service: 'Registration / service', delivery: 'Delivery task', worklog: 'Work entry' };
/** @type {Record<string, [string,string,(string|string[])?][]>} */
const FIELDS = {
  family: [['name', 'Family name'], ['athlete_name', 'Athlete name'], ['grad_year', 'Graduating class'], ['sport', 'Sport'], ['school', 'School'], ['source', 'Source / provenance'], ['notes', 'Notes', 'textarea']],
  person: [['name', 'Contact name'], ['family_id', 'Family', 'family'], ['role', 'Contact role', ['unknown', 'parent', 'guardian', 'athlete', 'coach', 'organization']], ['relationship', 'Relationship evidence checked', ['unknown', 'verified']], ['phone', 'Phone'], ['email', 'Email'], ['source', 'Contact source'], ['sms_permission', 'SMS permission', ['unknown', 'granted', 'denied']], ['email_permission', 'Email permission', ['unknown', 'granted', 'denied']], ['permission_evidence', 'Permission evidence / date'], ['notes', 'Notes', 'textarea']],
  followup: [['title', 'Next action'], ['family_id', 'Family', 'family'], ['owner', 'Assigned staff'], ['due', 'Due date', 'date'], ['kind', 'Observation / action', ['registration', 'call requested', 'verified reply', 'consultation', 'staff task', 'unverified engagement']], ['status', 'Status', ['open', 'in progress', 'done']], ['notes', 'Call / follow-up notes', 'textarea']],
  draft: [['title', 'Draft title'], ['channel', 'Channel', ['sms', 'email']], ['body', 'Exact message — use {first_name} if needed', 'textarea'], ['notes', 'Claims, audience and cadence to review', 'textarea']],
  service: [['title', 'Registration / service name'], ['family_id', 'Family', 'family'], ['stage', 'Stage', ['registration pending', 'registered (staff confirmed)', 'consultation requested', 'consultation complete', 'offer under review', 'service agreed', 'fulfillment', 'complete']], ['package', 'Agreed package / offer (confirm with Dennis)'], ['price_cents', 'Agreed price in cents', 'number'], ['payment', 'Payment record', ['unknown', 'not applicable', 'pending', 'paid (staff confirmed)', 'refunded (staff confirmed)']], ['deliverables', 'Agreed deliverables / evidence', 'textarea'], ['notes', 'Notes', 'textarea']],
  delivery: [['title', 'Deliverable / task'], ['family_id', 'Family', 'family'], ['owner', 'Assigned staff'], ['due', 'Due date', 'date'], ['status', 'Status', ['awaiting footage', 'drafting', 'editing', 'awaiting review', 'approved', 'delivered (staff confirmed)']], ['reference', 'File / delivery reference'], ['notes', 'Revision and delivery notes', 'textarea']],
  worklog: [['title', 'Work performed'], ['family_id', 'Family (optional)', 'family'], ['owner', 'Staff name'], ['minutes', 'Minutes worked', 'number'], ['expense_cents', 'Expense in cents', 'number'], ['notes', 'Outcome / evidence', 'textarea']],
};
/** @param {string} kind */
const empty = kind => Object.fromEntries(FIELDS[kind].map(([key, , type]) => [key, Array.isArray(type) ? type[0] : type === 'number' ? 0 : '']));
/** @param {WorkRecord} r */
const titleOf = r => r.payload.name || r.payload.title;

/** @param {{backendUrl?:string, BACKEND_URL?:string}} props */
export default function RecDebutWorkspace({ backendUrl, BACKEND_URL }) {
  const base = (backendUrl || BACKEND_URL || (['localhost', '127.0.0.1'].includes(location.hostname) ? 'http://127.0.0.1:8080' : 'https://api.brettstehouwer.live')).replace(/\/$/, '');
  const [section, setSection] = useState('today');
  const [data, setData] = useState(/** @type {Snapshot|null} */ (null));
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [actor, setActor] = useState('');
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [editor, setEditor] = useState(/** @type {WorkRecord|null} */ (null));
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState(/** @type {Preview|null} */ (null));
  const [legacy, setLegacy] = useState(/** @type {Record<string, any>|null} */ (null));
  const [legacyPage, setLegacyPage] = useState(0);
  const [traffic, setTraffic] = useState(/** @type {Record<string, any>|null} */ (null));
  const [suppression, setSuppression] = useState({ destination: '', reason: '' });
  const records = data?.records || [];
  const families = records.filter(r => r.kind === 'family');
  const people = records.filter(r => r.kind === 'person');
  /** @param {string} id */
  const familyName = id => families.find(r => r.id === id)?.payload.name || 'Unlinked';

  /** @param {string} path @param {RequestInit} options */
  const request = useCallback(/** @param {string} path @param {RequestInit} options */ async (path, options = {}) => {
    const response = await fetch(`${base}/api/v1/recdebut${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers }, signal: AbortSignal.timeout(20000) });
    let result;
    try { result = await response.json(); } catch { throw new Error('The server returned an unreadable response. Your changes were not confirmed.'); }
    if (!response.ok) {
      const detail = result.detail;
      throw new Error([401, 403].includes(response.status) ? 'An administrator sign-in is required for this private workspace.' : typeof detail === 'string' ? detail : detail?.message || `Request failed (HTTP ${response.status}). Your changes were not confirmed.`);
    }
    return result;
  }, [base]);
  async function load() {
    setError('');
    try { setData(await request('/workflow')); } catch (err) { setError(err instanceof Error ? err.message : 'Request failed. Your changes were not confirmed.'); }
  }
  useEffect(() => { load(); }, [base]);
  useEffect(() => {
    /** @param {BeforeUnloadEvent} event */
    const handler = event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);
  const canLeave = () => !dirty || window.confirm('Discard the unsaved changes in this form?');
  /** @param {string} next */
  function navigate(next) { if (canLeave()) { setSection(next); setEditor(null); setDirty(false); setPreview(null); setError(''); setNotice(''); } }
  /** @param {WorkRecord} record */
  function edit(record) { if (canLeave()) { setEditor({ ...record, payload: { ...record.payload } }); setDirty(false); setPreview(null); setError(''); setNotice(''); } }
  /** @param {string} kind */
  function create(kind) { edit({ id: crypto.randomUUID(), kind, revision: 0, payload: { ...empty(kind), ...(FIELDS[kind].some(([k]) => k === 'family_id') ? { family_id: filter } : {}), ...(kind === 'draft' ? { person_ids: [] } : {}) } }); }
  /** @param {string} key @param {any} value */
  function change(key, value) { setEditor(r => r ? ({ ...r, payload: { ...r.payload, [key]: value } }) : null); setDirty(true); setPreview(null); }
  /** @param {import("react").FormEvent} event */
  async function save(event) {
    event.preventDefault(); if (!editor) return; setBusy(true); setError(''); setNotice('');
    try {
      const result = await request(`/workflow/records/${editor.kind}/${editor.id}`, { method: 'PUT', body: JSON.stringify({ actor, revision: editor.revision, payload: editor.payload }) });
      setData(d => d ? ({ ...d, records: [result.record, ...(d?.records || []).filter(r => r.id !== result.record.id)] }) : d);
      setEditor(result.record); setDirty(false); setNotice('Saved to the shared workspace. Available after sign-in in another session.');
      // A refresh updates the event log; a refresh failure does not undo a confirmed save.
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Request failed. Your changes were not confirmed.'); } finally { setBusy(false); }
  }
  /** @param {WorkRecord} record */
  async function showPreview(record) {
    setError(''); setBusy(true);
    try { setPreview((await request(`/workflow/drafts/${record.id}/preview`)).preview); }
    catch (err) { setError(err instanceof Error ? err.message : 'Request failed. Your changes were not confirmed.'); } finally { setBusy(false); }
  }
  async function review() {
    if (!preview) return;
    setBusy(true); setError('');
    try {
      await request(`/workflow/drafts/${preview.draft_id}/review`, { method: 'POST', body: JSON.stringify({ actor, revision: preview.revision, expected_digest: preview.digest }) });
      setNotice('Review recorded for this exact draft and audience. Sending remains disabled.'); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Request failed. Your changes were not confirmed.'); setPreview(null); } finally { setBusy(false); }
  }
  /** @param {import("react").FormEvent} event */
  async function addSuppression(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await request('/workflow/suppressions', { method: 'POST', body: JSON.stringify({ ...suppression, actor }) }); setSuppression({ destination: '', reason: '' }); setPreview(null); setNotice('Destination suppressed. Sending remains disabled.'); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Request failed. Your changes were not confirmed.'); } finally { setBusy(false); }
  }
  async function loadLegacy() {
    setBusy(true); setError('');
    const sources = [['athletes', '/athletes'], ['campaigns', '/campaigns'], ['replies', '/sms/replies']];
    const results = await Promise.allSettled(sources.map(async ([key, path]) => [key, await request(path)]));
    setLegacy(Object.fromEntries(results.map((result, index) => result.status === 'fulfilled' ? result.value : [sources[index][0], { error: result.reason.message }])));
    setBusy(false);
  }
  async function loadTraffic() {
    setBusy(true); setError('');
    try { setTraffic(await request('/workflow/traffic')); }
    catch (err) { setError(err instanceof Error ? err.message : 'Campaign activity could not be loaded.'); }
    finally { setBusy(false); }
  }
  const visible = records.filter(r => TYPES[section].includes(r.kind) && (!filter || r.id === filter || r.payload.family_id === filter || r.kind === 'draft') && (!search || JSON.stringify(r.payload).toLowerCase().includes(search.toLowerCase()))).sort((a, b) => {
    if (section !== 'today') return (b.updated_at || '').localeCompare(a.updated_at || '');
    const done = Number(a.payload.status === 'done') - Number(b.payload.status === 'done');
    return done || (a.payload.due || '9999').localeCompare(b.payload.due || '9999');
  });
  const due = records.filter(r => r.kind === 'followup' && r.payload.status !== 'done');
  const legacyRows = legacy?.athletes?.athletes || [];
  return <section className="rd-workspace" aria-label="RecDebut staff workspace">
    <header className="rd-header"><div><small>PRIVATE STAFF WORKSPACE</small><h1>Recreational Debut</h1><p>Families → follow-ups → message review → services → delivery</p></div><div className="rd-actions"><a href="https://recdebut.com/" target="_blank" rel="noopener noreferrer">Family website ↗</a><a href="https://recdebut.com/all-registration/" target="_blank" rel="noopener noreferrer">Registration ↗</a></div></header>
    <div className="rd-hold" role="status"><strong>Sending disabled · review in progress</strong><span>Drafts and reviews never send messages. Automated dispatch, provider polling and reply forwarding are on hold.</span></div>
    <nav className="rd-nav" aria-label="RecDebut sections">{SECTIONS.map(([key, label]) => <button key={key} aria-current={key === section ? 'page' : undefined} onClick={() => navigate(key)}>{label}</button>)}</nav>
    <div className="rd-toolbar"><label>Recorded by<input value={actor} maxLength={100} onChange={e => setActor(e.target.value)} placeholder="Your staff name" /></label><label>Family<select value={filter} onChange={e => setFilter(e.target.value)}><option value="">All families</option>{families.map(r => <option key={r.id} value={r.id}>{titleOf(r)}</option>)}</select></label><label>Search records<input value={search} onChange={e => setSearch(e.target.value)} placeholder="Name, class, owner or notes" /></label><button disabled={busy || dirty} onClick={load}>Refresh saved records</button></div>
    {error && <div className="rd-error" role="alert">{error}</div>}{notice && <div className="rd-notice" role="status">{notice}</div>}
    {!data ? <p>Workspace unavailable until an authorized connection succeeds. <button onClick={load}>Retry</button></p> : <>
      <div className="rd-summary"><span>{families.length} families</span><span>{people.length} separate contacts</span><span>{due.length} open follow-ups</span><span>{data.suppressions.length} suppressed destinations</span></div>
      <h2>{SECTIONS.find(([key]) => key === section)?.[1]}</h2>
      {section === 'today' && <p>Requested calls and verified replies take priority. Assign an owner and due date. Class 2027 can be found with search; a link visit alone is not confirmed interest.</p>}
      {section === 'families' && <p>Add a family first, then link separate parent, guardian and athlete contacts. Unknown roles and permissions stay unknown. Existing rosters are preserved under Results; no automatic contact import occurs.</p>}
      {section === 'messages' && <p>Prepare exact copy and choose contacts for a review preview. Contact role, family relationship, source and channel permission must be recorded. Staff attribution does not establish Dennis’s approval; review the copy and claims together before any later sending authorization.</p>}
      {section === 'services' && <div className="rd-card"><strong>Confirm offers with Dennis</strong><p>Gold $150, Silver $35 and Bronze $25 are historical proposals. Current price, coach-site access and deliverables are unconfirmed. Enter an agreed offer per family. Registration and payment states below are staff records, not automatic website or payment confirmations.</p><p>Families can explore <a href="https://recdebut.com/" target="_blank" rel="noopener noreferrer">Dennis’s website</a> and its <a href="https://recdebut.com/all-registration/" target="_blank" rel="noopener noreferrer">registration page</a>. Opening a link does not record a registration.</p></div>}
      {section === 'delivery' && <p>Track footage, editing, endorsements, review and delivery. References are notes only; files are not uploaded or sent by this form.</p>}
      {section === 'results' && <p>Record staff work and evidence. Historical queued/sent and click counts are retained as reported records, not proof of delivery, interest or registration.</p>}
      {section === 'results' && <div className="rd-card"><h3>Campaign link activity</h3><button disabled={busy} onClick={loadTraffic}>Refresh campaign activity</button>{traffic ? <><p><strong>{traffic.total_requests} recorded link requests</strong> · {traffic.tracking_configured ? 'Link tracking configured for new reviewed email plans' : 'Link tracking is off for new email plans'}</p><p>{traffic.notice}</p>{traffic.campaigns.length === 0 ? <p>No campaign link requests recorded.</p> : <div className="rd-table"><table><thead><tr><th>Campaign</th><th>Link</th><th>Requests</th><th>Distinct links requested</th><th>Latest request</th></tr></thead><tbody>{traffic.campaigns.map((/** @type {any} */ row) => <tr key={`${row.plan_id}-${row.target}`}><td>{row.title}<br /><small>{row.plan_id}</small></td><td>{row.target}</td><td>{row.requests}</td><td>{row.distinct_links}</td><td>{new Date(row.last_requested_at).toLocaleString()}</td></tr>)}</tbody></table><small>Showing up to {traffic.group_limit} recent campaign/link groups.</small></div>}</> : <p>Load activity from accepted campaign emails. Website and video link requests are counted separately.</p>}</div>}
      {!editor && ['inbox', 'families'].includes(section) && <RecDebutIntake key={section} mode={section === 'inbox' ? 'inbox' : 'timeline'} request={request} families={families} records={records} actor={actor} busy={busy} setDirty={setDirty} />} 
      <div className="rd-actions">{TYPES[section].map(kind => <button key={kind} disabled={busy} onClick={() => create(kind)}>Add {LABELS[kind].toLowerCase()}</button>)}</div>
      {editor && <form className="rd-editor" onSubmit={save}><h3>{editor.revision ? 'Edit' : 'New'} {LABELS[editor.kind].toLowerCase()}</h3><div className="rd-fields">{FIELDS[editor.kind].map(([key, label, type]) => <label key={key}>{label}{Array.isArray(type) ? <select value={editor.payload[key] ?? type[0]} onChange={e => change(key, e.target.value)}>{type.map(v => <option key={v}>{v}</option>)}</select> : type === 'family' ? <select value={editor.payload[key] || ''} onChange={e => change(key, e.target.value)}><option value="">Unlinked / unknown</option>{families.map(r => <option key={r.id} value={r.id}>{titleOf(r)}</option>)}</select> : type === 'textarea' ? <textarea rows={key === 'body' ? 7 : 3} maxLength={12000} value={editor.payload[key] || ''} onChange={e => change(key, e.target.value)} /> : <input required={['name', 'title'].includes(key)} type={type === 'number' ? 'number' : type === 'date' ? 'date' : 'text'} min={type === 'number' ? 0 : undefined} step={type === 'number' ? 1 : undefined} maxLength={1000} value={editor.payload[key] ?? ''} onChange={e => change(key, type === 'number' ? (e.target.value === '' ? 0 : Number(e.target.value)) : e.target.value)} />}</label>)}</div>
        {editor.kind === 'draft' && <fieldset><legend>Exact review audience (up to 100 contacts)</legend>{people.length === 0 ? <p>Add contacts under Families first.</p> : people.map(r => <label className="rd-checkbox" key={r.id}><input type="checkbox" checked={(editor.payload.person_ids || []).includes(r.id)} onChange={e => change('person_ids', e.target.checked ? [...(editor.payload.person_ids || []), r.id] : editor.payload.person_ids.filter((/** @type {string} */ id) => id !== r.id))} />{titleOf(r)} · {r.payload.role || 'unknown'} · {familyName(r.payload.family_id)}</label>)}</fieldset>}
        <div className="rd-actions"><button type="submit" disabled={busy || !actor.trim()}>Save {LABELS[editor.kind].toLowerCase()}</button><button type="button" disabled={busy} onClick={() => { if (canLeave()) { setEditor(null); setDirty(false); } }}>Close form</button>{dirty && <span>Unsaved changes</span>}</div>{!actor.trim() && <p>Enter your staff name in Recorded by before saving.</p>}</form>}
      <div className="rd-records">{visible.map(record => <article className="rd-card" key={record.id}><h3>{titleOf(record)}</h3>{record.kind === 'family' ? <p>{record.payload.athlete_name || 'Athlete unknown'} · Class {record.payload.grad_year || 'unknown'}</p> : record.payload.family_id ? <p>{familyName(record.payload.family_id)}</p> : null}<p>{record.payload.status || record.payload.stage || record.payload.role || LABELS[record.kind]}{record.payload.owner ? ` · ${record.payload.owner}` : ''}{record.payload.due ? ` · due ${record.payload.due}` : ''}</p>{record.kind === 'person' && <p>SMS: {record.payload.sms_permission || 'unknown'} · Email: {record.payload.email_permission || 'unknown'}</p>}{record.payload.notes && <p className="rd-notes">{record.payload.notes}</p>}{record.kind === 'draft' && <p className="rd-notes">{record.payload.body}</p>}<small>Saved {new Date(record.updated_at || '').toLocaleString()} · revision {record.revision}</small><div className="rd-actions"><button disabled={busy} onClick={() => edit(record)}>Edit</button>{record.kind === 'draft' && <button disabled={busy || dirty} onClick={() => showPreview(record)}>Preview saved draft & audience</button>}</div></article>)}</div>{visible.length === 0 && <p>No matching saved records. Add a record to begin.</p>}
      {preview && <aside className="rd-editor" aria-label="Exact draft preview"><h3>Review preview · sending disabled</h3><p>{preview.reviewable ? 'Audience metadata is ready for human review. This is not delivery clearance.' : 'Resolve the following warnings before recording a review.'}</p>{preview.audience.length === 0 && <p>No contacts selected.</p>}{preview.audience.map(p => <div className="rd-card" key={p.person_id}><strong>{p.name} · {p.destination || 'No destination'}</strong><p className="rd-notes">{p.message}</p>{p.reasons.map(reason => <p key={reason} className="rd-warning">{reason}</p>)}</div>)}<small>Exact draft/audience fingerprint: {preview.digest}</small><div className="rd-actions"><button disabled={busy || !actor.trim() || !preview.reviewable} onClick={review}>Record review only</button><button disabled title="Sending is disabled until the workflow is reviewed">Send disabled</button></div></aside>}
      {section === 'families' && <div className="rd-editor"><h3>Do not contact / opt-out register</h3><p>A suppression applies to the normalized destination, including shared numbers. It cannot be removed from this screen.</p><form onSubmit={addSuppression}><div className="rd-fields"><label>Phone or email<input required value={suppression.destination} onChange={e => setSuppression(s => ({ ...s, destination: e.target.value }))} /></label><label>Reason / evidence<input required maxLength={500} value={suppression.reason} onChange={e => setSuppression(s => ({ ...s, reason: e.target.value }))} /></label></div><button disabled={busy || !actor.trim()}>Save suppression</button></form>{data.suppressions.map(s => <p key={s.destination}>{s.destination} · {s.reason} · recorded by {s.actor}</p>)}</div>}
      {section === 'results' && <><div className="rd-card"><h3>Existing records · read only</h3><p>Preserved athlete roster, campaign history and received replies. Contact roles and permissions are not inferred from these records.</p><button disabled={busy} onClick={loadLegacy}>Load existing records</button>{legacy && <><p>{legacyRows.length} roster records loaded. Campaign records: {(legacy.campaigns?.campaigns || []).length}. Reply records: {(legacy.replies?.replies || []).length}.</p>{Object.entries(legacy).filter(([, value]) => value.error).map(([key, value]) => <p role="alert" key={key}>{key}: {value.error}</p>)}<div className="rd-table"><table><thead><tr><th>Name</th><th>Class</th><th>Recorded status (unverified)</th></tr></thead><tbody>{legacyRows.slice(legacyPage * 25, legacyPage * 25 + 25).map((/** @type {any} */ r) => <tr key={r.id}><td>{r.name}</td><td>{r.grad_year || 'unknown'}</td><td>{r.status || 'unknown'}</td></tr>)}</tbody></table></div><div className="rd-actions"><button disabled={legacyPage === 0} onClick={() => setLegacyPage(p => p - 1)}>Previous</button><span>Page {legacyPage + 1}</span><button disabled={(legacyPage + 1) * 25 >= legacyRows.length} onClick={() => setLegacyPage(p => p + 1)}>Next</button></div>{['campaigns', 'replies'].map(key => <details key={key}><summary>View retained {key}</summary><pre>{JSON.stringify(legacy[key]?.[key] || [], null, 2)}</pre></details>)}</>}</div><h3>Recent saved-work history</h3><p>Recorded staff names are attribution entered by signed-in staff. Reviews are tied to an exact draft and audience, and never authorize sending.</p>{data.events.map(e => <p key={e.sequence}>#{e.sequence} · {e.actor} · {e.action.replaceAll('_', ' ')} · {new Date(e.created_at).toLocaleString()}</p>)}</>}
    </>}
  </section>;
}
