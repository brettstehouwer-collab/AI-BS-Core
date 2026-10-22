import sys

comp_path = r"C:\AI-BS\frontend\src\components\TopNavbar.jsx"
with open(comp_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add onOpenMobileDrawer to props
prop_target = """  zenMode = false,
  onToggleZenMode
}) {"""

prop_repl = """  zenMode = false,
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
  }, []);"""

# 2. Add Mobile Header in return
return_target = """  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Main Top Navbar with Pinned Quick-Dock & Horizontal Pan Controls */}
      <div ref={navRef} style={{"""

return_repl = """  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 📱 NATIVE SMARTPHONE HEADER BAR (<= 768px) */}
      {isMobile ? (
        <div style={{
          height: '52px',
          background: 'rgba(13, 17, 23, 0.98)',
          borderBottom: '1px solid rgba(56, 189, 248, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 12px',
          paddingTop: 'max(env(safe-area-inset-top, 0px), 6px)',
          color: '#c9d1d9',
          userSelect: 'none',
          zIndex: 1000,
          position: 'relative',
          backdropFilter: 'blur(16px)'
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
      <div ref={navRef} style={{"""

# 3. Close the isMobile condition before modals
close_target = """        {/* ▶ PAN RIGHT BUTTON */}
        <button
          onClick={handleScrollRight}
          title="Scroll Navigation Right (▶)"
          style={{
            background: '#161b22',
            color: '#58a6ff',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '6px 10px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: 'bold',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 6px rgba(0,0,0,0.4)'
          }}
        >
          ▶
        </button>
      </div>

      {/* Modals */}"""

close_repl = """        {/* ▶ PAN RIGHT BUTTON */}
        <button
          onClick={handleScrollRight}
          title="Scroll Navigation Right (▶)"
          style={{
            background: '#161b22',
            color: '#58a6ff',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '6px 10px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            fontWeight: 'bold',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 6px rgba(0,0,0,0.4)'
          }}
        >
          ▶
        </button>
      </div>
      )}

      {/* Modals */}"""

# Apply patches
if prop_target in content:
    content = content.replace(prop_target, prop_repl, 1)
    print("Props Patched (LF)")
elif prop_target.replace('\n', '\r\n') in content:
    content = content.replace(prop_target.replace('\n', '\r\n'), prop_repl.replace('\n', '\r\n'), 1)
    print("Props Patched (CRLF)")
else:
    print("Props Target Not Found")

if return_target in content:
    content = content.replace(return_target, return_repl, 1)
    print("Return Patched (LF)")
elif return_target.replace('\n', '\r\n') in content:
    content = content.replace(return_target.replace('\n', '\r\n'), return_repl.replace('\n', '\r\n'), 1)
    print("Return Patched (CRLF)")
else:
    print("Return Target Not Found")

if close_target in content:
    content = content.replace(close_target, close_repl, 1)
    print("Close Patched (LF)")
elif close_target.replace('\n', '\r\n') in content:
    content = content.replace(close_target.replace('\n', '\r\n'), close_repl.replace('\n', '\r\n'), 1)
    print("Close Patched (CRLF)")
else:
    print("Close Target Not Found")

with open(comp_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("TopNavbar.jsx patched successfully!")
