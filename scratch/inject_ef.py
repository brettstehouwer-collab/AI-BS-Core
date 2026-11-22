import os
import re

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_block = '''
          {/* ELECTRO-FERMENTATION (EF) INTEGRATION */}
          <div style={{ background: theme.cardBg, border: '1px solid #7c3aed', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>?? Electro-Fermentation (EF) Biorefinery Integration</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>
              Integrating advanced Bioelectrochemical Systems (BES) to optimize anaerobic fermentation of agricultural and organic waste. By utilizing solid-state electrodes as electron mediators, we control microbial metabolic pathways to maximize energy yield and value-added product synthesis without chemical buffers.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(124, 58, 237, 0.3)' }}>
                <h4 style={{ color: theme.accentViolet, margin: '0 0 6px 0', fontSize: '0.95rem' }}>Anodic Electro-Fermentation (AEF)</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                  The working electrode acts as an electron sink for exoelectrogenic bacteria (e.g., <i>Geobacter</i>). This dissipates surplus electrons during waste breakdown, facilitating a higher biomass yield, stabilizing pH/redox irregularities, and generating direct microgrid electricity.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <h4 style={{ color: theme.accentGreen, margin: '0 0 6px 0', fontSize: '0.95rem' }}>Microbial Electrosynthesis (MES)</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                  Cathodic biofilms utilize excess microgrid power as an electron donor to reduce CO2 into value-added platform chemicals (like acetate or methane). This acts as a biological energy storage medium.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.3)' }}>
                <h4 style={{ color: theme.accentCyan, margin: '0 0 6px 0', fontSize: '0.95rem' }}>Stoichiometric Equilibration</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                  Overcoming traditional anaerobic setbacks by avoiding expensive gas micro-bubbling or chemical pH neutralizers. Electrodes directly manage the electron transfer kinetics and extracellular electron transport (EET) via cytochromes and nanowires.
                </p>
              </div>
            </div>
          </div>
'''

# Find the injection point: right before BIO-ENERGY DEFICIT MATHEMATICAL RECONCILIATION ENGINE
pattern = r"(\s*{\s*/\*\s*BIO-ENERGY DEFICIT MATHEMATICAL RECONCILIATION ENGINE\s*\*/)"
match = re.search(pattern, content)

if match:
    content = content[:match.start()] + new_block + content[match.start():]
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully injected Electro-Fermentation block!")
else:
    print("Failed to find injection point!")
