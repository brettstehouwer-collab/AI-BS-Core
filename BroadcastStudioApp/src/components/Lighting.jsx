import React, { useState } from 'react';
import { theme } from '../styles/theme';

export const NeonBlueAndPurpleLEDStrips = ({ intensity = 85, colorMode = 'cyber' }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: `1px solid ${theme.colors.secondary}`,
      borderRadius: '12px',
      padding: '16px',
      boxShadow: `0 0 20px ${theme.colors.glowViolet}`,
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ color: theme.colors.accent, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>⚡</span> Neon Blue & Purple LED Strips
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(0,255,255,0.15)', color: theme.colors.accent, padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}` }}>
          DMX Channel 01-08 · {intensity}%
        </span>
      </div>
      <div style={{
        height: '10px',
        width: '100%',
        borderRadius: '5px',
        background: `linear-gradient(90deg, ${theme.colors.accent} 0%, ${theme.colors.secondary} 50%, ${theme.colors.accent} 100%)`,
        boxShadow: `0 0 15px ${theme.colors.accent}, 0 0 25px ${theme.colors.secondary}`,
        animation: 'pulseGlow 3s infinite alternate'
      }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '0.75rem', color: theme.colors.textMuted }}>
        <span>Perimeter Linear Array</span>
        <span>Recessed Cove Integration</span>
        <span>RGBW Dynamic Sweep</span>
      </div>
    </div>
  );
};

export const HangingGeometricPendantLights = ({ quantity = 12 }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: `1px solid ${theme.colors.accent}`,
      borderRadius: '12px',
      padding: '16px',
      boxShadow: `0 0 20px ${theme.colors.glowCyan}`,
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ color: '#FFFFFF', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>💎</span> Hanging Geometric Pendant Lights
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(122,40,138,0.2)', color: '#D8B4FE', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.secondary}` }}>
          {quantity} Fixtures Hanging
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '10px', margin: '12px 0' }}>
        {Array.from({ length: quantity > 12 ? 12 : quantity }).map((_, i) => (
          <div key={i} style={{
            height: '40px',
            clipPath: theme.shapes.glowingGeometricShapes.clipPath,
            background: i % 2 === 0 ? `linear-gradient(135deg, ${theme.colors.accent}, #008888)` : `linear-gradient(135deg, ${theme.colors.secondary}, #4A1058)`,
            boxShadow: `0 0 10px ${i % 2 === 0 ? theme.colors.accent : theme.colors.secondary}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.7rem',
            fontWeight: 'bold',
            color: '#FFF'
          }}>
            P{i+1}
          </div>
        ))}
      </div>
      <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted, textAlign: 'right' }}>
        Hexagonal Steel Wireframes · 2700K-6500K Tunable White
      </div>
    </div>
  );
};

export const ColorChangingAccentLights = ({ activeMood = 'Cyberpunk Violet' }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: '1px solid rgba(255, 255, 255, 0.15)',
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ color: theme.colors.accent, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🎨</span> Color-Changing Accent Lights
        </h4>
        <span style={{ fontSize: '0.8rem', color: '#A7F3D0', background: 'rgba(16, 185, 129, 0.15)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #10B981' }}>
          Mood: {activeMood}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        {['Cyberpunk Violet', 'Electric Cyan', 'Deep Midnight', 'Neon Amber'].map((mood) => (
          <div key={mood} style={{
            padding: '8px 14px',
            borderRadius: '6px',
            fontSize: '0.8rem',
            cursor: 'pointer',
            border: activeMood === mood ? `1px solid ${theme.colors.accent}` : '1px solid rgba(255,255,255,0.1)',
            background: activeMood === mood ? 'rgba(0, 255, 255, 0.15)' : 'rgba(255,255,255,0.03)',
            color: activeMood === mood ? theme.colors.accent : '#94A3B8',
            transition: 'all 0.2s ease'
          }}>
            {mood}
          </div>
        ))}
      </div>
    </div>
  );
};

const Lighting = () => {
  const [intensity, setIntensity] = useState(85);
  const [activeMood, setActiveMood] = useState('Cyberpunk Violet');

  return (
    <div style={{ color: theme.colors.textPrimary }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: theme.colors.accent }}>💡 Layered Lighting System</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.85rem', color: theme.colors.textMuted }}>Global Dimmer:</span>
          <input
            type="range"
            min="0"
            max="100"
            value={intensity}
            onChange={(e) => setIntensity(Number(e.target.value))}
            style={{ accentColor: theme.colors.accent, cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.85rem', color: theme.colors.accent, fontWeight: 'bold' }}>{intensity}%</span>
        </div>
      </div>

      <NeonBlueAndPurpleLEDStrips intensity={intensity} />
      <HangingGeometricPendantLights quantity={12} />
      <ColorChangingAccentLights activeMood={activeMood} />
    </div>
  );
};

export default Lighting;
