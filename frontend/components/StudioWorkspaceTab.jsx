import React, { useState } from 'react';
import DocumentsTab from './DocumentsTab';

export default function StudioWorkspaceTab(props) {
  const { backendUrl, sharedContent, setSharedContent, sharedActiveDoc, setSharedActiveDoc } = props;
  const [activeMode, setActiveMode] = useState('documents'); // 'documents', 'firewriting'

  const [fireProfile, setFireProfile] = useState('fire_writing');
  const [fireTextRaw, setFireTextRaw] = useState('');
  const [fireTextFormatted, setFireTextFormatted] = useState('');
  const [isFormatting, setIsFormatting] = useState(false);

  const handleFormatFireWriting = async () => {
    setIsFormatting(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/firewrite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: fireTextRaw, profile: fireProfile })
      });
      const data = await res.json();
      setFireTextFormatted(data.formatted || data.error || 'Error formatting');
    } catch (e) {
      setFireTextFormatted('Network error while reaching formatting endpoint.');
    } finally {
      setIsFormatting(false);
    }
  };

  const handleExportFireWriting = () => {
    const blob = new Blob([fireTextFormatted], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `firewrite_${Date.now()}.md`;
    a.click();
  };

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', background: 'var(--bg-main, #0d1117)' }}>
      {/* Studio Sub-Navigation Sidebar */}
      <div style={{ 
        width: '60px', 
        background: 'var(--bg-panel, #161b22)', 
        borderRight: '1px solid var(--border-color, #30363d)', 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        paddingTop: '20px', 
        gap: '20px',
        zIndex: 10
      }}>
        <button 
          onClick={() => setActiveMode('documents')} 
          style={{ background: 'none', border: 'none', color: activeMode === 'documents' ? '#58a6ff' : '#8b949e', fontSize: '1.5rem', cursor: 'pointer', padding: '10px' }}
          title="General Documents"
        >
          📄
        </button>
        <button 
          onClick={() => setActiveMode('firewriting')} 
          style={{ background: 'none', border: 'none', color: activeMode === 'firewriting' ? '#58a6ff' : '#8b949e', fontSize: '1.5rem', cursor: 'pointer', padding: '10px' }}
          title="Fire Writing"
        >
          🔥
        </button>
      </div>

      {/* Main Studio Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
        {activeMode === 'documents' && (
          <DocumentsTab 
            backendUrl={backendUrl} 
            sharedContent={sharedContent}
            setSharedContent={setSharedContent}
            sharedActiveDoc={sharedActiveDoc}
            setSharedActiveDoc={setSharedActiveDoc}
            onSwitchToScreenwriting={props.onSwitchToScreenwriting}
          />
        )}
        
        {/* Isolated FireWriting Environment */}
        {activeMode === 'firewriting' && (
          <div className="fire-writing-container" style={{ height: '100%', padding: '20px', display: 'flex', flexDirection: 'column' }}>
            <div className="fire-writing-toolbar glass-panel" style={{ padding: '16px', borderRadius: '8px', marginBottom: '20px', background: 'var(--bg-panel, #161b22)', border: '1px solid var(--border-color, #30363d)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="fire-controls-left">
                <span style={{ fontWeight: '600', marginRight: '10px', color: '#c9d1d9' }}>Formatting Style:</span>
                <select 
                  value={fireProfile}
                  onChange={(e) => setFireProfile(e.target.value)}
                  style={{ background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '6px 12px', borderRadius: '4px' }}
                >
                  <option value="fire_writing">🔥 Strict Structural (No words altered)</option>
                  <option value="professional">💼 Professional Polish (Emails, Memos)</option>
                  <option value="creative">📖 Creative Prose (Narrative & Flow)</option>
                  <option value="journal">📓 Journal Outline (Summaries & Actions)</option>
                </select>
              </div>

              <div className="fire-buttons-right" style={{ display: 'flex', gap: '12px' }}>
                <button 
                  onClick={handleFormatFireWriting}
                  disabled={isFormatting || !fireTextRaw.trim()}
                  style={{ background: '#238636', color: 'white', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: (isFormatting || !fireTextRaw.trim()) ? 'not-allowed' : 'pointer', opacity: (isFormatting || !fireTextRaw.trim()) ? 0.6 : 1, fontWeight: 'bold' }}
                >
                  {isFormatting ? 'Processing AI...' : '✨ Execute Formatting'}
                </button>
                <button 
                  onClick={handleExportFireWriting}
                  disabled={!fireTextFormatted}
                  style={{ background: '#1f6feb', color: 'white', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: !fireTextFormatted ? 'not-allowed' : 'pointer', opacity: !fireTextFormatted ? 0.5 : 1 }}
                >
                  📥 Export (.md)
                </button>
              </div>
            </div>

            <div className="split-pane" style={{ display: 'flex', gap: '20px', flex: 1, overflow: 'hidden' }}>
              <div className="pane input-pane" style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid var(--border-color, #30363d)', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ padding: '10px 15px', background: 'var(--bg-panel, #161b22)', borderBottom: '1px solid var(--border-color, #30363d)', fontWeight: 'bold', color: '#8b949e' }}>Raw Input (Stream of Consciousness)</div>
                <textarea 
                  placeholder="Pour out your raw, unfiltered thoughts here..."
                  value={fireTextRaw}
                  onChange={(e) => setFireTextRaw(e.target.value)}
                  style={{ flex: 1, background: '#0d1117', color: '#c9d1d9', border: 'none', padding: '15px', resize: 'none', outline: 'none', fontFamily: 'monospace', fontSize: '14px' }}
                />
              </div>
              <div className="pane output-pane" style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid var(--border-color, #30363d)', borderRadius: '8px', overflow: 'hidden' }}>
                <div style={{ padding: '10px 15px', background: 'var(--bg-panel, #161b22)', borderBottom: '1px solid var(--border-color, #30363d)', fontWeight: 'bold', color: '#8b949e' }}>Structured Output (AI Formatted)</div>
                <textarea 
                  readOnly
                  placeholder="AI formatted text will appear here..."
                  value={fireTextFormatted}
                  style={{ flex: 1, background: '#0d1117', color: '#c9d1d9', border: 'none', padding: '15px', resize: 'none', outline: 'none', fontFamily: 'sans-serif', fontSize: '15px', lineHeight: '1.5' }}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
