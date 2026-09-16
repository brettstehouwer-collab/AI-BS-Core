import React, { useState, useRef } from 'react';

const TheatricalMicClient = ({ backendUrl: propBackendUrl }) => {
    const backendUrl = propBackendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
    const wsBase = backendUrl.replace(/^http/, 'ws');
    
    const [isRecording, setIsRecording] = useState(false);
    const [status, setStatus] = useState("Microphone disconnected.");
    const mediaRecorderRef = useRef(null);
    const wsRef = useRef(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setStatus("Microphone connected. Connecting to Stage...");
            
            wsRef.current = new WebSocket(`${wsBase}/api/proxy/8001/theatrical/audio_stream`);
            
            wsRef.current.onopen = () => {
                setStatus("Live on Stage! Streaming audio to Theatrical Module...");
                setIsRecording(true);
                
                mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                
                mediaRecorderRef.current.ondataavailable = (event) => {
                    if (event.data.size > 0 && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.send(event.data);
                    }
                };
                
                // Send chunks every 1 second for near real-time processing
                mediaRecorderRef.current.start(1000);
            };

            wsRef.current.onclose = () => {
                setStatus("Disconnected from Stage.");
                setIsRecording(false);
            };
            
            wsRef.current.onerror = (err) => {
                console.error("WebSocket Error:", err);
                setStatus("Error: WebSocket disconnected.");
            };

        } catch (err) {
            console.error("Mic access denied:", err);
            setStatus("Error: Microphone access denied or not found.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
        if (wsRef.current) {
            wsRef.current.close();
        }
        setIsRecording(false);
        setStatus("Microphone disconnected.");
    };

    return (
        <div style={{ padding: '2rem', border: '2px solid #555', borderRadius: '8px', backgroundColor: '#111', color: '#eee' }}>
            <h3>Stage Microphone Client</h3>
            <p>Status: <span style={{ color: isRecording ? '#00ff00' : '#ff3333' }}>{status}</span></p>
            
            {!isRecording ? (
                <button 
                    onClick={startRecording}
                    style={{ padding: '1rem 2rem', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    Connect & Go Live
                </button>
            ) : (
                <button 
                    onClick={stopRecording}
                    style={{ padding: '1rem 2rem', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    Cut Mic
                </button>
            )}
        </div>
    );
};

export default TheatricalMicClient;
