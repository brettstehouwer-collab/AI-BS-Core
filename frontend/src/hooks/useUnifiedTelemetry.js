import { useState, useEffect } from 'react';
import { useSHMTelemetry } from './useSHMTelemetry';

export function useUnifiedTelemetry() {
  const shm = useSHMTelemetry();
  
  const [crypto, setCrypto] = useState(null);
  const [siteAnalytics, setSiteAnalytics] = useState(null);
  
  useEffect(() => {
    // Poll Crypto Bot
    const fetchCrypto = async () => {
      try {
        const res = await fetch(`https://api.brettstehouwer.live/api/proxy/8007/api/v1/telemetry`);
        if (res.ok) {
          const data = await res.json();
          setCrypto(data);
        }
      } catch (err) {
        // Silently fail if offline
      }
    };

    // Poll Site Analytics
    const fetchSiteAnalytics = async () => {
      try {
        const res = await fetch(`https://api.brettstehouwer.live/api/analytics/live_summary`);
        if (res.ok) {
          const data = await res.json();
          setSiteAnalytics(data);
        }
      } catch (err) {
        // Silently fail
      }
    };

    fetchCrypto();
    fetchSiteAnalytics();
    
    const interval = setInterval(() => {
      fetchCrypto();
      fetchSiteAnalytics();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  return {
    shm,
    crypto,
    siteAnalytics
  };
}
