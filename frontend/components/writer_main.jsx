import React from 'react';
import ReactDOM from 'react-dom/client';
import ScreenwritingTab from '../components/ScreenwritingTab.jsx';
import './index.css';
import '../components/ScreenwritingTab.css';
import './mobile_writer.css';

// ═══════════════════════════════════════════════════════════════════════
// GLOBAL FETCH INTERCEPTOR (Ngrok Bypass / Local Routing)
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

const StandaloneWriterApp = () => {
  return (
    <div className="mobile-writer-root">
      <ScreenwritingTab backendUrl="http://127.0.0.1:8000" />
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <StandaloneWriterApp />
  </React.StrictMode>
);
