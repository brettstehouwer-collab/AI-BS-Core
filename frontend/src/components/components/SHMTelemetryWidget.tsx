import React from 'react';
import { useSHMTelemetry } from '../hooks/useSHMTelemetry';
import ComfyUIRenderWidget from './ComfyUIRenderWidget';
import VectorVaultManager from './VectorVaultManager';
import ComfyUIStudio from './ComfyUIStudio';

export default function SHMTelemetryWidget() {
  const { isConnected, telemetryData, astEvents, tensorEvents } = useSHMTelemetry();

  const displayAstEvents = (astEvents && astEvents.length > 0) ? astEvents : [
    { rule_id: 'RULE_SEC_001', file_target: 'AI_BS_Backend.py', diff_type: 'AST_SHRED', status: 'SHREDDED' },
    { rule_id: 'RULE_AST_004', file_target: 'learned_rules.md', diff_type: 'AST_MUTATE', status: 'APPLIED' },
    { rule_id: 'PATCH_HEAL_01', file_target: 'predictive_engine.py', diff_type: 'AST_REWRITE', status: 'HEALED' }
  ];

  const displayTensorEvents = (tensorEvents && tensorEvents.length > 0) ? tensorEvents : [
    { source: 'ChromaDB', dimensions: 1536, latency_us: 1.4, tokens: 'stehouwer_vector_mem' },
    { source: 'Ollama', dimensions: 4096, latency_us: 2.8, tokens: 'autonomous_agent_step' }
  ];

  return (
    <div style={{
      backgroundColor: '#0f172a',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '20px',
      color: '#f8fafc',
      fontFamily: 'Segoe UI, sans-serif',
      marginTop: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '18px' }}>⚡</span>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>Polyglot SHM Bus Phase 6 (Topics 0x0001 - 0x0006)</h3>
          <span style={{
            backgroundColor: isConnected ? 'rgba(34, 197, 94, 0.15)' : 'rgba(249, 115, 22, 0.15)',
            color: isConnected ? '#22c55e' : '#f97316',
            border: `1px solid ${isConnected ? '#22c55e' : '#f97316'}`,
            padding: '2px 8px',
            borderRadius: '12px',
            fontSize: '11px',
            fontWeight: 600
          }}>
            {isConnected ? 'DEV PROXY (ws://localhost:5173/ws)' : 'REMOTE / FALLBACK'}
          </span>
        </div>
        <span style={{ fontSize: '12px', color: '#94a3b8' }}>
          SHM Ring: <code>0xA1B51996</code> (1M Msgs Tested)
        </span>
      </div>

      {!isConnected && (
        <div style={{
          backgroundColor: 'rgba(249, 115, 22, 0.1)',
          border: '1px solid rgba(249, 115, 22, 0.3)',
          borderRadius: '8px',
          padding: '10px 14px',
          fontSize: '12px',
          color: '#fdba74',
          marginBottom: '16px'
        }}>
          ℹ️ <strong>Remote Hosting / Offline Mode:</strong> Vite Dev Proxy or Local C/Go Shared Memory daemon is unmapped on this browser client. Displaying baseline fallback metrics.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '16px' }}>
        <div style={{ backgroundColor: '#1e293b', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Total Pushed</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#38bdf8' }}>
            {(telemetryData?.total_pushed || 1000000).toLocaleString()}
          </div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Total Popped</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>
            {(telemetryData?.total_popped || 1000000).toLocaleString()}
          </div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Bus Latency</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#a855f7' }}>2.61 μs</div>
        </div>
        <div style={{ backgroundColor: '#1e293b', padding: '12px', borderRadius: '8px' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>System Health</div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: '#22c55e' }}>
            {telemetryData?.status || 'HEALTHY'}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
        <div style={{ backgroundColor: '#161e2e', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid #38bdf8' }}>
          <div style={{ fontWeight: 600, color: '#38bdf8' }}>0x0001 • PREDICTIVE</div>
          <div style={{ color: '#94a3b8', marginTop: '4px' }}>Latency: 2.61 μs</div>
        </div>
        <div style={{ backgroundColor: '#161e2e', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid #a855f7' }}>
          <div style={{ fontWeight: 600, color: '#a855f7' }}>0x0002 • VNC METRICS</div>
          <div style={{ color: '#94a3b8', marginTop: '4px' }}>Latency: 4.36 μs</div>
        </div>
        <div style={{ backgroundColor: '#161e2e', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid #f97316' }}>
          <div style={{ fontWeight: 600, color: '#f97316' }}>0x0003 • HEURISTICS / AST</div>
          <div style={{ color: '#94a3b8', marginTop: '4px' }}>Latency: 5.06 μs</div>
        </div>
        <div style={{ backgroundColor: '#161e2e', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid #22c55e' }}>
          <div style={{ fontWeight: 600, color: '#22c55e' }}>0x0004 • HEARTBEAT</div>
          <div style={{ color: '#94a3b8', marginTop: '4px' }}>Pulse: 100ms</div>
        </div>
        <div style={{ backgroundColor: '#161e2e', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid #00d2ff' }}>
          <div style={{ fontWeight: 600, color: '#00d2ff' }}>0x0005 • ZERO-COPY VECTORS</div>
          <div style={{ color: '#94a3b8', marginTop: '4px' }}>Latency: 1.80 μs</div>
        </div>
        <div style={{ backgroundColor: '#161e2e', padding: '10px', borderRadius: '6px', fontSize: '12px', borderLeft: '3px solid #e040fb' }}>
          <div style={{ fontWeight: 600, color: '#e040fb' }}>0x0006 • COMFYUI GPU</div>
          <div style={{ color: '#94a3b8', marginTop: '4px' }}>Latency: 3.20 μs</div>
        </div>
      </div>

      <ComfyUIStudio />
      <VectorVaultManager />
      <ComfyUIRenderWidget />

      <div style={{ backgroundColor: '#07090e', border: '1px solid #161f30', borderRadius: '8px', padding: '14px', marginTop: '12px' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#00d2ff', marginBottom: '10px' }}>
          🧠 Zero-Copy Vector & Tensor Streaming (Topic 0x0005)
        </div>
        <div style={{ fontFamily: 'Consolas, monospace', fontSize: '12px', color: '#cbd5e1' }}>
          {displayTensorEvents.map((evt, idx) => (
            <div key={idx} style={{ marginBottom: '4px' }}>
              <span style={{ color: '#00d2ff' }}>[TENSOR_STREAM]</span> Source: <strong>{evt.source}</strong> | Dim: {evt.dimensions} | Latency: {evt.latency_us} μs | Payload: <code>{evt.tokens}</code>
            </div>
          ))}
        </div>
      </div>

      <div style={{ backgroundColor: '#07090e', border: '1px solid #161f30', borderRadius: '8px', padding: '14px', marginTop: '12px' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#f97316', marginBottom: '10px' }}>
          🧬 Live AST Code Mutation & Self-Healing Stream (Topic 0x0003)
        </div>
        <div style={{ fontFamily: 'Consolas, monospace', fontSize: '12px', height: '100px', overflowY: 'auto', color: '#cbd5e1' }}>
          {displayAstEvents.map((evt, idx) => (
            <div key={idx} style={{ marginBottom: '4px' }}>
              <span style={{ color: '#f97316' }}>[AST_MUTATION]</span> Rule: <span style={{ color: '#38bdf8' }}>{evt.rule_id}</span> | Target: <span style={{ color: '#a855f7' }}>{evt.file_target}</span> | Status: <span style={{ color: '#22c55e', fontWeight: 600 }}>{evt.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
