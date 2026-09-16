import { useState, useEffect } from 'react';
import { getApiBase, setApiBase } from '../config/api.js';
import { useAppStore } from './useAppStore.js';

export function useBackendHealth(intervalMs = 10000) {
  const [backendUrl, setBackendUrl] = useState(() => {
    const base = getApiBase();
    const isMobile = typeof window !== 'undefined' && (
      /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || 
      window.location.protocol === 'capacitor:' || 
      window.location.protocol === 'https:' ||
      !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform())
    );
    if (isMobile && (!base || base.includes('127.0.0.1') || base.includes('localhost'))) {
      return 'https://api.brettstehouwer.live';
    }
    return base || 'https://api.brettstehouwer.live';
  });
  const [backendStatus, setBackendStatus] = useState('checking'); // checking | online | offline

  useEffect(() => {
    let isMounted = true;
    const isCapacitor = typeof window !== 'undefined' && (
      !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
      window.location.protocol === 'capacitor:' ||
      (window.location.origin && window.location.origin.includes('localhost') && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) ||
      /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
    );

    const isLocal = !isCapacitor && typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.protocol === 'file:'
    );

    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';

    const markOnline = (targetUrl) => {
      if (!isMounted) return;
      setApiBase(targetUrl);
      setBackendUrl(targetUrl);
      setBackendStatus('online');
      try {
        const store = useAppStore.getState();
        if (store && store.setBackendUrl && store.BACKEND_URL !== targetUrl) {
          store.setBackendUrl(targetUrl);
        }
      } catch (e) {}
    };

    const checkBackend = async () => {
      // 0. If running inside native mobile app (Capacitor), prioritize Cloudflare tunnel or LAN to PC
      if (isCapacitor) {
        const candidateUrls = ['https://api.brettstehouwer.live'];
        if (!isHttps) {
          candidateUrls.push('http://192.168.4.92:8000', 'http://100.104.31.50:8000');
        }
        for (const remoteUrl of candidateUrls) {
          try {
            const res = await fetch(`${remoteUrl}/api/health`, { signal: AbortSignal.timeout(3000) });
            if (isMounted && res.ok) {
              markOnline(remoteUrl);
              return;
            }
          } catch (e) {}
        }
      }

      // 1. Try Localhost FastAPI Backend (for PC desktop dev)
      if (isLocal) {
        for (const path of ['/v1/health', '/api/health', '/health']) {
          try {
            const localRes = await fetch(`http://127.0.0.1:8000${path}`, { signal: AbortSignal.timeout(1500) });
            if (isMounted && localRes.ok) {
              markOnline('http://127.0.0.1:8000');
              return;
            }
          } catch (e) {
            // Localhost unavailable
          }
        }
        if (isMounted) {
          markOnline('http://127.0.0.1:8000');
          return;
        }
      }

      // 1.5. Try Hostname IP (Tailscale/LAN)
      const hn = typeof window !== 'undefined' ? window.location.hostname : '';
      const isIp = /^\d+\.\d+\.\d+\.\d+$/.test(hn) && hn !== '127.0.0.1';
      
      if (!isHttps && isIp) {
        for (const path of ['/v1/health', '/api/health', '/health']) {
          try {
            const ipRes = await fetch(`http://${hn}:8000${path}`, { signal: AbortSignal.timeout(1500) });
            if (isMounted && ipRes.ok) {
              markOnline(`http://${hn}:8000`);
              return;
            }
          } catch (e) {
            // IP unavailable
          }
        }
      }

      // 2. Try Remote Production Domains over HTTPS (or Cloudflare Tunnel)
      const candidateDomains = [
        'https://api.brettstehouwer.live',
        'https://ai-bs.brettstehouwer.live'
      ];

      for (const domain of candidateDomains) {
        try {
          const res = await fetch(`${domain}/api/health`, { signal: AbortSignal.timeout(2500) });
          if (isMounted && res.ok) {
            markOnline(domain);
            return;
          }
        } catch (e) {
          // Fallback domain
        }
      }

      // 2.5 Try LAN candidate if on HTTP
      if (!isHttps) {
        for (const lanIp of ['http://192.168.4.92:8000', 'http://100.104.31.50:8000']) {
          try {
            const lanRes = await fetch(`${lanIp}/api/health`, { signal: AbortSignal.timeout(1500) });
            if (isMounted && lanRes.ok) {
              markOnline(lanIp);
              return;
            }
          } catch (e) {}
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
