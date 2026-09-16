import React, { useState, useEffect, useMemo } from 'react';
import { useAppStore } from './useAppStore';

const OperationsAuditHubTab = () => {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL) || 'http://127.0.0.1:8080';
  
  // Navigation Sub-tab State
  const [activeSubTab, setActiveSubTab] = useState('tasks'); // 'tasks' | 'media' | 'saves' | 'admin' | 'errors'
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(10); // seconds
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const [actionFeedback, setActionFeedback] = useState(null);

  // Data States
  const [processData, setProcessData] = useState(null);
  const [mediaData, setMediaData] = useState(null);
  const [savesData, setSavesData] = useState(null);
  const [adminData, setAdminData] = useState(null);
  const [errorData, setErrorData] = useState(null);

  // UI Interactive States
  const [processSearch, setProcessSearch] = useState('');
  const [selectedLogFile, setSelectedLogFile] = useState('auto_healer_daemon.log');
  const [logTailContent, setLogTailContent] = useState('');
  const [logTailLoading, setLogTailLoading] = useState(false);
  const [selectedMediaModal, setSelectedMediaModal] = useState(null);
  const [selectedAdminTable, setSelectedAdminTable] = useState(null);
  const [errorFilter, setErrorFilter] = useState('');

  // Fetch all live telemetry
  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [pRes, mRes, sRes, aRes, eRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/operations/processes`).then(r => r.ok ? r.json() : null),
        fetch(`${BACKEND_URL}/api/operations/media-workloads`).then(r => r.ok ? r.json() : null),
        fetch(`${BACKEND_URL}/api/operations/saves-and-work`).then(r => r.ok ? r.json() : null),
        fetch(`${BACKEND_URL}/api/operations/admin-submissions`).then(r => r.ok ? r.json() : null),
        fetch(`${BACKEND_URL}/api/operations/error-diagnostics`).then(r => r.ok ? r.json() : null),
      ]);

      if (pRes) setProcessData(pRes);
      if (mRes) setMediaData(mRes);
      if (sRes) setSavesData(sRes);
      if (aRes) {
        setAdminData(aRes);
        if (!selectedAdminTable && aRes.tables && aRes.tables.length > 0) {
          setSelectedAdminTable(aRes.tables[0]);
        }
      }
      if (eRes) setErrorData(eRes);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error("Operations Audit Hub fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch Log Tail
  const fetchLogTail = async (filename) => {
    if (!filename) return;
    setLogTailLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/operations/log-tail?logfile=${encodeURIComponent(filename)}&lines=120`);
      if (res.ok) {
        const data = await res.json();
        setLogTailContent(data.content || 'Empty log file.');
      } else {
        setLogTailContent(`Failed to load ${filename} (${res.status})`);
      }
    } catch (e) {
      setLogTailContent(`Error fetching log: ${e.message}`);
    } finally {
      setLogTailLoading(false);
    }
  };

  // Auto-refresh timer (staggered & targeted to active subtab to avoid event-loop starvation)
  useEffect(() => {
    fetchAllData();
  }, [BACKEND_URL]);

  // Fetch active subtab data immediately upon tab switch
  useEffect(() => {
    if (activeSubTab === 'tasks') {
      fetch(`${BACKEND_URL}/api/operations/processes`).then(r => r.ok ? r.json() : null).then(d => d && setProcessData(d));
    } else if (activeSubTab === 'media') {
      fetch(`${BACKEND_URL}/api/operations/media-workloads`).then(r => r.ok ? r.json() : null).then(d => d && setMediaData(d));
    } else if (activeSubTab === 'saves') {
      fetch(`${BACKEND_URL}/api/operations/saves-and-work`).then(r => r.ok ? r.json() : null).then(d => d && setSavesData(d));
    } else if (activeSubTab === 'admin') {
      fetch(`${BACKEND_URL}/api/operations/admin-submissions`).then(r => r.ok ? r.json() : null).then(d => {
        if (d) {
          setAdminData(d);
          if (!selectedAdminTable && d.tables && d.tables.length > 0) {
            setSelectedAdminTable(d.tables[0]);
          }
        }
      });
    } else if (activeSubTab === 'errors') {
      fetch(`${BACKEND_URL}/api/operations/error-diagnostics`).then(r => r.ok ? r.json() : null).then(d => d && setErrorData(d));
    }
  }, [activeSubTab, BACKEND_URL]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      if (document.hidden) return; // Pause polling when browser tab is inactive

      // Always refresh system processes & port status
      fetch(`${BACKEND_URL}/api/operations/processes`).then(r => r.ok ? r.json() : null).then(d => d && setProcessData(d));

      // Refresh data specific to active subtab
      if (activeSubTab === 'media') {
        fetch(`${BACKEND_URL}/api/operations/media-workloads`).then(r => r.ok ? r.json() : null).then(d => d && setMediaData(d));
      } else if (activeSubTab === 'saves') {
        fetch(`${BACKEND_URL}/api/operations/saves-and-work`).then(r => r.ok ? r.json() : null).then(d => d && setSavesData(d));
      } else if (activeSubTab === 'admin') {
        fetch(`${BACKEND_URL}/api/operations/admin-submissions`).then(r => r.ok ? r.json() : null).then(d => d && setAdminData(d));
      } else if (activeSubTab === 'errors') {
        fetch(`${BACKEND_URL}/api/operations/error-diagnostics`).then(r => r.ok ? r.json() : null).then(d => d && setErrorData(d));
      }
      setLastRefreshed(new Date());
    }, refreshInterval * 1000);
    return () => clearInterval(timer);
  }, [autoRefresh, refreshInterval, BACKEND_URL, activeSubTab]);

  useEffect(() => {
    if (activeSubTab === 'errors' && selectedLogFile) {
      fetchLogTail(selectedLogFile);
    }
  }, [activeSubTab, selectedLogFile]);

  // Handle Process Kill / Terminate
  const handleProcessAction = async (pid, action) => {
    if (!window.confirm(`Are you sure you want to ${action.toUpperCase()} process PID ${pid}?`)) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/operations/process-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid, action })
      });
      const data = await res.json();
      if (res.ok) {
        setActionFeedback(`Success: ${data.message}`);
        setTimeout(() => setActionFeedback(null), 4000);
        fetchAllData();
      } else {
        alert(`Action failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    }
  };

  // Filtered Processes
  const filteredProcesses = useMemo(() => {
    if (!processData?.processes) return [];
    if (!processSearch.trim()) return processData.processes;
    const q = processSearch.toLowerCase();
    return processData.processes.filter(p => 
      p.name.toLowerCase().includes(q) ||
      p.role.toLowerCase().includes(q) ||
      String(p.pid).includes(q) ||
      p.cmd.toLowerCase().includes(q)
    );
  }, [processData, processSearch]);

  // Filtered Errors
  const filteredErrors = useMemo(() => {
    if (!errorData?.error_feed) return [];
    if (!errorFilter.trim()) return errorData.error_feed;
    const q = errorFilter.toLowerCase();
    return errorData.error_feed.filter(e => 
      e.log_file.toLowerCase().includes(q) ||
      e.line.toLowerCase().includes(q)
    );
  }, [errorData, errorFilter]);

  // Helper for formatting bytes / sizes
  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#0a0d14',
      color: '#e2e8f0',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      overflow: 'hidden'
    }}>
      {/* ── TOP MISSION CONTROL HEADER ───────────────────────────── */}
      <header style={{
        padding: '14px 24px',
        backgroundColor: '#0f172a',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.4rem',
            boxShadow: '0 0 20px rgba(14, 165, 233, 0.4)'
          }}>
            ⚡
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.02em' }}>
                Omni Operations & Live Audit Hub
              </h1>
              <span style={{
                padding: '2px 8px',
                borderRadius: '999px',
                fontSize: '0.7rem',
                fontWeight: 600,
                backgroundColor: 'rgba(14, 165, 233, 0.15)',
                color: '#38bdf8',
                border: '1px solid rgba(14, 165, 233, 0.3)'
              }}>
                100% REAL-TIME LIVE DATA
              </span>
            </div>
            <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '2px' }}>
              Host PID Telemetry · ComfyUI SDXL Queue · Continuous Autosaves · Admin SQLite Vault · Daemon Diagnostics
            </div>
          </div>
        </div>

        {/* Global Hardware HUD Quick Stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {processData?.host_hardware && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '6px 14px',
              borderRadius: '8px',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              fontSize: '0.8rem'
            }}>
              <div>
                <span style={{ color: '#64748b' }}>Host RAM: </span>
                <strong style={{ color: processData.host_hardware.ram_percent > 85 ? '#f87171' : '#38bdf8' }}>
                  {processData.host_hardware.ram_percent}%
                </strong>
                <span style={{ fontSize: '0.72rem', color: '#94a3b8', marginLeft: '4px' }}>
                  ({processData.host_hardware.used_ram_gb}/{processData.host_hardware.total_ram_gb} GB)
                </span>
              </div>
              <div style={{ width: '1px', height: '14px', backgroundColor: '#475569' }} />
              <div>
                <span style={{ color: '#64748b' }}>Cores: </span>
                <strong style={{ color: '#a78bfa' }}>{processData.host_hardware.logical_cores} Cores</strong>
              </div>
              <div style={{ width: '1px', height: '14px', backgroundColor: '#475569' }} />
              <div>
                <span style={{ color: '#64748b' }}>Processes: </span>
                <strong style={{ color: '#34d399' }}>{processData.total_active_processes}</strong>
              </div>
              <div style={{ width: '1px', height: '14px', backgroundColor: '#475569' }} />
              <div>
                <span style={{ color: '#64748b' }}>Admin DB Rows: </span>
                <strong style={{ color: '#fbbf24' }}>{adminData?.total_admin_records ?? '...'}</strong>
              </div>
            </div>
          )}

          {/* Refresh Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={fetchAllData}
              disabled={loading}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                backgroundColor: loading ? '#334155' : '#0284c7',
                color: '#ffffff',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'background 0.2s'
              }}
            >
              <span style={{ display: 'inline-block', transform: loading ? 'rotate(360deg)' : 'none', transition: 'transform 0.5s' }}>🔄</span>
              {loading ? 'Polling...' : 'Refresh'}
            </button>

            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              style={{
                padding: '6px 10px',
                borderRadius: '6px',
                backgroundColor: autoRefresh ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: autoRefresh ? '#34d399' : '#f87171',
                border: `1px solid ${autoRefresh ? 'rgba(52, 211, 153, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {autoRefresh ? `Auto (${refreshInterval}s)` : 'Paused'}
            </button>
          </div>
        </div>
      </header>

      {/* Action Notification Banner */}
      {actionFeedback && (
        <div style={{
          backgroundColor: '#065f46',
          color: '#34d399',
          padding: '8px 24px',
          fontSize: '0.85rem',
          fontWeight: 600,
          borderBottom: '1px solid #047857'
        }}>
          {actionFeedback}
        </div>
      )}

      {/* ── SUB-NAVIGATION TABS ───────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        backgroundColor: '#090d16',
        borderBottom: '1px solid #1e293b',
        gap: '4px',
        overflowX: 'auto'
      }}>
        {[
          { id: 'tasks', label: 'Active Tasks & Daemons', icon: '⚙️', badge: processData?.total_active_processes },
          { id: 'media', label: 'Media Generation Pipeline', icon: '🎨', badge: mediaData?.total_generated_media },
          { id: 'saves', label: 'Work & Autosaves Log', icon: '💾', badge: savesData?.total_modified_last_24h ? `${savesData.total_modified_last_24h} 24h` : null },
          { id: 'admin', label: 'Admin User Data Vault', icon: '🏛️', badge: adminData?.total_admin_records },
          { id: 'errors', label: 'System Error & Crash Diagnostics', icon: '🚨', badge: errorData?.total_recent_errors_extracted, badgeColor: '#ef4444' }
        ].map(tab => {
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                backgroundColor: 'transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                border: 'none',
                borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap'
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {tab.badge !== undefined && tab.badge !== null && (
                <span style={{
                  fontSize: '0.7rem',
                  padding: '2px 6px',
                  borderRadius: '999px',
                  backgroundColor: tab.badgeColor ? 'rgba(239, 68, 68, 0.2)' : 'rgba(148, 163, 184, 0.15)',
                  color: tab.badgeColor || '#cbd5e1',
                  fontWeight: 700
                }}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── MAIN CONTENT WORKSPACE ───────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        {/* ========================================================================= */}
        {/* TAB 1: ACTIVE TASKS & DAEMONS                                            */}
        {/* ========================================================================= */}
        {activeSubTab === 'tasks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* TCP Listening Ports Matrix */}
            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#94a3b8', margin: '0 0 12px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                TCP Listening Port Matrix ({processData?.ports?.filter(p => p.is_open).length || 0} Active Listeners)
              </h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: '10px'
              }}>
                {processData?.ports?.map(p => (
                  <div
                    key={p.port}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '8px',
                      backgroundColor: p.is_open ? 'rgba(15, 23, 42, 0.8)' : 'rgba(15, 23, 42, 0.4)',
                      border: `1px solid ${p.is_open ? '#0284c7' : '#1e293b'}`,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.9rem', fontWeight: 700, color: p.is_open ? '#38bdf8' : '#64748b' }}>
                        :{p.port}
                      </span>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: p.is_open ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.1)',
                        color: p.is_open ? '#34d399' : '#f87171'
                      }}>
                        {p.status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#cbd5e1', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {p.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Live Processes Table */}
            <div style={{
              backgroundColor: '#0f172a',
              borderRadius: '10px',
              border: '1px solid #1e293b',
              overflow: 'hidden'
            }}>
              <div style={{
                padding: '14px 18px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '12px'
              }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
                  Live System Processes & Daemons ({filteredProcesses.length})
                </div>
                <input
                  type="text"
                  placeholder="Search PID, name, role, command..."
                  value={processSearch}
                  onChange={e => setProcessSearch(e.target.value)}
                  style={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    color: '#f8fafc',
                    fontSize: '0.82rem',
                    minWidth: '280px',
                    outline: 'none'
                  }}
                />
              </div>

              <div style={{ overflowX: 'auto', maxHeight: '550px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#131e33', color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '10px 16px' }}>PID</th>
                      <th style={{ padding: '10px 16px' }}>Subsystem Role</th>
                      <th style={{ padding: '10px 16px' }}>Process Name</th>
                      <th style={{ padding: '10px 16px' }}>RAM (MB)</th>
                      <th style={{ padding: '10px 16px' }}>Status</th>
                      <th style={{ padding: '10px 16px' }}>Command Line Executed</th>
                      <th style={{ padding: '10px 16px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredProcesses.map((p, idx) => (
                      <tr
                        key={p.pid}
                        style={{
                          borderBottom: '1px solid #1e293b',
                          backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)'
                        }}
                      >
                        <td style={{ padding: '10px 16px', fontWeight: 700, color: '#38bdf8' }}>{p.pid}</td>
                        <td style={{ padding: '10px 16px', fontWeight: 600, color: '#f1f5f9' }}>{p.role}</td>
                        <td style={{ padding: '10px 16px', color: '#a78bfa' }}>{p.name}</td>
                        <td style={{ padding: '10px 16px', fontWeight: 700, color: p.memory_mb > 500 ? '#fbbf24' : '#94a3b8' }}>
                          {p.memory_mb} MB
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <span style={{
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '0.72rem',
                            backgroundColor: p.status === 'running' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                            color: p.status === 'running' ? '#34d399' : '#cbd5e1'
                          }}>
                            {p.status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 16px', color: '#64748b', fontFamily: 'monospace', fontSize: '0.75rem', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {p.cmd}
                        </td>
                        <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleProcessAction(p.pid, 'kill')}
                            title="Force Kill Process"
                            style={{
                              padding: '4px 8px',
                              backgroundColor: 'rgba(239, 68, 68, 0.15)',
                              color: '#f87171',
                              border: '1px solid rgba(239, 68, 68, 0.3)',
                              borderRadius: '4px',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              cursor: 'pointer'
                            }}
                          >
                            Kill PID
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: MEDIA GENERATION PIPELINE                                         */}
        {/* ========================================================================= */}
        {activeSubTab === 'media' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Status Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              <div style={{
                padding: '16px 20px',
                borderRadius: '10px',
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  ComfyUI Engine Status (Port 8189)
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor: mediaData?.comfyui?.online ? '#34d399' : '#ef4444',
                    boxShadow: mediaData?.comfyui?.online ? '0 0 10px #34d399' : 'none'
                  }} />
                  <span style={{ fontSize: '1.2rem', fontWeight: 700, color: '#f8fafc' }}>
                    {mediaData?.comfyui?.online ? 'Online & Generating' : 'Offline / Standby'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Active Queue: {mediaData?.comfyui?.queue_remaining || 0} prompt(s) in execution pipeline
                </div>
              </div>

              <div style={{
                padding: '16px 20px',
                borderRadius: '10px',
                backgroundColor: '#0f172a',
                border: '1px solid #1e293b',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Broadcast & Streaming Ingest
                </div>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <div>
                    <span style={{ fontSize: '0.78rem', color: '#64748b' }}>RTMP Ingest (:1935): </span>
                    <strong style={{ color: mediaData?.streaming_ingest?.rtmp_1935 === 'ONLINE' ? '#34d399' : '#f87171' }}>
                      {mediaData?.streaming_ingest?.rtmp_1935}
                    </strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.78rem', color: '#64748b' }}>HLS Web (:8089): </span>
                    <strong style={{ color: mediaData?.streaming_ingest?.hls_8089 === 'ONLINE' ? '#34d399' : '#f87171' }}>
                      {mediaData?.streaming_ingest?.hls_8089}
                    </strong>
                  </div>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                  Total Media Outputs on Disk: {mediaData?.total_generated_media || 0} files
                </div>
              </div>
            </div>

            {/* Generated Media Gallery Grid */}
            <div style={{
              backgroundColor: '#0f172a',
              borderRadius: '10px',
              border: '1px solid #1e293b',
              padding: '20px'
            }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
                Recent Generated Photos, Videos & Media Assets ({mediaData?.recent_outputs?.length || 0} Previewable)
              </h3>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: '16px'
              }}>
                {mediaData?.recent_outputs?.map((m, idx) => {
                  const mediaUrl = m.media_url.startsWith('http') ? m.media_url : `${BACKEND_URL}${m.media_url}`;
                  const isVideo = m.ext === 'MP4';
                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedMediaModal(m)}
                      style={{
                        borderRadius: '8px',
                        overflow: 'hidden',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        cursor: 'pointer',
                        transition: 'transform 0.15s, border-color 0.15s',
                        display: 'flex',
                        flexDirection: 'column'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.borderColor = '#0284c7';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.transform = 'none';
                        e.currentTarget.style.borderColor = '#334155';
                      }}
                    >
                      <div style={{
                        height: '160px',
                        backgroundColor: '#0a0d14',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        overflow: 'hidden'
                      }}>
                        {isVideo ? (
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '2.5rem' }}>🎬</span>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>MP4 Video File</span>
                          </div>
                        ) : (
                          <img
                            src={mediaUrl.startsWith('http') ? mediaUrl : `${BACKEND_URL}${mediaUrl}`}
                            alt={m.filename}
                            loading="lazy"
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            onError={e => {
                              e.target.style.display = 'none';
                            }}
                          />
                        )}
                      </div>
                      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          color: '#f8fafc',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {m.filename}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#94a3b8' }}>
                          <span>{m.ext} · {m.size_kb} KB</span>
                          <span>{new Date(m.mtime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: WORK & AUTOSAVES LOG                                              */}
        {/* ========================================================================= */}
        {activeSubTab === 'saves' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* System Saves Overview */}
            <div style={{
              backgroundColor: '#0f172a',
              borderRadius: '10px',
              border: '1px solid #1e293b',
              padding: '18px 20px'
            }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
                Continuous Autosaves & State Database Ledgers
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
                {savesData?.system_saves?.map((s, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '8px',
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <strong style={{ color: '#38bdf8', fontSize: '0.85rem' }}>{s.source}</strong>
                      <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{s.type}</span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>{s.details}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '4px' }}>
                      Last state check: {new Date(s.mtime * 1000).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Files Modified in the last 24 Hours */}
            <div style={{
              backgroundColor: '#0f172a',
              borderRadius: '10px',
              border: '1px solid #1e293b',
              overflow: 'hidden'
            }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e293b', fontWeight: 600, fontSize: '0.95rem' }}>
                Files Modified Across Workspace in the Last 24 Hours ({savesData?.total_modified_last_24h || 0})
              </div>
              <div style={{ overflowX: 'auto', maxHeight: '500px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#131e33', color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '10px 16px' }}>Relative Workspace Path</th>
                      <th style={{ padding: '10px 16px' }}>Size</th>
                      <th style={{ padding: '10px 16px' }}>Last Modified Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {savesData?.recent_modified_files?.map((f, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '10px 16px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                          {f.relative_path}
                        </td>
                        <td style={{ padding: '10px 16px', color: '#a78bfa' }}>{formatBytes(f.size_bytes)}</td>
                        <td style={{ padding: '10px 16px', color: '#64748b' }}>
                          {new Date(f.mtime * 1000).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: ADMIN USER DATA VAULT                                             */}
        {/* ========================================================================= */}
        {activeSubTab === 'admin' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Database Selector Cards */}
            <div>
              <div style={{ fontSize: '0.85rem', color: '#94a3b8', margin: '0 0 10px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Select Active Admin Database Table ({adminData?.total_tables_monitored || 0} Tables Monitored)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '10px' }}>
                {adminData?.tables?.map((tbl, idx) => {
                  const isSelected = selectedAdminTable?.table === tbl.table && selectedAdminTable?.database === tbl.database;
                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedAdminTable(tbl)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '8px',
                        backgroundColor: isSelected ? 'rgba(2, 132, 199, 0.15)' : '#0f172a',
                        border: `1px solid ${isSelected ? '#0284c7' : '#1e293b'}`,
                        cursor: 'pointer',
                        transition: 'all 0.15s'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ color: isSelected ? '#38bdf8' : '#f8fafc', fontSize: '0.85rem' }}>
                          {tbl.table}
                        </strong>
                        <span style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: '#1e293b',
                          color: '#fbbf24'
                        }}>
                          {tbl.count} rows
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px' }}>
                        {tbl.database}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Table Data Viewer */}
            {selectedAdminTable && (
              <div style={{
                backgroundColor: '#0f172a',
                borderRadius: '10px',
                border: '1px solid #1e293b',
                overflow: 'hidden'
              }}>
                <div style={{
                  padding: '14px 20px',
                  borderBottom: '1px solid #1e293b',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div>
                    <span style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
                      Table: {selectedAdminTable.table}
                    </span>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginLeft: '8px' }}>
                      ({selectedAdminTable.database})
                    </span>
                  </div>
                  <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                    Showing top {selectedAdminTable.sample_records?.length || 0} sample rows
                  </span>
                </div>

                {selectedAdminTable.sample_records?.length > 0 ? (
                  <div style={{ overflowX: 'auto', maxHeight: '480px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#131e33', color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>
                          {Object.keys(selectedAdminTable.sample_records[0]).map(col => (
                            <th key={col} style={{ padding: '10px 14px', whiteSpace: 'nowrap' }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {selectedAdminTable.sample_records.map((row, rIdx) => (
                          <tr key={rIdx} style={{ borderBottom: '1px solid #1e293b' }}>
                            {Object.entries(row).map(([k, val], cIdx) => (
                              <td key={cIdx} style={{ padding: '10px 14px', color: '#cbd5e1', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {String(val)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
                    No records found in this table.
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: SYSTEM ERROR & CRASH DIAGNOSTICS                                  */}
        {/* ========================================================================= */}
        {activeSubTab === 'errors' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Split layout: Daemon Health Grid + Raw Log Tail */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 400px) 1fr', gap: '20px', alignItems: 'start' }}>
              {/* Left Column: Daemons & Log Files */}
              <div style={{
                backgroundColor: '#0f172a',
                borderRadius: '10px',
                border: '1px solid #1e293b',
                overflow: 'hidden'
              }}>
                <div style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid #1e293b',
                  fontSize: '0.88rem',
                  fontWeight: 600,
                  color: '#f8fafc',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span>Daemon Log Files ({errorData?.total_log_files || 0})</span>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Click to view raw tail</span>
                </div>
                <div style={{ overflowY: 'auto', maxHeight: '550px' }}>
                  {errorData?.daemons?.map((d, idx) => {
                    const isSelected = selectedLogFile === d.logfile;
                    const hasErrors = d.error_count_in_tail > 0;
                    return (
                      <div
                        key={idx}
                        onClick={() => setSelectedLogFile(d.logfile)}
                        style={{
                          padding: '10px 14px',
                          borderBottom: '1px solid #1e293b',
                          backgroundColor: isSelected ? 'rgba(2, 132, 199, 0.15)' : 'transparent',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px',
                          borderLeft: isSelected ? '3px solid #38bdf8' : hasErrors ? '3px solid #ef4444' : '3px solid transparent'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.82rem', fontWeight: 600, color: isSelected ? '#38bdf8' : '#e2e8f0' }}>
                            {d.logfile}
                          </span>
                          {hasErrors && (
                            <span style={{
                              fontSize: '0.68rem',
                              fontWeight: 700,
                              padding: '1px 5px',
                              borderRadius: '3px',
                              backgroundColor: 'rgba(239, 68, 68, 0.2)',
                              color: '#f87171'
                            }}>
                              {d.error_count_in_tail} errs
                            </span>
                          )}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#64748b' }}>
                          <span>Size: {d.size_kb} KB</span>
                          <span>{d.status}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Live Log Tail Viewer */}
              <div style={{
                backgroundColor: '#0f172a',
                borderRadius: '10px',
                border: '1px solid #1e293b',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div style={{
                  padding: '12px 18px',
                  borderBottom: '1px solid #1e293b',
                  backgroundColor: '#131e33',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                      Terminal Log Tail:
                    </span>
                    <span style={{ fontSize: '0.85rem', fontFamily: 'monospace', color: '#38bdf8' }}>
                      {selectedLogFile}
                    </span>
                  </div>
                  <button
                    onClick={() => fetchLogTail(selectedLogFile)}
                    disabled={logTailLoading}
                    style={{
                      padding: '4px 10px',
                      borderRadius: '4px',
                      backgroundColor: '#1e293b',
                      color: '#94a3b8',
                      border: '1px solid #334155',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    {logTailLoading ? 'Refreshing...' : 'Reload Log Tail'}
                  </button>
                </div>

                <div style={{
                  padding: '16px',
                  backgroundColor: '#060911',
                  color: '#a7f3d0',
                  fontFamily: 'Consolas, monospace',
                  fontSize: '0.78rem',
                  lineHeight: '1.45',
                  overflowY: 'auto',
                  maxHeight: '520px',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {logTailLoading ? 'Loading log stream...' : logTailContent}
                </div>
              </div>
            </div>

            {/* Error Feed Log Table */}
            <div style={{
              backgroundColor: '#0f172a',
              borderRadius: '10px',
              border: '1px solid #1e293b',
              overflow: 'hidden'
            }}>
              <div style={{
                padding: '14px 18px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '10px'
              }}>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f87171' }}>
                  Extracted Error Events & Tracebacks ({filteredErrors.length})
                </div>
                <input
                  type="text"
                  placeholder="Filter by log filename or error text..."
                  value={errorFilter}
                  onChange={e => setErrorFilter(e.target.value)}
                  style={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    color: '#f8fafc',
                    fontSize: '0.82rem',
                    minWidth: '280px',
                    outline: 'none'
                  }}
                />
              </div>

              <div style={{ overflowX: 'auto', maxHeight: '350px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#131e33', color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '10px 16px', width: '220px' }}>Log File Source</th>
                      <th style={{ padding: '10px 16px' }}>Extracted Line / Error Traceback</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredErrors.map((err, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '10px 16px', fontWeight: 600, color: '#a78bfa' }}>
                          {err.log_file}
                        </td>
                        <td style={{ padding: '10px 16px', fontFamily: 'monospace', color: '#fca5a5' }}>
                          {err.line}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── MEDIA PREVIEW MODAL ───────────────────────────────────── */}
      {selectedMediaModal && (
        <div
          onClick={() => setSelectedMediaModal(null)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '24px'
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              backgroundColor: '#0f172a',
              borderRadius: '12px',
              border: '1px solid #334155',
              maxWidth: '900px',
              maxHeight: '90vh',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            <div style={{
              padding: '12px 18px',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <strong style={{ color: '#f8fafc', fontSize: '0.95rem' }}>{selectedMediaModal.filename}</strong>
                <span style={{ fontSize: '0.78rem', color: '#94a3b8', marginLeft: '10px' }}>
                  {selectedMediaModal.ext} · {selectedMediaModal.size_kb} KB
                </span>
              </div>
              <button
                onClick={() => setSelectedMediaModal(null)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '1.2rem',
                  cursor: 'pointer'
                }}
              >
                ✕
              </button>
            </div>
            <div style={{ padding: '20px', display: 'flex', justifyContent: 'center', backgroundColor: '#020617' }}>
              {selectedMediaModal.ext === 'MP4' ? (
                <video
                  controls
                  autoPlay
                  style={{ maxWidth: '100%', maxHeight: '65vh', borderRadius: '8px' }}
                  src={selectedMediaModal.media_url.startsWith('http') ? selectedMediaModal.media_url : `${BACKEND_URL}${selectedMediaModal.media_url}`}
                />
              ) : (
                <img
                  src={selectedMediaModal.media_url.startsWith('http') ? selectedMediaModal.media_url : `${BACKEND_URL}${selectedMediaModal.media_url}`}
                  alt={selectedMediaModal.filename}
                  style={{ maxWidth: '100%', maxHeight: '65vh', objectFit: 'contain', borderRadius: '8px' }}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OperationsAuditHubTab;
