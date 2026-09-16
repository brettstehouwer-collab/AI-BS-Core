import React, { useState } from 'react';

export default function ActionGlassQuoter({ backendUrl }) {
  const [vehicle, setVehicle] = useState({ year: '2022', make: 'Ford', model: 'F-150' });
  const [hasADAS, setHasADAS] = useState(true);
  const [wipers, setWipers] = useState(false);
  const [insurance, setInsurance] = useState(false);

  const basePrice = 350;
  const adasPrice = 275;
  const wipersPrice = 45;

  const total = basePrice + (hasADAS ? adasPrice : 0) + (wipers ? wipersPrice : 0);

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ color: '#58a6ff', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
        Interactive Lead Quoter Widget (Simulator)
      </h2>
      <p>This is a live simulator of the exact widget Action Glass will embed on their public website to capture leads instantly before they bounce to Safelite.</p>

      <div style={{ display: 'flex', gap: '30px', marginTop: '20px' }}>
        {/* Input Form */}
        <div style={{ flex: 1, background: '#161b22', padding: '20px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <h3 style={{ marginTop: 0 }}>Vehicle Details</h3>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <input type="text" value={vehicle.year} onChange={e => setVehicle({...vehicle, year: e.target.value})} placeholder="Year" style={{ width: '80px', padding: '8px', background: '#0d1117', color: '#fff', border: '1px solid #30363d', borderRadius: '4px' }} />
            <input type="text" value={vehicle.make} onChange={e => setVehicle({...vehicle, make: e.target.value})} placeholder="Make" style={{ flex: 1, padding: '8px', background: '#0d1117', color: '#fff', border: '1px solid #30363d', borderRadius: '4px' }} />
            <input type="text" value={vehicle.model} onChange={e => setVehicle({...vehicle, model: e.target.value})} placeholder="Model" style={{ flex: 1, padding: '8px', background: '#0d1117', color: '#fff', border: '1px solid #30363d', borderRadius: '4px' }} />
          </div>

          <h3 style={{ marginTop: 0 }}>Required Services</h3>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', cursor: 'pointer' }}>
            <input type="checkbox" checked={true} readOnly style={{ width: '18px', height: '18px' }} />
            <span>Full Windshield Replacement (OEM Quality Glass)</span>
          </label>
          
          <div style={{ padding: '10px', background: 'rgba(210, 153, 34, 0.1)', border: '1px solid #d29922', borderRadius: '4px', marginBottom: '10px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
              <input type="checkbox" checked={hasADAS} onChange={(e) => setHasADAS(e.target.checked)} style={{ width: '18px', height: '18px' }} />
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 'bold', color: '#d29922' }}>ADAS Safety Camera Recalibration</span>
                <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#8b949e' }}>Required for modern vehicles with lane-assist/auto-braking to ensure safety.</p>
              </div>
            </label>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', cursor: 'pointer' }}>
            <input type="checkbox" checked={wipers} onChange={(e) => setWipers(e.target.checked)} style={{ width: '18px', height: '18px' }} />
            <span>Add Premium Wiper Blades (Protects New Glass)</span>
          </label>

          <h3 style={{ marginTop: 0 }}>Insurance Coverage</h3>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
            <input type="checkbox" checked={insurance} onChange={(e) => setInsurance(e.target.checked)} style={{ width: '18px', height: '18px' }} />
            <span>I have Full Glass Coverage ($0 Deductible)</span>
          </label>

        </div>

        {/* Live Estimate Output */}
        <div style={{ flex: 1, background: '#0d1117', padding: '20px', borderRadius: '8px', border: '1px solid #58a6ff', display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginTop: 0, color: '#58a6ff', textAlign: 'center' }}>Instant Quote</h3>
          
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Glass & Labor (Base)</span>
              <span>${basePrice}</span>
            </div>
            
            {hasADAS && (
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#d29922' }}>
                <span>ADAS Dynamic Recalibration</span>
                <span>${adasPrice}</span>
              </div>
            )}
            
            {wipers && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Premium Wiper Blades</span>
                <span>${wipersPrice}</span>
              </div>
            )}
          </div>

          <div style={{ borderTop: '1px solid #30363d', paddingTop: '20px', marginTop: '20px', textAlign: 'center' }}>
            {insurance ? (
              <div>
                <h1 style={{ color: '#3fb950', margin: '0 0 10px 0' }}>$0 Out of Pocket</h1>
                <p style={{ margin: 0, fontSize: '14px', color: '#8b949e' }}>We handle the insurance claim entirely.</p>
              </div>
            ) : (
              <h1 style={{ margin: 0 }}>${total} <span style={{ fontSize: '14px', fontWeight: 'normal', color: '#8b949e' }}>+ tax</span></h1>
            )}
          </div>

          <button style={{ 
            marginTop: '30px', 
            padding: '15px', 
            background: '#238636', 
            color: 'white', 
            border: 'none', 
            borderRadius: '6px', 
            fontSize: '18px', 
            fontWeight: 'bold', 
            cursor: 'pointer' 
          }}>
            Book Mobile Service Now
          </button>
          <p style={{ textAlign: 'center', fontSize: '12px', marginTop: '10px', color: '#8b949e' }}>
            Free mobile service in Jenison, Allendale, and Grand Rapids.
          </p>
        </div>
      </div>
    </div>
  );
}
