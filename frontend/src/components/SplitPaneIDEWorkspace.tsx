import React from 'react';
import ChatTab from '../../components/ChatTab';
import WebGLRenderBridge from './WebGLRenderBridge';
import ChatToolControlBar from './ChatToolControlBar';

export default function SplitPaneIDEWorkspace() {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '12px',
      height: 'calc(100vh - 80px)',
      padding: '12px',
      backgroundColor: '#0d1117',
      boxSizing: 'border-box'
    }}>
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
          <span style={{ fontSize: '11px', color: '#7ee787' }}>● Split-Pane Active</span>
        </div>

        <ChatToolControlBar />

        <div style={{ flex: 1, overflowY: 'auto' }}>
          <ChatTab />
        </div>
      </div>

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
          <h3 style={{ margin: 0, fontSize: '14px', color: '#e040fb', display: 'flex', alignItems: 'center', gap: '8px' }}>
            🎮 3D WebGL Bridge
          </h3>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          <div>
            <WebGLRenderBridge />
            <div style={{ marginTop: '16px', backgroundColor: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
              <h4 style={{ margin: '0 0 8px 0', color: '#e040fb', fontSize: '13px' }}>🧬 Node-Graph to AST Compiler Output</h4>
              <pre style={{ backgroundColor: '#161b22', padding: '10px', borderRadius: '4px', color: '#7ee787', fontSize: '11px' }}>
{`// Compiled Visual Script AST
def execute_node_1():
    print('[AST Node 1] Live Telemetry query...')
    return {'cpu_percent': 12.5, 'vram_mb': 18432}

def execute_node_2():
    print('[AST Node 2] WebGL 3D Render Frame...')
    return {'fps': 60, 'frame_buffer': '0x8A9B'}`}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
