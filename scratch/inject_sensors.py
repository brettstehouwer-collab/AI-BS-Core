import os
import re

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_blocks = '''
        {/* SUB-TAB: AG SENSORS & POULTRY IPM */}
        {activeSubTab === 'ag_sensors' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#00FFFF', marginTop: 0 }}>?? Ag Sensor Networks & Automation</h3>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
                <li><strong>Wired & Wireless Nodes:</strong> Continuous monitoring of temperature, humidity, soil moisture, and air quality across the campus.</li>
                <li><strong>Centralized Automation:</strong> Sensor data integrated into building automation systems for centralized control of the HPA misting cycles and greenhouse climate.</li>
                <li><strong>Dynamic Islanding Logic:</strong> Sensor network coordinates with Automatic Transfer Switches (ATS) for seamless microgrid failover during utility outages.</li>
              </ul>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#f59e0b', marginTop: 0 }}>?? Poultry & Integrated Pest Management (IPM)</h3>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
                <li><strong>Dedicated Enclosures:</strong> Secure chicken and duck enclosures for egg production and organic pest control.</li>
                <li><strong>Biocontrol Integration:</strong> Poultry rotation through Agro-Shield zones minimizes chemical pesticide reliance.</li>
                <li><strong>Manure Management:</strong> Composting systems process poultry waste into nutrient-rich organic fertilizer for the bamboo and hemp perimeter.</li>
              </ul>
            </div>
          </div>
        )}
'''

pattern = r"(\s*{\s*/\*\s*SUB-TAB: LAMMERSON LANE MASTER PLAN)"
match = re.search(pattern, content)

if match:
    # Insert new_blocks right before Lammerson Lane
    content = content[:match.start()] + new_blocks + content[match.start():]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully injected Ag Sensors tab!")
else:
    print("Failed to find injection point!")
