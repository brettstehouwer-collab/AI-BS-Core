import React, { useState, useEffect } from 'react';
import { theme } from '../../styles/theme';
import { SlidersHorizontal, Activity, Zap, Radio } from 'lucide-react';
import { useDawStore } from './dawStore';

const Mixer = () => {
  const channels = useDawStore(state => state.channels);
  const masterVolume = useDawStore(state => state.masterVolume);
  const setMasterVolume = useDawStore(state => state.setMasterVolume);
  const setChannelVolume = useDawStore(state => state.setChannelVolume);
  const setChannelPan = useDawStore(state => state.setChannelPan);
  const setChannelSend = useDawStore(state => state.setChannelSend);
  const toggleChannelMute = useDawStore(state => state.toggleChannelMute);
  const toggleChannelSolo = useDawStore(state => state.toggleChannelSolo);
  const activeMixerTrackId = useDawStore(state => state.activeMixerTrackId);
  const setActiveMixerTrackId = useDawStore(state => state.setActiveMixerTrackId);
  const fxState = useDawStore(state => state.fxState);
  const toggleFX = useDawStore(state => state.toggleFX);
  const isPlaying = useDawStore(state => state.isPlaying);
  const fetchAvailableVstPlugins = useDawStore(state => state.fetchAvailableVstPlugins);
  const loadVstPlugin = useDawStore(state => state.loadVstPlugin);

  useEffect(() => {
    fetchAvailableVstPlugins();
  }, []);

  // Meter Animation Level Simulation
  const [meterLevels, setMeterLevels] = useState({});

  useEffect(() => {
    let animId;
    const updateMeters = () => {
      if (isPlaying) {
        const levels = { master: Math.random() * 0.7 + 0.2 };
        channels.forEach(ch => {
          if (!ch.mute) {
            levels[ch.id] = Math.random() * 0.6 + 0.1;
          } else {
            levels[ch.id] = 0;
          }
        });
        setMeterLevels(levels);
      } else {
        setMeterLevels({});
      }
      animId = requestAnimationFrame(updateMeters);
    };
    animId = requestAnimationFrame(updateMeters);
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, channels]);

  return (
    <div style={{
      background: 'rgba(10, 12, 16, 0.98)',
      borderTop: `1px solid ${theme.colors.border}`,
      height: '100%',
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SlidersHorizontal size={16} color={theme.colors.accent} />
          <h3 style={{ margin: 0, fontSize: '13px', color: '#fff', fontWeight: 'bold' }}>
            MIXER & MASTER EFFECTS RACK
          </h3>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Side: Channel Fader Strips */}
        <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', flex: 1, paddingBottom: '4px' }}>
          
          {/* Master Strip */}
          <div
            onClick={() => setActiveMixerTrackId(0)}
            style={{
              width: '68px',
              background: activeMixerTrackId === 0 ? 'rgba(0, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.03)',
              border: activeMixerTrackId === 0 ? `1px solid ${theme.colors.accent}` : '1px solid rgba(255,255,255,0.08)',
              borderRadius: '6px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '8px 4px',
              borderTop: `3px solid ${theme.colors.accent}`,
              cursor: 'pointer'
            }}
          >
            <div style={{ fontSize: '10px', fontWeight: 'bold', color: theme.colors.accent, marginBottom: '6px' }}>
              MASTER
            </div>

            {/* VU Meter & Fader Pair */}
            <div style={{ display: 'flex', gap: '4px', flex: 1, alignItems: 'center', width: '100%', justifyContent: 'center' }}>
              {/* Animated VU Peak Meter */}
              <div style={{ width: '6px', height: '100%', background: '#000', borderRadius: '3px', position: 'relative', overflow: 'hidden' }}>
                <div style={{
                  position: 'absolute',
                  bottom: 0,
                  width: '100%',
                  height: `${(meterLevels.master || 0) * 100}%`,
                  background: 'linear-gradient(to top, #5eff7b 60%, #ffd000 85%, #ff3b30 100%)',
                  transition: 'height 0.08s ease'
                }} />
              </div>

              {/* Volume Fader */}
              <input
                type="range"
                min="-30"
                max="6"
                value={masterVolume}
                onChange={(e) => setMasterVolume(Number(e.target.value))}
                title={`Master Vol: ${masterVolume} dB`}
                style={{
                  writingMode: 'vertical-lr',
                  direction: 'rtl',
                  height: '100%',
                  accentColor: theme.colors.accent,
                  cursor: 'pointer',
                  width: '20px'
                }}
              />
            </div>

            <div style={{ fontSize: '9px', color: '#aaa', marginTop: '6px', fontFamily: 'monospace' }}>
              {masterVolume > 0 ? `+${masterVolume}` : masterVolume} dB
            </div>
          </div>

          {/* Sub-Mix Summing Buses (A: Drums, B: Inst, C: Vocals, D: FX) */}
          {useDawStore.getState().subBuses?.map((bus, bIdx) => (
            <div
              key={bus.id}
              style={{
                width: '54px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: `1px solid ${bus.color}44`,
                borderTop: `3px solid ${bus.color}`,
                borderRadius: '6px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: '6px 2px'
              }}
            >
              <div style={{ fontSize: '8px', fontWeight: 'bold', color: bus.color, marginBottom: '4px', textAlign: 'center' }}>
                {bus.name.split(':')[0]}
              </div>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <input
                  type="range"
                  min="-30"
                  max="6"
                  value={bus.volume}
                  onChange={(e) => useDawStore.getState().setSubBusVolume(bus.id, Number(e.target.value))}
                  title={`${bus.name} Vol: ${bus.volume} dB`}
                  style={{
                    writingMode: 'vertical-lr',
                    direction: 'rtl',
                    height: '100%',
                    accentColor: bus.color,
                    cursor: 'pointer',
                    width: '14px'
                  }}
                />
              </div>
              <div style={{ fontSize: '8px', color: '#888', marginTop: '4px', fontFamily: 'monospace' }}>
                {bus.volume}dB
              </div>
            </div>
          ))}

          <div style={{ width: '1px', background: '#30363d', margin: '0 4px' }} />

          {/* Insert Tracks */}
          {channels.map((ch, idx) => {
            const isSelected = activeMixerTrackId === idx + 1;
            const level = meterLevels[ch.id] || 0;

            return (
              <div
                key={ch.id}
                onClick={() => setActiveMixerTrackId(idx + 1)}
                style={{
                  width: '64px',
                  background: isSelected ? 'rgba(0, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? `1px solid ${ch.color || theme.colors.accent}` : '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '6px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: '8px 4px',
                  borderTop: `3px solid ${ch.color || '#888'}`,
                  cursor: 'pointer'
                }}
              >
                <div style={{ fontSize: '9px', fontWeight: 'bold', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '100%', textAlign: 'center', marginBottom: '4px' }}>
                  {ch.name}
                </div>

                {/* Pan Slider Small */}
                <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
                   <span style={{fontSize: '7px', color: '#888'}}>P</span>
                   <input
                     type="range"
                     min="-1"
                     max="1"
                     step="0.1"
                     value={ch.pan}
                     onChange={(e) => setChannelPan(ch.id, Number(e.target.value))}
                     title={`Pan: ${ch.pan}`}
                     style={{ width: '36px', height: '4px', accentColor: '#888', cursor: 'pointer' }}
                   />
                </div>
                
                {/* Sends (Reverb & Delay) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', margin: '4px 0' }}>
                   <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
                      <span style={{fontSize: '7px', color: '#888'}}>R</span>
                      <input
                        type="range"
                        min="-60"
                        max="0"
                        defaultValue="-60"
                        onChange={(e) => setChannelSend(ch.id, 'reverb', Number(e.target.value))}
                        title={`Send Reverb`}
                        style={{ width: '36px', height: '4px', accentColor: '#00f0ff', cursor: 'pointer' }}
                      />
                   </div>
                   <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
                      <span style={{fontSize: '7px', color: '#888'}}>D</span>
                      <input
                        type="range"
                        min="-60"
                        max="0"
                        defaultValue="-60"
                        onChange={(e) => setChannelSend(ch.id, 'delay', Number(e.target.value))}
                        title={`Send Delay`}
                        style={{ width: '36px', height: '4px', accentColor: '#ff007f', cursor: 'pointer' }}
                      />
                   </div>
                   <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
                      <span style={{fontSize: '7px', color: '#888'}}>P</span>
                      <input
                        type="range"
                        min="-60"
                        max="0"
                        defaultValue="-60"
                        onChange={(e) => setChannelSend(ch.id, 'pitchShift', Number(e.target.value))}
                        title={`Send Pitch`}
                        style={{ width: '36px', height: '4px', accentColor: '#d95eff', cursor: 'pointer' }}
                      />
                   </div>
                   <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
                      <span style={{fontSize: '7px', color: '#888'}}>V</span>
                      <input
                        type="range"
                        min="-60"
                        max="0"
                        defaultValue="-60"
                        onChange={(e) => setChannelSend(ch.id, 'vst', Number(e.target.value))}
                        title={`Send VST`}
                        style={{ width: '36px', height: '4px', accentColor: '#ffbd5e', cursor: 'pointer' }}
                      />
                   </div>
                </div>

                {/* Meter + Fader */}
                <div style={{ display: 'flex', gap: '4px', flex: 1, alignItems: 'center', width: '100%', justifyContent: 'center' }}>
                  {/* VU Peak Meter */}
                  <div style={{ width: '5px', height: '100%', background: '#000', borderRadius: '3px', position: 'relative', overflow: 'hidden' }}>
                    <div style={{
                      position: 'absolute',
                      bottom: 0,
                      width: '100%',
                      height: `${level * 100}%`,
                      background: 'linear-gradient(to top, #5eff7b 60%, #ffd000 85%, #ff3b30 100%)',
                      transition: 'height 0.08s ease'
                    }} />
                  </div>

                  {/* Fader */}
                  <input
                    type="range"
                    min="-30"
                    max="6"
                    value={ch.volume}
                    onChange={(e) => setChannelVolume(ch.id, Number(e.target.value))}
                    title={`${ch.name} Vol: ${ch.volume} dB`}
                    style={{
                      writingMode: 'vertical-lr',
                      direction: 'rtl',
                      height: '100%',
                      accentColor: ch.color || theme.colors.accent,
                      cursor: 'pointer',
                      width: '18px'
                    }}
                  />
                </div>

                {/* Track Mute / Solo mini */}
                <div style={{ display: 'flex', gap: '2px', marginTop: '6px' }}>
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleChannelMute(ch.id); }}
                    style={{
                      background: ch.mute ? '#ff3b30' : 'rgba(255,255,255,0.08)',
                      color: ch.mute ? '#fff' : '#888',
                      border: 'none',
                      borderRadius: '2px',
                      fontSize: '8px',
                      padding: '2px 4px',
                      cursor: 'pointer',
                      fontWeight: 'bold'
                    }}
                  >
                    M
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleChannelSolo(ch.id); }}
                    style={{
                      background: ch.solo ? '#5eff7b' : 'rgba(255,255,255,0.08)',
                      color: ch.solo ? '#000' : '#888',
                      border: 'none',
                      borderRadius: '2px',
                      fontSize: '8px',
                      padding: '2px 4px',
                      cursor: 'pointer',
                      fontWeight: 'bold'
                    }}
                  >
                    S
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Side: Insert FX Rack */}
        <div style={{
          width: '200px',
          background: 'rgba(15, 18, 24, 0.95)',
          border: '1px solid #30363d',
          borderRadius: '6px',
          padding: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          <div style={{ fontSize: '11px', fontWeight: 'bold', color: theme.colors.accent, borderBottom: '1px solid #30363d', paddingBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Zap size={12} /> EFFECT INSERTS
          </div>

          {/* Reverb FX Slot */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#fff' }}>Tone.Reverb</span>
              <input
                type="checkbox"
                checked={fxState.reverb.enabled}
                onChange={() => toggleFX('reverb')}
                style={{ cursor: 'pointer' }}
              />
            </div>
            <div style={{ fontSize: '9px', color: '#888', marginTop: '2px' }}>Decay: {fxState.reverb.decay}s • Wet: {Math.round(fxState.reverb.wet * 100)}%</div>
          </div>

          {/* Delay FX Slot */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#fff' }}>Feedback Delay</span>
              <input
                type="checkbox"
                checked={fxState.delay.enabled}
                onChange={() => toggleFX('delay')}
                style={{ cursor: 'pointer' }}
              />
            </div>
            <div style={{ fontSize: '9px', color: '#888', marginTop: '2px' }}>Time: 8n Sync • Wet: {Math.round(fxState.delay.wet * 100)}%</div>
          </div>

          {/* Distortion FX Slot */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#fff' }}>Overdrive Saturation</span>
              <input
                type="checkbox"
                checked={fxState.distortion.enabled}
                onChange={() => toggleFX('distortion')}
                style={{ cursor: 'pointer' }}
              />
            </div>
            <div style={{ fontSize: '9px', color: '#888', marginTop: '2px' }}>Drive: {fxState.distortion.amount}</div>
          </div>

          {/* Pitch Correction FX Slot */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#fff' }}>Vocal Pitch Snap</span>
              <input
                type="checkbox"
                checked={fxState.pitchShift.enabled}
                onChange={() => toggleFX('pitchShift')}
                style={{ cursor: 'pointer' }}
              />
            </div>
            <div style={{ fontSize: '9px', color: '#888', marginTop: '2px' }}>Amount: {fxState.pitchShift.pitch} Semitones</div>
          </div>

          {/* VST3 Plugin Host Slot with Parameter Knobs */}
          <div style={{ background: 'rgba(0,0,0,0.4)', padding: '8px', borderRadius: '4px', border: '1px solid #ffbd5e44' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#fff', display: 'flex', gap: '4px', alignItems: 'center' }}>
                 Native VST3 Host <span style={{ fontSize: '8px', background: '#ffbd5e', color: '#000', padding: '1px 4px', borderRadius: '2px', fontWeight: 'bold' }}>PORT 8013</span>
              </span>
              <input
                type="checkbox"
                checked={fxState.vst?.enabled || false}
                onChange={() => toggleFX('vst')}
                style={{ cursor: 'pointer' }}
              />
            </div>
            
            <select 
              value={useDawStore.getState().activeLoadedVstId || ''} 
              onChange={(e) => useDawStore.getState().loadVstPlugin(e.target.value)}
              style={{ width: '100%', marginTop: '6px', background: '#0a0d14', color: '#00f0ff', border: '1px solid #30363d', fontSize: '10px', padding: '4px', borderRadius: '3px' }}
            >
              <option value="">Select VST3 Plugin...</option>
              {useDawStore.getState().availableVstPlugins?.map((p, i) => (
                <option key={i} value={p.path}>{p.name}</option>
              ))}
            </select>

            {/* Granular VST Parameter Knobs */}
            {useDawStore.getState().activeVstParams?.length > 0 && (
              <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '140px', overflowY: 'auto' }}>
                <div style={{ fontSize: '9px', color: '#ffbd5e', fontWeight: 'bold' }}>LIVE VST PARAMETERS:</div>
                {useDawStore.getState().activeVstParams.slice(0, 6).map((param, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '9px', color: '#ccc' }}>
                    <span style={{ maxWidth: '70px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={param.label}>
                      {param.label}
                    </span>
                    <input
                      type="range"
                      min={param.min_value}
                      max={param.max_value}
                      step={(param.max_value - param.min_value) / 100}
                      value={param.raw_value}
                      onChange={(e) => useDawStore.getState().setVstParameter(
                        useDawStore.getState().activeLoadedVstId,
                        param.name,
                        Number(e.target.value)
                      )}
                      style={{ width: '70px', height: '3px', accentColor: '#ffbd5e', cursor: 'pointer' }}
                    />
                    <span style={{ fontSize: '8px', color: '#888', width: '24px', textAlign: 'right' }}>
                      {typeof param.raw_value === 'number' ? param.raw_value.toFixed(1) : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Master Bus Dynamics */}
          <div style={{ marginTop: 'auto', background: 'rgba(0, 255, 255, 0.05)', padding: '6px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}44` }}>
            <div style={{ fontSize: '10px', color: theme.colors.accent, fontWeight: 'bold' }}>Master Chain:</div>
            <div style={{ fontSize: '9px', color: '#aaa', marginTop: '2px' }}>EQ3 $\rightarrow$ Glue Compressor $\rightarrow$ Limiter (-0.1dB)</div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Mixer;
