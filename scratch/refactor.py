import re

with open(r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update state
code = code.replace(
    "const [activeSubTab, setActiveSubTab] = useState('governance');",
    "const [activeSubTab, setActiveSubTab] = useState('strategy_master_plan');"
)

# 2. Update subTabsList
old_tabs = '''  const subTabsList = [
    { id: 'governance', category: '🏛️ Strategy & Master Plan', label: '⚖️ Trojan Horse Strategy & Governance' },
    { id: 'master_plan_23acres', category: '🏛️ Strategy & Master Plan', label: '🗺️ 23-Acre Master Plan & Ithaca NY Renderings' },
    { id: 'spatial_radial', category: '🏛️ Strategy & Master Plan', label: '🗺️ Lammerson Lane Master Plan' },
    { id: 'pillars', category: '🏛️ Strategy & Master Plan', label: '🏛️ Operational Pillars' },

    { id: 'acoustic_engineering', category: '🔊 Acoustics & Stage', label: '🔊 Acoustic Engineering & Parabolic Shell' },
    { id: 'stage_prompter', category: '🔊 Acoustics & Stage', label: '🎤 Live Stage Switcher & Teleprompter' },
    { id: 'neon_lounge', category: '🔊 Acoustics & Stage', label: '🍸 Futuristic Neon Lounge Architect' },

    { id: 'microgrid_infrastructure', category: '⚡ Infrastructure & Energy', label: '⚡ Redundant Microgrid & Geothermal' },
    { id: 'biofuel_electrical', category: '⚡ Infrastructure & Energy', label: '🔌 Biofuel, Isolation Transformer & Safety' },
    { id: 'bioenergy_rd', category: '⚡ Infrastructure & Energy', label: '🔬 R&D Bio-Energy Density & Deficit Reconciliation' },

    { id: 'hydro_recycling', category: '🌾 Agriculture & Facilities', label: '🌱 Closed-Loop Hydro Waste & Koi Re-Bonding' },
    { id: 'ag_sensors', category: '🌾 Agriculture & Facilities', label: '📡 Ag Sensor Networks & Poultry IPM' },
    { id: 'cea_farming', category: '🌾 Agriculture & Facilities', label: '🌾 CEA Agriculture & Livestock' },
    { id: 'support_facilities', category: '🌾 Agriculture & Facilities', label: '🎪 Support Buildings & 350-Person Septic' },

    { id: 'calculators', category: '📊 Financials & Operations', label: '📊 CapEx, ROI & System Calculators' },
    { id: 'operational_scenarios', category: '📊 Financials & Operations', label: '⚡ Operational Load Profiles & Scenarios' }
  ];'''

new_tabs = '''  const subTabsList = [
    { id: 'strategy_master_plan', category: '🏛️ Strategy & Master Plan', label: '🏛️ Strategy & Master Plan' },
    { id: 'acoustics_stage', category: '🔊 Acoustics & Stage', label: '🔊 Acoustics & Stage' },
    { id: 'infrastructure_energy', category: '⚡ Infrastructure & Energy', label: '⚡ Infrastructure & Energy' },
    { id: 'agriculture_facilities', category: '🌾 Agriculture & Facilities', label: '🌾 Agriculture & Facilities' },
    { id: 'financials_operations', category: '📊 Financials & Operations', label: '📊 Financials & Operations' }
  ];'''
code = code.replace(old_tabs, new_tabs)

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
                color: activeSubTab === tab.id ? '#ffffff' : theme.textMuted,
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


def replace_group(code, start_tab, sub_tabs):
    # This function wraps multiple consecutive tabs into one big div
    
    # 1. Change the first tab condition to the new group condition and open the wrapper
    code = code.replace(f"{{activeSubTab === '{start_tab}' && (", f"{{activeSubTab === '{sub_tabs[0]['group']}' && (\\n        <div style={{{{ display: 'flex', flexDirection: 'column', gap: '32px' }}}}>\\n          <div>")
    
    # 2. For each intermediate tab boundary, replace the closing and opening with a simple boundary
    for i in range(len(sub_tabs)-1):
        curr_tab = sub_tabs[i]['id']
        next_tab = sub_tabs[i+1]['id']
        
        # We need to find the boundary where curr_tab ends and next_tab begins
        # Usually it looks like:
        #      )}
        #
        #      {activeSubTab === 'next_tab' && (
        
        # Try a regex approach
        boundary_pattern = r'\}\)\}\s*\{activeSubTab === \'' + next_tab + r'\' && \(\s*<div.*?>'
        
        # Since some might be <div style... or just <div> we can just strip the react condition
        code = re.sub(r'\}\)\}\s*\{activeSubTab === \'' + next_tab + r'\' && \(', '</div>\\n\\n          <div>', code)

    # 3. Close the wrapper after the last tab
    last_tab = sub_tabs[-1]['id']
    # The last tab ends with `)}`, we need to replace it with `</div> )}` but ONLY the one corresponding to the last tab.
    # We will just replace all `)}` but it's tricky.
    
    return code

# We'll just do manual string replacement because it's safer.
# We know exactly how it looks.

# GROUP 1: strategy_master_plan
code = code.replace("{activeSubTab === 'governance' && (", "{activeSubTab === 'strategy_master_plan' && (\n        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'master_plan_23acres' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'spatial_radial' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'pillars' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'acoustic_engineering' && (", "</div>\n        </div>\n      )}\n\n      {activeSubTab === 'acoustic_engineering' && (")

# GROUP 2: acoustics_stage
code = code.replace("{activeSubTab === 'acoustic_engineering' && (", "{activeSubTab === 'acoustics_stage' && (\n        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'stage_prompter' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'neon_lounge' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'microgrid_infrastructure' && (", "</div>\n        </div>\n      )}\n\n      {activeSubTab === 'microgrid_infrastructure' && (")

# GROUP 3: infrastructure_energy
code = code.replace("{activeSubTab === 'microgrid_infrastructure' && (", "{activeSubTab === 'infrastructure_energy' && (\n        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'biofuel_electrical' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'bioenergy_rd' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'hydro_recycling' && (", "</div>\n        </div>\n      )}\n\n      {activeSubTab === 'hydro_recycling' && (")

# GROUP 4: agriculture_facilities
code = code.replace("{activeSubTab === 'hydro_recycling' && (", "{activeSubTab === 'agriculture_facilities' && (\n        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'ag_sensors' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'cea_farming' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'support_facilities' && (", "</div>\n\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'calculators' && (", "</div>\n        </div>\n      )}\n\n      {activeSubTab === 'calculators' && (")

# GROUP 5: financials_operations
code = code.replace("{activeSubTab === 'calculators' && (", "{activeSubTab === 'financials_operations' && (\n        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>\n          <div className='section-group'>")
code = code.replace(")}\n\n      {activeSubTab === 'operational_scenarios' && (", "</div>\n\n          <div className='section-group'>")

# For the very last one, we need to replace the last `)}`
# It's right before `    </div>\n  );\n};\n\nexport default ProjectNoCoStudioTab;`
code = code.replace(")}\n    </div>\n  );\n};\n\nexport default ProjectNoCoStudioTab;", "</div>\n        </div>\n      )}\n    </div>\n  );\n};\n\nexport default ProjectNoCoStudioTab;")


with open(r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
