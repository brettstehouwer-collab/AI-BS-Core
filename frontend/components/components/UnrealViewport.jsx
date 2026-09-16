import React, { useEffect, useRef, useState } from 'react';

export default function UnrealViewport({ signalingUrl = 'ws://127.0.0.1:8888' }) {
    const videoRef = useRef(null);
    const [status, setStatus] = useState('Disconnected');

    useEffect(() => {
        let ws;
        let pc;

        const connect = () => {
            setStatus('Connecting to Signaling Server...');
            ws = new WebSocket(signalingUrl);

            ws.onopen = () => {
                setStatus('Signaling Connected. Waiting for Unreal Streamer...');
                ws.send(JSON.stringify({ type: 'player' }));
            };

            ws.onmessage = async (event) => {
                const msg = JSON.parse(event.data);

                if (msg.type === 'offer') {
                    setStatus('Received Offer from Unreal. Negotiating...');
                    pc = new RTCPeerConnection({
                        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
                    });

                    pc.ontrack = (e) => {
                        if (videoRef.current) {
                            if (e.streams && e.streams[0]) {
                                videoRef.current.srcObject = e.streams[0];
                            } else {
                                videoRef.current.srcObject = new MediaStream([e.track]);
                            }
                            setStatus('Streaming 3D Environment');
                        }
                    };

                    pc.onicecandidate = (e) => {
                        if (e.candidate) {
                            ws.send(JSON.stringify({
                                type: 'iceCandidate',
                                candidate: e.candidate
                            }));
                        }
                    };

                    await pc.setRemoteDescription(new RTCSessionDescription(msg));
                    const answer = await pc.createAnswer();
                    await pc.setLocalDescription(answer);

                    ws.send(JSON.stringify({
                        type: 'answer',
                        sdp: answer.sdp
                    }));
                } else if (msg.type === 'iceCandidate' && pc) {
                    try {
                        await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
                    } catch (e) {
                        console.error('Error adding ICE candidate', e);
                    }
                } else if (msg.type === 'streamerDisconnected') {
                    setStatus('Unreal Engine Disconnected.');
                    if (videoRef.current) {
                        videoRef.current.srcObject = null;
                    }
                }
            };

            ws.onclose = () => {
                setStatus('Signaling Server Disconnected. Retrying in 5s...');
                setTimeout(connect, 5000);
            };
        };

        connect();

        return () => {
            if (pc) pc.close();
            if (ws) ws.close();
        };
    }, [signalingUrl]);

    return (
        <div className="w-full h-full flex flex-col bg-slate-900 rounded-lg overflow-hidden border border-slate-700 relative shadow-2xl">
            {/* Status Overlay */}
            {status !== 'Streaming 3D Environment' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10 backdrop-blur-sm">
                    <div className="text-center p-8 bg-slate-800/90 rounded-2xl border border-blue-500/30 shadow-[0_0_30px_rgba(59,130,246,0.2)]">
                        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
                        <p className="text-blue-400 font-medium tracking-wide animate-pulse text-lg">{status}</p>
                        <p className="text-slate-400 text-sm mt-3 max-w-xs mx-auto">
                            Ensure Unreal Engine is running and Pixel Streaming is enabled on port 8888.
                        </p>
                    </div>
                </div>
            )}
            
            {/* Unreal Viewport Video */}
            <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted 
                className="w-full h-full object-cover transition-opacity duration-1000"
                style={{ opacity: status === 'Streaming 3D Environment' ? 1 : 0 }}
            />
            
            {/* 3D Interface Controls Overlay */}
            {status === 'Streaming 3D Environment' && (
                <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 flex items-center space-x-3 bg-black/60 backdrop-blur-md py-2 px-5 rounded-full border border-white/10 shadow-xl transition-all hover:bg-black/80 hover:scale-105">
                    <div className="w-2.5 h-2.5 bg-green-500 rounded-full shadow-[0_0_10px_#22c55e] animate-pulse"></div>
                    <span className="text-white/90 text-sm font-semibold tracking-wide uppercase">Live 3D Viewport</span>
                </div>
            )}
        </div>
    );
}
