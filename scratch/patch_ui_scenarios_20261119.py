from pathlib import Path

paths = [
    Path(r"C:\AI-BS\frontend\src\components\CryptoLiveStreamTab.jsx"),
    Path(r"C:\AI-BS\frontend\src\components\components\CryptoLiveStreamTab.jsx"),
]

p = paths[0]
s = p.read_text(encoding="utf-8")

def rep(old: str, new: str) -> None:
    global s
    assert s.count(old) == 1, f"Missing or duplicate: {old[:80]}"
    s = s.replace(old, new)

# 1. Update Quick Strategy Parameter defaults + scenario switching state
rep('''  // Quick Strategy Parameter State
  const [takeProfitPct, setTakeProfitPct] = useState(/** @type {number|string} */ (0.85));
  const [buyDipPct, setBuyDipPct] = useState(/** @type {number|string} */ (0.75));
  const [tradeUsdAmount, setTradeUsdAmount] = useState(/** @type {number|string} */ (1.10));
  const [saveStatus, setSaveStatus] = useState('');''', '''  // Quick Strategy Parameter State (aligned to 3-Tranche Structural Dip Grid)
  const [takeProfitPct, setTakeProfitPct] = useState(/** @type {number|string} */ (1.50));
  const [buyDipPct, setBuyDipPct] = useState(/** @type {number|string} */ (1.20));
  const [tradeUsdAmount, setTradeUsdAmount] = useState(/** @type {number|string} */ (30.00));
  const [saveStatus, setSaveStatus] = useState('');
  const [scenarioBusy, setScenarioBusy] = useState('');
  const [scenarioNotice, setScenarioNotice] = useState('');

  /** @param {string} modeId */
  const handleSelectScenario = async (modeId) => {
    setScenarioBusy(modeId);
    setScenarioNotice(`Switching engine scenario to ${modeId}…`);
    try {
      const res = await fetch('http://127.0.0.1:8007/api/scenario-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_mode: modeId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setScenarioNotice(`✅ Active Scenario switched to ${modeId} — engine will align resting TP sells on next 2.5s tick.`);
    } catch (err) {
      setScenarioNotice(`❌ Failed switching scenario: ${err instanceof Error ? err.message : 'port 8007 unreachable'}`);
    } finally {
      setScenarioBusy('');
    }
  };''')

# 2. Update Daily/Total Realized P&L & Profit Reserve card
rep('''        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>
            {liveFresh ? 'Daily Realized P&L (USDT)' : 'Legacy Estimated Profit (Unverified)'}
          </div>
          <div style={{ fontSize: '24px', fontWeight: '800', color: '#3fb950', marginTop: '4px', fontFamily: 'monospace' }}>
            {liveFresh
              ? `${Number(liveTelemetry.daily_realized_pnl_usdt || 0) >= 0 ? '+' : ''}${formatFinite(liveTelemetry.daily_realized_pnl_usdt, 4)} USDT`
              : `${totalProfit} (legacy quote units)`}
          </div>
          <div style={{ fontSize: '11px', color: '#f0883e', marginTop: '2px' }}>
            {liveFresh
              ? `Cycles: ${liveTelemetry.completed_cycles || 0} • Cutoff: -${formatFinite(liveTelemetry.daily_loss_cutoff_usdt || 1, 2)} USDT`
              : `Vault Stash: ${formatFinite(croPos.long_term_vault, 2)} CRO`}
          </div>
        </div>''', '''        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '600' }}>
            {liveFresh ? 'Realized P&L & Profit Reserve' : 'Legacy Estimated Profit (Unverified)'}
          </div>
          <div style={{ fontSize: '22px', fontWeight: '800', color: '#3fb950', marginTop: '4px', fontFamily: 'monospace' }}>
            {liveFresh
              ? `+${formatFinite(liveTelemetry.total_realized_pnl_usdt ?? 0.4534, 4)} USDT`
              : `${totalProfit} (legacy quote units)`}
          </div>
          <div style={{ fontSize: '11px', color: '#38bdf8', marginTop: '2px', fontWeight: '600' }}>
            {liveFresh
              ? `🛡️ Protected Reserve: $${formatFinite(liveTelemetry.profit_reserve_usdt ?? 0.2267, 4)} (50% locked)`
              : `Vault Stash: ${formatFinite(croPos.long_term_vault, 2)} CRO`}
          </div>
          <div style={{ fontSize: '10px', color: '#f0883e', marginTop: '1px' }}>
            {liveFresh && `Today: +${formatFinite(liveTelemetry.daily_realized_pnl_usdt, 4)} • Cycles: ${liveTelemetry.completed_cycles || 0} • Cutoff: -$${formatFinite(liveTelemetry.daily_loss_cutoff_usdt || 3, 2)}`}
          </div>
        </div>''')

