import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '/firebase.js';
import { ADMIN_EMAILS, ADMIN_UIDS } from '/components/accessControl.js';
import ScreenwritingTab from '../components/ScreenwritingTab.jsx';
import './index.css';
import '../components/ScreenwritingTab.css';
import './mobile_writer.css';

const originalFetch = window.fetch;
window.fetch = async function (resource, config = {}) {
  config = config || {};
  let requestUrl;
  try {
    requestUrl = new URL(resource instanceof Request ? resource.url : String(resource), window.location.href);
  } catch {
    return originalFetch(resource, config);
  }
  
  const isMobileOrHttps = typeof window !== 'undefined' && (
    window.location.protocol === 'https:' ||
    window.location.protocol === 'capacitor:' ||
    !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  );

  if (!isMobileOrHttps && requestUrl.hostname.endsWith('brettstehouwer.live')) {
    // Only rewrite for desktop PC local dev running on plain HTTP localhost
    if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.protocol === 'http:') {
      requestUrl = new URL(`http://127.0.0.1:8000${requestUrl.pathname}${requestUrl.search}${requestUrl.hash}`);
      resource = resource instanceof Request ? new Request(requestUrl.href, resource) : requestUrl.href;
    }
  }

  const localApi = ['localhost', '127.0.0.1'].includes(requestUrl.hostname) && ['8000', '8080'].includes(requestUrl.port);
  const localDevProxy = ['localhost', '127.0.0.1'].includes(window.location.hostname) &&
    requestUrl.origin === window.location.origin && /^\/(api|v1)(\/|$)/.test(requestUrl.pathname);
  const hostedApi = requestUrl.protocol === 'https:' && requestUrl.hostname === 'api.brettstehouwer.live';
  const user = auth.currentUser;
  const userEmail = (user?.email || '').toLowerCase().trim();
  const isAdmin = Boolean(user && user.emailVerified && (
    ADMIN_EMAILS.includes(userEmail) || ADMIN_UIDS.includes(user.uid)
  ));

  if ((localApi || localDevProxy || hostedApi) && isAdmin) {
    const headers = new Headers(resource instanceof Request ? resource.headers : undefined);
    new Headers(config.headers || {}).forEach((value, name) => headers.set(name, value));
    if (!headers.has('Authorization') && !headers.has('X-Admin-Key') && !headers.has('X-API-Key')) {
      try {
        headers.set('Authorization', `Bearer ${await user.getIdToken()}`);
      } catch {
        // Protected API routes fail closed if Firebase cannot provide an ID token.
      }
    }
    config = { ...config, headers };
  }

  return originalFetch(resource, config);
};

const StandaloneWriterApp = () => {
  const [session, setSession] = useState({ ready: false, user: null });
  useEffect(() => onAuthStateChanged(auth, user => setSession({ ready: true, user })), []);
  const user = session.user;
  const allowed = Boolean(user?.emailVerified && (
    ADMIN_EMAILS.includes((user.email || '').toLowerCase().trim()) || ADMIN_UIDS.includes(user.uid)
  ));
  const local = ['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.protocol === 'http:';
  const backendUrl = local ? 'http://127.0.0.1:8000' : 'https://api.brettstehouwer.live';
  if (!session.ready) return <main role="status">Checking your writer session…</main>;
  if (!allowed) return <main style={{ padding: '2rem' }}>
    <h1>Sign in to the Writing Studio</h1>
    <p>Use your administrator account in the AI-BS dashboard, then return to this writer.</p>
    <a href="/?tab=unified_creation">Open AI-BS sign-in</a>
  </main>;
  return <div className="mobile-writer-root"><ScreenwritingTab backendUrl={backendUrl} /></div>;
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><StandaloneWriterApp /></React.StrictMode>
);
