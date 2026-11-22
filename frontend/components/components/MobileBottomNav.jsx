import 'react';

/**
 * MobileBottomNav: Native-feeling bottom tab bar for smartphone screens (<= 768px).
 * Provides 1-thumb instant access to the core hubs:
 * - 💬 Chat (BS-Chat / Swarm)
 * - 🏕️ NoCo (Project NoCo 23-Acre Campus & 3D Walkthrough)
 * - 🎬 Media (VLC Player, Video Streaming & Media Studio)
 * - ⚡ Cockpit (Executive Cockpit & Command Center)
 * - ☰ More (Opens the full categorized tool drawer)
 */
export const SPECIALIST_NAV_CATALOG = {
  chat: { specialistCount: 24, roleRange: '01-24', domains: ['game_development_core', 'ide_and_repo_governance'] },
  project_noco: { specialistCount: 8, roleRange: '33-40', domains: ['noco_3d_and_biosystems'] },
  video_streaming: { specialistCount: 8, roleRange: '41-48', domains: ['vlc_media_and_vocal_studio'] },
  executive_cockpit: { specialistCount: 8, roleRange: '25-32', domains: ['cockpit_and_hardware_telemetry'] },
  menu: { specialistCount: 16, roleRange: '49-64', domains: ['publishing_and_immutable_archival', 'logistics_leads_and_recruiting'] }
};

/** @param {{activeTab: string, onTabChange?: (tab: string) => void, onOpenDrawer: () => void, unreadCount?: number}} props */
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
      specialistCount: 24,
      matches: ['chat', 'team_chat', 'mobile_chat']
    },
    {
      key: 'project_noco',
      label: 'NoCo',
      icon: '🏛️',
      badge: '3D',
      specialistCount: 8,
      matches: ['project_noco', 'noco_properties', 'campus_map', 'master_plan_23acres']
    },
    {
      key: 'video_streaming',
      label: 'VLC / Media',
      icon: '🎬',
      specialistCount: 8,
      matches: ['video_streaming', 'media_studio', 'music_daw']
    },
    {
      key: 'executive_cockpit',
      label: 'Cockpit',
      icon: '⚡',
      specialistCount: 8,
      matches: ['executive_cockpit', 'command_center', 'agent_apps']
    },
    {
      key: 'menu',
      label: 'All Tools',
      icon: '☰',
      specialistCount: 16,
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
            onTabChange?.(item.key);
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
