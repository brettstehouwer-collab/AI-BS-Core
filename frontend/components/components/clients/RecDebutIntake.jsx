import { useEffect, useState } from 'react';

/** @typedef {{event_id:string,family_id:string,received_at:string,revision:number,status:string,target_family_id:string,notes:string}} Receipt */
/** @typedef {{entries:{sequence:number,action:string,actor:string,created_at:string,details:Record<string,any>}[],next_before:number|null}} Timeline */
/** @param {{mode:string,request:(path:string,options?:RequestInit)=>Promise<any>,families:import("./RecDebutWorkspace.jsx").WorkRecord[],records:import("./RecDebutWorkspace.jsx").WorkRecord[],actor:string,busy:boolean,setDirty:(value:boolean)=>void}} props */
export default function RecDebutIntake({ mode, request, families, records, actor, busy, setDirty }) {
  const [rows, setRows] = useState(/** @type {Receipt[]} */ ([]));
  const [selected, setSelected] = useState(/** @type {Receipt|null} */ (null));
  const [status, setStatus] = useState('all');
  const [family, setFamily] = useState('');
  const [timeline, setTimeline] = useState(/** @type {Timeline|null} */ (null));
  const [note, setNote] = useState('');
  const [working, setWorking] = useState(false);
  const [changed, setChanged] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  /** @param {string} id */
  const name = id => families.find(r => r.id === id)?.payload.name || id;
  /** @param {boolean} value */
  const dirty = value => { setChanged(value); setDirty(value); };
  const leave = () => !changed || window.confirm('Discard the unsaved review or internal note?');
  async function refresh() {
    setError('');
    try { setRows((await request('/workflow/registrations')).registrations); }
    catch (e) { setError(e instanceof Error ? e.message : "Request failed; changes were not confirmed."); }
  }
  useEffect(() => { if (mode === 'inbox') refresh(); }, [mode, request]);
  /** @param {string} id @param {number|null} before */
  async function history(id, before = null) {
    setWorking(true); setError('');
    try {
      const result = await request(`/workflow/families/${encodeURIComponent(id)}/timeline${before ? `?before=${before}` : ''}`);
      setTimeline(old => before ? { ...result, entries: [...(old?.entries || []), ...result.entries] } : result);
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed; changes were not confirmed."); } finally { setWorking(false); }
  }
  /** @param {import("react").FormEvent} event */
  async function saveReview(event) {
    if (!selected) return;
    event.preventDefault(); setWorking(true); setError(''); setNotice('');
    try {
      const result = await request(`/workflow/registrations/${encodeURIComponent(selected.event_id)}/review`, { method: 'PUT', body: JSON.stringify({ revision: selected.revision, status: selected.status, target_family_id: selected.status === 'duplicate' ? selected.target_family_id : '', notes: selected.notes, actor }) });
      setSelected(r => r ? ({ ...r, revision: result.revision }) : r); dirty(false);
      setNotice('Review saved. No messages sent, contacts merged or payments confirmed.'); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed; changes were not confirmed."); } finally { setWorking(false); }
  }
  /** @param {import("react").FormEvent} event */
  async function saveNote(event) {
    event.preventDefault(); setWorking(true); setError(''); setNotice('');
    try {
      await request(`/workflow/families/${encodeURIComponent(family)}/timeline`, { method: 'POST', body: JSON.stringify({ actor, text: note }) });
      setNote(''); dirty(false); setNotice('Internal note saved to the shared family timeline.'); await history(family);
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed; changes were not confirmed."); } finally { setWorking(false); }
  }
  const locked = busy || working;
  return <div className="rd-intake">
    {error && <p className="rd-error" role="alert">{error}</p>}{notice && <p className="rd-notice" role="status">{notice}</p>}
    {mode === 'inbox' ? <>
      <p>Newest website receipts first. Website installation is still pending; an empty inbox does not mean the website has no registrations. Reviews never establish consent, payment or identity.</p>
      <div className="rd-actions"><label>Review status<select value={status} onChange={e => setStatus(e.target.value)}>{['all', 'pending', 'accepted', 'needs_information', 'duplicate'].map(s => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}</select></label><button disabled={locked || changed} onClick={refresh}>Refresh registration inbox</button></div>
      <div className="rd-records">{rows.filter(r => status === 'all' || r.status === status).map(r => <article className="rd-card" key={r.event_id}><h3>{name(r.family_id)}</h3><p>{r.status.replaceAll('_', ' ')} · Received {new Date(r.received_at).toLocaleString()}</p><small>Receipt {r.event_id}</small>{r.target_family_id && <p>Linked to {name(r.target_family_id)}; originals retained.</p>}<div className="rd-actions"><button disabled={locked} onClick={() => { if (leave()) { setSelected({ ...r }); dirty(false); setError(''); } }}>Review registration</button></div></article>)}</div>
      {!rows.length && <p>No registration receipts received by AI-BS yet. Families can still be added manually.</p>}
      {selected && <form className="rd-editor" onSubmit={saveReview}><h3>Review {name(selected.family_id)}</h3><p>Original submission family and contacts are preserved. A duplicate link records an association only.</p>
        {records.filter(r => r.payload.family_id === selected.family_id && r.kind === 'person').map(r => <p key={r.id}>{r.payload.name} · {r.payload.role || 'unknown'} · {r.payload.email || 'Email unknown'} · {r.payload.phone || 'Phone unknown'}</p>)}
        <div className="rd-fields"><label>Review decision<select value={selected.status} onChange={e => { setSelected(r => r ? ({ ...r, status: e.target.value, target_family_id: '' }) : r); dirty(true); }}>{['pending', 'accepted', 'needs_information', 'duplicate'].map(s => <option value={s} key={s}>{s.replaceAll('_', ' ')}</option>)}</select></label>
        {selected.status === 'duplicate' && <label>Link to existing family<select required value={selected.target_family_id} onChange={e => { setSelected(r => r ? ({ ...r, target_family_id: e.target.value }) : r); dirty(true); }}><option value="">Choose a different family</option>{families.filter(r => r.id !== selected.family_id).map(r => <option key={r.id} value={r.id}>{name(r.id)}</option>)}</select></label>}
        <label>Internal review notes<textarea maxLength={4000} value={selected.notes} onChange={e => { setSelected(r => r ? ({ ...r, notes: e.target.value }) : r); dirty(true); }} /></label></div>
        <button disabled={locked || !actor.trim()}>Save registration review</button><p>Review revision {selected.revision}. Enter Recorded by above before saving.</p>
      </form>}
    </> : <div className="rd-editor"><h3>Family timeline</h3><p>Saved changes and internal notes appear here. Detailed history starts with this feature; earlier records remain in the workspace. Staff names are entered attribution.</p>
      <label>Timeline family<select value={family} disabled={locked} onChange={e => { if (leave()) { const id = e.target.value; setFamily(id); setNote(''); dirty(false); setTimeline(null); if (id) history(id); } }}><option value="">Select a family</option>{families.map(r => <option key={r.id} value={r.id}>{name(r.id)}</option>)}</select></label>
      {family && <><button disabled={locked || changed} onClick={() => history(family)}>Refresh timeline</button><form onSubmit={saveNote}><label>Internal family note<textarea required maxLength={4000} value={note} onChange={e => { setNote(e.target.value); dirty(true); }} /></label><button disabled={locked || !actor.trim() || !note.trim()}>Save internal note</button><p>Internal only. Saving never sends this note.</p></form></>}
      {timeline && <><ol className="rd-timeline">{timeline.entries.map(e => <li className="rd-card" key={e.sequence}><strong>{e.action.replaceAll('_', ' ')}</strong><p>{e.actor} · {new Date(e.created_at).toLocaleString()} · #{e.sequence}</p>{e.details.text && <p className="rd-notes">{e.details.text}</p>}{e.details.notes && <p className="rd-notes">{e.details.notes}</p>}<details><summary>Saved evidence</summary><pre>{JSON.stringify(e.details, null, 2)}</pre></details></li>)}</ol>{!timeline.entries.length && <p>No detailed history yet. Existing records have not been removed.</p>}{timeline.next_before && <button disabled={locked || changed} onClick={() => history(family, timeline.next_before)}>Load older history</button>}</>}
    </div>}
  </div>;
}
