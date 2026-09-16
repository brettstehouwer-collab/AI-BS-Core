import React, { useState, useEffect, useRef } from 'react';
import ActionGlassQuoter from './action_glass/ActionGlassQuoter';
import CompetitorRadar from './action_glass/CompetitorRadar';
import DriverOutreach from './action_glass/DriverOutreach';
import FleetTracker from './action_glass/FleetTracker';
import SeoOptimizer from './action_glass/SeoOptimizer';

export default function ActionGlass({ BACKEND_URL }) {
  const [activeTab, setActiveTab] = useState('quoter');
  const [consoleLogs, setConsoleLogs] = useState([]);
  const consoleEndRef = useRef(null);

  const addLog = (msg) => {
    setConsoleLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [consoleLogs]);

  useEffect(() => {
    addLog(`System Initialized: Action Glass Workspace Loaded.`);
    addLog(`Connected to Backend: ${BACKEND_URL}`);
  }, []);

  const renderTabContent = () => {
    switch(activeTab) {
      case 'quoter': return <ActionGlassQuoter backendUrl={BACKEND_URL} />;
      case 'competitor_radar': return <CompetitorRadar backendUrl={BACKEND_URL} />;
      case 'driver_outreach': return <DriverOutreach backendUrl={BACKEND_URL} />;
      case 'fleet_tracker': return <FleetTracker backendUrl={BACKEND_URL} />;
      case 'seo_optimizer': return <SeoOptimizer backendUrl={BACKEND_URL} />;
      default: return null;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', background: '#0d1117' }}>
      
      {/* Sidebar Navigation */}
      <div style={{ 
        width: '250px', 
        background: '#161b22', 
        borderRight: '1px solid #30363d',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #30363d' }}>
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px', color: '#fff' }}>Action Glass</h1>
          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>Jenison, MI | Auto Glass Specialists</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', padding: '10px 0', flex: 1, overflowY: 'auto' }}>
          <div 
            onClick={() => { setActiveTab('quoter'); addLog("Switched to Interactive Quoter."); }}
            style={{ padding: '15px 20px', cursor: 'pointer', background: activeTab === 'quoter' ? '#1f6feb' : 'transparent', color: activeTab === 'quoter' ? '#fff' : '#c9d1d9', fontWeight: activeTab === 'quoter' ? 'bold' : 'normal', borderLeft: activeTab === 'quoter' ? '4px solid #ffd832' : '4px solid transparent', transition: '0.2s' }}
          >
            💲 Interactive Quoter
          </div>
          <div 
            onClick={() => { setActiveTab('competitor_radar'); addLog("Switched to Competitor Radar."); }}
            style={{ padding: '15px 20px', cursor: 'pointer', background: activeTab === 'competitor_radar' ? '#1f6feb' : 'transparent', color: activeTab === 'competitor_radar' ? '#fff' : '#c9d1d9', fontWeight: activeTab === 'competitor_radar' ? 'bold' : 'normal', borderLeft: activeTab === 'competitor_radar' ? '4px solid #ffd832' : '4px solid transparent', transition: '0.2s' }}
          >
            🎯 Competitor Radar
          </div>
          <div 
            onClick={() => { setActiveTab('driver_outreach'); addLog("Switched to Driver Outreach."); }}
            style={{ padding: '15px 20px', cursor: 'pointer', background: activeTab === 'driver_outreach' ? '#1f6feb' : 'transparent', color: activeTab === 'driver_outreach' ? '#fff' : '#c9d1d9', fontWeight: activeTab === 'driver_outreach' ? 'bold' : 'normal', borderLeft: activeTab === 'driver_outreach' ? '4px solid #ffd832' : '4px solid transparent', transition: '0.2s' }}
          >
            🚗 New Driver Outreach
          </div>
          <div 
            onClick={() => { setActiveTab('fleet_tracker'); addLog("Switched to Fleet Tracker."); }}
            style={{ padding: '15px 20px', cursor: 'pointer', background: activeTab === 'fleet_tracker' ? '#1f6feb' : 'transparent', color: activeTab === 'fleet_tracker' ? '#fff' : '#c9d1d9', fontWeight: activeTab === 'fleet_tracker' ? 'bold' : 'normal', borderLeft: activeTab === 'fleet_tracker' ? '4px solid #ffd832' : '4px solid transparent', transition: '0.2s' }}
          >
            🚚 Fleet Branding Tracker
          </div>
          <div 
            onClick={() => { setActiveTab('seo_optimizer'); addLog("Switched to SEO & Ad Optimizer."); }}
            style={{ padding: '15px 20px', cursor: 'pointer', background: activeTab === 'seo_optimizer' ? '#1f6feb' : 'transparent', color: activeTab === 'seo_optimizer' ? '#fff' : '#c9d1d9', fontWeight: activeTab === 'seo_optimizer' ? 'bold' : 'normal', borderLeft: activeTab === 'seo_optimizer' ? '4px solid #ffd832' : '4px solid transparent', transition: '0.2s' }}
          >
            📈 SEO & Ad Optimizer
          </div>
        </div>

        {/* Console Log Window */}
        <div style={{ height: '150px', background: '#010409', borderTop: '1px solid #30363d', padding: '10px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '10px', color: '#8b949e', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '5px' }}>Terminal Output</div>
          <div style={{ flex: 1, overflowY: 'auto', fontFamily: 'monospace', fontSize: '11px', color: '#4aff4a' }}>
            {consoleLogs.map((log, idx) => (
              <div key={idx} style={{ marginBottom: '4px' }}>{log}</div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
        {renderTabContent()}
      </div>

    </div>
  );
}
