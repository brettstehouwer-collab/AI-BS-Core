import React, { useState } from 'react';
import { useAppStore } from './useAppStore';

const ProjectNoCoStudioTab = () => {
  const [activeSubTab, setActiveSubTab] = useState('governance');
  const [selectedZone, setSelectedZone] = useState('zone0');
  const [hpaPressure, setHpaPressure] = useState(80);
  const [hpaIsolatorOffset, setHpaIsolatorOffset] = useState(15);
  const [smartGlassOpacity, setSmartGlassOpacity] = useState(85);
  const [subStageTemp, setSubStageTemp] = useState(18.5);
  const [targetEnergyDemand, setTargetEnergyDemand] = useState(224.3);
  const [mfcGen, setMfcGen] = useState(12.8);
  const [biogasGen, setBiogasGen] = useState(32.5);
  const [bpecGen, setBpecGen] = useState(4.2);
  const [piezoGen, setPiezoGen] = useState(2.98);

  const calculatedBioTotal = (parseFloat(mfcGen) + parseFloat(biogasGen) + parseFloat(bpecGen) + parseFloat(piezoGen)).toFixed(2);
  const energyDeficit = (parseFloat(targetEnergyDemand) - parseFloat(calculatedBioTotal)).toFixed(2);

  // Design Tokens
  const theme = {
    bg: '#000000',
    cardBg: 'rgba(13, 17, 23, 0.95)',
    border: '1px solid rgba(0, 255, 255, 0.25)',
    accentCyan: '#00FFFF',
    accentViolet: '#7A288A',
    accentBlue: '#38bdf8',
    textMuted: '#94a3b8',
    textLight: '#f8fafc'
  };

  const zones = {
    zone0: {
      name: 'Zone 0 (The Core): "The Living Stage" Amphitheater',
      size: '3,000 sq ft base footprint | 150 - 1,500 Capacity',
      details: 'The central acoustic heartbeat of the enclave. Built with excavated bio-morphic concrete seating, root-roof vine lattice (Hops/Wisteria) for solar diffusion, and live foliage acoustic dampening to eliminate slap-back echo.',
      badge: 'Core Performance & Assembly'
    },
    zone1: {
      name: 'Zone 1 (Inner Ring): "The Green Rooms"',
      size: 'High-Yield Nursery & Artist Prep Suites',
      details: 'Glass-walled prep rooms that double as high-yield vertical nurseries. Utilizes natural overhead sunlight and recirculating nutrient mists for immediate farm-to-artist nourishment.',
      badge: 'Artist Prep & CEA Nurseries'
    },
    zone2: {
      name: 'Zone 2 (Residential Halo): Connected Tech-Earthships',
      size: 'Continuous Housing Ring & Sound Lock Corridor',
      details: 'Continuous rammed-earth North walls (thermal mass) and south-facing triple-pane electrochromic smart glass facing inward toward the stage. Features sound-lock entries and ring-main utility trenching.',
      badge: 'Acoustic Barrier & Living Enclave'
    },
    zone3: {
      name: 'Zone 3 (Agro-Shield): Biomass & Privacy Perimeter',
      size: 'Timber Bamboo, Corn Gasifier Feedstock, Hemp',
      details: 'Dense planting barrier providing physical privacy from the outside world while generating biomass for anaerobic biogas gasification and localized manufacturing.',
      badge: 'Privacy Barrier & Biomass Supply'
    },
    livestock: {
      name: 'Livestock Sectors: Valais Blacknose & Vicuña Alpacas',
      size: '2.5 Acres Pasture | 2,000 sq ft Barn Structures',
      details: 'Valais Blacknose Sheep (1.5 acres pasture, 1,200 sq ft barn with lambing pens) and Vicuña Alpacas (1.0 acre pasture, 800 sq ft fiber shelter) providing manure effluent for co-digestion biogas generators.',
      badge: 'Effluent & Fiber Co-Gen'
    },
    foh: {
      name: 'Front of House (FOH) Tower (6 o\'clock Position)',
      size: '3-Story Operational Control Gateway',
      details: 'Operated by Sean Stehouwer. Level 1: Farm Concessions (distribution from The MELT). Level 2: FOH Control Room (Lighting, Audio, Video logic). Level 3: Crow\'s Nest (VIP & Donor Deck).',
      badge: 'System Control & Gateway'
    }
  };

  return (
    <div style={{
      background: theme.bg,
      color: theme.textLight,
      minHeight: '100vh',
      padding: '20px',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(122, 40, 138, 0.3) 0%, rgba(0, 255, 255, 0.15) 100%)',
        border: theme.border,
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 0 30px rgba(0, 255, 255, 0.15)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ fontSize: '1.8rem' }}>🏛️</span>
            <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 800, color: '#ffffff', letterSpacing: '0.5px' }}>
              Project NoCo & "The Living Stage" Master Studio
            </h1>
            <span style={{
              background: 'rgba(0, 255, 255, 0.15)',
              color: theme.accentCyan,
              border: '1px solid #00ffff',
              borderRadius: '20px',
              padding: '2px 10px',
              fontSize: '0.75rem',
              fontWeight: 700
            }}>
              v5.39.0 Active
            </span>
          </div>
          <p style={{ margin: 0, color: theme.textMuted, fontSize: '0.92rem', maxWidth: '850px' }}>
            Non-Corporate Philanthropic Enclave & Autonomous Acoustic-Agricultural Infrastructure. Directed by <strong>Sean (Kief) Stehouwer</strong> and <strong>Brett Adam Stehouwer</strong> in living memory of <strong>Adam Stehouwer</strong>.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',
            color: '#34d399',
            border: '1px solid #10b981',
            borderRadius: '6px',
            padding: '4px 12px',
            fontSize: '0.78rem',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span>🛡️ Safety Filter Directive:</span>
            <span>Refusal Interceptor Active</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            The Kief Protocol (Est. Aug 17, 2025) Enforced
          </div>
        </div>
      </div>

      {/* Sub-Tab Navigation Bar */}
      <div style={{
        display: 'flex',
        gap: '8px',
        overflowX: 'auto',
        paddingBottom: '12px',
        marginBottom: '20px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        {[
          { id: 'governance', label: '⚖️ Executive Governance & Protocol', badge: 'diarchy' },
          { id: 'pillars', label: '🏛️ Operational Pillars', badge: '5 pillars' },
          { id: 'spatial_radial', label: '🗺️ "The Mycelial Radial" Spatial Map', badge: '4 zones' },
          { id: 'acoustic_stage', label: '🎭 "The Living Stage" Acoustic Simulator', badge: 'Huygens-Fresnel' },
          { id: 'cea_farming', label: '🌱 CEA Agriculture & Aeroponics', badge: 'HPA / NFT / DWC' },
          { id: 'energy_audit', label: '⚡ Bio-Energy & Discrepancy Auditor', badge: '224.3 kWh' },
          { id: 'neon_lounge', label: '🍸 Futuristic Neon Lounge Architect', badge: 'Aesthetics' }
        ].map(tab => {
          const isActive = activeSubTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              style={{
                background: isActive ? 'linear-gradient(135deg, rgba(122, 40, 138, 0.5), rgba(0, 255, 255, 0.25))' : 'rgba(15, 23, 42, 0.6)',
                color: isActive ? '#ffffff' : theme.textMuted,
                border: isActive ? '1px solid #00ffff' : '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                padding: '10px 16px',
                cursor: 'pointer',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.85rem',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? '0 0 15px rgba(0, 255, 255, 0.2)' : 'none'
              }}
            >
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* SUB-TAB 1: EXECUTIVE GOVERNANCE & PROTOCOL */}
      {activeSubTab === 'governance' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentCyan, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>👥</span> Diarchic Partnership Framework
            </h3>
            <p style={{ fontSize: '0.88rem', color: theme.textMuted, lineHeight: 1.6 }}>
              Project NoCo operates as a joint diarchic partnership directed symmetrically by <strong>Sean (Kief) Stehouwer</strong> and <strong>Brett Adam Stehouwer</strong>. The management model bypasses corporate profit extraction to insulate humanitarian objectives.
            </p>
            <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)', marginTop: '12px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: theme.accentBlue, marginBottom: '4px' }}>
                🛡️ The Kief Protocol (Est. August 17, 2025)
              </div>
              <div style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
                Sean Stehouwer serves as primary executor and human safeguard overseeing land asset acquisition and donation pipelines, ensuring absolute fidelity to community distribution.
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentViolet, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🕊️</span> Memorial Designation
            </h3>
            <p style={{ fontSize: '0.88rem', color: theme.textMuted, lineHeight: 1.6 }}>
              NoCo operates as an active living testament dedicated to <strong>Adam Stehouwer</strong>. The operational ethos prioritizes <em>fidelitas</em> (loyalty to philanthropic mission) over capital accumulation.
            </p>
            <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)', marginTop: '12px' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f472b6', marginBottom: '4px' }}>
                🎯 Bifurcated Teleology
              </div>
              <div style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
                1. <strong>Nutrient Security:</strong> Vertical farming aeroponics eliminating food insecurity.<br />
                2. <strong>Communal Architecture:</strong> Unamplified acoustic amphitheater performance & assembly.
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentBlue, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>📖</span> Core Terminology Engine
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ padding: '10px', background: 'rgba(56, 189, 248, 0.08)', borderRadius: '6px', borderLeft: '3px solid #38bdf8' }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#ffffff' }}>Noko-gada</div>
                <div style={{ fontSize: '0.8rem', color: theme.textMuted }}>Permanent land acquisition strategy ("Acres for Impact").</div>
              </div>
              <div style={{ padding: '10px', background: 'rgba(168, 85, 247, 0.08)', borderRadius: '6px', borderLeft: '3px solid #a855f7' }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#ffffff' }}>Nogo</div>
                <div style={{ fontSize: '0.8rem', color: theme.textMuted }}>Localized humanitarian scaling and land philanthropy framework.</div>
              </div>
              <div style={{ padding: '10px', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
                <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#ffffff' }}>Nok-ta (The MELT)</div>
                <div style={{ fontSize: '0.8rem', color: theme.textMuted }}>Direct distribution protocol supplying high-density nutrition without retail markups.</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: OPERATIONAL PILLARS */}
      {activeSubTab === 'pillars' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {[
            {
              title: 'The Living Stage',
              icon: '🎭',
              mechanism: 'Amphitheater venue integrated with sub-stage agricultural HPA basement infrastructure.',
              objective: 'Facilitates unamplified acoustic performances, artistic laboratories, and community assembly.',
              color: '#00ffff'
            },
            {
              title: 'The MELT',
              icon: '🥗',
              mechanism: 'Systemic food donation protocol from vertical farming yield.',
              objective: 'Converts high-nutrient caloric yield to eliminate regional food insecurity within geographic radius.',
              color: '#34d399'
            },
            {
              title: 'High-Pressure Aeroponics (HPA)',
              icon: '🌿',
              mechanism: 'Root-zone nutrient misting at 60–100 PSI inside closed mist chambers.',
              objective: 'Delivers 10:1 water-to-biomass efficiency ratio while minimizing environmental footprint.',
              color: '#a78bfa'
            },
            {
              title: 'Acres for Impact',
              icon: '🌲',
              mechanism: 'Strategic land acquisition (site evaluations in NY and MI).',
              objective: 'Establishes permanent "Tech-Earthship" enclaves, Ööd artist studios, and agricultural assembly zones.',
              color: '#fbbf24'
            },
            {
              title: 'Closed-Loop Energy',
              icon: '⚡',
              mechanism: 'Anaerobic Digestion & Microbial Fuel Cells (MFCs).',
              objective: 'Recycles organic crop and livestock waste into biomethane (CH4) for microturbines and winter heating.',
              color: '#f472b6'
            }
          ].map((pillar, idx) => (
            <div key={idx} style={{
              background: theme.cardBg,
              border: `1px solid ${pillar.color}40`,
              borderRadius: '10px',
              padding: '18px',
              boxShadow: `0 4px 20px ${pillar.color}10`
            }}>
              <div style={{ fontSize: '1.8rem', marginBottom: '8px' }}>{pillar.icon}</div>
              <h4 style={{ margin: '0 0 8px 0', color: pillar.color, fontSize: '1.05rem' }}>{pillar.title}</h4>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '10px', fontWeight: 600 }}>
                Mechanism: {pillar.mechanism}
              </div>
              <div style={{ fontSize: '0.8rem', color: theme.textMuted, background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '6px' }}>
                🎯 <strong>Objective:</strong> {pillar.objective}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SUB-TAB 3: SPATIAL RADIAL MAP */}
      {activeSubTab === 'spatial_radial' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', color: theme.accentCyan }}>
              🗺️ "The Mycelial Radial" Concentric Layout Inspector
            </h3>
            <p style={{ fontSize: '0.85rem', color: theme.textMuted, marginBottom: '20px' }}>
              Select a zone on the spatial map to view its detailed architectural specifications, acoustic barriers, and agricultural functions:
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginBottom: '20px' }}>
              {Object.keys(zones).map(key => (
                <button
                  key={key}
                  onClick={() => setSelectedZone(key)}
                  style={{
                    background: selectedZone === key ? 'rgba(0, 255, 255, 0.2)' : 'rgba(15, 23, 42, 0.7)',
                    border: selectedZone === key ? '1px solid #00ffff' : '1px solid rgba(255,255,255,0.1)',
                    color: selectedZone === key ? '#ffffff' : theme.textMuted,
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontWeight: selectedZone === key ? 700 : 400,
                    fontSize: '0.82rem'
                  }}
                >
                  <div style={{ fontSize: '0.75rem', opacity: 0.8, textTransform: 'uppercase' }}>{zones[key].badge}</div>
                  <div style={{ color: selectedZone === key ? theme.accentCyan : '#ffffff', fontWeight: 700 }}>{key.toUpperCase()}</div>
                </button>
              ))}
            </div>

            {/* Selected Zone Card */}
            <div style={{ background: 'rgba(0,0,0,0.6)', border: '1px solid #00ffff', borderRadius: '8px', padding: '20px' }}>
              <div style={{ color: theme.accentCyan, fontWeight: 700, fontSize: '1.1rem', marginBottom: '4px' }}>
                {zones[selectedZone].name}
              </div>
              <div style={{ fontSize: '0.82rem', color: theme.accentBlue, marginBottom: '12px' }}>
                📐 {zones[selectedZone].size}
              </div>
              <p style={{ fontSize: '0.88rem', color: '#e2e8f0', lineHeight: 1.6, margin: 0 }}>
                {zones[selectedZone].details}
              </p>
            </div>
          </div>

          {/* FOH Tower Sidebar */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentViolet, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🎛️</span> FOH Control Tower
            </h3>
            <div style={{ fontSize: '0.8rem', color: theme.textMuted, marginBottom: '16px' }}>
              Positioned at the 6 o'clock mark of the residential ring. Directed by <strong>Sean Stehouwer</strong>.
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '12px', background: 'rgba(122, 40, 138, 0.15)', borderRadius: '6px', border: '1px solid #7A288A' }}>
                <div style={{ fontWeight: 700, color: '#f472b6', fontSize: '0.85rem' }}>Level 3: The Crow's Nest</div>
                <div style={{ fontSize: '0.8rem', color: theme.textMuted }}>VIP & Donor observation deck overlooking Zone 0.</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(56, 189, 248, 0.15)', borderRadius: '6px', border: '1px solid #38bdf8' }}>
                <div style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.85rem' }}>Level 2: FOH Control Room</div>
                <div style={{ fontSize: '0.8rem', color: theme.textMuted }}>Sean's Master Lighting, Audio, and Video operational logic console.</div>
              </div>
              <div style={{ padding: '12px', background: 'rgba(16, 185, 129, 0.15)', borderRadius: '6px', border: '1px solid #10b981' }}>
                <div style={{ fontWeight: 700, color: '#34d399', fontSize: '0.85rem' }}>Level 1: Public Concessions</div>
                <div style={{ fontSize: '0.8rem', color: theme.textMuted }}>Direct distribution of farm-to-table produce from The MELT.</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 4: ACOUSTIC & STAGE SIMULATOR */}
      {activeSubTab === 'acoustic_stage' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentCyan }}>
              🔊 Sub-Stage HPA Engine Room & Vibration Damping
            </h3>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', color: theme.textMuted, marginBottom: '6px' }}>
                HPA Pump Pressure Target: <strong>{hpaPressure} PSI</strong>
              </label>
              <input
                type="range"
                min="60"
                max="100"
                value={hpaPressure}
                onChange={(e) => setHpaPressure(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', color: theme.textMuted, marginBottom: '6px' }}>
                Spring Isolator Offset Distance: <strong>{hpaIsolatorOffset} Meters</strong>
              </label>
              <input
                type="range"
                min="5"
                max="30"
                value={hpaIsolatorOffset}
                onChange={(e) => setHpaIsolatorOffset(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px', fontSize: '0.82rem' }}>
              <div>🌊 <strong>Aqueous Reservoir Mass Damping:</strong> Sub-stage reservoir water mass absorbs low-frequency bass rumble.</div>
              <div style={{ marginTop: '6px' }}>💨 <strong>Plant Breath Climate Coupling:</strong> Cool, oxygenated root mist ({subStageTemp}°C) is piped up stage vents.</div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentViolet }}>
              🎼 Acoustic & Solar Alignment
            </h3>
            <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '0.85rem', color: theme.textMuted, lineHeight: 1.7 }}>
              <li><strong>Huygens-Fresnel Sound Propagation:</strong> Stage located at lowest topographical elevation for natural hemispherical vocal projection up audience rake.</li>
              <li><strong>Scenae Frons Rear Wall:</strong> Parabolic rammed-earth rear wall acts as a non-porous acoustic mirror redirecting sound forward.</li>
              <li><strong>The Root Roof Lattice:</strong> Cantilevered vine lattice (Hops/Wisteria) diffuses sunlight and breaks up standing acoustic slap-back echoes.</li>
              <li><strong>Solar/Wind Vector:</strong> Facing North-Northeast in MI/NY to eliminate performer solar glare while utilizing prevailing Southwesterly winds.</li>
            </ul>
          </div>
        </div>
      )}

      {/* SUB-TAB 5: CEA AGRICULTURE */}
      {activeSubTab === 'cea_farming' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '6px' }}>🌿</div>
            <h4 style={{ margin: '0 0 8px 0', color: theme.accentCyan }}>Aeroponics (HPA)</h4>
            <div style={{ fontSize: '0.8rem', color: theme.accentBlue, marginBottom: '8px' }}>Integrated Vertical Modules</div>
            <p style={{ fontSize: '0.82rem', color: theme.textMuted, margin: 0 }}>
              60–100 PSI mist-suspended root chambers reducing water consumption by 95% while accelerating root oxygen absorption.
            </p>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '6px' }}>🥬</div>
            <h4 style={{ margin: '0 0 8px 0', color: '#34d399' }}>Nutrient Film Technique (NFT)</h4>
            <div style={{ fontSize: '0.8rem', color: theme.accentBlue, marginBottom: '8px' }}>2,400 sq ft (~9,600 sites)</div>
            <p style={{ fontSize: '0.82rem', color: theme.textMuted, margin: 0 }}>
              Recirculating shallow nutrient streams designed for continuous high-density production of leafy greens, microgreens, and medicinal herbs.
            </p>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '6px' }}>🧪</div>
            <h4 style={{ margin: '0 0 8px 0', color: '#a78bfa' }}>Deep Water Culture (DWC)</h4>
            <div style={{ fontSize: '0.8rem', color: theme.accentBlue, marginBottom: '8px' }}>1,200 sq ft Submersion Tanks</div>
            <p style={{ fontSize: '0.82rem', color: theme.textMuted, margin: 0 }}>
              Aerated submersion tanks dedicated to high-biomass heavy-feeding crops (industrial hemp, fruiting crops) for gasifier feedstock.
            </p>
          </div>
        </div>
      )}

      {/* SUB-TAB 6: BIO-ENERGY & DISCREPANCY AUDITOR */}
      {activeSubTab === 'energy_audit' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', color: theme.accentCyan }}>
              ⚡ Bio-Energy Generation & Discrepancy Reconciliation Engine
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px' }}>
              <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: theme.textMuted }}>Microbial Fuel Cells (MFC)</div>
                <input type="number" step="0.1" value={mfcGen} onChange={(e) => setMfcGen(e.target.value)} style={{ width: '100%', background: '#0f172a', color: '#ffffff', border: '1px solid #334155', borderRadius: '4px', padding: '4px', marginTop: '4px' }} />
                <div style={{ fontSize: '0.7rem', color: '#38bdf8', marginTop: '4px' }}>kWh/day</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: theme.textMuted }}>Anaerobic Digestion (CH4)</div>
                <input type="number" step="0.1" value={biogasGen} onChange={(e) => setBiogasGen(e.target.value)} style={{ width: '100%', background: '#0f172a', color: '#ffffff', border: '1px solid #334155', borderRadius: '4px', padding: '4px', marginTop: '4px' }} />
                <div style={{ fontSize: '0.7rem', color: '#34d399', marginTop: '4px' }}>kWh/day</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: theme.textMuted }}>Bio-Photoelectrochemical (BPEC)</div>
                <input type="number" step="0.1" value={bpecGen} onChange={(e) => setBpecGen(e.target.value)} style={{ width: '100%', background: '#0f172a', color: '#ffffff', border: '1px solid #334155', borderRadius: '4px', padding: '4px', marginTop: '4px' }} />
                <div style={{ fontSize: '0.7rem', color: '#a78bfa', marginTop: '4px' }}>kWh/day</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.5)', padding: '12px', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.75rem', color: theme.textMuted }}>Piezoelectric Wind Strain</div>
                <input type="number" step="0.01" value={piezoGen} onChange={(e) => setPiezoGen(e.target.value)} style={{ width: '100%', background: '#0f172a', color: '#ffffff', border: '1px solid #334155', borderRadius: '4px', padding: '4px', marginTop: '4px' }} />
                <div style={{ fontSize: '0.7rem', color: '#fbbf24', marginTop: '4px' }}>kWh/day</div>
              </div>
            </div>

            {/* Reconciliation Audit Box */}
            <div style={{
              background: energyDeficit > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
              border: energyDeficit > 0 ? '1px solid #ef4444' : '1px solid #10b981',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', color: energyDeficit > 0 ? '#fca5a5' : '#6ee7b7', marginBottom: '6px' }}>
                🔍 Documented Energy Audit Discrepancy Analysis
              </div>
              <div style={{ fontSize: '0.85rem', color: '#f8fafc' }}>
                Current Bio-Generation Calculated Sum: <strong>{calculatedBioTotal} kWh/day</strong><br />
                Target Daily Summary Requirement: <strong>{targetEnergyDemand} kWh/day</strong><br />
                Reconciliation Deficit: <strong style={{ color: energyDeficit > 0 ? '#ef4444' : '#10b981' }}>{energyDeficit} kWh/day</strong>
              </div>
              <p style={{ fontSize: '0.8rem', color: theme.textMuted, margin: '8px 0 0 0' }}>
                Reconciliation Note: Power density gap (~5 W/m²) is bridged via biomethane microturbine peak shaving and battery storage buffer.
              </p>
            </div>
          </div>

          {/* Site Utilities Sidebar */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentViolet }}>💧 Site Utilities</h3>
            <div style={{ fontSize: '0.82rem', color: theme.textMuted, display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ padding: '10px', background: 'rgba(0,0,0,0.4)', borderRadius: '6px' }}>
                <strong>Domestic Well:</strong> 6-inch diameter, 20 GPM flow rate; 5,000-gallon buried cistern.
              </div>
              <div style={{ padding: '10px', background: 'rgba(0,0,0,0.4)', borderRadius: '6px' }}>
                <strong>Agricultural Well:</strong> 50 GPM flow rate; 10,000-gallon cistern with split heated/unheated zones.
              </div>
              <div style={{ padding: '10px', background: 'rgba(0,0,0,0.4)', borderRadius: '6px' }}>
                <strong>Electrical Grid:</strong> Hub-and-spoke configuration with Automatic Transfer Switches (ATS) for dynamic islanding.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 7: NEON LOUNGE ARCHITECT */}
      {activeSubTab === 'neon_lounge' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentCyan }}>
              🍸 Futuristic Neon Lounge Aesthetics
            </h3>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.82rem', color: theme.textMuted, marginBottom: '6px' }}>
                Smart-Tinting Glass Opacity: <strong>{smartGlassOpacity}%</strong>
              </label>
              <input
                type="range"
                min="10"
                max="100"
                value={smartGlassOpacity}
                onChange={(e) => setSmartGlassOpacity(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.82rem' }}>
              <div style={{ padding: '10px', background: 'rgba(122, 40, 138, 0.2)', borderRadius: '6px', borderLeft: '3px solid #7A288A' }}>
                <strong>Lighting Array:</strong> Baseboard LED strips (neon blue/purple), geometric hanging pendant lamps, backlit bar.
              </div>
              <div style={{ padding: '10px', background: 'rgba(0, 255, 255, 0.15)', borderRadius: '6px', borderLeft: '3px solid #00FFFF' }}>
                <strong>Space Planning:</strong> Open, pillarless main hall with glowing LED glass dance floor and concealed backstage service doors.
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', color: theme.accentViolet }}>
              🛠️ Structural & Finish Specifications
            </h3>
            <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '0.82rem', color: theme.textMuted, lineHeight: 1.8 }}>
              <li><strong>Stage & Boundaries:</strong> Hardwood or stone trim over dark polished concrete for structural durability.</li>
              <li><strong>Main Hall Flooring:</strong> Dark polished concrete (high durability, easy cleaning, clear reflection).</li>
              <li><strong>Acoustic Treatment:</strong> Textured 3D geometric wall panels wrapped in matte black vinyl for flutter echo reduction.</li>
              <li><strong>AV Integration:</strong> Concealed ceiling projectors, motorized drop-down screens, and recessed LED arrays.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectNoCoStudioTab;
