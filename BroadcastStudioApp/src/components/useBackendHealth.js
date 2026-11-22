import { useState, useEffect } from 'react';
import { getApiBase, setApiBase } from '../config/api.js';

export function useBackendHealth(intervalMs = 10000) {
  const [backendUrl, setBackendUrl] = useState(getApiBase());
  const [backendStatus, setBackendStatus] = useState('checking'); // checking | online | offline

  useEffect(() => {
    let isMounted = true;
    const isLocal = typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.protocol === 'file:'
    );

    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';

    const checkBackend = async () => {
      // 1. Try Localhost FastAPI Backend (for local dev or HTTP environments)
      if (!isHttps || isLocal) {
        for (const path of ['/v1/health', '/api/health', '/health']) {
          try {
            const localRes = await fetch(`http://127.0.0.1:8000${path}`, { signal: AbortSignal.timeout(1500) });
            if (isMounted && localRes.ok) {
              setApiBase('http://127.0.0.1:8000');
              setBackendUrl('http://127.0.0.1:8000');
              setBackendStatus('online');
              return;
            }
          } catch (e) {
            // Localhost unavailable
          }
        }
      }

      if (isMounted && isLocal) {
        setApiBase('http://127.0.0.1:8000');
        setBackendUrl('http://127.0.0.1:8000');
        setBackendStatus('online');
        return;
      }

      // 1.5. Try Hostname IP (Tailscale/LAN)
      const hn = typeof window !== 'undefined' ? window.location.hostname : '';
      const isIp = /^\d+\.\d+\.\d+\.\d+$/.test(hn) && hn !== '127.0.0.1';
      
      if (!isHttps && isIp) {
        for (const path of ['/v1/health', '/api/health', '/health']) {
          try {
            const ipRes = await fetch(`http://${hn}:8000${path}`, { signal: AbortSignal.timeout(1500) });
            if (isMounted && ipRes.ok) {
              setApiBase(`http://${hn}:8000`);
              setBackendUrl(`http://${hn}:8000`);
              setBackendStatus('online');
              return;
            }
          } catch (e) {
            // IP unavailable
          }
        }
      }

      // 2. Try Remote Production Domains over HTTPS
      const candidateDomains = [
        'https://ai-bs.brettstehouwer.live',
        'https://api.brettstehouwer.live'
      ];

      for (const domain of candidateDomains) {
        try {
          const res = await fetch(`${domain}/api/health`, { signal: AbortSignal.timeout(2500) });
          if (isMounted && res.ok) {
            setApiBase(domain);
            setBackendUrl(domain);
            setBackendStatus('online');
            return;
          }
        } catch (e) {
          // Fallback domain
        }
      }

      // 3. Fallback to configured API base
      if (isMounted) {
        setBackendStatus('offline');
      }
    };
    
    checkBackend();
    const interval = setInterval(checkBackend, intervalMs);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [intervalMs]);

  return { backendUrl, backendStatus };
}
