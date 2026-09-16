import React, { useState } from 'react';
import { theme } from '../../styles/theme';
import { 
  Sliders, Volume2, RotateCcw, Sparkles, X, Scissors, Layers, Check
} from 'lucide-react';

export default function ClipSettingsModal({ clip, onClose, onUpdateClip, onMakeUnique, onOpenEdison, onOpenSlicex }) {
  const [pitch, setPitch] = useState(clip?.pitch || 0); // -12 to +12 semitones
  const [fineTune, setFineTune] = useState(clip?.fineTune || 0); // -50 to +50 cents
  const [stretchMode, setStretchMode] = useState(clip?.stretchMode || 'e3_generic'); // 'e3_generic' | 'e3_pro' | 'resample' | 'stretch_pro'
  const [isReversed, setIsReversed] = useState(clip?.isReversed || false);
  const [isNormalized, setIsNormalized] = useState(clip?.isNormalized || false);
  const [volume, setVolume] = useState(clip?.volume !== undefined ? clip.volume : 0); // -24 to +6 dB
  const [pan, setPan] = useState(clip?.pan !== undefined ? clip.pan : 0); // -1 to 1
  const [fadeIn, setFadeIn] = useState(clip?.fadeIn || 0); // ms
  const [fadeOut, setFadeOut] = useState(clip?.fadeOut || 0); // ms

  const handleApply = () => {
    if (onUpdateClip) {
      onUpdateClip({
        ...clip,
        pitch,
        fineTune,
        stretchMode,
        isReversed,
        isNormalized,
        volume,
        pan,
        fadeIn,
        fadeOut
      });
    }
    onClose();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      backdropFilter: 'blur(6px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: '8px',
        width: '560px',
        maxWidth: '94vw',
        boxShadow: '0 20px 50px rgba(0,0,0,0.8), 0 0 20px rgba(0, 240, 255, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '10px 14px',
          background: 'linear-gradient(90deg, #161b22, #0d1117)',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '13px', background: '#a855f7', color: '#fff', padding: '2px 6px', borderRadius: '3px', fontWeight: 'bold' }}>
              CHANNEL SETTINGS
            </span>
            <span style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold' }}>
              {clip?.title || 'Audio Clip Properties'}
            </span>
          </div>

          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body Form */}
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          
          {/* Pitch Shifter & Fine Tuning */}
          <div style={{ background: '#161b22', padding: '12px', borderRadius: '6px', border: '1px solid #21262d' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', color: '#fff', fontWeight: 'bold' }}>PITCH & TIME STRETCHING</span>
              <span style={{ fontSize: '10px', color: '#00f0ff', fontFamily: 'monospace' }}>
                {pitch > 0 ? `+${pitch}` : pitch} st • {fineTune} cents
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '9px', color: '#888', marginBottom: '4px' }}>SEMITONES (-12 to +12)</div>
                <input
                  type="range"
                  min="-12"
                  max="12"
                  value={pitch}
                  onChange={(e) => setPitch(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#00f0ff' }}
                />
              </div>
              <div>
                <div style={{ fontSize: '9px', color: '#888', marginBottom: '4px' }}>FINE TUNE (-50 to +50 Cents)</div>
                <input
                  type="range"
                  min="-50"
                  max="50"
                  value={fineTune}
                  onChange={(e) => setFineTune(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#ff7b00' }}
                />
              </div>
            </div>

            {/* Time Stretch Algorithm */}
            <div style={{ marginTop: '10px' }}>
              <div style={{ fontSize: '9px', color: '#888', marginBottom: '4px' }}>TIME STRETCHING ALGORITHM</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
                {[
                  { id: 'e3_generic', label: 'e3 Generic' },
                  { id: 'e3_pro', label: 'e3 Pro' },
                  { id: 'resample', label: 'Resample' },
                  { id: 'stretch_pro', label: 'Stretch Pro' }
                ].map(m => (
                  <button
                    key={m.id}
                    onClick={() => setStretchMode(m.id)}
                    style={{
                      background: stretchMode === m.id ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255,255,255,0.03)',
                      border: stretchMode === m.id ? '1px solid #00f0ff' : '1px solid #30363d',
                      color: stretchMode === m.id ? '#00f0ff' : '#8b949e',
                      borderRadius: '3px',
                      padding: '4px',
                      fontSize: '9px',
                      fontWeight: 'bold',
                      cursor: 'pointer'
                    }}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Quick Audio Modifiers: Reverse, Normalize */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label style={{
              background: isReversed ? 'rgba(255, 123, 0, 0.15)' : '#161b22',
              border: isReversed ? '1px solid #ff7b00' : '1px solid #21262d',
              padding: '8px 12px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer'
            }}>
              <span style={{ fontSize: '11px', color: isReversed ? '#ff7b00' : '#ccc', fontWeight: 'bold' }}>
                🔄 REVERSE AUDIO
              </span>
              <input
                type="checkbox"
                checked={isReversed}
                onChange={() => setIsReversed(!isReversed)}
                style={{ cursor: 'pointer' }}
              />
            </label>

            <label style={{
              background: isNormalized ? 'rgba(0, 240, 255, 0.15)' : '#161b22',
              border: isNormalized ? '1px solid #00f0ff' : '1px solid #21262d',
              padding: '8px 12px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer'
            }}>
              <span style={{ fontSize: '11px', color: isNormalized ? '#00f0ff' : '#ccc', fontWeight: 'bold' }}>
                ⚡ NORMALIZE (0 dB)
              </span>
              <input
                type="checkbox"
                checked={isNormalized}
                onChange={() => setIsNormalized(!isNormalized)}
                style={{ cursor: 'pointer' }}
              />
            </label>
          </div>

          {/* Volume, Pan & Envelope Fades */}
          <div style={{ background: '#161b22', padding: '12px', borderRadius: '6px', border: '1px solid #21262d' }}>
            <div style={{ fontSize: '11px', color: '#fff', fontWeight: 'bold', marginBottom: '8px' }}>
              LEVEL & FADE ENVELOPES
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#888', marginBottom: '4px' }}>
                  <span>VOLUME</span>
                  <span>{volume} dB</span>
                </div>
                <input
                  type="range"
                  min="-24"
                  max="6"
                  value={volume}
                  onChange={(e) => setVolume(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#5eff7b' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#888', marginBottom: '4px' }}>
                  <span>PAN</span>
                  <span>{pan > 0 ? `R${Math.round(pan * 100)}%` : pan < 0 ? `L${Math.round(-pan * 100)}%` : 'Center'}</span>
                </div>
                <input
                  type="range"
                  min="-1"
                  max="1"
                  step="0.1"
                  value={pan}
                  onChange={(e) => setPan(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#a855f7' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '10px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#888', marginBottom: '4px' }}>
                  <span>FADE IN</span>
                  <span>{fadeIn} ms</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="2000"
                  step="50"
                  value={fadeIn}
                  onChange={(e) => setFadeIn(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#ffaa00' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#888', marginBottom: '4px' }}>
                  <span>FADE OUT</span>
                  <span>{fadeOut} ms</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="2000"
                  step="50"
                  value={fadeOut}
                  onChange={(e) => setFadeOut(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#ffaa00' }}
                />
              </div>
            </div>
          </div>

          {/* Quick Studio Actions */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => {
                if (onMakeUnique) onMakeUnique(clip);
                onClose();
              }}
              style={{
                flex: 1,
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '4px',
                padding: '8px',
                color: '#fff',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px'
              }}
            >
              <Layers size={12} color="#00f0ff" /> MAKE UNIQUE
            </button>

            <button
              onClick={() => {
                onClose();
                if (onOpenEdison) onOpenEdison(clip);
              }}
              style={{
                flex: 1,
                background: 'rgba(255, 123, 0, 0.12)',
                border: '1px solid #ff7b00',
                borderRadius: '4px',
                padding: '8px',
                color: '#ff7b00',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px'
              }}
            >
              <Scissors size={12} /> EDIT IN EDISON
            </button>

            <button
              onClick={() => {
                onClose();
                if (onOpenSlicex) onOpenSlicex(clip);
              }}
              style={{
                flex: 1,
                background: 'rgba(0, 240, 255, 0.12)',
                border: '1px solid #00f0ff',
                borderRadius: '4px',
                padding: '8px',
                color: '#00f0ff',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px'
              }}
            >
              <Sparkles size={12} /> SLICE IN SLICEX
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '10px 16px',
          background: '#161b22',
          borderTop: '1px solid #30363d',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '8px'
        }}>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: '1px solid #30363d',
              color: '#888',
              padding: '6px 12px',
              borderRadius: '4px',
              fontSize: '11px',
              cursor: 'pointer'
            }}
          >
            CANCEL
          </button>
          <button
            onClick={handleApply}
            style={{
              background: '#00f0ff',
              color: '#000',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Check size={13} /> APPLY SETTINGS
          </button>
        </div>
      </div>
    </div>
  );
}
