import React, { useState } from 'react';
import RapidApiReconTab from './RapidApiReconTab';
import BrettDataTab from './BrettDataTab';
import LostPropertyTab from './LostPropertyTab';
import OsintDataVaultTab from './OsintDataVaultTab';

export default function UnifiedOsintHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('recon');

  const tabs = [
    { id: 'recon', label: 'RapidAPI Recon OSINT', icon: '🌐' },
    { id: 'lost_property', label: 'Lost Property & Breach Scanner', icon: '🔍' },
    { id: 'api_hub', label: 'API Keys & Data Hub', icon: '🔑' },
    { id: 'saved_vault', label: 'Data Saved Vault', icon: '🗄️' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      {/* Top Navigation Header */}
      <div style={{ display: 'flex', gap: '10px', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeSubTab === tab.id ? '#238636' : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeSubTab === 'recon' && <RapidApiReconTab {...props} />}
        {activeSubTab === 'lost_property' && <LostPropertyTab {...props} />}
        {activeSubTab === 'api_hub' && <BrettDataTab {...props} />}
        {activeSubTab === 'saved_vault' && (
          <div style={{ padding: '20px', height: '100%', overflowY: 'auto' }}>
            <OsintDataVaultTab {...props} />
          </div>
        )}
      </div>
    </div>
  );
}
