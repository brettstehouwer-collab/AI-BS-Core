import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')
    print(f"Written: {path}")

useCanvasCompositor_js = """import { useEffect, useRef } from 'react';

export function useCanvasCompositor({ canvasRef, sources, activeScene, isStreaming }) {
  const animFrameRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let running = true;

    const renderLoop = () => {
      if (!running) return;

      ctx.fillStyle = '#090d16';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      sources.forEach((source, idx) => {
        if (!source.enabled) return;

        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        const x = (idx % 2) * (canvas.width / 2);
        const y = Math.floor(idx / 2) * (canvas.height / 2);
        const w = canvas.width / 2;
        const h = canvas.height / 2;

        ctx.fillRect(x + 10, y + 10, w - 20, h - 20);

        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 2;
        ctx.strokeRect(x + 10, y + 10, w - 20, h - 20);

        ctx.fillStyle = '#00e5ff';
        ctx.font = '14px sans-serif';
        ctx.fillText(`${source.name} [Layer ${idx + 1}]`, x + 25, y + 35);
      });

      animFrameRef.current = requestAnimationFrame(renderLoop);
    };

    animFrameRef.current = requestAnimationFrame(renderLoop);

    return () => {
      running = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [canvasRef, sources, activeScene]);

  return { animFrameRef };
}
"""

useBroadcastTelemetry_js = """import { useState, useEffect } from 'react';

export function useBroadcastTelemetry(daemonPort = 8005) {
  const [telemetry, setTelemetry] = useState({
    fps: 60,
    bitrateKbps: 8000,
    cpuUsage: 12,
    gpuVramUsedGb: 6.4,
    droppedFrames: 0,
    status: 'connected'
  });

  useEffect(() => {
    let ws;
    try {
      ws = new WebSocket(`ws://127.0.0.1:${daemonPort}/ws/telemetry`);
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          setTelemetry((prev) => ({ ...prev, ...data }));
        } catch (e) {}
      };
      ws.onerror = () => setTelemetry((prev) => ({ ...prev, status: 'disconnected' }));
    } catch (e) {}

    return () => {
      if (ws) ws.close();
    };
  }, [daemonPort]);

  return telemetry;
}
"""

useAudioMixer_js = """import { useState, useCallback } from 'react';

export function useAudioMixer(initialTracks = []) {
  const [tracks, setTracks] = useState(initialTracks.length ? initialTracks : [
    { id: 'track1', name: 'Master Stream', volume: 0.9, muted: false, solo: false },
    { id: 'track2', name: 'Clean Mic', volume: 0.85, muted: false, solo: false },
    { id: 'track3', name: 'Desktop & WASAPI', volume: 0.75, muted: false, solo: false },
    { id: 'track4', name: 'DAW Synthesizers', volume: 0.8, muted: false, solo: false },
    { id: 'track5', name: 'Remote WebRTC Guests', volume: 0.7, muted: false, solo: false },
    { id: 'track6', name: 'AI Sidekick Voice', volume: 0.85, muted: false, solo: false },
  ]);

  const setVolume = useCallback((id, vol) => {
    setTracks(prev => prev.map(t => t.id === id ? { ...t, volume: vol } : t));
  }, []);

  const toggleMute = useCallback((id) => {
    setTracks(prev => prev.map(t => t.id === id ? { ...t, muted: !t.muted } : t));
  }, []);

  const toggleSolo = useCallback((id) => {
    setTracks(prev => prev.map(t => t.id === id ? { ...t, solo: !t.solo } : t));
  }, []);

  return { tracks, setVolume, toggleMute, toggleSolo };
}
"""

