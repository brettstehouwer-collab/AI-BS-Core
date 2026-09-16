import React, { useState, useEffect } from 'react';
import './DeveloperWorkspaceTab.css'; // Reuse existing styles for consistency

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

export default function MiningDashboardTab() {
  const [telemetry, setTelemetry] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const daemons = ['minerwatch_daemon', 'drip_trader_daemon', 'chia_plotter_daemon'];
    const apiBase = getEffectiveApiBase();
    
    daemons.forEach(d => {
      fetch(`${apiBase}/api/daemons/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ daemon: d })
      }).catch(err => console.error(`Failed to start ${d}:`, err));
    });
  }, []);

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const apiBase = getEffectiveApiBase();
        const [miningRes, walletRes, ledgerRes] = await Promise.all([
          fetch(`${apiBase}/api/mining/status`),
          fetch(`${apiBase}/api/wallet/status`).catch(() => null),
          fetch(`${apiBase}/api/trading/ledger`).catch(() => null)
        ]);
        
        const data = await miningRes.json();
        const walletData = walletRes ? await walletRes.json() : null;
        const ledgerData = ledgerRes ? await ledgerRes.json() : null;
        
        if (walletData && walletData.status !== "error") {
          data.wallet_status = walletData.wallet_status;
        }

        if (data.status === "waiting" || data.status === "error") {
          setStatus(data.status);
          setTelemetry(null);
        } else {
          setTelemetry(data);
          if (ledgerData && ledgerData.status === "active") {
            setLedger(ledgerData.trades);
          } else {
            setLedger([]);
          }
          setStatus("active");
          
          // Trigger Thoughtful Friction if alerts are present
          if (data.alerts && data.alerts.length > 0) {
            // Local simulation of Thoughtful Friction modal
            const proceed = window.confirm(`⛏️ THOUGHTFUL FRICTION: SYSTEM PAUSED\n\nMining Alert: ${data.alerts.join(", ")}\n\nWould you like to execute the Aegis mitigation script to lower power limits?`);
            if (proceed) {
                // Execute mitigation
                await fetch(`${apiBase}/api/mining/mitigate`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ action: "lower_power", target: "all" })
                });
            }
          }
        }
      } catch (e) {
        setStatus("error");
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="developer-workspace-tab">
      <div className="header-bar">
        <h2>⛏️ Aegis MinerWatch Dashboard</h2>
        <div className={`status-badge ${status === 'active' && (!telemetry?.alerts?.length) ? 'healthy' : (telemetry?.alerts?.length ? 'critical' : status)}`}>
          {status === 'active' ? (telemetry?.alerts?.length ? 'ALERTS ACTIVE' : 'SYSTEM HEALTHY') : (status || 'UNKNOWN').toUpperCase()}
        </div>
      </div>

      <div className="split-view" style={{flexDirection: "column", padding: "20px", gap: "20px", overflowY: "auto"}}>
        
        {/* ASIC Branch */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">ASIC Branch (AwesomeMiner)</div>
          <div className="panel-content" style={{display: "flex", gap: "20px"}}>
             <div className="metric-box">
                <span className="metric-label">Status</span>
                <span className="metric-value">{telemetry?.asic_status?.status || "--"}</span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Temperature</span>
                <span className={`metric-value ${telemetry?.asic_status?.temp > 80 ? 'text-critical' : ''}`}>
                  {telemetry?.asic_status?.temp ? `${telemetry.asic_status.temp} °C` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Hashrate</span>
                <span className="metric-value">{telemetry?.asic_status?.hashrate_th ? `${telemetry.asic_status.hashrate_th} TH/s` : "--"}</span>
             </div>
          </div>
        </div>

        {/* GPU Branch */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">GPU Branch (HiveOS / T-Rex)</div>
          <div className="panel-content" style={{display: "flex", gap: "20px"}}>
             <div className="metric-box">
                <span className="metric-label">Status</span>
                <span className="metric-value">{telemetry?.gpu_status?.status || "--"}</span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Temperature</span>
                <span className={`metric-value ${telemetry?.gpu_status?.temp > 80 ? 'text-critical' : ''}`}>
                  {telemetry?.gpu_status?.temp ? `${telemetry.gpu_status.temp} °C` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Hashrate</span>
                <span className="metric-value">{telemetry?.gpu_status?.hashrate_mh ? `${telemetry.gpu_status.hashrate_mh} MH/s` : "--"}</span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Power Draw</span>
                <span className="metric-value">{telemetry?.gpu_status?.power_w ? `${telemetry.gpu_status.power_w} W` : "--"}</span>
             </div>
          </div>
        </div>

        {/* Storage Branch */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">Storage Branch (Chia)</div>
          <div className="panel-content" style={{display: "flex", gap: "20px"}}>
             <div className="metric-box">
                <span className="metric-label">Status</span>
                <span className="metric-value">{telemetry?.storage_status?.status || "--"}</span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Plot Progress</span>
                <span className="metric-value">
                  {telemetry?.storage_status?.plot_progress_pct ? `${telemetry.storage_status.plot_progress_pct}%` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Capacity</span>
                <span className="metric-value">{telemetry?.storage_status?.capacity_tb ? `${telemetry.storage_status.capacity_tb} TB` : "--"}</span>
             </div>
          </div>
        </div>

        {/* System Host Metrics (SQLite) */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">Host Node (VRAM & CPU)</div>
          <div className="panel-content" style={{display: "flex", gap: "20px", flexWrap: "wrap"}}>
             <div className="metric-box">
                <span className="metric-label">Allocated VRAM</span>
                <span className="metric-value">
                  {telemetry?.system_stats?.vram_allocated_mb ? `${(telemetry.system_stats.vram_allocated_mb / 1024).toFixed(2)} GB` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">System RAM</span>
                <span className="metric-value">
                  {telemetry?.system_stats?.system_ram_mb ? `${(telemetry.system_stats.system_ram_mb / 1024).toFixed(2)} GB` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Active CPU Cores</span>
                <span className="metric-value">
                  {telemetry?.system_stats?.cpu_thread_utilization ? Object.keys(telemetry.system_stats.cpu_thread_utilization).length : "--"}
                </span>
             </div>
             {telemetry?.system_stats_error && (
                 <div className="metric-box" style={{borderColor: "#e06c75"}}>
                    <span className="metric-label text-critical">DB Error</span>
                    <span className="metric-value" style={{fontSize:"1rem"}}>{telemetry.system_stats_error}</span>
                 </div>
             )}
          </div>
        </div>

        {/* Alerts Log */}
        <div className="console-panel" style={{flex: 1, minHeight: "200px"}}>
          <div className="panel-header">Aegis Alerts Log</div>
          <div className="panel-content" style={{fontFamily: "monospace", color: "#e06c75"}}>
            {telemetry?.alerts && telemetry.alerts.length > 0 ? (
               telemetry.alerts.map((a, i) => <div key={i}>[{telemetry.timestamp}] {a}</div>)
            ) : (
               <div style={{color: "#98c379"}}>[{telemetry?.timestamp || new Date().toISOString()}] No active alerts.</div>
            )}
          </div>
        </div>

        {/* Wallet Tracker Branch */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">Wallet Tracker (DOGE)</div>
          <div className="panel-content" style={{display: "flex", gap: "20px"}}>
             <div className="metric-box">
                <span className="metric-label">Status</span>
                <span className="metric-value">{telemetry?.wallet_status?.status || "--"}</span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Confirmed Balance</span>
                <span className="metric-value">
                  {telemetry?.wallet_status?.balance_doge !== undefined ? `${telemetry.wallet_status.balance_doge} DOGE` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Unconfirmed Balance</span>
                <span className="metric-value">
                  {telemetry?.wallet_status?.unconfirmed_balance_doge !== undefined ? `${telemetry.wallet_status.unconfirmed_balance_doge} DOGE` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Total Transactions</span>
                <span className="metric-value">
                  {telemetry?.wallet_status?.tx_count !== undefined ? telemetry.wallet_status.tx_count : "--"}
                </span>
             </div>
          </div>
        </div>
        
        {/* Trade Activity Feed */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">Swarm Trading Ledger (Recent)</div>
          <div className="panel-content" style={{fontFamily: "monospace", color: "#61afef", maxHeight: "150px", overflowY: "auto"}}>
            {ledger && ledger.length > 0 ? (
               <table style={{width: "100%", textAlign: "left", borderCollapse: "collapse"}}>
                 <thead>
                   <tr style={{color: "#888", fontSize: "0.8rem"}}>
                     <th style={{paddingBottom: "8px"}}>Timestamp</th>
                     <th style={{paddingBottom: "8px"}}>Type</th>
                     <th style={{paddingBottom: "8px"}}>Asset</th>
                     <th style={{paddingBottom: "8px"}}>USD Value</th>
                   </tr>
                 </thead>
                 <tbody>
                   {ledger.map((trade, i) => (
                     <tr key={i} style={{borderBottom: "1px solid rgba(255,255,255,0.05)"}}>
                       <td style={{padding: "4px 0"}}>{new Date(trade.timestamp).toLocaleString()}</td>
                       <td style={{padding: "4px 0", color: trade.type === "sell_bootstrap" ? "#e06c75" : "#98c379"}}>{(trade.type || 'UNKNOWN').toUpperCase()}</td>
                       <td style={{padding: "4px 0"}}>{trade.coin_amount ? trade.coin_amount.toFixed(4) : "--"}</td>
                       <td style={{padding: "4px 0"}}>${trade.usd_value ? trade.usd_value.toFixed(2) : "--"}</td>
                     </tr>
                   ))}
                 </tbody>
               </table>
            ) : (
               <div style={{color: "#888"}}>[System] No recent trades executed. Awaiting market conditions.</div>
            )}
          </div>
        </div>

      </div>
      
      {/* Basic inline styles for the metric boxes since they are new */}
      <style>{`
        .metric-box {
          background: rgba(0, 0, 0, 0.2);
          padding: 10px 20px;
          border-radius: 4px;
          border: 1px solid rgba(255,255,255,0.05);
          display: flex;
          flex-direction: column;
          min-width: 120px;
        }
        .metric-label {
          font-size: 0.8rem;
          color: #888;
          text-transform: uppercase;
        }
        .metric-value {
          font-size: 1.4rem;
          font-weight: 500;
          color: #e5e5e5;
          margin-top: 5px;
        }
        .text-critical {
          color: #e06c75;
          font-weight: bold;
        }
        .status-badge.critical {
          background-color: #e06c75;
          color: #1e1e1e;
        }
      `}</style>
    </div>
  );
}
