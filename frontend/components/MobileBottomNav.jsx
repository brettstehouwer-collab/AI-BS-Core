import React from 'react';

/**
 * MobileBottomNav: Native-feeling bottom tab bar for smartphone screens (<= 768px).
 * Provides 1-thumb instant access to the core hubs:
 * - 💬 Chat (BS-Chat / Swarm)
 * - 🏕️ NoCo (Project NoCo 23-Acre Campus & 3D Walkthrough)
 * - 🎬 Media (VLC Player, Video Streaming & Media Studio)
 * - ⚡ Cockpit (Executive Cockpit & Command Center)
 * - ☰ More (Opens the full categorized tool drawer)
 */
export default function MobileBottomNav({
  activeTab,
  onTabChange,
  onOpenDrawer,
  unreadCount = 0
}) {
  const navItems = [
    {
      key: 'chat',
      label: 'Chat',
      icon: '💬',
      badge: unreadCount > 0 ? unreadCount : null,
      matches: ['chat', 'team_chat', 'mobile_chat']
    },
    {
      key: 'project_noco',
      label: 'NoCo',
      icon: '🏛️',
      badge: '3D',
      matches: ['project_noco', 'noco_properties', 'campus_map', 'master_plan_23acres']
    },
    {
      key: 'video_streaming',
      label: 'VLC / Media',
      icon: '🎬',
      matches: ['video_streaming', 'media_studio', 'music_daw']
    },
    {
      key: 'executive_cockpit',
      label: 'Cockpit',
      icon: '⚡',
      matches: ['executive_cockpit', 'command_center', 'agent_apps']
    },
    {
      key: 'menu',
      label: 'All Tools',
      icon: '☰',
      isAction: true,
      action: onOpenDrawer
    }
  ];

  return (
    <nav
      aria-label="Mobile Bottom Navigation"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: 'rgba(13, 17, 23, 0.94)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(56, 189, 248, 0.25)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 8px)',
        paddingTop: '6px',
        paddingLeft: '6px',
        paddingRight: '6px',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        boxShadow: '0 -4px 24px rgba(0, 0, 0, 0.7)',
        userSelect: 'none'
      }}
      className="mobile-bottom-nav-container"
    >
      {navItems.map((item) => {
        const isActive = item.matches
          ? item.matches.includes(activeTab)
          : activeTab === item.key;

        const handleClick = () => {
          if (item.isAction && item.action) {
            item.action();
          } else {
            onTabChange(item.key);
          }
        };

        return (
          <button
            key={item.key}
            onClick={handleClick}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'transparent',
              border: 'none',
              padding: '6px 2px',
              borderRadius: '8px',
              cursor: 'pointer',
              position: 'relative',
              outline: 'none',
              color: isActive ? '#38bdf8' : '#94a3b8',
              transition: 'all 0.15s ease',
              minHeight: '48px',
              touchAction: 'manipulation'
            }}
          >
            {/* Active Glow Pill Indicator */}
            {isActive && (
              <span
                style={{
                  position: 'absolute',
                  top: '-6px',
                  width: '28px',
                  height: '3px',
                  background: 'linear-gradient(90deg, #38bdf8, #a855f7)',
                  borderRadius: '2px',
                  boxShadow: '0 0 8px #38bdf8'
                }}
              />
            )}

            {/* Icon + Badge */}
            <div style={{ position: 'relative', fontSize: '1.25rem', lineHeight: 1.1 }}>
              <span>{item.icon}</span>
              {item.badge && (
                <span
                  style={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-10px',
                    background: item.badge === '3D' ? '#00FFFF' : '#ef4444',
                    color: item.badge === '3D' ? '#000000' : '#ffffff',
                    fontSize: '0.6rem',
                    fontWeight: 900,
                    padding: '1px 4px',
                    borderRadius: '8px',
                    lineHeight: 1.1,
                    boxShadow: '0 0 6px rgba(0,0,0,0.5)'
                  }}
                >
                  {item.badge}
                </span>
              )}
            </div>

            {/* Label */}
            <span
              style={{
                fontSize: '0.68rem',
                fontWeight: isActive ? 800 : 500,
                marginTop: '3px',
                letterSpacing: '0.2px',
                color: isActive ? '#ffffff' : '#94a3b8'
              }}
            >
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
