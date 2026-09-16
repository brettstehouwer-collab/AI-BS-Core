/**
 * ═══════════════════════════════════════════════════════════════════════════
 * AI-BS Sovereign Client Telemetry & Active Visitor Sentinel
 * Site ID: aibs_dashboard | Target: https://ai-bs-dashboard.web.app/
 * ═══════════════════════════════════════════════════════════════════════════
 */

(function () {
  'use strict';

  if (typeof window === 'undefined') return;

  const SITE_ID = 'aibs_dashboard';
  const DOMAIN = window.location.hostname || 'ai-bs-dashboard.web.app';
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  const PRIMARY_API = isLocal ? 'http://127.0.0.1:8080' : 'https://api.brettstehouwer.live';
  const FALLBACK_API = 'https://api.brettstehouwer.live';

  // 1. Session Management
  function getOrCreateSessionId() {
    try {
      let sid = sessionStorage.getItem('aibs_telemetry_sid');
      if (!sid) {
        sid = 'sid_aibs_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now().toString(36);
        sessionStorage.setItem('aibs_telemetry_sid', sid);
      }
      return sid;
    } catch (e) {
      return 'sid_aibs_' + Date.now().toString(36);
    }
  }

  const SESSION_ID = getOrCreateSessionId();
  const PAGE_START_TIME = performance.now();
  let maxScrollPct = 0;
  let lastReportedDwell = 0;

  // 2. Hardware & Device Inspection
  function getGpuRenderer() {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (gl) {
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
          return gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || 'WebGL Supported';
        }
      }
    } catch (e) {}
    return 'WebGL Unsupported';
  }

  function getDeviceInfo() {
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection || {};
    return {
      screen_res: `${window.screen.width}x${window.screen.height}`,
      viewport_res: `${window.innerWidth}x${window.innerHeight}`,
      device_pixel_ratio: window.devicePixelRatio || 1.0,
      color_depth: window.screen.colorDepth || 24,
      dark_mode: window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Detroit',
      language: navigator.language || 'en-US',
      cpu_cores: navigator.hardwareConcurrency || 4,
      device_memory_gb: navigator.deviceMemory || 8,
      gpu_renderer: getGpuRenderer(),
      network_type: conn.effectiveType || '4g',
      downlink_mbps: conn.downlink || null,
      rtt_ms: conn.rtt || null,
      hls_supported: !!(document.createElement('video').canPlayType('application/vnd.apple.mpegurl'))
    };
  }

  // 3. Web Vitals & Performance Metrics
  let lcpValue = null;
  let clsValue = 0;

  if (typeof PerformanceObserver !== 'undefined') {
    try {
      const lcpObserver = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        if (lastEntry) lcpValue = Math.round(lastEntry.startTime);
      });
      lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) {}

    try {
      const clsObserver = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        }
      });
      clsObserver.observe({ type: 'layout-shift', buffered: true });
    } catch (e) {}
  }

  function getNavigationTimings() {
    const timings = {};
    try {
      const navEntries = performance.getEntriesByType('navigation');
      if (navEntries && navEntries.length > 0) {
        const nav = navEntries[0];
        timings.dns_ms = Math.round(nav.domainLookupEnd - nav.domainLookupStart);
        timings.ttfb_ms = Math.round(nav.responseStart - nav.requestStart);
        timings.dom_load_ms = Math.round(nav.domContentLoadedEventEnd - nav.startTime);
        timings.page_load_ms = Math.round(nav.loadEventEnd - nav.startTime);
      }
    } catch (e) {}
    return timings;
  }

  // 4. UTM & Referrer Parameters
  function getUtmParams() {
    try {
      const params = new URLSearchParams(window.location.search);
      return {
        utm_source: params.get('utm_source') || null,
        utm_medium: params.get('utm_medium') || null,
        utm_campaign: params.get('utm_campaign') || null
      };
    } catch (e) {
      return {};
    }
  }

  // 5. Beacon Dispatch Engine
  function dispatchBeacon(endpointPath, payload) {
    const dataStr = JSON.stringify(payload);
    const targetUrl = `${PRIMARY_API}${endpointPath}`;

    if (navigator.sendBeacon) {
      try {
        const blob = new Blob([dataStr], { type: 'application/json' });
        const success = navigator.sendBeacon(targetUrl, blob);
        if (success) return;
      } catch (e) {}
    }

    fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: dataStr,
      keepalive: true,
      mode: 'cors'
    }).catch(() => {
      if (PRIMARY_API !== FALLBACK_API) {
        fetch(`${FALLBACK_API}${endpointPath}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: dataStr,
          keepalive: true,
          mode: 'cors'
        }).catch(() => {});
      }
    });
  }

  // 6. Public Telemetry Method
  function sendPageView(eventType = 'pageview', customData = null) {
    const dwell = Math.round((performance.now() - PAGE_START_TIME) / 1000);
    const device = getDeviceInfo();
    const nav = getNavigationTimings();
    const utm = getUtmParams();

    const payload = {
      session_id: SESSION_ID,
      site_id: SITE_ID,
      domain: DOMAIN,
      page_path: window.location.pathname + window.location.hash,
      page_title: document.title || 'Stehouwer AI • Sovereign Mobile',
      referrer: document.referrer || 'Direct',
      event_type: eventType,
      dwell_time_sec: dwell,
      scroll_depth_pct: maxScrollPct,
      lcp_ms: lcpValue,
      cls_score: parseFloat(clsValue.toFixed(4)),
      event_data: customData || (localStorage.getItem('aibs_cached_user') ? 'authenticated_session' : 'visitor_active_presence'),
      ...device,
      ...nav,
      ...utm
    };

    dispatchBeacon('/api/analytics/track', payload);
  }

  // 7. Public User Login Notification Method
  function sendLoginNotification(userPayload) {
    if (!userPayload || !userPayload.email) return;

    const payload = {
      email: userPayload.email,
      displayName: userPayload.displayName || 'Authorized Admin',
      uid: userPayload.uid || '',
      photoURL: userPayload.photoURL || '',
      url: window.location.href,
      session_id: SESSION_ID,
      timestamp: new Date().toISOString(),
      event_type: 'user_login',
      device_info: {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        screen: `${window.screen.width}x${window.screen.height}`,
        gpu: getGpuRenderer()
      }
    };

    dispatchBeacon('/api/analytics/notify-login', payload);
  }

  // Expose on window for App.jsx & React components
  window.sendDashboardAnalyticsBeacon = sendPageView;
  window.sendDashboardLoginNotification = sendLoginNotification;

  // 8. Event Listeners (Pageview, Scroll, Visibility, Unload)
  window.addEventListener('scroll', () => {
    try {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight > 0) {
        const pct = Math.round((window.scrollY / scrollHeight) * 100);
        if (pct > maxScrollPct) maxScrollPct = Math.min(100, pct);
      }
    } catch (e) {}
  }, { passive: true });

  // Initial Beacon on Load
  if (document.readyState === 'complete') {
    setTimeout(() => sendPageView('pageview'), 1000);
  } else {
    window.addEventListener('load', () => {
      setTimeout(() => sendPageView('pageview'), 1000);
    });
  }

  // Route Change Listener for Single Page App
  window.addEventListener('popstate', () => sendPageView('navigation'));
  window.addEventListener('hashchange', () => sendPageView('navigation'));

  // Visibility / Dwell Update
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      sendPageView('visibility_hidden');
    }
  });

  window.addEventListener('beforeunload', () => {
    sendPageView('session_end');
  });

})();
