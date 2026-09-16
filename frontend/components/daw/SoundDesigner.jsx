import React, { useState, useEffect } from 'react';
import { theme } from '../../styles/theme';
import { useDawStore } from './dawStore';
import { Sliders, Activity, X } from 'lucide-react';

const SoundDesigner = ({ channel, onClose }) => {
  const setChannelEQ = useDawStore(state => state.setChannelEQ);
  const setChannelEnvelope = useDawStore(state => state.setChannelEnvelope);

  // Local state for smooth UI dragging before committing to Tone.js
  const [eq, setEq] = useState({ low: 0, mid: 0, high: 0 });
  const [env, setEnv] = useState({ attack: 0.01, decay: 0.1, sustain: 0.5, release: 0.5 });

  // Sync state when channel changes
  useEffect(() => {
    if (channel && channel.eq) {
      setEq({
        low: channel.eq.low.value,
        mid: channel.eq.mid.value,
        high: channel.eq.high.value
      });
    }
    if (channel && channel.synth && channel.synth.envelope) {
      setEnv({
        attack: channel.synth.envelope.attack || 0.01,
        decay: channel.synth.envelope.decay || 0.1,
        sustain: channel.synth.envelope.sustain || 0.5,
        release: channel.synth.envelope.release || 0.5
      });
    }
  }, [channel]);

  const handleEqChange = (band, val) => {
    setEq(prev => ({ ...prev, [band]: val }));
    setChannelEQ(channel.id, band, val);
  };

  const handleEnvChange = (param, val) => {
    setEnv(prev => ({ ...prev, [param]: val }));
    setChannelEnvelope(channel.id, param, val);
  };

  if (!channel) return null;

  const hasEnvelope = !!(channel.synth && channel.synth.envelope);

  return (
    <div style={{
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      height: '180px',
      background: 'rgba(10, 13, 18, 0.98)',
      borderTop: `1px solid ${theme.colors.accent}`,
      boxShadow: `0 -5px 20px rgba(0, 0, 0, 0.8)`,
      zIndex: 100,
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '6px 12px',
        background: '#161b22',
        borderBottom: '1px solid #30363d'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={14} color={channel.color || theme.colors.accent} />
          <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#fff', textTransform: 'uppercase' }}>
            Sound Designer: <span style={{ color: channel.color || theme.colors.accent }}>{channel.name}</span>
          </span>
        </div>
        <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: '#888', cursor: 'pointer' }}>
          <X size={16} />
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, padding: '12px', gap: '24px' }}>
        
        {/* EQ Section */}
        <div style={{ flex: 1, background: '#0d1117', border: '1px solid #30363d', borderRadius: '4px', padding: '10px' }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '10px', color: '#8b949e', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Activity size={12} /> PARAMETRIC EQ3
          </h4>
          <div style={{ display: 'flex', justifyContent: 'space-around', height: '80px' }}>
            {['low', 'mid', 'high'].map(band => (
              <div key={band} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <input
                  type="range"
                  min="-24"
                  max="12"
                  step="0.1"
                  value={eq[band]}
                  onChange={(e) => handleEqChange(band, Number(e.target.value))}
                  style={{
                    appearance: 'slider-vertical',
                    width: '4px',
                    height: '60px',
                    accentColor: theme.colors.accent,
                    cursor: 'pointer'
                  }}
                />
                <span style={{ fontSize: '9px', color: '#888', textTransform: 'uppercase' }}>{band}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ADSR Envelope Section */}
        {hasEnvelope ? (
          <div style={{ flex: 1, background: '#0d1117', border: '1px solid #30363d', borderRadius: '4px', padding: '10px' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '10px', color: '#8b949e', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Sliders size={12} /> ADSR ENVELOPE
            </h4>
            <div style={{ display: 'flex', justifyContent: 'space-around', height: '80px' }}>
              {[
                { key: 'attack', min: 0.001, max: 2, label: 'ATT' },
                { key: 'decay', min: 0.01, max: 2, label: 'DEC' },
                { key: 'sustain', min: 0, max: 1, label: 'SUS' },
                { key: 'release', min: 0.01, max: 4, label: 'REL' }
              ].map(param => (
                <div key={param.key} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                  <input
                    type="range"
                    min={param.min}
                    max={param.max}
                    step="0.01"
                    value={env[param.key]}
                    onChange={(e) => handleEnvChange(param.key, Number(e.target.value))}
                    style={{
                      appearance: 'slider-vertical',
                      width: '4px',
                      height: '60px',
                      accentColor: channel.color || theme.colors.secondary,
                      cursor: 'pointer'
                    }}
                  />
                  <span style={{ fontSize: '9px', color: '#888' }}>{param.label}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, background: '#0d1117', border: '1px dashed #30363d', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: '10px', color: '#666' }}>ENVELOPE NOT AVAILABLE FOR THIS SYNTH TYPE</span>
          </div>
        )}

      </div>
    </div>
  );
};

export default SoundDesigner;
