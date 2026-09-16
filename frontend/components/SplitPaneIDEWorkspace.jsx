import React, { useState } from 'react';
import ChatToolControlBar from './ChatToolControlBar';
import ChatTab from './ChatTab';
import VisualScriptingTab from './VisualScriptingTab';
import BullshitTelemetrySuite from '../src/BullshitTelemetrySuite';
import BullshitKnowledgeSuite from '../src/BullshitKnowledgeSuite';

export default function SplitPaneIDEWorkspace() {
  const [activeRightTab, setActiveRightTab] = useState('shm_telemetry');
  const [showRightPane, setShowRightPane] = useState(false);

  return (
    <div className="w-full h-full flex flex-col box-border" style={{
      display: 'grid',
      gridTemplateColumns: showRightPane ? 'repeat(auto-fit, minmax(400px, 1fr))' : '1fr',
      gap: 0,
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', color: '#58a6ff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>💬</span> AI-BS Autonomous Agentic IDE Chat
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '11px', color: '#7ee787' }}>● {showRightPane ? 'Split-Pane Active' : 'Single-Pane Active'} (Phase 7 Sandbox)</span>
            <button
              onClick={() => setShowRightPane(!showRightPane)}
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '11px'
              }}
            >
              ↔ Toggle Split View
            </button>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', backgroundColor: '#0d1117', borderRadius: '6px', border: '1px solid #30363d' }}>
          {/* Primary Chat Interface Injected into Left Pane */}
          <ChatTab isNested={true} />
        </div>
      </div>

      {/* RIGHT PANE: Dynamic Workspaces */}
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
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', borderBottom: '1px solid #30363d', paddingBottom: '8px' }}>
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

          <div style={{ flex: 1, overflowY: 'auto', backgroundColor: '#0d1117', padding: '12px', borderRadius: '6px', border: '1px solid #30363d' }}>
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
