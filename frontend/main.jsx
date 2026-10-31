import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './src/index.css';
import './style.css';
import './responsive-fixes.css';
import { initAntiTamperGuard } from './utils/antiTamperGuard.js';
import { auth } from './firebase.js';
import { onAuthStateChanged } from 'firebase/auth';
import { ADMIN_EMAILS, ADMIN_UIDS } from './components/accessControl.js';

// Initialize Client-Side Anti-Tamper & IP Protection Guard
initAntiTamperGuard();

// Register Service Worker for Mobile PWA Installation
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

// Silence React DevTools prompt in console
if (typeof window !== 'undefined') {
  const origInfo = console.info;
  console.info = (...args) => {
    if (typeof args[0] === 'string' && args[0].includes('Download the React DevTools')) return;
    origInfo.apply(console, args);
  };
}

// ═══════════════════════════════════════════════════════════════════════
// GLOBAL FETCH INTERCEPTOR (Local Dev & Ngrok Bypass)
// Automatically handles Ngrok warnings and localhost routing for zero-latency.
// ═══════════════════════════════════════════════════════════════════════
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
  const isMobileOrHttps = window.location.protocol === 'https:' || window.location.protocol === 'capacitor:' ||
    Boolean(window.Capacitor?.isNativePlatform?.()) || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  const hostedGateway = requestUrl.protocol === 'https:' && ['api.brettstehouwer.live', 'ai-bs.brettstehouwer.live'].includes(requestUrl.hostname);
  if (!isMobileOrHttps && hostedGateway && ['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.protocol === 'http:') {
    requestUrl = new URL(`http://127.0.0.1:8000${requestUrl.pathname}${requestUrl.search}${requestUrl.hash}`);
    resource = resource instanceof Request ? new Request(requestUrl.href, resource) : requestUrl.href;
  }
  const localApi = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:8080', 'http://127.0.0.1:8080'].includes(requestUrl.origin);
  const localDevProxy = ['localhost', '127.0.0.1'].includes(window.location.hostname) &&
    requestUrl.origin === window.location.origin && /^\/(api|v1)(\/|$)/.test(requestUrl.pathname);
  const hostedApi = requestUrl.origin === 'https://api.brettstehouwer.live';
  const user = auth.currentUser;
  const generation = authGeneration;
  const userEmail = (user?.email || '').toLowerCase().trim();
  const isAdmin = Boolean(user && user.emailVerified && (ADMIN_EMAILS.includes(userEmail) || ADMIN_UIDS.includes(user.uid)));
  if (!(localApi || localDevProxy || hostedApi) || !isAdmin) return originalFetch.call(window, resource, config);

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
  // An owned authenticated request may not follow a redirect to another destination.
  const response = await originalFetch.call(window, resource, { ...config, headers, redirect: 'error' });
  ensureCurrent();
  return response;
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
