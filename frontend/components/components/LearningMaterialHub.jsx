import React, { useState } from 'react';
import AeoTracker from '../src/components/AeoTracker.jsx';
import SeoOptimizer from '../src/clients/action_glass/SeoOptimizer.jsx';

export default function LearningMaterialHub() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

  const [activeSubTab, setActiveSubTab] = useState('aeo_tracker');

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>📘 Learning Material & Educational Tools</h2>
      <p style={{ color: '#8b949e', marginBottom: '20px' }}>
        Interactive educational modules and information explainers.
      </p>

      {/* Internal Tab Navigation */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
        <button
          onClick={() => setActiveSubTab('aeo_tracker')}
          style={{
            padding: '8px 16px',
            background: activeSubTab === 'aeo_tracker' ? '#1f6feb' : 'transparent',
            color: activeSubTab === 'aeo_tracker' ? '#ffffff' : '#c9d1d9',
            border: '1px solid',
            borderColor: activeSubTab === 'aeo_tracker' ? '#1f6feb' : '#30363d',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          🔍 AEO Tracker Explainer
        </button>
        <button
          onClick={() => setActiveSubTab('seo_optimizer')}
          style={{
            padding: '8px 16px',
            background: activeSubTab === 'seo_optimizer' ? '#1f6feb' : 'transparent',
            color: activeSubTab === 'seo_optimizer' ? '#ffffff' : '#c9d1d9',
            border: '1px solid',
            borderColor: activeSubTab === 'seo_optimizer' ? '#1f6feb' : '#30363d',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          📈 SEO Optimizer Explainer
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ background: '#0d1117', padding: '20px', borderRadius: '8px', border: '1px solid #30363d' }}>
        {activeSubTab === 'aeo_tracker' && <AeoTracker />}
        {activeSubTab === 'seo_optimizer' && <SeoOptimizer backendUrl={`${backendUrl}/api/proxy/3000`} />}
      </div>
    </div>
  );
}
