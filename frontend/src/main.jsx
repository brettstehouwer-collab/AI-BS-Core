import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

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
// GLOBAL FETCH INTERCEPTOR (Ngrok Bypass)
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

  if (!isMobileOrHttps && typeof resource === 'string' && (resource.includes('api.brettstehouwer.live') || resource.includes('ai-bs.brettstehouwer.live'))) {
    if ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.protocol === 'http:') {
      resource = resource.replace(/https:\/\/(api|ai-bs)\.brettstehouwer\.live/, 'http://127.0.0.1:8000');
    }
  }
  
  return originalFetch(resource, config);
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
