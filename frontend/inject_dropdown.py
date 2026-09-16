import os
import shutil

path = "C:/AI-BS/frontend/components/ChatTab.jsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add state variables if missing
if "const [copiedChatUrl, setCopiedChatUrl] = useState(false);" not in content:
    content = content.replace(
        "const [starterCategory, setStarterCategory] = useState('All');",
        "const [starterCategory, setStarterCategory] = useState('All');\n  const [copiedChatUrl, setCopiedChatUrl] = useState(false);\n  const [showPresetDropdown, setShowPresetDropdown] = useState(false);\n  const presetDropdownRef = useRef(null);"
    )

# 2. Add click-outside useEffect for preset dropdown if missing
if "presetDropdownRef.current" not in content:
    click_outside = """  // Close preset dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (presetDropdownRef.current && !presetDropdownRef.current.contains(event.target)) {
        setShowPresetDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
"""
    content = content.replace(
        "  // Auto-scroll on new messages",
        click_outside + "\n  // Auto-scroll on new messages"
    )

# 3. Add ⚡ 18 Quick Starters button in header if missing
if "⚡ 18 Quick Starters" not in content:
    header_btn = """          <button
            onClick={() => setChatMessages([])}
            title="Reset Chat & View 18 Quick Starter Showcase Cards"
            style={{
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
              color: '#ffffff',
              border: '1px solid #60a5fa',
              padding: '4px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.72rem',
              fontWeight: '700',
              boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)'
            }}
          >
            ⚡ 18 Quick Starters
          </button>
"""
    content = content.replace(
        "          <button\n            onClick={() => setShowTips(!showTips)}",
        header_btn + "\n          <button\n            onClick={() => setShowTips(!showTips)}"
    )

# 4. Add ⚡ Presets Dropdown button next to 📎 attachment button
dropdown_ui = """          {/* Preset Dropdown Button & Menu by Chat Bar */}
          <div style={{ position: 'relative', flexShrink: 0 }} ref={presetDropdownRef}>
            <button
              onClick={() => setShowPresetDropdown(!showPresetDropdown)}
              title="Select a Quick Action Preset"
              style={{
                height: '42px',
                padding: '0 12px',
                background: showPresetDropdown ? 'linear-gradient(135deg, #2563eb, #4f46e5)' : 'rgba(56, 189, 248, 0.12)',
                border: `1px solid ${showPresetDropdown ? '#60a5fa' : 'rgba(56, 189, 248, 0.35)'}`,
                borderRadius: '10px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: showPresetDropdown ? '#ffffff' : '#38bdf8',
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap'
              }}
            >
              <span>⚡ Presets</span>
              <span style={{ fontSize: '0.65rem' }}>{showPresetDropdown ? '▲' : '▼'}</span>
            </button>

            {/* Dropdown Menu Popup (Anchored Above the Button) */}
            {showPresetDropdown && (
              <div style={{
                position: 'absolute',
                bottom: '48px',
                left: '0',
                width: '350px',
                maxHeight: '380px',
                overflowY: 'auto',
                background: 'linear-gradient(180deg, #0f172a 0%, #090d16 100%)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                borderRadius: '12px',
                boxShadow: '0 16px 40px rgba(0,0,0,0.8), 0 0 20px rgba(56, 189, 248, 0.15)',
                zIndex: 1000,
                padding: '8px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}>
                <div style={{
                  padding: '6px 8px 8px 8px',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#38bdf8' }}>
                    ⚡ 18 Quick Action Presets
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#64748b' }}>Click to Launch</span>
                </div>

                {starterCards.map((card, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      setShowPresetDropdown(false);
                      handleSendMessage(card.prompt);
                    }}
                    style={{
                      padding: '8px 10px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid transparent',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(56, 189, 248, 0.15)';
                      e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                      e.currentTarget.style.borderColor = 'transparent';
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                      <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9' }}>{card.title}</span>
                      <span style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.06)', padding: '1px 6px', borderRadius: '4px', color: '#94a3b8' }}>{card.category}</span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: '1.3' }}>{card.desc}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
"""

if "{/* Preset Dropdown Button & Menu by Chat Bar */}" not in content:
    content = content.replace(
        "          {/* Attachment Button 📎 */}",
        dropdown_ui + "\n          {/* Attachment Button 📎 */}"
    )

with open(path, "w", encoding="utf-8", newline="\n") as f:
    f.write(content)

shutil.copy2(path, "C:/AI-BS/frontend/src/components/ChatTab.jsx")
print("Successfully injected Dropdown, copiedChatUrl, and 18-presets cleanly in UTF-8!")
