import React, { useState, useEffect } from 'react';
import { getApiBase } from '../../config/api.js';

const TwapControlModule = ({ apiBase, activeDrips = [], onRefresh }) => {
  const [form, setForm] = useState({
    symbol: 'SOL/USD',
    total_usd: 10.0,
    drip_size_usd: 2.0,
    drip_interval_seconds: 60
  });
  const [status, setStatus] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: name === 'symbol' ? value : parseFloat(value)
    }));
  };

  const handleLaunch = async () => {
    try {
      setStatus('Launching...');
      const res = await fetch(`${apiBase}/drip_trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      if (res.ok) {
        setStatus('Campaign Launched!');
        if (onRefresh) onRefresh();
      } else {
        setStatus('Failed to launch.');
      }
      setTimeout(() => setStatus(''), 3000);
    } catch (err) {
      setStatus('Error launching campaign.');
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.5rem' }}>
      <h3 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem', margin: 0, color: '#a8c0ff' }}>
        TWAP / Drip Controls
      </h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Symbol</label>
          <input 
            type="text" name="symbol" value={form.symbol} onChange={handleChange} 
            style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Total Campaign USD</label>
          <input 
            type="number" step="1.0" name="total_usd" value={form.total_usd} onChange={handleChange} 
            style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Drip Size (USD)</label>
          <input 
            type="number" step="1.0" name="drip_size_usd" value={form.drip_size_usd} onChange={handleChange} 
            style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Interval (Seconds)</label>
          <input 
            type="number" step="10" name="drip_interval_seconds" value={form.drip_interval_seconds} onChange={handleChange} 
            style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
          />
        </div>
      </div>

      <button 
        onClick={handleLaunch} 
        style={{ padding: '0.8rem', background: 'linear-gradient(90deg, #a8c0ff 0%, #3f2b96 100%)', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}
      >
        Launch Drip Campaign
      </button>
      {status && <div style={{ textAlign: 'center', fontSize: '0.9rem', color: status.includes('Error') || status.includes('Failed') ? '#f87171' : '#4ade80' }}>{status}</div>}

      {activeDrips.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h4 style={{ margin: '0 0 0.5rem', opacity: 0.8 }}>Active Campaigns</h4>
          {activeDrips.map((drip, i) => (
            <div key={i} style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
              <strong>{drip.symbol}</strong>: ${drip.usd_spent.toFixed(2)} / ${drip.total_usd.toFixed(2)} (${drip.drip_size_usd} every {drip.drip_interval_seconds}s)
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default function CryptoTraderTab() {
  const [telemetry, setTelemetry] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updateStatus, setUpdateStatus] = useState('');

  // The bot runs on Port 8007
  const TRADER_API_BASE = `${getApiBase()}/api/proxy/8007/api/v1`;

  const fetchData = async () => {
    try {
      const [telRes, setRes] = await Promise.all([
        fetch(`${TRADER_API_BASE}/telemetry`),
        fetch(`${TRADER_API_BASE}/settings`)
      ]);
      
      if (!telRes.ok || !setRes.ok) throw new Error("Bot Offline or Unreachable");

      const telData = await telRes.json();
      const setData = await setRes.json();

      setTelemetry(telData);
      setSettings(setData);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Trader Bot is offline. Ensure crypto_trader_bot.py is running on port 8007.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSettingChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
  };

  const saveSettings = async () => {
    try {
      setUpdateStatus('Saving...');
      const res = await fetch(`${TRADER_API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) setUpdateStatus('Saved Successfully!');
      else setUpdateStatus('Failed to Save.');
      setTimeout(() => setUpdateStatus(''), 3000);
    } catch (err) {
      setUpdateStatus('Error saving settings.');
    }
  };

  if (loading) {
    return <div style={{ padding: '2rem', color: '#00f2fe' }}>Connecting to Diamond Hand Engine...</div>;
  }

  if (error) {
    return <div style={{ padding: '2rem', color: '#ff4d4d', background: 'rgba(255,0,0,0.1)', borderRadius: '8px' }}>{error}</div>;
  }

  const { status, usd_balance, ledger } = telemetry;
  const positions = ledger?.positions || {};

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginTop: '1rem' }}>
      
      {/* LEFT COLUMN: P&L & Positions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        {/* Top KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          <div className="glass-panel" style={{ padding: '1.5rem', textAlign: 'center', borderTop: '3px solid #00f2fe' }}>
            <h4 style={{ margin: 0, opacity: 0.7 }}>Available USD</h4>
            <h2 style={{ margin: '0.5rem 0 0', color: '#fff' }}>${usd_balance?.toFixed(2)}</h2>
          </div>
          <div className="glass-panel" style={{ padding: '1.5rem', textAlign: 'center', borderTop: '3px solid #4facfe' }}>
            <h4 style={{ margin: 0, opacity: 0.7 }}>Realized Profit</h4>
            <h2 style={{ margin: '0.5rem 0 0', color: '#00f2fe' }}>+${ledger?.total_profit_usd?.toFixed(2)}</h2>
          </div>
          <div className="glass-panel" style={{ padding: '1.5rem', textAlign: 'center', borderTop: '3px solid #a8c0ff' }}>
            <h4 style={{ margin: 0, opacity: 0.7 }}>Status</h4>
            <h2 style={{ margin: '0.5rem 0 0', color: status === 'active' ? '#4ade80' : '#f87171' }}>
              {status.toUpperCase()}
            </h2>
          </div>
        </div>

        {/* Active Holdings Table */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
            Active Holdings
          </h3>
          <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ opacity: 0.7, borderBottom: '1px solid rgba(255,255,255,0.2)' }}>
                <th style={{ padding: '0.5rem' }}>Asset</th>
                <th style={{ padding: '0.5rem' }}>Amount</th>
                <th style={{ padding: '0.5rem' }}>Avg Buy Price</th>
                <th style={{ padding: '0.5rem' }}>Last Buy Price</th>
                <th style={{ padding: '0.5rem' }}>Invested USD</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(positions).length === 0 ? (
                <tr><td colSpan="5" style={{ padding: '1rem', textAlign: 'center', opacity: 0.5 }}>No active bags. Waiting for dips.</td></tr>
              ) : (
                Object.entries(positions).map(([sym, pos]) => (
                  <tr key={sym} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '0.5rem', fontWeight: 'bold' }}>{sym}</td>
                    <td style={{ padding: '0.5rem' }}>{pos.amount.toFixed(4)}</td>
                    <td style={{ padding: '0.5rem' }}>${pos.avg_buy_price.toFixed(4)}</td>
                    <td style={{ padding: '0.5rem' }}>${pos.last_buy_price.toFixed(4)}</td>
                    <td style={{ padding: '0.5rem' }}>${(pos.amount * pos.avg_buy_price).toFixed(2)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Last Action Terminal Log */}
        <div className="glass-panel" style={{ padding: '1.5rem', background: 'rgba(0,0,0,0.6)' }}>
           <h4 style={{ margin: '0 0 0.5rem', opacity: 0.7, fontFamily: 'monospace' }}>&gt; SHM LAST_ACTION_LOG</h4>
           <div style={{ color: '#00f2fe', fontFamily: 'monospace', fontSize: '1.1rem' }}>
             {ledger?.last_action || "Waiting for market movement..."}
           </div>
        </div>

      </div>

      {/* RIGHT COLUMN: Risk Controls */}
      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem', margin: 0 }}>
          Risk Controls & Strategy
        </h3>
        
        {settings && (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Buy Dip % (e.g. 0.015 = 1.5%)</label>
              <input 
                type="number" step="0.005" name="BUY_DIP_PCT" 
                value={settings.BUY_DIP_PCT} onChange={handleSettingChange} 
                style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
              />
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Take Profit % (e.g. 0.02 = 2.0%)</label>
              <input 
                type="number" step="0.005" name="TAKE_PROFIT_PCT" 
                value={settings.TAKE_PROFIT_PCT} onChange={handleSettingChange} 
                style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>USD Amount per Trade ($)</label>
              <input 
                type="number" step="1.0" name="TRADE_USD_AMOUNT" 
                value={settings.TRADE_USD_AMOUNT} onChange={handleSettingChange} 
                style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
              <label style={{ fontSize: '0.9rem', opacity: 0.8 }}>Max Cap per Coin ($)</label>
              <input 
                type="number" step="10.0" name="MAX_POSITION_USD" 
                value={settings.MAX_POSITION_USD} onChange={handleSettingChange} 
                style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', borderRadius: '4px' }} 
              />
            </div>

            <button 
              onClick={saveSettings} 
              style={{ marginTop: '1rem', padding: '0.8rem', background: 'linear-gradient(90deg, #00f2fe 0%, #4facfe 100%)', color: '#000', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Apply Hot Reload
            </button>
            {updateStatus && <div style={{ textAlign: 'center', fontSize: '0.9rem', color: updateStatus.includes('Error') ? '#f87171' : '#4ade80' }}>{updateStatus}</div>}
          </>
        )}
      </div>

      <TwapControlModule apiBase={TRADER_API_BASE} activeDrips={ledger?.twap_orders || []} onRefresh={fetchData} />


    </div>
  );
}
