import React, { useState, useEffect } from 'react';
import { masterHubs, getAllToolsFlatList } from './navigationConfig';
import { subscribeToTeamActivity, subscribeToPresence } from './collaborationService';
import './SimpleDashboardPortal.css';

export default function SimpleDashboardPortal({ 
  onNavigateTab, 
  onOpenGuide, 
  onStartTour,
  onSwitchToProMode,
  currentUser 
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedHubFilter, setSelectedHubFilter] = useState('all');
  const [recentActivities, setRecentActivities] = useState([]);
  const [onlineMembers, setOnlineMembers] = useState([]);
  const allTools = getAllToolsFlatList();

  useEffect(() => {
    const unsubActivity = subscribeToTeamActivity((acts) => {
      setRecentActivities(acts);
    }, 6);
    const unsubPresence = subscribeToPresence((mems) => {
      setOnlineMembers(mems.filter(m => m.status === 'online'));
    });
    return () => {
      unsubActivity && unsubActivity();
      unsubPresence && unsubPresence();
    };
  }, []);

  const filteredTools = allTools.filter(tool => {
    const matchesHub = selectedHubFilter === 'all' || tool.hubKey === selectedHubFilter;
    const q = searchQuery.toLowerCase().trim();
    if (!q) return matchesHub;
    return (
      matchesHub &&
      (tool.label.toLowerCase().includes(q) ||
       (tool.description && tool.description.toLowerCase().includes(q)) ||
       tool.hubLabel.toLowerCase().includes(q))
    );
  });

  const starterSteps = [
    {
      id: 'step-drive',
      icon: '☁️',
      title: '1. Shared Cloud Drive',
      desc: 'Centralized cloud folders for screenplays, media assets, contracts, and audio stems.',
      tab: 'shared_cloud_drive',
      cta: 'Open Cloud Drive'
    },
    {
      id: 'step-creative',
      icon: '✍️',
      title: '2. Hollywood Screenwriting',
      desc: 'Write in Final Draft format with AST shortcuts (Ctrl+1..6), run the !proof AI Doctor, and stream audio.',
      tab: 'unified_creation',
      cta: 'Open Creative Studio'
    },
    {
      id: 'step-advertising',
      icon: '📢',
      title: '3. Advertising Campaign Studio',
      desc: 'Generate viral ad copy, Facebook/Google campaigns, and high-conversion client funnels.',
      tab: 'advertising',
      cta: 'Launch Ad Studio'
    },
    {
      id: 'step-hospitality',
      icon: '💒',
      title: '4. Hospitality & Banquets',
      desc: 'Architect 2D/3D venue floor plans, VIP seating charts, and dietary registries.',
      tab: 'banquet_architect',
      cta: 'Launch Banquet Studio'
    },
    {
      id: 'step-calendar',
      icon: '📅',
      title: '5. Master Calendar',
      desc: 'Plan client jobs, banquet bookings, content releases, and team deadlines with synced action items.',
      tab: 'unified_calendar',
      cta: 'Open Master Calendar'
    }
  ];

  return (
    <div className="simple-dashboard-container">
      {/* Hero Welcome Banner */}
      <div className="simple-hero-card">
        <div className="simple-hero-left">
          <div className="simple-badge">
            <span>✨ AI-BS SIMPLE MODE</span>
            <span className="badge-divider">•</span>
            <span>Stehouwer Publishing Collaboration OS</span>
          </div>
          <h1>Welcome to the AI-BS Matrix</h1>
          <p>
            All 32+ business, screenwriting, hospitality, and neural engineering tools streamlined into intuitive master workspaces with real-time multi-user sync.
          </p>

          {/* Active Online Team Ribbon */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 'bold' }}>ACTIVE TEAM:</span>
            {onlineMembers.length === 0 ? (
              <span style={{ fontSize: '0.78rem', color: '#38bdf8' }}>🟢 You are online (Admin)</span>
            ) : (
              onlineMembers.map((m, idx) => (
                <span key={m.email || m.id || idx} style={{ fontSize: '0.78rem', color: '#f8fafc', background: '#1e293b', border: '1px solid #334155', padding: '3px 8px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>🟢</span>
                  <span>{m.name}</span>
                </span>
              ))
            )}
          </div>
        </div>

        <div className="simple-hero-actions">
          <button onClick={onStartTour} className="simple-btn-primary">
            <span>🎯 Start 1-Minute Tour</span>
          </button>
          <button onClick={onOpenGuide} className="simple-btn-secondary">
            <span>💡 Guide & Tips</span>
          </button>
          <button onClick={onSwitchToProMode} className="simple-btn-ghost">
            <span>⚡ Pro Cockpit Mode</span>
          </button>
        </div>
      </div>

      {/* ✍️ PROMINENT STEHOUWER PUBLISHING WRITING & STORY STUDIO */}
      <div className="simple-section-header" style={{ marginTop: '30px' }}>
        <div>
          <h2>✍️ Stehouwer Publishing — Writing & Screenplay Studio</h2>
          <p>Full-featured Hollywood scriptwriting, story bibles, multi-voice audio drama, and AI coverage.</p>
        </div>
        <button 
          onClick={() => onNavigateTab && onNavigateTab('unified_creation')}
          className="simple-see-all-btn"
        >
          Open Full Creative Studio →
        </button>
      </div>

      <div className="simple-starter-grid">
        <div className="simple-step-card featured-writing" onClick={() => onNavigateTab && onNavigateTab('unified_creation')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(56, 189, 248, 0.15)' }}>
            <span className="step-icon">🎬</span>
          </div>
          <div className="step-content">
            <h3>Hollywood AST Screenwriting</h3>
            <p>Industry-standard script editor with Final Draft keyboard shortcuts (<kbd>Ctrl+1..6</kbd>) and auto-formatting.</p>
            <span className="step-cta">Open Screenplay Studio →</span>
          </div>
        </div>

        <div className="simple-step-card featured-writing" onClick={() => onNavigateTab && onNavigateTab('stehouwer_cms')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(168, 85, 247, 0.15)' }}>
            <span className="step-icon">📖</span>
          </div>
          <div className="step-content">
            <h3>Story Bible & Character Vault</h3>
            <p>Character relationship matrices, episode outlines, lore databases, and publication management.</p>
            <span className="step-cta">Open Stehouwer CMS →</span>
          </div>
        </div>

        <div className="simple-step-card featured-writing" onClick={() => onNavigateTab && onNavigateTab('media_vault')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(236, 72, 153, 0.15)' }}>
            <span className="step-icon">🎙️</span>
          </div>
          <div className="step-content">
            <h3>2h 39m Master Audio Drama</h3>
            <p>Listen to the full multi-voice audio drama stream with synchronized visual screenplay teleprompter.</p>
            <span className="step-cta">Launch Audio Stream →</span>
          </div>
        </div>

        <div className="simple-step-card featured-writing" onClick={() => onNavigateTab && onNavigateTab('definitions_module')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(56, 189, 248, 0.15)' }}>
            <span className="step-icon">🛡️</span>
          </div>
          <div className="step-content">
            <h3>Content Risk &amp; Governance Analyzer</h3>
            <p>Quantifiable Risk Scoring (QRS), 6-vector compliance audit, and 1-click executive terminology de-risking.</p>
            <span className="step-cta">Open Governance Analyzer →</span>
          </div>
        </div>
      </div>

      {/* 📢 PROMINENT ADVERTISING, MARKETING & B2B LEAD MATRIX */}
      <div className="simple-section-header" style={{ marginTop: '30px' }}>
        <div>
          <h2>📢 Advertising, Marketing & B2B Growth Matrix</h2>
          <p>Drive revenue with automated AI ad copy, lead acquisition funnels, and personal branding.</p>
        </div>
        <button 
          onClick={() => onNavigateTab && onNavigateTab('advertising')}
          className="simple-see-all-btn"
        >
          Open Ad Campaign Studio →
        </button>
      </div>

      <div className="simple-starter-grid">
        <div className="simple-step-card featured-ads" onClick={() => onNavigateTab && onNavigateTab('advertising')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(239, 68, 68, 0.15)' }}>
            <span className="step-icon">📢</span>
          </div>
          <div className="step-content">
            <h3>AI Ad Copy & Multi-Channel Campaigns</h3>
            <p>Generate high-converting copy for Facebook Ads, Google Search, Print Flyers, and Email Funnels in seconds.</p>
            <span className="step-cta">Launch Ad Generator →</span>
          </div>
        </div>

        <div className="simple-step-card featured-ads" onClick={() => onNavigateTab && onNavigateTab('leadmatrix')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)' }}>
            <span className="step-icon">🎯</span>
          </div>
          <div className="step-content">
            <h3>B2B Lead Matrix & Client Funnels</h3>
            <p>Targeted West Michigan business leads, contract value scoring, and automated outreach sequences.</p>
            <span className="step-cta">Open Lead Matrix →</span>
          </div>
        </div>

        <div className="simple-step-card featured-ads" onClick={() => onNavigateTab && onNavigateTab('personal_brand')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(249, 115, 22, 0.15)' }}>
            <span className="step-icon">🔥</span>
          </div>
          <div className="step-content">
            <h3>Personal Brand Ghostwriter</h3>
            <p>Automate viral social media thought-leadership posts, founder stories, and content calendars.</p>
            <span className="step-cta">Open Brand Ghostwriter →</span>
          </div>
        </div>

        <div className="simple-step-card featured-ads" onClick={() => onNavigateTab && onNavigateTab('digital_storefront')}>
          <div className="step-icon-wrapper" style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
            <span className="step-icon">🏪</span>
          </div>
          <div className="step-content">
            <h3>Digital Storefront & Pricing Passes</h3>
            <p>Manage digital products, publication tiers, and client subscription pass checkout.</p>
            <span className="step-cta">Open Storefront →</span>
          </div>
        </div>
      </div>

      {/* 🤝 SHARED TEAM ACTIVITY & COLLABORATION STREAM */}
      <div className="simple-section-header" style={{ marginTop: '30px' }}>
        <div>
          <h2>🤝 Live Stehouwer Publishing Team Stream</h2>
          <p>Real-time audit log of all updates made by logged-in administrators.</p>
        </div>
      </div>

      <div style={{ background: '#090d16', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px', marginBottom: '24px' }}>
        {recentActivities.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '16px', color: '#64748b' }}>
            <span>🤝 Team collaboration active. Any saved screenplays, ad copy, or files will appear here live.</span>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {recentActivities.map((act, idx) => (
              <div key={act.id || act._id || idx} style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span>{act.userAvatar || '👤'}</span>
                  <strong style={{ fontSize: '0.85rem', color: '#f8fafc' }}>{act.userName}</strong>
                  <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: 'auto' }}>
                    {new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <p style={{ margin: '0 0 8px 0', fontSize: '0.82rem', color: '#94a3b8' }}>{act.action}</p>
                {act.tabKey && (
                  <button 
                    onClick={() => onNavigateTab && onNavigateTab(act.tabKey)}
                    style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', border: '1px solid #38bdf8', borderRadius: '4px', padding: '4px 8px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 'bold' }}
                  >
                    👁️ View in {act.toolName || 'Workspace'} →
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 5 Core Master Hubs Directory */}
      <div className="simple-section-header">
        <div>
          <h2>🏛️ The 5 Master Operating Hubs</h2>
          <p>Core departments governing business, entertainment, hospitality, and neural compute.</p>
        </div>
      </div>

      <div className="simple-hubs-grid">
        {masterHubs.map((hub, idx) => (
          <div key={hub.key || hub.id || idx} className="simple-hub-card">
            <div className="hub-card-header">
              <div className="hub-badge-group">
                <span className="hub-main-icon">{hub.icon}</span>
                <div className="hub-title-stack">
                  <h3>{hub.label}</h3>
                  <span className="hub-tool-count">{hub.subTabs.length} Specialized Tools</span>
                </div>
              </div>
            </div>

            <div className="hub-subtabs-chips">
              {hub.subTabs.slice(0, 4).map(sub => (
                <button
                  key={sub.key}
                  onClick={() => onNavigateTab(sub.key)}
                  className="subtab-chip-btn"
                  title={sub.description}
                >
                  <span className="chip-icon">{sub.icon || '•'}</span>
                  <span className="chip-label">{sub.label}</span>
                </button>
              ))}
              {hub.subTabs.length > 4 && (
                <span className="subtab-more-badge">+{hub.subTabs.length - 4} more</span>
              )}
            </div>

            <div className="hub-card-footer">
              <button
                onClick={() => onNavigateTab(hub.subTabs[0]?.key || 'dashboard')}
                className="hub-launch-btn"
              >
                <span>Launch {hub.label.split(' ')[0]} Hub →</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
