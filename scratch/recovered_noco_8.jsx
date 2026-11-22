import React, { useState } from 'react';
import { useAppStore } from './useAppStore';
import TheatricalStageSwitch from './TheatricalStageSwitch.jsx';
import TheatricalMicClient from './TheatricalMicClient.jsx';

const ProjectNoCoStudioTab = () => {
  const [activeSubTab, setActiveSubTab] = useState('governance');
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedZone, setSelectedZone] = useState('zone0');
  const [activeRenderView, setActiveRenderView] = useState('view01');
  const [activeStructureCategory, setActiveStructureCategory] = useState('all');

  // Sub-Tab Master List with Categories & Sequence Index
  const subTabsList = [
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
  ];

  const categories = [
    'all',
    '🏛️ Strategy & Master Plan',
    '🔊 Acoustics & Stage',
    '⚡ Infrastructure & Energy',
    '🌾 Agriculture & Facilities',
    '📊 Financials & Operations'
  ];

  const currentIndex = subTabsList.findIndex(t => t.id === activeSubTab);
  const currentTabObj = subTabsList[currentIndex] || subTabsList[0];
  const prevTab = subTabsList[(currentIndex - 1 + subTabsList.length) % subTabsList.length];
  const nextTab = subTabsList[(currentIndex + 1) % subTabsList.length];

  // Acoustic Engineering State
  const [glazingTiltAngle, setGlazingTiltAngle] = useState(6.0); // 5-7 deg recommended
  const [subwooferArrayMode, setSubwooferArrayMode] = useState('cardioid');
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
  const [acDcRegulatorMode, setAcDcRegulatorMode] = useState('AC');
  const [changeoverDelayTimerSec, setChangeoverDelayTimerSec] = useState(3.5);
  const [autoRelayBreakerTripped, setAutoRelayBreakerTripped] = useState(false);

  // Hydroponic Waste & Koi Pond Re-Bonding State
  const [hydroponicEcStatus, setHydroponicEcStatus] = useState(1.4);
  const [koiPondFishWasteDosage, setKoiPondFishWasteDosage] = useState(85);
  const [electrodeDisinfectionActive, setElectrodeDisinfectionActive] = useState(true);
  const [selectedSecondaryCrop, setSelectedSecondaryCrop] = useState('Tomatoes');

  // CapEx & Financial Calculators State (23-Acre Master Plan)
  const [landAcquisitionAcres, setLandAcquisitionAcres] = useState(23);
  const [costPerAcre, setCostPerAcre] = useState(18500);
  const [buildingSqFtCost, setBuildingSqFtCost] = useState(145);
  const [elecRateKwh, setElecRateKwh] = useState(0.16);
  const [solarSystemCost, setSolarSystemCost] = useState(185000);
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
  const [sensorTemp, setSensorTemp] = useState(21.4);
  const [sensorHumidity, setSensorHumidity] = useState(68);
  const [sensorSoilMoisture, setSensorSoilMoisture] = useState(82);
  const [sensorPh, setSensorPh] = useState(6.2);
  const [poultryCount, setPoultryCount] = useState(30);

  // Financial Calculations
  const totalLandCost = landAcquisitionAcres * costPerAcre;
  const greenhouseCost = 4000 * buildingSqFtCost;
  const livingStageCost = 3000 * (buildingSqFtCost * 1.35);
  const totalEstimatedCapEx = totalLandCost + greenhouseCost + livingStageCost + solarSystemCost + geothermalSystemCost;
  const annualSolarGenKwh = 150 * 1350;
  const annualSolarElectricSavings = annualSolarGenKwh * elecRateKwh;
  const annualGeothermalHeatingSavings = 14500;
  const totalAnnualUtilitySavings = annualSolarElectricSavings + annualGeothermalHeatingSavings;
  const paybackPeriodYears = (totalEstimatedCapEx / (totalAnnualUtilitySavings > 0 ? totalAnnualUtilitySavings : 1)).toFixed(1);

  // Ag Calculations
  const annualNftGreensHeads = 9600 * 8.5;
  const annualNftRevenue = annualNftGreensHeads * nftPricePerHead;
  const annualSheepFleeceLbs = 15 * 11.5;
  const annualSheepFleeceRevenue = annualSheepFleeceLbs * sheepWoolPricePerLb;
  const annualVicunaFiberKg = (6 * 0.45);
  const annualVicunaFiberRevenue = annualVicunaFiberKg * vicunaFiberPricePerKg;
  const totalAnnualAgRevenue = annualNftRevenue + annualSheepFleeceRevenue + annualVicunaFiberRevenue;
  const dailyFreeMealsSupported = Math.floor(annualNftGreensHeads / 365);

  // Scenarios Data
  const scenarioData = {
    performance: {
      name: '🎭 Performance Scenario (150 Occupants, 3 Hours)',
      occupancy: 150,
      durationHrs: 3,
      powerDemandKw: 21.0,
      energyKwh: 63.0,
      notes: 'Peak venue assembly with main PA sound, stage lighting rigs, and full HVAC.'
    },
    rehearsal: {
      name: '🎼 Rehearsal Scenario (20 Occupants, 4 Hours)',
      occupancy: 20,
      durationHrs: 4,
      powerDemandKw: 8.75,
      energyKwh: 35.0,
      notes: 'Cast & crew acoustic rehearsal with minimal PA reinforcement and moderate climate control.'
    },
    maintenance: {
      name: '🛠️ Maintenance Scenario (Minimal Occupancy, 8 Hours)',
      occupancy: 2,
      durationHrs: 8,
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

  // Render Views Data
  const renderViews = {
    view01: {
      title: 'VIEW 01 / 06: Aerial Overview — Full 23-Acre Campus',
      time: 'Golden Hour / Late Afternoon',
      imgSrc: '/noco_vector_aerial.png',
      details: 'Looking southeast across the full 23-acre NoCo Farms campus at golden hour in Ithaca, NY. Christmas tree grove cradles the family compound in the northwest.',
      badge: 'Master Aerial Campus'
    },
    view02: {
      title: 'VIEW 02 / 06: The Family Compound — 4-Unit ÖÖD Home Cluster',
      time: 'Early Morning Dawn',
      imgSrc: '/noco_vector_family_compound.png',
      details: 'Eye-level view from the central courtyard at dawn. Four ÖÖD pods arranged in a protective cluster tucked inside the Christmas fir canopy.',
      badge: 'Family Compound Sanctuary'
    },
    view03: {
      title: 'VIEW 03 / 06: The Living Stage — 4,000 SF Polycarbonate Greenhouse Stage',
      time: 'Evening Performance (Capacity 100–120)',
      imgSrc: '/noco_vector_greenhouse_stage.png',
      details: 'Interior view during a performance evening. Polycarbonate walls diffuse dusk daylight while purple LED grow lights illuminate living lettuce towers.',
      badge: 'Polycarbonate Living Stage'
    },
    view04_05: {
      title: 'VIEWS 04 & 05 / 06: Farm Life & Earth-Berm Outdoor Theater',
      time: 'Afternoon & Night Sky',
      imgSrc: '/noco_vector_sheep_and_theater.png',
      details: 'Left: Valais Blacknose sheep grazing below the timber-frame barn. Right: Open-air earth-berm outdoor theater under a late-summer moon with fire torches.',
      badge: 'Agritourism & Earth-Berm Theater'
    },
    view06: {
      title: 'VIEW 06 / 06: Artist Residency ÖÖD Pods — Winter Retreat',
      time: 'Deep Winter Evening (January Snowfall)',
      imgSrc: '/noco_vector_family_compound.png',
      details: 'Three artist residency ÖÖD pods in deep January snowfall in the NE sector.',
      badge: 'Winter Retreat Residency'
    }
  };

  // Matrix Data
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

  // Bio-Energy Energy Calculations
  const calculatedBioSum = (parseFloat(mfcGen) + parseFloat(biogasGen) + parseFloat(bpecGen) + parseFloat(piezoGen));
  const evapotranspirationCoolingCredit = 22.30;
  const solarWindBessBufferContribution = 149.52;
  const thermalWasteHeatRecycled = 44.60;
  const totalReconciledEnergyBalance = calculatedBioSum + evapotranspirationCoolingCredit + solarWindBessBufferContribution;

  // Lighting Calculations
  const totalStageLightWattage = numLedStageLights * wattsPerLedLight;
  const stageLightEnergyNeededKwh = (totalStageLightWattage * desiredRuntimeHours) / 1000.0;
  const batteryCapacityRequiredAmpHours = (stageLightEnergyNeededKwh * 1000) / 48.0;

  // Theme Tokens
  const theme = {
    bg: '#000000',
    cardBg: 'rgba(13, 17, 23, 0.95)',
    border: '1px solid rgba(0, 255, 255, 0.3)',
    accentCyan: '#00FFFF',
    accentViolet: '#7A288A',
    accentBlue: '#38bdf8',
    accentGreen: '#10b981',
    accentAmber: '#f59e0b',
    textMuted: '#94a3b8',
    textLight: '#f8fafc'
  };

  const zones = {
    zone0: { name: 'Zone 0 (The Core): "The Living Stage" Amphitheater', size: '3,000 sq ft base footprint | 150 - 1,500 Capacity', details: 'The central acoustic heartbeat of the enclave.', badge: 'Core Performance & Assembly' },
    zone1: { name: 'Zone 1 (Inner Ring): "The Green Rooms"', size: 'High-Yield Nursery & Artist Prep Suites', details: 'Glass-walled prep rooms that double as high-yield vertical nurseries.', badge: 'Artist Prep & CEA Nurseries' },
    zone2: { name: 'Zone 2 (Residential Halo): Connected Tech-Earthships', size: 'Continuous Housing Ring & Sound Lock Corridor', details: 'Continuous rammed-earth North walls faced inward.', badge: 'Acoustic Barrier & Living Enclave' },
    ood_cottages: { name: '8 ÖÖD Mirror Houses & Studios Ring', size: '8 Pods (4 ÖÖD Mirror Houses + 4 ÖÖD Studios)', details: 'Sleek mirrored glass cottages integrated into natural Finger Lakes forest.', badge: 'Artist Residency & Creative Production' },
    zone3: { name: 'Zone 3 (Agro-Shield): Biomass & Privacy Perimeter', size: 'Christmas Tree Grove, Timber Bamboo, Hemp', details: 'Dense Christmas tree fir grove and biomass perimeter providing natural privacy.', badge: 'Privacy Barrier & Fir Grove' },
    livestock: { name: 'Livestock Sectors: Valais Sheep, Alpacas & Poultry', size: '2.5 Acres Pasture | 2,000 sq ft Barn Structures', details: 'Valais Blacknose Sheep and Vicuña Alpacas plus 30 free-range poultry.', badge: 'Effluent, Fiber & IPM' },
    foh: { name: 'Front of House (FOH) Tower (6 o\'clock Position)', size: '3-Story Operational Control Gateway', details: 'Operated by Sean Stehouwer. Level 1 Concessions, Level 2 FOH Control, Level 3 Crow\'s Nest.', badge: 'System Control & Gateway' }
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
        padding: '20px',
        marginBottom: '20px',
        boxShadow: '0 0 30px rgba(0, 255, 255, 0.15)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <span style={{ fontSize: '1.8rem' }}>🏛️</span>
            <h1 style={{ margin: 0, fontSize: '1.7rem', fontWeight: 800, color: '#ffffff', letterSpacing: '0.5px' }}>
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
              v5.47.0 (Phase 56)
            </span>
          </div>
          <p style={{ margin: 0, color: theme.textMuted, fontSize: '0.9rem' }}>
            23-Acre Autonomous Acoustic-Agricultural Enclave | Ithaca, NY | Co-Founded by Sean (Kief) Stehouwer & Brett Adam Stehouwer
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '8px', padding: '6px 12px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: '#10b981', fontWeight: 700 }}>LLM SAFETY</div>
            <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 800 }}>ACTIVE (S1/S3/S4)</div>
          </div>
          <div style={{ background: 'rgba(122, 40, 138, 0.25)', border: '1px solid #7A288A', borderRadius: '8px', padding: '6px 12px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: '#c084fc', fontWeight: 700 }}>KIEF PROTOCOL</div>
            <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 800 }}>EST. AUG 17, 2025</div>
          </div>
        </div>
      </div>

      {/* DUAL NAVIGATION CONTROL BAR (CATEGORY FILTERS + DIRECT DROPDOWN) */}
      <div style={{
        background: 'rgba(13, 17, 23, 0.98)',
        border: '1px solid #00FFFF',
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '24px',
        boxShadow: '0 0 25px rgba(0, 255, 255, 0.15)'
      }}>
        {/* ROW 1: CATEGORY FILTER BUTTONS */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '10px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', marginBottom: '12px' }}>
          <span style={{ color: theme.textMuted, fontSize: '0.8rem', fontWeight: 700, alignSelf: 'center', whiteSpace: 'nowrap', marginRight: '6px' }}>
            CATEGORIES:
          </span>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              style={{
                background: activeCategory === cat
                  ? 'linear-gradient(135deg, rgba(0, 255, 255, 0.25), rgba(122, 40, 138, 0.4))'
                  : 'rgba(255, 255, 255, 0.04)',
                border: activeCategory === cat ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                color: activeCategory === cat ? '#ffffff' : theme.textMuted,
                padding: '6px 14px',
                borderRadius: '20px',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600,
                whiteSpace: 'nowrap'
              }}
            >
              {cat === 'all' ? '🌐 All 16 Sections' : cat}
            </button>
          ))}
        </div>

        {/* ROW 2: DIRECT SECTION DROPDOWN SELECTOR + PREV/NEXT QUICK CONTROLS */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '260px' }}>
            <label style={{ fontSize: '0.75rem', color: theme.accentCyan, fontWeight: 700, display: 'block', marginBottom: '4px' }}>
              DIRECT SECTION SELECTOR ({currentIndex + 1} of {subTabsList.length}):
            </label>
            <select
              value={activeSubTab}
              onChange={(e) => setActiveSubTab(e.target.value)}
              style={{
                width: '100%',
                background: '#0d1117',
                color: '#ffffff',
                border: '1px solid #00FFFF',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '0.9rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              {subTabsList.map((item, idx) => (
                <option key={item.id} value={item.id}>
                  {idx + 1}. {item.category} → {item.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setActiveSubTab(prevTab.id)}
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#ffffff',
                padding: '10px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '0.85rem'
              }}
            >
              ◀ Prev: {prevTab.label.split(' ')[0]}
            </button>

            <button
              onClick={() => setActiveSubTab(nextTab.id)}
              style={{
                background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(122, 40, 138, 0.4))',
                border: '1px solid #00FFFF',
                color: '#ffffff',
                padding: '10px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 700,
                fontSize: '0.85rem'
              }}
            >
              Next: {nextTab.label.split(' ')[0]} ▶
            </button>
          </div>
        </div>

        {/* ROW 3: SCROLLABLE SUB-TAB PILLS (FILTERED BY CATEGORY) */}
        <div style={{
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          marginTop: '12px',
          paddingTop: '12px',
          borderTop: '1px dashed rgba(255, 255, 255, 0.1)'
        }}>
          {subTabsList
            .filter(tab => activeCategory === 'all' || tab.category === activeCategory)
            .map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                style={{
                  background: activeSubTab === tab.id
                    ? 'linear-gradient(135deg, rgba(0, 255, 255, 0.3), rgba(122, 40, 138, 0.5))'
                    : 'rgba(255, 255, 255, 0.03)',
                  border: activeSubTab === tab.id ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.08)',
                  color: activeSubTab === tab.id ? '#ffffff' : theme.textMuted,
                  padding: '8px 14px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  whiteSpace: 'nowrap'
                }}
              >
                {tab.label}
              </button>
            ))}
        </div>
      </div>

      {/* SUB-TAB CONTENT RENDERING */}
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

      {activeSubTab === 'master_plan_23acres' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ color: theme.accentCyan, margin: 0 }}>MAP: MASTER PLAN: NoCo FARM & THEATRE — 23 ACRES</h3>
              <span style={{ background: 'rgba(0, 255, 255, 0.15)', border: '1px solid #00FFFF', color: '#00FFFF', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 700 }}>
                Ithaca, New York · Finger Lakes Landscape
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
              <div>
                <img src="/noco_master_plan_23acres.jpg" alt="NoCo Farm & Theatre 23 Acres Master Plan" style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(0, 255, 255, 0.3)' }} />
              </div>
              <div>
                <img src="/noco_master_plan_siheyuan.jpg" alt="NoCo Siheyuan Courtyard Blueprint Variant" style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(122, 40, 138, 0.4)' }} />
              </div>
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🎨 Phase III Conceptual Architectural Renderings & Vector Gallery</h3>
            <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '16px' }}>
              {Object.keys(renderViews).map(key => (
                <button
                  key={key} onClick={() => setActiveRenderView(key)}
                  style={{
                    background: activeRenderView === key ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                    border: activeRenderView === key ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.1)',
                    color: activeRenderView === key ? '#10b981' : theme.textMuted,
                    padding: '8px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600, whiteSpace: 'nowrap'
                  }}
                >
                  {renderViews[key].title.split(':')[0]}
                </button>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', background: 'rgba(0, 0, 0, 0.6)', border: '1px solid #10b981', padding: '20px', borderRadius: '8px' }}>
              <div>
                <img src={renderViews[activeRenderView].imgSrc} alt={renderViews[activeRenderView].title} style={{ width: '100%', borderRadius: '8px' }} />
              </div>
              <div>
                <h4 style={{ color: '#ffffff', margin: '0 0 10px 0' }}>{renderViews[activeRenderView].title}</h4>
                <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>{renderViews[activeRenderView].details}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeSubTab === 'acoustic_engineering' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🪟 Smart Glass Glazing Tilt Angle Simulator</h3>
            <div style={{ margin: '16px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: theme.textMuted, marginBottom: '6px' }}>
                <span>Glass Tilt Angle: <strong style={{ color: '#00FFFF' }}>{glazingTiltAngle}° off vertical</strong></span>
                <span>{glazingTiltAngle >= 5 && glazingTiltAngle <= 7 ? '✅ OPTIMAL TILT (5°-7°)' : '⚠️ NON-OPTIMAL TILT'}</span>
              </div>
              <input type="range" min="0" max="15" step="0.5" value={glazingTiltAngle} onChange={(e) => setGlazingTiltAngle(parseFloat(e.target.value))} style={{ width: '100%' }} />
            </div>
          </div>

          <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🌿 Soil Substrate & Bio-Acoustic Absorption</h3>
            <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid #10b981' }}>
              <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem' }}>Moist Soil Absorption Coefficient ($\alpha$): 0.90 – 0.98</div>
            </div>
          </div>
        </div>
      )}

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
        </div>
      )}

      {activeSubTab === 'bioenergy_rd' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ background: theme.cardBg, border: '1px solid #10b981', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>⚖️ Bio-Energy Deficit Mathematical Reconciliation Engine</h3>
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '14px', borderRadius: '8px', border: '1px solid #10b981', textAlign: 'center' }}>
              <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.05rem' }}>
                ✅ NET RECONCILED SYSTEM ENERGY BALANCE: {totalReconciledEnergyBalance.toFixed(1)} kWh / day
              </div>
            </div>
          </div>
        </div>
      )}

      {/* FOOTER NAVIGATION CONTROLS AT BOTTOM OF EVERY SECTION */}
      <div style={{
        marginTop: '32px',
        paddingTop: '20px',
        borderTop: '1px solid rgba(0, 255, 255, 0.3)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        background: 'rgba(13, 17, 23, 0.95)',
        padding: '16px 20px',
        borderRadius: '12px'
      }}>
        <button
          onClick={() => setActiveSubTab(prevTab.id)}
          style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            color: '#ffffff',
            padding: '12px 20px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '0.9rem'
          }}
        >
          ◀ Previous: {prevTab.label}
        </button>

        <div style={{ textAlign: 'center' }}>
          <span style={{ color: theme.accentCyan, fontWeight: 800, fontSize: '0.9rem' }}>
            Section {currentIndex + 1} of {subTabsList.length}: {currentTabObj.label}
          </span>
        </div>

        <button
          onClick={() => setActiveSubTab(nextTab.id)}
          style={{
            background: 'linear-gradient(135deg, #00FFFF, #7A288A)',
            border: 'none',
            color: '#ffffff',
            padding: '12px 20px',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 800,
            fontSize: '0.9rem',
            boxShadow: '0 0 15px rgba(0, 255, 255, 0.3)'
          }}
        >
          Next: {nextTab.label} ▶
        </button>
      </div>
    </div>
  );
};

export default ProjectNoCoStudioTab;
