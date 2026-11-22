/** @jsxRuntime classic */
import React, { useState, useEffect } from './applicationReact.js';

/** @typedef {import('/types/portal').PortalValue} PortalValue */
const Context = React.createContext(/** @type {import('/types/portal').PortalContextValue | null} */ (null));
/**
 * Versioned legacy hydration boundary: callers own each field's inert data contract.
 * This assertion preserves saved JSON verbatim; it is not runtime schema validation.
 * @template T @param {unknown} value @returns {T}
 */
function readPortalField(value) { return /** @type {T} */ (value); }

// Only inert values are restored. Saving a draft never submits a business action.
/** @overload @param {string} key @param {string | (() => string)} initial @returns {[string, import('react').Dispatch<import('react').SetStateAction<string>>]} */
/** @overload @param {string} key @param {number | (() => number)} initial @returns {[number, import('react').Dispatch<import('react').SetStateAction<number>>]} */
/** @overload @param {string} key @param {boolean | (() => boolean)} initial @returns {[boolean, import('react').Dispatch<import('react').SetStateAction<boolean>>]} */
/** @template {PortalValue} T @overload @param {string} key @param {T | (() => T)} initial @returns {[T, import('react').Dispatch<import('react').SetStateAction<T>>]} */
/** @template {PortalValue} T @param {string} key @param {T | (() => T)} initial @returns {[T, import('react').Dispatch<import('react').SetStateAction<T>>]} */
export function usePortalState(key, initial) {
  const context = React.useContext(Context);
  if (!context) throw new Error("Portal workspace is unavailable.");
  const fallback = React.useRef(/** @type {{value: T} | null} */ (null));
  if (!fallback.current) fallback.current = { value: typeof initial === 'function' ? initial() : initial };
  /** @type {T} */
  const value = Object.hasOwn(context.values, key) ? readPortalField(context.values[key]) : fallback.current.value;
  const initialValue = fallback.current.value;
  /** @param {import("react").SetStateAction<T>} next */
  const set = next => context.update(key, next, initialValue);
  return [value, set];
}

export function PortalSaveButton() {
  const context = React.useContext(Context);
  if (!context) throw new Error("Portal workspace is unavailable.");
  return <div style={{ padding: 12, background: '#142033', color: '#f8fafc', border: '1px solid #475569', borderRadius: 8, marginBottom: 14 }}>
    <button type="button" disabled={context.saving} onClick={context.save} style={{ padding: '11px 18px', background: '#047857', color: 'white', border: '1px solid #34d399', borderRadius: 6 }}> {context.saving ? 'Saving portal…' : 'Save portal'} </button>
    <span role="status" style={{ marginLeft: 12 }}>{context.error || (context.dirty ? 'Portal changes not yet saved.' : context.savedAt ? `Portal saved ${new Date(context.savedAt).toLocaleString()}.` : 'Ready to save portal settings and drafts.')}</span>
    <div style={{ fontSize: 12, marginTop: 6 }}>Shared across FE Express sessions and devices. Saves selections and form drafts. Use Add driver, Save day or Save shipment to finalize records; upload selected files before leaving. Restoring a draft does not submit it.</div>
  </div>;
}

/** @param {{baseUrl:string,request:typeof fetch,children:import("react").ReactNode}} props */
export function PortalWorkspace({ baseUrl, request, children }) {
  const [snapshot, setSnapshot] = useState(/** @type {Record<string, unknown> | null} */ (null)), [error, setError] = useState('');
  const [saving, setSaving] = useState(false), [savedAt, setSavedAt] = useState(/** @type {string | null} */ (null));
  const [dirty, setDirty] = useState(false);
  const state = React.useRef(/** @type {{values:Record<string,unknown>,revision:number,serial:number}} */ ({ values: {}, revision: 0, serial: 0 }));
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
  /** @template {PortalValue} T @param {string} key @param {import("react").SetStateAction<T>} next @param {T} fallback */
  function update(key, next, fallback) {
    const current = state.current;
    /** @type {T} */
    const previous = Object.hasOwn(current.values, key) ? readPortalField(current.values[key]) : fallback;
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
