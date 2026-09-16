import React, { useState, useEffect, useRef } from 'react';

function TerminalWindow({ title, logs, statusColor = "#4ade80" }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'rgba(10, 10, 10, 0.75)',
      backdropFilter: 'blur(12px) saturate(180%)',
      WebkitBackdropFilter: 'blur(12px) saturate(180%)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      borderRadius: '8px',
      overflow: 'hidden',
      boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
    }}>
      <div style={{
        padding: '8px 12px',
        backgroundColor: 'rgba(26, 26, 26, 0.8)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: statusColor,
          boxShadow: `0 0 10px ${statusColor}`,
          animation: 'statusPulse 2s infinite ease-in-out'
        }}></div>
        <span style={{ color: '#fff', fontSize: '0.85rem', fontWeight: 'bold', letterSpacing: '1px' }}>{title}</span>
      </div>
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '10px', fontFamily: 'monospace', fontSize: '0.75rem', lineHeight: '1.4', color: '#00ff41' }}>
        {logs && logs.length > 0 ? (
          logs.map((line, i) => (
            <div key={i} style={{ wordBreak: 'break-all', marginBottom: '2px' }}>{line || '\u00A0'}</div>
          ))
        ) : (
          <div style={{ color: '#555', fontStyle: 'italic' }}>Awaiting data stream...</div>
        )}
      </div>
    </div>
  );
}

