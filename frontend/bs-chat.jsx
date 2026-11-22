import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from './firebase.js';
import { ADMIN_EMAILS, ADMIN_UIDS } from './components/accessControl.js';
import LoginModal from './components/LoginModal.jsx';
import MobileStehouwerChat from './components/MobileStehouwerChat.jsx';
import { useAppStore } from './components/useAppStore.js';
import { getApiBase } from './config/api.js';
import { chatAuthHeaders } from './src/utils/chatAuth.js';
import { readBSChatProviderConfig } from './src/utils/bsChatProvider.js';
import './src/index.css';
import './style.css';
import './responsive-fixes.css';

const isVerifiedAdmin = user => Boolean(user && user.emailVerified && (
  ADMIN_EMAILS.includes((user.email || '').toLowerCase().trim()) || ADMIN_UIDS.includes(user.uid)
));
const localDesktop = window.location.protocol === 'http:' &&
  ['localhost', '127.0.0.1'].includes(window.location.hostname) &&
  !/Android|iPhone|iPad|iPod/i.test(navigator.userAgent) && !window.Capacitor?.isNativePlatform?.();
const backendUrl = localDesktop ? 'http://127.0.0.1:8000' : getApiBase();

// Keep the same account/abort/redirect checks as the Studio entry for child
// components that rely on authenticated fetch rather than chatAuthHeaders.
const originalFetch = window.fetch;
let authGeneration = 0;
onAuthStateChanged(auth, () => { authGeneration += 1; });
window.fetch = async function (resource, config = {}) {
  config = config || {};
  let requestUrl;
  try {
    requestUrl = new URL(resource instanceof Request ? resource.url : String(resource), window.location.href);
  } catch {
    return originalFetch.call(window, resource, config);
  }
  const localApi = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:8080', 'http://127.0.0.1:8080'].includes(requestUrl.origin);
  const localDevProxy = ['localhost', '127.0.0.1'].includes(window.location.hostname) &&
    requestUrl.origin === window.location.origin && /^\/(api|v1)(\/|$)/.test(requestUrl.pathname);
  const hostedApi = requestUrl.origin === 'https://api.brettstehouwer.live';
  const user = auth.currentUser;
  const generation = authGeneration;
  if (!(localApi || localDevProxy || hostedApi) || !isVerifiedAdmin(user)) return originalFetch.call(window, resource, config);
  const signal = config.signal || (resource instanceof Request ? resource.signal : null);
  const ensureCurrent = () => {
    if (signal?.aborted || auth.currentUser !== user || authGeneration !== generation) {
      throw new DOMException('Request cancelled because its account or abort state changed.', 'AbortError');
    }
  };
  ensureCurrent();
  const headers = new Headers(resource instanceof Request ? resource.headers : undefined);
  new Headers(config.headers || {}).forEach((value, name) => headers.set(name, value));
  if (!headers.has('Authorization') && !headers.has('X-Admin-Key') && !headers.has('X-API-Key')) {
    const token = await user.getIdToken();
    ensureCurrent();
    if (!token) throw new Error('A verified identity token is unavailable.');
    headers.set('Authorization', `Bearer ${token}`);
  }
  ensureCurrent();
  const response = await originalFetch.call(window, resource, { ...config, headers, redirect: 'error' });
  ensureCurrent();
  return response;
};

function BSChatEntry() {
  const [currentUser, setCurrentUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [authError, setAuthError] = useState('');
  useEffect(() => onAuthStateChanged(auth, user => {
    const admitted = isVerifiedAdmin(user) ? user : null;
    useAppStore.getState().setBackendUrl(backendUrl);
    useAppStore.getState().setCurrentUser(admitted);
    setCurrentUser(admitted);
    setReady(true);
    setAuthError(user && !admitted ? 'This verified account is not on the AI-BS administrator list.' : '');
  }, () => {
    useAppStore.getState().setCurrentUser(null);
    setCurrentUser(null);
    setReady(true);
    setAuthError('Unable to verify sign-in. Please sign in again.');
  }), []);

  useEffect(() => {
    if (!currentUser) return;
    let current = true;
    const uid = currentUser.uid;
    const revision = useAppStore.getState().aiProviderSelectionRevision;
    (async () => {
      try {
        const response = await fetch(`${backendUrl}/api/ai/providers`, { headers: await chatAuthHeaders({}, uid) });
        if (!response.ok) return;
        const configuration = readBSChatProviderConfig(await response.json());
        if (current && auth.currentUser?.uid === uid) useAppStore.getState().setAIProviderConfiguration(configuration, revision);
      } catch { /* Keep the existing selection if discovery is unavailable. */ }
    })();
    return () => { current = false; };
  }, [currentUser?.uid]);

  if (!ready) return <p role="status">Verifying sign-in…</p>;
  if (!currentUser) return <>
    <LoginModal backendUrl={backendUrl} onLoginSuccess={() => { /* Firebase observer admits the account. */ }} />
    <aside className="bs-chat-sign-in">
      {authError && <p role="alert">{authError}</p>}
      Google sign-in inside an Android app is not qualified.{' '}
      <a href="https://ai-bs-dashboard.web.app/chat" target="_blank" rel="noopener noreferrer">Open BS-Chat in your browser</a>.
      {' '}Browser and app sign-in sessions are separate.
    </aside>
  </>;
  return <MobileStehouwerChat key={currentUser.uid} currentUser={currentUser} backendUrl={backendUrl}
    onSwitchToDesktop={() => { window.location.assign('/chat'); }} />;
}

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('Missing BS-Chat root element.');
ReactDOM.createRoot(rootElement).render(<React.StrictMode><BSChatEntry /></React.StrictMode>);
