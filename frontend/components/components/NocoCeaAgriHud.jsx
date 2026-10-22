import React, { useState } from 'react';

export default function NocoCeaAgriHud() {
  // VPD Environmental Inputs
  const [airTemp, setAirTemp] = useState(22.0); // °C
  const [leafTemp, setLeafTemp] = useState(20.5); // °C
  const [relativeHumidity, setRelativeHumidity] = useState(68); // %

  // Hydroponics & NFT Reservoir
  const [ecTarget, setEcTarget] = useState(1.4); // mS/cm
  const [ecCurrent, setEcCurrent] = useState(1.42);
  const [phCurrent, setPhCurrent] = useState(6.15);
  const [waterTemp, setWaterTemp] = useState(19.2); // °C
  const [dissolvedOxygen, setDissolvedOxygen] = useState(8.6); // mg/L
  const [koiWasteDosage, setKoiWasteDosage] = useState(85); // %

  // High-Pressure Aeroponics (HPA)
  const [hpaPressure, setHpaPressure] = useState(85); // PSI (80 - 100 PSI)
  const [sprayDurationSec, setSprayDurationSec] = useState(5);
  const [dwellDurationSec, setDwellDurationSec] = useState(180);
  const [isHpaPumping, setIsHpaPumping] = useState(false);

  // Livestock & Poultry Telemetry
  const [sheepPastureMoisture, setSheepPastureMoisture] = useState(72); // %
  const [sheepBarnFloorTemp, setSheepBarnFloorTemp] = useState(18.0); // °C
  const [alpacaShelterHumidity, setAlpacaShelterHumidity] = useState(58); // %
  const [poultryDoorOpen, setPoultryDoorOpen] = useState(true);
  const [dailyEggsCount, setDailyEggsCount] = useState(28);

  // Dosing Action Alerts
  const [dosingMessage, setDosingMessage] = useState(null);

  // Calculate Vapor Pressure Deficit (VPD)
  // SVP (Saturation Vapor Pressure) in kPa = 0.61078 * exp((17.27 * T) / (T + 237.3))
  const svpLeaf = 0.61078 * Math.exp((17.27 * leafTemp) / (leafTemp + 237.3));
  const svpAir = 0.61078 * Math.exp((17.27 * airTemp) / (airTemp + 237.3));
  const avpAir = svpAir * (relativeHumidity / 100.0);
  const vpdKpa = Number((svpLeaf - avpAir).toFixed(2));

  // Determine VPD Zone
  const getVpdZone = (val) => {
    if (val < 0.4) return { label: '⚠️ UNDER-TRANSPIRING (Fungal/Mold Risk)', color: '#ef4444' };
    if (val >= 0.4 && val < 0.8) return { label: '🌱 EARLY PROPAGATION / ROOTING', color: '#38bdf8' };
    if (val >= 0.8 && val <= 1.2) return { label: '✅ OPTIMAL VEGETATIVE VIGOR (0.8–1.2 kPa)', color: '#10b981' };
    if (val > 1.2 && val <= 1.5) return { label: '🌸 OPTIMAL FLOWERING & YIELD (1.2–1.5 kPa)', color: '#c084fc' };
    return { label: '⚠️ SEVERE TRANSPIRATION STRESS (Dry/Wilting)', color: '#ef4444' };
  };

  const vpdStatus = getVpdZone(vpdKpa);

  // Interactive Dosing Triggers
  const triggerDose = (nutrient) => {
    setDosingMessage(`🧪 Automated micro-dosing pump activated: Injected 45mL of ${nutrient}. Re-balancing EC/pH...`);
    setTimeout(() => {
      setDosingMessage(`✅ Closed-loop nutrient balance restored. EC: 1.40 mS/cm | pH: 6.12`);
      setTimeout(() => setDosingMessage(null), 4000);
    }, 2000);
  };

  const triggerHpaAtomize = () => {
    setIsHpaPumping(true);
    setTimeout(() => {
      setIsHpaPumping(false);
    }, 3000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      
      {/* 1. Header Banner */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.9)',
        border: '1px solid rgba(16, 185, 129, 0.35)',
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
            <span style={{ fontSize: '1.4rem' }}>🌱</span>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#10B981', fontWeight: 800 }}>
              Controlled Environment Agriculture (CEA) &amp; Livestock IoT HUD
            </h3>
            <span style={{
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid #10b981',
              color: '#10b981',
              padding: '3px 8px',
              borderRadius: '6px',
              fontSize: '0.75rem',
              fontWeight: 800
            }}>
              4,000 SF LIVING GREENHOUSE STAGE
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
            Automated NFT Lettuce Towers &bull; 50-Micron HPA Atomization &bull; Valais Sheep &amp; Alpaca Welfare
          </p>
        </div>

        {/* Quick Harvest Stat */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>DAILY CEA HARVEST</div>
            <div style={{ fontSize: '1.1rem', color: '#10b981', fontWeight: 800 }}>224 Heads / Day</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>COMMUNITY MEALS (THE MELT)</div>
            <div style={{ fontSize: '1.1rem', color: '#38bdf8', fontWeight: 800 }}>100% Free Organic Food</div>
          </div>
        </div>
      </div>

      {/* Dosing Alert Banner */}
      {dosingMessage && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.2)',
          border: '1px solid #10b981',
          borderRadius: '8px',
          padding: '12px 16px',
          color: '#a7f3d0',
          fontSize: '0.85rem',
          fontWeight: 700
        }}>
          {dosingMessage}
        </div>
      )}

      {/* 2. Top Grid: VPD Engine + Hydroponics Dosing System */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.2fr) minmax(320px, 1fr)', gap: '20px' }}>
        
        {/* VPD Optimization Engine */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
              💨 Vapor Pressure Deficit (VPD) Calculator
            </h4>
            <span style={{ fontSize: '0.75rem', color: vpdStatus.color, fontWeight: 700 }}>
              {vpdStatus.label}
            </span>
          </div>

          {/* Big VPD Value Card */}
          <div style={{
            background: 'radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.15) 0%, rgba(0,0,0,0.4) 100%)',
            border: `1.5px solid ${vpdStatus.color}`,
            borderRadius: '10px',
            padding: '20px',
            textAlign: 'center',
            marginBottom: '16px'
          }}>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 600 }}>CALCULATED TRANSPIRATION PRESSURE</div>
            <div style={{ fontSize: '2.5rem', color: vpdStatus.color, fontWeight: 900, margin: '4px 0' }}>
              {vpdKpa} <span style={{ fontSize: '1.2rem', fontWeight: 600 }}>kPa</span>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
              Target Leaf-to-Air Transpiration: <strong>0.80 – 1.20 kPa</strong>
            </div>
          </div>

          {/* Sliders for Air Temp, Leaf Temp, and RH */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            
            {/* Air Temp */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Ambient Air Temperature:</span>
                <strong style={{ color: '#38bdf8' }}>{airTemp}°C ({((airTemp * 9/5) + 32).toFixed(1)}°F)</strong>
              </div>
              <input
                type="range" min="15" max="32" step="0.5" value={airTemp}
                onChange={e => setAirTemp(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8' }}
              />
            </div>

            {/* Leaf Temp */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Infrared Leaf Canopy Temperature:</span>
                <strong style={{ color: '#10b981' }}>{leafTemp}°C ({((leafTemp * 9/5) + 32).toFixed(1)}°F)</strong>
              </div>
              <input
                type="range" min="14" max="30" step="0.5" value={leafTemp}
                onChange={e => setLeafTemp(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#10b981' }}
              />
            </div>

            {/* Relative Humidity */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Greenhouse Relative Humidity:</span>
                <strong style={{ color: '#00FFFF' }}>{relativeHumidity}% RH</strong>
              </div>
              <input
                type="range" min="30" max="95" step="1" value={relativeHumidity}
                onChange={e => setRelativeHumidity(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#00FFFF' }}
              />
            </div>
          </div>
        </div>

        {/* Closed-Loop Hydroponic & NFT Dosing */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
                🧪 Closed-Loop Hydroponic Dosing
              </h4>
              <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>NFT Reservoir: 1,500 Gal</span>
            </div>

            {/* Nutrient Grid Matrix */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
              
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>ELECTRICAL CONDUCTIVITY (EC)</div>
                <div style={{ fontSize: '1.25rem', color: '#00FFFF', fontWeight: 800 }}>{ecCurrent} mS/cm</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Target: {ecTarget} mS/cm</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>NUTRIENT pH LEVEL</div>
                <div style={{ fontSize: '1.25rem', color: '#10b981', fontWeight: 800 }}>{phCurrent} pH</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Target: 6.0 – 6.2</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>DISSOLVED OXYGEN (DO)</div>
                <div style={{ fontSize: '1.25rem', color: '#38bdf8', fontWeight: 800 }}>{dissolvedOxygen} mg/L</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Micro-bubble Aerator: Active</div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>RESERVOIR WATER TEMP</div>
                <div style={{ fontSize: '1.25rem', color: '#fbbf24', fontWeight: 800 }}>{waterTemp}°C</div>
                <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Geothermal Loop Buffered</div>
              </div>
            </div>
          </div>

          {/* Dosing Trigger Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => triggerDose('Solution A & B (Macronutrients)')}
                style={{
                  flex: 1,
                  background: 'rgba(0, 255, 255, 0.15)',
                  border: '1px solid #00FFFF',
                  color: '#00FFFF',
                  padding: '8px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                + Dose Nutrients A+B
              </button>
              <button
                onClick={() => triggerDose('pH Down (Phosphoric Acid)')}
                style={{
                  flex: 1,
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444',
                  color: '#f87171',
                  padding: '8px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                - Dose pH Down
              </button>
            </div>
            <button
              onClick={() => triggerDose('Koi Pond Effluent Organic Bloom')}
              style={{
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid #10b981',
                color: '#10b981',
                padding: '8px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              🐟 Blend Koi Pond Waste Organic Effluent ({koiWasteDosage}%)
            </button>
          </div>
        </div>
      </div>

      {/* 3. Bottom Grid: High-Pressure Aeroponics (HPA) & Livestock Welfare */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) minmax(340px, 1.2fr)', gap: '20px' }}>
        
        {/* HPA Atomizer */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
              💨 High-Pressure Aeroponics (HPA) Pulse Engine
            </h4>
            <span style={{
              background: isHpaPumping ? '#15803d' : '#334155',
              color: '#ffffff',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontWeight: 800
            }}>
              {isHpaPumping ? 'SPRAYING (50μm)' : 'DWELLING'}
            </span>
          </div>

          <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0 0 16px 0', lineHeight: 1.5 }}>
            Suspended root chambers atomized at <strong>{hpaPressure} PSI</strong>. Produces 50-micron droplet mist for maximum oxygenation without root rot.
          </p>

          <div style={{ display: 'flex', justifyContent: 'space-between', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', marginBottom: '14px' }}>
            <div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>PRESSURE ACCUMULATOR</div>
              <div style={{ fontSize: '1.2rem', color: '#00FFFF', fontWeight: 800 }}>{hpaPressure} PSI</div>
            </div>
            <div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>PULSE INTERVAL</div>
              <div style={{ fontSize: '1.2rem', color: '#10b981', fontWeight: 800 }}>{sprayDurationSec}s ON / {dwellDurationSec}s OFF</div>
            </div>
          </div>

          <button
            onClick={triggerHpaAtomize}
            disabled={isHpaPumping}
            style={{
              width: '100%',
              background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(16, 185, 129, 0.4))',
              border: '1px solid #00FFFF',
              color: '#ffffff',
              padding: '10px',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            {isHpaPumping ? '⚡ Atomizing Root Chambers...' : '▶ Manual 5s Root Chamber Atomize'}
          </button>
        </div>

        {/* Livestock & Free-Range Poultry Welfare */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '20px'
        }}>
          <h4 style={{ margin: '0 0 14px 0', color: '#f8fafc', fontSize: '1rem', fontWeight: 700 }}>
            🐑 Livestock &amp; Free-Range Poultry Welfare Telemetry
          </h4>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            
            {/* Valais Sheep */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f59e0b' }}>🐑 15 Valais Blacknose Sheep (Western Pasture)</div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Barn Floor Temp: <strong>{sheepBarnFloorTemp}°C</strong> &bull; Pasture Soil Moisture: <strong>{sheepPastureMoisture}%</strong>
                </div>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 700 }}>Fleece: $45/lb</span>
            </div>

            {/* Vicuña Alpacas */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#c084fc' }}>🦙 6 Vicuña Alpacas (Southern Shelter)</div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Shelter RH: <strong>{alpacaShelterHumidity}%</strong> &bull; Solar Trough Water: <strong>Nominal 15°C</strong>
                </div>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#c084fc', fontWeight: 700 }}>Fiber: $450/kg</span>
            </div>

            {/* Free-Range Poultry IPM */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8' }}>🐔 30 Free-Range Poultry (Biological IPM)</div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Automated Predator Door: <strong>{poultryDoorOpen ? 'OPEN (Day Grazing)' : 'LOCKED (Dusk Security)'}</strong> &bull; Eggs: <strong>{dailyEggsCount} Today</strong>
                </div>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 700 }}>95% Tick Control</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
