import React, { useEffect, useRef, useState } from 'react';
import { emptyTruckProfile, openTruckProfileStore } from './truckProfileStore.js';
import './truckProfile.css';

const DIMENSIONS = { cargo_box_length_ft: 'Cargo box length (feet)', height_in: 'Actual total height (inches)', width_in: 'Actual width (inches)', overall_length_ft: 'Actual overall vehicle length (feet)', loaded_gross_lb: 'Actual loaded gross weight (pounds)' };

export default function TruckProfile({ instance, owner }) {
  const [state, setState] = useState(null), [draft, setDraft] = useState(emptyTruckProfile), [error, setError] = useState(''), [saving, setSaving] = useState(false), [busy, setBusy] = useState(false), [unsaved, setUnsaved] = useState(false);
  const store = useRef(null), current = useRef(null), draftRef = useRef(emptyTruckProfile()), chain = useRef(Promise.resolve()), alive = useRef(false), localWrites = useRef(0), unsavedRef = useRef(false);
  const accept = (value, replaceDraft = true) => {
    if (!alive.current) return;
    current.current = value; setState(value);
    if (replaceDraft) { draftRef.current = value.draft; setDraft(value.draft); unsavedRef.current = false; setUnsaved(false); }
  };
  const enqueue = task => {
    const next = chain.current.then(task);
    chain.current = next.catch(failure => { if (alive.current) setError(failure.message); });
    return chain.current;
  };
  const transfer = action => enqueue(async () => {
    if (!store.current) throw new Error('Open the saved truck profile first');
    setBusy(true); setError('');
    try { accept(await store.current[action](operation => instance.truckProfile(operation))); }
    catch (failure) { if (store.current) accept(await store.current.snapshot()); throw failure; }
    finally { if (alive.current) setBusy(false); }
  });
  useEffect(() => {
    alive.current = true;
    let cancelled = false;
    const guard = () => { if (cancelled || !alive.current || instance.getSnapshot().owner !== owner) throw new Error('Driver sign-in changed'); };
    const opening = openTruckProfileStore(owner, guard).then(async cache => { store.current = cache; const initial = await cache.snapshot(); guard(); accept(initial); }).catch(failure => { if (!cancelled && alive.current) setError(failure.message); });
    chain.current = opening;
    const reconnect = () => { void enqueue(async () => {
      if (!store.current) return;
      const snapshot = await store.current.snapshot();
      if ((snapshot.dirty || snapshot.pending) && !snapshot.conflict) {
        setBusy(true);
        try { accept(await store.current.sync(operation => instance.truckProfile(operation))); }
        catch (failure) { if (store.current) accept(await store.current.snapshot()); throw failure; }
        finally { if (alive.current) setBusy(false); }
      }
    }); };
    const leaving = event => { if (localWrites.current || unsavedRef.current) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('online', reconnect); window.addEventListener('beforeunload', leaving);
    return () => { cancelled = true; alive.current = false; store.current?.close(); store.current = null; window.removeEventListener('online', reconnect); window.removeEventListener('beforeunload', leaving); };
  }, [instance, owner]);
  const edit = (key, value) => {
    const next = { ...draftRef.current, [key]: value };
    if (Object.hasOwn(DIMENSIONS, key) || key === 'vehicle_configuration') next.dimensions_confirmed = false;
    if (key === 'loaded_gross_lb' || key === 'axles') next.weights_confirmed = false;
    draftRef.current = next; setDraft(next); localWrites.current++; setSaving(true); unsavedRef.current = true; setUnsaved(true);
    void enqueue(async () => {
      try {
        if (!store.current || !current.current) throw new Error('Truck-profile cache unavailable; this edit is not saved');
        accept(await store.current.change(next, current.current.generation), false); setError('');
        if (localWrites.current === 1) { unsavedRef.current = false; setUnsaved(false); }
      } finally { localWrites.current--; if (alive.current) setSaving(localWrites.current > 0); }
    });
  };
  const resolve = decision => enqueue(async () => { accept(await store.current.resolve(decision, current.current.generation)); setError(''); });
  const locked = !state || busy || Boolean(state.pending || state.conflict);
  return <section className="truck-profile" aria-label="Truck profile">
    <h2>Truck profile</h2>
    <p>Record the whole vehicle, including tractor where applicable. Cargo box length alone is not overall length. Leave unmeasured facts blank.</p>
    <p role="status">{saving ? 'Saving truck draft…' : unsaved ? 'Truck edits are not saved — keep this view open' : state?.pending ? 'Upload confirmation pending — saved retry retained' : state?.dirty ? 'Truck draft saved on this device — not synchronized' : state ? `Truck profile saved revision ${state.revision}` : 'Opening truck profile…'}</p>
    <p><strong>Truck navigation unavailable.</strong> Vehicle facts and a maintained truck-routing provider must be qualified first.</p>
    {error && <p role="alert">{error}</p>}
    <fieldset disabled={locked}>
      <label>Vehicle configuration<select aria-label="Vehicle configuration" value={draft.vehicle_configuration || 'unknown'} onChange={event => edit('vehicle_configuration', event.target.value)}><option value="unknown">Not confirmed</option><option value="straight_truck">Straight truck</option><option value="tractor_trailer">Tractor and trailer</option><option value="other">Other</option></select></label>
      {Object.entries(DIMENSIONS).map(([key, label]) => <label key={key}>{label}<input type="number" min="0.01" step="any" value={draft[key] ?? ''} onChange={event => edit(key, event.target.value === '' ? null : Number(event.target.value))}/></label>)}
      <h3>Individual axle weights</h3>
      {(draft.axles || []).map((axle, index) => <div key={index}>
        <label>Axle {index + 1} identifier<input maxLength={100} value={axle.axle_id} onChange={event => edit('axles', draftRef.current.axles.map((item, position) => position === index ? { ...item, axle_id: event.target.value } : item))}/></label>
        <label>Axle {index + 1} actual weight (pounds)<input type="number" min="0.01" step="any" value={axle.actual_weight_lb ?? ''} onChange={event => edit('axles', draftRef.current.axles.map((item, position) => position === index ? { ...item, actual_weight_lb: event.target.value === '' ? null : Number(event.target.value) } : item))}/></label>
        <button type="button" onClick={() => edit('axles', draftRef.current.axles.filter((_, position) => position !== index))}>Remove axle {index + 1}</button>
      </div>)}
      <button type="button" disabled={(draft.axles || []).length >= 16} onClick={() => edit('axles', [...(draftRef.current.axles || []), { axle_id: `axle-${crypto.randomUUID().slice(0, 8)}`, actual_weight_lb: null }])}>Add axle</button>
      <label>Hazardous materials<select aria-label="Hazardous materials" value={draft.hazmat_status || 'unknown'} onChange={event => edit('hazmat_status', event.target.value)}><option value="unknown">Not confirmed</option><option value="none">None declared for this load</option><option value="declared">Declared — record restrictions below</option></select></label>
      <label>Restrictions and permit notes<textarea aria-label="Restrictions and permit notes" maxLength={4000} value={draft.restrictions_notes || ''} onChange={event => edit('restrictions_notes', event.target.value)}/></label>
      <label>Measurement source and date<textarea aria-label="Measurement source and date" maxLength={4000} value={draft.measurement_notes || ''} onChange={event => edit('measurement_notes', event.target.value)}/></label>
      <label><input type="checkbox" checked={Boolean(draft.dimensions_confirmed)} onChange={event => edit('dimensions_confirmed', event.target.checked)}/>I have confirmed actual whole-vehicle dimensions</label>
      <label><input type="checkbox" checked={Boolean(draft.weights_confirmed)} onChange={event => edit('weights_confirmed', event.target.checked)}/>I have confirmed loaded gross and every axle weight</label>
    </fieldset>
    <div className="quick"><button disabled={!state || busy || saving || unsaved || Boolean(state.conflict)} onClick={() => void transfer('sync')}>Sync / retry truck profile</button><button disabled={!state || busy || saving || unsaved || Boolean(state.pending)} onClick={() => void transfer('pull')}>Review server truck profile</button><button disabled={busy || saving} onClick={() => void enqueue(async () => accept(await store.current.snapshot()))}>Reload saved truck draft</button></div>
    {state?.conflict && <div role="region" aria-label="Truck profile conflict"><h3>Choose which truck profile to keep</h3><p>Your local version is retained until you choose. Keeping it requires another sync.</p><h4>Local draft</h4><pre>{JSON.stringify(state.draft, null, 2)}</pre><h4>Server revision {state.conflict.revision}</h4><pre>{JSON.stringify(state.conflict.profile?.payload || {}, null, 2)}</pre><button disabled={busy || saving} onClick={() => void resolve('keep-local')}>Keep local truck draft</button><button disabled={busy || saving} onClick={() => void resolve('use-server')}>Use server truck profile</button></div>}
  </section>;
}
