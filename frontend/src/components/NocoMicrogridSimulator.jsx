import React, { useState, useEffect } from 'react';

export default function NocoMicrogridSimulator() {
  // Grid Operating Mode
  const [gridMode, setGridMode] = useState('ISLANDED'); // 'ISLANDED', 'GRID_TIED', 'OUTAGE_SIMULATION'
  
  // Power Generation Sources (kW)
  const [solarIrradiance, setSolarIrradiance] = useState(850); // W/m²
  const [solarOutputKw, setSolarOutputKw] = useState(115.5); // Max 150 kW
  const [biogasOutputKw, setBiogasOutputKw] = useState(24.0); // Max 35 kW
  const [geothermalThermalKw, setGeothermalThermalKw] = useState(14.5);
  const [mfcOutputKw, setMfcOutputKw] = useState(1.8);

  // BESS Battery Energy Storage System (500 kWh Capacity)
  const [batterySoc, setBatterySoc] = useState(82.4); // %
  const [batteryCapacityKwh] = useState(500);
  const [batteryCellTemp, setBatteryCellTemp] = useState(23.2); // °C
  const [batteryHealth] = useState(99.4); // %
  const [bessCycleCount] = useState(412);

  // Load Shedding States
  const [tier1Active, setTier1Active] = useState(true); // Life Support / Freeze (6.5 kW)
  const [tier2Active, setTier2Active] = useState(true); // Living Stage (21.0 kW)
  const [tier3Active, setTier3Active] = useState(true); // CEA Hydroponics (12.5 kW)
  const [tier4Active, setTier4Active] = useState(true); // EV Charging / Non-critical (15.0 kW)
  
  // Simulation Alarms & Logs
  const [gridAlarm, setGridAlarm] = useState(null);
  const [autoTransferSwitchActive, setAutoTransferSwitchActive] = useState(true);

  // Calculate Solar Output based on Irradiance slider
  useEffect(() => {
    const calculatedSolar = (solarIrradiance / 1000.0) * 150.0 * 0.92;
    setSolarOutputKw(Number(calculatedSolar.toFixed(1)));
  }, [solarIrradiance]);

  // Calculate Total Generation & Total Load
  const totalGenKw = Number((solarOutputKw + biogasOutputKw + mfcOutputKw).toFixed(1));
  
  const loadTier1 = tier1Active ? 6.5 : 0;
  const loadTier2 = tier2Active ? 21.0 : 0;
  const loadTier3 = tier3Active ? 12.5 : 0;
  const loadTier4 = tier4Active ? 15.0 : 0;
  const totalLoadKw = Number((loadTier1 + loadTier2 + loadTier3 + loadTier4).toFixed(1));

  // Net Balance (Positive = Charging Battery / Exporting, Negative = Discharging Battery)
  const netPowerKw = Number((totalGenKw - totalLoadKw).toFixed(1));

  // Handle Simulated Grid Outage
  const triggerGridOutageSimulation = () => {
    setGridMode('OUTAGE_SIMULATION');
    setGridAlarm('⚠️ NYSEG EXTERNAL UTILITY TRIP DETECTED! Shunt Tripping Tier 4 Non-Critical Loads...');
    setTier4Active(false); // Automated Load Shedding
    
    setTimeout(() => {
      setGridAlarm('✅ BESS Inverters & Biogas Generator Restabilized 60Hz Microgrid Frequency.');
    }, 3500);
  };

  const resetNominalGrid = () => {
    setGridMode('ISLANDED');
    setGridAlarm(null);
    setTier4Active(true);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      
      {/* 1. Header Banner & Grid Mode Switcher */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.9)',
        border: '1px solid rgba(0, 255, 255, 0.25)',
        borderRadius: '12px',
        padding: '16px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.4rem' }}>⚡</span>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#00FFFF', fontWeight: 800 }}>
              Microgrid Power Flow &amp; 500 kWh BESS Simulator
            </h3>
            <span style={{
              background: gridMode === 'ISLANDED' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.2)',
              border: `1px solid ${gridMode === 'ISLANDED' ? '#10b981' : '#38bdf8'}`,
              color: gridMode === 'ISLANDED' ? '#10b981' : '#38bdf8',
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 800
            }}>
              {gridMode === 'ISLANDED' ? '🏝️ 100% SOVEREIGN ISLANDED' : gridMode === 'GRID_TIED' ? '🌐 GRID-TIED NET METER' : '⚠️ SIMULATED UTILITY OUTAGE'}
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
            Finger Lakes Enclave Redundant Microgrid &bull; Shane’s Safety Isolation Transformer Protected
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setGridMode('ISLANDED')}
            style={{
              background: gridMode === 'ISLANDED' ? '#10b981' : 'rgba(255, 255, 255, 0.05)',
              color: '#ffffff',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            🏝️ Islanded Mode
          </button>
          <button
            onClick={() => setGridMode('GRID_TIED')}
            style={{
              background: gridMode === 'GRID_TIED' ? '#38bdf8' : 'rgba(255, 255, 255, 0.05)',
              color: '#ffffff',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            🌐 Grid-Tied Mode
          </button>
          <button
            onClick={gridMode === 'OUTAGE_SIMULATION' ? resetNominalGrid : triggerGridOutageSimulation}
            style={{
              background: gridMode === 'OUTAGE_SIMULATION' ? '#15803d' : '#ef4444',
              color: '#ffffff',
              border: 'none',
              padding: '8px 12px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 800,
              cursor: 'pointer'
            }}
          >
            {gridMode === 'OUTAGE_SIMULATION' ? '↺ Reset Nominal Grid' : '💥 Simulate Grid Blackout'}
          </button>
        </div>
      </div>

      {/* Alarm Banner if Active */}
      {gridAlarm && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          padding: '12px 16px',
          color: '#fca5a5',
          fontSize: '0.85rem',
          fontWeight: 700,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{gridAlarm}</span>
          <button onClick={() => setGridAlarm(null)} style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer', fontWeight: 800 }}>✕</button>
        </div>
      )}

      {/* 2. Top Summary KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
        
        {/* Total Generation */}
        <div style={{ background: 'rgba(15, 23, 42, 0.85)', border: '1px solid #38bdf8', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>TOTAL GENERATION</div>
          <div style={{ fontSize: '1.6rem', color: '#38bdf8', fontWeight: 800, margin: '4px 0' }}>{totalGenKw} kW</div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Solar ({solarOutputKw} kW) + Biogas ({biogasOutputKw} kW)</div>
        </div>

        {/* Total Load Demand */}
        <div style={{ background: 'rgba(15, 23, 42, 0.85)', border: '1px solid #f59e0b', borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>CAMPUS LOAD DEMAND</div>
          <div style={{ fontSize: '1.6rem', color: '#f59e0b', fontWeight: 800, margin: '4px 0' }}>{totalLoadKw} kW</div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Stage ({loadTier2} kW) + CEA Farm ({loadTier3} kW)</div>
        </div>

        {/* Net Battery Flow */}
        <div style={{ background: 'rgba(15, 23, 42, 0.85)', border: `1px solid ${netPowerKw >= 0 ? '#10b981' : '#f43f5e'}`, borderRadius: '10px', padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>NET POWER BUS BALANCE</div>
          <div style={{ fontSize: '1.6rem', color: netPowerKw >= 0 ? '#10b981' : '#f43f5e', fontWeight: 800, margin: '4px 0' }}>
            {netPowerKw >= 0 ? `+${netPowerKw} kW` : `${netPowerKw} kW`}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            {netPowerKw >= 0 ? 'Charging BESS Battery Bank' : 'Drawing from BESS Energy Vault'}
          </div>
        </div>

        {/* BESS State of Charge (SoC) */}
        <div style={{ background: 'rgba(15, 23, 42, 0.85)', border: '1px solid #00FFFF', borderRadius: '10px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>BESS 500 kWh SoC</span>
            <span style={{ fontSize: '0.75rem', color: '#00FFFF', fontWeight: 700 }}>400V DC</span>
          </div>
          <div style={{ fontSize: '1.6rem', color: '#00FFFF', fontWeight: 800, margin: '4px 0' }}>{batterySoc}%</div>
          {/* Progress bar */}
          <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${batterySoc}%`, height: '100%', background: '#00FFFF' }} />
          </div>
        </div>
      </div>

      {/* 3. Deep Interactive Simulator: Generation Controls vs Priority Loads */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.2fr) minmax(320px, 1fr)', gap: '20px' }}>
        
        {/* Generation Sources Sliders */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '1rem', color: '#f8fafc', fontWeight: 700 }}>
            ☀️ Dynamic Energy Generation Sources
          </h4>

          {/* Solar Irradiance Slider */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span>☀️ 150 kW Solar PV Array (Solar Irradiance):</span>
              <strong style={{ color: '#38bdf8' }}>{solarIrradiance} W/m² ({solarOutputKw} kW Output)</strong>
            </div>
            <input
              type="range" min="0" max="1000" step="25" value={solarIrradiance}
              onChange={e => setSolarIrradiance(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#38bdf8' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b', marginTop: '2px' }}>
              <span>0 (Midnight)</span>
              <span>400 (Overcast)</span>
              <span>750 (Finger Lakes Summer)</span>
              <span>1000 (Peak Sun)</span>
            </div>
          </div>

          {/* Biogas Output Slider */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '6px' }}>
              <span>🔥 35 kW Biogas Generator (Manure Digester):</span>
              <strong style={{ color: '#f59e0b' }}>{biogasOutputKw} kW</strong>
            </div>
            <input
              type="range" min="0" max="35" step="1" value={biogasOutputKw}
              onChange={e => setBiogasOutputKw(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
          </div>

          {/* 2-Ton Geothermal Heat Pump */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 700 }}>
              <span style={{ color: '#10b981' }}>♨️ 2-Ton Geothermal Heat Loop</span>
              <span style={{ color: '#ffffff' }}>COP: 4.8 &bull; 14.5 kW Thermal</span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
              Deep vertical earth heat exchangers maintaining 12°C baseline ground temperature, heating Earthships and Greenhouse in winter.
            </p>
          </div>

          {/* Microbial Fuel Cells */}
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 700 }}>
              <span style={{ color: '#c084fc' }}>🧫 Microbial Fuel Cells (MFC Wetland)</span>
              <span style={{ color: '#ffffff' }}>{mfcOutputKw} kW Continuous</span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.75rem', color: '#94a3b8' }}>
              Anaerobic electrogenic bacteria in wastewater treatment wetland producing continuous trickle-charge DC power.
            </p>
          </div>
        </div>

        {/* Priority Load Shedding Governor */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem', color: '#f8fafc', fontWeight: 700 }}>
            🎛️ Tiered Load Governance &amp; Automated Shedding
          </h4>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: '0 0 16px 0' }}>
            Shane’s safety isolation relays automatically drop non-essential loads if BESS capacity drops below 30% during islanding.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            
            {/* Tier 1 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #ef4444' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }}>TIER 1: Life Support &amp; Freeze Protection</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Well pumps, emergency egress, server core (6.5 kW)</div>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 800 }}>MANDATORY</span>
            </div>

            {/* Tier 2 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #00FFFF' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }}>TIER 2: The Living Stage Show Rig</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Main PA Sound, Wireless DMX, FOH Tower (21.0 kW)</div>
              </div>
              <input
                type="checkbox"
                checked={tier2Active}
                onChange={e => setTier2Active(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: '#00FFFF', cursor: 'pointer' }}
              />
            </div>

            {/* Tier 3 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #10b981' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }}>TIER 3: CEA Hydroponics &amp; Aeroponics</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>NFT pumps, high-pressure atomizers, grow LEDs (12.5 kW)</div>
              </div>
              <input
                type="checkbox"
                checked={tier3Active}
                onChange={e => setTier3Active(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: '#10b981', cursor: 'pointer' }}
              />
            </div>

            {/* Tier 4 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #a855f7' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ffffff' }}>TIER 4: EV Charging &amp; Utility Outlets</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Vehicle fast chargers, secondary workshop tools (15.0 kW)</div>
              </div>
              <input
                type="checkbox"
                checked={tier4Active}
                onChange={e => setTier4Active(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: '#a855f7', cursor: 'pointer' }}
              />
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
