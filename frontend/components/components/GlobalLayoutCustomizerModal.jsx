import React, { useState, useEffect } from 'react';

export const DEFAULT_LAYOUT_CONFIG = {
  fontScale: 1.0,           // 0.75 to 1.50
  cardPadding: 24,          // 10px to 48px
  boxRadius: 16,            // 0px to 32px
  gapScale: 20,             // 8px to 40px
  glassBlur: 16,            // 0px to 32px
  glassOpacity: 0.60,       // 0.20 to 0.95
  borderGlowSpread: 0,      // 0px to 16px
  fontFamilyKey: 'outfit',  // outfit, inter, space_grotesk, jetbrains, lexend, comic
  sidebarWidth: 260,        // 180px to 380px
};

export const FONT_OPTIONS = [
  { key: 'outfit', label: 'Outfit (Default Geometric)', family: "'Outfit', 'Inter', sans-serif" },
  { key: 'inter', label: 'Inter (Clean Technical)', family: "'Inter', -apple-system, sans-serif" },
  { key: 'space_grotesk', label: 'Space Grotesk (Tech Editorial)', family: "'Space Grotesk', sans-serif" },
  { key: 'jetbrains', label: 'JetBrains Mono (Hacker Terminal)', family: "'JetBrains Mono', monospace" },
  { key: 'lexend', label: 'Lexend (High Readability)', family: "'Lexend', sans-serif" },
  { key: 'roboto', label: 'Roboto / Modern Standard', family: "'Roboto', sans-serif" }
];

export const LAYOUT_PRESETS = [
  {
    key: 'compact_pro',
    label: '⚡ Compact Pro',
    description: 'Dense tables & small padding for max screen real-estate',
    config: {
      fontScale: 0.88,
      cardPadding: 14,
      boxRadius: 8,
      gapScale: 12,
      glassBlur: 10,
      glassOpacity: 0.75,
      borderGlowSpread: 0,
      fontFamilyKey: 'inter'
    }
  },
  {
    key: 'balanced_default',
    label: '⚖️ Standard Balanced',
    description: 'Original Stehouwer AI-BS balanced dark glassmorphism',
    config: {
      fontScale: 1.0,
      cardPadding: 24,
      boxRadius: 16,
      gapScale: 20,
      glassBlur: 16,
      glassOpacity: 0.60,
      borderGlowSpread: 0,
      fontFamilyKey: 'outfit'
    }
  },
  {
    key: 'ultra_spacious',
    label: '🌌 Ultra Spacious',
    description: 'Luxurious breathing room, large cards, and soft padding',
    config: {
      fontScale: 1.12,
      cardPadding: 36,
      boxRadius: 24,
      gapScale: 30,
      glassBlur: 24,
      glassOpacity: 0.50,
      borderGlowSpread: 4,
      fontFamilyKey: 'outfit'
    }
  },
  {
    key: 'high_contrast_readability',
    label: '👓 High Readability',
    description: 'Enlarged text size, opaque cards, and maximum text clarity',
    config: {
      fontScale: 1.25,
      cardPadding: 28,
      boxRadius: 14,
      gapScale: 24,
      glassBlur: 8,
      glassOpacity: 0.90,
      borderGlowSpread: 0,
      fontFamilyKey: 'lexend'
    }
  },
  {
    key: 'cyber_neon',
    label: '🔮 Cyber Neon Deck',
    description: 'Sharp zero-radius corners, glowing edges, and terminal typography',
    config: {
      fontScale: 0.95,
      cardPadding: 20,
      boxRadius: 2,
      gapScale: 16,
      glassBlur: 20,
      glassOpacity: 0.70,
      borderGlowSpread: 8,
      fontFamilyKey: 'jetbrains'
    }
  }
];

export function applyLayoutConfigToDom(config) {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  const selectedFont = FONT_OPTIONS.find(f => f.key === config.fontFamilyKey) || FONT_OPTIONS[0];

  root.style.setProperty('--aibs-font-scale', config.fontScale.toString());
  root.style.setProperty('--aibs-card-padding', `${config.cardPadding}px`);
  root.style.setProperty('--aibs-box-radius', `${config.boxRadius}px`);
  root.style.setProperty('--aibs-gap-scale', `${config.gapScale}px`);
  root.style.setProperty('--aibs-glass-blur', `${config.glassBlur}px`);
  root.style.setProperty('--aibs-glass-opacity', config.glassOpacity.toString());
  root.style.setProperty('--aibs-border-glow-spread', `${config.borderGlowSpread}px`);
  root.style.setProperty('--aibs-primary-font', selectedFont.family);
}

