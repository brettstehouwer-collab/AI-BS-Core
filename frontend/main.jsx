import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './src/index.css';
import './style.css';
import './responsive-fixes.css';
import { initAntiTamperGuard } from './utils/antiTamperGuard.js';
import { auth } from './firebase.js';
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

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
