import React, { useState } from 'react';
import './TheatricalStageSwitch.css'; // Assuming we might add specific styles

const TheatricalStageSwitch = () => {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

    const [isActive, setIsActive] = useState(false);
    const [statusMessage, setStatusMessage] = useState("System in Standard Swarm Mode (Monetization Active)");

    const toggleMode = async () => {
        const newState = !isActive;
        setIsActive(newState);
        
        try {
            const response = await fetch(`${backendUrl}/api/proxy/8001/theatrical/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ active: newState })
            });
            
            const data = await response.json();
            if (data.status === "success") {
                if (data.theatrical_mode_active) {
                    setStatusMessage("THEATRICAL WORLD MODE ACTIVE. Monetization Paused. GPU allocated to ComfyUI & Isolated Module.");
                } else {
                    setStatusMessage("System in Standard Swarm Mode (Monetization Active)");
                }
            } else {
                setStatusMessage("Error: Failed to toggle state in backend.");
                setIsActive(!newState); // Revert UI
            }
        } catch (error) {
            console.error("Failed to hit toggle endpoint:", error);
            setStatusMessage("Error: Network disconnected.");
            setIsActive(!newState); // Revert UI
        }
    };

    return (
        <div className={`stage-switch-container ${isActive ? 'active' : 'inactive'}`}>
            <h2>Theatrical World Engine</h2>
            <p className="status-message">{statusMessage}</p>
            
            <button 
                className={`giant-toggle-btn ${isActive ? 'btn-danger' : 'btn-primary'}`}
                onClick={toggleMode}
                style={{
                    padding: '2rem 4rem',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    boxShadow: isActive ? '0 0 30px rgba(255,0,0,0.6)' : '0 0 15px rgba(0,123,255,0.4)',
                    backgroundColor: isActive ? '#dc3545' : '#0d6efd',
                    color: 'white',
                    border: 'none'
                }}
            >
                {isActive ? "EXIT STAGE (Resume Monetization)" : "ENTER STAGE (Trigger Theatrical World)"}
            </button>
            
            {isActive && (
                <div className="active-modules-list" style={{ marginTop: '2rem', textAlign: 'left' }}>
                    <h3 style={{ color: '#ff4d4d' }}>Active Isolation Protocols:</h3>
                    <ul>
                        <li>VRAM Lock: Clore/Vast processes terminated.</li>
                        <li>ChromaDB Local Vector Search: Online.</li>
                        <li>ComfyUI Visual Streamer: Ready.</li>
                        <li>Teleprompter WebSocket: Listening.</li>
                    </ul>
                </div>
            )}
        </div>
    );
};

export default TheatricalStageSwitch;