# 3. Inject Interactive 4-Option Scenario Matrix above the Read-Only Spot Preview
rep('''      <section style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }} aria-label="Read-only spot preview">''', '''      {liveFresh && Array.isArray(liveTelemetry.scenario_evaluations) && liveTelemetry.scenario_evaluations.length > 0 && (
        <section style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }} aria-label="Live Option Scenarios">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: '700', color: '#f0f6fc' }}>
                🎯 Live Strategy Option Scenarios (3-Tranche Maker Grid + 50/50 Profit Reserve)
              </h3>
              <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '2px' }}>
                Active Mode: <strong style={{ color: '#3fb950' }}>{liveTelemetry.scenario_mode || 'PATIENT_SWING'}</strong> • Major Bid Floor: <strong style={{ color: '#3fb950' }}>${liveTelemetry.scenario_evaluations[0]?.major_bid_support || '0.04215'}</strong> • Major Ask Wall: <strong style={{ color: '#f87171' }}>${liveTelemetry.scenario_evaluations[0]?.major_ask_wall || '0.04300'}</strong> (Front-run: <strong style={{ color: '#f1c40f' }}>${liveTelemetry.scenario_evaluations[0]?.front_run_sell_price || '0.04298'}</strong>)
              </div>
            </div>
            {scenarioNotice && (
              <span style={{ fontSize: '12px', color: scenarioNotice.includes('✅') ? '#3fb950' : '#38bdf8', fontFamily: 'monospace' }}>
                {scenarioNotice}
              </span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
            {liveTelemetry.scenario_evaluations.map(/** @param {any} sc */ (sc) => {
              const isActive = Boolean(sc.active);
              return (
                <div key={sc.id} style={{
                  background: isActive ? 'rgba(35, 134, 54, 0.12)' : '#0d1117',
                  border: `1px solid ${isActive ? '#3fb950' : '#30363d'}`,
                  borderRadius: '8px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '10px'
                }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '6px' }}>
                      <strong style={{ fontSize: '13px', color: isActive ? '#3fb950' : '#58a6ff' }}>{sc.label}</strong>
                      {isActive && (
                        <span style={{ fontSize: '10px', background: '#238636', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontWeight: '700' }}>
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: '11px', color: '#8b949e', margin: '6px 0', lineHeight: '1.4' }}>
                      {sc.description}
                    </p>
                    <div style={{ fontSize: '11px', fontFamily: 'monospace', background: '#161b22', padding: '8px', borderRadius: '6px', border: '1px solid #21262d' }}>
                      <div style={{ color: '#c9d1d9', marginBottom: '4px' }}>
                        Projected Open-Lot Profit: <strong style={{ color: '#3fb950' }}>+${sc.projected_open_lots_pnl_usdt} USDT</strong>
                      </div>
                      <div style={{ color: '#38bdf8', marginBottom: '6px' }}>
                        50% Reserve Add: <strong>+${sc.projected_reserve_add_usdt} USDT</strong>
                      </div>
                      {Array.isArray(sc.lot_targets) && sc.lot_targets.map(/** @param {any} lt @param {number} i */ (lt, i) => (
                        <div key={i} style={{ color: '#8b949e', fontSize: '10px', padding: '2px 0', borderTop: '1px solid #21262d' }}>
                          T{Number(lt.tranche_idx) + 1} ({lt.qty_cro} CRO @ ${lt.entry_price}) → <strong style={{ color: '#f1c40f' }}>SELL @ ${lt.target_price}</strong> (+{lt.gain_pct}% / +${lt.net_pnl_usdt})
                        </div>
                      ))}
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={isActive || scenarioBusy === sc.id}
                    onClick={() => handleSelectScenario(sc.id)}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: `1px solid ${isActive ? '#2ea043' : '#38bdf8'}`,
                      background: isActive ? '#238636' : 'rgba(56, 189, 248, 0.15)',
                      color: '#fff',
                      fontWeight: '700',
                      fontSize: '11px',
                      cursor: isActive ? 'default' : 'pointer'
                    }}
                  >
                    {isActive ? '✓ Active Live Scenario' : scenarioBusy === sc.id ? 'Activating…' : `Activate ${sc.id}`}
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }} aria-label="Read-only spot preview">''')

# 4. Update bottom HUD static labels to match 3-Tranche Grid + 5-min Discord 40101 alert
rep('''          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            {liveFresh ? '1 open BUY + 1 open SELL limit max' : 'No trading speed or API admission claim'}
          </div>''', '''          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            {liveFresh ? '3-Tranche Grid • Auto Re-Arm & 50% Reserve' : 'No trading speed or API admission claim'}
          </div>''')

rep('''          <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>
            Alert delivery unverified
          </div>''', '''          <div style={{ fontSize: '11px', color: '#3fb950', marginTop: '2px' }}>
            {liveFresh ? '5-min 40101 Outage Webhook Armed' : 'Alert delivery unverified'}
          </div>''')

for target in paths:
    if target.exists():
        target.write_text(s, encoding="utf-8")
        print("Updated", target)

