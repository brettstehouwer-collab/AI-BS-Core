import { useState, useEffect } from "react";
import CryptoSwarmMobileController from './CryptoSwarmMobileController';
import MiningDashboardTab from './MiningDashboardTab';
import GpuNetworkTab from './GpuNetworkTab';
import PearlMiningHubTab from './PearlMiningHubTab';
import CryptoAccountingTab from './CryptoAccountingTab';
import CryptoLiveStreamTab from './CryptoLiveStreamTab';

/** @param {{backendUrl?: string, initialSubTab?: string}} props */
export default function UnifiedCryptoHub( props) {
  const getInitialSubTab = () => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const sub = params.get('subtab') || params.get('sub');
      if (sub && ['livestream', 'pearl', 'trader', 'accounting', 'mining', 'network'].includes(sub)) {
        return sub;
      }
      const mainTab = params.get('tab');
      if (['crypto_accounting', 'accounting', 'wallets', 'wallet', 'transfers'].includes(mainTab || '')) {
        return 'accounting';
      }
    }
    return props.initialSubTab || 'livestream';
  };

  const [activeSubTab, setActiveSubTab] = useState(getInitialSubTab);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (url.searchParams.get('subtab') !== activeSubTab) {
        url.searchParams.set('subtab', activeSubTab);
        window.history.replaceState({ ...window.history.state, subtab: activeSubTab }, '', url.toString());
      }
    }
  }, [activeSubTab]);

  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const sub = params.get('subtab') || params.get('sub');
      if (sub && ['livestream', 'pearl', 'trader', 'accounting', 'mining', 'network'].includes(sub)) {
        setActiveSubTab(sub);
      } else {
        const mainTab = params.get('tab');
        if (['crypto_accounting', 'accounting', 'wallets', 'wallet', 'transfers'].includes(mainTab || '')) {
          setActiveSubTab('accounting');
        }
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const tabs = [
    { id: 'livestream', label: 'Live Scalp & Orderbook Radar', icon: '⚡' },
    { id: 'pearl', label: 'Pearl (PRL) Sovereign Mining', icon: '🦪' },
    { id: 'trader', label: 'Crypto Trader & Swarm', icon: '💎' },
    { id: 'accounting', label: 'Crypto Accounting & Transfers', icon: '📊' },
    { id: 'mining', label: 'Mining, Hardware & Chia', icon: '⛏️' },
    { id: 'network', label: 'GPU Network & AI Renting', icon: '⚡' },
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
              backgroundColor: activeSubTab === tab.id ? (tab.id === 'livestream' ? '#1f6feb' : (tab.id === 'pearl' ? '#0066cc' : (tab.id === 'accounting' ? '#1f6feb' : '#238636'))) : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: activeSubTab === tab.id ? (tab.id === 'livestream' ? '1px solid #38bdf8' : (tab.id === 'pearl' ? '1px solid #00d2ff' : (tab.id === 'accounting' ? '1px solid #38bdf8' : '1px solid #2ea043'))) : '1px solid transparent',
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

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
        {activeSubTab === 'livestream' && <CryptoLiveStreamTab {...props} />}
        {activeSubTab === 'pearl' && <PearlMiningHubTab />}
        {activeSubTab === 'trader' && <CryptoSwarmMobileController {...props} />}
        {activeSubTab === 'accounting' && <CryptoAccountingTab />}
        {activeSubTab === 'mining' && <MiningDashboardTab />}
        {activeSubTab === 'network' && <GpuNetworkTab {...props} />}
      </div>
    </div>
  );
}
