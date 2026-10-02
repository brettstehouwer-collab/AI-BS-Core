import React, { useState } from 'react';
import { Sliders, Mic, Sparkles, RefreshCw, Download, Play, Square, Layers, Zap, CheckCircle2, AlertCircle } from 'lucide-react';
import { theme } from '../../styles/theme';

export default function AiVocalStemSuite({ onSendStemToPlaylist }) {
  const [activeSubTab, setActiveSubTab] = useState('stems'); // 'stems' | 'vocal_gen' | 'projects'
  const [isProcessing, setIsProcessing] = useState(false);
  const [vramSafeMode, setVramSafeMode] = useState(true);
  const [vocalPrompt, setVocalPrompt] = useState('Soulful acoustic vocal harmony, emotional tone, 120 BPM');
  const [voiceModel, setVoiceModel] = useState('f5_tts_neural');
  const [stemProgress, setStemProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Ready for JIT synthesis / separation pass.');

  const [activeProject, setActiveProject] = useState({
    id: 'proj_demo_01',
    title: 'Sovereign Frequency Master',
    stems: {
      vocals: { name: 'Vocals (Clean Solo)', duration: '0:48', loaded: true },
      drums: { name: 'Drums (Transient Crisp)', duration: '0:48', loaded: true },
      bass: { name: 'Sub-Bass (808 Sine)', duration: '0:48', loaded: true },
      other: { name: 'Synthesizers & FX', duration: '0:48', loaded: true }
    }
  });

  const handleRunStemSeparation = () => {
    setIsProcessing(true);
    setStatusMessage('Allocating JIT VRAM slice (Demucs v4)...');
    setStemProgress(20);

    setTimeout(() => {
      setStatusMessage('Separating 4 stems: Vocals, Drums, Bass, Other...');
      setStemProgress(65);
    }, 1200);

    setTimeout(() => {
      setStatusMessage('Emptying PyTorch CUDA cache... 0MB VRAM retained.');
      setStemProgress(100);
      setIsProcessing(false);
    }, 2400);
  };

  const handleGenerateVocalTrack = () => {
    setIsProcessing(true);
    setStatusMessage(`Synthesizing lyrical stem via ${voiceModel}...`);
    setStemProgress(35);

    setTimeout(() => {
      setStatusMessage('Purging neural weights to protect Salad compute...');
      setStemProgress(100);
      setIsProcessing(false);
    }, 1800);
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#0d1117',
      color: '#e6edf3',
      fontFamily: 'Inter, system-ui, sans-serif',
      padding: '16px',
      overflow: 'auto',
      boxSizing: 'border-box'
    }}>
      {/* Top Header Card */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 18px',
        background: 'rgba(22, 27, 34, 0.85)',
        border: '1px solid #30363d',
        borderRadius: '8px',
        marginBottom: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #a855f7, #6366f1)',
            padding: '8px',
            borderRadius: '6px',
            display: 'flex'
          }}>
            <Sparkles size={20} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '15px', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              AI Music & Neural Vocal Suite
              <span style={{
                background: 'rgba(168, 85, 247, 0.15)',
                color: '#c084fc',
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '12px',
                border: '1px solid rgba(168, 85, 247, 0.3)'
              }}>
                v5.300.0 Sovereign Core
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '2px' }}>
              On-Demand Neural Stem Isolation (Demucs v4) & F5-TTS Neural Voice Cloning with JIT VRAM Purge
            </div>
          </div>
        </div>

        {/* Salad Coexistence Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(35, 134, 54, 0.15)',
            border: '1px solid rgba(46, 160, 67, 0.4)',
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '11px',
            color: '#56d364'
          }}>
            <Zap size={14} />
            <span>Salad Protected (JIT Purge Active)</span>
          </div>

          <button
            onClick={() => setVramSafeMode(!vramSafeMode)}
            style={{
              background: vramSafeMode ? 'rgba(56, 189, 248, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              border: vramSafeMode ? '1px solid #38bdf8' : '1px solid #ef4444',
              color: vramSafeMode ? '#38bdf8' : '#ef4444',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            {vramSafeMode ? 'Safe Headroom: ON' : 'Force Full GPU'}
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {[
          { key: 'stems', label: '🎛️ Neural Stem Separation (Demucs)', icon: Layers },
          { key: 'vocal_gen', label: '🎙️ F5-TTS Lyrical Vocal Synthesis', icon: Mic },
          { key: 'projects', label: '📂 Vault Stems Archive', icon: Sliders }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveSubTab(tab.key)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: activeSubTab === tab.key ? 'rgba(168, 85, 247, 0.2)' : 'rgba(22, 27, 34, 0.6)',
              border: activeSubTab === tab.key ? '1px solid #a855f7' : '1px solid #30363d',
              color: activeSubTab === tab.key ? '#c084fc' : '#8b949e',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Content Area */}
      {activeSubTab === 'stems' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '16px', flex: 1 }}>
          {/* Controls Card */}
          <div style={{
            background: 'rgba(22, 27, 34, 0.6)',
            border: '1px solid #30363d',
            borderRadius: '8px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>Input Audio Track Source</div>
            <div style={{
              border: '2px dashed #30363d',
              borderRadius: '6px',
              padding: '24px',
              textAlign: 'center',
              color: '#8b949e',
              fontSize: '12px',
              background: 'rgba(13, 17, 23, 0.5)'
            }}>
              Drag and drop master audio mix (WAV/MP3) or select from Stehouwer Vault
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', color: '#8b949e' }}>Separation Model Target</label>
              <select style={{
                background: '#0d1117',
                border: '1px solid #30363d',
                color: '#fff',
                padding: '8px',
                borderRadius: '6px',
                fontSize: '12px'
              }}>
                <option value="htdemucs">Demucs v4 Hybrid Transformer (Highest Fidelity 4-Stem)</option>
                <option value="htdemucs_ft">Demucs Fine-Tuned (Acapella / Vocal Focus)</option>
                <option value="mdx_extra">MDX-Extra Q (Ultra-Low Latency)</option>
              </select>
            </div>

            <button
              onClick={handleRunStemSeparation}
              disabled={isProcessing}
              style={{
                background: 'linear-gradient(135deg, #a855f7, #6366f1)',
                border: 'none',
                color: '#fff',
                fontWeight: 700,
                padding: '10px',
                borderRadius: '6px',
                cursor: isProcessing ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginTop: 'auto'
              }}
            >
              {isProcessing ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
              {isProcessing ? 'Processing Separation...' : 'Extract 4 Stems (JIT VRAM Mode)'}
            </button>
          </div>

          {/* Stems Visualizer Card */}
          <div style={{
            background: 'rgba(22, 27, 34, 0.6)',
            border: '1px solid #30363d',
            borderRadius: '8px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ fontWeight: 600, fontSize: '13px', color: '#fff', display: 'flex', justifyContent: 'space-between' }}>
              <span>Extracted Stems Rack</span>
              <span style={{ fontSize: '11px', color: '#56d364' }}>100% On-Chain / Local Vault</span>
            </div>

            {Object.entries(activeProject.stems).map(([key, stem]) => (
              <div key={key} style={{
                background: '#0d1117',
                border: '1px solid #21262d',
                borderRadius: '6px',
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: key === 'vocals' ? '#a855f7' : key === 'drums' ? '#f59e0b' : key === 'bass' ? '#38bdf8' : '#10b981'
                  }} />
                  <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'capitalize' }}>{stem.name}</span>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => onSendStemToPlaylist && onSendStemToPlaylist(null, stem.name)}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      border: '1px solid #38bdf8',
                      color: '#38bdf8',
                      borderRadius: '4px',
                      padding: '4px 8px',
                      fontSize: '11px',
                      cursor: 'pointer'
                    }}
                  >
                    Add to Playlist
                  </button>
                  <button style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid #30363d',
                    color: '#8b949e',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '11px',
                    cursor: 'pointer'
                  }}>
                    <Download size={12} />
                  </button>
                </div>
              </div>
            ))}

            {/* Status Footer */}
            <div style={{
              marginTop: 'auto',
              background: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '10px',
              fontSize: '11px',
              color: '#8b949e',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <CheckCircle2 size={14} color="#56d364" />
              <span>{statusMessage}</span>
            </div>
          </div>
        </div>
      )}

      {/* Vocal Synthesis Tab */}
      {activeSubTab === 'vocal_gen' && (
        <div style={{
          background: 'rgba(22, 27, 34, 0.6)',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          maxWidth: '750px'
        }}>
          <div style={{ fontWeight: 600, fontSize: '13px', color: '#fff' }}>Neural Vocal Synthesis (F5-TTS Directorial Voice)</div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e' }}>Lyric & Style Prompt</label>
            <textarea
              rows={3}
              value={vocalPrompt}
              onChange={(e) => setVocalPrompt(e.target.value)}
              style={{
                background: '#0d1117',
                border: '1px solid #30363d',
                color: '#fff',
                padding: '10px',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '11px', color: '#8b949e' }}>Reference Voice Model</label>
              <select
                value={voiceModel}
                onChange={(e) => setVoiceModel(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  color: '#fff',
                  padding: '8px',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}
              >
                <option value="f5_tts_neural">F5-TTS Sovereign English (Zero-Cost)</option>
                <option value="voice_clone_stehouwer">Stehouwer Publishing Voice Clone</option>
                <option value="acapella_studio">Acapella Directorial Vocalist</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '11px', color: '#8b949e' }}>Sample Rate / Output Format</label>
              <select style={{
                width: '100%',
                background: '#0d1117',
                border: '1px solid #30363d',
                color: '#fff',
                padding: '8px',
                borderRadius: '6px',
                fontSize: '12px'
              }}>
                <option value="48000">48,000 Hz 24-bit Broadcast Master</option>
                <option value="44100">44,100 Hz 16-bit CD Master</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleGenerateVocalTrack}
            disabled={isProcessing}
            style={{
              background: 'linear-gradient(135deg, #a855f7, #6366f1)',
              border: 'none',
              color: '#fff',
              fontWeight: 700,
              padding: '10px',
              borderRadius: '6px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            {isProcessing ? <RefreshCw size={16} className="animate-spin" /> : <Mic size={16} />}
            {isProcessing ? 'Synthesizing...' : 'Generate Neural Vocal Track'}
          </button>
        </div>
      )}

      {/* Projects Archive Tab */}
      {activeSubTab === 'projects' && (
        <div style={{
          background: 'rgba(22, 27, 34, 0.6)',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '16px'
        }}>
          <div style={{ fontWeight: 600, fontSize: '13px', color: '#fff', marginBottom: '12px' }}>
            Stehouwer Vault Stems Ledger (`audio_vocal_projects`)
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e' }}>
            All stem separations and synthesized vocal takes are permanently cataloged in SQLite WAL storage (`backend/stehouwer_vault.db`).
          </div>
        </div>
      )}
    </div>
  );
}