export default function GlobalLayoutCustomizerModal({ isOpen, onClose }) {
  const [config, setConfig] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('aibs_layout_customizer_settings');
        if (saved) return { ...DEFAULT_LAYOUT_CONFIG, ...JSON.parse(saved) };
      } catch (e) {
        console.warn("Failed to load saved layout settings", e);
      }
    }
    return DEFAULT_LAYOUT_CONFIG;
  });

  const [activeTab, setActiveTab] = useState('sliders'); // 'sliders' | 'fonts' | 'presets'
  const [copiedNotification, setCopiedNotification] = useState(false);

  // Sync to DOM and localStorage on any config change
  const updateConfig = (key, value) => {
    setConfig(prev => {
      const updated = { ...prev, [key]: value };
      applyLayoutConfigToDom(updated);
      try {
        localStorage.setItem('aibs_layout_customizer_settings', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  const handleApplyPreset = (presetConfig) => {
    const updated = { ...config, ...presetConfig };
    setConfig(updated);
    applyLayoutConfigToDom(updated);
    try {
      localStorage.setItem('aibs_layout_customizer_settings', JSON.stringify(updated));
    } catch {}
  };

  const handleResetToDefault = () => {
    setConfig(DEFAULT_LAYOUT_CONFIG);
    applyLayoutConfigToDom(DEFAULT_LAYOUT_CONFIG);
    try {
      localStorage.setItem('aibs_layout_customizer_settings', JSON.stringify(DEFAULT_LAYOUT_CONFIG));
    } catch {}
  };

  const handleCopyCssVariables = () => {
    const cssText = `/* AI-BS Custom Layout Variables */
:root {
  --aibs-font-scale: ${config.fontScale};
  --aibs-card-padding: ${config.cardPadding}px;
  --aibs-box-radius: ${config.boxRadius}px;
  --aibs-gap-scale: ${config.gapScale}px;
  --aibs-glass-blur: ${config.glassBlur}px;
  --aibs-glass-opacity: ${config.glassOpacity};
  --aibs-border-glow-spread: ${config.borderGlowSpread}px;
}`;
    navigator.clipboard.writeText(cssText);
    setCopiedNotification(true);
    setTimeout(() => setCopiedNotification(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(5, 5, 15, 0.82)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100000,
      padding: '20px'
    }} onClick={onClose}>
      <div style={{
        background: 'linear-gradient(135deg, #0d1117 0%, #161b22 100%)',
        border: '1px solid #38bdf8',
        borderRadius: '20px',
        width: '100%',
        maxWidth: '820px',
        maxHeight: '90vh',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 35px rgba(56, 189, 248, 0.35)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif"
      }} onClick={(e) => e.stopPropagation()}>
        
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.6)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '1.6rem' }}>🎨</span>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.2rem', color: '#38bdf8', letterSpacing: '0.3px' }}>
                AI-BS Program-Wide CSS & Layout Controller
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Adjust font sizes, card padding, box radius, and visual styling across all 32+ tools live
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#21262d',
              border: '1px solid #30363d',
              color: '#cbd5e1',
              borderRadius: '8px',
              padding: '6px 12px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '1rem'
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab Selector Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '12px 24px',
          background: '#090d16',
          borderBottom: '1px solid #21262d'
        }}>
          <button
            onClick={() => setActiveTab('sliders')}
            style={{
              background: activeTab === 'sliders' ? 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)' : '#161b22',
              color: activeTab === 'sliders' ? '#ffffff' : '#94a3b8',
              border: `1px solid ${activeTab === 'sliders' ? '#38bdf8' : '#30363d'}`,
              padding: '8px 16px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>🎚️ Live Sliders</span>
          </button>

          <button
            onClick={() => setActiveTab('fonts')}
            style={{
              background: activeTab === 'fonts' ? 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)' : '#161b22',
              color: activeTab === 'fonts' ? '#ffffff' : '#94a3b8',
              border: `1px solid ${activeTab === 'fonts' ? '#38bdf8' : '#30363d'}`,
              padding: '8px 16px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>🔤 Typography & Font Style</span>
          </button>

          <button
            onClick={() => setActiveTab('presets')}
            style={{
              background: activeTab === 'presets' ? 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)' : '#161b22',
              color: activeTab === 'presets' ? '#ffffff' : '#94a3b8',
              border: `1px solid ${activeTab === 'presets' ? '#38bdf8' : '#30363d'}`,
              padding: '8px 16px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>✨ 1-Click Presets</span>
          </button>

          <div style={{ flex: 1 }} />

          <button
            onClick={handleResetToDefault}
            title="Reset all layout settings back to system standard"
            style={{
              background: '#27272a',
              color: '#f87171',
              border: '1px solid #71717a',
              padding: '6px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.78rem',
              fontWeight: 700
            }}
          >
            🔄 Reset Defaults
          </button>
        </div>

        {/* Scrollable Body Content */}
        <div style={{
          padding: '24px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          flex: 1
        }}>

          {/* SLIDERS TAB */}
          {activeTab === 'sliders' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
              
              {/* Slider 1: Global Font Scale */}
              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid #334155',
                borderRadius: '12px',
                padding: '16px 20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem' }}>🔤</span>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0' }}>Spot & System Text Scale</span>
                  </div>
                  <span style={{
                    background: '#0284c7',
                    color: '#ffffff',
                    padding: '3px 10px',
                    borderRadius: '12px',
                    fontSize: '0.85rem',
                    fontWeight: 800
                  }}>
                    {Math.round(config.fontScale * 100)}% ({Math.round(16 * config.fontScale)}px base)
                  </span>
                </div>
                <input
                  type="range"
                  min="0.75"
                  max="1.50"
                  step="0.05"
                  value={config.fontScale}
                  onChange={(e) => updateConfig('fontScale', parseFloat(e.target.value))}
                  style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                  <span>75% (Micro Compact)</span>
                  <span>100% (Default Balanced)</span>
                  <span>150% (Max Legibility)</span>
                </div>
              </div>

              {/* Slider 2: Card & Box Padding */}
              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid #334155',
                borderRadius: '12px',
                padding: '16px 20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem' }}>📦</span>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0' }}>Box, Card & Panel Padding</span>
                  </div>
                  <span style={{
                    background: '#0284c7',
                    color: '#ffffff',
                    padding: '3px 10px',
                    borderRadius: '12px',
                    fontSize: '0.85rem',
                    fontWeight: 800
                  }}>
                    {config.cardPadding}px
                  </span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="48"
                  step="2"
                  value={config.cardPadding}
                  onChange={(e) => updateConfig('cardPadding', parseInt(e.target.value, 10))}
                  style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                  <span>10px (Tight)</span>
                  <span>24px (Standard)</span>
                  <span>48px (Spacious)</span>
                </div>
              </div>

              {/* Slider 3: Corner Roundness & Border Radius */}
              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid #334155',
                borderRadius: '12px',
                padding: '16px 20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem' }}>📐</span>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0' }}>Corner Radius & Box Roundness</span>
                  </div>
                  <span style={{
                    background: '#0284c7',
                    color: '#ffffff',
                    padding: '3px 10px',
                    borderRadius: '12px',
                    fontSize: '0.85rem',
                    fontWeight: 800
                  }}>
                    {config.boxRadius}px
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="32"
                  step="2"
                  value={config.boxRadius}
                  onChange={(e) => updateConfig('boxRadius', parseInt(e.target.value, 10))}
                  style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                  <span>0px (Sharp Cyber)</span>
                  <span>16px (Smooth Modern)</span>
                  <span>32px (Pill / Organic)</span>
                </div>
              </div>

              {/* Slider 4: Grid & Spacing Gap */}
              <div style={{
                background: 'rgba(30, 41, 59, 0.4)',
                border: '1px solid #334155',
                borderRadius: '12px',
                padding: '16px 20px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem' }}>↔️</span>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#e2e8f0' }}>Grid & Component Gap Spacing</span>
                  </div>
                  <span style={{
                    background: '#0284c7',
                    color: '#ffffff',
                    padding: '3px 10px',
                    borderRadius: '12px',
                    fontSize: '0.85rem',
                    fontWeight: 800
                  }}>
                    {config.gapScale}px
                  </span>
                </div>
                <input
                  type="range"
                  min="8"
                  max="40"
                  step="2"
                  value={config.gapScale}
                  onChange={(e) => updateConfig('gapScale', parseInt(e.target.value, 10))}
                  style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
                  <span>8px (Dense)</span>
                  <span>20px (Standard)</span>
                  <span>40px (Wide)</span>
                </div>
              </div>

              {/* Dual Sliders: Glass Blur & Background Opacity */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{
                  background: 'rgba(30, 41, 59, 0.4)',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                  padding: '16px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.88rem', color: '#e2e8f0' }}>🪟 Glass Blur Depth</span>
                    <span style={{ color: '#38bdf8', fontWeight: 800 }}>{config.glassBlur}px</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="32"
                    step="2"
                    value={config.glassBlur}
                    onChange={(e) => updateConfig('glassBlur', parseInt(e.target.value, 10))}
                    style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
                  />
                </div>

                <div style={{
                  background: 'rgba(30, 41, 59, 0.4)',
                  border: '1px solid #334155',
                  borderRadius: '12px',
                  padding: '16px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.88rem', color: '#e2e8f0' }}>🎨 Panel Opacity</span>
                    <span style={{ color: '#38bdf8', fontWeight: 800 }}>{Math.round(config.glassOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.20"
                    max="0.95"
                    step="0.05"
                    value={config.glassOpacity}
                    onChange={(e) => updateConfig('glassOpacity', parseFloat(e.target.value))}
                    style={{ width: '100%', cursor: 'pointer', accentColor: '#38bdf8' }}
                  />
                </div>
              </div>

              {/* Live Card Preview Box */}
              <div style={{
                background: `rgba(30, 41, 59, ${config.glassOpacity})`,
                backdropFilter: `blur(${config.glassBlur}px)`,
                WebkitBackdropFilter: `blur(${config.glassBlur}px)`,
                borderRadius: `${config.boxRadius}px`,
                padding: `${config.cardPadding}px`,
                border: '1px solid rgba(56, 189, 248, 0.4)',
                boxShadow: `0 4px 15px rgba(0,0,0,0.2), 0 0 ${config.borderGlowSpread}px rgba(0, 229, 255, 0.4)`,
                marginTop: '10px'
              }}>
                <div style={{ fontSize: `calc(0.85rem * ${config.fontScale})`, color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Live Component Preview
                </div>
                <div style={{ fontSize: `calc(1.4rem * ${config.fontScale})`, fontWeight: 800, color: '#ffffff', margin: '6px 0' }}>
                  Stehouwer AI-BS Adaptive Workspace
                </div>
                <div style={{ fontSize: `calc(0.92rem * ${config.fontScale})`, color: '#cbd5e1', lineHeight: 1.5 }}>
                  This interactive card demonstrates your live padding, text scale, border radius, and glass opacity in real time.
                </div>
              </div>
            </div>
          )}

          {/* FONTS TAB */}
          {activeTab === 'fonts' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '4px' }}>
                Select a global typography suite for AI-BS:
              </div>
              {FONT_OPTIONS.map((font) => {
                const isSelected = config.fontFamilyKey === font.key;
                return (
                  <div
                    key={font.key}
                    onClick={() => updateConfig('fontFamilyKey', font.key)}
                    style={{
                      background: isSelected ? 'rgba(56, 189, 248, 0.15)' : '#161b22',
                      border: `2px solid ${isSelected ? '#38bdf8' : '#30363d'}`,
                      borderRadius: '12px',
                      padding: '16px 20px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s',
                      fontFamily: font.family
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '1.05rem', color: isSelected ? '#38bdf8' : '#f8fafc' }}>
                        {font.label}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '4px' }}>
                        The quick brown fox jumps over the lazy dog · 0123456789
                      </div>
                    </div>
                    {isSelected && (
                      <span style={{
                        background: '#38bdf8',
                        color: '#0f172a',
                        fontWeight: 900,
                        padding: '4px 12px',
                        borderRadius: '20px',
                        fontSize: '0.78rem'
                      }}>
                        ACTIVE
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* PRESETS TAB */}
          {activeTab === 'presets' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {LAYOUT_PRESETS.map((preset) => (
                <div
                  key={preset.key}
                  style={{
                    background: '#161b22',
                    border: '1px solid #30363d',
                    borderRadius: '14px',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '12px'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#38bdf8', marginBottom: '6px' }}>
                      {preset.label}
                    </div>
                    <div style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: 1.4 }}>
                      {preset.description}
                    </div>
                  </div>
                  <button
                    onClick={() => handleApplyPreset(preset.config)}
                    style={{
                      background: 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)',
                      color: '#ffffff',
                      border: '1px solid #38bdf8',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
                    }}
                  >
                    Apply Preset
                  </button>
                </div>
              ))}
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid #30363d',
          background: 'rgba(15, 23, 42, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <button
            onClick={handleCopyCssVariables}
            style={{
              background: '#1e293b',
              color: copiedNotification ? '#34d399' : '#cbd5e1',
              border: '1px solid #475569',
              padding: '8px 14px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.82rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>{copiedNotification ? '✅ Copied CSS Vars!' : '📋 Copy CSS Variables'}</span>
          </button>

          <button
            onClick={onClose}
            style={{
              background: 'linear-gradient(90deg, #38bdf8 0%, #0284c7 100%)',
              color: '#0f172a',
              border: 'none',
              padding: '8px 24px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 800,
              fontSize: '0.9rem',
              boxShadow: '0 4px 14px rgba(56, 189, 248, 0.4)'
            }}
          >
            Done & Save
          </button>
        </div>

      </div>
    </div>
  );
}
