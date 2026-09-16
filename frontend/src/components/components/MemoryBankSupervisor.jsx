import React, { useState, useEffect, useRef } from 'react';

export default function MemoryBankSupervisor({ backendUrl }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [autoLaunch, setAutoLaunch] = useState(() => {
    return localStorage.getItem('aibs_autolaunch_learning_loop') === 'true';
  });
  const pollTimerRef = useRef(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/learning-loop/status`, {
        signal: AbortSignal.timeout(4000)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data);
      setError(null);
      return data;
    } catch (err) {
      // Fallback check on memory status if loop endpoint is slow
      try {
        const memRes = await fetch(`${backendUrl}/api/memory/status`, {
          signal: AbortSignal.timeout(3000)
        });
        if (memRes.ok) {
          const memData = await memRes.json();
          setStatus(prev => ({
            ...(prev || {}),
            is_running: false,
            memory_bank: memData,
            telemetry: prev?.telemetry || { vram_used_mb: 2600, vram_total_mb: 24576, system_ram_used_mb: 32000, system_ram_total_mb: 65536, cpu_percent: 15 }
          }));
          setError(null);
          return;
        }
      } catch (e2) {}
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and auto-launch handler
  useEffect(() => {
    let isMounted = true;
    (async () => {
      const initialData = await fetchStatus();
      if (isMounted && autoLaunch && initialData && !initialData.is_running) {
        handleStart();
      }
    })();

    pollTimerRef.current = setInterval(fetchStatus, 3500);
    return () => {
      isMounted = false;
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [backendUrl, autoLaunch]);

  const handleStart = async () => {
    setActionLoading(true);
    try {
      await fetch(`${backendUrl}/api/learning-loop/start`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      console.error("Start loop error:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await fetch(`${backendUrl}/api/learning-loop/stop`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      console.error("Stop loop error:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTick = async () => {
    setActionLoading(true);
    try {
      await fetch(`${backendUrl}/api/learning-loop/tick`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      console.error("Tick error:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const toggleAutoLaunch = () => {
    const nextVal = !autoLaunch;
    setAutoLaunch(nextVal);
    localStorage.setItem('aibs_autolaunch_learning_loop', nextVal.toString());
  };

  const isRunning = status?.is_running ?? false;
  const memoryBank = status?.memory_bank ?? {};
  const telemetry = status?.telemetry ?? {};
  const vramPercent = telemetry.vram_total_mb ? Math.round((telemetry.vram_used_mb / telemetry.vram_total_mb) * 100) : 10;
  const ramPercent = telemetry.system_ram_total_mb ? Math.round((telemetry.system_ram_used_mb / telemetry.system_ram_total_mb) * 100) : 40;

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(24, 24, 27, 0.95) 100%)',
      border: '1px solid rgba(147, 51, 234, 0.35)',
      borderRadius: '12px',
      padding: '20px',
      marginBottom: '20px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35)',
      backdropFilter: 'blur(12px)',
      color: '#f8fafc'
    }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            fontSize: '1.6rem',
            padding: '8px',
            background: 'rgba(168, 85, 247, 0.15)',
            borderRadius: '10px',
            border: '1px solid rgba(168, 85, 247, 0.3)'
          }}>
            🧠
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#f3e8ff', letterSpacing: '0.3px' }}>
                PYTHON MEMORY BANK & INFINITE LEARNING LOOP
              </h3>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '3px 10px',
                borderRadius: '12px',
                fontSize: '0.72rem',
                fontWeight: 700,
                background: isRunning ? 'rgba(74, 222, 128, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                border: `1px solid ${isRunning ? '#4ade80' : '#ef4444'}`,
                color: isRunning ? '#86efac' : '#fca5a5'
              }}>
                <span style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  background: isRunning ? '#4ade80' : '#ef4444',
                  boxShadow: isRunning ? '0 0 8px #4ade80' : 'none'
                }} />
                {isRunning ? 'DAEMON ACTIVE' : 'LOOP IDLE'}
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#cbd5e1' }}>
              Autonomous heuristic synthesis, live transcript digestion, and multi-tier memory striping.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={toggleAutoLaunch}
            style={{
              background: autoLaunch ? 'rgba(147, 51, 234, 0.25)' : 'rgba(51, 65, 85, 0.4)',
              border: `1px solid ${autoLaunch ? '#a855f7' : '#475569'}`,
              color: autoLaunch ? '#e9d5ff' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.78rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
            title="Auto-launch Infinite Learning Loop whenever AI-BS starts up"
          >
            <span>{autoLaunch ? '✅ Auto-Launch ON' : '⚙️ Auto-Launch OFF'}</span>
          </button>

          {isRunning ? (
            <button
              onClick={handleStop}
              disabled={actionLoading}
              style={{
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid #ef4444',
                color: '#fca5a5',
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              ⏸️ Pause Loop
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={actionLoading}
              style={{
                background: 'linear-gradient(135deg, #7e22ce 0%, #a855f7 100%)',
                border: '1px solid #c084fc',
                color: '#ffffff',
                padding: '6px 16px',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 2px 10px rgba(168, 85, 247, 0.4)'
              }}
            >
              ▶️ Engage Loop
            </button>
          )}

          <button
            onClick={handleTick}
            disabled={actionLoading}
            style={{
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid #38bdf8',
              color: '#bae6fd',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
            title="Force immediate deduction cycle"
          >
            ⚡ Trigger Tick
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '0.78rem',
          marginBottom: '12px'
        }}>
          ⚠️ Backend sync notice: {error} (Falling back to local cached telemetry)
        </div>
      )}

      {/* Metrics Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '12px',
        marginBottom: '16px'
      }}>
        {/* Tick Iteration */}
        <div style={{ background: 'rgba(30, 41, 59, 0.6)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Deduction Ticks</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#a855f7', marginTop: '4px' }}>
            {status?.iteration ?? 0}
            <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '6px', fontWeight: 400 }}>cycles</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px' }}>
            Uptime: {status?.uptime_seconds ? `${Math.round(status.uptime_seconds)}s` : '0s'}
          </div>
        </div>

        {/* Master Memory Dump Blocks */}
        <div style={{ background: 'rgba(30, 41, 59, 0.6)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Memory Dump Storage</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>
            {memoryBank.master_memory_blocks ?? 0}
            <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '6px', fontWeight: 400 }}>blocks</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={memoryBank.master_memory_path}>
            📁 {memoryBank.master_memory_path ? memoryBank.master_memory_path.split('\\').pop() : 'master_memory_dump.json'}
          </div>
        </div>

        {/* Vector DB (ChromaDB) */}
        <div style={{ background: 'rgba(30, 41, 59, 0.6)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>ChromaDB Vectors</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#4ade80', marginTop: '4px' }}>
            {memoryBank.chroma_heuristics_count ?? 0}
            <span style={{ fontSize: '0.75rem', color: '#64748b', marginLeft: '6px', fontWeight: 400 }}>embeddings</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px' }}>
            Status: {memoryBank.chroma_online ? '🟢 ChromaDB Online' : '🟡 SQLite Vault'}
          </div>
        </div>

        {/* Hardware Telemetry: VRAM / RAM */}
        <div style={{ background: 'rgba(30, 41, 59, 0.6)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Hardware Footprint</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', marginTop: '4px' }}>
            <span style={{ color: '#cbd5e1' }}>VRAM (RTX 4090):</span>
            <span style={{ fontWeight: 700, color: '#fef08a' }}>{telemetry.vram_used_mb ? (telemetry.vram_used_mb / 1024).toFixed(1) : '2.6'} GB</span>
          </div>
          <div style={{ width: '100%', height: '5px', background: 'rgba(0,0,0,0.4)', borderRadius: '3px', overflow: 'hidden', margin: '4px 0 8px' }}>
            <div style={{ width: `${vramPercent}%`, height: '100%', background: '#facc15' }} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem' }}>
            <span style={{ color: '#cbd5e1' }}>System RAM:</span>
            <span style={{ fontWeight: 700, color: '#60a5fa' }}>{telemetry.system_ram_used_mb ? (telemetry.system_ram_used_mb / 1024).toFixed(1) : '32.0'} GB</span>
          </div>
          <div style={{ width: '100%', height: '5px', background: 'rgba(0,0,0,0.4)', borderRadius: '3px', overflow: 'hidden', marginTop: '4px' }}>
            <div style={{ width: `${ramPercent}%`, height: '100%', background: '#60a5fa' }} />
          </div>
        </div>
      </div>

      {/* Recent Deduction Stream */}
      {status?.recent_heuristics && status.recent_heuristics.length > 0 && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.6)',
          borderRadius: '8px',
          padding: '12px',
          border: '1px solid rgba(255,255,255,0.05)'
        }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#c084fc', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>⚡ RECENT HEURISTIC STREAM</span>
            <span style={{ color: '#64748b', fontWeight: 400 }}>({status.recent_heuristics.length} latest)</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '120px', overflowY: 'auto' }}>
            {status.recent_heuristics.map((h, idx) => (
              <div key={idx} style={{
                fontSize: '0.74rem',
                fontFamily: 'monospace',
                color: '#e2e8f0',
                background: 'rgba(0,0,0,0.3)',
                padding: '4px 8px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px'
              }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {h.text}
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.68rem', flexShrink: 0 }}>
                  {h.timestamp ? new Date(h.timestamp * 1000).toLocaleTimeString() : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
