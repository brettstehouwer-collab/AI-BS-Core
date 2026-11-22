import re

file_path = r"C:\AI-BS\frontend\src\components\daw\StehouwerWaveStudio.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add formatMusicalBar after formatPrecisionTime
target_fn = """// Format seconds into Stehouwer Precision Timecode: 00:00.000
function formatPrecisionTime(seconds) {
  if (isNaN(seconds) || seconds < 0) seconds = 0;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const millis = Math.floor((seconds - Math.floor(seconds)) * 1000);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(millis).padStart(3, '0')}`;
}"""

replacement_fn = """// Format seconds into Stehouwer Precision Timecode: 00:00.000
function formatPrecisionTime(seconds) {
  if (isNaN(seconds) || seconds < 0) seconds = 0;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const millis = Math.floor((seconds - Math.floor(seconds)) * 1000);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(millis).padStart(3, '0')}`;
}

// Format seconds into Musical Bar / Beat timecode at given BPM: 034.2.2
function formatMusicalBar(seconds, bpm = 85) {
  if (isNaN(seconds) || seconds < 0) return '001.1.1';
  const totalBeats = seconds * (bpm / 60);
  const bar = Math.floor(totalBeats / 4) + 1;
  const beat = Math.floor(totalBeats % 4) + 1;
  const subBeat = Math.floor((totalBeats % 1) * 4) + 1;
  return `${String(bar).padStart(3, '0')}.${beat}.${subBeat}`;
}"""

content = content.replace(target_fn, replacement_fn, 1)

# 2. Add bpm, rulerMode, latencyOffsetMs state
target_state = """  // Transport & Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [playheadTime, setPlayheadTime] = useState(0);
  const [selection, setSelection] = useState({ start: 0, end: 0, active: false });
  const [clipboard, setClipboard] = useState(null);"""

replacement_state = """  // Transport & Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [playheadTime, setPlayheadTime] = useState(0);
  const [selection, setSelection] = useState({ start: 0, end: 0, active: false });
  const [clipboard, setClipboard] = useState(null);
  const [bpm, setBpm] = useState(85);
  const [rulerMode, setRulerMode] = useState('musical'); // 'musical' | 'timecode'
  const [latencyOffsetMs, setLatencyOffsetMs] = useState(0);"""

content = content.replace(target_state, replacement_state, 1)

# 3. Add BPM controller and ruler toggle in transport before Zoom Controls
target_zoom = """        {/* Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>"""

replacement_zoom = """        {/* BPM & Timing Sync */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#090d16', border: '1px solid #1e293b', borderRadius: '4px', padding: '2px 8px', marginLeft: 'auto' }}>
          <span style={{ fontSize: '9px', color: '#94a3b8', fontWeight: 'bold' }}>TEMPO</span>
          <input
            type="number"
            min="40"
            max="240"
            value={bpm}
            onChange={(e) => setBpm(Math.max(40, Math.min(240, Number(e.target.value))))}
            style={{ width: '38px', background: '#1e293b', border: '1px solid #334155', color: '#38bdf8', fontSize: '11px', fontWeight: 'bold', padding: '2px 4px', borderRadius: '3px', textAlign: 'center' }}
          />
          <button
            onClick={() => setBpm(85)}
            title="Lock project tempo to 85 BPM (Suno October 7v2 Native Timing)"
            style={{
              background: bpm === 85 ? 'rgba(56, 189, 248, 0.25)' : '#1e293b',
              border: bpm === 85 ? '1px solid #38bdf8' : '1px solid #334155',
              color: bpm === 85 ? '#38bdf8' : '#94a3b8',
              borderRadius: '3px',
              padding: '2px 5px',
              fontSize: '9px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            85 Suno
          </button>

          <div style={{ height: '14px', width: '1px', background: '#1e293b' }} />

          {/* Ruler Mode Toggle */}
          <button
            onClick={() => setRulerMode(prev => prev === 'musical' ? 'timecode' : 'musical')}
            title="Toggle between Musical Bars (85 BPM) and Seconds Timecode"
            style={{
              background: rulerMode === 'musical' ? 'rgba(168, 85, 247, 0.2)' : '#1e293b',
              border: rulerMode === 'musical' ? '1px solid #a855f7' : '1px solid #334155',
              color: rulerMode === 'musical' ? '#c084fc' : '#94a3b8',
              borderRadius: '3px',
              padding: '2px 6px',
              fontSize: '9px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            {rulerMode === 'musical' ? '🎼 Musical Bars' : '⏱ Timecode'}
          </button>
        </div>

        {/* Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>"""

content = content.replace(target_zoom, replacement_zoom, 1)

