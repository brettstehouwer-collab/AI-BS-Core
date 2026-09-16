import React, { useState, useEffect } from 'react';
import SHMTelemetryWidget from './SHMTelemetryWidget';


const AUTHORIZED_ADMIN_EMAILS = [
  'footballstar0325@gmail.com',
  'footballsyat0325@gmail.com',
  'brettstehouwer@gmail.com',
  'stehouwer@gmail.com',
  'theseandaley@gmail.com',
  'rottierannajoy@gmail.com',
  'keith@evolution6media.com'
];

export default function AdminSecurityMonitorTab({ currentUser }) {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
  const userEmail = (currentUser?.email || '').toLowerCase().trim();
  const isAuthorized = AUTHORIZED_ADMIN_EMAILS.includes(userEmail);

  const [activeSubPage, setActiveSubPage] = useState('threat_monitor'); // 'threat_monitor', 'billing_paypal', 'dev_portal', 'tunnel_status'

  // Telemetry State
  const [telemetry, setTelemetry] = useState({
    security_events: [],
    active_ip_bans: [],
    live_stream: []
  });
  
  // Billing Simulator State
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [payProvider, setPayProvider] = useState('paypal');
  const [payTier, setPayTier] = useState('pro');
  const [payAmount, setPayAmount] = useState('29.99');
  const [billingResult, setBillingResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Manual IP Ban State
  const [manualIp, setManualIp] = useState('');
  const [banReason, setBanReason] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  // Authorized Auditor Passkey State
  const [testerEmail, setTesterEmail] = useState('');
  const [testerIps, setTesterIps] = useState('127.0.0.1');
  const [testerProfile, setTesterProfile] = useState(null);
  const [isGeneratingTester, setIsGeneratingTester] = useState(false);

  const fetchTelemetry = async () => {
    if (!isAuthorized) return;
    try {
      const res = await fetch(`${backendUrl}/api/admin/security-telemetry`, {
        headers: { 'X-Admin-Email': userEmail }
      });
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.error('Failed to fetch admin telemetry:', err);
    }
  };

  const handleGenerateTesterPasskey = async (e) => {
    e.preventDefault();
    if (!testerEmail.trim()) return;
    setIsGeneratingTester(true);
    try {
      const ipsArray = testerIps.split(',').map(ip => ip.trim()).filter(Boolean);
      const res = await fetch(`${getApiBase()}/api/admin/tester-passkey/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Email': userEmail
        },
        body: JSON.stringify({
          tester_email: testerEmail.trim(),
          allowed_ips: ipsArray,
          duration_days: 30
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTesterProfile(data.tester_profile);
      }
    } catch (err) {
      console.error('Failed to generate tester passkey:', err);
    } finally {
      setIsGeneratingTester(false);
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      fetchTelemetry();
      const interval = setInterval(fetchTelemetry, 3000);
      return () => clearInterval(interval);
    }
  }, [isAuthorized]);

  const handleManualBan = async (e) => {
    e.preventDefault();
    if (!manualIp) return;
    try {
      const res = await fetch(`${getApiBase()}/api/admin/ip-ban`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Email': userEmail
        },
        body: JSON.stringify({ ip_address: manualIp, reason: banReason || 'Manual Admin Ban' })
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMsg(`IP ${manualIp} successfully banned.`);
        setManualIp('');
        setBanReason('');
        fetchTelemetry();
      } else {
        setStatusMsg(`Error: ${data.detail?.message || 'Ban failed.'}`);
      }
    } catch (err) {
      setStatusMsg(`Exception: ${err.message}`);
    }
  };

  const handleSimulatePayment = async (e) => {
    e.preventDefault();
    if (!clientName || !clientEmail) return alert('Please enter client name and email.');
    setIsSimulating(true);
    setBillingResult(null);
    try {
      const res = await fetch(`${getApiBase()}/api/v1/billing/simulate-checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: clientName,
          email: clientEmail,
          payment_provider: payProvider,
          tier: payTier,
          amount_paid: parseFloat(payAmount) || 29.99
        })
      });
      const data = await res.json();
      if (res.ok) {
        setBillingResult(data);
      } else {
        alert('Payment Simulation Error: ' + JSON.stringify(data));
      }
    } catch (err) {
      alert('Simulation Exception: ' + err.message);
    } finally {
      setIsSimulating(false);
    }
  };

  if (!isAuthorized) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        background: '#0d1117',
        color: '#f85149',
        fontFamily: 'Consolas, monospace',
        padding: '40px'
      }}>
        <div style={{ fontSize: '64px', marginBottom: '20px' }}>🔒</div>
        <h2>ACCESS RESTRICTED: SECURITY & COMMERCIAL SUITE</h2>
        <p style={{ color: '#8b949e', maxWidth: '500px', textAlign: 'center', marginTop: '10px' }}>
          This interface is protected under strict Role-Based Access Control (RBAC). Access is exclusively restricted to verified administrators:
        </p>
        <div style={{ background: '#161b22', padding: '15px 25px', borderRadius: '8px', border: '1px solid #30363d', marginTop: '20px', color: '#58a6ff' }}>
          {AUTHORIZED_ADMIN_EMAILS.map(email => (
            <div key={email}>• {email}</div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#0d1117',
      color: '#c9d1d9',
      fontFamily: 'Consolas, monospace',
      overflow: 'hidden'
    }}>
      {/* Header Bar */}
      <div style={{
        padding: '12px 24px',
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>🛡️</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', color: '#58a6ff' }}>ADMIN SECURITY & COMMERCIAL INTERCEPTOR SUITE</h2>
            <span style={{ fontSize: '12px', color: '#7d8590' }}>Active Hardware Monitor • Admin User: {userEmail}</span>
          </div>
        </div>

        {/* Sub-Page Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px', background: '#0d1117', padding: '4px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <button
            onClick={() => setActiveSubPage('threat_monitor')}
            style={{
              background: activeSubPage === 'threat_monitor' ? '#1f6feb' : 'transparent',
              color: activeSubPage === 'threat_monitor' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            🛡️ Live Threat Stream
          </button>
          <button
            onClick={() => setActiveSubPage('billing_paypal')}
            style={{
              background: activeSubPage === 'billing_paypal' ? '#238636' : 'transparent',
              color: activeSubPage === 'billing_paypal' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            💳 Billing & PayPal Payouts
          </button>
          <button
            onClick={() => setActiveSubPage('dev_portal')}
            style={{
              background: activeSubPage === 'dev_portal' ? '#8957e5' : 'transparent',
              color: activeSubPage === 'dev_portal' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            🌐 Developer API Docs
          </button>
          <button
            onClick={() => setActiveSubPage('tunnel_status')}
            style={{
              background: activeSubPage === 'tunnel_status' ? '#d29922' : 'transparent',
              color: activeSubPage === 'tunnel_status' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            ☁️ Cloudflare Tunnel
          </button>
          <button
            onClick={() => setActiveSubPage('shm_telemetry')}
            style={{
              background: activeSubPage === 'shm_telemetry' ? '#00d2ff' : 'transparent',
              color: activeSubPage === 'shm_telemetry' ? 'black' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            ⚡ SHM Telemetry
          </button>
        </div>
      </div>


      {/* Main Content Area rendering Sub-Pages */}
      <div style={{ flex: 1, overflow: 'hidden', padding: '16px' }}>

        {/* SUB-PAGE 1: LIVE THREAT STREAM */}
        {activeSubPage === 'threat_monitor' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflowY: 'auto' }}>
            
            {/* Authorized Security Auditor Passkey Card */}
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.4)' }}>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🔑 Authorized Security Auditor & Pen Tester Management
              </h3>
              <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#8b949e' }}>
                Generate temporary Passkeys and secret authorization rules for authorized security auditors. Automatically bypasses IP bans during testing windows.
              </p>

              <form onSubmit={handleGenerateTesterPasskey} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
                <input
                  type="email"
                  placeholder="Auditor Email (e.g. tester@securityfirm.com)"
                  value={testerEmail}
                  onChange={(e) => setTesterEmail(e.target.value)}
                  required
                  style={{ flex: 1, minWidth: '240px', padding: '10px 14px', borderRadius: '6px', background: '#0d1117', border: '1px solid #30363d', color: '#fff', fontSize: '13px' }}
                />
                <input
                  type="text"
                  placeholder="Allowed IPs (comma separated or 127.0.0.1)"
                  value={testerIps}
                  onChange={(e) => setTesterIps(e.target.value)}
                  style={{ flex: 1, minWidth: '200px', padding: '10px 14px', borderRadius: '6px', background: '#0d1117', border: '1px solid #30363d', color: '#fff', fontSize: '13px' }}
                />
                <button
                  type="submit"
                  disabled={isGeneratingTester}
                  style={{ padding: '10px 20px', background: 'linear-gradient(135deg, #38bdf8, #818cf8)', color: '#000', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px' }}
                >
                  {isGeneratingTester ? 'Generating...' : '⚡ Generate Auditor Passkey'}
                </button>
              </form>

              {testerProfile && (
                <div style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.3)', fontSize: '13px' }}>
                  <div style={{ color: '#4ade80', fontWeight: 'bold', marginBottom: '8px' }}>✨ Active Auditor Security Profile Generated:</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontFamily: 'monospace' }}>
                    <div><strong>Auditor Email:</strong> <span style={{ color: '#38bdf8' }}>{testerProfile.tester_email}</span></div>
                    <div><strong>Secret Header Name:</strong> <span style={{ color: '#f59e0b' }}>{testerProfile.secret_header_name}</span></div>
                    <div style={{ gridColumn: 'span 2' }}><strong>Secret Header Value:</strong> <code style={{ color: '#a855f7', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{testerProfile.secret_header_value}</code></div>
                    <div style={{ gridColumn: 'span 2' }}><strong>Tester API Passkey:</strong> <code style={{ color: '#4ade80', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{testerProfile.tester_api_passkey}</code></div>
                    <div style={{ gridColumn: 'span 2', fontSize: '11px', color: '#8b949e' }}>Testing Window: {testerProfile.window_start} to {testerProfile.window_end}</div>
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', minHeight: '400px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflow: 'hidden' }}>
                
                {/* Live Request Interceptor */}
                <div style={{ flex: 1, background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', background: '#21262d', borderBottom: '1px solid #30363d', fontWeight: 'bold', color: '#79c0ff', display: 'flex', justifyContent: 'space-between' }}>
                    <span>📡 LIVE HARDWARE & API INTERACTION STREAM</span>
                    <span>{telemetry.live_stream.length} Events Logged</span>
                  </div>
                  <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {telemetry.live_stream.length === 0 ? (
                      <div style={{ color: '#8b949e', textAlign: 'center', marginTop: '40px' }}>Waiting for incoming tenant requests...</div>
                    ) : (
                      telemetry.live_stream.map((item) => (
                        <div key={item.id} style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e' }}>
                            <span>IP: <strong style={{ color: '#f0883e' }}>{item.ip_address}</strong> • Key: {item.key_prefix}</span>
                            <span>{new Date(item.timestamp * 1000).toLocaleTimeString()}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: '#58a6ff', fontWeight: 'bold' }}>{item.endpoint}</span>
                            <span style={{ color: item.status_code === 200 ? '#7ee787' : '#f85149', background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: '4px' }}>
                              HTTP {item.status_code} ({item.response_time_ms} ms)
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Threat Interception Panel */}
                <div style={{ height: '220px', background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '10px 16px', background: '#21262d', borderBottom: '1px solid #30363d', fontWeight: 'bold', color: '#ff7b72' }}>
                    ⚠️ ACTIVE DEFENSE & INJECTION INTERCEPTIONS
                  </div>
                  <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {telemetry.security_events.length === 0 ? (
                      <div style={{ color: '#8b949e', textAlign: 'center', marginTop: '20px' }}>No active threat detections logged. Zero-Trust Shield Operational.</div>
                    ) : (
                      telemetry.security_events.map((ev) => (
                        <div key={ev.id} style={{ background: '#21262d', padding: '8px 12px', borderRadius: '4px', borderLeft: '3px solid #f85149', fontSize: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#ff7b72' }}>
                            <strong>[{ev.event_type}] Severity: {ev.severity}</strong>
                            <span>{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                          </div>
                          <div style={{ color: '#c9d1d9', marginTop: '4px' }}>
                            IP: <code>{ev.ip_address}</code> — {ev.details}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Manual IP Ban */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '16px' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#d2a8ff' }}>🚫 MANUAL IP BAN CONTROLS</h3>
                  <form onSubmit={handleManualBan} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <input
                      type="text"
                      placeholder="Target IP Address"
                      value={manualIp}
                      onChange={(e) => setManualIp(e.target.value)}
                      style={{ background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', fontFamily: 'inherit' }}
                    />
                    <input
                      type="text"
                      placeholder="Ban Reason"
                      value={banReason}
                      onChange={(e) => setBanReason(e.target.value)}
                      style={{ background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', fontFamily: 'inherit' }}
                    />
                    <button type="submit" style={{ background: '#da3633', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
                      EXECUTE IMMEDIATE BAN
                    </button>
                  </form>
                  {statusMsg && <div style={{ marginTop: '10px', fontSize: '12px', color: '#7ee787' }}>{statusMsg}</div>}
                </div>

                <div style={{ flex: 1, background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '10px 16px', background: '#21262d', borderBottom: '1px solid #30363d', fontWeight: 'bold', color: '#f0883e' }}>
                    🛑 BLACKLISTED IP ADDRESSES ({telemetry.active_ip_bans.length})
                  </div>
                  <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {telemetry.active_ip_bans.map((ban) => (
                      <div key={ban.ip_address} style={{ background: '#0d1117', padding: '8px 12px', borderRadius: '4px', border: '1px solid #30363d', fontSize: '12px' }}>
                        <div style={{ color: '#ff7b72', fontWeight: 'bold' }}>{ban.ip_address}</div>
                        <div style={{ color: '#8b949e', fontSize: '11px', marginTop: '2px' }}>{ban.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SUB-PAGE 2: Billing & PayPal Provisioner */}
        {activeSubPage === 'billing_paypal' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', height: '100%', overflowY: 'auto' }}>
            
            {/* Payment & Key Provisioner Simulator */}
            <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px' }}>
              <h3 style={{ margin: '0 0 16px 0', color: '#7ee787', display: 'flex', alignItems: 'center', gap: '8px' }}>
                💳 PAYPAL & STRIPE KEY PROVISIONER SIMULATOR
              </h3>
              <p style={{ color: '#8b949e', fontSize: '13px', lineHeight: '1.5' }}>
                Test immediate API key issuance and income credit triggers when clients rent your hardware or purchase tokens. Deposits directly to your PayPal account balance upon live checkout.
              </p>
              
              <form onSubmit={handleSimulatePayment} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#7d8590' }}>Client Name / Company</label>
                  <input
                    type="text"
                    placeholder="e.g. Acme Corp AI Lab"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#7d8590' }}>Client PayPal Email</label>
                  <input
                    type="email"
                    placeholder="client@paypal.com"
                    value={clientEmail}
                    onChange={(e) => setClientEmail(e.target.value)}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '12px', color: '#7d8590' }}>Payout Channel</label>
                    <select
                      value={payProvider}
                      onChange={(e) => setPayProvider(e.target.value)}
                      style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px', borderRadius: '6px', marginTop: '4px' }}
                    >
                      <option value="paypal">PayPal Payout</option>
                      <option value="stripe">Stripe Payout</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: '#7d8590' }}>Hardware Tier</label>
                    <select
                      value={payTier}
                      onChange={(e) => setPayTier(e.target.value)}
                      style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px', borderRadius: '6px', marginTop: '4px' }}
                    >
                      <option value="starter">Starter ($9.99/mo)</option>
                      <option value="pro">Pro ($29.99/mo)</option>
                      <option value="enterprise">Enterprise ($149.99/mo)</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: '#7d8590' }}>Amount ($ USD)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={payAmount}
                      onChange={(e) => setPayAmount(e.target.value)}
                      style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px', borderRadius: '6px', marginTop: '4px' }}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSimulating}
                  style={{
                    background: '#238636',
                    color: 'white',
                    border: 'none',
                    padding: '10px 20px',
                    borderRadius: '6px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    marginTop: '8px'
                  }}
                >
                  {isSimulating ? 'Processing Payout...' : 'SIMULATE PAYPAL CHECKOUT & ISSUE KEY'}
                </button>
              </form>

              {billingResult && (
                <div style={{ marginTop: '20px', background: '#0d1117', padding: '16px', borderRadius: '6px', border: '1px solid #7ee787' }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#7ee787' }}>🎉 PAYOUT RECEIVED & KEY PROVISIONED</h4>
                  <div style={{ fontSize: '12px', color: '#c9d1d9', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div><strong>Raw Key Issued:</strong> <code style={{ color: '#58a6ff' }}>{billingResult.api_key_details.raw_key}</code></div>
                    <div><strong>Tier Allocated:</strong> {billingResult.api_key_details.tier} ({billingResult.api_key_details.daily_quota} units/day)</div>
                    <div><strong>Client:</strong> {billingResult.api_key_details.client_name}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Payout Credentials Status */}
            <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px' }}>
              <h3 style={{ margin: '0 0 16px 0', color: '#58a6ff' }}>⚙️ LIVE PAYOUT CONFIGURATION</h3>
              <p style={{ color: '#8b949e', fontSize: '13px', lineHeight: '1.5' }}>
                Your live PayPal and Stripe credentials are safely stored in your local <code>C:\AI-BS\.env</code> environment file.
              </p>
              
              <div style={{ background: '#0d1117', padding: '14px', borderRadius: '6px', border: '1px solid #30363d', fontSize: '12px', marginTop: '14px' }}>
                <div style={{ color: '#79c0ff', fontWeight: 'bold', marginBottom: '8px' }}>Active Local Environment (.env):</div>
                <pre style={{ margin: 0, color: '#8b949e' }}>
{`PAYPAL_CLIENT_ID=BAAmicjyvk5iBoTJTebv5fi9wSGXdv3JeENHw31HNcum6Jtv1dWKK5PxfnBdFCESVmKz25GSnCkjwOvkj4
PAYPAL_PRIMARY_EMAIL=footballstar0325@gmail.com
PAYPAL_WEBHOOK_ID=webhook_paypal_v6_active_2026
STRIPE_WEBHOOK_SECRET=whsec_live_active_2026
AIBS_HMAC_SALT=AI_BS_SECURE_HMAC_SALT_2026`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* SUB-PAGE 3: Developer Portal & API Docs */}
        {activeSubPage === 'dev_portal' && (
          <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px', height: '100%', overflowY: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#8957e5' }}>🌐 COMMERCIAL DEVELOPER PORTAL & API SPECS</h3>
            <p style={{ color: '#8b949e', fontSize: '13px' }}>
              Public OpenAI-compliant REST endpoints for clients renting your RTX 4090 GPU hardware.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
              <div style={{ background: '#0d1117', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
                <h4 style={{ color: '#58a6ff', margin: '0 0 8px 0' }}>POST /v1/images/generations</h4>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>GPU-accelerated ComfyUI image synthesis.</div>
                <pre style={{ background: '#161b22', padding: '10px', borderRadius: '4px', fontSize: '11px', color: '#7ee787', marginTop: '8px' }}>
{`curl -X POST http://localhost:8000/v1/images/generations \\
  -H "Authorization: Bearer sk_aibs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "futuristic matrix room"}'`}
                </pre>
              </div>

              <div style={{ background: '#0d1117', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
                <h4 style={{ color: '#d2a8ff', margin: '0 0 8px 0' }}>POST /v1/chat/completions</h4>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>Stehouwer LLM / Ollama text completion.</div>
                <pre style={{ background: '#161b22', padding: '10px', borderRadius: '4px', fontSize: '11px', color: '#7ee787', marginTop: '8px' }}>
{`curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Authorization: Bearer sk_aibs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* SUB-PAGE 4: Cloudflare Tunnel Status */}
        {activeSubPage === 'tunnel_status' && (
          <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px', height: '100%', overflowY: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#d29922' }}>☁️ CLOUDFLARE ZERO-TRUST TUNNEL STATUS</h3>
            <p style={{ color: '#8b949e', fontSize: '13px' }}>
              Exposes <code>http://localhost:8000/v1</code> securely to the public internet without opening home router ports.
            </p>
            <div style={{ background: '#0d1117', padding: '16px', borderRadius: '6px', border: '1px solid #30363d', marginTop: '16px' }}>
              <div style={{ color: '#7ee787', fontWeight: 'bold', fontSize: '14px' }}>● Local Gateway Port: 8000 (Active)</div>
              <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '8px' }}>
                Run the quick tunnel command to launch your free public HTTPS endpoint:
              </div>
              <pre style={{ background: '#161b22', padding: '10px', borderRadius: '4px', color: '#58a6ff', marginTop: '8px' }}>
cloudflared tunnel --url http://localhost:8000
              </pre>
            </div>
          </div>
        )}

        {/* SUB-PAGE 5: Polyglot SHM Telemetry */}
        {activeSubPage === 'shm_telemetry' && (
          <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px', height: '100%', overflowY: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#00d2ff' }}>⚡ LOW-LEVEL POLYGLOT SHM BUS TELEMETRY</h3>
            <p style={{ color: '#8b949e', fontSize: '13px' }}>
              Real-time multiplexed Shared Memory ring buffer (0x0001 - 0x0004) streamed directly from <code>Local\AI_BS_IPC_SHM_RING</code> over WebSockets.
            </p>
            <SHMTelemetryWidget />
          </div>
        )}

      </div>
    </div>
  );
}

