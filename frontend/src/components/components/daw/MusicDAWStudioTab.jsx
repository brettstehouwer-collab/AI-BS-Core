import React, { useState, useRef } from 'react';
import { Play, Square, Pause, Volume2, Cpu, Download, Layout, Grid, Sliders, Music, Radio, Film, Video } from 'lucide-react';
import { theme } from '../../styles/theme';
import { useDawStore } from './dawStore';
import * as Tone from 'tone';

import Browser from './Browser';
import ChannelRack from './ChannelRack';
import PianoRoll from './PianoRoll';
import Playlist from './Playlist';
import Mixer from './Mixer';
import VideoPreviewMonitor from './VideoPreviewMonitor';
import ThematicVstVisualizer from '../ThematicVstVisualizer';
import StehouwerWaveStudio from './StehouwerWaveStudio';

function audioBufferToWavBlob(buffer) {
  const numOfChan = buffer.numberOfChannels;
  const length = buffer.length * numOfChan * 2 + 44;
  const out = new DataView(new ArrayBuffer(length));
  const channels = [];
  const sampleRate = buffer.sampleRate;
  let offset = 0;
  let pos = 0;

  function writeString(str) {
    for (let i = 0; i < str.length; i++) {
      out.setUint8(pos++, str.charCodeAt(i));
    }
  }

  function setUint16(data) {
    out.setUint16(pos, data, true);
    pos += 2;
  }

  function setUint32(data) {
    out.setUint32(pos, data, true);
    pos += 4;
  }

  writeString('RIFF');
  setUint32(length - 8);
  writeString('WAVE');
  writeString('fmt ');
  setUint32(16);
  setUint16(1);
  setUint16(numOfChan);
  setUint32(sampleRate);
  setUint32(sampleRate * 2 * numOfChan);
  setUint16(numOfChan * 2);
  setUint16(16);
  writeString('data');
  setUint32(length - pos - 4);

  for (let i = 0; i < buffer.numberOfChannels; i++) {
    channels.push(buffer.getChannelData(i));
  }

  while (offset < buffer.length) {
    for (let i = 0; i < numOfChan; i++) {
      let sample = Math.max(-1, Math.min(1, channels[i][offset]));
      sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
      out.setInt16(pos, sample, true);
      pos += 2;
    }
    offset++;
  }

  return new Blob([out.buffer], { type: 'audio/wav' });
}

