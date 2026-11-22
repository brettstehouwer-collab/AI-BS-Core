import React, { useState, useEffect } from 'react';
import { Sliders, Activity, Flame, Waves, Zap, Cpu } from 'lucide-react';
import { theme } from '../styles/theme';

const BACKEND_VST_URL = 'http://127.0.0.1:8013';

const THEME_CONFIG = {
  aggressive: { color: '#ff3366', icon: Flame, label: 'AGGRESSIVE', desc: 'High Drive, Tight Gate, Saturating Harmonics' },
  calm: { color: '#00e5ff', icon: Waves, label: 'CALM', desc: 'Deep Reverb, Warm 1.2kHz Filter, Spatial Echo' },
  hype: { color: '#ffb700', icon: Zap, label: 'HYPE', desc: 'Fast Modulation, Open 12kHz Cutoff, Resonant Lead' },
  analytical: { color: '#a855f7', icon: Cpu, label: 'ANALYTICAL', desc: 'Pristine 0% THD, Linear Phase, Studio Transparency' },
  neutral: { color: '#94a3b8', icon: Activity, label: 'NEUTRAL', desc: 'Default Pass-Through Acoustic Profile' }
};

export const ThematicVstVisualizer = ({ compact = false }) => {
  const [vstState, setVstState] = useState({ theme: 'neutral', active_modulations: {} });
  const [isOnline, setIsOnline] = useState(false);
  const [isTriggering, setIsTriggering] = useState(false);

  const fetchState = async () => {
    try {
      const res = await fetch(`${BACKEND_VST_URL}/api/vst/theme-state`);
      if (res.ok) {
        const data = await res.json();
        setVstState(data);
        setIsOnline(true);
      } else {
        setIsOnline(false);
      }
    } catch {
      setIsOnline(false);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 1500);
    return () => clearInterval(interval);
  }, []);

  const triggerTheme = async (themeName) => {
    setIsTriggering(true);
    try {
      const res = await fetch(`${BACKEND_VST_URL}/api/vst/trigger-theme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: themeName })
      });
      if (res.ok) {
        const data = await res.json();
        setVstState({ theme: data.theme, active_modulations: data.modulations });
      }
    } catch (e) {
      console.warn('Failed to trigger VST theme:', e);
    } finally {
      setIsTriggering(false);
    }
  };

  const currentThemeKey = vstState.theme?.toLowerCase() || 'neutral';
  const themeInfo = THEME_CONFIG[currentThemeKey] || THEME_CONFIG.neutral;
  const ThemeIcon = themeInfo.icon;
  const mods = vstState.active_modulations || {};

  if (compact) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        background: 'rgba(10, 15, 25, 0.85)',
        border: `1px solid ${themeInfo.color}44`,
        borderRadius: '6px',
        padding: '4px 10px',
        boxShadow: `0 0 12px ${themeInfo.color}22`
      }}>
        <ThemeIcon size={14} color={themeInfo.color} />
        <span style={{ fontSize: '11px', fontWeight: 'bold', color: themeInfo.color, letterSpacing: '0.05em' }}>
          VST THEME: {themeInfo.label}
        </span>
        <div style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          background: isOnline ? '#10b981' : '#ef4444',
          boxShadow: isOnline ? '0 0 6px #10b981' : 'none'
        }} title={isOnline ? 'Port 8013 Connected' : 'VST Daemon Offline'} />
      </div>
    );
  }

  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.95)',
      border: `1px solid ${themeInfo.color}66`,
      borderRadius: '8px',
      padding: '16px',
      color: '#fff',
      boxShadow: `0 0 20px ${themeInfo.color}18`,
      backdropFilter: 'blur(8px)',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={18} color={theme.colors?.accent || '#00e5ff'} />
          <span style={{ fontSize: '13px', fontWeight: 'bold', letterSpacing: '0.08em', color: '#e2e8f0' }}>
            THEATRICAL VST3 DSP TELEMETRY
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: isOnline ? '#10b981' : '#ef4444',
            boxShadow: isOnline ? '0 0 8px #10b981' : 'none'
          }} />
          <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
            PORT 8013 {isOnline ? 'LIVE' : 'STANDBY'}
          </span>
        </div>
      </div>

      {/* Active Theme Card */}
      <div style={{
        background: `linear-gradient(135deg, ${themeInfo.color}15, rgba(0,0,0,0.4))`,
        border: `1px solid ${themeInfo.color}44`,
        borderRadius: '6px',
        padding: '12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            background: `${themeInfo.color}25`,
            padding: '8px',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ThemeIcon size={22} color={themeInfo.color} />
          </div>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 'bold', color: themeInfo.color, letterSpacing: '0.05em' }}>
              {themeInfo.label} DSP MODE
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              {themeInfo.desc}
            </div>
          </div>
        </div>

        {/* Quick Trigger Buttons */}
        <div style={{ display: 'flex', gap: '6px' }}>
          {['aggressive', 'calm', 'hype', 'analytical'].map((t) => (
            <button
              key={t}
              onClick={() => triggerTheme(t)}
              disabled={isTriggering}
              style={{
                background: currentThemeKey === t ? THEME_CONFIG[t].color : 'rgba(255,255,255,0.06)',
                color: currentThemeKey === t ? '#000' : '#cbd5e1',
                border: `1px solid ${THEME_CONFIG[t].color}44`,
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                textTransform: 'uppercase'
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Parameter Meters */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: '10px'
      }}>
        {Object.entries(mods).map(([key, val]) => {
          const displayVal = typeof val === 'number' ? (val > 10 ? `${val} Hz` : `${Math.round(val * 100)}%`) : JSON.stringify(val);
          const percent = typeof val === 'number' ? (val > 10 ? Math.min(100, Math.round((val / 15000) * 100)) : Math.round(val * 100)) : 50;

          return (
            <div key={key} style={{
              background: 'rgba(0,0,0,0.4)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '4px',
              padding: '8px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>
                <span>{key}</span>
                <span style={{ color: themeInfo.color, fontFamily: 'monospace', fontWeight: 'bold' }}>{displayVal}</span>
              </div>
              <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  width: `${percent}%`,
                  height: '100%',
                  background: themeInfo.color,
                  boxShadow: `0 0 8px ${themeInfo.color}`,
                  transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ThematicVstVisualizer;
