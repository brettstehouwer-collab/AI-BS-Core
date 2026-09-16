import React, { useState, useEffect } from 'react';
import {
  Gamepad2,
  Cpu,
  RefreshCw,
  Zap,
  Shield,
  Coins,
  Heart,
  Sliders,
  Terminal,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Layers,
  ArrowRight,
  RotateCcw,
  ExternalLink,
  Eye,
  EyeOff,
  Minimize2,
  Maximize2
} from 'lucide-react';

export default function ProcessMemoryLabTab({ backendUrl = 'http://localhost:8080' }) {
  const [activeSubTab, setActiveSubTab] = useState('gaming'); // 'gaming' or 'inspector'
  const [selectedProfile, setSelectedProfile] = useState('btd6');

  // Process Telemetry State
  const [processes, setProcesses] = useState([]);
  const [procSearch, setProcSearch] = useState('');
  const [selectedProc, setSelectedProc] = useState('BloonsTD6.exe');
  const [status, setStatus] = useState({ attached: false, pid: null, base_address: '0x0' });
  const [isAttaching, setIsAttaching] = useState(false);
  const [notice, setNotice] = useState(null);

  // Floating Translucent HUD Overlay State
  const [showWebOverlay, setShowWebOverlay] = useState(true);
  const [overlayMinimized, setOverlayMinimized] = useState(false);

  // Quick Key Features State (for BTD6)
  const [quickKeys, setQuickKeys] = useState({
    unlimitedCash: false,
    unlimitedLives: false,
    unlimitedCoins: false,
    zeroCostPlacement: false,
    instantCooldowns: false,
  });

  // Manual Memory Inspector State
  const [readAddress, setReadAddress] = useState('0x7FF6B0C40000');
  const [readType, setReadType] = useState('int32');
  const [readValue, setReadValue] = useState(null);
  const [writeAddress, setWriteAddress] = useState('');
  const [writeType, setWriteType] = useState('int32');
  const [writeValue, setWriteValue] = useState('');

  // Auto-Scan & Calibration State
  const [scanCashVal, setScanCashVal] = useState('650');
  const [scanCoinsVal, setScanCoinsVal] = useState('99999');
  const [isScanningCash, setIsScanningCash] = useState(false);
  const [isFilteringCash, setIsFilteringCash] = useState(false);
  const [isScanningCoins, setIsScanningCoins] = useState(false);


  // Fetch running processes
  const fetchProcesses = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/processes?search=${encodeURIComponent(procSearch)}`);
      if (res.ok) {
        const data = await res.json();
        setProcesses(data.processes || []);
      }
    } catch (e) {
      console.debug('Error fetching processes:', e);
    }
  };

  // Fetch current attachment status
  const fetchStatus = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.debug('Error fetching memory status:', e);
    }
  };

  useEffect(() => {
    fetchProcesses();
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleAttach = async (target) => {
    setIsAttaching(true);
    setNotice(null);
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/attach`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: target || selectedProc })
      });
      const data = await res.json();
      if (res.ok) {
        setNotice({ type: 'success', text: `Attached to ${target || selectedProc} (PID ${data.pid})` });
        fetchStatus();
      } else {
        setNotice({ type: 'error', text: data.detail || 'Failed to attach to process.' });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    } finally {
      setIsAttaching(false);
    }
  };

  const handleDetach = async () => {
    try {
      await fetch(`${backendUrl}/api/memory-lab/detach`, { method: 'POST' });
      fetchStatus();
      setNotice({ type: 'info', text: 'Detached memory engine cleanly.' });
    } catch (e) {
      console.debug('Error detaching:', e);
    }
  };

  const toggleFeature = async (featureName, stateKey) => {
    const nextState = !quickKeys[stateKey];
    setQuickKeys((prev) => ({ ...prev, [stateKey]: nextState }));

    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/profile/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: selectedProfile,
          feature_name: featureName,
          action: 'toggle'
        })
      });
      if (!res.ok) {
        // Revert on failure
        setQuickKeys((prev) => ({ ...prev, [stateKey]: !nextState }));
        const err = await res.json();
        setNotice({ type: 'error', text: err.detail });
      }
    } catch (e) {
      setQuickKeys((prev) => ({ ...prev, [stateKey]: !nextState }));
      setNotice({ type: 'error', text: e.message });
    }
  };

  const triggerOneShot = async (featureName) => {
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/profile/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: selectedProfile,
          feature_name: featureName,
          action: 'trigger'
        })
      });
      const data = await res.json();
      if (res.ok) {
        setNotice({ type: 'success', text: `Executed ${featureName} successfully!` });
      } else {
        setNotice({ type: 'error', text: data.detail });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    }
  };

  // Pop-Out Floating HUD Mini-Window
  const handlePopOutHud = () => {
    const popup = window.open(
      '',
      'AI_BS_Trainer_HUD',
      'width=350,height=430,menubar=no,toolbar=no,location=no,status=no,resizable=yes'
    );
    if (!popup) {
      alert('Popup was blocked by your browser. Please allow popups for AI-BS.');
      return;
    }

    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>AI-BS Trainer HUD</title>
        <meta charset="utf-8" />
        <style>
          body {
            margin: 0;
            padding: 14px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0b0f19;
            color: #f8fafc;
            user-select: none;
          }
          .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 8px;
            margin-bottom: 12px;
          }
          .title { font-size: 13px; font-weight: bold; color: #38bdf8; }
          .badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            background: #15803d;
            color: #fff;
            font-weight: 600;
          }
          .row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #131d31;
            padding: 8px 10px;
            border-radius: 6px;
            margin-bottom: 6px;
            font-size: 11px;
          }
          .key { font-family: monospace; color: #38bdf8; font-weight: bold; }
          .btn {
            background: #2563eb;
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 10px;
            cursor: pointer;
            font-weight: 600;
          }
          .btn.on { background: #16a34a; }
          .footer {
            margin-top: 12px;
            font-size: 9px;
            color: #64748b;
            text-align: center;
            border-top: 1px solid #1e293b;
            padding-top: 6px;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="title">⚡ AI-BS TRAINER HUD</div>
          <div class="badge">ACTIVE</div>
        </div>
        <div class="row">
          <div><span class="key">[F1/NUM1]</span> Match Cash</div>
          <button class="btn ${quickKeys.unlimitedCash ? 'on' : ''}" onclick="window.opener.postMessage({action:'toggle', feature:'Unlimited Match Cash', key:'unlimitedCash'}, '*')">${quickKeys.unlimitedCash ? 'ACTIVE' : 'OFF'}</button>
        </div>
        <div class="row">
          <div><span class="key">[F2/NUM2]</span> Match Lives</div>
          <button class="btn ${quickKeys.unlimitedLives ? 'on' : ''}" onclick="window.opener.postMessage({action:'toggle', feature:'Unlimited Match Lives', key:'unlimitedLives'}, '*')">${quickKeys.unlimitedLives ? 'ACTIVE' : 'OFF'}</button>
        </div>
        <div class="row">
          <div><span class="key">[F3/NUM3]</span> Add $50k</div>
          <button class="btn" style="background:#0284c7;" onclick="window.opener.postMessage({action:'trigger', feature:'Add $50,000 Match Cash'}, '*')">+ $50k</button>
        </div>
        <div class="row">
          <div><span class="key">[F7/NUM7]</span> 99k Coins</div>
          <div style="display:flex;gap:4px;">
            <button class="btn" style="background:#ca8a04;padding:3px 6px;" onclick="window.opener.postMessage({action:'directCoins', amount:99999}, '*')">99k</button>
            <button class="btn ${quickKeys.unlimitedCoins ? 'on' : ''}" onclick="window.opener.postMessage({action:'toggle', feature:'Unlimited Monkey Money', key:'unlimitedCoins'}, '*')">${quickKeys.unlimitedCoins ? 'LOCK' : 'OFF'}</button>
          </div>
        </div>
        <div class="row">
          <div><span class="key">[F4/NUM4]</span> Zero-Cost</div>
          <button class="btn ${quickKeys.zeroCostPlacement ? 'on' : ''}" onclick="window.opener.postMessage({action:'toggle', feature:'Zero-Cost Placement', key:'zeroCostPlacement'}, '*')">${quickKeys.zeroCostPlacement ? 'ACTIVE' : 'OFF'}</button>
        </div>
        <div class="row">
          <div><span class="key">[F5/NUM5]</span> Cooldowns</div>
          <button class="btn ${quickKeys.instantCooldowns ? 'on' : ''}" onclick="window.opener.postMessage({action:'toggle', feature:'Instant Ability Cooldowns', key:'instantCooldowns'}, '*')">${quickKeys.instantCooldowns ? 'ACTIVE' : 'OFF'}</button>
        </div>
        <div class="row">
          <div><span class="key">[F10/NUM0]</span> Reset All</div>
          <button class="btn" style="background:#475569;" onclick="window.opener.postMessage({action:'trigger', feature:'Reset & Restore Normal'}, '*')">RESET</button>
        </div>
        <div class="footer">[F6] Desktop Overlay | Live Bridge</div>
      </body>
      </html>
    `;
    popup.document.open();
    popup.document.write(htmlContent);
    popup.document.close();
  };

  // Listen to messages from pop-out HUD
  useEffect(() => {
    const handleMsg = (e) => {
      if (e.data?.action === 'toggle') {
        toggleFeature(e.data.feature, e.data.key);
      } else if (e.data?.action === 'trigger') {
        triggerOneShot(e.data.feature);
      } else if (e.data?.action === 'directCoins') {
        handleSetCoinsDirect(e.data.amount || 99999);
      }
    };
    window.addEventListener('message', handleMsg);
    return () => window.removeEventListener('message', handleMsg);
  }, [quickKeys, selectedProfile]);

  const handleReadMemory = async () => {
    setReadValue(null);
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: readAddress,
          data_type: readType,
          length: readType === 'string' ? 64 : 8
        })
      });
      const data = await res.json();
      if (res.ok) {
        setReadValue(data.value);
      } else {
        setNotice({ type: 'error', text: data.detail });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    }
  };

  const handleWriteMemory = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: writeAddress,
          data_type: writeType,
          value: writeValue
        })
      });
      const data = await res.json();
      if (res.ok) {
        setNotice({ type: 'success', text: `Successfully wrote value to ${writeAddress}` });
      } else {
        setNotice({ type: 'error', text: data.detail });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    }
  };

  const handleScanCash = async () => {
    setIsScanningCash(true);
    setNotice(null);
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/scan-cash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_cash: parseFloat(scanCashVal) || null })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.count > 0) {
          setNotice({
            type: 'success',
            text: `Locked ${data.count} cash address(es): ${data.locked_addresses.join(', ')}! Unlimited Cash (F1) and Add $50k (F3) are active.`
          });
        } else {
          setNotice({
            type: 'error',
            text: `No addresses matched $${scanCashVal}. Enter the exact cash currently displayed in your match.`
          });
        }
        fetchStatus();
      } else {
        setNotice({ type: 'error', text: data.detail || 'Scan failed' });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    } finally {
      setIsScanningCash(false);
    }
  };

  const handleFilterCash = async () => {
    setIsFilteringCash(true);
    setNotice(null);
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/filter-cash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_cash: parseFloat(scanCashVal) || 0 })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.locked_count > 0) {
          setNotice({
            type: 'success',
            text: `Successfully locked ${data.locked_count} cash address(es): ${data.locked_addresses.join(', ')}! Cheats are now active.`
          });
        } else if (data.candidates_count > 0) {
          setNotice({
            type: 'info',
            text: `Filtered down to ${data.candidates_count} candidate(s). Change cash in-game and click Next Scan again.`
          });
        } else {
          setNotice({
            type: 'error',
            text: `0 candidates matched $${scanCashVal}. Click Scan Cash to restart search.`
          });
        }
        fetchStatus();
      } else {
        setNotice({ type: 'error', text: data.detail || 'Filter scan failed' });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    } finally {
      setIsFilteringCash(false);
    }
  };

  const handleSetCashDirect = async (amt = 99999) => {
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/set-cash`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: amt })
      });
      const data = await res.json();
      if (res.ok) {
        setNotice({ type: 'success', text: `Injected $${amt.toLocaleString()} cash into ${data.updated_addresses.length} addresses!` });
        fetchStatus();
      } else {
        setNotice({ type: 'error', text: data.detail || 'Failed to inject cash' });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    }
  };

  const handleSetCoinsDirect = async (amt = 99999) => {
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/set-coins`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: amt })
      });
      const data = await res.json();
      if (res.ok) {
        setNotice({ type: 'success', text: `Injected ${amt.toLocaleString()} Monkey Money into ${data.updated_addresses.length} addresses!` });
        fetchStatus();
      } else {
        setNotice({ type: 'error', text: data.detail || 'Failed to inject Monkey Money' });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    }
  };

  const handleScanCoins = async () => {
    if (!scanCoinsVal) {
      setNotice({ type: 'error', text: 'Enter your current Monkey Money count first.' });
      return;
    }
    setIsScanningCoins(true);
    setNotice(null);
    try {
      const res = await fetch(`${backendUrl}/api/memory-lab/scan-coins`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_coins: parseInt(scanCoinsVal, 10) })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.count > 0) {
          setNotice({
            type: 'success',
            text: `Locked ${data.count} Monkey Money address(es): ${data.locked_addresses.join(', ')}! Press F7 to add 50,000!`
          });
        } else {
          setNotice({
            type: 'error',
            text: `No addresses matched ${scanCoinsVal} Monkey Money.`
          });
        }
        fetchStatus();
      } else {
        setNotice({ type: 'error', text: data.detail || 'Coins scan failed' });
      }
    } catch (e) {
      setNotice({ type: 'error', text: e.message });
    } finally {
      setIsScanningCoins(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto', color: '#e2e8f0' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)', padding: '10px', borderRadius: '10px' }}>
              <Gamepad2 size={24} color="#ffffff" />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: '700', color: '#f8fafc' }}>
                Gaming & Process Memory Lab
              </h2>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Win32 Runtime Memory Manipulation, Pointer Resolution & Process Automation Suite
              </div>
            </div>
          </div>
        </div>

        {/* Tab Controls */}
        <div style={{ display: 'flex', gap: '8px', background: '#0f172a', padding: '4px', borderRadius: '8px', border: '1px solid #334155' }}>
          <button
            onClick={() => setActiveSubTab('gaming')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.85rem',
              background: activeSubTab === 'gaming' ? '#2563eb' : 'transparent',
              color: activeSubTab === 'gaming' ? '#ffffff' : '#94a3b8',
              transition: 'all 0.2s ease'
            }}
          >
            <Gamepad2 size={16} />
            Gaming Trainer Deck
          </button>
          <button
            onClick={() => setActiveSubTab('inspector')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.85rem',
              background: activeSubTab === 'inspector' ? '#2563eb' : 'transparent',
              color: activeSubTab === 'inspector' ? '#ffffff' : '#94a3b8',
              transition: 'all 0.2s ease'
            }}
          >
            <Cpu size={16} />
            Memory Inspector & Automation
          </button>
        </div>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div
          style={{
            marginBottom: '20px',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: notice.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(34, 197, 94, 0.15)',
            border: `1px solid ${notice.type === 'error' ? '#ef4444' : '#22c55e'}`,
            color: notice.type === 'error' ? '#fca5a5' : '#86efac'
          }}
        >
          {notice.type === 'error' ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
          <span>{notice.text}</span>
        </div>
      )}

      {/* Target Attachment Ribbon */}
      <div
        style={{
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '12px',
          padding: '18px 24px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>TARGET EXECUTABLE</div>
            <select
              value={selectedProc}
              onChange={(e) => setSelectedProc(e.target.value)}
              style={{
                background: '#0f172a',
                border: '1px solid #475569',
                color: '#f8fafc',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.85rem'
              }}
            >
              <option value="BloonsTD6.exe">BloonsTD6.exe (Desktop)</option>
              <option value="python.exe">python.exe (Titan Arena Mock)</option>
              {processes.map((p) => (
                <option key={p.pid} value={p.name}>
                  {p.name} (PID {p.pid} - {p.memory_mb} MB)
                </option>
              ))}
            </select>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>CONNECTION STATE</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: status.attached ? '#22c55e' : '#ef4444'
                }}
              />
              <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>
                {status.attached ? `ATTACHED (PID ${status.pid})` : 'DISCONNECTED'}
              </span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>MODULE BASE ADDRESS</div>
            <div style={{ fontSize: '0.85rem', fontFamily: 'monospace', color: '#38bdf8' }}>
              {status.base_address || '0x0'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          {status.attached ? (
            <button
              onClick={handleDetach}
              style={{
                background: '#dc2626',
                border: 'none',
                color: '#ffffff',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem'
              }}
            >
              Detach Engine
            </button>
          ) : (
            <button
              onClick={() => handleAttach(selectedProc)}
              disabled={isAttaching}
              style={{
                background: '#2563eb',
                border: 'none',
                color: '#ffffff',
                padding: '8px 18px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {isAttaching ? <RefreshCw size={14} className="spin" /> : <Zap size={14} />}
              Attach to Process
            </button>
          )}
        </div>
      </div>

      {/* SUB-TAB 1: GAMING TRAINER DECK */}
      {activeSubTab === 'gaming' && (
        <div>
          {/* Operational Boundaries Notice */}
          <div
            style={{
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '8px',
              padding: '14px 18px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px'
            }}
          >
            <Shield size={20} color="#60a5fa" style={{ marginTop: '2px', flexShrink: 0 }} />
            <div style={{ fontSize: '0.82rem', color: '#bfdbfe', lineHeight: '1.5' }}>
              <strong>Single-Player / Offline Policy:</strong> This trainer profile operates strictly in local memory for single-player maps and offline sandboxes.
              In-game match cash is stored locally as an IEEE 754 64-bit float (`double`). Persistent store coins (Monkey Money) synchronize with cloud servers and cannot be altered client-side.
            </div>
          </div>

          {/* In-Game Cash & Coins Calibration & Auto-Lock Card */}
          <div
            style={{
              background: '#131d31',
              border: '1px solid #1e3a8a',
              borderRadius: '10px',
              padding: '18px 20px',
              marginBottom: '24px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '1.1rem' }}>🎯</span>
                <span style={{ fontWeight: '700', fontSize: '0.95rem', color: '#38bdf8' }}>
                  In-Game Match Cash & Coins Auto-Lock
                </span>
                <span style={{ fontSize: '0.75rem', background: '#1e293b', padding: '2px 8px', borderRadius: '4px', color: '#94a3b8' }}>
                  Heap Scanner
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                Status: <strong style={{ color: status?.btd6_trainer?.cash_addresses?.length > 0 ? '#4ade80' : '#f87171' }}>
                  {status?.btd6_trainer?.cash_addresses?.length > 0
                    ? `Locked (${status.btd6_trainer.cash_addresses.length} addrs)`
                    : 'Not Locked Yet'}
                </strong>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              {/* Cash Calibration Block */}
              <div style={{ background: '#0b1120', padding: '12px 14px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: '600' }}>1. Match Cash ($)</span>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {[650, 850, 450, 1750].map((val) => (
                      <button
                        key={val}
                        onClick={() => setScanCashVal(val.toString())}
                        style={{
                          background: '#1e293b',
                          border: '1px solid #334155',
                          color: '#cbd5e1',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          fontSize: '0.68rem',
                          cursor: 'pointer'
                        }}
                      >
                        ${val}
                      </button>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  <input
                    type="number"
                    value={scanCashVal}
                    onChange={(e) => setScanCashVal(e.target.value)}
                    placeholder="650"
                    style={{
                      flex: 1,
                      minWidth: '80px',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  />
                  <button
                    onClick={handleScanCash}
                    disabled={isScanningCash}
                    style={{
                      background: '#2563eb',
                      border: 'none',
                      color: '#ffffff',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                    title="First scan for current displayed cash"
                  >
                    {isScanningCash ? 'Scanning...' : '🔍 First Scan'}
                  </button>
                  <button
                    onClick={handleFilterCash}
                    disabled={isFilteringCash}
                    style={{
                      background: '#16a34a',
                      border: 'none',
                      color: '#ffffff',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                    title="Filter down candidate addresses after cash changes in-game"
                  >
                    {isFilteringCash ? 'Filtering...' : '🎯 Next Scan'}
                  </button>
                  <button
                    onClick={() => handleSetCashDirect(99999)}
                    style={{
                      background: '#047857',
                      border: 'none',
                      color: '#ffffff',
                      padding: '6px 10px',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                    title="Directly inject $99,999 to locked cash addresses"
                  >
                    ⚡ $99.9k
                  </button>
                </div>
                {status?.btd6_trainer?.cash_candidates_count > 0 && (!status?.btd6_trainer?.cash_addresses || status?.btd6_trainer?.cash_addresses.length === 0) && (
                  <div style={{ marginTop: '6px', fontSize: '0.72rem', color: '#f59e0b' }}>
                    Candidates: {status.btd6_trainer.cash_candidates_count} found (Spend cash in-game and click Next Scan)
                  </div>
                )}
                {status?.btd6_trainer?.cash_addresses?.length > 0 && (
                  <div style={{ marginTop: '6px', fontSize: '0.72rem', color: '#4ade80', fontFamily: 'monospace' }}>
                    Locked: {status.btd6_trainer.cash_addresses.join(', ')}
                  </div>
                )}
              </div>

              {/* Monkey Money Calibration Block */}
              <div style={{ background: '#0b1120', padding: '12px 14px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '6px', fontWeight: '600' }}>
                  2. Monkey Money / Coins (int32)
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="number"
                    value={scanCoinsVal}
                    onChange={(e) => setScanCoinsVal(e.target.value)}
                    placeholder="99999"
                    style={{
                      flex: 1,
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '6px',
                      padding: '6px 10px',
                      color: '#f8fafc',
                      fontSize: '0.85rem'
                    }}
                  />
                  <button
                    onClick={handleScanCoins}
                    disabled={isScanningCoins}
                    style={{
                      background: '#0284c7',
                      border: 'none',
                      color: '#ffffff',
                      padding: '6px 14px',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {isScanningCoins ? 'Scanning...' : 'Scan & Lock'}
                  </button>
                  <button
                    onClick={() => handleSetCoinsDirect(99999)}
                    style={{
                      background: '#ca8a04',
                      border: 'none',
                      color: '#ffffff',
                      padding: '6px 12px',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                    title="Directly inject 99,999 Monkey Money to locked addresses"
                  >
                    🪙 99,999
                  </button>
                </div>
                {status?.btd6_trainer?.coins_addresses?.length > 0 && (
                  <div style={{ marginTop: '8px', fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace' }}>
                    Locked: {status.btd6_trainer.coins_addresses.join(', ')}
                  </div>
                )}
              </div>
            </div>
          </div>


          {/* Quick Key Cards Grid */}
          {/* Quick Key Header & HUD Controls Toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '600', margin: 0, color: '#f1f5f9' }}>
              Pre-Filled Quick Keys (Bloons TD 6)
            </h3>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                onClick={() => setShowWebOverlay(!showWebOverlay)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: showWebOverlay ? 'rgba(56, 189, 248, 0.15)' : '#1e293b',
                  border: `1px solid ${showWebOverlay ? '#38bdf8' : '#475569'}`,
                  color: showWebOverlay ? '#38bdf8' : '#94a3b8',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                {showWebOverlay ? <Eye size={14} /> : <EyeOff size={14} />}
                {showWebOverlay ? 'Floating HUD: Visible' : 'Floating HUD: Hidden'}
              </button>

              <button
                onClick={handlePopOutHud}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: '#0284c7',
                  border: 'none',
                  color: '#ffffff',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.78rem',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                <ExternalLink size={14} />
                Pop-Out Mini HUD
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px', marginBottom: '32px' }}>
            {/* Card 1: Unlimited Match Cash */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(234, 179, 8, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Coins size={20} color="#eab308" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Unlimited Match Cash</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F1 / NUMPAD 1
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={quickKeys.unlimitedCash}
                  onChange={() => toggleFeature('Unlimited Match Cash', 'unlimitedCash')}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                Locks current round match cash to $99,999.0 (`double`). Enables endless tower upgrades in offline matches.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Memory Type: 64-bit Float (Double)</div>
            </div>

            {/* Card 2: Unlimited Match Lives */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(239, 68, 68, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Heart size={20} color="#ef4444" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Unlimited Lives</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F2 / NUMPAD 2
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={quickKeys.unlimitedLives}
                  onChange={() => toggleFeature('Unlimited Match Lives', 'unlimitedLives')}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                Locks single-player match lives to 99,999. Prevents game over when bloons leak.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Memory Type: 64-bit Float (Double)</div>
            </div>

            {/* Card 3: Instant Add Cash */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(34, 197, 94, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Zap size={20} color="#22c55e" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Add $50,000 Cash</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F3 / NUMPAD 3
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => triggerOneShot('Add $50,000 Match Cash')}
                  style={{
                    background: '#15803d',
                    border: 'none',
                    color: '#ffffff',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    fontWeight: '600'
                  }}
                >
                  + $50k
                </button>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                One-shot trigger that reads current cash and adds 50,000 instantly without locking.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Action: Read + Add Primitive</div>
            </div>

            {/* Card 4: Zero-Cost Placement */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(168, 85, 247, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Sliders size={20} color="#a855f7" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Zero-Cost Placement</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F4 / NUMPAD 4
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={quickKeys.zeroCostPlacement}
                  onChange={() => toggleFeature('Zero-Cost Placement', 'zeroCostPlacement')}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                NOPs out the cash decrement instruction in GameAssembly.dll. Towers place for free.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Action: Byte Patching / NOP</div>
            </div>

            {/* Card 5: Instant Ability Cooldowns */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(14, 165, 233, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Activity size={20} color="#0ea5e9" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Instant Cooldowns</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F5 / NUMPAD 5
                    </span>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={quickKeys.instantCooldowns}
                  onChange={() => toggleFeature('Instant Ability Cooldowns', 'instantCooldowns')}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                Resets active ability timers on heroes and towers for continuous activation.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Action: Timer Reset Loop</div>
            </div>

            {/* Card 6: Toggle On-Screen HUD */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(56, 189, 248, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Eye size={20} color="#38bdf8" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Transparent HUD</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F6
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => triggerOneShot('Toggle On-Screen HUD')}
                  style={{
                    background: '#0284c7',
                    border: 'none',
                    color: '#ffffff',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    fontWeight: '600'
                  }}
                >
                  Toggle HUD
                </button>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                Shows or hides the on-screen transparent HUD overlay while playing the game.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Action: Win32 Layered Overlay</div>
            </div>

            {/* Card 7: Unlimited Monkey Money */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(202, 138, 4, 0.15)', padding: '8px', borderRadius: '8px' }}>
                    <Coins size={20} color="#ca8a04" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Unlimited Monkey Money</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#38bdf8', fontWeight: '600' }}>
                      F7 / NUMPAD 7
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    onClick={() => handleSetCoinsDirect(99999)}
                    style={{
                      background: '#ca8a04',
                      border: 'none',
                      color: '#ffffff',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      fontWeight: '600'
                    }}
                    title="Directly inject 99,999 Monkey Money"
                  >
                    🪙 99,999
                  </button>
                  <input
                    type="checkbox"
                    checked={quickKeys.unlimitedCoins}
                    onChange={() => toggleFeature('Unlimited Monkey Money', 'unlimitedCoins')}
                    style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                  />
                </div>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                Locks and continuously freezes Monkey Money (Coins) to 99,999 (int32). Once scanned, upgrades, heroes, powers, and continues are unlimited.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Memory Type: 32-bit Integer (Continuous Freeze)</div>
            </div>

            {/* Card 0: Reset & Restore */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ background: 'rgba(100, 116, 139, 0.2)', padding: '8px', borderRadius: '8px' }}>
                    <RotateCcw size={20} color="#94a3b8" />
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', fontSize: '0.95rem' }}>Reset & Restore</div>
                    <span style={{ fontSize: '0.72rem', background: '#0f172a', padding: '2px 6px', borderRadius: '4px', color: '#94a3b8', fontWeight: '600' }}>
                      F10 / NUMPAD 0
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => triggerOneShot('Reset & Restore Normal')}
                  style={{
                    background: '#334155',
                    border: 'none',
                    color: '#ffffff',
                    padding: '4px 10px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    fontWeight: '600'
                  }}
                >
                  Restore
                </button>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: '0 0 14px 0' }}>
                Disables all active freezes and restores original bytecode in target memory.
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Action: Rollback Engine</div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: PROCESS MEMORY INSPECTOR & AUTOMATION LAB */}
      {activeSubTab === 'inspector' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '24px' }}>
          {/* Live Memory Reader */}
          <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '24px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={18} color="#38bdf8" />
              Live Memory Reader
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Target Memory Address (Hex)</label>
                <input
                  type="text"
                  value={readAddress}
                  onChange={(e) => setReadAddress(e.target.value)}
                  placeholder="0x7FF6B0C40000"
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    border: '1px solid #475569',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    color: '#38bdf8',
                    fontFamily: 'monospace'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Data Type</label>
                  <select
                    value={readType}
                    onChange={(e) => setReadType(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid #475569',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: '#f8fafc'
                    }}
                  >
                    <option value="int32">32-bit Signed Int</option>
                    <option value="uint32">32-bit Unsigned Int</option>
                    <option value="int64">64-bit Int</option>
                    <option value="float">32-bit Float</option>
                    <option value="double">64-bit Double</option>
                    <option value="string">String (UTF-8)</option>
                    <option value="hex">Raw Hex Dump</option>
                  </select>
                </div>
                <div style={{ alignSelf: 'flex-end' }}>
                  <button
                    onClick={handleReadMemory}
                    style={{
                      background: '#2563eb',
                      border: 'none',
                      color: '#ffffff',
                      padding: '9px 20px',
                      borderRadius: '6px',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    Read Address
                  </button>
                </div>
              </div>

              {readValue !== null && (
                <div style={{ marginTop: '10px', background: '#0f172a', padding: '14px', borderRadius: '8px', border: '1px solid #334155' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '4px' }}>VALUE AT {readAddress}</div>
                  <div style={{ fontSize: '1.2rem', fontFamily: 'monospace', color: '#4ade80', fontWeight: '700' }}>
                    {String(readValue)}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Live Memory Writer */}
          <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '24px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} color="#a855f7" />
              Live Memory Writer / State Mutator
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Target Memory Address (Hex)</label>
                <input
                  type="text"
                  value={writeAddress}
                  onChange={(e) => setWriteAddress(e.target.value)}
                  placeholder="0x7FF6B0C40000"
                  style={{
                    width: '100%',
                    background: '#0f172a',
                    border: '1px solid #475569',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    color: '#38bdf8',
                    fontFamily: 'monospace'
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Data Type</label>
                  <select
                    value={writeType}
                    onChange={(e) => setWriteType(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid #475569',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: '#f8fafc'
                    }}
                  >
                    <option value="int32">32-bit Signed Int</option>
                    <option value="uint32">32-bit Unsigned Int</option>
                    <option value="int64">64-bit Int</option>
                    <option value="float">32-bit Float</option>
                    <option value="double">64-bit Double</option>
                    <option value="string">String (UTF-8)</option>
                    <option value="hex">Hex Bytes</option>
                  </select>
                </div>
                <div style={{ flex: 2 }}>
                  <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>New Value</label>
                  <input
                    type="text"
                    value={writeValue}
                    onChange={(e) => setWriteValue(e.target.value)}
                    placeholder="9999999"
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid #475569',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      color: '#f8fafc'
                    }}
                  />
                </div>
              </div>

              <button
                onClick={handleWriteMemory}
                style={{
                  marginTop: '6px',
                  background: '#9333ea',
                  border: 'none',
                  color: '#ffffff',
                  padding: '10px 20px',
                  borderRadius: '6px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Write to Process Memory
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Translucent On-Screen HUD Overlay */}
      {showWebOverlay && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            zIndex: 9999,
            width: overlayMinimized ? '220px' : '310px',
            background: 'rgba(11, 15, 25, 0.88)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            borderRadius: '12px',
            boxShadow: '0 12px 40px rgba(0, 0, 0, 0.75)',
            overflow: 'hidden',
            transition: 'width 0.2s ease, height 0.2s ease'
          }}
        >
          {/* Overlay Header */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '10px 14px',
              background: 'rgba(17, 24, 39, 0.95)',
              borderBottom: '1px solid rgba(56, 189, 248, 0.2)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: status.attached ? '#22c55e' : '#f59e0b'
                }}
              />
              <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#38bdf8', letterSpacing: '0.5px' }}>
                BTD6 HUD
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={() => setOverlayMinimized(!overlayMinimized)}
                title={overlayMinimized ? 'Expand HUD' : 'Minimize HUD'}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                {overlayMinimized ? <Maximize2 size={13} /> : <Minimize2 size={13} />}
              </button>
              <button
                onClick={() => setShowWebOverlay(false)}
                title="Hide HUD"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                <EyeOff size={13} />
              </button>
            </div>
          </div>

          {/* Overlay Body (If Expanded) */}
          {!overlayMinimized && (
            <div style={{ padding: '12px 14px' }}>
              {/* Row 1: Cash */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>[F1]</span>
                  <span>Match Cash</span>
                </div>
                <button
                  onClick={() => toggleFeature('Unlimited Match Cash', 'unlimitedCash')}
                  style={{
                    background: quickKeys.unlimitedCash ? '#16a34a' : '#1e293b',
                    border: `1px solid ${quickKeys.unlimitedCash ? '#22c55e' : '#475569'}`,
                    color: quickKeys.unlimitedCash ? '#ffffff' : '#94a3b8',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {quickKeys.unlimitedCash ? 'ACTIVE' : 'OFF'}
                </button>
              </div>

              {/* Row 2: Lives */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>[F2]</span>
                  <span>Match Lives</span>
                </div>
                <button
                  onClick={() => toggleFeature('Unlimited Match Lives', 'unlimitedLives')}
                  style={{
                    background: quickKeys.unlimitedLives ? '#16a34a' : '#1e293b',
                    border: `1px solid ${quickKeys.unlimitedLives ? '#22c55e' : '#475569'}`,
                    color: quickKeys.unlimitedLives ? '#ffffff' : '#94a3b8',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {quickKeys.unlimitedLives ? 'ACTIVE' : 'OFF'}
                </button>
              </div>

              {/* Row 3: Add Cash */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>[F3]</span>
                  <span>Add $50,000</span>
                </div>
                <button
                  onClick={() => triggerOneShot('Add $50,000 Match Cash')}
                  style={{
                    background: '#0284c7',
                    border: 'none',
                    color: '#ffffff',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  + $50k
                </button>
              </div>

              {/* Row 7: Unlimited Monkey Money */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>[F7]</span>
                  <span>99k Coins</span>
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => handleSetCoinsDirect(99999)}
                    style={{
                      background: '#ca8a04',
                      border: 'none',
                      color: '#ffffff',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontSize: '0.68rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                    title="Direct Inject 99,999"
                  >
                    99k
                  </button>
                  <button
                    onClick={() => toggleFeature('Unlimited Monkey Money', 'unlimitedCoins')}
                    style={{
                      background: quickKeys.unlimitedCoins ? '#16a34a' : '#1e293b',
                      border: `1px solid ${quickKeys.unlimitedCoins ? '#22c55e' : '#475569'}`,
                      color: quickKeys.unlimitedCoins ? '#ffffff' : '#94a3b8',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}
                  >
                    {quickKeys.unlimitedCoins ? 'LOCK' : 'OFF'}
                  </button>
                </div>
              </div>

              {/* Row 4: Zero-Cost */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>[F4]</span>
                  <span>Zero-Cost</span>
                </div>
                <button
                  onClick={() => toggleFeature('Zero-Cost Placement', 'zeroCostPlacement')}
                  style={{
                    background: quickKeys.zeroCostPlacement ? '#16a34a' : '#1e293b',
                    border: `1px solid ${quickKeys.zeroCostPlacement ? '#22c55e' : '#475569'}`,
                    color: quickKeys.zeroCostPlacement ? '#ffffff' : '#94a3b8',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {quickKeys.zeroCostPlacement ? 'ACTIVE' : 'OFF'}
                </button>
              </div>

              {/* Row 5: Cooldowns */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>[F5]</span>
                  <span>Cooldowns</span>
                </div>
                <button
                  onClick={() => toggleFeature('Instant Ability Cooldowns', 'instantCooldowns')}
                  style={{
                    background: quickKeys.instantCooldowns ? '#16a34a' : '#1e293b',
                    border: `1px solid ${quickKeys.instantCooldowns ? '#22c55e' : '#475569'}`,
                    color: quickKeys.instantCooldowns ? '#ffffff' : '#94a3b8',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {quickKeys.instantCooldowns ? 'ACTIVE' : 'OFF'}
                </button>
              </div>

              {/* Row 6: Reset */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px', borderTop: '1px solid #1e293b', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#94a3b8', fontWeight: 'bold' }}>[F10]</span>
                  <span style={{ color: '#94a3b8' }}>Reset Normal</span>
                </div>
                <button
                  onClick={() => triggerOneShot('Reset & Restore Normal')}
                  style={{
                    background: '#334155',
                    border: 'none',
                    color: '#f8fafc',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  RESET
                </button>
              </div>

              {/* Overlay Footer Note */}
              <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(56, 189, 248, 0.15)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.68rem', color: '#64748b' }}>[F6] Desktop Overlay</span>
                <button
                  onClick={handlePopOutHud}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#38bdf8',
                    fontSize: '0.68rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <ExternalLink size={10} />
                  Pop-Out
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
