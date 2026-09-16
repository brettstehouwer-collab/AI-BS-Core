import React from 'react';
import { useSHMTelemetry } from '../hooks/useSHMTelemetry';

export default function ComfyUIRenderWidget() {
  const { gpuStats } = useSHMTelemetry();

  const vramPercent = Math.round((gpuStats.vram_used_mb / gpuStats.vram_total_mb) * 100);
  const stepPercent = Math.round((gpuStats.step / gpuStats.total_steps) * 100);

  return (
    <div style={{
      backgroundColor: '#0d1117',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '16px',
      color: '#f0f6fc',
      marginTop: '12px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, color: '#a855f7', fontSize: '14px' }}>
          🎨 ComfyUI Render Telemetry & RTX 4090 VRAM (Topic 0x0006)
        </h4>
        <span style={{ fontSize: '12px', color: '#7ee787', fontWeight: 600 }}>
          {gpuStats.fps} FPS
        </span>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>
          <span>Active Model: <strong>{gpuStats.model}</strong></span>
          <span>Step: {gpuStats.step} / {gpuStats.total_steps} ({stepPercent}%)</span>
        </div>
        <div style={{ background: '#21262d', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
          <div style={{ background: 'linear-gradient(90deg, #a855f7, #38bdf8)', height: '100%', width: `${stepPercent}%` }}></div>
        </div>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>
          <span>RTX 4090 VRAM Allocation</span>
          <span>{gpuStats.vram_used_mb.toLocaleString()} MB / {gpuStats.vram_total_mb.toLocaleString()} MB ({vramPercent}%)</span>
        </div>
        <div style={{ background: '#21262d', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
          <div style={{ background: vramPercent > 85 ? '#f97316' : '#22c55e', height: '100%', width: `${vramPercent}%` }}></div>
        </div>
      </div>
    </div>
  );
}
