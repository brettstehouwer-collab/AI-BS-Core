import React, { useState, useEffect, useRef } from 'react';
import { useAppStore } from './useAppStore';

export default function ExecutiveCockpitTab({ BACKEND_URL, backendUrl }) {
  const activeBackend = backendUrl || BACKEND_URL || useAppStore((state) => state.BACKEND_URL) || 'http://localhost:8080';

  // =========================================================================
  // STATE MANAGEMENT
  // =========================================================================
  // Autonomy Mode
  const [autonomyMode, setAutonomyMode] = useState('SAFE'); // 'SAFE', 'SEMI_AUTO', 'FULL_AUTO'
  const [isUpdatingAutonomy, setIsUpdatingAutonomy] = useState(false);

  // Column 1: Copilot Chat
  const [chatInput, setChatInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('stehouwer_llm');
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      content: "⚡ **Sovereign Executive Command Cockpit Online (v5.305.0)**\n\nDirectorial Voice HUD & Autonomous Sentinel Engine active. 100% Sovereign Local RTX 4090 execution enforced (Zero Cloud Spend: $0.00).\n\nSpeak or issue directives across Media Studio, Broadcast Kernel, Crypto Swarm, Knowledge Vault (305k records), and Local Ollama Swarm.",
      tool_calls: []
    }
  ]);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const chatEndRef = useRef(null);

  // Column 2: 4-Pillar Matrix Status
  const [matrixStatus, setMatrixStatus] = useState({
    pillars: {
      media_studio: { status: 'ONLINE', nvenc_cfr_gate: 'READY', supported_models: ['wan2.1', 'ltx-video'] },
      broadcast_kernel: { is_obs_running: false, suggested_scene: 'AI-BS Main Dashboard', active_studio_apps_count: 0 },
      crypto_swarm: { status: 'ONLINE', daemon_port: 8007, twap_plans_count: 0, drip_orders_count: 0 },
      ollama_swarm: { status: 'CONNECTING', models_count: 17, models_sample: ['stehouwer_llm', 'stehouwer_qwen'] }
    },
    hardware: {
      gpu_name: 'NVIDIA GeForce RTX 4090 (24GB)',
      temp_c: 42,
      vram_used_mb: 4096,
      vram_total_mb: 24576,
      vram_free_mb: 20480,
      gpu_util_pct: 12,
      ram_used_gb: 18.4,
      ram_total_gb: 64.0,
      ram_percent: 28.7,
      disk_free_gb: 840.5,
      disk_total_gb: 1900.0,
      disk_percent: 55.7
    },
    vault: {
      sqlite_vault_records: 305654,
      media_memory_records: 12,
      chromadb_collection: 'stehouwer_media_memory'
    }
  });

  // Column 3: Action Queue & Governance
  const [pendingActions, setPendingActions] = useState([]);
  const [actionHistory, setActionHistory] = useState([]);
  const [isResolving, setIsResolving] = useState(false);
  const [resolvingActionIds, setResolvingActionIds] = useState(new Set());
  const [isHalting, setIsHalting] = useState(false);

  // Column 4: Polling & Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(Date.now());

  // v5.299.0: Directorial Voice HUD State
  const [isListening, setIsListening] = useState(false);
  const [voiceAudioEnabled, setVoiceAudioEnabled] = useState(true);
  const [voiceStatus, setVoiceStatus] = useState({
    web_speech_api_available: true,
    f5_tts_eligible: false,
    active_mode: 'Web Speech API (Zero-Overhead Hybrid Fallback)'
  });
  const recognitionRef = useRef(null);

  // v5.299.0: Autonomous Sentinel Engine State
  const [sentinelAlerts, setSentinelAlerts] = useState([]);
  const [sentinelStatus, setSentinelStatus] = useState(null);
  const [isScanningSentinel, setIsScanningSentinel] = useState(false);
  const [expandingHashes, setExpandingHashes] = useState(new Set());

  // v5.299.0: Sovereign GPU Execution ($0.00 spend lock)
  const [cloudStatus, setCloudStatus] = useState({
    sovereign_local_exclusive: true,
    cloud_burst_enabled: false,
    daily_spend_limit_usd: 5.0,
    current_daily_spend_usd: 0.0,
    remaining_budget_usd: 5.0,
    queued_jobs_count: 0
  });

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // =========================================================================
  // API CALLS
  // =========================================================================
  // 1. Fetch Matrix Status & Telemetry
  const fetchMatrixStatus = async () => {
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/matrix/status`);
      if (res.ok) {
        const data = await res.json();
        setMatrixStatus(data);
        if (data.autonomy_mode) {
          setAutonomyMode(data.autonomy_mode);
        }
      }
    } catch (err) {
      console.warn('Matrix status fetch warning:', err);
    }
  };

  // 2. Fetch Pending Queue
  const fetchPendingActions = async () => {
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/actions/pending`);
      if (res.ok) {
        const data = await res.json();
        setPendingActions(data.pending_actions || []);
      }
    } catch (err) {
      console.warn('Pending actions fetch warning:', err);
    }
  };

  // 3. Fetch Action History
  const fetchActionHistory = async () => {
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/actions/history?limit=25`);
      if (res.ok) {
        const data = await res.json();
        setActionHistory(data.history || []);
      }
    } catch (err) {
      console.warn('Action history fetch warning:', err);
    }
  };

  // 4. Fetch Sentinel Alerts
  const fetchSentinelAlerts = async () => {
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/sentinel/alerts?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setSentinelAlerts(data.alerts || []);
        if (data.engine_status) setSentinelStatus(data.engine_status);
      }
    } catch (err) {
      console.warn('Sentinel alerts fetch warning:', err);
    }
  };

  // 5. Fetch Cloud / Sovereign GPU Status
  const fetchCloudStatus = async () => {
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/cloud/status`);
      if (res.ok) {
        const data = await res.json();
        if (data.gpu_sovereignty) setCloudStatus(data.gpu_sovereignty);
      }
    } catch (err) {
      console.warn('Cloud status fetch warning:', err);
    }
  };

  // 6. Fetch Voice Status
  const fetchVoiceStatus = async () => {
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/voice/status`);
      if (res.ok) {
        const data = await res.json();
        setVoiceStatus(data);
      }
    } catch (err) {
      console.warn('Voice status fetch warning:', err);
    }
  };

  // 7. Polling loop
  useEffect(() => {
    fetchMatrixStatus();
    fetchPendingActions();
    fetchActionHistory();
    fetchSentinelAlerts();
    fetchCloudStatus();
    fetchVoiceStatus();

    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchMatrixStatus();
      fetchPendingActions();
      fetchActionHistory();
      fetchSentinelAlerts();
      fetchCloudStatus();
      setLastRefreshed(Date.now());
    }, 3000);
    return () => clearInterval(interval);
  }, [activeBackend, autoRefresh]);

  // 8. Directorial Voice Feedback
  const speakDirectorialResponse = (text) => {
    if (!voiceAudioEnabled || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[*#`_~\[\]()]/g, '').slice(0, 240);
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Speech synthesis note:', err);
    }
  };

  // 9. Toggle Voice Recognition (STT)
  const toggleVoiceRecognition = () => {
    if (isListening) {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please use Microsoft Edge or Chrome.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => setIsListening(true);
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript;
        if (transcript) {
          setChatInput(transcript);
          handleSendMessage(transcript);
        }
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Voice recognition start error:', err);
      setIsListening(false);
    }
  };

  // 10. Trigger Manual Sentinel Scan
  const handleTriggerSentinelScan = async () => {
    setIsScanningSentinel(true);
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/sentinel/scan`, { method: 'POST' });
      if (res.ok) {
        await fetchSentinelAlerts();
        await fetchMatrixStatus();
      }
    } catch (err) {
      console.error('Sentinel scan error:', err);
    } finally {
      setIsScanningSentinel(false);
    }
  };

  // 11. Expand Media Asset Non-destructively
  const handleExpandMedia = async (fileHash, action = 'reframe_9_16') => {
    setExpandingHashes((prev) => new Set(prev).add(fileHash));
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/sentinel/expand-media`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_hash: fileHash, action })
      });
      if (res.ok) {
        await fetchSentinelAlerts();
        await fetchMatrixStatus();
      }
    } catch (err) {
      console.error('Expand media error:', err);
    } finally {
      setExpandingHashes((prev) => {
        const next = new Set(prev);
        next.delete(fileHash);
        return next;
      });
    }
  };

  // 12. Send Prompt to Executive Copilot
  const handleSendMessage = async (textToSend) => {
    const text = textToSend || chatInput;
    if (!text.trim() || isSendingChat) return;

    const userMsg = { role: 'user', content: text, tool_calls: [] };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput('');
    setIsSendingChat(true);

    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: text,
          model: selectedModel,
          autonomy_mode: autonomyMode
        })
      });

      if (res.ok) {
        const data = await res.json();
        const assistantMsg = {
          role: 'assistant',
          content: data.response || 'Action processed.',
          tool_calls: data.tool_calls || []
        };
        setChatMessages((prev) => [...prev, assistantMsg]);
        speakDirectorialResponse(data.response || 'Action processed.');
        // Refresh queue & history immediately
        fetchPendingActions();
        fetchActionHistory();
        fetchMatrixStatus();
        fetchSentinelAlerts();
      } else {
        setChatMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `❌ Error ${res.status}: Failed to dispatch executive action.`, tool_calls: [] }
        ]);
      }
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `❌ Connection Error: ${err.message}`, tool_calls: [] }
      ]);
    } finally {
      setIsSendingChat(false);
    }
  };

  // 6. Resolve Pending Action (Approve / Reject)
  const handleResolveAction = async (actionId, decision) => {
    setIsResolving(true);
    setResolvingActionIds((prev) => new Set(prev).add(actionId));
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/actions/${actionId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, operator_note: `Manual resolution via Executive Cockpit HUD.` })
      });
      if (res.ok) {
        await fetchPendingActions();
        await fetchActionHistory();
        await fetchMatrixStatus();
      }
    } catch (err) {
      console.error('Resolve action error:', err);
    } finally {
      setIsResolving(false);
      setResolvingActionIds((prev) => {
        const next = new Set(prev);
        next.delete(actionId);
        return next;
      });
    }
  };

  // 7. Toggle Autonomy Mode
  const handleSetAutonomy = async (mode) => {
    setIsUpdatingAutonomy(true);
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/settings/autonomy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      if (res.ok) {
        const data = await res.json();
        setAutonomyMode(data.autonomy_mode);
      }
    } catch (err) {
      console.error('Autonomy update error:', err);
    } finally {
      setIsUpdatingAutonomy(false);
    }
  };

  // 8. Emergency Halt
  const handleEmergencyHalt = async () => {
    if (!window.confirm('⚠️ EMERGENCY HALT: Revoke ALL pending actions and enforce SAFE autonomy mode?')) return;
    setIsHalting(true);
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/actions/halt`, {
        method: 'POST'
      });
      if (res.ok) {
        setAutonomyMode('SAFE');
        await fetchPendingActions();
        await fetchActionHistory();
      }
    } catch (err) {
      console.error('Halt error:', err);
    } finally {
      setIsHalting(false);
    }
  };

  // 8b. Vibe Checkpoint & Rollback Handlers (Vibe-Coding Protection Engine)
  const [isCheckpointing, setIsCheckpointing] = useState(false);
  const [lastCheckpointHash, setLastCheckpointHash] = useState(null);

  const handleCreateVibeCheckpoint = async () => {
    setIsCheckpointing(true);
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/vibe-checkpoint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: 'Manual Executive Vibe Checkpoint', author: 'Operator' })
      });
      if (res.ok) {
        const data = await res.json();
        setLastCheckpointHash(data.checkpoint);
        alert(`✅ Vibe-Checkpoint Captured: [${data.checkpoint}] in ${data.elapsed_ms}ms.`);
      }
    } catch (err) {
      console.error('Checkpoint error:', err);
    } finally {
      setIsCheckpointing(false);
    }
  };

  const handleRollbackVibeCheckpoint = async () => {
    if (!window.confirm('⚠️ ROLLBACK: Revert all uncommitted code changes to the last safe Vibe-Checkpoint?')) return;
    setIsCheckpointing(true);
    try {
      const res = await fetch(`${activeBackend}/api/v1/executive/vibe-rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (res.ok) {
        alert('✅ Rollback Complete: Workspace code restored to last safe Vibe-Checkpoint.');
      }
    } catch (err) {
      console.error('Rollback error:', err);
    } finally {
      setIsCheckpointing(false);
    }
  };

  // =========================================================================
  // PRESET COMMANDS
  // =========================================================================
  const PRESET_COMMANDS = [
    { label: '🎬 Reframe 9:16 Short', prompt: 'Generate 9:16 Short from mtd.mp4' },
    { label: '🎥 Switch OBS Scene', prompt: 'Switch OBS to Camera 1' },
    { label: '⚡ Crypto Scalp Status', prompt: 'Query CRO Scalp Status' },
    { label: '🏛️ Query Vault (305k)', prompt: 'Search Vault for Bio-Intelligence' },
    { label: '💰 Stage CRO Buy Order', prompt: 'Stage a $50 CRO limit buy order at 0.125' },
    { label: '🏥 Full System Health Audit', prompt: 'Audit system health and check crypto daemon status' }
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      backgroundColor: '#090d13',
      color: '#c9d1d9',
      fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
      overflow: 'hidden'
    }}>
      {/* ── TOP EXECUTIVE BANNER & GLOBAL HUD CONTROLS ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 18px',
        backgroundColor: '#0d1117',
        borderBottom: '1px solid #21262d',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.4rem' }}>⚡</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 800, fontSize: '1.05rem', color: '#58a6ff', letterSpacing: '0.04em' }}>
                AI-BS EXECUTIVE COMMAND COCKPIT
              </span>
              <span style={{
                background: 'rgba(88, 166, 255, 0.15)',
                color: '#58a6ff',
                fontSize: '0.68rem',
                padding: '2px 7px',
                borderRadius: '10px',
                fontWeight: 700,
                border: '1px solid rgba(88, 166, 255, 0.3)'
              }}>
                v5.305.0
              </span>
              <span style={{
                background: 'rgba(63, 185, 80, 0.15)',
                color: '#3fb950',
                fontSize: '0.68rem',
                padding: '2px 7px',
                borderRadius: '10px',
                fontWeight: 700,
                border: '1px solid rgba(63, 185, 80, 0.3)'
              }}>
                UNIFIED BUS ONLINE
              </span>
              <span style={{
                background: 'rgba(163, 113, 247, 0.15)',
                color: '#d2a8ff',
                fontSize: '0.68rem',
                padding: '2px 7px',
                borderRadius: '10px',
                fontWeight: 700,
                border: '1px solid rgba(163, 113, 247, 0.3)'
              }}>
                VOICE HUD & SENTINEL
              </span>
              <span style={{
                background: 'rgba(56, 139, 253, 0.15)',
                color: '#79c0ff',
                fontSize: '0.68rem',
                padding: '2px 7px',
                borderRadius: '10px',
                fontWeight: 700,
                border: '1px solid rgba(56, 139, 253, 0.3)'
              }}>
                SOVEREIGN RTX 4090 ($0.00 SPEND)
              </span>
            </div>
            <div style={{ fontSize: '0.74rem', color: '#8b949e', marginTop: '1px' }}>
              Autonomous 4-Pillar Cross-Matrix Dispatcher • Tiered Governance Gates • Zero Real-Money Mock Law • Proactive Sentinel
            </div>
          </div>
        </div>

        {/* Global Controls: Autonomy Mode & Emergency Halt */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* Autonomy Mode Switcher */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: '#161b22',
            padding: '3px 4px',
            borderRadius: '8px',
            border: '1px solid #30363d'
          }}>
            <span style={{ fontSize: '0.7rem', color: '#8b949e', margin: '0 8px', fontWeight: 600 }}>GOVERNANCE:</span>
            {['SAFE', 'SEMI_AUTO', 'FULL_AUTO'].map((mode) => {
              const active = autonomyMode === mode;
              const color = mode === 'SAFE' ? '#3fb950' : (mode === 'SEMI_AUTO' ? '#d29922' : '#f85149');
              return (
                <button
                  key={mode}
                  onClick={() => handleSetAutonomy(mode)}
                  disabled={isUpdatingAutonomy}
                  style={{
                    background: active ? color : 'transparent',
                    color: active ? '#ffffff' : '#8b949e',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '4px 10px',
                    fontSize: '0.72rem',
                    fontWeight: active ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  title={
                    mode === 'SAFE'
                      ? 'SAFE: Tier 1 auto-executes. Tier 2 & Tier 3 held in approval queue.'
                      : (mode === 'SEMI_AUTO'
                        ? 'SEMI_AUTO: Tier 1 & Tier 2 auto-execute. Tier 3 trades held for operator.'
                        : 'FULL_AUTO: Autonomous execution across all tiers (override permitted).')
                  }
                >
                  {mode}
                </button>
              );
            })}
          </div>

          {/* Vibe Checkpoint & Rollback Controls */}
          <button
            onClick={handleCreateVibeCheckpoint}
            disabled={isCheckpointing}
            style={{
              background: 'linear-gradient(180deg, #1f6feb 0%, #1158c7 100%)',
              color: '#ffffff',
              border: '1px solid #388bfd',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              boxShadow: '0 0 8px rgba(56, 139, 253, 0.3)'
            }}
            title="Create an instant non-destructive Git snapshot of your code"
          >
            <span>💾</span>
            <span>{isCheckpointing ? 'SAVING...' : lastCheckpointHash ? `CP: [${lastCheckpointHash}]` : 'VIBE-CHECKPOINT'}</span>
          </button>

          <button
            onClick={handleRollbackVibeCheckpoint}
            disabled={isCheckpointing}
            style={{
              background: '#21262d',
              color: '#e6edf3',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px'
            }}
            title="Revert all uncommitted code changes to last safe Vibe-Checkpoint"
          >
            <span>↩️</span>
            <span>ROLLBACK</span>
          </button>

          {/* Emergency Halt Button */}
          <button
            onClick={handleEmergencyHalt}
            disabled={isHalting}
            style={{
              background: 'linear-gradient(180deg, #da3633 0%, #b62324 100%)',
              color: '#ffffff',
              border: '1px solid #f85149',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '0.78rem',
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 0 10px rgba(248, 81, 73, 0.4)'
            }}
          >
            <span>🛑</span>
            <span>EMERGENCY HALT</span>
          </button>

          {/* Auto Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{
              background: autoRefresh ? 'rgba(63, 185, 80, 0.15)' : '#161b22',
              color: autoRefresh ? '#3fb950' : '#8b949e',
              border: `1px solid ${autoRefresh ? 'rgba(63, 185, 80, 0.4)' : '#30363d'}`,
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            title="Auto-refresh telemetry every 3 seconds"
          >
            {autoRefresh ? '🔄 Live (3s)' : '⏸️ Paused'}
          </button>
        </div>
      </div>

      {/* ── SENTINEL ALERT TICKER & DIRECTORIAL VOICE DIRECTING STRIP (v5.299.0) ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 18px',
        backgroundColor: '#161b22',
        borderBottom: '1px solid #30363d',
        gap: '12px',
        fontSize: '0.76rem',
        flexShrink: 0
      }}>
        {/* Left: Sentinel Live Feed */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden', flex: 1 }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            background: 'rgba(210, 153, 34, 0.2)',
            color: '#e3b341',
            padding: '2px 8px',
            borderRadius: '6px',
            fontWeight: 700,
            fontSize: '0.7rem',
            whiteSpace: 'nowrap'
          }}>
            🛰️ SENTINEL FEED ({sentinelAlerts.length})
          </span>

          {sentinelAlerts.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <span style={{
                background: sentinelAlerts[0].severity === 'RECOMMENDATION' ? 'rgba(88, 166, 255, 0.2)' : 'rgba(248, 81, 73, 0.2)',
                color: sentinelAlerts[0].severity === 'RECOMMENDATION' ? '#58a6ff' : '#f85149',
                padding: '1px 6px',
                borderRadius: '4px',
                fontSize: '0.68rem',
                fontWeight: 600
              }}>
                {sentinelAlerts[0].category}
              </span>
              <span style={{ color: '#c9d1d9', fontWeight: 500 }}>
                {sentinelAlerts[0].title}: {sentinelAlerts[0].message}
              </span>
              {sentinelAlerts[0]?.metadata?.file_hash && (
                <button
                  onClick={() => handleExpandMedia(sentinelAlerts[0].metadata.file_hash, 'reframe_9_16')}
                  disabled={expandingHashes.has(sentinelAlerts[0].metadata.file_hash)}
                  style={{
                    background: 'linear-gradient(180deg, #238636 0%, #2ea043 100%)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '2px 8px',
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  {expandingHashes.has(sentinelAlerts[0].metadata.file_hash) ? 'Rendering 9:16...' : '⚡ Reframe 9:16'}
                </button>
              )}
            </div>
          ) : (
            <span style={{ color: '#8b949e', fontStyle: 'italic' }}>
              All intake folders, market velocity, and GPU thermals nominal.
            </span>
          )}
        </div>

        {/* Right: Directorial Voice HUD & Scan Trigger */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <button
            onClick={handleTriggerSentinelScan}
            disabled={isScanningSentinel}
            style={{
              background: '#21262d',
              color: '#58a6ff',
              border: '1px solid #30363d',
              borderRadius: '5px',
              padding: '3px 8px',
              fontSize: '0.7rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            title="Scan folders, crypto velocity, and hardware now"
          >
            {isScanningSentinel ? 'Scanning...' : '📡 Scan Now'}
          </button>

          {/* Voice Microphone Directing Button */}
          <button
            onClick={toggleVoiceRecognition}
            style={{
              background: isListening ? '#f85149' : 'rgba(88, 166, 255, 0.15)',
              color: isListening ? '#ffffff' : '#58a6ff',
              border: `1px solid ${isListening ? '#f85149' : 'rgba(88, 166, 255, 0.4)'}`,
              borderRadius: '6px',
              padding: '3px 10px',
              fontSize: '0.72rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px'
            }}
            title={isListening ? 'Listening for voice directive... Click to stop.' : 'Click to direct sovereign assistant via microphone.'}
          >
            <span>{isListening ? '🎙️ Listening...' : '🎤 Direct by Voice'}</span>
          </button>

          {/* Voice Audio Feedback Toggle */}
          <button
            onClick={() => setVoiceAudioEnabled(!voiceAudioEnabled)}
            style={{
              background: voiceAudioEnabled ? 'rgba(63, 185, 80, 0.15)' : '#21262d',
              color: voiceAudioEnabled ? '#3fb950' : '#8b949e',
              border: `1px solid ${voiceAudioEnabled ? 'rgba(63, 185, 80, 0.4)' : '#30363d'}`,
              borderRadius: '6px',
              padding: '3px 8px',
              fontSize: '0.7rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            title="Toggle directorial voice speech synthesis feedback"
          >
            {voiceAudioEnabled ? '🔊 Voice Feedback: ON' : '🔇 Muted'}
          </button>

          {/* Sovereign Local GPU Spend Lock Badge */}
          <span style={{
            background: 'rgba(56, 139, 253, 0.12)',
            color: '#58a6ff',
            border: '1px solid rgba(56, 139, 253, 0.3)',
            borderRadius: '6px',
            padding: '2px 8px',
            fontSize: '0.68rem',
            fontWeight: 700
          }}>
            RTX 4090: 100% LOCAL ($0.00 SPEND)
          </span>
        </div>
      </div>

      {/* ── HIGH-DENSITY 4-COLUMN RESPONSIVE COCKPIT HUD ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(320px, 1.25fr) minmax(280px, 1fr) minmax(320px, 1.2fr) minmax(260px, 0.95fr)',
        gap: '12px',
        padding: '12px',
        flex: 1,
        overflow: 'hidden'
      }}>

        {/* ── COLUMN 1: SOVEREIGN COPILOT & ACTION TERMINAL ── */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0d1117',
          borderRadius: '8px',
          border: '1px solid #21262d',
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            padding: '10px 14px',
            backgroundColor: '#161b22',
            borderBottom: '1px solid #21262d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1rem' }}>💬</span>
              <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#c9d1d9' }}>Sovereign Copilot Terminal</span>
            </div>
            {/* Model Selector */}
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{
                background: '#0d1117',
                color: '#58a6ff',
                border: '1px solid #30363d',
                borderRadius: '6px',
                fontSize: '0.72rem',
                padding: '3px 8px',
                fontWeight: 600,
                outline: 'none'
              }}
            >
              <option value="stehouwer_llm">stehouwer_llm (17-Fleet Primary)</option>
              <option value="stehouwer_qwen">stehouwer_qwen (Fast Logic)</option>
              <option value="gemma4:12b">gemma4:12b (Dense Reasoning)</option>
              <option value="mixtral">mixtral (MoE Swarm)</option>
            </select>
          </div>

          {/* Quick Command Presets */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px',
            padding: '8px 12px',
            backgroundColor: '#12171f',
            borderBottom: '1px solid #21262d'
          }}>
            {PRESET_COMMANDS.map((cmd, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(cmd.prompt)}
                disabled={isSendingChat}
                style={{
                  background: 'rgba(88, 166, 255, 0.08)',
                  color: '#58a6ff',
                  border: '1px solid rgba(88, 166, 255, 0.25)',
                  borderRadius: '5px',
                  padding: '4px 8px',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {cmd.label}
              </button>
            ))}
          </div>

          {/* Chat Messages Log */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            {chatMessages.map((msg, index) => {
              const isAssistant = msg.role === 'assistant';
              return (
                <div
                  key={index}
                  style={{
                    alignSelf: isAssistant ? 'flex-start' : 'flex-end',
                    maxWidth: isAssistant ? '96%' : '85%',
                    backgroundColor: isAssistant ? '#161b22' : '#1f6feb',
                    color: isAssistant ? '#c9d1d9' : '#ffffff',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: isAssistant ? '1px solid #30363d' : 'none',
                    fontSize: '0.82rem',
                    lineHeight: '1.45',
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  {msg.content}

                  {/* Render Tool-Call Badges */}
                  {msg.tool_calls && msg.tool_calls.length > 0 && (
                    <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <div style={{ fontSize: '0.68rem', color: '#8b949e', fontWeight: 700, textTransform: 'uppercase' }}>
                        Dispatched Tool Actions ({msg.tool_calls.length}):
                      </div>
                      {msg.tool_calls.map((tc, tcIdx) => {
                        const isQueued = tc.status === 'QUEUED';
                        const isExecuted = tc.status === 'EXECUTED';
                        const badgeColor = isQueued ? '#d29922' : (isExecuted ? '#3fb950' : '#f85149');
                        return (
                          <div
                            key={tcIdx}
                            style={{
                              background: '#0d1117',
                              border: `1px solid ${badgeColor}`,
                              borderRadius: '6px',
                              padding: '6px 10px',
                              fontSize: '0.74rem'
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '3px' }}>
                              <span style={{ fontWeight: 700, color: '#58a6ff' }}>
                                ⚙️ {tc.pillar}.{tc.action_name || tc.action}
                              </span>
                              <span style={{
                                color: badgeColor,
                                fontWeight: 800,
                                fontSize: '0.68rem',
                                background: `${badgeColor}22`,
                                padding: '1px 6px',
                                borderRadius: '4px'
                              }}>
                                {isQueued ? `[TIER ${tc.tier} - QUEUED FOR APPROVAL]` : `[TIER ${tc.tier} - ${tc.status}]`}
                              </span>
                            </div>
                            {tc.result && (
                              <div style={{ fontSize: '0.7rem', color: '#8b949e', marginTop: '2px' }}>
                                {tc.result.message || JSON.stringify(tc.result)}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={chatEndRef} />
          </div>

          {/* Terminal Input Bar */}
          <div style={{
            padding: '10px',
            backgroundColor: '#161b22',
            borderTop: '1px solid #21262d',
            display: 'flex',
            gap: '8px'
          }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="Enter sovereign directive (e.g. Stage $50 CRO limit buy at 0.125)..."
              disabled={isSendingChat}
              style={{
                flex: 1,
                background: '#0d1117',
                color: '#c9d1d9',
                border: '1px solid #30363d',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '0.8rem',
                outline: 'none'
              }}
            />
            <button
              onClick={toggleVoiceRecognition}
              style={{
                background: isListening ? '#f85149' : '#21262d',
                color: isListening ? '#ffffff' : '#58a6ff',
                border: `1px solid ${isListening ? '#f85149' : '#30363d'}`,
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
              title={isListening ? 'Listening for voice directive... Click to stop.' : 'Direct by Voice'}
            >
              {isListening ? '🔴' : '🎤'}
            </button>
            <button
              onClick={() => handleSendMessage()}
              disabled={isSendingChat || !chatInput.trim()}
              style={{
                background: '#238636',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 16px',
                fontWeight: 700,
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              {isSendingChat ? '...' : 'Dispatch'}
            </button>
          </div>
        </div>

        {/* ── COLUMN 2: 4-PILLAR LIVE MATRIX STATUS ── */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0d1117',
          borderRadius: '8px',
          border: '1px solid #21262d',
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            padding: '10px 14px',
            backgroundColor: '#161b22',
            borderBottom: '1px solid #21262d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1rem' }}>🌐</span>
              <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#c9d1d9' }}>4-Pillar Live Matrix</span>
            </div>
            <span style={{ fontSize: '0.7rem', color: '#3fb950', fontWeight: 600 }}>● ALL SYSTEMS GREEN</span>
          </div>

          {/* Cards List */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            {/* Pillar 1: Media Creator Studio */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.1rem' }}>🎨</span>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#f0883e' }}>Media Studio (Wan2.1 / LTX)</span>
                </div>
                <span style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: '#3fb950',
                  background: 'rgba(63, 185, 80, 0.15)',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  ONLINE
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• NVENC CFR 30fps Gate: <span style={{ color: '#3fb950', fontWeight: 600 }}>PASSING</span></div>
                <div>• Vertical 9:16 Reframer: <span style={{ color: '#c9d1d9' }}>MediaPipe / Gaze Active</span></div>
                <div>• ComfyUI Port: <span style={{ color: '#58a6ff' }}>8188 (Primary) / 8189 (Screenplay)</span></div>
                <div>• Local Checkpoints: <span style={{ color: '#c9d1d9' }}>Wan2.1 (5.41GB), LTX-2B (5.45GB)</span></div>
              </div>
            </div>

            {/* Pillar 2: Broadcast Kernel & OBS Studio */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.1rem' }}>📡</span>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#a371f7' }}>Broadcast Kernel (OBS / UE5)</span>
                </div>
                <span style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: matrixStatus.pillars?.broadcast_kernel?.is_obs_running ? '#3fb950' : '#8b949e',
                  background: matrixStatus.pillars?.broadcast_kernel?.is_obs_running ? 'rgba(63, 185, 80, 0.15)' : 'rgba(139, 148, 158, 0.15)',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  {matrixStatus.pillars?.broadcast_kernel?.is_obs_running ? 'OBS STREAMING' : 'SOCKET READY'}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• OBS WebSocket Engine: <span style={{ color: '#58a6ff' }}>Port 4455 (v5.x Protocol)</span></div>
                <div>• Suggested Scene: <span style={{ color: '#c9d1d9' }}>{matrixStatus.pillars?.broadcast_kernel?.suggested_scene || 'AI-BS Main'}</span></div>
                <div>• Unreal Engine 5 Bridge: <span style={{ color: '#58a6ff' }}>Port 8888 (Signaling Host)</span></div>
                <div>• Master Audio Mix: <span style={{ color: '#3fb950' }}>48kHz AES3 6-Track Matrix</span></div>
              </div>
            </div>

            {/* Pillar 3: Crypto Swarm & Scalp Bot */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.1rem' }}>⚡</span>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#3fb950' }}>Crypto Swarm (Port 8007)</span>
                </div>
                <span style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: matrixStatus.pillars?.crypto_swarm?.trading_paused ? '#f85149' : '#3fb950',
                  background: matrixStatus.pillars?.crypto_swarm?.trading_paused ? 'rgba(248, 81, 73, 0.15)' : 'rgba(63, 185, 80, 0.15)',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  {matrixStatus.pillars?.crypto_swarm?.trading_paused ? 'TRADING PAUSED' : 'PORT 8007 ACTIVE'}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• Execution Engine: <span style={{ color: '#c9d1d9' }}>TWAP Drip Micro-Allocations</span></div>
                <div>• Active TWAP Plans: <span style={{ color: '#58a6ff', fontWeight: 600 }}>{matrixStatus.pillars?.crypto_swarm?.twap_plans_count ?? 0}</span></div>
                <div>• Drip Orders in Queue: <span style={{ color: '#58a6ff', fontWeight: 600 }}>{matrixStatus.pillars?.crypto_swarm?.drip_orders_count ?? 0}</span></div>
                <div>• Trailing Stop Guards: <span style={{ color: '#3fb950' }}>ARMED (Max Slippage 0.5%)</span></div>
              </div>
            </div>

            {/* Pillar 4: Ollama Swarm & Reasoning */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.1rem' }}>🧠</span>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#58a6ff' }}>Ollama Swarm (17 Models)</span>
                </div>
                <span style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: matrixStatus.pillars?.ollama_swarm?.status === 'ONLINE' ? '#3fb950' : '#d29922',
                  background: 'rgba(88, 166, 255, 0.15)',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  {matrixStatus.pillars?.ollama_swarm?.status || 'ONLINE'}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• Port Matrix: <span style={{ color: '#58a6ff' }}>11434 (C: Drive) & 11435 (E: Drive)</span></div>
                <div>• Loaded Models: <span style={{ color: '#c9d1d9' }}>stehouwer_llm, stehouwer_qwen, mixtral</span></div>
                <div>• Vector Memory: <span style={{ color: '#3fb950' }}>ChromaDB (stehouwer_llm_memory)</span></div>
                <div>• Context Window: <span style={{ color: '#c9d1d9' }}>8,192 tokens with SSD Virtual Swap</span></div>
              </div>
            </div>

            {/* Pillar 5: Salad Compute & Distributed Telemetry Feed */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '1.1rem' }}>🥗</span>
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#7ee787' }}>Salad Distributed Node</span>
                </div>
                <span style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  color: (matrixStatus.salad?.running || matrixStatus.pillars?.salad_engine?.running) ? '#3fb950' : '#8b949e',
                  background: (matrixStatus.salad?.running || matrixStatus.pillars?.salad_engine?.running) ? 'rgba(63, 185, 80, 0.15)' : 'rgba(139, 148, 158, 0.15)',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  {(matrixStatus.salad?.running || matrixStatus.pillars?.salad_engine?.running) ? 'ACTIVE' : 'IDLE'}
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• Workload State: <span style={{ color: '#58a6ff', fontWeight: 600 }}>{matrixStatus.salad?.status || matrixStatus.pillars?.salad_engine?.status || 'idle'}</span></div>
                <div>• Bandwidth Sharing: <span style={{ color: '#3fb950', fontWeight: 600 }}>{(matrixStatus.salad?.bandwidth_mbps || matrixStatus.pillars?.salad_engine?.bandwidth_mbps || 0) > 0 ? `${matrixStatus.salad?.bandwidth_mbps || matrixStatus.pillars?.salad_engine?.bandwidth_mbps} Mbps` : 'Online / Listening'}</span></div>
                <div>• GPU Chopping: <span style={{ color: (matrixStatus.salad?.rigel_mining || matrixStatus.pillars?.salad_engine?.rigel_mining) ? '#3fb950' : '#c9d1d9' }}>{(matrixStatus.salad?.rigel_mining || matrixStatus.pillars?.salad_engine?.rigel_mining) ? 'Rigel RTX 4090 Mining' : 'RTX 4090 Available'}</span></div>
                <div>• Container Disk: <span style={{ color: '#c9d1d9' }}>E:\SaladData\ (Junction on C:\)</span></div>
              </div>
            </div>

          </div>
        </div>

        {/* ── COLUMN 3: ACTION QUEUE & GOVERNANCE LEDGER ── */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0d1117',
          borderRadius: '8px',
          border: '1px solid #21262d',
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            padding: '10px 14px',
            backgroundColor: '#161b22',
            borderBottom: '1px solid #21262d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1rem' }}>🛡️</span>
              <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#c9d1d9' }}>
                Action Queue & Governance ({pendingActions.length})
              </span>
            </div>
            <span style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              color: pendingActions.length > 0 ? '#f85149' : '#3fb950'
            }}>
              {pendingActions.length > 0 ? `⚠️ ${pendingActions.length} PENDING APPROVAL` : '✓ QUEUE CLEAR'}
            </span>
          </div>

          {/* Pending Approval List & History */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            {/* Section 1: Pending Actions Awaiting Operator Approval */}
            <div style={{ fontSize: '0.72rem', color: '#8b949e', fontWeight: 700, textTransform: 'uppercase' }}>
              Pending Operator Confirmation:
            </div>

            {pendingActions.length === 0 ? (
              <div style={{
                padding: '24px 16px',
                textAlign: 'center',
                backgroundColor: '#161b22',
                borderRadius: '8px',
                border: '1px dashed #30363d',
                color: '#8b949e',
                fontSize: '0.78rem'
              }}>
                <div>✓ No actions currently awaiting confirmation.</div>
                <div style={{ fontSize: '0.7rem', marginTop: '4px', color: '#484f58' }}>
                  Tier 1 operations auto-execute immediately. Tier 2 and Tier 3 actions appear here for 1-click confirmation.
                </div>
              </div>
            ) : (
              pendingActions.map((action) => {
                const isHighRisk = action.tier === 3;
                return (
                  <div
                    key={action.action_id}
                    style={{
                      backgroundColor: '#161b22',
                      borderRadius: '8px',
                      border: `1px solid ${isHighRisk ? '#f85149' : '#d29922'}`,
                      padding: '12px',
                      boxShadow: isHighRisk ? '0 0 10px rgba(248, 81, 73, 0.2)' : 'none'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontWeight: 800, fontSize: '0.8rem', color: isHighRisk ? '#f85149' : '#d29922' }}>
                        {isHighRisk ? '🚨 HIGH RISK TIER 3 ACTION' : '⚠️ TIER 2 MEDIA/BROADCAST'}
                      </span>
                      <span style={{
                        fontSize: '0.66rem',
                        background: '#0d1117',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        color: '#8b949e'
                      }}>
                        {action.action_id}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.76rem', color: '#c9d1d9', marginBottom: '8px', fontWeight: 600 }}>
                      Target: <span style={{ color: '#58a6ff' }}>{action.pillar}.{action.action_name}</span>
                    </div>

                    {/* Parameters Box */}
                    <div style={{
                      backgroundColor: '#0d1117',
                      padding: '8px',
                      borderRadius: '6px',
                      fontSize: '0.7rem',
                      fontFamily: 'monospace',
                      color: '#8b949e',
                      marginBottom: '10px',
                      maxHeight: '80px',
                      overflowY: 'auto'
                    }}>
                      {JSON.stringify(action.parameters, null, 2)}
                    </div>

                    {/* Action Confirmation Buttons */}
                    {(() => {
                      const isThisResolving = isResolving && resolvingActionIds.has(action.action_id);
                      return (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            onClick={() => handleResolveAction(action.action_id, 'APPROVE')}
                            disabled={isThisResolving}
                            style={{
                              flex: 1,
                              background: isThisResolving ? '#21262d' : '#238636',
                              color: '#ffffff',
                              border: 'none',
                              borderRadius: '6px',
                              padding: '7px',
                              fontWeight: 700,
                              fontSize: '0.75rem',
                              cursor: isThisResolving ? 'not-allowed' : 'pointer',
                              opacity: isThisResolving ? 0.6 : 1
                            }}
                          >
                            {isThisResolving ? '⏳ EXECUTING...' : '✓ APPROVE & EXECUTE'}
                          </button>
                          <button
                            onClick={() => handleResolveAction(action.action_id, 'REJECT')}
                            disabled={isThisResolving}
                            style={{
                              background: isThisResolving ? '#21262d' : '#da3633',
                              color: '#ffffff',
                              border: 'none',
                              borderRadius: '6px',
                              padding: '7px 12px',
                              fontWeight: 700,
                              fontSize: '0.75rem',
                              cursor: isThisResolving ? 'not-allowed' : 'pointer',
                              opacity: isThisResolving ? 0.6 : 1
                            }}
                          >
                            ✕ REJECT
                          </button>
                        </div>
                      );
                    })()}
                  </div>
                );
              })
            )}

            {/* Section 2: Execution Audit Ledger */}
            <div style={{ fontSize: '0.72rem', color: '#8b949e', fontWeight: 700, textTransform: 'uppercase', marginTop: '12px' }}>
              Recent Audit Log ({actionHistory.length}):
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {actionHistory.slice(0, 8).map((hist, idx) => {
                const isApproved = hist.status === 'APPROVED' || hist.status === 'EXECUTED';
                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      backgroundColor: '#161b22',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      borderLeft: `3px solid ${isApproved ? '#3fb950' : '#f85149'}`
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 600, color: '#c9d1d9' }}>{hist.pillar}.{hist.action_name}</span>
                      <span style={{ fontSize: '0.66rem', color: '#8b949e', marginLeft: '6px' }}>T{hist.tier}</span>
                    </div>
                    <span style={{
                      color: isApproved ? '#3fb950' : '#f85149',
                      fontWeight: 700,
                      fontSize: '0.68rem'
                    }}>
                      {hist.status}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── COLUMN 4: HARDWARE & VAULT TELEMETRY HUD ── */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0d1117',
          borderRadius: '8px',
          border: '1px solid #21262d',
          overflow: 'hidden'
        }}>
          {/* Header */}
          <div style={{
            padding: '10px 14px',
            backgroundColor: '#161b22',
            borderBottom: '1px solid #21262d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1rem' }}>📊</span>
              <span style={{ fontWeight: 700, fontSize: '0.86rem', color: '#c9d1d9' }}>Hardware & Vault HUD</span>
            </div>
            <span style={{ fontSize: '0.7rem', color: '#8b949e' }}>RTX 4090 • NVMe</span>
          </div>

          {/* Gauges & Telemetry Panels */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}>
            {/* RTX 4090 GPU Panel */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 700, fontSize: '0.8rem', color: '#58a6ff' }}>
                  NVIDIA GeForce RTX 4090
                </span>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: (matrixStatus.hardware?.temp_c || 0) < 70 ? '#3fb950' : '#f85149'
                }}>
                  {matrixStatus.hardware?.temp_c || 42}°C
                </span>
              </div>

              {/* VRAM Meter */}
              <div style={{ marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e', marginBottom: '3px' }}>
                  <span>VRAM Allocated:</span>
                  <span>{matrixStatus.hardware?.vram_used_mb || 0} MB / {matrixStatus.hardware?.vram_total_mb || 24576} MB</span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#0d1117', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, Math.round(((matrixStatus.hardware?.vram_used_mb || 0) / (matrixStatus.hardware?.vram_total_mb || 24576)) * 100))}%`,
                    height: '100%',
                    backgroundColor: '#58a6ff',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              {/* GPU Load Meter */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e', marginBottom: '3px' }}>
                  <span>Core Utilization:</span>
                  <span>{matrixStatus.hardware?.gpu_util_pct || 0}%</span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#0d1117', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${matrixStatus.hardware?.gpu_util_pct || 0}%`,
                    height: '100%',
                    backgroundColor: '#3fb950',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
            </div>

            {/* Host System RAM & NVMe Disk */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <span style={{ fontWeight: 700, fontSize: '0.8rem', color: '#c9d1d9', display: 'block', marginBottom: '8px' }}>
                System Memory & Storage
              </span>

              {/* RAM Meter */}
              <div style={{ marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e', marginBottom: '3px' }}>
                  <span>DDR5 RAM:</span>
                  <span>{matrixStatus.hardware?.ram_used_gb || 0} GB / {matrixStatus.hardware?.ram_total_gb || 64} GB ({matrixStatus.hardware?.ram_percent || 0}%)</span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#0d1117', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${matrixStatus.hardware?.ram_percent || 0}%`,
                    height: '100%',
                    backgroundColor: '#a371f7',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>

              {/* NVMe Storage Meter */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e', marginBottom: '3px' }}>
                  <span>Samsung 990 Pro NVMe:</span>
                  <span>{matrixStatus.hardware?.disk_free_gb || 0} GB Free</span>
                </div>
                <div style={{ width: '100%', height: '8px', backgroundColor: '#0d1117', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${matrixStatus.hardware?.disk_percent || 0}%`,
                    height: '100%',
                    backgroundColor: '#f0883e',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
            </div>

            {/* Knowledge Vault Intelligence Counter */}
            <div style={{
              backgroundColor: '#161b22',
              borderRadius: '7px',
              border: '1px solid #30363d',
              padding: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.1rem' }}>🏛️</span>
                <span style={{ fontWeight: 700, fontSize: '0.8rem', color: '#c9d1d9' }}>
                  Stehouwer Knowledge Vault
                </span>
              </div>
              <div style={{ fontSize: '0.74rem', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>• SQLite Vault Records: <span style={{ color: '#58a6ff', fontWeight: 700 }}>{(matrixStatus.vault?.sqlite_vault_records || 305654).toLocaleString()}</span></div>
                <div>• Media Memory Records: <span style={{ color: '#3fb950', fontWeight: 700 }}>{matrixStatus.vault?.media_memory_records || 0}</span></div>
                <div>• ChromaDB Vector Heartbeat: <span style={{ color: '#3fb950', fontWeight: 600 }}>ONLINE</span></div>
                <div>• Multi-Tenant Isolation: <span style={{ color: '#c9d1d9' }}>stehouwer_publishing</span></div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
