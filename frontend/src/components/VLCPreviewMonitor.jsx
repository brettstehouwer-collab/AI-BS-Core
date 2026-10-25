import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';

/**
 * VLCPreviewMonitor
 * Comprehensive VLC-styled Media Player for AI-BS.
 * Supports direct HTML5 MP4 playback, byte-range video streaming, live HLS streams,
 * local video file opening/drag-and-drop, playlist switching, snapshot capture,
 * and opening streams in external native VLC Media Player (.m3u / vlc://).
 */
export default function VLCPreviewMonitor({
    streamUrl,
    videoSrc,
    videoPath,
    title,
    playlist = [],
    backendUrl = '',
    onRenderVideo
}) {
    const videoRef = useRef(null);
    const fileInputRef = useRef(null);
    const containerRef = useRef(null);

    // Active playlist selection
    const [activeVideoIndex, setActiveVideoIndex] = useState(0);
    const [localUploadedVideos, setLocalUploadedVideos] = useState([]);
    
    // Playback state
    const [status, setStatus] = useState("Ready");
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1.0);
    const [isMuted, setIsMuted] = useState(false);
    const [playbackRate, setPlaybackRate] = useState(1.0);
    const [isLooping, setIsLooping] = useState(true);
    const [aspectRatio, setAspectRatio] = useState('contain'); // 'contain', 'cover', '16/9', '4/3'
    const [videoError, setVideoError] = useState(null);
    const [vlcLaunchToast, setVlcLaunchToast] = useState(null);

    // Python script state for Unreal Engine mode (backward compatibility)
    const [scriptContent, setScriptContent] = useState('');
    const [copied, setCopied] = useState(false);
    const [loadingScript, setLoadingScript] = useState(false);
    const [isExecutingUE5, setIsExecutingUE5] = useState(false);
    const [ue5Result, setUe5Result] = useState(null);

    // Resolve unified playlist
    const fullPlaylist = React.useMemo(() => {
        const list = [...playlist, ...localUploadedVideos];
        if (list.length === 0) {
            if (videoSrc || videoPath || streamUrl) {
                list.push({
                    id: 'default',
                    title: title || "AI-BS Media Stream",
                    src: videoSrc || (videoPath ? `${backendUrl}/api/video/stream?path=${encodeURIComponent(videoPath)}` : streamUrl),
                    badge: videoPath?.endsWith('.py') ? 'UE5 Script' : 'Active Stream'
                });
            }
        }
        return list;
    }, [playlist, localUploadedVideos, videoSrc, videoPath, streamUrl, title, backendUrl]);

    const activeItem = fullPlaylist[activeVideoIndex] || fullPlaylist[0];
    const isPyScript = (activeItem?.src && activeItem.src.endsWith('.py')) || (videoPath && videoPath.endsWith('.py'));
    const activeSrc = activeItem?.src;

    // Load and attach video source
    useEffect(() => {
        setVideoError(null);
        if (isPyScript) {
            setLoadingScript(true);
            setUe5Result(null);
            const pathParam = videoPath || streamUrl || activeSrc;
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

        if (!activeSrc) {
            setStatus("No Media");
            return;
        }

        setStatus("Buffering...");
        const isHls = typeof activeSrc === 'string' && activeSrc.includes('.m3u8');

        if (isHls && Hls.isSupported()) {
            const hls = new Hls({ maxLiveSyncPlaybackRate: 1.5 });
            hls.loadSource(activeSrc);
            if (videoRef.current) {
                hls.attachMedia(videoRef.current);
            }

            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                setStatus("Playing");
                if (videoRef.current) {
                    videoRef.current.play().then(() => setIsPlaying(true)).catch(() => setStatus("Ready"));
                }
            });

            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    setStatus("Stream error, retrying...");
                    hls.startLoad();
                }
            });

            return () => hls.destroy();
        } else if (videoRef.current) {
            videoRef.current.src = activeSrc;
            videoRef.current.load();
            videoRef.current.playbackRate = playbackRate;
            videoRef.current.volume = isMuted ? 0 : volume;
            
            // Try auto-play
            videoRef.current.play().then(() => {
                setIsPlaying(true);
                setStatus("Playing");
            }).catch(e => {
                setStatus("Ready (Click Play)");
            });
        }
    }, [activeSrc, isPyScript, videoPath, streamUrl, backendUrl]);

    // Handle local file upload
    const handleFileUpload = (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        const newItems = files.map((file, idx) => ({
            id: `local-${Date.now()}-${idx}`,
            title: `📁 ${file.name}`,
            src: URL.createObjectURL(file),
            badge: `${(file.size / (1024 * 1024)).toFixed(1)} MB`,
            isLocal: true
        }));

        setLocalUploadedVideos(prev => [...prev, ...newItems]);
        setActiveVideoIndex(fullPlaylist.length); // Switch immediately to the newly uploaded item
    };

    // Playback Controls
    const togglePlay = () => {
        if (!videoRef.current) return;
        if (isPlaying) {
            videoRef.current.pause();
            setIsPlaying(false);
            setStatus("Paused");
        } else {
            videoRef.current.play().then(() => {
                setIsPlaying(true);
                setStatus("Playing");
            }).catch(err => {
                console.error("Playback error:", err);
                setVideoError("Playback failed to initiate. Tap or click directly on the screen.");
            });
        }
    };

    const handleSkip = (seconds) => {
        if (!videoRef.current) return;
        const newTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + seconds));
        videoRef.current.currentTime = newTime;
        setCurrentTime(newTime);
    };

    const handleSeek = (e) => {
        const time = parseFloat(e.target.value);
        if (videoRef.current) {
            videoRef.current.currentTime = time;
            setCurrentTime(time);
        }
    };

    const handleVolumeChange = (e) => {
        const val = parseFloat(e.target.value);
        setVolume(val);
        setIsMuted(val === 0);
        if (videoRef.current) {
            videoRef.current.volume = val;
            videoRef.current.muted = (val === 0);
        }
    };

    const toggleMute = () => {
        if (!videoRef.current) return;
        const nextMuted = !isMuted;
        setIsMuted(nextMuted);
        videoRef.current.muted = nextMuted;
    };

    const handleRateChange = (rate) => {
        setPlaybackRate(rate);
        if (videoRef.current) {
            videoRef.current.playbackRate = rate;
        }
    };

    const toggleFullscreen = () => {
        if (containerRef.current) {
            if (!document.fullscreenElement) {
                containerRef.current.requestFullscreen().catch(() => {});
            } else {
                document.exitFullscreen().catch(() => {});
            }
        }
    };

    const captureSnapshot = () => {
        if (!videoRef.current) return;
        const video = videoRef.current;
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 1280;
        canvas.height = video.videoHeight || 720;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const dataUrl = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.download = `VLC_Snapshot_${formatTime(currentTime).replace(':', '_')}.png`;
        link.href = dataUrl;
        link.click();
    };

    const launchInNativeVLC = () => {
        if (!activeSrc) return;
        // Construct VLC playlist (.m3u) file for immediate desktop/mobile opening
        const resolvedUrl = activeSrc.startsWith('http') ? activeSrc : window.location.origin + activeSrc;
        const m3uContent = `#EXTM3U\n#EXTINF:-1,${activeItem?.title || "AI-BS Media Stream"}\n${resolvedUrl}\n`;
        const blob = new Blob([m3uContent], { type: 'audio/x-mpegurl' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${(activeItem?.title || "stream").replace(/[^a-zA-Z0-9_-]/g, '_')}.m3u`;
        a.click();
        URL.revokeObjectURL(url);

        // Also attempt direct vlc:// custom protocol link
        const vlcProtocolUrl = `vlc://${resolvedUrl}`;
        window.open(vlcProtocolUrl, '_blank');

        setVlcLaunchToast("🔶 VLC Playlist downloaded & vlc:// triggered! Opening in VLC Media Player...");
        setTimeout(() => setVlcLaunchToast(null), 4000);
    };

    const formatTime = (secs) => {
        if (isNaN(secs) || secs === 0) return "00:00";
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    };

    return (
        <div
            ref={containerRef}
            style={{
                position: 'relative',
                width: '100%',
                backgroundColor: '#0a0d14',
                borderRadius: '12px',
                overflow: 'hidden',
                border: '1px solid #f97316', // VLC Orange accent
                boxShadow: '0 8px 32px rgba(249, 115, 22, 0.15)',
                display: 'flex',
                flexDirection: 'column',
                fontFamily: 'system-ui, -apple-system, sans-serif'
            }}
        >
            {/* Hidden File Input for Opening Local Media */}
            <input
                ref={fileInputRef}
                type="file"
                accept="video/*,audio/*"
                multiple
                style={{ display: 'none' }}
                onChange={handleFileUpload}
            />

            {/* VLC Title Bar & Media Switcher */}
            <div style={{
                background: 'linear-gradient(90deg, #1c1917 0%, #0c0a09 100%)',
                padding: '10px 16px',
                borderBottom: '1px solid rgba(249, 115, 22, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '10px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '1.4rem' }}>🔶</span>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: 800, fontSize: '0.9rem', color: '#f97316', letterSpacing: '0.5px' }}>
                                VLC Media Player • AI-BS Studio
                            </span>
                            <span style={{
                                fontSize: '0.68rem',
                                background: 'rgba(249, 115, 22, 0.2)',
                                color: '#fdba74',
                                border: '1px solid #f97316',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                fontWeight: 700
                            }}>
                                {activeItem?.badge || "PRO"}
                            </span>
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#a8a29e' }}>
                            {activeItem?.title || title || "AI-BS Media Viewer"}
                        </div>
                    </div>
                </div>

                {/* Top Action Buttons: Open Local File & Open in Native VLC */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                            background: 'rgba(255, 255, 255, 0.08)',
                            color: '#ffffff',
                            border: '1px solid rgba(255, 255, 255, 0.2)',
                            borderRadius: '6px',
                            padding: '5px 12px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px'
                        }}
                    >
                        📁 Open / Upload
                    </button>

                    <button
                        onClick={launchInNativeVLC}
                        style={{
                            background: 'linear-gradient(135deg, #f97316, #ea580c)',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '5px 12px',
                            fontSize: '0.75rem',
                            fontWeight: 800,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '5px',
                            boxShadow: '0 2px 8px rgba(249, 115, 22, 0.35)'
                        }}
                    >
                        🔶 In VLC App (.m3u)
                    </button>
                </div>
            </div>

            {/* Playlist Channel Selector Tabs (if multiple videos exist) */}
            {fullPlaylist.length > 1 && (
                <div style={{
                    display: 'flex',
                    gap: '6px',
                    background: '#0c0a09',
                    padding: '8px 14px',
                    borderBottom: '1px solid #292524',
                    overflowX: 'auto'
                }}>
                    <span style={{ fontSize: '0.7rem', color: '#78716c', fontWeight: 700, textTransform: 'uppercase', alignSelf: 'center', marginRight: '4px' }}>
                        Channels:
                    </span>
                    {fullPlaylist.map((item, idx) => {
                        const isCurrent = activeVideoIndex === idx;
                        return (
                            <button
                                key={item.id || idx}
                                onClick={() => setActiveVideoIndex(idx)}
                                style={{
                                    background: isCurrent ? 'rgba(249, 115, 22, 0.25)' : 'rgba(255, 255, 255, 0.04)',
                                    border: isCurrent ? '1px solid #f97316' : '1px solid rgba(255, 255, 255, 0.08)',
                                    color: isCurrent ? '#f97316' : '#a8a29e',
                                    padding: '4px 10px',
                                    borderRadius: '6px',
                                    fontSize: '0.72rem',
                                    fontWeight: isCurrent ? 700 : 500,
                                    cursor: 'pointer',
                                    whiteSpace: 'nowrap'
                                }}
                            >
                                {item.title}
                            </button>
                        );
                    })}
                </div>
            )}

            {/* Launch Notification Toast */}
            {vlcLaunchToast && (
                <div style={{
                    background: '#ea580c',
                    color: '#ffffff',
                    padding: '8px 16px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    textAlign: 'center'
                }}>
                    {vlcLaunchToast}
                </div>
            )}

            {/* Video Viewport */}
            <div style={{
                position: 'relative',
                backgroundColor: '#000000',
                minHeight: '360px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden'
            }}>
                <video
                    ref={videoRef}
                    onTimeUpdate={() => {
                        if (videoRef.current) {
                            setCurrentTime(videoRef.current.currentTime);
                            if (videoRef.current.duration && !isNaN(videoRef.current.duration)) {
                                setDuration(videoRef.current.duration);
                            }
                        }
                    }}
                    onEnded={() => {
                        if (!isLooping) {
                            setIsPlaying(false);
                            setStatus("Finished");
                        }
                    }}
                    onError={() => {
                        setVideoError("Video stream failed to decode or file not found.");
                        setStatus("Error");
                    }}
                    loop={isLooping}
                    playsInline
                    style={{
                        width: '100%',
                        maxHeight: 'clamp(220px, 45vh, 520px)',
                        objectFit: aspectRatio,
                        display: 'block'
                    }}
                    onClick={togglePlay}
                />

                {/* Big Center Play Button Overlay when paused */}
                {!isPlaying && !videoError && (
                    <button
                        onClick={togglePlay}
                        aria-label="Play video"
                        style={{
                            position: 'absolute',
                            width: '68px',
                            height: '68px',
                            borderRadius: '50%',
                            background: 'rgba(249, 115, 22, 0.9)',
                            color: '#ffffff',
                            border: 'none',
                            fontSize: '2rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            boxShadow: '0 0 30px rgba(249, 115, 22, 0.6)',
                            transition: 'transform 0.15s ease'
                        }}
                    >
                        ▶
                    </button>
                )}

                {/* Error Banner Overlay */}
                {videoError && (
                    <div style={{
                        position: 'absolute',
                        background: 'rgba(127, 29, 29, 0.92)',
                        border: '1px solid #ef4444',
                        color: '#fecaca',
                        padding: '16px 24px',
                        borderRadius: '8px',
                        textAlign: 'center',
                        maxWidth: '85%'
                    }}>
                        <div style={{ fontSize: '1.4rem', marginBottom: '6px' }}>⚠️</div>
                        <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>{videoError}</div>
                        <div style={{ fontSize: '0.75rem', marginTop: '6px', color: '#fca5a5' }}>
                            You can click "Open in VLC App (.m3u)" above to play it directly in VLC Player.
                        </div>
                    </div>
                )}
            </div>

            {/* VLC Control Deck */}
            <div style={{
                background: '#141210',
                padding: '12px 18px',
                borderTop: '1px solid rgba(249, 115, 22, 0.25)',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
            }}>
                {/* Timeline Progress Bar */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '0.78rem', fontFamily: 'monospace', color: '#f97316', fontWeight: 700, minWidth: '45px' }}>
                        {formatTime(currentTime)}
                    </span>
                    <input
                        type="range"
                        min="0"
                        max={duration || 100}
                        step="0.01"
                        value={currentTime}
                        onChange={handleSeek}
                        style={{
                            flex: 1,
                            accentColor: '#f97316',
                            height: '6px',
                            cursor: 'pointer'
                        }}
                    />
                    <span style={{ fontSize: '0.78rem', fontFamily: 'monospace', color: '#a8a29e', minWidth: '45px', textAlign: 'right' }}>
                        {formatTime(duration)}
                    </span>
                </div>

                {/* Primary Transport Buttons */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '10px'
                }}>
                    {/* Left: Transport Group */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', flex: '1 1 auto' }}>
                        <button
                            onClick={togglePlay}
                            style={{
                                background: isPlaying ? '#dc2626' : '#f97316',
                                color: '#ffffff',
                                border: 'none',
                                borderRadius: '6px',
                                padding: '6px 14px',
                                fontSize: '0.82rem',
                                fontWeight: 800,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                            }}
                        >
                            {isPlaying ? '⏸ Pause' : '▶ Play'}
                        </button>

                        <button
                            onClick={() => handleSkip(-5)}
                            style={{
                                background: '#292524',
                                color: '#d6d3d1',
                                border: '1px solid #44403c',
                                borderRadius: '6px',
                                padding: '6px 10px',
                                fontSize: '0.75rem',
                                cursor: 'pointer'
                            }}
                        >
                            ⏪ -5s
                        </button>

                        <button
                            onClick={() => handleSkip(5)}
                            style={{
                                background: '#292524',
                                color: '#d6d3d1',
                                border: '1px solid #44403c',
                                borderRadius: '6px',
                                padding: '6px 10px',
                                fontSize: '0.75rem',
                                cursor: 'pointer'
                            }}
                        >
                            ⏩ +5s
                        </button>

                        <button
                            onClick={() => setIsLooping(!isLooping)}
                            style={{
                                background: isLooping ? 'rgba(249, 115, 22, 0.2)' : '#292524',
                                color: isLooping ? '#f97316' : '#78716c',
                                border: isLooping ? '1px solid #f97316' : '1px solid #44403c',
                                borderRadius: '6px',
                                padding: '6px 10px',
                                fontSize: '0.75rem',
                                fontWeight: 700,
                                cursor: 'pointer'
                            }}
                        >
                            🔁 {isLooping ? 'Loop ON' : 'Loop OFF'}
                        </button>

                        {/* Volume Slider */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
                            <button
                                onClick={toggleMute}
                                style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: isMuted ? '#ef4444' : '#f97316',
                                    cursor: 'pointer',
                                    fontSize: '1rem',
                                    padding: 0
                                }}
                            >
                                {isMuted ? '🔇' : volume > 0.5 ? '🔊' : '🔉'}
                            </button>
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.05"
                                value={isMuted ? 0 : volume}
                                onChange={handleVolumeChange}
                                style={{ width: '65px', accentColor: '#f97316', height: '4px', cursor: 'pointer' }}
                            />
                        </div>
                    </div>

                    {/* Right: Playback Speed, Snapshot, Fullscreen */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        {/* Playback Speed Selector */}
                        <div style={{ display: 'flex', background: '#0c0a09', borderRadius: '6px', padding: '2px', border: '1px solid #292524' }}>
                            {[0.5, 1.0, 1.5, 2.0].map((rate) => (
                                <button
                                    key={rate}
                                    onClick={() => handleRateChange(rate)}
                                    style={{
                                        background: playbackRate === rate ? '#f97316' : 'transparent',
                                        color: playbackRate === rate ? '#ffffff' : '#a8a29e',
                                        border: 'none',
                                        borderRadius: '4px',
                                        padding: '3px 8px',
                                        fontSize: '0.7rem',
                                        fontWeight: 700,
                                        cursor: 'pointer'
                                    }}
                                >
                                    {rate}x
                                </button>
                            ))}
                        </div>

                        {/* Aspect Ratio Switcher */}
                        <button
                            onClick={() => {
                                const modes = ['contain', 'cover', 'fill'];
                                const next = modes[(modes.indexOf(aspectRatio) + 1) % modes.length];
                                setAspectRatio(next);
                            }}
                            style={{
                                background: '#292524',
                                color: '#d6d3d1',
                                border: '1px solid #44403c',
                                borderRadius: '6px',
                                padding: '5px 10px',
                                fontSize: '0.72rem',
                                cursor: 'pointer',
                                fontWeight: 600
                            }}
                        >
                            📐 {aspectRatio.toUpperCase()}
                        </button>

                        {/* Snapshot Frame Capture */}
                        <button
                            onClick={captureSnapshot}
                            title="Capture Snapshot Image"
                            style={{
                                background: '#292524',
                                color: '#d6d3d1',
                                border: '1px solid #44403c',
                                borderRadius: '6px',
                                padding: '5px 10px',
                                fontSize: '0.72rem',
                                cursor: 'pointer',
                                fontWeight: 600
                            }}
                        >
                            📸 Snapshot
                        </button>

                        {/* Fullscreen */}
                        <button
                            onClick={toggleFullscreen}
                            style={{
                                background: '#292524',
                                color: '#d6d3d1',
                                border: '1px solid #44403c',
                                borderRadius: '6px',
                                padding: '5px 10px',
                                fontSize: '0.72rem',
                                cursor: 'pointer',
                                fontWeight: 700
                            }}
                        >
                            ⛶ Fullscreen
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
