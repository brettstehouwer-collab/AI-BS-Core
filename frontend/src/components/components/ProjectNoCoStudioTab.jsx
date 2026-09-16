import React, { useState } from 'react';
import { useAppStore } from './useAppStore';
import TheatricalStageSwitch from './TheatricalStageSwitch.jsx';
import TheatricalMicClient from './TheatricalMicClient.jsx';

const ProjectNoCoStudioTab = () => {
  const [activeSubTab, setActiveSubTab] = useState('governance');
  const [selectedZone, setSelectedZone] = useState('zone0');
  const [activeRenderView, setActiveRenderView] = useState('view01');
  const [activeStructureCategory, setActiveStructureCategory] = useState('all');
  
  // Acoustic Engineering State
  const [glazingTiltAngle, setGlazingTiltAngle] = useState(6.0); // 5-7 deg recommended
  const [subwooferArrayMode, setSubwooferArrayMode] = useState('cardioid'); // 'cardioid' or 'end_fire'
  const [hpaPressure, setHpaPressure] = useState(80);
  const [hpaIsolatorOffset, setHpaIsolatorOffset] = useState(15);
  const [smartGlassOpacity, setSmartGlassOpacity] = useState(85);
  const [subStageTemp, setSubStageTemp] = useState(18.5);

  // Bio-Energy Audit & Reconciliation State
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

  // CapEx & Financial Calculators State (23-Acre Master Plan)
  const [landAcquisitionAcres, setLandAcquisitionAcres] = useState(23); // 23-acre master plan
  const [costPerAcre, setCostPerAcre] = useState(18500);
  const [buildingSqFtCost, setBuildingSqFtCost] = useState(145); // $/sq ft
  const [elecRateKwh, setElecRateKwh] = useState(0.16); // $/kWh
  const [solarSystemCost, setSolarSystemCost] = useState(185000); // 150 kW system
  const [geothermalSystemCost, setGeothermalSystemCost] = useState(95000);

  // CEA Crop Yield & Fiber Calculators State
  const [nftPricePerHead, setNftPricePerHead] = useState(3.50);
  const [sheepWoolPricePerLb, setSheepWoolPricePerLb] = useState(45.00);
  const [vicunaFiberPricePerKg, setVicunaFiberPricePerKg] = useState(450.00);

  // Operational Load Profile Scenarios State
  const [selectedScenario, setSelectedScenario] = useState('performance');
  const [performanceCountMonthly, setPerformanceCountMonthly] = useState(8);
  const [rehearsalCountMonthly, setRehearsalCountMonthly] = useState(16);
  const [maintenanceCountMonthly, setMaintenanceCountMonthly] = useState(6);

  // Ag Sensor Network Telemetry State
  const [sensorTemp, setSensorTemp] = useState(21.4); // °C
  const [sensorHumidity, setSensorHumidity] = useState(68); // %
  const [sensorSoilMoisture, setSensorSoilMoisture] = useState(82); // %
  const [sensorPh, setSensorPh] = useState(6.2);
  const [poultryCount, setPoultryCount] = useState(30);

  // Calculated CapEx & Payback Values
  const totalLandCost = landAcquisitionAcres * costPerAcre;
  const greenhouseCost = 4000 * buildingSqFtCost;
  const livingStageCost = 3000 * (buildingSqFtCost * 1.35);
  const totalEstimatedCapEx = totalLandCost + greenhouseCost + livingStageCost + solarSystemCost + geothermalSystemCost;

  // Annual Utility Savings & Payback
  const annualSolarGenKwh = 150 * 1350;
  const annualSolarElectricSavings = annualSolarGenKwh * elecRateKwh;
  const annualGeothermalHeatingSavings = 14500;
  const totalAnnualUtilitySavings = annualSolarElectricSavings + annualGeothermalHeatingSavings;
  const paybackPeriodYears = (totalEstimatedCapEx / (totalAnnualUtilitySavings > 0 ? totalAnnualUtilitySavings : 1)).toFixed(1);

  // CEA Harvest Yields & Revenue
  const annualNftGreensHeads = 9600 * 8.5;
  const annualNftRevenue = annualNftGreensHeads * nftPricePerHead;
  const annualSheepFleeceLbs = 15 * 11.5;
  const annualSheepFleeceRevenue = annualSheepFleeceLbs * sheepWoolPricePerLb;
  const annualVicunaFiberKg = (6 * 0.45);
  const annualVicunaFiberRevenue = annualVicunaFiberKg * vicunaFiberPricePerKg;
  const totalAnnualAgRevenue = annualNftRevenue + annualSheepFleeceRevenue + annualVicunaFiberRevenue;

  // The MELT Community Meal Equivalents
  const dailyFreeMealsSupported = Math.floor(annualNftGreensHeads / 365);

  // Operational Scenario Consumption Calculations
  const scenarioData = {
    performance: {
      name: '🎭 Performance Scenario (150 Occupants, 3 Hours)',
      occupancy: 150,
      durationHrs: 3,
      loads: { lighting: 8.0, sound: 1.5, hvac: 8.0, hydroponics: 2.5, misc: 1.0 },
      powerDemandKw: 21.0,
      energyKwh: 63.0,
      notes: 'Peak venue assembly with main PA sound, stage lighting rigs, and full HVAC.'
    },
    rehearsal: {
      name: '🎼 Rehearsal Scenario (20 Occupants, 4 Hours)',
      occupancy: 20,
      durationHrs: 4,
      loads: { lighting: 2.0, sound: 0.75, hvac: 3.0, hydroponics: 2.5, misc: 0.5 },
      powerDemandKw: 8.75,
      energyKwh: 35.0,
      notes: 'Cast & crew acoustic rehearsal with minimal PA reinforcement and moderate climate control.'
    },
    maintenance: {
      name: '🛠️ Maintenance Scenario (Minimal Occupancy, 8 Hours)',
      occupancy: 2,
      durationHrs: 8,
      loads: { lighting: 0.6, sound: 0.0, hvac: 1.5, hydroponics: 2.5, misc: 0.3 },
      powerDemandKw: 4.9,
      energyKwh: 39.2,
      notes: 'Off-show baseline status maintaining hydroponics environment and security sensors.'
    }
  };

  const monthlyTotalKwh = (
    (performanceCountMonthly * scenarioData.performance.energyKwh) +
    (rehearsalCountMonthly * scenarioData.rehearsal.energyKwh) +
    (maintenanceCountMonthly * scenarioData.maintenance.energyKwh)
  );
  const avgDailyKwh = (monthlyTotalKwh / 30.0).toFixed(1);

  // Phase III Render Views Data
  const renderViews = {
    view01: {
      title: 'VIEW 01 / 06: Aerial Overview — Full 23-Acre Campus',
      time: 'Golden Hour / Late Afternoon',
      imgSrc: '/noco_vector_aerial.png',
      details: 'Looking southeast across the full 23-acre NoCo Farms campus at golden hour in Ithaca, NY. Christmas tree grove cradles the family compound in the northwest. The glass hydroponic greenhouse catches the last light at center while Valais sheep graze in the western pasture ring.',
      badge: 'Master Aerial Campus'
    },
    view02: {
      title: 'VIEW 02 / 06: The Family Compound — 4-Unit ÖÖD Home Cluster',
      time: 'Early Morning Dawn',
      imgSrc: '/noco_vector_family_compound.png',
      details: 'Eye-level view from the central courtyard at dawn. Four ÖÖD pods arranged in a protective cluster tucked inside the Christmas fir canopy — the primary family unit opens toward southern sun exposure, anchored by a central stone fire ring and reflecting pool.',
      badge: 'Family Compound Sanctuary'
    },
    view03: {
      title: 'VIEW 03 / 06: The Living Stage — 4,000 SF Polycarbonate Greenhouse Stage',
      time: 'Evening Performance (Capacity 100–120)',
      imgSrc: '/noco_vector_greenhouse_stage.png',
      details: 'Interior view during a performance evening. Polycarbonate walls diffuse dusk daylight while purple LED grow lights illuminate living lettuce towers and hanging herb walls as dynamic stage scenery. Stage spots warm the central performance platform with "の NOCO FARMS" branding.',
      badge: 'Polycarbonate Living Stage'
    },
    view04_05: {
      title: 'VIEWS 04 & 05 / 06: Farm Life & Earth-Berm Outdoor Theater',
      time: 'Afternoon & Night Sky',
      imgSrc: '/noco_vector_sheep_and_theater.png',
      details: 'Left: Valais Blacknose sheep grazing below the timber-frame barn on a clear Finger Lakes afternoon. Right: Open-air earth-berm outdoor theater under a late-summer moon with fire torches flanking the stage and Christmas tree silhouettes framing the sky.',
      badge: 'Agritourism & Earth-Berm Theater'
    },
    view06: {
      title: 'VIEW 06 / 06: Artist Residency ÖÖD Pods — Winter Retreat',
      time: 'Deep Winter Evening (January Snowfall)',
      imgSrc: '/noco_vector_family_compound.png',
      details: 'Three artist residency ÖÖD pods in deep January snowfall in the NE sector. Large north-facing skylights of the center pod glow amber where a painter works by studio light. Snow-laden Christmas trees create the ultimate creative winter retreat stillness.',
      badge: 'Winter Retreat Residency'
    }
  };

  // Functionally Grouped Structure Matrix
  const structureMatrix = [
    { category: 'Performance & Creative', name: 'Performance Venue', spec: '150-Seat Capacity', area: 'Northern Sector', desc: 'Large curved roof building at top of property.' },
    { category: 'Performance & Creative', name: 'Rehearsal Space', spec: '1,200 sq ft', area: 'Southeastern Sector', desc: 'Music rehearsals and intimate 40-seat preview performances.' },
    { category: 'Performance & Creative', name: 'Recording Studio', spec: '800 sq ft', area: 'Southeastern Sector', desc: 'Floating-floor acoustic isolation with tracking & control rooms.' },
    { category: 'Performance & Creative', name: 'Costume & Set Workshop', spec: '1,500 sq ft', area: 'Southeastern Sector', desc: 'Shared textile, wardrobe tailoring, and set fabrication workshop.' },
    { category: 'Residential', name: 'Main House', spec: 'Central Hub', area: 'Center of Property', desc: 'Large rectangular glass building serving as central electrical distribution hub.' },
    { category: 'Residential', name: 'ÖÖD Glass Artist Residences', spec: '8 Pod Units', area: 'NW, West, SW, East', desc: 'Mirrored electrochromic glass cottages with composting toilets.' },
    { category: 'Agricultural', name: 'Hydroponics Greenhouse', spec: '4,000 sq ft', area: 'Eastern Sector', desc: 'Glass grid structure using NFT & DWC for leafy greens and herbs.' },
    { category: 'Agricultural', name: 'Sheep Pasture & Barn', spec: '1.5 Acres / 1,200 sq ft Barn', area: 'Western Sector', desc: '15 Valais Blacknose ewes with lambing pens & radiant heated floor.' },
    { category: 'Agricultural', name: 'Alpaca Paddock & Shelter', spec: '1.0 Acre / 800 sq ft Shelter', area: 'Southern Sector', desc: '6 breeding female Vicuña alpacas with open-sided fleece shelter.' },
    { category: 'Communal & Circulation', name: 'Fire Pit', spec: 'Concentric Stone Rings', area: 'Southwest of Main House', desc: 'Circular stone gathering fire ring anchored in courtyard.' },
    { category: 'Communal & Circulation', name: 'Entrance & Curved Pathways', spec: 'Feng Shui Alignment', area: 'Lammerson Lane Entrance', desc: 'Curved gravel/boardwalk paths preserving mature trees.' }
  ];

  // Bio-Energy Deficit Mathematical Reconciliation Calculations
  const calculatedBioSum = 52.48;
  const evapotranspirationCoolingCredit = -22.30;
  const solarWindBessBufferContribution = 149.52;
  const thermalWasteHeatRecycled = 44.60;
  const targetReconciledTarget = 224.3;

  // Lighting & Power Calculations
  const totalStageLightWattage = numLedStageLights * wattsPerLedLight;
  const stageLightEnergyNeededKwh = (totalStageLightWattage * desiredRuntimeHours) / 1000.0;
  const batteryCapacityRequiredAmpHours = (stageLightEnergyNeededKwh * 1000) / 48.0;

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
      name: '8 ÖÖD Mirror Houses & Studios Ring',
      size: '8 Pods (4 ÖÖD Mirror Houses + 4 ÖÖD Studios)',
      details: 'Sleek mirrored glass cottages integrated into the natural Finger Lakes forest landscape. Feature composting toilets (humanure nutrient recycling), dedicated graywater treatment wetlands, and shared 2-ton geothermal loop fields.',
      badge: 'Artist Residency & Creative Production'
    },
    zone3: {
      name: 'Zone 3 (Agro-Shield): Biomass & Privacy Perimeter',
      size: 'Christmas Tree Grove, Timber Bamboo, Hemp',
      details: 'Dense Christmas tree fir grove and biomass perimeter providing natural privacy from the outside world while cradling the family compound in the northwest.',
      badge: 'Privacy Barrier & Fir Grove'
    },
    livestock: {
      name: 'Livestock Sectors: Valais Sheep, Alpacas & Poultry',
      size: '2.5 Acres Pasture | 2,000 sq ft Barn Structures',
      details: 'Valais Blacknose Sheep (1.5 acres pasture, 15 breeding ewes, 1,200 sq ft barn with lambing pens & radiant floor heating) and Vicuña Alpacas (1.0 acre pasture, 6 breeding females, 800 sq ft fiber shelter) plus 30 free-range chickens/ducks providing manure effluent and natural IPM pest control.',
      badge: 'Effluent, Fiber & IPM'
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
      height: '100%',
      overflowY: 'auto',
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
              v5.54.0 (Phase 59)
            </span>
          </div>
          <p style={{ margin: 0, color: theme.textMuted, fontSize: '0.95rem' }}>
            23-Acre Autonomous Acoustic-Agricultural Enclave | Ithaca, Finger Lakes, NY | Co-Founded by Sean (Kief) Stehouwer & Brett Adam Stehouwer
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
          { id: 'master_plan_23acres', label: '🗺️ 23-Acre Master Plan & Ithaca NY Renderings' },
          { id: 'acoustic_engineering', label: '🔊 Acoustic Engineering & Parabolic Shell' },
          { id: 'stage_prompter', label: '🎤 Live Stage Switcher & Teleprompter' },
          { id: 'support_facilities', label: '🎪 Support Buildings & 350-Person Septic' },
          { id: 'operational_scenarios', label: '⚡ Operational Load Profiles & Scenarios' },
          { id: 'calculators', label: '📊 CapEx, ROI & System Calculators' },
          { id: 'ag_sensors', label: '📡 Ag Sensor Networks & Poultry IPM' },
          { id: 'spatial_radial', label: '🗺️ Lammerson Lane Master Plan' },
          { id: 'microgrid_infrastructure', label: '⚡ Redundant Microgrid & Geothermal' },
          { id: 'hydro_recycling', label: '🌱 Closed-Loop Hydro Waste & Koi Re-Bonding' },
          { id: 'biofuel_electrical', label: '🔌 Biofuel, Isolation Transformer & Shane\'s Safety' },
          { id: 'bioenergy_rd', label: '🔬 R&D Bio-Energy Density & Deficit Reconciliation' },
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

      {/* NEW SUB-TAB: ACOUSTIC ENGINEERING & PARABOLIC SOUND SHELL SIMULATOR */}
      {activeSubTab === 'acoustic_engineering' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
          {/* SIMULATOR 1: GLAZING TILT & REFLECTION RAY TRACING */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🪟 Smart Glass Glazing Tilt Angle Simulator</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Standard smart-tinting glass has high specular reflectivity. Angling floor-to-ceiling glass panes <strong>5°–7° off vertical</strong> directs reflections toward ceiling acoustic absorbers rather than performance microphones.
            </p>

            <div style={{ margin: '16px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: theme.textMuted, marginBottom: '6px' }}>
                <span>Glass Tilt Angle: <strong style={{ color: '#00FFFF' }}>{glazingTiltAngle}° off vertical</strong></span>
                <span>{glazingTiltAngle >= 5 && glazingTiltAngle <= 7 ? '✅ OPTIMAL ACOUSTIC TILT (5°-7°)' : '⚠️ NON-OPTIMAL TILT'}</span>
              </div>
              <input
                type="range" min="0" max="15" step="0.5" value={glazingTiltAngle}
                onChange={(e) => setGlazingTiltAngle(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div style={{ background: 'rgba(0, 255, 255, 0.08)', padding: '12px', borderRadius: '8px', border: '1px solid #00FFFF' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.85rem' }}>Ray Tracing Reflection Path:</div>
              <div style={{ color: theme.accentCyan, fontSize: '0.8rem', marginTop: '4px' }}>
                {glazingTiltAngle >= 5 && glazingTiltAngle <= 7
                  ? 'Specular rays angled upward into overhead 3D porous ceiling absorbers (Corning 703 substrate). Stage microphones protected from flutter echo.'
                  : 'Direct specular reflections bouncing horizontally into stage microphones & performers. High risk of comb filtering.'}
              </div>
            </div>
          </div>

          {/* SIMULATOR 2: SOIL SUBSTRATE ABSORPTION & PARABOLIC DIFFUSION */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🌿 Soil Substrate & Bio-Acoustic Absorption</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              Foliage scatters high frequencies (&gt;1.6 kHz), while the <strong>moist soil substrate</strong> (planted with ferns & baby tears) acts as the primary broad-spectrum sound absorber.
            </p>

            <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid #10b981', marginBottom: '14px' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem' }}>Moist Soil Absorption Coefficient ($\alpha$): 0.90 – 0.98</div>
              <div style={{ color: theme.textMuted, fontSize: '0.8rem', marginTop: '4px' }}>
                Prevents harsh reflections off the parabolic rear scenae frons while projecting unamplified vocal acoustics forward up the audience slope.
              </div>
            </div>
          </div>

          {/* SIMULATOR 3: MECHANICAL DECOUPLING & SUBWOOFER ARRAYS */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>🔊 Sub-Stage Mechanical Isolation & Subwoofer Arrays</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
              HPA pumps mounted on concrete inertia pads with elastomeric spring decouplers (<strong>15m offset</strong>) eliminate 60 Hz–120 Hz ground rumble on stage.
            </p>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block', marginBottom: '6px' }}>Select Subwoofer Dispersion Mode over Concrete Floor:</label>
              <select
                value={subwooferArrayMode}
                onChange={(e) => setSubwooferArrayMode(e.target.value)}
                style={{ width: '100%', background: '#0d1117', color: '#c084fc', border: '1px solid #7A288A', padding: '8px', borderRadius: '6px' }}
              >
                <option value="cardioid">🔊 Cardioid Array (Recommended: Rejection at Rear Stage)</option>
                <option value="end_fire">🔊 End-Fire Array (High Directional Throw)</option>
              </select>
            </div>

            <div style={{ background: 'rgba(122, 40, 138, 0.15)', padding: '12px', borderRadius: '8px', border: '1px solid #7A288A' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.85rem' }}>Active Array: {subwooferArrayMode === 'cardioid' ? 'Cardioid Array' : 'End-Fire Array'}</div>
              <div style={{ color: theme.textMuted, fontSize: '0.8rem', marginTop: '4px' }}>
                {subwooferArrayMode === 'cardioid'
                  ? 'Cancels low-frequency sound behind the subwoofers, preventing low-end rumble from bouncing off rear glass walls into stage microphones.'
                  : 'Maximizes directional forward acoustic throw up the 150-seat audience slope.'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB: 23-ACRE MASTER PLAN & ITHACA NY RENDERINGS */}
      {activeSubTab === 'master_plan_23acres' && (
        <div style={{ display: 'block' }}>
          {/* Master Blueprints Display */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ color: theme.accentCyan, margin: 0 }}>MAP: MASTER PLAN: NoCo FARM & THEATRE — 23 ACRES</h3>
              <span style={{ background: 'rgba(0, 255, 255, 0.15)', border: '1px solid #00FFFF', color: '#00FFFF', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 700 }}>
                Ithaca, New York · Finger Lakes Landscape
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
              <div>
                <img
                  src="/noco_master_plan_23acres.jpg"
                  alt="NoCo Farm & Theatre 23 Acres Master Plan"
                  style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.3)', boxShadow: '0 0 20px rgba(0, 255, 255, 0.2)' }}
                />
                <div style={{ color: theme.textMuted, fontSize: '0.8rem', textAlign: 'center', marginTop: '8px' }}>
                  23-Acre Master Site Plan: Siheyuan Private Sanctuary (North), Serene Pond & Saunas (NE), 8 ÖÖD Pods Ring (West), Living Stage & Rehearsal Studios (Center), Outdoor Amphitheater & Permaculture (East).
                </div>
              </div>

              <div>
                <img
                  src="/noco_master_plan_siheyuan.jpg"
                  alt="NoCo Siheyuan Courtyard Blueprint Variant"
                  style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', border: '1px solid rgba(122, 40, 138, 0.4)', boxShadow: '0 0 20px rgba(122, 40, 138, 0.2)' }}
                />
                <div style={{ color: theme.textMuted, fontSize: '0.8rem', textAlign: 'center', marginTop: '8px' }}>
                  Central Siheyuan Quadrangle Courtyard & Glass Enclosure Detail Variant: Outdoor Performance Venue (East), Serene Pond & Saunas (SE), Valais Sheep Pasture (West), Berry Plots & Torii Gate (South).
                </div>
              </div>
            </div>
          </div>

          {/* Phase III Conceptual Architectural Renderings & Vector Gallery */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🎨 Phase III Conceptual Architectural Renderings & Vector Gallery</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.85rem', marginBottom: '16px' }}>
              Full build-out vector illustrations across four seasons in the Finger Lakes landscape:
            </p>

            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '16px' }}>
              {Object.keys(renderViews).map(key => (
                <button
                  key={key}
                  onClick={() => setActiveRenderView(key)}
                  style={{
                    background: activeRenderView === key ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                    border: activeRenderView === key ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.1)',
                    color: activeRenderView === key ? '#10b981' : theme.textMuted,
                    padding: '8px 14px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    whiteSpace: 'nowrap'
                  }}
                >
                  {renderViews[key].title.split(':')[0]}
                </button>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', background: 'rgba(0, 0, 0, 0.6)', border: '1px solid #10b981', padding: '20px', borderRadius: '8px' }}>
              <div>
                <img
                  src={renderViews[activeRenderView].imgSrc}
                  alt={renderViews[activeRenderView].title}
                  style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.4)', boxShadow: '0 0 20px rgba(16, 185, 129, 0.2)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <h4 style={{ color: '#ffffff', margin: 0, fontSize: '1.1rem' }}>{renderViews[activeRenderView].title}</h4>
                  <span style={{ background: 'rgba(16, 185, 129, 0.2)', border: '1px solid #10b981', color: '#10b981', padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 700 }}>
                    {renderViews[activeRenderView].badge}
                  </span>
                </div>
                <div style={{ color: theme.accentCyan, fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>
                  LIGHTING & TIMING: {renderViews[activeRenderView].time}
                </div>
                <p style={{ color: theme.textMuted, fontSize: '0.9rem', margin: 0, lineHeight: 1.6 }}>
                  {renderViews[activeRenderView].details}
                </p>
              </div>
            </div>
          </div>

          {/* Functionally Grouped Structure Matrix Table */}
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ color: theme.accentCyan, margin: 0 }}>📋 Functionally Grouped Structures & Facilities Matrix</h3>
              
              <div style={{ display: 'flex', gap: '8px' }}>
                {['all', 'Performance & Creative', 'Residential', 'Agricultural', 'Communal & Circulation'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setActiveStructureCategory(cat)}
                    style={{
                      background: activeStructureCategory === cat ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                      border: activeStructureCategory === cat ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                      color: activeStructureCategory === cat ? '#00FFFF' : theme.textMuted,
                      padding: '6px 12px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.75rem',
                      fontWeight: 600
                    }}
                  >
                    {cat === 'all' ? 'All Structures' : cat}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', color: theme.textLight, fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(0, 255, 255, 0.1)', borderBottom: '1px solid #00FFFF', textAlign: 'left' }}>
                    <th style={{ padding: '10px' }}>Category</th>
                    <th style={{ padding: '10px' }}>Building / Structure</th>
                    <th style={{ padding: '10px' }}>Specification</th>
                    <th style={{ padding: '10px' }}>Spatial Location</th>
                    <th style={{ padding: '10px' }}>Description & Function</th>
                  </tr>
                </thead>
                <tbody>
                  {structureMatrix
                    .filter(item => activeStructureCategory === 'all' || item.category === activeStructureCategory)
                    .map((row, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', background: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.02)' : 'transparent' }}>
                        <td style={{ padding: '10px', color: theme.accentCyan, fontWeight: 600 }}>{row.category}</td>
                        <td style={{ padding: '10px', color: '#ffffff', fontWeight: 700 }}>{row.name}</td>
                        <td style={{ padding: '10px', color: theme.accentGreen }}>{row.spec}</td>
                        <td style={{ padding: '10px', color: theme.accentViolet }}>{row.area}</td>
                        <td style={{ padding: '10px', color: theme.textMuted }}>{row.desc}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

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

      {/* SUB-TAB: LIVE STAGE SWITCHER & TELEPROMPTER */}
      {activeSubTab === 'stage_prompter' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div style={{ border: theme.border, padding: '20px', borderRadius: '12px', background: theme.cardBg }}>
            <h3 style={{ marginTop: 0, color: theme.accentCyan }}>🎬 Core Stage Control & Lighting Switcher</h3>
            <TheatricalStageSwitch />
          </div>

          <div style={{ border: theme.border, padding: '20px', borderRadius: '12px', background: theme.cardBg }}>
            <h3 style={{ marginTop: 0, color: theme.accentBlue }}>🎙️ Speech Audio Ingestion & Teleprompter Feed</h3>
            <TheatricalMicClient />
          </div>

          <div style={{ border: theme.border, padding: '20px', borderRadius: '12px', background: theme.cardBg }}>
            <h3 style={{ marginTop: 0, color: theme.accentViolet }}>🖥️ Stage Displays & Remote Viewports</h3>
            <p style={{ color: theme.textMuted, fontSize: '0.9rem' }}>
              Launch live fullscreen stage displays on secondary monitors, teleprompter glass, or projection screens:
            </p>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button 
                onClick={() => window.open('/nocovision/teleprompter', '_blank')}
                style={{ padding: '12px 24px', background: 'linear-gradient(135deg, #0d6efd, #00FFFF)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.9rem' }}>
                📺 Launch Fullscreen Teleprompter
              </button>
              <button 
                onClick={() => window.open('/nocovision/projector', '_blank')}
                style={{ padding: '12px 24px', background: 'linear-gradient(135deg, #6f42c1, #7A288A)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.9rem' }}>
                📽️ Launch Fullscreen Visual Projector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB: R&D BIO-ENERGY DENSITY & DEFICIT RECONCILIATION */}
      {activeSubTab === 'bioenergy_rd' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
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


          {/* BIO-ENERGY DEFICIT MATHEMATICAL RECONCILIATION ENGINE */}
            <div style={{ background: theme.cardBg, border: '1px solid #10b981', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>?? Bio-Energy Deficit Mathematical Reconciliation Engine</h3>
              
              <div style={{ marginBottom: '20px', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: theme.textMuted }}>Raw Bio-Gen Output (MFC + Biogas + BPEC + Piezo):</span>
                  <strong style={{ color: '#ffffff' }}>52.48 kWh/day</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: theme.textMuted }}>Evapotranspiration Avoided Cooling Demand Credit:</span>
                  <span><strong style={{ color: '#ef4444' }}>-22.3 kWh/day</strong> <span style={{ fontSize: '0.75rem', color: theme.textMuted }}>(load reduction)</span></span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: theme.textMuted }}>Solar Array (150 kW) & BESS Buffer:</span>
                  <strong style={{ color: theme.accentGreen }}>+149.52 kWh/day</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ color: theme.textMuted }}>Recycled Server/MFC Thermal Waste Heat:</span>
                  <strong style={{ color: theme.accentGreen }}>+44.6 kWh/day</strong>
                </div>
              </div>

              <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '14px', borderRadius: '8px', border: '1px solid #10b981', textAlign: 'center' }}>
                <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.05rem' }}>
                  ? NET RECONCILED SYSTEM ENERGY BALANCE: {targetReconciledTarget.toFixed(1)} kWh / day (100% Solved)
                </div>
              </div>
            </div>
          </div>
        )}

      {/* SUB-TAB: REDUNDANT MICROGRID & INFRASTRUCTURE */}
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
              <li><strong>120 kW Monocrystalline Rooftop Array:</strong> Venue, Main House, & Hydroponics Facility</li>
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
              <li><strong>8 ÖÖD Glass Cottages:</strong> Shared 2-ton loop fields</li>
              <li><strong>Hydroponics Greenhouse:</strong> Dedicated climate stabilization unit</li>
            </ul>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
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

      {/* SUB-TAB: CLOSED-LOOP HYDROPONIC WASTE & KOI RE-BONDING */}
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

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
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

      {/* SUB-TAB: BIOFUEL, ISOLATION TRANSFORMER & SHANE'S SAFETY */}
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

      {/* SUB-TAB: PILLARS */}
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

      {/* SUB-TAB: CEA FARMING & LIVESTOCK */}
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

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🐑 Livestock Husbandry Sectors</h3>
            <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
              <li><strong>Valais Blacknose Sheep (15 ewes):</strong> 1.5 acres pasture, 1,200 sq ft barn with lambing pens & radiant floor heating</li>
              <li><strong>Vicuña Alpacas (6 females):</strong> 1.0 acre paddock, 800 sq ft fiber shelter</li>
              <li><strong>Chickens & Ducks (30 birds):</strong> Free-range orchard rotational grazing for IPM pest control</li>
              <li><strong>Closed-Loop Co-Digestion:</strong> Livestock manure collected for anaerobic methane biogas generators</li>
            </ul>
          </div>
        </div>
      )}

      {/* SUB-TAB: NEON LOUNGE ARCHITECT */}
        {/* SUB-TAB: SUPPORT BUILDINGS & SEPTIC */}
        {activeSubTab === 'support_facilities' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#00FFFF', marginTop: 0 }}>?? Support & Ancillary Buildings</h3>
              <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
                <li><strong>Recording Studio:</strong> 800 sq ft, professional acoustic treatment.</li>
                <li><strong>Rehearsal Space:</strong> 1,200 sq ft for music rehearsals and small performances.</li>
                <li><strong>Costume Shop & Set Workshop:</strong> 1,500 sq ft for textile work and light construction.</li>
                <li><strong>Fire Pit:</strong> Circular stone area with concentric rings for gatherings.</li>
                <li><strong>Sheep Barn:</strong> 1,200 sq ft with lambing pens and feed storage.</li>
                <li><strong>Alpaca Shelter:</strong> 800 sq ft open-sided building.</li>
              </ul>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#10b981', marginTop: 0 }}>?? 350-Person Septic & Wastewater</h3>
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
        {activeSubTab === 'operational_scenarios' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#7A288A', marginTop: 0 }}>? Peak Event Day Scenarios</h3>
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
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#00FFFF', marginTop: 0 }}>?? Baseline Night Operations</h3>
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
        {activeSubTab === 'calculators' && (
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: '#10b981', marginTop: 0 }}>?? CapEx & ROI Estimations</h3>
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
                  <td style={{ padding: '10px', color: '#00FFFF' }}>,000</td>
                  <td style={{ padding: '10px' }}>6-8 Years (Utility Savings)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px' }}>3,000-Gal Advanced Septic & Wetlands</td>
                  <td style={{ padding: '10px', color: '#00FFFF' }}>,000</td>
                  <td style={{ padding: '10px' }}>Immediate (Required Infrastructure)</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px' }}>4,000 sq ft Hydroponics Greenhouse</td>
                  <td style={{ padding: '10px', color: '#00FFFF' }}>,000</td>
                  <td style={{ padding: '10px' }}>3-4 Years (Crop Yields)</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px' }}>Geothermal Ground Source Heat Pumps</td>
                  <td style={{ padding: '10px', color: '#00FFFF' }}>,000</td>
                  <td style={{ padding: '10px' }}>5-7 Years (HVAC Savings)</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
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


        {/* SUB-TAB: LAMMERSON LANE MASTER PLAN */}
        {activeSubTab === 'spatial_radial' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ color: '#7A288A', marginTop: 0 }}>??? The Mycelial Radial: Lammerson Lane Master Plan</h3>
              <p style={{ color: 'rgba(255,255,255,0.6)', lineHeight: '1.6' }}>
                The campus footprint follows concentric zoning optimized for acoustic isolation, microclimate management, and resource routing across the Lammerson Lane property.
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '15px', marginTop: '20px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #00FFFF' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 0: The Core</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>"Living Stage" Amphitheater (3,000 sq ft, 150 seats) incorporating live foliage as natural acoustic dampening.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #7A288A' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 1: Inner Ring</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>Glass-walled "Green Rooms" serving as artist preparation spaces and high-yield plant nurseries.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 2: Residential Halo</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>Continuous ring of Tech-Earthship housing providing primary acoustic containment and living spaces.</p>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#fff' }}>Zone 3: Agro-Shield</h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>Dense barrier of timber bamboo, corn, and hemp providing physical isolation and biomass gasification supply.</p>
                </div>
              </div>
            </div>
          </div>
        )}

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