const MusicDAWStudioTab = () => {
  const isPlaying = useDawStore(state => state.isPlaying);
  const togglePlay = useDawStore(state => state.togglePlay);
  const bpm = useDawStore(state => state.bpm);
  const setBpm = useDawStore(state => state.setBpm);
  const playMode = useDawStore(state => state.playMode);
  const setPlayMode = useDawStore(state => state.setPlayMode);
  const isMetronomeOn = useDawStore(state => state.isMetronomeOn);
  const toggleMetronome = useDawStore(state => state.toggleMetronome);
  const masterVolume = useDawStore(state => state.masterVolume);
  const setMasterVolume = useDawStore(state => state.setMasterVolume);
  const activeView = useDawStore(state => state.activeView);
  const setActiveView = useDawStore(state => state.setActiveView);
  const currentStep = useDawStore(state => state.currentStep);
  const currentBar = useDawStore(state => state.currentBar);

  const [isExporting, setIsExporting] = useState(false);
  const [exportType, setExportType] = useState('wav'); // 'wav' or 'mp4'
  const [browserWidth, setBrowserWidth] = useState(320);
  const [isBrowserExpanded, setIsBrowserExpanded] = useState(false);
  const [isTheater, setIsTheater] = useState(false);

  const handleTogglePlay = async () => {
    try {
      if (Tone.context.state !== 'running') {
        await Tone.start();
      }
    } catch {}
    togglePlay();
  };

  const handleToggleTheater = () => {
    setIsTheater(prev => !prev);
  };

  const handleToggleBrowserExpand = () => {
    if (isBrowserExpanded) {
      setBrowserWidth(320);
      setIsBrowserExpanded(false);
    } else {
      setBrowserWidth(480);
      setIsBrowserExpanded(true);
    }
  };

  const handleExportWAV = async () => {
    setIsExporting(true);
    try {
      const buffer = await Tone.Offline(async () => {
        const kick = new Tone.MembraneSynth().toDestination();
        kick.triggerAttackRelease('C1', '8n', 0);
        kick.triggerAttackRelease('C1', '8n', 0.5);
        kick.triggerAttackRelease('C1', '8n', 1.0);
        kick.triggerAttackRelease('C1', '8n', 1.5);
      }, 4);

      const blob = audioBufferToWavBlob(buffer.get());
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AI-BS_Beat_${Date.now()}.wav`;
      a.click();
    } catch (err) {
      console.warn('WAV export error:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportMasterMP4 = async () => {
    setIsExporting(true);
    try {
      const res = await fetch('http://localhost:8080/api/studio/render_master_video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: `AI-BS_Multimedia_${Date.now()}` })
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Master Video Rendered Successfully!\nFile: ${data.rendered_file}\nEngine: ${data.engine}`);
      }
    } catch (e) {
      console.warn('Master MP4 export warning:', e);
    } finally {
      setIsExporting(false);
    }
  };

  const centerCanvasRef = useRef(null);

  const handleGlobalWheel = (e) => {
    const target = e.target;
    // Let elements with their own internal scrollbars scroll naturally
    if (target && target.closest && (target.closest('.browser-sound-list') || target.closest('.channel-rack-steps-container'))) {
      return;
    }
    if (centerCanvasRef.current) {
      centerCanvasRef.current.scrollTop += e.deltaY;
    }
  };

  return (
    <div 
      onWheel={handleGlobalWheel}
      style={{
        width: '100%',
        minHeight: '750px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: '#07090e',
        color: '#c9d1d9',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}
    >
      
      {/* TOP MASTER TRANSPORT BAR */}
      <div style={{
        height: '52px',
        background: 'rgba(13, 16, 22, 0.98)',
        borderBottom: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: '14px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.5)',
        zIndex: 10
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Music size={18} color={theme.colors.accent} />
          <span style={{ fontWeight: 'bold', fontSize: '13px', color: '#fff', letterSpacing: '0.5px' }}>
            AI-BS <span style={{ color: theme.colors.accent }}>STUDIO COMBO</span>
          </span>
        </div>

        <div style={{ height: '24px', width: '1px', background: '#30363d' }} />

        {/* Playback Controls */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button 
            onClick={handleTogglePlay}
            title={isPlaying ? 'Pause Playback' : 'Start Playback'}
            style={{ 
              background: isPlaying ? 'rgba(94, 255, 123, 0.25)' : 'rgba(255,255,255,0.06)', 
              border: isPlaying ? '1px solid #5eff7b' : '1px solid rgba(255,255,255,0.12)', 
              color: isPlaying ? '#5eff7b' : '#fff',
              padding: '6px 14px',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              boxShadow: isPlaying ? '0 0 12px rgba(94, 255, 123, 0.4)' : 'none',
              fontWeight: 'bold'
            }}>
            {isPlaying ? <Pause size={15} /> : <Play size={15} fill="#fff" />}
          </button>

          <button 
            onClick={() => { if (isPlaying) togglePlay(); }}
            title="Stop & Reset Playhead"
            style={{ 
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              color: '#fff',
              padding: '6px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center' 
            }}>
            <Square size={14} fill="#fff" />
          </button>
        </div>

        {/* Mode Toggle: PAT vs SONG */}
        <div style={{ display: 'flex', background: '#000', borderRadius: '4px', border: '1px solid #30363d', padding: '2px' }}>
          <button
            onClick={() => setPlayMode('PAT')}
            style={{
              background: playMode === 'PAT' ? theme.colors.accent : 'transparent',
              color: playMode === 'PAT' ? '#000' : '#888',
              border: 'none',
              borderRadius: '2px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            PAT
          </button>
          <button
            onClick={() => setPlayMode('SONG')}
            style={{
              background: playMode === 'SONG' ? '#5eff7b' : 'transparent',
              color: playMode === 'SONG' ? '#000' : '#888',
              border: 'none',
              borderRadius: '2px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            SONG
          </button>
        </div>

        {/* Tempo Controller */}
        <div style={{ display: 'flex', alignItems: 'center', background: '#000', padding: '4px 10px', borderRadius: '4px', border: '1px solid #30363d' }}>
          <span style={{ fontSize: '9px', color: '#888', marginRight: '8px', fontWeight: 'bold' }}>BPM</span>
          <input 
            type="number" 
            min="60"
            max="220"
            value={bpm} 
            onChange={(e) => setBpm(Number(e.target.value))}
            style={{ background: 'transparent', border: 'none', color: theme.colors.accent, width: '42px', fontSize: '14px', fontFamily: 'monospace', outline: 'none', fontWeight: 'bold' }}
          />
        </div>

        {/* Metronome */}
        <button
          onClick={toggleMetronome}
          style={{
            background: isMetronomeOn ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255,255,255,0.05)',
            border: isMetronomeOn ? `1px solid ${theme.colors.accent}` : '1px solid rgba(255,255,255,0.1)',
            color: isMetronomeOn ? theme.colors.accent : '#888',
            borderRadius: '4px',
            padding: '5px 10px',
            fontSize: '11px',
            fontWeight: 'bold',
            cursor: 'pointer'
          }}
        >
          ⏱ CLICK
        </button>

        {/* Step / Bar Display */}
        <div style={{
          background: '#000',
          border: '1px solid #30363d',
          borderRadius: '4px',
          padding: '4px 10px',
          fontFamily: 'monospace',
          fontSize: '12px',
          color: theme.colors.accent
        }}>
          BAR: <b style={{ color: '#fff' }}>{currentBar + 1}</b> • STEP: <b style={{ color: '#fff' }}>{currentStep + 1}</b>
        </div>

        {/* Live Theatrical VST Theme Badge & Broadcast Sync */}
        <ThematicVstVisualizer compact={true} />

        <button
          onClick={useDawStore.getState().toggleTheatricalSync}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: useDawStore.getState().theatricalSyncEnabled ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255,255,255,0.05)',
            border: useDawStore.getState().theatricalSyncEnabled ? '1px solid #a855f7' : '1px solid rgba(255,255,255,0.1)',
            color: useDawStore.getState().theatricalSyncEnabled ? '#c084fc' : '#888',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            cursor: 'pointer'
          }}
          title="Broadcast live transport triggers to OBS scenes & Unreal Engine 5 DMX lighting"
        >
          ⚡ Live Sync: {useDawStore.getState().theatricalSyncEnabled ? 'OBS & UE5' : 'OFF'}
        </button>

        {/* Stehouwer Multi-Track Waveform Studio Quick Trigger */}
        <button
          onClick={() => setActiveView(activeView === 'wave_studio' ? 'playlist' : 'wave_studio')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: activeView === 'wave_studio' ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255,255,255,0.05)',
            border: activeView === 'wave_studio' ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
            color: activeView === 'wave_studio' ? '#38bdf8' : '#cbd5e1',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            cursor: 'pointer'
          }}
          title="Switch to Stehouwer Multi-Track Linear Waveform Studio & Recorder"
        >
          🎙️ Wave Studio
        </button>

        {/* Master Volume */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: 'auto' }}>
          <Volume2 size={15} color="#888" />
          <input
            type="range"
            min="-30"
            max="6"
            value={masterVolume}
            onChange={(e) => setMasterVolume(Number(e.target.value))}
            style={{ width: '60px', height: '4px', accentColor: theme.colors.accent, cursor: 'pointer' }}
          />
        </div>

        {/* Master Export Actions (WAV & NVENC MP4) */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={handleExportWAV}
            disabled={isExporting}
            style={{
              background: 'linear-gradient(135deg, #238636, #2ea043)',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 10px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: isExporting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 0 8px rgba(46, 160, 67, 0.3)'
            }}
          >
            <Download size={12} /> WAV
          </button>

          <button
            onClick={handleExportMasterMP4}
            disabled={isExporting}
            style={{
              background: 'linear-gradient(135deg, #a371f7, #8957e5)',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '6px 10px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: isExporting ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 0 8px rgba(163, 113, 247, 0.4)'
            }}
          >
            <Film size={12} /> Master MP4
          </button>
        </div>
      </div>

      {/* WORKSPACE VIEW SELECTOR */}
      <div style={{
        height: '32px',
        background: 'rgba(10, 13, 18, 0.95)',
        borderBottom: '1px solid #21262d',
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        gap: '8px'
      }}>
        <span style={{ fontSize: '10px', color: '#666', fontWeight: 'bold' }}>VIEWS:</span>
        {[
          { key: 'multimedia', label: '🎬 Multimedia Video+Audio Studio' },
          { key: 'wave_studio', label: '🎙️ Stehouwer Wave Studio' },
          { key: 'all', label: '🎛 Full Audio Studio Layout' },
          { key: 'channel_rack', label: '🥁 Channel Rack & Piano Roll' },
          { key: 'playlist', label: '🎼 Arranger Playlist' },
          { key: 'mixer', label: '🎚 Mixer & FX Rack' },
          { key: 'vst_thematic', label: '🎹 Theatrical VST3 DSP Telemetry' }
        ].map(v => (
          <button
            key={v.key}
            onClick={() => setActiveView(v.key)}
            style={{
              background: (activeView === v.key || (!activeView && v.key === 'multimedia')) ? 'rgba(0, 255, 255, 0.12)' : 'transparent',
              border: (activeView === v.key || (!activeView && v.key === 'multimedia')) ? `1px solid ${theme.colors.accent}` : '1px solid transparent',
              color: (activeView === v.key || (!activeView && v.key === 'multimedia')) ? theme.colors.accent : '#888',
              borderRadius: '3px',
              padding: '2px 8px',
              fontSize: '10px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* MAIN WORKSPACE CANVAS */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        
        {/* Left Side: Browser / Sound Vault */}
        <div style={{ 
          width: `${browserWidth}px`, 
          height: '100%', 
          transition: 'width 0.18s ease-in-out', 
          flexShrink: 0, 
          display: 'flex', 
          flexDirection: 'column', 
          overflow: 'hidden' 
        }}>
          <Browser 
            browserWidth={browserWidth}
            setBrowserWidth={setBrowserWidth}
            isExpanded={isBrowserExpanded}
            onToggleExpand={handleToggleBrowserExpand}
          />
        </div>

        {/* Center Canvas Areas */}
        <div 
          ref={centerCanvasRef}
          className="daw-center-canvas"
          style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', overflowX: 'hidden' }}
        >
          
          {/* MULTIMEDIA VIEW: Video Preview Monitor (Top Right) + Channel Rack (Top Left) + Timeline (Bottom) */}
          {(activeView === 'multimedia' || !activeView) && (
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: '740px', flex: 1 }}>
              <div style={{ display: 'flex', minHeight: isTheater ? '460px' : '360px', height: isTheater ? '58%' : '48%', borderBottom: '1px solid #30363d', transition: 'all 0.2s ease', flexShrink: 0 }}>
                <div style={{ 
                  flex: isTheater ? '0 0 32%' : '0 0 50%', 
                  overflow: 'hidden', 
                  transition: 'flex 0.2s ease' 
                }}>
                  <ChannelRack />
                </div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <VideoPreviewMonitor 
                    isTheater={isTheater} 
                    onToggleTheater={handleToggleTheater} 
                  />
                </div>
              </div>

              <div style={{ display: 'flex', minHeight: '350px', flex: 1, flexShrink: 0, overflow: 'hidden' }}>
                <div style={{ flex: '0 0 68%', overflow: 'hidden' }}>
                  <Playlist />
                </div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <Mixer />
                </div>
              </div>
            </div>
          )}

          {/* ALL AUDIO VIEW */}
          {activeView === 'all' && (
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: '740px', flex: 1 }}>
              <div style={{ display: 'flex', minHeight: '360px', height: '48%', borderBottom: '1px solid #30363d', flexShrink: 0 }}>
                <div style={{ flex: '0 0 45%', overflow: 'hidden' }}>
                  <ChannelRack />
                </div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <PianoRoll />
                </div>
              </div>

              <div style={{ display: 'flex', minHeight: '350px', flex: 1, flexShrink: 0, overflow: 'hidden' }}>
                <div style={{ flex: '0 0 65%', overflow: 'hidden' }}>
                  <Playlist />
                </div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <Mixer />
                </div>
              </div>
            </div>
          )}

          {/* CHANNEL RACK ONLY */}
          {activeView === 'channel_rack' && (
            <div style={{ display: 'flex', height: '100%' }}>
              <div style={{ flex: '0 0 45%', overflow: 'hidden' }}>
                <ChannelRack />
              </div>
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <PianoRoll />
              </div>
            </div>
          )}

          {/* PLAYLIST ONLY */}
          {activeView === 'playlist' && (
            <div style={{ height: '100%', overflow: 'hidden' }}>
              <Playlist />
            </div>
          )}

          {/* MIXER ONLY */}
          {activeView === 'mixer' && (
            <div style={{ height: '100%', overflow: 'hidden' }}>
              <Mixer />
            </div>
          )}

          {/* STEHOUWER MULTI-TRACK LINEAR WAVEFORM STUDIO */}
          {activeView === 'wave_studio' && (
            <div style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <StehouwerWaveStudio 
                onSendToPlaylist={(buffer, name) => {
                  useDawStore.getState().addPlaylistClip?.({ name, buffer, startBar: 0, lengthBars: 4 });
                  setActiveView('playlist');
                }} 
              />
            </div>
          )}

          {/* THEATRICAL VST3 DSP TELEMETRY VIEW */}
          {activeView === 'vst_thematic' && (
            <div style={{ height: '100%', overflow: 'auto', padding: '16px' }}>
              <ThematicVstVisualizer />
            </div>
          )}

        </div>
      </div>

    </div>
  );
};

export default MusicDAWStudioTab;
