import React, { useState } from 'react';
import StehouwerCMSTab from './StehouwerCMSTab';
import UniversalCreationSuite from './UniversalCreationSuite';

export default function UnifiedCreationHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('creation');

  const tabs = [
    { id: 'creation', label: 'Universal Creation Suite (Drafting)', icon: '🎨' },
    { id: 'cms', label: 'Stehouwer CMS (Publishing)', icon: '🌐' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      <div className="mobile-scroll-ribbon" style={{ display: 'flex', gap: '8px', padding: '8px clamp(10px, 2.5vw, 20px)', backgroundColor: '#161b22', borderBottom: '1px solid #30363d', overflowX: 'auto', whiteSpace: 'nowrap', scrollbarWidth: 'none', WebkitOverflowScrolling: 'touch', flexShrink: 0 }}>
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

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeSubTab === 'creation' && <UniversalCreationSuite {...props} />}
        {activeSubTab === 'cms' && <StehouwerCMSTab {...props} />}
      </div>
    </div>
  );
}
