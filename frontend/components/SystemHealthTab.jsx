import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Database, Activity, Search, AlertCircle, RefreshCw, Cpu, HardDrive, Zap } from 'lucide-react';

export default function SystemHealthTab({ backendUrl }) {
  const [activeTab, setActiveTab] = useState('live'); // 'live' or 'history'
  
  // GPU Hardware Telemetry
  const [gpuTelemetry, setGpuTelemetry] = useState(null);

  // Live Stream State
  const [liveLogs, setLiveLogs] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const logsEndRef = useRef(null);

  // History State
  const [historyLogs, setHistoryLogs] = useState([]);
  const [totalLogs, setTotalLogs] = useState(0);
  const [historyPage, setHistoryPage] = useState(0);
  const [filterLevel, setFilterLevel] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);
  
  const limit = 50;

  // Fetch GPU Telemetry
  const fetchGpuTelemetry = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/system/gpu-telemetry`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          setGpuTelemetry(data.telemetry);
        }
      }
    } catch (e) {
      console.debug('GPU telemetry fetch error:', e);
    }
  };

  useEffect(() => {
    fetchGpuTelemetry();
    const interval = setInterval(fetchGpuTelemetry, 5000);
    return () => clearInterval(interval);
  }, [backendUrl]);

  // Setup SSE for Live Stream
  useEffect(() => {
    if (activeTab !== 'live') return;
    
    setIsStreaming(true);
    const eventSource = new EventSource(`${backendUrl}/api/system/logs/stream`);
    
    eventSource.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data);
        setLiveLogs(prev => [...prev.slice(-199), log]); // keep last 200 logs
      } catch (e) {
        console.error("SSE parse error", e);
      }
    };
    
    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
      // attempt reconnect after 3s
      setTimeout(() => setIsStreaming(true), 3000);
    };

    return () => {
      eventSource.close();
      setIsStreaming(false);
    };
  }, [activeTab, backendUrl]);

  // Auto-scroll Live Stream
  useEffect(() => {
    if (activeTab === 'live' && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [liveLogs, activeTab]);

  // Fetch History
  const fetchHistory = async () => {
    setIsFetchingHistory(true);
    try {
      const url = new URL(`${backendUrl}/api/system/logs/history`);
      url.searchParams.append('limit', limit);
      url.searchParams.append('offset', historyPage * limit);
      if (filterLevel !== 'ALL') url.searchParams.append('level', filterLevel);
      if (searchQuery) url.searchParams.append('search', searchQuery);

      const res = await fetch(url);
      const data = await res.json();
      if (data.status === 'success') {
        setHistoryLogs(data.logs);
        setTotalLogs(data.total);
      }
    } catch (e) {
      console.error('Failed to fetch log history', e);
    } finally {
      setIsFetchingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, historyPage, filterLevel]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setHistoryPage(0);
    fetchHistory();
  };

  const getLogColor = (level) => {
    switch (level) {
      case 'ERROR': return '#ef4444';
      case 'CRITICAL': return '#dc2626';
      case 'WARNING': return '#eab308';
      case 'INFO': return '#3b82f6';
      default: return '#94a3b8';
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#050505',
      color: '#e2e8f0',
      fontFamily: 'sans-serif',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 32px',
        backgroundColor: '#121212',
        borderBottom: '1px solid #333',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 10
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Activity color="#3b82f6" size={24} />
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontFamily: '"Inter", sans-serif', color: '#f8fafc' }}>
            System Health & <span style={{ color: '#3b82f6' }}>Logs</span>
          </h1>
        </div>

        {/* View Toggle */}
        <div style={{
          display: 'flex',
          backgroundColor: '#1a1a1a',
          borderRadius: '8px',
          padding: '4px',
          border: '1px solid #333'
        }}>
          <button
            onClick={() => setActiveTab('live')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 24px',
              backgroundColor: activeTab === 'live' ? '#2d2d2d' : 'transparent',
              color: activeTab === 'live' ? '#3b82f6' : '#888',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: activeTab === 'live' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            <Terminal size={18} /> Live Stream
          </button>
          <button
            onClick={() => setActiveTab('history')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 24px',
              backgroundColor: activeTab === 'history' ? '#2d2d2d' : 'transparent',
              color: activeTab === 'history' ? '#3b82f6' : '#888',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: activeTab === 'history' ? 'bold' : 'normal',
              transition: 'all 0.2s'
            }}
          >
            <Database size={18} /> Persistent Archive
          </button>
        </div>
      </div>

      {/* Main Workspace */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        
        {/* Real-Time Hardware & VRAM Allocation Telemetry */}
        {gpuTelemetry && (
          <div style={{
            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.8) 100%)',
            border: '1px solid #334155',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Cpu size={18} color="#00f0ff" />
                <span style={{ fontWeight: 'bold', fontSize: '13px', color: '#f8fafc' }}>
                  {gpuTelemetry.device_name} • {gpuTelemetry.total_vram_gb} GB VRAM
                </span>
                <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                  Temp: {gpuTelemetry.temperature_c}°C
                </span>
                <span style={{ fontSize: '11px', color: '#00f0ff', background: 'rgba(0, 240, 255, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                  GPU Load: {gpuTelemetry.utilization_gpu_pct}%
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px' }}>
                <span style={{ color: gpuTelemetry.ollama_online ? '#10b981' : '#ef4444' }}>
                  ● Ollama Core (Port 11434): {gpuTelemetry.ollama_online ? 'ONLINE' : 'OFFLINE'}
                </span>
                <span style={{ color: gpuTelemetry.comfyui_online ? '#10b981' : '#f59e0b' }}>
                  ● ComfyUI (Port 8189): {gpuTelemetry.comfyui_online ? 'ACTIVE' : 'IDLE'}
                </span>
              </div>
            </div>

            {/* VRAM Allocation Visual Meter */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                <span>Allocated VRAM: <strong>{gpuTelemetry.used_vram_gb} GB</strong> (Llama 8B: 4.9G + RAG: 0.3G)</span>
                <span>Unallocated Headroom: <strong style={{ color: '#10b981' }}>{gpuTelemetry.free_vram_gb} GB</strong></span>
              </div>
              <div style={{ width: '100%', height: '8px', background: '#0f172a', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                <div style={{ width: `${(4.9 / 24.0) * 100}%`, background: '#3b82f6' }} title="Llama 3.1 8B Base: 4.9 GB" />
                <div style={{ width: `${(0.28 / 24.0) * 100}%`, background: '#00f0ff' }} title="nomic-embed RAG: 0.28 GB" />
                {gpuTelemetry.comfyui_online && (
                  <div style={{ width: `${(8.4 / 24.0) * 100}%`, background: '#ec4899' }} title="ComfyUI Diffusion: 8.4 GB" />
                )}
                <div style={{ flex: 1, background: '#1e293b' }} title="Available Headroom" />
              </div>
            </div>
          </div>
        )}

        {/* LIVE STREAM TAB */}
        {activeTab === 'live' && (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, backgroundColor: '#0a0a0a', border: '1px solid #333', borderRadius: '12px', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', backgroundColor: '#161616', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ 
                  display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', 
                  backgroundColor: isStreaming ? '#22c55e' : '#ef4444',
                  boxShadow: isStreaming ? '0 0 8px #22c55e' : 'none'
                }} />
                <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>{isStreaming ? 'Connected to EventStream' : 'Reconnecting...'}</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Showing last 200 events</div>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', fontFamily: '"Fira Code", monospace', fontSize: '0.85rem' }}>
              {liveLogs.length === 0 ? (
                <div style={{ color: '#555', textAlign: 'center', marginTop: '40px' }}>Waiting for logs...</div>
              ) : (
                liveLogs.map((log, i) => (
                  <div key={i} style={{ marginBottom: '6px', display: 'flex', gap: '12px', wordBreak: 'break-all' }}>
                    <span style={{ color: '#64748b', minWidth: '180px' }}>[{log.timestamp.substring(11, 23)}]</span>
                    <span style={{ color: getLogColor(log.level), minWidth: '70px', fontWeight: 'bold' }}>[{log.level}]</span>
                    <span style={{ color: '#94a3b8', minWidth: '120px' }}>{log.name}</span>
                    <span style={{ color: log.level === 'ERROR' ? '#ef4444' : '#e2e8f0' }}>{log.message}</span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#0a0a0a', border: '1px solid #333', borderRadius: '12px', overflow: 'hidden' }}>
            {/* Toolbar */}
            <div style={{ padding: '16px', backgroundColor: '#161616', borderBottom: '1px solid #333', display: 'flex', gap: '16px', alignItems: 'center' }}>
              <select 
                value={filterLevel} 
                onChange={(e) => { setFilterLevel(e.target.value); setHistoryPage(0); }}
                style={{ backgroundColor: '#111', color: '#f8fafc', border: '1px solid #333', padding: '8px 12px', borderRadius: '6px', outline: 'none' }}
              >
                <option value="ALL">All Levels</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>

              <form onSubmit={handleSearchSubmit} style={{ flex: 1, display: 'flex', gap: '8px' }}>
                <div style={{ position: 'relative', flex: 1 }}>
                  <Search size={16} color="#64748b" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search logs by keyword..."
                    style={{ width: '100%', backgroundColor: '#111', color: '#f8fafc', border: '1px solid #333', padding: '8px 12px 8px 36px', borderRadius: '6px', outline: 'none' }}
                  />
                </div>
                <button type="submit" style={{ backgroundColor: '#2d2d2d', color: '#f8fafc', border: '1px solid #333', padding: '0 16px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {isFetchingHistory ? <RefreshCw size={16} className="animate-spin" /> : 'Search'}
                </button>
              </form>
            </div>

            {/* Table */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: '#111', zIndex: 1, borderBottom: '1px solid #333' }}>
                  <tr>
                    <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 'bold' }}>Timestamp</th>
                    <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 'bold' }}>Level</th>
                    <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 'bold' }}>Logger</th>
                    <th style={{ padding: '12px 16px', color: '#94a3b8', fontWeight: 'bold', width: '60%' }}>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {historyLogs.map((log) => (
                    <tr key={log.id} style={{ borderBottom: '1px solid #222', backgroundColor: log.level === 'ERROR' || log.level === 'CRITICAL' ? 'rgba(239, 68, 68, 0.05)' : 'transparent' }}>
                      <td style={{ padding: '10px 16px', color: '#64748b' }}>{log.timestamp.substring(0, 19).replace('T', ' ')}</td>
                      <td style={{ padding: '10px 16px', color: getLogColor(log.level), fontWeight: 'bold' }}>{log.level}</td>
                      <td style={{ padding: '10px 16px', color: '#94a3b8' }}>{log.name}</td>
                      <td style={{ padding: '10px 16px', color: '#e2e8f0', wordBreak: 'break-word' }}>{log.message}</td>
                    </tr>
                  ))}
                  {historyLogs.length === 0 && !isFetchingHistory && (
                    <tr>
                      <td colSpan="4" style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                        <AlertCircle size={32} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
                        No logs found matching your criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div style={{ padding: '12px 16px', backgroundColor: '#161616', borderTop: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                Showing {Math.min(historyLogs.length, limit)} of {totalLogs} results
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  onClick={() => setHistoryPage(p => Math.max(0, p - 1))}
                  disabled={historyPage === 0}
                  style={{ backgroundColor: '#222', color: historyPage === 0 ? '#555' : '#f8fafc', border: '1px solid #333', padding: '6px 12px', borderRadius: '4px', cursor: historyPage === 0 ? 'not-allowed' : 'pointer' }}
                >
                  Previous
                </button>
                <button 
                  onClick={() => setHistoryPage(p => p + 1)}
                  disabled={(historyPage + 1) * limit >= totalLogs}
                  style={{ backgroundColor: '#222', color: (historyPage + 1) * limit >= totalLogs ? '#555' : '#f8fafc', border: '1px solid #333', padding: '6px 12px', borderRadius: '4px', cursor: (historyPage + 1) * limit >= totalLogs ? 'not-allowed' : 'pointer' }}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <style>{`
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
