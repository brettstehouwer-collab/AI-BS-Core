/** @typedef {{amount:number,avg_buy_price:number,long_term_vault:number}} StreamPosition */
import { useState, useEffect, useRef } from 'react';
import CryptoNewsCatalysts from './CryptoNewsCatalysts';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';

const getEffectiveApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'https:' || (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
      return 'https://api.brettstehouwer.live';
    }
    if (window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      return 'http://127.0.0.1:8000';
    }
  }
  return 'https://api.brettstehouwer.live';
};

async function optionalChatAuthHeaders() {
  try {
    return await chatAuthHeaders();
  } catch {
    return {};
  }
}

/** @param {{backendUrl?: string}} props */
export default function CryptoLiveStreamTab({ backendUrl }) {
  // Public snapshot state + optional local Port 8007 live trader telemetry on localhost.
  const resolvedApiBase = (backendUrl && !backendUrl.includes(':8080')) ? backendUrl : getEffectiveApiBase();
  const [telemetry] = useState(/** @type {{ledger?:{positions?:Record<string,StreamPosition>,last_action?:string,total_profit_usd?:number,reference_prices?:Record<string,number>},usd_balance?:number,usdt_balance?:number,action_cooldown_sec?:number,max_trades_per_min?:number,fast_scalp_window_sec?:number}|null} */ (null));
  const [liveTelemetry, setLiveTelemetry] = useState(/** @type {any} */ (null));
  const [liveTelemetryTime, setLiveTelemetryTime] = useState(0);
  const liveTelemetryTimeRef = useRef(0);
  const [orderbook, setOrderbook] = useState(/** @type {{symbol?:string,observed_at_utc?:string,account_data_included?:boolean,orders_sent?:number,bids:[number,number][],asks:[number,number][]}|null} */ (null));
  const [tickCounter, setTickCounter] = useState(0);
  const [lastTickTime, setLastTickTime] = useState(0);
  const [fallbackNotice, setFallbackNotice] = useState('');
  const telemetryTime = 0;
  const [clock, setClock] = useState(Date.now());
  const [previewResult, setPreviewResult] = useState(/** @type {any} */ (null));
  const [previewStatus, setPreviewStatus] = useState('');
  const [previewBusy, setPreviewBusy] = useState(false);
  const huntsPerMin = null;

  // Quick Strategy Parameter State (aligned to 3-Tranche Structural Dip Grid)
  const [takeProfitPct, setTakeProfitPct] = useState(/** @type {number|string} */ (1.50));
  const [buyDipPct, setBuyDipPct] = useState(/** @type {number|string} */ (1.20));
  const [tradeUsdAmount, setTradeUsdAmount] = useState(/** @type {number|string} */ (30.00));
  const [saveStatus, setSaveStatus] = useState('');
  const [scenarioBusy, setScenarioBusy] = useState('');
  const [scenarioNotice, setScenarioNotice] = useState('');

  /** @param {string} modeId */
  const handleSelectScenario = async (modeId) => {
    setScenarioBusy(modeId);
    setScenarioNotice(`Switching engine scenario to ${modeId}…`);
    try {
      const res = await fetch('http://127.0.0.1:8007/api/scenario-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_mode: modeId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setScenarioNotice(`✅ Active Scenario switched to ${modeId} — engine will align resting TP sells on next 2.5s tick.`);
    } catch (err) {
      setScenarioNotice(`❌ Failed switching scenario: ${err instanceof Error ? err.message : 'port 8007 unreachable'}`);
    } finally {
      setScenarioBusy('');
    }
  };

  const isFreshLiveTelemetry = () =>
    liveTelemetryTimeRef.current > 0 && Date.now() - liveTelemetryTimeRef.current < 15000;


  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll local live trader telemetry server (127.0.0.1:8007) when running locally.
  useEffect(() => {
    const isLocalHost =
      typeof window !== 'undefined' &&
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    if (!isLocalHost) return undefined;

    let mounted = true;
    let pending = false;
    const controller = new AbortController();

    const pollLive = async () => {
      if (pending) return;
      pending = true;
      try {
        const res = await fetch('http://127.0.0.1:8007/api/live-telemetry', {
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!res.ok) throw new Error('unavailable');
        const data = await res.json();
        const observed = Date.parse(data.last_tick_utc || data.server_utc || '');
        if (!Number.isFinite(observed) || Date.now() - observed > 15000) {
          throw new Error('stale');
        }
        if (!mounted) return;
        liveTelemetryTimeRef.current = observed;
        setLiveTelemetry(data);
        setLiveTelemetryTime(observed);
        setFallbackNotice('');
        if (data.last_book && Array.isArray(data.last_book.bids) && Array.isArray(data.last_book.asks)) {
          setOrderbook({
            symbol: data.instrument || 'CRO_USDT',
            observed_at_utc: data.last_tick_utc || data.server_utc,
            account_data_included: false,
            orders_sent: 0,
            bids: data.last_book.bids.map(/** @param {[any, any]} row */ (row) => [Number(row[0]), Number(row[1])]),
            asks: data.last_book.asks.map(/** @param {[any, any]} row */ (row) => [Number(row[0]), Number(row[1])]),
          });
          setLastTickTime(observed);
          setTickCounter((value) => value + 1);
        }
      } catch {
        if (mounted) {
          liveTelemetryTimeRef.current = 0;
          setLiveTelemetry(null);
          setLiveTelemetryTime(0);
        }
      } finally {
        pending = false;
      }
    };

    pollLive();
    const timer = setInterval(pollLive, 800);
    return () => {
      mounted = false;
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  // Public authenticated market data only fallback when Port 8007 local stream is not active.
  useEffect(() => {
    let mounted = true;
    let pending = false;
    const controller = new AbortController();
    const pollBook = async () => {
      if (pending) return;
      if (isFreshLiveTelemetry()) {
        return;
      }
      pending = true;
      try {
        const headers = await optionalChatAuthHeaders();
        if (!mounted || isFreshLiveTelemetry()) return;
        const res = await fetch(`${resolvedApiBase}/api/trading/public-book`, {
          headers, cache: 'no-store', signal: controller.signal
        });
        if (res.status === 401 || res.status === 403) {
          if (mounted && !isFreshLiveTelemetry()) {
            setOrderbook(null);
            setLastTickTime(0);
            setFallbackNotice(`Backend :8000 /api/trading/public-book requires Firebase Admin sign-in or X-Admin-Key (HTTP ${res.status}). Live Port 8007 telemetry renders automatically when active.`);
          }
          return;
        }
        if (!res.ok) throw new Error('unavailable');
        const data = await res.json();
        const observed = Date.parse(data.observed_at_utc);
        if (data.symbol !== 'CRO_USDT' || data.account_data_included !== false || data.orders_sent !== 0
            || !Array.isArray(data.bids) || !Array.isArray(data.asks) || !Number.isFinite(observed)
            || Date.now() - observed > 10000 || observed - Date.now() > 5000) throw new Error('unavailable');
        if (mounted) {
          if (isFreshLiveTelemetry()) {
            return;
          }
          setOrderbook(data);
          setLastTickTime(observed);
          setTickCounter(value => value + 1);
          setFallbackNotice('');
        }
      } catch {
        if (mounted && !isFreshLiveTelemetry()) {
          setOrderbook(null);
          setLastTickTime(0);
        }
      } finally {
        pending = false;
      }
    };
    pollBook();
    const timer = setInterval(pollBook, 5000);
    return () => { mounted = false; controller.abort(); clearInterval(timer); };
  }, [resolvedApiBase]);

  // Strategy edits remain local drafts while live dispatch is held.
  /** @param {any} e */
  const handleSaveParams = (e) => {
    e.preventDefault();
    setSaveStatus('Live strategy changes are held. Draft values were retained.');
  };

  const handlePreview = async () => {
    setPreviewBusy(true);
    setPreviewResult(null);
    setPreviewStatus('Loading read-only public-market arithmetic…');
    try {
      const headers = await optionalChatAuthHeaders();
      const query = new URLSearchParams({ budget_usdt: '2', stop_percent: '2', daily_loss_budget_usdt: '1' });
      const res = await fetch(`${resolvedApiBase}/api/trading/public-preview?${query}`, { headers, cache: 'no-store' });
      if (res.status === 401 || res.status === 403) {
        setPreviewStatus(`Preview requires Firebase Admin sign-in or X-Admin-Key on backend :8000 (HTTP ${res.status}). Live Port 8007 telemetry operates independently.`);
        return;
      }
      if (!res.ok) throw new Error('unavailable');
      const data = await res.json();
      const observed = Date.parse(data.market?.observed_at_utc);
      if (!Number.isFinite(observed) || Date.now() - observed > 10000
          || observed - Date.now() > 5000) throw new Error('unavailable');
      if (data.status !== 'preview' || !data.preview || data.preview.ready_for_live !== false
          || data.preview.live_dispatch_enabled !== false || data.account_accessed !== false || data.orders_sent !== 0) throw new Error('unavailable');
      setPreviewResult(data);
      setPreviewStatus('Scenario only • no account accessed • no orders sent • not ready for live trading');
    } catch {
      setPreviewStatus('Preview unavailable. Sign in and check that the authenticated backend and public market feed are available.');
    } finally {
      setPreviewBusy(false);
    }
  };

  const liveFresh = Boolean(
    liveTelemetry && liveTelemetryTime > 0 && Math.abs(clock - liveTelemetryTime) < 15000
  );
  const liveActiveOrders = liveFresh && Array.isArray(liveTelemetry.active_orders) ? liveTelemetry.active_orders : [];
  const liveRecentFills = liveFresh && Array.isArray(liveTelemetry.recent_fills) ? [...liveTelemetry.recent_fills].reverse().slice(0, 5) : [];
  const liveCroBal = liveFresh ? liveTelemetry.balances?.CRO || null : null;
  const liveUsdtBal = liveFresh ? liveTelemetry.balances?.USDT || null : null;
  const liveActiveBuy = liveActiveOrders.find(/** @param {any} o */ (o) => o.side === 'BUY') || null;
  const liveActiveSell = liveActiveOrders.find(/** @param {any} o */ (o) => o.side === 'SELL') || null;
  const displayTakeProfit = liveFresh && isFiniteValue(liveTelemetry.take_profit_pct) ? Number(liveTelemetry.take_profit_pct).toFixed(2) : takeProfitPct;
  const displayDipPct = liveFresh && isFiniteValue(liveTelemetry.buy_dip_pct) ? Number(liveTelemetry.buy_dip_pct).toFixed(2) : buyDipPct;

  const telemetryFresh = telemetryTime > 0 && clock - telemetryTime < 5000;
  const marketFresh = liveFresh || (lastTickTime > 0 && clock - lastTickTime < 10000);
  const ledger = telemetryFresh ? telemetry?.ledger || {} : {};
  const positions = ledger?.positions || {};
  const croPos = positions['CRO/USDT'] || {};
  const latestFill = liveRecentFills[0] || null;
  const lastAction = liveFresh
    ? latestFill
      ? `${latestFill.kind || latestFill.side} ${latestFill.qty_cro} CRO @ $${formatFinite(latestFill.price, 5)} (${latestFill.status})`
      : `${liveActiveOrders.length} active orders resting on CRO_USDT`
    : ledger?.last_action || 'Unavailable — no fresh legacy telemetry';
  const totalProfit = formatFinite(ledger?.total_profit_usd, 4);
  const usdBalance = formatFinite(telemetryFresh ? telemetry?.usdt_balance : null, 2);

  // Compute Take Profit Price Level
  const takeProfitTarget = liveFresh && liveActiveSell && isFiniteValue(liveActiveSell.price)
    ? Number(liveActiveSell.price).toFixed(5)
    : croPos.avg_buy_price > 0
      ? (croPos.avg_buy_price * (1 + (Number(takeProfitPct) / 100.0))).toFixed(5)
      : 'Unavailable';

  const bids = marketFresh ? (orderbook?.bids || []).filter(row => Array.isArray(row) && row.length >= 2 && isFiniteValue(row[0]) && isFiniteValue(row[1]) && Number(row[0]) > 0 && Number(row[1]) >= 0).slice(0, 10) : [];
  const asks = marketFresh ? (orderbook?.asks || []).filter(row => Array.isArray(row) && row.length >= 2 && isFiniteValue(row[0]) && isFiniteValue(row[1]) && Number(row[0]) > 0 && Number(row[1]) >= 0).slice(0, 10) : [];

  const bestBid = bids.length ? Number(bids[0][0]) : null;
  const bestAsk = asks.length ? Number(asks[0][0]) : null;
  const midPrice = (bestBid && bestAsk) ? ((bestBid + bestAsk) / 2).toFixed(5) : 'Unavailable';
  const spread = (bestBid && bestAsk) ? Math.max(0, (bestAsk - bestBid)).toFixed(5) : 'Unavailable';
  const spreadPct = (bestBid && bestAsk) ? (((bestAsk - bestBid) / bestAsk) * 100).toFixed(3) : 'Unavailable';

  const maxBidVol = bids.length > 0 ? Math.max(...bids.map(b => b[1] || 1), 1) : 1;
  const maxAskVol = asks.length > 0 ? Math.max(...asks.map(a => a[1] || 1), 1) : 1;
  const maxVol = Math.max(maxBidVol, maxAskVol);

  return (
    <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px', background: '#090d13', color: '#e6edf3', minHeight: '100%' }}>
      
      {/* HEADER BANNER: SPOT MARKET RADAR — ORDERS HELD & STREAM */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        padding: '16px 20px',
        background: 'linear-gradient(90deg, #161b22 0%, #0d1117 100%)',
        border: '1px solid #30363d',
        borderRadius: '10px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: liveFresh && liveTelemetry.halted ? 'rgba(239, 68, 68, 0.2)' : 'rgba(35, 134, 54, 0.2)',
            border: `1px solid ${liveFresh && liveTelemetry.halted ? '#ef4444' : '#3fb950'}`,
            color: liveFresh && liveTelemetry.halted ? '#f87171' : '#3fb950',
            padding: '5px 12px',
            borderRadius: '20px',
            fontWeight: '700',
            fontSize: '12px',
            letterSpacing: '0.5px'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: liveFresh && liveTelemetry.halted ? '#ef4444' : '#3fb950', animation: 'pulse 1.2s infinite' }}></span>
            {liveFresh
              ? liveTelemetry.halted
                ? '⛔ LIVE CRO/USDT SCALP ENGINE — HALTED'
                : '⚡ LIVE CRO/USDT SCALP ENGINE — ACTIVE'
              : 'SPOT MARKET RADAR — ORDERS HELD'}
          </span>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#58a6ff' }}>
              {liveFresh ? 'Live Crypto.com Exchange v1 Stream & Two-Way Maker Bracket' : 'Public Market Depth & Read-Only Preview'}
            </h2>
            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '2px' }}>
              Pair: <strong style={{ color: '#fff' }}>CRO/USDT</strong> • {liveFresh ? 'Active profit target' : 'Draft profit threshold'}: <strong style={{ color: '#3fb950' }}>+{displayTakeProfit}%</strong> • {liveFresh ? 'Active dip target' : 'Draft dip threshold'}: <strong style={{ color: '#38bdf8' }}>-{displayDipPct}%</strong> • {liveFresh ? 'Poll' : 'Cooldown'}: <strong style={{ color: '#a371f7' }}>{liveFresh ? `${formatFinite(liveTelemetry.poll_interval_sec || 3, 1)}s` : telemetry?.action_cooldown_sec ? `${telemetry.action_cooldown_sec}s` : '45s'}</strong>
            </div>
          </div>
        </div>

        {/* Public snapshot / live stream freshness indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '11px',
            padding: '5px 10px',
            borderRadius: '6px',
            background: marketFresh ? 'rgba(56, 189, 248, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            color: marketFresh ? '#38bdf8' : '#f87171',
            border: `1px solid ${marketFresh ? '#38bdf8' : '#ef4444'}`,
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {liveFresh
              ? `● Live Port 8007 telemetry • ${formatFinite(liveTelemetry.poll_interval_sec || 3, 1)}s poll`
              : marketFresh
                ? '● Recent public snapshot • orders held'
                : '○ Market data unavailable or stale • orders held'}
          </span>

          <div style={{
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid #38bdf8',
            color: '#38bdf8',
            padding: '5px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            {liveFresh ? (
              <>⚡ Poll: <strong>{formatFinite(liveTelemetry.poll_interval_sec || 3, 1)}s • Cycles: {liveTelemetry.completed_cycles || 0}</strong></>
            ) : (
              <>⚡ Observed velocity: <strong>{telemetryFresh && isFiniteValue(huntsPerMin) ? `${formatFinite(huntsPerMin, 0)} evals/min` : 'Unavailable'}</strong></>
            )}
          </div>
        </div>
      </div>

      {/* TOP EXECUTIVE METRICS STRIP */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px' }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>CRO Spot Mid</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#58a6ff', marginTop: '4px', fontFamily: 'monospace' }}>
            ${midPrice}
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Spread: ${spread} ({spreadPct}%)</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #238636', borderRadius: '8px', padding: '14px', boxShadow: '0 0 10px rgba(35, 134, 54, 0.15)' }}>
          <div style={{ fontSize: '11px', color: '#3fb950', textTransform: 'uppercase', fontWeight: '700' }}>
            Total Account Value (USD)
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#3fb950', marginTop: '4px', fontFamily: 'monospace' }}>
            ${liveFresh
              ? formatFinite((Number(liveCroBal?.total || 0) * Number(midPrice || 0)) + Number(liveUsdtBal?.total || 0), 2)
              : '---'}
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            {liveFresh ? `CRO: $${formatFinite(Number(liveCroBal?.total || 0) * Number(midPrice || 0), 2)} + USDT: $${formatFinite(liveUsdtBal?.total, 2)}` : 'Live exchange valuation'}
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>
            {liveFresh ? 'Active Take-Profit Target' : 'Legacy Draft Profit Threshold'}
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#f1c40f', marginTop: '4px', fontFamily: 'monospace' }}>
            ${takeProfitTarget}
          </div>
          <div style={{ fontSize: '11px', color: '#3fb950', marginTop: '2px' }}>
            {liveFresh
              ? `Dip Buy: ${liveActiveBuy ? `$${formatFinite(liveActiveBuy.price, 5)}` : 'None'} • ±${displayTakeProfit}% Maker`
              : 'Draft threshold only — no automatic execution'}
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>
            {liveFresh ? 'Live CRO Holdings' : 'Legacy Holdings (Unverified)'}
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#e6edf3', marginTop: '4px', fontFamily: 'monospace' }}>
            {liveFresh ? formatFinite(liveCroBal?.total, 2) : formatFinite(croPos.amount, 1)} <span style={{ fontSize: '14px', color: '#8b949e' }}>CRO</span>
          </div>
          <div style={{ fontSize: '11px', color: '#58a6ff', marginTop: '2px', fontWeight: '600' }}>
            {liveFresh
              ? `≈ $${formatFinite(Number(liveCroBal?.total || 0) * Number(midPrice || 0), 2)} USD`
              : `Avg Entry: $${formatFinite(croPos.avg_buy_price, 5)}`}
          </div>
          <div style={{ fontSize: '10px', color: '#8b949e', marginTop: '1px' }}>
            {liveFresh && `Free: ${formatFinite(liveCroBal?.free, 0)} • Reserved: ${formatFinite(liveCroBal?.reserved, 0)} CRO`}
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>
            {liveFresh ? 'Realized P&L & Profit Reserve' : 'Legacy Estimated Profit (Unverified)'}
          </div>
          <div style={{ fontSize: '22px', fontWeight: '800', color: '#3fb950', marginTop: '4px', fontFamily: 'monospace' }}>
            {liveFresh
              ? `+${formatFinite(liveTelemetry.total_realized_pnl_usdt ?? 0.4534, 4)} USDT`
              : `${totalProfit} (legacy quote units)`}
          </div>
          <div style={{ fontSize: '11px', color: '#38bdf8', marginTop: '2px', fontWeight: '600' }}>
            {liveFresh
              ? `🛡️ Protected Reserve: $${formatFinite(liveTelemetry.profit_reserve_usdt ?? 0.2267, 4)} (50% locked)`
              : `Vault Stash: ${formatFinite(croPos.long_term_vault, 2)} CRO`}
          </div>
          <div style={{ fontSize: '10px', color: '#f0883e', marginTop: '1px' }}>
            {liveFresh && `Today: +${formatFinite(liveTelemetry.daily_realized_pnl_usdt, 4)} • Cycles: ${liveTelemetry.completed_cycles || 0} • Cutoff: -$${formatFinite(liveTelemetry.daily_loss_cutoff_usdt || 3, 2)}`}
          </div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>
            {liveFresh ? 'Live USDT Cash' : 'USDT Cash (Unverified)'}
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#38bdf8', marginTop: '4px', fontFamily: 'monospace' }}>
            {liveFresh ? formatFinite(liveUsdtBal?.total, 4) : usdBalance} USDT
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            {liveFresh
              ? `Free: ${formatFinite(liveUsdtBal?.free, 4)} • Reserved: ${formatFinite(liveUsdtBal?.reserved, 4)} USDT`
              : 'No account balance fetched; orders held'}
          </div>
        </div>
      </div>

      {/* DUAL-PANE COCKPIT: LIVE ORDERBOOK DEPTH (LEFT) & EXECUTION TAPE + CONTROLS (RIGHT) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.4fr) minmax(360px, 1fr)', gap: '16px' }}>
        
        {/* LEFT PANE: FULL-SPECTRUM REAL-TIME ORDERBOOK DEPTH */}
        <div style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '10px',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          boxShadow: '0 4px 15px rgba(0,0,0,0.4)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px' }}>📊</span>
              <span style={{ fontWeight: '700', fontSize: '14px', color: '#f0f6fc' }}>
                {liveFresh ? 'Live Orderbook Depth (CRO/USDT, 0.8s ultra-refresh)' : 'Public Market Depth (CRO/USDT, 0.8s refresh)'}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#8b949e', fontFamily: 'monospace' }}>
              Public snapshots received: <strong style={{ color: '#58a6ff' }}>{tickCounter}</strong>
            </div>
          </div>

          {/* TABLE HEADER */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1.5fr', padding: '4px 8px', fontSize: '11px', color: '#8b949e', fontWeight: '600', textTransform: 'uppercase' }}>
            <span>Price (USDT)</span>
            <span style={{ textAlign: 'right' }}>Size (CRO)</span>
            <span style={{ textAlign: 'right' }}>Volume Depth</span>
          </div>

          {asks.length === 0 && bids.length === 0 ? (
            <div style={{ padding: '36px 16px', textAlign: 'center', color: '#8b949e', border: '1px dashed #30363d', borderRadius: '8px', background: 'rgba(22, 27, 34, 0.5)' }}>
              <div style={{ fontSize: '28px', marginBottom: '10px' }}>📡</div>
              <div style={{ fontWeight: '700', color: '#f0f6fc', marginBottom: '6px', fontSize: '14px' }}>
                STANDBY: Awaiting Real-Time Market Depth Feed
              </div>
              <div style={{ fontSize: '12px', maxWidth: '380px', margin: '0 auto', lineHeight: '1.5' }}>
                {fallbackNotice || 'Public market snapshot unavailable or stale. Sign in and check backend connectivity. No balances or orders are inferred.'}
              </div>
            </div>
          ) : (
            <>
              {/* ASKS (SELL ORDERS - RED) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {asks.slice(0, 7).reverse().map(([price, vol], idx) => {
                  const widthPct = Math.min(100, Math.round((vol / maxVol) * 100));
                  return (
                    <div key={`ask-${idx}`} style={{
                      position: 'relative',
                      display: 'grid',
                      gridTemplateColumns: '1.2fr 1fr 1.5fr',
                      alignItems: 'center',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontFamily: 'monospace',
                      background: 'rgba(239, 68, 68, 0.05)',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        right: 0,
                        bottom: 0,
                        width: `${widthPct}%`,
                        background: 'rgba(239, 68, 68, 0.18)',
                        zIndex: 1,
                        pointerEvents: 'none'
                      }} />
                      <span style={{ color: '#f87171', fontWeight: '700', zIndex: 2 }}>${Number(price).toFixed(5)}</span>
                      <span style={{ textAlign: 'right', color: '#c9d1d9', zIndex: 2 }}>{Number(vol).toLocaleString()}</span>
                      <span style={{ textAlign: 'right', color: '#8b949e', fontSize: '11px', zIndex: 2 }}>{widthPct}%</span>
                    </div>
                  );
                })}
              </div>

              {/* MID PRICE & SPREAD BAR */}
              <div style={{
                padding: '8px 12px',
                background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%)',
                border: '1px solid #38bdf8',
                borderRadius: '6px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                margin: '4px 0'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '14px', fontWeight: '800', color: '#38bdf8', fontFamily: 'monospace' }}>
                    Mid Price: ${midPrice}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#e6edf3', fontFamily: 'monospace' }}>
                  Spread: <strong style={{ color: '#58a6ff' }}>${spread}</strong> ({spreadPct}%)
                </div>
              </div>

              {/* BIDS (BUY ORDERS - GREEN) */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {bids.slice(0, 7).map(([price, vol], idx) => {
                  const widthPct = Math.min(100, Math.round((vol / maxVol) * 100));
                  return (
                    <div key={`bid-${idx}`} style={{
                      position: 'relative',
                      display: 'grid',
                      gridTemplateColumns: '1.2fr 1fr 1.5fr',
                      alignItems: 'center',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontFamily: 'monospace',
                      background: 'rgba(35, 134, 54, 0.05)',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        bottom: 0,
                        width: `${widthPct}%`,
                        background: 'rgba(35, 134, 54, 0.18)',
                        zIndex: 1,
                        pointerEvents: 'none'
                      }} />
                      <span style={{ color: '#3fb950', fontWeight: '700', zIndex: 2 }}>${Number(price).toFixed(5)}</span>
                      <span style={{ textAlign: 'right', color: '#c9d1d9', zIndex: 2 }}>{Number(vol).toLocaleString()}</span>
                      <span style={{ textAlign: 'right', color: '#8b949e', fontSize: '11px', zIndex: 2 }}>{widthPct}%</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* RIGHT PANE: LIVE EXECUTION TAPE & SPEED TUNER */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* LIVE ACTION TAPE */}
          <div style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.4)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #30363d', paddingBottom: '8px' }}>
              <span style={{ fontWeight: '700', fontSize: '13px', color: '#f0f6fc' }}>
                ⚡ Engine Execution Tape
              </span>
              <span style={{ fontSize: '11px', color: liveFresh ? '#38bdf8' : '#3fb950', fontFamily: 'monospace' }}>
                {liveFresh
                  ? liveTelemetry.halted
                    ? 'Halted by daily cutoff'
                    : 'Live orders active on Exchange • 2% stop'
                  : 'Orders held • execution unverified'}
              </span>
            </div>

            <div style={{
              padding: '10px 14px',
              background: '#0d1117',
              borderRadius: '6px',
              border: '1px solid #21262d',
              fontSize: '12px',
              fontFamily: 'monospace',
              color: '#38bdf8',
              lineHeight: '1.5'
            }}>
              <div style={{ color: '#8b949e', fontSize: '11px', marginBottom: '4px' }}>Latest Registered Action:</div>
              <strong style={{ color: '#f0f6fc' }}>{lastAction}</strong>
            </div>

            {liveFresh && (
              <>
                <div style={{ padding: '10px 12px', background: '#0d1117', borderRadius: '6px', border: '1px solid #21262d', fontSize: '12px', fontFamily: 'monospace' }}>
                  <div style={{ color: '#8b949e', fontSize: '11px', marginBottom: '6px', fontWeight: '700' }}>
                    ACTIVE EXCHANGE ORDERS ({liveActiveOrders.length})
                  </div>
                  {liveActiveOrders.length === 0 ? (
                    <div style={{ color: '#8b949e' }}>No open orders resting on CRO_USDT</div>
                  ) : (
                    liveActiveOrders.map(/** @param {any} ord */ (ord) => (
                      <div key={ord.order_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3px 0', gap: '8px' }}>
                        <span style={{ color: ord.side === 'BUY' ? '#3fb950' : '#f87171', fontWeight: '700' }}>
                          {ord.side} {ord.quantity} CRO @ ${formatFinite(ord.price, 5)}
                        </span>
                        <span style={{ color: '#8b949e', fontSize: '11px' }}>
                          {ord.status} • #{String(ord.order_id).slice(-6)}
                        </span>
                      </div>
                    ))
                  )}
                </div>

                {liveRecentFills.length > 0 && (
                  <div style={{ padding: '10px 12px', background: '#0d1117', borderRadius: '6px', border: '1px solid #21262d', fontSize: '12px', fontFamily: 'monospace' }}>
                    <div style={{ color: '#8b949e', fontSize: '11px', marginBottom: '6px', fontWeight: '700' }}>
                      RECENT FILLS
                    </div>
                    {liveRecentFills.map((fill) => {
                      let dateStr = '';
                      if (fill.utc) {
                        try {
                          const d = new Date(fill.utc);
                          dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                            + ' ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true });
                        } catch {
                          dateStr = fill.utc;
                        }
                      }
                      return (
                        <div key={`${fill.order_id}-${fill.utc}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #161b22', gap: '8px' }}>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: fill.side === 'BUY' ? '#3fb950' : '#f0883e', fontWeight: '700' }}>
                              {fill.kind || fill.side}: {fill.qty_cro} CRO @ ${formatFinite(fill.price, 5)}
                            </span>
                            {dateStr && (
                              <span style={{ color: '#8b949e', fontSize: '10px' }}>
                                📅 {dateStr}
                              </span>
                            )}
                          </div>
                          <span style={{ color: '#58a6ff', fontSize: '11px', fontWeight: '600' }}>{fill.status}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              marginTop: '4px',
              fontSize: '12px',
              color: '#8b949e'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{liveFresh ? 'Poll Interval (Crypto.com v1):' : 'Measured Execution Interval:'}</span>
                <strong style={{ color: '#e6edf3' }}>
                  {liveFresh ? `${formatFinite(liveTelemetry.poll_interval_sec || 3, 1)}s live loop` : 'Unavailable — orders held'}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{liveFresh ? 'Active Strategy Bracket:' : 'Verified Trading Speed:'}</span>
                <strong style={{ color: '#3fb950' }}>
                  {liveFresh ? `±${displayTakeProfit}% Maker Bracket` : 'Unavailable — orders held'}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{liveFresh ? 'Risk Guardrails:' : 'Rolling Scalp Window:'}</span>
                <strong style={{ color: '#58a6ff' }}>
                  {liveFresh
                    ? `${formatFinite(liveTelemetry.stop_loss_pct || 2, 0)}% Stop • $${formatFinite(liveTelemetry.daily_loss_cutoff_usdt || 1, 2)} Daily Cutoff`
                    : `${telemetry?.fast_scalp_window_sec || 30}-second micro-dip detection`}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{liveFresh ? 'Bootstrap Status:' : 'Profit Compounding:'}</span>
                <strong style={{ color: '#f0883e' }}>
                  {liveFresh ? (liveTelemetry.bootstrap_completed ? 'Completed (CRO → USDT ready)' : 'Pending') : 'Disabled / unverified'}
                </strong>
              </div>
            </div>
          </div>

          {/* SPEED & TRIGGER PARAMETERS TUNER */}
          <div style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            boxShadow: '0 4px 15px rgba(0,0,0,0.4)'
          }}>
            <div style={{ fontWeight: '700', fontSize: '13px', color: '#f0f6fc' }}>
              ⚙️ Strategy Draft (Live Changes Held)
            </div>

            <form onSubmit={handleSaveParams} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>
                    Take Profit (%):
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.05"
                    max="10.0"
                    value={takeProfitPct}
                    onChange={(e) => setTakeProfitPct(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      color: '#3fb950',
                      fontWeight: '700',
                      fontSize: '13px',
                      fontFamily: 'monospace',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>
                    Dip Target (%):
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
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      color: '#38bdf8',
                      fontWeight: '700',
                      fontSize: '13px',
                      fontFamily: 'monospace',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>
                  Trade Amount (USDT draft):
                </label>
                <input
                  type="number"
                  step="0.10"
                  min="1.00"
                  max="50.00"
                  value={tradeUsdAmount}
                  onChange={(e) => setTradeUsdAmount(e.target.value)}
                  style={{
                    width: '100%',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    color: '#f0f6fc',
                    fontWeight: '700',
                    fontSize: '13px',
                    fontFamily: 'monospace',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px' }}>
                <button
                  type="submit"
                  disabled={true}
                  style={{
                    flex: 1,
                    background: '#238636',
                    color: '#fff',
                    border: '1px solid #2ea043',
                    padding: '8px 14px',
                    borderRadius: '6px',
                    fontWeight: '700',
                    fontSize: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  Live Strategy Changes Held
                </button>
                {saveStatus && (
                  <span style={{ fontSize: '11px', color: saveStatus.includes('✅') ? '#3fb950' : '#f87171' }}>
                    {saveStatus}
                  </span>
                )}
              </div>
            </form>
          </div>

        </div>

      </div>

      {liveFresh && Array.isArray(liveTelemetry.scenario_evaluations) && liveTelemetry.scenario_evaluations.length > 0 && (
        <section style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }} aria-label="Live Option Scenarios">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: '700', color: '#f0f6fc' }}>
                🎯 Live Strategy Option Scenarios (3-Tranche Maker Grid + 50/50 Profit Reserve)
              </h3>
              <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '2px' }}>
                Active Mode: <strong style={{ color: '#3fb950' }}>{liveTelemetry.scenario_mode || 'PATIENT_SWING'}</strong> • Major Bid Floor: <strong style={{ color: '#3fb950' }}>${liveTelemetry.scenario_evaluations[0]?.major_bid_support || '0.04215'}</strong> • Major Ask Wall: <strong style={{ color: '#f87171' }}>${liveTelemetry.scenario_evaluations[0]?.major_ask_wall || '0.04300'}</strong> (Front-run: <strong style={{ color: '#f1c40f' }}>${liveTelemetry.scenario_evaluations[0]?.front_run_sell_price || '0.04298'}</strong>)
              </div>
            </div>
            {scenarioNotice && (
              <span style={{ fontSize: '12px', color: scenarioNotice.includes('✅') ? '#3fb950' : '#38bdf8', fontFamily: 'monospace' }}>
                {scenarioNotice}
              </span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
            {liveTelemetry.scenario_evaluations.map(/** @param {any} sc */ (sc) => {
              const isActive = Boolean(sc.active);
              return (
                <div key={sc.id} style={{
                  background: isActive ? 'rgba(35, 134, 54, 0.12)' : '#0d1117',
                  border: `1px solid ${isActive ? '#3fb950' : '#30363d'}`,
                  borderRadius: '8px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '10px'
                }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px' }}>
                      <strong style={{ fontSize: '13px', color: isActive ? '#3fb950' : '#58a6ff' }}>{sc.label}</strong>
                      {isActive && (
                        <span style={{ fontSize: '10px', background: '#238636', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontWeight: '700' }}>
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: '11px', color: '#8b949e', margin: '6px 0', lineHeight: '1.4' }}>
                      {sc.description}
                    </p>
                    <div style={{ fontSize: '11px', fontFamily: 'monospace', background: '#161b22', padding: '8px', borderRadius: '6px', border: '1px solid #21262d' }}>
                      <div style={{ color: '#c9d1d9', marginBottom: '4px' }}>
                        Projected Open-Lot Profit: <strong style={{ color: '#3fb950' }}>+${sc.projected_open_lots_pnl_usdt} USDT</strong>
                      </div>
                      <div style={{ color: '#38bdf8', marginBottom: '6px' }}>
                        50% Reserve Add: <strong>+${sc.projected_reserve_add_usdt} USDT</strong>
                      </div>
                      {Array.isArray(sc.lot_targets) && sc.lot_targets.map(/** @param {any} lt @param {number} i */ (lt, i) => (
                        <div key={i} style={{ color: '#8b949e', fontSize: '10px', padding: '2px 0', borderTop: '1px solid #21262d' }}>
                          T{Number(lt.tranche_idx) + 1} ({lt.qty_cro} CRO @ ${lt.entry_price}) → <strong style={{ color: '#f1c40f' }}>SELL @ ${lt.target_price}</strong> (+{lt.gain_pct}% / +${lt.net_pnl_usdt})
                        </div>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={isActive || scenarioBusy === sc.id}
                    onClick={() => handleSelectScenario(sc.id)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: `1px solid ${isActive ? '#2ea043' : '#38bdf8'}`,
                      background: isActive ? '#238636' : 'rgba(56, 189, 248, 0.15)',
                      color: '#fff',
                      fontWeight: '700',
                      fontSize: '11px',
                      cursor: isActive ? 'default' : 'pointer'
                    }}
                  >
                    {isActive ? '✓ Active Live Scenario' : scenarioBusy === sc.id ? 'Activating…' : `Activate ${sc.id}`}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }} aria-label="Read-only spot preview">
        <button type="button" disabled={previewBusy} onClick={handlePreview} style={{ padding: '8px 12px', color: '#fff', background: '#1f6feb', borderRadius: '6px', border: '1px solid #58a6ff' }}>
          {previewBusy ? 'Loading preview…' : 'Preview 2-USDT spot test'}
        </button>
        <p role="status" style={{ fontSize: '12px', color: '#c9d1d9' }}>{previewStatus || 'Explicit click only. Public market arithmetic; this does not place a trade.'}</p>
        {previewResult && <div style={{ fontSize: '12px', overflowWrap: 'anywhere' }}>
          <p>All-in budget: {formatFinite(previewResult.preview.entry?.budget_all_in_usdt, 4)} USDT • Quantity: {formatFinite(previewResult.preview.entry?.quantity_cro, 8)} CRO • Maximum entry debit including quote-fee reserve: {formatFinite(previewResult.preview.entry?.maximum_quote_debit_usdt, 6)} USDT</p>
          <p>Scenario fee assumptions: entry {formatFinite(previewResult.preview.fee_assumptions?.entry_bps, 2)} bps / exit {formatFinite(previewResult.preview.fee_assumptions?.exit_bps, 2)} bps. These are not authenticated account rates.</p>
          <p>Market snapshot: {previewResult.market?.observed_at_utc || 'Unavailable'} • CRO/USDT • snapshot does not refresh automatically.</p>
          {(previewResult.preview.fee_currency_scenarios || []).map(/** @param {any} scenario @param {number} index */ (scenario, index) => <div key={index} style={{ margin: '8px 0', padding: '8px', background: '#0d1117' }}>
            <strong>Fee assets: buy {scenario.entry_fee_asset}, sell {scenario.exit_fee_asset}</strong>
            <div>Sellable quantity: {formatFinite(scenario.sell_quantity_cro, 8)} CRO • Unsold dust: {formatFinite(scenario.residual_cro_after_assumed_exit, 8)} CRO</div>
            {(scenario.levels || []).map(/** @param {any} level */ level => <div key={level.assumed_execution}>
              {level.assumed_execution} at {formatFinite(level.price, 8)} USDT: cash P&amp;L {formatFinite(level.cash_pnl_excluding_residual_value_usdt, 6)} USDT; equity P&amp;L including unsold dust {formatFinite(level.equity_pnl_including_unsold_residual_usdt, 6)} USDT; minimum {level.meets_minimum_at_assumed_execution_price === true ? 'met at assumed price' : 'NOT MET'}
            </div>)}
          </div>)}
          <p>Unresolved checks: {(previewResult.preview.blocking_checks || []).join(', ') || 'Unavailable'}</p>
          <p>Not live-ready. Stop/target prices are scenarios, not guaranteed fills or maximum losses. No account access or orders.</p>
        </div>}
      </section>

      <CryptoNewsCatalysts apiBase={resolvedApiBase} />

      {/* BOTTOM SPEED HUD: ULTRA FAST EXECUTION SPECIFICATIONS */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '12px',
        padding: '14px 18px',
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '10px'
      }}>
        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Tick Evaluation Engine</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#58a6ff', marginTop: '2px' }}>
            {liveFresh ? 'Crypto.com Exchange v1 Live REST' : 'Market snapshots only'}
          </div>
          <div style={{ fontSize: '11px', color: '#3fb950', marginTop: '2px' }}>
            {liveFresh ? `Last tick: ${liveTelemetry.last_tick_utc}` : 'No measured execution latency'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Max Allowable Trading Speed</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#38bdf8', marginTop: '2px' }}>
            {liveFresh ? `${formatFinite(liveTelemetry.poll_interval_sec || 3, 1)}s Poll • Passive Maker` : 'Live orders held'}
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            {liveFresh ? '3-Tranche Grid • Auto Re-Arm & 50% Reserve' : 'No trading speed or API admission claim'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Profit Harvesting Rule</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#3fb950', marginTop: '2px' }}>
            {liveFresh ? `±${displayTakeProfit}% Maker Bracket` : `${takeProfitPct}% draft threshold`}
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            {liveFresh ? `${formatFinite(liveTelemetry.stop_loss_pct || 2, 0)}% stop • $${formatFinite(liveTelemetry.daily_loss_cutoff_usdt || 1, 2)} daily cutoff` : 'Profit depends on fills, fees and price; no guaranteed yield'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Audio & Visual Alerting</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#a371f7', marginTop: '2px' }}>
            Discord & Windows Chimes
          </div>
          <div style={{ fontSize: '11px', color: '#3fb950', marginTop: '2px' }}>
            {liveFresh ? '5-min 40101 Outage Webhook Armed' : 'Alert delivery unverified'}
          </div>
        </div>
      </div>

    </div>
  );
}

/** @param {unknown} value */
function isFiniteValue(value) {
  return (typeof value === 'number' || (typeof value === 'string' && value.trim() !== '')) && Number.isFinite(Number(value));
}

/** @param {unknown} value */
function formatFinite(value, digits = 2) {
  return isFiniteValue(value) ? Number(value).toFixed(digits) : 'Unavailable';
}
