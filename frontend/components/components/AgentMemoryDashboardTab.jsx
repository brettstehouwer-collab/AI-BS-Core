import React, { useState, useEffect, useRef } from 'react';
import MemoryBankSupervisor from './MemoryBankSupervisor.jsx';

// ─── colour palette for file-type bars ───────────────────────────────────────
const TYPE_COLORS = {
  py:   '#4ade80',
  md:   '#60a5fa',
  pdf:  '#f97316',
  txt:  '#facc15',
  json: '#c084fc',
  other:'#94a3b8',
};

function IngestionMonitor({ backendUrl }) {
  const [stats, setStats]           = useState(null);
  const [error, setError]           = useState(null);
  const intervalRef                 = useRef(null);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/ingestion/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStats(await res.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    fetchStats();
    intervalRef.current = setInterval(fetchStats, 3000);   // poll every 3 s
    return () => clearInterval(intervalRef.current);
  }, []);

  const total = stats?.files_processed?.total ?? 0;
  const fp    = stats?.files_processed ?? {};

  // Build bar segments
  const types = ['py','md','pdf','txt','json','other'];
  const segments = types.map(t => ({ key: t, count: fp[t] ?? 0 })).filter(s => s.count > 0);

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(74,222,128,0.06) 0%, rgba(96,165,250,0.06) 100%)',
      border: '1px solid rgba(74,222,128,0.25)',
      borderRadius: '12px',
      padding: '20px',
      marginBottom: '20px',
    }}>
      {/* Header row */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'16px' }}>
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <span style={{ fontSize:'1.3rem' }}>💾</span>
          <h3 style={{ margin:0, color:'#4ade80', fontSize:'1rem', fontWeight:700 }}>
            SSD Knowledge Ingestion
          </h3>
          {/* live pulse dot */}
          <span style={{
            width:8, height:8, borderRadius:'50%',
            background: stats?.status === 'running' ? '#4ade80' : '#6b7280',
            display:'inline-block',
            boxShadow: stats?.status === 'running' ? '0 0 6px #4ade80' : 'none',
            animation: stats?.status === 'running' ? 'pulse 1.5s infinite' : 'none',
          }}/>
          <span style={{ fontSize:'0.75rem', color: stats?.status === 'running' ? '#4ade80' : '#6b7280' }}>
            {stats?.status === 'running' ? 'LIVE' : 'IDLE'}
          </span>
        </div>
        <div style={{ fontSize:'1.6rem', fontWeight:800, color:'#fff' }}>
          {total.toLocaleString()}
          <span style={{ fontSize:'0.8rem', color:'#aaa', fontWeight:400, marginLeft:4 }}>files</span>
        </div>
      </div>

      {error && <p style={{ color:'#f87171', fontSize:'0.8rem', margin:'0 0 8px' }}>⚠ {error}</p>}

      {/* Stacked progress bar */}
      {total > 0 && (
        <div style={{ height:12, borderRadius:6, overflow:'hidden', display:'flex', marginBottom:12, background:'rgba(0,0,0,0.3)' }}>
          {segments.map(({ key, count }) => (
            <div key={key} style={{
              width: `${(count / total) * 100}%`,
              background: TYPE_COLORS[key],
              transition: 'width 0.6s ease',
            }}/>
          ))}
        </div>
      )}

      {/* Legend */}
      <div style={{ display:'flex', flexWrap:'wrap', gap:'10px', marginBottom:14 }}>
        {types.map(t => (fp[t] ?? 0) > 0 && (
          <div key={t} style={{ display:'flex', alignItems:'center', gap:5, fontSize:'0.78rem', color:'#ccc' }}>
            <span style={{ width:10, height:10, borderRadius:2, background:TYPE_COLORS[t], display:'inline-block' }}/>
            <span style={{ color: TYPE_COLORS[t], fontWeight:600 }}>.{t}</span>
            <span>{(fp[t] ?? 0).toLocaleString()}</span>
          </div>
        ))}
      </div>

      {/* Current file ticker */}
      {stats?.current_file && (
        <div style={{
          background:'rgba(0,0,0,0.4)', borderRadius:6, padding:'6px 10px',
          fontFamily:'monospace', fontSize:'0.72rem', color:'#60a5fa',
          whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
        }}>
          🔄 {stats.current_file}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%,100% { opacity:1; }
          50%      { opacity:0.3; }
        }
      `}</style>
    </div>
  );
}


export default function AgentMemoryDashboardTab(props) {
  const { backendUrl, currentUser } = props;
  
  const [memoryItems, setMemoryItems] = useState([]);
  const [sandboxState, setSandboxState] = useState("{}");
  const [newMemoryInput, setNewMemoryInput] = useState("");
  const [newMemoryMeta, setNewMemoryMeta] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Fetch data
  const fetchData = async () => {
    setIsLoading(true);
    try {
      // Fetch Memory
      const memRes = await fetch(`${backendUrl}/api/memory`);
      if (memRes.ok) {
        const data = await memRes.json();
        const formatted = (data.ids || []).map((id, i) => ({
          id,
          content: data.documents[i],
          metadata: data.metadatas[i] || {}
        }));
        setMemoryItems(formatted);
      }
      
      // Fetch State
      const stateRes = await fetch(`${backendUrl}/api/state`);
      if (stateRes.ok) {
        const stateData = await stateRes.json();
        setSandboxState(JSON.stringify(stateData.state, null, 2));
      }
    } catch (err) {
      console.error("Error fetching dashboard data", err);
    }
    setIsLoading(false);
  };
  
  useEffect(() => {
    fetchData();
  }, []);
  
  const handleAddMemory = async () => {
    if (!newMemoryInput.trim()) return;
    try {
      let meta = {};
      if (newMemoryMeta.trim()) {
        meta = JSON.parse(newMemoryMeta);
      }
      const res = await fetch(`${backendUrl}/api/memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newMemoryInput, metadata: meta })
      });
      if (res.ok) {
        setNewMemoryInput("");
        setNewMemoryMeta("");
        fetchData();
      }
    } catch (err) {
      alert("Error adding memory or invalid metadata JSON");
    }
  };
  
  const handleDeleteMemory = async (id) => {
    try {
      const res = await fetch(`${backendUrl}/api/memory/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSaveState = async () => {
    try {
      const parsed = JSON.parse(sandboxState);
      const res = await fetch(`${backendUrl}/api/state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: parsed })
      });
      if (res.ok) {
        alert("State saved successfully!");
      }
    } catch (err) {
      alert("Invalid JSON format in state.");
    }
  };

  const handleWipeMemory = async () => {
    try {
      await fetch(`${backendUrl}/api/friction/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'MEMORY_WIPE',
          diagnostic_trace: 'User requested wiping all long-term vector memory in stehouwer_llm_memory collection. This is a destructive action.',
          target_url: '/api/memory/wipe' // assuming backend supports this after friction
        })
      });
      // The Friction Modal will catch this via websockets
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto', padding: '20px', gap: '20px', color: '#fff' }}>
      
      {/* 🧠 Live Python Memory Bank + Infinite Learning Loop Status */}
      <MemoryBankSupervisor backendUrl={backendUrl} />

      <div style={{ display: 'flex', flexDirection: 'row', flex: 1, minHeight: '600px', gap: '20px' }}>
        {/* Left Column: Vector Memory Log */}
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px', borderRadius: '12px', overflow: 'hidden' }}>
          <h2 style={{ color: '#4ade80', margin: '0 0 16px 0' }}>🧠 Agent Vector Memory</h2>
          <p style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '20px' }}>
            This collection (stehouwer_llm_memory) stores case libraries, session variables, and critical directives like the "Architecture of Ethical Utility".
          </p>
          
          <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', border: '1px solid rgba(255,255,255,0.1)', padding: '10px', borderRadius: '8px' }}>
            {isLoading ? <p>Loading memories...</p> : memoryItems.map((item) => (
              <div key={item.id} style={{ background: 'rgba(0,0,0,0.4)', padding: '12px', borderRadius: '8px', marginBottom: '10px', borderLeft: '4px solid #4ade80' }}>
                <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '8px' }}>ID: {item.id}</div>
                <div style={{ whiteSpace: 'pre-wrap', marginBottom: '8px' }}>{item.content}</div>
                <div style={{ fontSize: '0.8rem', color: '#aaa', background: '#222', padding: '4px', borderRadius: '4px' }}>
                  Metadata: {JSON.stringify(item.metadata)}
                </div>
                <button onClick={() => handleDeleteMemory(item.id)} style={{ marginTop: '8px', background: 'rgba(255,0,0,0.2)', color: '#ff6b6b', border: '1px solid rgba(255,0,0,0.5)', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>
                  Forget Context
                </button>
              </div>
            ))}
            {memoryItems.length === 0 && !isLoading && <p style={{ color: '#666' }}>No memories stored yet.</p>}
          </div>

          {/* Add Memory Form */}
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px' }}>
            <h3 style={{ margin: '0 0 8px 0' }}>Inject New Directive/Memory</h3>
            <textarea 
              aria-label="New Memory Content"
              value={newMemoryInput}
              onChange={(e) => setNewMemoryInput(e.target.value)}
              placeholder="E.g., Directive: Architecture of Ethical Utility..."
              style={{ width: '100%', height: '60px', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '8px', borderRadius: '4px', marginBottom: '8px' }}
            />
            <input 
              aria-label="New Memory Metadata"
              value={newMemoryMeta}
              onChange={(e) => setNewMemoryMeta(e.target.value)}
              placeholder='Metadata (JSON optional): {"type": "directive"}'
              style={{ width: '100%', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', padding: '8px', borderRadius: '4px', marginBottom: '8px' }}
            />
            <button onClick={handleAddMemory} style={{ background: '#4ade80', color: '#000', border: 'none', padding: '8px 16px', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer', marginRight: '10px' }}>
              Store in Vector DB
            </button>
            <button onClick={() => setShowAdvanced(!showAdvanced)} style={{ background: 'transparent', color: '#aaa', border: '1px solid #444', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}>
              {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
            </button>
          </div>
            
          {/* Advanced Danger Zone */}
          {showAdvanced && (
            <div style={{ marginTop: '16px', border: '1px solid #ff4444', background: 'rgba(255,0,0,0.05)', padding: '16px', borderRadius: '8px' }}>
              <h3 style={{ margin: '0 0 8px 0', color: '#ffaaaa' }}>⚠️ Danger Zone</h3>
              <p style={{ fontSize: '0.85rem', color: '#ccc', marginBottom: '12px' }}>
                Wiping Long-Term Memory will completely destroy the AI's stored vector memory (ChromaDB). This action requires Admin verification.
              </p>
              <button onClick={handleWipeMemory} style={{ background: 'rgba(255,0,0,0.2)', color: '#ff6b6b', border: '1px solid rgba(255,0,0,0.5)', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                Wipe Long-Term Memory (ChromaDB)
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Sandbox State Monitor */}
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px', borderRadius: '12px' }}>
          <h2 style={{ color: '#60a5fa', margin: '0 0 16px 0' }}>🛡️ Execution Sandbox State</h2>
          <p style={{ color: '#aaa', fontSize: '0.9rem', marginBottom: '20px' }}>
            The local state.json ensures crash-recovery and provides environmental awareness to the Orchestrator/Executor bifurcation logic.
          </p>

          <textarea
            aria-label="Sandbox State JSON"
            value={sandboxState}
            onChange={(e) => setSandboxState(e.target.value)}
            style={{
              flex: 1,
              width: '100%',
              background: '#1e1e1e',
              color: '#d4d4d4',
              fontFamily: 'monospace',
              padding: '12px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.1)',
              resize: 'none',
              marginBottom: '16px'
            }}
          />

          <button onClick={handleSaveState} style={{ background: '#60a5fa', color: '#000', border: 'none', padding: '12px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
            Save / Override state.json
          </button>
        </div>
      </div>
    </div>
  );
}
