import React, { useState } from 'react';
import { theme } from '../styles/theme';
import { AIBSAutogradEngine, AIBSReasoningEngine } from './DesignSoftwareUsed';

const DesignParameters = () => {
  const [guestCapacityTarget, setGuestCapacityTarget] = useState(350);
  const [rt60ReverbMs, setRt60ReverbMs] = useState(420);
  const [lightingFrequencyHz, setLightingFrequencyHz] = useState(60);
  const [loadMarginFactor, setLoadMarginFactor] = useState(1.45);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const handleRunOptimization = () => {
    setIsOptimizing(true);
    setTimeout(() => {
      setIsOptimizing(false);
    }, 1200);
  };

  return (
    <div style={{ color: theme.colors.textPrimary }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: theme.colors.accent }}>🎛️ Parametric Design & Computational Optimization Controls</h3>
        <button
          onClick={handleRunOptimization}
          disabled={isOptimizing}
          style={{
            background: isOptimizing ? 'rgba(122,40,138,0.3)' : `linear-gradient(135deg, ${theme.colors.secondary}, ${theme.colors.accent})`,
            border: 'none',
            color: '#FFF',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: isOptimizing ? 'wait' : 'pointer',
            fontWeight: 'bold',
            fontSize: '0.85rem',
            boxShadow: `0 0 15px ${theme.colors.glowCyan}`
          }}
        >
          {isOptimizing ? '⚙️ Re-calculating Tensors...' : '🚀 Execute AI Structural Autograd'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '20px' }}>
        <div style={{
          background: 'rgba(13, 17, 23, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '12px',
          padding: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: theme.colors.textMuted }}>Guest Capacity Target:</span>
            <span style={{ fontSize: '0.9rem', color: theme.colors.accent, fontWeight: 'bold' }}>{guestCapacityTarget} Guests</span>
          </div>
          <input
            type="range"
            min="100"
            max="600"
            step="10"
            value={guestCapacityTarget}
            onChange={(e) => setGuestCapacityTarget(Number(e.target.value))}
            style={{ width: '100%', accentColor: theme.colors.accent, cursor: 'pointer' }}
          />
        </div>

        <div style={{
          background: 'rgba(13, 17, 23, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '12px',
          padding: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: theme.colors.textMuted }}>Acoustic RT60 Target:</span>
            <span style={{ fontSize: '0.9rem', color: '#D8B4FE', fontWeight: 'bold' }}>{rt60ReverbMs} ms</span>
          </div>
          <input
            type="range"
            min="200"
            max="800"
            step="10"
            value={rt60ReverbMs}
            onChange={(e) => setRt60ReverbMs(Number(e.target.value))}
            style={{ width: '100%', accentColor: theme.colors.secondary, cursor: 'pointer' }}
          />
        </div>

        <div style={{
          background: 'rgba(13, 17, 23, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '12px',
          padding: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: theme.colors.textMuted }}>Lighting DMX Refresh:</span>
            <span style={{ fontSize: '0.9rem', color: '#A7F3D0', fontWeight: 'bold' }}>{lightingFrequencyHz} Hz</span>
          </div>
          <input
            type="range"
            min="30"
            max="120"
            step="5"
            value={lightingFrequencyHz}
            onChange={(e) => setLightingFrequencyHz(Number(e.target.value))}
            style={{ width: '100%', accentColor: '#10B981', cursor: 'pointer' }}
          />
        </div>

        <div style={{
          background: 'rgba(13, 17, 23, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '12px',
          padding: '16px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.85rem', color: theme.colors.textMuted }}>Structural Load Safety Factor:</span>
            <span style={{ fontSize: '0.9rem', color: '#FDE047', fontWeight: 'bold' }}>{loadMarginFactor.toFixed(2)}x</span>
          </div>
          <input
            type="range"
            min="1.1"
            max="2.5"
            step="0.05"
            value={loadMarginFactor}
            onChange={(e) => setLoadMarginFactor(Number(e.target.value))}
            style={{ width: '100%', accentColor: '#FDE047', cursor: 'pointer' }}
          />
        </div>
      </div>

      <h4 style={{ color: theme.colors.accent, margin: '16px 0 12px 0' }}>Neural Engine Execution Nodes</h4>
      <AIBSAutogradEngine loss={isOptimizing ? 0.0008 : 0.0014} />
      <AIBSReasoningEngine reasoningState={isOptimizing ? 'Re-optimizing Tensors...' : 'Optimal Geometry'} />
    </div>
  );
};

export default DesignParameters;
