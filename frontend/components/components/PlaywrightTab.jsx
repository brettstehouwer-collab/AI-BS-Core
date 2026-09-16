import React, { useState } from 'react';
import ScreenwritingTab from './ScreenwritingTab';
import StudioWorkspaceTab from './StudioWorkspaceTab';

export default function PlaywrightTab(props) {
  const { backendUrl } = props;
  const [activeMode, setActiveMode] = useState('screenwriting'); // 'screenwriting', 'play_performance', 'studio'
  
  // Shared state for Workspace <-> Screenwriting cross-communication
  const [sharedContent, setSharedContent] = useState(null);
  const [sharedActiveDoc, setSharedActiveDoc] = useState(null);

  const handleSwitchToScreenwriting = (newContent, docName) => {
    if (newContent !== undefined) setSharedContent(newContent);
    if (docName) setSharedActiveDoc(docName);
    setActiveMode('screenwriting');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'row', flexWrap: 'nowrap', height: '100%', width: '100%', minHeight: 0, overflow: 'hidden', background: 'var(--bg-main, #0d1117)' }}>
      {/* Studio Sub-Navigation Sidebar */}
      {typeof window !== 'undefined' && !window.location.search.includes('standalone_writer=true') && (
      <div style={{ 
        width: '60px', 
        minWidth: '60px', 
        flexShrink: 0, 
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
          onClick={() => setActiveMode('play_performance')} 
          style={{ background: 'none', border: 'none', color: activeMode === 'play_performance' ? '#58a6ff' : '#8b949e', fontSize: '1.5rem', cursor: 'pointer', padding: '10px' }}
          title="Theatrical Performance Mode"
        >
          🎭
        </button>
        <button 
          onClick={() => setActiveMode('screenwriting')} 
          style={{ background: 'none', border: 'none', color: activeMode === 'screenwriting' ? '#58a6ff' : '#8b949e', fontSize: '1.5rem', cursor: 'pointer', padding: '10px' }}
          title="Screenwriting (FDX/Fountain)"
        >
          🎬
        </button>
        <button 
          onClick={() => setActiveMode('studio')} 
          style={{ background: 'none', border: 'none', color: activeMode === 'studio' ? '#58a6ff' : '#8b949e', fontSize: '1.5rem', cursor: 'pointer', padding: '10px' }}
          title="Studio Workspace (Documents/PDFs)"
        >
          🎨
        </button>
      </div>
      )}

      {/* Main Studio Area */}
      <div style={{ flex: 1, flexShrink: 1, width: 'calc(100% - 60px)', height: '100%', maxHeight: '100%', minHeight: 0, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
        {activeMode === 'studio' && (
          <StudioWorkspaceTab 
            {...props} 
            sharedContent={sharedContent} 
            setSharedContent={setSharedContent}
            sharedActiveDoc={sharedActiveDoc}
            setSharedActiveDoc={setSharedActiveDoc}
            onSwitchToScreenwriting={handleSwitchToScreenwriting}
          />
        )}
        {activeMode === 'screenwriting' && (
          <ScreenwritingTab 
            backendUrl={backendUrl} 
            sharedContent={sharedContent}
            setSharedContent={setSharedContent}
            sharedActiveDoc={sharedActiveDoc}
            onSendToVideoStudio={props.onSendToVideoStudio}
          />
        )}
        
        {/* Theatrical Performance Mode */}
        {activeMode === 'play_performance' && (
          <div className="play-performance-container" style={{ height: '100%', padding: '20px', display: 'flex', flexDirection: 'column', color: 'white', overflowY: 'auto' }}>
            <h2 style={{ color: '#d2a8ff', marginBottom: '10px' }}>🎭 Domain-Restricted Intelligence (The Play)</h2>
            <p style={{ color: '#8b949e', marginBottom: '20px' }}>
              Upload the "AI Bible" and script documents here. When Performance Mode is active, the AI will completely isolate its memory and ONLY draw from these documents, ignoring all general global knowledge and past conversations.
            </p>

            <div style={{ background: 'var(--bg-panel, #161b22)', padding: '20px', borderRadius: '8px', border: '1px solid var(--border-color, #30363d)', marginBottom: '20px' }}>
              <h3 style={{ margin: '0 0 15px 0', color: '#58a6ff' }}>1. Ingest "AI Bible"</h3>
              <input type="file" multiple style={{ marginBottom: '10px' }} />
              <button style={{ background: '#238636', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                Upload to Isolated Vector Space
              </button>
            </div>

            <div style={{ background: 'var(--bg-panel, #161b22)', padding: '20px', borderRadius: '8px', border: '1px solid #ff7b72' }}>
              <h3 style={{ margin: '0 0 15px 0', color: '#ff7b72' }}>2. Live Performance Control</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                  <input type="checkbox" style={{ width: '20px', height: '20px' }} />
                  <span style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>Enable Strict Contextual Isolation (Performance Mode)</span>
                </label>
              </div>
              <p style={{ color: '#ffaaaa', marginTop: '10px', fontSize: '0.9rem' }}>
                ⚠️ Warning: When checked, the orchestrator routes all queries exclusively through the `theatrical_play_memory` ChromaDB collection. 
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
