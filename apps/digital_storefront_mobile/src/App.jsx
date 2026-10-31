import React, { useState } from 'react';
import DigitalStorefrontTab from './components/DigitalStorefrontTab';
import CryptoSwarmMobileController from './components/CryptoSwarmMobileController';

export default function App({ currentUser = null } = {}) {
  const [activeTab, setActiveTab] = useState('storefront');
  const backendUrl = "https://ai-bs.brettstehouwer.live";

  return (
    <div className="standalone-app-shell">
      {/* App Header Bar */}
      <div className="standalone-topbar">
        <h1>
          <span>🚀</span> Stehouwer Storefront
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#3fb950', background: 'rgba(63,185,80,0.15)', padding: '4px 8px', borderRadius: '12px' }}>
          ● Identity / service verification unavailable
        </div>
      </div>

      {/* Navigation Subtab Bar */}
      <div className="standalone-subtab-bar">
        <button
          onClick={() => setActiveTab('storefront')}
          className={`standalone-subtab-btn ${activeTab === 'storefront' ? 'active' : 'inactive'}`}
        >
          <span>🚀</span>
          <span>Digital Resale & SaaS</span>
        </button>

        <button
          onClick={() => setActiveTab('crypto')}
          className={`standalone-subtab-btn ${activeTab === 'crypto' ? 'active' : 'inactive'}`}
        >
          <span>⚡</span>
          <span>Crypto Swarm Controller</span>
        </button>
      </div>

      {/* Active Tab Content Area */}
      <div className="standalone-content-area">
        {activeTab === 'storefront' && (
          <DigitalStorefrontTab backendUrl={backendUrl} currentUser={currentUser} selectedModel="stehouwer_llm" />
        )}
        {activeTab === 'crypto' && (
          <CryptoSwarmMobileController backendUrl={backendUrl} currentUser={currentUser} />
        )}
      </div>
    </div>
  );
}
