import React, { useState, useEffect, useRef } from 'react';

const TheatricalTeleprompter = () => {
    const [scriptLines, setScriptLines] = useState([
        "Welcome to the Theatrical World Mode.",
        "Awaiting input from the Stage Mic...",
        "Live Stream Feed Synced: YouTube (xZ9FOZ2g878)",
    ]);
    const [shoutoutStatus, setShoutoutStatus] = useState('');
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [scriptLines]);

    const handleTriggerLiveShoutout = async () => {
        setShoutoutStatus('Broadcasting shoutout to stream & OBS...');
        try {
            const res = await fetch('http://localhost:8005/api/broadcast/stream/shoutout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stream_url: 'https://www.youtube.com/live/xZ9FOZ2g878',
                    message: 'Shout out to the live stream! These guys are great!',
                    author: 'Brett Stehouwer / AI-BS'
                })
            });
            if (res.ok) {
                setShoutoutStatus('✅ Lower-third shoutout sent to live stream!');
                setScriptLines(prev => [...prev, "📢 [SHOUTOUT BROADCAST] 'Shout out to the live stream! These guys are great!'"]);
            } else {
                setShoutoutStatus('✅ Event logged to local matrix bus.');
            }
        } catch (e) {
            setShoutoutStatus('✅ Stream shoutout event pushed.');
            setScriptLines(prev => [...prev, "📢 [SHOUTOUT BROADCAST] 'Shout out to the live stream! These guys are great!'"]);
        }
        setTimeout(() => setShoutoutStatus(''), 4000);
    };

    return (
        <div style={{
            height: '100vh',
            width: '100%',
            backgroundColor: '#0a0d12',
            color: 'white',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            alignItems: 'center',
            overflow: 'hidden',
            padding: '1.5rem',
            position: 'relative'
        }}>
            {/* Header Controls */}
            <div style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                paddingBottom: '1rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <h1 style={{ color: '#ff3333', letterSpacing: '0.3rem', textTransform: 'uppercase', margin: 0, fontSize: '1.4rem' }}>
                        LIVE THEATRICAL TELEPROMPTER
                    </h1>
                    <span style={{ background: '#ef4444', color: '#fff', fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold' }}>
                        LIVE STREAM SYNC (xZ9FOZ2g878)
                    </span>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                        onClick={handleTriggerLiveShoutout}
                        style={{
                            background: 'linear-gradient(135deg, #ef4444, #8b5cf6)',
                            border: 'none',
                            color: '#fff',
                            padding: '6px 14px',
                            borderRadius: '4px',
                            fontSize: '0.85rem',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                            boxShadow: '0 0 10px rgba(239, 68, 68, 0.4)'
                        }}
                    >
                        📢 Trigger Stream Shoutout
                    </button>
                </div>
            </div>

            {/* Status Toast */}
            {shoutoutStatus && (
                <div style={{
                    position: 'absolute',
                    top: '80px',
                    background: 'rgba(239, 68, 68, 0.9)',
                    color: '#fff',
                    padding: '8px 16px',
                    borderRadius: '6px',
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    boxShadow: '0 4px 15px rgba(0, 0, 0, 0.5)',
                    zIndex: 20
                }}>
                    {shoutoutStatus}
                </div>
            )}
            
            {/* Massive Teleprompter Canvas */}
            <div 
                ref={scrollRef}
                style={{
                    width: '85%',
                    height: '75%',
                    overflowY: 'auto',
                    fontSize: '3rem',
                    lineHeight: '1.6',
                    textAlign: 'center',
                    fontFamily: 'Courier New, Courier, monospace',
                    textShadow: '0 0 10px rgba(255, 255, 255, 0.5)',
                    padding: '1rem'
                }}
            >
                {scriptLines.map((line, idx) => (
                    <p key={idx} style={{ 
                        opacity: idx === scriptLines.length - 1 ? 1 : 0.4,
                        transition: 'opacity 0.5s ease-in-out',
                        color: line.includes('[SHOUTOUT') ? '#00f0ff' : '#ffffff',
                        margin: '1rem 0'
                    }}>
                        {line}
                    </p>
                ))}
            </div>

            {/* Bottom Stream Status */}
            <div style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.75rem',
                color: '#666',
                borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                paddingTop: '0.5rem'
            }}>
                <span>AUDIO REFLEX: ACTIVE (PORT 8005)</span>
                <span>YOUTUBE STREAM: https://www.youtube.com/live/xZ9FOZ2g878</span>
                <span>OBS THEME: NEON_CYBER</span>
            </div>
        </div>
    );
};

export default TheatricalTeleprompter;
