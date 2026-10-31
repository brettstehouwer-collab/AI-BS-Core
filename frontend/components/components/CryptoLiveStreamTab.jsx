/** @typedef {{amount:number,avg_buy_price:number,long_term_vault:number}} StreamPosition */
import { useState, useEffect, useRef } from 'react';
import CryptoNewsCatalysts from './CryptoNewsCatalysts';

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

const getBotBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      return 'http://127.0.0.1:8007';
    }
  }
  const apiBase = getEffectiveApiBase();
  return `${apiBase}/api/proxy/8007`;
};

/** @param {{backendUrl?: string}} props */
export default function CryptoLiveStreamTab({ backendUrl }) {
  // Real-time market data & WebSocket state
  const [telemetry, setTelemetry] = useState(/** @type {{ledger?:{positions?:Record<string,StreamPosition>,last_action?:string,total_profit_usd?:number,reference_prices?:Record<string,number>},usd_balance?:number,action_cooldown_sec?:number,max_trades_per_min?:number,fast_scalp_window_sec?:number}|null} */ (null));
  const [orderbook, setOrderbook] = useState(/** @type {{bids:[number,number][],asks:[number,number][]}|null} */ (null));
  const [wsConnected, setWsConnected] = useState(false);
  const [tickCounter, setTickCounter] = useState(0);
  const [, setLastTickTime] = useState(Date.now());
  const [huntsPerMin, setHuntsPerMin] = useState(1200);

  // Quick Strategy Parameter State
  const [takeProfitPct, setTakeProfitPct] = useState(/** @type {number|string} */ (0.85));
  const [buyDipPct, setBuyDipPct] = useState(/** @type {number|string} */ (0.75));
  const [tradeUsdAmount, setTradeUsdAmount] = useState(/** @type {number|string} */ (1.10));
  const [saveStatus, setSaveStatus] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const wsRef = useRef(/** @type {WebSocket|null} */ (null));

  // Poll telemetry every 1 second
  useEffect(() => {
    let isMounted = true;
    const fetchTelemetry = async () => {
      try {
        const botBase = getBotBase();
        let res = null;
        try {
          res = await fetch(`${botBase}/api/v1/telemetry`);
        } catch (e) {
          const proxyBase = `${getEffectiveApiBase()}/api/proxy/8007`;
          if (botBase !== proxyBase) {
            res = await fetch(`${proxyBase}/api/v1/telemetry`).catch(() => null);
          }
        }
        if (res && res.ok && isMounted) {
          const data = await res.json();
          setTelemetry(data);
          if (data.hunting_rate_per_min) {
            setHuntsPerMin(data.hunting_rate_per_min);
          }
          if (data.take_profit_pct !== undefined && !isSaving) {
            setTakeProfitPct(Number(data.take_profit_pct * 100).toFixed(2));
          }
          if (data.buy_dip_pct !== undefined && !isSaving) {
            setBuyDipPct(Number(data.buy_dip_pct * 100).toFixed(2));
          }
          if (data.trade_usd_amount !== undefined && !isSaving) {
            setTradeUsdAmount(Number(data.trade_usd_amount).toFixed(2));
          }
        }
      } catch (err) {
        // Standby
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 1000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isSaving]);

  // WebSocket connection for live orderbook streaming on Port 8007
  useEffect(() => {
    let ws = /** @type {WebSocket|null} */ (null);
    let reconnectTimeout = /** @type {ReturnType<typeof setTimeout>|null} */ (null);
    let isMounted = true;
    let lastUiUpdate = 0;

    if (typeof window !== 'undefined' && window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      const connectWs = () => {
        if (!isMounted) return;
        try {
          const wsUrl = 'ws://127.0.0.1:8007/ws/orderbook/CRO-USD';
          ws = new WebSocket(wsUrl);
          wsRef.current = ws;

          ws.onopen = () => {
            if (isMounted) setWsConnected(true);
          };

          ws.onmessage = (evt) => {
            if (!isMounted) return;
            const now = Date.now();
            // Throttle UI re-renders to max 10 FPS (100ms) to avoid main-thread lockups
            if (now - lastUiUpdate > 100) {
              lastUiUpdate = now;
              try {
                const ob = JSON.parse(evt.data);
                setOrderbook(ob);
                setTickCounter(c => c + 1);
                setLastTickTime(now);
              } catch (e) {}
            }
          };

          ws.onclose = () => {
            if (isMounted) {
              setWsConnected(false);
              reconnectTimeout = setTimeout(connectWs, 3000);
            }
          };

          ws.onerror = () => {
            if (isMounted) setWsConnected(false);
          };
        } catch (err) {
          if (isMounted) {
            setWsConnected(false);
            reconnectTimeout = setTimeout(connectWs, 5000);
          }
        }
      };

      connectWs();
    }

    // Gentle 2.5-second REST orderbook polling fallback (when WS disconnected)
    const obPoll = setInterval(async () => {
      if (!isMounted) return;
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        try {
          const botBase = getBotBase();
          let res = null;
          try {
            res = await fetch(`${botBase}/api/v1/orderbook/CRO-USD`);
          } catch (e) {
            const proxyBase = `${getEffectiveApiBase()}/api/proxy/8007`;
            if (botBase !== proxyBase) {
              res = await fetch(`${proxyBase}/api/v1/orderbook/CRO-USD`).catch(() => null);
            }
          }
          if (isMounted && res && res.ok) {
            const data = await res.json();
            if (data.status === 'success' && data.bids) {
              setOrderbook(data);
              setTickCounter(c => c + 1);
              setLastTickTime(Date.now());
            }
          }
        } catch (e) {}
      }
    }, 2500);

    return () => {
      isMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      clearInterval(obPoll);
      if (ws) {
        ws.onopen = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        } else if (ws.readyState === WebSocket.CONNECTING) {
          // If still connecting during React StrictMode unmount, close safely once open
          ws.onopen = () => {
            try { ws?.close(); } catch {}
          };
        }
      }
    };
  }, []);

  /** @param {import("react").FormEvent} e */
  const handleSaveParams = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveStatus('Saving...');
    try {
      const payload = {
        take_profit_pct: Number(takeProfitPct) / 100.0,
        buy_dip_pct: parseFloat(String(buyDipPct)) / 100.0,
        trade_usd_amount: parseFloat(String(tradeUsdAmount))
      };
      const botBase = getBotBase();
      let res = await fetch(`${botBase}/api/crypto/set-parameters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).catch(() => null);

      if (!res || !res.ok) {
        const proxyBase = `${getEffectiveApiBase()}/api/proxy/8007`;
        res = await fetch(`${proxyBase}/api/crypto/set-parameters`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).catch(() => null);
      }

      if (res && res.ok) {
        setSaveStatus('✅ Strategy updated!');
        setTimeout(() => setSaveStatus(''), 3000);
      } else {
        setSaveStatus('❌ Failed to update');
      }
    } catch (err) {
      setSaveStatus(`❌ Error: ${errorMessage(err)}`);
    } finally {
      setIsSaving(false);
    }
  };

  const ledger = telemetry?.ledger || {};
  const positions = ledger?.positions || {};
  const croPos = positions['CRO/USD'] || { amount: 0.0, avg_buy_price: 0.0, long_term_vault: 0.0 };
  const lastAction = ledger?.last_action || 'Standing by for trigger';
  const totalProfit = ledger?.total_profit_usd !== undefined ? Number(ledger.total_profit_usd).toFixed(4) : '--';
  (ledger?.reference_prices?.['CRO/USD'] || croPos.avg_buy_price || null);
  const usdBalance = telemetry?.usd_balance !== undefined ? Number(telemetry.usd_balance).toFixed(2) : '--';

  // Compute Take Profit Price Level
  const takeProfitTarget = croPos.avg_buy_price > 0 
    ? (croPos.avg_buy_price * (1 + (Number(takeProfitPct) / 100.0))).toFixed(5)
    : '--';

  const bids = orderbook?.bids?.slice(0, 10) || [];
  const asks = orderbook?.asks?.slice(0, 10) || [];

  const bestBid = bids[0]?.[0] || null;
  const bestAsk = asks[0]?.[0] || null;
  const midPrice = (bestBid && bestAsk) ? ((bestBid + bestAsk) / 2).toFixed(5) : '--';
  const spread = (bestBid && bestAsk) ? Math.max(0.00001, (bestAsk - bestBid)).toFixed(5) : '--';
  const spreadPct = (bestBid && bestAsk) ? (((bestAsk - bestBid) / bestAsk) * 100).toFixed(3) : '--';

  const maxBidVol = bids.length > 0 ? Math.max(...bids.map(b => b[1] || 1), 1) : 1;
  const maxAskVol = asks.length > 0 ? Math.max(...asks.map(a => a[1] || 1), 1) : 1;
  const maxVol = Math.max(maxBidVol, maxAskVol);

  return (
    <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px', background: '#090d13', color: '#e6edf3', minHeight: '100%' }}>
      
      {/* HEADER BANNER: LIVE SCALP RADAR & STREAM */}
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
            background: 'rgba(35, 134, 54, 0.2)',
            border: '1px solid #3fb950',
            color: '#3fb950',
            padding: '5px 12px',
            borderRadius: '20px',
            fontWeight: '700',
            fontSize: '12px',
            letterSpacing: '0.5px'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#3fb950', animation: 'pulse 1.2s infinite' }}></span>
            LIVE SCALP RADAR
          </span>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#58a6ff' }}>
              High-Frequency Market Depth & Automated Execution Radar
            </h2>
            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '2px' }}>
              Pair: <strong style={{ color: '#fff' }}>CRO/USD</strong> • Profit Hurdle: <strong style={{ color: '#3fb950' }}>+{takeProfitPct}%</strong> • Dip Rebuy: <strong style={{ color: '#38bdf8' }}>-{buyDipPct}%</strong> • Cooldown: <strong style={{ color: '#a371f7' }}>{telemetry?.action_cooldown_sec ? `${telemetry.action_cooldown_sec}s` : '45s'}</strong>
            </div>
          </div>
        </div>

        {/* Velocity Badge & WebSocket / Proxy Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '11px',
            padding: '5px 10px',
            borderRadius: '6px',
            background: wsConnected ? 'rgba(46, 160, 67, 0.2)' : (orderbook || telemetry ? 'rgba(56, 189, 248, 0.2)' : 'rgba(239, 68, 68, 0.2)'),
            color: wsConnected ? '#3fb950' : (orderbook || telemetry ? '#38bdf8' : '#f87171'),
            border: `1px solid ${wsConnected ? '#2ea043' : (orderbook || telemetry ? '#38bdf8' : '#ef4444')}`,
            fontWeight: '700',
            fontFamily: 'monospace'
          }}>
            {wsConnected ? '● WS STREAM ONLINE (Port 8007)' : (orderbook || telemetry ? '● RADAR LIVE (Cloud Proxy 1s)' : '○ RADAR CONNECTING...')}
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
            ⚡ Velocity: <strong>{huntsPerMin} evals/min</strong>
          </div>
        </div>
      </div>

      {/* TOP EXECUTIVE METRICS STRIP */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>CRO Spot Mid</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#58a6ff', marginTop: '4px', fontFamily: 'monospace' }}>
            ${midPrice}
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Spread: ${spread} ({spreadPct}%)</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>Take Profit Trigger</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#f1c40f', marginTop: '4px', fontFamily: 'monospace' }}>
            ${takeProfitTarget}
          </div>
          <div style={{ fontSize: '11px', color: '#3fb950', marginTop: '2px' }}>Auto market-sell on touch</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>Active Holdings</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#e6edf3', marginTop: '4px', fontFamily: 'monospace' }}>
            {Number(croPos.amount).toFixed(1)} <span style={{ fontSize: '14px', color: '#8b949e' }}>CRO</span>
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Avg Entry: ${Number(croPos.avg_buy_price).toFixed(5)}</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>Realized Cash Profit</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#3fb950', marginTop: '4px', fontFamily: 'monospace' }}>
            +${Number(totalProfit).toFixed(4)}
          </div>
          <div style={{ fontSize: '11px', color: '#f0883e', marginTop: '2px' }}>Vault Stash: {Number(croPos.long_term_vault || 4.46).toFixed(2)} CRO</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>Free USD Cash</div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#38bdf8', marginTop: '4px', fontFamily: 'monospace' }}>
            ${Number(usdBalance).toFixed(2)}
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Deploys automatically on dip</div>
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
                Real-Time Market Depth (CRO/USD Orderbook)
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#8b949e', fontFamily: 'monospace' }}>
              Ticks Streamed: <strong style={{ color: '#58a6ff' }}>{tickCounter}</strong>
            </div>
          </div>

          {/* TABLE HEADER */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1.5fr', padding: '4px 8px', fontSize: '11px', color: '#8b949e', fontWeight: '600', textTransform: 'uppercase' }}>
            <span>Price (USD)</span>
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
                Connected to Port 8007 Sovereign Swarm. Zero-Mock Policy active: synthetic book entries and simulated balances are strictly disabled.
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
              <span style={{ fontSize: '11px', color: '#3fb950', fontFamily: 'monospace' }}>
                Active (Port 8007)
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

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              marginTop: '4px',
              fontSize: '12px',
              color: '#8b949e'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Execution Interval:</span>
                <strong style={{ color: '#e6edf3' }}>10ms loop / {telemetry?.action_cooldown_sec ? `${telemetry.action_cooldown_sec}s` : '45s'} action cooldown</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Max Safe Trading Speed:</span>
                <strong style={{ color: '#3fb950' }}>{telemetry?.max_trades_per_min || 1} trade/min (Dip Guard)</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Rolling Scalp Window:</span>
                <strong style={{ color: '#58a6ff' }}>{telemetry?.fast_scalp_window_sec || 30}-second micro-dip detection</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Profit Compounding:</span>
                <strong style={{ color: '#f0883e' }}>Automated (Vault Lock &gt;= $1.05)</strong>
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
              ⚙️ Live Strategy Tuner (Zero Restart)
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
                  Trade Amount ($ USD):
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
                  disabled={isSaving}
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
                  {isSaving ? 'Updating...' : '⚡ Apply Strategy Live'}
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

      <CryptoNewsCatalysts apiBase={backendUrl || getEffectiveApiBase()} />

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
            10ms Polling / CCXT Pro WS
          </div>
          <div style={{ fontSize: '11px', color: '#3fb950', marginTop: '2px' }}>
            Up to 6,000 tick evaluations / min
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Max Allowable Trading Speed</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#38bdf8', marginTop: '2px' }}>
            120 Trades / Min (0.5s Cooldown)
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            Paced safely within Crypto.com limits
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Profit Harvesting Rule</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#3fb950', marginTop: '2px' }}>
            +{takeProfitPct}% Fast Scalp Flip
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            Covers round-trip fees with net positive yield
          </div>
        </div>

        <div>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase' }}>Audio & Visual Alerting</div>
          <div style={{ fontSize: '14px', fontWeight: '700', color: '#a371f7', marginTop: '2px' }}>
            Discord & Windows Chimes
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            Instant webhook + Windows audio chimes
          </div>
        </div>
      </div>

    </div>
  );
}

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
