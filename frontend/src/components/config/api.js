let currentApiBase = 'https://api.brettstehouwer.live';

export const isNativeMobile = () => {
  if (typeof window === 'undefined') return false;
  return !!(
    (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()) ||
    window.location.protocol === 'capacitor:' ||
    (window.location.origin && window.location.origin.includes('localhost') && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) ||
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  );
};

export const getApiBase = () => {
  if (typeof window !== 'undefined') {
    // 1. Local desktop PC dev (plain http://localhost or http://127.0.0.1) ALWAYS routes directly to local core
    if (window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      return 'http://127.0.0.1:8080';
    }

    // 2. Mobile devices (Capacitor APK, iPhone PWA, Mobile browsers) or HTTPS use Cloudflare Tunnel
    if (isNativeMobile() || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || window.location.protocol === 'https:') {
      return (currentApiBase && currentApiBase.startsWith('https://')) ? currentApiBase : 'https://api.brettstehouwer.live';
    }

    // 3. Local LAN IP directly
    if (/^\d+\.\d+\.\d+\.\d+$/.test(window.location.hostname)) {
      return `http://${window.location.hostname}:8080`;
    }
  }
  return 'http://127.0.0.1:8080';
};

export const setApiBase = (url) => {
  if (url) {
    currentApiBase = url;
  }
};

export default { getApiBase, setApiBase, isNativeMobile };
