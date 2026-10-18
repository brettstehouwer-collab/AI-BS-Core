import React, { useState, useEffect } from 'react';
import ChatToolControlBar from './ChatToolControlBar';
import ChatTab from './ChatTab';
import VisualScriptingTab from './VisualScriptingTab';
import BullshitTelemetrySuite from '../src/BullshitTelemetrySuite';
import BullshitKnowledgeSuite from '../src/BullshitKnowledgeSuite';
import { useAppStore } from './useAppStore';

function resolveHostCPath(rawPath) {
  if (!rawPath) return 'C:\\AI-BS\\scratch\\test_chat.txt';
  let p = String(rawPath).trim().replace(/^file:\/\/\/?/i, '');
  if (/^[a-zA-Z]:/.test(p)) {
    return p.replace(/\//g, '\\');
  }
  p = p.replace(/^[\/\\]+/, '').replace(/\//g, '\\');
  if (p.toLowerCase().startsWith('ai-bs\\')) {
    return 'C:\\' + p;
  }
  return 'C:\\AI-BS\\' + p;
}

export default function SplitPaneIDEWorkspace() {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL) || 'http://127.0.0.1:8080';
  const [activeRightTab, setActiveRightTab] = useState('ide_editor');
  const [showRightPane, setShowRightPane] = useState(false);
  const [ideFile, setIdeFile] = useState({
    path: 'scratch/test_chat.txt',
    fullPath: 'C:\\AI-BS\\scratch\\test_chat.txt',
    content: '',
    lines: 1,
    size_bytes: 0
  });
  const [editorStatus, setEditorStatus] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [showRenameBar, setShowRenameBar] = useState(false);

  const reqHeaders = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
    'X-Client-ID': 'stehouwer_publishing'
  };

  const loadFileIntoIde = async (targetPath, preloadedContent = null) => {
    const cleanTarget = String(targetPath || '').trim().replace(/^file:\/\/\/?/i, '');
    const fullCPath = resolveHostCPath(cleanTarget);
    setShowRightPane(true);
    setActiveRightTab('ide_editor');

    if (preloadedContent !== null && preloadedContent !== undefined) {
      setIdeFile({
        path: cleanTarget,
        fullPath: fullCPath,
        content: preloadedContent,
        lines: preloadedContent.split('\n').length,
        size_bytes: preloadedContent.length
      });
      setEditorStatus(`✅ Loaded ${fullCPath}`);
      setTimeout(() => setEditorStatus(''), 4000);
      return;
    }

    setEditorStatus(`⏳ Loading ${fullCPath}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({ command_type: 'file_read', target: fullCPath })
      });
      const data = await res.json();
      if (data.status === 'success' && data.result) {
        const text = data.result.content || '';
        setIdeFile({
          path: cleanTarget,
          fullPath: fullCPath,
          content: text,
          lines: data.result.lines || text.split('\n').length,
          size_bytes: data.result.size_bytes ?? text.length
        });
        setEditorStatus(`✅ Opened ${fullCPath} (${data.result.size_bytes ?? text.length} bytes)`);
      } else {
        // Fallback try with relative path
        const res2 = await fetch(`${BACKEND_URL}/api/executive/run`, {
          method: 'POST',
          headers: reqHeaders,
          body: JSON.stringify({ command_type: 'file_read', target: cleanTarget })
        });
        const data2 = await res2.json();
        const text2 = data2?.result?.content || '';
        setIdeFile({
          path: cleanTarget,
          fullPath: fullCPath,
          content: text2,
          lines: text2 ? text2.split('\n').length : 1,
          size_bytes: text2.length
        });
        setEditorStatus(data2.status === 'success' ? `✅ Opened ${fullCPath}` : `⚠️ File ready for editing: ${fullCPath}`);
      }
    } catch (err) {
      setEditorStatus(`❌ Error loading file: ${err.message}`);
    }
    setTimeout(() => setEditorStatus(''), 4500);
  };

  useEffect(() => {
    const handleOpenIdeEvent = (e) => {
      if (e.detail && e.detail.path) {
        loadFileIntoIde(e.detail.path, e.detail.content ?? null);
      }
    };
    window.addEventListener('aibs-open-ide-editor', handleOpenIdeEvent);
    return () => window.removeEventListener('aibs-open-ide-editor', handleOpenIdeEvent);
  }, [BACKEND_URL]);

  const handleSaveIdeFile = async () => {
    setIsSaving(true);
    setEditorStatus('⏳ Saving to C: drive with .bak backup...');
    try {
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({
          command_type: 'file_write',
          target: ideFile.fullPath || ideFile.path,
          payload: { content: ideFile.content }
        })
      });
      const data = await res.json();
      if (data.status === 'success' || data.result?.status === 'success') {
        const bytes = ideFile.content.length;
        setIdeFile(prev => ({ ...prev, lines: prev.content.split('\n').length, size_bytes: bytes }));
        setEditorStatus(`✅ Saved to ${ideFile.fullPath} (${bytes} bytes)`);
      } else {
        setEditorStatus(`⚠️ Save error: ${data.message || 'Failed'}`);
      }
    } catch (err) {
      setEditorStatus(`❌ Error saving: ${err.message}`);
    } finally {
      setIsSaving(false);
      setTimeout(() => setEditorStatus(''), 4500);
    }
  };

  const handleShowInExplorer = async (pathToReveal) => {
    const fullCPath = resolveHostCPath(pathToReveal || ideFile.fullPath || ideFile.path);
    setEditorStatus(`📂 Opening Windows File Explorer: ${fullCPath}`);
    try {
      await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({
          command_type: 'show_in_explorer',
          target: fullCPath
        })
      });
    } catch (err) {
      setEditorStatus(`❌ Explorer error: ${err.message}`);
    }
    setTimeout(() => setEditorStatus(''), 4000);
  };

  const handleRenameIdeFile = async () => {
    if (!renameValue.trim()) return;
    setEditorStatus(`⏳ Renaming to ${renameValue.trim()}...`);
    try {
      const res = await fetch(`${BACKEND_URL}/api/executive/run`, {
        method: 'POST',
        headers: reqHeaders,
        body: JSON.stringify({
          command_type: 'file_rename',
          target: ideFile.fullPath || ideFile.path,
          payload: { new_name: renameValue.trim() }
        })
      });
      const data = await res.json();
      if (data.status === 'success' && data.result?.new_path) {
        const newFull = data.result.new_path;
        setIdeFile(prev => ({ ...prev, path: newFull, fullPath: newFull }));
        setShowRenameBar(false);
        setRenameValue('');
        setEditorStatus(`✅ Renamed on C: drive to ${newFull}`);
        window.dispatchEvent(new CustomEvent('aibs-file-renamed', { detail: { oldPath: ideFile.fullPath, newPath: newFull } }));
      } else {
        setEditorStatus(`⚠️ Rename failed: ${data.message || 'Error'}`);
      }
    } catch (err) {
      setEditorStatus(`❌ Rename error: ${err.message}`);
    }
    setTimeout(() => setEditorStatus(''), 4500);
  };

  const lineCount = Math.max(1, (ideFile.content || '').split('\n').length);

  return (
    <div className="w-full h-full flex flex-col box-border" style={{
      display: 'grid',
      gridTemplateColumns: showRightPane ? 'repeat(auto-fit, minmax(420px, 1fr))' : '1fr',
      gap: '8px',
      height: '100%',
      width: '100%',
      padding: 0,
      backgroundColor: '#0d1117',
      boxSizing: 'border-box',
      overflowX: 'auto',
      overflowY: 'hidden'
    }}>
      {/* LEFT PANE: Persistent Agentic Chat & Tool Bar */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '12px',
        overflow: 'hidden'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', color: '#58a6ff', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span>💬</span> AI-BS Autonomous Agentic IDE Chat
            <span style={{
              fontSize: '10px',
              background: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              padding: '2px 7px',
              borderRadius: '999px',
              fontWeight: 700
            }}>
              1M+ Offload RAG Window Active
            </span>
            <span style={{
              fontSize: '10px',
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#34d399',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              padding: '2px 7px',
              borderRadius: '999px',
              fontWeight: 700
            }}>
              🩺 Stage 1 Auto-Heal (3x)
            </span>
            <span style={{
              fontSize: '10px',
              background: 'rgba(239, 68, 68, 0.15)',
              color: '#fca5a5',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              padding: '2px 7px',
              borderRadius: '999px',
              fontWeight: 700
            }}>
              🕸️ Stage 2 AST Blast Graph (491 Nodes)
            </span>
            <span style={{
              fontSize: '10px',
              background: 'rgba(168, 85, 247, 0.15)',
              color: '#c084fc',
              border: '1px solid rgba(168, 85, 247, 0.35)',
              padding: '2px 7px',
              borderRadius: '999px',
              fontWeight: 700
            }}>
              🧬 Stage 3 RTX 4090 QLoRA
            </span>
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', color: '#7ee787' }}>● {showRightPane ? 'Split-Pane IDE Active' : 'Single-Pane Active'} (v5.323.0)</span>
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('aibs-toggle-wireless-cast'))}
              style={{
                background: 'linear-gradient(135deg, #0284c7, #2563eb)',
                border: '1px solid #60a5fa',
                color: '#fff',
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 700
              }}
              title="Open 3-Way Wireless Screen Mirror & Display Cast Hub (PC➔Wireless Display, PC➔Phone, Phone➔PC)"
            >
              📡 Wireless Cast & Mirror
            </button>
            <button
              onClick={() => {
                setActiveRightTab('ide_editor');
                setShowRightPane(!showRightPane);
              }}
              style={{
                background: showRightPane ? 'linear-gradient(135deg, #2563eb, #1d4ed8)' : 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#fff',
                padding: '4px 10px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: 600
              }}
            >
              ↔ Toggle Split View ({showRightPane ? 'Hide IDE' : 'Open IDE Editor'})
            </button>
          </div>
        </div>

        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', borderRadius: '6px', border: '1px solid #30363d' }}>
          {/* Primary Chat Interface Injected into Left Pane */}
          <ChatTab isNested={true} />
        </div>
      </div>

      {/* RIGHT PANE: Dynamic IDE Code Editor & Workspaces */}
      {showRightPane && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '12px',
          overflow: 'hidden'
        }}>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', borderBottom: '1px solid #30363d', paddingBottom: '8px', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => setActiveRightTab('ide_editor')}
                style={{
                  backgroundColor: activeRightTab === 'ide_editor' ? '#1e3a8a' : 'transparent',
                  color: activeRightTab === 'ide_editor' ? '#93c5fd' : '#8b949e',
                  border: activeRightTab === 'ide_editor' ? '1px solid #3b82f6' : '1px solid #30363d',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                📝 IDE Code Editor
              </button>
              <button
                type="button"
                onClick={() => setActiveRightTab('shm_telemetry')}
                style={{
                  backgroundColor: activeRightTab === 'shm_telemetry' ? '#21262d' : 'transparent',
                  color: activeRightTab === 'shm_telemetry' ? '#00d2ff' : '#8b949e',
                  border: '1px solid #30363d',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                ⚡ SHM Telemetry
              </button>
              <button
                type="button"
                onClick={() => setActiveRightTab('omnidrive')}
                style={{
                  backgroundColor: activeRightTab === 'omnidrive' ? '#21262d' : 'transparent',
                  color: activeRightTab === 'omnidrive' ? '#7ee787' : '#8b949e',
                  border: '1px solid #30363d',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                📂 Omni-Drive Explorer
              </button>
              <button
                type="button"
                onClick={() => setActiveRightTab('visual_scripting')}
                style={{
                  backgroundColor: activeRightTab === 'visual_scripting' ? '#21262d' : 'transparent',
                  color: activeRightTab === 'visual_scripting' ? '#a855f7' : '#8b949e',
                  border: '1px solid #30363d',
                  borderRadius: '4px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                🧩 Visual Scripting
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowRightPane(false)}
              style={{
                background: 'transparent',
                border: '1px solid #30363d',
                color: '#94a3b8',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '11px',
                cursor: 'pointer'
              }}
            >
              ✕ Close Split
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', backgroundColor: '#0d1117', padding: '12px', borderRadius: '6px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column' }}>
            {activeRightTab === 'ide_editor' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '8px' }}>
                {/* IDE Header Bar */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: '#161b22',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid #30363d',
                  flexWrap: 'wrap',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8' }}>📄 HOST FILE (C: DRIVE):</span>
                    <code
                      onContextMenu={(e) => {
                        e.preventDefault();
                        handleShowInExplorer(ideFile.fullPath);
                      }}
                      title="Right-click to Show in Windows File Explorer"
                      style={{
                        fontSize: '12px',
                        color: '#93c5fd',
                        background: 'rgba(59, 130, 246, 0.12)',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {ideFile.fullPath}
                    </code>
                    <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                      ({lineCount} lines • {ideFile.content.length} bytes)
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => handleShowInExplorer(ideFile.fullPath)}
                      style={{
                        background: 'rgba(16, 185, 129, 0.15)',
                        border: '1px solid rgba(16, 185, 129, 0.4)',
                        color: '#34d399',
                        borderRadius: '4px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      📂 Show in File Explorer
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setRenameValue(ideFile.fullPath.split('\\').pop() || '');
                        setShowRenameBar(!showRenameBar);
                      }}
                      style={{
                        background: 'rgba(245, 158, 11, 0.15)',
                        border: '1px solid rgba(245, 158, 11, 0.4)',
                        color: '#fbbf24',
                        borderRadius: '4px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      ✏️ Rename File
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(ideFile.content);
                        setEditorStatus('📋 Copied file contents to clipboard');
                        setTimeout(() => setEditorStatus(''), 3000);
                      }}
                      style={{
                        background: 'rgba(255, 255, 255, 0.08)',
                        border: '1px solid rgba(255, 255, 255, 0.2)',
                        color: '#e2e8f0',
                        borderRadius: '4px',
                        padding: '4px 10px',
                        fontSize: '11px',
                        cursor: 'pointer'
                      }}
                    >
                      📋 Copy
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveIdeFile}
                      disabled={isSaving}
                      style={{
                        background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                        border: 'none',
                        color: '#ffffff',
                        borderRadius: '4px',
                        padding: '4px 12px',
                        fontSize: '11px',
                        fontWeight: 700,
                        cursor: isSaving ? 'wait' : 'pointer'
                      }}
                    >
                      {isSaving ? '⏳ Saving...' : '💾 Save to Host'}
                    </button>
                  </div>
                </div>

                {/* Inline Rename Bar */}
                {showRenameBar && (
                  <div style={{
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'center',
                    background: '#1e293b',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid rgba(245, 158, 11, 0.4)'
                  }}>
                    <span style={{ fontSize: '11px', color: '#fbbf24', fontWeight: 700 }}>New File Name:</span>
                    <input
                      type="text"
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleRenameIdeFile(); }}
                      placeholder="e.g. bretttest.txt"
                      style={{
                        flex: 1,
                        background: '#0f172a',
                        border: '1px solid #475569',
                        color: '#f8fafc',
                        borderRadius: '4px',
                        padding: '4px 8px',
                        fontSize: '12px',
                        fontFamily: 'monospace'
                      }}
                    />
                    <button
                      type="button"
                      onClick={handleRenameIdeFile}
                      style={{
                        background: '#d97706',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '4px 12px',
                        fontSize: '11px',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      ✓ Apply Rename
                    </button>
                  </div>
                )}

                {editorStatus && (
                  <div style={{
                    fontSize: '11px',
                    color: '#34d399',
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    padding: '5px 10px',
                    borderRadius: '4px'
                  }}>
                    {editorStatus}
                  </div>
                )}

                {/* Code Editor Area with Line Numbers */}
                <div style={{
                  flex: 1,
                  display: 'flex',
                  background: '#090d16',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  overflow: 'hidden',
                  minHeight: '380px'
                }}>
                  <div style={{
                    width: '44px',
                    background: '#0d1117',
                    borderRight: '1px solid #21262d',
                    padding: '12px 6px',
                    textAlign: 'right',
                    color: '#475569',
                    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
                    fontSize: '12px',
                    lineHeight: '1.6',
                    userSelect: 'none',
                    overflow: 'hidden'
                  }}>
                    {Array.from({ length: Math.min(lineCount, 500) }, (_, i) => (
                      <div key={i + 1}>{i + 1}</div>
                    ))}
                  </div>
                  <textarea
                    value={ideFile.content}
                    onChange={e => setIdeFile(prev => ({ ...prev, content: e.target.value }))}
                    onKeyDown={e => {
                      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
                        e.preventDefault();
                        handleSaveIdeFile();
                      }
                    }}
                    spellCheck={false}
                    placeholder="Click any file hyperlink in BS-Chat to view & edit here..."
                    style={{
                      flex: 1,
                      background: 'transparent',
                      color: '#e2e8f0',
                      border: 'none',
                      outline: 'none',
                      padding: '12px',
                      fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
                      fontSize: '12.5px',
                      lineHeight: '1.6',
                      resize: 'none',
                      overflowY: 'auto',
                      whiteSpace: 'pre'
                    }}
                  />
                </div>
              </div>
            )}
            {activeRightTab === 'shm_telemetry' && (
              <div style={{ height: '100%', overflow: 'auto' }}>
                <BullshitTelemetrySuite activeTab="noco_telemetry" />
              </div>
            )}
            {activeRightTab === 'omnidrive' && (
              <div style={{ height: '100%', overflow: 'auto' }}>
                <BullshitKnowledgeSuite activeTab="omnidrive" />
              </div>
            )}
            {activeRightTab === 'visual_scripting' && (
              <div style={{ height: '100%' }}>
                <VisualScriptingTab />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

