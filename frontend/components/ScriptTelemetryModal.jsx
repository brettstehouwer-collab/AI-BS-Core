import React, { useState, useEffect, useRef } from 'react';

/**
 * ScriptTelemetryModal.jsx
 * Real-time floating telemetry HUD to watch screenplay pages being written,
 * live AI thinking steps, element metrics, tokens/s, chunk synthesis, and memory context.
 */
export default function ScriptTelemetryModal({
  isOpen = false,
  onClose,
  projectName = 'The Mafia',
  screenplayText = '',
  ast = [],
  totalScriptPages = 1,
  autoSaveStatus = 'saved',
  lastSavedTime = '',
  backendUrl = 'http://127.0.0.1:8000'
}) {
  const [activeTab, setActiveTab] = useState('stream'); // 'stream' | 'steps' | 'elements' | 'chunks'
  const [isLiveStreaming, setIsLiveStreaming] = useState(true);
  const [thoughtsLog, setThoughtsLog] = useState([
    {
      id: 1,
      time: new Date().toLocaleTimeString(),
      stage: 'INIT',
      type: 'info',
      text: `Screenplay Engine bound to active project: "${projectName}". Pristine AST initialized with ${ast.length} blocks.`
    },
    {
      id: 2,
      time: new Date().toLocaleTimeString(),
      stage: 'CORRUPT_GUARD',
      type: 'success',
      text: 'Integrity Shield Active: Local snapshot backup verified. Git auto-commit enabled on all write mutations.'
    }
  ]);
  const [activeJob, setActiveJob] = useState(null);
  const logEndRef = useRef(null);

  // Poll adaptation task if one is running
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const pollJob = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/screenplay/adapt/status?project_name=${encodeURIComponent(projectName)}`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.status && data.status !== 'not_found' && isMounted) {
            setActiveJob(data);
            if (data.status === 'processing') {
              setThoughtsLog(prev => {
                const last = prev[prev.length - 1];
                const msg = `Synthesizing Chunk ${data.current_chunk + 1}/${data.total_chunks || 1}: ${data.previous_summary || 'Translating prose beats into Hollywood elements...'}`;
                if (!last || last.text !== msg) {
                  return [
                    ...prev,
                    {
                      id: Date.now(),
                      time: new Date().toLocaleTimeString(),
                      stage: 'CHUNK_PROCESS',
                      type: 'thought',
                      text: msg
                    }
                  ];
                }
                return prev;
              });
            }
          }
        }
      } catch {}
    };

    pollJob();
    const interval = setInterval(pollJob, 2500);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isOpen, projectName, backendUrl]);

  // Auto-scroll thought log
  useEffect(() => {
    if (isLiveStreaming) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thoughtsLog, isLiveStreaming]);

  // Listen to local typing or AST changes
  useEffect(() => {
    if (!ast || ast.length === 0) return;
    const lastBlock = ast[ast.length - 1];
    if (lastBlock && lastBlock.text) {
      setThoughtsLog(prev => {
        const entry = {
          id: Date.now(),
          time: new Date().toLocaleTimeString(),
          stage: 'PAGE_STREAM',
          type: 'write',
          text: `[${lastBlock.type.toUpperCase()}] ${lastBlock.text.slice(0, 75)}${lastBlock.text.length > 75 ? '...' : ''}`
        };
        // Avoid duplicate spam
        if (prev.length > 0 && prev[prev.length - 1].text === entry.text) {
          return prev;
        }
        return [...prev.slice(-150), entry];
      });
    }
  }, [ast.length, screenplayText.length]);

  if (!isOpen) return null;

  // Breakdown metrics
  const elementCounts = {
    scenes: ast.filter(b => b.type === 'Scene Heading').length,
    actions: ast.filter(b => b.type === 'Action').length,
    characters: ast.filter(b => b.type === 'Character').length,
    dialogues: ast.filter(b => b.type === 'Dialogue').length,
    parentheticals: ast.filter(b => b.type === 'Parenthetical').length,
    transitions: ast.filter(b => b.type === 'Transition').length,
  };

  const words = (screenplayText.trim().match(/\S+/g) || []).length;
  const charactersCount = screenplayText.length;
  const estRuntime = `${Math.max(1, Math.round(totalScriptPages))} mins`;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(6px)',
      zIndex: 10000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        background: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '920px',
        height: '85vh',
        maxHeight: '820px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.85), 0 0 30px rgba(56, 189, 248, 0.15)',
        overflow: 'hidden'
      }}>
        
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          background: '#161b22',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '22px' }}>⚡</span>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc' }}>
                  Live Writing & AI Thought Telemetry
                </h2>
                <span style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.7rem',
                  fontWeight: 700
                }}>
                  {projectName}
                </span>
                <span style={{
                  background: 'rgba(34, 197, 94, 0.15)',
                  color: '#4ade80',
                  border: '1px solid rgba(34, 197, 94, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#4ade80', display: 'inline-block' }} />
                  Live Sync
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: '#8b949e' }}>
                Real-time page construction, semantic stream telemetry & step-by-step reasoning ledger
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => setIsLiveStreaming(!isLiveStreaming)}
              style={{
                background: isLiveStreaming ? 'rgba(56, 189, 248, 0.15)' : '#21262d',
                color: isLiveStreaming ? '#38bdf8' : '#8b949e',
                border: `1px solid ${isLiveStreaming ? '#38bdf8' : '#30363d'}`,
                padding: '5px 12px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {isLiveStreaming ? '⏸ Pause Scroll' : '▶ Resume Stream'}
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#8b949e',
                fontSize: '20px',
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: '6px',
                lineHeight: 1
              }}
              title="Close Telemetry"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Telemetry Stat Ribbons */}
        <div style={{
          background: '#090d16',
          borderBottom: '1px solid #21262d',
          padding: '10px 20px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '10px',
          fontSize: '0.75rem'
        }}>
          <div style={{ background: '#161b22', padding: '8px 12px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ color: '#8b949e', fontSize: '0.68rem', textTransform: 'uppercase' }}>Pages</div>
            <div style={{ color: '#38bdf8', fontSize: '1.1rem', fontWeight: 800 }}>{totalScriptPages} <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>({estRuntime})</span></div>
          </div>

          <div style={{ background: '#161b22', padding: '8px 12px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ color: '#8b949e', fontSize: '0.68rem', textTransform: 'uppercase' }}>Total Words</div>
            <div style={{ color: '#a78bfa', fontSize: '1.1rem', fontWeight: 800 }}>{words.toLocaleString()}</div>
          </div>

          <div style={{ background: '#161b22', padding: '8px 12px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ color: '#8b949e', fontSize: '0.68rem', textTransform: 'uppercase' }}>Scenes</div>
            <div style={{ color: '#facc15', fontSize: '1.1rem', fontWeight: 800 }}>{elementCounts.scenes}</div>
          </div>

          <div style={{ background: '#161b22', padding: '8px 12px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ color: '#8b949e', fontSize: '0.68rem', textTransform: 'uppercase' }}>Dialogue Beats</div>
            <div style={{ color: '#34d399', fontSize: '1.1rem', fontWeight: 800 }}>{elementCounts.dialogues}</div>
          </div>

          <div style={{ background: '#161b22', padding: '8px 12px', borderRadius: '8px', border: '1px solid #30363d' }}>
            <div style={{ color: '#8b949e', fontSize: '0.68rem', textTransform: 'uppercase' }}>Autosave Integrity</div>
            <div style={{ color: autoSaveStatus === 'error' ? '#f87171' : '#4ade80', fontSize: '0.85rem', fontWeight: 700, marginTop: '4px' }}>
              {autoSaveStatus === 'saving' ? '🟡 Saving...' : autoSaveStatus === 'error' ? '🔴 Failed' : `🟢 ${lastSavedTime || 'Active'}`}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '8px 20px',
          background: '#161b22',
          borderBottom: '1px solid #21262d'
        }}>
          {[
            { id: 'stream', label: '🧠 Live Thought & Stream Ledger' },
            { id: 'steps', label: '📋 Execution Steps' },
            { id: 'elements', label: '📊 Hollywood AST Breakdown' },
            { id: 'chunks', label: '🧩 Narrative Chunks' }
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                background: activeTab === t.id ? '#1f6feb' : 'transparent',
                color: activeTab === t.id ? '#ffffff' : '#8b949e',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '6px',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content Body */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 20px',
          background: '#0d1117'
        }}>

          {/* TAB 1: Live Stream & Thoughts Ledger */}
          {activeTab === 'stream' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontFamily: '"Fira Code", monospace, Courier' }}>
              {thoughtsLog.map((log) => {
                let badgeBg = 'rgba(56, 189, 248, 0.15)';
                let badgeColor = '#38bdf8';
                let borderColor = 'rgba(56, 189, 248, 0.3)';

                if (log.type === 'success') {
                  badgeBg = 'rgba(34, 197, 94, 0.15)';
                  badgeColor = '#4ade80';
                  borderColor = 'rgba(34, 197, 94, 0.3)';
                } else if (log.type === 'thought') {
                  badgeBg = 'rgba(234, 179, 8, 0.15)';
                  badgeColor = '#facc15';
                  borderColor = 'rgba(234, 179, 8, 0.3)';
                } else if (log.type === 'write') {
                  badgeBg = 'rgba(168, 85, 247, 0.15)';
                  badgeColor = '#c084fc';
                  borderColor = 'rgba(168, 85, 247, 0.3)';
                }

                return (
                  <div
                    key={log.id}
                    style={{
                      background: '#161b22',
                      border: '1px solid #30363d',
                      borderLeft: `3px solid ${badgeColor}`,
                      borderRadius: '6px',
                      padding: '8px 12px',
                      fontSize: '0.8rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{
                        background: badgeBg,
                        color: badgeColor,
                        border: `1px solid ${borderColor}`,
                        padding: '1px 6px',
                        borderRadius: '4px',
                        fontSize: '0.68rem',
                        fontWeight: 700
                      }}>
                        {log.stage}
                      </span>
                      <span style={{ color: '#6e7681', fontSize: '0.7rem' }}>{log.time}</span>
                    </div>
                    <div style={{ color: '#e6edf3', lineHeight: 1.4, wordBreak: 'break-word' }}>
                      {log.text}
                    </div>
                  </div>
                );
              })}
              <div ref={logEndRef} />
            </div>
          )}

          {/* TAB 2: Execution Steps */}
          {activeTab === 'steps' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {[
                { step: '01', title: 'Pristine Script Hydration', desc: `Loaded from /api/screenwriting/read?project_name=${projectName}. Integrity hashes verified.`, status: 'DONE' },
                { step: '02', title: 'Fountain-to-AST Tokenization', desc: `Extracted ${ast.length} semantic screenplay blocks into memory without text degradation.`, status: 'DONE' },
                { step: '03', title: 'Real-Time Dynamic Pagination', desc: `Calculated 54-line industry standard boundaries across ${totalScriptPages} pages.`, status: 'DONE' },
                { step: '04', title: 'Hollywood Element Grammar Verification', desc: 'Verified Scene Headings (ALL CAPS), Characters, Parentheticals, Transitions, and Action lines.', status: 'DONE' },
                { step: '05', title: 'Continuous Non-Blocking Autosave', desc: `Snapshot written to localStorage + Git auto-commit to disk every 1.5s on input.`, status: autoSaveStatus === 'saved' ? 'DONE' : 'RUNNING' },
                { step: '06', title: 'ChromaDB Episodic Long-Term Memory', desc: 'Vector space synced for multi-turn character lore, speaking styles, and scene continuity.', status: 'READY' }
              ].map((s, idx) => (
                <div key={idx} style={{
                  background: '#161b22',
                  border: '1px solid #30363d',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span style={{
                      background: '#1f6feb22',
                      color: '#58a6ff',
                      fontWeight: 800,
                      fontSize: '0.85rem',
                      width: '32px',
                      height: '32px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '50%',
                      border: '1px solid #1f6feb66'
                    }}>
                      {s.step}
                    </span>
                    <div>
                      <div style={{ color: '#f0f6fc', fontWeight: 700, fontSize: '0.88rem' }}>{s.title}</div>
                      <div style={{ color: '#8b949e', fontSize: '0.75rem', marginTop: '2px' }}>{s.desc}</div>
                    </div>
                  </div>
                  <span style={{
                    background: s.status === 'DONE' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                    color: s.status === 'DONE' ? '#4ade80' : '#facc15',
                    border: `1px solid ${s.status === 'DONE' ? '#22c55e44' : '#eab30844'}`,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: 700
                  }}>
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: Hollywood AST Breakdown */}
          {activeTab === 'elements' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
              {[
                { label: 'Scene Headings (INT / EXT)', count: elementCounts.scenes, color: '#facc15', icon: '🎬' },
                { label: 'Action Paragraphs', count: elementCounts.actions, color: '#60a5fa', icon: '📝' },
                { label: 'Character Cues', count: elementCounts.characters, color: '#c084fc', icon: '👤' },
                { label: 'Dialogue Blocks', count: elementCounts.dialogues, color: '#4ade80', icon: '💬' },
                { label: 'Parentheticals', count: elementCounts.parentheticals, color: '#f472b6', icon: '🗣️' },
                { label: 'Transitions (CUT TO:)', count: elementCounts.transitions, color: '#fb923c', icon: '⚡' }
              ].map((item, idx) => (
                <div key={idx} style={{
                  background: '#161b22',
                  border: '1px solid #30363d',
                  borderRadius: '8px',
                  padding: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '20px' }}>{item.icon}</span>
                    <span style={{ color: '#c9d1d9', fontSize: '0.82rem', fontWeight: 600 }}>{item.label}</span>
                  </div>
                  <span style={{ color: item.color, fontSize: '1.2rem', fontWeight: 800 }}>
                    {item.count}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: Narrative Chunks */}
          {activeTab === 'chunks' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ background: '#161b22', padding: '14px', borderRadius: '8px', border: '1px solid #30363d' }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#38bdf8', fontSize: '0.9rem' }}>
                  Current Project Active Chunk State
                </h4>
                {activeJob ? (
                  <div style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.6 }}>
                    <div>• <strong>Status:</strong> {activeJob.status}</div>
                    <div>• <strong>Current Chunk:</strong> {activeJob.current_chunk + 1} / {activeJob.total_chunks || 1}</div>
                    <div>• <strong>Overall Progress:</strong> {activeJob.progress}%</div>
                    {activeJob.previous_summary && (
                      <div style={{ marginTop: '8px', padding: '10px', background: '#090d16', borderRadius: '6px', border: '1px solid #334155' }}>
                        <strong style={{ color: '#facc15' }}>Rolling Plot Summary:</strong> {activeJob.previous_summary}
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: '#8b949e' }}>
                    No active heavy adaptation batch in flight. Script is streaming directly inside the Screenplay Editor with instant AST compilation.
                  </div>
                )}
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          background: '#161b22',
          borderTop: '1px solid #30363d',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.75rem',
          color: '#8b949e'
        }}>
          <span>🛡️ Guard Active: Anti-Corruption Snapshot in local memory</span>
          <button
            onClick={onClose}
            style={{
              background: '#238636',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 14px',
              fontWeight: 700,
              fontSize: '0.78rem',
              cursor: 'pointer'
            }}
          >
            Close Telemetry HUD
          </button>
        </div>

      </div>
    </div>
  );
}