export default function BullshitTelemetrySuite(props) {
  const { BACKEND_URL = `http://${window.location.hostname}:8000`, activeTab } = props;

  // SYSTEM ANALYTICS STATE
  const [daemonLogs, setDaemonLogs] = useState({
    ollama: [], backend: [], remote_bridge: [], hunter: [], trainer: [], refactoring: []
  });
  const [isPolling, setIsPolling] = useState(true);

  // AGENT MEMORY DASHBOARD STATE
  const [memoryItems, setMemoryItems] = useState([]);
  const [sandboxState, setSandboxState] = useState("{}");
  const [newMemoryInput, setNewMemoryInput] = useState("");
  const [newMemoryMeta, setNewMemoryMeta] = useState("");
  const [isMemLoading, setIsMemLoading] = useState(false);

  // MEMORY VISUALIZER STATE
  const [memoryStream, setMemoryStream] = useState([]);

  // FETCHING LOGIC
  useEffect(() => {
    if (activeTab === 'system_analytics' && isPolling) {
      const fetchLogs = async () => {
        try {
          const res = await fetch(`${BACKEND_URL}/api/system/daemon_logs`);
          if (res.ok) {
            const data = await res.json();
            if (data.status === 'success') setDaemonLogs(data.logs);
          }
        } catch (err) {}
      };
      fetchLogs();
      const interval = setInterval(fetchLogs, 1500);
      return () => clearInterval(interval);
    }
  }, [activeTab, isPolling, BACKEND_URL]);

  const fetchMemoryData = async () => {
    setIsMemLoading(true);
    try {
      const memRes = await fetch(`${BACKEND_URL}/api/memory`);
      if (memRes.ok) {
        const data = await memRes.json();
        const formatted = (data.ids || []).map((id, i) => ({
          id, content: data.documents[i], metadata: data.metadatas[i] || {}
        }));
        setMemoryItems(formatted);
      }
      const stateRes = await fetch(`${BACKEND_URL}/api/state`);
      if (stateRes.ok) {
        const stateData = await stateRes.json();
        setSandboxState(JSON.stringify(stateData.state, null, 2));
      }
    } catch (err) {}
    setIsMemLoading(false);
  };

  useEffect(() => {
    if (activeTab === 'memory') {
      fetchMemoryData();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === 'memory_visualizer') {
      fetch(`${BACKEND_URL}/memory/stats`)
        .then(res => res.json())
        .then(data => setMemoryStream(data.recent_memories || []))
        .catch(err => console.error(err));
    }
  }, [activeTab]);

  const handleAddMemory = async () => {
    if (!newMemoryInput.trim()) return;
    try {
      let meta = {};
      if (newMemoryMeta.trim()) meta = JSON.parse(newMemoryMeta);
      const res = await fetch(`${BACKEND_URL}/api/memory`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newMemoryInput, metadata: meta })
      });
      if (res.ok) {
        setNewMemoryInput(""); setNewMemoryMeta("");
        fetchMemoryData();
      }
    } catch (err) { alert("Error adding memory or invalid metadata JSON"); }
  };

  const handleDeleteMemory = async (id) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/memory/${id}`, { method: 'DELETE' });
      if (res.ok) fetchMemoryData();
    } catch (err) {}
  };

  const handleSaveState = async () => {
    try {
      const parsed = JSON.parse(sandboxState);
      const res = await fetch(`${BACKEND_URL}/api/state`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: parsed })
      });
      if (res.ok) alert("State saved successfully!");
    } catch (err) { alert("Invalid JSON format in state."); }
  };

  if (activeTab === 'system_analytics') {
    return (
      <div className='tab-content fade-in' style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px', background: 'transparent' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <div>
            <h2 style={{ margin: 0, color: '#fff', textShadow: '0 0 10px rgba(255,255,255,0.3)' }}>AI-BS Matrix Dashboard</h2>
            <p style={{ margin: '5px 0 0 0', color: '#888', fontSize: '0.9rem' }}>Real-time telemetry from all 6 headless cognitive daemons.</p>
          </div>
          <button 
            onClick={() => setIsPolling(!isPolling)}
            style={{ background: isPolling ? 'rgba(255,0,0,0.2)' : 'rgba(0,255,0,0.2)', color: isPolling ? '#ff6b6b' : '#4ade80', border: `1px solid ${isPolling ? '#ff6b6b' : '#4ade80'}`, padding: '6px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            {isPolling ? '⏸ PAUSE TELEMETRY' : '▶ RESUME STREAM'}
          </button>
        </div>
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gridTemplateRows: 'repeat(2, 1fr)', gap: '15px', minHeight: 0 }}>
          <TerminalWindow title="[1] Ollama Neural Engine" logs={daemonLogs.ollama} statusColor="#a855f7" />
          <TerminalWindow title="[2] AI-BS Backend API" logs={daemonLogs.backend} statusColor="#3b82f6" />
          <TerminalWindow title="[3] Airgapped Remote Bridge" logs={daemonLogs.remote_bridge} statusColor="#f59e0b" />
          <TerminalWindow title="[4] Hunter-Gatherer Daemon" logs={daemonLogs.hunter} statusColor="#10b981" />
          <TerminalWindow title="[5] Trainer Daemon" logs={daemonLogs.trainer} statusColor="#06b6d4" />
          <TerminalWindow title="[6] Refactoring Daemon" logs={daemonLogs.refactoring} statusColor="#ef4444" />
        </div>
      </div>
    );
  }

  if (activeTab === 'memory') {
    return (
      <div style={{ display: 'flex', flexDirection: 'row', height: '100%', padding: '20px', gap: '20px', color: '#fff' }}>
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px', borderRadius: '12px', overflow: 'hidden' }}>
          <h2 style={{ color: '#4ade80', margin: '0 0 16px 0' }}>🧠 Agent Vector Memory</h2>
          <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', border: '1px solid rgba(255,255,255,0.1)', padding: '10px', borderRadius: '8px' }}>
            {isMemLoading ? <p>Loading memories...</p> : memoryItems.map((item) => (
              <div key={item.id} style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '8px', marginBottom: '10px', borderLeft: '4px solid #4ade80' }}>
                <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '8px' }}>ID: {item.id}</div>
                <div style={{ whiteSpace: 'pre-wrap', marginBottom: '8px' }}>{item.content}</div>
                <div style={{ fontSize: '0.8rem', color: '#aaa', background: '#222', padding: '4px', borderRadius: '4px' }}>Metadata: {JSON.stringify(item.metadata)}</div>
                <button onClick={() => handleDeleteMemory(item.id)} style={{ marginTop: '8px', background: 'rgba(255,0,0,0.2)', color: '#ff6b6b', border: '1px solid rgba(255,0,0,0.5)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>Forget Context</button>
              </div>
            ))}
            {memoryItems.length === 0 && !isMemLoading && <p style={{ color: '#666' }}>No memories stored yet.</p>}
          </div>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px 0' }}>Inject New Directive/Memory</h4>
            <textarea value={newMemoryInput} onChange={(e) => setNewMemoryInput(e.target.value)} placeholder="E.g., Directive: Architecture of Ethical Utility..." style={{ width: '100%', height: '60px', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '8px', borderRadius: '4px', marginBottom: '8px' }} />
            <input value={newMemoryMeta} onChange={(e) => setNewMemoryMeta(e.target.value)} placeholder='Metadata (JSON optional): {"type": "directive"}' style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '8px', borderRadius: '4px', marginBottom: '8px' }} />
            <button onClick={handleAddMemory} style={{ background: '#4ade80', color: '#000', border: 'none', padding: '8px 16px', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer' }}>Store in Vector DB</button>
          </div>
        </div>
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px', borderRadius: '12px' }}>
          <h2 style={{ color: '#60a5fa', margin: '0 0 16px 0' }}>🛡️ Execution Sandbox State</h2>
          <textarea value={sandboxState} onChange={(e) => setSandboxState(e.target.value)} style={{ flex: 1, width: '100%', background: '#1e1e1e', color: '#d4d4d4', fontFamily: 'monospace', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', resize: 'none', marginBottom: '16px' }} />
          <button onClick={handleSaveState} style={{ background: '#60a5fa', color: '#000', border: 'none', padding: '12px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Save / Override state.json</button>
        </div>
      </div>
    );
  }

  if (activeTab === 'memory_visualizer') {
    return (
      <div style={{ padding: '20px', color: '#fff', height: '100%', display: 'flex', flexDirection: 'column' }}>
        <h2 style={{ color: '#c084fc' }}>🧠 Real-Time Memory Visualizer</h2>
        <div className="glass-panel" style={{ flex: 1, padding: '20px', borderRadius: '12px', overflowY: 'auto', background: '#111' }}>
          {memoryStream.length > 0 ? memoryStream.map((mem, idx) => (
            <div key={idx} style={{ padding: '10px', borderBottom: '1px solid #333' }}>
              <span style={{ color: '#4ade80' }}>[{mem.timestamp || 'Just Now'}]</span> {mem.content || mem}
            </div>
          )) : <div style={{ color: '#555', textAlign: 'center', marginTop: '50px' }}>[Memory Stream is Idle.]</div>}
        </div>
      </div>
    );
  }

  if (activeTab === 'noco_telemetry') {
    return (
      <div className="noco-workspace-grid">
        <div className="noco-panel glass-panel">
          <h3>🌱 Live Aero-Agri Telemetry</h3>
          <div className="telemetry-grid">
            <div className="telemetry-card"><div className="tele-val">{props.nocoTelemetry?.temp || 0} °C</div></div>
            <div className="telemetry-card"><div className="tele-val">{props.nocoTelemetry?.mfcOutput || 0} mW</div></div>
            <div className="telemetry-card"><div className="tele-val">{props.nocoTelemetry?.aeroponicLayers || 0}</div></div>
          </div>
          <div className="noco-alerts-card">
            <h4>⚠️ Telemetry Diagnostic Alerts</h4>
            {props.nocoAlert ? <div className="alert-message active-alert"><strong>ALERT:</strong> {props.nocoAlert}</div> : <div className="alert-message normal-state">🟢 Nominal state.</div>}
            <button className="noco-alert-btn" onClick={props.handleTriggerNocoAlert}>💥 Trigger Anomaly</button>
          </div>
        </div>
        <div className="noco-panel glass-panel">
          <h3>🛠️ Microcontroller Automation Coder</h3>
          <div className="noco-coder-controls">
            <select value={props.nocoCodeType} onChange={(e) => props.setNocoCodeType(e.target.value)}>
              <option value="arduino">Arduino</option><option value="raspberry_pi">Raspberry Pi</option>
            </select>
            <textarea className="noco-prompt-input" value={props.nocoCodePrompt} onChange={(e) => props.setNocoCodePrompt(e.target.value)} />
            <button className="noco-btn-code" onClick={props.handleGenerateNocoCode}>{props.isGeneratingNocoCode ? 'Compiling...' : '💾 Generate Automation Code'}</button>
          </div>
          {props.nocoGeneratedCode && <pre className="code-pre"><code>{props.nocoGeneratedCode}</code></pre>}
        </div>
      </div>
    );
  }

  return null;
}
