import React from 'react';

export function SourcesDock({ sources, onToggleSource, onMoveUp, onMoveDown, onAddSource }) {
  return (
    <div className="sources-dock bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg p-3 text-white shadow-xl">
      <div className="flex justify-between items-center mb-3 pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <h3 className="text-xs uppercase font-black tracking-wider text-cyan-400">Sources ({sources.length})</h3>
        </div>
        <button 
          onClick={onAddSource} 
          className="px-2.5 py-1 bg-cyan-600 hover:bg-cyan-500 rounded text-xs font-bold text-white shadow-md shadow-cyan-500/20 transition-all cursor-pointer"
        >
          + Add Source
        </button>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {sources.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500 font-mono">No active sources in scene</div>
        ) : (
          sources.map((src, idx) => (
            <div 
              key={src.id || idx} 
              className={`flex items-center justify-between p-2.5 rounded border transition-all ${
                src.enabled 
                  ? 'bg-cyan-950/40 border-cyan-500/60 shadow-sm shadow-cyan-500/10 text-cyan-100' 
                  : 'bg-slate-800/30 border-slate-700/30 text-slate-400'
              }`}
            >
              <div className="flex items-center space-x-2.5 truncate">
                <input 
                  type="checkbox" 
                  checked={!!src.enabled} 
                  onChange={() => onToggleSource(src.id || idx)} 
                  className="accent-cyan-400 w-4 h-4 cursor-pointer rounded" 
                />
                <div className="truncate">
                  <div className="text-xs font-bold truncate">{src.name}</div>
                  <div className="text-[10px] text-slate-400 font-mono">Z-Index: {idx + 1}</div>
                </div>
              </div>

              <div className="flex items-center space-x-1">
                <button 
                  onClick={() => onMoveUp(idx)} 
                  disabled={idx === 0} 
                  className="px-2 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-20 rounded text-xs font-mono font-bold cursor-pointer transition-colors"
                  title="Move Layer Up"
                >
                  ▲
                </button>
                <button 
                  onClick={() => onMoveDown(idx)} 
                  disabled={idx === sources.length - 1} 
                  className="px-2 py-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-20 rounded text-xs font-mono font-bold cursor-pointer transition-colors"
                  title="Move Layer Down"
                >
                  ▼
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
