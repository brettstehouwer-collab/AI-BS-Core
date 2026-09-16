import React, { useState } from 'react';

export default function BullshitPanicButton() {
  const [panicPassword, setPanicPassword] = useState('');
  const [panicLoading, setPanicLoading] = useState(false);
  const [panicError, setPanicError] = useState(null);
  const [panicLogs, setPanicLogs] = useState(null);

  const handlePanicExecute = async () => {
    setPanicLoading(true);
    setPanicError(null);
    setPanicLogs(null);
    try {
      const res = await fetch('http://localhost:8000/api/crypto/liquidate_all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: panicPassword })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Liquidation failed");
      }
      setPanicLogs(data.logs);
    } catch (err) {
      setPanicError(err.message);
    } finally {
      setPanicLoading(false);
    }
  };

  return (
    <div className="system-tab-content">
      <div className="studio-header" style={{ borderBottom: '1px solid rgba(255, 77, 77, 0.3)' }}>
        <div className="header-left">
          <h2 style={{ color: '#ff4d4d' }}>? EMERGENCY LIQUIDATION PROTOCOL</h2>
          <span className="version-badge" style={{ background: '#ff4d4d', color: 'white' }}>NUKESITE ACTIVE</span>
        </div>
      </div>
      
      <div className="glass-panel" style={{ padding: '2rem', marginTop: '2rem', border: '1px solid rgba(255, 77, 77, 0.3)' }}>
        <p style={{ marginBottom: '1.5rem', color: 'rgba(255,255,255,0.7)' }}>
          Warning: Executing this command will force a market sell order for every non-USD asset held on the connected exchange, ignoring all strategy limits.
        </p>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <input 
            type="password" 
            placeholder="Enter Authorization Code..." 
            value={panicPassword}
            onChange={(e) => setPanicPassword(e.target.value)}
            className="system-input"
            style={{ width: '300px' }}
          />
          <button 
            className="primary-btn" 
            style={{ background: '#ff4d4d', color: 'white', fontWeight: 'bold' }}
            onClick={handlePanicExecute}
            disabled={panicLoading || !panicPassword}
          >
            {panicLoading ? 'EXECUTING...' : 'FORCE LIQUIDATION'}
          </button>
        </div>
        
        {panicError && (
          <div style={{ color: '#ff4d4d', padding: '1rem', background: 'rgba(255, 77, 77, 0.1)', borderRadius: '4px', border: '1px solid rgba(255, 77, 77, 0.3)' }}>
            <strong>ACCESS DENIED:</strong> {panicError}
          </div>
        )}

        {panicLogs && (
          <div style={{ marginTop: '1.5rem' }}>
            <h4>Execution Logs:</h4>
            <pre style={{ background: '#1a1a1a', padding: '1rem', borderRadius: '4px', border: '1px solid #333', overflowX: 'auto', color: '#00ff00', fontSize: '13px' }}>
              {panicLogs}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
