import React, { useState, useEffect } from 'react';

const API_BASE = 'https://ai-bs.brettstehouwer.live/api';

export default function BullshitChiaManager() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/chia-stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    try {
      await fetch(`${API_BASE}/chia-start`, { method: 'POST' });
      fetchStats();
    } catch (err) {
      console.error(err);
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API_BASE}/chia-stop`, { method: 'POST' });
      fetchStats();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="dashboard-container">
      <div className="header">
        <div>
          <h1>Chia Farming Engine</h1>
          <p>Native RPC integration with your local Chia node.</p>
        </div>
      </div>

      {error && (
        <div className="alerts" style={{ marginBottom: '1rem' }}>
          <strong>Error connecting to backend:</strong> {error}
        </div>
      )}

      <div className="grid">
        {/* Status Panel */}
        <div className="glass-panel">
          <h2>Engine Status</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Daemon Status:</span>
              <div className="daemon-status" style={{ fontSize: '1rem' }}>
                <div className={`status-dot ${stats?.status === 'Farming' || stats?.status === 'Syncing' ? 'running' : 'stopped'}`}></div>
                {stats?.status || (loading ? 'Loading...' : 'Unknown')}
              </div>
            </div>
            
            <div className="btn-group" style={{ marginTop: '1rem' }}>
              <button 
                className="start" 
                onClick={handleStart}
                style={{ flex: 1, padding: '1rem' }}
              >
                Start Farmer
              </button>
              <button 
                className="stop" 
                onClick={handleStop}
                style={{ flex: 1, padding: '1rem' }}
              >
                Stop Engine
              </button>
            </div>
          </div>
        </div>

        {/* Telemetry Panel */}
        <div className="glass-panel" style={{ gridColumn: 'span 2' }}>
          <h2>Farming Telemetry</h2>
          <div className="telemetry-grid">
            <div className="widget-stat">
              <span className="label">Total Plots</span>
              <span className="value highlight">{stats?.total_plots || '0'}</span>
            </div>
            
            <div className="widget-stat">
              <span className="label">Plot Size</span>
              <span className="value">{stats?.plot_size || '0 GiB'}</span>
            </div>

            <div className="widget-stat">
              <span className="label">Time to Win</span>
              <span className="value">{stats?.estimated_time_to_win || 'Unknown'}</span>
            </div>

            <div className="widget-stat">
              <span className="label">Total Farmed</span>
              <span className="value success">{stats?.total_chia_farmed || '0.0'} XCH</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
