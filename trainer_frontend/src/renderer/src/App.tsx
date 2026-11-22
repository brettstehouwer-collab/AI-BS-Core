import { useState, useEffect, useRef } from 'react'

interface StateUpdate {
  type: string
  status: string
  pid: number
  cash_locked: boolean
  cash_addresses: string[]
  cash_candidates_count: number
  lives_locked: boolean
  lives_addresses: string[]
  lives_candidates_count: number
  coins_locked: boolean
  coins_addresses: string[]
  coins_candidates_count: number
  features: Record<string, any>
  variables: Record<string, any>
}

interface LogEntry {
  id: number
  time: string
  level: string
  message: string
}

function App() {
  const [activeTab, setActiveTab] = useState<'scanner' | 'cheats' | 'variables' | 'logs'>('scanner')
  const [status, setStatus] = useState<'SEARCHING' | 'ATTACHED'>('SEARCHING')
  const [pid, setPid] = useState<number>(0)

  // Memory Locks & Candidates
  const [cashLocked, setCashLocked] = useState<boolean>(false)
  const [cashAddresses, setCashAddresses] = useState<string[]>([])
  const [cashCandidatesCount, setCashCandidatesCount] = useState<number>(0)

  const [livesLocked, setLivesLocked] = useState<boolean>(false)
  const [livesAddresses, setLivesAddresses] = useState<string[]>([])
  const [livesCandidatesCount, setLivesCandidatesCount] = useState<number>(0)

  const [coinsLocked, setCoinsLocked] = useState<boolean>(false)
  const [coinsAddresses, setCoinsAddresses] = useState<string[]>([])
  const [coinsCandidatesCount, setCoinsCandidatesCount] = useState<number>(0)

  // Cheats & Variables
  const [features, setFeatures] = useState<Record<string, any>>({
    'Unlimited Match Cash': false,
    'Unlimited Lives': false,
    'Unlimited Monkey Money': false,
    'Add $50k Cash': 'READY',
    'Zero-Cost Placement': false,
    'Instant Cooldowns': false,
    'Reset & Restore': 'READY'
  })
  const [variables, setVariables] = useState<Record<string, any>>({
    frozen_cash_val: 99999.0,
    frozen_lives_val: 99999.0,
    frozen_coins_val: 99999
  })

  // Inputs
  const [cashInput, setCashInput] = useState<string>('1300')
  const [livesInput, setLivesInput] = useState<string>('200')
  const [coinsInput, setCoinsInput] = useState<string>('99999')
  const [varInputs, setVarInputs] = useState<Record<string, string>>({})

  // Event Logs
  const [logs, setLogs] = useState<LogEntry[]>([])
  const logIdRef = useRef<number>(0)
  const logEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    window.api.onDaemonMessage((data: any) => {
      if (data.type === 'state_update') {
        const su = data as StateUpdate
        setStatus(su.status === 'ATTACHED' ? 'ATTACHED' : 'SEARCHING')
        setPid(su.pid || 0)

        setCashLocked(Boolean(su.cash_locked))
        setCashAddresses(su.cash_addresses || [])
        setCashCandidatesCount(su.cash_candidates_count || 0)

        setLivesLocked(Boolean(su.lives_locked))
        setLivesAddresses(su.lives_addresses || [])
        setLivesCandidatesCount(su.lives_candidates_count || 0)

        setCoinsLocked(Boolean(su.coins_locked))
        setCoinsAddresses(su.coins_addresses || [])
        setCoinsCandidatesCount(su.coins_candidates_count || 0)

        if (su.features) setFeatures(su.features)
        if (su.variables) setVariables(su.variables)
      } else if (data.type === 'log') {
        const now = new Date().toLocaleTimeString()
        setLogs((prev) => [
          ...prev.slice(-150),
          {
            id: ++logIdRef.current,
            time: now,
            level: data.level || 'info',
            message: data.message || ''
          }
        ])
      } else if (data.type === 'error') {
        const now = new Date().toLocaleTimeString()
        setLogs((prev) => [
          ...prev.slice(-150),
          {
            id: ++logIdRef.current,
            time: now,
            level: 'error',
            message: data.message || 'Daemon error'
          }
        ])
      }
    })
  }, [])

  useEffect(() => {
    if (activeTab === 'logs') {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, activeTab])

  // Actions
  const handleAutoCalibrate = () => {
    window.api.sendDaemonCommand({ action: 'auto_calibrate' })
  }

  const handleFirstScanCash = (valStr?: string) => {
    const val = parseFloat(valStr !== undefined ? valStr : cashInput)
    if (!isNaN(val)) {
      window.api.sendDaemonCommand({ action: 'first_scan_cash', value: val })
    }
  }

  const handleNextScanCash = () => {
    const val = parseFloat(cashInput)
    if (!isNaN(val)) {
      window.api.sendDaemonCommand({ action: 'next_scan_cash', value: val })
    }
  }

  const handleLockCash = () => {
    const val = parseFloat(cashInput)
    window.api.sendDaemonCommand({ action: 'lock_cash', value: isNaN(val) ? 99999.0 : val })
  }

  const handleAddCash = (amount: number = 50000.0) => {
    window.api.sendDaemonCommand({ action: 'add_cash', amount })
  }

  const handleFirstScanLives = (valStr?: string) => {
    const val = parseFloat(valStr !== undefined ? valStr : livesInput)
    if (!isNaN(val)) {
      window.api.sendDaemonCommand({ action: 'first_scan_lives', value: val })
    }
  }

  const handleNextScanLives = () => {
    const val = parseFloat(livesInput)
    if (!isNaN(val)) {
      window.api.sendDaemonCommand({ action: 'next_scan_lives', value: val })
    }
  }

  const handleLockLives = () => {
    const val = parseFloat(livesInput)
    window.api.sendDaemonCommand({ action: 'lock_lives', value: isNaN(val) ? 99999.0 : val })
  }

  const handleFirstScanCoins = () => {
    const val = parseInt(coinsInput, 10)
    if (!isNaN(val)) {
      window.api.sendDaemonCommand({ action: 'first_scan_coins', value: val })
    }
  }

  const handleNextScanCoins = () => {
    const val = parseInt(coinsInput, 10)
    if (!isNaN(val)) {
      window.api.sendDaemonCommand({ action: 'next_scan_coins', value: val })
    }
  }

  const handleSetCoins = (val: number = 99999) => {
    window.api.sendDaemonCommand({ action: 'set_coins', value: val })
  }

  const handleToggleFeature = (featureName: string) => {
    window.api.sendDaemonCommand({ action: 'toggle_feature', feature: featureName })
  }

  const handleSetVariable = (key: string) => {
    const raw = varInputs[key]
    if (raw !== undefined && raw !== '') {
      const num = parseFloat(raw)
      if (!isNaN(num)) {
        window.api.sendDaemonCommand({ action: 'set_variable', variable: key, value: num })
      }
    }
  }

  const cheatMetadata: Record<string, { fKey: string; numKey: string; desc: string }> = {
    'Unlimited Match Cash': { fKey: 'F1', numKey: 'NUM 1', desc: 'Continuous $99k/$9.9M freeze loop' },
    'Unlimited Lives': { fKey: 'F2', numKey: 'NUM 2', desc: 'Continuous 99,999 health God Mode' },
    'Add $50k Cash': { fKey: 'F3', numKey: 'NUM 3', desc: 'Instant +$50,000 cash inject' },
    'Zero-Cost Placement': { fKey: 'F4', numKey: 'NUM 4', desc: 'Tower cost memory patch' },
    'Instant Cooldowns': { fKey: 'F5', numKey: 'NUM 5', desc: 'Bypass ability recharge timers' },
    'Unlimited Monkey Money': { fKey: 'F7', numKey: 'NUM 7', desc: 'Continuous 99,999 coin freeze' },
    'Reset & Restore': { fKey: 'F10', numKey: 'NUM 0', desc: 'Disable cheats & restore normal memory' }
  }

  return (
    <>
      {/* Custom Frameless Window Titlebar */}
      <div className="window-topbar">
        <div className="topbar-brand">
          <span className="topbar-logo">🐵</span>
          <span>AI-BS BLOONS TD 6 TRAINER</span>
          <span className="topbar-tag">GO NATIVE IPC v5.253.0</span>
        </div>

        <div className="topbar-controls">
          <button className="window-ctrl-btn" onClick={() => window.api.minimizeWindow()} title="Minimize">
            —
          </button>
          <button className="window-ctrl-btn" onClick={() => window.api.maximizeWindow()} title="Maximize">
            □
          </button>
          <button className="window-ctrl-btn close" onClick={() => window.api.closeWindow()} title="Close">
            ✕
          </button>
        </div>
      </div>

      <div className="app-container">
        {/* Sidebar */}
        <div className="sidebar">
          <div
            className={`sidebar-icon ${activeTab === 'scanner' ? 'active' : ''}`}
            onClick={() => setActiveTab('scanner')}
            title="Memory Scanner & Calibration"
          >
            🎯
          </div>
          <div
            className={`sidebar-icon ${activeTab === 'cheats' ? 'active' : ''}`}
            onClick={() => setActiveTab('cheats')}
            title="Match Cheats"
          >
            ⚡
          </div>
          <div
            className={`sidebar-icon ${activeTab === 'variables' ? 'active' : ''}`}
            onClick={() => setActiveTab('variables')}
            title="Variables & Limits"
          >
            🎛️
          </div>
          <div
            className={`sidebar-icon ${activeTab === 'logs' ? 'active' : ''}`}
            onClick={() => setActiveTab('logs')}
            title="Live Telemetry Logs"
          >
            📊
          </div>
        </div>

        {/* Main Content Area */}
        <div className="main-content">
          {/* Hero Banner */}
          <div className="hero-banner">
            <div className="hero-top-row">
              <div className={`hero-status-pill ${status === 'ATTACHED' ? 'attached' : 'searching'}`}>
                {status === 'ATTACHED' ? `● ATTACHED (PID ${pid})` : '◌ SEARCHING FOR BLOONSTD6.EXE...'}
              </div>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span className={`status-badge ${cashLocked ? 'locked' : 'unlocked'}`}>
                  CASH: {cashLocked ? `LOCKED (${cashAddresses.length})` : 'UNLOCKED'}
                </span>
                <span className={`status-badge ${livesLocked ? 'locked' : 'unlocked'}`}>
                  LIVES: {livesLocked ? `LOCKED (${livesAddresses.length})` : 'UNLOCKED'}
                </span>
                <span className={`status-badge ${coinsLocked ? 'locked' : 'unlocked'}`}>
                  COINS: {coinsLocked ? `LOCKED (${coinsAddresses.length})` : 'UNLOCKED'}
                </span>
              </div>
            </div>

            <h1 className="hero-title">Bloons TD 6 Sovereign Trainer</h1>
            <p className="hero-subtitle">
              Native 64-bit Go Engine • Win32 Hotkey Poller • Double Cash Calibration • Sub-Millisecond Freeze Loop
            </p>

            <div className="hero-actions">
              <button
                className="launch-btn"
                onClick={() => window.api.openExternal('steam://rungameid/960090')}
              >
                ▶ Launch Steam Game
              </button>
              <button
                className="launch-btn"
                style={{ background: '#06b6d4', color: '#070a12', fontWeight: 700 }}
                onClick={handleAutoCalibrate}
              >
                ⚡ Auto-Calibrate (Scan All In-Game Values)
              </button>
              <button
                className="launch-btn"
                style={{ background: 'rgba(255,255,255,0.08)' }}
                onClick={() => {
                  setCashInput('1300')
                  handleFirstScanCash('1300')
                }}
              >
                🪙 Double Cash ($1,300)
              </button>
              <button
                className="launch-btn"
                style={{ background: 'rgba(255,255,255,0.08)' }}
                onClick={() => {
                  setCashInput('650')
                  handleFirstScanCash('650')
                }}
              >
                💵 Standard Cash ($650)
              </button>
            </div>

            {/* Quick In-Game Hotkey Bar */}
            <div style={{
              marginTop: '12px',
              padding: '8px 14px',
              background: 'rgba(0,0,0,0.4)',
              borderRadius: '6px',
              border: '1px solid rgba(255,255,255,0.08)',
              fontSize: '11px',
              display: 'flex',
              gap: '12px',
              alignItems: 'center',
              flexWrap: 'wrap'
            }}>
              <span style={{ color: '#06b6d4', fontWeight: 700 }}>🎮 IN-GAME HOTKEYS:</span>
              <span><strong>[F1]</strong> Freeze Cash</span>
              <span>•</span>
              <span><strong>[F2]</strong> God Mode Lives</span>
              <span>•</span>
              <span><strong>[F3]</strong> +$50,000 Cash</span>
              <span>•</span>
              <span><strong>[F7]</strong> 99k Coins</span>
              <span>•</span>
              <span><strong>[F10]</strong> Reset All</span>
            </div>
          </div>

          {/* Tab Bar */}
          <div className="tab-bar">
            <button
              className={`tab-btn ${activeTab === 'scanner' ? 'active' : ''}`}
              onClick={() => setActiveTab('scanner')}
            >
              🎯 Memory Scanner & Calibration
            </button>
            <button
              className={`tab-btn ${activeTab === 'cheats' ? 'active' : ''}`}
              onClick={() => setActiveTab('cheats')}
            >
              ⚡ Match Cheats (F1–F7, F10)
            </button>
            <button
              className={`tab-btn ${activeTab === 'variables' ? 'active' : ''}`}
              onClick={() => setActiveTab('variables')}
            >
              🎛️ Variables & Limits
            </button>
            <button
              className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
              onClick={() => setActiveTab('logs')}
            >
              📊 Telemetry & Logs ({logs.length})
            </button>
          </div>

          {/* TAB 1: SCANNER & CALIBRATION */}
          {activeTab === 'scanner' && (
            <div className="scanner-grid">
              {/* Card 1: Match Cash */}
              <div className="deck-card">
                <div className="card-header">
                  <span className="card-title">💵 Match Cash Calibration</span>
                  <span className={`status-badge ${cashLocked ? 'locked' : 'unlocked'}`}>
                    {cashLocked ? `LOCKED (${cashAddresses.length})` : 'UNLOCKED'}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Select starting cash preset or enter your exact displayed in-match cash value:
                </p>

                <div className="preset-pills">
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setCashInput('1300')
                      handleFirstScanCash('1300')
                    }}
                  >
                    [$1,300] Normal x2
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setCashInput('650')
                      handleFirstScanCash('650')
                    }}
                  >
                    [$650] Normal
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setCashInput('1700')
                      handleFirstScanCash('1700')
                    }}
                  >
                    [$1,700] Easy x2
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setCashInput('850')
                      handleFirstScanCash('850')
                    }}
                  >
                    [$850] Easy
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setCashInput('900')
                      handleFirstScanCash('900')
                    }}
                  >
                    [$900] Hard x2
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setCashInput('450')
                      handleFirstScanCash('450')
                    }}
                  >
                    [$450] Hard
                  </button>
                </div>

                <div className="scan-input-row">
                  <input
                    type="number"
                    className="scan-input"
                    placeholder="Enter cash (e.g. 1300)"
                    value={cashInput}
                    onChange={(e) => setCashInput(e.target.value)}
                  />
                  <button className="scan-btn first" onClick={() => handleFirstScanCash()}>
                    🔍 First Scan
                  </button>
                  <button className="scan-btn next" onClick={handleNextScanCash}>
                    🎯 Next Scan
                  </button>
                </div>

                {cashCandidatesCount > 0 && !cashLocked && (
                  <p style={{ fontSize: '11px', color: 'var(--accent-cyan)' }}>
                    Found <strong>{cashCandidatesCount}</strong> candidates. Spend cash in-game, enter new amount, and click <strong>Next Scan</strong>.
                  </p>
                )}

                {cashAddresses.length > 0 && (
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--accent-green)', fontWeight: 600 }}>
                      Verified Simulation Addresses:
                    </span>
                    <div className="address-chip-container">
                      {cashAddresses.map((addr) => (
                        <span key={addr} className="address-chip">
                          {addr}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 'auto', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    className="scan-btn"
                    style={{ background: 'rgba(6,182,212,0.15)', color: '#06b6d4', border: '1px solid rgba(6,182,212,0.3)', flex: 1 }}
                    onClick={() => handleAddCash(50000.0)}
                  >
                    ⚡ Inject +$50,000
                  </button>
                  <button
                    className="scan-btn"
                    style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)', flex: 1 }}
                    onClick={handleLockCash}
                  >
                    🔒 Lock Cash (F1)
                  </button>
                </div>
              </div>

              {/* Card 2: Match Lives (Hearts) */}
              <div className="deck-card">
                <div className="card-header">
                  <span className="card-title">❤️ Match Lives (God Mode)</span>
                  <span className={`status-badge ${livesLocked ? 'locked' : 'unlocked'}`}>
                    {livesLocked ? `LOCKED (${livesAddresses.length})` : 'UNLOCKED'}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Calibrate match health or freeze to 99,999 for instant invulnerability:
                </p>

                <div className="preset-pills">
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setLivesInput('200')
                      handleFirstScanLives('200')
                    }}
                  >
                    [200] Medium/Hard
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setLivesInput('150')
                      handleFirstScanLives('150')
                    }}
                  >
                    [150] Easy
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setLivesInput('100')
                      handleFirstScanLives('100')
                    }}
                  >
                    [100] Alternate
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setLivesInput('250')
                      handleFirstScanLives('250')
                    }}
                  >
                    [250] Co-op
                  </button>
                  <button
                    className="preset-pill"
                    onClick={() => {
                      setLivesInput('1')
                      handleFirstScanLives('1')
                    }}
                  >
                    [1] Sudden Death
                  </button>
                </div>

                <div className="scan-input-row">
                  <input
                    type="number"
                    className="scan-input"
                    placeholder="Enter lives (e.g. 200)"
                    value={livesInput}
                    onChange={(e) => setLivesInput(e.target.value)}
                  />
                  <button className="scan-btn first" onClick={() => handleFirstScanLives()}>
                    🔍 First Scan
                  </button>
                  <button className="scan-btn next" onClick={handleNextScanLives}>
                    🎯 Next Scan
                  </button>
                </div>

                {livesCandidatesCount > 0 && !livesLocked && (
                  <p style={{ fontSize: '11px', color: 'var(--accent-cyan)' }}>
                    Found <strong>{livesCandidatesCount}</strong> candidates. Leak a bloon, enter new health, and click <strong>Next Scan</strong>.
                  </p>
                )}

                {livesAddresses.length > 0 && (
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--accent-green)', fontWeight: 600 }}>
                      Locked Lives Address:
                    </span>
                    <div className="address-chip-container">
                      {livesAddresses.map((addr) => (
                        <span key={addr} className="address-chip">
                          {addr}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 'auto', display: 'flex', gap: '8px' }}>
                  <button
                    className="scan-btn"
                    style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)', width: '100%' }}
                    onClick={handleLockLives}
                  >
                    🛡️ Activate God Mode (F2)
                  </button>
                </div>
              </div>

              {/* Card 3: Monkey Money */}
              <div className="deck-card">
                <div className="card-header">
                  <span className="card-title">🪙 Monkey Money Calibration</span>
                  <span className={`status-badge ${coinsLocked ? 'locked' : 'unlocked'}`}>
                    {coinsLocked ? `LOCKED (${coinsAddresses.length})` : 'UNLOCKED'}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Calibrate your global profile monkey money for purchasing knowledge and heroes:
                </p>

                <div className="scan-input-row">
                  <input
                    type="number"
                    className="scan-input"
                    placeholder="Current Monkey Money amount"
                    value={coinsInput}
                    onChange={(e) => setCoinsInput(e.target.value)}
                  />
                  <button className="scan-btn first" onClick={handleFirstScanCoins}>
                    🔍 First Scan
                  </button>
                  <button className="scan-btn next" onClick={handleNextScanCoins}>
                    🎯 Next Scan
                  </button>
                </div>

                {coinsCandidatesCount > 0 && !coinsLocked && (
                  <p style={{ fontSize: '11px', color: 'var(--accent-cyan)' }}>
                    Found <strong>{coinsCandidatesCount}</strong> coin candidates. Spend/gain coins, update input, and click <strong>Next Scan</strong>.
                  </p>
                )}

                {coinsAddresses.length > 0 && (
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--accent-green)', fontWeight: 600 }}>
                      Locked Profile Address:
                    </span>
                    <div className="address-chip-container">
                      {coinsAddresses.map((addr) => (
                        <span key={addr} className="address-chip">
                          {addr}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 'auto', display: 'flex', gap: '8px' }}>
                  <button
                    className="scan-btn"
                    style={{ background: 'rgba(168,85,247,0.15)', color: '#a855f7', border: '1px solid rgba(168,85,247,0.3)', width: '100%' }}
                    onClick={() => handleSetCoins(99999)}
                  >
                    🪙 Instant 99,999 Monkey Money (F7)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CHEATS GRID */}
          {activeTab === 'cheats' && (
            <div className="cheats-grid">
              {Object.entries(features).map(([featName, activeState]) => {
                const meta = cheatMetadata[featName] || { fKey: 'HOTKEY', numKey: '', desc: 'Memory Feature' }
                const isToggle = typeof activeState === 'boolean'

                return (
                  <div
                    key={featName}
                    className="cheat-card"
                    onClick={() => handleToggleFeature(featName)}
                  >
                    <div className="cheat-info">
                      <h4>{featName}</h4>
                      <p>{meta.desc}</p>
                      <div className="cheat-badge-row">
                        <span className="key-badge">{meta.fKey}</span>
                        {meta.numKey && <span className="key-badge">{meta.numKey}</span>}
                      </div>
                    </div>

                    {isToggle ? (
                      <div className={`toggle-switch ${activeState ? 'active' : ''}`}>
                        <div className="toggle-slider"></div>
                      </div>
                    ) : (
                      <button
                        className="scan-btn"
                        style={{ padding: '6px 12px', fontSize: '11px', background: 'rgba(255,255,255,0.08)', color: '#94a3b8' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleToggleFeature(featName)
                        }}
                      >
                        TRIGGER
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* TAB 3: VARIABLES & LIMITS */}
          {activeTab === 'variables' && (
            <div className="cheats-grid">
              {Object.entries(variables).map(([key, val]) => (
                <div key={key} className="deck-card">
                  <div className="card-header">
                    <span className="card-title">{key}</span>
                    <span className="status-badge" style={{ background: 'rgba(255,255,255,0.08)', color: '#fff' }}>
                      Active: {val}
                    </span>
                  </div>

                  <div className="scan-input-row">
                    <input
                      type="number"
                      className="scan-input"
                      placeholder={`New ${key}`}
                      value={varInputs[key] || ''}
                      onChange={(e) => setVarInputs((p) => ({ ...p, [key]: e.target.value }))}
                    />
                    <button className="scan-btn next" onClick={() => handleSetVariable(key)}>
                      Set
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: LIVE TELEMETRY & LOGS */}
          {activeTab === 'logs' && (
            <div className="deck-card" style={{ height: '420px' }}>
              <div className="card-header">
                <span className="card-title">📊 Native Go Engine Telemetry & IPC Log Stream</span>
                <button
                  className="preset-pill"
                  onClick={() => setLogs([])}
                >
                  Clear Logs
                </button>
              </div>

              <div className="logs-container">
                {logs.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center', marginTop: '40px' }}>
                    No IPC logs recorded yet. Commands and state changes will stream here live.
                  </div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="log-line">
                      <span className="log-time">[{log.time}]</span>
                      <span className={`log-level ${log.level}`}>[{log.level.toUpperCase()}]</span>
                      <span className="log-msg">{log.message}</span>
                    </div>
                  ))
                )}
                <div ref={logEndRef} />
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default App
