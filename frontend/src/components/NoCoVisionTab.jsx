import React from 'react';
import TheatricalStageSwitch from './TheatricalStageSwitch.jsx';
import TheatricalMicClient from './TheatricalMicClient.jsx';
import { useAppStore } from './useAppStore.js';

const NoCoVisionTab = () => {
  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ border: '1px solid #444', padding: '20px', borderRadius: '8px', background: '#161b22' }}>
        <h3 style={{ marginTop: 0 }}>Core Control</h3>
        <TheatricalStageSwitch />
      </div>

      <div style={{ border: '1px solid #444', padding: '20px', borderRadius: '8px', background: '#161b22' }}>
        <h3 style={{ marginTop: 0 }}>Audio Ingestion</h3>
        <TheatricalMicClient />
      </div>

      <div style={{ border: '1px solid #444', padding: '20px', borderRadius: '8px', background: '#161b22' }}>
        <h3 style={{ marginTop: 0 }}>Stage Displays</h3>
        <p>To view the stage displays, open these routes in a new window or on your secondary stage monitors:</p>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li>
            <button 
                onClick={() => window.open('/nocovision/teleprompter', '_blank')}
                style={{ padding: '10px 20px', background: '#0d6efd', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '10px' }}>
              Launch Fullscreen Teleprompter
            </button>
          </li>
          <li>
            <button 
                onClick={() => window.open('/nocovision/projector', '_blank')}
                style={{ padding: '10px 20px', background: '#6f42c1', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Launch Fullscreen Visual Projector
            </button>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default NoCoVisionTab;
