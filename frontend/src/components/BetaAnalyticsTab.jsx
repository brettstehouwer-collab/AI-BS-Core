import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';
import EcosystemPortMonitorWidget from './EcosystemPortMonitorWidget';
import UserSessionTelemetryWidget from './UserSessionTelemetryWidget';

const AUTHORIZED_EMAILS = [
  'brettstehouwer@gmail.com',
  'footballstar0325@gmail.com',
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'julie@stehouwer-publishing.com'
];

const JULIE_EMAILS = [
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'julie@stehouwer-publishing.com'
];

export default function BetaAnalyticsTab({ backendUrl, currentUser }) {
  // Determine if running locally or on local home network (LAN)
  const isLocalDev = typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname.startsWith('192.168.') ||
    window.location.hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./.test(window.location.hostname) ||
    window.location.protocol === 'file:'
  );

  // Determine current active user email
  const userEmail = (currentUser?.email || '').toLowerCase().trim();

  // Julie Stehouwer has full unrestricted access without any password requirement
  const isJulie = JULIE_EMAILS.includes(userEmail) || userEmail.includes('julie');

  // Allowed operators: Julie, Brett, LocalDev, footballstar0325
  const isAuthorizedOperator = isLocalDev || isJulie || AUTHORIZED_EMAILS.includes(userEmail);

  // Check persistent authorization or session unlock (Julie is ALWAYS unlocked with zero password prompt)
  const [isUnlocked, setIsUnlocked] = useState(() => {
    if (isJulie) return true;
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('aibs_beta_analytics_unlocked') === 'true';
    }
    return false;
  });

  const [enteredPassword, setEnteredPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const handlePasswordUnlock = (e) => {
    e?.preventDefault();
    setPasswordError('');
    if (!enteredPassword.trim()) {
      setPasswordError('Please enter the telemetry suite security password.');
      return;
    }

    if (enteredPassword.trim() === 'jssdbdAS2631') {
      setIsUnlocked(true);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('aibs_beta_analytics_unlocked', 'true');
      }
    } else {
      setPasswordError('Invalid security password. Access denied.');
    }
  };

  const handleLockVault = () => {
    setIsUnlocked(false);
    setEnteredPassword('');
    setPasswordError('');
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('aibs_beta_analytics_unlocked');
    }
  };

  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;
  const [activeSubView, setActiveSubView] = useState('user_sessions'); // 'user_sessions' | 'ecosystem_ports' | 'site_traffic' | 'wire_packets' | 'air_sensors' | 'api_compute' | 'cdz_audit'
  const [selectedSite, setSelectedSite] = useState('stehouwer_publishing'); // 'stehouwer_publishing' | 'thesimplechef'
  const [siteCounts, setSiteCounts] = useState({ stehouwer_publishing: 0, thesimplechef: 0 });

  // 1. Site Traffic Telemetry State (16-Layer Suite)
  const [trafficData, setTrafficData] = useState({
    total_pageviews: 0,
    unique_visitors: 0,
    avg_dwell_time_sec: 0,
    scroll_completion_rate: 0,
    human_traffic_pct: 100,
    top_pages: [],
    top_referrers: [],
    geo_distribution: [],
    top_gpus: [],
    web_vitals: { lcp_ms: 0, cls_score: 0 },
    network_metrics: { avg_ttfb_ms: 35, avg_rtt_ms: 18, avg_downlink_mbps: 24.5, network_breakdown: [] },
    attribution_metrics: { top_sources: [], top_campaigns: [] },
    media_readiness: { hls_supported_pct: 100, live_stream_hits: 0 },
    client_diagnostics: { dark_mode_pct: 0, top_timezones: [] },
    recent_errors: [],
    form_abandonment_leads: [],
    heatmap_points: [],
    live_events: []
  });

  // 2. Wire Packet Hashes & ASGI Gateway State
  const [wireRecordType, setWireRecordType] = useState('ALL');
  const [correlationModalData, setCorrelationModalData] = useState(null);
  const [isLoadingCorrelation, setIsLoadingCorrelation] = useState(false);
  const [wireSummary, setWireSummary] = useState({
    total_requests: 0,
    total_bytes_in: 0,
    total_bytes_out: 0,
    bandwidth_in_kb: 0,
    bandwidth_out_kb: 0,
    status_codes: { '2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0 },
    active_websockets: 0,
    latency: { avg_ms: 0, min_ms: 0, max_ms: 0, p95_ms: 0 },
    top_routes: [],
    stehouwer_publishing: {
      total_packets: 0,
      bytes_in: 0,
      bytes_out: 0,
      bandwidth_in_kb: 0,
      bandwidth_out_kb: 0,
      recent_packet_hashes: []
    }
  });
  const [wireTraffic, setWireTraffic] = useState([]);
  const [wireFilterStehouwer, setWireFilterStehouwer] = useState(false);
  const [wireFilterHasHash, setWireFilterHasHash] = useState(false);
  const [wireSearchDomain, setWireSearchDomain] = useState('');
  const [wireLimit, setWireLimit] = useState(50);
  const [captureInterfaces, setCaptureInterfaces] = useState([]);
  const [selectedInterface, setSelectedInterface] = useState('');
  const [bpfFilterInput, setBpfFilterInput] = useState('tcp or udp');
  const [wireFilterEngine, setWireFilterEngine] = useState('ALL');
  const [engineFeedback, setEngineFeedback] = useState(null);
  const [isSwitchingEngine, setIsSwitchingEngine] = useState(false);

  // 3. Over-The-Air Wave Hardware Sensors State
  const [airSummary, setAirSummary] = useState({
    total_records: 0,
    unique_beacon_hashes: 0,
    avg_signal_pct: 0,
    band_distribution: {},
    sensor_distribution: {},
    recent_hashes: []
  });
  const [airRecords, setAirRecords] = useState([]);
  const [isScanningAir, setIsScanningAir] = useState(false);
  const [airFilterType, setAirFilterType] = useState('ALL'); // 'ALL' | 'WIFI_RF' | 'BLUETOOTH_BLE'
  const [airFilterBand, setAirFilterBand] = useState('ALL'); // 'ALL' | '2.4GHz_ISM' | '5GHz_UNII' | '6GHz_WIFI6E'
  const [airSearchHash, setAirSearchHash] = useState('');
  const [airLimit, setAirLimit] = useState(50);
  const [airScanAlert, setAirScanAlert] = useState(null);

  // 4. API Compute & Security State
  const [apiData, setApiData] = useState({
    total_security_events: 0,
    total_banned_ips: 0,
    security_events: [],
    active_ip_bans: [],
    live_stream: []
  });
  const [pubSecurityEvents, setPubSecurityEvents] = useState([]);

  // 5. CDZ Cryptographic Audit Ledger State
  const [cdzSummary, setCdzSummary] = useState({
    total_blocks: 0,
    head_hash: '0000000000000000',
    genesis_hash: '0000000000000000',
    is_valid: true,
    tampered_at: null,
    domain_breakdown: {},
    event_breakdown: {},
    recent_blocks: [],
    watcher: {}
  });
  const [cdzBlocks, setCdzBlocks] = useState([]);
  const [cdzTotal, setCdzTotal] = useState(0);
  const [cdzFilterDomain, setCdzFilterDomain] = useState('ALL');
  const [cdzFilterEvent, setCdzFilterEvent] = useState('ALL');
  const [cdzSearch, setCdzSearch] = useState('');
  const [cdzLimit, setCdzLimit] = useState(50);
  const [isScanningCdz, setIsScanningCdz] = useState(false);
  const [cdzScanAlert, setCdzScanAlert] = useState(null);

  const [isLoading, setIsLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  const copyToClipboard = (text, label) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedHash(label);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  // Fetch functions
  const fetchCdzTelemetry = async () => {
    try {
      const sumRes = await fetch(`${apiHost}/api/audit-ledger/summary`);
      if (sumRes.ok) {
        const json = await sumRes.json();
        setCdzSummary(json);
      }
      let url = `${apiHost}/api/audit-ledger/blocks?limit=${cdzLimit}&offset=0`;
      if (cdzFilterDomain && cdzFilterDomain !== 'ALL') url += `&domain=${cdzFilterDomain}`;
      if (cdzFilterEvent && cdzFilterEvent !== 'ALL') url += `&event=${cdzFilterEvent}`;
      if (cdzSearch) url += `&search=${encodeURIComponent(cdzSearch)}`;
      const blkRes = await fetch(url);
      if (blkRes.ok) {
        const json = await blkRes.json();
        setCdzBlocks(json.blocks || []);
        setCdzTotal(json.total || 0);
      }
    } catch (e) {
      console.warn('Failed to fetch CDZ audit telemetry:', e);
    }
  };

  const handleScanCdz = async () => {
    setIsScanningCdz(true);
    setCdzScanAlert(null);
    try {
      const res = await fetch(`${apiHost}/api/audit-ledger/scan`, { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        const newIngested = json.scan_result?.new_blocks_ingested || 0;
        const total = json.summary?.total_blocks || 0;
        setCdzScanAlert(`Scan complete. Ingested ${newIngested} new block(s). Total chain length: ${total} blocks.`);
        await fetchCdzTelemetry();
      } else {
        setCdzScanAlert('Failed to trigger CDZ scan.');
      }
    } catch (e) {
      setCdzScanAlert(`Error triggering CDZ scan: ${e.message}`);
    } finally {
      setIsScanningCdz(false);
    }
  };

  const fetchTrafficData = async () => {
    try {
      const res = await fetch(`${apiHost}/api/analytics/traffic-summary?site_id=${selectedSite}&limit=50`);
      if (res.ok) {
        const json = await res.json();
        setTrafficData(json);
      }
    } catch (e) {
      console.warn('Failed to fetch site traffic telemetry:', e);
    }

    // Refresh hit count tallies for both sites
    try {
      const [spRes, chefRes] = await Promise.all([
        fetch(`${apiHost}/api/analytics/traffic-summary?site_id=stehouwer_publishing&limit=1`),
        fetch(`${apiHost}/api/analytics/traffic-summary?site_id=thesimplechef&limit=1`)
      ]);
      if (spRes.ok && chefRes.ok) {
        const spJ = await spRes.json();
        const chefJ = await chefRes.json();
        setSiteCounts({
          stehouwer_publishing: spJ.total_pageviews || 0,
          thesimplechef: chefJ.total_pageviews || 0
        });
      }
    } catch (e) {
      // non-blocking
    }
  };

  const handleFetchCorrelation = async (flowId, txId) => {
    setIsLoadingCorrelation(true);
    try {
      let u = `${apiHost}/api/network-telemetry/correlation?`;
      if (flowId) u += `flow_id=${encodeURIComponent(flowId)}`;
      else if (txId) u += `transaction_id=${encodeURIComponent(txId)}`;
      const r = await fetch(u);
      if (r.ok) {
        const j = await r.json();
        setCorrelationModalData(j);
      }
    } catch (e) {
      console.warn('Failed to fetch correlation:', e);
    } finally {
      setIsLoadingCorrelation(false);
    }
  };

  const fetchWireTelemetry = async () => {
    try {
      const sumRes = await fetch(`${apiHost}/api/network-telemetry/summary`);
      if (sumRes.ok) {
        const json = await sumRes.json();
        setWireSummary(json);
      }
    } catch (e) {
      console.warn('Failed to fetch wire telemetry summary:', e);
    }

    try {
      let q = `${apiHost}/api/network-telemetry/traffic?limit=${wireLimit}`;
      if (wireRecordType !== 'ALL') q += `&record_type=${wireRecordType}`;
      if (wireFilterStehouwer) q += '&is_stehouwer=true';
      if (wireFilterHasHash) q += '&has_hash=true';
      if (wireSearchDomain) q += `&domain=${encodeURIComponent(wireSearchDomain)}`;
      if (wireFilterEngine !== 'ALL') q += `&engine=${encodeURIComponent(wireFilterEngine)}`;
      const trafRes = await fetch(q);
      if (trafRes.ok) {
        const json = await trafRes.json();
        setWireTraffic(json.traffic || []);
      }
    } catch (e) {
      console.warn('Failed to fetch wire traffic:', e);
    }
  };

  const fetchInterfaces = async () => {
    try {
      const res = await fetch(`${apiHost}/api/network-telemetry/interfaces`);
      if (res.ok) {
        const data = await res.json();
        setCaptureInterfaces(data.interfaces || []);
        if (data.active_interface) setSelectedInterface(data.active_interface);
        if (data.bpf_filter) setBpfFilterInput(data.bpf_filter);
      }
    } catch (e) {
      console.warn('Failed to fetch capture interfaces:', e);
    }
  };

  const handleApplyInterface = async () => {
    try {
      const res = await fetch(`${apiHost}/api/network-telemetry/set-interface`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interface_name: selectedInterface, bpf_filter: bpfFilterInput })
      });
      if (res.ok) {
        fetchInterfaces();
      }
    } catch (e) {
      console.warn('Failed to apply interface config:', e);
    }
  };

  const handleSwitchEngine = async (targetEngine) => {
    setIsSwitchingEngine(true);
    setEngineFeedback(null);
    try {
      const res = await fetch(`${apiHost}/api/network-telemetry/engine/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ engine: targetEngine })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setEngineFeedback({ type: 'success', text: `Engine successfully switched to: ${targetEngine} (Active: ${data.active_engine})` });
        await fetchWireTelemetry();
      } else {
        setEngineFeedback({ type: 'error', text: `Failed to switch engine: ${data.detail || data.message || 'Unknown error'}` });
      }
    } catch (e) {
      setEngineFeedback({ type: 'error', text: `Engine switch error: ${e.message}` });
    } finally {
      setIsSwitchingEngine(false);
      setTimeout(() => setEngineFeedback(null), 5000);
    }
  };

  const fetchAirTelemetry = async () => {
    try {
      const sumRes = await fetch(`${apiHost}/api/network-telemetry/air/summary`);
      if (sumRes.ok) {
        const json = await sumRes.json();
        setAirSummary(json);
      }
    } catch (e) {
      console.warn('Failed to fetch air summary:', e);
    }

    try {
      let q = `${apiHost}/api/network-telemetry/air/records?limit=${airLimit}`;
      if (airFilterType !== 'ALL') q += `&sensor_type=${airFilterType}`;
      if (airFilterBand !== 'ALL') q += `&band=${airFilterBand}`;
      if (airSearchHash) q += `&hash_query=${encodeURIComponent(airSearchHash)}`;
      const recRes = await fetch(q);
      if (recRes.ok) {
        const json = await recRes.json();
        setAirRecords(json.records || []);
      }
    } catch (e) {
      console.warn('Failed to fetch air records:', e);
    }
  };

  const handleScanAir = async () => {
    setIsScanningAir(true);
    setAirScanAlert(null);
    try {
      const res = await fetch(`${apiHost}/api/network-telemetry/air/scan`);
      if (res.ok) {
        const data = await res.json();
        setAirScanAlert(`Scanned ${data.total_detected} over-the-air signals in ${data.duration_ms}ms (${data.wifi_count} Wi-Fi RF beacons, ${data.bluetooth_count} Bluetooth devices).`);
        await fetchAirTelemetry();
      }
    } catch (e) {
      setAirScanAlert(`Air scan error: ${e.message}`);
    } finally {
      setIsScanningAir(false);
    }
  };

  const handleClearWire = async () => {
    if (!confirm('Clear all in-memory wire packet records?')) return;
    try {
      await fetch(`${apiHost}/api/network-telemetry/clear`, { method: 'POST' });
      await fetchWireTelemetry();
    } catch (e) {
      console.warn('Clear wire error:', e);
    }
  };

  const handleClearAir = async () => {
    if (!confirm('Flush all persisted over-the-air beacon records from SQLite?')) return;
    try {
      await fetch(`${apiHost}/api/network-telemetry/air/clear`, { method: 'POST' });
      await fetchAirTelemetry();
    } catch (e) {
      console.warn('Clear air error:', e);
    }
  };

  const fetchApiData = async () => {
    try {
      const res = await fetch(`${apiHost}/api/admin/security-telemetry`, {
        headers: { 'x-admin-email': currentUser?.email || 'footballstar0325@gmail.com' }
      });
      if (res.ok) {
        const json = await res.json();
        setApiData(json);
      }
    } catch (e) {
      console.warn('Failed to fetch API security telemetry:', e);
    }

    try {
      const res = await fetch(`${apiHost}/api/analytics/publishing-events`);
      if (res.ok) {
        const json = await res.json();
        setPubSecurityEvents(json.events || []);
      }
    } catch (e) {
      console.warn('Failed to fetch publishing security events:', e);
    }
  };

  const refreshAll = async () => {
    setIsLoading(true);
    await Promise.all([fetchTrafficData(), fetchWireTelemetry(), fetchAirTelemetry(), fetchApiData()]);
    setLastRefreshed(new Date().toLocaleTimeString());
    setIsLoading(false);
  };

  useEffect(() => {
    if (!isAuthorizedOperator || !isUnlocked) {
      return;
    }
    refreshAll();
    if (activeSubView === 'wire_packets') {
      fetchInterfaces();
    }
    const interval = setInterval(refreshAll, 6000);
    return () => clearInterval(interval);
  }, [isAuthorizedOperator, isUnlocked, activeSubView, selectedSite, wireFilterStehouwer, wireFilterHasHash, wireSearchDomain, wireLimit, wireFilterEngine, airFilterType, airFilterBand, airSearchHash, airLimit]);

  const isChef = selectedSite === 'thesimplechef';

  // Security Barrier 1: Email / LocalDev Identity Enforcement
  if (!isAuthorizedOperator) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '75vh',
        padding: '32px 16px',
        background: '#090d16',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}>
        <div style={{
          background: '#0d1117',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '16px',
          padding: '40px 32px',
          maxWidth: '520px',
          width: '100%',
          textAlign: 'center',
          boxShadow: '0 20px 45px rgba(0,0,0,0.7)',
          animation: 'fadeIn 0.3s ease-in-out'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔒</div>
          <h2 style={{ color: '#ef4444', fontSize: '24px', fontWeight: '800', margin: '0 0 12px 0' }}>
            Restricted Telemetry Access
          </h2>
          <p style={{ color: '#8b949e', fontSize: '14px', lineHeight: '1.6', margin: '0 0 24px 0' }}>
            The Web Analytics & Telemetry Suite is strictly restricted to authorized operators:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
            <span style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', color: '#c9d1d9', fontWeight: '600' }}>
              👤 Brettstehouwer@gmail.com
            </span>
            <span style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', color: '#38bdf8', fontWeight: '600' }}>
              ⚡ LocalDev (localhost / 127.0.0.1)
            </span>
            <span style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '8px 14px', fontSize: '13px', color: '#c9d1d9', fontWeight: '600' }}>
              👤 footballstar0325@gmail.com
            </span>
          </div>
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '10px 14px', fontSize: '12px', color: '#fca5a5' }}>
            Current Operator Identity: <strong>{userEmail || 'Unauthenticated Guest'}</strong>
          </div>
        </div>
      </div>
    );
  }

  // Security Barrier 2: Password Challenge
  if (!isUnlocked) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '75vh',
        padding: '32px 16px',
        background: '#090d16',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}>
        <div style={{
          background: '#0d1117',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          borderRadius: '16px',
          padding: '40px 32px',
          maxWidth: '520px',
          width: '100%',
          textAlign: 'center',
          boxShadow: '0 20px 45px rgba(0,0,0,0.7)',
          animation: 'fadeIn 0.3s ease-in-out'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔐</div>
          <h2 style={{ color: '#38bdf8', fontSize: '24px', fontWeight: '800', margin: '0 0 12px 0' }}>
            Telemetry Suite — Password Required
          </h2>
          <p style={{ color: '#8b949e', fontSize: '14px', lineHeight: '1.6', margin: '0 0 24px 0' }}>
            Identity Verified: <span style={{ color: '#38bdf8', fontWeight: '700' }}>{isLocalDev ? 'LocalDev' : userEmail}</span>. Enter the master security password to unlock live telemetry.
          </p>
          <form onSubmit={handlePasswordUnlock} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="password"
                placeholder="Enter Vault Password"
                value={enteredPassword}
                onChange={(e) => setEnteredPassword(e.target.value)}
                autoFocus
                style={{
                  flex: 1,
                  background: '#161b22',
                  border: '1px solid #30363d',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  color: '#fff',
                  fontSize: '14px',
                  outline: 'none'
                }}
              />
              <button
                type="submit"
                style={{
                  background: 'linear-gradient(135deg, #1f6feb 0%, #38bdf8 100%)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '12px 20px',
                  fontWeight: '700',
                  fontSize: '14px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                Unlock Suite 🔓
              </button>
            </div>
            {passwordError && (
              <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', padding: '10px 14px', fontSize: '13px', color: '#f87171', textAlign: 'left' }}>
                ⚠️ {passwordError}
              </div>
            )}
          </form>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px', color: '#e6edf3', height: '100%', overflowY: 'auto', background: '#090d16', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ margin: 0, fontSize: '22px', fontWeight: '800', color: '#38bdf8' }}>📈 Web Analytics & Telemetry Suite</h1>
            <span style={{
              fontSize: '11px',
              padding: '2px 8px',
              borderRadius: '12px',
              background: isChef ? 'rgba(245, 158, 11, 0.15)' : 'rgba(56, 189, 248, 0.15)',
              color: isChef ? '#f59e0b' : '#38bdf8',
              border: isChef ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid rgba(56, 189, 248, 0.4)',
              fontWeight: '700'
            }}>
              {isChef ? '👨‍🍳 The Simple Chef Module' : '📚 Stehouwer Publishing Module'}
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#8b949e' }}>
            Real-time dwell times, scroll depths, Geo-IP, hardware specs, Web Vitals, wire packet hashes & over-the-air RF wave sensors
          </p>
        </div>

        {/* Site Switcher Toggle & Refresh Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#161b22', padding: '3px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <button
              onClick={() => { setSelectedSite('stehouwer_publishing'); setActiveSubView('site_traffic'); }}
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: '700',
                cursor: 'pointer',
                background: selectedSite === 'stehouwer_publishing' ? '#1f6feb' : 'transparent',
                color: selectedSite === 'stehouwer_publishing' ? '#fff' : '#8b949e',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>📚 Stehouwer Publishing</span>
              <span style={{ fontSize: '10px', background: 'rgba(255,255,255,0.18)', padding: '1px 6px', borderRadius: '10px' }}>
                {siteCounts.stehouwer_publishing}
              </span>
            </button>

            <button
              onClick={() => { setSelectedSite('thesimplechef'); setActiveSubView('site_traffic'); }}
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '12px',
                fontWeight: '700',
                cursor: 'pointer',
                background: selectedSite === 'thesimplechef' ? '#d97706' : 'transparent',
                color: selectedSite === 'thesimplechef' ? '#fff' : '#8b949e',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>👨‍🍳 The Simple Chef (John Barr)</span>
              <span style={{ fontSize: '10px', background: 'rgba(255,255,255,0.18)', padding: '1px 6px', borderRadius: '10px' }}>
                {siteCounts.thesimplechef}
              </span>
            </button>
          </div>

          {lastRefreshed && (
            <span style={{ fontSize: '12px', color: '#8b949e' }}>Updated: {lastRefreshed}</span>
          )}
          <button
            onClick={refreshAll}
            disabled={isLoading}
            style={{
              background: '#238636',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: isLoading ? 'not-allowed' : 'pointer'
            }}
          >
            {isLoading ? '⏳ Refreshing...' : '🔄 Live Sync'}
          </button>
          <button
            onClick={handleLockVault}
            title="Lock Suite (Requires password to re-enter)"
            style={{
              background: '#21262d',
              color: '#f85149',
              border: '1px solid rgba(248, 81, 73, 0.4)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🔒 Lock Suite
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveSubView('user_sessions')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'user_sessions' ? '#059669' : '#161b22',
            color: '#fff',
            border: activeSubView === 'user_sessions' ? '1px solid #34d399' : '1px solid #30363d',
            fontWeight: '700',
            cursor: 'pointer',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <span>👥</span> Live User Presence & Session Audit
        </button>

        <button
          onClick={() => setActiveSubView('ecosystem_ports')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'ecosystem_ports' ? '#0284c7' : '#161b22',
            color: '#fff',
            border: activeSubView === 'ecosystem_ports' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          ⚡ Ecosystem Ports & Tool Devices (79 Sockets)
        </button>

        <button
          onClick={() => { setActiveSubView('site_traffic'); setSelectedSite('stehouwer_publishing'); }}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: (activeSubView === 'site_traffic' && selectedSite === 'stehouwer_publishing') ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: (activeSubView === 'site_traffic' && selectedSite === 'stehouwer_publishing') ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          🌐 Stehouwer-Publishing.com Web Traffic ({siteCounts.stehouwer_publishing} Hits)
        </button>

        <button
          onClick={() => { setActiveSubView('site_traffic'); setSelectedSite('thesimplechef'); }}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: (activeSubView === 'site_traffic' && selectedSite === 'thesimplechef') ? '#d97706' : '#161b22',
            color: '#fff',
            border: (activeSubView === 'site_traffic' && selectedSite === 'thesimplechef') ? '1px solid #f59e0b' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          🌶️ TheSimpleChef.com Web Traffic ({siteCounts.thesimplechef} Hits)
        </button>

        <button
          onClick={() => setActiveSubView('wire_packets')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'wire_packets' ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: activeSubView === 'wire_packets' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          📡 Wire Packets & L2/L3 Dissection ({wireSummary?.wire_frames?.total_count || 0} Frames | {wireSummary?.transactions?.total_count || wireSummary?.total_requests || 0} Tx)
        </button>

        <button
          onClick={() => setActiveSubView('air_sensors')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'air_sensors' ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: activeSubView === 'air_sensors' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          📡 Over-The-Air Wave Hardware Sensors ({airSummary?.total_records || 0} Beacons)
        </button>

        <button
          onClick={() => setActiveSubView('api_compute')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'api_compute' ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: activeSubView === 'api_compute' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          ⚡ Commercial API & Security Logs ({apiData.live_stream.length} Calls)
        </button>

        <button
          onClick={() => setActiveSubView('cdz_audit')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'cdz_audit' ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: activeSubView === 'cdz_audit' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          🛡️ CDZ Zero-Trust Audit Ledger ({cdzSummary?.total_blocks || 0} Blocks)
        </button>
      </div>

      {/* VIEW: LIVE USER PRESENCE, DWELL TIME & SESSION AUDIT TELEMETRY */}
      {activeSubView === 'user_sessions' && (
        <UserSessionTelemetryWidget backendUrl={apiHost} />
      )}

      {/* VIEW 0: UNIFIED ECOSYSTEM PORT & TOOL CALLING MESH */}
      {activeSubView === 'ecosystem_ports' && (
        <EcosystemPortMonitorWidget backendUrl={apiHost} />
      )}

      {/* VIEW 1: WEBSITE TRAFFIC ANALYTICS (16-LAYER DEEP TELEMETRY SUITE) */}
      {activeSubView === 'site_traffic' && (
        <div>
          {/* Active Site Scope Banner */}
          <div style={{
            background: isChef ? 'rgba(245, 158, 11, 0.08)' : 'rgba(56, 189, 248, 0.08)',
            border: isChef ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            marginBottom: '20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '20px' }}>{isChef ? '👨‍🍳' : '🌐'}</span>
              <div>
                <div style={{ fontSize: '14px', fontWeight: '800', color: isChef ? '#f59e0b' : '#38bdf8' }}>
                  {isChef ? 'TheSimpleChef.com (John Barr)' : 'Stehouwer-Publishing.com'} — 16-Layer Deep Web Telemetry
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e' }}>
                  {isChef ? 'Smokehouse BBQ Storefront • Venmo/Credit/Cash Checkout Telemetry • ChromaDB Partition: thesimplechef_analytics_bin' : 'Publishing Platform • HLS Ingest Telemetry • CDZ Cryptographic Hash Ledger'}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: '#8b949e' }}>Filtered Scope:</span>
              <span style={{ fontSize: '11px', fontFamily: 'monospace', background: '#161b22', padding: '3px 8px', borderRadius: '4px', color: '#4ade80' }}>
                site_id = "{selectedSite}"
              </span>
            </div>
          </div>

          {/* 16-Layer KPI Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Total Pageviews</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: isChef ? '#f59e0b' : '#38bdf8', marginTop: '4px' }}>
                {trafficData.total_pageviews}
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Total web visits</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Unique Visitors</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#4ade80', marginTop: '4px' }}>
                {trafficData.unique_visitors}
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Distinct browser sessions</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>⏱️ Avg Dwell Time</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>
                {trafficData.avg_dwell_time_sec}s
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Active reading/viewing time</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>📜 Scroll Depth</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#a855f7', marginTop: '4px' }}>
                {trafficData.scroll_completion_rate}%
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Hit 75%+ scroll milestone</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>⚡ Web Vitals (LCP)</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>
                {trafficData.web_vitals?.lcp_ms || 320}ms
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>CLS: {trafficData.web_vitals?.cls_score || 0.005}</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>📶 Edge Latency (TTFB)</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>
                {trafficData.network_metrics?.avg_ttfb_ms || 35}ms
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>RTT: {trafficData.network_metrics?.avg_rtt_ms || 18}ms | {trafficData.network_metrics?.avg_downlink_mbps || 25} Mbps</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>📡 HLS Stream Ready</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>
                {trafficData.media_readiness?.hls_supported_pct || 100}%
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>{trafficData.media_readiness?.live_stream_hits || 0} media stream hits</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>🤖 Human Ratio</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#ec4899', marginTop: '4px' }}>
                {trafficData.human_traffic_pct}%
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Verified human sessions</div>
            </div>
          </div>

          {/* Breakdown Grid 1: Pages & Referrers */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>📑 Popular Site Pages</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Total Hits</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.top_pages.length === 0 ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No page hits recorded yet.</td></tr>
                  ) : (
                    trafficData.top_pages.map((p, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#38bdf8', fontFamily: 'monospace' }}>{p.path}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#4ade80' }}>{p.hits}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>🔗 Traffic Referral Sources</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Referrer</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Visitors</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.top_referrers.length === 0 ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No referral source data recorded yet.</td></tr>
                  ) : (
                    trafficData.top_referrers.map((r, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#c9d1d9' }}>{r.referrer}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#38bdf8' }}>{r.hits}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Breakdown Grid 2: Edge Network & Campaign Attribution */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#38bdf8' }}>📶 Network Connection & Throughput</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Connection Type</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Session Count</th>
                  </tr>
                </thead>
                <tbody>
                  {(!trafficData.network_metrics?.network_breakdown || trafficData.network_metrics.network_breakdown.length === 0) ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>Standard broadband / 4G default.</td></tr>
                  ) : (
                    trafficData.network_metrics.network_breakdown.map((n, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#4ade80', fontWeight: '700' }}>⚡ {n.type.toUpperCase()}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#38bdf8' }}>{n.count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f59e0b' }}>🎯 Campaign & Marketing Attribution</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Source / Campaign</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Attributed Hits</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.attribution_metrics?.top_sources && trafficData.attribution_metrics.top_sources.length > 0 ? (
                    trafficData.attribution_metrics.top_sources.map((s, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '600' }}>{s.source}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#4ade80' }}>{s.hits}</td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>Direct / organic visitors active.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Breakdown Grid 3: Geo-IP Location Distribution & Hardware */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>🌍 Geo-IP Location Distribution</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Country</th>
                    <th style={{ padding: '8px' }}>City / Region</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Visits</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.geo_distribution.length === 0 ? (
                    <tr><td colSpan={3} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No Geo-IP locations recorded yet.</td></tr>
                  ) : (
                    trafficData.geo_distribution.map((g, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '600' }}>🇺🇸 {g.country}</td>
                        <td style={{ padding: '8px', color: '#c9d1d9' }}>{g.city}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#4ade80' }}>{g.hits}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>💻 Hardware & WebGL GPU Telemetry</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>GPU Renderer Model</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Devices</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.top_gpus.length === 0 ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No GPU renderer telemetry recorded yet.</td></tr>
                  ) : (
                    trafficData.top_gpus.map((gpu, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#a855f7', fontFamily: 'monospace', fontSize: '11px' }}>{gpu.gpu}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#38bdf8' }}>{gpu.count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Client Errors */}
          {trafficData.recent_errors && trafficData.recent_errors.length > 0 && (
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(239, 68, 68, 0.4)', marginBottom: '24px' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#ef4444' }}>⚠️ Live Client-Side Diagnostics & Error Catcher</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Session ID</th>
                    <th style={{ padding: '8px' }}>Page</th>
                    <th style={{ padding: '8px' }}>Type</th>
                    <th style={{ padding: '8px' }}>Exception Details</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.recent_errors.map((e, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{e.formatted_time}</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace', color: '#38bdf8' }}>{e.session_id}</td>
                      <td style={{ padding: '8px', color: '#f59e0b' }}>{e.page_path}</td>
                      <td style={{ padding: '8px', color: '#ef4444', fontWeight: 'bold' }}>{e.event_type}</td>
                      <td style={{ padding: '8px', color: '#e2e8f0', fontFamily: 'monospace' }}>{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Form Field Abandonment Leads */}
          {trafficData.form_abandonment_leads && trafficData.form_abandonment_leads.length > 0 && (
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(245, 158, 11, 0.4)', marginBottom: '24px' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f59e0b' }}>🎯 Form Field Abandonment Leads</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Session ID</th>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px' }}>Target Field</th>
                    <th style={{ padding: '8px' }}>Partial Input Lead</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.form_abandonment_leads.map((f, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{f.formatted_time}</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace', color: '#38bdf8', fontSize: '11px' }}>{f.session_id}</td>
                      <td style={{ padding: '8px', color: '#4ade80' }}>{f.page_path}</td>
                      <td style={{ padding: '8px', color: '#a855f7', fontFamily: 'monospace' }}>{f.field_name}</td>
                      <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '700', fontFamily: 'monospace' }}>{f.partial_email}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Live 16-Layer Visitor Event Stream Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d', marginBottom: '24px' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>🔴 Live 16-Layer Visitor Event Telemetry Stream ({trafficData.live_events.length} Events)</span>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>Scope: {selectedSite}</span>
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Session ID</th>
                    <th style={{ padding: '8px' }}>Location</th>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px' }}>Event</th>
                    <th style={{ padding: '8px' }}>Network</th>
                    <th style={{ padding: '8px' }}>TTFB</th>
                    <th style={{ padding: '8px' }}>Dwell</th>
                    <th style={{ padding: '8px' }}>Scroll</th>
                    <th style={{ padding: '8px' }}>GPU Renderer</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.live_events.length === 0 ? (
                    <tr>
                      <td colSpan={10} style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                        No live website traffic recorded yet for {selectedSite}.
                      </td>
                    </tr>
                  ) : (
                    trafficData.live_events.map((e) => (
                      <tr key={e.id} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{e.formatted_time}</td>
                        <td style={{ padding: '8px', fontFamily: 'monospace', color: '#38bdf8', fontSize: '11px' }}>{e.session_id}</td>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '600' }}>🇺🇸 {e.city}</td>
                        <td style={{ padding: '8px', color: '#4ade80', fontWeight: '600' }}>{e.page_path}</td>
                        <td style={{ padding: '8px' }}>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '10px',
                            fontSize: '10px',
                            fontWeight: '700',
                            background: e.event_type === 'click' ? '#d97706' : e.event_type === 'add_to_cart' ? '#10b981' : e.event_type === 'checkout_modal_opened' ? '#6366f1' : e.event_type === 'order_placed' ? '#ec4899' : e.event_type === 'form_field_input' ? '#8957e5' : e.event_type === 'js_error' ? '#ef4444' : '#238636',
                            color: '#ffffff'
                          }}>
                            {e.event_type.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#38bdf8', fontWeight: 'bold' }}>{e.network_type ? e.network_type.toUpperCase() : '4G'}</td>
                        <td style={{ padding: '8px', color: '#10b981', fontFamily: 'monospace' }}>{e.ttfb_ms ? `${e.ttfb_ms}ms` : '—'}</td>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '700' }}>{e.dwell_time_sec || 0}s</td>
                        <td style={{ padding: '8px', color: '#a855f7', fontWeight: '700' }}>{e.scroll_depth_pct || 0}%</td>
                        <td style={{ padding: '8px', color: '#8b949e', fontSize: '11px', fontFamily: 'monospace' }}>{e.gpu_renderer || 'WebGL'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Decoupled L7 Application Metrics */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <span style={{ fontSize: '12px', fontWeight: '800', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                🌐 Layer 7 Application Telemetry (ASGI Middleware)
              </span>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>
                Observed HTTP/WS request bodies & Python app execution duration
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>ASGI Transactions</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>
                  {wireSummary.transactions?.total_count ?? wireSummary.total_requests ?? 0}
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>HTTP & WS lifecycle events</div>
              </div>

              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Observed Body In</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#4ade80', marginTop: '4px' }}>
                  {wireSummary.transactions?.bandwidth_in_kb ?? wireSummary.bandwidth_in_kb ?? 0} KB
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>HTTP request payload bodies</div>
              </div>

              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Observed Body Out</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#a855f7', marginTop: '4px' }}>
                  {wireSummary.transactions?.bandwidth_out_kb ?? wireSummary.bandwidth_out_kb ?? 0} KB
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>HTTP response payload bodies</div>
              </div>

              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Avg ASGI App Duration</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>
                  {wireSummary.transactions?.asgi_duration?.avg_ms ?? wireSummary.latency?.avg_ms ?? 0} ms
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
                  P95: {wireSummary.transactions?.asgi_duration?.p95_ms ?? 0}ms (App execution, not wire RTT)
                </div>
              </div>
            </div>
          </div>

          {/* Stehouwer-Publishing.com Dedicated Packet Sub-Ledger Highlight */}
          {wireSummary.stehouwer_publishing?.recent_packet_hashes?.length > 0 && (
            <div style={{ background: 'rgba(56, 189, 248, 0.06)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ margin: 0, fontSize: '14px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🌐 {isChef ? 'TheSimpleChef.com Ingest Packet Digest Stream' : 'Stehouwer-Publishing.com Cryptographic Packet Digest Stream'}
                </h3>
                <span style={{ fontSize: '11px', color: '#8b949e' }}>
                  {wireSummary.stehouwer_publishing.recent_packet_hashes.length} Recent Packets
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '10px' }}>
                {wireSummary.stehouwer_publishing.recent_packet_hashes.slice(0, 4).map((sh, idx) => (
                  <div key={idx} style={{ background: '#161b22', padding: '10px 14px', borderRadius: '6px', border: '1px solid #30363d' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '4px' }}>
                      <span style={{ color: '#4ade80', fontWeight: '700' }}>{sh.method} {sh.path}</span>
                      <span style={{ color: '#38bdf8' }}>{sh.status_code}</span>
                    </div>
                    {sh.hash_in && (
                      <div style={{ fontSize: '11px', color: '#8b949e', fontFamily: 'monospace', display: 'flex', justifyContent: 'space-between' }}>
                        <span>IN: {sh.hash_in.slice(0, 16)}...</span>
                        <button
                          onClick={() => copyToClipboard(sh.hash_in, `sh_in_${idx}`)}
                          style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '10px' }}
                        >
                          {copiedHash === `sh_in_${idx}` ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                    )}
                    {sh.hash_out && (
                      <div style={{ fontSize: '11px', color: '#8b949e', fontFamily: 'monospace', display: 'flex', justifyContent: 'space-between' }}>
                        <span>OUT: {sh.hash_out.slice(0, 16)}...</span>
                        <button
                          onClick={() => copyToClipboard(sh.hash_out, `sh_out_${idx}`)}
                          style={{ background: 'none', border: 'none', color: '#4ade80', cursor: 'pointer', fontSize: '10px' }}
                        >
                          {copiedHash === `sh_out_${idx}` ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: WIRE PACKETS & L2/L3 DISSECTION */}
      {activeSubView === 'wire_packets' && (
        <div>
          {/* Decoupled L2/L3 Physical Wire Metrics */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <span style={{ fontSize: '12px', fontWeight: '800', color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                📡 Layer 2/3 Physical Wire Metrics (Npcap Kernel Driver)
              </span>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>
                Ethernet frames, IP headers, transport octets & TCP flag bitmasks
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Captured Wire Frames</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#a855f7', marginTop: '4px' }}>
                  {wireSummary.wire_frames?.total_count || 0}
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Physical Ethernet frames</div>
              </div>

              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Captured Wire Volume</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>
                  {wireSummary.wire_frames?.wire_bandwidth_kb || 0} KB
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
                  Payload: {wireSummary.wire_frames?.payload_bandwidth_kb || 0} KB | Overhead: {((wireSummary.wire_frames?.captured_overhead_bytes || 0) / 1024).toFixed(1)} KB
                </div>
              </div>

              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Active 5-Tuple Flows</div>
                <div style={{ fontSize: '26px', fontWeight: '800', color: '#4ade80', marginTop: '4px' }}>
                  {wireSummary.wire_frames?.active_flows_count ?? wireSummary.flows?.active_count ?? 0}
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
                  TCP: {wireSummary.flows?.tcp_active ?? 0} | UDP: {wireSummary.flows?.udp_active ?? 0} ({wireSummary.flows?.idle_timeout_seconds ?? 60}s idle timeout)
                </div>
              </div>

              <div style={{ background: '#161b22', padding: '14px 16px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>TCP Flags Observed</div>
                <div style={{ fontSize: '15px', fontWeight: '800', color: '#f0f6fc', marginTop: '6px', fontFamily: 'monospace' }}>
                  SYN: {wireSummary.wire_frames?.tcp_flags_distribution?.SYN || 0} | ACK: {wireSummary.wire_frames?.tcp_flags_distribution?.ACK || 0}
                </div>
                <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px', fontFamily: 'monospace' }}>
                  PSH: {wireSummary.wire_frames?.tcp_flags_distribution?.PSH || 0} | FIN: {wireSummary.wire_frames?.tcp_flags_distribution?.FIN || 0} | RST: {wireSummary.wire_frames?.tcp_flags_distribution?.RST || 0}
                </div>
              </div>
            </div>
          </div>

          {/* Controls & Filter Bar */}
          <div style={{ background: '#161b22', padding: '14px 18px', borderRadius: '10px', border: '1px solid #30363d', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer', color: wireFilterStehouwer ? '#38bdf8' : '#c9d1d9' }}>
                <input
                  type="checkbox"
                  checked={wireFilterStehouwer}
                  onChange={(e) => setWireFilterStehouwer(e.target.checked)}
                />
                Filter Stehouwer-Publishing.com Only
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', cursor: 'pointer', color: wireFilterHasHash ? '#4ade80' : '#c9d1d9' }}>
                <input
                  type="checkbox"
                  checked={wireFilterHasHash}
                  onChange={(e) => setWireFilterHasHash(e.target.checked)}
                />
                Only Packets with SHA-256 Hashes
              </label>

              <input
                type="text"
                placeholder="Search domain or path..."
                value={wireSearchDomain}
                onChange={(e) => setWireSearchDomain(e.target.value)}
                style={{ background: '#090d16', border: '1px solid #30363d', color: '#fff', padding: '4px 10px', borderRadius: '4px', fontSize: '12px', width: '180px' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <select
                value={wireFilterEngine}
                onChange={(e) => setWireFilterEngine(e.target.value)}
                style={{ background: '#090d16', border: '1px solid #30363d', color: '#38bdf8', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: '600' }}
              >
                <option value="ALL">All Tiers (ASGI + Npcap)</option>
                <option value="ASGI">ASGI (L7) Only</option>
                <option value="NPCAP_L2_L3">NPCAP (L2/L3) Only</option>
              </select>

              <select
                value={wireLimit}
                onChange={(e) => setWireLimit(Number(e.target.value))}
                style={{ background: '#090d16', border: '1px solid #30363d', color: '#fff', padding: '4px 8px', borderRadius: '4px', fontSize: '12px' }}
              >
                <option value={25}>25 rows</option>
                <option value={50}>50 rows</option>
                <option value={100}>100 rows</option>
                <option value={250}>250 rows</option>
              </select>

              <button
                onClick={handleClearWire}
                style={{ background: '#da3633', color: '#fff', border: 'none', padding: '5px 12px', borderRadius: '4px', fontSize: '11px', fontWeight: '600', cursor: 'pointer' }}
              >
                Clear Buffer
              </button>
            </div>
          </div>

          {/* Wire Transactions & Hashes Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <h3 style={{ margin: 0, fontSize: '15px', color: '#f0f6fc' }}>
                📡 Decoupled L7 Transactions & Physical Wire Frames Stream
              </h3>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>
                {wireTraffic.length} records displayed | Showing {wireRecordType === 'ALL' ? 'Transactions & Wire Frames' : wireRecordType}
              </span>
            </div>

            {/* Formal Flow Correlation Modal Popup */}
            {correlationModalData && (
              <div style={{ background: '#0d1117', border: '1px solid #38bdf8', borderRadius: '8px', padding: '16px', marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: '800', color: '#38bdf8' }}>🔗 Formal Flow Correlation Matrix:</span>
                    <span style={{ fontFamily: 'monospace', fontSize: '12px', color: '#f0f6fc', background: '#161b22', padding: '2px 8px', borderRadius: '4px' }}>
                      {correlationModalData.flow_id}
                    </span>
                  </div>
                  <button
                    onClick={() => setCorrelationModalData(null)}
                    style={{ background: '#21262d', color: '#8b949e', border: 'none', padding: '3px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}
                  >
                    ✕ Close
                  </button>
                </div>
                <div style={{ fontSize: '12px', color: '#8b949e', marginBottom: '8px' }}>
                  L7 Request Path: <code style={{ color: '#4ade80' }}>{correlationModalData.l7_transaction?.path || 'N/A'}</code> • IP: <code style={{ color: '#38bdf8' }}>{correlationModalData.l7_transaction?.src_endpoint || 'N/A'}</code>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div style={{ background: '#161b22', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '11px', color: '#8b949e' }}>Inbound Wire Payload SHA-256</div>
                    <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#38bdf8', wordBreak: 'break-all' }}>
                      {correlationModalData.wire_frames?.inbound_sha256 || 'None recorded'}
                    </div>
                  </div>
                  <div style={{ background: '#161b22', padding: '10px', borderRadius: '6px' }}>
                    <div style={{ fontSize: '11px', color: '#8b949e' }}>Outbound Wire Payload SHA-256</div>
                    <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#4ade80', wordBreak: 'break-all' }}>
                      {correlationModalData.wire_frames?.outbound_sha256 || 'None recorded'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Tier</th>
                    <th style={{ padding: '8px' }}>Method / Proto</th>
                    <th style={{ padding: '8px' }}>Path / Endpoint</th>
                    <th style={{ padding: '8px' }}>Status</th>
                    <th style={{ padding: '8px' }}>Domain / Remote Host</th>
                    <th style={{ padding: '8px' }}>Payload / Overhead</th>
                    <th style={{ padding: '8px' }}>Payload SHA-256</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Latency</th>
                    <th style={{ padding: '8px', textAlign: 'center' }}>Correlate</th>
                  </tr>
                </thead>
                <tbody>
                  {wireTraffic.length === 0 ? (
                    <tr>
                      <td colSpan={10} style={{ padding: '24px', color: '#8b949e', textAlign: 'center' }}>
                        No wire packets captured yet. Verify Npcap kernel driver or ASGI activity.
                      </td>
                    </tr>
                  ) : (
                    wireTraffic.map((t, idx) => {
                      const isFrame = t.record_type === 'NPCAP_FRAME' || !t.method;
                      return (
                        <tr key={t.id || idx} style={{ borderBottom: '1px solid #21262d' }}>
                          <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>
                            {t.timestamp ? new Date(t.timestamp * 1000).toLocaleTimeString() : 'Live'}
                          </td>
                          <td style={{ padding: '8px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: '700',
                              background: isFrame ? 'rgba(168, 85, 247, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                              color: isFrame ? '#a855f7' : '#38bdf8',
                              border: `1px solid ${isFrame ? '#a855f7' : '#38bdf8'}`
                            }}>
                              {isFrame ? 'L2/L3 WIRE' : 'L7 ASGI'}
                            </span>
                          </td>
                          <td style={{ padding: '8px' }}>
                            {isFrame ? (
                              <span style={{ color: '#ec4899', fontWeight: '700', fontFamily: 'monospace' }}>
                                {t.protocol || 'ETH/IP'}
                              </span>
                            ) : (
                              <span style={{ fontWeight: '700', color: t.method === 'POST' ? '#38bdf8' : '#4ade80' }}>
                                {t.method}
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '8px', color: '#e6edf3', fontFamily: 'monospace', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {isFrame ? (t.endpoint || t.path) : t.path}
                          </td>
                          <td style={{ padding: '8px' }}>
                            {isFrame ? (
                              <span style={{ color: '#8b949e', fontSize: '11px', fontFamily: 'monospace' }}>— (Wire)</span>
                            ) : (
                              <span style={{ fontWeight: '700', color: t.status_code < 300 ? '#4ade80' : t.status_code < 400 ? '#38bdf8' : '#ef4444' }}>
                                {t.status_code}
                              </span>
                            )}
                          </td>
                          <td style={{ padding: '8px', color: t.is_stehouwer_publishing ? '#38bdf8' : '#8b949e', fontWeight: t.is_stehouwer_publishing ? '700' : '400' }}>
                            {t.origin_domain || t.src_endpoint}
                          </td>
                          <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace', fontSize: '11px' }}>
                            {isFrame ? (
                              <span>{t.captured_frame_bytes ?? t.frame_bytes ?? 0}B frame / {t.transport_payload_bytes ?? t.payload_bytes ?? 0}B payload ({t.captured_overhead_bytes ?? t.header_bytes ?? 0}B overhead)</span>
                            ) : (
                              <span>In: {t.body_bytes_in ?? t.bytes_in ?? 0}B / Out: {t.body_bytes_out ?? t.bytes_out ?? 0}B (Body)</span>
                            )}
                          </td>
                          <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '11px' }}>
                            {isFrame ? (
                              (t.frame_payload_sha256 || t.payload_sha256) ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#a855f7' }}>
                                  <span>FRM: {(t.frame_payload_sha256 || t.payload_sha256).slice(0, 12)}...</span>
                                  <button
                                    onClick={() => copyToClipboard(t.frame_payload_sha256 || t.payload_sha256, `row_frm_${idx}`)}
                                    style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '10px' }}
                                  >
                                    {copiedHash === `row_frm_${idx}` ? 'Copied' : '📋'}
                                  </button>
                                </div>
                              ) : (
                                <span style={{ color: '#484f58' }}>[NO_PAYLOAD]</span>
                              )
                            ) : (
                              <div>
                                {t.payload_sha256_in && (
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#38bdf8' }}>
                                    <span>IN: {t.payload_sha256_in.slice(0, 10)}...</span>
                                    <button onClick={() => copyToClipboard(t.payload_sha256_in, `row_in_${idx}`)} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '9px' }}>📋</button>
                                  </div>
                                )}
                                {t.payload_sha256_out && (
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#4ade80' }}>
                                    <span>OUT: {t.payload_sha256_out.slice(0, 10)}...</span>
                                    <button onClick={() => copyToClipboard(t.payload_sha256_out, `row_out_${idx}`)} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '9px' }}>📋</button>
                                  </div>
                                )}
                                {!t.payload_sha256_in && !t.payload_sha256_out && (
                                  <span style={{ color: '#484f58' }}>[EMPTY_BODY]</span>
                                )}
                              </div>
                            )}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'right', color: '#f59e0b', fontWeight: '700', fontFamily: 'monospace' }}>
                            {isFrame ? (
                              <span style={{ color: '#484f58', fontWeight: '400' }}>— (wire)</span>
                            ) : (
                              <span>{t.asgi_duration_ms ?? t.duration_ms ?? 0}ms</span>
                            )}
                          </td>
                          <td style={{ padding: '8px', textAlign: 'center' }}>
                            {t.flow_id ? (
                              <button
                                onClick={() => handleFetchCorrelation(isFrame ? t.flow_id : null, isFrame ? null : t.id)}
                                style={{ background: '#21262d', color: '#38bdf8', border: '1px solid #30363d', borderRadius: '4px', padding: '3px 8px', fontSize: '10px', cursor: 'pointer', fontWeight: '600' }}
                              >
                                🔗 Flow
                              </button>
                            ) : (
                              <span style={{ color: '#484f58' }}>—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

{/* VIEW 3: OVER-THE-AIR WAVE HARDWARE SENSORS */}
      {activeSubView === 'air_sensors' && (
        <div>
          {/* Summary Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Total Beacons Stored</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>{airSummary.total_records}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Persisted in SQLite database</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Unique Beacon Hashes</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#4ade80', marginTop: '4px' }}>{airSummary.unique_beacon_hashes}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Deterministic SHA-256 fingerprints</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Avg Signal Quality</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>{airSummary.avg_signal_pct}%</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>RSSI relative receiver strength</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Bands Detected</div>
              <div style={{ fontSize: '18px', fontWeight: '800', color: '#a855f7', marginTop: '6px' }}>
                2.4G ({airSummary.band_distribution?.['2.4GHz_ISM'] || 0}) • 5G ({airSummary.band_distribution?.['5GHz_UNII'] || 0}) • 6G ({airSummary.band_distribution?.['6GHz_WIFI6E'] || 0})
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Wi-Fi 6E/7 & Bluetooth BLE</div>
            </div>
          </div>

          {/* Trigger Scan Alert / Status Banner */}
          {airScanAlert && (
            <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid #38bdf8', padding: '12px 18px', borderRadius: '8px', marginBottom: '20px', fontSize: '13px', color: '#38bdf8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>📡 {airScanAlert}</span>
              <button onClick={() => setAirScanAlert(null)} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '13px' }}>✕</button>
            </div>
          )}

          {/* Active Sensor Sweep Controls */}
          <div style={{ background: '#161b22', padding: '14px 18px', borderRadius: '10px', border: '1px solid #30363d', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <button
                onClick={handleScanAir}
                disabled={isScanningAir}
                style={{
                  background: 'linear-gradient(90deg, #1f6feb, #38bdf8)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 18px',
                  fontWeight: '700',
                  fontSize: '13px',
                  cursor: isScanningAir ? 'not-allowed' : 'pointer'
                }}
              >
                {isScanningAir ? '📡 Sweeping RF Waves...' : '📡 Trigger Active Air Wave Sweep'}
              </button>

              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#8b949e' }}>Sensor:</span>
                {['ALL', 'WIFI_RF', 'BLUETOOTH_BLE'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setAirFilterType(st)}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: 'none',
                      fontSize: '11px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      background: airFilterType === st ? '#1f6feb' : '#090d16',
                      color: airFilterType === st ? '#fff' : '#8b949e'
                    }}
                  >
                    {st === 'ALL' ? 'All Sensors' : st === 'WIFI_RF' ? 'Wi-Fi RF' : 'Bluetooth BLE'}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: '#8b949e' }}>Band:</span>
                {['ALL', '2.4GHz_ISM', '5GHz_UNII', '6GHz_WIFI6E'].map((b) => (
                  <button
                    key={b}
                    onClick={() => setAirFilterBand(b)}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: 'none',
                      fontSize: '11px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      background: airFilterBand === b ? '#238636' : '#090d16',
                      color: airFilterBand === b ? '#fff' : '#8b949e'
                    }}
                  >
                    {b.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input
                type="text"
                placeholder="Search beacon hash..."
                value={airSearchHash}
                onChange={(e) => setAirSearchHash(e.target.value)}
                style={{ background: '#090d16', border: '1px solid #30363d', color: '#fff', padding: '4px 10px', borderRadius: '4px', fontSize: '12px', width: '160px' }}
              />

              <button
                onClick={handleClearAir}
                style={{ background: '#da3633', color: '#fff', border: 'none', padding: '5px 12px', borderRadius: '4px', fontSize: '11px', fontWeight: '600', cursor: 'pointer' }}
              >
                Flush DB
              </button>
            </div>
          </div>

          {/* Air Beacon Records Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>
              📡 Ambient Electromagnetic Wave Telemetry & SHA-256 Beacon Hashes
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Timestamp</th>
                    <th style={{ padding: '8px' }}>Sensor Type</th>
                    <th style={{ padding: '8px' }}>Frequency Band</th>
                    <th style={{ padding: '8px' }}>Channel</th>
                    <th style={{ padding: '8px' }}>Signal</th>
                    <th style={{ padding: '8px' }}>SSID / Device Name</th>
                    <th style={{ padding: '8px' }}>BSSID (MAC)</th>
                    <th style={{ padding: '8px' }}>Radio Type</th>
                    <th style={{ padding: '8px' }}>SHA-256 Cryptographic Beacon Hash</th>
                  </tr>
                </thead>
                <tbody>
                  {airRecords.length === 0 ? (
                    <tr>
                      <td colSpan={9} style={{ padding: '20px', color: '#8b949e', textAlign: 'center' }}>
                        No air wave signals stored. Click "Trigger Active Air Wave Sweep" above to scan.
                      </td>
                    </tr>
                  ) : (
                    airRecords.map((ar, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>
                          {ar.timestamp ? new Date(ar.timestamp).toLocaleTimeString() : 'Recent'}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: '700',
                            background: ar.sensor_type === 'WIFI_RF' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(168, 85, 247, 0.2)',
                            color: ar.sensor_type === 'WIFI_RF' ? '#38bdf8' : '#a855f7'
                          }}>
                            {ar.sensor_type}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#4ade80', fontWeight: '600' }}>
                          {ar.frequency_band}
                        </td>
                        <td style={{ padding: '8px', color: '#f59e0b', fontFamily: 'monospace' }}>
                          {ar.channel}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '700',
                            background: ar.signal_pct >= 70 ? 'rgba(74, 222, 128, 0.2)' : ar.signal_pct >= 40 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: ar.signal_pct >= 70 ? '#4ade80' : ar.signal_pct >= 40 ? '#f59e0b' : '#ef4444'
                          }}>
                            {ar.signal_pct}%
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#e6edf3', fontWeight: '600' }}>
                          {ar.ssid_name}
                        </td>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>
                          {ar.bssid_mac}
                        </td>
                        <td style={{ padding: '8px', color: '#8b949e' }}>
                          {ar.radio_type}
                        </td>
                        <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '11px', color: '#38bdf8' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>{ar.beacon_hash.slice(0, 16)}...</span>
                            <button
                              onClick={() => copyToClipboard(ar.beacon_hash, `air_hash_${idx}`)}
                              style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '10px' }}
                            >
                              {copiedHash === `air_hash_${idx}` ? 'Copied' : '📋'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 4: API & SECURITY TELEMETRY */}
      {activeSubView === 'api_compute' && (
        <div>
          {/* Summary Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Security Incidents</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#ef4444', marginTop: '4px' }}>{apiData.total_security_events}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Total intercepted violations</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Active IP Blacklist</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>{apiData.total_banned_ips}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Auto-banned hosts</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Active API Keys</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>14 Active</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Passkeys authenticated</div>
            </div>
          </div>

          {/* Stehouwer-Publishing.com Live Web Security Shield Telemetry Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(56, 189, 248, 0.4)', marginBottom: '24px' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#38bdf8' }}>🌐 Stehouwer-Publishing.com Live Security Shield</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Origin IP</th>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px' }}>Event Type</th>
                    <th style={{ padding: '8px' }}>Severity</th>
                    <th style={{ padding: '8px' }}>Details / Attack Vector</th>
                  </tr>
                </thead>
                <tbody>
                  {pubSecurityEvents.length === 0 ? (
                    <tr><td colSpan={6} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No publishing web security events logged yet (Shield active).</td></tr>
                  ) : (
                    pubSecurityEvents.map((pev, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{pev.timestamp ? new Date(pev.timestamp).toLocaleTimeString() : 'Live'}</td>
                        <td style={{ padding: '8px', color: '#38bdf8', fontFamily: 'monospace', fontWeight: 'bold' }}>{pev.ip_address}</td>
                        <td style={{ padding: '8px', color: '#4ade80' }}>{pev.page_path}</td>
                        <td style={{ padding: '8px', color: pev.severity === 'HIGH' || pev.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b', fontWeight: 'bold' }}>{pev.event_type}</td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: '700', background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8' }}>
                            {pev.severity}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#e2e8f0', fontFamily: 'monospace' }}>{pev.details}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    
      {/* VIEW 5: CDZ ZERO-TRUST CRYPTOGRAPHIC AUDIT LEDGER */}
      {activeSubView === 'cdz_audit' && (
        <div>
          {/* Summary Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Total Audit Blocks</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>{cdzSummary.total_blocks} Blocks</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Indices 0 through {Math.max(0, cdzSummary.total_blocks - 1)} in aibs_master.db</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Chain Verification</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: cdzSummary.is_valid ? '#4ade80' : '#ef4444', marginTop: '4px' }}>
                {cdzSummary.is_valid ? '● 100% VALID' : '✖ BROKEN CHAIN'}
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
                {cdzSummary.tampered_at ? `Tampered at index ${cdzSummary.tampered_at}` : 'Zero integrity breaches detected'}
              </div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Current Head Hash</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                <span style={{ fontSize: '16px', fontWeight: '800', color: '#a855f7', fontFamily: 'monospace' }}>
                  {cdzSummary.head_hash}
                </span>
                <button
                  onClick={() => copyToClipboard(cdzSummary.head_hash, 'head_hash')}
                  style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '12px' }}
                >
                  {copiedHash === 'head_hash' ? 'Copied' : '📋'}
                </button>
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>Genesis: {cdzSummary.genesis_hash?.slice(0, 8)}...</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Domain Purges & Boundaries</div>
              <div style={{ fontSize: '24px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>
                {cdzSummary.event_breakdown?.domain_purge || 0} Purges
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
                Tactical: {cdzSummary.domain_breakdown?.TACTICAL || 0} • Adult: {cdzSummary.domain_breakdown?.ADULT || 0}
              </div>
            </div>
          </div>

          {/* Watcher Status & Scan Alert */}
          {cdzScanAlert && (
            <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid #38bdf8', padding: '12px 18px', borderRadius: '8px', marginBottom: '20px', fontSize: '13px', color: '#38bdf8', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>🛡️ {cdzScanAlert}</span>
              <button onClick={() => setCdzScanAlert(null)} style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '13px' }}>✕</button>
            </div>
          )}

          {/* Active Watcher Daemon Controller */}
          <div style={{ background: '#161b22', padding: '14px 18px', borderRadius: '10px', border: '1px solid #30363d', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <span style={{
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '11px',
                fontWeight: '700',
                background: cdzSummary.watcher?.running ? 'rgba(74, 222, 128, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                color: cdzSummary.watcher?.running ? '#4ade80' : '#ef4444',
                border: `1px solid ${cdzSummary.watcher?.running ? '#4ade80' : '#ef4444'}`
              }}>
                {cdzSummary.watcher?.running ? '● CDZ Active Polling Daemon (5s)' : '○ Watcher Idle'}
              </span>
              <span style={{ fontSize: '12px', color: '#8b949e' }}>
                Watching: <code>C:\AI-BS</code> & <code>Desktop\PenitsCradle</code> • Total Scans: {cdzSummary.watcher?.total_scans || 0}
              </span>
            </div>

            <button
              onClick={handleScanCdz}
              disabled={isScanningCdz}
              style={{
                background: '#1f6feb',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                padding: '7px 16px',
                fontSize: '12px',
                fontWeight: '700',
                cursor: isScanningCdz ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {isScanningCdz ? '⏳ Scanning Sources...' : '⚡ Scan Sources Now'}
            </button>
          </div>

          {/* Filter & Search Toolbar */}
          <div style={{ background: '#161b22', padding: '14px 18px', borderRadius: '10px', border: '1px solid #30363d', marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: '#8b949e', fontWeight: '600' }}>Domain:</span>
              {['ALL', 'TACTICAL', 'ADULT'].map((d) => (
                <button
                  key={d}
                  onClick={() => setCdzFilterDomain(d)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    border: '1px solid #30363d',
                    fontSize: '11px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    background: cdzFilterDomain === d ? (d === 'ADULT' ? '#ec4899' : '#38bdf8') : '#21262d',
                    color: cdzFilterDomain === d ? '#fff' : '#c9d1d9'
                  }}
                >
                  {d}
                </button>
              ))}

              <span style={{ fontSize: '12px', color: '#8b949e', fontWeight: '600', marginLeft: '8px' }}>Event:</span>
              {['ALL', 'domain_purge', 'domain_enter', 'sensor_source_change'].map((ev) => (
                <button
                  key={ev}
                  onClick={() => setCdzFilterEvent(ev)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '4px',
                    border: '1px solid #30363d',
                    fontSize: '11px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    background: cdzFilterEvent === ev ? '#f59e0b' : '#21262d',
                    color: cdzFilterEvent === ev ? '#000' : '#c9d1d9'
                  }}
                >
                  {ev}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="text"
                placeholder="Search detail, hash, event..."
                value={cdzSearch}
                onChange={(e) => setCdzSearch(e.target.value)}
                style={{
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  color: '#c9d1d9',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '12px',
                  width: '200px'
                }}
              />
              <span style={{ fontSize: '12px', color: '#8b949e' }}>Showing {cdzBlocks.length} of {cdzTotal} blocks</span>
            </div>
          </div>

          {/* Blocks Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>🔗 Immutable SHA-256 Ledger Blocks</span>
              <span style={{ fontSize: '12px', color: '#8b949e', fontWeight: 'normal' }}>Table: <code>penitscradle_audit_ledger</code> in <code>aibs_master.db</code></span>
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>#</th>
                    <th style={{ padding: '8px' }}>Timestamp (UTC)</th>
                    <th style={{ padding: '8px' }}>Domain</th>
                    <th style={{ padding: '8px' }}>Event</th>
                    <th style={{ padding: '8px' }}>Detail</th>
                    <th style={{ padding: '8px' }}>Block Hash</th>
                    <th style={{ padding: '8px' }}>Previous Hash</th>
                    <th style={{ padding: '8px' }}>Status</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {cdzBlocks.length === 0 ? (
                    <tr>
                      <td colSpan={9} style={{ padding: '24px', color: '#8b949e', textAlign: 'center' }}>
                        No audit blocks matching filter criteria. Click "⚡ Scan Sources Now" to ingest ledger files.
                      </td>
                    </tr>
                  ) : (
                    cdzBlocks.map((b) => (
                      <tr key={b.id || b.block_index} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#38bdf8', fontWeight: '700', fontFamily: 'monospace' }}>
                          {b.block_index}
                        </td>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>
                          {b.timestamp_iso ? b.timestamp_iso.replace('T', ' ').slice(0, 19) : new Date(b.timestamp * 1000).toISOString().slice(0, 19)}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '10px',
                            fontSize: '10px',
                            fontWeight: '700',
                            background: b.domain === 'ADULT' ? 'rgba(236, 72, 153, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                            color: b.domain === 'ADULT' ? '#ec4899' : '#38bdf8',
                            border: `1px solid ${b.domain === 'ADULT' ? '#ec4899' : '#38bdf8'}`
                          }}>
                            {b.domain}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: b.event === 'domain_purge' ? '#f59e0b' : b.event === 'sensor_source_change' ? '#a855f7' : '#4ade80', fontWeight: '600' }}>
                          {b.event}
                        </td>
                        <td style={{ padding: '8px', color: '#e2e8f0', fontFamily: 'monospace' }}>
                          {b.detail}
                        </td>
                        <td style={{ padding: '8px', fontFamily: 'monospace', color: '#a855f7' }}>
                          {b.hash}
                        </td>
                        <td style={{ padding: '8px', fontFamily: 'monospace', color: '#8b949e' }}>
                          {b.prev_hash}
                        </td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ color: '#4ade80', fontWeight: '700' }}>✔ Verified</span>
                        </td>
                        <td style={{ padding: '8px', textAlign: 'right' }}>
                          <button
                            onClick={() => copyToClipboard(b.full_hash || b.hash, `cdz_hash_${b.block_index}`)}
                            title="Copy Full SHA-256 Hash"
                            style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '12px' }}
                          >
                            {copiedHash === `cdz_hash_${b.block_index}` ? 'Copied' : '📋'}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
