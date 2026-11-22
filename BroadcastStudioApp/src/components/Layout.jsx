import React, { useState } from 'react';
import { theme } from '../styles/theme';

export const PillarlessCenter = ({ areaSqFt = 4500, guestCapacity = 350 }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: `1px solid ${theme.colors.accent}`,
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px',
      boxShadow: `0 0 15px ${theme.colors.glowCyan}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: theme.colors.accent, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🏛️</span> Pillarless Center Hall
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(0, 255, 255, 0.15)', color: theme.colors.accent, padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}` }}>
          {areaSqFt.toLocaleString()} sq ft · Max Capacity: {guestCapacity} Guests
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: '0 0 12px 0' }}>
        Unobstructed sightlines engineered via post-tensioned steel trussing. Provides complete visual exposure across the entire main lounge area.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>Clear Ceiling Height</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#FFF' }}>18'-6"</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>Structural Span</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: theme.colors.accent }}>75 ft Span</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>Acoustic Rating</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: theme.colors.secondary }}>STC 65</div>
        </div>
      </div>
    </div>
  );
};

export const DanceFloor = ({ isBassActive = true }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: `1px solid ${theme.colors.secondary}`,
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px',
      boxShadow: `0 0 15px ${theme.colors.glowViolet}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: '#D8B4FE', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>💃</span> Interactive LED Grid Dance Floor
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(122, 40, 138, 0.25)', color: '#E9D5FF', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.secondary}` }}>
          Sub-Bass Sync: Active 60Hz
        </span>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(8, 1fr)',
        gap: '6px',
        padding: '12px',
        background: '#000',
        borderRadius: '8px',
        border: `1px solid ${theme.colors.secondary}`
      }}>
        {Array.from({ length: 24 }).map((_, i) => (
          <div key={i} style={{
            height: '28px',
            borderRadius: '4px',
            background: (i + (isBassActive ? 1 : 0)) % 3 === 0
              ? `linear-gradient(135deg, ${theme.colors.accent}, #006666)`
              : (i % 2 === 0 ? `linear-gradient(135deg, ${theme.colors.secondary}, #330033)` : '#111116'),
            boxShadow: (i + (isBassActive ? 1 : 0)) % 3 === 0 ? `0 0 8px ${theme.colors.accent}` : 'none',
            transition: 'all 0.3s ease'
          }} />
        ))}
      </div>
    </div>
  );
};

export const WideAisles = ({ aisleWidthFeet = 8.5 }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: '1px solid rgba(255, 255, 255, 0.15)',
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: theme.colors.accent, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🚶‍♂️</span> Wide Circulation Aisles
        </h4>
        <span style={{ fontSize: '0.8rem', color: '#94A3B8' }}>
          Aisle Clearance: {aisleWidthFeet} ft
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: 0 }}>
        High-throughput circulation channels designed for dual-directional guest traffic, ADA accessibility, and rapid VIP service delivery.
      </p>
    </div>
  );
};

const Layout = () => {
  const [isBassActive, setIsBassActive] = useState(true);

  return (
    <div style={{ color: theme.colors.textPrimary }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: theme.colors.accent }}>📐 Spatial Layout & Guest Flow</h3>
        <button
          onClick={() => setIsBassActive(!isBassActive)}
          style={{
            background: isBassActive ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255,255,255,0.05)',
            border: `1px solid ${isBassActive ? theme.colors.accent : 'rgba(255,255,255,0.2)'}`,
            color: isBassActive ? theme.colors.accent : '#94A3B8',
            padding: '6px 12px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.8rem'
          }}
        >
          {isBassActive ? '🎵 Audio Pulse ON' : '🔇 Audio Pulse OFF'}
        </button>
      </div>

      <PillarlessCenter />
      <DanceFloor isBassActive={isBassActive} />
      <WideAisles />
    </div>
  );
};

export default Layout;
