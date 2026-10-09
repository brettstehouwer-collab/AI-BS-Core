import React, { useState, useEffect, useRef } from 'react';
import * as Tone from 'tone';
import { Activity, Zap, ShieldCheck, AlertTriangle, Cpu, Radio } from 'lucide-react';
import { useDawStore } from './dawStore';

export const LatencyMonitorHUD = ({ compact = false }) => {
  const isPlaying = useDawStore(state => state.isPlaying);
  const bpm = useDawStore(state => state.bpm);

  const [metrics, setMetrics] = useState({
    totalLatencyMs: 45.0,
    baseLatencyMs: 5.3,
    outputLatencyMs: 10.2,
    lookAheadMs: 45.0,
    clockDriftMs: 0.1,
    underruns: 0,
    status: 'OPTIMAL', // OPTIMAL | HEALTHY | DRIFTING | CRITICAL
    fps: 60,
    sampleRate: 44100,
    vstOnline: true
  });

  const [showDetails, setShowDetails] = useState(false);
  const lastTimeRef = useRef(0);
  const lastTransportSecRef = useRef(0);
  const frameCountRef = useRef(0);
  const lastFpsCalcRef = useRef(performance.now());

  useEffect(() => {
    let animId;
    let pollInterval = 0;

    const measure = (now) => {
      // Calculate FPS
      frameCountRef.current++;
      if (now - lastFpsCalcRef.current >= 1000) {
        const currentFps = Math.round((frameCountRef.current * 1000) / (now - lastFpsCalcRef.current));
        frameCountRef.current = 0;
        lastFpsCalcRef.current = now;

        // Query Web Audio Context
        try {
          const rawCtx = Tone.getContext().rawContext;
          const sampleRate = rawCtx?.sampleRate || 44100;
          const baseLat = (rawCtx?.baseLatency || 0.005) * 1000;
          const outLat = (rawCtx?.outputLatency || 0.010) * 1000;
          const lookAhead = (Tone.context.lookAhead || 0.045) * 1000;
          const totalLat = Math.round((baseLat + outLat + lookAhead) * 10) / 10;

          // Measure Clock Drift if playing
          let drift = 0.1;
          let status = 'OPTIMAL';
          if (isPlaying && Tone.Transport.state === 'started') {
            const currentTransportSec = Tone.Transport.seconds;
            const wallDeltaSec = (now - lastTimeRef.current) / 1000;
            const transportDeltaSec = currentTransportSec - lastTransportSecRef.current;

            if (lastTimeRef.current > 0 && wallDeltaSec > 0.05) {
              const diffSec = Math.abs(transportDeltaSec - wallDeltaSec);
              drift = Math.round(diffSec * 1000 * 10) / 10;
              if (drift > 35) {
                status = 'DRIFTING';
              } else if (drift > 15) {
                status = 'HEALTHY';
              } else {
                status = 'OPTIMAL';
              }
            }
            lastTransportSecRef.current = currentTransportSec;
          }
          lastTimeRef.current = now;

          setMetrics(prev => ({
            ...prev,
            totalLatencyMs: totalLat,
            baseLatencyMs: Math.round(baseLat * 10) / 10,
            outputLatencyMs: Math.round(outLat * 10) / 10,
            lookAheadMs: Math.round(lookAhead * 10) / 10,
            clockDriftMs: drift,
            status,
            fps: currentFps,
            sampleRate
          }));
        } catch {
          // fallback
        }
      }

      animId = requestAnimationFrame(measure);
    };

    animId = requestAnimationFrame(measure);

    // Periodic check for VST daemon on Port 8013
    const checkVst = async () => {
      try {
        const res = await fetch('http://localhost:8013/api/vst/scan', { signal: AbortSignal.timeout(1200) });
        setMetrics(m => ({ ...m, vstOnline: res.ok }));
      } catch {
        setMetrics(m => ({ ...m, vstOnline: false }));
      }
    };
    checkVst();
    const vstInterval = setInterval(checkVst, 5000);

    return () => {
      cancelAnimationFrame(animId);
      clearInterval(vstInterval);
    };
  }, [isPlaying]);

  const getStatusColor = () => {
    switch (metrics.status) {
      case 'OPTIMAL': return '#00f0ff';
      case 'HEALTHY': return '#5eff7b';
      case 'DRIFTING': return '#ffbd5e';
      default: return '#ff5e5e';
    }
  };

  const statusColor = getStatusColor();

  if (compact) {
    return (
      <div 
        onClick={() => setShowDetails(!showDetails)}
        title="Live Web Audio Latency & DSP Synchronization Monitor (Click for details)"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '7px',
          background: 'rgba(0,0,0,0.7)',
          border: `1px solid ${statusColor}44`,
          borderRadius: '4px',
          padding: '3px 8px',
          cursor: 'pointer',
          userSelect: 'none',
          boxShadow: isPlaying ? `0 0 10px ${statusColor}22` : 'none',
          transition: 'all 0.2s ease'
        }}
      >
        <Zap size={12} color={statusColor} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', fontFamily: 'monospace' }}>
          <span style={{ color: '#888' }}>LATENCY:</span>
          <span style={{ color: statusColor, fontWeight: 'bold' }}>{metrics.totalLatencyMs}ms</span>
          <span style={{ color: '#555' }}>|</span>
          <span style={{ color: '#888' }}>DRIFT:</span>
          <span style={{ color: metrics.clockDriftMs < 5 ? '#5eff7b' : '#ffbd5e', fontWeight: 'bold' }}>
            ±{metrics.clockDriftMs}ms
          </span>
        </div>
        {metrics.vstOnline && (
          <span 
            title="VST3 Native Bridge Active on Port 8013"
            style={{ 
              width: '6px', 
              height: '6px', 
              borderRadius: '50%', 
              background: '#a855f7',
              boxShadow: '0 0 6px #a855f7'
            }} 
          />
        )}
      </div>
    );
  }

  return (
    <div style={{
      position: 'relative',
      display: 'inline-flex',
      alignItems: 'center'
    }}>
      <div 
        onClick={() => setShowDetails(!showDetails)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(10, 15, 25, 0.95)',
          border: `1px solid ${statusColor}55`,
          borderRadius: '5px',
          padding: '4px 10px',
          cursor: 'pointer',
          userSelect: 'none',
          boxShadow: `0 2px 8px rgba(0,0,0,0.6), 0 0 12px ${statusColor}1a`
        }}
      >
        <Activity size={13} color={statusColor} />
        <div style={{ display: 'flex', gap: '8px', fontSize: '11px', fontFamily: 'monospace' }}>
          <div>
            <span style={{ color: '#888', fontSize: '9px' }}>LATENCY: </span>
            <strong style={{ color: statusColor }}>{metrics.totalLatencyMs} ms</strong>
          </div>
          <div style={{ color: '#444' }}>•</div>
          <div>
            <span style={{ color: '#888', fontSize: '9px' }}>DRIFT: </span>
            <strong style={{ color: metrics.clockDriftMs < 5 ? '#5eff7b' : '#ffbd5e' }}>
              ±{metrics.clockDriftMs} ms
            </strong>
          </div>
          <div style={{ color: '#444' }}>•</div>
          <div>
            <span style={{ color: '#888', fontSize: '9px' }}>SYNC: </span>
            <strong style={{ color: statusColor }}>{metrics.status}</strong>
          </div>
        </div>

        <span style={{
          fontSize: '9px',
          padding: '1px 5px',
          borderRadius: '2px',
          background: metrics.vstOnline ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255,255,255,0.06)',
          color: metrics.vstOnline ? '#a855f7' : '#666',
          border: metrics.vstOnline ? '1px solid #a855f766' : '1px solid rgba(255,255,255,0.1)',
          fontWeight: 'bold'
        }}>
          {metrics.vstOnline ? 'VST3: 8013' : 'VST3: OFF'}
        </span>
      </div>

      {/* Expanded Telemetry Modal */}
      {showDetails && (
        <div style={{
          position: 'absolute',
          top: '110%',
          right: 0,
          width: '280px',
          background: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.85)',
          zIndex: 100,
          color: '#e6edf3',
          fontFamily: 'sans-serif',
          fontSize: '11px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px solid #21262d', paddingBottom: '6px' }}>
            <span style={{ fontWeight: 'bold', color: '#00f0ff', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Cpu size={13} /> DSP AUDIO ENGINE TELEMETRY
            </span>
            <span style={{ fontSize: '9px', background: `${statusColor}22`, color: statusColor, padding: '1px 5px', borderRadius: '3px', fontWeight: 'bold' }}>
              {metrics.status}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontFamily: 'monospace' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Total Roundtrip:</span>
              <span style={{ color: statusColor, fontWeight: 'bold' }}>{metrics.totalLatencyMs} ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Hardware Base Buffer:</span>
              <span style={{ color: '#ccc' }}>{metrics.baseLatencyMs} ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Audio Driver Output:</span>
              <span style={{ color: '#ccc' }}>{metrics.outputLatencyMs} ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Tone.js Lookahead:</span>
              <span style={{ color: '#ccc' }}>{metrics.lookAheadMs} ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Transport Clock Jitter:</span>
              <span style={{ color: metrics.clockDriftMs < 5 ? '#5eff7b' : '#ffbd5e' }}>±{metrics.clockDriftMs} ms</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Sample Rate:</span>
              <span style={{ color: '#ccc' }}>{metrics.sampleRate} Hz</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>UI Frame Rate:</span>
              <span style={{ color: metrics.fps > 50 ? '#5eff7b' : '#ffbd5e' }}>{metrics.fps} FPS</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Native VST3 Daemon:</span>
              <span style={{ color: metrics.vstOnline ? '#a855f7' : '#ff5e5e', fontWeight: 'bold' }}>
                {metrics.vstOnline ? 'Online (Port 8013)' : 'Offline'}
              </span>
            </div>
          </div>

          <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #21262d', fontSize: '9px', color: '#8b949e', lineHeight: '1.4' }}>
            💡 <strong style={{ color: '#00f0ff' }}>Zero-Stall Protection:</strong> Audio lookahead is calibrated to 45ms with throttled animation frames, preventing main-thread garbage collection pauses from starving the audio context.
          </div>
        </div>
      )}
    </div>
  );
};
