import React, { useState, useEffect } from 'react';

const SCENARIOS = [
  {
    id: 'case_iphone14_screen',
    title: 'Case #1: iPhone 14 Pro Max — Shattered OLED (Standard Claim)',
    customer: 'Marcus Vance',
    claimNumber: 'ASU-99281-NY',
    device: 'Apple iPhone 14 Pro Max (A2651)',
    portalImei: '356891092837412',
    hardwareImei: '356891092837412',
    reportedIssue: 'Dropped on concrete. Touch works partially, spiderweb cracks on front glass.',
    lciStatus: 'WHITE',
    chassisCondition: 'FLAT',
    iqcState: {
      touchGrid: 'PASS',
      cameras: 'PASS',
      audioHaptics: 'PASS',
      biometricsFaceId: 'PASS',
      chargeCurrent: '1.8A (Normal)'
    },
    correctAction: 'APPROVE_SCREEN',
    explanation: 'Hardware and Portal IMEIs match, LCI is pristine white, chassis is flat. Standard $29 OEM Screen Repair intake approved in under 4 minutes.'
  },
  {
    id: 'case_s23_fraud_trap',
    title: 'Case #2: Samsung Galaxy S23 Ultra — SIM-Swap IMEI Mismatch (Fraud Trap)',
    customer: 'Derek Holland',
    claimNumber: 'ASU-44102-MI',
    device: 'Samsung Galaxy S23 Ultra (SM-S918U)',
    portalImei: '359876543210987',
    hardwareImei: '351234567890123',
    reportedIssue: 'Customer claims screen went black. Wants new OLED covered under insurance claim.',
    lciStatus: 'WHITE',
    chassisCondition: 'FLAT',
    iqcState: {
      touchGrid: 'FAIL',
      cameras: 'UNTESTABLE',
      audioHaptics: 'PASS',
      biometricsFaceId: 'UNTESTABLE',
      chargeCurrent: '1.2A (Normal)'
    },
    correctAction: 'HALT_FRAUD',
    explanation: 'CRITICAL FRAUD TRAP: Hardware IMEI on SIM tray/dialer (*#06#) does NOT match the Asurion claim authorization. Intake MUST be halted. Proceeding results in unbillable OEM parts charged to the store.'
  },
  {
    id: 'case_pixel8_liquid_ber',
    title: 'Case #3: Google Pixel 8 Pro — Submerged in Pool (BER Liquid Escalation)',
    customer: 'Elena Rostova',
    claimNumber: 'ASU-77192-CA',
    device: 'Google Pixel 8 Pro (GC3VE)',
    portalImei: '354455667788990',
    hardwareImei: '354455667788990',
    reportedIssue: 'Phone fell into shallow pool. Dried with rice for 24h. Display flickers green.',
    lciStatus: 'PINK_RED',
    chassisCondition: 'FLAT',
    iqcState: {
      touchGrid: 'FAIL',
      cameras: 'FAIL',
      audioHaptics: 'FAIL',
      biometricsFaceId: 'FAIL',
      chargeCurrent: '0.08A (Short Circuit / Leakage)'
    },
    correctAction: 'ESCALATE_BER',
    explanation: 'BER PROTOCOL: Liquid Contact Indicator (LCI) is triggered red and USB port shows galvanic corrosion. Repairing only the screen leaves latent board corrosion that voids warranty. Must escalate to Whole Unit Replacement (WUR).'
  },
  {
    id: 'case_iphone13_bent_frame',
    title: 'Case #4: iPhone 13 — Twisted Chassis / Bent Aluminum Rail',
    customer: 'Jordan Reed',
    claimNumber: 'ASU-11234-TX',
    device: 'Apple iPhone 13 (A2482)',
    portalImei: '358822334455667',
    hardwareImei: '358822334455667',
    reportedIssue: 'Ran over by bicycle. Front glass cracked. Customer demands screen swap only.',
    lciStatus: 'WHITE',
    chassisCondition: 'BENT',
    iqcState: {
      touchGrid: 'PASS',
      cameras: 'PASS',
      audioHaptics: 'PASS',
      biometricsFaceId: 'PASS',
      chargeCurrent: '1.5A (Normal)'
    },
    correctAction: 'DECLINE_OR_HOUSING',
    explanation: 'GEOMETRIC HAZARD: The aluminum chassis is warped by 4.5mm. Installing a rigid OLED display into a bent chassis will fracture the new glass within 24 hours. Must require a full housing replacement or escalate to WUR.'
  },
  {
    id: 'case_ipad_chemical_battery',
    title: 'Case #5: iPad Pro 11" — Degraded Pouch Cell (Chemical Extraction)',
    customer: 'Sarah Jenkins',
    claimNumber: 'WALK-IN-REPAIR',
    device: 'Apple iPad Pro 11" 3rd Gen (A2377)',
    portalImei: 'N/A (Retail Walk-in)',
    hardwareImei: 'DLXQ2819P029',
    reportedIssue: 'Battery drains in 45 minutes. Slight display lift along left seam.',
    lciStatus: 'WHITE',
    chassisCondition: 'FLAT',
    iqcState: {
      touchGrid: 'PASS',
      cameras: 'PASS',
      audioHaptics: 'PASS',
      biometricsFaceId: 'PASS',
      chargeCurrent: '2.1A (Normal)'
    },
    correctAction: 'APPROVE_CHEMICAL_BATTERY',
    explanation: 'CHEMICAL ADHESIVE EXTRACTION: Pouch cell requires discharge < 25%, 70°C heat mat softening, 2-3 mL 99% IPA solvent injection, and Kevlar floss-saw extraction without upward prying (prevent Taco fold / thermal runaway).'
  }
];

