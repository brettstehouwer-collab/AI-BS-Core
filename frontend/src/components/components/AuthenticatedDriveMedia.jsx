import React, { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { useAppStore } from './useAppStore';

/** @param {{BACKEND_URL?:string,currentUser?:{uid?:string}|null}} state */
const contextStamp = state => JSON.stringify([state?.BACKEND_URL, state?.currentUser?.uid || '']);

/** @param {string} [backendUrl] */
export function useDriveMediaSession(backendUrl = '') {
  const backend = useRef(backendUrl);
  backend.current = backendUrl;
  const [session] = useState(() => {
    let generation = 0;
    const snapshot = () => JSON.stringify([generation, contextStamp(useAppStore.getState())]);
    return { snapshot,
      /** @param {()=>void} notify */
      subscribe(notify) {
        const unsubscribe = useAppStore.subscribe((next, previous) => {
          if (contextStamp(next) !== contextStamp(previous)) { generation++; notify(); }
        });
        return () => { generation++; unsubscribe(); };
      },
    };
  });
  const snapshot = useSyncExternalStore(session.subscribe, session.snapshot, session.snapshot);
  const key = JSON.stringify([backendUrl, snapshot]);
  return useMemo(() => ({ key, isCurrent: () => session.snapshot() === snapshot && backend.current === backendUrl }), [session, snapshot, backendUrl, key]);
}

/** @param {string} backendUrl @param {string} path @param {string} [action] @param {AbortSignal} [signal] */
export async function requestDriveMediaUrl(backendUrl, path, action = 'preview', signal) {
  const stamp = contextStamp(useAppStore.getState());
  let retired = false;
  const unsubscribe = useAppStore.subscribe((next, previous) => {
    if (contextStamp(next) !== contextStamp(previous)) retired = true;
  });
  const requireCurrent = () => {
    if (retired || signal?.aborted || contextStamp(useAppStore.getState()) !== stamp) {
      throw new Error('The media request belongs to an earlier sign-in session.');
    }
  };
  try {
    requireCurrent();
    const response = await fetch(`${backendUrl}/api/drive/media-ticket`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, action }), signal,
    });
    requireCurrent();
    const data = await response.json();
    requireCurrent();
    if (!response.ok) throw new Error(data.detail || 'Administrator sign-in is required to open this file.');
    const api = new URL(backendUrl || '/', window.location.href);
    const url = new URL(data.url, api);
    if (url.origin !== api.origin || !url.pathname.startsWith('/api/drive/')) {
      throw new Error('The server returned an invalid media link.');
    }
    return url.href;
  } finally {
    unsubscribe();
  }
}

/** @param {string} backendUrl @param {string} path @param {string} action */
function useDriveMediaUrl(backendUrl, path, action) {
  const session = useDriveMediaSession(backendUrl);
  const key = JSON.stringify([backendUrl, path, action, session.key]);
  const [state, setState] = useState(/** @type {{key?:string,url?:string,error?:string}} */ ({}));
  useEffect(() => {
    const controller = new AbortController();
    requestDriveMediaUrl(backendUrl, path, action, controller.signal)
      .then(url => { if (!controller.signal.aborted && session.isCurrent()) setState({ key, url }); })
      .catch(error => { if (!controller.signal.aborted && session.isCurrent()) setState({ key, error: error.message }); });
    return () => controller.abort();
  }, [backendUrl, path, action, key, session]);
  return state.key === key ? state : {};
}

export function AuthenticatedDriveMedia({ backendUrl, path, as = 'iframe', ...props }) {
  const { url, error } = useDriveMediaUrl(backendUrl, path, 'preview');
  if (error) return <span role="alert">Unable to open file: {error}</span>;
  if (!url) return <span role="status">Preparing file preview…</span>;
  return React.createElement(as, { ...props, src: url, referrerPolicy: 'no-referrer' });
}

export function AuthenticatedDriveDownload({ backendUrl, path, children, ...props }) {
  const { url, error } = useDriveMediaUrl(backendUrl, path, 'download');
  if (error) return <span role="alert">Download unavailable: {error}</span>;
  return <a {...props} href={url} referrerPolicy="no-referrer" aria-disabled={!url}
    onClick={event => { if (!url) event.preventDefault(); }}>
    {children}{!url && ' (preparing…)'}
  </a>;
}
