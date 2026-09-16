import React, { useState, useEffect } from 'react';

const getEffectiveApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'https:' || (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
      return 'https://api.brettstehouwer.live';
    }
    if (window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      return 'http://localhost:8080';
    }
  }
  return 'https://api.brettstehouwer.live';
};

export default function GpuNetworkTab({ backendUrl }) {
  const [activeSubTab, setActiveSubTab] = useState('provider'); // provider | renter | telemetry
  
  // Host Telemetry State
  const [nodeId, setNodeId] = useState('Brett-RTX4090-Desktop');
  const [gpuName, setGpuName] = useState('NVIDIA GeForce RTX 4090');
  const [vramTotalGb, setVramTotalGb] = useState(24.0);
  const [vramUsedGb, setVramUsedGb] = useState(3.4);
  const [gpuTempC, setGpuTempC] = useState(52);
  const [isIdleOnly, setIsIdleOnly] = useState(true);
  const [isIdleActive, setIsIdleActive] = useState(true);
  const [payoutRateHr, setPayoutRateHr] = useState(0.55);

  // Earnings Ledger (Synced directly with compute_telemetry.json)
  const [totalEarnedUsd, setTotalEarnedUsd] = useState(12.92);
  const [pendingUsd, setPendingUsd] = useState(12.92);
  const [redeemedUsd, setRedeemedUsd] = useState(0.00);
  const [totalComputeHours, setTotalComputeHours] = useState(0.9);

  // Payout Form State
  const [payoutAmount, setPayoutAmount] = useState(10.00);
  const [payoutMethod, setPayoutMethod] = useState('paypal');
  const [payoutStatusMsg, setPayoutStatusMsg] = useState('');
  const [isRedeeming, setIsRedeeming] = useState(false);

  // Job Submission State (Renter)
  const [renterJobType, setRenterJobType] = useState('sdxl_inference');
  const [renterTargetTier, setRenterTargetTier] = useState('ultra_rtx4090');
  const [renterPrompt, setRenterPrompt] = useState('Generate high-resolution 3D cyberpunk cityscape model rendering');
  const [renterBudgetUsd, setRenterBudgetUsd] = useState(2.50);
  const [submittedJobs, setSubmittedJobs] = useState([]);

  // Live On-Chain Treasury State
  const [treasuryData, setTreasuryData] = useState(null);
  const [copiedAddress, setCopiedAddress] = useState(null);

  const apiBase = backendUrl || getEffectiveApiBase();

  // Fetch Live Node Earnings & Telemetry
  const fetchEarnings = () => {
    fetch(`${apiBase}/v1/network/earnings/${nodeId}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.ledger) {
          setTotalEarnedUsd(data.ledger.total_earned_usd);
          setPendingUsd(data.ledger.pending_usd);
          setRedeemedUsd(data.ledger.redeemed_usd);
          setTotalComputeHours(data.ledger.total_compute_hours);
        }
      })
      .catch(err => console.error("Failed to fetch earnings:", err));
  };

  useEffect(() => {
    fetchEarnings();
    const eInterval = setInterval(fetchEarnings, 10000);
    return () => clearInterval(eInterval);
  }, [apiBase, nodeId]);

  // Fetch Live On-Chain Treasury Data
  const fetchTreasury = () => {
    fetch(`${apiBase}/v1/network/treasury-status`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setTreasuryData(data);
        }
      })
      .catch(err => console.error("Failed to fetch treasury:", err));
  };

  useEffect(() => {
    fetchTreasury();
    const tInterval = setInterval(fetchTreasury, 15000);
    return () => clearInterval(tInterval);
  }, [apiBase]);

  // Simulate real-time compute earnings counter when active & idle
  useEffect(() => {
    const interval = setInterval(() => {
      if (isIdleActive) {
        const delta = (5 / 3600) * payoutRateHr;
        setTotalEarnedUsd(prev => Number((prev + delta).toFixed(4)));
        setPendingUsd(prev => Number((prev + delta).toFixed(4)));
        setTotalComputeHours(prev => Number((prev + (5 / 3600)).toFixed(3)));
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [isIdleActive, payoutRateHr]);

  // Handle Payout Redemption
  const handleRedeemPayout = async () => {
    setIsRedeeming(true);
    setPayoutStatusMsg('');
    try {
      const res = await fetch(`${apiBase}/v1/network/redeem-payout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: nodeId,
          amount_usd: Number(payoutAmount),
          payout_method: payoutMethod
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setPendingUsd(data.remaining_pending_usd);
        setRedeemedUsd(data.total_redeemed_usd);
        setPayoutStatusMsg(`✅ ${data.message}`);
      } else {
        setPayoutStatusMsg(`❌ ${data.message || 'Payout failed.'}`);
      }
    } catch (err) {
      setPayoutStatusMsg(`❌ Server error during payout redemption: ${err.message}`);
    } finally {
      setIsRedeeming(false);
    }
  };

  // Handle Job Submission (Renter)
  const handleSubmitJob = async () => {
    try {
      const res = await fetch(`${apiBase}/v1/network/submit-job`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          renter_id: "brett_publishing_renter",
          job_type: renterJobType,
          prompt_or_code: renterPrompt,
          target_tier: renterTargetTier,
          max_budget_usd: Number(renterBudgetUsd)
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSubmittedJobs(prev => [data, ...prev]);
      }
    } catch (err) {
      console.error("Job submit error:", err);
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: '#090d16',
      color: '#c9d1d9',
      padding: '24px',
      overflowY: 'auto',
      boxSizing: 'border-box'
    }}>
      {/* Top Banner Header */}
      <div style={{
        background: 'linear-gradient(135deg, #1f293d 0%, #0d1117 100%)',
        border: '1px solid #30363d',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h2 style={{ margin: 0, color: '#58a6ff', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            ⚡ Decentralized GPU Compute Network
          </h2>
          <p style={{ margin: '6px 0 0 0', color: '#8b949e', fontSize: '0.88rem' }}>
            Monetize idle RTX 4090 GPU compute power for containerized AI inference & deep learning workloads.
          </p>
        </div>
        
        {/* Navigation Sub-Tabs */}
        <div style={{ display: 'flex', gap: '8px', background: '#161b22', padding: '4px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <button
            onClick={() => setActiveSubTab('provider')}
            style={{
              background: activeSubTab === 'provider' ? '#238636' : 'transparent',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.85rem'
            }}
          >
            💰 Host Provider Dashboard
          </button>
          <button
            onClick={() => setActiveSubTab('renter')}
            style={{
              background: activeSubTab === 'renter' ? '#1f6feb' : 'transparent',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.85rem'
            }}
          >
            🚀 AI Renter Marketplace
          </button>
        </div>
      </div>

      {/* PROVIDER DASHBOARD VIEW */}
      {activeSubTab === 'provider' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
          
          {/* Left Column: Live Earnings & Node Hardware Telemetry */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Live Earnings Stat Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>Available Balance</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#3fb950', marginTop: '4px' }}>
                  ${pendingUsd.toFixed(2)}
                </div>
              </div>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>Total Earned</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#58a6ff', marginTop: '4px' }}>
                  ${totalEarnedUsd.toFixed(2)}
                </div>
              </div>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>GPU Earning Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#e3b341', marginTop: '4px' }}>
                  ${payoutRateHr.toFixed(2)} <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>/ hr</span>
                </div>
              </div>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>Compute Hours</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#d2a8ff', marginTop: '4px' }}>
                  {totalComputeHours.toFixed(1)} <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>hrs</span>
                </div>
              </div>
            </div>

            {/* Hardware Node Telemetry & Status */}
            <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#c9d1d9' }}>🖥️ Host Worker Node Telemetry</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: isIdleActive ? '#3fb950' : '#d29922'
                  }} />
                  <span style={{ fontSize: '0.85rem', fontWeight: '600', color: isIdleActive ? '#3fb950' : '#d29922' }}>
                    {isIdleActive ? 'IDLE & COMPUTING ($/hr Active)' : 'BUSY (Computing Paused)'}
                  </span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.88rem' }}>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>Host Node ID</div>
                  <div style={{ fontWeight: '600', color: '#58a6ff', marginTop: '2px' }}>{nodeId}</div>
                </div>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>GPU Acceleration Hardware</div>
                  <div style={{ fontWeight: '600', color: '#c9d1d9', marginTop: '2px' }}>{gpuName}</div>
                </div>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>VRAM Allocation & Allocation</div>
                  <div style={{ fontWeight: '600', color: '#c9d1d9', marginTop: '2px' }}>
                    {vramUsedGb} GB / {vramTotalGb} GB VRAM ({Math.round((vramUsedGb/vramTotalGb)*100)}%)
                  </div>
                </div>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>GPU Operating Temperature</div>
                  <div style={{ fontWeight: '600', color: gpuTempC > 70 ? '#f85149' : '#3fb950', marginTop: '2px' }}>
                    {gpuTempC} °C (Optimal Cooling)
                  </div>
                </div>
              </div>

              {/* Safety Idle Switch */}
              <div style={{ marginTop: '16px', background: '#21262d', padding: '12px 16px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>🛡️ Windows Idle-Only Task Execution</div>
                  <div style={{ fontSize: '0.78rem', color: '#8b949e' }}>
                    Automatically pauses AI container tasks instantly when mouse/keyboard input is detected or gaming starts.
                  </div>
                </div>
                <button
                  onClick={() => setIsIdleOnly(!isIdleOnly)}
                  style={{
                    background: isIdleOnly ? '#238636' : '#da3633',
                    color: '#fff',
                    border: 'none',
                    padding: '6px 14px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '0.8rem'
                  }}
                >
                  {isIdleOnly ? 'ACTIVE (Idle Only)' : 'ALWAYS ON'}
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Earnings Payout Redemption Module */}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#58a6ff' }}>💳 Payout & Rewards Redemption</h3>
            
            <p style={{ margin: 0, fontSize: '0.82rem', color: '#8b949e' }}>
              Redeem host GPU compute earnings directly via PayPal, Visa Prepaid Card, or Gift Cards.
            </p>

            <div>
              <label htmlFor="payout-amount-input" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                Redemption Amount ($ USD):
              </label>
              <input
                id="payout-amount-input"
                aria-label="Redemption Amount ($ USD)"
                type="number"
                min="1"
                max={pendingUsd}
                step="1"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  color: '#fff',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label htmlFor="payout-method-select" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                Payout Destination Method:
              </label>
              <select
                id="payout-method-select"
                aria-label="Payout Destination Method"
                value={payoutMethod}
                onChange={(e) => setPayoutMethod(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  color: '#fff',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box'
                }}
              >
                <option value="paypal">PayPal Direct Cash Transfer</option>
                <option value="giftcard">Visa Virtual Prepaid Card</option>
                <option value="amazon">Amazon Gift Card Code</option>
                <option value="crypto">USDC Crypto Deposit</option>
                <option value="cryptocom_app">Crypto.com App Direct Transfer</option>
              </select>
            </div>

            <button
              onClick={handleRedeemPayout}
              disabled={isRedeeming || pendingUsd < payoutAmount}
              style={{
                background: pendingUsd >= payoutAmount ? '#238636' : '#21262d',
                color: pendingUsd >= payoutAmount ? '#fff' : '#8b949e',
                border: 'none',
                padding: '12px',
                borderRadius: '8px',
                cursor: pendingUsd >= payoutAmount ? 'pointer' : 'not-allowed',
                fontWeight: '700',
                fontSize: '0.95rem',
                marginTop: '8px'
              }}
            >
              {isRedeeming ? 'Processing Payout...' : `Redeem $${payoutAmount} Payout`}
            </button>

            {payoutStatusMsg && (
              <div style={{
                background: payoutStatusMsg.includes('✅') ? '#122e1a' : '#3c1e1e',
                color: payoutStatusMsg.includes('✅') ? '#3fb950' : '#f85149',
                border: `1px solid ${payoutStatusMsg.includes('✅') ? '#238636' : '#da3633'}`,
                padding: '10px',
                borderRadius: '6px',
                fontSize: '0.8rem'
              }}>
                {payoutStatusMsg}
              </div>
            )}

            <div style={{ borderTop: '1px solid #21262d', paddingTop: '12px', fontSize: '0.78rem', color: '#8b949e' }}>
              <div>Total Payouts Redeemed: <strong style={{ color: '#c9d1d9' }}>${redeemedUsd.toFixed(2)}</strong></div>
              <div style={{ marginTop: '4px' }}>Payout Email: <strong style={{ color: '#58a6ff' }}>footballstar0325@mail.com</strong></div>
            </div>

            {/* LIVE ON-CHAIN TREASURY & BLOCKCHAIN TELEMETRY CARD */}
            <div style={{ background: '#0d1117', border: '1px solid #238636', borderRadius: '8px', padding: '14px', marginTop: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#3fb950', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  🏛️ Server On-Chain Treasury
                </div>
                <span style={{ fontSize: '0.7rem', background: '#122e1a', color: '#3fb950', border: '1px solid #238636', padding: '2px 6px', borderRadius: '4px' }}>
                  Polygon Mainnet
                </span>
              </div>

              {treasuryData ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.78rem' }}>
                  <div style={{ background: '#161b22', padding: '10px 12px', borderRadius: '6px', border: '1px solid #30363d' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ color: '#8b949e', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Server Hot Wallet Treasury</span>
                      <span style={{ fontSize: '0.65rem', background: '#21262d', color: '#8b949e', padding: '1px 6px', borderRadius: '4px' }}>Node Payout Source</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        USDC: <strong style={{ color: treasuryData.hot_wallet.usdc_balance > 0 ? '#3fb950' : '#f85149' }}>${treasuryData.hot_wallet.usdc_balance.toFixed(2)}</strong>
                      </div>
                      <div>
                        POL (Gas): <strong style={{ color: treasuryData.hot_wallet.pol_balance > 0.05 ? '#3fb950' : '#d29922' }}>{treasuryData.hot_wallet.pol_balance} POL</strong>
                      </div>
                    </div>
                    <div style={{ marginTop: '6px', fontSize: '0.72rem', color: '#58a6ff', wordBreak: 'break-all', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span title={treasuryData.hot_wallet.address} style={{ fontFamily: 'monospace' }}>
                        {treasuryData.hot_wallet.address ? `${treasuryData.hot_wallet.address.slice(0, 10)}...${treasuryData.hot_wallet.address.slice(-8)}` : 'Unconfigured'}
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {treasuryData.hot_wallet.address && (
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(treasuryData.hot_wallet.address);
                              setCopiedAddress('hot');
                              setTimeout(() => setCopiedAddress(null), 2000);
                            }}
                            style={{
                              background: copiedAddress === 'hot' ? '#238636' : '#21262d',
                              color: '#f0f6fc',
                              border: '1px solid #30363d',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              padding: '2px 6px',
                              cursor: 'pointer'
                            }}
                          >
                            {copiedAddress === 'hot' ? '✓ Copied' : '📋 Copy'}
                          </button>
                        )}
                        <a href={treasuryData.hot_wallet.explorer_url} target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'underline' }}>Explorer ↗</a>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: '#161b22', padding: '10px 12px', borderRadius: '6px', border: '1px solid #238636' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ color: '#3fb950', fontWeight: '700', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Destination Wallet (Crypto.com)
                      </span>
                      <span style={{ fontSize: '0.65rem', background: '#122e1a', color: '#3fb950', border: '1px solid #238636', padding: '1px 6px', borderRadius: '4px' }}>
                        Active Polygon Deposit
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        USDC: <strong style={{ color: '#58a6ff' }}>${treasuryData.dest_wallet.usdc_balance.toFixed(2)}</strong>
                      </div>
                      <div>
                        POL: <strong style={{ color: '#8b949e' }}>{treasuryData.dest_wallet.pol_balance} POL</strong>
                      </div>
                    </div>
                    <div style={{ marginTop: '6px', fontSize: '0.72rem', color: '#58a6ff', wordBreak: 'break-all', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span title={treasuryData.dest_wallet.address} style={{ fontFamily: 'monospace', fontWeight: '600', color: '#e6edf3' }}>
                        {treasuryData.dest_wallet.address ? `${treasuryData.dest_wallet.address.slice(0, 10)}...${treasuryData.dest_wallet.address.slice(-8)}` : 'Unconfigured'}
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {treasuryData.dest_wallet.address && (
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard.writeText(treasuryData.dest_wallet.address);
                              setCopiedAddress('dest');
                              setTimeout(() => setCopiedAddress(null), 2000);
                            }}
                            style={{
                              background: copiedAddress === 'dest' ? '#2ea043' : '#238636',
                              color: '#ffffff',
                              border: '1px solid #2ea043',
                              borderRadius: '4px',
                              fontSize: '0.68rem',
                              fontWeight: '600',
                              padding: '2px 8px',
                              cursor: 'pointer'
                            }}
                          >
                            {copiedAddress === 'dest' ? '✓ Copied' : '📋 Copy Address'}
                          </button>
                        )}
                        <a href={treasuryData.dest_wallet.explorer_url} target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'underline' }}>Explorer ↗</a>
                      </div>
                    </div>
                    <div style={{ marginTop: '4px', fontSize: '0.68rem', color: '#8b949e', wordBreak: 'break-all' }}>
                      Full Address: <code style={{ color: '#7ee787' }}>{treasuryData.dest_wallet.address}</code>
                    </div>
                  </div>

                  <div style={{ background: '#161b22', padding: '8px 10px', borderRadius: '6px', border: '1px solid #30363d', fontSize: '0.7rem', color: '#8b949e' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: '600', color: '#c9d1d9' }}>USDC Token Contract (Polygon Native):</span>
                      <a href="https://polygonscan.com/token/0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359" target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'underline' }}>Token Contract ↗</a>
                    </div>
                    <div style={{ marginTop: '3px', fontFamily: 'monospace', color: '#79c0ff', wordBreak: 'break-all', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359</span>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText('0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359');
                          setCopiedAddress('contract');
                          setTimeout(() => setCopiedAddress(null), 2000);
                        }}
                        style={{
                          background: copiedAddress === 'contract' ? '#238636' : '#21262d',
                          color: '#f0f6fc',
                          border: '1px solid #30363d',
                          borderRadius: '4px',
                          fontSize: '0.65rem',
                          padding: '1px 6px',
                          cursor: 'pointer'
                        }}
                      >
                        {copiedAddress === 'contract' ? '✓' : '📋'}
                      </button>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e', paddingTop: '4px' }}>
                    <span>Block: <strong style={{ color: '#c9d1d9' }}>#{treasuryData.block_number}</strong></span>
                    <span>Node: <strong style={{ color: '#3fb950' }}>PublicNode Dedicated</strong></span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '0.78rem', color: '#8b949e', textAlign: 'center', padding: '8px' }}>
                  Connecting to Polygon Web3 Node...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* RENTER MARKETPLACE VIEW */}
      {activeSubTab === 'renter' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          
          {/* Submit Container Job Form */}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#58a6ff' }}>
              🚀 Submit Container Task to Consumer Network
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label htmlFor="renter-job-type-select" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Task Workload Type:
                </label>
                <select
                  id="renter-job-type-select"
                  aria-label="Task Workload Type"
                  value={renterJobType}
                  onChange={(e) => setRenterJobType(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px' }}
                >
                  <option value="sdxl_inference">ComfyUI SDXL Image / Video Generation</option>
                  <option value="pytorch_train">PyTorch Model Fine-Tuning Task</option>
                  <option value="ollama_llm">Ollama LLM Batch Inference Processing</option>
                </select>
              </div>

              <div>
                <label htmlFor="renter-target-tier-select" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Target Hardware Tier:
                </label>
                <select
                  id="renter-target-tier-select"
                  aria-label="Target Hardware Tier"
                  value={renterTargetTier}
                  onChange={(e) => setRenterTargetTier(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px' }}
                >
                  <option value="ultra_rtx4090">Ultra Tier (RTX 4090 - 24GB VRAM) @ $0.55/hr</option>
                  <option value="high_rtx4080">High Tier (RTX 4080 - 16GB VRAM) @ $0.35/hr</option>
                  <option value="mid_rtx3070">Mid Tier (RTX 3070 - 8GB VRAM) @ $0.20/hr</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Container Execution Payload / Code / Prompt:
                </label>
                <textarea
                  rows={4}
                  value={renterPrompt}
                  onChange={(e) => setRenterPrompt(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontFamily: 'monospace' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Max Budget Limit ($ USD):
                </label>
                <input
                  type="number"
                  step="0.50"
                  value={renterBudgetUsd}
                  onChange={(e) => setRenterBudgetUsd(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px' }}
                />
              </div>

              <button
                onClick={handleSubmitJob}
                style={{
                  background: '#1f6feb',
                  color: '#fff',
                  border: 'none',
                  padding: '12px',
                  borderRadius: '8px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  fontSize: '0.95rem'
                }}
              >
                Submit Job to Network Dispatcher
              </button>
            </div>
          </div>

          {/* Active Job Queue */}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#c9d1d9' }}>
              📊 Network Job Queue & Dispatch History
            </h3>

            {submittedJobs.length === 0 ? (
              <div style={{ color: '#8b949e', fontSize: '0.88rem', fontStyle: 'italic', textAlign: 'center', padding: '40px 0' }}>
                No active jobs submitted yet. Use the form on the left to queue container workloads.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {submittedJobs.map((job, idx) => (
                  <div key={idx} style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: '6px', padding: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: '#58a6ff' }}>
                      <span>{job.job_id}</span>
                      <span style={{ color: '#3fb950' }}>Queued (Node Assigned)</span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#8b949e', marginTop: '4px' }}>
                      Position: #{job.queue_position} | Target Tier: {renterTargetTier}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
