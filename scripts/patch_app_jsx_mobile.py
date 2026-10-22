import os

app_path = r"C:\AI-BS\frontend\App.jsx"
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
import_target = """import MobileStehouwerChat from './components/MobileStehouwerChat.jsx';"""
import_repl = """import MobileStehouwerChat from './components/MobileStehouwerChat.jsx';
import MobileBottomNav from './components/MobileBottomNav.jsx';
import MobileNavDrawer from './components/MobileNavDrawer.jsx';"""

# 2. Add state
state_target = """  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);"""
state_repl = """  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);"""

# 3. Remove hard chat intercept so the entire platform works on phones
intercept_target = """  // Mobile Stehouwer Chat View (Default on Phone / APK)
  if (isMobileDevice && mobileViewMode === 'chat') {
    return (
      <MobileStehouwerChat
        backendUrl={backendUrl}
        onSwitchToDesktop={() => handleSetMobileViewMode('desktop')}
        currentUser={currentUser}
      />
    );
  }"""

intercept_repl = """  // Native Responsive Platform Mode for Mobile & Desktop
  // Users can access Chat, Project NoCo, VLC Media Player, and all 35+ tools seamlessly on phones."""

# 4. Add onOpenMobileDrawer to TopNavbar
topbar_target = """          <TopNavbar 
            activeTab={activeTab}
            onTabChange={(t) => { setActiveTab(t); setIsMobileMenuOpen(false); }}
            navLayout={navLayout}
            onToggleNavLayout={handleToggleNavLayout}"""

topbar_repl = """          <TopNavbar 
            activeTab={activeTab}
            onTabChange={(t) => { setActiveTab(t); setIsMobileMenuOpen(false); setIsMobileDrawerOpen(false); }}
            onOpenMobileDrawer={() => setIsMobileDrawerOpen(true)}
            navLayout={navLayout}
            onToggleNavLayout={handleToggleNavLayout}"""

# 5. Replace bottom floating button with MobileBottomNav and MobileNavDrawer
bottom_target = """        {/* Floating Toggle to return to Gemini Mobile Chat Mode when in Desktop view on phone */}
        {isMobileDevice && mobileViewMode === 'desktop' && (
          <button
            onClick={() => handleSetMobileViewMode('chat')}
            style={{
              position: 'fixed',
              bottom: '20px',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 99999,
              background: 'linear-gradient(135deg, #4285f4, #9b72cf)',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              borderRadius: '24px',
              padding: '10px 20px',
              fontSize: '0.85rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
              cursor: 'pointer'
            }}
          >
            <span>✦</span>
            <span>Switch to Stehouwer Mobile Chat</span>
          </button>
        )}"""

bottom_repl = """        {/* Native Mobile Bottom Navigation Bar (Active on Mobile Viewports) */}
        <MobileBottomNav
          activeTab={activeTab}
          onTabChange={(t) => {
            setActiveTab(t);
            setIsMobileDrawerOpen(false);
          }}
          onOpenDrawer={() => setIsMobileDrawerOpen(true)}
        />

        {/* Fullscreen Mobile Navigation & Tool Drawer */}
        <MobileNavDrawer
          isOpen={isMobileDrawerOpen}
          onClose={() => setIsMobileDrawerOpen(false)}
          activeTab={activeTab}
          onTabChange={(t) => {
            setActiveTab(t);
            setIsMobileDrawerOpen(false);
          }}
          momMode={momMode}
          onToggleMomMode={handleToggleMomMode}
          currentUser={currentUser}
        />"""

# Apply all patches
for target, repl, label in [
    (import_target, import_repl, "1: Imports"),
    (state_target, state_repl, "2: State"),
    (intercept_target, intercept_repl, "3: Chat Intercept"),
    (topbar_target, topbar_repl, "4: TopNavbar prop"),
    (bottom_target, bottom_repl, "5: Bottom Nav & Drawer")
]:
    if target in content:
        content = content.replace(target, repl, 1)
        print(f"Patched {label} (LF)")
    elif target.replace('\n', '\r\n') in content:
        content = content.replace(target.replace('\n', '\r\n'), repl.replace('\n', '\r\n'), 1)
        print(f"Patched {label} (CRLF)")
    else:
        print(f"Failed to find target for {label}")

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("App.jsx updated successfully!")
