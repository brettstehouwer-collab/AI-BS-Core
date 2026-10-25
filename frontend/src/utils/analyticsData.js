// Private reads use the application's existing Firebase-token fetch interceptor.
export const emptyTrafficData = () => ({
  total_pageviews: 0, unique_visitors: 0, avg_dwell_time_sec: 0,
  scroll_completion_rate: 0, human_traffic_pct: 0,
  top_pages: [], top_referrers: [], geo_distribution: [], top_gpus: [],
  web_vitals: { lcp_ms: 0, cls_score: 0 },
  network_metrics: { avg_ttfb_ms: 0, avg_rtt_ms: 0, avg_downlink_mbps: 0, network_breakdown: [] },
  attribution_metrics: { top_sources: [], top_campaigns: [] },
  media_readiness: { hls_supported_pct: 0, live_stream_hits: 0 },
  client_diagnostics: { dark_mode_pct: 0, top_timezones: [] },
  recent_errors: [], form_abandonment_leads: [], heatmap_points: [], live_events: []
});

export const emptyApiData = () => ({
  total_security_events: 0, total_banned_ips: 0,
  security_events: [], active_ip_bans: [], live_stream: []
});

export async function loadAnalyticsSnapshot(baseUrl, site, { fetchImpl = globalThis.fetch, signal } = {}) {
  const base = baseUrl.replace(/\/$/, '');
  const timeout = AbortSignal.timeout(15000);
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout;
  const routes = [
    `/api/analytics/traffic-summary?site_id=${encodeURIComponent(site)}&limit=50`,
    '/api/analytics/traffic-summary?site_id=stehouwer_publishing&limit=1',
    '/api/analytics/traffic-summary?site_id=thesimplechef&limit=1',
    '/api/admin/security-telemetry',
    '/api/analytics/publishing-events'
  ];
  const data = await Promise.all(routes.map(async route => {
    const response = await fetchImpl(base + route, { signal: requestSignal, cache: 'no-store' });
    if (!response.ok) {
      const message = [401, 403].includes(response.status)
        ? 'Web analytics requires an authorized administrator session. Sign in again to continue.'
        : `Web analytics could not refresh (HTTP ${response.status}).`;
      throw Object.assign(new Error(message), { status: response.status });
    }
    return response.json();
  }));
  for (const traffic of data.slice(0, 3)) {
    if (!traffic || !Number.isFinite(traffic.total_pageviews) || traffic.total_pageviews < 0 ||
        !Number.isFinite(traffic.unique_visitors) || !Array.isArray(traffic.live_events)) {
      throw new Error('Invalid web traffic response.');
    }
  }
  if (!data[3] || !Number.isFinite(data[3].total_security_events) || !Number.isFinite(data[3].total_banned_ips) ||
      !Array.isArray(data[3].security_events) || !Array.isArray(data[3].active_ip_bans)) {
    throw new Error('Invalid API security response.');
  }
  if (!data[4] || !Array.isArray(data[4].events)) throw new Error('Invalid publishing security response.');
  return {
    trafficData: { ...emptyTrafficData(), ...data[0] },
    siteCounts: { stehouwer_publishing: data[1].total_pageviews, thesimplechef: data[2].total_pageviews },
    apiData: data[3], pubSecurityEvents: data[4].events
  };
}
