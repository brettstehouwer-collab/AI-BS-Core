import React, { useState, useEffect, useRef } from 'react';
import { MonitorPlay, WifiOff, Box, Image as ImageIcon, Sparkles, Camera, Play, Square, RefreshCw } from 'lucide-react';

function WebRTCSession({ signalingUrl, onStatusChange }) {
    const videoRef = useRef(null);

    useEffect(() => {
        let ws;
        let pc;
        let isMounted = true;

        const connect = () => {
            if (!isMounted) return;
            if (onStatusChange) onStatusChange('Connecting to Signaling Server...');
            
            try {
                ws = new WebSocket(signalingUrl);
            } catch (e) {
                if (onStatusChange) onStatusChange('Signaling Connection Error');
                return;
            }

            ws.onopen = () => {
                if (isMounted) {
                    if (onStatusChange) onStatusChange('Signaling Connected. Waiting for Unreal Streamer...');
                    ws.send(JSON.stringify({ type: 'player' }));
                }
            };

            let remotePlayerId = null;

            ws.onmessage = async (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'offer') {
                        remotePlayerId = msg.playerId || null;
                        if (onStatusChange) onStatusChange('Negotiating WebRTC Connection...');
                        pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
                        
                        pc.ontrack = (e) => {
                            if (videoRef.current) {
                                if (e.streams && e.streams[0]) {
                                    videoRef.current.srcObject = e.streams[0];
                                } else {
                                    videoRef.current.srcObject = new MediaStream([e.track]);
                                }
                                videoRef.current.play().catch(console.warn);
                                if (onStatusChange) onStatusChange('Streaming 3D Environment');
                            }
                        };

                        pc.onicecandidate = (e) => {
                            if (e.candidate && isMounted) {
                                ws.send(JSON.stringify({ 
                                    type: 'iceCandidate', 
                                    candidate: e.candidate,
                                    ...(remotePlayerId ? { playerId: remotePlayerId } : {})
                                }));
                            }
                        };

                        await pc.setRemoteDescription(new RTCSessionDescription(msg));
                        const answer = await pc.createAnswer();
                        await pc.setLocalDescription(answer);
                        if (isMounted) {
                            ws.send(JSON.stringify({ 
                                type: 'answer', 
                                sdp: answer.sdp,
                                ...(remotePlayerId ? { playerId: remotePlayerId } : {})
                            }));
                        }
                    } else if (msg.type === 'iceCandidate' && pc) {
                        try { await pc.addIceCandidate(new RTCIceCandidate(msg.candidate)); } catch (e) {}
                    } else if (msg.type === 'streamerDisconnected') {
                        if (onStatusChange) onStatusChange('Unreal Engine Streamer Disconnected');
                        if (videoRef.current) videoRef.current.srcObject = null;
                    }
                } catch (err) {
                    console.warn('WebRTC message parsing error:', err);
                }
            };

            ws.onerror = () => {
                if (onStatusChange) onStatusChange('Signaling Server Offline (Port 8888)');
            };

            ws.onclose = () => {
                if (isMounted) {
                    if (onStatusChange) onStatusChange('Signaling Disconnected. Retrying in 5s...');
                    setTimeout(connect, 5000);
                }
            };
        };

        connect();

        return () => { 
            isMounted = false;
            if (pc) pc.close(); 
            if (ws) ws.close(); 
        };
    }, [signalingUrl]);

    return (
        <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted 
            style={{ width: '100%', height: '100%', objectFit: 'contain', backgroundColor: '#000' }} 
        />
    );
}

