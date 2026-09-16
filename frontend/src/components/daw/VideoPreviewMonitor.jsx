import React, { useState, useRef, useEffect, useCallback } from 'react';
import { theme } from '../../styles/theme';
import { useDawStore, masterAnalyser } from './dawStore';
import { 
  Film, Maximize2, Minimize2, Smartphone, Monitor, Sparkles, VolumeX, Volume2, 
  Scaling, Upload, Clock, Sliders, Radio, Zap
} from 'lucide-react';

const PROCEDURAL_PRESETS = [
  { id: 'cyber_city', name: 'Cyber City Grid (Synthwave)', color: '#00f0ff', desc: 'Audio-reactive wireframe cityscape' },
  { id: 'matrix_tunnel', name: 'Matrix Data Tunnel', color: '#10b981', desc: '3D hyperspace data stream' },
  { id: 'spectrum_vault', name: 'Neural Spectrum Visualizer', color: '#ff007f', desc: 'Real-time 64-band FFT analyzer' },
  { id: 'glitch_nebula', name: 'Cosmic Nebula & Glitch', color: '#8b5cf6', desc: 'Audio-reactive particle matrix' }
];

export default function VideoPreviewMonitor({ isTheater = false, onToggleTheater = null }) {
  const isPlaying = useDawStore(state => state.isPlaying);
  const currentBar = useDawStore(state => state.currentBar);
  const currentStep = useDawStore(state => state.currentStep);
  const bpm = useDawStore(state => state.bpm);

  const [aspectRatio, setAspectRatio] = useState('16:9'); // '16:9', '9:16', '21:9', '4:3'
  const [fitMode, setFitMode] = useState('fit'); // 'fit' (contain), 'fill' (cover), 'stretch'
  const [selectedVideo, setSelectedVideo] = useState(null); // Blob URL or stream if loaded
  const [activePresetId, setActivePresetId] = useState('cyber_city');
  const [isMuted, setIsMuted] = useState(true);
  const [latencyOffsetMs, setLatencyOffsetMs] = useState(0); // -300ms to +300ms
  const [showLatencyDrawer, setShowLatencyDrawer] = useState(false);
  const [isGeneratingScene, setIsGeneratingScene] = useState(false);
  const [promptText, setPromptText] = useState('Cinematic 4k neon cyberpunk city street in rain with reflections');
  const [showPromptModal, setShowPromptModal] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const animFrameRef = useRef(null);
  const lastRenderTimeRef = useRef(performance.now());
  const visualizerPhaseRef = useRef(0);

  // Aspect Ratio calculations
  const getAspectDimensions = useCallback(() => {
    switch (aspectRatio) {
      case '9:16': return { w: 1080, h: 1920, ratio: 9 / 16 };
      case '21:9': return { w: 2560, h: 1080, ratio: 21 / 9 };
      case '4:3': return { w: 1440, h: 1080, ratio: 4 / 3 };
      case '16:9':
      default: return { w: 1920, h: 1080, ratio: 16 / 9 };
    }
  }, [aspectRatio]);

  // Synchronize HTML5 video playback with Tone.js transport with latency offset
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !selectedVideo) return;

    if (isPlaying) {
      const totalSteps = (currentBar * 16) + currentStep;
      const beatDuration = 60 / bpm;
      const rawTimeSec = (totalSteps / 4) * beatDuration;
      const targetTimeSec = Math.max(0, rawTimeSec + (latencyOffsetMs / 1000));

      if (video.duration && !isNaN(video.duration) && video.duration > 0) {
        const loopTime = targetTimeSec % video.duration;
        if (Math.abs(video.currentTime - loopTime) > 0.15) {
          try {
            if (typeof video.fastSeek === 'function') {
              video.fastSeek(loopTime);
            } else {
              video.currentTime = loopTime;
            }
          } catch (_) {}
        }
      }
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, [isPlaying, currentBar, currentStep, bpm, selectedVideo, latencyOffsetMs]);

  // Main 60 FPS Procedural Audio-Reactive Rendering Engine
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let isRunning = true;
    const fftBuffer = new Float32Array(64);

    const render = (now) => {
      if (!isRunning) return;
      const dt = Math.min(0.1, (now - lastRenderTimeRef.current) / 1000);
      lastRenderTimeRef.current = now;

      // Extract real-time Web Audio FFT values from DAW master bus
      let avgEnergy = 0;
      let bassEnergy = 0;
      let midEnergy = 0;
      try {
        if (masterAnalyser) {
          const values = masterAnalyser.getValue();
          if (values && values.length) {
            for (let i = 0; i < Math.min(values.length, 64); i++) {
              // Normalize dB (-100 to 0) to 0.0 - 1.0
              const normalized = Math.max(0, Math.min(1, (values[i] + 90) / 90));
              fftBuffer[i] = normalized;
              avgEnergy += normalized;
              if (i < 8) bassEnergy += normalized;
              else if (i < 32) midEnergy += normalized;
            }
            avgEnergy /= 64;
            bassEnergy /= 8;
            midEnergy /= 24;
          }
        }
      } catch (_) {}

      // If simulated / no audio playing, give subtle breathing energy
      if (isPlaying && avgEnergy < 0.05) {
        const beatPulse = (Math.sin(now * 0.008 * (bpm / 120)) + 1) * 0.5;
        avgEnergy = 0.15 + (beatPulse * 0.25);
        bassEnergy = 0.2 + (beatPulse * 0.4);
        midEnergy = 0.15 + (beatPulse * 0.2);
      }

      visualizerPhaseRef.current += dt * (isPlaying ? 1.8 * (bpm / 120) : 0.4);
      const phase = visualizerPhaseRef.current;

      const { w: targetW, h: targetH } = getAspectDimensions();
      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
      }

      // 1. Clear background
      ctx.fillStyle = '#05070f';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const video = videoRef.current;
      const isVideoPlaying = video && selectedVideo && video.readyState >= 2 && !video.paused;

      if (isVideoPlaying) {
        // Draw real video with proper Aspect Containment / Letterboxing
        const srcW = video.videoWidth || targetW;
        const srcH = video.videoHeight || targetH;
        const srcRatio = srcW / srcH;
        const destRatio = targetW / targetH;

        if (fitMode === 'stretch') {
          ctx.drawImage(video, 0, 0, targetW, targetH);
        } else if (fitMode === 'fill') {
          // Cover crop
          let cropX = 0, cropY = 0, cropW = srcW, cropH = srcH;
          if (srcRatio > destRatio) {
            cropW = srcH * destRatio;
            cropX = (srcW - cropW) / 2;
          } else {
            cropH = srcW / destRatio;
            cropY = (srcH - cropH) / 2;
          }
          ctx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, targetW, targetH);
        } else {
          // Contain (Letterbox / Pillarbox)
          let renderW = targetW;
          let renderH = targetH;
          let offsetX = 0;
          let offsetY = 0;
          if (srcRatio > destRatio) {
            renderH = targetW / srcRatio;
            offsetY = (targetH - renderH) / 2;
          } else {
            renderW = targetH * srcRatio;
            offsetX = (targetW - renderW) / 2;
          }
          ctx.drawImage(video, offsetX, offsetY, renderW, renderH);
        }
      } else {
        // 2. Procedural Audio-Reactive 60 FPS Canvas Shader & Wireframe Engine
        const cx = targetW / 2;
        const cy = targetH / 2;

        if (activePresetId === 'cyber_city') {
          // ─── CYBER CITY WIREFRAME GRID (SYNTHWAVE) ───
          // Horizon gradient
          const horizY = targetH * 0.58;
          const skyGrad = ctx.createLinearGradient(0, 0, 0, horizY);
          skyGrad.addColorStop(0, '#090514');
          skyGrad.addColorStop(0.7, '#1b0c36');
          skyGrad.addColorStop(1, '#ff007f');
          ctx.fillStyle = skyGrad;
          ctx.fillRect(0, 0, targetW, horizY);

          // Neon Sun
          const sunR = Math.min(targetW, targetH) * 0.18 * (1 + bassEnergy * 0.15);
          const sunGrad = ctx.createLinearGradient(cx, horizY - sunR, cx, horizY + sunR);
          sunGrad.addColorStop(0, '#fffa00');
          sunGrad.addColorStop(0.5, '#ff007f');
          sunGrad.addColorStop(1, '#7a00ff');
          ctx.fillStyle = sunGrad;
          ctx.beginPath();
          ctx.arc(cx, horizY - 20, sunR, Math.PI, 0, false);
          ctx.fill();

          // Sun horizontal scanlines
          ctx.fillStyle = '#090514';
          for (let y = horizY - sunR; y < horizY; y += 12) {
            ctx.fillRect(cx - sunR - 10, y, sunR * 2 + 20, 3);
          }

          // Ground 3D Perspective Grid
          const groundGrad = ctx.createLinearGradient(0, horizY, 0, targetH);
          groundGrad.addColorStop(0, '#0a001a');
          groundGrad.addColorStop(1, '#020008');
          ctx.fillStyle = groundGrad;
          ctx.fillRect(0, horizY, targetW, targetH - horizY);

          // Perspective Grid Lines
          ctx.strokeStyle = `rgba(0, 240, 255, ${0.4 + bassEnergy * 0.5})`;
          ctx.lineWidth = 1.5;
          const numVLines = 18;
          for (let i = -numVLines; i <= numVLines; i++) {
            const spread = (i / numVLines) * (targetW * 1.6);
            ctx.beginPath();
            ctx.moveTo(cx, horizY);
            ctx.lineTo(cx + spread, targetH);
            ctx.stroke();
          }

          // Moving horizontal depth lines
          const gridSpeed = (phase * 120) % 60;
          for (let d = 0; d < 12; d++) {
            const p = Math.pow((d * 5 + gridSpeed) / 60, 2.2);
            const lineY = horizY + p * (targetH - horizY);
            ctx.strokeStyle = `rgba(255, 0, 127, ${p * 0.8})`;
            ctx.beginPath();
            ctx.moveTo(0, lineY);
            ctx.lineTo(targetW, lineY);
            ctx.stroke();
          }

          // Audio-reactive City Silhouette Blocks
          const numBuildings = 20;
          const bW = targetW / numBuildings;
          ctx.fillStyle = '#06020e';
          ctx.strokeStyle = '#00f0ff';
          ctx.lineWidth = 1;
          for (let i = 0; i < numBuildings; i++) {
            const fftIndex = (i * 3) % 64;
            const bHeight = 40 + (fftBuffer[fftIndex] || 0.2) * 180 + Math.sin(i * 1.5) * 30;
            const bx = i * bW;
            const by = horizY - bHeight;
            ctx.fillRect(bx, by, bW - 2, bHeight);
            ctx.strokeRect(bx, by, bW - 2, bHeight);

            // Windows
            ctx.fillStyle = (i + Math.floor(phase * 2)) % 3 === 0 ? '#ff007f' : '#00f0ff';
            ctx.fillRect(bx + 4, by + 10, 4, 6);
            ctx.fillRect(bx + bW - 10, by + 25, 4, 6);
            ctx.fillStyle = '#06020e';
          }

        } else if (activePresetId === 'matrix_tunnel') {
          // ─── 3D MATRIX DATA TUNNEL ───
          ctx.fillStyle = 'rgba(2, 8, 14, 0.9)';
          ctx.fillRect(0, 0, targetW, targetH);

          const rings = 12;
          for (let r = 0; r < rings; r++) {
            const depth = ((r + (phase * 1.5)) % rings) / rings;
            const radius = Math.pow(depth, 1.8) * Math.min(targetW, targetH) * 0.7;
            const alpha = depth * (0.3 + bassEnergy * 0.7);
            ctx.strokeStyle = `rgba(16, 185, 129, ${alpha})`;
            ctx.lineWidth = 2 + depth * 3;

            ctx.beginPath();
            const segments = 8;
            for (let s = 0; s < segments; s++) {
              const ang = (s / segments) * Math.PI * 2 + (phase * 0.2 * (r % 2 ? 1 : -1));
              const px = cx + Math.cos(ang) * radius;
              const py = cy + Math.sin(ang) * radius;
              if (s === 0) ctx.moveTo(px, py);
              else ctx.lineTo(px, py);
            }
            ctx.closePath();
            ctx.stroke();
          }

          // Tunnel Rays
          ctx.strokeStyle = `rgba(0, 240, 255, ${0.15 + midEnergy * 0.4})`;
          ctx.lineWidth = 1;
          for (let a = 0; a < 8; a++) {
            const ang = (a / 8) * Math.PI * 2 + (phase * 0.1);
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + Math.cos(ang) * targetW, cy + Math.sin(ang) * targetH);
            ctx.stroke();
          }

        } else if (activePresetId === 'spectrum_vault') {
          // ─── NEURAL SPECTRUM 64-BAND VISUALIZER ───
          const numBars = 48;
          const barW = (targetW - 120) / numBars;
          const baseY = targetH * 0.8;

          for (let i = 0; i < numBars; i++) {
            const val = fftBuffer[i % 64] || (0.1 + Math.sin(phase * 4 + i * 0.3) * 0.2);
            const barH = Math.max(8, val * (targetH * 0.6));
            const bx = 60 + i * barW;
            const by = baseY - barH;

            const barGrad = ctx.createLinearGradient(bx, by, bx, baseY);
            barGrad.addColorStop(0, '#ff007f');
            barGrad.addColorStop(0.5, '#00f0ff');
            barGrad.addColorStop(1, '#3b82f6');
            ctx.fillStyle = barGrad;
            ctx.fillRect(bx + 2, by, barW - 4, barH);

            // Peak Dot
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(bx + 2, by - 6, barW - 4, 3);
          }

        } else {
          // ─── GLITCH NEBULA & PARTICLES ───
          ctx.fillStyle = '#080512';
          ctx.fillRect(0, 0, targetW, targetH);

          const particles = 60;
          for (let p = 0; p < particles; p++) {
            const ang = (p / particles) * Math.PI * 2 + (phase * 0.5);
            const dist = (50 + Math.sin(p * 3 + phase) * 40) * (1 + bassEnergy * 2.5);
            const px = cx + Math.cos(ang) * dist * 3;
            const py = cy + Math.sin(ang) * dist * 1.8;
            const rad = 3 + (p % 5) + bassEnergy * 8;

            ctx.fillStyle = p % 2 === 0 ? 'rgba(139, 92, 246, 0.8)' : 'rgba(0, 240, 255, 0.8)';
            ctx.beginPath();
            ctx.arc(px, py, rad, 0, Math.PI * 2);
            ctx.fill();
          }
        }

        // 3. Audio Energy HUD Arc (Center Bottom)
        const arcR = 36 * (1 + bassEnergy * 0.2);
        ctx.strokeStyle = '#00f0ff';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(cx, targetH - 60, arcR, Math.PI, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = isPlaying ? '#00f0ff' : '#64748b';
        ctx.font = 'bold 12px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(isPlaying ? `● LIVE DSP SYNC • ${bpm} BPM` : '⏸ DAW PAUSED', cx, targetH - 35);
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      isRunning = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [selectedVideo, activePresetId, isPlaying, bpm, fitMode, getAspectDimensions]);

  const handleSelectPreset = (preset) => {
    setActivePresetId(preset.id);
    setSelectedVideo(null);
  };

  const handleLocalVideoUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const blobUrl = URL.createObjectURL(file);
      setSelectedVideo(blobUrl);
    }
  };

  const handleGenerateAIScene = async () => {
    setIsGeneratingScene(true);
    try {
      const res = await fetch('http://localhost:8080/api/studio/generate_ai_scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText, engine: 'comfyui' })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.stream_url) {
          setSelectedVideo(data.stream_url);
        }
      }
    } catch (e) {
      console.warn('AI Scene Gen error:', e);
    } finally {
      setIsGeneratingScene(false);
      setShowPromptModal(false);
    }
  };

  const handleScrollForward = (e) => {
    const canvas = document.querySelector('.daw-center-canvas');
    if (canvas) {
      canvas.scrollTop += e.deltaY;
    }
  };

  return (
    <div 
      onWheel={handleScrollForward}
      style={{
        background: 'rgba(10, 13, 18, 0.98)',
        border: `1px solid ${theme.colors.border}`,
        borderRadius: '8px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}
    >
      {/* Monitor Header */}
      <div style={{
        padding: '5px 8px',
        borderBottom: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(18, 22, 28, 0.95)',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Film size={13} color={theme.colors.accent} />
          <h3 style={{ margin: 0, fontSize: '11px', color: '#fff', fontWeight: 'bold', letterSpacing: '0.5px' }}>
            VIDEO PREVIEW MONITOR
          </h3>
          <span style={{
            fontSize: '9px',
            background: isPlaying ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
            color: isPlaying ? '#00f0ff' : '#666',
            padding: '1px 5px',
            borderRadius: '3px',
            border: `1px solid ${isPlaying ? 'rgba(0, 240, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '3px'
          }}>
            <Radio size={9} /> {isPlaying ? '60FPS DSP SYNC' : 'STANDBY'}
          </span>
        </div>

        {/* Aspect Ratio, Fit Mode, Latency Drawer & Controls */}
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {onToggleTheater && (
            <button
              onClick={onToggleTheater}
              title={isTheater ? 'Restore Standard Layout' : 'Expand Wide Theater Mode (70% Width)'}
              style={{
                background: isTheater ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                border: isTheater ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '4px',
                color: isTheater ? '#00f0ff' : '#ccc',
                padding: '2px 6px',
                fontSize: '10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
                fontWeight: 'bold'
              }}
            >
              {isTheater ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
              {isTheater ? 'Standard' : 'Theater'}
            </button>
          )}

          {/* Fit Mode Toggle */}
          <button
            onClick={() => {
              const modes = ['fit', 'fill', 'stretch'];
              const nextIdx = (modes.indexOf(fitMode) + 1) % modes.length;
              setFitMode(modes[nextIdx]);
            }}
            title="Toggle Framing (Fit Contain / Fill Cover / Stretch)"
            style={{
              background: fitMode === 'fit' ? 'rgba(0, 240, 255, 0.15)' : fitMode === 'fill' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: fitMode === 'fit' ? '1px solid #00f0ff' : fitMode === 'fill' ? '1px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px',
              color: fitMode === 'fit' ? '#00f0ff' : fitMode === 'fill' ? '#c084fc' : '#ccc',
              padding: '2px 6px',
              fontSize: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              fontWeight: 'bold'
            }}
          >
            <Scaling size={11} /> {fitMode.toUpperCase()}
          </button>

          {/* Aspect Ratio Switcher */}
          <button
            onClick={() => {
              const ratios = ['16:9', '9:16', '21:9', '4:3'];
              const nextIdx = (ratios.indexOf(aspectRatio) + 1) % ratios.length;
              setAspectRatio(ratios[nextIdx]);
            }}
            title="Switch Aspect Ratio (16:9 / 9:16 Shorts / 21:9 Ultrawide / 4:3)"
            style={{
              background: 'rgba(0, 255, 255, 0.1)',
              border: `1px solid ${theme.colors.accent}`,
              borderRadius: '4px',
              color: theme.colors.accent,
              padding: '2px 6px',
              fontSize: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              fontWeight: 'bold'
            }}
          >
            {aspectRatio === '9:16' ? <Smartphone size={11} /> : <Monitor size={11} />}
            {aspectRatio}
          </button>

          {/* Latency Calibration Offset Drawer Toggle */}
          <button
            onClick={() => setShowLatencyDrawer(!showLatencyDrawer)}
            title="Adjust Latency Offset Calibration (-300ms to +300ms)"
            style={{
              background: latencyOffsetMs !== 0 ? 'rgba(234, 179, 8, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: latencyOffsetMs !== 0 ? '1px solid #eab308' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px',
              color: latencyOffsetMs !== 0 ? '#fde047' : '#aaa',
              padding: '2px 6px',
              fontSize: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              fontWeight: 'bold'
            }}
          >
            <Clock size={11} /> {latencyOffsetMs >= 0 ? `+${latencyOffsetMs}ms` : `${latencyOffsetMs}ms`}
          </button>

          {/* Load Local File */}
          <button
            onClick={() => fileInputRef.current?.click()}
            title="Load Local Video File (.mp4, .webm, .mov)"
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px',
              color: '#ccc',
              padding: '2px 6px',
              fontSize: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px'
            }}
          >
            <Upload size={11} /> Load Clip
          </button>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleLocalVideoUpload} 
            accept="video/*" 
            style={{ display: 'none' }} 
          />

          {/* AI Scene Gen */}
          <button
            onClick={() => setShowPromptModal(!showPromptModal)}
            title="Generate AI Scene with ComfyUI Wan2.1"
            style={{
              background: 'linear-gradient(135deg, rgba(255, 0, 127, 0.2), rgba(122, 40, 138, 0.3))',
              border: '1px solid #ff007f',
              borderRadius: '4px',
              color: '#ff007f',
              padding: '2px 6px',
              fontSize: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              fontWeight: 'bold'
            }}
          >
            <Sparkles size={11} /> AI Scene
          </button>

          {/* Audio Mute */}
          <button
            onClick={() => setIsMuted(!isMuted)}
            title={isMuted ? 'Unmute Video Audio' : 'Mute Video Audio'}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px',
              color: '#ccc',
              padding: '2px 5px',
              fontSize: '10px',
              cursor: 'pointer'
            }}
          >
            {isMuted ? <VolumeX size={11} /> : <Volume2 size={11} />}
          </button>
        </div>
      </div>

      {/* Latency Calibration Drawer */}
      {showLatencyDrawer && (
        <div style={{
          background: 'rgba(15, 20, 30, 0.98)',
          borderBottom: '1px solid #eab308',
          padding: '6px 10px',
          display: 'flex',
          gap: '12px',
          alignItems: 'center',
          fontSize: '10px',
          flexShrink: 0
        }}>
          <span style={{ color: '#fde047', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Sliders size={12} /> LATENCY COMPENSATION:
          </span>
          <input
            type="range"
            min="-300"
            max="300"
            step="5"
            value={latencyOffsetMs}
            onChange={(e) => setLatencyOffsetMs(parseInt(e.target.value, 10))}
            style={{ flex: 1, accentColor: '#eab308' }}
          />
          <span style={{ color: '#fff', fontFamily: 'monospace', width: '55px', textAlign: 'right' }}>
            {latencyOffsetMs >= 0 ? `+${latencyOffsetMs}ms` : `${latencyOffsetMs}ms`}
          </span>
          <button
            onClick={() => setLatencyOffsetMs(0)}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#fff',
              borderRadius: '3px',
              padding: '1px 6px',
              fontSize: '9px',
              cursor: 'pointer'
            }}
          >
            Reset (0ms)
          </button>
        </div>
      )}

      {/* AI Scene Prompt Drawer */}
      {showPromptModal && (
        <div style={{
          background: 'rgba(15, 20, 30, 0.98)',
          borderBottom: `1px solid #ff007f`,
          padding: '6px 8px',
          display: 'flex',
          gap: '6px',
          alignItems: 'center',
          flexShrink: 0
        }}>
          <input
            type="text"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder="Enter AI video generation prompt..."
            style={{
              flex: 1,
              background: '#000',
              border: '1px solid #30363d',
              borderRadius: '4px',
              padding: '4px 8px',
              color: '#fff',
              fontSize: '10px',
              outline: 'none'
            }}
          />
          <button
            onClick={handleGenerateAIScene}
            disabled={isGeneratingScene}
            style={{
              background: 'linear-gradient(135deg, #ff007f, #7a288a)',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '10px',
              fontWeight: 'bold',
              cursor: isGeneratingScene ? 'not-allowed' : 'pointer'
            }}
          >
            {isGeneratingScene ? 'Rendering...' : 'Generate Clip'}
          </button>
        </div>
      )}

      {/* Video Viewport Canvas */}
      <div style={{
        flex: 1,
        minHeight: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#000',
        position: 'relative',
        overflow: 'hidden'
      }}>
        {/* Hidden video element for media stream playback */}
        <video
          ref={videoRef}
          src={selectedVideo ? (selectedVideo.startsWith('blob:') || selectedVideo.startsWith('http') ? selectedVideo : selectedVideo) : undefined}
          muted={isMuted}
          loop
          playsInline
          style={{ display: 'none' }}
        />

        {/* 60 FPS Accelerated Compositor Canvas */}
        <canvas
          ref={canvasRef}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            aspectRatio: aspectRatio.replace(':', ' / '),
            objectFit: fitMode === 'stretch' ? 'fill' : fitMode === 'fill' ? 'cover' : 'contain',
            boxShadow: '0 0 25px rgba(0, 0, 0, 0.8)'
          }}
        />

        {/* Sync Timecode & Framing HUD */}
        <div style={{
          position: 'absolute',
          bottom: '8px',
          left: '8px',
          background: 'rgba(0, 0, 0, 0.85)',
          border: '1px solid rgba(0, 240, 255, 0.3)',
          borderRadius: '4px',
          padding: '3px 7px',
          fontSize: '9px',
          fontFamily: 'monospace',
          color: '#00f0ff',
          pointerEvents: 'none',
          zIndex: 5,
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span>TC: 00:0{currentBar + 1}:{(currentStep * 2).toString().padStart(2, '0')}:00</span>
          <span>•</span>
          <span>{aspectRatio} ({fitMode.toUpperCase()})</span>
          {latencyOffsetMs !== 0 && <span style={{ color: '#fde047' }}>• OFFSET: {latencyOffsetMs}ms</span>}
        </div>
      </div>

      {/* Procedural Visualizer Presets Bar */}
      <div style={{
        height: '28px',
        background: 'rgba(15, 18, 24, 0.95)',
        borderTop: '1px solid rgba(255, 255, 255, 0.05)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        gap: '6px',
        overflowX: 'auto',
        flexShrink: 0
      }}>
        <span style={{ fontSize: '9px', color: '#666', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '3px' }}>
          <Zap size={10} color="#00f0ff" /> PRESETS:
        </span>
        {PROCEDURAL_PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelectPreset(p)}
            style={{
              background: activePresetId === p.id && !selectedVideo ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.04)',
              border: activePresetId === p.id && !selectedVideo ? `1px solid ${p.color}` : '1px solid rgba(255, 255, 255, 0.08)',
              color: activePresetId === p.id && !selectedVideo ? p.color : '#888',
              borderRadius: '3px',
              padding: '2px 7px',
              fontSize: '9px',
              fontWeight: activePresetId === p.id && !selectedVideo ? 'bold' : 'normal',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: p.color }} />
            {p.name}
          </button>
        ))}
      </div>
    </div>
  );
}
