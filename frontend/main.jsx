import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './src/index.css';
import './style.css';
import './responsive-fixes.css';
import { initAntiTamperGuard } from './utils/antiTamperGuard.js';

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
window.fetch = async function () {
  let [resource, config] = arguments;
  
  const isMobileOrHttps = typeof window !== 'undefined' && (
    window.location.protocol === 'https:' ||
    window.location.protocol === 'capacitor:' ||
    !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  );

  if (!isMobileOrHttps && typeof resource === 'string' && resource.includes('brettstehouwer.live')) {
    // Only rewrite for desktop PC local dev running on plain HTTP localhost
    if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.protocol === 'http:') {
      resource = resource.replace(/https?:\/\/[a-zA-Z0-9.-]*brettstehouwer\.live/, 'http://127.0.0.1:8000');
    }
  }
  
  return originalFetch(resource, config);
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
