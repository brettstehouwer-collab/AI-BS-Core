import React from 'react';

export function AudioMixerDock({ tracks = [], onSetVolume, onToggleMute, onToggleSolo }) {
  return (
    <div className="audio-mixer-dock bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg p-3 text-white shadow-xl">
      <div className="flex justify-between items-center mb-3 pb-2 border-b border-slate-800">
        <h3 className="text-xs uppercase font-black tracking-wider text-cyan-400">6-Track 48kHz Stem Mixer</h3>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
          DSP Peak Limiter: ON (-0.1 dBFS)
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
        {tracks.map((t) => {
          const volPct = Math.round(t.volume * 100);
          return (
            <div 
              key={t.id} 
              className={`border rounded p-2.5 flex flex-col items-center justify-between transition-all ${
                t.muted 
                  ? 'bg-red-950/10 border-red-900/40 opacity-75' 
                  : t.solo 
                  ? 'bg-yellow-950/20 border-yellow-500/50' 
                  : 'bg-slate-800/50 border-slate-700/60'
              }`}
            >
              <span className="text-[11px] font-bold text-slate-200 text-center truncate w-full mb-2">
                {t.name}
              </span>

              {/* Fader & VU Meter Layout */}
              <div className="flex items-center space-x-2 my-2">
                <input 
                  type="range" 
                  min="0" 
                  max="1" 
                  step="0.01" 
                  value={t.volume} 
                  onChange={(e) => onSetVolume(t.id, parseFloat(e.target.value))} 
                  className="h-28 w-2 accent-cyan-400 cursor-pointer" 
                  style={{ writingMode: 'vertical-lr', direction: 'rtl' }} 
                />
                
                {/* Visual Level Meter Bar */}
                <div className="w-2 h-28 bg-slate-950 rounded-full overflow-hidden flex flex-col justify-end p-0.5 border border-slate-800">
                  <div 
                    style={{ height: `${t.muted ? 0 : volPct}%` }} 
                    className={`w-full rounded-full transition-all duration-75 ${
                      volPct > 90 ? 'bg-red-500' : volPct > 75 ? 'bg-yellow-400' : 'bg-emerald-400'
                    }`} 
                  />
                </div>
              </div>

              <span className="text-[10px] font-mono text-cyan-300 font-semibold mb-2">
                {t.muted ? 'MUTED' : `${volPct}%`}
              </span>

              {/* Mute & Solo Toggles */}
              <div className="flex space-x-1 w-full justify-center">
                <button 
                  onClick={() => onToggleMute(t.id)} 
                  className={`flex-1 py-1 rounded text-[10px] font-black cursor-pointer transition-colors ${
                    t.muted ? 'bg-red-600 text-white' : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  }`}
                >
                  M
                </button>
                <button 
                  onClick={() => onToggleSolo(t.id)} 
                  className={`flex-1 py-1 rounded text-[10px] font-black cursor-pointer transition-colors ${
                    t.solo ? 'bg-yellow-500 text-black' : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  }`}
                >
                  S
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
