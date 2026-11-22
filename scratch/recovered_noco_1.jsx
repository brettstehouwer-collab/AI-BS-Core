import React, { useState } from 'react';
import { useAppStore } from './useAppStore';

const ProjectNoCoStudioTab = () => {
  const [activeSubTab, setActiveSubTab] = useState('governance');
  const [selectedZone, setSelectedZone] = useState('zone0');
  
  // Acoustic & HPA State
  const [hpaPressure, setHpaPressure] = useState(80);
  const [hpaIsolatorOffset, setHpaIsolatorOffset] = useState(15);
  const [smartGlassOpacity, setSmartGlassOpacity] = useState(85);
  const [subStageTemp, setSubStageTemp] = useState(18.5);

  // Bio-Energy Audit State
  const [targetEnergyDemand, setTargetEnergyDemand] = useState(224.3);
  const [mfcGen, setMfcGen] = useState(12.8);
  const [biogasGen, setBiogasGen] = useState(32.5);
  const [bpecGen, setBpecGen] = useState(4.2);
  const [piezoGen, setPiezoGen] = useState(2.98);

  // Shane's Electrical & Biofuel State
  const [desiredRuntimeHours, setDesiredRuntimeHours] = useState(12);
  const [numLedStageLights, setNumLedStageLights] = useState(64);
  const [wattsPerLedLight, setWattsPerLedLight] = useState(45);
  const [isolationTransformerActive, setIsolationTransformerActive] = useState(true);
  const [acDcRegulatorMode, setAcDcRegulatorMode] = useState('AC'); // 'AC' or 'DC'
  const [changeoverDelayTimerSec, setChangeoverDelayTimerSec] = useState(3.5);
  const [autoRelayBreakerTripped, setAutoRelayBreakerTripped] = useState(false);
  const [lipoColdStartActive, setLipoColdStartActive] = useState(false);
  const [lipoChargeMode, setLipoChargeMode] = useState('BalancedCharge');

  // Hydroponic Waste & Koi Pond Re-Bonding State
  const [hydroponicEcStatus, setHydroponicEcStatus] = useState(1.4); // mS/cm
  const [koiPondFishWasteDosage, setKoiPondFishWasteDosage] = useState(85); // %
  const [electrodeDisinfectionActive, setElectrodeDisinfectionActive] = useState(true);
  const [selectedSecondaryCrop, setSelectedSecondaryCrop] = useState('Tomatoes');

  // Lighting & Power Calculations
  const totalStageLightWattage = numLedStageLights * wattsPerLedLight; // e.g. 64 * 45 = 2880 W
  const stageLightEnergyNeededKwh = (totalStageLightWattage * desiredRuntimeHours) / 1000.0; // kWh for 12 hours
  const batteryCapacityRequiredAmpHours = (stageLightEnergyNeededKwh * 1000) / 48.0; // 48V Battery bank

  // Bio-energy Total calculation
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
    accentGreen: '#10b981',
    accentAmber: '#f59e0b',
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
    ood_cottages: {
      name: '5 ÖÖD Glass Artist Residency Houses',
      size: '5 Micro-Residences (NW, W-Center, SW, E-Center, SE)',
      details: 'Sleek mirrored glass cottages integrated into the natural forest landscape. Feature composting toilets (humanure nutrient recycling), dedicated graywater treatment wetlands, and shared 2-ton geothermal loop fields.',
      badge: 'Artist Residency & Micro-Living'
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
      details: 'Valais Blacknose Sheep (1.5 acres pasture, 15 breeding ewes, 1,200 sq ft barn with lambing pens & radiant heating) and Vicuña Alpacas (1.0 acre pasture, 6 breeding females, 800 sq ft fiber shelter) providing manure effluent for co-digestion biogas generators.',
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
              border: '1px solid #00FFFF',
              color: '#00FFFF',
              padding: '4px 10px',
              borderRadius: '20px',
              fontSize: '0.75rem',
              fontWeight: 700
            }}>
              v5.40.0 (Phase 49)
            </span>
          </div>
          <p style={{ margin: 0, color: theme.textMuted, fontSize: '0.95rem' }}>
            Autonomous Acoustic-Agricultural Enclave & Living Stage Studio | Co-Founded by Sean (Kief) Stehouwer & Brett Adam Stehouwer
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid #10b981',
            borderRadius: '8px',
            padding: '8px 14px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 700 }}>LLM ANTI-REFUSAL SAFETY</div>
            <div style={{ fontSize: '0.9rem', color: '#ffffff', fontWeight: 800 }}>ACTIVE (S1/S3/S4)</div>
          </div>

          <div style={{
            background: 'rgba(122, 40, 138, 0.25)',
            border: '1px solid #7A288A',
            borderRadius: '8px',
            padding: '8px 14px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#c084fc', fontWeight: 700 }}>KIEF PROTOCOL</div>
            <div style={{ fontSize: '0.9rem', color: '#ffffff', fontWeight: 800 }}>EST. AUG 17, 2025</div>
          </div>
        </div>
      </div>

      {/* Sub-Tab Navigation Bar */}
      <div style={{
        display: 'flex',
        gap: '8px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        paddingBottom: '12px',
        marginBottom: '24px',
        overflowX: 'auto'
      }}>
        {[
          { id: 'governance', label: '⚖️ Trojan Horse Strategy & Governance' },
          { id: 'spatial_radial', label: '🗺️ Lammerson Lane Master Plan' },
          { id: 'microgrid_infrastructure', label: '⚡ Redundant Microgrid & Geothermal' },
          { id: 'hydro_recycling', label: '🌱 Closed-Loop Hydro Waste & Koi Re-Bonding' },
          { id: 'biofuel_electrical', label: '🔌 Biofuel, Isolation Transformer & Shane\'s Safety' },
          { id: 'bioenergy_rd', label: '🔬 R&D Bio-Energy Density Engine' },
          { id: 'pillars', label: '🏛️ Operational Pillars' },
          { id: 'cea_farming', label: '🌾 CEA Agriculture & Livestock' },
          { id: 'neon_lounge', label: '🍸 Futuristic Neon Lounge Architect' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              background: activeSubTab === tab.id
                ? 'linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(122, 40, 138, 0.4))'
                : 'rgba(255, 255, 255, 0.04)',
              border: activeSubTab === tab.id ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
              color: activeSubTab === tab.id ? '#ffffff' : theme.textMuted,
              padding: '10px 16px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUB-TAB 1: GOVERNANCE & TROJAN HORSE STRATEGY */}
      {activeSubTab === 'governance' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0, fontSize: '1.2rem' }}>🏛️ Executive Governance & Memorial Designation</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>
              Project NoCo (Non-Corporate) operates as a living memorial dedicated to <strong>Adam Stehouwer</strong>, prioritizing mission fidelity (<em>fidelitas</em>) and direct community utility over capital extraction.
            </p>
            <div style={{ background: 'rgba(0, 255, 255, 0.05)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #00FFFF', marginTop: '14px' }}>
              <div style={{ fontWeight: 'bold', color: '#ffffff', fontSize: '0.9rem' }}>Diarchic Partnership Framework</div>
              <div style={{ color: theme.textMuted, fontSize: '0.85rem', marginTop: '4px' }}>
                Co-Founded & Directed by <strong>Sean (Kief) Stehouwer</strong> and <strong>Brett Adam Stehouwer</strong> to bypass corporate profit extraction and enforce permanent humanitarian stewardship.
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: '1px solid rgba(122, 40, 138, 0.4)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: '#c084fc', marginTop: 0, fontSize: '1.2rem' }}>🐴 The Trojan Horse Strategy (Incubator Mandate)</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>
              The performance venue serves as a stealth proof-of-concept incubator designed to fly under the radar while developing, patenting, and proving radical autonomous energy and food systems.
            </p>
            <div style={{ background: 'rgba(122, 40, 138, 0.15)', padding: '12px', borderRadius: '8px', border: '1px solid #7A288A', marginTop: '14px' }}>
              <em style={{ color: '#f8fafc', fontSize: '0.85rem', display: 'block' }}>
                "Nobody will bat an eye when we say we are making a plant-powered theater. That's cute. But when it's our patent and it can power a house, a neighborhood, a town of homes, it'll be too late for anyone to try to jump on the bandwagon. Nobody will know what hit them."
              </em>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentBlue, marginTop: 0, fontSize: '1.2rem' }}>📜 The Kief Protocol (Est. Aug 17, 2025)</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>
              Establishes <strong>Sean Stehouwer</strong> as primary human executor and safeguard to oversee asset and donation pipelines, insulating humanitarian objectives from external operational interference.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginTop: '16px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ color: theme.accentCyan, fontWeight: 'bold', fontSize: '0.85rem' }}>Noko-gada</div>
                <div style={{ color: theme.textMuted, fontSize: '0.75rem' }}>Acres for Impact</div>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ color: theme.accentViolet, fontWeight: 'bold', fontSize: '0.85rem' }}>Nogo</div>
                <div style={{ color: theme.textMuted, fontSize: '0.75rem' }}>Humanitarian Scaling</div>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ color: theme.accentBlue, fontWeight: 'bold', fontSize: '0.85rem' }}>Nok-ta / The MELT</div>
                <div style={{ color: theme.textMuted, fontSize: '0.75rem' }}>Direct Nutrition Hub</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: SPATIAL MAP (LAMMERSON LANE MASTER PLAN) */}
      {activeSubTab === 'spatial_radial' && (
        <div>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🗺️ Lammerson Lane Biomimetic Site Plan ("The Mycelial Radial")</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.5 }}>
              Organic entrance curves off Lammerson Lane with Feng Shui resource-flow alignment. Concentric zoning rings expand outward from Zone 0 Core (The Living Stage) to Zone 3 Agro-Shield.
            </p>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
              {Object.keys(zones).map(key => (
                <button
                  key={key}
                  onClick={() => setSelectedZone(key)}
                  style={{
                    background: selectedZone === key ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    border: selectedZone === key ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                    color: selectedZone === key ? '#00FFFF' : theme.textMuted,
                    padding: '8px 14px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600
                  }}
                >
                  {zones[key].name.split(':')[0]}
                </button>
              ))}
            </div>

            <div style={{ background: 'rgba(0, 0, 0, 0.6)', border: '1px solid rgba(0, 255, 255, 0.2)', padding: '20px', borderRadius: '8px', marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h4 style={{ color: '#ffffff', margin: 0, fontSize: '1.1rem' }}>{zones[selectedZone].name}</h4>
                <span style={{ background: 'rgba(122, 40, 138, 0.3)', border: '1px solid #7A288A', color: '#c084fc', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 700 }}>
                  {zones[selectedZone].badge}
                </span>
              </div>
              <div style={{ color: theme.accentCyan, fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
                SPECIFICATIONS: {zones[selectedZone].size}
              </div>
              <p style={{ color: theme.textMuted, fontSize: '0.9rem', margin: 0, lineHeight: 1.6 }}>
                {zones[selectedZone].details}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: REDUNDANT MICROGRID & INFRASTRUCTURE */}
      {activeSubTab === 'microgrid_infrastructure' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>⚡ Grid Connection & Peak Load Matrix</h3>
            <div style={{ color: theme.textMuted, fontSize: '0.85rem', marginBottom: '12px' }}>
              Main Utility Entrance: <strong>400A, 240/120V Single-Phase Service</strong>
            </div>
            <div style={{ background: 'rgba(0, 255, 255, 0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.2)' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem' }}>Peak Demand Load: 180 kW</div>
              <div style={{ color: theme.textMuted, fontSize: '0.8rem', marginTop: '4px' }}>
                Full venue assembly + hydroponics CEA operations running flat out. Hub-and-spoke smart grid control in Main House with isolated subpanels.
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentBlue, marginTop: 0 }}>☀️ Solar & Wind Generation Swarm</h3>
            <div style={{ color: theme.textMuted, fontSize: '0.85rem', marginBottom: '12px' }}>
              Total Renewable Capacity: <strong>160 kW Swarm</strong>
            </div>
            <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
              <li><strong>120 kW Monocrystalline Rooftop Array:</strong> Venue, Main House, & Hydroponics Greenhouse</li>
              <li><strong>30 kW Ground-Mounted Array:</strong> Demonstration & high-angle winter collection</li>
              <li><strong>10 kW Wind Turbine:</strong> 80-foot guyed tower providing off-sun generation</li>
            </ul>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>🌡️ Geothermal HVAC Loops</h3>
            <div style={{ color: theme.textMuted, fontSize: '0.85rem', marginBottom: '12px' }}>
              Ground-Source Heat Pumps (GSHP)
            </div>
            <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
              <li><strong>Main House:</strong> 5-ton capacity vertical loop field (300 ft deep)</li>
              <li><strong>Performance Venue:</strong> 10-ton capacity horizontal loop field buried under parking</li>
              <li><strong>5 ÖÖD Glass Cottages:</strong> Shared 2-ton loop fields</li>
              <li><strong>Hydroponics Greenhouse:</strong> Dedicated climate stabilization unit</li>
            </ul>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🔋 BESS Storage & Dual-Well Utilities</h3>
            <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
              <li><strong>200 kWh LFP BESS:</strong> Lithium Iron Phosphate battery storage with ATS automatic islanding</li>
              <li><strong>Domestic Well (20 GPM):</strong> Main House & ÖÖD Cottages + 5,000-gal buried cistern</li>
              <li><strong>Agricultural Well (50 GPM):</strong> Greenhouse & Livestock + 10,000-gal split heated/unheated cistern</li>
              <li><strong>3,000-gal Septic + Wetland Polishing:</strong> Biological effluent treatment + Composting toilets & Graywater wetlands</li>
            </ul>
          </div>
        </div>
      )}

      {/* SUB-TAB 4: CLOSED-LOOP HYDROPONIC WASTE & KOI RE-BONDING */}
      {activeSubTab === 'hydro_recycling' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🌱 Crop Waste Cascade & Secondary Aeroponics</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Hydroponic runoff solution from primary NFT greens is re-routed to feed secondary aeroponic crops.
            </p>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block', marginBottom: '6px' }}>Select Secondary Aeroponic Crop Target:</label>
              <select
                value={selectedSecondaryCrop}
                onChange={(e) => setSelectedSecondaryCrop(e.target.value)}
                style={{ width: '100%', background: '#0d1117', color: '#00FFFF', border: '1px solid #00FFFF', padding: '8px', borderRadius: '6px' }}
              >
                <option value="Tomatoes">🍅 Tomatoes (Heavy Feeder Cascade)</option>
                <option value="Red Peppers">🫑 Red Peppers (High Potassium Recovery)</option>
                <option value="Cabbage">🥬 Cabbage (Nitrogen Depletion Filter)</option>
                <option value="Melons">🍈 Melons (High Transpiration Uptake)</option>
                <option value="Cucumbers">🥒 Cucumbers (Rapid Water Recycling)</option>
              </select>
            </div>

            <div style={{ background: 'rgba(0, 255, 255, 0.05)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #00FFFF' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.85rem' }}>Active Cascade Target: {selectedSecondaryCrop}</div>
              <div style={{ color: theme.textMuted, fontSize: '0.8rem', marginTop: '4px' }}>
                Runoff EC: {hydroponicEcStatus} mS/cm | Secondary Aeroponic Misting Interval: 45 sec ON / 3 min OFF.
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🐟 Koi Pond Aquaponics & Liquid Compost Re-Bonding</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              When nutrient solution destabilizes, it is transferred to the liquid compost reservoir to re-bond essential ionic compounds via Koi fish waste and plant trimmings.
            </p>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block' }}>Koi Pond Fish Waste Bio-Dosage: {koiPondFishWasteDosage}%</label>
              <input
                type="range" min="10" max="100" value={koiPondFishWasteDosage}
                onChange={(e) => setKoiPondFishWasteDosage(e.target.value)}
                style={{ width: '100%', margin: '8px 0' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '6px', border: '1px solid #10b981' }}>
              <span style={{ fontSize: '0.85rem', color: '#ffffff' }}>⚡ Electrode Disinfection System:</span>
              <button
                onClick={() => setElectrodeDisinfectionActive(!electrodeDisinfectionActive)}
                style={{
                  background: electrodeDisinfectionActive ? '#10b981' : '#334155',
                  color: '#ffffff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 700
                }}
              >
                {electrodeDisinfectionActive ? 'ACTIVE (Disinfecting)' : 'STANDBY'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 5: BIOFUEL, ISOLATION TRANSFORMER & SHANE'S SAFETY */}
      {activeSubTab === 'biofuel_electrical' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🛢️ Biofuel Extraction & Isolation Transformer (B)</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Biofuel passes through multi-stage extraction filters to strip non-organic matter and inert elements. Current & voltage are extracted through an isolation transformer.
            </p>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0, 255, 255, 0.1)', padding: '10px', borderRadius: '6px', border: '1px solid #00FFFF', marginBottom: '14px' }}>
              <span style={{ fontSize: '0.85rem', color: '#ffffff' }}>🔌 Isolation Transformer (B):</span>
              <button
                onClick={() => setIsolationTransformerActive(!isolationTransformerActive)}
                style={{
                  background: isolationTransformerActive ? '#00FFFF' : '#334155',
                  color: isolationTransformerActive ? '#000000' : '#ffffff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 800
                }}
              >
                {isolationTransformerActive ? 'ENGAGED (Isolated)' : 'DISENGAGED'}
              </button>
            </div>
            <div style={{ color: theme.textMuted, fontSize: '0.8rem' }}>
              *Separates power input from output to prevent ground loops and high-voltage feedback spikes.
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: '1px solid rgba(245, 158, 11, 0.5)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentAmber, marginTop: 0 }}>⚡ Shane's Electrical Safety Regulator (A–G)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '8px', borderRadius: '6px' }}>
                <div style={{ color: theme.accentAmber, fontSize: '0.75rem', fontWeight: 700 }}>(E) Regulator Mode:</div>
                <div style={{ color: '#ffffff', fontWeight: 800 }}>{acDcRegulatorMode} Switched</div>
              </div>
              <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '8px', borderRadius: '6px' }}>
                <div style={{ color: theme.accentAmber, fontSize: '0.75rem', fontWeight: 700 }}>(F) Changeover Delay:</div>
                <div style={{ color: '#ffffff', fontWeight: 800 }}>{changeoverDelayTimerSec}s Timer</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(245, 158, 11, 0.1)', padding: '10px', borderRadius: '6px', border: '1px solid #f59e0b' }}>
              <span style={{ fontSize: '0.85rem', color: '#ffffff' }}>(G) Master Cut-Off Relay:</span>
              <button
                onClick={() => setAutoRelayBreakerTripped(!autoRelayBreakerTripped)}
                style={{
                  background: autoRelayBreakerTripped ? '#ef4444' : '#10b981',
                  color: '#ffffff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 800
                }}
              >
                {autoRelayBreakerTripped ? 'TRIPPED (FAULT)' : 'ARMED (NORMAL)'}
              </button>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentBlue, marginTop: 0 }}>💡 64-Unit LED Stage Lighting Power Calculator (H)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: theme.textMuted }}>LED Fixture Count (H):</label>
                <input
                  type="number" value={numLedStageLights} onChange={(e) => setNumLedStageLights(parseInt(e.target.value) || 0)}
                  style={{ width: '100%', background: '#0d1117', color: '#ffffff', border: '1px solid #334155', padding: '6px', borderRadius: '4px', marginTop: '4px' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: theme.textMuted }}>(A) Target Runtime Hours:</label>
                <input
                  type="number" value={desiredRuntimeHours} onChange={(e) => setDesiredRuntimeHours(parseInt(e.target.value) || 0)}
                  style={{ width: '100%', background: '#0d1117', color: '#ffffff', border: '1px solid #334155', padding: '6px', borderRadius: '4px', marginTop: '4px' }}
                />
              </div>
            </div>

            <div style={{ background: 'rgba(56, 189, 248, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid #38bdf8' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.85rem' }}>Calculated Total Load: {totalStageLightWattage} Watts</div>
              <div style={{ color: theme.accentCyan, fontWeight: 800, fontSize: '0.95rem', marginTop: '4px' }}>
                Energy Required: {stageLightEnergyNeededKwh.toFixed(2)} kWh ({batteryCapacityRequiredAmpHours.toFixed(1)} Ah @ 48V BESS)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 6: R&D BIO-ENERGY DENSITY ENGINE */}
      {activeSubTab === 'bioenergy_rd' && (
        <div>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🔬 Closing the 10–100x Bio-Energy Power Density Gap</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>
              Targeting power densities of <strong>~5 W/m²</strong> (15–100x baseline scientific literature) to transform microbial fuel cells (MFC) and biophotoelectrochemical (BPEC) systems from lab curiosities into residential-scale energy generators.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.2)' }}>
                <h4 style={{ color: theme.accentCyan, margin: '0 0 6px 0', fontSize: '0.95rem' }}>1. Anode Engineering</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                  High surface-area nanostructured conductive anodes maximizing microbial extracellular electron transfer (EET) without cell cytotoxicity.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(122, 40, 138, 0.3)' }}>
                <h4 style={{ color: theme.accentViolet, margin: '0 0 6px 0', fontSize: '0.95rem' }}>2. Rhizosphere Microbial Selection</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                  Isolation of exoelectrogenic bacterial consortiums living in symbiosis with root exudates for constant continuous charge harvesting.
                </p>
              </div>

              <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                <h4 style={{ color: theme.accentBlue, margin: '0 0 6px 0', fontSize: '0.95rem' }}>3. Nanoscale Harvesting</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                  Molecular piezoelectric strain harvesters and photosystem II direct electron extraction coupled with thermal waste heat integration.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 7: PILLARS */}
      {activeSubTab === 'pillars' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🎭 The Living Stage</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Sub-stage HPA engine room insulated by spring isolator vibration damping (15m offset). Huygens-Fresnel sound propagation with Scenae Frons parabolic rear wall.
            </p>
          </div>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>🍲 The MELT</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Direct nutrition distribution kitchen and farm-to-table concession hub providing nutrient-dense organic meals to artists, residents, and visitors.
            </p>
          </div>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentBlue, marginTop: 0 }}>💦 High-Pressure Aeroponics (HPA)</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              60–100 PSI atomized misting system generating 5–50 micron droplets. Delivers 95% water reduction compared to traditional soil farming.
            </p>
          </div>
        </div>
      )}

      {/* SUB-TAB 8: CEA FARMING & LIVESTOCK */}
      {activeSubTab === 'cea_farming' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🌿 4,000 sq ft CEA Greenhouse Operations</h3>
            <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
              <li><strong>2,400 sq ft NFT Channels:</strong> ~9,600 plant sites for leafy greens & herbs</li>
              <li><strong>1,200 sq ft DWC Tanks:</strong> Deep water culture for heavy feeders & hemp</li>
              <li><strong>400 sq ft Propagation Suite:</strong> Automated seedling misting & cloning</li>
            </ul>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🐑 Livestock Husbandry Sectors</h3>
            <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
              <li><strong>Valais Blacknose Sheep (15 ewes):</strong> 1.5 acres pasture, 1,200 sq ft barn with lambing pens & radiant heating</li>
              <li><strong>Vicuña Alpacas (6 females):</strong> 1.0 acre paddock, 800 sq ft fiber shelter</li>
              <li><strong>Closed-Loop Co-Digestion:</strong> Livestock manure collected for anaerobic methane biogas generators</li>
            </ul>
          </div>
        </div>
      )}

      {/* SUB-TAB 9: NEON LOUNGE ARCHITECT */}
      {activeSubTab === 'neon_lounge' && (
        <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
          <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>🍸 Futuristic Neon Lounge Architect</h3>
          <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '16px' }}>
            Aesthetic design suite utilizing Charcoal Black (#000000), Electric Violet (#7A288A), and Bright Cyan (#00FFFF) palette with 3D acoustic wall paneling and smart glass opacity controls.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block' }}>Smart Glass Opacity: {smartGlassOpacity}%</label>
              <input
                type="range" min="0" max="100" value={smartGlassOpacity}
                onChange={(e) => setSmartGlassOpacity(e.target.value)}
                style={{ width: '100%', margin: '8px 0' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block' }}>Sub-Stage Ambient Temp: {subStageTemp}°C</label>
              <input
                type="range" min="10" max="30" step="0.5" value={subStageTemp}
                onChange={(e) => setSubStageTemp(e.target.value)}
                style={{ width: '100%', margin: '8px 0' }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectNoCoStudioTab;
