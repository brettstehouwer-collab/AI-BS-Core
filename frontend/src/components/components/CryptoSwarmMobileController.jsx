/** @typedef {{symbol:string,amount:number,avg_buy_price:number,long_term_vault:number,current_ref_price:number,estimated_value_usd:number,unrealized_profit_pct:number}} SwarmPosition */
/** @typedef {{symbol:string,total_usd:number|string,remaining_usd:number|string,drip_size_usd:number|string,drip_interval_seconds:number|string}} SwarmTwap */
/** @typedef {{status:string,total_active_positions:number,tracked_symbols_count:number,total_estimated_portfolio_usd:number,total_profit_usd:number,total_vault_cro:number,strategy_layer:string,last_action:string,positions:SwarmPosition[],twaps:SwarmTwap[],hunting_rate_per_min:number,max_trades_per_min:number,action_cooldown_sec:number,hft_mode:string}} SwarmData */
import { useState, useEffect } from 'react';

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

/** @param {number|string|null|undefined} num */
const fmt = (num, decimals = 2) => {
  if (num === undefined || num === null || isNaN(Number(num))) return (0).toFixed(decimals);
  return Number(num).toFixed(decimals);
};

const getEffectiveApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'https:' || (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
      return 'https://api.brettstehouwer.live';
    }
    if (window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      return 'http://127.0.0.1:8080';
    }
  }
  return 'https://api.brettstehouwer.live';
};

