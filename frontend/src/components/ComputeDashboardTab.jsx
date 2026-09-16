import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api.js';
import './DeveloperWorkspaceTab.css'; // Reuse existing styles for consistency

export default function ComputeDashboardTab() {
  const [telemetry, setTelemetry] = useState(null);
  const [status, setStatus] = useState("loading");

  const toggleHosting = async (newMode) => {
    try {
      await fetch(`${getApiBase()}/api/compute/toggle_mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode })
      });
      setStatus(newMode); // Optimistic update
    } catch (err) {
      console.error("Failed to toggle hosting mode:", err);
    }
  };

  useEffect(() => {
    fetch(`${getApiBase()}/api/daemons/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ daemon: 'compute_monetization_daemon' })
    }).catch(err => console.error("Failed to start compute daemon:", err));
    
    // We intentionally DO NOT stop the daemon on unmount.
    // Passive monetization requires it to run 24/7 in the background.
  }, []);

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`${getApiBase()}/api/compute/status`);
        const data = await res.json();
        
        if (data.status === "waiting" || data.status === "error") {
          setStatus(data.status);
          setTelemetry(null);
        } else {
          setTelemetry(data);
          setStatus(data.status);
        }
      } catch (e) {
        setStatus("error");
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 3000); // Fast 3-second polling for live earning updates
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="developer-workspace-tab">
      <div className="header-bar">
        <h2>🧠 AI Compute Monetization Engine (Vast.ai / Clore.ai)</h2>
        <div className={`status-badge ${status === 'renting' ? 'healthy' : (status === 'paused' ? 'warning' : 'critical')}`}>
          {status === 'renting' ? 'ACTIVE WORKLOAD' : status === 'not_installed' ? 'OFFLINE' : (status || 'UNKNOWN').toUpperCase()}
        </div>
        <button 
          className="primary-btn" 
          style={{ marginLeft: 'auto', background: status === 'paused' ? '#98c379' : '#e5c07b', color: '#000', fontWeight: 'bold' }}
          onClick={() => toggleHosting(status === 'paused' ? 'active' : 'paused')}
        >
          {status === 'paused' ? '▶ Resume Hosting' : '⏸ Pause Hosting'}
        </button>
      </div>

      {status === 'not_installed' ? (
        <div style={{ padding: "40px", textAlign: "center", color: "#e5e5e5" }}>
          <h2 style={{ color: "#e06c75", marginBottom: "15px" }}>Vast.ai / Clore.ai Host is Not Detected</h2>
          <p style={{ fontSize: "1.1rem", marginBottom: "20px" }}>
            The compute telemetry daemon cannot detect the WSL2 hosting applications on your machine.
            To begin monetizing your RTX 4090, you must configure the Master Schedule.
          </p>
        </div>
      ) : (
      <div className="split-view" style={{flexDirection: "column", padding: "20px", gap: "20px", overflowY: "auto"}}>
        
        {/* Earnings Ticker Panel */}
        <div className="console-panel" style={{flex: "none", borderColor: "#98c379"}}>
          <div className="panel-header" style={{color: "#98c379"}}>Revenue Tracker (USD)</div>
          <div className="panel-content" style={{display: "flex", gap: "30px"}}>
             <div className="metric-box">
                <span className="metric-label">Today</span>
                <span className="metric-value" style={{color: "#98c379"}}>
                  ${telemetry?.earnings?.today_usd ? telemetry.earnings.today_usd.toFixed(4) : "0.0000"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">This Week</span>
                <span className="metric-value" style={{color: "#98c379"}}>
                  ${telemetry?.earnings?.this_week_usd ? telemetry.earnings.this_week_usd.toFixed(4) : "0.0000"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">All-Time Yield</span>
                <span className="metric-value">
                  ${telemetry?.earnings?.all_time_usd ? telemetry.earnings.all_time_usd.toFixed(2) : "0.00"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Active Uptime</span>
                <span className="metric-value">
                  {telemetry?.earnings?.active_time_minutes ? telemetry.earnings.active_time_minutes.toFixed(1) : "0.0"} mins
                </span>
             </div>
          </div>
        </div>

        {/* Current Job & Hardware Panel */}
        <div className="console-panel" style={{flex: "none"}}>
          <div className="panel-header">RTX 4090 Workload Status</div>
          <div className="panel-content" style={{display: "flex", gap: "20px", flexWrap: "wrap"}}>
             <div className="metric-box" style={{minWidth: "250px"}}>
                <span className="metric-label">Current AI Client Job</span>
                <span className="metric-value" style={{fontSize: "1.1rem", color: "#61afef"}}>
                  {telemetry?.current_job || "Awaiting Payload..."}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">Core Load</span>
                <span className={`metric-value ${telemetry?.gpu_metrics?.utilization_pct > 90 ? 'text-critical' : ''}`}>
                  {telemetry?.gpu_metrics?.utilization_pct !== undefined ? `${telemetry.gpu_metrics.utilization_pct}%` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">VRAM Allocation</span>
                <span className="metric-value">
                  {telemetry?.gpu_metrics?.vram_used_gb !== undefined ? `${telemetry.gpu_metrics.vram_used_gb} GB / 24 GB` : "--"}
                </span>
             </div>
             <div className="metric-box">
                <span className="metric-label">GPU Core Temp</span>
                <span className={`metric-value ${telemetry?.gpu_metrics?.temp_c > 80 ? 'text-critical' : ''}`}>
                  {telemetry?.gpu_metrics?.temp_c !== undefined ? `${telemetry.gpu_metrics.temp_c} °C` : "--"}
                </span>
             </div>
          </div>
        </div>

        {/* Alerts Log */}
        <div className="console-panel" style={{flex: 1, minHeight: "200px"}}>
          <div className="panel-header">System Events & Pauses</div>
          <div className="panel-content" style={{fontFamily: "monospace"}}>
            {telemetry?.alerts && telemetry.alerts.length > 0 ? (
               telemetry.alerts.map((a, i) => <div key={i} style={{color: "#e5c07b"}}>[{new Date(telemetry.timestamp * 1000).toLocaleTimeString()}] {a}</div>)
            ) : (
               <div style={{color: "#5c6370"}}>[{new Date().toLocaleTimeString()}] Engine running flawlessly. No active pauses or thermal alerts.</div>
            )}
          </div>
        </div>

      </div>
      )}
      
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
        .status-badge.warning {
          background-color: #e5c07b;
          color: #1e1e1e;
        }
        .status-badge.critical {
          background-color: #e06c75;
          color: #1e1e1e;
        }
      `}</style>
    </div>
  );
}
