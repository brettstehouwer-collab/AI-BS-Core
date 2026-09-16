import React, { useState, useEffect, useCallback } from 'react';
import { useAppStore } from './useAppStore';
import DraggableGridWorkspace from './DraggableGridWorkspace.jsx';
import DroppableContainer from './dnd/DroppableContainer.jsx';
import DraggableItem from './dnd/DraggableItem.jsx';
import SimpleDashboardPortal from './SimpleDashboardPortal.jsx';
import MemoryBankSupervisor from './MemoryBankSupervisor.jsx';
import './CommandCenterTab.css';

const DEFAULT_LAYOUT = [
  { i: 'header', x: 0, y: 0, w: 24, h: 3, static: true },
  { i: 'daemon_supervisor', x: 0, y: 3, w: 24, h: 7 },
  { i: 'agent_launcher', x: 0, y: 10, w: 12, h: 11 },
  { i: 'model_registry', x: 12, y: 10, w: 12, h: 6 },
  { i: 'active_sessions', x: 12, y: 16, w: 12, h: 5 },
  { i: 'ssd_ram', x: 0, y: 21, w: 24, h: 7 },
  { i: 'cmd_library', x: 0, y: 28, w: 24, h: 12 },
];

// ---------------------------------------------------------------------------
// Daemon status colours
// ---------------------------------------------------------------------------
const STATUS_STYLES = {
  running: { dot: '#22c55e', text: '#86efac', label: 'ONLINE',   bg: 'rgba(34,197,94,0.12)',   border: 'rgba(34,197,94,0.35)' },
  stopped: { dot: '#ef4444', text: '#fca5a5', label: 'OFFLINE',  bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.35)' },
  loading: { dot: '#f59e0b', text: '#fde047', label: 'CHECKING', bg: 'rgba(245,158,11,0.14)',  border: 'rgba(245,158,11,0.35)' },
};

// Friendly display names for each daemon key
const DAEMON_LABELS = {
  infinite_learning_loop: { icon: '♾️', name: 'Infinite Learning Loop', desc: 'Autonomous heuristic deduction & transcript synthesis daemon' },
  trainer_daemon: { icon: '📼', name: 'Trainer Daemon',  desc: 'Tails agent transcripts → structured JSONL logs' },
  memory_daemon:  { icon: '🧠', name: 'Memory Daemon',   desc: 'Vectorizes session history → ChromaDB embeddings' },
  chroma_daemon:  { icon: '🗄️', name: 'ChromaDB Server', desc: 'Serves Stehouwer Vector Memory on port 8001' },
};