/** @param {{backendUrl?:string}} props */
const CryptoSwarmMobileController = ({ backendUrl }) => {
  const getDaemonHost = () => {
    if (typeof window !== 'undefined' && window.location) {
      if (window.location.protocol === 'https:' || (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
        return `${getEffectiveApiBase()}/api/proxy/8007`;
      }
      const hostname = String(window.location.hostname);
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8007';
      }
      if (hostname.startsWith('192.168.') || hostname.startsWith('10.') || hostname.startsWith('172.')) {
        return `http://${hostname}:8007`;
      }
    }
    return backendUrl || `${getEffectiveApiBase()}/api/proxy/8007`;
  };

  const getApiHost = () => {
    return getEffectiveApiBase();
  };

  const daemonHost = getDaemonHost();
  const apiHost = getApiHost();
  
  const [data, setData] = useState(/** @type {SwarmData|null} */ (null));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [lastUpdated, setLastUpdated] = useState(/** @type {string|null} */ (null));

  // Control Parameter Form State (Defaults to Fast Scalp HFT Parameters)
  const [buyDipPct, setBuyDipPct] = useState(/** @type {number|string} */ (0.20));
  const [takeProfitPct, setTakeProfitPct] = useState(/** @type {number|string} */ (0.25));
  const [tradeUsdAmount, setTradeUsdAmount] = useState(/** @type {number|string} */ (1.10));
  const [macroSupportCeiling, setMacroSupportCeiling] = useState(/** @type {number|string} */ (0.08500));
  const [savingParams, setSavingParams] = useState(false);
  const [paramStatus, setParamStatus] = useState('');
  const [macroAnalysis, setMacroAnalysis] = useState(/** @type {{price_channel?:{market_regime?:string,historical_low?:number,historical_high?:number},macro_correlation_model?:{estimated_gain_loss_probability?:Record<string,number>,upside_target_1?:number}}|null} */ (null));

  // Force Swap Form State
  const [fromSymbol, setFromSymbol] = useState('');
  const [toSymbol, setToSymbol] = useState('');
  const [swapping, setSwapping] = useState(false);
  const [swapMessage, setSwapMessage] = useState('');

  const fetchStatus = async () => {
    try {
      if (!data) setLoading(true);
      
      let res = null;
      // 1. Prioritize direct Swarm Daemon (port 8007) for real-time live scalping telemetry
      try {
        const r = await fetch(`${daemonHost}/api/v1/telemetry`);
        if (r.ok) res = r;
      } catch (e) {}

      // 2. Try FastAPI Core Backend (port 8080) crypto status
      if (!res) {
        try {
          const r = await fetch(`${apiHost}/api/crypto/swarm-status`);
          if (r.ok) res = r;
        } catch (e) {}
      }

      // 3. Fallback to /api/v1/telemetry on apiHost
      if (!res) {
        try {
          const r = await fetch(`${apiHost}/api/v1/telemetry`);
          if (r.ok) res = r;
        } catch (e) {}
      }

      if (!res || !res.ok) {
        setError('Standby / Connecting to Crypto Swarm');
        return;
      }
      const json = await res.json();
      
      // Map the telemetry payload to the component's expected data structure
      const ledger = json.ledger || {};
      const positionsObj = ledger.positions || {};
      const refsObj = ledger.reference_prices || {};
      
      let totalEstValue = parseFloat(json.usd_balance || 0);
      let totalVaultCro = 0;

      const mappedPositions = Object.keys(positionsObj).map(symbol => {
        const amount = positionsObj[symbol]?.amount || 0;
        const avgBuy = positionsObj[symbol]?.avg_buy_price || 0;
        const vaultStash = positionsObj[symbol]?.long_term_vault || 0;
        totalVaultCro += vaultStash;

        const currentRef = refsObj[symbol] || avgBuy || 0.056;
        const estValue = amount * currentRef;
        totalEstValue += estValue;
        
        let unrealizedPct = 0;
        if (avgBuy > 0) {
          unrealizedPct = ((currentRef - avgBuy) / avgBuy) * 100;
        }
        
        return {
          symbol,
          amount,
          avg_buy_price: avgBuy,
          long_term_vault: vaultStash,
          current_ref_price: currentRef,
          estimated_value_usd: estValue,
          unrealized_profit_pct: unrealizedPct
        };
      });

      // Try fetching predictive macro analysis
      try {
        const macroRes = await fetch(`${apiHost}/api/crypto/cro/predict`);
        if (macroRes.ok) {
          const macroJson = await macroRes.json();
          setMacroAnalysis(macroJson);
        }
      } catch (mErr) {
        // Silent fallback
      }
      
      const mappedData = {
        status: json.status || 'offline',
        total_active_positions: mappedPositions.length,
        tracked_symbols_count: Object.keys(refsObj).length,
        total_estimated_portfolio_usd: totalEstValue,
        total_profit_usd: ledger.total_profit_usd || 0.0,
        total_vault_cro: totalVaultCro,
        strategy_layer: ledger.strategy_layer || 'High-Frequency Fast Scalp & Harvest Engine',
        last_action: ledger.last_action || 'Standing by',
        positions: mappedPositions,
        twaps: ledger.twap_orders || [],
        hunting_rate_per_min: json.hunting_rate_per_min || 1200,
        max_trades_per_min: json.max_trades_per_min || 120,
        action_cooldown_sec: json.action_cooldown_sec || 0.5,
        hft_mode: json.hft_mode || 'Maximum Frequency (Zero Bottleneck)'
      };

      setData(mappedData);
      setError(null);
      setLastUpdated(new Date().toLocaleTimeString());
      
    } catch (err) {
      console.warn("Crypto status fetch notice:", errorMessage(err));
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, [apiHost, daemonHost]);

  /** @param {import("react").FormEvent} e */
  const handleSaveParameters = async (e) => {
    e.preventDefault();
    setSavingParams(true);
    setParamStatus('');
    try {
      const res = await fetch(`${daemonHost}/api/crypto/set-parameters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          buy_dip_pct: parseFloat(String(buyDipPct)) / 100.0,
          take_profit_pct: parseFloat(String(takeProfitPct)) / 100.0,
          trade_usd_amount: parseFloat(String(tradeUsdAmount)),
          macro_support_ceiling: parseFloat(String(macroSupportCeiling))
        })
      });
      const resJson = await res.json();
      if (resJson.status === 'success') {
        setParamStatus('✅ Strategy parameters updated!');
        fetchStatus();
      } else {
        setParamStatus('❌ Update failed');
      }
    } catch (err) {
      setParamStatus(`❌ Error: ${errorMessage(err)}`);
    } finally {
      setSavingParams(false);
    }
  };

  /** @param {import("react").FormEvent} e */
  const handleForceSwap = async (e) => {
    e.preventDefault();
    if (!fromSymbol || !toSymbol) {
      setSwapMessage('⚠️ Select both from and to symbols.');
      return;
    }
    setSwapping(true);
    setSwapMessage('');
    try {
      const res = await fetch(`${daemonHost}/api/crypto/force-swap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_symbol: fromSymbol, to_symbol: toSymbol })
      });
      const resJson = await res.json();
      if (res.ok && resJson.status === 'success') {
        setSwapMessage(`✅ Swapped ${fromSymbol} -> ${toSymbol} ($${resJson.usd_value})`);
        setFromSymbol('');
        setToSymbol('');
        fetchStatus();
      } else {
        setSwapMessage(`❌ ${resJson.detail || 'Swap failed'}`);
      }
    } catch (err) {
      setSwapMessage(`❌ Error: ${errorMessage(err)}`);
    } finally {
      setSwapping(false);
    }
  };

  const positions = data?.positions || [];
  const twaps = data?.twaps || [];
  const trackedSymbolsCount = data?.tracked_symbols_count || 0;

  return (
    <div style={{
      width: '100%',
      minHeight: '100vh',
      backgroundColor: '#0d1117',
      color: '#c9d1d9',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      padding: '20px',
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
            Real-Time Automated Trade Monitoring & Volatility Harvesting Daemon
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {lastUpdated && (
            <span style={{ fontSize: '12px', color: '#8b949e' }}>Updated: {lastUpdated}</span>
          )}
          <button
            onClick={fetchStatus}
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
            {data ? (data.total_active_positions ?? 0) : '--'}
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
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>CRO Long-Term Vault</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#f0883e', marginTop: '6px' }}>
            {fmt(data?.total_vault_cro, 4)} CRO
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>Zero-risk accumulated stash</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Active Strategy Layer</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#ff7b72', marginTop: '6px', lineHeight: '1.2' }}>
            {data?.strategy_layer || 'Hourly Dip Compounding'}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={data?.last_action}>
            {data?.last_action || 'Standing by'}
          </div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Swarm Status</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#388bfd', marginTop: '6px', textTransform: 'capitalize' }}>
            {data ? data.status : 'Offline'}
          </div>
          <div style={{ fontSize: '12px', color: '#3fb950', marginTop: '4px' }}>● Bot Active (Port 8007)</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Hunting Velocity</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f0883e', marginTop: '6px' }}>
            ~{data?.hunting_rate_per_min || 1200} <span style={{ fontSize: '13px', fontWeight: 500, color: '#8b949e' }}>evals/min</span>
          </div>
          <div style={{ fontSize: '12px', color: '#3fb950', marginTop: '4px' }}>⚡ Max {data?.max_trades_per_min || 120} trades/min (0.5s)</div>
        </div>
      </div>

      {/* Macro Prediction Banner */}
      {macroAnalysis && (
        <div style={{ backgroundColor: '#1c2128', border: '1px solid #388bfd', borderRadius: '8px', padding: '14px 18px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '12px', color: '#58a6ff', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px' }}>📈 Macro Pattern Forecast (CRO/USD)</span>
            <div style={{ fontSize: '14px', color: '#c9d1d9', marginTop: '4px' }}>
              Market Regime: <strong style={{ color: '#3fb950' }}>{macroAnalysis?.price_channel?.market_regime}</strong> | Channel: ${macroAnalysis?.price_channel?.historical_low} – ${macroAnalysis?.price_channel?.historical_high}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>24h Upside Probability</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#3fb950' }}>
                {((macroAnalysis?.macro_correlation_model?.estimated_gain_loss_probability?.['24h_upside_prob'] || 0.62) * 100).toFixed(1)}%
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: '#8b949e' }}>Target 1</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#58a6ff' }}>
                ${macroAnalysis?.macro_correlation_model?.upside_target_1 || '0.0588'}
              </div>
            </div>
          </div>
        </div>
      )}

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
                  <th style={{ padding: '10px 12px' }}>Vault Stash</th>
                  <th style={{ padding: '10px 12px' }}>Avg Buy Price</th>
                  <th style={{ padding: '10px 12px' }}>Ref Price</th>
                  <th style={{ padding: '10px 12px' }}>Est Value (USD)</th>
                  <th style={{ padding: '10px 12px' }}>P/L %</th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                      No active positions held currently.
                    </td>
                  </tr>
                ) : (
                  positions.map((pos) => {
                    const isProfit = (pos.unrealized_profit_pct ?? 0) >= 0;
                    return (
                      <tr key={pos.symbol} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>{pos.symbol}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>{fmt(pos.amount, 4)}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace', color: '#f0883e' }}>{fmt(pos.long_term_vault, 4)} CRO</td>
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

        {/* Active Drip Campaigns Table Container */}
        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px', gridColumn: 'span 2' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>💧</span> Active Drip Campaigns ({twaps.length})
          </h2>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                  <th style={{ padding: '10px 12px' }}>Symbol</th>
                  <th style={{ padding: '10px 12px' }}>Total Ordered</th>
                  <th style={{ padding: '10px 12px' }}>Remaining USD</th>
                  <th style={{ padding: '10px 12px' }}>Drip Size</th>
                  <th style={{ padding: '10px 12px' }}>Interval (s)</th>
                </tr>
              </thead>
              <tbody>
                {twaps.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                      No active TWAP/Drip campaigns running.
                    </td>
                  </tr>
                ) : (
                  twaps.map((twap, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>{twap.symbol}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace' }}>${fmt(twap.total_usd, 2)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace', color: '#3fb950' }}>${fmt(twap.remaining_usd, 2)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace' }}>${fmt(twap.drip_size_usd, 2)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace' }}>{twap.drip_interval_seconds}s</td>
                    </tr>
                  ))
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
                  step="0.05"
                  min="0.05"
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
                  step="0.05"
                  min="0.05"
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

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Macro Support Ceiling ($): <strong>${macroSupportCeiling}</strong>
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="0.0100"
                  max="1.0000"
                  value={macroSupportCeiling}
                  onChange={(e) => setMacroSupportCeiling(e.target.value)}
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
                {savingParams ? 'Updating...' : 'Save Parameters'}
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
                {swapping ? 'Executing Swap...' : 'Execute Force Swap'}
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

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
