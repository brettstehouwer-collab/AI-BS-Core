import React, { useState, useEffect } from 'react';

export function VRAMTelemetryWidget() {
  const [vram, setVram] = useState({
    totalGb: 24.0,
    usedGb: 6.4,
    freeGb: 17.6,
    ollamaGb: 4.8,
    comfyGb: 0.0,
    nvencGb: 1.6
  });

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://127.0.0.1:8080/api/system/health');
        if (res.ok) {
          const data = await res.json();
        }
      } catch (e) {}
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const usedPct = Math.round((vram.usedGb / vram.totalGb) * 100);

  return (
    <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-300">
      <span className="font-bold text-cyan-400">RTX 4090 VRAM:</span>
      <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden flex">
        <div style={{ width: `${(vram.ollamaGb / vram.totalGb) * 100}%` }} className="bg-purple-500 h-full" title="Ollama" />
        <div style={{ width: `${(vram.comfyGb / vram.totalGb) * 100}%` }} className="bg-pink-500 h-full" title="ComfyUI" />
        <div style={{ width: `${(vram.nvencGb / vram.totalGb) * 100}%` }} className="bg-cyan-400 h-full" title="NVENC" />
      </div>
      <span className="font-mono font-semibold text-slate-200">{vram.usedGb.toFixed(1)} / {vram.totalGb.toFixed(0)} GB ({usedPct}%)</span>
    </div>
  );
}
