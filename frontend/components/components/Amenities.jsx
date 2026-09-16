import React from 'react';
import { theme } from '../styles/theme';

export const BuiltInBar = ({ tapsCount = 16, barLengthFeet = 32 }) => {
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
          <span>🍸</span> Built-In Translucent Quartz Bar
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(0, 255, 255, 0.15)', color: theme.colors.accent, padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}` }}>
          {barLengthFeet} ft Countertop · {tapsCount} Craft Taps
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: 0 }}>
        Backlit Cristallo Quartzite bar top with integrated POS terminals, under-counter refrigeration, and digital mixology telemetry.
      </p>
    </div>
  );
};

export const AVTechnology = ({ screenResolution = '4K Micro-LED', dmxActive = true }) => {
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
          <span>📺</span> Integrated AV Technology Suite
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(122, 40, 138, 0.25)', color: '#E9D5FF', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.secondary}` }}>
          DMX 512 Control · {screenResolution}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginTop: '10px' }}>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>Spatial Audio</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: theme.colors.accent }}>Dolby Atmos 11.2</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>Video Wall</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#FFF' }}>1.2mm Pixel Pitch</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>DMX Latency</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#A7F3D0' }}>&lt; 2ms Low-Latency</div>
        </div>
      </div>
    </div>
  );
};

export const DiscreetServiceDoors = ({ accessControl = 'RFID / Biometric' }) => {
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
          <span>🚪</span> Discreet Staff Service Doors
        </h4>
        <span style={{ fontSize: '0.8rem', color: '#94A3B8' }}>
          Access: {accessControl}
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: 0 }}>
        Flush-mounted acoustic hidden portals providing invisible staff access to back-of-house kitchens, storage, and VIP suites without interrupting the lounge aesthetics.
      </p>
    </div>
  );
};

const Amenities = () => {
  return (
    <div style={{ color: theme.colors.textPrimary }}>
      <h3 style={{ margin: '0 0 16px 0', color: theme.colors.accent }}>🍸 Key Venue Amenities</h3>
      <BuiltInBar />
      <AVTechnology />
      <DiscreetServiceDoors />
    </div>
  );
};

export default Amenities;
