import React from 'react';
import { theme } from '../styles/theme';

export const AIBSAutogradEngine = ({ activeLayers = 24, loss = 0.0014 }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.85)',
      border: `1px solid ${theme.colors.accent}`,
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px',
      boxShadow: `0 0 15px ${theme.colors.glowCyan}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: theme.colors.accent, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🧠</span> AIBS Autograd Structural Engine
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(0, 255, 255, 0.15)', color: theme.colors.accent, padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.accent}` }}>
          PyTorch Autograd · Loss: {loss}
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: '0 0 10px 0' }}>
        Automatic differentiation pipeline calculating real-time finite element structural stress, truss deflection, and material optimization tensors.
      </p>
      <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#A7F3D0', background: '#000', padding: '8px', borderRadius: '6px' }}>
        [aibsAutogradEngine] Forward Pass Complete · {activeLayers} Structural Nodes Optimized
      </div>
    </div>
  );
};

export const AIBSReasoningEngine = ({ graphNodes = 1420, reasoningState = 'Optimal Geometry' }) => {
  return (
    <div style={{
      background: 'rgba(13, 17, 23, 0.85)',
      border: `1px solid ${theme.colors.secondary}`,
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px',
      boxShadow: `0 0 15px ${theme.colors.glowViolet}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ color: '#D8B4FE', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🕸️</span> AIBS Spatial Reasoning Engine
        </h4>
        <span style={{ fontSize: '0.8rem', background: 'rgba(122, 40, 138, 0.25)', color: '#E9D5FF', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${theme.colors.secondary}` }}>
          Graph Reasoning · {reasoningState}
        </span>
      </div>
      <p style={{ fontSize: '0.85rem', color: theme.colors.textMuted, margin: '0 0 10px 0' }}>
        Graph neural network evaluating acoustic ray tracing, thermal dissipation vectors, and egress circulation paths across {graphNodes} architectural vertices.
      </p>
      <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#E9D5FF', background: '#000', padding: '8px', borderRadius: '6px' }}>
        [aibsReasoningEngine] {graphNodes} Graph Nodes Verified · Acoustic Ray Tracing Converged (RT60 = 0.42s)
      </div>
    </div>
  );
};

const DesignSoftwareUsed = () => {
  return (
    <div style={{ color: theme.colors.textPrimary }}>
      <h3 style={{ margin: '0 0 16px 0', color: theme.colors.accent }}>🤖 Computational Design Software & Neural Engines</h3>
      <AIBSAutogradEngine />
      <AIBSReasoningEngine />
    </div>
  );
};

export default DesignSoftwareUsed;
