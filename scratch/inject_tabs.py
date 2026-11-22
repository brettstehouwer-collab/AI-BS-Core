import os

filepath = r'C:\AI-BS\frontend\components\ProjectNoCoStudioTab.jsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

injection_point = "        {activeSubTab === 'neon_lounge' && ("

new_blocks = '''
        {/* SUB-TAB: SUPPORT BUILDINGS & SEPTIC */}
        {activeSubTab === 'support_facilities' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentBlue, marginTop: 0 }}>?? Support & Ancillary Buildings</h3>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
                <li><strong>Recording Studio:</strong> 800 sq ft, professional acoustic treatment.</li>
                <li><strong>Rehearsal Space:</strong> 1,200 sq ft for music rehearsals and small performances.</li>
                <li><strong>Costume Shop & Set Workshop:</strong> 1,500 sq ft for textile work and light construction.</li>
                <li><strong>Fire Pit:</strong> Circular stone area with concentric rings for gatherings.</li>
                <li><strong>Sheep Barn:</strong> 1,200 sq ft with lambing pens and feed storage.</li>
                <li><strong>Alpaca Shelter:</strong> 800 sq ft open-sided building.</li>
              </ul>
            </div>
            <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>?? 350-Person Septic & Wastewater</h3>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
                <li><strong>Main Treatment System:</strong> 3,000-gallon concrete septic tank with advanced treatment unit and constructed wetland. Designed for 350-person peak occupancy.</li>
                <li><strong>Artist Residences:</strong> Composting toilet systems to reduce hydraulic loading.</li>
                <li><strong>Greywater System:</strong> Sinks and showers routed through constructed wetlands for landscape irrigation.</li>
                <li><strong>Agricultural Wastewater:</strong> Specialized treatment for nutrient-rich drainage from hydroponics.</li>
              </ul>
            </div>
          </div>
        )}

        {/* SUB-TAB: OPERATIONAL LOAD PROFILES */}
        {activeSubTab === 'operational_loads' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
            <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>? Peak Event Day Scenarios</h3>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px' }}>
                <p><strong>Scenario:</strong> 150-Person Concert + Full Farm Operation</p>
                <ul style={{ paddingLeft: '20px', lineHeight: '1.6', marginBottom: 0 }}>
                  <li><strong>PA System & Lighting:</strong> 12 kW continuous</li>
                  <li><strong>HPA Farm Pumps:</strong> 5 kW continuous</li>
                  <li><strong>HVAC & Green Rooms:</strong> 18 kW</li>
                  <li><strong>Total Peak Draw:</strong> ~35 kW</li>
                  <li><strong>Buffer Capacity:</strong> 200 kWh BESS handles 5+ hours of peak event time with zero grid reliance.</li>
                </ul>
              </div>
            </div>
            <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentBlue, marginTop: 0 }}>?? Baseline Night Operations</h3>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px' }}>
                <p><strong>Scenario:</strong> Winter Nighttime Maintenance</p>
                <ul style={{ paddingLeft: '20px', lineHeight: '1.6', marginBottom: 0 }}>
                  <li><strong>Geothermal Heating:</strong> 8 kW</li>
                  <li><strong>Base Lighting & Security:</strong> 2 kW</li>
                  <li><strong>Hydroponics Circulation:</strong> 3 kW</li>
                  <li><strong>MFC/Biogas Generation:</strong> +2 kW steady trickle</li>
                  <li><strong>Total Draw:</strong> ~13 kW</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* SUB-TAB: CAPEX & ROI */}
        {activeSubTab === 'capex_calculators' && (
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>?? CapEx & ROI Estimations</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                  <th style={{ padding: '10px' }}>System Component</th>
                  <th style={{ padding: '10px' }}>Est. CapEx</th>
                  <th style={{ padding: '10px' }}>Payback Period</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px' }}>150kW Solar Array + 200kWh BESS</td>
                  <td style={{ padding: '10px', color: theme.accentBlue }}>,000</td>
                  <td style={{ padding: '10px' }}>6-8 Years (Utility Savings)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px' }}>3,000-Gal Advanced Septic & Wetlands</td>
                  <td style={{ padding: '10px', color: theme.accentBlue }}>,000</td>
                  <td style={{ padding: '10px' }}>Immediate (Required Infrastructure)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px' }}>4,000 sq ft Hydroponics Greenhouse</td>
                  <td style={{ padding: '10px', color: theme.accentBlue }}>,000</td>
                  <td style={{ padding: '10px' }}>3-4 Years (Crop Yields)</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px' }}>Geothermal Ground Source Heat Pumps</td>
                  <td style={{ padding: '10px', color: theme.accentBlue }}>,000</td>
                  <td style={{ padding: '10px' }}>5-7 Years (HVAC Savings)</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* SUB-TAB: LAMMERSON LANE MASTER PLAN */}
        {activeSubTab === 'spatial_radial' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>??? The Mycelial Radial: Lammerson Lane Master Plan</h3>
              <p style={{ color: theme.textMuted, lineHeight: '1.6' }}>
                The campus footprint follows concentric zoning optimized for acoustic isolation, microclimate management, and resource routing across the Lammerson Lane property.
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '15px', marginTop: '20px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #00FFFF' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 0: The Core</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: theme.textMuted }}>"Living Stage" Amphitheater (3,000 sq ft, 150 seats) incorporating live foliage as natural acoustic dampening.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #7A288A' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 1: Inner Ring</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: theme.textMuted }}>Glass-walled "Green Rooms" serving as artist preparation spaces and high-yield plant nurseries.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 2: Residential Halo</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: theme.textMuted }}>Continuous ring of Tech-Earthship housing providing primary acoustic containment and living spaces.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 3: Agro-Shield</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: theme.textMuted }}>Dense barrier of timber bamboo, corn, and hemp providing physical isolation and biomass gasification supply.</p>
                </div>
              </div>
            </div>
          </div>
        )}

'''

if injection_point in content:
    content = content.replace(injection_point, new_blocks + injection_point)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully injected missing sub-tabs!")
else:
    print("Could not find injection point!")

