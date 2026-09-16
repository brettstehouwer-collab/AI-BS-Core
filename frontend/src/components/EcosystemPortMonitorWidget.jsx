import React, { useState, useEffect, useRef } from 'react';
import { getApiBase } from '../config/api';

export default function EcosystemPortMonitorWidget({ backendUrl, isCompact = false }) {
  const apiHost = backendUrl || getApiBase() || 'http://localhost:8080';
  const [telemetry, setTelemetry] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [activeFilter, setActiveFilter] = useState('ALL'); // 'ALL' | 'CORE' | 'WSL' | 'DYNAMIC'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPort, setSelectedPort] = useState(null);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testEndpoint, setTestEndpoint] = useState('/api/health');
  const [testMethod, setTestMethod] = useState('GET');
  const [testPayload, setTestPayload] = useState('{}');
  const [isExecutingTest, setIsExecutingTest] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState(null);
  const wsRef = useRef(null);

  // WebSocket / Polling Stream
  useEffect(() => {
    let wsUrl = apiHost.replace(/^http/, 'ws');
    if (!wsUrl.includes('/ws/ecosystem/telemetry')) {
      wsUrl = `${wsUrl}/ws/ecosystem/telemetry`;
    }

    let isMounted = true;
    const connectWs = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isMounted) setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (isMounted) setTelemetry(data);
          } catch (e) {
            console.warn('Ecosystem telemetry parse error:', e);
          }
        };

        ws.onerror = () => {
          if (isMounted) setIsConnected(false);
        };

        ws.onclose = () => {
          if (isMounted) {
            setIsConnected(false);
            // Reconnect after 3s
            setTimeout(connectWs, 3000);
          }
        };
      } catch (err) {
        if (isMounted) setIsConnected(false);
      }
    };

    connectWs();

    // Fallback REST fetch initially and as interval backup
    const fetchSnapshot = async () => {
      try {
        const res = await fetch(`${apiHost}/api/v1/system/ecosystem/telemetry`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setTelemetry(data);
        }
      } catch (e) {
        // Silent fallback
      }
    };
    fetchSnapshot();
    const interval = setInterval(fetchSnapshot, 4000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [apiHost]);

  // Execute Tool Test on Target Port
  const handleExecutePortTest = async () => {
    if (!selectedPort) return;
    setIsExecutingTest(true);
    setTestResult(null);
    try {
      let parsedPayload = null;
      if (testMethod !== 'GET' && testPayload.trim()) {
        try {
          parsedPayload = JSON.parse(testPayload);
        } catch (err) {
          setTestResult({ status: 'error', message: `Invalid JSON payload: ${err.message}` });
          setIsExecutingTest(false);
          return;
        }
      }

      const res = await fetch(`${apiHost}/api/v1/system/ecosystem/ports/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          port: selectedPort.port,
          endpoint: testEndpoint,
          method: testMethod,
          payload: parsedPayload,
          timeout_seconds: 15.0
        })
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({ status: 'error', message: err.message });
    } finally {
      setIsExecutingTest(false);
    }
  };

  // Discover OpenAPI / Tool signatures on Port
  const handleDiscoverPortTools = async (portNum) => {
    setIsDiscovering(true);
    setDiscoveryResult(null);
    try {
      const res = await fetch(`${apiHost}/api/v1/system/ecosystem/ports/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ports: [portNum], timeout_seconds: 2.0 })
      });
      const data = await res.json();
      setDiscoveryResult(data);
    } catch (err) {
      setDiscoveryResult({ status: 'error', message: err.message });
    } finally {
      setIsDiscovering(false);
    }
  };

  const summary = telemetry?.summary || {};
  const coreMatrix = telemetry?.core_matrix || [];
  const dynamicPorts = telemetry?.dynamic_ports || [];
  const wslPorts = telemetry?.wsl_ports || [];

  // Filter Ports
  let displayPorts = [];
  if (activeFilter === 'ALL') {
    displayPorts = [
      ...coreMatrix.map(p => ({ ...p, category: 'CORE' })),
      ...wslPorts.map(p => ({ ...p, service: `WSL2 Service (${p.subsystem || 'Linux'})`, runtime: 'WSL2 Ubuntu', status: 'ONLINE', category: 'WSL' })),
      ...dynamicPorts.map(p => ({ ...p, service: p.process_name || 'Dynamic Socket', runtime: 'Host Process', status: 'ONLINE', category: 'DYNAMIC' }))
    ];
  } else if (activeFilter === 'CORE') {
    displayPorts = coreMatrix.map(p => ({ ...p, category: 'CORE' }));
  } else if (activeFilter === 'WSL') {
    displayPorts = wslPorts.map(p => ({ ...p, service: `WSL2 Service (${p.subsystem || 'Linux'})`, runtime: 'WSL2 Ubuntu', status: 'ONLINE', category: 'WSL' }));
  } else if (activeFilter === 'DYNAMIC') {
    displayPorts = dynamicPorts.map(p => ({ ...p, service: p.process_name || 'Dynamic Socket', runtime: 'Host Process', status: 'ONLINE', category: 'DYNAMIC' }));
  }

  // Search Query
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    displayPorts = displayPorts.filter(p => 
      String(p.port).includes(q) || 
      (p.service && p.service.toLowerCase().includes(q)) || 
      (p.process_name && p.process_name.toLowerCase().includes(q)) ||
      (p.type && p.type.toLowerCase().includes(q))
    );
  }

  // Compact Header Mode
  if (isCompact) {
    return (
      <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-900/90 border border-slate-700/60 rounded-xl text-xs backdrop-blur-md shadow-lg">
        <div className="flex items-center gap-1.5">
          <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
          <span className="font-semibold text-slate-300">Port Mesh:</span>
          <span className="text-emerald-400 font-mono font-bold">{summary.core_matrix_online || 0}/{summary.core_matrix_total || 25} Online</span>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-slate-400 border-l border-slate-700 pl-3">
          <span>Total Sockets: <strong className="text-sky-400 font-mono">{summary.total_listening_ports || 0}</strong></span>
          <span>CPU: <strong className="text-amber-400 font-mono">{summary.host_cpu_pct || 0}%</strong></span>
          <span>VRAM: <strong className="text-purple-400 font-mono">{Math.round((summary.rtx_4090_vram_used_mb || 0) / 1024)}GB</strong></span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-6 text-slate-200">
      {/* Top Header & Live Pulse */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-sky-500/10 border border-sky-500/30 rounded-xl text-sky-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold bg-gradient-to-r from-sky-400 via-emerald-400 to-indigo-400 bg-clip-text text-transparent">
                Unified Ecosystem Port & Dynamic Tool Mesh
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time WebSocket & SHM Telemetry • Port-as-a-Tool Dispatcher • 18-Port Collision Matrix
              </p>
            </div>
          </div>
        </div>

        {/* Live Stream Pill */}
        <div className="flex items-center gap-3 self-start md:self-auto">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-950/80 border border-slate-700/60 rounded-xl text-xs">
            <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className="font-mono text-slate-300">
              {isConnected ? 'LIVE WS CONNECTED' : 'REST POLLING'}
            </span>
            <span className="text-slate-500">|</span>
            <span className="text-sky-400 font-mono">{(telemetry?.scan_latency_ms || 0).toFixed(1)}ms</span>
          </div>
          <button
            onClick={() => handleDiscoverPortTools(8080)}
            disabled={isDiscovering}
            className="px-3 py-1.5 bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/40 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all"
          >
            {isDiscovering ? '🔍 Scanning...' : '⚡ Auto-Discover Tools'}
          </button>
        </div>
      </div>

      {/* KPI Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Active Ports</span>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
            {summary.core_matrix_online || 0} <span className="text-xs text-slate-500 font-normal">/ {summary.core_matrix_total || 25}</span>
          </div>
          <span className="text-[10px] text-slate-500">Core Matrix Online</span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Total Sockets</span>
          <div className="text-xl font-bold font-mono text-sky-400 mt-1">{summary.total_listening_ports || 0}</div>
          <span className="text-[10px] text-slate-500">Listening Endpoints</span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Host CPU</span>
          <div className="text-xl font-bold font-mono text-amber-400 mt-1">{summary.host_cpu_pct || 0}%</div>
          <div className="w-full bg-slate-800 h-1 rounded-full mt-1.5 overflow-hidden">
            <div className="bg-amber-400 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(summary.host_cpu_pct || 0, 100)}%` }}></div>
          </div>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Host RAM</span>
          <div className="text-xl font-bold font-mono text-cyan-400 mt-1">{summary.host_mem_used_gb || 0} <span className="text-xs text-slate-500 font-normal">GB</span></div>
          <span className="text-[10px] text-slate-500">{summary.host_mem_pct || 0}% of {summary.host_mem_total_gb || 0}GB</span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">RTX 4090 VRAM</span>
          <div className="text-xl font-bold font-mono text-purple-400 mt-1">
            {Math.round((summary.rtx_4090_vram_used_mb || 0) / 1024)} <span className="text-xs text-slate-500 font-normal">/ 24GB</span>
          </div>
          <span className="text-[10px] text-slate-500">{summary.rtx_4090_temp_c || 0}°C • {summary.rtx_4090_util_pct || 0}% GPU</span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-center">
          <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Network I/O</span>
          <div className="text-sm font-bold font-mono text-indigo-400 mt-1">
            ▲ {summary.net_bytes_sent_mb || 0} MB
          </div>
          <div className="text-xs font-mono text-slate-400">
            ▼ {summary.net_bytes_recv_mb || 0} MB
          </div>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 bg-slate-950/80 border border-slate-800 rounded-xl text-xs w-full sm:w-auto">
          {[
            { id: 'ALL', label: `All Sockets (${(summary.total_listening_ports || 0)})` },
            { id: 'CORE', label: `Core Matrix (${summary.core_matrix_total || 25})` },
            { id: 'WSL', label: `WSL2 Linux (${summary.wsl_ports_count || 0})` },
            { id: 'DYNAMIC', label: `Dynamic Tools (${summary.dynamic_ports_count || 0})` }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
                activeFilter === tab.id
                  ? 'bg-sky-500 text-white font-semibold shadow-md'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <input
            type="text"
            placeholder="Filter by port, service, process..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-700/60 rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1.5 text-slate-400 hover:text-slate-200 text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Discovery Report Card (If Triggered) */}
      {discoveryResult && (
        <div className="bg-sky-950/30 border border-sky-500/40 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sky-400 font-bold text-sm">🔍 Port Tool Discovery Results:</span>
              <span className="text-xs text-slate-300 font-mono">{discoveryResult.scanned_ports_count} Ports Scanned</span>
            </div>
            <button onClick={() => setDiscoveryResult(null)} className="text-xs text-slate-400 hover:text-slate-200">Close ✕</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-60 overflow-y-auto pr-1">
            {Object.values(discoveryResult.discovered_services || {}).map((srv, idx) => (
              <div key={idx} className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sky-300">Port {srv.port}: {srv.service_title}</span>
                  <span className="px-1.5 py-0.5 bg-sky-900/60 text-sky-200 rounded text-[10px] font-mono">{srv.protocol}</span>
                </div>
                <div className="text-slate-400">Available Tool Endpoints: <strong className="text-emerald-400">{srv.tools_count}</strong></div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {(srv.tools || []).slice(0, 4).map((t, tIdx) => (
                    <span key={tIdx} className="px-1.5 py-0.5 bg-slate-800 text-slate-300 rounded font-mono text-[10px]">
                      {t.method} {t.endpoint}
                    </span>
                  ))}
                  {(srv.tools || []).length > 4 && (
                    <span className="text-[10px] text-slate-500">+{srv.tools.length - 4} more</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Port Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {displayPorts.map((p, idx) => {
          const isOnline = p.status === 'ONLINE';
          return (
            <div
              key={`${p.port}-${idx}`}
              className={`bg-slate-950/70 border rounded-xl p-3.5 transition-all space-y-2.5 flex flex-col justify-between ${
                isOnline ? 'border-slate-800 hover:border-slate-700 shadow-sm' : 'border-slate-900 opacity-60'
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-600'}`}></span>
                    <span className="font-mono font-bold text-slate-200 text-sm">Port {p.port}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider uppercase font-mono ${
                    isOnline ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-500'
                  }`}>
                    {p.status}
                  </span>
                </div>

                <div className="font-semibold text-slate-200 text-xs mt-1 truncate" title={p.service}>
                  {p.service || p.process_name}
                </div>
                <div className="text-[11px] text-slate-400 flex items-center justify-between mt-0.5">
                  <span className="truncate">{p.runtime || 'Process'}</span>
                  {p.pid && <span className="font-mono text-slate-500 text-[10px]">PID {p.pid}</span>}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 text-[11px] space-y-1">
                <div className="flex items-center justify-between text-slate-400">
                  <span>CPU: <strong className="text-slate-200 font-mono">{p.cpu_pct || 0}%</strong></span>
                  <span>RAM: <strong className="text-slate-200 font-mono">{p.mem_mb || 0} MB</strong></span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span>Threads: <strong className="text-slate-200 font-mono">{p.threads || 1}</strong></span>
                  <span className="text-[10px] text-sky-400 font-mono truncate max-w-[120px]">{p.type || p.category}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-1.5 pt-1">
                <button
                  onClick={() => {
                    setSelectedPort(p);
                    setTestEndpoint(p.health_endpoint ? p.health_endpoint.replace(/^http:\/\/127.0.0.1:\d+/, '') : '/api/health');
                    setTestMethod('GET');
                    setTestResult(null);
                    setTestModalOpen(true);
                  }}
                  className="flex-1 py-1 px-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] font-medium transition-colors text-center"
                >
                  ⚡ Tool Call
                </button>
                <button
                  onClick={() => handleDiscoverPortTools(p.port)}
                  className="py-1 px-2 bg-sky-950/60 hover:bg-sky-900/60 text-sky-300 border border-sky-800/40 rounded text-[11px] font-medium transition-colors"
                  title="Discover APIs & Schemas"
                >
                  🔍
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Dynamic Port Tool Caller Modal */}
      {testModalOpen && selectedPort && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="p-1.5 bg-sky-500/20 text-sky-400 rounded-lg text-sm">⚡</span>
                <div>
                  <h3 className="text-base font-bold text-slate-100">
                    Dispatch Tool Call: Port {selectedPort.port}
                  </h3>
                  <p className="text-xs text-slate-400">{selectedPort.service} ({selectedPort.runtime})</p>
                </div>
              </div>
              <button onClick={() => setTestModalOpen(false)} className="text-slate-400 hover:text-slate-200 text-sm">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-4 gap-2">
                <div className="col-span-1">
                  <label className="block text-slate-400 mb-1">HTTP Method</label>
                  <select
                    value={testMethod}
                    onChange={(e) => setTestMethod(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </div>
                <div className="col-span-3">
                  <label className="block text-slate-400 mb-1">Endpoint Path</label>
                  <input
                    type="text"
                    value={testEndpoint}
                    onChange={(e) => setTestEndpoint(e.target.value)}
                    placeholder="/api/health or /openapi.json"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
                  />
                </div>
              </div>

              {testMethod !== 'GET' && (
                <div>
                  <label className="block text-slate-400 mb-1">JSON Payload Body</label>
                  <textarea
                    rows={4}
                    value={testPayload}
                    onChange={(e) => setTestPayload(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
                    placeholder='{"key": "value"}'
                  />
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setTestModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecutePortTest}
                  disabled={isExecutingTest}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-sky-600/30"
                >
                  {isExecutingTest ? '⚡ Executing...' : 'Execute Tool Call'}
                </button>
              </div>

              {/* Execution Results */}
              {testResult && (
                <div className="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-bold text-slate-300">
                      Status: <span className={testResult.status === 'success' ? 'text-emerald-400' : 'text-rose-400'}>{testResult.status}</span>
                      {testResult.http_status && ` (HTTP ${testResult.http_status})`}
                    </span>
                    {testResult.execution_time_ms && (
                      <span className="text-slate-500">{testResult.execution_time_ms} ms</span>
                    )}
                  </div>
                  <pre className="text-[11px] font-mono bg-slate-900 p-2.5 rounded-lg text-slate-300 max-h-48 overflow-y-auto whitespace-pre-wrap">
                    {JSON.stringify(testResult.response || testResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
