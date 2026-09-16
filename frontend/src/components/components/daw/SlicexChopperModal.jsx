import React, { useState, useEffect, useRef } from 'react';
import { theme } from '../../styles/theme';
import { 
  Scissors, Play, Square, Grid, Sparkles, X, ArrowDownRight, Layers, Music
} from 'lucide-react';

export default function SlicexChopperModal({ clip, onClose, onDumpSlices }) {
  const canvasRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioBufferRef = useRef(null);
  const activeSourceRef = useRef(null);

  const [chopMode, setChopMode] = useState('transients'); // 'transients' | '1/2_beat' | '1/4_beat' | '8_slices' | '16_slices'
  const [slices, setSlices] = useState([]); // array of { start: 0..1, end: 0..1, label: string, color: string }
  const [activeSliceIdx, setActiveSliceIdx] = useState(null);
  const [audioDuration, setAudioDuration] = useState(4);
  const [statusMsg, setStatusMsg] = useState('Slicex Transient Chopper Ready');

  const SLICE_COLORS = [
    '#ff5e5e', '#ffaa00', '#ffd000', '#5eff7b', 
    '#00f0ff', '#38bdf8', '#a855f7', '#ff007f',
    '#e11d48', '#f59e0b', '#10b981', '#06b6d4',
    '#6366f1', '#ec4899', '#84cc16', '#14b8a6'
  ];

  // Initialize Audio
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
          // Synthetic beat loop buffer for demonstration
          buffer = ctx.createBuffer(2, ctx.sampleRate * 4, ctx.sampleRate);
          for (let ch = 0; ch < 2; ch++) {
            const data = buffer.getChannelData(ch);
            for (let i = 0; i < data.length; i++) {
              const t = i / ctx.sampleRate;
              const beatEnv = Math.exp(-((t % 0.25) * 16));
              data[i] = (Math.sin(2 * Math.PI * 110 * t) * 0.5 + Math.sin(2 * Math.PI * 880 * t) * 0.2) * beatEnv;
            }
          }
        }
        audioBufferRef.current = buffer;
        setAudioDuration(buffer.duration);
        generateSlices(buffer, chopMode);
      } catch (err) {
        console.warn('Slicex Load Error:', err);
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

  // Generate slice divisions
  const generateSlices = (buffer, mode) => {
    if (!buffer) return;
    let count = 8;
    let computedSlices = [];

    if (mode === '1/2_beat') count = 8;
    else if (mode === '1/4_beat') count = 16;
    else if (mode === '8_slices') count = 8;
    else if (mode === '16_slices') count = 16;
    else if (mode === 'transients') {
      // Analyze energy peaks
      const data = buffer.getChannelData(0);
      const windowSize = Math.floor(buffer.sampleRate * 0.05);
      const peaks = [];
      let prevEnergy = 0;

      for (let i = 0; i < data.length - windowSize; i += windowSize) {
        let energy = 0;
        for (let j = 0; j < windowSize; j++) {
          energy += Math.abs(data[i + j]);
        }
        if (energy > prevEnergy * 1.8 && energy > 2.0) {
          peaks.push(i / data.length);
        }
        prevEnergy = energy;
      }

      const points = [0, ...peaks.filter(p => p > 0.04), 1].sort((a, b) => a - b);
      for (let i = 0; i < points.length - 1; i++) {
        computedSlices.push({
          id: `s_${i + 1}`,
          start: points[i],
          end: points[i + 1],
          label: `S${i + 1}`,
          color: SLICE_COLORS[i % SLICE_COLORS.length]
        });
      }
      setSlices(computedSlices);
      setStatusMsg(`Detected ${computedSlices.length} transient hits`);
      return;
    }

    // Grid mode
    for (let i = 0; i < count; i++) {
      computedSlices.push({
        id: `s_${i + 1}`,
        start: i / count,
        end: (i + 1) / count,
        label: `S${i + 1}`,
        color: SLICE_COLORS[i % SLICE_COLORS.length]
      });
    }
    setSlices(computedSlices);
    setStatusMsg(`Generated ${count} grid slices`);
  };

  useEffect(() => {
    if (audioBufferRef.current) {
      generateSlices(audioBufferRef.current, chopMode);
    }
  }, [chopMode]);

  // Redraw Canvas
  useEffect(() => {
    if (audioBufferRef.current && slices.length > 0) {
      drawSlices();
    }
  }, [slices, activeSliceIdx]);

  const drawSlices = () => {
    const canvas = canvasRef.current;
    if (!canvas || !audioBufferRef.current) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = '#0a0d14';
    ctx.fillRect(0, 0, width, height);

    const data = audioBufferRef.current.getChannelData(0);
    const step = Math.ceil(data.length / width);
    const amp = height / 2.3;

    // Draw Slices Backgrounds & Waveform
    slices.forEach((slice, idx) => {
      const x1 = slice.start * width;
      const x2 = slice.end * width;
      const isActive = activeSliceIdx === idx;

      // Slice region tint
      ctx.fillStyle = isActive ? `${slice.color}44` : `${slice.color}15`;
      ctx.fillRect(x1, 0, x2 - x1, height);

      // Slice boundary marker
      ctx.strokeStyle = slice.color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x1, 0);
      ctx.lineTo(x1, height);
      ctx.stroke();

      // Slice Label Tag
      ctx.fillStyle = slice.color;
      ctx.font = 'bold 9px monospace';
      ctx.fillText(slice.label, x1 + 4, 14);
    });

    // Draw Waveform Strokes
    ctx.strokeStyle = '#fff';
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
      ctx.moveTo(i, (1 + min) * amp);
      ctx.lineTo(i, (1 + max) * amp);
    }
    ctx.stroke();
  };

  // Play Specific Slice
  const playSlice = (slice, idx) => {
    if (!audioBufferRef.current || !audioContextRef.current) return;
    stopPlayback();

    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') ctx.resume();

    const source = ctx.createBufferSource();
    source.buffer = audioBufferRef.current;
    source.connect(ctx.destination);

    const sStart = slice.start * audioDuration;
    const sEnd = slice.end * audioDuration;
    const duration = Math.max(0.05, sEnd - sStart);

    source.start(0, sStart, duration);
    activeSourceRef.current = source;
    setActiveSliceIdx(idx);

    source.onended = () => {
      setActiveSliceIdx(null);
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
    setActiveSliceIdx(null);
  };

  // Dump Slices to Piano Roll / Channel Rack
  const handleDumpToPianoRoll = () => {
    if (onDumpSlices) {
      onDumpSlices(slices, clip);
    }
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
        width: '880px',
        maxWidth: '96vw',
        height: '580px',
        maxHeight: '94vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 240, 255, 0.15)',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '10px 14px',
          background: 'linear-gradient(90deg, #161b22, #0d1117)',
          borderBottom: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '14px', background: '#00f0ff', color: '#000', padding: '2px 6px', borderRadius: '3px', fontWeight: 'bold' }}>
              SLICEX
            </span>
            <span style={{ fontSize: '12px', color: '#fff', fontWeight: 'bold' }}>
              Transient Chopper & Beat Re-Arranger
            </span>
            <span style={{ fontSize: '10px', color: '#8b949e', marginLeft: '6px' }}>
              [{clip?.title || 'Beat Loop'}] • {slices.length} Slices
            </span>
          </div>

          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Mode Selector Toolbar */}
        <div style={{
          padding: '6px 12px',
          background: '#161b22',
          borderBottom: '1px solid #21262d',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{ fontSize: '10px', color: '#8b949e', fontWeight: 'bold' }}>CHOP METHOD:</span>
          {[
            { id: 'transients', label: '⚡ Auto Transients' },
            { id: '1/2_beat', label: '🥁 1/2 Beat' },
            { id: '1/4_beat', label: '🎼 1/4 Beat' },
            { id: '8_slices', label: '8 Chops' },
            { id: '16_slices', label: '16 Chops' }
          ].map(m => (
            <button
              key={m.id}
              onClick={() => setChopMode(m.id)}
              style={{
                background: chopMode === m.id ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255,255,255,0.04)',
                border: chopMode === m.id ? '1px solid #00f0ff' : '1px solid rgba(255,255,255,0.08)',
                color: chopMode === m.id ? '#00f0ff' : '#8b949e',
                borderRadius: '3px',
                padding: '3px 8px',
                fontSize: '10px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Waveform Canvas with Slices */}
        <div style={{ height: '180px', position: 'relative', background: '#05070a' }}>
          <canvas
            ref={canvasRef}
            width={840}
            height={180}
            style={{ width: '100%', height: '100%', display: 'block' }}
          />
        </div>

        {/* Interactive Slice Pads Grid */}
        <div style={{
          flex: 1,
          padding: '12px',
          background: '#0d1117',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto'
        }}>
          <div style={{ fontSize: '10px', color: '#888', fontWeight: 'bold', marginBottom: '8px' }}>
            CLICK PAD TO AUDITION SLICE (OR PLAY VIA PIANO ROLL / MIDI):
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(8, 1fr)',
            gap: '8px',
            flex: 1
          }}>
            {slices.map((slice, idx) => (
              <button
                key={slice.id}
                onClick={() => playSlice(slice, idx)}
                style={{
                  background: activeSliceIdx === idx ? slice.color : `rgba(255,255,255,0.04)`,
                  border: `1px solid ${slice.color}`,
                  borderRadius: '4px',
                  color: activeSliceIdx === idx ? '#000' : '#fff',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  padding: '8px',
                  boxShadow: activeSliceIdx === idx ? `0 0 12px ${slice.color}` : 'none',
                  transition: 'all 0.1s'
                }}
              >
                <span style={{ fontSize: '13px', fontWeight: 'bold' }}>{slice.label}</span>
                <span style={{ fontSize: '8px', opacity: 0.7, marginTop: '2px' }}>
                  {((slice.end - slice.start) * audioDuration).toFixed(2)}s
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Footer & Dump Actions */}
        <div style={{
          padding: '10px 14px',
          background: '#161b22',
          borderTop: '1px solid #30363d',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ fontSize: '11px', color: '#00f0ff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={13} /> {statusMsg}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={onClose}
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
              CLOSE
            </button>

            <button
              onClick={handleDumpToPianoRoll}
              style={{
                background: 'linear-gradient(135deg, #00f0ff, #0088ff)',
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
              <ArrowDownRight size={13} /> DUMP TO PIANO ROLL / TRACKS
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