function DaemonSupervisor({ backendUrl }) {
  const [daemons, setDaemons]       = useState({});
  const [polling, setPolling]       = useState(true);
  const [restarting, setRestarting] = useState({});
  const [lastFetch, setLastFetch]   = useState(null);
  const [fetchError, setFetchError] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/health`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDaemons(data.daemons || {});
      setLastFetch(new Date());
      setFetchError(null);
    } catch (err) {
      setFetchError(err.message);
    }
  }, [backendUrl]);

  // Poll every 5 seconds when polling is enabled
  useEffect(() => {
    fetchStatus();
    if (!polling) return;
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, [fetchStatus, polling]);

  const handleRestart = async (name) => {
    setRestarting(prev => ({ ...prev, [name]: true }));
    try {
      const res = await fetch(`${backendUrl}/api/daemons/${name}/restart`, {
        method: 'POST',
        signal: AbortSignal.timeout(10000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Give the backend a moment then re-poll
      setTimeout(fetchStatus, 1500);
    } catch (err) {
      alert(`Restart failed for ${name}: ${err.message}`);
    } finally {
      setRestarting(prev => ({ ...prev, [name]: false }));
    }
  };

  const daemonEntries = Object.entries(daemons);

  return (
    <div className="daemon-panel">
      {/* Panel header */}
      <div className="daemon-header drag-handle cursor-move">
        <div>
          <h3 className="daemon-title">
            🛰️ DAEMON SUPERVISOR
          </h3>
          <p className="daemon-subtitle">
            Live process health — auto-refreshes every 5s
            {lastFetch && ` · last sync ${lastFetch.toLocaleTimeString()}`}
          </p>
        </div>
        <div className="daemon-actions">
          {fetchError && (
            <span className="daemon-error">
              ⚠ {fetchError}
            </span>
          )}
          <button
            onClick={() => setPolling(p => !p)}
            className={`daemon-btn-pause ${polling ? 'active' : 'inactive'}`}
          >
            {polling ? '⏸ Pause' : '▶ Resume'}
          </button>
          <button
            onClick={fetchStatus}
            className="daemon-btn-refresh"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Python Memory Bank + Infinite Learning Loop HUD */}
      <MemoryBankSupervisor backendUrl={backendUrl} />

      {/* Daemon rows */}
      {daemonEntries.length === 0 ? (
        <div className="daemon-loading">
          {fetchError ? 'Cannot reach backend — start AI_BS_Backend.py first.' : 'Loading daemon status…'}
        </div>
      ) : (
        <div className="daemon-list">
          {daemonEntries.map(([name, info]) => {
            const state  = info.running ? 'running' : 'stopped';
            const style  = STATUS_STYLES[state];
            const meta   = DAEMON_LABELS[name] ?? { icon: '⚙️', name, desc: '' };
            const isRestarting = restarting[name];

            return (
              <div key={name} className="daemon-row" style={{
                background: style.bg,
                border: `1px solid ${style.border}`
              }}>
                {/* Left: icon + name + desc */}
                <div className="daemon-row-left">
                  <span className="daemon-icon">{meta.icon}</span>
                  <div style={{ minWidth: 0 }}>
                    <div className="daemon-name">{meta.name}</div>
                    <div className="daemon-desc">{meta.desc}</div>
                  </div>
                </div>

                {/* Right: status badge + PID + restart button */}
                <div className="daemon-row-right">
                  {info.pid && (
                    <span className="daemon-pid">PID {info.pid}</span>
                  )}
                  {info.restart_count > 0 && (
                    <span className="daemon-restarts" title="Auto-restart count">
                      ↺ {info.restart_count}
                    </span>
                  )}
                  <span className="daemon-status-badge" style={{
                    color: style.text || style.dot,
                    border: `1px solid ${style.border}`,
                    background: style.bg,
                  }}>
                    <span className="daemon-dot" style={{
                      background: style.dot,
                      boxShadow: info.running ? `0 0 6px ${style.dot}` : 'none',
                      animation: info.running ? 'pulse-dot 2s infinite' : 'none',
                    }} />
                    {style.label}
                  </span>
                  <button
                    onClick={() => handleRestart(name)}
                    disabled={isRestarting}
                    title={`Restart ${meta.name}`}
                    className={`daemon-btn-restart ${isRestarting ? 'restarting' : 'idle'}`}
                  >
                    {isRestarting ? '…' : '⟳ Restart'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const ORCHESTRATOR_COMMANDS = [
  {
    title: '🧠 Full System Audit',
    description: 'Run a comprehensive audit across all subsystems — code quality, telemetry, agent logs, and memory health.',
    prompt: 'Perform a full system audit: check all Python modules for syntax errors, review the telemetry checkpoint database for anomalies, summarize agent transcript logs, and report findings.',
  },
  {
    title: '📦 Auto-Package Project',
    description: 'Bundle the current workspace into a distributable archive with dependencies.',
    prompt: 'Package the AI-BS Matrix project: freeze Python dependencies to requirements.txt, run npm build in the frontend, and create a zip archive of the distributable files.',
  },
  {
    title: '🌱 Vertical Farm Optimizer',
    description: 'Analyze Noco telemetry data and generate optimization recommendations for the aeroponic system.',
    prompt: 'Analyze the Noco telemetry data from the last session. Identify CO2, temperature, and MFC output trends. Recommend parameter adjustments to optimize yield.',
  },
  {
    title: '🎵 Audio Production Assistant',
    description: 'Generate a structured audio production workflow for a new track.',
    prompt: 'Create a detailed audio production workflow for an electronic track: BPM selection, key and scale, layering strategy, mix structure, and mastering checklist.',
  },
  {
    title: '🐛 Codebase Bug Sweep',
    description: 'Scan all Python files for common bugs, anti-patterns, and security issues.',
    prompt: 'Scan all Python files in the project for: syntax errors, undefined variable references, insecure subprocess calls, hardcoded secrets, and missing error handling. Report by file.',
  },
  {
    title: '📈 Lead Generation Strategy',
    description: 'Generate a West Michigan B2B lead acquisition strategy using the heuristics engine.',
    prompt: 'Generate a 30-day B2B lead acquisition strategy targeting West Michigan small businesses. Focus on: industries with weak digital presence, outreach templates, follow-up cadence, and value propositions.',
  },
];

export default function CommandCenterTab({ 
  backendUrl: propBackendUrl,
  workspaceMode = 'simple',
  onToggleWorkspaceMode,
  onNavigateTab,
  onOpenGuide,
  onStartTour,
  currentUser
}) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const setChatMessages = useAppStore(state => state.setChatMessages);
  const setFooterInput = useAppStore(state => state.setFooterInput);
  const activeAgents = useAppStore(state => state.activeAgents);
  const setActiveAgents = useAppStore(state => state.setActiveAgents);
  const telegramToken = useAppStore(state => state.telegramToken);
  const setTelegramToken = useAppStore(state => state.setTelegramToken);
  const safetySkipPermissions = useAppStore(state => state.safetySkipPermissions);
  const setSafetySkipPermissions = useAppStore(state => state.setSafetySkipPermissions);
  const customLoopTime = useAppStore(state => state.customLoopTime);
  const setCustomLoopTime = useAppStore(state => state.setCustomLoopTime);
  const customLoopTask = useAppStore(state => state.customLoopTask);
  const setCustomLoopTask = useAppStore(state => state.setCustomLoopTask);
  const pullModelInput = useAppStore(state => state.pullModelInput);
  const setPullModelInput = useAppStore(state => state.setPullModelInput);
  const pullingStatus = useAppStore(state => state.pullingStatus);
  const setPullingStatus = useAppStore(state => state.setPullingStatus);
  const ssdRamPath = useAppStore(state => state.ssdRamPath);
  const setSsdRamPath = useAppStore(state => state.setSsdRamPath);
  const ssdRamSize = useAppStore(state => state.ssdRamSize);
  const setSsdRamSize = useAppStore(state => state.setSsdRamSize);
  const ssdRamCount = useAppStore(state => state.ssdRamCount);
  const setSsdRamCount = useAppStore(state => state.setSsdRamCount);
  const isSsdLoading = useAppStore(state => state.isSsdLoading);
  const setIsSsdLoading = useAppStore(state => state.setIsSsdLoading);

  // Prefer the explicit prop (passed from App.jsx); fall back to context value
  const backendUrl = propBackendUrl || BACKEND_URL;

  const [localSsdPath, setLocalSsdPath] = useState('');

  // If in Simple Mode, render the clean visual portal launchpad
  if (workspaceMode === 'simple') {
    return (
      <SimpleDashboardPortal 
        onNavigateTab={onNavigateTab}
        onOpenGuide={onOpenGuide}
        onStartTour={onStartTour}
        onSwitchToProMode={onToggleWorkspaceMode}
        currentUser={currentUser}
      />
    );
  }

  const handleLaunchAgent = async (agentType, extraArgs = '') => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/agents/launch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: agentType, args: extraArgs }),
      });
      const data = await res.json();
      if (data.pid) {
        setActiveAgents(prev => [...prev.filter(a => a.agent !== agentType), { agent: agentType, pid: data.pid, is_running: true }]);
      }
    } catch (err) {
      alert(`Failed to launch agent: ${err.message}`);
    }
  };

  const handleKillAgent = async (agentType) => {
    try {
      await fetch(`${BACKEND_URL}/api/agents/kill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: agentType }),
      });
      setActiveAgents(prev => prev.map(a => a.agent === agentType ? { ...a, is_running: false } : a));
    } catch (err) {
      alert(`Failed to kill agent: ${err.message}`);
    }
  };

  const handlePullModel = async () => {
    const model = pullModelInput.trim();
    if (!model) return;
    setPullingStatus(prev => ({ ...prev, [model]: { status: 'Downloading', progress: 0, log: 'Connecting...' } }));
    try {
      const res = await fetch(`${BACKEND_URL}/api/models/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      const data = await res.json();
      setPullingStatus(prev => ({ ...prev, [model]: { status: data.status || 'Complete', progress: 100, log: data.message || 'Done.' } }));
      setTimeout(() => setPullingStatus(prev => { const n = { ...prev }; delete n[model]; return n; }), 5000);
    } catch (err) {
      setPullingStatus(prev => ({ ...prev, [model]: { status: 'Error', progress: 0, log: err.message } }));
    }
    setPullModelInput('');
  };

  const updateSsdSettings = async (path) => {
    setIsSsdLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/ssd-ram/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      const data = await res.json();
      setSsdRamPath(data.path || path);
      setSsdRamSize(data.size_bytes || 0);
      setSsdRamCount(data.turn_count || 0);
    } catch (err) {
      alert(`SSD RAM config failed: ${err.message}`);
    } finally {
      setIsSsdLoading(false);
    }
  };

  const wipeSsdRam = async () => {
    if (!confirm('Wipe all SSD RAM cache? This cannot be undone.')) return;
    setIsSsdLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/ssd-ram/wipe`, { method: 'POST' });
      setSsdRamSize(0);
      setSsdRamCount(0);
    } catch (err) {
      alert(`Wipe failed: ${err.message}`);
    } finally {
      setIsSsdLoading(false);
    }
  };

  return (
    <div className="cc-container" style={{ display: 'block', padding: '0' }}>
      <DraggableGridWorkspace tabKey="command-center" defaultLayout={DEFAULT_LAYOUT}>
        
        {/* HEADER WIDGET */}
        <div key="header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }} className="drag-handle cursor-move">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ background: '#7c3aed22', color: '#c084fc', border: '1px solid #7c3aed', padding: '2px 8px', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 'bold' }}>
                ⚡ PRO COCKPIT MODE
              </span>
              <h2 className="cc-header-title" style={{ margin: 0 }}>Orchestrator Command Library & Agentic Manager</h2>
            </div>
            <p className="cc-header-desc" style={{ margin: 0 }}>
              Manage background agent daemons, pull HuggingFace/Ollama models, and execute pre-engineered agentic workflows.
            </p>
          </div>
          {onToggleWorkspaceMode && (
            <button
              onClick={onToggleWorkspaceMode}
              style={{
                background: '#1e293b',
                color: '#38bdf8',
                border: '1px solid #38bdf8',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '700',
                fontSize: '0.8rem'
              }}
            >
              ✨ Switch to Simple Mode
            </button>
          )}
        </div>

        {/* DAEMON SUPERVISOR WIDGET */}
        <div key="daemon_supervisor" style={{ height: '100%' }}>
          <DaemonSupervisor backendUrl={backendUrl} />
        </div>

        {/* AGENT LAUNCHER WIDGET */}
        <div key="agent_launcher" className="agent-launcher-panel glass-panel" style={{ height: '100%', overflowY: 'auto' }}>
          <h3 className="agent-launcher-title drag-handle cursor-move">⚡ Local Agent Launcher</h3>

          <div className="launcher-section">
            <h4 className="launcher-h4">VS Code IDE Synchronization</h4>
            <p className="launcher-p">Expose local models to VS Code Copilot Chat backend for real-time coding alignment.</p>
            <button onClick={() => handleLaunchAgent('vscode')} className="btn-blue">
              Launch VS Code Sync
            </button>
          </div>

          <div className="launcher-section">
            <h4 className="launcher-h4">Autonomous Background Loop</h4>
            <p className="launcher-p">Launch a background instance to recursively review code or logs.</p>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
              <select
                id="autonomous-loop-interval"
                aria-label="Autonomous loop execution interval"
                value={customLoopTime}
                onChange={(e) => setCustomLoopTime(e.target.value)}
                className="input-dark"
              >
                <option value="15m">Every 15m</option>
                <option value="30m">Every 30m</option>
                <option value="1h">Every 1h</option>
                <option value="4h">Every 4h</option>
              </select>
              <input
                type="text"
                aria-label="Autonomous loop task description"
                value={customLoopTask}
                onChange={(e) => setCustomLoopTask(e.target.value)}
                placeholder="Task description..."
                className="input-dark"
                style={{ flexGrow: 1 }}
              />
            </div>
            <button onClick={() => handleLaunchAgent('claude', `/loop ${customLoopTime} ${customLoopTask}`)} className="btn-purple">
              Start Autonomous Loop
            </button>
          </div>

          <div className="launcher-section">
            <h4 className="launcher-h4">Remote Telegram Bot Bridge</h4>
            <p className="launcher-p">Bind Claude Code agent to Telegram for remote mobile control.</p>
            <input
              type="password"
              aria-label="Telegram Bot Token"
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
              placeholder="Telegram Bot Token..."
              className="input-dark"
              style={{ width: '100%', marginBottom: '12px' }}
            />
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
              <input type="checkbox" id="safety-toggle" checked={safetySkipPermissions} onChange={(e) => setSafetySkipPermissions(e.target.checked)} style={{ marginRight: '8px' }} />
              <label htmlFor="safety-toggle" style={{ fontSize: '0.8rem', color: '#ccc', cursor: 'pointer' }}>Dangerously Skip Permissions</label>
            </div>
            {safetySkipPermissions && (
              <div style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', padding: '10px', borderRadius: '6px', fontSize: '0.75rem', marginBottom: '16px', border: '1px solid rgba(239,68,68,0.2)' }}>
                ⚠️ <strong>WARNING:</strong> This bypasses remote authorization. Keep disabled for safety.
              </div>
            )}
            <button
              onClick={() => {
                if (!telegramToken.trim()) return alert('Enter your Telegram Bot Token first.');
                handleLaunchAgent('claude', `--channels plugin:telegram@claude-plugins-official --token ${telegramToken} ${safetySkipPermissions ? '--dangerously-skip-permissions' : ''}`);
              }}
              className="btn-green"
            >Launch Telegram Bridge</button>
          </div>
        </div>

        {/* MODEL REGISTRY WIDGET */}
        <div key="model_registry" className="registry-panel glass-panel" style={{ height: '100%', overflowY: 'auto' }}>
          <h3 className="registry-title drag-handle cursor-move">📥 Model Registry & HF Ingestion</h3>
          <p className="launcher-p">Pull GGUF models from HuggingFace or ingest Ollama models to maximize RTX 4090 VRAM.</p>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <input
              type="text"
              aria-label="Model name or HuggingFace path"
              value={pullModelInput}
              onChange={(e) => setPullModelInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handlePullModel()}
              placeholder="e.g. gemma4:12b-it-qat or hf.co/QuantFactory/..."
              className="input-dark"
              style={{ flexGrow: 1 }}
            />
            <button onClick={handlePullModel} className="btn-blue">Pull</button>
          </div>
          {Object.keys(pullingStatus).length > 0 && (
            <div>
              {Object.entries(pullingStatus).map(([model, info]) => (
                <div key={model} style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#fff', marginBottom: '6px' }}>
                    <span style={{ fontFamily: 'monospace' }}>{model}</span>
                    <span style={{ color: '#38bdf8' }}>{info.status} ({info.progress}%)</span>
                  </div>
                  <div className="pull-progress-bar">
                    <div className="pull-progress-fill" style={{ width: `${info.progress}%` }} />
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '4px', fontFamily: 'monospace' }}>{info.log}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ACTIVE SESSIONS WIDGET */}
        <div key="active_sessions" className="registry-panel glass-panel" style={{ height: '100%', overflowY: 'auto' }}>
          <h3 className="active-sessions-title drag-handle cursor-move">🤖 Active Background Sessions</h3>
          {activeAgents.filter(a => a.is_running).length === 0 ? (
            <div className="session-empty">No active background agent sessions.</div>
          ) : (
            <DroppableContainer id="active_sessions_list" items={activeAgents.filter(a => a.is_running).map(a => a.agent)}>
              {activeAgents.filter(a => a.is_running).map(agent => (
                <DraggableItem key={agent.agent} id={agent.agent}>
                  <div className="session-row">
                    <div>
                      <div className="session-name">{agent.agent.toUpperCase()} Sync Daemon</div>
                      <div className="session-meta">PID: {agent.pid} | ACTIVE</div>
                    </div>
                    <button onClick={() => handleKillAgent(agent.agent)} className="btn-red-outline">
                      Terminate
                    </button>
                  </div>
                </DraggableItem>
              ))}
            </DroppableContainer>
          )}
        </div>

        {/* SSD VIRTUAL RAM WIDGET */}
        <div key="ssd_ram" className="ssd-panel glass-panel" style={{ height: '100%', overflowY: 'auto' }}>
          <h3 className="ssd-title drag-handle cursor-move">💾 SSD Virtual RAM — Context Memory</h3>
          <p className="launcher-p" style={{ marginBottom: '24px' }}>Long-term conversation turns offloaded to local SSD and indexed into the vector database.</p>
          <div className="ssd-grid">
            {[
              { label: 'Storage Path', value: ssdRamPath || '—', mono: true },
              { label: 'Cache Size', value: `${(ssdRamSize / 1024).toFixed(1)} KB` },
              { label: 'Archived Turns', value: `${ssdRamCount} turn pairs` },
              { label: 'Tokenizer', value: 'Stehouwer LLM v2' },
            ].map((item, i) => (
              <div key={i} className="ssd-item">
                <div className="ssd-label">{item.label}</div>
                <div className="ssd-val" style={{ fontFamily: item.mono ? 'monospace' : 'inherit' }}>{item.value}</div>
              </div>
            ))}
          </div>
          <div className="ssd-actions">
            <input
              type="text"
              aria-label="Local SSD RAM cache path"
              value={localSsdPath}
              onChange={(e) => setLocalSsdPath(e.target.value)}
              placeholder={ssdRamPath || 'Enter SSD path (e.g. D:\\AI_RAM_Cache)...'}
              className="input-dark"
              style={{ flexGrow: 1, fontFamily: 'monospace', minWidth: '240px' }}
            />
            <button onClick={() => { const p = localSsdPath.trim(); if (!p) return alert('Enter a valid path first.'); updateSsdSettings(p); setLocalSsdPath(''); }} disabled={isSsdLoading} className="btn-purple-save" style={{ opacity: isSsdLoading ? 0.6 : 1, cursor: isSsdLoading ? 'not-allowed' : 'pointer' }}>
              {isSsdLoading ? 'Saving...' : '💾 Set Path'}
            </button>
            <button onClick={wipeSsdRam} disabled={isSsdLoading} className="btn-red-wipe" style={{ opacity: isSsdLoading ? 0.6 : 1, cursor: isSsdLoading ? 'not-allowed' : 'pointer' }}>
              🗑️ Wipe Cache
            </button>
          </div>
        </div>

        {/* ORCHESTRATOR COMMAND LIBRARY WIDGET */}
        <div key="cmd_library" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <h3 className="cmd-lib-title drag-handle cursor-move" style={{ marginTop: 0 }}>🧠 Orchestrator Command Library</h3>
          <div className="cmd-grid" style={{ flexGrow: 1, overflowY: 'auto' }}>
            <DroppableContainer id="cmd_library_list" items={ORCHESTRATOR_COMMANDS.map(cmd => cmd.title)}>
              {ORCHESTRATOR_COMMANDS.map((cmd, idx) => (
                <DraggableItem key={cmd.title} id={cmd.title} className="cmd-card-draggable-wrapper">
                  <div className="cmd-card glass-panel" style={{ height: 'fit-content' }}>
                    <h4 className="cmd-title">{cmd.title}</h4>
                    <p className="cmd-desc">{cmd.description}</p>
                    <div className="cmd-prompt">
                      {cmd.prompt}
                    </div>
                    <button
                      onClick={() => {
                        setChatMessages(prev => [...prev, { role: 'user', content: cmd.prompt }]);
                        setFooterInput('');
                      }}
                      className="btn-green"
                      style={{ width: '100%', padding: '12px', borderRadius: '8px' }}
                    >
                      Send to AI Chat ➤
                    </button>
                  </div>
                </DraggableItem>
              ))}
            </DroppableContainer>
          </div>
        </div>

      </DraggableGridWorkspace>
    </div>
  );
}
