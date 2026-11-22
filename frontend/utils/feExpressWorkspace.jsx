/** @jsxRuntime classic */
import React, { useState, useEffect } from './applicationReact.js';

const Context = React.createContext(/** @type {any} */ (null));

// Only inert values are restored. Saving a draft never submits a business action.
/** @param {string} key @param {any} initial @returns {[any, (next:any)=>void]} */
export function usePortalState(key, initial) {
  const context = React.useContext(Context);
  const fallback = React.useRef(/** @type {any} */ (null));
  if (!fallback.current) fallback.current = { value: typeof initial === 'function' ? initial() : initial };
  const value = Object.hasOwn(context.values, key) ? context.values[key] : fallback.current.value;
  /** @param {any} next */
  const set = next => context.update(key, next, fallback.current.value);
  return [value, set];
}

export function PortalSaveButton() {
  const context = React.useContext(Context);
  return <div style={{ padding: 12, background: '#142033', color: '#f8fafc', border: '1px solid #475569', borderRadius: 8, marginBottom: 14 }}>
    <button type="button" disabled={context.saving} onClick={context.save} style={{ padding: '11px 18px', background: '#047857', color: 'white', border: '1px solid #34d399', borderRadius: 6 }}> {context.saving ? 'Saving portal…' : 'Save portal'} </button>
    <span role="status" style={{ marginLeft: 12 }}>{context.error || (context.dirty ? 'Portal changes not yet saved.' : context.savedAt ? `Portal saved ${new Date(context.savedAt).toLocaleString()}.` : 'Ready to save portal settings and drafts.')}</span>
    <div style={{ fontSize: 12, marginTop: 6 }}>Shared across FE Express sessions and devices. Saves selections and form drafts. Use Add driver, Save day or Save shipment to finalize records; upload selected files before leaving. Restoring a draft does not submit it.</div>
  </div>;
}

/** @param {{baseUrl:string,request:typeof fetch,children:import("react").ReactNode}} props */
export function PortalWorkspace({ baseUrl, request, children }) {
  const [snapshot, setSnapshot] = useState(/** @type {any} */ (null)), [error, setError] = useState('');
  const [saving, setSaving] = useState(false), [savedAt, setSavedAt] = useState(/** @type {any} */ (null));
  const [dirty, setDirty] = useState(false);
  const state = React.useRef(/** @type {{values:Record<string,any>,revision:number,serial:number}} */ ({ values: {}, revision: 0, serial: 0 }));
  const url = `${baseUrl.replace(/\/$/, '')}/api/v1/fe-express/workspace`;
  async function load() {
    setError('');
    try {
      const response = await request(url);
      if (!response.ok) throw Error(`Cannot load saved portal (${response.status}).`);
      const body = await response.json();
      if (!Number.isInteger(body.revision) || !body.values || Array.isArray(body.values)) throw Error('Invalid saved portal response.');
      state.current = { values: body.values, revision: body.revision, serial: 0 };
      setSnapshot(body.values); setSavedAt(body.saved_at); setDirty(false);
    } catch (e) { setError(e instanceof Error ? e.message : 'Cannot load saved portal.'); }
  }
  useEffect(() => { load(); }, [url, request]);
  useEffect(() => {
    if (!dirty) return;
    /** @param {BeforeUnloadEvent} e */
    const warn = e => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  /** @param {string} key @param {any} next @param {any} fallback */
  function update(key, next, fallback) {
    const current = state.current;
    const previous = Object.hasOwn(current.values, key) ? current.values[key] : fallback;
    const value = typeof next === 'function' ? next(previous) : next;
    if (Object.is(previous, value)) return;
    current.values = { ...current.values, [key]: value }; current.serial++;
    setSnapshot(current.values); setDirty(true); setError('');
  }
  async function save() {
    if (saving) return;
    setSaving(true); setError('');
    const current = state.current, serial = current.serial;
    const payload = JSON.stringify({ revision: current.revision, values: current.values });
    try {
      const response = await request(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: payload });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw Error(typeof body.detail === 'string' ? body.detail : `Portal save failed (${response.status}). Your edits are still here.`);
      }
      const body = await response.json();
      state.current.revision = body.revision; setSavedAt(body.saved_at);
      setDirty(state.current.serial !== serial);
    } catch (e) { setError(e instanceof Error ? e.message : 'Save not confirmed. Keep this tab open and check a fresh tab before retrying.'); }
    finally { setSaving(false); }
  }
  if (!snapshot) return <div role="status" style={{ padding: 24, color: '#f8fafc' }}>{error || 'Loading saved FE Express portal…'}{error && <button onClick={load}>Retry loading portal</button>}</div>;
  return <Context.Provider value={{ values: snapshot, update, save, saving, savedAt, dirty, error }}>{children}</Context.Provider>;
}
