import 'react';
import { useSHMTelemetry } from '/src/hooks/useSHMTelemetry';

export default function ComfyUIRenderWidget() {
  const { gpuStats } = useSHMTelemetry();

  if (!gpuStats) return (
    <section role="status" aria-label="ComfyUI render telemetry" style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: 8, padding: 16, marginTop: 12, color: '#f0f6fc' }}>
      <h4>ComfyUI render telemetry</h4>
      <p>GPU telemetry: Unavailable. No verified GPU frame is connected.</p>
      <p>Frame rate: Unavailable · Active model: Unavailable · Render progress: Unavailable · VRAM: Unavailable</p>
    </section>
  );
  const vramPercent = gpuStats.vram_total_mb > 0 ? Math.min(100, Math.max(0, Math.round((gpuStats.vram_used_mb / gpuStats.vram_total_mb) * 100))) : null;
  const stepPercent = gpuStats.total_steps > 0 ? Math.min(100, Math.max(0, Math.round((gpuStats.step / gpuStats.total_steps) * 100))) : null;

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
          🎨 ComfyUI Render Telemetry & GPU VRAM
        </h4>
        <span style={{ fontSize: '12px', color: '#7ee787', fontWeight: 600 }}>
          {gpuStats.fps} FPS
        </span>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>
          <span>Active Model: <strong>{gpuStats.model || 'Unavailable'}</strong></span>
          <span>Step: {gpuStats.step} / {gpuStats.total_steps} ({stepPercent === null ? 'Unavailable' : `${stepPercent}%`})</span>
        </div>
        <div aria-label={stepPercent === null ? 'Render progress unavailable' : `Render progress ${stepPercent}%`} style={{ background: '#21262d', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
          {stepPercent !== null && <div style={{ background: 'linear-gradient(90deg, #a855f7, #38bdf8)', height: '100%', width: `${stepPercent}%` }}></div>}
        </div>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>
          <span>GPU VRAM allocation</span>
          <span>{gpuStats.vram_used_mb.toLocaleString()} MB / {gpuStats.vram_total_mb.toLocaleString()} MB ({vramPercent === null ? 'Unavailable' : `${vramPercent}%`})</span>
        </div>
        <div style={{ background: '#21262d', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
          {vramPercent !== null && <div style={{ background: vramPercent > 85 ? '#f97316' : '#22c55e', height: '100%', width: `${vramPercent}%` }}></div>}
        </div>
      </div>
    </div>
  );
}
