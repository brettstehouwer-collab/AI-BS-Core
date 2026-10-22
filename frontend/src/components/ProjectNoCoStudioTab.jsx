import React, { useState } from 'react';
import { useAppStore } from './useAppStore';
import TheatricalStageSwitch from './TheatricalStageSwitch.jsx';
import TheatricalMicClient from './TheatricalMicClient.jsx';
import NocoSpatialCampusMap from './NocoSpatialCampusMap.jsx';
import NocoTheatricalConsole from './NocoTheatricalConsole.jsx';
import NocoMicrogridSimulator from './NocoMicrogridSimulator.jsx';
import NocoCeaAgriHud from './NocoCeaAgriHud.jsx';
import NocoAgritourismCrm from './NocoAgritourismCrm.jsx';
import NocoPropertiesTracker from './NocoPropertiesTracker.jsx';
import Noco3DCampusWalkthrough from './Noco3DCampusWalkthrough.jsx';
import VLCPreviewMonitor from './VLCPreviewMonitor.jsx';

const ProjectNoCoStudioTab = () => {
  // 6 Consolidated Master Pillars (replacing the 22 cluttered tabs with zero data loss)
  const [activeSubTab, setActiveSubTab] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const sub = params.get('subtab');
      if (sub === 'properties' || params.get('tab') === 'noco_properties') return 'properties_tracker';
      if (['campus_map', 'master_plan_23acres', 'spatial_radial', 'support_facilities'].includes(sub)) return 'campus_master_plan';
      if (['theatrical_console', 'acoustic_engineering', 'stage_prompter', 'neon_lounge'].includes(sub)) return 'stage_acoustics';
      if (['microgrid_bess', 'microgrid_infrastructure', 'operational_scenarios', 'bioenergy_rd', 'biofuel_electrical'].includes(sub)) return 'energy_microgrid';
      if (['cea_iot_hud', 'cea_farming', 'hydro_recycling', 'ag_sensors'].includes(sub)) return 'cea_agriculture';
      if (['agritourism_crm', 'governance', 'pillars', 'calculators'].includes(sub)) return 'governance_financials';
    } catch (e) {}
    return 'properties_tracker';
  });

  // Internal Sub-Mode Filters within each Master Pillar ('all' shows unified view)
  const [campusViewMode, setCampusViewMode] = useState('all');
  const [stageViewMode, setStageViewMode] = useState('all');
  const [energyViewMode, setEnergyViewMode] = useState('all');
  const [ceaViewMode, setCeaViewMode] = useState('all');
  const [govViewMode, setGovViewMode] = useState('all');

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
  const livingStageCost = Math.round(3000 * (buildingSqFtCost * 1.35));
  const totalEstimatedCapEx = totalLandCost + greenhouseCost + livingStageCost + solarSystemCost + geothermalSystemCost;

  // Annual Utility Savings & Payback
  const annualSolarGenKwh = 150 * 1350;
  const annualSolarElectricSavings = Math.round(annualSolarGenKwh * elecRateKwh);
  const annualGeothermalHeatingSavings = 14500;
  const totalAnnualUtilitySavings = annualSolarElectricSavings + annualGeothermalHeatingSavings;
  const paybackPeriodYears = (totalEstimatedCapEx / (totalAnnualUtilitySavings > 0 ? totalAnnualUtilitySavings : 1)).toFixed(1);

  // CEA Harvest Yields & Revenue
  const annualNftGreensHeads = 9600 * 8.5;
  const annualNftRevenue = Math.round(annualNftGreensHeads * nftPricePerHead);
  const annualSheepFleeceLbs = 15 * 11.5;
  const annualSheepFleeceRevenue = Math.round(annualSheepFleeceLbs * sheepWoolPricePerLb);
  const annualVicunaFiberKg = 6 * 0.45;
  const annualVicunaFiberRevenue = Math.round(annualVicunaFiberKg * vicunaFiberPricePerKg);
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
  const calculatedBioSum = (mfcGen + biogasGen + bpecGen + piezoGen).toFixed(2);
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

  const masterPillars = [
    {
      id: 'properties_tracker',
      label: '🏡 Land Tracker & 112 Audit',
      badge: '8 Parcels · 112 Qs',
      desc: 'Nationwide Property Sniffer, 112 Due Diligence Questionnaire & Municipal Defense'
    },
    {
      id: 'campus_master_plan',
      label: '🗺️ Campus Map & 23-Ac Blueprints',
      badge: 'Zones 0–3 · 6 Views',
      desc: 'Interactive 2D Campus Map, 23-Acre Renderings, Structure Matrix & 350-Person Septic'
    },
    {
      id: 'stage_acoustics',
      label: '🎭 Living Stage, Acoustics & DMX',
      badge: '5°–7° Tilt · DMX',
      desc: 'Parabolic Sound Shell Simulators, Wireless DMX Console, Teleprompter & Neon Lounge'
    },
    {
      id: 'energy_microgrid',
      label: '⚡ Microgrid, Bio-Energy & Safety',
      badge: '160kW · Shane A–H',
      desc: '500kWh BESS Simulator, Geothermal GSHP, Bio-Energy R&D & Shane\'s Safety Regulator'
    },
    {
      id: 'cea_agriculture',
      label: '🌱 CEA Hydro, Koi Loop & Livestock',
      badge: '4,000 SF · Valais',
      desc: 'CEA Greenhouse IoT HUD, Closed-Loop Koi Re-Bonding, Sheep/Alpacas & Poultry IPM'
    },
    {
      id: 'governance_financials',
      label: '🏛️ Governance, CRM & Financials',
      badge: 'Kief Protocol · ROI',
      desc: 'Trojan Horse Strategy, Kief Protocol, Agritourism CRM & Interactive CapEx/ROI Calculators'
    }
  ];

  // Reusable sub-navigation bar renderer
  const renderSubNavBar = (items, activeValue, onSelect, accentColor = '#00FFFF') => (
    <div style={{
      display: 'flex',
      gap: '8px',
      flexWrap: 'wrap',
      alignItems: 'center',
      background: 'rgba(13, 17, 23, 0.85)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      borderRadius: '10px',
      padding: '10px 14px',
      marginBottom: '20px'
    }}>
      <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginRight: '4px' }}>
        Module Filter:
      </span>
      {items.map(item => {
        const isActive = activeValue === item.id;
        return (
          <button
            key={item.id}
            onClick={() => onSelect(item.id)}
            style={{
              background: isActive ? 'rgba(0, 255, 255, 0.16)' : 'rgba(255, 255, 255, 0.03)',
              border: isActive ? `1px solid ${accentColor}` : '1px solid rgba(255, 255, 255, 0.08)',
              color: isActive ? '#ffffff' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: isActive ? 700 : 600,
              fontSize: '0.78rem',
              transition: 'transform 0.15s ease, opacity 0.15s ease, background-color 0.15s ease'
            }}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );

  return (
    <div style={{
      background: theme.bg,
      color: theme.textLight,
      height: '100%',
      overflowY: 'auto',
      padding: 'clamp(10px, 2.5vw, 20px)',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(122, 40, 138, 0.3) 0%, rgba(0, 255, 255, 0.15) 100%)',
        border: theme.border,
        borderRadius: '12px',
        padding: 'clamp(12px, 3vw, 20px)',
        marginBottom: '16px',
        boxShadow: '0 0 30px rgba(0, 255, 255, 0.15)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1.7rem' }}>🏛️</span>
            <h1 style={{ margin: 0, fontSize: 'clamp(1.15rem, 3.5vw, 1.65rem)', fontWeight: 800, color: '#ffffff', letterSpacing: '0.5px' }}>
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
              v5.55.0 (6-Pillar Unified Hub)
            </span>
          </div>
          <p style={{ margin: 0, color: theme.textMuted, fontSize: '0.9rem' }}>
            23-Acre Autonomous Acoustic-Agricultural Enclave | Ithaca, Finger Lakes, NY | Co-Founded by Sean (Kief) Stehouwer & Brett Adam Stehouwer
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
          alignItems: 'stretch',
          width: '100%',
          maxWidth: '560px'
        }}>
          <a
            href="/NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
            target="_blank"
            rel="noreferrer"
            download="NoCo_Executive_Due_Diligence_Dossier_2026.pdf"
            style={{
              background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.25), rgba(122, 40, 138, 0.45))',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '8px 14px',
              textAlign: 'center',
              textDecoration: 'none',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              cursor: 'pointer',
              boxShadow: '0 0 14px rgba(239, 68, 68, 0.3)',
              transition: 'all 0.2s ease'
            }}
          >
            <div style={{ fontSize: '0.68rem', color: '#f87171', fontWeight: 800, letterSpacing: '0.5px' }}>
              📄 EXECUTIVE DOSSIER
            </div>
            <div style={{ fontSize: '0.85rem', color: '#ffffff', fontWeight: 800 }}>
              DOWNLOAD PDF (9.2 KB)
            </div>
          </a>

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

      {/* 6 Master Pillars Navigation Grid (Adaptive 2D Grid on Desktop, Horizontal Swipe Ribbon on Mobile) */}
      <div
        role="tablist"
        aria-label="Project NoCo Master Pillars"
        className="mobile-scroll-ribbon"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '10px',
          marginBottom: '20px'
        }}
      >
        {masterPillars.map(pillar => {
          const isActive = activeSubTab === pillar.id;
          return (
            <button
              key={pillar.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveSubTab(pillar.id)}
              style={{
                background: isActive
                  ? 'linear-gradient(135deg, rgba(0, 255, 255, 0.22), rgba(122, 40, 138, 0.45))'
                  : 'rgba(13, 17, 23, 0.9)',
                border: isActive ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                color: isActive ? '#ffffff' : theme.textLight,
                padding: '12px 14px',
                borderRadius: '10px',
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '6px',
                boxShadow: isActive ? '0 0 18px rgba(0, 255, 255, 0.2)' : 'none',
                transition: 'transform 0.15s ease, opacity 0.15s ease, background-color 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px', width: '100%' }}>
                <span style={{ fontWeight: 800, fontSize: '0.86rem', color: isActive ? '#00FFFF' : '#ffffff' }}>
                  {pillar.label}
                </span>
                <span style={{
                  fontSize: '0.66rem',
                  fontWeight: 700,
                  padding: '2px 7px',
                  borderRadius: '10px',
                  background: isActive ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.06)',
                  color: isActive ? '#00FFFF' : '#94a3b8',
                  whiteSpace: 'nowrap'
                }}>
                  {pillar.badge}
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.35 }}>
                {pillar.desc}
              </div>
            </button>
          );
        })}
      </div>

      {/* =====================================================================
          PILLAR 1: NATIONWIDE LAND TRACKER & 112 DUE DILIGENCE AUDIT HUB
         ===================================================================== */}
      {activeSubTab === 'properties_tracker' && <NocoPropertiesTracker />}

      {/* =====================================================================
          PILLAR 2: MASTER PLAN, 2D CAMPUS & ARCHITECTURE
         ===================================================================== */}
      {activeSubTab === 'campus_master_plan' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {renderSubNavBar([
            { id: 'all', label: '📋 All Campus Blueprints & Maps (Unified)' },
            { id: 'walkthrough_3d', label: '🌐 Interactive 3D WebGL Property Walkthrough' },
            { id: 'video_tours', label: '🎬 Cinematic 3D Property Flythrough Videos' },
            { id: 'interactive_map', label: '🗺️ Interactive 2D Spatial Campus Map' },
            { id: 'blueprints_23ac', label: '📐 23-Acre Blueprints & Seasonal Renderings' },
            { id: 'structures_septic', label: '🏗️ Structure Matrix, Radial Zones & 350-Person Septic' }
          ], campusViewMode, setCampusViewMode)}

          {(campusViewMode === 'all' || campusViewMode === 'walkthrough_3d') && (
            <Noco3DCampusWalkthrough />
          )}

          {(campusViewMode === 'all' || campusViewMode === 'video_tours') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <VLCPreviewMonitor
                title="Project NoCo 3D Property Flythrough & Video Showcase"
                playlist={[
                  {
                    id: 'flythrough_60fps',
                    title: '✨ AI-BS Remastered 60 FPS Cinema Flythrough',
                    src: '/noco_flythrough_60fps.mp4?v=vlc_fs2',
                    badge: '60 FPS • UNBLURRED',
                    desc: 'Interpolated to 60 FPS motion compensation with enhanced micro-contrast, atmospheric color grading, and edge sharpening highlighting solar roof arrays and reflecting ponds.'
                  },
                  {
                    id: 'source_uploaded',
                    title: '📹 Uploaded Master Property Tour',
                    src: '/noco_property_tour_uploaded.mp4?v=vlc_fs2',
                    badge: 'SOURCE 24 FPS',
                    desc: 'Direct reference video with natural architectural overlay showing the central quadrangle, amphitheater rake, pond saunas, and surrounding conifer forest.'
                  },
                  {
                    id: 'dxr_greenhouse',
                    title: '🌿 RTX 4090 DXR: CEA Hydroponics & Koi Biome',
                    src: '/noco_dxr_greenhouse_tour.mp4?v=lora_dxr_v1',
                    badge: 'DXR RAY-TRACED • 60 FPS',
                    desc: 'Interior CEA greenhouse sweep showing purple-spectrum LED grow arrays, automated misting nozzles, vertical hydroponic towers, and circulating koi bio-filter canal.'
                  },
                  {
                    id: 'dxr_winter',
                    title: '❄️ RTX 4090 DXR: Winter Dusk ÖÖD Cabins & Stage',
                    src: '/noco_dxr_winter_dusk.mp4?v=lora_dxr_v1',
                    badge: 'LUMEN GI • DLSS 3.5',
                    desc: 'Cinematic winter dusk perspective showcasing mirror-glass ÖÖD guest cabins reflecting snow-dusted conifer forests, amber timber uplighting, and glowing geodesic living domes.'
                  }
                ]}
              />
            </div>
          )}

          {(campusViewMode === 'all' || campusViewMode === 'interactive_map') && (
            <NocoSpatialCampusMap />
          )}

          {(campusViewMode === 'all' || campusViewMode === 'blueprints_23ac') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Master Blueprints Display */}
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                  <h2 style={{ color: theme.accentCyan, margin: 0, fontSize: '1.25rem' }}>🗺️ MASTER PLAN: NoCo FARM & THEATRE — 23 ACRES</h2>
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
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
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
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
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
            </div>
          )}

          {(campusViewMode === 'all' || campusViewMode === 'structures_septic') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Functionally Grouped Structure Matrix Table */}
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                  <h3 style={{ color: theme.accentCyan, margin: 0 }}>📋 Functionally Grouped Structures & Facilities Matrix</h3>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
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

              {/* Lammerson Lane Mycelial Radial & Support / 350-Person Septic */}
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ color: '#c084fc', marginTop: 0 }}>🕸️ The Mycelial Radial: Lammerson Lane Concentric Zoning</h3>
                <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6 }}>
                  The campus footprint follows concentric zoning optimized for acoustic isolation, microclimate management, and resource routing across the Lammerson Lane property.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginTop: '14px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.35)', padding: '14px', borderRadius: '8px', borderLeft: '4px solid #00FFFF' }}>
                    <h4 style={{ margin: '0 0 6px 0', color: '#fff', fontSize: '0.95rem' }}>Zone 0: The Core</h4>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: theme.textMuted }}>"Living Stage" Amphitheater (3,000 sq ft, 150 seats) incorporating live foliage as natural acoustic dampening.</p>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.35)', padding: '14px', borderRadius: '8px', borderLeft: '4px solid #7A288A' }}>
                    <h4 style={{ margin: '0 0 6px 0', color: '#fff', fontSize: '0.95rem' }}>Zone 1: Inner Ring</h4>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: theme.textMuted }}>Glass-walled "Green Rooms" serving as artist preparation spaces and high-yield plant nurseries.</p>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.35)', padding: '14px', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
                    <h4 style={{ margin: '0 0 6px 0', color: '#fff', fontSize: '0.95rem' }}>Zone 2: Residential Halo</h4>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: theme.textMuted }}>Continuous ring of Tech-Earthship housing providing primary acoustic containment and living spaces.</p>
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.35)', padding: '14px', borderRadius: '8px', borderLeft: '4px solid #f59e0b' }}>
                    <h4 style={{ margin: '0 0 6px 0', color: '#fff', fontSize: '0.95rem' }}>Zone 3: Agro-Shield</h4>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: theme.textMuted }}>Dense barrier of timber bamboo, Christmas firs, and hemp providing physical isolation and biomass supply.</p>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: '#00FFFF', marginTop: 0 }}>🎪 Support & Ancillary Buildings</h3>
                  <ul style={{ paddingLeft: '20px', lineHeight: 1.6, color: theme.textMuted, fontSize: '0.85rem', margin: 0 }}>
                    <li><strong style={{ color: '#fff' }}>Recording Studio:</strong> 800 sq ft, floating-floor professional acoustic treatment.</li>
                    <li><strong style={{ color: '#fff' }}>Rehearsal Space:</strong> 1,200 sq ft for music rehearsals and 40-seat preview performances.</li>
                    <li><strong style={{ color: '#fff' }}>Costume Shop & Set Workshop:</strong> 1,500 sq ft for textile tailoring and stage fabrication.</li>
                    <li><strong style={{ color: '#fff' }}>Fire Pit Courtyard:</strong> Circular stone gathering area with concentric rings.</li>
                    <li><strong style={{ color: '#fff' }}>Sheep Barn & Alpaca Shelter:</strong> 1,200 sq ft heated lambing barn + 800 sq ft fiber shelter.</li>
                  </ul>
                </div>
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: '#10b981', marginTop: 0 }}>💧 350-Person Septic & Constructed Wetlands</h3>
                  <ul style={{ paddingLeft: '20px', lineHeight: 1.6, color: theme.textMuted, fontSize: '0.85rem', margin: 0 }}>
                    <li><strong style={{ color: '#fff' }}>Main Treatment System:</strong> 3,000-gallon concrete septic tank with advanced treatment unit and constructed wetland for 350-person peak occupancy.</li>
                    <li><strong style={{ color: '#fff' }}>Artist Residences:</strong> Composting toilet systems to reduce hydraulic loading and produce humanure compost.</li>
                    <li><strong style={{ color: '#fff' }}>Greywater Wetlands:</strong> Sinks and showers routed through constructed reed beds for landscape irrigation.</li>
                    <li><strong style={{ color: '#fff' }}>Agricultural Wastewater:</strong> Specialized nutrient recovery loop for hydroponic drainage.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          PILLAR 3: LIVING STAGE, ACOUSTICS & WIRELESS DMX CONSOLE
         ===================================================================== */}
      {activeSubTab === 'stage_acoustics' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {renderSubNavBar([
            { id: 'all', label: '📋 Full Stage, Acoustics & DMX Suite (Unified)' },
            { id: 'acoustic_shell', label: '🔊 Acoustic Engineering & Parabolic Shell' },
            { id: 'dmx_console', label: '🎛️ Live Theatrical & Wireless DMX Console' },
            { id: 'stage_prompter', label: '🎤 Stage Switcher, Mic & Teleprompter' }
          ], stageViewMode, setStageViewMode)}

          {(stageViewMode === 'all' || stageViewMode === 'acoustic_shell') && (
            <div>
              <div style={{ marginBottom: '18px' }}>
                <h2 style={{ color: '#ffffff', fontSize: '1.3rem', fontWeight: 700, margin: '0 0 6px 0' }}>
                  Acoustic Engineering, Parabolic Sound Shell & Neon Lounge Controls
                </h2>
                <p style={{ color: theme.textMuted, fontSize: '0.85rem', margin: 0 }}>
                  Specular reflection ray tracing, bio-acoustic soil absorption coefficients, cardioid sub-stage mechanical isolation, and smart glass environmental tuning.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
                {/* SIMULATOR 1: GLAZING TILT & REFLECTION RAY TRACING */}
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🪟 Smart Glass Glazing Tilt Angle Simulator</h3>
                  <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
                    Standard smart-tinting glass has high specular reflectivity. Angling floor-to-ceiling glass panes <strong>5°–7° off vertical</strong> directs reflections toward ceiling acoustic absorbers rather than performance microphones.
                  </p>

                  <div style={{ margin: '16px 0' }}>
                    <label
                      htmlFor="glazing-tilt-range"
                      style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: theme.textMuted, marginBottom: '6px', cursor: 'pointer' }}
                    >
                      <span>Glass Tilt Angle: <strong style={{ color: '#00FFFF' }}>{glazingTiltAngle}° off vertical</strong></span>
                      <span>{glazingTiltAngle >= 5 && glazingTiltAngle <= 7 ? '✅ OPTIMAL ACOUSTIC TILT (5°-7°)' : '⚠️ NON-OPTIMAL TILT'}</span>
                    </label>
                    <input
                      id="glazing-tilt-range"
                      name="glazingTiltAngle"
                      aria-label="Smart Glass Glazing Tilt Angle in degrees off vertical"
                      type="range" min="0" max="15" step="0.5" value={glazingTiltAngle}
                      onChange={(e) => setGlazingTiltAngle(parseFloat(e.target.value))}
                      style={{ width: '100%', cursor: 'pointer' }}
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
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🌿 Soil Substrate & Bio-Acoustic Absorption</h3>
                  <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
                    Foliage scatters high frequencies (&gt;1.6 kHz), while the <strong>moist soil substrate</strong> (planted with ferns & baby tears) acts as the primary broad-spectrum sound absorber.
                  </p>

                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid #10b981', marginBottom: '14px' }}>
                    <div style={{ color: '#ffffff', fontWeight: 700, fontSize: '0.9rem' }}>Moist Soil Absorption Coefficient (α): 0.90 – 0.98</div>
                    <div style={{ color: theme.textMuted, fontSize: '0.8rem', marginTop: '4px' }}>
                      Prevents harsh reflections off the parabolic rear scenae frons while projecting unamplified vocal acoustics forward up the audience slope.
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label htmlFor="smart-glass-opacity-slider" style={{ fontSize: '0.78rem', color: theme.textMuted, display: 'block' }}>
                        Smart Glass Opacity: <strong style={{ color: '#00FFFF' }}>{smartGlassOpacity}%</strong>
                      </label>
                      <input
                        id="smart-glass-opacity-slider"
                        aria-label="Smart Glass Electrochromic Opacity Percentage"
                        type="range" min="0" max="100" value={smartGlassOpacity}
                        onChange={(e) => setSmartGlassOpacity(parseInt(e.target.value, 10))}
                        style={{ width: '100%', marginTop: '6px' }}
                      />
                    </div>
                    <div>
                      <label htmlFor="sub-stage-temp-slider" style={{ fontSize: '0.78rem', color: theme.textMuted, display: 'block' }}>
                        Sub-Stage Ambient: <strong style={{ color: '#10b981' }}>{subStageTemp}°C</strong>
                      </label>
                      <input
                        id="sub-stage-temp-slider"
                        aria-label="Sub-Stage Ambient Temperature in Celsius"
                        type="range" min="10" max="30" step="0.5" value={subStageTemp}
                        onChange={(e) => setSubStageTemp(parseFloat(e.target.value))}
                        style={{ width: '100%', marginTop: '6px' }}
                      />
                    </div>
                  </div>
                </div>

                {/* SIMULATOR 3: MECHANICAL DECOUPLING & SUBWOOFER ARRAYS */}
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: theme.accentViolet, marginTop: 0 }}>🔊 Sub-Stage Mechanical Isolation & Subwoofer Arrays</h3>
                  <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
                    HPA pumps mounted on concrete inertia pads with elastomeric spring decouplers (<strong>{hpaIsolatorOffset}m offset</strong> @ <strong>{hpaPressure} PSI</strong>) eliminate 60 Hz–120 Hz ground rumble on stage.
                  </p>

                  <div style={{ marginBottom: '14px' }}>
                    <label htmlFor="subwoofer-array-select" style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block', marginBottom: '6px' }}>
                      Select Subwoofer Dispersion Mode over Concrete Floor:
                    </label>
                    <select
                      id="subwoofer-array-select"
                      name="subwooferArrayMode"
                      aria-label="Subwoofer Acoustic Array Configuration"
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
            </div>
          )}

          {(stageViewMode === 'all' || stageViewMode === 'dmx_console') && (
            <NocoTheatricalConsole />
          )}

          {(stageViewMode === 'all' || stageViewMode === 'stage_prompter') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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
                    style={{ padding: '12px 24px', background: 'linear-gradient(135deg, #0d6efd, #00FFFF)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.9rem' }}
                  >
                    📺 Launch Fullscreen Teleprompter
                  </button>
                  <button
                    onClick={() => window.open('/nocovision/projector', '_blank')}
                    style={{ padding: '12px 24px', background: 'linear-gradient(135deg, #6f42c1, #7A288A)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.9rem' }}
                  >
                    📽️ Launch Fullscreen Visual Projector
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          PILLAR 4: MICROGRID, BIO-ENERGY & SHANE'S ELECTRICAL SAFETY
         ===================================================================== */}
      {activeSubTab === 'energy_microgrid' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {renderSubNavBar([
            { id: 'all', label: '📋 Full Microgrid, Bio-Energy & Safety Suite (Unified)' },
            { id: 'bess_simulator', label: '⚡ Live Microgrid & 500kWh BESS Simulator' },
            { id: 'grid_geothermal', label: '☀️ 160kW Solar/Wind, Geothermal & Load Scenarios' },
            { id: 'bioenergy_rd', label: '🔬 R&D Bio-Energy & 224.3 kWh/d Reconciliation' },
            { id: 'shane_safety', label: '🔌 Isolation Transformer & Shane\'s Safety (A–H)' }
          ], energyViewMode, setEnergyViewMode)}

          {(energyViewMode === 'all' || energyViewMode === 'bess_simulator') && (
            <NocoMicrogridSimulator />
          )}

          {(energyViewMode === 'all' || energyViewMode === 'grid_geothermal') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
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

                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🔋 BESS Storage & Dual-Well Utilities</h3>
                  <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
                    <li><strong>200 kWh LFP BESS:</strong> Lithium Iron Phosphate battery storage with ATS automatic islanding</li>
                    <li><strong>Domestic Well (20 GPM):</strong> Main House & ÖÖD Cottages + 5,000-gal buried cistern</li>
                    <li><strong>Agricultural Well (50 GPM):</strong> Greenhouse & Livestock + 10,000-gal split heated/unheated cistern</li>
                    <li><strong>3,000-gal Septic + Wetland Polishing:</strong> Biological effluent treatment + Composting toilets</li>
                  </ul>
                </div>
              </div>

              {/* Interactive Operational Load Profile Scenarios */}
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
                  <h3 style={{ color: '#00FFFF', margin: 0 }}>⚡ Interactive Operational Load Profiles & Monthly Cadence</h3>
                  <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', padding: '6px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 700, color: '#10b981' }}>
                    Monthly Consumption: {monthlyTotalKwh.toFixed(1)} kWh/mo ({avgDailyKwh} kWh/day avg)
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                  {Object.entries(scenarioData).map(([key, sc]) => (
                    <div
                      key={key}
                      onClick={() => setSelectedScenario(key)}
                      style={{
                        background: selectedScenario === key ? 'rgba(0, 255, 255, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                        border: selectedScenario === key ? '1px solid #00FFFF' : '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '10px',
                        padding: '16px',
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ fontWeight: 800, color: '#ffffff', fontSize: '0.92rem', marginBottom: '6px' }}>{sc.name}</div>
                      <div style={{ fontSize: '0.78rem', color: theme.textMuted, marginBottom: '10px' }}>{sc.notes}</div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: '#00FFFF', fontWeight: 700 }}>
                        <span>Peak Draw: {sc.powerDemandKw} kW</span>
                        <span>Event Total: {sc.energyKwh} kWh</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {(energyViewMode === 'all' || energyViewMode === 'bioenergy_rd') && (
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
                <h3 style={{ color: '#c084fc', marginTop: 0 }}>⚡ Electro-Fermentation (EF) Biorefinery Integration</h3>
                <p style={{ color: theme.textMuted, fontSize: '0.9rem', lineHeight: 1.6 }}>
                  Integrating advanced Bioelectrochemical Systems (BES) to optimize anaerobic fermentation of agricultural and organic waste. By utilizing solid-state electrodes as electron mediators, we control microbial metabolic pathways to maximize energy yield and value-added product synthesis without chemical buffers.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginTop: '16px' }}>
                  <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(124, 58, 237, 0.3)' }}>
                    <h4 style={{ color: '#c084fc', margin: '0 0 6px 0', fontSize: '0.95rem' }}>Anodic Electro-Fermentation (AEF)</h4>
                    <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                      The working electrode acts as an electron sink for exoelectrogenic bacteria (e.g., <i>Geobacter</i>). This dissipates surplus electrons during waste breakdown, facilitating a higher biomass yield, stabilizing pH/redox irregularities, and generating direct microgrid electricity.
                    </p>
                  </div>

                  <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    <h4 style={{ color: theme.accentGreen, margin: '0 0 6px 0', fontSize: '0.95rem' }}>Microbial Electrosynthesis (MES)</h4>
                    <p style={{ color: theme.textMuted, fontSize: '0.8rem', margin: 0, lineHeight: 1.5 }}>
                      Cathodic biofilms utilize excess microgrid power as an electron donor to reduce CO₂ into value-added platform chemicals (like acetate or methane). This acts as a biological energy storage medium.
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
                <h3 style={{ color: theme.accentGreen, marginTop: 0 }}>🧮 Bio-Energy Deficit Mathematical Reconciliation Engine</h3>
                <div style={{ marginBottom: '20px', fontSize: '0.9rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ color: theme.textMuted }}>Raw Bio-Gen Output (MFC {mfcGen} + Biogas {biogasGen} + BPEC {bpecGen} + Piezo {piezoGen}):</span>
                    <strong style={{ color: '#ffffff' }}>{calculatedBioSum} kWh/day</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ color: theme.textMuted }}>Evapotranspiration Avoided Cooling Demand Credit:</span>
                    <span><strong style={{ color: '#ef4444' }}>{evapotranspirationCoolingCredit.toFixed(1)} kWh/day</strong> <span style={{ fontSize: '0.75rem', color: theme.textMuted }}>(load reduction)</span></span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ color: theme.textMuted }}>Solar Array (150 kW) & BESS Buffer:</span>
                    <strong style={{ color: theme.accentGreen }}>+{solarWindBessBufferContribution} kWh/day</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ color: theme.textMuted }}>Recycled Server/MFC Thermal Waste Heat:</span>
                    <strong style={{ color: theme.accentGreen }}>+{thermalWasteHeatRecycled.toFixed(1)} kWh/day</strong>
                  </div>
                </div>

                <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '14px', borderRadius: '8px', border: '1px solid #10b981', textAlign: 'center' }}>
                  <div style={{ color: '#ffffff', fontWeight: 800, fontSize: '1.05rem' }}>
                    ✅ NET RECONCILED SYSTEM ENERGY BALANCE: {targetReconciledTarget.toFixed(1)} kWh / day (100% Solved)
                  </div>
                </div>
              </div>
            </div>
          )}

          {(energyViewMode === 'all' || energyViewMode === 'shane_safety') && (
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
                    <label htmlFor="led-fixture-count-input" style={{ fontSize: '0.8rem', color: theme.textMuted }}>LED Fixture Count (H):</label>
                    <input
                      id="led-fixture-count-input"
                      aria-label="LED Stage Lighting Fixture Count"
                      type="number" value={numLedStageLights} onChange={(e) => setNumLedStageLights(parseInt(e.target.value, 10) || 0)}
                      style={{ width: '100%', background: '#0d1117', color: '#ffffff', border: '1px solid #334155', padding: '6px', borderRadius: '4px', marginTop: '4px' }}
                    />
                  </div>
                  <div>
                    <label htmlFor="target-runtime-hours-input" style={{ fontSize: '0.8rem', color: theme.textMuted }}>(A) Target Runtime Hours:</label>
                    <input
                      id="target-runtime-hours-input"
                      aria-label="Target Runtime Hours for Stage Lighting"
                      type="number" value={desiredRuntimeHours} onChange={(e) => setDesiredRuntimeHours(parseInt(e.target.value, 10) || 0)}
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
        </div>
      )}

      {/* =====================================================================
          PILLAR 5: CEA HYDROPONICS, KOI LOOP & LIVESTOCK
         ===================================================================== */}
      {activeSubTab === 'cea_agriculture' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {renderSubNavBar([
            { id: 'all', label: '📋 Full CEA Hydroponics, Koi Loop & Livestock Suite (Unified)' },
            { id: 'cea_iot_hud', label: '🌱 Live CEA Greenhouse & Livestock IoT HUD' },
            { id: 'koi_hydro_loop', label: '🐟 Closed-Loop Hydro Waste & Koi Re-Bonding' },
            { id: 'livestock_ipm', label: '🐑 Valais Sheep, Vicuña Alpacas & Poultry IPM' }
          ], ceaViewMode, setCeaViewMode)}

          {(ceaViewMode === 'all' || ceaViewMode === 'cea_iot_hud') && (
            <NocoCeaAgriHud />
          )}

          {(ceaViewMode === 'all' || ceaViewMode === 'koi_hydro_loop') && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🌱 Crop Waste Cascade & Secondary Aeroponics</h3>
                <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5 }}>
                  Hydroponic runoff solution from primary NFT greens is re-routed to feed secondary aeroponic crops.
                </p>

                <div style={{ marginBottom: '14px' }}>
                  <label htmlFor="secondary-crop-select" style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block', marginBottom: '6px' }}>Select Secondary Aeroponic Crop Target:</label>
                  <select
                    id="secondary-crop-select"
                    aria-label="Secondary Aeroponic Crop Target"
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
                  <label htmlFor="koi-dosage-slider" style={{ fontSize: '0.85rem', color: theme.textMuted, display: 'block' }}>Koi Pond Fish Waste Bio-Dosage: {koiPondFishWasteDosage}%</label>
                  <input
                    id="koi-dosage-slider"
                    aria-label="Koi Pond Fish Waste Bio-Dosage Percentage"
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

          {(ceaViewMode === 'all' || ceaViewMode === 'livestock_ipm') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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
                    <li><strong>Valais Blacknose Sheep (15 ewes):</strong> 1.5 acres pasture, 1,200 sq ft barn with lambing pens & radiant floor heating</li>
                    <li><strong>Vicuña Alpacas (6 females):</strong> 1.0 acre paddock, 800 sq ft fiber shelter</li>
                    <li><strong>Chickens & Ducks ({poultryCount} birds):</strong> Free-range orchard rotational grazing for IPM pest control</li>
                    <li><strong>Closed-Loop Co-Digestion:</strong> Livestock manure collected for anaerobic methane biogas generators</li>
                  </ul>
                </div>

                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: '#00FFFF', marginTop: 0 }}>📡 Ag Sensor Networks & Automation</h3>
                  <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
                    <li><strong>Wired & Wireless Nodes:</strong> Continuous monitoring of temp ({sensorTemp}°C), humidity ({sensorHumidity}%), soil moisture ({sensorSoilMoisture}%), and pH ({sensorPh}).</li>
                    <li><strong>Centralized Automation:</strong> Sensor data integrated into building automation systems for HPA misting cycles.</li>
                    <li><strong>Dynamic Islanding Logic:</strong> Coordinates with Automatic Transfer Switches (ATS) for seamless microgrid failover.</li>
                  </ul>
                </div>

                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: '#f59e0b', marginTop: 0 }}>🦆 Poultry & Integrated Pest Management (IPM)</h3>
                  <ul style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.6, paddingLeft: '18px', margin: 0 }}>
                    <li><strong>Dedicated Enclosures:</strong> Secure chicken and duck enclosures for egg production and organic pest control.</li>
                    <li><strong>Biocontrol Integration:</strong> Poultry rotation through Agro-Shield zones eliminates chemical pesticide reliance.</li>
                    <li><strong>Manure Management:</strong> Composting systems process poultry waste into fertilizer for the bamboo and hemp perimeter.</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =====================================================================
          PILLAR 6: GOVERNANCE, CRM & CAPEX FINANCIAL CALCULATORS
         ===================================================================== */}
      {activeSubTab === 'governance_financials' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {renderSubNavBar([
            { id: 'all', label: '📋 Full Governance, CRM & Financials Suite (Unified)' },
            { id: 'capex_calculators', label: '📊 Interactive CapEx, ROI & Ag Revenue Calculators' },
            { id: 'trojan_kief', label: '⚖️ Trojan Horse Strategy, Kief Protocol & Pillars' },
            { id: 'agritourism_crm', label: '🎟️ Agritourism, Box Office & Residency CRM' }
          ], govViewMode, setGovViewMode)}

          {(govViewMode === 'all' || govViewMode === 'capex_calculators') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Interactive CapEx, Payback & Ag Revenue Simulator */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h2 style={{ color: theme.accentCyan, marginTop: 0, fontSize: '1.2rem' }}>📊 23-Acre Master Plan CapEx & Payback Calculator</h2>
                  <p style={{ color: theme.textMuted, fontSize: '0.82rem', marginBottom: '16px' }}>
                    Adjust acquisition and construction parameters to model total capital outlay and autonomous utility payback:
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '16px' }}>
                    <div>
                      <label htmlFor="capex-acres-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.textMuted }}>
                        <span>Target Land Footprint:</span>
                        <strong style={{ color: '#00FFFF' }}>{landAcquisitionAcres} Acres (@ ${costPerAcre.toLocaleString()}/ac = ${totalLandCost.toLocaleString()})</strong>
                      </label>
                      <input
                        id="capex-acres-slider"
                        aria-label="Target Land Footprint in Acres"
                        type="range" min="10" max="50" step="1" value={landAcquisitionAcres}
                        onChange={(e) => setLandAcquisitionAcres(parseInt(e.target.value, 10))}
                        style={{ width: '100%', accentColor: '#00FFFF' }}
                      />
                    </div>

                    <div>
                      <label htmlFor="capex-cost-per-acre-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.textMuted }}>
                        <span>Land Acquisition Cost / Acre:</span>
                        <strong style={{ color: '#10b981' }}>${costPerAcre.toLocaleString()} / acre</strong>
                      </label>
                      <input
                        id="capex-cost-per-acre-slider"
                        aria-label="Land Acquisition Cost Per Acre"
                        type="range" min="6000" max="45000" step="500" value={costPerAcre}
                        onChange={(e) => setCostPerAcre(parseInt(e.target.value, 10))}
                        style={{ width: '100%', accentColor: '#10b981' }}
                      />
                    </div>

                    <div>
                      <label htmlFor="capex-sqft-cost-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.textMuted }}>
                        <span>Greenhouse & Living Stage Build Cost / SF:</span>
                        <strong style={{ color: '#c084fc' }}>${buildingSqFtCost} / sq ft</strong>
                      </label>
                      <input
                        id="capex-sqft-cost-slider"
                        aria-label="Building Construction Cost Per Square Foot"
                        type="range" min="85" max="250" step="5" value={buildingSqFtCost}
                        onChange={(e) => setBuildingSqFtCost(parseInt(e.target.value, 10))}
                        style={{ width: '100%', accentColor: '#c084fc' }}
                      />
                    </div>
                  </div>

                  <div style={{ background: 'rgba(0, 255, 255, 0.08)', border: '1px solid #00FFFF', borderRadius: '8px', padding: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
                      <span style={{ color: theme.textMuted }}>Estimated Total Master CapEx:</span>
                      <strong style={{ color: '#ffffff', fontSize: '1rem' }}>${totalEstimatedCapEx.toLocaleString()}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.82rem' }}>
                      <span style={{ color: theme.textMuted }}>Annual Solar + Geothermal Utility Savings:</span>
                      <strong style={{ color: '#10b981' }}>${totalAnnualUtilitySavings.toLocaleString()} / yr</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                      <span style={{ color: theme.textMuted }}>Baseline Energy Payback Horizon:</span>
                      <strong style={{ color: '#00FFFF' }}>{paybackPeriodYears} Years (Excl. Ag & Box Office Revenue)</strong>
                    </div>
                  </div>
                </div>

                {/* CEA Crop Yield & Luxury Fiber Revenue Calculator */}
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h2 style={{ color: theme.accentGreen, marginTop: 0, fontSize: '1.2rem' }}>🌾 CEA Harvest Yield, Fiber & The MELT Impact</h2>
                  <p style={{ color: theme.textMuted, fontSize: '0.82rem', marginBottom: '16px' }}>
                    Annual agricultural production from 9,600 NFT sites, 15 Valais Blacknose ewes, and 6 Vicuña alpacas:
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '16px' }}>
                    <div>
                      <label htmlFor="ag-nft-price-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.textMuted }}>
                        <span>NFT Leafy Greens & Herbs (81,600 heads/yr):</span>
                        <strong style={{ color: '#10b981' }}>${nftPricePerHead.toFixed(2)}/head → ${annualNftRevenue.toLocaleString()}/yr</strong>
                      </label>
                      <input
                        id="ag-nft-price-slider"
                        aria-label="NFT Leafy Greens Price Per Head"
                        type="range" min="2.0" max="6.0" step="0.25" value={nftPricePerHead}
                        onChange={(e) => setNftPricePerHead(parseFloat(e.target.value))}
                        style={{ width: '100%', accentColor: '#10b981' }}
                      />
                    </div>

                    <div>
                      <label htmlFor="ag-sheep-wool-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.textMuted }}>
                        <span>Valais Blacknose Wool (172.5 lbs/yr):</span>
                        <strong style={{ color: '#38bdf8' }}>${sheepWoolPricePerLb}/lb → ${annualSheepFleeceRevenue.toLocaleString()}/yr</strong>
                      </label>
                      <input
                        id="ag-sheep-wool-slider"
                        aria-label="Valais Blacknose Sheep Wool Price Per Pound"
                        type="range" min="25" max="85" step="5" value={sheepWoolPricePerLb}
                        onChange={(e) => setSheepWoolPricePerLb(parseFloat(e.target.value))}
                        style={{ width: '100%', accentColor: '#38bdf8' }}
                      />
                    </div>

                    <div>
                      <label htmlFor="ag-vicuna-fiber-slider" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: theme.textMuted }}>
                        <span>Vicuña Alpaca Luxury Fiber (2.7 kg/yr):</span>
                        <strong style={{ color: '#c084fc' }}>${vicunaFiberPricePerKg}/kg → ${annualVicunaFiberRevenue.toLocaleString()}/yr</strong>
                      </label>
                      <input
                        id="ag-vicuna-fiber-slider"
                        aria-label="Vicuna Alpaca Fiber Price Per Kilogram"
                        type="range" min="250" max="800" step="25" value={vicunaFiberPricePerKg}
                        onChange={(e) => setVicunaFiberPricePerKg(parseFloat(e.target.value))}
                        style={{ width: '100%', accentColor: '#c084fc' }}
                      />
                    </div>
                  </div>

                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', borderRadius: '8px', padding: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
                      <span style={{ color: theme.textMuted }}>Total Annual CEA & Fiber Value:</span>
                      <strong style={{ color: '#10b981', fontSize: '1rem' }}>${totalAnnualAgRevenue.toLocaleString()} / yr</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                      <span style={{ color: theme.textMuted }}>🍲 The MELT Direct Nutrition Equivalent:</span>
                      <strong style={{ color: '#ffffff' }}>{dailyFreeMealsSupported} Fresh Organic Salads / Day</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Core Infrastructure CapEx & ROI Schedule Table */}
              <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ color: '#10b981', marginTop: 0 }}>📋 Core Infrastructure CapEx & ROI Schedule</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px', fontSize: '0.85rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.15)', textAlign: 'left', color: '#00FFFF' }}>
                        <th style={{ padding: '10px' }}>System Component</th>
                        <th style={{ padding: '10px' }}>Est. CapEx</th>
                        <th style={{ padding: '10px' }}>Annual Value / Offset</th>
                        <th style={{ padding: '10px' }}>Payback Horizon</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px', fontWeight: 700, color: '#fff' }}>150 kW Solar Array + 200 kWh LFP BESS</td>
                        <td style={{ padding: '10px', color: '#00FFFF', fontWeight: 700 }}>${solarSystemCost.toLocaleString()}</td>
                        <td style={{ padding: '10px', color: '#10b981' }}>${annualSolarElectricSavings.toLocaleString()}/yr Electric Offset</td>
                        <td style={{ padding: '10px' }}>5.7 – 6.8 Years (Utility Savings)</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px', fontWeight: 700, color: '#fff' }}>3,000-Gal Advanced Septic & Constructed Wetlands</td>
                        <td style={{ padding: '10px', color: '#00FFFF', fontWeight: 700 }}>$85,000</td>
                        <td style={{ padding: '10px', color: '#10b981' }}>350-Person Peak Assembly Permitting</td>
                        <td style={{ padding: '10px' }}>Immediate (Required Venue Infrastructure)</td>
                      </tr>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px', fontWeight: 700, color: '#fff' }}>4,000 sq ft Polycarbonate Hydroponics Greenhouse</td>
                        <td style={{ padding: '10px', color: '#00FFFF', fontWeight: 700 }}>${greenhouseCost.toLocaleString()}</td>
                        <td style={{ padding: '10px', color: '#10b981' }}>${annualNftRevenue.toLocaleString()}/yr Crop Yield</td>
                        <td style={{ padding: '10px' }}>2.1 – 3.4 Years (Crop Yields + Trojan Horse Exemption)</td>
                      </tr>
                      <tr>
                        <td style={{ padding: '10px', fontWeight: 700, color: '#fff' }}>Geothermal Ground-Source Heat Pumps (17-Ton Total)</td>
                        <td style={{ padding: '10px', color: '#00FFFF', fontWeight: 700 }}>${geothermalSystemCost.toLocaleString()}</td>
                        <td style={{ padding: '10px', color: '#10b981' }}>${annualGeothermalHeatingSavings.toLocaleString()}/yr HVAC Savings</td>
                        <td style={{ padding: '10px' }}>5.5 – 6.5 Years (Winter Heating & Cooling Offset)</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {(govViewMode === 'all' || govViewMode === 'trojan_kief') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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

              {/* Operational Pillars */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: theme.accentCyan, marginTop: 0 }}>🎭 Pillar I: The Living Stage</h3>
                  <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5, margin: 0 }}>
                    Sub-stage HPA engine room insulated by spring isolator vibration damping (15m offset). Huygens-Fresnel sound propagation with Scenae Frons parabolic rear wall.
                  </p>
                </div>
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: '#c084fc', marginTop: 0 }}>🍲 Pillar II: The MELT</h3>
                  <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5, margin: 0 }}>
                    Direct nutrition distribution kitchen and farm-to-table concession hub providing nutrient-dense organic meals ({dailyFreeMealsSupported} salads/day capacity) to artists, residents, and visitors.
                  </p>
                </div>
                <div style={{ background: theme.cardBg, border: theme.border, borderRadius: '12px', padding: '20px' }}>
                  <h3 style={{ color: theme.accentBlue, marginTop: 0 }}>💦 Pillar III: High-Pressure Aeroponics (HPA)</h3>
                  <p style={{ color: theme.textMuted, fontSize: '0.85rem', lineHeight: 1.5, margin: 0 }}>
                    60–100 PSI atomized misting system generating 5–50 micron droplets. Delivers 95% water reduction compared to traditional soil farming.
                  </p>
                </div>
              </div>
            </div>
          )}

          {(govViewMode === 'all' || govViewMode === 'agritourism_crm') && (
            <NocoAgritourismCrm />
          )}
        </div>
      )}
    </div>
  );
};

export default ProjectNoCoStudioTab;
