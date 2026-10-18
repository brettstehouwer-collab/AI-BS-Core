// =========================================================================
// AI-BS Sovereign Intelligence Ecosystem - Tap-To-Run Canvas Component
// File: C:\AI-BS\frontend\src\components\TapToRunCanvas.jsx
// Description: Staged Payload Queue & Click-Triggered Headless Canvas Runner
// Execution Guarantee: Strictly passive until the user explicitly taps "Run"
// =========================================================================

import React, { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Extracts BASH and PYTHON code blocks from raw message text to populate
 * the stagedPayloads queue without executing any code.
 */
export function extractStagedPayloads(messageText) {
  if (!messageText || typeof messageText !== 'string') {
    return { bash: [], python: [] };
  }

  const stagedPayloads = { bash: [], python: [] };
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\s*\n([\s\S]*?)```/g;
  let match;

  while ((match = codeBlockRegex.exec(messageText)) !== null) {
    const lang = (match[1] || '').toLowerCase().trim();
    const code = match[2].trim();

    if (lang === 'bash' || lang === 'sh' || lang === 'shell' || lang === 'powershell' || lang === 'cmd') {
      stagedPayloads.bash.push(code);
    } else if (lang === 'python' || lang === 'py') {
      stagedPayloads.python.push(code);
    } else if (code.startsWith('mkdir ') || code.includes('pip install')) {
      stagedPayloads.bash.push(code);
    } else if (code.includes('import pygame') || code.includes('class ChessGame') || code.includes('class CheckersGame')) {
      stagedPayloads.python.push(code);
    }
  }

  return stagedPayloads;
}

/**
 * TapToRunCanvas renders an interactive trigger button for staged code payloads.
 * Nothing runs during LLM streaming. Execution only begins when the user taps "Run".
 */
export default function TapToRunCanvas({
  label = 'Interactive Canvas',
  stagedPayloads = { bash: [], python: [] },
  backendUrl = '',
  targetDir = 'C:\\AI-BS\\backend\\chess\\animated_chess'
}) {
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState('STAGED (IDLE)');
  const [pid, setPid] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [showPayloadDetails, setShowPayloadDetails] = useState(false);

  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const fallbackPollRef = useRef(null);
  const isRunningRef = useRef(false);

  // Keep isRunningRef in sync for cleanup/listeners
  useEffect(() => {
    isRunningRef.current = isRunning;
  }, [isRunning]);

  // Determine active daemon endpoints
  const getBackendEndpoints = useCallback(() => {
    let httpBase = backendUrl;
    if (!httpBase) {
      if (typeof window !== 'undefined') {
        const host = window.location.hostname || '127.0.0.1';
        const port = window.location.port === '8080' ? '8080' : '8080';
        httpBase = `http://${host}:${port}`;
      } else {
        httpBase = 'http://127.0.0.1:8080';
      }
    }

    // Replace localhost in mobile/https environments if needed
    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && (httpBase.includes('127.0.0.1') || httpBase.includes('localhost'))) {
      httpBase = 'https://api.brettstehouwer.live';
    }

    let wsBase = httpBase.replace(/^http/, 'ws');
    return { httpBase, wsBase };
  }, [backendUrl]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (e) { /* silent */ }
        wsRef.current = null;
      }
      if (fallbackPollRef.current) {
        clearInterval(fallbackPollRef.current);
        fallbackPollRef.current = null;
      }
    };
  }, []);

  // Forward mouse / touch coordinates to backend
  const handlePointerDown = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * 800);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * 800);

    const eventPayload = {
      type: 'MOUSEBUTTONDOWN',
      x: Math.max(0, Math.min(800, x)),
      y: Math.max(0, Math.min(800, y)),
      button: 1,
      timestamp: Date.now()
    };

    // Forward over active WebSocket if available
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(eventPayload));
        return;
      } catch (err) {
        // Fallback to HTTP input endpoint
      }
    }

    // Fallback: send via HTTP POST
    const { httpBase } = getBackendEndpoints();
    fetch(`${httpBase}/api/canvas/input`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(eventPayload)
    }).catch(() => { /* silent */ });
  };

  const handleStop = async () => {
    setStatus('STOPPING...');
    if (wsRef.current) {
      try { wsRef.current.close(); } catch (e) { /* silent */ }
      wsRef.current = null;
    }
    if (fallbackPollRef.current) {
      clearInterval(fallbackPollRef.current);
      fallbackPollRef.current = null;
    }

    try {
      const { httpBase } = getBackendEndpoints();
      await fetch(`${httpBase}/api/canvas/stop`, { method: 'POST' });
    } catch (e) {
      // Continue cleanup regardless
    }

    setIsRunning(false);
    setPid(null);
    setStatus('TERMINATED');
  };

  const handleRun = async () => {
    if (isRunning) {
      await handleStop();
      return;
    }

    setErrorMessage('');
    setStatus('PROVISIONING & LAUNCHING...');

    try {
      const { httpBase, wsBase } = getBackendEndpoints();

      const res = await fetch(`${httpBase}/api/canvas/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label,
          target_dir: targetDir,
          bash_commands: stagedPayloads?.bash || [],
          python_scripts: stagedPayloads?.python || []
        })
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();

      if (data.status === 'running') {
        setIsRunning(true);
        setPid(data.pid);
        setStatus(`LIVE [PID: ${data.pid}]`);

        // Connect WebSocket frame streamer
        setTimeout(() => {
          connectWebSocket(wsBase, httpBase);
        }, 150);
      } else {
        setStatus(data.status || 'ERROR');
        setErrorMessage(data.message || 'Execution failed to start.');
      }
    } catch (err) {
      setStatus('ERROR');
      setErrorMessage(err.message || 'Could not connect to root daemon (Port 8080).');
    }
  };

  const connectWebSocket = (wsBase, httpBase) => {
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const socket = new WebSocket(`${wsBase}/ws/canvas`);
      socket.binaryType = 'blob';

      socket.onmessage = async (ev) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        try {
          const bmp = await createImageBitmap(ev.data);
          ctx.drawImage(bmp, 0, 0, 800, 800);
          bmp.close();
        } catch (e) {
          // Fallback image rendering
          const img = new Image();
          img.onload = () => {
            ctx.drawImage(img, 0, 0, 800, 800);
            URL.revokeObjectURL(img.src);
          };
          img.src = URL.createObjectURL(ev.data);
        }
      };

      socket.onerror = () => {
        // Fallback to HTTP polling if WebSocket is blocked or fails
        startFallbackHttpPolling(httpBase);
      };

      socket.onclose = () => {
        if (isRunningRef.current) {
          // If connection drops while game is supposed to be live, try fallback polling
          startFallbackHttpPolling(httpBase);
        }
      };

      wsRef.current = socket;
    } catch (err) {
      startFallbackHttpPolling(httpBase);
    }
  };

  const startFallbackHttpPolling = (httpBase) => {
    if (fallbackPollRef.current) return;

    fallbackPollRef.current = setInterval(async () => {
      const canvas = canvasRef.current;
      if (!canvas || !isRunningRef.current) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      try {
        const res = await fetch(`${httpBase}/api/canvas/frame?t=${Date.now()}`);
        if (res.ok) {
          const blob = await res.blob();
          const bmp = await createImageBitmap(blob);
          ctx.drawImage(bmp, 0, 0, 800, 800);
          bmp.close();
        }
      } catch (e) {
        // Silent polling error retry
      }
    }, 40); // ~25 FPS fallback
  };

  const stagedCount = (stagedPayloads?.bash?.length || 0) + (stagedPayloads?.python?.length || 0);

  return (
    <div
      style={{
        margin: '14px 0',
        background: '#0c0d16',
        border: '1px solid #7c3aed',
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: '0 6px 24px rgba(124, 58, 237, 0.25)'
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
          padding: '10px 14px',
          background: '#151628',
          borderBottom: isRunning ? '1px solid rgba(124, 58, 237, 0.4)' : 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleRun}
            style={{
              background: isRunning ? '#e11d48' : '#7c3aed',
              color: '#ffffff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              fontWeight: '700',
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: isRunning ? '0 0 12px rgba(225, 29, 72, 0.4)' : '0 0 12px rgba(124, 58, 237, 0.4)',
              transition: 'all 0.2s ease'
            }}
          >
            {isRunning ? `■ Stop ${label}` : `▶ Run ${label}`}
          </button>

          <span
            style={{
              fontFamily: 'monospace',
              fontSize: '0.78rem',
              fontWeight: '600',
              color: isRunning ? '#10b981' : status === 'ERROR' ? '#f87171' : '#94a3b8',
              background: 'rgba(255, 255, 255, 0.05)',
              padding: '3px 8px',
              borderRadius: '4px',
              border: '1px solid rgba(255, 255, 255, 0.1)'
            }}
          >
            {status}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {stagedCount > 0 && (
            <button
              onClick={() => setShowPayloadDetails(!showPayloadDetails)}
              style={{
                background: 'transparent',
                color: '#a78bfa',
                border: '1px solid rgba(167, 139, 250, 0.3)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer'
              }}
            >
              {showPayloadDetails ? 'Hide Staged Blocks' : `Staged Blocks (${stagedCount})`}
            </button>
          )}

          <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
            Port 8080 Headless SDL2
          </span>
        </div>
      </div>

      {/* Staged Payload Details Drawer */}
      {showPayloadDetails && (
        <div
          style={{
            padding: '10px 14px',
            background: '#080811',
            borderBottom: '1px solid #1e293b',
            fontSize: '0.75rem',
            fontFamily: 'monospace',
            color: '#cbd5e1'
          }}
        >
          <div style={{ color: '#38bdf8', marginBottom: '4px', fontWeight: 'bold' }}>
            🔒 Staged Execution Buffer (Gated Until Button Tap):
          </div>
          <div>• Target Directory: <span style={{ color: '#a78bfa' }}>{targetDir}</span></div>
          <div>• Staged Bash Commands: {stagedPayloads?.bash?.length || 0}</div>
          <div>• Staged Python Scripts: {stagedPayloads?.python?.length || 0}</div>
          {errorMessage && (
            <div style={{ color: '#f87171', marginTop: '6px' }}>⚠️ Error: {errorMessage}</div>
          )}
        </div>
      )}

      {/* Interactive Canvas Viewport (Mounted when running) */}
      {isRunning && (
        <div
          style={{
            padding: '12px',
            background: '#05050a',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <div
            style={{
              position: 'relative',
              width: '100%',
              maxWidth: '420px',
              aspectRatio: '1 / 1',
              borderRadius: '8px',
              overflow: 'hidden',
              border: '2px solid #00ffff',
              boxShadow: '0 0 25px rgba(0, 255, 255, 0.25)',
              background: '#0a0a14'
            }}
          >
            <canvas
              ref={canvasRef}
              width={800}
              height={800}
              onPointerDown={handlePointerDown}
              style={{
                width: '100%',
                height: '100%',
                display: 'block',
                touchAction: 'none',
                cursor: 'crosshair'
              }}
            />
          </div>

          <div
            style={{
              marginTop: '8px',
              fontSize: '0.72rem',
              color: '#94a3b8',
              display: 'flex',
              gap: '12px',
              justifyContent: 'center'
            }}
          >
            <span>🎮 Tap / Click on board to move pieces</span>
            <span>⚡ 30 FPS Streamed Live</span>
          </div>
        </div>
      )}
    </div>
  );
}
