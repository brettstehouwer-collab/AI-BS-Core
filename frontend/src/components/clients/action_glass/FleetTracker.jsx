import React from 'react';

export default function FleetTracker() {
  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ color: '#3fb950', margin: '0 0 5px 0', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
        Fleet & Branding Deployment Tracker
      </h2>
      <p style={{ marginBottom: '20px' }}>Ensuring maximum local visibility for the "Free Mobile Service" fleet vans across West Michigan corridors.</p>

      <div style={{ display: 'flex', gap: '20px' }}>
        
        {/* Strategic Parking Zones */}
        <div style={{ flex: 1, background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 15px 0' }}>Strategic High-Visibility Parking Targets</h3>
          <p style={{ fontSize: '12px', color: '#8b949e', marginTop: '-10px', marginBottom: '15px' }}>
            Instruct mobile techs to park in these high-traffic retail lots during lunch breaks instead of hiding in back alleys.
          </p>
          
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <li style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input type="checkbox" style={{ width: '18px', height: '18px' }} />
              <div>
                <strong>Chicago Drive Corridor (Grandville)</strong>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>Target: Near Cabela's / Target retail lots</div>
              </div>
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input type="checkbox" style={{ width: '18px', height: '18px' }} />
              <div>
                <strong>28th Street SW (Wyoming)</strong>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>Target: Near Rogers Plaza / Food courts</div>
              </div>
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input type="checkbox" style={{ width: '18px', height: '18px' }} />
              <div>
                <strong>US-31 / West Shore (Holland)</strong>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>Target: Near Meijer / Strip malls</div>
              </div>
            </li>
          </ul>
        </div>

        {/* Brand Authority Checklist */}
        <div style={{ flex: 1, background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
          <h3 style={{ margin: '0 0 15px 0' }}>Digital Trust & Branding Checklist</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ background: '#0d1117', padding: '15px', borderRadius: '6px', borderLeft: '4px solid #3fb950' }}>
              <h4 style={{ margin: '0 0 5px 0', color: 'white' }}>Google Screened Badge</h4>
              <p style={{ margin: 0, fontSize: '13px', color: '#8b949e' }}>Required for LSA (Local Services Ads) to establish instant trust over Safelite.</p>
              <button style={{ marginTop: '10px', background: 'transparent', border: '1px solid #30363d', color: '#c9d1d9', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>Check Verification Status</button>
            </div>

            <div style={{ background: '#0d1117', padding: '15px', borderRadius: '6px', borderLeft: '4px solid #1f6feb' }}>
              <h4 style={{ margin: '0 0 5px 0', color: 'white' }}>High-Contrast Fleet Wraps</h4>
              <p style={{ margin: 0, fontSize: '13px', color: '#8b949e' }}>Verify that the (616) 669-8888 phone number and "$0 Deductible" message are readable from 50 feet away.</p>
            </div>

            <div style={{ background: '#0d1117', padding: '15px', borderRadius: '6px', borderLeft: '4px solid #d29922' }}>
              <h4 style={{ margin: '0 0 5px 0', color: 'white' }}>Click-to-Call Setup</h4>
              <p style={{ margin: 0, fontSize: '13px', color: '#8b949e' }}>Ensure mobile searchers see a direct "Call Now" button for emergency roadside cracks.</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
