import re

with open(r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx', 'r', encoding='utf-16') as f:
    code = f.read()

# 1. Update state
code = code.replace(
    "const [activeSubTab, setActiveSubTab] = useState('governance');",
    "const [activeSubTab, setActiveSubTab] = useState('strategy_master_plan');"
)
code = code.replace(
    "const [activeCategory, setActiveCategory] = useState('all');",
    ""
)

# 2. Update subTabsList
old_tabs_pattern = r'const subTabsList = \[\s*\{ id: \'governance\'.*?\];'
new_tabs = '''const subTabsList = [
    { id: 'strategy_master_plan', category: '🏛️ Strategy & Master Plan', label: '🏛️ Strategy & Master Plan' },
    { id: 'acoustics_stage', category: '🔊 Acoustics & Stage', label: '🔊 Acoustics & Stage' },
    { id: 'infrastructure_energy', category: '⚡ Infrastructure & Energy', label: '⚡ Infrastructure & Energy' },
    { id: 'agriculture_facilities', category: '🌾 Agriculture & Facilities', label: '🌾 Agriculture & Facilities' },
    { id: 'financials_operations', category: '📊 Financials & Operations', label: '📊 Financials & Operations' }
  ];'''
code = re.sub(old_tabs_pattern, new_tabs, code, flags=re.DOTALL)

old_categories = r'const categories = \[\s*\'all\',.*?\];'
code = re.sub(old_categories, 'const categories = [];', code, flags=re.DOTALL)

# 3. Replace Navigation Bar
nav_pattern = r'\{\/\* DUAL NAVIGATION CONTROL BAR.*?\{\/\* SUB-TAB CONTENT RENDERING \*\/\}'
new_nav = '''{/* CATEGORY NAVIGATION BAR */}
      <div style={{
        background: 'rgba(13, 17, 23, 0.98)',
        border: '1px solid #00FFFF',
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '24px',
        boxShadow: '0 0 25px rgba(0, 255, 255, 0.15)'
      }}>
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', flexWrap: 'wrap' }}>
          {subTabsList.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                flex: '1 1 auto',
                background: activeSubTab === tab.id
                  ? 'linear-gradient(135deg, rgba(0, 255, 255, 0.3), rgba(122, 40, 138, 0.5))'
                  : 'rgba(255, 255, 255, 0.03)',
                border: activeSubTab === tab.id ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.08)',
                color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
                padding: '12px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 700,
                whiteSpace: 'nowrap',
                textAlign: 'center',
                transition: 'all 0.2s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* SECTION CONTENT RENDERING */}'''
code = re.sub(nav_pattern, new_nav, code, flags=re.DOTALL)

# 4. Group formatting
# Strategy & Master Plan
code = code.replace("{activeSubTab === 'governance' && (", "{activeSubTab === 'strategy_master_plan' && ( <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>")
code = code.replace(")}\n\n      {activeSubTab === 'master_plan_23acres' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")
code = code.replace(")}\n\n      {activeSubTab === 'spatial_radial' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")
code = code.replace(")}\n\n      {activeSubTab === 'pillars' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")

# Acoustics & Stage
code = code.replace(")}\n\n      {activeSubTab === 'acoustic_engineering' && (", "</div> )}\n\n      {activeSubTab === 'acoustics_stage' && ( <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>")
code = code.replace(")}\n\n      {activeSubTab === 'stage_prompter' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")
code = code.replace(")}\n\n      {activeSubTab === 'neon_lounge' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")

# Infrastructure & Energy
code = code.replace(")}\n\n      {activeSubTab === 'microgrid_infrastructure' && (", "</div> )}\n\n      {activeSubTab === 'infrastructure_energy' && ( <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>")
code = code.replace(")}\n\n      {activeSubTab === 'biofuel_electrical' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")
code = code.replace(")}\n\n      {activeSubTab === 'bioenergy_rd' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")

# Agriculture & Facilities
code = code.replace(")}\n\n      {activeSubTab === 'hydro_recycling' && (", "</div> )}\n\n      {activeSubTab === 'agriculture_facilities' && ( <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>")
code = code.replace(")}\n\n      {activeSubTab === 'ag_sensors' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")
code = code.replace(")}\n\n      {activeSubTab === 'cea_farming' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")
code = code.replace(")}\n\n      {activeSubTab === 'support_facilities' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")

# Financials & Operations
code = code.replace(")}\n\n      {activeSubTab === 'calculators' && (", "</div> )}\n\n      {activeSubTab === 'financials_operations' && ( <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>")
code = code.replace(")}\n\n      {activeSubTab === 'operational_scenarios' && (", "<div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>")

# Final closing before footer
code = code.replace(")}\n\n      {/* FOOTER NAVIGATION CONTROLS", "</div> )}\n\n      {/* FOOTER NAVIGATION CONTROLS")

with open(r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx', 'w', encoding='utf-16') as f:
    f.write(code)
