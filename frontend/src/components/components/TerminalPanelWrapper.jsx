import React from 'react';
import TerminalPanel from './TerminalPanel';
import { useAppStore } from './useAppStore';

export default function TerminalPanelWrapper() {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  return (
    <div className="powershell-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <h3 style={{ margin: 0, color: '#fff' }}>Windows Administrative PowerShell</h3>
        <p style={{ margin: '4px 0 0 0', color: '#888', fontSize: '0.85rem' }}>
          Execute raw PowerShell and system commands directly against your backend infrastructure.
        </p>
      </div>
      <TerminalPanel backendUrl={BACKEND_URL} />
    </div>
  );
}