export default function UBreakiFixPracticePortal() {
  const [currentScenarioIdx, setCurrentScenarioIdx] = useState(0);
  const [step, setStep] = useState(1);
  const [timeLeft, setTimeLeft] = useState(240);
  const [timerActive, setTimerActive] = useState(true);
  const [checkedIqc, setCheckedIqc] = useState({});
  const [waiversSigned, setWaiversSigned] = useState({ dataLoss: false, disassembly: false, preDamage: false });
  const [simResult, setSimResult] = useState(null);
  const [totalScore, setTotalScore] = useState(0);
  const [completedScenarios, setCompletedScenarios] = useState(0);

  const scenario = SCENARIOS[currentScenarioIdx];

  useEffect(() => {
    let timer = null;
    if (timerActive && timeLeft > 0 && !simResult) {
      timer = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && !simResult) {
      handleFinalDecision('TIMEOUT');
    }
    return () => clearInterval(timer);
  }, [timerActive, timeLeft, simResult]);

  const resetScenario = (nextIdx = 0) => {
    setCurrentScenarioIdx(nextIdx);
    setStep(1);
    setTimeLeft(240);
    setTimerActive(true);
    setCheckedIqc({});
    setWaiversSigned({ dataLoss: false, disassembly: false, preDamage: false });
    setSimResult(null);
  };

  const handleIqcToggle = (key) => {
    setCheckedIqc(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleFinalDecision = (action) => {
    setTimerActive(false);
    const elapsedSeconds = 240 - timeLeft;
    const isUnderFourMinutes = elapsedSeconds <= 240;
    const correct = action === scenario.correctAction;

    let points = 0;
    let feedbackNotes = [];

    if (action === 'TIMEOUT') {
      points = 0;
      feedbackNotes.push('❌ KPI BREACH: You exceeded the 4-minute maximum customer intake standard.');
    } else if (correct) {
      points += 70;
      feedbackNotes.push(`✅ CORRECT PROTOCOL: You accurately selected ${action}.`);
    } else {
      points += 10;
      feedbackNotes.push(`❌ INCORRECT PROTOCOL: You selected ${action}, but the correct standard was ${scenario.correctAction}.`);
    }

    if (isUnderFourMinutes && action !== 'TIMEOUT') {
      points += 20;
      feedbackNotes.push(`⚡ SPEED KPI: Completed in ${Math.floor(elapsedSeconds / 60)}m ${elapsedSeconds % 60}s (Under 4-minute target).`);
    }

    const allWaivers = waiversSigned.dataLoss && waiversSigned.disassembly && waiversSigned.preDamage;
    if (allWaivers) {
      points += 10;
      feedbackNotes.push('📝 COMPLIANCE: All 3 mandatory customer risk waivers obtained.');
    } else if (action === 'APPROVE_SCREEN' || action === 'APPROVE_CHEMICAL_BATTERY') {
      points = Math.max(0, points - 30);
      feedbackNotes.push('⚠️ LEGAL RISK: Missing customer signatures on Data Loss / Disassembly Auth waivers!');
    }

    setTotalScore(prev => prev + points);
    setCompletedScenarios(prev => prev + 1);

    setSimResult({
      pass: correct && action !== 'TIMEOUT',
      score: points,
      elapsed: elapsedSeconds,
      feedback: feedbackNotes,
      explanation: scenario.explanation
    });
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="aibs-portal-root">
      <style>{`
        .aibs-portal-root {
          width: 100%;
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          gap: 20px;
          max-width: 100vw;
          overflow-x: hidden;
        }
        .aibs-portal-header {
          background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 27, 75, 0.95));
          border: 1px solid rgba(168, 85, 247, 0.4);
          border-radius: 16px;
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 16px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .aibs-portal-ribbon {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          flex-wrap: nowrap;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
          padding-bottom: 6px;
        }
        .aibs-portal-btn {
          white-space: nowrap !important;
          flex-shrink: 0 !important;
          min-height: 40px;
          touch-action: manipulation;
        }
        .aibs-portal-grid {
          display: grid;
          grid-template-columns: 1.1fr 1.3fr;
          gap: 20px;
        }
        .aibs-portal-subgrid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .aibs-portal-steps {
          display: flex;
          gap: 6px;
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
        @media (max-width: 900px) {
          .aibs-portal-grid {
            grid-template-columns: 1fr !important;
          }
        }
        @media (max-width: 640px) {
          .aibs-portal-subgrid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
      
      {/* Simulator Control Header */}
      <div className="aibs-portal-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '1.4rem' }}>⚡</span>
            <h2 style={{ margin: 0, fontSize: '1.25rem', color: '#c084fc', fontWeight: 800 }}>
              NextGen Intake Practice Portal & KPI Simulator
            </h2>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.84rem', color: '#94a3b8' }}>
            Interactive speed intake drill: Master the 4-minute Asurion / Walk-In intake workflow, IMEI verification & BER fraud traps.
          </p>
        </div>

        {/* Live Timer & Stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{
            background: timeLeft < 60 ? 'rgba(239, 68, 68, 0.2)' : timeLeft < 120 ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
            border: `1px solid ${timeLeft < 60 ? '#ef4444' : timeLeft < 120 ? '#f59e0b' : '#10b981'}`,
            borderRadius: '12px',
            padding: '8px 18px',
            textAlign: 'center',
            minWidth: '110px'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Intake Timer</div>
            <div style={{
              fontSize: '1.4rem',
              fontWeight: 900,
              fontFamily: 'monospace',
              color: timeLeft < 60 ? '#f87171' : timeLeft < 120 ? '#fbbf24' : '#34d399'
            }}>
              ⏱️ {formatTime(timeLeft)}
            </div>
          </div>

          <div style={{
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '12px',
            padding: '8px 18px',
            textAlign: 'center',
            minWidth: '110px'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Aggregate Score</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 900, color: '#38bdf8' }}>
              {totalScore} pts ({completedScenarios} done)
            </div>
          </div>
        </div>
      </div>

      {/* Scenario Selector Ribbon */}
      <div className="aibs-portal-ribbon">
        {SCENARIOS.map((sc, idx) => (
          <button
            key={sc.id}
            className="aibs-portal-btn"
            onClick={() => resetScenario(idx)}
            style={{
              background: currentScenarioIdx === idx ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(56, 189, 248, 0.2))' : 'rgba(15, 23, 42, 0.6)',
              border: `1px solid ${currentScenarioIdx === idx ? '#c084fc' : 'rgba(255, 255, 255, 0.08)'}`,
              color: currentScenarioIdx === idx ? '#ffffff' : '#94a3b8',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '0.78rem',
              fontWeight: currentScenarioIdx === idx ? 700 : 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Scenario {idx + 1}: {sc.device.split(' ')[1]} {sc.device.split(' ')[2] || ''}
          </button>
        ))}
      </div>

      {/* Main Simulation Workspace Grid */}
      <div className="aibs-portal-grid">
        
        {/* LEFT COLUMN: Customer & Device Physical Dossier */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ background: '#090e17', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '14px', padding: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '6px' }}>
              <span style={{ fontSize: '0.74rem', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Customer & Asurion Claim Ticket
              </span>
              <span style={{ fontSize: '0.74rem', color: '#34d399', background: 'rgba(16, 185, 129, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                Claim: {scenario.claimNumber}
              </span>
            </div>

            <h3 style={{ margin: '0 0 6px 0', fontSize: '1.05rem', color: '#f8fafc' }}>
              {scenario.title}
            </h3>
            <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginBottom: '14px' }}>
              Customer: <strong style={{ color: '#fff' }}>{scenario.customer}</strong> • Device: <strong style={{ color: '#38bdf8' }}>{scenario.device}</strong>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '12px', marginBottom: '14px' }}>
              <div style={{ fontSize: '0.76rem', color: '#94a3b8', marginBottom: '4px' }}>Reported Problem / Customer Narrative:</div>
              <div style={{ fontSize: '0.84rem', color: '#f1f5f9', fontStyle: 'italic' }}>
                "{scenario.reportedIssue}"
              </div>
            </div>

            {/* Hardware Inspection Visuals */}
            <div className="aibs-portal-subgrid">
              <div style={{
                background: 'rgba(0,0,0,0.4)',
                border: `1px solid ${scenario.lciStatus === 'PINK_RED' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(16, 185, 129, 0.3)'}`,
                borderRadius: '8px',
                padding: '10px'
              }}>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Liquid Indicator (LCI)</div>
                <div style={{
                  fontSize: '0.88rem',
                  fontWeight: 800,
                  marginTop: '4px',
                  color: scenario.lciStatus === 'PINK_RED' ? '#f87171' : '#34d399',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  {scenario.lciStatus === 'PINK_RED' ? '🔴 TRIGGERED (Red/Pink)' : '⚪ Pristine White (Dry)'}
                </div>
              </div>

              <div style={{
                background: 'rgba(0,0,0,0.4)',
                border: `1px solid ${scenario.chassisCondition === 'BENT' ? 'rgba(245, 158, 11, 0.5)' : 'rgba(16, 185, 129, 0.3)'}`,
                borderRadius: '8px',
                padding: '10px'
              }}>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Chassis Geometry</div>
                <div style={{
                  fontSize: '0.88rem',
                  fontWeight: 800,
                  marginTop: '4px',
                  color: scenario.chassisCondition === 'BENT' ? '#fbbf24' : '#34d399',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  {scenario.chassisCondition === 'BENT' ? '⚠️ WARPED / BENT 4.5mm' : '✅ Flat & True (0° Bend)'}
                </div>
              </div>
            </div>
          </div>

          {/* Step Progression Bar */}
          <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '14px' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 700, marginBottom: '10px', textTransform: 'uppercase' }}>
              Intake Progression Workflow
            </div>
            <div className="aibs-portal-steps">
              {[
                { s: 1, label: '1. IMEI Check' },
                { s: 2, label: '2. Physical/LCI' },
                { s: 3, label: '3. Pre-IQC' },
                { s: 4, label: '4. Waivers' },
                { s: 5, label: '5. Decision' }
              ].map(st => (
                <button
                  key={st.s}
                  onClick={() => setStep(st.s)}
                  style={{
                    flex: 1,
                    background: step === st.s ? '#38bdf8' : step > st.s ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${step === st.s ? '#38bdf8' : step > st.s ? '#10b981' : 'rgba(255,255,255,0.08)'}`,
                    color: step === st.s ? '#000' : step > st.s ? '#34d399' : '#94a3b8',
                    padding: '8px 4px',
                    borderRadius: '6px',
                    fontSize: '0.72rem',
                    fontWeight: 800,
                    cursor: 'pointer'
                  }}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Interactive NextGen POS Terminal Screen */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: '16px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          minHeight: '440px'
        }}>
          
          {/* STEP 1: IMEI VERIFICATION */}
          {step === 1 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <span style={{ background: '#38bdf8', color: '#000', borderRadius: '50%', width: '22px', height: '22px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '0.75rem' }}>1</span>
                <h4 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc' }}>Asurion Claim vs. Physical Hardware IMEI Verification</h4>
              </div>

              <p style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: '1.5' }}>
                Dial <code>*#06#</code> on the device or inspect the laser-engraved IMEI on the SIM tray. Compare directly with the open Asurion claim.
              </p>

              <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '16px', marginTop: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>Asurion Portal Claim IMEI:</span>
                  <span style={{ fontSize: '0.9rem', color: '#38bdf8', fontFamily: 'monospace', fontWeight: 700 }}>{scenario.portalImei}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '10px' }}>
                  <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>Physical Hardware IMEI (*#06#):</span>
                  <span style={{ fontSize: '0.9rem', color: scenario.portalImei === scenario.hardwareImei ? '#34d399' : '#f87171', fontFamily: 'monospace', fontWeight: 700 }}>
                    {scenario.hardwareImei} {scenario.portalImei !== scenario.hardwareImei && '⚠️ MISMATCH'}
                  </span>
                </div>
              </div>

              {scenario.portalImei !== scenario.hardwareImei && (
                <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', padding: '12px', marginTop: '14px', color: '#fca5a5', fontSize: '0.8rem' }}>
                  ⚠️ <strong>CRITICAL WARNING:</strong> Hardware IMEI does not match insurance claim. Proceeding will trigger an Asurion audit rejection.
                </div>
              )}
            </div>
          )}

          {/* STEP 2: PHYSICAL DAMAGE & LCI INSPECTION */}
          {step === 2 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <span style={{ background: '#38bdf8', color: '#000', borderRadius: '50%', width: '22px', height: '22px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '0.75rem' }}>2</span>
                <h4 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc' }}>Liquid Contact (LCI) & Frame Integrity Verification</h4>
              </div>

              <p style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: '1.5' }}>
                Shine 395nm UV/White light into the SIM tray port. Inspect the paper LCI tape. Lay device face down on flat glass to measure corner lift.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '14px' }}>
                <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '12px', display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>Liquid Ingress Status:</span>
                  <span style={{ fontWeight: 800, fontSize: '0.84rem', color: scenario.lciStatus === 'PINK_RED' ? '#f87171' : '#34d399' }}>
                    {scenario.lciStatus === 'PINK_RED' ? 'Red (Water Damage Detected)' : 'White (No Liquid)'}
                  </span>
                </div>
                <div style={{ background: '#090e17', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px', padding: '12px', display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>Chassis Alignment:</span>
                  <span style={{ fontWeight: 800, fontSize: '0.84rem', color: scenario.chassisCondition === 'BENT' ? '#fbbf24' : '#34d399' }}>
                    {scenario.chassisCondition === 'BENT' ? 'Severe Bend Detected' : 'Flush / Nominal'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: PRE-REPAIR IQC DIAGNOSTIC MATRIX */}
          {step === 3 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <span style={{ background: '#38bdf8', color: '#000', borderRadius: '50%', width: '22px', height: '22px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '0.75rem' }}>3</span>
                <h4 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc' }}>6-Point Pre-Repair Diagnostic Matrix (IQC)</h4>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px' }}>
                {[
                  { id: 'touch', label: 'Touch / Digitizer Grid', val: scenario.iqcState.touchGrid },
                  { id: 'cameras', label: 'Front / Rear Optics', val: scenario.iqcState.cameras },
                  { id: 'audio', label: 'Audio / Mic / Haptics', val: scenario.iqcState.audioHaptics },
                  { id: 'bio', label: 'Biometrics (Face/Touch ID)', val: scenario.iqcState.biometricsFaceId },
                  { id: 'pwr', label: 'Power Draw (USB Meter)', val: scenario.iqcState.chargeCurrent }
                ].map(item => (
                  <div
                    key={item.id}
                    onClick={() => handleIqcToggle(item.id)}
                    style={{
                      background: checkedIqc[item.id] ? 'rgba(16, 185, 129, 0.15)' : '#090e17',
                      border: `1px solid ${checkedIqc[item.id] ? '#10b981' : 'rgba(255,255,255,0.08)'}`,
                      borderRadius: '8px',
                      padding: '10px',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px'
                    }}
                  >
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{item.label}</div>
                    <div style={{ fontSize: '0.84rem', fontWeight: 800, color: item.val.includes('FAIL') ? '#f87171' : item.val.includes('PASS') ? '#34d399' : '#fbbf24' }}>
                      {checkedIqc[item.id] ? '✓ Verified: ' : '○ Test: '} {item.val}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 4: CUSTOMER WAIVERS & SIGNATURES */}
          {step === 4 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <span style={{ background: '#38bdf8', color: '#000', borderRadius: '50%', width: '22px', height: '22px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '0.75rem' }}>4</span>
                <h4 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc' }}>Customer Risk Waivers & Authorization</h4>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
                {[
                  { key: 'dataLoss', title: 'Data Loss Disclaimer', desc: 'Customer acknowledges device memory may be wiped or reset during calibration.' },
                  { key: 'disassembly', title: 'Disassembly Authorization', desc: 'Customer authorizes technician to puncture original adhesive seals.' },
                  { key: 'preDamage', title: 'Pre-Existing Damage Acceptance', desc: 'Customer accepts documented cosmetic scuffs and bent frame notes.' }
                ].map(w => (
                  <div
                    key={w.key}
                    onClick={() => setWaiversSigned(prev => ({ ...prev, [w.key]: !prev[w.key] }))}
                    style={{
                      background: waiversSigned[w.key] ? 'rgba(16, 185, 129, 0.15)' : '#090e17',
                      border: `1px solid ${waiversSigned[w.key] ? '#10b981' : 'rgba(255,255,255,0.08)'}`,
                      borderRadius: '8px',
                      padding: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={waiversSigned[w.key]}
                      readOnly
                      style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                    />
                    <div>
                      <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#f8fafc' }}>{w.title}</div>
                      <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>{w.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 5: FINAL ROUTING & DISPATCH DECISION */}
          {step === 5 && !simResult && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <span style={{ background: '#38bdf8', color: '#000', borderRadius: '50%', width: '22px', height: '22px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '0.75rem' }}>5</span>
                <h4 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc' }}>NextGen Portal Final Action Decision</h4>
              </div>

              <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '14px' }}>
                Based on your physical inspection, IMEI audit, LCI status, and IQC checks, select the correct POS intake dispatch action:
              </p>

              <div className="aibs-portal-subgrid">
                <button
                  onClick={() => handleFinalDecision('APPROVE_SCREEN')}
                  style={{
                    background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.3))',
                    border: '1px solid #10b981',
                    color: '#34d399',
                    borderRadius: '10px',
                    padding: '14px',
                    fontWeight: 800,
                    fontSize: '0.84rem',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  🟢 Approve Screen Repair
                  <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px', fontWeight: 400 }}>
                    Bind OEM Display SKU & print ESD bin tag.
                  </div>
                </button>

                <button
                  onClick={() => handleFinalDecision('HALT_FRAUD')}
                  style={{
                    background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(185, 28, 28, 0.3))',
                    border: '1px solid #ef4444',
                    color: '#f87171',
                    borderRadius: '10px',
                    padding: '14px',
                    fontWeight: 800,
                    fontSize: '0.84rem',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  🛑 Halt Intake (IMEI Mismatch)
                  <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px', fontWeight: 400 }}>
                    Flag fraud / return device to customer.
                  </div>
                </button>

                <button
                  onClick={() => handleFinalDecision('ESCALATE_BER')}
                  style={{
                    background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(126, 34, 206, 0.3))',
                    border: '1px solid #c084fc',
                    color: '#c084fc',
                    borderRadius: '10px',
                    padding: '14px',
                    fontWeight: 800,
                    fontSize: '0.84rem',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  🟣 Escalate to BER (Liquid WUR)
                  <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px', fontWeight: 400 }}>
                    Trigger Asurion Whole Unit Replacement.
                  </div>
                </button>

                <button
                  onClick={() => handleFinalDecision('DECLINE_OR_HOUSING')}
                  style={{
                    background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(180, 83, 9, 0.3))',
                    border: '1px solid #f59e0b',
                    color: '#fbbf24',
                    borderRadius: '10px',
                    padding: '14px',
                    fontWeight: 800,
                    fontSize: '0.84rem',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  🟡 Decline Screen (Bent Frame)
                  <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px', fontWeight: 400 }}>
                    Require full chassis housing swap.
                  </div>
                </button>

                <button
                  onClick={() => handleFinalDecision('APPROVE_CHEMICAL_BATTERY')}
                  style={{
                    gridColumn: 'span 2',
                    background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(3, 105, 161, 0.3))',
                    border: '1px solid #38bdf8',
                    color: '#38bdf8',
                    borderRadius: '10px',
                    padding: '14px',
                    fontWeight: 800,
                    fontSize: '0.84rem',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  🔵 Chemical Battery Extraction Protocol
                  <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px', fontWeight: 400 }}>
                    iPad / Tablet 70°C pad + 99% IPA floss saw procedure.
                  </div>
                </button>
              </div>
            </div>
          )}

          {/* SIMULATION RESULT & SCORECARD */}
          {simResult && (
            <div style={{
              background: simResult.pass ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              border: `1px solid ${simResult.pass ? '#10b981' : '#ef4444'}`,
              borderRadius: '12px',
              padding: '18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontSize: '1.15rem', color: simResult.pass ? '#34d399' : '#f87171' }}>
                  {simResult.pass ? '🎉 Intake Approved & Certified!' : '❌ Franchise SOP Violation'}
                </h3>
                <span style={{ fontSize: '1.2rem', fontWeight: 900, color: '#fff', background: 'rgba(0,0,0,0.4)', padding: '4px 12px', borderRadius: '6px' }}>
                  +{simResult.score} pts
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {simResult.feedback.map((f, i) => (
                  <div key={i} style={{ fontSize: '0.82rem', color: '#e2e8f0' }}>{f}</div>
                ))}
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '8px', fontSize: '0.8rem', color: '#94a3b8' }}>
                💡 <strong>SOP Debrief:</strong> {simResult.explanation}
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                <button
                  onClick={() => resetScenario(currentScenarioIdx)}
                  style={{
                    flex: 1,
                    background: 'rgba(255,255,255,0.08)',
                    border: '1px solid rgba(255,255,255,0.2)',
                    color: '#fff',
                    padding: '10px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  🔄 Retry Scenario
                </button>
                <button
                  onClick={() => resetScenario((currentScenarioIdx + 1) % SCENARIOS.length)}
                  style={{
                    flex: 1,
                    background: '#38bdf8',
                    border: 'none',
                    color: '#000',
                    padding: '10px',
                    borderRadius: '8px',
                    fontWeight: 800,
                    cursor: 'pointer'
                  }}
                >
                  ➡️ Next Practice Drill
                </button>
              </div>
            </div>
          )}

          {/* Navigation Controls Footer */}
          {!simResult && (
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '16px', marginTop: '16px' }}>
              <button
                disabled={step === 1}
                onClick={() => setStep(prev => Math.max(1, prev - 1))}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: step === 1 ? '#475569' : '#cbd5e1',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: step === 1 ? 'not-allowed' : 'pointer'
                }}
              >
                ← Previous Step
              </button>

              {step < 5 ? (
                <button
                  onClick={() => setStep(prev => Math.min(5, prev + 1))}
                  style={{
                    background: '#38bdf8',
                    border: 'none',
                    color: '#000',
                    padding: '8px 20px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 800,
                    cursor: 'pointer'
                  }}
                >
                  Next Step →
                </button>
              ) : null}
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
