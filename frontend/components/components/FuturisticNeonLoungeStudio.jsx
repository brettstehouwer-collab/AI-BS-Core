import React, { useState } from 'react';
import { theme } from '../styles/theme';
import Lighting from './Lighting';
import Layout from './Layout';
import MaterialsAndFinishes from './MaterialsAndFinishes';
import Amenities from './Amenities';
import DesignSoftwareUsed from './DesignSoftwareUsed';
import DesignParameters from './DesignParameters';
import ThematicVstVisualizer from './ThematicVstVisualizer';

export default function FuturisticNeonLoungeStudio() {
  const [activeSubTab, setActiveSubTab] = useState('full_lounge');

  return (
    <div style={{
      background: theme.colors.primary, // Charcoal Black
      minHeight: '100vh',
      color: theme.colors.textPrimary,
      padding: '24px',
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
    }}>
      {/* Hero Header Deck */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(122, 40, 138, 0.25) 0%, rgba(0, 255, 255, 0.15) 100%)',
        border: `1px solid ${theme.colors.accent}`,
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: `0 0 30px ${theme.colors.glowCyan}, inset 0 0 20px ${theme.colors.glowViolet}`,
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: '-20px',
          right: '-20px',
          width: '120px',
          height: '120px',
          background: theme.colors.accent,
          opacity: 0.15,
          borderRadius: '50%',
          filter: 'blur(30px)'
        }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative', zIndex: 2 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <span style={{ fontSize: '2rem' }}>🍸</span>
              <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 800, letterSpacing: '-0.5px', color: '#FFF' }}>
                Futuristic Neon Lounge Design Studio
              </h1>
              <span style={{
                background: `linear-gradient(90deg, ${theme.colors.secondary}, ${theme.colors.accent})`,
                color: '#FFF',
                padding: '4px 10px',
                borderRadius: '20px',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                textTransform: 'uppercase',
                letterSpacing: '1px'
              }}>
                v5.97.0 Active
              </span>
            </div>
            <p style={{ margin: 0, color: theme.colors.textMuted, fontSize: '0.95rem' }}>
              Next-generation spatial architectural studio combining Charcoal Black (#000000), Electric Violet (#7A288A), and Bright Cyan (#00FFFF) with live AI Autograd structural optimization and VST3 Theatrical Acoustic modulation.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <div style={{ background: 'rgba(0,0,0,0.6)', padding: '10px 16px', borderRadius: '10px', border: `1px solid ${theme.colors.accent}`, textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>PRIMARY COLOR</div>
              <div style={{ fontSize: '0.9rem', color: '#FFF', fontWeight: 'bold' }}>#000000</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.6)', padding: '10px 16px', borderRadius: '10px', border: `1px solid ${theme.colors.secondary}`, textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>SECONDARY COLOR</div>
              <div style={{ fontSize: '0.9rem', color: '#D8B4FE', fontWeight: 'bold' }}>#7A288A</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.6)', padding: '10px 16px', borderRadius: '10px', border: `1px solid ${theme.colors.accent}`, textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: theme.colors.textMuted }}>ACCENT COLOR</div>
              <div style={{ fontSize: '0.9rem', color: theme.colors.accent, fontWeight: 'bold' }}>#00FFFF</div>
            </div>
          </div>
        </div>

        {/* Subtab Selector */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '16px', flexWrap: 'wrap' }}>
          {[
            { id: 'full_lounge', label: '🌆 Complete Lounge Overview', icon: '🏬' },
            { id: 'vst_acoustics', label: '🎹 Theatrical VST Acoustic DSP', icon: '🎛️' },
            { id: 'lighting', label: '💡 Layered Lighting', icon: '⚡' },
            { id: 'layout', label: '📐 Layout & Flow', icon: '🏛️' },
            { id: 'materials', label: '✨ Materials & Finishes', icon: '🪟' },
            { id: 'amenities', label: '🍸 Key Amenities', icon: '🍹' },
            { id: 'software', label: '🤖 Neural Software Engine', icon: '🧠' },
            { id: 'parameters', label: '⚙️ Parametric AI Tuning', icon: '⚙️' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                background: activeSubTab === tab.id
                  ? `linear-gradient(135deg, ${theme.colors.secondary}, rgba(0, 255, 255, 0.3))`
                  : 'rgba(255,255,255,0.04)',
                border: activeSubTab === tab.id ? `1px solid ${theme.colors.accent}` : '1px solid rgba(255,255,255,0.08)',
                color: activeSubTab === tab.id ? '#FFF' : '#94A3B8',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: activeSubTab === tab.id ? 'bold' : 'normal',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Studio Viewport */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
        {activeSubTab === 'full_lounge' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <ThematicVstVisualizer />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              <div>
                <Lighting />
                <MaterialsAndFinishes />
              </div>
              <div>
                <Layout />
                <Amenities />
                <DesignSoftwareUsed />
              </div>
            </div>
          </div>
        )}

        {activeSubTab === 'vst_acoustics' && <ThematicVstVisualizer />}
        {activeSubTab === 'lighting' && <Lighting />}
        {activeSubTab === 'layout' && <Layout />}
        {activeSubTab === 'materials' && <MaterialsAndFinishes />}
        {activeSubTab === 'amenities' && <Amenities />}
        {activeSubTab === 'software' && <DesignSoftwareUsed />}
        {activeSubTab === 'parameters' && <DesignParameters />}
      </div>
    </div>
  );
}
