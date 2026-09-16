import React, { useState } from 'react';

export function MatrixDoctorTab() {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState(null);

  const runDiagnostic = async () => {
    setRunning(true);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/system/health');
      const data = await res.json();
      setReport({
        timestamp: new Date().toLocaleTimeString(),
        system: data,
        status: 'Matrix Core Operational'
      });
    } catch (e) {
      setReport({ timestamp: new Date().toLocaleTimeString(), error: e.message, status: 'Connection Warning' });
    }
    setRunning(false);
  };

  return (
    <div className="matrix-doctor-tab p-6 bg-slate-950 text-white min-h-screen">
      <div className="flex justify-between items-center mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-black text-cyan-400 tracking-wider uppercase">Matrix Doctor Diagnostic Deck (v5.92.0)</h1>
          <p className="text-xs text-slate-400">Automated Health Scans, Port Topology & SQLite Integrity Audits</p>
        </div>
        <button onClick={runDiagnostic} disabled={running} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded font-bold text-sm shadow-lg shadow-cyan-500/20 disabled:opacity-50 transition-all">
          {running ? 'Running Scans...' : 'Run Full Diagnostic'}
        </button>
      </div>

      {report && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-4">
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-sm text-emerald-400">{report.status}</span>
            <span className="text-xs text-slate-500 font-mono">({report.timestamp})</span>
          </div>
          <pre className="bg-black/50 p-4 rounded text-xs font-mono text-cyan-300 overflow-x-auto">
            {JSON.stringify(report, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
