import React, { useState, useEffect, useRef } from 'react';

const RefreshIcon = ({ size = 18, color = "#58a6ff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"></polyline>
    <polyline points="1 20 1 14 7 14"></polyline>
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
  </svg>
);

const SwapIcon = ({ size = 18, color = "#3fb950" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="17 1 21 5 17 9"></polyline>
    <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
    <polyline points="7 23 3 19 7 15"></polyline>
    <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
  </svg>
);

const SlidersIcon = ({ size = 18, color = "#a371f7" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="21" x2="4" y2="14"></line>
    <line x1="4" y1="10" x2="4" y2="3"></line>
    <line x1="12" y1="21" x2="12" y2="12"></line>
    <line x1="12" y1="8" x2="12" y2="3"></line>
    <line x1="20" y1="21" x2="20" y2="16"></line>
    <line x1="20" y1="12" x2="20" y2="3"></line>
    <line x1="1" y1="14" x2="7" y2="14"></line>
    <line x1="9" y1="8" x2="15" y2="8"></line>
    <line x1="17" y1="16" x2="23" y2="16"></line>
  </svg>
);

const fmt = (num, decimals = 2) => {
  if (typeof num !== 'number' || !Number.isFinite(num)) return 'Unavailable';
  return Number(num).toFixed(decimals);
};

const CryptoSwarmMobileController = ({ backendUrl, currentUser = null }) => {
  const apiHost = backendUrl || "https://ai-bs.brettstehouwer.live";
  
  const ownerSessionRef = useRef({ user: currentUser });
  if (ownerSessionRef.current.user !== currentUser) ownerSessionRef.current = { user: currentUser };
  const requestOwned = async (url, options = {}) => {
    const destination = new URL(url);
    const trustedOrigins = ['https://api.brettstehouwer.live', 'https://ai-bs.brettstehouwer.live', 'http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:8080', 'http://127.0.0.1:8080'];
    const trustedPaths = ['/api/storefront/balance', '/api/storefront/leads', '/api/crypto/swarm-status'];
    if (!trustedOrigins.includes(destination.origin) || !trustedPaths.includes(destination.pathname) || destination.username || destination.password) throw new Error('Untrusted owned-record destination.');
    const session = ownerSessionRef.current;
    const owner = session.user;
    if (!owner?.uid || !owner.emailVerified || !owner.email || typeof owner.getIdToken !== 'function') {
      throw new Error('Unavailable: a verified current identity is required.');
    }
    const ensureCurrent = () => {
      if (ownerSessionRef.current !== session || options.signal?.aborted) throw new DOMException('Account changed or request aborted.', 'AbortError');
    };
    ensureCurrent();
    const token = await owner.getIdToken();
    ensureCurrent();
    if (!token) throw new Error('Identity token unavailable.');
    const headers = new Headers(options.headers || {});
    headers.set('Authorization', `Bearer ${token}`);
    const response = await fetch(url, { ...options, headers, cache: 'no-store', redirect: 'error' });
    ensureCurrent();
    if (!response.ok) throw new Error(`Request rejected (HTTP ${response.status})`);
    const payload = await response.json();
    ensureCurrent();
    return payload;
  };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Control Parameter Form State
  const [buyDipPct, setBuyDipPct] = useState(1.5);
  const [takeProfitPct, setTakeProfitPct] = useState(2.0);
  const [tradeUsdAmount, setTradeUsdAmount] = useState(2.0);
  const [savingParams, setSavingParams] = useState(false);
  const [paramStatus, setParamStatus] = useState('');

  // Force Swap Form State
  const [fromSymbol, setFromSymbol] = useState('');
  const [toSymbol, setToSymbol] = useState('');
  const [swapping, setSwapping] = useState(false);
  const [swapMessage, setSwapMessage] = useState('');

  const fetchStatus = async (signal = null) => {
    try {
      setLoading(true);
      const json = await requestOwned(`${apiHost}/api/crypto/swarm-status`, { signal });
      if (!json || typeof json !== 'object' || Array.isArray(json)) throw new Error('Status data unavailable.');
      setData(json);
      setError(null);
      setLastUpdated(new Date().toLocaleTimeString());
      
      if (json.parameters) {
        setBuyDipPct(json.parameters.buy_dip_pct * 100);
        setTakeProfitPct(json.parameters.take_profit_pct * 100);
        setTradeUsdAmount(json.parameters.trade_usd_amount);
      }
    } catch (err) {
      console.error("Crypto status fetch error:", err);
      if (signal?.aborted || err.name === 'AbortError') return;
      setData(null);
      setLastUpdated(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setLastUpdated(null);
    fetchStatus(controller.signal);
    const interval = setInterval(() => fetchStatus(controller.signal), 15000);
    return () => { controller.abort(); clearInterval(interval); };
  }, [apiHost, currentUser]);

  const handleSaveParameters = async (e) => {
    e.preventDefault();
    setParamStatus('Strategy changes held locally. Live trading and external dispatch are disabled.');
  };

  const handleForceSwap = async (e) => {
    e.preventDefault();
    setSwapMessage('Swap held. Live trading and external dispatch are disabled; selections retained.');
  };

  const positions = Array.isArray(data?.positions) ? data.positions : [];
  const trackedSymbolsCount = Number.isInteger(data?.tracked_symbols_count) ? data.tracked_symbols_count : 'Unavailable';

  return (
    <div style={{
      width: '100%',
      minHeight: '100%',
      backgroundColor: '#0d1117',
      color: '#c9d1d9',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      padding: '12px 8px',
      boxSizing: 'border-box'
    }}>
      {/* Header Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: '1px solid #30363d'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>⚡</span> Crypto Swarm Mobile Controller
          </h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#8b949e' }}>
            Read-only monitoring. Live trading and external dispatch are held.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {lastUpdated && (
            <span style={{ fontSize: '12px', color: '#8b949e' }}>Updated: {lastUpdated}</span>
          )}
          <button
            onClick={() => fetchStatus()}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#21262d',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <RefreshIcon size={16} color="#58a6ff" />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ backgroundColor: '#3d1619', border: '1px solid #f85149', color: '#ff7b72', padding: '12px 16px', borderRadius: '6px', marginBottom: '20px' }}>
          <strong>Connection Error:</strong> {error}
        </div>
      )}

      {/* Metrics Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Active Positions</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#58a6ff', marginTop: '6px' }}>
            {Number.isInteger(data?.total_active_positions) ? data.total_active_positions : 'Unavailable'}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>Tracking {trackedSymbolsCount} Markets</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Est. Portfolio Value</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#3fb950', marginTop: '6px' }}>
            ${fmt(data?.total_estimated_portfolio_usd, 2)}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>USD Value across held coins</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Realized Profit</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#a371f7', marginTop: '6px' }}>
            ${fmt(data?.total_profit_usd, 2)}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>Cumulative profit banked</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Swarm Status</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#388bfd', marginTop: '6px', textTransform: 'capitalize' }}>
            {typeof data?.status === 'string' ? data.status : 'Unavailable'}
          </div>
          <div style={{ fontSize: '12px', color: '#3fb950', marginTop: '4px' }}>Trading held — execution state unverified</div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        
        {/* Active Positions Table Container */}
        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px', gridColumn: 'span 2' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📊</span> Active Coin Positions ({positions.length})
          </h2>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                  <th style={{ padding: '10px 12px' }}>Symbol</th>
                  <th style={{ padding: '10px 12px' }}>Holdings</th>
                  <th style={{ padding: '10px 12px' }}>Avg Buy Price</th>
                  <th style={{ padding: '10px 12px' }}>Ref Price</th>
                  <th style={{ padding: '10px 12px' }}>Est Value (USD)</th>
                  <th style={{ padding: '10px 12px' }}>P/L %</th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                      {Array.isArray(data?.positions) ? 'No active positions reported.' : 'Position records unavailable.'}
                    </td>
                  </tr>
                ) : (
                  positions.map((pos) => {
                    const isProfit = (pos.unrealized_profit_pct ?? 0) >= 0;
                    return (
                      <tr key={pos.symbol} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>{pos.symbol}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>{fmt(pos.amount, 4)}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>${(pos.avg_buy_price || 0) < 0.01 ? fmt(pos.avg_buy_price, 6) : fmt(pos.avg_buy_price, 4)}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>${(pos.current_ref_price || 0) < 0.01 ? fmt(pos.current_ref_price, 6) : fmt(pos.current_ref_price, 4)}</td>
                        <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>${fmt(pos.estimated_value_usd, 2)}</td>
                        <td style={{ padding: '12px', fontWeight: 600, color: isProfit ? '#3fb950' : '#f85149' }}>
                          {isProfit ? '+' : ''}{fmt(pos.unrealized_profit_pct, 2)}%
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Side Panel: Strategy Parameters & Manual Force Swap */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Strategy Parameter Tuning */}
          <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SlidersIcon size={18} color="#a371f7" /> Strategy Parameters
            </h2>

            <form onSubmit={handleSaveParameters} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Buy Dip Target (%): <strong>{buyDipPct}%</strong>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10.0"
                  value={buyDipPct}
                  onChange={(e) => setBuyDipPct(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Take Profit Target (%): <strong>{takeProfitPct}%</strong>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="20.0"
                  value={takeProfitPct}
                  onChange={(e) => setTakeProfitPct(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Trade USD Amount ($):
                </label>
                <input
                  type="number"
                  step="0.50"
                  min="1.00"
                  max="100.00"
                  value={tradeUsdAmount}
                  onChange={(e) => setTradeUsdAmount(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={savingParams}
                style={{
                  backgroundColor: '#238636',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 16px',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  marginTop: '8px'
                }}
              >
                Save Draft Parameters (Held)
              </button>

              {paramStatus && (
                <div style={{ fontSize: '12px', color: '#58a6ff', marginTop: '4px' }}>{paramStatus}</div>
              )}
            </form>
          </div>

          {/* Manual Force Swap Override */}
          <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SwapIcon size={18} color="#3fb950" /> Force Swap Override
            </h2>

            <form onSubmit={handleForceSwap} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>From Held Position:</label>
                <select
                  value={fromSymbol}
                  onChange={(e) => setFromSymbol(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="">-- Select Held Symbol --</option>
                  {positions.map(p => (
                    <option key={p.symbol} value={p.symbol}>
                      {p.symbol} (${fmt(p.estimated_value_usd, 2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Swap Into Target:</label>
                <select
                  value={toSymbol}
                  onChange={(e) => setToSymbol(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="">-- Select Target Symbol --</option>
                  <option value="BTC/USD">BTC/USD</option>
                  <option value="ETH/USD">ETH/USD</option>
                  <option value="SOL/USD">SOL/USD</option>
                  <option value="DOGE/USD">DOGE/USD</option>
                  <option value="CRO/USD">CRO/USD</option>
                  <option value="AVAX/USD">AVAX/USD</option>
                  <option value="LINK/USD">LINK/USD</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={swapping || !fromSymbol || !toSymbol}
                style={{
                  backgroundColor: swapping ? '#30363d' : '#8957e5',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 16px',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: swapping ? 'not-allowed' : 'pointer',
                  marginTop: '8px'
                }}
              >
                Swap Held
              </button>

              {swapMessage && (
                <div style={{ fontSize: '12px', marginTop: '4px' }}>{swapMessage}</div>
              )}
            </form>
          </div>

        </div>
      </div>
    </div>
  );
};

export default CryptoSwarmMobileController;