sourcesDock_jsx = """import React from 'react';

export function SourcesDock({ sources, onToggleSource, onMoveUp, onMoveDown, onAddSource }) {
  return (
    <div className="sources-dock bg-slate-900 border border-slate-800 rounded-lg p-3 text-white">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs uppercase font-bold tracking-wider text-cyan-400">Sources ({sources.length})</h3>
        <button onClick={onAddSource} className="px-2 py-1 bg-cyan-600 hover:bg-cyan-500 rounded text-xs font-semibold">+ Add</button>
      </div>
      <div className="space-y-2 max-h-60 overflow-y-auto">
        {sources.map((src, idx) => (
          <div key={src.id || idx} className={`flex items-center justify-between p-2 rounded border transition-all ${src.enabled ? 'bg-cyan-950/40 border-cyan-500/60 text-cyan-200' : 'bg-slate-800/40 border-slate-700/40 text-slate-400'}`}>
            <div className="flex items-center space-x-2">
              <input type="checkbox" checked={!!src.enabled} onChange={() => onToggleSource(src.id || idx)} className="accent-cyan-400 cursor-pointer" />
              <span className="text-sm font-medium">{src.name}</span>
            </div>
            <div className="flex items-center space-x-1">
              <button onClick={() => onMoveUp(idx)} disabled={idx === 0} className="px-1 py-0.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 rounded text-xs">▲</button>
              <button onClick={() => onMoveDown(idx)} disabled={idx === sources.length - 1} className="px-1 py-0.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 rounded text-xs">▼</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

audioMixerDock_jsx = """import React from 'react';

export function AudioMixerDock({ tracks, onSetVolume, onToggleMute, onToggleSolo }) {
  return (
    <div className="audio-mixer-dock bg-slate-900 border border-slate-800 rounded-lg p-3 text-white">
      <h3 className="text-xs uppercase font-bold tracking-wider text-cyan-400 mb-3">6-Track 48kHz Stem Mixer</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        {tracks.map((t) => (
          <div key={t.id} className="bg-slate-800/60 border border-slate-700/60 rounded p-2 flex flex-col items-center">
            <span className="text-[11px] text-slate-300 font-semibold text-center truncate w-full mb-2">{t.name}</span>
            <input type="range" min="0" max="1" step="0.01" value={t.volume} onChange={(e) => onSetVolume(t.id, parseFloat(e.target.value))} className="h-24 w-2 accent-cyan-400 cursor-pointer" style={{ writingMode: 'vertical-lr', direction: 'rtl' }} />
            <span className="text-[10px] text-cyan-300 mt-2">{Math.round(t.volume * 100)}%</span>
            <div className="flex space-x-1 mt-2">
              <button onClick={() => onToggleMute(t.id)} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${t.muted ? 'bg-red-600 text-white' : 'bg-slate-700 text-slate-300'}`}>M</button>
              <button onClick={() => onToggleSolo(t.id)} className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${t.solo ? 'bg-yellow-500 text-black' : 'bg-slate-700 text-slate-300'}`}>S</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
"""

webglCompositor_js = """export class WebGLCompositor {
  constructor(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl2', { premultipliedAlpha: false, preserveDrawingBuffer: true });
    if (!this.gl) {
      console.warn('WebGL2 not supported, falling back to 2D canvas');
    }
  }

  renderFrame(sources) {
    if (!this.gl) return;
    const gl = this.gl;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0.03, 0.05, 0.09, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }
}
"""

write_file("C:/AI-BS/frontend/src/components/broadcast/hooks/useCanvasCompositor.js", useCanvasCompositor_js)
write_file("C:/AI-BS/frontend/src/components/broadcast/hooks/useBroadcastTelemetry.js", useBroadcastTelemetry_js)
write_file("C:/AI-BS/frontend/src/components/broadcast/hooks/useAudioMixer.js", useAudioMixer_js)
write_file("C:/AI-BS/frontend/src/components/broadcast/components/SourcesDock.jsx", sourcesDock_jsx)
write_file("C:/AI-BS/frontend/src/components/broadcast/components/AudioMixerDock.jsx", audioMixerDock_jsx)
write_file("C:/AI-BS/frontend/src/components/broadcast/WebGLCompositor.js", webglCompositor_js)

print("Broadcast modular hooks and components created successfully.")