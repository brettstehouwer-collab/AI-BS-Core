import { useState } from 'react';

/** Standalone OmniDrive view; selected files and relocation drafts stay local.
 * @param {{BACKEND_URL?: string}} props
 */
export default function OmniDriveExplorer({ BACKEND_URL = '' }) {
  const [odQuery, setOdQuery] = useState('');
  const [odResults, setOdResults] = useState(/** @type {Array<{drive: string, filename: string, filepath: string}>} */ ([]));
  const [odIsSearching, setOdIsSearching] = useState(false);
  const [odDestination, setOdDestination] = useState('');
    const handleOdSearch = async () => {
      if (!odQuery) return;
      setOdIsSearching(true);
      try {
        const res = await fetch(`${BACKEND_URL || `http://${window.location.hostname}:8000`}/api/omnidrive/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: odQuery, limit: 50 }) });
        const data = await res.json();
        if (data.status === "success") setOdResults(data.results);
      } catch (e) { console.error(e); }
      setOdIsSearching(false);
    };
    return (
      <div className="tab-pane active glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px' }}>
        <h1 className="header-glow">Omni-Drive Explorer</h1>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input type="text" value={odQuery} onChange={e => setOdQuery(e.target.value)} placeholder="Search..." className="ai-input" onKeyDown={(e) => e.key === 'Enter' && handleOdSearch()} style={{ flex: 1 }} />
          <button onClick={handleOdSearch} className="it-btn-primary" disabled={odIsSearching}>{odIsSearching ? "Searching..." : "Omni Search"}</button>
        </div>
        <div style={{ marginBottom: '20px', padding: '15px', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', borderLeft: '4px solid #ff3366' }}>
          <h3 style={{ color: '#ff3366', marginBottom: '10px' }}>Thoughtful Friction Relocation System</h3>
          <input type="text" value={odDestination} onChange={e => setOdDestination(e.target.value)} placeholder="Set global relocation destination" className="ai-input" style={{ width: '100%' }} />
        </div>
        <div className="telemetry-grid" style={{ flex: 1, overflowY: 'auto' }}>
          <table style={{ width: '100%', color: 'white', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '1px solid rgba(0, 210, 255, 0.3)' }}><th style={{ padding: '10px' }}>Drive</th><th style={{ padding: '10px' }}>Filename</th><th style={{ padding: '10px' }}>Path</th></tr></thead>
            <tbody>
              {odResults.map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}><td style={{ padding: '10px', color: '#00d2ff' }}>{r.drive}</td><td style={{ padding: '10px' }}>{r.filename}</td><td style={{ padding: '10px', fontSize: '0.8em', opacity: 0.8 }}>{r.filepath}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
}
