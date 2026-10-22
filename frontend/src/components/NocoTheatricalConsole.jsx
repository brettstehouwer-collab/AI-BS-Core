import React, { useState, useEffect } from 'react';

export default function NocoTheatricalConsole() {
  // Master Production Mode
  const [productionMode, setProductionMode] = useState('PERFORMANCE'); // 'PERFORMANCE', 'REHEARSAL', 'INTERMISSION', 'STANDBY', 'BLACKOUT', 'ESTOP'
  
  // DMX Lighting State
  const [activeLightingPreset, setActiveLightingPreset] = useState('sunset');
  const [masterDimmer, setMasterDimmer] = useState(85);
  const [colorTemp, setColorTemp] = useState(2800); // 2200K - 6500K
  const [hazeDensity, setHazeDensity] = useState(35); // 0 - 100%
  const [growLightBlend, setGrowLightBlend] = useState(true);
  const [movingHeadSpeed, setMovingHeadSpeed] = useState(50);

  // Audio Telemetry & VU Meters
  const [leftVu, setLeftVu] = useState(72);
  const [rightVu, setRightVu] = useState(75);
  const [cardioidRejectionDb, setCardioidRejectionDb] = useState(18.5); // dB rear attenuation
  const [isSubwooferCardioid, setIsSubwooferCardioid] = useState(true);
  const [selectedMicChannel, setSelectedMicChannel] = useState('mic1');

  // Teleprompter & Setlist State
  const [activeSongIndex, setActiveSongIndex] = useState(0);
  const [isPrompterScrolling, setIsPrompterScrolling] = useState(false);
  const [prompterSpeed, setPrompterSpeed] = useState(3);
  const [prompterFontSize, setPrompterFontSize] = useState(22);
  const [isMirroredPrompter, setIsMirroredPrompter] = useState(false);
  const [scrollOffset, setScrollOffset] = useState(0);

  // Setlist Songs
  const setlist = [
    {
      title: "01. Finger Lakes Dusk (Opening Acoustic)",
      key: "G Major",
      tempo: "78 BPM",
      lyrics: `[Intro - Fingerpicked Acoustic Guitar & Living Greenhouse Reverb]
(G) - (Cadd9) - (Em7) - (D/F#)

[Verse 1]
Dusk is settling down across Lammerson Lane
Sunlight angles through the polycarbonate pane
The Fraser firs are whispering in the evening breeze
Forty-five miles of quiet in the cedar trees

[Chorus]
Welcome to the Living Stage tonight
Lettuce growing tall beneath the purple light
Acoustic resonance in earth and stone
Where the wild and the sovereign call home...`
    },
    {
      title: "02. The Living Stage (Full Band Groove)",
      key: "D Minor",
      tempo: "105 BPM",
      lyrics: `[Intro - Cardioid Bass Pulse & Analog Synthesizer]
(Dm) - (Bb) - (F) - (C)

[Verse 1]
Root-roof wisteria catching every frequency
Five-degree tilt on the smart-glass sea
Microbial fuel cells humming in the dark
Bio-mass energy igniting the spark

[Chorus]
This is the stage that breathes, this is the stage that grows
Sound waves rippling through the aeroponic rows
Hear the subwoofers phase, hear the harmony rise
Underneath the Ithaca midnight skies...`
    },
    {
      title: "03. Harvest Moon Echoes (Cello & Vocal)",
      key: "A Minor",
      tempo: "64 BPM",
      lyrics: `[Intro - Valais Sheep Pasture Ambient Sounds & Cello Solo]
(Am) - (Em) - (F) - (G)

[Verse 1]
The fire pit is crackling in concentric stone
Artist residency voices far away from home
We broke the mold, we broke the grid
Found the quiet frequency that the machine hid...`
    }
  ];

  // Auto-scroll simulation for teleprompter
  useEffect(() => {
    let interval;
    if (isPrompterScrolling) {
      interval = setInterval(() => {
        setScrollOffset(prev => prev + prompterSpeed * 0.8);
      }, 50);
    }
    return () => clearInterval(interval);
  }, [isPrompterScrolling, prompterSpeed]);

  // Audio VU Meter dynamic jitter simulation
  useEffect(() => {
    const vuInterval = setInterval(() => {
      if (productionMode === 'PERFORMANCE' || productionMode === 'REHEARSAL') {
        setLeftVu(Math.floor(65 + Math.random() * 25));
        setRightVu(Math.floor(68 + Math.random() * 26));
      } else {
        setLeftVu(5);
        setRightVu(5);
      }
    }, 150);
    return () => clearInterval(vuInterval);
  }, [productionMode]);

  const lightingPresets = {
    sunset: { name: '🌅 Warm Acoustic Sunset', temp: 2400, dim: 75, haze: 20, color: '#f59e0b' },
    cyberpunk: { name: '🌌 Cyberpunk Neon Violet', temp: 5600, dim: 90, haze: 65, color: '#c084fc' },
    emerald: { name: '🌿 Living Greenhouse Emerald', temp: 4000, dim: 70, haze: 30, color: '#10b981' },
    pulse: { name: '⚡ Dynamic Beat Strobe', temp: 6500, dim: 100, haze: 80, color: '#00ffff' },
    spotlight: { name: '🎭 Dramatic Key Spotlight', temp: 3200, dim: 85, haze: 15, color: '#f8fafc' }
  };

  const applyPreset = (key) => {
    setActiveLightingPreset(key);
    const p = lightingPresets[key];
    if (p) {
      setColorTemp(p.temp);
      setMasterDimmer(p.dim);
      setHazeDensity(p.haze);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      
      {/* 1. Master Production Mode Control Bar */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.9)',
        border: '1px solid rgba(0, 255, 255, 0.25)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.4rem' }}>🎛️</span>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#00FFFF', fontWeight: 800 }}>
              Theatrical Production &amp; Wireless DMX 512 Console
            </h3>
            <span style={{
              background: productionMode === 'PERFORMANCE' ? '#15803d' : productionMode === 'ESTOP' ? '#dc2626' : '#64748b',
              color: '#ffffff',
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 800
            }}>
              MODE: {productionMode}
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
            Living Stage Digital Patchbay &bull; Front of House (FOH) Gateway Operated by Sean Stehouwer
          </p>
        </div>

        {/* Master State Buttons */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { id: 'PERFORMANCE', label: '🎭 LIVE PERFORMANCE', bg: '#10b981' },
            { id: 'REHEARSAL', label: '🎼 DRESS REHEARSAL', bg: '#38bdf8' },
            { id: 'INTERMISSION', label: '☕ INTERMISSION', bg: '#f59e0b' },
            { id: 'BLACKOUT', label: '🌑 BLACKOUT', bg: '#334155' },
            { id: 'ESTOP', label: '🛑 EMERGENCY E-STOP', bg: '#ef4444' }
          ].map(btn => (
            <button
              key={btn.id}
              onClick={() => setProductionMode(btn.id)}
              style={{
                background: productionMode === btn.id ? btn.bg : 'rgba(255, 255, 255, 0.05)',
                color: productionMode === btn.id ? '#ffffff' : '#94a3b8',
                border: `1px solid ${productionMode === btn.id ? btn.bg : 'rgba(255, 255, 255, 0.15)'}`,
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Middle Grid: Lighting Rack + Audio VU Telemetry */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.3fr) minmax(320px, 1fr)', gap: '20px' }}>
        
        {/* DMX 512 Lighting Rack */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.3)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
              💡 Wireless DMX 512 Stage Lighting Rack
            </h4>
            <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>● DMX Universe 1 Online (512/512 Ch)</span>
          </div>

          {/* Quick Presets */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', marginBottom: '16px' }}>
            {Object.keys(lightingPresets).map(key => (
              <button
                key={key}
                onClick={() => applyPreset(key)}
                style={{
                  background: activeLightingPreset === key ? 'rgba(0, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.4)',
                  border: `1px solid ${activeLightingPreset === key ? '#00FFFF' : 'rgba(255, 255, 255, 0.1)'}`,
                  color: activeLightingPreset === key ? '#00FFFF' : '#cbd5e1',
                  borderRadius: '6px',
                  padding: '8px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
              >
                {lightingPresets[key].name}
              </button>
            ))}
          </div>

          {/* Master Faders */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '8px' }}>
            
            {/* Master Dimmer */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Master Stage Dimmer:</span>
                <strong style={{ color: '#00FFFF' }}>{masterDimmer}%</strong>
              </div>
              <input
                type="range" min="0" max="100" value={masterDimmer}
                onChange={e => setMasterDimmer(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#00FFFF' }}
              />
            </div>

            {/* Color Temp */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Color Temperature (Kelvin):</span>
                <strong style={{ color: '#fbbf24' }}>{colorTemp} K ({colorTemp < 3200 ? 'Warm Tungsten' : colorTemp < 5000 ? 'Neutral Halogen' : 'Daylight Cool'})</strong>
              </div>
              <input
                type="range" min="2200" max="6500" step="100" value={colorTemp}
                onChange={e => setColorTemp(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#fbbf24' }}
              />
            </div>

            {/* Haze / Fog */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Atmospheric Haze / Fog Output:</span>
                <strong style={{ color: '#a78bfa' }}>{hazeDensity}%</strong>
              </div>
              <input
                type="range" min="0" max="100" value={hazeDensity}
                onChange={e => setHazeDensity(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#a78bfa' }}
              />
            </div>

            {/* Grow-Light Synchronization Toggle */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc' }}>CEA Hydroponic Grow-Spectrum Sync</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Auto-dims purple grow spectrum to 2700K during live show</div>
              </div>
              <input
                type="checkbox"
                checked={growLightBlend}
                onChange={e => setGrowLightBlend(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: '#10b981', cursor: 'pointer' }}
              />
            </div>
          </div>
        </div>

        {/* Real-time Audio Level Telemetry & Cardioid Polar Alignment */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
                🔊 Real-Time Acoustic &amp; VU Telemetry
              </h4>
              <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>Dante Audio Network &bull; 96kHz</span>
            </div>

            {/* Stereo Master VU Meter Bars */}
            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '14px', borderRadius: '8px', marginBottom: '14px' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '8px' }}>MAIN STEREO PA OUTPUT (L / R)</div>
              
              {/* Left Channel */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.75rem', width: '20px', fontWeight: 700, color: '#38bdf8' }}>L:</span>
                <div style={{ flex: 1, height: '12px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                  <div style={{
                    width: `${leftVu}%`,
                    background: leftVu > 85 ? 'linear-gradient(90deg, #10b981 0%, #f59e0b 70%, #ef4444 100%)' : '#10b981',
                    transition: 'width 0.1s ease'
                  }} />
                </div>
                <span style={{ fontSize: '0.75rem', width: '45px', textAlign: 'right', fontWeight: 700, color: leftVu > 85 ? '#ef4444' : '#10b981' }}>
                  {(leftVu * 0.3 - 24).toFixed(1)} dB
                </span>
              </div>

              {/* Right Channel */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', width: '20px', fontWeight: 700, color: '#38bdf8' }}>R:</span>
                <div style={{ flex: 1, height: '12px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                  <div style={{
                    width: `${rightVu}%`,
                    background: rightVu > 85 ? 'linear-gradient(90deg, #10b981 0%, #f59e0b 70%, #ef4444 100%)' : '#10b981',
                    transition: 'width 0.1s ease'
                  }} />
                </div>
                <span style={{ fontSize: '0.75rem', width: '45px', textAlign: 'right', fontWeight: 700, color: rightVu > 85 ? '#ef4444' : '#10b981' }}>
                  {(rightVu * 0.3 - 24).toFixed(1)} dB
                </span>
              </div>
            </div>

            {/* Cardioid Subwoofer Low-End Directional Attenuation */}
            <div style={{ background: 'rgba(0,0,0,0.4)', padding: '14px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc' }}>Cardioid Subwoofer Array</span>
                <button
                  onClick={() => setIsSubwooferCardioid(!isSubwooferCardioid)}
                  style={{
                    background: isSubwooferCardioid ? '#15803d' : '#475569',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  {isSubwooferCardioid ? 'ACTIVE (180° Inverted Delay)' : 'OMNIDIRECTIONAL'}
                </button>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: '0 0 8px 0' }}>
                Inverts rear subwoofer element phase with calibrated 4.2ms delay to cancel low-frequency sub-bass spill toward the residential earthships.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: '#64748b' }}>Rear Sub-Bass Attenuation:</span>
                <strong style={{ color: isSubwooferCardioid ? '#10b981' : '#ef4444' }}>
                  {isSubwooferCardioid ? `-${cardioidRejectionDb} dB Attenuation (Optimal)` : '0 dB (Omnidirectional Spill)'}
                </strong>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '14px', fontSize: '0.75rem', color: '#64748b', textAlign: 'center' }}>
            Acoustic Ground Resonance: <strong>Nominal 0.04 mm/s² (Shane's Isolators Intact)</strong>
          </div>
        </div>
      </div>

      {/* 3. Interactive Teleprompter & Live Setlist HUD */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.9)',
        border: '1px solid rgba(0, 255, 255, 0.25)',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
      }}>
        {/* Prompter Header & Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem' }}>📜</span>
              <h4 style={{ margin: 0, fontSize: '1.05rem', color: '#ffffff', fontWeight: 800 }}>
                Performer Teleprompter &amp; Live Setlist HUD
              </h4>
            </div>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Beam-Splitter Floor Glass &bull; Wireless Stage Monitor Feed
            </span>
          </div>

          {/* Prompter Control Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => setIsPrompterScrolling(!isPrompterScrolling)}
              style={{
                background: isPrompterScrolling ? '#ef4444' : '#10b981',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 16px',
                fontSize: '0.85rem',
                fontWeight: 800,
                cursor: 'pointer'
              }}
            >
              {isPrompterScrolling ? '⏸ PAUSE SCROLL' : '▶ START AUTO-SCROLL'}
            </button>

            <button
              onClick={() => setScrollOffset(0)}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                color: '#cbd5e1',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              ↺ Reset
            </button>

            <button
              onClick={() => setIsMirroredPrompter(!isMirroredPrompter)}
              style={{
                background: isMirroredPrompter ? '#7a288a' : 'rgba(255, 255, 255, 0.08)',
                color: '#ffffff',
                border: '1px solid #c084fc',
                borderRadius: '6px',
                padding: '8px 12px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {isMirroredPrompter ? '🪞 Mirror Mode: ON' : '🪞 Mirror Mode: OFF'}
            </button>

            {/* Speed Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Speed:</span>
              <input
                type="range" min="1" max="8" value={prompterSpeed}
                onChange={e => setPrompterSpeed(Number(e.target.value))}
                style={{ width: '60px', accentColor: '#00FFFF' }}
              />
              <span style={{ fontSize: '0.75rem', color: '#00FFFF', fontWeight: 700 }}>{prompterSpeed}x</span>
            </div>
          </div>
        </div>

        {/* Setlist Song Selector Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', overflowX: 'auto' }}>
          {setlist.map((song, idx) => (
            <button
              key={idx}
              onClick={() => {
                setActiveSongIndex(idx);
                setScrollOffset(0);
              }}
              style={{
                background: activeSongIndex === idx ? 'rgba(0, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.4)',
                border: activeSongIndex === idx ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                color: activeSongIndex === idx ? '#00FFFF' : '#94a3b8',
                borderRadius: '6px',
                padding: '8px 14px',
                fontSize: '0.8rem',
                fontWeight: 700,
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              {song.title} &bull; <span style={{ color: '#fbbf24' }}>{song.key}</span>
            </button>
          ))}
        </div>

        {/* Teleprompter Scroll Screen */}
        <div style={{
          height: '240px',
          background: '#000000',
          border: '1px solid #334155',
          borderRadius: '8px',
          overflow: 'hidden',
          position: 'relative',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-start',
          transform: isMirroredPrompter ? 'scaleX(-1)' : 'none'
        }}>
          <div style={{
            transform: `translateY(-${scrollOffset}px)`,
            transition: 'transform 0.05s linear',
            color: '#fbbf24',
            fontFamily: 'monospace',
            fontSize: `${prompterFontSize}px`,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
            fontWeight: 700
          }}>
            {setlist[activeSongIndex].lyrics}
          </div>

          {/* Prompter Guide Cue Lines */}
          <div style={{
            position: 'absolute',
            top: '45%',
            left: 0,
            right: 0,
            height: '2px',
            background: 'rgba(0, 255, 255, 0.3)',
            pointerEvents: 'none'
          }} />
        </div>
      </div>

    </div>
  );
}