export default function UnrealPixelStreamBridge({ 
  signalingUrl = "ws://127.0.0.1", 
  port = "8888", 
  height = "560px", 
  title = "Unreal Engine 5.8 | Live 3D Viewport",
  backendUrl = '',
  onAction = async (actionType) => {}
}) {
  const [streamActive, setStreamActive] = useState(true);
  const [streamStatus, setStreamStatus] = useState('Initializing...');
  const [trackerActive, setTrackerActive] = useState(false);
  const [isLaunchingStreamer, setIsLaunchingStreamer] = useState(false);
  const [actionFeedback, setActionFeedback] = useState('');
  
  const streamAddress = `${signalingUrl}:${port}`;

  const handleLaunchStreamer = async () => {
    setIsLaunchingStreamer(true);
    setActionFeedback('🚀 Launching Unreal Engine 5.8 Pixel Streaming engine in background...');
    try {
      const res = await fetch(`${backendUrl}/api/unreal/launch_streamer`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setActionFeedback('🎮 Unreal Engine 5.8 is booting with Pixel Streaming! Connecting to stream in 10s...');
        setStreamActive(true);
      } else {
        setActionFeedback(`⚠️ Launch failed: ${data.message}`);
      }
    } catch (e) {
      setActionFeedback(`❌ Failed to reach backend: ${e.message}`);
    } finally {
      setIsLaunchingStreamer(false);
    }
  };

  const toggleTracker = async () => {
    const endpoint = trackerActive 
      ? `${backendUrl}/api/unreal/tracker/stop` 
      : `${backendUrl}/api/unreal/tracker/start`;
    try {
      const res = await fetch(endpoint, { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        setTrackerActive(!trackerActive);
        setActionFeedback(trackerActive ? 'OpenCV Tracking Stopped' : 'OpenCV Head Tracking Active');
      }
    } catch (e) {
      console.error(e);
      setActionFeedback('Failed to toggle OpenCV tracker');
    }
  };

  const triggerAction = async (actionType) => {
    setActionFeedback(`⚡ Executing ${actionType} in Unreal Engine...`);
    try {
      const res = await fetch(`${backendUrl}/api/unreal/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool_id: actionType, parameters: {} })
      });
      const data = await res.json();
      setActionFeedback(`✅ ${actionType.toUpperCase()} executed: ${data.status}`);
      if (onAction) onAction(actionType);
    } catch (e) {
      console.error(e);
      setActionFeedback(`❌ Action failed: ${e.message}`);
    }
  };

  return (
    <div style={{
      width: '100%',
      backgroundColor: '#0a0a0a',
      border: '1px solid #3d2b1f',
      borderRadius: '8px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      marginTop: '8px',
      marginBottom: '16px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)'
    }}>
      {/* Header / Controls */}
      <div style={{
        padding: '10px 16px',
        backgroundColor: '#14100c',
        borderBottom: '1px solid #3d2b1f',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MonitorPlay size={18} color="#d4af37" />
          <span style={{ color: '#d4af37', fontWeight: 600, fontSize: '14px', fontFamily: '"Playfair Display", serif' }}>
            {title}
          </span>
          <span style={{ 
            fontSize: '11px', 
            background: '#2a1e17', 
            color: '#eab308', 
            padding: '2px 8px', 
            borderRadius: '4px',
            border: '1px solid #451a03'
          }}>
            UE 5.8 RTX 4090
          </span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Action to launch streamer on desktop */}
          <button
            onClick={handleLaunchStreamer}
            disabled={isLaunchingStreamer}
            style={{
              background: '#b45309',
              border: 'none',
              color: '#fff',
              padding: '4px 10px',
              borderRadius: '4px',
              cursor: isLaunchingStreamer ? 'not-allowed' : 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Play size={12} fill="#fff" />
            {isLaunchingStreamer ? 'Booting UE5...' : 'Launch UE5 Streamer'}
          </button>

          <span style={{ 
            color: streamActive ? '#22c55e' : '#ef4444', 
            fontSize: '12px', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '4px' 
          }}>
            <span style={{
              display: 'inline-block',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: streamActive ? '#22c55e' : '#ef4444',
              boxShadow: streamActive ? '0 0 8px #22c55e' : 'none'
            }} />
            {streamActive ? 'WebRTC Ready' : 'Stream Paused'}
          </span>

          <button onClick={() => setStreamActive(!streamActive)} style={{
            background: 'transparent',
            border: '1px solid #d4af37',
            color: '#d4af37',
            padding: '4px 10px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}>
            {streamActive ? 'Disconnect' : 'Connect'}
          </button>
        </div>
      </div>

      {/* Action / Stream feedback status bar */}
      {actionFeedback && (
        <div style={{
          padding: '4px 16px',
          backgroundColor: '#1f1610',
          borderBottom: '1px solid #3d2b1f',
          color: '#fbbf24',
          fontSize: '12px',
          fontFamily: 'monospace'
        }}>
          {actionFeedback}
        </div>
      )}

      {/* Viewport Canvas */}
      <div style={{ width: '100%', height: height, position: 'relative', backgroundColor: '#050505', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {streamActive ? (
          <WebRTCSession signalingUrl={streamAddress} onStatusChange={setStreamStatus} />
        ) : (
          <div style={{ 
            textAlign: 'center',
            color: '#737373',
            padding: '24px'
          }}>
            <WifiOff size={44} style={{ margin: '0 auto 12px', opacity: 0.5 }} />
            <p style={{ margin: 0, fontSize: '14px', color: '#e2e8f0', fontWeight: 'bold' }}>Pixel Streaming Offline</p>
            <p style={{ margin: '6px 0 14px', fontSize: '12px', opacity: 0.7 }}>Click Connect to bind WebRTC stream via Python WS Relay ({streamAddress}).</p>
            <button
              onClick={handleLaunchStreamer}
              style={{
                background: '#d4af37',
                color: '#000',
                fontWeight: 'bold',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              🚀 Launch Unreal Engine 5.8 Now
            </button>
          </div>
        )}
      </div>

      {/* Interaction Bar */}
      <div style={{
        padding: '10px 16px',
        backgroundColor: '#14100c',
        borderTop: '1px solid #3d2b1f',
        display: 'flex',
        gap: '10px',
        alignItems: 'center',
        flexWrap: 'wrap'
      }}>
        <span style={{ color: '#8c7355', fontSize: '12px', marginRight: '4px', fontWeight: 'bold' }}>Native Python Controls:</span>
        
        <button 
          onClick={() => triggerAction("level")}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#e2e8f0',
            fontSize: '12px',
            padding: '4px 10px',
            borderRadius: '4px',
            border: '1px solid #334155',
            cursor: 'pointer'
          }}>
          <Box size={14} color="#34d399" />
          ⚡ Spawn Actors
        </button>

        <button 
          onClick={() => triggerAction("material")}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#e2e8f0',
            fontSize: '12px',
            padding: '4px 10px',
            borderRadius: '4px',
            border: '1px solid #334155',
            cursor: 'pointer'
          }}>
          <ImageIcon size={14} color="#60a5fa" />
          🎨 Change Material
        </button>

        <button 
          onClick={() => triggerAction("niagara")}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#1e293b',
            color: '#e2e8f0',
            fontSize: '12px',
            padding: '4px 10px',
            borderRadius: '4px',
            border: '1px solid #334155',
            cursor: 'pointer'
          }}>
          <Sparkles size={14} color="#f59e0b" />
          ✨ Trigger VFX
        </button>

        <button 
          onClick={toggleTracker}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: trackerActive ? '#064e3b' : '#1e293b',
            color: trackerActive ? '#6ee7b7' : '#e2e8f0',
            fontSize: '12px',
            padding: '4px 10px',
            borderRadius: '4px',
            border: trackerActive ? '1px solid #059669' : '1px solid #334155',
            cursor: 'pointer'
          }}>
          <Camera size={14} color={trackerActive ? "#34d399" : "#c084fc"} />
          {trackerActive ? "Tracking Active" : "🎥 OpenCV Head Track"}
        </button>
      </div>
    </div>
  );
}
