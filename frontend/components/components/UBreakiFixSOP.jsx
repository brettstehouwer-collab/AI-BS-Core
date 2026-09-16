import React, { useState } from 'react';

export default function UBreakiFixSOP() {
  const [activeTab, setActiveTab] = useState('lead_ops'); // 'lead_ops', 'training', 'pricing', 'intake', 'ber', 'operations', 'chemical'
  const [activeBatch, setActiveBatch] = useState('batch1'); // For Tab 7 Lead Ops

  return (
    <div className="aibs-sop-root" style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%', boxSizing: 'border-box' }}>
      <style>{`
        .aibs-sop-root {
          box-sizing: border-box;
          max-width: 100vw;
          overflow-x: hidden;
        }
        .aibs-sop-ribbon {
          display: flex;
          gap: 8px;
          margin-top: 16px;
          overflow-x: auto;
          flex-wrap: nowrap;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
          padding-bottom: 6px;
        }
        @media (min-width: 1200px) {
          .aibs-sop-ribbon {
            flex-wrap: wrap !important;
          }
        }
        .aibs-sop-btn {
          white-space: nowrap !important;
          flex-shrink: 0 !important;
          min-height: 40px;
          touch-action: manipulation;
        }
        .aibs-sop-grid-2col {
          display: grid;
          grid-template-columns: 1.2fr 1fr;
          gap: 20px;
        }
        .aibs-sop-grid-equal {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        @media (max-width: 880px) {
          .aibs-sop-grid-2col,
          .aibs-sop-grid-equal {
            grid-template-columns: 1fr !important;
          }
        }
        .aibs-table-wrap {
          width: 100%;
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
      `}</style>
      
      {/* SOP Header & Navigation */}
      <div style={{ background: 'rgba(15, 23, 42, 0.85)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '14px', padding: '20px' }}>
        <h2 style={{ margin: '0 0 6px 0', fontSize: '1.25rem', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          🏢 uBreakiFix Academy & Lead Tech Field SOPs
        </h2>
        <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8' }}>
          Accelerated training modules, lead technician operations, 2024–2025 pricing benchmarks, and corporate escalation procedures for franchise operations.
        </p>

        <div className="aibs-sop-ribbon">
          {[
            { id: 'lead_ops', label: '🗂️ Lead Tech Operations Guide (Batches 1–6)' },
            { id: 'training', label: '14-Day Training & Core Pillars' },
            { id: 'pricing', label: '2024–2025 Pricing Matrix & Store Policies' },
            { id: 'intake', label: 'Asurion Claim & IQC Workflow' },
            { id: 'ber', label: 'BER Escalation Protocol' },
            { id: 'operations', label: 'Store Operations & Turnaround' },
            { id: 'chemical', label: 'Chemical Extraction Protocol' }
          ].map(tab => (
            <button
              key={tab.id}
              className="aibs-sop-btn"
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(99, 102, 241, 0.25))' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${activeTab === tab.id ? '#c084fc' : 'rgba(255,255,255,0.1)'}`,
                color: activeTab === tab.id ? '#fff' : '#cbd5e1',
                padding: '8px 14px',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: activeTab === tab.id ? 700 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ============================================== */}
      {/* TAB 0: LEAD TECHNICIAN OPERATIONS GUIDE (BATCHES 1-6) */}
      {/* ============================================== */}
      {activeTab === 'lead_ops' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Header Banner */}
          <div style={{ background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.9), rgba(15, 23, 42, 0.95))', border: '1px solid rgba(168, 85, 247, 0.4)', borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <h3 style={{ margin: '0 0 6px 0', fontSize: '1.2rem', color: '#c084fc' }}>
                  🗂️ Lead Technician Operations Guide & Visual Protocols
                </h3>
                <p style={{ margin: 0, fontSize: '0.84rem', color: '#94a3b8' }}>
                  From Front-of-House liability defense to high-risk micro-soldering, chemical extraction, and store metrics governance.
                </p>
              </div>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, background: 'rgba(168, 85, 247, 0.2)', border: '1px solid #c084fc', color: '#c084fc', padding: '4px 10px', borderRadius: '6px' }}>
                FRANCHISE LEAD STANDARD
              </span>
            </div>

            {/* Batch Selector Ribbon */}
            <div style={{ display: 'flex', gap: '6px', marginTop: '16px', flexWrap: 'wrap' }}>
              {[
                { id: 'batch1', num: '1', title: 'Front-of-House & Liability Defense' },
                { id: 'batch2', num: '2', title: 'The Professional Repair Bench' },
                { id: 'batch3', num: '3', title: 'Smartphone Architecture Evolution' },
                { id: 'batch4', num: '4', title: 'Consoles & Tablets Hardware Hazards' },
                { id: 'batch5', num: '5', title: 'High-Liability Battery Extraction' },
                { id: 'batch6', num: '6', title: 'Lead Technician Focus: Managing Metrics' }
              ].map(b => (
                <button
                  key={b.id}
                  onClick={() => setActiveBatch(b.id)}
                  style={{
                    background: activeBatch === b.id ? 'rgba(56, 189, 248, 0.25)' : 'rgba(0,0,0,0.4)',
                    border: `1px solid ${activeBatch === b.id ? '#38bdf8' : 'rgba(255,255,255,0.1)'}`,
                    color: activeBatch === b.id ? '#38bdf8' : '#cbd5e1',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '0.78rem',
                    fontWeight: activeBatch === b.id ? 700 : 500,
                    cursor: 'pointer'
                  }}
                >
                  <strong>Batch {b.num}:</strong> {b.title}
                </button>
              ))}
            </div>
          </div>

          {/* BATCH 1 CONTENT */}
          {activeBatch === 'batch1' && (
            <div className="aibs-sop-grid-2col">
              <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#38bdf8' }}>
                  📋 Batch 1: Front-of-House & Liability Defense
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  Visualizing the Flow: The NextGen Portal Intake Validation Interface
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  This stage establishes the high-liability, process-driven tone of the entire repair lifecycle. The Lead Technician oversees the service counter intake where every incoming device is thoroughly audited against carrier standards before a screw is touched.
                </p>

                <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '14px', marginBottom: '14px' }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#34d399', marginBottom: '8px' }}>
                    ✅ Mandatory NextGen Portal Validation Points:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.82rem', lineHeight: '1.6' }}>
                    <li><strong>Asurion Audit Readiness:</strong> Exact hardware IMEI match (*#06# vs claim) to prevent $200+ chargebacks.</li>
                    <li><strong>Liability Waiver Sign-off:</strong> Customer electronic signature acknowledging pre-existing damage & potential data loss.</li>
                    <li><strong>LCI Moisture Check:</strong> Visual verification that liquid indicators remain pristine white/silver.</li>
                    <li><strong>Chassis Geometric Tolerance:</strong> Verifying rails are within 2mm tolerance to prevent instant OLED stress fractures.</li>
                  </ul>
                </div>
              </div>

              <div style={{ background: '#090e17', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#34d399' }}>
                    🛡️ Counter Defense Protocol
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.82rem' }}>
                    <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
                      <strong style={{ color: '#34d399' }}>The Golden Rule:</strong> <em>"If a flaw is not documented during intake, the store absorbs liability for the cost of repair."</em>
                    </div>
                    <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '10px', borderRadius: '6px', borderLeft: '3px solid #ef4444' }}>
                      <strong style={{ color: '#f87171' }}>Zero-Refusal Policy:</strong> Never reject a claim verbally at the counter without logging the diagnostic evidence in NextGen Portal to generate the official claim release token.
                    </div>
                  </div>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', fontSize: '0.76rem', color: '#94a3b8', marginTop: '16px' }}>
                  💡 <strong>Lead Tech Checklist:</strong> Audit the first 3 tickets created by junior technicians every morning to ensure photo attachments are legible.
                </div>
              </div>
            </div>
          )}

          {/* BATCH 2 CONTENT */}
          {activeBatch === 'batch2' && (
            <div className="aibs-sop-grid-equal">
              <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#38bdf8' }}>
                  🔬 Batch 2: The Professional Repair Bench
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  The Tech Lead's Workspace: Setting the Standard for Precision & Safety
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  Building directly upon professional liability, the Tech Lead maintains a benchmark workspace. Grounded with ESD-safe blue anti-static mats and equipped with surgical-grade diagnostics, this bench is the cleanroom standard of the store.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.82rem' }}>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', borderLeft: '3px solid #38bdf8' }}>
                    <strong style={{ color: '#fff' }}>1. Blue Anti-Static Mat (ESD-Safe):</strong> Grounded with 1MΩ resistor to eliminate electrostatic discharge that kills micro-ICs.
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', borderLeft: '3px solid #38bdf8' }}>
                    <strong style={{ color: '#fff' }}>2. 4K Microscopic Camera:</strong> High-magnification trinocular scope for inspecting cracked solder joints, 0201 passives, and FPC pins.
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', borderLeft: '3px solid #38bdf8' }}>
                    <strong style={{ color: '#fff' }}>3. HEPA Fume Extractor Arm:</strong> High-volume active carbon filtration to capture toxic rosin fluxes and lead fumes.
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', borderLeft: '3px solid #38bdf8' }}>
                    <strong style={{ color: '#fff' }}>4. 4-Digit Calibrated DC Power Supply:</strong> 0-30V / 0-5A current monitor to detect sub-milliamp logic board short circuits.
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px', borderLeft: '3px solid #f87171' }}>
                    <strong style={{ color: '#f87171' }}>5. Fireproof Battery Charging Bag & Sand Bucket:</strong> Mandatory containment apparatus for isolated and swollen lithium-ion cells.
                  </div>
                </div>
              </div>

              <div style={{ background: '#090e17', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#c084fc' }}>
                  🛠️ Daily Bench Calibration Routine
                </h3>
                <ul style={{ margin: '0 0 16px 0', paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.84rem', lineHeight: '1.6' }}>
                  <li><strong>09:45 AM:</strong> Test ESD wrist strap resistance with multi-meter.</li>
                  <li><strong>09:50 AM:</strong> Inspect soldering iron tips for oxidation; clean with brass wool and lead-free tinning compound.</li>
                  <li><strong>09:55 AM:</strong> Verify DC bench supply output voltage matches multimeter reference (5.00V ± 0.02V).</li>
                  <li><strong>10:00 AM:</strong> Confirm sand bucket is unblocked and clear of clutter.</li>
                </ul>

                <div style={{ background: 'rgba(168, 85, 247, 0.1)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '8px', padding: '14px', fontSize: '0.8rem', color: '#e2e8f0' }}>
                  ⚠️ <strong>Tech Lead Enforcement:</strong> Any technician found working without an ESD mat or using a damaged battery charging bag is subject to immediate safety re-certification.
                </div>
              </div>
            </div>
          )}

          {/* BATCH 3 CONTENT */}
          {activeBatch === 'batch3' && (
            <div className="aibs-sop-grid-equal">
              <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#f87171' }}>
                  📱 Batch 3: Smartphone Architecture Evolution
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  Serialization Hazards: Legacy Modular vs. Modern Stacked Flagship Boards
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  Modern smartphones have evolved from simple modular screw assemblies into high-density stacked logic boards tied to cryptographic serialization. A simple mistake during teardown now poses catastrophic financial liability.
                </p>

                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#f87171', marginBottom: '6px' }}>
                    ⚠️ Flagged Serialization Pain Points:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#fca5a5', fontSize: '0.82rem', lineHeight: '1.6' }}>
                    <li><strong>Face ID Sensor Arrays:</strong> The Flood Illuminator and Dot Projector are cryptographically paired to the Secure Enclave. Tearing this flex permanently disables Face ID.</li>
                    <li><strong>Serialized Battery BMS:</strong> Modern batteries contain an EEPROM microcontroller. Swapping cells without spot-welding the OEM BMS triggers "Unknown Part" OS warnings and disables Battery Health metrics.</li>
                    <li><strong>TrueTone & Display ICs:</strong> Screens require EEPROM readout & write-back (via JC V1SE or QianLi programmer) or official GSX/AST2 cloud authorization.</li>
                  </ul>
                </div>
              </div>

              <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#38bdf8' }}>
                  🏗️ Architectural Comparison Matrix
                </h3>
                <div className="aibs-table-wrap">
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}>
                      <th style={{ padding: '8px' }}>Feature</th>
                      <th style={{ padding: '8px' }}>Older (iPhone 11)</th>
                      <th style={{ padding: '8px' }}>Modern (14/15/16 Pro)</th>
                    </tr>
                  </thead>
                  <tbody style={{ color: '#cbd5e1' }}>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px', fontWeight: 600 }}>Logic Board</td>
                      <td style={{ padding: '8px' }}>Single-layer PCB</td>
                      <td style={{ padding: '8px', color: '#f87171' }}>Dual-layer Stacked Sandwich</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px', fontWeight: 600 }}>Back Glass</td>
                      <td style={{ padding: '8px' }}>Laser-fused Housing</td>
                      <td style={{ padding: '8px', color: '#34d399' }}>Modular Removable Glass</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px', fontWeight: 600 }}>Parts Pairing</td>
                      <td style={{ padding: '8px' }}>Basic Display/Batt</td>
                      <td style={{ padding: '8px', color: '#f87171' }}>100% Cryptographic Lockout</td>
                    </tr>
                  </tbody>
                </table>
                </div>

                <div style={{ background: '#090e17', padding: '12px', borderRadius: '8px', fontSize: '0.78rem', color: '#94a3b8', marginTop: '16px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  💡 <strong>Lead Tip:</strong> Never quote a flat screen fee without checking if the customer requires TrueTone transfer or OEM System Configuration pairing.
                </div>
              </div>
            </div>
          )}

          {/* BATCH 4 CONTENT */}
          {activeBatch === 'batch4' && (
            <div className="aibs-sop-grid-equal">
              <div style={{ background: '#090e17', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#c084fc' }}>
                  🎮 PS5 APU Liquid Metal Compound Hazard
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  The Shimmering Pool: High Electrical Conductivity Risks
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  Lifting the PS5 heatsink reveals a shimmering pool of liquid metal (Gallium-Indium alloy) on the custom AMD APU processor. Unlike non-conductive thermal paste, liquid metal conducts full electrical current.
                </p>

                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '12px', fontSize: '0.82rem', color: '#fca5a5' }}>
                  <strong>🚨 The PS5 Liquid Metal Rule:</strong> A single microscopic droplet of liquid metal splashing onto surrounding motherboard SMD capacitors will cause an instantaneous short-circuit, permanently destroying the console during first boot. Always tape foam barriers and use silicone swab applicators.
                </div>
              </div>

              <div style={{ background: '#090e17', border: '1px solid rgba(234, 179, 8, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#facc15' }}>
                  📱 Surface Pro & Laminated Tablet Screen Fragility
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  High-Tension Prying Hazards & Thermal Separation
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  Microsoft Surface Pro and iPad Pro screens utilize ultra-thin glass laminated directly to LCD/OLED panels with high-bond adhesive tape.
                </p>

                <div style={{ background: 'rgba(234, 179, 8, 0.1)', border: '1px solid rgba(234, 179, 8, 0.3)', borderRadius: '8px', padding: '12px', fontSize: '0.82rem', color: '#fde047' }}>
                  <strong>⚠️ Prying Rule:</strong> Never apply upward torque with metal pry tools. Heat the perimeter to 75°C and slide plastic playing cards horizontally. Prying unevenly shatters the underlying panel into thousands of dangerous shards.
                </div>
              </div>
            </div>
          )}

          {/* BATCH 5 CONTENT */}
          {activeBatch === 'batch5' && (
            <div className="aibs-sop-grid-2col">
              <div style={{ background: '#090e17', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.15rem', color: '#f87171' }}>
                  🧪 Batch 5: High-Liability Battery Extraction (Chemical Protocol)
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  The Precision Pipette Solvent Procedure: Zero-Prying Compliance
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  This is the single most critical safety protocol in consumer electronics repair. Glued iPad and tablet lithium pouch cells are under high mechanical tension. Prying them with tools bends the internal separator layers, causing catastrophic thermal runaway.
                </p>

                <div style={{ background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', padding: '14px', marginBottom: '14px' }}>
                  <div style={{ fontSize: '0.88rem', fontWeight: 800, color: '#f87171', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    ⛔ WARNING: HIGH-LIABILITY PROTOCOL — NO PRYING PERMITTED
                  </div>
                  <ul style={{ margin: '8px 0 0 0', paddingLeft: '20px', color: '#fca5a5', fontSize: '0.82rem', lineHeight: '1.6' }}>
                    <li><strong>Discharge First:</strong> Ensure battery is drained below 25% charge before attempting extraction.</li>
                    <li><strong>99% IPA Chemical Injection:</strong> Use a precision dropper or blunt syringe to dispense 2-3 mL of 99% Isopropyl Alcohol directly along the adhesive margin.</li>
                    <li><strong>Capillary Dissolution:</strong> Wait a full 3 to 5 minutes for the solvent to dissolve the adhesive matrix.</li>
                    <li><strong>Floss-Saw Severing:</strong> Slide Kevlar thread or dental floss horizontally beneath the pouch to shear the adhesive without flexing the battery.</li>
                  </ul>
                </div>
              </div>

              <div style={{ background: '#090e17', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#34d399' }}>
                    🧯 Thermal Runaway Reaction Steps
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '6px' }}>
                      <strong style={{ color: '#fff' }}>Step 1: Smell Bubblegum / Sweet Odor?</strong><br/>
                      <span style={{ color: '#f87171' }}>Electrolyte seal breached. Cease work immediately.</span>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '6px' }}>
                      <strong style={{ color: '#fff' }}>Step 2: Smoke or Hissing?</strong><br/>
                      <span style={{ color: '#f87171' }}>Drop device into the metal sand bucket immediately using tongs.</span>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '6px' }}>
                      <strong style={{ color: '#fff' }}>Step 3: Post-Event Quarantine</strong><br/>
                      <span style={{ color: '#34d399' }}>Leave submerged under sand for a minimum of 2 hours.</span>
                    </div>
                  </div>
                </div>

                <div style={{ background: '#090e17', padding: '12px', borderRadius: '8px', fontSize: '0.76rem', color: '#94a3b8', marginTop: '16px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  💡 <strong>Lead Tech Mandate:</strong> Inspect all scrap battery disposal bins weekly and ensure sand buckets are dry and uncompacted.
                </div>
              </div>
            </div>
          )}

          {/* BATCH 6 CONTENT */}
          {activeBatch === 'batch6' && (
            <div className="aibs-sop-grid-2col">
              <div style={{ background: '#090e17', border: '1px solid rgba(168, 85, 247, 0.4)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '1.15rem', color: '#c084fc' }}>
                  📊 Batch 6: Lead Technician Focus (Managing Store Metrics)
                </h3>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#94a3b8' }}>
                  Transitioning from Individual Repairer to Store Quality & Compliance Officer
                </h4>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6', margin: '0 0 14px 0' }}>
                  The Lead Technician's primary duty shifts from bench repairs to store performance analytics. The Tech Lead manages the live digital dashboard to ensure the shop meets all Asurion and OEM service SLAs.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                  <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>REWORK METRIC (Target &lt; 2%)</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#38bdf8' }}>0.8%</div>
                    <div style={{ fontSize: '0.72rem', color: '#34d399' }}>🟢 Franchise Top Tier</div>
                  </div>
                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>QUEUE TRIAGE (Turnaround)</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#34d399' }}>52 min</div>
                    <div style={{ fontSize: '0.72rem', color: '#34d399' }}>🟢 Within 2-hr SLA</div>
                  </div>
                  <div style={{ background: 'rgba(234, 179, 8, 0.1)', border: '1px solid rgba(234, 179, 8, 0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>CORE RETURNS COMPLIANCE</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#facc15' }}>98.4%</div>
                    <div style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>📦 OEM Harvest Audited</div>
                  </div>
                  <div style={{ background: 'rgba(168, 85, 247, 0.1)', border: '1px solid rgba(168, 85, 247, 0.3)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>HOME+ ATTACH RATE</div>
                    <div style={{ fontSize: '1.4rem', fontWeight: 900, color: '#c084fc' }}>14.2%</div>
                    <div style={{ fontSize: '0.72rem', color: '#34d399' }}>📈 Above Regional Avg</div>
                  </div>
                </div>
              </div>

              <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#38bdf8' }}>
                  🎯 The 3 Pillars of Lead Tech Governance
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.82rem' }}>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#38bdf8' }}>1. Rework Triage & Root Cause Analysis:</strong> When a device returns within 30 days, the Tech Lead conducts a mandatory teardown audit to identify whether failure was caused by part defect (DOA) or technician error (torn flex, missed screw).
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#34d399' }}>2. Dynamic Bench Queue Triage:</strong> Dynamically assigning quick screen swaps to apprentices while routing complex micro-soldering, liquid metal, and frame straightening to senior techs.
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '6px' }}>
                    <strong style={{ color: '#facc15' }}>3. OEM Core Box Shipping:</strong> Ensuring all harvested cracked OEM OLED displays and dead batteries are boxed and returned within 7 days to prevent $150/unit non-return penalties.
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      {/* ============================================== */}
      {/* TAB 1: 14-DAY TRAINING & CORE PILLARS */}
      {/* ============================================== */}
      {activeTab === 'training' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
          
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#38bdf8' }}>Core Competency Pillars</h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.88rem', lineHeight: '1.6' }}>
              <li><strong style={{ color: '#fff' }}>Intake & Initial Quality Check (IQC):</strong> Documenting every pre-existing flaw. If a flaw is not documented during intake, the store absorbs liability for the cost of repair.</li>
              <li><strong style={{ color: '#fff' }}>Thermal & Mechanical Disassembly:</strong> Managing temperature thresholds, pry angles, and adhesive softening without tearing underlying cables or OLEDs.</li>
              <li><strong style={{ color: '#fff' }}>Component Tracking & Screw Mapping:</strong> Maintaining strict segregation of screws. Driving a long screw into a short screw standoff causes permanent board separation ("long-screw damage").</li>
              <li><strong style={{ color: '#fff' }}>OEM Calibration & Diagnostics:</strong> Running proprietary software suites to pair replacement hardware and clear serial warnings (Samsung GSPN, Google AST, Apple GSX/AST2).</li>
            </ul>
          </div>

          <div style={{ background: '#090e17', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '12px', padding: '20px', overflowX: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#34d399' }}>14-Day Accelerated Training Schedule</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(16, 185, 129, 0.4)', color: '#34d399' }}>
                  <th style={{ padding: '10px' }}>Phase</th>
                  <th style={{ padding: '10px' }}>Days</th>
                  <th style={{ padding: '10px' }}>Focus Areas</th>
                  <th style={{ padding: '10px' }}>Practical Drills</th>
                </tr>
              </thead>
              <tbody style={{ color: '#cbd5e1' }}>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Pillar 1: Safety & Disassembly Fundamentals</td>
                  <td style={{ padding: '10px' }}>Days 1–3</td>
                  <td style={{ padding: '10px' }}>• Lithium-ion safety & thermal runaway procedures<br/>• Heat plate / hot air temperature standards (65°C to 80°C max on OLEDs)<br/>• Tool hierarchy: nylon spudgers, suction pliers, iFlex, 99% IPA</td>
                  <td style={{ padding: '10px' }}>Practice screw mapping grids on scrap boards; drill zero-metal contact rules on battery extractions using IPA.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Pillar 2: Apple Architecture</td>
                  <td style={{ padding: '10px' }}>Days 4–6</td>
                  <td style={{ padding: '10px' }}>• iPhone display and battery assemblies<br/>• Ambient light sensor / proximity flex transfers<br/>• Face ID flood illuminator preservation</td>
                  <td style={{ padding: '10px' }}>Teardown and reassembly of iPhone housings; test display bracket transfers without tearing top speaker flexes.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Pillar 3: Android Architecture</td>
                  <td style={{ padding: '10px' }}>Days 7–9</td>
                  <td style={{ padding: '10px' }}>• Rear curved glass removal using heat/alcohol<br/>• Service pack assembly swaps (OLED + midframe transfer)<br/>• Sub-board and interconnect cable routing</td>
                  <td style={{ padding: '10px' }}>Disassemble back glass without stripping film; extract stubborn pull-tab batteries.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Pillar 4: OEM Calibration Software</td>
                  <td style={{ padding: '10px' }}>Days 10–11</td>
                  <td style={{ padding: '10px' }}>• Samsung GSPN platform<br/>• Google AST<br/>• Apple System Configuration workflows</td>
                  <td style={{ padding: '10px' }}>Walk through standard diagnostic execution flows; review USB-debugging failures.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Pillar 5: Portal Operations & Metrics</td>
                  <td style={{ padding: '10px' }}>Days 12–13</td>
                  <td style={{ padding: '10px' }}>• NextGen Portal ticket creation & check-out<br/>• Reconciling OEM parts against insurance claims<br/>• Front-counter intake & de-escalation</td>
                  <td style={{ padding: '10px' }}>Run timed intake simulations (check-in, diagnostic, ticket generation in under 4 mins).</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Pillar 6: Speed & QA Testing</td>
                  <td style={{ padding: '10px' }}>Day 14</td>
                  <td style={{ padding: '10px' }}>• Post-repair QA checklist (charging current, digitizer grid, proximity sensor, attenuation)<br/>• Clean room / dust mitigation</td>
                  <td style={{ padding: '10px' }}>Full cycle practice: screen replacement from intake to post-QC in under 45 minutes.</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#f87171' }}>⚠️ Critical Technical Hazards</h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#fca5a5', fontSize: '0.85rem', lineHeight: '1.6' }}>
              <li><strong>Long-Screw Damage:</strong> iPhone logic boards route critical signal traces directly beneath screw standoffs. Driving an incorrect screw into a standoff can sever traces, resulting in permanent boot-loops. Always use a magnetic screw mat.</li>
              <li><strong>Pry Tool Depth:</strong> Insertion of metal pry tools past 2–3 mm into an iPad or modern smartphone risks severing ambient light sensors, microphones, or display flex cables.</li>
              <li><strong>Battery Punctures:</strong> Never use metal tools or heat exceeding 70°C directly on lithium-ion pouch cells. A breached separator layer causes rapid thermal venting and fire.</li>
              <li><strong>Optical Fingerprint Scanner Calibration:</strong> Replacing displays on Pixel or Samsung devices requires clean optical sensor calibration. Smudges lead to calibration failure errors.</li>
            </ul>
          </div>
        </div>
      )}

      {/* ============================================== */}
      {/* TAB 2: ASURION CLAIM & IQC WORKFLOW */}
      {/* ============================================== */}
      {activeTab === 'intake' && (
        <div className="aibs-sop-grid-2col">
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#38bdf8' }}>Step-by-Step Insurance Intake Workflow</h3>
              <ol style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.85rem', lineHeight: '1.6' }}>
                <li style={{ marginBottom: '10px' }}><strong style={{ color: '#fff' }}>Claim Retrieval:</strong> Query open claim in NextGen Portal. Verify status is <em>Approved for In-Store Repair</em>.</li>
                <li style={{ marginBottom: '10px' }}><strong style={{ color: '#fff' }}>Physical IMEI Verification:</strong> Verify the hardware IMEI (*#06# or SIM tray) exactly matches the 15-digit IMEI on the Asurion claim. <em>Mismatch = Halt Intake.</em></li>
                <li style={{ marginBottom: '10px' }}><strong style={{ color: '#fff' }}>Physical Damage & Tier Verification:</strong> Inspect LCI (Liquid Contact Indicators). Check for chassis warping. If back glass is cracked or frame is bent, a "Screen Only" claim must be escalated to a Whole Unit Replacement (WUR).</li>
                <li style={{ marginBottom: '10px' }}><strong style={{ color: '#fff' }}>Pre-Repair IQC:</strong> Log diagnostic checklist: Touch grid, Optics, Audio/Haptics, Connectivity, Biometrics, and Power draw (1.0A-2.4A target). Document every pre-existing scuff to prevent fraud.</li>
                <li style={{ marginBottom: '10px' }}><strong style={{ color: '#fff' }}>Signatures:</strong> Customer must sign Data Loss Waiver, Disassembly Auth, and Pre-Existing Damage Acceptance.</li>
                <li style={{ marginBottom: '10px' }}><strong style={{ color: '#fff' }}>Deductible:</strong> Verify pre-paid token or process via NETePay terminal.</li>
                <li><strong style={{ color: '#fff' }}>Serialized Binding:</strong> Assign OEM SKU to the ticket. Print routing slips for the ticket and the ESD bin.</li>
              </ol>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ background: '#090e17', border: '1px solid rgba(234, 179, 8, 0.3)', borderRadius: '12px', padding: '20px' }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#facc15' }}>Intake Decision Matrix</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px' }}>
                  <strong style={{ color: '#fff' }}>IMEI / Serial:</strong> Must be exact match. 
                  <span style={{ color: '#f87171', display: 'block', marginTop: '4px' }}>Discrepancy: Halt Intake. Customer must call Asurion.</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px' }}>
                  <strong style={{ color: '#fff' }}>LCI / Moisture Sensor:</strong> Must be White/Silver.
                  <span style={{ color: '#f87171', display: 'block', marginTop: '4px' }}>Discrepancy: If pink/red, escalate to replacement/WUR claim.</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px' }}>
                  <strong style={{ color: '#fff' }}>Frame Geometry:</strong> Undistorted flat rails.
                  <span style={{ color: '#f87171', display: 'block', marginTop: '4px' }}>Discrepancy: If bent/twisted, decline screen-only repair; frame will crack replacement OLED.</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '10px', borderRadius: '8px' }}>
                  <strong style={{ color: '#fff' }}>Device Passcode:</strong> Provided or removed.
                  <span style={{ color: '#f87171', display: 'block', marginTop: '4px' }}>Discrepancy: Flag ticket as "Untestable / Customer Assumes Diagnostic Risk."</span>
                </div>
              </div>
            </div>
            
            <div style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '12px', padding: '16px', fontSize: '0.8rem', color: '#94a3b8' }}>
              💡 <strong>The "SIM-Swap" IMEI Trap:</strong> Carrier backends frequently update the active IMEI to an old backup phone the customer used temporarily. If an intake tech starts the repair under the wrong IMEI, the claim will fail validation at checkout, leaving the store with an unbillable OEM part.
            </div>
          </div>
        </div>
      )}

      {/* ============================================== */}
      {/* TAB 3: BER ESCALATION PROTOCOL */}
      {/* ============================================== */}
      {activeTab === 'ber' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
          <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '24px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.2rem', color: '#f87171' }}>Beyond Economical Repair (BER) Protocol</h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.88rem', color: '#cbd5e1' }}>
              Devices exhibiting catastrophic structural, liquid, or thermal damage must be intercepted and categorized as BER. Executing a standard repair on a BER device transfers liability for future hardware failures to the technician.
            </p>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left', background: '#090e17', borderRadius: '8px', overflow: 'hidden' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(239, 68, 68, 0.4)', color: '#fca5a5' }}>
                  <th style={{ padding: '12px' }}>Failure Modality</th>
                  <th style={{ padding: '12px' }}>Diagnostic Indicators</th>
                  <th style={{ padding: '12px' }}>Portal Action</th>
                </tr>
              </thead>
              <tbody style={{ color: '#e2e8f0' }}>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', fontWeight: 600 }}>Structural Catastrophe</td>
                  <td style={{ padding: '12px' }}>Frame shearing; logic board fracture; housing warping exceeding 2mm tolerance.</td>
                  <td style={{ padding: '12px', color: '#f87171' }}>Escalate to BER. Halt intake. WUR required.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', fontWeight: 600 }}>Liquid Intrusion</td>
                  <td style={{ padding: '12px' }}>Triggered LCI (pink/red) coupled with galvanic corrosion on primary ICs or trace delamination.</td>
                  <td style={{ padding: '12px', color: '#f87171' }}>Escalate to BER. Document corrosion photographically.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', fontWeight: 600 }}>Economic Deficit</td>
                  <td style={{ padding: '12px' }}>Aggregate OEM parts cost (OLED + Logic Board + Battery + Housing) exceeds secondary market retail value.</td>
                  <td style={{ padding: '12px', color: '#f87171' }}>Quote BER. Transition to WUR claim if insured.</td>
                </tr>
                <tr>
                  <td style={{ padding: '12px', fontWeight: 600 }}>Thermal Event</td>
                  <td style={{ padding: '12px' }}>Battery thermal runaway resulting in internal charring, soot, or melted sub-components.</td>
                  <td style={{ padding: '12px', color: '#f87171' }}>Isolate hardware immediately. Escalate to BER.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#38bdf8' }}>Escalation & Claim Conversion Workflow</h3>
            <ol style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.85rem', lineHeight: '1.6' }}>
              <li><strong>Identification & Documentation:</strong> Capture high-resolution photographic evidence of the structural or liquid damage.</li>
              <li><strong>Status Modification:</strong> Update NextGen Portal job status to <em>Unrepairable / BER</em>. Attach photographic evidence.</li>
              <li><strong>Claim Release:</strong> For carrier claims, the physical repair ticket must be aborted. Contact Asurion Dealer Support to release the IMEI claim lock.</li>
              <li><strong>Customer Conversion:</strong> Inform customer physical repair is aborted. Direct them to Asurion to pay the WUR deductible for overnight device replacement.</li>
              <li><strong>Reassembly & Handback:</strong> Reassemble the damaged device to exact intake state. Close Portal ticket as $0 balance / incomplete.</li>
            </ol>
          </div>
        </div>
      )}

      {/* ============================================== */}
      {/* TAB 4: STORE OPERATIONS & TURNAROUND */}
      {/* ============================================== */}
      {activeTab === 'operations' && (
        <div className="aibs-sop-grid-equal">
          
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#38bdf8' }}>Retail Hours & Turnaround Times</h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.85rem', lineHeight: '1.6' }}>
              <li><strong style={{ color: '#fff' }}>Standard Hours:</strong> Monday–Saturday 10:00 AM – 7:00 PM. Sunday Closed.</li>
              <li><strong style={{ color: '#fff' }}>Smartphones (Screen/Battery):</strong> 45 to 90 minutes. (iPhones clear faster than Androids).</li>
              <li><strong style={{ color: '#fff' }}>Android Assemblies (Frame Transfers):</strong> 1.5 to 3 hours. Requires thermal curing & OEM diagnostics.</li>
              <li><strong style={{ color: '#fff' }}>Tablets (iPad/Galaxy Tab):</strong> 2 to 24 hours. Screen bonding requires sustained clamping pressure.</li>
              <li><strong style={{ color: '#fff' }}>Computers & Consoles:</strong> 24 to 72 hours. Hardware triage and soldering require longer windows.</li>
            </ul>
          </div>

          <div style={{ background: '#090e17', border: '1px solid rgba(168, 85, 247, 0.2)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#c084fc' }}>Scope of Repair Services</h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.85rem', lineHeight: '1.6' }}>
              <li><strong style={{ color: '#fff' }}>Smartphones:</strong> Screen/digitizer, battery swaps, charging ports, camera modules, rear glass.</li>
              <li><strong style={{ color: '#fff' }}>Tablets:</strong> Full LCD/OLED replacements, battery swaps, housing de-bending.</li>
              <li><strong style={{ color: '#fff' }}>Computers:</strong> LCD panel replacement, SSD upgrades, RAM, DC power jack soldering, thermal repasting.</li>
              <li><strong style={{ color: '#fff' }}>Game Consoles:</strong> HDMI port surface-mount desoldering, optical drive lasers, liquid metal replenishment, PSU swaps.</li>
            </ul>
          </div>

          <div style={{ gridColumn: '1 / -1', background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.2)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#f59e0b' }}>Field Technician Insights & Friction Points</h3>
            <div className="aibs-sop-grid-equal" style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
              <div>
                <strong style={{ color: '#fcd34d' }}>Sales Metrics vs. Technical Skill:</strong> Store performance reviews frequently weigh conversion on "Asurion Home+" protection plan sales as heavily as repair output.
              </div>
              <div>
                <strong style={{ color: '#fcd34d' }}>NextGen Portal Bottlenecks:</strong> Portal can be prone to intermittent slowdowns and session timeouts. Learning keyboard shortcuts and keeping paper IMEI records helps.
              </div>
              <div>
                <strong style={{ color: '#fcd34d' }}>Samsung GSPN Audit Strictness:</strong> Corporate audits are rigorous. Failing to run the full diagnostic sweep leads to rejected claims charged back to the store.
              </div>
              <div>
                <strong style={{ color: '#fcd34d' }}>Console Repair Variability:</strong> In locations lacking board-level hot air rework equipment, consoles (like PS5 HDMI ports) are sent to centralized hubs, extending turnarounds to 1–2 weeks.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================== */}
      {/* TAB 5: CHEMICAL ADHESIVE-RELEASE PROTOCOL */}
      {/* ============================================== */}
      {activeTab === 'chemical' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.15rem', color: '#38bdf8' }}>Chemical Adhesive-Release Technique (iPad Batteries)</h3>
            <p style={{ margin: '0 0 16px 0', fontSize: '0.85rem', color: '#cbd5e1' }}>
              Unlike iPhones (stretch-release tabs), Apple bonds iPad pouch cells directly to the chassis. Applying direct mechanical force will puncture the cell, causing rapid thermal runaway. Technicians must use chemical debonding paired with thermal delivery and friction-slicing.
            </p>

            <h4 style={{ margin: '16px 0 8px 0', fontSize: '0.95rem', color: '#fff' }}>Required Equipment:</h4>
            <ul style={{ margin: '0 0 16px 0', paddingLeft: '20px', color: '#94a3b8', fontSize: '0.82rem' }}>
              <li><strong>99% Isopropyl Alcohol (IPA):</strong> Primary chemical solvent. (Do NOT use 70% as water induces logic board corrosion).</li>
              <li><strong>Blunt Syringe / Fine-Tip Dropper:</strong> For precise application.</li>
              <li><strong>Flexible Plastic Pry Cards:</strong> Non-conductive. Never use metal.</li>
              <li><strong>Heavy-Duty Dental Floss / Kevlar Thread:</strong> For friction sawing.</li>
              <li><strong>Digital Heating Pad:</strong> Set to 65°C - 70°C.</li>
              <li><strong>Fire-Safe Sand Bucket:</strong> Must be adjacent to the bench.</li>
            </ul>

            <h4 style={{ margin: '16px 0 8px 0', fontSize: '0.95rem', color: '#fff' }}>The 5-Phase Extraction Protocol:</h4>
            <ol style={{ margin: '0', paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.85rem', lineHeight: '1.6' }}>
              <li style={{ marginBottom: '8px' }}><strong>Phase 1 (Isolation):</strong> Discharge battery below 25%. Isolate power by inserting a plastic pick between the battery contact and logic board pins.</li>
              <li style={{ marginBottom: '8px' }}><strong>Phase 2 (Thermal Softening):</strong> Place iPad rear-down onto the heating pad at 70°C for 5-10 mins. <span style={{ color: '#f87171' }}>Hazard: Never exceed 70°C or use direct localized heat guns on the battery.</span></li>
              <li style={{ marginBottom: '8px' }}><strong>Phase 3 (Solvent Injection):</strong> Elevate one edge 15-20 degrees. Drip 2-3 mL of 99% IPA along the upper seam. Wait 3-5 minutes for capillary action to break the adhesive matrix.</li>
              <li style={{ marginBottom: '8px' }}><strong>Phase 4 (Mechanical Separation):</strong> Use the Floss Saw technique (pulling kevlar thread back and forth underneath the cell) or slide a thin plastic card completely horizontally to sever the weakened adhesive.</li>
              <li style={{ marginBottom: '8px' }}><strong>Phase 5 (Cleanup):</strong> Remove gummy adhesive with a plastic scraper while warm. Frame must be perfectly clean before installing the new battery to prevent LCD pressure points.</li>
            </ol>
          </div>

          <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '12px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: '#f87171' }}>⚠️ Specific Extraction Hazards</h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#fca5a5', fontSize: '0.85rem', lineHeight: '1.6' }}>
              <li><strong>The "Taco" Effect:</strong> Prying upward before the alcohol has dissolved the adhesive will bend the battery in the middle, crushing internal separators and causing a short circuit. Keep cards flat against the chassis.</li>
              <li><strong>The Alcohol Tsunami:</strong> Flooding the chassis with too much IPA can permanently dissolve internal membranes of ambient microphones or the Face ID dot projector. Apply strictly to battery edges.</li>
              <li><strong>Battery Odor Indicator:</strong> If you smell a distinct sweet, metallic odor (bubblegum / nail polish remover), <strong>STOP IMMEDIATELY</strong>. The outer foil pouch is ruptured and toxic electrolyte gas is leaking. Evacuate to the sand bucket.</li>
            </ul>
          </div>
        </div>
      )}

      {/* ============================================== */}
      {/* TAB 6: PRICING MATRIX & STORE POLICIES (2024-2025) */}
      {/* ============================================== */}
      {activeTab === 'pricing' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Top Banner Notice */}
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '16px' }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#38bdf8' }}>
              📊 Two-Track Pricing Framework (Insurance vs. Walk-In Retail)
            </h3>
            <p style={{ margin: 0, fontSize: '0.84rem', color: '#cbd5e1', lineHeight: '1.5' }}>
              Because uBreakiFix operates primarily on a franchise model and uses real-time market pricing for replacement parts, there is no single universal out-of-pocket price chart. Pricing fluctuates based on device age, your local store’s labor rate, and the wholesale cost of OEM parts. As a technician or store lead, you will manage two distinct tracks: <strong>Fixed Insurance Deductibles (Nationwide)</strong> and <strong>Out-of-Pocket Walk-Ins</strong>.
            </p>
          </div>

          {/* CHART 1: ASURION INSURANCE DEDUCTIBLES */}
          <div style={{ background: '#090e17', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '12px', padding: '20px', overflowX: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#34d399' }}>
                Chart 1: Asurion Insurance Deductibles (Carrier Claims)
              </h3>
              <span style={{ fontSize: '0.74rem', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                Fixed Nationwide Rates
              </span>
            </div>
            <p style={{ margin: '0 0 14px 0', fontSize: '0.82rem', color: '#94a3b8' }}>
              Customers with AT&T, Verizon, or Asurion retail insurance pay a fixed deductible dictated by carrier tier, rather than retail part costs.
            </p>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(16, 185, 129, 0.4)', color: '#34d399' }}>
                  <th style={{ padding: '10px' }}>Repair Type / Claim Outcome</th>
                  <th style={{ padding: '10px' }}>Standard Deductible</th>
                  <th style={{ padding: '10px' }}>Tech Lead Notes & Claim Rules</th>
                </tr>
              </thead>
              <tbody style={{ color: '#cbd5e1' }}>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Front Screen / Back Glass Repair</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$0 or $29</td>
                  <td style={{ padding: '10px' }}>Must be strictly glass damage. If frame is bent or internal LCD is bleeding, it escalates to a WUR claim.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Battery Replacement</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$0 (or $29)</td>
                  <td style={{ padding: '10px' }}>Usually free under extended warranty tiers if battery health is verified below 80% on OEM diagnostics.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Charge Port / Camera Repair</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$0 or $29</td>
                  <td style={{ padding: '10px' }}>Available on select carrier tiers; if the part is modular and in stock.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Whole Unit Replacement (Tier 1 Device)</td>
                  <td style={{ padding: '10px', color: '#facc15', fontWeight: 700 }}>$99</td>
                  <td style={{ padding: '10px' }}>Applied if the device is deemed BER (Beyond Economical Repair) on budget/older models.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Whole Unit Replacement (Tier 2/3 Flagships)</td>
                  <td style={{ padding: '10px', color: '#f87171', fontWeight: 700 }}>$200 – $275+</td>
                  <td style={{ padding: '10px' }}>Applied to Pro Max, Ultra, or Foldable devices when catastrophic liquid/board damage is present.</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Asurion Home+ (Laptops/Consoles/Tablets)</td>
                  <td style={{ padding: '10px', color: '#38bdf8', fontWeight: 700 }}>$0 to $99</td>
                  <td style={{ padding: '10px' }}>Fixed claim service fee for registered smart home and computer products.</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* CHART 2: ESTIMATED OUT-OF-POCKET PRICES (SMARTPHONES) */}
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '20px', overflowX: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#38bdf8' }}>
                Chart 2: Estimated Out-of-Pocket Prices (Walk-In Smartphones)
              </h3>
              <span style={{ fontSize: '0.74rem', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                Retail Hardware Averages
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}>
                  <th style={{ padding: '10px' }}>Device Family</th>
                  <th style={{ padding: '10px' }}>Screen Replacement</th>
                  <th style={{ padding: '10px' }}>Battery Replacement</th>
                  <th style={{ padding: '10px' }}>Back Glass Repair</th>
                  <th style={{ padding: '10px' }}>Tech Lead Notes</th>
                </tr>
              </thead>
              <tbody style={{ color: '#cbd5e1' }}>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>iPhone (Older: 11, 12, 13)</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$120 – $180</td>
                  <td style={{ padding: '10px' }}>$79 – $99</td>
                  <td style={{ padding: '10px' }}>$129 – $169</td>
                  <td style={{ padding: '10px' }}>Aftermarket screens are cheaper; OEM pulls carry a 20-30% premium.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>iPhone (Newer: 14, 15, 16 Series)</td>
                  <td style={{ padding: '10px', color: '#38bdf8', fontWeight: 700 }}>$249 – $349+</td>
                  <td style={{ padding: '10px' }}>$99 – $119</td>
                  <td style={{ padding: '10px' }}>$149+</td>
                  <td style={{ padding: '10px' }}>Back glass is modular on 14/15/16 base; Pro models require laser removal or housing swap.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Samsung Galaxy (S-Series Base/Plus)</td>
                  <td style={{ padding: '10px', color: '#38bdf8', fontWeight: 700 }}>$199 – $249</td>
                  <td style={{ padding: '10px' }}>$89 – $109</td>
                  <td style={{ padding: '10px' }}>$89 – $119</td>
                  <td style={{ padding: '10px' }}>Samsung OEM Service Packs include a brand-new metal chassis & pre-installed battery.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Samsung Galaxy Ultra Series</td>
                  <td style={{ padding: '10px', color: '#f87171', fontWeight: 700 }}>$299 – $429+</td>
                  <td style={{ padding: '10px' }}>$99 – $129</td>
                  <td style={{ padding: '10px' }}>$99 – $139</td>
                  <td style={{ padding: '10px' }}>Curved Dynamic AMOLED panels drive up wholesale part costs significantly.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Samsung Galaxy Z Fold / Z Flip</td>
                  <td style={{ padding: '10px', color: '#f87171', fontWeight: 700 }}>$350 – $650+</td>
                  <td style={{ padding: '10px' }}>$119 – $149</td>
                  <td style={{ padding: '10px' }}>$119 – $149</td>
                  <td style={{ padding: '10px' }}>Inner folding screens require full hinge/rail replacement assemblies.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Google Pixel (Older: 6, 7 Series)</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$149 – $229</td>
                  <td style={{ padding: '10px' }}>$89 – $109</td>
                  <td style={{ padding: '10px' }}>$119 – $149</td>
                  <td style={{ padding: '10px' }}>Requires Google AST fingerprint calibration tool post-installation.</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Google Pixel (Newer: 8, 9 Pro Series)</td>
                  <td style={{ padding: '10px', color: '#38bdf8', fontWeight: 700 }}>$269 – $329+</td>
                  <td style={{ padding: '10px' }}>$109 – $129</td>
                  <td style={{ padding: '10px' }}>$139 – $169</td>
                  <td style={{ padding: '10px' }}>High refresh rate Actua displays have strictly controlled OEM distribution.</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* CHART 3: TABLETS, COMPUTERS & GAME CONSOLES */}
          <div style={{ background: '#090e17', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '12px', padding: '20px', overflowX: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#c084fc' }}>
                Chart 3: Tablets, Computers & Game Consoles
              </h3>
              <span style={{ fontSize: '0.74rem', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                Specialized Hardware & Soldering
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid rgba(168, 85, 247, 0.4)', color: '#c084fc' }}>
                  <th style={{ padding: '10px' }}>Device & Service Type</th>
                  <th style={{ padding: '10px' }}>Estimated Price</th>
                  <th style={{ padding: '10px' }}>Tech Lead Operational Notes</th>
                </tr>
              </thead>
              <tbody style={{ color: '#cbd5e1' }}>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>iPad Screen (Glass Only / Non-Laminated)</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$129 – $149</td>
                  <td style={{ padding: '10px' }}>Base iPads (7th, 8th, 9th, 10th Gen). Glass digitizer is separate from the internal LCD.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>iPad Pro / Air Screen (Fused Laminated)</td>
                  <td style={{ padding: '10px', color: '#f87171', fontWeight: 700 }}>$249 – $399+</td>
                  <td style={{ padding: '10px' }}>Glass and LCD/OLED are fused. Entire assembly must be replaced even if only the top glass is cracked.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>PS5 / Xbox Series X HDMI Port Repair</td>
                  <td style={{ padding: '10px', color: '#38bdf8', fontWeight: 700 }}>$149 – $199</td>
                  <td style={{ padding: '10px' }}>Requires Tier-3 micro-soldering hot air station. Liquid metal APU barrier must be carefully isolated.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Console Deep Clean & Thermal Paste</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$79 – $119</td>
                  <td style={{ padding: '10px' }}>Full teardown, heatsink de-dusting, and non-conductive thermal paste application for overheating units.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Laptop Screen Replacement (PC / Mac)</td>
                  <td style={{ padding: '10px', color: '#38bdf8', fontWeight: 700 }}>$150 – $300+</td>
                  <td style={{ padding: '10px' }}>Standard 1080p panels are $150; MacBook Retina/OLED assemblies can reach $400–$600+.</td>
                </tr>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>PC/Mac Operating System Reinstall / Virus</td>
                  <td style={{ padding: '10px', color: '#34d399', fontWeight: 700 }}>$99 – $149</td>
                  <td style={{ padding: '10px' }}>Clean OS install, driver initialization, and malware removal. $49–$99 extra for data backup.</td>
                </tr>
                <tr>
                  <td style={{ padding: '10px', color: '#f8fafc', fontWeight: 600 }}>Data Recovery (Temporary Board-Level Boot)</td>
                  <td style={{ padding: '10px', color: '#facc15', fontWeight: 700 }}>$200 – $350+</td>
                  <td style={{ padding: '10px' }}>Clearing VDD_MAIN shorts or jumper wiring to power the board long enough to extract an unencrypted NAND backup.</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* CRITICAL STORE POLICIES & DE-ESCALATION */}
          <div className="aibs-sop-grid-equal">
            
            <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '18px' }}>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '1.05rem', color: '#38bdf8' }}>
                🛡️ Critical Store Policies Regarding Pricing
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.82rem' }}>
                <div style={{ background: 'rgba(56, 189, 248, 0.08)', padding: '10px', borderRadius: '6px', borderLeft: '3px solid #38bdf8' }}>
                  <strong style={{ color: '#fff' }}>1. The Diagnostic is ALWAYS Free:</strong> Technicians inspect the hardware, bench-test power draw, and open the device at $0.00. If the device is BER or unrepairable, the invoice is $0.
                </div>
                <div style={{ background: 'rgba(16, 185, 129, 0.08)', padding: '10px', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
                  <strong style={{ color: '#fff' }}>2. The $5 Price Match Guarantee:</strong> uBreakiFix will beat any local brick-and-mortar competitor's published price by $5, provided they use the exact same OEM quality tier.
                </div>
                <div style={{ background: 'rgba(234, 179, 8, 0.08)', padding: '10px', borderRadius: '6px', borderLeft: '3px solid #facc15' }}>
                  <strong style={{ color: '#fff' }}>3. The "No Fix, No Fee" Policy:</strong> If a technician attempts a repair (e.g. a micro-soldered charging port or board repair) and it does not resolve the issue, the old parts are reinstalled and the customer pays $0.
                </div>
              </div>
            </div>

            <div style={{ background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.8), rgba(15, 23, 42, 0.9))', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '12px', padding: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#c084fc' }}>
                  🗣️ "Price Shock" Customer De-escalation Script
                </h3>
                <span style={{ fontSize: '0.72rem', background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
                  Tech Lead Dialogue
                </span>
              </div>
              <p style={{ margin: '0 0 10px 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                Because OEM parts are expensive, walk-in customers will often experience sticker shock. As a Tech Lead, use this exact verbal response:
              </p>
              <div style={{ background: 'rgba(0,0,0,0.4)', borderLeft: '3px solid #c084fc', padding: '12px 16px', borderRadius: '0 8px 8px 0', fontSize: '0.86rem', color: '#f1f5f9', fontStyle: 'italic', lineHeight: '1.5' }}>
                "I understand that price feels high. Because we are an Authorized Service Center, we don't just glue a cheap aftermarket screen on. You are getting a brand new screen pre-built into a new metal frame, and a newly calibrated fingerprint scanner straight from the manufacturer, backed by a 1-year nationwide warranty."
              </div>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}
