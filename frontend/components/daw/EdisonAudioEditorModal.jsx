import React, { useState, useEffect, useRef } from 'react';
import { theme } from '../../styles/theme';
import { 
  Scissors, Volume2, ZoomIn, ZoomOut, Play, Square, Repeat, 
  Download, ArrowDownRight, RefreshCw, Wand2, ShieldAlert, X, Sparkles, Sliders
} from 'lucide-react';

export default function EdisonAudioEditorModal({ clip, onClose, onSendToPlaylist, onSendToChannelRack }) {
  const canvasRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioBufferRef = useRef(null);
  const activeSourceRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLooping, setIsLooping] = useState(false);
  const [selectionStart, setSelectionStart] = useState(0); // 0 to 1 ratio
  const [selectionEnd, setSelectionEnd] = useState(1);   // 0 to 1 ratio
  const [isSelecting, setIsSelecting] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1); // 1x to 10x
  const [audioDuration, setAudioDuration] = useState(0);
  const [sampleRate, setSampleRate] = useState(44100);
  const [channelsCount, setChannelsCount] = useState(2);
  const [statusMsg, setStatusMsg] = useState('Edison Precision Editor Ready');
  const [denoiseThreshold, setDenoiseThreshold] = useState(-36); // dB

  // Initialize or fetch audio buffer
  useEffect(() => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    audioContextRef.current = ctx;

    const loadAudio = async () => {
      try {
        let buffer;
        if (clip?.audioBuffer) {
          buffer = clip.audioBuffer;
        } else if (clip?.url) {
          const res = await fetch(clip.url);
          const arrayBuffer = await res.arrayBuffer();
          buffer = await ctx.decodeAudioData(arrayBuffer);
        } else {
          // Generate realistic vocal/music sample buffer for demonstration if no URL
          buffer = ctx.createBuffer(2, ctx.sampleRate * 4, ctx.sampleRate);
          for (let ch = 0; ch < 2; ch++) {
            const data = buffer.getChannelData(ch);
            for (let i = 0; i < data.length; i++) {
              const t = i / ctx.sampleRate;
              const beatEnv = Math.exp(-((t % 0.5) * 8));
              data[i] = (Math.sin(2 * Math.PI * 130 * t) * 0.4 + Math.sin(2 * Math.PI * 440 * t) * 0.2) * beatEnv;
            }
          }
        }

        audioBufferRef.current = buffer;
        setAudioDuration(buffer.duration);
        setSampleRate(buffer.sampleRate);
        setChannelsCount(buffer.numberOfChannels);
        drawWaveform(buffer, 0, 1);
      } catch (err) {
        console.warn('Edison Audio Load Error:', err);
        setStatusMsg('Loaded fallback demo waveform');
      }
    };

    loadAudio();

    return () => {
      stopPlayback();
      try {
        ctx.close();
      } catch (e) {}
    };
  }, [clip]);

  // Redraw waveform on selection or zoom change
  useEffect(() => {
    if (audioBufferRef.current) {
      drawWaveform(audioBufferRef.current, selectionStart, selectionEnd);
    }
  }, [selectionStart, selectionEnd, zoomLevel]);

  // Waveform Drawing
  const drawWaveform = (buffer, selStart, selEnd) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Background gradient
    const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
    bgGrad.addColorStop(0, '#090d14');
    bgGrad.addColorStop(1, '#05070a');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, width, height);

    // Grid lines (sample ticks)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    // Center baseline
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.2)';
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    const data = buffer.getChannelData(0);
    const step = Math.ceil((data.length / width) / zoomLevel);
    const amp = height / 2.2;

    // Draw Waveform Body
    ctx.fillStyle = '#ff7b00';
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 1;
    ctx.beginPath();

    for (let i = 0; i < width; i++) {
      let min = 1.0;
      let max = -1.0;
      const startIdx = Math.floor(i * step);
      for (let j = 0; j < step; j++) {
        const datum = data[startIdx + j] || 0;
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }
      const yMin = (1 + min) * amp;
      const yMax = (1 + max) * amp;

      ctx.moveTo(i, yMin);
      ctx.lineTo(i, yMax);
    }
    ctx.stroke();

    // Draw Selection Highlight
    if (selStart !== undefined && selEnd !== undefined && selStart !== selEnd) {
      const x1 = Math.min(selStart, selEnd) * width;
      const x2 = Math.max(selStart, selEnd) * width;
      ctx.fillStyle = 'rgba(255, 123, 0, 0.25)';
      ctx.fillRect(x1, 0, x2 - x1, height);

      ctx.strokeStyle = '#ff7b00';
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, 0, x2 - x1, height);
    }
  };

  // Playback handlers
  const startPlayback = () => {
    if (!audioBufferRef.current || !audioContextRef.current) return;
    stopPlayback();

    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') ctx.resume();

    const source = ctx.createBufferSource();
    source.buffer = audioBufferRef.current;
    source.connect(ctx.destination);

    const sStart = Math.min(selectionStart, selectionEnd) * audioDuration;
    const sEnd = Math.max(selectionStart, selectionEnd) * audioDuration;
    const duration = sEnd > sStart ? sEnd - sStart : audioDuration;

    source.loop = isLooping;
    if (isLooping && sEnd > sStart) {
      source.loopStart = sStart;
      source.loopEnd = sEnd;
    }

    source.start(0, sStart > 0 ? sStart : 0, duration > 0 ? duration : undefined);
    activeSourceRef.current = source;
    setIsPlaying(true);

    source.onended = () => {
      setIsPlaying(false);
    };
  };

  const stopPlayback = () => {
    if (activeSourceRef.current) {
      try {
        activeSourceRef.current.stop();
        activeSourceRef.current.disconnect();
      } catch (e) {}
      activeSourceRef.current = null;
    }
    setIsPlaying(false);
  };

  // Selection Drag Handlers
  const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    setSelectionStart(pos);
    setSelectionEnd(pos);
    setIsSelecting(true);
  };

  const handleMouseMove = (e) => {
    if (!isSelecting) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setSelectionEnd(pos);
  };

  const handleMouseUp = () => {
    setIsSelecting(false);
  };

  // Audio Processing Operations
  const cloneBuffer = (buffer) => {
    const ctx = audioContextRef.current;
    const clone = ctx.createBuffer(buffer.numberOfChannels, buffer.length, buffer.sampleRate);
    for (let ch = 0; ch < buffer.numberOfChannels; ch++) {
      clone.getChannelData(ch).set(buffer.getChannelData(ch));
    }
    return clone;
  };

  // 1. Trim / Crop to selection
  const handleTrim = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    stopPlayback();

    const sStart = Math.floor(Math.min(selectionStart, selectionEnd) * buf.length);
    const sEnd = Math.floor(Math.max(selectionStart, selectionEnd) * buf.length);
    const newLen = Math.max(1, sEnd - sStart);

    const ctx = audioContextRef.current;
    const trimmed = ctx.createBuffer(buf.numberOfChannels, newLen, buf.sampleRate);
    for (let ch = 0; ch < buf.numberOfChannels; ch++) {
      const src = buf.getChannelData(ch);
      const dest = trimmed.getChannelData(ch);
      for (let i = 0; i < newLen; i++) {
        dest[i] = src[sStart + i];
      }
    }

    audioBufferRef.current = trimmed;
    setAudioDuration(trimmed.duration);
    setSelectionStart(0);
    setSelectionEnd(1);
    setStatusMsg(`Trimmed to ${(trimmed.duration).toFixed(3)}s`);
  };

  // 2. Cut / Excise Selection
  const handleCut = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    stopPlayback();

    const sStart = Math.floor(Math.min(selectionStart, selectionEnd) * buf.length);
    const sEnd = Math.floor(Math.max(selectionStart, selectionEnd) * buf.length);
    const cutLen = sEnd - sStart;
    const newLen = buf.length - cutLen;
    if (newLen <= 0) return;

    const ctx = audioContextRef.current;
    const cutBuffer = ctx.createBuffer(buf.numberOfChannels, newLen, buf.sampleRate);
    for (let ch = 0; ch < buf.numberOfChannels; ch++) {
      const src = buf.getChannelData(ch);
      const dest = cutBuffer.getChannelData(ch);
      dest.set(src.subarray(0, sStart), 0);
      dest.set(src.subarray(sEnd), sStart);
    }

    audioBufferRef.current = cutBuffer;
    setAudioDuration(cutBuffer.duration);
    setSelectionStart(0);
    setSelectionEnd(1);
    setStatusMsg(`Cut section (${(cutLen / buf.sampleRate).toFixed(3)}s deleted)`);
  };

  // 3. Silence Selection (Kill Noise & Breaths)
  const handleSilence = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    const cloned = cloneBuffer(buf);

    const sStart = Math.floor(Math.min(selectionStart, selectionEnd) * buf.length);
    const sEnd = Math.floor(Math.max(selectionStart, selectionEnd) * buf.length);

    for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
      const data = cloned.getChannelData(ch);
      for (let i = sStart; i < sEnd; i++) {
        data[i] = 0;
      }
    }

    audioBufferRef.current = cloned;
    drawWaveform(cloned, selectionStart, selectionEnd);
    setStatusMsg('Silenced selected region');
  };

  // 4. Fade In across selection
  const handleFadeIn = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    const cloned = cloneBuffer(buf);

    const sStart = Math.floor(Math.min(selectionStart, selectionEnd) * buf.length);
    const sEnd = Math.floor(Math.max(selectionStart, selectionEnd) * buf.length);
    const len = sEnd - sStart;

    for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
      const data = cloned.getChannelData(ch);
      for (let i = sStart; i < sEnd; i++) {
        const factor = (i - sStart) / len;
        data[i] *= factor;
      }
    }

    audioBufferRef.current = cloned;
    drawWaveform(cloned, selectionStart, selectionEnd);
    setStatusMsg('Fade In applied to selection');
  };

  // 5. Fade Out across selection
  const handleFadeOut = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    const cloned = cloneBuffer(buf);

    const sStart = Math.floor(Math.min(selectionStart, selectionEnd) * buf.length);
    const sEnd = Math.floor(Math.max(selectionStart, selectionEnd) * buf.length);
    const len = sEnd - sStart;

    for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
      const data = cloned.getChannelData(ch);
      for (let i = sStart; i < sEnd; i++) {
        const factor = 1 - ((i - sStart) / len);
        data[i] *= factor;
      }
    }

    audioBufferRef.current = cloned;
    drawWaveform(cloned, selectionStart, selectionEnd);
    setStatusMsg('Fade Out applied to selection');
  };

  // 6. Normalize to 0 dB (-0.1 dB ceiling)
  const handleNormalize = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    const cloned = cloneBuffer(buf);

    let maxAmp = 0;
    for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
      const data = cloned.getChannelData(ch);
      for (let i = 0; i < data.length; i++) {
        const abs = Math.abs(data[i]);
        if (abs > maxAmp) maxAmp = abs;
      }
    }

    if (maxAmp > 0) {
      const gain = 0.99 / maxAmp;
      for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
        const data = cloned.getChannelData(ch);
        for (let i = 0; i < data.length; i++) {
          data[i] *= gain;
        }
      }
      audioBufferRef.current = cloned;
      drawWaveform(cloned, selectionStart, selectionEnd);
      setStatusMsg(`Normalized: Peak amplified by ${(20 * Math.log10(gain)).toFixed(2)} dB`);
    }
  };

  // 7. Reverse Selection or Full
  const handleReverse = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    const cloned = cloneBuffer(buf);

    const sStart = Math.floor(Math.min(selectionStart, selectionEnd) * buf.length);
    const sEnd = Math.floor(Math.max(selectionStart, selectionEnd) * buf.length);

    for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
      const data = cloned.getChannelData(ch);
      const sub = data.slice(sStart, sEnd).reverse();
      data.set(sub, sStart);
    }

    audioBufferRef.current = cloned;
    drawWaveform(cloned, selectionStart, selectionEnd);
    setStatusMsg('Reversed selected audio buffer');
  };

  // 8. Denoise Gate
  const handleDenoise = () => {
    const buf = audioBufferRef.current;
    if (!buf) return;
    const cloned = cloneBuffer(buf);
    const thresholdLinear = Math.pow(10, denoiseThreshold / 20);

    for (let ch = 0; ch < cloned.numberOfChannels; ch++) {
      const data = cloned.getChannelData(ch);
      for (let i = 0; i < data.length; i++) {
        if (Math.abs(data[i]) < thresholdLinear) {
          data[i] = 0;
        }
      }
    }

    audioBufferRef.current = cloned;
    drawWaveform(cloned, selectionStart, selectionEnd);
    setStatusMsg(`Noise Gate applied (${denoiseThreshold} dB threshold)`);
  };

  // Send edited audio to playlist as new Audio Clip
  const handleExportToPlaylist = () => {
    if (!audioBufferRef.current) return;
    const editedClip = {
      ...clip,
      title: `${clip?.title || 'Audio Clip'} (Edison)`,
      audioBuffer: audioBufferRef.current,
      duration: audioBufferRef.current.duration
    };
    if (onSendToPlaylist) onSendToPlaylist(editedClip);
    onClose();
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: '8px',
        width: '920px',
        maxWidth: '96vw',
        height: '640px',
        maxHeight: '94vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 20px rgba(255, 123, 0, 0.15)',
        overflow: 'hidden'
      }}>
        {/* Header Bar */}
        <div style={{
          padding: '10px 14px',
          background: 'linear-gradient(90deg, #161b22, #0d1117)',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', background: '#ff7b00', color: '#000', padding: '2px 6px', borderRadius: '3px', fontWeight: 'bold' }}>
              EDISON
            </span>
            <span style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold' }}>
              Precision Audio Editor & Waveform Cleaner
            </span>
            <span style={{ fontSize: '10px', color: '#8b949e', marginLeft: '6px' }}>
              [{clip?.title || 'Master Audio Clip'}] • {audioDuration.toFixed(3)}s • {sampleRate}Hz • {channelsCount}Ch
            </span>
          </div>

          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Action Toolbar Ribbon */}
        <div style={{
          padding: '6px 12px',
          background: '#161b22',
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          flexWrap: 'wrap'
        }}>
          {/* Playback Controls */}
          <button
            onClick={isPlaying ? stopPlayback : startPlayback}
            style={{
              background: isPlaying ? '#5eff7b' : 'rgba(255,255,255,0.08)',
              color: isPlaying ? '#000' : '#fff',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '3px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            {isPlaying ? <Square size={11} fill="#000" /> : <Play size={11} fill="#fff" />}
            {isPlaying ? 'STOP' : 'PLAY SEL'}
          </button>

          <button
            onClick={() => setIsLooping(!isLooping)}
            style={{
              background: isLooping ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255,255,255,0.04)',
              color: isLooping ? '#00f0ff' : '#888',
              border: isLooping ? '1px solid #00f0ff' : '1px solid rgba(255,255,255,0.08)',
              borderRadius: '3px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Repeat size={11} /> LOOP
          </button>

          <div style={{ height: '16px', width: '1px', background: '#30363d', margin: '0 4px' }} />

          {/* Slicing / Editing Tools */}
          <button
            onClick={handleTrim}
            title="Trim: Keep only selection and delete edges"
            style={{ background: '#21262d', color: '#fff', border: '1px solid #30363d', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <Scissors size={10} color="#ff7b00" /> TRIM
          </button>

          <button
            onClick={handleCut}
            title="Cut / Excise selection"
            style={{ background: '#21262d', color: '#fff', border: '1px solid #30363d', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer' }}
          >
            CUT SEL
          </button>

          <button
            onClick={handleSilence}
            title="Silence: Zero out background noise or breaths"
            style={{ background: '#21262d', color: '#fff', border: '1px solid #30363d', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer' }}
          >
            SILENCE
          </button>

          <button
            onClick={handleFadeIn}
            title="Fade In Ramp across selection"
            style={{ background: '#21262d', color: '#fff', border: '1px solid #30363d', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer' }}
          >
            FADE IN
          </button>

          <button
            onClick={handleFadeOut}
            title="Fade Out Ramp across selection"
            style={{ background: '#21262d', color: '#fff', border: '1px solid #30363d', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer' }}
          >
            FADE OUT
          </button>

          <button
            onClick={handleNormalize}
            title="Normalize to 0 dB"
            style={{ background: '#21262d', color: '#00f0ff', border: '1px solid #00f0ff44', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            NORMALIZE
          </button>

          <button
            onClick={handleReverse}
            title="Reverse Selection"
            style={{ background: '#21262d', color: '#ffbd5e', border: '1px solid #ffbd5e44', borderRadius: '3px', padding: '4px 8px', fontSize: '10px', cursor: 'pointer' }}
          >
            REVERSE
          </button>

          <div style={{ height: '16px', width: '1px', background: '#30363d', margin: '0 4px' }} />

          {/* Denoise Gate */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: '#8b949e' }}>GATE:</span>
            <input
              type="range"
              min="-60"
              max="-12"
              value={denoiseThreshold}
              onChange={(e) => setDenoiseThreshold(Number(e.target.value))}
              style={{ width: '45px', height: '3px', accentColor: '#ff7b00' }}
              title={`Noise Gate Threshold: ${denoiseThreshold} dB`}
            />
            <button
              onClick={handleDenoise}
              style={{ background: '#21262d', color: '#a855f7', border: '1px solid #a855f744', borderRadius: '3px', padding: '4px 6px', fontSize: '10px', cursor: 'pointer' }}
            >
              CLEAN
            </button>
          </div>

          {/* Zoom Buttons */}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              onClick={() => setZoomLevel(Math.max(1, zoomLevel - 0.5))}
              style={{ background: '#21262d', color: '#888', border: 'none', borderRadius: '3px', padding: '4px 6px', cursor: 'pointer' }}
            >
              <ZoomOut size={12} />
            </button>
            <span style={{ fontSize: '9px', color: '#888', width: '24px', textAlign: 'center' }}>{zoomLevel}x</span>
            <button
              onClick={() => setZoomLevel(Math.min(8, zoomLevel + 0.5))}
              style={{ background: '#21262d', color: '#888', border: 'none', borderRadius: '3px', padding: '4px 6px', cursor: 'pointer' }}
            >
              <ZoomIn size={12} />
            </button>
          </div>
        </div>

        {/* Main Waveform Canvas */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', cursor: 'crosshair', background: '#05070a' }}>
          <canvas
            ref={canvasRef}
            width={880}
            height={360}
            style={{ width: '100%', height: '100%', display: 'block' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          />
        </div>

        {/* Footer & Export Bar */}
        <div style={{
          padding: '10px 14px',
          background: '#161b22',
          borderTop: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ fontSize: '11px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={13} /> {statusMsg}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => {
                setSelectionStart(0);
                setSelectionEnd(1);
              }}
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                color: '#ccc',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '11px',
                cursor: 'pointer'
              }}
            >
              SELECT ALL
            </button>

            <button
              onClick={handleExportToPlaylist}
              style={{
                background: 'linear-gradient(135deg, #ff7b00, #ffaa00)',
                color: '#000',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <ArrowDownRight size={13} /> SEND TO PLAYLIST
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
