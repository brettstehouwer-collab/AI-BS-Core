import React, { useState, useEffect } from 'react';

const TheatricalProjector = () => {
    const [currentImage, setCurrentImage] = useState(null);

    useEffect(() => {
        // In a full implementation, this connects to a WebSocket that broadcasts
        // Base64 images directly from the ComfyUI generation pipeline.
        
        // Mock connection simulation
        console.log("Theatrical Projector active. Awaiting ComfyUI stream...");
    }, []);

    return (
        <div style={{
            height: '100vh',
            width: '100%',
            backgroundColor: 'black',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            overflow: 'hidden'
        }}>
            {currentImage ? (
                <img 
                    src={`data:image/png;base64,${currentImage}`} 
                    alt="Stage Projection" 
                    style={{
                        minWidth: '100%',
                        minHeight: '100%',
                        objectFit: 'cover',
                        opacity: 1,
                        transition: 'opacity 2s ease-in-out' // Smooth fade between scenes
                    }}
                />
            ) : (
                <div style={{ color: '#333', fontSize: '2rem', fontFamily: 'sans-serif' }}>
                    [ AWAITING STAGE PROJECTION STREAM ]
                </div>
            )}
        </div>
    );
};

export default TheatricalProjector;
