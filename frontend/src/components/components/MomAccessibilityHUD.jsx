import React, { useState, useEffect } from 'react';
import './MomMode.css';

// Gentle Web Audio API sound cue
function playSoundCue(frequency = 520, duration = 0.06) {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(frequency, ctx.currentTime);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (e) {
    // Audio contexts may be blocked prior to user gesture
  }
}

export default function MomAccessibilityHUD({ 
  momMode, 
  onToggleMomMode, 
  zoomLevel = 125, 
  onZoomChange 
}) {
  const [isMinimized, setIsMinimized] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [activeTab, setActiveTab] = useState('zoom'); // 'zoom' | 'contrast' | 'font'
  
  // Persistent accessibility preferences
  const [contrastTheme, setContrastTheme] = useState(() => localStorage.getItem('aibs_mom_theme') || 'default');
  const [fontFamily, setFontFamily] = useState(() => localStorage.getItem('aibs_mom_font') || 'sans');
  const [spacingMode, setSpacingMode] = useState(() => localStorage.getItem('aibs_mom_spacing') || 'relaxed');
  const [audioCues, setAudioCues] = useState(() => localStorage.getItem('aibs_mom_audio_cues') !== 'false');
  const [speechRate, setSpeechRate] = useState(() => parseFloat(localStorage.getItem('aibs_mom_speech_rate') || '0.85'));

  // Sync classes to document.body
  useEffect(() => {
    if (!momMode) {
      document.body.classList.remove(
        'mom-theme-amber', 'mom-theme-cyan', 'mom-theme-mono',
        'mom-font-dyslexic', 'mom-font-serif',
        'mom-spacing-relaxed', 'mom-spacing-loose'
      );
      return;
    }

    // Contrast
    document.body.classList.remove('mom-theme-amber', 'mom-theme-cyan', 'mom-theme-mono');
    if (contrastTheme !== 'default') {
      document.body.classList.add(`mom-theme-${contrastTheme}`);
    }

    // Font
    document.body.classList.remove('mom-font-dyslexic', 'mom-font-serif');
    if (fontFamily !== 'sans') {
      document.body.classList.add(`mom-font-${fontFamily}`);
    }

    // Spacing
    document.body.classList.remove('mom-spacing-relaxed', 'mom-spacing-loose');
    if (spacingMode !== 'standard') {
      document.body.classList.add(`mom-spacing-${spacingMode}`);
    }
  }, [momMode, contrastTheme, fontFamily, spacingMode]);

  if (!momMode) return null;

  const triggerFeedback = (freq = 520) => {
    if (audioCues) playSoundCue(freq);
  };

  const zoomLevels = [100, 115, 125, 140, 160];

  const handleZoomIn = () => {
    triggerFeedback(600);
    const currentIndex = zoomLevels.indexOf(zoomLevel);
    if (currentIndex < zoomLevels.length - 1) {
      onZoomChange(zoomLevels[currentIndex + 1]);
    }
  };

  const handleZoomOut = () => {
    triggerFeedback(450);
    const currentIndex = zoomLevels.indexOf(zoomLevel);
    if (currentIndex > 0) {
      onZoomChange(zoomLevels[currentIndex - 1]);
    }
  };

  const handleSetTheme = (theme) => {
    triggerFeedback(540);
    setContrastTheme(theme);
    localStorage.setItem('aibs_mom_theme', theme);
  };

  const handleSetFont = (font) => {
    triggerFeedback(540);
    setFontFamily(font);
    localStorage.setItem('aibs_mom_font', font);
  };

  const handleSetSpacing = (spacing) => {
    triggerFeedback(540);
    setSpacingMode(spacing);
    localStorage.setItem('aibs_mom_spacing', spacing);
  };

  const toggleAudioCues = () => {
    const next = !audioCues;
    if (next) playSoundCue(700);
    setAudioCues(next);
    localStorage.setItem('aibs_mom_audio_cues', next.toString());
  };

  const handleReadScreen = () => {
    if ('speechSynthesis' in window) {
      if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
        setIsSpeaking(false);
        return;
      }

      const mainContent = document.querySelector('.subinterface-content') || document.querySelector('main') || document.body;
      const textToRead = mainContent?.innerText?.slice(0, 600) || "Welcome to AI-BS Mom Version. You are on the main dashboard.";
      
      const utterance = new SpeechSynthesisUtterance(textToRead);
      utterance.rate = speechRate;
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      
      setIsSpeaking(true);
      triggerFeedback(660);
      speechSynthesis.speak(utterance);
    } else {
      alert("Speech synthesis is not supported on this browser.");
    }
  };

  if (isMinimized) {
    return (
      <div className="mom-hud-container">
        <button 
          className="mom-hud-minimized-badge"
          onClick={() => {
            triggerFeedback(600);
            setIsMinimized(false);
          }}
          title="Open Mom Accessibility Controls"
        >
          <span>🌸 MOM CONTROLS ({zoomLevel}%)</span>
          <span>🔍</span>
        </button>
      </div>
    );
  }

  return (
    <div className="mom-hud-container">
      <div className="mom-hud-card">
        {/* Header */}
        <div className="mom-hud-header">
          <span className="mom-hud-title">
            <span>🌸</span>
            <span>MOM ACCESSIBILITY HUD</span>
          </span>
          <button 
            className="mom-hud-close-btn"
            onClick={() => {
              triggerFeedback(400);
              setIsMinimized(true);
            }}
            title="Minimize Controls"
          >
            ✕
          </button>
        </div>

        {/* Sub-Tab Switcher */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '12px', background: 'rgba(0,0,0,0.3)', padding: '3px', borderRadius: '8px' }}>
          <button
            onClick={() => { triggerFeedback(500); setActiveTab('zoom'); }}
            style={{
              flex: 1, padding: '6px 4px', fontSize: '0.78rem', fontWeight: 800,
              background: activeTab === 'zoom' ? '#38bdf8' : 'transparent',
              color: activeTab === 'zoom' ? '#0f172a' : '#cbd5e1',
              border: 'none', borderRadius: '6px', cursor: 'pointer'
            }}
          >
            🔍 Zoom
          </button>
          <button
            onClick={() => { triggerFeedback(500); setActiveTab('contrast'); }}
            style={{
              flex: 1, padding: '6px 4px', fontSize: '0.78rem', fontWeight: 800,
              background: activeTab === 'contrast' ? '#fde047' : 'transparent',
              color: activeTab === 'contrast' ? '#0f172a' : '#cbd5e1',
              border: 'none', borderRadius: '6px', cursor: 'pointer'
            }}
          >
            🎨 Color
          </button>
          <button
            onClick={() => { triggerFeedback(500); setActiveTab('font'); }}
            style={{
              flex: 1, padding: '6px 4px', fontSize: '0.78rem', fontWeight: 800,
              background: activeTab === 'font' ? '#4ade80' : 'transparent',
              color: activeTab === 'font' ? '#0f172a' : '#cbd5e1',
              border: 'none', borderRadius: '6px', cursor: 'pointer'
            }}
          >
            📖 Font
          </button>
        </div>

        {/* TAB 1: ZOOM & SPEECH */}
        {activeTab === 'zoom' && (
          <>
            <div className="mom-hud-section-label">🔍 INSTANT PAGE ZOOM</div>
            <div className="mom-hud-zoom-row">
              <button 
                className="mom-hud-zoom-btn"
                onClick={handleZoomOut}
                disabled={zoomLevel <= 100}
                title="Zoom Out (Make Smaller)"
              >
                −
              </button>
              <span className="mom-hud-zoom-display">{zoomLevel}%</span>
              <button 
                className="mom-hud-zoom-btn"
                onClick={handleZoomIn}
                disabled={zoomLevel >= 160}
                title="Zoom In (Make Bigger)"
              >
                +
              </button>
            </div>

            <div className="mom-hud-actions-grid" style={{ marginBottom: '10px' }}>
              <button 
                className="mom-hud-action-btn"
                onClick={() => { triggerFeedback(500); onZoomChange(100); }}
                title="Reset Zoom to 100%"
              >
                <span>🔄 100% Reset</span>
              </button>
              <button 
                className="mom-hud-action-btn"
                onClick={handleReadScreen}
                title="Read screen text aloud"
              >
                <span>{isSpeaking ? '⏹️ Stop Voice' : '🔊 Read Aloud'}</span>
              </button>
            </div>

            {/* Speech Rate & Audio Cues */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.78rem', color: '#cbd5e1', padding: '6px 8px', background: 'rgba(0,0,0,0.25)', borderRadius: '6px', marginBottom: '10px' }}>
              <span>🔊 Audio Click Tones</span>
              <button
                onClick={toggleAudioCues}
                style={{
                  background: audioCues ? '#4ade80' : '#475569',
                  color: audioCues ? '#052e16' : '#f8fafc',
                  border: 'none', borderRadius: '4px', padding: '3px 8px', fontWeight: 800, fontSize: '0.72rem', cursor: 'pointer'
                }}
              >
                {audioCues ? 'ON' : 'OFF'}
              </button>
            </div>
          </>
        )}

        {/* TAB 2: CONTRAST THEMES */}
        {activeTab === 'contrast' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '10px' }}>
            <div className="mom-hud-section-label">🎨 HIGH CONTRAST PALETTE</div>
            
            <button
              onClick={() => handleSetTheme('default')}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 700,
                background: contrastTheme === 'default' ? '#1e293b' : 'rgba(0,0,0,0.3)',
                color: '#ffffff', border: `2px solid ${contrastTheme === 'default' ? '#38bdf8' : '#334155'}`, cursor: 'pointer'
              }}
            >
              <span>🌙 Standard High-Contrast Dark</span>
              {contrastTheme === 'default' && <span>✓</span>}
            </button>

            <button
              onClick={() => handleSetTheme('amber')}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 700,
                background: contrastTheme === 'amber' ? '#451a03' : 'rgba(0,0,0,0.3)',
                color: '#fef08a', border: `2px solid ${contrastTheme === 'amber' ? '#facc15' : '#334155'}`, cursor: 'pointer'
              }}
            >
              <span>🟡 Ultra Low-Glare Amber</span>
              {contrastTheme === 'amber' && <span>✓</span>}
            </button>

            <button
              onClick={() => handleSetTheme('cyan')}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 700,
                background: contrastTheme === 'cyan' ? '#082f49' : 'rgba(0,0,0,0.3)',
                color: '#7dd3fc', border: `2px solid ${contrastTheme === 'cyan' ? '#38bdf8' : '#334155'}`, cursor: 'pointer'
              }}
            >
              <span>🔵 Deep Navy & Crisp Cyan</span>
              {contrastTheme === 'cyan' && <span>✓</span>}
            </button>

            <button
              onClick={() => handleSetTheme('mono')}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 700,
                background: contrastTheme === 'mono' ? '#000000' : 'rgba(0,0,0,0.3)',
                color: '#ffffff', border: `2px solid ${contrastTheme === 'mono' ? '#ffffff' : '#334155'}`, cursor: 'pointer'
              }}
            >
              <span>☀️ Pure Black & White Mono</span>
              {contrastTheme === 'mono' && <span>✓</span>}
            </button>
          </div>
        )}

        {/* TAB 3: FONT & SPACING */}
        {activeTab === 'font' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '10px' }}>
            <div className="mom-hud-section-label">📖 TYPEFACE LEGIBILITY</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
              <button
                onClick={() => handleSetFont('sans')}
                style={{
                  padding: '8px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700,
                  background: fontFamily === 'sans' ? '#1e293b' : 'rgba(0,0,0,0.3)',
                  color: '#ffffff', border: `2px solid ${fontFamily === 'sans' ? '#38bdf8' : '#334155'}`, cursor: 'pointer'
                }}
              >
                Clean Sans
              </button>
              <button
                onClick={() => handleSetFont('dyslexic')}
                style={{
                  padding: '8px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700,
                  fontFamily: 'Verdana, sans-serif',
                  background: fontFamily === 'dyslexic' ? '#1e293b' : 'rgba(0,0,0,0.3)',
                  color: '#fde047', border: `2px solid ${fontFamily === 'dyslexic' ? '#fde047' : '#334155'}`, cursor: 'pointer'
                }}
              >
                Dyslexia-Aid
              </button>
            </div>

            <div className="mom-hud-section-label" style={{ marginTop: '6px' }}>📐 LINE AIR & BREATHING ROOM</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
              <button
                onClick={() => handleSetSpacing('standard')}
                style={{
                  padding: '6px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700,
                  background: spacingMode === 'standard' ? '#0f766e' : 'rgba(0,0,0,0.3)',
                  color: '#ffffff', border: `1px solid ${spacingMode === 'standard' ? '#2dd4bf' : '#334155'}`, cursor: 'pointer'
                }}
              >
                Normal
              </button>
              <button
                onClick={() => handleSetSpacing('relaxed')}
                style={{
                  padding: '6px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700,
                  background: spacingMode === 'relaxed' ? '#0f766e' : 'rgba(0,0,0,0.3)',
                  color: '#ffffff', border: `1px solid ${spacingMode === 'relaxed' ? '#2dd4bf' : '#334155'}`, cursor: 'pointer'
                }}
              >
                Relaxed
              </button>
              <button
                onClick={() => handleSetSpacing('loose')}
                style={{
                  padding: '6px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700,
                  background: spacingMode === 'loose' ? '#0f766e' : 'rgba(0,0,0,0.3)',
                  color: '#ffffff', border: `1px solid ${spacingMode === 'loose' ? '#2dd4bf' : '#334155'}`, cursor: 'pointer'
                }}
              >
                Loose
              </button>
            </div>
          </div>
        )}

        {/* Exit Mom Mode Button */}
        <button 
          className="mom-hud-action-btn"
          style={{ width: '100%', background: '#7f1d1d', color: '#fecaca', borderColor: '#ef4444', marginTop: '4px' }}
          onClick={() => {
            triggerFeedback(350);
            onToggleMomMode();
          }}
          title="Turn off Mom Mode and return to standard developer view"
        >
          <span>Exit Mom Version</span>
        </button>
      </div>
    </div>
  );
}
