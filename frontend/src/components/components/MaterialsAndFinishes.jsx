import React, { useState } from 'react';
import { theme } from '../styles/theme';

export const DarkPolishedConcrete = ({ glossLevel = 92 }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: '1px solid rgba(255, 255, 255, 0.15)',
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: '#E2E8F0', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🏢</span> Dark Polished Concrete Flooring
        </h4>
        <span style={{ fontSize: '0.8rem', color: theme.colors.accent, background: 'rgba(0,255,255,0.1)', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}` }}>
          High-Gloss Index: {glossLevel}%
        </span>
      </div>
      <div style={{
        height: '45px',
        borderRadius: '6px',
        background: 'linear-gradient(180deg, #111115 0%, #050508 100%)',
        boxShadow: `inset 0 0 15px rgba(0, 255, 255, 0.2), 0 2px 8px rgba(0,0,0,0.8)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#64748B',
        fontSize: '0.8rem',
        letterSpacing: '1px'
      }}>
        REFLECTIVE CHARCOAL EPOXY SEALANT · SLIP-RESISTANT COATING
      </div>
    </div>
  );
};

export const HardWoodOrStone = ({ materialType = 'Black Walnut' }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.75)',
      border: '1px solid rgba(255, 255, 255, 0.15)',
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: '#FDE047', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🪵</span> Hardwood & Natural Stone Accents
        </h4>
        <span style={{ fontSize: '0.8rem', color: '#FDE047', background: 'rgba(253, 224, 71, 0.1)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #FDE047' }}>
          {materialType}
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: 0 }}>
        Thermally modified European Black Walnut paired with brushed Nero Marquina black marble countertops for tactile acoustic warmth.
      </p>
    </div>
  );
};

export const Textured3DGeometricWallPanels = ({ pattern = 'Hexagonal Prism' }) => {
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
          <span>📐</span> Textured 3D Geometric Wall Panels
        </h4>
        <span style={{ fontSize: '0.8rem', color: '#D8B4FE', background: 'rgba(122, 40, 138, 0.2)', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.secondary}` }}>
          Pattern: {pattern}
        </span>
      </div>
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', padding: '8px 0' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} style={{
            minWidth: '50px',
            height: '50px',
            borderRadius: '6px',
            clipPath: theme.shapes.glowingGeometricShapes.clipPath,
            background: i % 2 === 0 ? `linear-gradient(135deg, ${theme.colors.secondary}, #1f0824)` : 'linear-gradient(135deg, #111827, #000)',
            border: `1px solid ${theme.colors.secondary}`,
            boxShadow: `0 0 8px ${theme.colors.glowViolet}`
          }} />
        ))}
      </div>
    </div>
  );
};

export const SmartTintingGlass = ({ opacityPercent = 75, onOpacityChange }) => {
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
          <span>🪟</span> Smart Electrochromic Tinting Glass
        </h4>
        <span style={{ fontSize: '0.8rem', color: theme.colors.accent, background: 'rgba(0,255,255,0.15)', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}` }}>
          Tint Opacity: {opacityPercent}%
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '12px' }}>
        <span style={{ fontSize: '0.8rem', color: theme.colors.textMuted }}>10% Clear</span>
        <input
          type="range"
          min="10"
          max="100"
          value={opacityPercent}
          onChange={(e) => onOpacityChange && onOpacityChange(Number(e.target.value))}
          style={{ flex: 1, accentColor: theme.colors.accent, cursor: 'pointer' }}
        />
        <span style={{ fontSize: '0.8rem', color: theme.colors.accent }}>100% Privacy</span>
      </div>
    </div>
  );
};

const MaterialsAndFinishes = () => {
  const [glassOpacity, setGlassOpacity] = useState(75);

  return (
    <div style={{ color: theme.colors.textPrimary }}>
      <h3 style={{ margin: '0 0 16px 0', color: theme.colors.accent }}>✨ Materials & Architectural Finishes</h3>
      <DarkPolishedConcrete />
      <HardWoodOrStone />
      <Textured3DGeometricWallPanels />
      <SmartTintingGlass opacityPercent={glassOpacity} onOpacityChange={setGlassOpacity} />
    </div>
  );
};

export default MaterialsAndFinishes;
