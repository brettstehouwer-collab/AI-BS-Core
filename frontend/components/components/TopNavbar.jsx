import React, { useState, useRef, useEffect } from 'react';
import { masterHubs, simpleModeNavItems, PINNED_QUICK_TABS } from './navigationConfig';
import { useAppStore } from './useAppStore';
import AIProviderSettingsModal from './AIProviderSettingsModal';
import GlobalWalkthroughGuide from './GlobalWalkthroughGuide';
import TourGuideEngine from './TourGuideEngine';
import GlobalCommandPalette from './GlobalCommandPalette';
import TeamLiveChatModal from './TeamLiveChatModal';
import { subscribeToPresence, startPresenceHeartbeat } from './collaborationService';
import { filterNavigationByTier, USER_TIERS } from './accessControl';
import { auth } from '../firebase';
import { SYSTEM_VERSION } from './version';
import './MomMode.css';

export default function TopNavbar({ 
  activeTab, 
  onTabChange, 
  navLayout, 
  onToggleNavLayout,
  backendUrl, 
  backendOnline,
  backendStatus = 'online', 
  comfyOnline, 
  selectedModel,
  onSelectModel,
  availableModels = [],
  onOpenProfile, 
  userProfile,
  currentUser,
  userTier,
  isAdmin = true,
  simulatedTier,
  onSimulateTier,
  workspaceMode = 'simple',
  onToggleWorkspaceMode,
  momMode = false,
  onToggleMomMode,
  zoomLevel = 125,
  onZoomChange,
  zenMode = false,
  onToggleZenMode,
  onOpenMobileDrawer
}) {
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  const [openGroup, setOpenGroup] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const [showGuideModal, setShowGuideModal] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('guide') === 'true' || params.get('guide') === 'open' || params.get('tab') === 'guide';
    }
    return false;
  });
  const [showTour, setShowTour] = useState(false);
  const [showCmdPalette, setShowCmdPalette] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false);
  const [onlineCount, setOnlineCount] = useState(1);
  const [copiedLink, setCopiedLink] = useState(false);
  const [activeAIProvider, setActiveAIProvider] = useState(localStorage.getItem('aibs_active_ai_provider') || 'local');
  const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0 });
  const navRef = useRef(null);
  const scrollRibbonRef = useRef(null);
  const efficiencyMode = useAppStore(state => state.efficiencyMode);
  const [hwTelemetry, setHwTelemetry] = useState(null);

  // Poll Live GPU/CPU Hardware Telemetry for Ambient Navbar HUD
  useEffect(() => {
    let isMounted = true;
    let failStreak = 0;

    const isLocalDev = typeof window !== 'undefined' && 
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

    const fetchTelemetry = async () => {
      if (failStreak > 3) return; // Prevent network churn and thread blocking if core unreachable
      try {
        const apiBase = isLocalDev ? 'http://127.0.0.1:8080' : 'https://api.brettstehouwer.live';
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1200);

        const res = await fetch(`${apiBase}/api/v1/hardware/gpu/telemetry`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (res.ok) {
          const data = await res.json();
          if (isMounted && data.telemetry) {
            setHwTelemetry(data.telemetry);
            failStreak = 0;
          }
        } else {
          failStreak++;
        }
      } catch (err) {
        failStreak++;
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleGroupHover = (groupName, event) => {
    if (event && event.currentTarget) {
      const rect = event.currentTarget.getBoundingClientRect();
      setDropdownPos({
        top: rect.bottom,
        left: Math.max(8, Math.min(rect.left, window.innerWidth - 240))
      });
    }
    setOpenGroup(groupName);
  };

  // Start Presence Heartbeat for Current User
  useEffect(() => {
    if (currentUser) {
      startPresenceHeartbeat(currentUser, activeTab);
    }
  }, [currentUser, activeTab]);

  // Subscribe to live online presence count
  useEffect(() => {
    const unsub = subscribeToPresence((members) => {
      const online = members.filter(m => m.status === 'online').length;
      setOnlineCount(Math.max(1, online));
    });
    return () => unsub && unsub();
  }, []);

  // 1-Click Universal Tool Share Hyperlink
  const handleShareToolLink = () => {
    const url = `${window.location.origin}${window.location.pathname}?tab=${activeTab}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    });
  };

  // Horizontal Pan Handlers
  const handleScrollLeft = () => {
    if (scrollRibbonRef.current) {
      scrollRibbonRef.current.scrollBy({ left: -260, behavior: 'smooth' });
    }
  };

  const handleScrollRight = () => {
    if (scrollRibbonRef.current) {
      scrollRibbonRef.current.scrollBy({ left: 260, behavior: 'smooth' });
    }
  };

  // Sync Guide URL parameter
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (showGuideModal) {
        url.searchParams.set('guide', 'true');
      } else {
        url.searchParams.delete('guide');
        url.searchParams.delete('tool');
        url.searchParams.delete('mode');
      }
      window.history.replaceState({}, '', url.toString());
    }
  }, [showGuideModal]);

  // Global Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        setShowCmdPalette(prev => !prev);
      } else if ((e.key === '?' || e.key === 'F1') && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        setShowGuideModal(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const visibleHubs = filterNavigationByTier(masterHubs, userTier?.id || 'admin');
  const groupedCategories = visibleHubs.map(hub => ({
    group: hub.label,
    icon: hub.icon,
    items: hub.subTabs
  }));

  const activeGroupObj = groupedCategories.find(g => 
    g.items.some(item => item.key === activeTab)
  );

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 📱 NATIVE SMARTPHONE HEADER BAR (<= 768px) */}
      {isMobile ? (
        <div className="mobile-top-navbar" style={{
          minHeight: '52px',
          height: 'auto',
          background: 'rgba(13, 17, 23, 0.98)',
          borderBottom: '1px solid rgba(56, 189, 248, 0.25)',
          display: 'flex',
          flexDirection: 'row',
          flexWrap: 'nowrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 12px',
          paddingTop: 'max(env(safe-area-inset-top, 0px), 8px)',
          color: '#c9d1d9',
          userSelect: 'none',
          zIndex: 1000,
          position: 'relative',
          backdropFilter: 'blur(16px)',
          boxSizing: 'border-box'
        }}>
          {/* Left: Brand + Status */}
          <div
            onClick={() => onTabChange && onTabChange('chat')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
          >
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: 'linear-gradient(135deg, #38bdf8, #a855f7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 900,
              fontSize: '0.85rem',
              color: '#000000'
            }}>
              AI
            </div>
            <div>
              <div style={{ fontWeight: 800, color: '#58a6ff', fontSize: '0.9rem', lineHeight: 1.1 }}>
                Stehouwer AI
              </div>
              <div style={{ fontSize: '0.62rem', color: '#8b949e', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
                <span>{SYSTEM_VERSION} • RTX 4090 ({hwTelemetry?.core_temp_c || 72}°C)</span>
              </div>
            </div>
          </div>

          {/* Right: Quick Mobile Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {onToggleMomMode && (
              <button
                onClick={onToggleMomMode}
                title="Mom View: High Contrast & Big Text"
                style={{
                  background: momMode ? 'rgba(244, 63, 94, 0.3)' : 'rgba(255, 255, 255, 0.05)',
                  border: `1px solid ${momMode ? '#fb7185' : 'rgba(255, 255, 255, 0.15)'}`,
                  color: momMode ? '#fb7185' : '#94a3b8',
                  borderRadius: '6px',
                  padding: '5px 8px',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                🌸
              </button>
            )}

            <button
              onClick={() => setShowCmdPalette(true)}
              title="Search Tools & Tabs (Ctrl+K)"
              style={{
                background: 'rgba(56, 189, 248, 0.15)',
                border: '1px solid rgba(56, 189, 248, 0.35)',
                color: '#38bdf8',
                borderRadius: '6px',
                padding: '6px 10px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <span>🔍</span>
            </button>

            <button
              onClick={() => setShowChatModal(true)}
              title="Open Stehouwer Team Messenger"
              className="mobile-messenger-trigger-btn"
              style={{
                background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                border: '1px solid #38bdf8',
                color: '#ffffff',
                borderRadius: '6px',
                padding: '6px 9px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <span>💬</span>
              {onlineCount > 0 && (
                <span style={{ fontSize: '0.62rem', background: '#10b981', color: '#fff', borderRadius: '8px', padding: '1px 5px', fontWeight: 800 }}>
                  {onlineCount}
                </span>
              )}
            </button>

            <button
              onClick={() => onOpenMobileDrawer && onOpenMobileDrawer()}
              title="Open Navigation Menu"
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#ffffff',
                borderRadius: '6px',
                padding: '6px 10px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: 900,
                display: 'flex',
                alignItems: 'center'
              }}
            >
              ☰
            </button>
          </div>
        </div>
      ) : (
      /* Main Top Navbar with Pinned Quick-Dock & Horizontal Pan Controls */
      <div ref={navRef} style={{
        height: 'auto',
        minHeight: '54px',
        background: '#0d1117',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        alignItems: 'center',
        padding: '6px 12px',
        color: '#c9d1d9',
        fontSize: '0.88rem',
        userSelect: 'none',
        zIndex: 1000,
        position: 'relative',
        gap: '8px'
      }}>
        {/* Fixed Left Branding */}
        <div style={{ display: 'flex', flexDirection: 'column', flexShrink: 0, paddingRight: '8px', borderRight: '1px solid #21262d' }}>
          <span style={{ fontWeight: '700', color: '#58a6ff', fontSize: '0.95rem', letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>
            Stehouwer Publishing AI
          </span>
          <span style={{ fontSize: '0.68rem', color: '#8b949e' }}>{SYSTEM_VERSION}</span>
        </div>

        {/* ⚡ PINNED QUICK-DOCK BAR (Instant 1-Click Jumping) */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          background: 'rgba(22, 27, 34, 0.85)',
          padding: '2px 6px',
          borderRadius: '8px',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          boxShadow: '0 0 10px rgba(0,0,0,0.3)',
          flexShrink: 0
        }}>
          {PINNED_QUICK_TABS.map((pt) => {
            const isDockActive = activeTab === pt.key;
            return (
              <button
                key={pt.key}
                onClick={() => onTabChange(pt.key)}
                title={`Quick Jump to ${pt.label} (${pt.badge})`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '5px 9px',
                  borderRadius: '6px',
                  border: isDockActive ? '1px solid #38bdf8' : '1px solid transparent',
                  background: isDockActive ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.3), rgba(147, 51, 234, 0.3))' : 'transparent',
                  color: isDockActive ? '#ffffff' : '#94a3b8',
                  fontSize: '0.78rem',
                  fontWeight: isDockActive ? '700' : '500',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isDockActive ? '0 0 8px rgba(56, 189, 248, 0.4)' : 'none',
                  whiteSpace: 'nowrap'
                }}
                onMouseEnter={(e) => {
                  if (!isDockActive) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)';
                    e.currentTarget.style.color = '#ffffff';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isDockActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = '#94a3b8';
                  }
                }}
              >
                <span>{pt.icon}</span>
                <span style={{ display: 'inline-block' }}>{pt.label}</span>
              </button>
            );
          })}
        </div>

        {/* 🔥 AMBIENT HARDWARE GOVERNOR HUD CHIP (RTX 4090 + RYZEN 9 9950X) */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          padding: '4px 9px',
          borderRadius: '8px',
          boxShadow: '0 0 12px rgba(0,0,0,0.5)',
          fontSize: '0.74rem',
          fontWeight: '700',
          flexShrink: 0,
          minHeight: '28px',
          minWidth: '220px',
          contain: 'layout'
        }}>
          <span 
            title={`RTX 4090 Core Temp: ${hwTelemetry?.core_temp_c || 28}°C (Fan: ${hwTelemetry?.fan_speed_pct || 100}%)`}
            style={{ color: (hwTelemetry?.core_temp_c || 28) >= 70 ? '#f87171' : '#38bdf8', display: 'flex', alignItems: 'center', gap: '3px' }}
          >
            {(hwTelemetry?.core_temp_c || 28) < 40 ? '❄️' : '🔥'} {hwTelemetry?.core_temp_c ? `${hwTelemetry.core_temp_c}°C` : '28°C'}
          </span>
          <span style={{ color: '#475569' }}>|</span>
          <span 
            title={`VRAM: ${hwTelemetry?.memory_used_mb ? (hwTelemetry.memory_used_mb/1024).toFixed(1) : '1.1'} / ${hwTelemetry?.memory_total_mb ? (hwTelemetry.memory_total_mb/1024).toFixed(1) : '24.0'} GB`}
            style={{ color: '#c084fc', display: 'flex', alignItems: 'center', gap: '3px' }}
          >
            ⚡ {hwTelemetry?.memory_used_mb ? `${(hwTelemetry.memory_used_mb/1024).toFixed(1)}/24G` : '1.1/24G'}
          </span>
          <span style={{ color: '#475569' }}>|</span>
          <span 
            title={`Ryzen 9 9950X CPU Load: ${hwTelemetry?.cpu_util_pct || 15}%`}
            style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '3px' }}
          >
            💻 {hwTelemetry?.cpu_util_pct ? `${Math.round(hwTelemetry.cpu_util_pct)}%` : '15%'}
          </span>
          <button
            onClick={() => onTabChange && onTabChange('gpu_telemetry')}
            title="Open Full Sovereign GPU & Telemetry Workspace"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#38bdf8',
              cursor: 'pointer',
              padding: '0 2px',
              fontSize: '0.74rem',
              fontWeight: '900',
              opacity: 0.85
            }}
          >
            ↗
          </button>
        </div>

        {/* 🔍 PROMINENT SEARCH EVERYWHERE BUTTON (Ctrl+K) */}
        <button
          onClick={() => setShowCmdPalette(true)}
          title="Search all 50+ Tools, Commands & Pages (Ctrl+K)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            color: '#38bdf8',
            padding: '5px 12px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.78rem',
            fontWeight: '600',
            flexShrink: 0,
            boxShadow: '0 0 10px rgba(56, 189, 248, 0.15)',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#38bdf8';
            e.currentTarget.style.background = 'rgba(56, 189, 248, 0.12)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
            e.currentTarget.style.background = 'rgba(15, 23, 42, 0.8)';
          }}
        >
          <span>🔍 Jump to tool...</span>
          <kbd style={{
            background: '#1e293b',
            color: '#94a3b8',
            padding: '1px 5px',
            borderRadius: '4px',
            fontSize: '0.68rem',
            border: '1px solid #334155'
          }}>
            Ctrl+K
          </kbd>
        </button>

        {/* 🌸 DISCREET MOM MODE BUTTON (Fixed in Top Bar) */}
        {onToggleMomMode && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', flexShrink: 0 }}>
            <button
              onClick={onToggleMomMode}
              title={momMode ? "Mom Mode is Active (Big Text & High Contrast) — Click to Turn Off" : "Toggle Mom Mode: Big Text & High Contrast"}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                background: momMode ? 'linear-gradient(135deg, #e11d48, #be123c)' : 'rgba(244, 63, 94, 0.12)',
                color: momMode ? '#ffffff' : '#fb7185',
                border: `1px solid ${momMode ? '#fda4af' : 'rgba(244, 63, 94, 0.35)'}`,
                padding: '5px 9px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.74rem',
                fontWeight: '700',
                boxShadow: momMode ? '0 0 10px rgba(225, 29, 72, 0.4)' : 'none',
                transition: 'all 0.15s ease'
              }}
            >
              <span>🌸</span>
              <span>{momMode ? 'Mom Mode' : 'Mom View'}</span>
            </button>
            {momMode && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                background: 'rgba(15, 23, 42, 0.9)',
                border: '1px solid rgba(244, 63, 94, 0.4)',
                padding: '2px 5px',
                borderRadius: '5px'
              }}>
                <button
                  onClick={() => onZoomChange && onZoomChange(Math.max(100, zoomLevel - 15))}
                  style={{ background: 'transparent', border: 'none', color: '#fda4af', cursor: 'pointer', fontWeight: 900, fontSize: '0.75rem', padding: '0 2px' }}
                  title="Make Text & Visuals Smaller"
                >−</button>
                <span style={{ fontSize: '0.7rem', color: '#fecdd3', fontWeight: 700 }}>{zoomLevel}%</span>
                <button
                  onClick={() => onZoomChange && onZoomChange(Math.min(160, zoomLevel + 15))}
                  style={{ background: 'transparent', border: 'none', color: '#fda4af', cursor: 'pointer', fontWeight: 900, fontSize: '0.75rem', padding: '0 2px' }}
                  title="Make Text & Visuals Bigger"
                >+</button>
              </div>
            )}
          </div>
        )}

        

        {/* ↔️ SCROLLABLE NAVIGATION & TOOL RIBBON CONTAINER */}
        <div 
          ref={scrollRibbonRef}
          onScroll={() => setOpenGroup(null)}
          onWheel={(e) => {
            if (scrollRibbonRef.current && Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
              scrollRibbonRef.current.scrollLeft += e.deltaY;
            }
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            overflowX: 'auto',
            overflowY: 'hidden',
            flex: 1,
            whiteSpace: 'nowrap',
            padding: '4px 0',
            scrollBehavior: 'smooth',
            scrollbarWidth: 'thin',
            scrollbarColor: '#58a6ff #161b22'
          }}
        >
          {/* Navigation Items (Simple Mode vs. Pro Cockpit) */}
          {workspaceMode === 'simple' ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {simpleModeNavItems.map(item => {
                const isSelected = activeTab === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => onTabChange(item.key)}
                    title={item.description}
                    style={{
                      background: isSelected ? '#1f293d' : 'transparent',
                      color: isSelected ? '#38bdf8' : '#c9d1d9',
                      border: 'none',
                      borderBottom: isSelected ? '2px solid #38bdf8' : '2px solid transparent',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontWeight: isSelected ? '700' : '500',
                      fontSize: '0.85rem',
                      flexShrink: 0
                    }}
                  >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                );
              })}

              <button
                onClick={() => setShowCmdPalette(true)}
                title="Search all 32+ Tools & Commands (Ctrl+K)"
                style={{
                  background: 'rgba(56, 189, 248, 0.12)',
                  color: '#38bdf8',
                  border: '1px dashed #38bdf8',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: '600',
                  fontSize: '0.8rem',
                  flexShrink: 0
                }}
              >
                <span>🔍 All Tools</span>
                <kbd style={{ background: '#1e293b', padding: '1px 5px', borderRadius: '4px', fontSize: '0.7rem', color: '#94a3b8' }}>Ctrl+K</kbd>
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {groupedCategories.map((group) => {
                const isGroupActive = activeGroupObj?.group === group.group;
                const isOpen = openGroup === group.group;

                return (
                  <div key={group.group} style={{ position: 'relative', flexShrink: 0 }}>
                    <button
                      onClick={(e) => {
                        if (isOpen) {
                          setOpenGroup(null);
                        } else {
                          handleGroupHover(group.group, e);
                        }
                      }}
                      onMouseEnter={(e) => handleGroupHover(group.group, e)}
                      style={{
                        background: isGroupActive ? '#1f242d' : (isOpen ? '#161b22' : 'transparent'),
                        color: isGroupActive ? '#58a6ff' : '#c9d1d9',
                        border: 'none',
                        borderBottom: isGroupActive ? '2px solid #58a6ff' : '2px solid transparent',
                        padding: '8px 12px',
                        borderRadius: '6px 6px 0 0',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontWeight: isGroupActive ? '600' : '400'
                      }}
                    >
                      <span>{group.icon}</span>
                      <span>{group.group}</span>
                      <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>{isOpen ? '▲' : '▼'}</span>
                    </button>

                    {isOpen && (
                      <div 
                        onMouseLeave={() => setOpenGroup(null)}
                        style={{
                          position: 'fixed',
                          top: `${dropdownPos.top}px`,
                          left: `${dropdownPos.left}px`,
                          background: '#161b22',
                          border: '1px solid #30363d',
                          borderRadius: '0 8px 8px 8px',
                          boxShadow: '0 10px 30px rgba(0,0,0,0.8), 0 0 20px rgba(88, 166, 255, 0.25)',
                          padding: '8px',
                          minWidth: '220px',
                          zIndex: 99999,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px'
                        }}
                      >
                        <div style={{ fontSize: '0.7rem', color: '#8b949e', textTransform: 'uppercase', padding: '4px 8px 6px 8px', borderBottom: '1px solid #21262d', marginBottom: '4px' }}>
                          {group.group}
                        </div>
                        {group.items.map((item) => {
                          const isSelected = activeTab === item.key;
                          return (
                            <button
                              key={item.key}
                              onClick={() => {
                                onTabChange(item.key);
                                setOpenGroup(null);
                              }}
                              style={{
                                background: isSelected ? '#1f242d' : 'transparent',
                                color: isSelected ? '#58a6ff' : '#c9d1d9',
                                border: 'none',
                                padding: '8px 10px',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                fontSize: '0.8rem',
                                textAlign: 'left',
                                fontWeight: isSelected ? '600' : 'normal',
                                width: '100%'
                              }}
                            >
                              <span>{item.icon || '•'}</span>
                              <span style={{ flexGrow: 1 }}>{item.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Action Buttons inside scrollable ribbon */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
            {/* 💬 TEAM MESSENGER BUTTON */}
            <button
              onClick={() => setShowChatModal(true)}
              title="Open Stehouwer Team Messenger"
              style={{
                background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                color: '#ffffff',
                border: '1px solid #38bdf8',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                flexShrink: 0,
                boxShadow: '0 0 10px rgba(56, 189, 248, 0.4)'
              }}
            >
              <span>💬 Messenger</span>
              <span style={{ background: '#10b981', color: '#ffffff', padding: '1px 6px', borderRadius: '10px', fontSize: '0.7rem' }}>
                🟢 {onlineCount}
              </span>
            </button>

            {/* Hardcoded Business Email Button */}
            <button 
              onClick={() => onTabChange && onTabChange('email_client')}
              className="top-navbar-mode-btn"
              title="Open Stehouwer Business Email Client"
              style={{
                background: activeTab === 'email_client' ? 'linear-gradient(90deg, #8b5cf6 0%, #6d28d9 100%)' : 'linear-gradient(90deg, #1e1b4b 0%, #312e81 100%)',
                color: '#ffffff',
                border: '1px solid #818cf8',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                flexShrink: 0,
                boxShadow: '0 0 10px rgba(129, 140, 248, 0.4)'
              }}
            >
              <span>📧 Business Email</span>
              <span style={{ background: '#6366f1', color: '#ffffff', padding: '1px 6px', borderRadius: '10px', fontSize: '0.7rem' }}>
                📬
              </span>
            </button>

            {/* Hardcoded Video Meeting Button */}
            <button 
              onClick={() => onTabChange && onTabChange('video_agent')}
              className="top-navbar-mode-btn"
              title="Open Stehouwer Enterprise Video Meeting Suite (Google Meet / Zoom)"
              style={{
                background: (activeTab === 'video_agent' || activeTab === 'video_streaming') ? 'linear-gradient(90deg, #059669 0%, #047857 100%)' : 'linear-gradient(90deg, #064e3b 0%, #065f46 100%)',
                color: '#ffffff',
                border: '1px solid #34d399',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                flexShrink: 0,
                boxShadow: '0 0 10px rgba(52, 211, 153, 0.4)'
              }}
            >
              <span>📹 Video Meet</span>
              <span style={{ background: '#10b981', color: '#ffffff', padding: '1px 6px', borderRadius: '10px', fontSize: '0.7rem' }}>
                LIVE
              </span>
            </button>

            {onToggleWorkspaceMode && (
              <button
                onClick={onToggleWorkspaceMode}
                className="top-navbar-mode-btn"
                title="Toggle Mode"
                style={{
                  background: workspaceMode === 'simple' ? 'rgba(56, 189, 248, 0.15)' : 'linear-gradient(90deg, #7c3aed 0%, #6d28d9 100%)',
                  color: workspaceMode === 'simple' ? '#38bdf8' : '#ffffff',
                  border: `1px solid ${workspaceMode === 'simple' ? '#38bdf8' : '#a78bfa'}`,
                  padding: '6px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.78rem',
                  fontWeight: '700',
                  flexShrink: 0
                }}
              >
                <span>{workspaceMode === 'simple' ? '✨ Simple' : '⚡ Pro Cockpit'}</span>
              </button>
            )}

            <button
              onClick={handleShareToolLink}
              title="Copy direct shareable link"
              style={{
                background: copiedLink ? '#10b981' : 'rgba(56, 189, 248, 0.12)',
                color: copiedLink ? '#ffffff' : '#38bdf8',
                border: `1px solid ${copiedLink ? '#34d399' : '#38bdf8'}`,
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                flexShrink: 0
              }}
            >
              <span>🔗 {copiedLink ? 'Copied Link!' : 'Share Tool'}</span>
            </button>

            <button
              onClick={() => setShowTour(true)}
              style={{
                background: 'linear-gradient(90deg, #7c3aed 0%, #6d28d9 100%)',
                color: '#ffffff',
                border: '1px solid #a78bfa',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                flexShrink: 0
              }}
            >
              <span>🎯 Tour</span>
            </button>

            <button
              onClick={() => setShowGuideModal(true)}
              style={{
                background: 'linear-gradient(90deg, #0284c7 0%, #0369a1 100%)',
                color: '#ffffff',
                border: '1px solid #38bdf8',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                flexShrink: 0
              }}
            >
              <span>💡 Guide & Tips</span>
            </button>

            {/* Docked Team Chat Trigger */}
            <button
              onClick={() => setShowChatModal(true)}
              title="Open Stehouwer Team Live Chat"
              style={{
                background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                color: '#ffffff',
                border: '1px solid #38bdf8',
                padding: '6px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.78rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                flexShrink: 0
              }}
            >
              <span>💬 Team Chat</span>
              <span style={{ background: '#10b981', color: '#ffffff', padding: '1px 6px', borderRadius: '10px', fontSize: '0.68rem', fontWeight: 800 }}>
                🟢 {onlineCount}
              </span>
            </button>

            {/* Docked Zen Mode Toggle */}
            {onToggleZenMode && (
              <button
                onClick={onToggleZenMode}
                title={zenMode ? "Exit Zen Mode" : "Enter Zen Mode (Focus View)"}
                style={{
                  background: zenMode ? '#ef4444' : 'rgba(255, 255, 255, 0.08)',
                  color: '#ffffff',
                  border: `1px solid ${zenMode ? '#f87171' : 'rgba(255, 255, 255, 0.15)'}`,
                  padding: '6px 10px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.78rem',
                  fontWeight: '700',
                  flexShrink: 0
                }}
              >
                <span>{zenMode ? '❌ Exit Zen' : '🔲 Zen'}</span>
              </button>
            )}

            {currentUser && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                <span style={{ fontSize: '0.72rem', color: '#94a3b8', background: '#161b22', padding: '4px 8px', borderRadius: '6px', border: '1px solid #30363d' }}>
                  👤 {currentUser.displayName || currentUser.email?.split('@')[0] || 'Admin'}
                </span>
                <button
                  onClick={() => {
                    if (window.confirm('Sign out of AI-BS Dashboard?')) {
                      auth.signOut();
                      localStorage.removeItem('aibs_cached_user');
                    }
                  }}
                  style={{ background: 'transparent', color: '#f85149', border: '1px solid rgba(248, 81, 73, 0.4)', borderRadius: '6px', padding: '4px 8px', fontSize: '0.72rem', cursor: 'pointer', fontWeight: '600' }}
                >
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>

        
      </div>
      )}

      {/* Modals */}
      <TeamLiveChatModal 
        isOpen={showChatModal} 
        onClose={() => setShowChatModal(false)} 
        currentUser={currentUser} 
        activeTab={activeTab} 
        onNavigateTab={onTabChange} 
      />
      <AIProviderSettingsModal isOpen={showAIModal} onClose={() => setShowAIModal(false)} backendUrl={backendUrl} onProviderChange={(p, m) => { setActiveAIProvider(p); if (onSelectModel && m) onSelectModel(m); }} />
      <GlobalWalkthroughGuide isOpen={showGuideModal} onClose={() => setShowGuideModal(false)} onNavigateTab={onTabChange} initialTab={activeTab} onStartTour={(tabKey) => { if (tabKey && onTabChange) onTabChange(tabKey); setShowTour(true); }} />
      <TourGuideEngine activeTab={activeTab} isOpen={showTour} onClose={() => setShowTour(false)} />
      <GlobalCommandPalette isOpen={showCmdPalette} onClose={() => setShowCmdPalette(false)} onNavigateTab={onTabChange} onOpenGuide={() => setShowGuideModal(true)} onStartTour={() => setShowTour(true)} workspaceMode={workspaceMode} onToggleWorkspaceMode={onToggleWorkspaceMode} />
    </div>
  );
}







