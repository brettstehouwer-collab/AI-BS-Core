import codecs
import json
import re

with codecs.open(r'C:\AI-BS\scratch\ProjectNoCoStudioTab.jsx', 'r', 'utf-16') as f:
    text = f.read()

with codecs.open(r'C:\AI-BS\scratch\extracted.json', 'r', 'utf-8') as f:
    extracted = json.load(f)

# 1. State updates
text = text.replace(
    "const [activeSubTab, setActiveSubTab] = useState('governance');",
    "const [activeSubTab, setActiveSubTab] = useState('strategy_master_plan');"
)
text = text.replace(
    "const [activeCategory, setActiveCategory] = useState('all');\n",
    ""
)

# 2. Tabs List
old_tabs_pattern = r'const subTabsList = \[\s*\{ id: \'governance\'.*?\];'
new_tabs = '''const subTabsList = [
    { id: 'strategy_master_plan', category: '🏛️ Strategy & Master Plan', label: '🏛️ Strategy & Master Plan' },
    { id: 'acoustics_stage', category: '🔊 Acoustics & Stage', label: '🔊 Acoustics & Stage' },
    { id: 'infrastructure_energy', category: '⚡ Infrastructure & Energy', label: '⚡ Infrastructure & Energy' },
    { id: 'agriculture_facilities', category: '🌾 Agriculture & Facilities', label: '🌾 Agriculture & Facilities' },
    { id: 'financials_operations', category: '📊 Financials & Operations', label: '📊 Financials & Operations' }
  ];'''
text = re.sub(old_tabs_pattern, new_tabs, text, flags=re.DOTALL)

old_categories = r'const categories = \[\s*\'all\',.*?\];'
text = re.sub(old_categories, 'const categories = [];', text, flags=re.DOTALL)

# 3. Build new body
new_body = []
new_body.append('''      {/* CATEGORY NAVIGATION BAR */}
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

      {/* SECTION CONTENT RENDERING */}''')

groups = {
    'strategy_master_plan': ['governance', 'master_plan_23acres', 'spatial_radial', 'pillars'],
    'acoustics_stage': ['acoustic_engineering', 'stage_prompter', 'neon_lounge'],
    'infrastructure_energy': ['microgrid_infrastructure', 'biofuel_electrical', 'bioenergy_rd'],
    'agriculture_facilities': ['hydro_recycling', 'ag_sensors', 'cea_farming', 'support_facilities'],
    'financials_operations': ['calculators', 'operational_scenarios']
}

divider = '''        <div style={{ padding: '32px 0', borderBottom: '1px solid rgba(255,255,255,0.1)' }}></div>'''

for group_id, sections in groups.items():
    new_body.append(f"      {{activeSubTab === '{group_id}' && ( <div style={{{{ display: 'flex', flexDirection: 'column', gap: '24px' }}}}>")
    for idx, s in enumerate(sections):
        if s in extracted:
            new_body.append("        " + extracted[s])
            if idx < len(sections) - 1:
                new_body.append(divider)
    new_body.append("      </div> )}")

new_body_str = '\n'.join(new_body)

# Find the start of the navigation bar and the footer
nav_start = text.find('{/* DUAL NAVIGATION CONTROL BAR')
footer_start = text.find('{/* FOOTER NAVIGATION CONTROLS')

if nav_start != -1 and footer_start != -1:
    text = text[:nav_start] + new_body_str + '\n\n      ' + text[footer_start:]

with codecs.open(r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx', 'w', 'utf-8') as f:
    f.write(text)

print('Successfully built new file.')