# 4. Update Time Telemetry Bar with Musical Bar readout
target_telemetry = """      {/* 3. TIME TELEMETRY BAR */}
      <div style={{
        background: '#090d16',
        borderBottom: '1px solid #1e293b',
        padding: '3px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        fontSize: '11px',
        color: '#94a3b8'
      }}>
        <div>
          Playhead: <span style={{ color: '#38bdf8', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(playheadTime)}</span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Selection In: <span style={{ color: '#facc15', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(selection.start)}</span>
        </div>
        <div>
          Selection Length: <span style={{ color: '#facc15', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(selection.end - selection.start)}</span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Stehouwer Engine: <span style={{ color: '#fff', fontWeight: 'bold' }}>44.1 kHz • 32-bit Float</span>
        </div>
      </div>"""

replacement_telemetry = """      {/* 3. TIME TELEMETRY BAR */}
      <div style={{
        background: '#090d16',
        borderBottom: '1px solid #1e293b',
        padding: '3px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        fontSize: '11px',
        color: '#94a3b8',
        flexWrap: 'wrap'
      }}>
        <div>
          Playhead: <span style={{ color: '#38bdf8', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(playheadTime)}</span>
          <span style={{ color: '#c084fc', fontFamily: 'monospace', fontWeight: 'bold', marginLeft: '6px' }}>
            [{formatMusicalBar(playheadTime, bpm)}]
          </span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Selection In: <span style={{ color: '#facc15', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(selection.start)}</span>
          <span style={{ color: '#eab308', fontFamily: 'monospace', fontSize: '10px', marginLeft: '4px' }}>
            [{formatMusicalBar(selection.start, bpm)}]
          </span>
        </div>
        <div>
          Selection Length: <span style={{ color: '#facc15', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(selection.end - selection.start)}</span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Tempo: <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>{bpm} BPM (4/4)</span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Stehouwer Engine: <span style={{ color: '#fff', fontWeight: 'bold' }}>44.1 kHz • 32-bit Float</span>
        </div>
      </div>"""

content = content.replace(target_telemetry, replacement_telemetry, 1)

# 5. Update Time Ruler to render Musical Bars & Beats or Timecode
target_ruler = """          {/* Time Ruler */}
          <div style={{
            width: `${Math.max(1200, projectDuration * pixelsPerSecond + 400)}px`,
            position: 'relative',
            height: '100%'
          }}>
            {Array.from({ length: Math.ceil(projectDuration + 10) }).map((_, sec) => (
              <div 
                key={sec} 
                style={{
                  position: 'absolute',
                  left: `${sec * pixelsPerSecond}px`,
                  top: 0,
                  height: '100%',
                  borderLeft: '1px solid #334155',
                  paddingLeft: '4px',
                  fontSize: '9px',
                  color: '#94a3b8',
                  fontFamily: 'monospace'
                }}
              >
                {formatPrecisionTime(sec).substring(0, 5)}
              </div>
            ))}"""

replacement_ruler = """          {/* Time Ruler */}
          <div style={{
            width: `${Math.max(1200, projectDuration * pixelsPerSecond + 400)}px`,
            position: 'relative',
            height: '100%'
          }}>
            {rulerMode === 'musical' ? (
              // Musical Bars (85 BPM Suno Timing)
              (() => {
                const secPerBar = 4 * (60 / bpm);
                const totalBars = Math.ceil(projectDuration / secPerBar) + 5;
                return Array.from({ length: totalBars }).map((_, b) => {
                  const barNum = b + 1;
                  const barTime = b * secPerBar;
                  const leftPx = barTime * pixelsPerSecond;
                  const isMajor = barNum === 1 || barNum % 8 === 1;
                  return (
                    <div 
                      key={`bar_${barNum}`} 
                      style={{
                        position: 'absolute',
                        left: `${leftPx}px`,
                        top: 0,
                        height: '100%',
                        borderLeft: isMajor ? '2px solid #38bdf8' : '1px solid #334155',
                        paddingLeft: '3px',
                        fontSize: '9px',
                        color: isMajor ? '#38bdf8' : '#94a3b8',
                        fontWeight: isMajor ? 'bold' : 'normal',
                        fontFamily: 'monospace'
                      }}
                    >
                      {barNum}
                    </div>
                  );
                });
              })()
            ) : (
              // Seconds Timecode
              Array.from({ length: Math.ceil(projectDuration + 10) }).map((_, sec) => (
                <div 
                  key={sec} 
                  style={{
                    position: 'absolute',
                    left: `${sec * pixelsPerSecond}px`,
                    top: 0,
                    height: '100%',
                    borderLeft: '1px solid #334155',
                    paddingLeft: '4px',
                    fontSize: '9px',
                    color: '#94a3b8',
                    fontFamily: 'monospace'
                  }}
                >
                  {formatPrecisionTime(sec).substring(0, 5)}
                </div>
              ))
            )}"""

content = content.replace(target_ruler, replacement_ruler, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("StehouwerWaveStudio.jsx successfully updated with Musical Bars, 85 BPM Suno sync, and dual timecode!")
