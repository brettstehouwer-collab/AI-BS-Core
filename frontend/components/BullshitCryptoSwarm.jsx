import React, { useState, useEffect } from 'react';
import DaemonControl from './components/DaemonControl';
import TelemetryWidget from './components/TelemetryWidget';
import AeoTracker from './components/AeoTracker';
import CryptoTraderTab from './components/CryptoTraderTab';

import { getApiBase } from '../config/api.js';

// The Master Engine handles daemons, Crypto-Swarm handles telemetry
const DAEMONS_API_BASE = `${getApiBase()}/api/daemons`;
const TELEMETRY_API_BASE = `${getApiBase()}/api/telemetry`;

export default function BullshitCryptoSwarm() {
  const [daemons, setDaemons] = useState({});
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('swarm');

  const fetchData = async () => {
    try {
      const [statusRes, telemetryRes] = await Promise.all([
        fetch(`${DAEMONS_API_BASE}/status`).catch(() => null),
        fetch(`${getApiBase()}/telemetry/status`).catch(() => null)
      ]);
      
      if (!statusRes || !telemetryRes || !statusRes.ok || !telemetryRes.ok) {
        throw new Error("Network response was not ok");
      }

      const statusData = await statusRes.json();
      const telemetryData = await telemetryRes.json();

      setDaemons(statusData);
      setTelemetry(telemetryData);
      setError(null);
    } catch (err) {
      console.error("Crypto-Swarm polling failed", err);
      setError("Failed to connect to Crypto-Swarm daemon (Port 8001). Is the Swarm running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (daemonName, action) => {
    try {
      const res = await fetch(`${DAEMONS_API_BASE}/${daemonName}/${action}`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(`Failed to ${action} ${daemonName}`, err);
    }
  };

  if (loading) {
    return (
      <div className="system-tab-content">
        <h2>Loading Crypto-Swarm Connection...</h2>
      </div>
    );
  }

  return (
    <div className="system-tab-content">
      <div className="studio-header">
        <div className="header-left">
          <h2>Crypto-Swarm Command Center</h2>
          <span className="version-badge">Live Market Sync</span>
        </div>
        {error && <div style={{ color: '#ff4d4d', marginLeft: 'auto', marginRight: '1rem', padding: '0.5rem 1rem', background: 'rgba(255, 77, 77, 0.1)', borderRadius: '6px', border: '1px solid rgba(255, 77, 77, 0.3)' }}>{error}</div>}
      </div>

      <div className="tab-navigation" style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.5rem' }}>
        <button 
          className={`primary-btn ${activeTab === 'swarm' ? 'active' : ''}`}
          style={{ opacity: activeTab === 'swarm' ? 1 : 0.6 }}
          onClick={() => setActiveTab('swarm')}
        >
          Swarm Dashboard
        </button>
        <button 
          className={`primary-btn ${activeTab === 'advertising' ? 'active' : ''}`}
          style={{ opacity: activeTab === 'advertising' ? 1 : 0.6 }}
          onClick={() => setActiveTab('advertising')}
        >
          Advertising & AEO
        </button>
        <button 
          className={`primary-btn ${activeTab === 'trader' ? 'active' : ''}`}
          style={{ opacity: activeTab === 'trader' ? 1 : 0.6 }}
          onClick={() => setActiveTab('trader')}
        >
          Diamond Hand Trader
        </button>
      </div>
      
      {activeTab === 'swarm' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          <section className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>Daemon Fleet Control</h3>
            <DaemonControl daemons={daemons} onAction={handleAction} />
          </section>
          
          <section className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>Live Swarm Telemetry</h3>
            <TelemetryWidget data={telemetry} />
          </section>
        </div>
      )}

      {activeTab === 'advertising' && (
        <div className="glass-panel" style={{ padding: '1.5rem', marginTop: '1rem' }}>
          <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>AEO Advertising Tracker</h3>
          <AeoTracker />
        </div>
      )}

      {activeTab === 'trader' && (
        <CryptoTraderTab />
      )}
    </div>
  );
}
