import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';

/**
 * VLCPreviewMonitor
 * Supports direct HTML5 MP4 playback, byte-range video streaming, live HLS streams,
 * and interactive Unreal Engine Python Script execution (headless or 3D visual editor).
 */
export default function VLCPreviewMonitor({ streamUrl, videoSrc, videoPath, title, backendUrl = '', onRenderVideo }) {
    const videoRef = useRef(null);
    const [status, setStatus] = useState("Ready");
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [playbackRate, setPlaybackRate] = useState(1.0);
    const [isLooping, setIsLooping] = useState(true);
    
    // Python script state for Unreal Engine mode
    const [scriptContent, setScriptContent] = useState('');
    const [copied, setCopied] = useState(false);
    const [loadingScript, setLoadingScript] = useState(false);
    
    // UE5 Execution States
    const [isExecutingUE5, setIsExecutingUE5] = useState(false);
    const [ue5Result, setUe5Result] = useState(null);

    const isPyScript = (videoPath && videoPath.endsWith('.py')) || (streamUrl && streamUrl.endsWith('.py'));
    const activeSrc = videoSrc || (videoPath ? `${backendUrl}/api/video/stream?path=${encodeURIComponent(videoPath)}` : streamUrl);

    // Fetch script content if it's a Python script
    useEffect(() => {
        if (isPyScript) {
            setLoadingScript(true);
            setUe5Result(null);
            const pathParam = videoPath || streamUrl;
            fetch(`${backendUrl}/api/video/script?path=${encodeURIComponent(pathParam)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        setScriptContent(data.content);
                    } else {
                        setScriptContent("# Script generated at: " + pathParam);
                    }
                })
                .catch(err => {
                    console.error("Failed to load script content:", err);
                    setScriptContent("# Local Unreal Engine Script Path: " + pathParam);
                })
                .finally(() => setLoadingScript(false));
            return;
        }

        if (!activeSrc) return;

        setStatus("Loading...");
        const isHls = typeof activeSrc === 'string' && activeSrc.includes('.m3u8');

        if (isHls && Hls.isSupported()) {
            const hls = new Hls({ maxLiveSyncPlaybackRate: 1.5 });
            hls.loadSource(activeSrc);
            hls.attachMedia(videoRef.current);

            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                setStatus("Playing");
                videoRef.current.play().then(() => setIsPlaying(true)).catch(e => console.warn("Autoplay blocked:", e));
            });

            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    setStatus("Stream error, retrying...");
                    hls.startLoad();
                }
            });

            return () => hls.destroy();
        } else if (videoRef.current) {
            // Direct MP4 / WebM stream
            videoRef.current.src = activeSrc;
            videoRef.current.load();
            videoRef.current.play().then(() => {
                setIsPlaying(true);
                setStatus("Playing");
            }).catch(e => {
                console.log("Ready to play (click to start)");
                setStatus("Ready");
            });
        }
    }, [activeSrc, isPyScript, videoPath, streamUrl, backendUrl]);

    const handleCopyScript = () => {
        if (!scriptContent) return;
        navigator.clipboard.writeText(scriptContent);
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
    };

    const handleDownloadScript = () => {
        const blob = new Blob([scriptContent], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = videoPath ? videoPath.split('\\').pop().split('/').pop() : 'unreal_scene_script.py';
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleRunInUnrealHeadless = async () => {
        const targetPath = videoPath || streamUrl;
        if (!targetPath) return;
        setIsExecutingUE5(true);
        setUe5Result({ status: 'running', message: '🚀 Building 3D Scene in Unreal Engine 5.8 (Spawning Actors & Materials)...' });
        
        try {
            const res = await fetch(`${backendUrl}/api/video/unreal/execute_script`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script_path: targetPath })
            });
            const data = await res.json();
            if (data.status === 'success') {
                setUe5Result({
                    status: 'success',
                    message: data.message || '✅ Scene constructed and saved in Unreal Engine 5.8 level!'
                });
            } else {
                setUe5Result({
                    status: 'error',
                    message: data.message || '⚠️ Unreal Engine execution encountered issues.'
                });
            }
        } catch (e) {
            setUe5Result({ status: 'error', message: `❌ Failed to trigger Unreal Engine: ${e.message}` });
        } finally {
            setIsExecutingUE5(false);
        }
    };

    const handleLaunchUnrealEditor = async () => {
        const targetPath = videoPath || streamUrl;
        try {
            const res = await fetch(`${backendUrl}/api/video/unreal/launch_editor`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script_path: targetPath })
            });
            const data = await res.json();
            alert(data.message || "🎮 Unreal Engine 5.8 Editor Launching on your Desktop!");
        } catch (e) {
            alert(`Error launching Unreal Editor: ${e.message}`);
        }
    };

    const togglePlay = () => {
        if (!videoRef.current) return;
        if (isPlaying) {
            videoRef.current.pause();
            setIsPlaying(false);
        } else {
            videoRef.current.play().then(() => setIsPlaying(true)).catch(console.error);
        }
    };

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
            if (videoRef.current.duration && !isNaN(videoRef.current.duration)) {
                setDuration(videoRef.current.duration);
            }
        }
    };

    const handleSeek = (e) => {
        const time = parseFloat(e.target.value);
        if (videoRef.current) {
            videoRef.current.currentTime = time;
            setCurrentTime(time);
        }
    };

    const handleRateChange = (rate) => {
        setPlaybackRate(rate);
        if (videoRef.current) {
            videoRef.current.playbackRate = rate;
        }
    };

    const toggleFullscreen = () => {
        if (videoRef.current) {
            if (videoRef.current.requestFullscreen) {
                videoRef.current.requestFullscreen();
            }
        }
    };

    const formatTime = (secs) => {
        if (isNaN(secs) || secs === 0) return "00:00";
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    };

    // If Unreal Engine Script mode
    if (isPyScript) {
        return (
            <div style={{
                position: 'relative',
                width: '100%',
                backgroundColor: '#070b14',
                borderRadius: '10px',
                overflow: 'hidden',
                border: '1px solid #1e293b',
                boxShadow: '0 8px 24px rgba(0,0,0,0.7)',
                display: 'flex',
                flexDirection: 'column'
            }}>
                {/* Header */}
                <div style={{
                    background: '#0f172a',
                    padding: '10px 16px',
                    borderBottom: '1px solid #1e293b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '8px'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '1.2rem' }}>🎮</span>
                        <div>
                            <span style={{ fontWeight: 'bold', fontSize: '0.85rem', color: '#38bdf8' }}>
                                Unreal Engine 5.8 Scene Generator
                            </span>
                            <span style={{ fontSize: '0.7rem', background: '#4c1d95', color: '#c4b5fd', padding: '1px 6px', borderRadius: '4px', marginLeft: '8px' }}>
                                Python Level Script
                            </span>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        <button
                            onClick={handleCopyScript}
                            style={{
                                background: copied ? '#059669' : '#1e293b',
                                color: copied ? '#fff' : '#38bdf8',
                                border: '1px solid #334155',
                                borderRadius: '4px',
                                padding: '4px 10px',
                                fontSize: '0.75rem',
                                cursor: 'pointer',
                                fontWeight: 'bold'
                            }}
                        >
                            {copied ? '✅ Copied!' : '📋 Copy Python Code'}
                        </button>
                        <button
                            onClick={handleDownloadScript}
                            style={{
                                background: '#1e293b',
                                color: '#a78bfa',
                                border: '1px solid #334155',
                                borderRadius: '4px',
                                padding: '4px 10px',
                                fontSize: '0.75rem',
                                cursor: 'pointer'
                            }}
                        >
                            ⬇️ Download .py
                        </button>
                    </div>
                </div>

                {/* Primary Action Buttons Bar */}
                <div style={{
                    background: '#0a0f1d',
                    padding: '10px 16px',
                    borderBottom: '1px solid #1e293b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '10px'
                }}>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                        <button
                            onClick={handleRunInUnrealHeadless}
                            disabled={isExecutingUE5}
                            style={{
                                background: isExecutingUE5 ? '#4338ca' : '#2563eb',
                                color: '#fff',
                                border: 'none',
                                borderRadius: '6px',
                                padding: '8px 14px',
                                fontSize: '0.8rem',
                                fontWeight: 'bold',
                                cursor: isExecutingUE5 ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                boxShadow: '0 2px 8px rgba(37, 99, 235, 0.4)'
                            }}
                        >
                            {isExecutingUE5 ? '⏳ Building Scene in UE5.8...' : '🚀 Build Scene in Unreal Engine 5.8'}
                        </button>

                        <button
                            onClick={handleLaunchUnrealEditor}
                            style={{
                                background: '#059669',
                                color: '#fff',
                                border: 'none',
                                borderRadius: '6px',
                                padding: '8px 14px',
                                fontSize: '0.8rem',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                boxShadow: '0 2px 8px rgba(5, 150, 105, 0.4)'
                            }}
                        >
                            <span>🎮</span>
                            <span>Open 3D Unreal Editor</span>
                        </button>
                    </div>

                    <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace' }}>
                        Project: AI_BS_Hub.uproject
                    </div>
                </div>

                {/* Execution Status Toast if present */}
                {ue5Result && (
                    <div style={{
                        padding: '8px 16px',
                        background: ue5Result.status === 'success' ? '#064e3b' : ue5Result.status === 'error' ? '#7f1d1d' : '#1e3a8a',
                        color: ue5Result.status === 'success' ? '#6ee7b7' : ue5Result.status === 'error' ? '#fca5a5' : '#93c5fd',
                        borderBottom: '1px solid #1e293b',
                        fontSize: '0.8rem',
                        fontWeight: 'bold'
                    }}>
                        {ue5Result.message}
                    </div>
                )}

                {/* Code Window */}
                <div style={{
                    padding: '16px',
                    backgroundColor: '#030712',
                    maxHeight: '340px',
                    overflowY: 'auto',
                    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                    fontSize: '0.82rem',
                    lineHeight: '1.5',
                    color: '#e2e8f0'
                }}>
                    {loadingScript ? (
                        <div style={{ color: '#38bdf8', padding: '20px', textAlign: 'center' }}>
                            ⏳ Loading generated Unreal Engine 5 script...
                        </div>
                    ) : (
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                            {scriptContent}
                        </pre>
                    )}
                </div>

                {/* UE5 Quick Run Instructions */}
                <div style={{
                    background: '#0b1120',
                    padding: '10px 16px',
                    borderTop: '1px solid #1e293b',
                    fontSize: '0.75rem',
                    color: '#94a3b8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}>
                    <div>
                        <strong style={{ color: '#38bdf8' }}>💡 Direct Execution:</strong> Click <strong style={{ color: '#60a5fa' }}>"Build Scene in Unreal Engine 5.8"</strong> above to place all CineCameraActors, characters, meshes, and lighting directly into your persistent level!
                    </div>
                </div>
            </div>
        );
    }

    if (!activeSrc) {
        return (
            <div style={{ color: '#555', textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '3.5rem', marginBottom: '12px' }}>📺</div>
                <div style={{ fontSize: '1.1rem', color: '#888' }}>No Active Video Stream</div>
                <div style={{ fontSize: '0.8rem', color: '#555', marginTop: '6px' }}>Generate a scene or enter a video file path on the left to start.</div>
            </div>
        );
    }

    return (
        <div style={{
            position: 'relative',
            width: '100%',
            backgroundColor: '#070b14',
            borderRadius: '10px',
            overflow: 'hidden',
            border: '1px solid #1e293b',
            boxShadow: '0 8px 24px rgba(0,0,0,0.7)',
            display: 'flex',
            flexDirection: 'column'
        }}>
            {/* Header info badge */}
            <div style={{
                background: '#0f172a',
                padding: '8px 16px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1rem' }}>🎬</span>
                    <span style={{ fontWeight: 'bold', fontSize: '0.85rem', color: '#38bdf8' }}>
                        {title || "AI-BS Cinematic Video Preview"}
                    </span>
                    <span style={{ fontSize: '0.7rem', background: '#065f46', color: '#6ee7b7', padding: '1px 6px', borderRadius: '4px' }}>
                        Wan2.1 RTX 4090
                    </span>
                </div>
                {activeSrc && (
                    <a
                        href={activeSrc}
                        download="generated_scene.mp4"
                        style={{
                            background: '#1e293b',
                            color: '#38bdf8',
                            border: '1px solid #334155',
                            borderRadius: '4px',
                            padding: '3px 10px',
                            fontSize: '0.75rem',
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                        }}
                    >
                        ⬇️ Download MP4
                    </a>
                )}
            </div>

            {/* Main Video Viewport */}
            <div style={{ position: 'relative', backgroundColor: '#000', minHeight: '360px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <video
                    ref={videoRef}
                    onTimeUpdate={handleTimeUpdate}
                    onEnded={() => {
                        if (!isLooping) setIsPlaying(false);
                    }}
                    loop={isLooping}
                    playsInline
                    style={{
                        width: '100%',
                        maxHeight: '480px',
                        objectFit: 'contain',
                        display: 'block'
                    }}
                    onClick={togglePlay}
                />

                {/* Big Center Play Button Overlay when paused */}
                {!isPlaying && (
                    <button
                        onClick={togglePlay}
                        style={{
                            position: 'absolute',
                            width: '60px',
                            height: '60px',
                            borderRadius: '50%',
                            background: 'rgba(37, 99, 235, 0.85)',
                            color: '#fff',
                            border: 'none',
                            fontSize: '1.8rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            boxShadow: '0 0 20px rgba(56, 189, 248, 0.5)'
                        }}
                    >
                        ▶
                    </button>
                )}
            </div>

            {/* Custom Interactive Player Control Deck */}
            <div style={{
                background: '#0b1120',
                padding: '10px 16px',
                borderTop: '1px solid #1e293b',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
            }}>
                {/* Timeline Scrubber */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#94a3b8', minWidth: '40px' }}>
                        {formatTime(currentTime)}
                    </span>
                    <input
                        type="range"
                        min="0"
                        max={duration || 100}
                        step="0.01"
                        value={currentTime}
                        onChange={handleSeek}
                        style={{ flex: 1, accentColor: '#38bdf8', height: '6px', cursor: 'pointer' }}
                    />
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#94a3b8', minWidth: '40px' }}>
                        {formatTime(duration)}
                    </span>
                </div>

                {/* Bottom Control Bar */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                    {/* Left: Play/Pause, Loop */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                            onClick={togglePlay}
                            style={{
                                background: isPlaying ? '#ef4444' : '#2563eb',
                                color: '#fff',
                                border: 'none',
                                borderRadius: '4px',
                                padding: '4px 12px',
                                fontSize: '0.8rem',
                                fontWeight: 'bold',
                                cursor: 'pointer'
                            }}
                        >
                            {isPlaying ? '⏸ Pause' : '▶ Play'}
                        </button>

                        <button
                            onClick={() => setIsLooping(!isLooping)}
                            style={{
                                background: isLooping ? '#1e3a8a' : '#1e293b',
                                color: isLooping ? '#93c5fd' : '#94a3b8',
                                border: '1px solid #334155',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                fontSize: '0.75rem',
                                cursor: 'pointer'
                            }}
                        >
                            🔁 {isLooping ? 'Loop ON' : 'Loop OFF'}
                        </button>
                    </div>

                    {/* Center: Playback Speed */}
                    <div style={{ display: 'flex', gap: '2px', background: '#070b14', padding: '2px', borderRadius: '4px', border: '1px solid #1e293b' }}>
                        {[0.5, 1.0, 1.5, 2.0].map((rate) => (
                            <button
                                key={rate}
                                onClick={() => handleRateChange(rate)}
                                style={{
                                    background: playbackRate === rate ? '#2563eb' : 'transparent',
                                    color: playbackRate === rate ? '#fff' : '#94a3b8',
                                    border: 'none',
                                    borderRadius: '3px',
                                    padding: '2px 6px',
                                    fontSize: '0.7rem',
                                    cursor: 'pointer'
                                }}
                            >
                                {rate}x
                            </button>
                        ))}
                    </div>

                    {/* Right: Fullscreen */}
                    <button
                        onClick={toggleFullscreen}
                        style={{
                            background: '#1e293b',
                            color: '#cbd5e1',
                            border: '1px solid #334155',
                            borderRadius: '4px',
                            padding: '4px 10px',
                            fontSize: '0.75rem',
                            cursor: 'pointer'
                        }}
                    >
                        ⛶ Fullscreen
                    </button>
                </div>
            </div>
        </div>
    );
}
