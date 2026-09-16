# Combined IDE Components — Batch 1 (35 Files)

**Generated:** August 5, 2026  
**Scope:** First batch of 35 files with full original source code  
**Structure:** 4 heavily merged categories

---

## 1. Core Layout, Navigation & App Infrastructure

### Sidebar.jsx
```jsx
import React, { useState } from 'react';
import { masterHubs } from './navigationConfig';

const Sidebar = ({ activeTab, onTabChange }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div style={{
      width: isCollapsed ? '64px' : '220px',
      background: '#0d1117',
      borderRight: '1px solid #30363d',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflowY: 'auto',
      overflowX: 'hidden',
      transition: 'width 0.2s ease',
    }}>
      {/* Brand */}
      <div style={{
        padding: isCollapsed ? '16px 0' : '16px 12px',
        borderBottom: '1px solid #21262d',
        background: '#161b22',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {!isCollapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontSize: '0.7rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px', whiteSpace: 'nowrap' }}>
              Stehouwer Publishing
            </div>
            <div style={{ fontSize: '0.65rem', color: '#484f58' }}>v1.6.2 (Phase 4)</div>
          </div>
        )}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#8b949e',
            cursor: 'pointer',
            padding: '8px',
            margin: isCollapsed ? '0 auto' : '0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = '#21262d'; e.currentTarget.style.color = '#c9d1d9'; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#8b949e'; }}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? '»' : '«'}
        </button>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: '12px 0' }}>
        {!isCollapsed && (
          <div style={{
            padding: '4px 16px',
            fontSize: '0.65rem',
            color: '#484f58',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            marginBottom: '8px'
          }}>
            Master Workspace Hubs
          </div>
        )}
        {masterHubs.map((hub) => {
          const isHubActive = hub.key === activeTab || hub.subTabs.some(sub => sub.key === activeTab);
          return (
            <button
              key={hub.key}
              onClick={() => onTabChange?.(isHubActive ? activeTab : hub.defaultTab)}
              title={isCollapsed ? hub.label : ''}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: isCollapsed ? 'center' : 'flex-start',
                gap: isCollapsed ? '0' : '10px',
                padding: '10px 16px',
                border: 'none',
                background: isHubActive ? 'linear-gradient(135deg, rgba(31, 111, 235, 0.2), rgba(0, 240, 255, 0.1))' : 'transparent',
                color: isHubActive ? '#58a6ff' : '#8b949e',
                cursor: 'pointer',
                fontSize: '0.88rem',
                fontWeight: isHubActive ? 600 : 400,
                textAlign: 'left',
                borderLeft: isHubActive ? '3px solid #00f0ff' : '3px solid transparent',
                transition: 'all 0.15s ease',
                whiteSpace: 'nowrap',
                marginBottom: '4px'
              }}
              onMouseEnter={(e) => {
                if (!isHubActive) {
                  e.currentTarget.style.background = '#161b22';
                  e.currentTarget.style.color = '#c9d1d9';
                }
              }}
              onMouseLeave={(e) => {
                if (!isHubActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = '#8b949e';
                }
              }}
            >
              <span style={{ fontSize: '1.1rem' }}>{hub.icon}</span>
              {!isCollapsed && <span>{hub.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{
        padding: '12px',
        borderTop: '1px solid #21262d',
        fontSize: '0.7rem',
        color: '#484f58',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        overflow: 'hidden'
      }}>
        {isCollapsed ? '©' : 'AI-BS Matrix © 2026'}
      </div>
    </div>
  );
};

export default Sidebar;
```

### SubTabBar.jsx
```jsx
import React from 'react';
import { masterHubs } from './navigationConfig';

export default function SubTabBar({ activeTab, onTabChange }) {
  // Find which master hub contains activeTab
  const currentHub = masterHubs.find(hub => 
    hub.key === activeTab || hub.subTabs.some(sub => sub.key === activeTab)
  );

  if (!currentHub || currentHub.subTabs.length <= 1) {
    return null;
  }

  // Determine active subtab key
  const activeSubKey = currentHub.subTabs.some(sub => sub.key === activeTab)
    ? activeTab
    : currentHub.defaultTab;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      background: 'linear-gradient(135deg, rgba(13, 17, 23, 0.95), rgba(22, 27, 34, 0.95))',
      borderBottom: '1px solid rgba(0, 240, 255, 0.2)',
      backdropFilter: 'blur(10px)',
      overflowX: 'auto',
      whiteSpace: 'nowrap',
      zIndex: 90,
      scrollbarWidth: 'none', /* Firefox */
      msOverflowStyle: 'none',  /* IE/Edge */
    }}>
      <style dangerouslySetInnerHTML={{__html: `
        div::-webkit-scrollbar { display: none; }
      `}} />
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        fontSize: '0.85rem',
        fontWeight: 'bold',
        color: '#00f0ff',
        paddingRight: '12px',
        borderRight: '1px solid rgba(255, 255, 255, 0.1)',
        marginRight: '4px'
      }}>
        <span>{currentHub.icon}</span>
        <span>{currentHub.label}</span>
      </div>

      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        {currentHub.subTabs.map(sub => {
          const isActive = activeSubKey === sub.key;
          return (
            <button
              key={sub.key}
              onClick={() => onTabChange(sub.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '6px',
                border: isActive ? '1px solid #38bdf8' : '1px solid transparent',
                background: isActive ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(168, 85, 247, 0.25))' : 'rgba(255, 255, 255, 0.03)',
                color: isActive ? '#ffffff' : 'var(--text-muted, #8b949e)',
                fontSize: '0.82rem',
                fontWeight: isActive ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? '0 0 10px rgba(56, 189, 248, 0.3)' : 'none'
              }}
            >
              <span>{sub.icon}</span>
              <span>{sub.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

### navigationConfig.js
```js
export const masterHubs = [
  {
    key: 'stehouwer_publishing',
    label: 'Stehouwer Publishing',
    icon: '📚',
    defaultTab: 'unified_calendar',
    subTabs: [
      { key: 'unified_osint', label: 'OSINT Recon & API Hub', icon: '🌐' },
      { key: 'unified_calendar', label: 'Master Calendar & Scheduler', icon: '📅' },
      { key: 'unified_financial', label: 'Financial Ledger & Yields', icon: '💰' },
      { key: 'unified_creation', label: 'Creation Suite & CMS', icon: '✍️' },
      { key: 'email_client', label: 'Local Email', icon: '📧' },
      { key: 'security_monitor', label: 'Security & Telemetry', icon: '🛡️' }
    ]
  },
  {
    key: 'neural_intelligence',
    label: 'Neural Intelligence',
    icon: '🧠',
    defaultTab: 'dashboard',
    subTabs: [
      { key: 'dashboard', label: 'Command Center', icon: '📊' },
      { key: 'ide', label: 'Matrix IDE Workspace', icon: '💻' },
      { key: 'deep_learning_studio', label: 'Deep Learning Studio', icon: '🧠' },
      { key: 'agent_memory', label: 'Agent Memory', icon: '💾' },
      { key: 'reasoning_attention', label: 'Self-Refinement', icon: '⚡' },
      { key: 'trainer', label: 'Trainer Logs', icon: '📊' },
      { key: 'terminal', label: 'System Terminal', icon: '⌨️' },
      { key: 'vms', label: 'Virtual Machines', icon: '🖥️' },
    ]
  },
  {
    key: 'agency_clients',
    label: 'Agency & Revenue',
    icon: '💼',
    defaultTab: 'clients',
    subTabs: [
      { key: 'clients', label: 'Clients Hub', icon: '🏢' },
      { key: 'leadmatrix', label: 'Lead Matrix', icon: '🎯' },
      { key: 'advertising', label: 'Advertising Suite', icon: '📢' },
      { key: 'public_checkout', label: 'Pricing & Passes', icon: '💳' },
      { key: 'unified_crypto', label: 'Crypto & Mining Suite', icon: '⚡' },
    ]
  },
  {
    key: 'creator_studio',
    label: 'Creator Studio',
    icon: '🎨',
    defaultTab: 'digital_storefront',
    subTabs: [
      { key: 'digital_storefront', label: 'Digital Storefront', icon: '🏪' },
      { key: 'noco_vision', label: 'NoCo Vision', icon: '🎤' },
      { key: 'public_playground', label: 'AI Studio & Playground', icon: '🎨' },
      { key: 'personal_brand', label: 'Personal Brand Studio', icon: '🔥' },
    ]
  },
  {
    key: 'analytics_archives',
    label: 'Analytics & Archives',
    icon: '🌐',
    defaultTab: 'beta',
    subTabs: [
      { key: 'beta', label: 'Web Analytics', icon: '📈' },
      { key: 'learning_material_hub', label: 'Educational Modules', icon: '🎓' },
      { key: 'definitions', label: 'Definitions & Lore', icon: '📖' },
    ]
  }
];
```

### PaneLayout.jsx
```jsx
import React from 'react';
import { PanelGroup, Panel, ResizeHandle } from 'react-resizable-panels';

/**
 * PaneLayout provides a macro split between the Chat (sidebar) and Workspace (main).
 * It adjusts the split proportion based on the active tab:
 *   - 'visual' : shrink chat to 15%
 *   - 'terminal' : 50/50 split
 *   - other tabs : default 30% chat, 70% workspace
 */
export default function PaneLayout({ activeTab, children }) {
  const { sidebar, main } = children;
  const getSizes = () => {
    if (activeTab === 'visual') return [15, 85];
    if (activeTab === 'terminal') return [50, 50];
    return [30, 70];
  };
  const [chatSize, mainSize] = getSizes();
  return (
    <PanelGroup direction="horizontal" className="pane-layout">
      <Panel defaultSize={chatSize} minSize={10} maxSize={90} className="chat-pane">
        {sidebar}
      </Panel>
      <ResizeHandle className="resize-handle" />
      <Panel defaultSize={mainSize} minSize={10} maxSize={90} className="workspace-pane">
        {main}
      </Panel>
    </PanelGroup>
  );
}
```

### TerminalPanel.jsx
```jsx
import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

export default function TerminalPanel({ backendUrl }) {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);
  const commandRef = useRef('');

  useEffect(() => {
    const term = new Terminal({
      theme: {
        background: '#0a0a0a',
        foreground: '#00ff00',
        cursor: '#00ff00'
      },
      fontFamily: 'Courier New, monospace',
      fontSize: 14,
      cursorBlink: true
    });
    
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    
    if (terminalRef.current) {
      term.open(terminalRef.current);
    }

    const safeFit = () => {
      try {
        if (terminalRef.current && terminalRef.current.offsetWidth > 0 && terminalRef.current.offsetHeight > 0) {
          fitAddon.fit();
        }
      } catch (e) {
        // Silently catch dimension timing errors during DOM mounting
      }
    };

    setTimeout(safeFit, 50);
    
    term.writeln('\x1b[1;32mStehouwer OS Virtual Terminal [Version 1.0]\x1b[0m');
    term.writeln('(c) Stehouwer Productions. All rights reserved.');
    term.write('\r\nPS C:\\Workspaces\\Stehouwer_Server\\Projects> ');

    term.onData(async (data) => {
      if (data === '\r') {
        // Execute command
        term.write('\r\n');
        const cmd = commandRef.current.trim();
        commandRef.current = '';
        
        if (cmd) {
          try {
            const res = await fetch(`${backendUrl}/api/terminal/run`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ command: cmd })
            });
            const result = await res.json();
            
            if (result.stdout) {
              const lines = result.stdout.split('\n');
              lines.forEach(l => term.writeln(l.replace(/\r/g, '')));
            }
            if (result.stderr) {
              const lines = result.stderr.split('\n');
              lines.forEach(l => term.writeln(`\x1b[1;31m${l.replace(/\r/g, '')}\x1b[0m`));
            }
          } catch (e) {
            term.writeln(`\x1b[1;31mError: ${e.message}\x1b[0m`);
          }
        }
        term.write('PS C:\\Workspaces\\Stehouwer_Server\\Projects> ');
      } else if (data === '\x7f') { // Backspace
        if (commandRef.current.length > 0) {
          commandRef.current = commandRef.current.slice(0, -1);
          term.write('\b \b');
        }
      } else {
        commandRef.current += data;
        term.write(data);
      }
    });

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    const handleResize = () => {
      safeFit();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      try {
        term.dispose();
      } catch (e) {
        // Suppress disposal errors
      }
    };
  }, [backendUrl]);

  return (
    <div style={{ flex: 1, height: '100%', width: '100%', overflow: 'hidden', borderTop: '1px solid var(--border-glow)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ background: '#111', padding: '4px 8px', fontSize: '12px', color: '#888', borderBottom: '1px solid #333' }}>
        TERMINAL
      </div>
      <div ref={terminalRef} style={{ flex: 1, width: '100%', padding: '8px', background: '#0a0a0a' }} />
    </div>
  );
}
```

### TerminalPanelWrapper.jsx
```jsx
import React from 'react';
import TerminalPanel from './TerminalPanel';
import { useAppStore } from './useAppStore';

export default function TerminalPanelWrapper() {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  return (
    <div className="powershell-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <h3 style={{ margin: 0, color: '#fff' }}>Windows Administrative PowerShell</h3>
        <p style={{ margin: '4px 0 0 0', color: '#888', fontSize: '0.85rem' }}>
          Execute raw PowerShell and system commands directly against your backend infrastructure.
        </p>
      </div>
      <TerminalPanel backendUrl={BACKEND_URL} />
    </div>
  );
}
```

### LoginModal.jsx
```jsx
import React, { useState } from 'react';
import { signInWithPopup, signInWithRedirect } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

const AUTHORIZED_EMAILS = [
  'theseandaley@gmail.com',
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'brettstehouwer@gmail.com',
  'footballstar0325@gmail.com',
  'rottierannajoy@gmail.com'
];

export default function LoginModal({ onLoginSuccess }) {
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleGoogleSignIn = async () => {
    setErrorMsg('');
    setIsSubmitting(true);

    try {
      const result = await signInWithPopup(auth, googleProvider);
      const user = result.user;

      if (AUTHORIZED_EMAILS.includes(user.email.toLowerCase())) {
        onLoginSuccess(user);
      } else {
        setErrorMsg(`Unauthorized Email (${user.email}). Access restricted.`);
        await auth.signOut();
      }
    } catch (err) {
      console.warn('Popup login failed or blocked, attempting mobile redirect...', err);
      if (err.code === 'auth/popup-blocked' || err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
        try {
          await signInWithRedirect(auth, googleProvider);
          return;
        } catch (redirectErr) {
          setErrorMsg('Mobile sign-in failed: ' + redirectErr.message);
        }
      } else {
        setErrorMsg('Authentication failed: ' + err.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRedirectSignIn = async () => {
    setErrorMsg('');
    setIsSubmitting(true);
    try {
      await signInWithRedirect(auth, googleProvider);
    } catch (err) {
      setErrorMsg('Redirect sign-in failed: ' + err.message);
      setIsSubmitting(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal} className="glass-panel">
        <h2 style={{ color: '#fff', marginBottom: '10px' }}>Security Perimeter</h2>
        <p style={{ color: '#94a3b8', marginBottom: '30px', fontSize: '0.9rem' }}>
          This dashboard is locked. Authorized personnel only.
        </p>
        
        <button onClick={handleGoogleSignIn} style={styles.button} disabled={isSubmitting}>
          {isSubmitting ? 'Verifying...' : 'Sign in with Google'}
        </button>
        
        {errorMsg && <p style={styles.error}>{errorMsg}</p>}
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 9999,
  },
  modal: {
    padding: '40px',
    borderRadius: '16px',
    width: '350px',
    textAlign: 'center',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(15, 23, 42, 0.95)',
    boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
    backdropFilter: 'blur(16px)',
  },
  button: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    backgroundColor: '#fff',
    color: '#000',
    fontWeight: 'bold',
    cursor: 'pointer',
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    fontSize: '1rem',
    transition: 'all 0.2s',
  },
  error: {
    marginTop: '20px',
    color: '#ff4444',
    fontSize: '0.9rem',
    background: 'rgba(255, 0, 0, 0.1)',
    padding: '10px',
    borderRadius: '8px',
  }
};
```

### useBackendHealth.js
```js
import { useState, useEffect } from 'react';
import { getApiBase, setApiBase } from '../config/api.js';

export function useBackendHealth(intervalMs = 10000) {
  const [backendUrl, setBackendUrl] = useState(getApiBase());
  const [backendStatus, setBackendStatus] = useState('checking'); // checking | online | offline

  useEffect(() => {
    const isLocal = typeof window !== 'undefined' && (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1' ||
      window.location.protocol === 'file:'
    );

    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';

    const checkBackend = async () => {
      // 1. Try Localhost FastAPI Backend (for local dev or HTTP environments)
      if (!isHttps || isLocal) {
        for (const path of ['/v1/health', '/api/health', '/health']) {
          try {
            const localRes = await fetch(`http://127.0.0.1:8000${path}`, { signal: AbortSignal.timeout(1500) });
            if (localRes.ok) {
              setApiBase('http://127.0.0.1:8000');
              setBackendUrl('http://127.0.0.1:8000');
              setBackendStatus('online');
              return;
            }
          } catch (e) {
            // Localhost unavailable
          }
        }
      }

      if (isLocal) {
        setApiBase('http://127.0.0.1:8000');
        setBackendUrl('http://127.0.0.1:8000');
        setBackendStatus('online');
        return;
      }

      // 1.5. Try Hostname IP (Tailscale/LAN)
      const hn = typeof window !== 'undefined' ? window.location.hostname : '';
      const isIp = /^\d+\.\d+\.\d+\.\d+$/.test(hn) && hn !== '127.0.0.1';
      
      if (!isHttps && isIp) {
        for (const path of ['/v1/health', '/api/health', '/health']) {
          try {
            const ipRes = await fetch(`http://${hn}:8000${path}`, { signal: AbortSignal.timeout(1500) });
            if (ipRes.ok) {
              setApiBase(`http://${hn}:8000`);
              setBackendUrl(`http://${hn}:8000`);
              setBackendStatus('online');
              return;
            }
          } catch (e) {
            // IP unavailable
          }
        }
      }

      // 2. Try Remote Production Domains over HTTPS
      const candidateDomains = [
        'https://ai-bs.brettstehouwer.live',
        'https://api.brettstehouwer.live'
      ];

      for (const domain of candidateDomains) {
        try {
          const res = await fetch(`${domain}/api/health`, { signal: AbortSignal.timeout(2500) });
          if (res.ok) {
            setApiBase(domain);
            setBackendUrl(domain);
            setBackendStatus('online');
            return;
          }
        } catch (e) {
          // Fallback domain
        }
      }

      // 3. Fallback to configured API base
      setBackendStatus('online');
    };
    
    checkBackend();
    const interval = setInterval(checkBackend, intervalMs);
    return () => clearInterval(interval);
  }, [intervalMs]);

  return { backendUrl, backendStatus };
}
```

### useSHMTelemetry.js
```js
import { useState, useEffect, useRef } from 'react';

export function useSHMTelemetry() {
  const [isConnected, setIsConnected] = useState(false);
  const [heartbeatActive, setHeartbeatActive] = useState(true);
  const [lastHealedEvent, setLastHealedEvent] = useState(null);
  const [astEvents, setAstEvents] = useState([]);
  const [tensorEvents, setTensorEvents] = useState([]);
  const [gpuStats, setGpuStats] = useState({
    model: 'SDXL_Turbo',
    step: 18,
    total_steps: 30,
    vram_used_mb: 18432,
    vram_total_mb: 24576,
    fps: 24.5
  });

  const [telemetryData, setTelemetryData] = useState({
    status: 'OFFLINE',
    head: 0,
    tail: 0,
    total_pushed: 0,
    total_popped: 0,
    topics: {
      '0x0001': { name: 'TOPIC_PREDICTIVE_TENSORS', latency_us: 2.61, status: 'OK' },
      '0x0002': { name: 'TOPIC_VNC_FRAME_METRICS', latency_us: 4.36, status: 'OK' },
      '0x0003': { name: 'TOPIC_HEURISTICS_TELEMETRY', latency_us: 5.06, status: 'OK' },
      '0x0004': { name: 'TOPIC_SYSTEM_STATE_HEARTBEAT', latency_us: 1.00, status: 'OK' },
      '0x0005': { name: 'TOPIC_ZERO_COPY_VECTOR_TENSORS', latency_us: 1.80, status: 'OK' },
      '0x0006': { name: 'TOPIC_COMFYUI_GPU_RENDER', latency_us: 3.20, status: 'OK' }
    }
  });

  const wsRef = useRef(null);

  useEffect(() => {
    let wsUrl = import.meta.env?.VITE_WS_URL;
    if (!wsUrl) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      if (backendUrl) {
        wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/shm_telemetry';
      } else if (typeof window !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        if (import.meta.env?.DEV) {
          wsUrl = `${protocol}//${window.location.host}/ws/shm_telemetry`;
        } else {
          wsUrl = 'ws://localhost:8010/ws/shm_telemetry';
        }
      } else {
        wsUrl = 'ws://localhost:8010/ws/shm_telemetry';
      }
    }

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          setHeartbeatActive(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setTelemetryData(data);
            setIsConnected(true);
            setHeartbeatActive(true);

            if (data.ast_event) {
              setAstEvents((prev) => [data.ast_event, ...prev.slice(0, 19)]);
            }
            if (data.tensor_event) {
              setTensorEvents((prev) => [data.tensor_event, ...prev.slice(0, 19)]);
            }
            if (data.gpu_stats) {
              setGpuStats(data.gpu_stats);
            }
          } catch (e) {
            console.error('Failed to parse SHM telemetry frame', e);
          }
        };

        ws.onerror = () => setIsConnected(false);
        ws.onclose = () => {
          setIsConnected(false);
          setTimeout(connectWebSocket, 3000);
        };
      } catch (err) {
        setIsConnected(false);
        setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return {
    isConnected,
    heartbeatActive,
    lastHealedEvent,
    astEvents,
    tensorEvents,
    gpuStats,
    telemetryData
  };
}
```

### ArtifactRenderer.jsx
```jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const ArtifactRenderer = ({ content }) => {
  return (
    <div className="artifact-markdown-container">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            return !inline && match ? (
              <div className="code-block-wrapper">
                <div className="code-block-header">
                  <span>{match[1]}</span>
                </div>
                <SyntaxHighlighter
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  className="syntax-highlighter-block"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code className={`inline-code ${className || ''}`} {...props}>
                {children}
              </code>
            );
          },
          blockquote({ node, children, ...props }) {
            // Check for GitHub style alerts inside blockquotes
            // e.g. > [!NOTE], > [!IMPORTANT], > [!WARNING]
            const textContent = node.children
              .filter(child => child.type === 'element' && child.tagName === 'p')
              .map(p => p.children.filter(c => c.type === 'text').map(t => t.value).join(''))
              .join('\n');

            let alertType = null;
            if (textContent.includes('[!NOTE]')) alertType = 'note';
            else if (textContent.includes('[!TIP]')) alertType = 'tip';
            else if (textContent.includes('[!IMPORTANT]')) alertType = 'important';
            else if (textContent.includes('[!WARNING]')) alertType = 'warning';
            else if (textContent.includes('[!CAUTION]')) alertType = 'caution';

            if (alertType) {
              // We need to strip the [!TYPE] from the children rendering
              // This is a simplified approach: just add the class, we'll let CSS hide the tag
              // or we can clean the children. For simplicity, we just add the alert class
              return (
                <blockquote className={`github-alert github-alert-${alertType}`} {...props}>
                  <div className="alert-title">{alertType.toUpperCase()}</div>
                  <div className="alert-content">{children}</div>
                </blockquote>
              );
            }

            return <blockquote {...props}>{children}</blockquote>;
          },
          table({ node, children, ...props }) {
            return (
              <div className="markdown-table-wrapper">
                <table {...props}>{children}</table>
              </div>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default ArtifactRenderer;
```

### WebGLRenderBridge.jsx
```jsx
import React, { useEffect, useRef } from 'react';

export default function WebGLRenderBridge() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let angle = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#0d1117';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Render animated neon cyber ring
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = 45;

      ctx.save();
      ctx.translate(centerX, centerY);
      ctx.rotate(angle);

      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 1.5);
      ctx.lineWidth = 4;
      ctx.strokeStyle = '#00d2ff';
      ctx.shadowColor = '#00d2ff';
      ctx.shadowBlur = 12;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, radius - 12, Math.PI * 0.5, Math.PI * 2);
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#e040fb';
      ctx.shadowColor = '#e040fb';
      ctx.shadowBlur = 10;
      ctx.stroke();

      ctx.restore();

      ctx.fillStyle = '#7ee787';
      ctx.font = '11px Consolas, monospace';
      ctx.fillText('⚡ 3D WebGL / Canvas Bridge: 60 FPS', 12, canvas.height - 12);

      angle += 0.04;
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div style={{
      backgroundColor: '#07090e',
      border: '1px solid #161f30',
      borderRadius: '8px',
      padding: '12px',
      marginTop: '12px'
    }}>
      <div style={{ fontSize: '12px', fontWeight: 600, color: '#00d2ff', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
        <span>🎮 Live WebGL 3D & Canvas Render Bridge</span>
        <span style={{ color: '#22c55e', fontSize: '11px' }}>● 60 FPS Render Loop</span>
      </div>
      <canvas ref={canvasRef} width={420} height={140} style={{ width: '100%', height: '140px', borderRadius: '6px' }} />
    </div>
  );
}
```

### VLCPreviewMonitor.jsx
```jsx
import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';

/**
 * VLCPreviewMonitor
 * Connects to the backend VLC streaming daemon to play HLS streams.
 */
const VLCPreviewMonitor = ({ streamUrl }) => {
    const videoRef = useRef(null);
    const [status, setStatus] = useState("Waiting for stream...");

    useEffect(() => {
        if (!streamUrl) return;

        setStatus("Initializing HLS...");
        let hls;

        if (Hls.isSupported()) {
            hls = new Hls({
                // Lower latency settings for live preview
                maxLiveSyncPlaybackRate: 1.5,
            });
            hls.loadSource(streamUrl);
            hls.attachMedia(videoRef.current);

            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                setStatus("Playing");
                videoRef.current.play().catch(e => console.warn("Autoplay blocked:", e));
            });

            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    switch (data.type) {
                        case Hls.ErrorTypes.NETWORK_ERROR:
                            setStatus("Network error, retrying...");
                            hls.startLoad();
                            break;
                        case Hls.ErrorTypes.MEDIA_ERROR:
                            setStatus("Media error, recovering...");
                            hls.recoverMediaError();
                            break;
                        default:
                            setStatus("Fatal HLS error.");
                            hls.destroy();
                            break;
                    }
                }
            });
        } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
            // Safari native support
            videoRef.current.src = streamUrl;
            videoRef.current.addEventListener('loadedmetadata', () => {
                setStatus("Playing");
                videoRef.current.play();
            });
        }

        return () => {
            if (hls) hls.destroy();
        };
    }, [streamUrl]);

    return (
        <div className="vlc-monitor-container" style={{ position: 'relative', width: '100%', maxWidth: '800px', backgroundColor: '#000', borderRadius: '8px', overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
            
            {/* Status Overlay */}
            {status !== "Playing" && (
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10, backgroundColor: 'rgba(0,0,0,0.7)', color: '#fff', fontFamily: 'monospace' }}>
                    <p>{status}</p>
                </div>
            )}
            
            {/* The Video Element */}
            <video 
                ref={videoRef} 
                controls 
                style={{ width: '100%', height: 'auto', display: 'block' }} 
            />
        </div>
    );
};

export default VLCPreviewMonitor;
```

---

## 2. Chat, Agents, Reasoning & Interaction

### ChatToolControlBar.jsx
```jsx
import React, { useState } from 'react';

export default function ChatToolControlBar({ onToolToggle }) {
  const [tools, setTools] = useState({
    plan_and_review: false,
    search_local_files: true,
    polyglot_runner: true,
    vector_vault: true,
    ast_shredder: true,
    auto_healer: true
  });

  const toggleTool = (name) => {
    const next = { ...tools, [name]: !tools[name] };
    setTools(next);
    if (onToolToggle) onToolToggle(next);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      backgroundColor: '#161b22',
      border: '1px solid #30363d',
      borderRadius: '6px',
      padding: '6px 12px',
      margin: '8px 0',
      fontSize: '11px',
      color: '#8b949e'
    }}>
      <span style={{ fontWeight: 600, color: '#58a6ff' }}>🛠️ Active Agent Tools:</span>
      {Object.entries(tools).map(([key, enabled]) => (
        <button
          key={key}
          type="button"
          onClick={() => toggleTool(key)}
          style={{
            backgroundColor: enabled ? 'rgba(56, 189, 248, 0.15)' : '#0d1117',
            color: enabled ? '#38bdf8' : '#484f58',
            border: `1px solid ${enabled ? '#38bdf8' : '#30363d'}`,
            borderRadius: '12px',
            padding: '2px 8px',
            fontSize: '10px',
            cursor: 'pointer',
            fontWeight: enabled ? 600 : 400
          }}
        >
          {enabled ? '●' : '○'} {key === 'plan_and_review' ? '📋 Mode: Plan & Review' : key.replace('_', ' ')}
        </button>
      ))}
    </div>
  );
}
```

### ChatContextToolbar.jsx
```jsx
import React from 'react';
import './ChatContextToolbar.css';

export default function ChatContextToolbar({ activeContexts, onToggleContext }) {
  return (
    <div className="chat-context-toolbar">
      <button 
        type="button"
        className={`context-btn ${activeContexts.file ? 'active' : ''}`}
        onClick={() => onToggleContext('file')}
        title="@file Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
      </button>

      <button 
        type="button"
        className={`context-btn ${activeContexts.terminal ? 'active' : ''}`}
        onClick={() => onToggleContext('terminal')}
        title="@terminal Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
      </button>

      <button 
        type="button"
        className={`context-btn ${activeContexts.codebase ? 'active' : ''}`}
        onClick={() => onToggleContext('codebase')}
        title="@codebase Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
      </button>

      <button 
        type="button"
        className={`context-btn ${activeContexts.web ? 'active' : ''}`}
        onClick={() => onToggleContext('web')}
        title="@web Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
      </button>
    </div>
  );
}
```

### ChatContextToolbar.css
```css
.chat-context-toolbar {
  display: flex;
  gap: 8px;
  padding: 4px;
  background: #0d1117;
  border-top: 1px solid #30363d;
}

.context-btn {
  background: transparent;
  border: 1px solid #30363d;
  color: #8b949e;
  border-radius: 4px;
  padding: 4px;
  cursor: pointer;
  display: 'flex';
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.context-btn:hover {
  background: #161b22;
  color: #c9d1d9;
}

.context-btn.active {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border-color: #38bdf8;
}

.context-icon {
  width: 16px;
  height: 16px;
}
```

### AgentPlanReviewCard.jsx
```jsx
import React, { useState } from 'react';
import './AgentPlanReviewCard.css';

export default function AgentPlanReviewCard({ planData, onExecutePlan, onRequestRevisions }) {
  if (!planData) return null;

  const [approvedSteps, setApprovedSteps] = useState(planData.steps ? planData.steps.map(s => s.step_num) : []);

  const toggleStep = (stepNum) => {
    if (approvedSteps.includes(stepNum)) {
      setApprovedSteps(approvedSteps.filter(s => s.step_num !== stepNum));
    } else {
      setApprovedSteps([...approvedSteps, stepNum]);
    }
  };

  const handleExecute = () => {
    onExecutePlan(planData.plan_id, approvedSteps);
  };

  return (
    <div className="agent-plan-review-card">
      <div className="plan-header">
        <h3 className="plan-title">📜 {planData.title || "Implementation Plan"}</h3>
        <p className="plan-summary">{planData.summary}</p>
      </div>

      <div className="plan-files">
        <h4>📁 Affected Files</h4>
        <div className="file-pills">
          {planData.affected_files && planData.affected_files.map((file, idx) => (
            <span key={idx} className="file-pill">{file}</span>
          ))}
        </div>
      </div>

      <div className="plan-steps">
        <h4>🔢 Execution Steps</h4>
        <ul className="step-list">
          {planData.steps && planData.steps.map((step, idx) => (
            <li key={idx} className={`step-item ${approvedSteps.includes(step.step_num) ? 'approved' : 'rejected'}`}>
              <label>
                <input 
                  type="checkbox" 
                  checked={approvedSteps.includes(step.step_num)} 
                  onChange={() => toggleStep(step.step_num)}
                />
                <span className="step-desc"><strong>Step {step.step_num}:</strong> {step.description}</span>
                <span className={`step-risk risk-${step.risk?.toLowerCase() || 'unknown'}`}>{step.risk?.toUpperCase()}</span>
              </label>
            </li>
          ))}
        </ul>
      </div>

      <div className="plan-actions">
        <button className="btn-revise" onClick={onRequestRevisions}>
          ✏️ Request Revisions
        </button>
        <button className="btn-execute" onClick={handleExecute} disabled={approvedSteps.length === 0}>
          🚀 Accept & Execute Plan
        </button>
      </div>
    </div>
  );
}
```

### AgentPlanReviewCard.css
```css
.agent-plan-review-card {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 12px;
  margin: 8px 0;
  color: #c9d1d9;
  font-size: 13px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}

.plan-header {
  margin-bottom: 12px;
}

.plan-title {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #58a6ff;
}

.plan-summary {
  margin: 0;
  color: #8b949e;
}

.plan-files {
  margin-bottom: 12px;
}

.plan-files h4, .plan-steps h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.file-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.file-pill {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 11px;
  font-family: monospace;
}

.step-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.step-item {
  display: flex;
  align-items: flex-start;
  padding: 6px 0;
  border-bottom: 1px solid #21262d;
}

.step-item:last-child {
  border-bottom: none;
}

.step-item label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  width: 100%;
}

.step-item input[type="checkbox"] {
  margin-top: 2px;
}

.step-desc {
  flex-grow: 1;
}

.step-risk {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 12px;
  font-weight: bold;
}

.risk-low { background: rgba(46, 160, 67, 0.15); color: #3fb950; }
.risk-medium { background: rgba(210, 153, 34, 0.15); color: #d29922; }
.risk-high { background: rgba(248, 81, 73, 0.15); color: #f85149; }
.risk-unknown { background: rgba(139, 148, 158, 0.15); color: #8b949e; }

.plan-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  justify-content: flex-end;
}

.btn-revise, .btn-execute {
  background: #21262d;
  border: 1px solid #30363d;
  color: #c9d1d9;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-revise:hover { background: #30363d; }
.btn-execute { background: #238636; border-color: rgba(240, 246, 252, 0.1); color: #ffffff; }
.btn-execute:hover { background: #2ea043; }
.btn-execute:disabled { background: #161b22; color: #484f58; cursor: not-allowed; border-color: #30363d; }
```

---

## 3. Creative Studios, Theatrical & Media Tools

### TheatricalStageSwitch.jsx
```jsx
import React, { useState } from 'react';
import './TheatricalStageSwitch.css'; // Assuming we might add specific styles

const TheatricalStageSwitch = () => {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

    const [isActive, setIsActive] = useState(false);
    const [statusMessage, setStatusMessage] = useState("System in Standard Swarm Mode (Monetization Active)");

    const toggleMode = async () => {
        const newState = !isActive;
        setIsActive(newState);
        
        try {
            const response = await fetch(`${backendUrl}/api/proxy/8001/theatrical/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ active: newState })
            });
            
            const data = await response.json();
            if (data.status === "success") {
                if (data.theatrical_mode_active) {
                    setStatusMessage("THEATRICAL WORLD MODE ACTIVE. Monetization Paused. GPU allocated to ComfyUI & Isolated Module.");
                } else {
                    setStatusMessage("System in Standard Swarm Mode (Monetization Active)");
                }
            } else {
                setStatusMessage("Error: Failed to toggle state in backend.");
                setIsActive(!newState); // Revert UI
            }
        } catch (error) {
            console.error("Failed to hit toggle endpoint:", error);
            setStatusMessage("Error: Network disconnected.");
            setIsActive(!newState); // Revert UI
        }
    };

    return (
        <div className={`stage-switch-container ${isActive ? 'active' : 'inactive'}`}>
            <h2>Theatrical World Engine</h2>
            <p className="status-message">{statusMessage}</p>
            
            <button 
                className={`giant-toggle-btn ${isActive ? 'btn-danger' : 'btn-primary'}`}
                onClick={toggleMode}
                style={{
                    padding: '2rem 4rem',
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    borderRadius: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    boxShadow: isActive ? '0 0 30px rgba(255,0,0,0.6)' : '0 0 15px rgba(0,123,255,0.4)',
                    backgroundColor: isActive ? '#dc3545' : '#0d6efd',
                    color: 'white',
                    border: 'none'
                }}
            >
                {isActive ? "EXIT STAGE (Resume Monetization)" : "ENTER STAGE (Trigger Theatrical World)"}
            </button>
            
            {isActive && (
                <div className="active-modules-list" style={{ marginTop: '2rem', textAlign: 'left' }}>
                    <h3 style={{ color: '#ff4d4d' }}>Active Isolation Protocols:</h3>
                    <ul>
                        <li>VRAM Lock: Clore/Vast processes terminated.</li>
                        <li>ChromaDB Local Vector Search: Online.</li>
                        <li>ComfyUI Visual Streamer: Ready.</li>
                        <li>Teleprompter WebSocket: Listening.</li>
                    </ul>
                </div>
            )}
        </div>
    );
};

export default TheatricalStageSwitch;
```

### TheatricalStageSwitch.css
```css
/* TheatricalStageSwitch.css */
```

### TheatricalMicClient.jsx
```jsx
import React, { useState, useRef } from 'react';

const TheatricalMicClient = ({ backendUrl: propBackendUrl }) => {
    const backendUrl = propBackendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
    const wsBase = backendUrl.replace(/^http/, 'ws');
    
    const [isRecording, setIsRecording] = useState(false);
    const [status, setStatus] = useState("Microphone disconnected.");
    const mediaRecorderRef = useRef(null);
    const wsRef = useRef(null);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setStatus("Microphone connected. Connecting to Stage...");
            
            wsRef.current = new WebSocket(`${wsBase}/api/proxy/8001/theatrical/audio_stream`);
            
            wsRef.current.onopen = () => {
                setStatus("Live on Stage! Streaming audio to Theatrical Module...");
                setIsRecording(true);
                
                mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                
                mediaRecorderRef.current.ondataavailable = (event) => {
                    if (event.data.size > 0 && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.send(event.data);
                    }
                };
                
                // Send chunks every 1 second for near real-time processing
                mediaRecorderRef.current.start(1000);
            };

            wsRef.current.onclose = () => {
                setStatus("Disconnected from Stage.");
                setIsRecording(false);
            };
            
            wsRef.current.onerror = (err) => {
                console.error("WebSocket Error:", err);
                setStatus("Error: WebSocket disconnected.");
            };

        } catch (err) {
            console.error("Mic access denied:", err);
            setStatus("Error: Microphone access denied or not found.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
        if (wsRef.current) {
            wsRef.current.close();
        }
        setIsRecording(false);
        setStatus("Microphone disconnected.");
    };

    return (
        <div style={{ padding: '2rem', border: '2px solid #555', borderRadius: '8px', backgroundColor: '#111', color: '#eee' }}>
            <h3>Stage Microphone Client</h3>
            <p>Status: <span style={{ color: isRecording ? '#00ff00' : '#ff3333' }}>{status}</span></p>
            
            {!isRecording ? (
                <button 
                    onClick={startRecording}
                    style={{ padding: '1rem 2rem', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    Connect & Go Live
                </button>
            ) : (
                <button 
                    onClick={stopRecording}
                    style={{ padding: '1rem 2rem', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                    Cut Mic
                </button>
            )}
        </div>
    );
};

export default TheatricalMicClient;
```

### TheatricalTeleprompter.jsx
```jsx
import React, { useState, useEffect, useRef } from 'react';

const TheatricalTeleprompter = () => {
    const [scriptLines, setScriptLines] = useState([
        "Welcome to the Theatrical World Mode.",
        "Awaiting input from the Stage Mic...",
    ]);
    const scrollRef = useRef(null);

    useEffect(() => {
        // In a full implementation, this would connect to the websocket 
        // to receive lines dynamically generated by the TheatricalDirectorDaemon.
        
        // Auto-scroll to bottom as new lines appear
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [scriptLines]);

    return (
        <div style={{
            height: '100vh',
            width: '100%',
            backgroundColor: 'black',
            color: 'white',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            overflow: 'hidden',
            padding: '2rem'
        }}>
            <h1 style={{ color: '#ff3333', letterSpacing: '0.5rem', textTransform: 'uppercase', marginBottom: '2rem' }}>
                LIVE TELEPROMPTER
            </h1>
            
            <div 
                ref={scrollRef}
                style={{
                    width: '80%',
                    height: '80%',
                    overflowY: 'auto',
                    fontSize: '4rem', // Massive font for stage reading
                    lineHeight: '1.5',
                    textAlign: 'center',
                    fontFamily: 'Courier New, Courier, monospace',
                    textShadow: '0 0 10px rgba(255, 255, 255, 0.5)'
                }}
            >
                {scriptLines.map((line, idx) => (
                    <p key={idx} style={{ 
                        opacity: idx === scriptLines.length - 1 ? 1 : 0.4, // Focus on current line
                        transition: 'opacity 0.5s ease-in-out'
                    }}>
                        {line}
                    </p>
                ))}
            </div>
        </div>
    );
};

export default TheatricalTeleprompter;
```

### TheatricalProjector.jsx
```jsx
import React, { useState, useEffect } from 'react';

const TheatricalProjector = () => {
    const [currentImage, setCurrentImage] = useState(null);

    useEffect(() => {
        // In a full implementation, this connects to a WebSocket that broadcasts
        // Base64 images directly from the ComfyUI generation pipeline.
        
        // Mock connection simulation
        console.log("Theatrical Projector active. Awaiting ComfyUI stream...");
    }, []);

    return (
        <div style={{
            height: '100vh',
            width: '100%',
            backgroundColor: 'black',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            overflow: 'hidden'
        }}>
            {currentImage ? (
                <img 
                    src={`data:image/png;base64,${currentImage}`} 
                    alt="Stage Projection" 
                    style={{
                        minWidth: '100%',
                        minHeight: '100%',
                        objectFit: 'cover',
                        opacity: 1,
                        transition: 'opacity 2s ease-in-out' // Smooth fade between scenes
                    }}
                />
            ) : (
                <div style={{ color: '#333', fontSize: '2rem', fontFamily: 'sans-serif' }}>
                    [ AWAITING STAGE PROJECTION STREAM ]
                </div>
            )}
        </div>
    );
};

export default TheatricalProjector;
```

### NoCoVisionTab.jsx
```jsx
import React from 'react';
import TheatricalStageSwitch from './TheatricalStageSwitch.jsx';
import TheatricalMicClient from './TheatricalMicClient.jsx';
import { useAppStore } from './useAppStore.js';

const NoCoVisionTab = () => {
  return (
    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div style={{ border: '1px solid #444', padding: '20px', borderRadius: '8px', background: '#161b22' }}>
        <h3 style={{ marginTop: 0 }}>Core Control</h3>
        <TheatricalStageSwitch />
      </div>

      <div style={{ border: '1px solid #444', padding: '20px', borderRadius: '8px', background: '#161b22' }}>
        <h3 style={{ marginTop: 0 }}>Audio Ingestion</h3>
        <TheatricalMicClient />
      </div>

      <div style={{ border: '1px solid #444', padding: '20px', borderRadius: '8px', background: '#161b22' }}>
        <h3 style={{ marginTop: 0 }}>Stage Displays</h3>
        <p>To view the stage displays, open these routes in a new window or on your secondary stage monitors:</p>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li>
            <button 
                onClick={() => window.open('/nocovision/teleprompter', '_blank')}
                style={{ padding: '10px 20px', background: '#0d6efd', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', marginBottom: '10px' }}>
              Launch Fullscreen Teleprompter
            </button>
          </li>
          <li>
            <button 
                onClick={() => window.open('/nocovision/projector', '_blank')}
                style={{ padding: '10px 20px', background: '#6f42c1', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Launch Fullscreen Visual Projector
            </button>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default NoCoVisionTab;
```

### ComfyUIRenderWidget.jsx
```jsx
import React from 'react';
import { useSHMTelemetry } from './useSHMTelemetry';

export default function ComfyUIRenderWidget() {
  const { gpuStats } = useSHMTelemetry();

  const vramPercent = Math.round((gpuStats.vram_used_mb / gpuStats.vram_total_mb) * 100);
  const stepPercent = Math.round((gpuStats.step / gpuStats.total_steps) * 100);

  return (
    <div style={{
      backgroundColor: '#0d1117',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '16px',
      color: '#f0f6fc',
      marginTop: '12px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, color: '#a855f7', fontSize: '14px' }}>
          🎨 ComfyUI Render Telemetry & RTX 4090 VRAM (Topic 0x0006)
        </h4>
        <span style={{ fontSize: '12px', color: '#7ee787', fontWeight: 600 }}>
          {gpuStats.fps} FPS
        </span>
      </div>

      {/* Model & Step Progress */}
      <div style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>
          <span>Active Model: <strong>{gpuStats.model}</strong></span>
          <span>Step: {gpuStats.step} / {gpuStats.total_steps} ({stepPercent}%)</span>
        </div>
        <div style={{ background: '#21262d', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
          <div style={{ background: 'linear-gradient(90deg, #a855f7, #38bdf8)', height: '100%', width: `${stepPercent}%` }}></div>
        </div>
      </div>

      {/* VRAM Utilization */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>
          <span>RTX 4090 VRAM Allocation</span>
          <span>{gpuStats.vram_used_mb.toLocaleString()} MB / {gpuStats.vram_total_mb.toLocaleString()} MB ({vramPercent}%)</span>
        </div>
        <div style={{ background: '#21262d', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
          <div style={{ background: vramPercent > 85 ? '#f97316' : '#22c55e', height: '100%', width: `${vramPercent}%` }}></div>
        </div>
      </div>
    </div>
  );
}
```

### ScreenwritingTab.css
```css
.screenwriting-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0d1017;
  color: #e2e8f0;
  font-family: sans-serif;
}

/* 1. Main Menu Bar */
.sw-menu-bar {
  display: flex;
  gap: 16px;
  padding: 4px 16px;
  background: #090a0f;
  border-bottom: 1px solid #1f2937;
  font-size: 0.85rem;
  color: #9ca3af;
}

.sw-menu-item {
  cursor: pointer;
}

/* 2. The Ribbon */
.sw-ribbon {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: #111827;
  border-bottom: 1px solid #1f2937;
  align-items: center;
  overflow-x: auto;
  flex-shrink: 0;
}

.sw-ribbon-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  border-right: 1px solid #374151;
  padding-right: 16px;
  padding-left: 8px;
  flex-shrink: 0;
}

.sw-ribbon-btn {
  background: transparent;
  border: none;
  color: #e5e7eb;
  font-size: 0.8rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  flex-shrink: 0;
  white-space: nowrap;
}

.sw-ribbon-btn-blue {
  background: #0284c7;
  color: white;
  font-weight: bold;
}

.sw-ribbon-btn-red {
  background: #dc2626;
  color: white;
  font-weight: bold;
}

.sw-ribbon-btn-active {
  background: #374151;
}

.sw-ribbon-label {
  font-size: 0.65rem;
  color: #6b7280;
  margin-top: 4px;
  text-transform: uppercase;
  text-align: center;
}

.sw-ribbon-select {
  background: #1f2937;
  color: #fff;
  border: 1px solid #374151;
  padding: 4px;
  border-radius: 4px;
  font-size: 0.8rem;
  outline: none;
  width: 120px;
}

.sw-save-btn {
  background: #4ade80;
  color: #000;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: bold;
  border: none;
  cursor: pointer;
  white-space: nowrap;
}

/* 3. Main Workspace */
.sw-workspace {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sw-left-panel {
  width: 250px;
  background: #0d1017;
  border-right: 1px solid #1f2937;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow-y: auto;
}

.sw-panel-header {
  margin: 0 0 8px 0;
  font-size: 0.8rem;
  text-transform: uppercase;
}

.sw-panel-input {
  background: #000;
  border: 1px solid #1f2937;
  color: #fff;
  padding: 4px;
  font-size: 0.8rem;
}

.sw-sprint-active {
  background: rgba(168,139,250,0.1);
  border: 1px solid #a78bfa;
  padding: 8px;
  margin-bottom: 16px;
}

.sw-scene-list {
  font-size: 0.8rem;
  color: #d1d5db;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sw-scene-item {
  padding-left: 8px;
  border-left: 2px solid #374151;
  cursor: pointer;
}

/* 4. Central Area & Beat Board */
.sw-central-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sw-editor-container {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sw-preview-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
  position: relative;
}

.sw-beat-board {
  display: flex;
  min-width: min-content;
  position: relative;
  align-items: center;
  padding: 40px 20px;
}

.sw-beat-timeline {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.2), rgba(244, 63, 94, 0.2));
  z-index: 0;
  border-radius: 2px;
}

.sw-beat-card {
  position: relative;
  z-index: 1;
  border-radius: 12px;
  box-sizing: border-box;
  cursor: grab;
  display: flex;
  flex-direction: column;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(8px);
}

.sw-beat-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 8px 24px rgba(56, 189, 248, 0.2);
  border-color: rgba(56, 189, 248, 0.8) !important;
}

.sw-beat-index {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  color: #fff;
  background: #38bdf8;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: bold;
  z-index: 2;
  box-shadow: 0 0 10px rgba(56,189,248,0.5);
}

.sw-beat-heading {
  color: #e2e8f0;
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}

.sw-beat-page {
  margin-top: auto;
  color: #94a3b8;
  font-weight: 600;
}

/* 5. Bottom Panel */
.sw-bottom-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 16px;
  background: #090a0f;
  border-top: 1px solid #1f2937;
  font-size: 0.75rem;
  color: #9ca3af;
  flex-shrink: 0;
}
```

### VisualScriptingTab.css
```css
.vs-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0d1017;
  color: #e2e8f0;
  font-family: sans-serif;
}

/* Toolbar */
.vs-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  padding: 12px 24px;
  background: rgba(13, 16, 23, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.vs-toolbar-group {
  display: flex;
  gap: 8px;
  margin-right: 20px;
}

.vs-toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: 16px;
  align-items: center;
}

.vs-select {
  padding: 8px 12px;
  color: #fff;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  font-size: 0.85rem;
  outline: none;
}

.vs-select-nodejs {
  background: rgba(59, 130, 246, 0.2);
}

.vs-select-webgl {
  background: rgba(168, 85, 247, 0.2);
}

/* Canvas */
.vs-canvas {
  flex: 1;
  background: #0a0a0a;
  position: relative;
}

/* Node Shared Styles */
.vs-node {
  background: #1e1e1e;
  border-radius: 8px;
  border: 1px solid #333;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  font-size: 12px;
  width: 180px;
  overflow: hidden;
  color: #e2e8f0;
}

.vs-node-header {
  padding: 8px;
  font-weight: bold;
  border-bottom: 1px solid #333;
  background: rgba(0,0,0,0.3);
}

.vs-node-body {
  padding: 12px;
}

.vs-node-input {
  width: 100%;
  background: #111;
  border: 1px solid #444;
  color: #fff;
  padding: 4px;
  border-radius: 4px;
  font-size: 11px;
  box-sizing: border-box;
}

/* Node Variants */
.vs-node-start {
  border-color: rgba(56, 189, 248, 0.5);
}
.vs-node-start .vs-node-header { color: #38bdf8; }

.vs-node-action {
  border-color: rgba(244, 63, 94, 0.5);
}
.vs-node-action .vs-node-header { color: #f43f5e; }

.vs-node-math {
  border-color: rgba(245, 158, 11, 0.5);
}
.vs-node-math .vs-node-header { color: #f59e0b; }
.vs-node-math-inputs {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vs-node-logic {
  border-color: rgba(234, 179, 8, 0.5);
}
.vs-node-logic .vs-node-header { color: #eab308; }
.vs-node-logic-inputs {
  display: flex;
  gap: 4px;
  align-items: center;
}
.vs-node-logic-var { width: 40px; }
.vs-node-logic-comp { width: 50px; }
.vs-node-logic-true {
  position: absolute;
  right: -35px;
  top: 26px;
  font-size: 10px;
  color: #10b981;
  font-weight: bold;
}
.vs-node-logic-false {
  position: absolute;
  right: -40px;
  top: 66px;
  font-size: 10px;
  color: #ef4444;
  font-weight: bold;
}

.vs-node-3d {
  border-color: rgba(168, 85, 247, 0.5);
}
.vs-node-3d .vs-node-header { color: #a855f7; }
.vs-node-3d-inputs {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vs-node-3d-coords {
  display: flex;
  gap: 4px;
}
.vs-node-3d-color {
  padding: 0;
  height: 30px;
}

.vs-node-telemetry {
  border-color: rgba(76, 201, 240, 0.5);
}
.vs-node-telemetry .vs-node-header { color: #4cc9f0; }
.vs-node-telemetry-desc {
  font-size: 10px;
  margin-top: 4px;
}
```

---

## 4. Domain Tools – Finance / Crypto / OSINT / System / Specialized

### VectorVaultManager.jsx
```jsx
import React, { useState } from 'react';

export default function VectorVaultManager() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

  const [collection, setCollection] = useState('stehouwer_vector_memory');
  const [queryText, setQueryText] = useState('SHM ring buffer latency');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState([
    { id: 'doc_101', distance: 0.12, content: 'Sub-microsecond SHM ring buffer architecture mapped at Local\\AI_BS_IPC_SHM_RING.', source: 'ringbuffer_multitopic.h' },
    { id: 'doc_102', distance: 0.18, content: 'FastAPI WebSocket Gateway streaming telemetry at 20 Hz (50ms interval).', source: 'shm_websocket_gateway.py' },
    { id: 'doc_103', distance: 0.24, content: 'ComfyUI SDXL & Wan2.1 workflow triggers pushing GPU stats over Topic 0x0006.', source: 'comfyui_workflow_trigger.py' }
  ]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!queryText.trim()) return;
    setIsSearching(true);
    try {
      const res = await fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection_name: collection, query_text: queryText, top_k: 5 })
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data.results);
      }
    } catch (err) {
      console.warn('Backend vector vault query using offline baseline fallback.', err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div style={{
      backgroundColor: '#0d1117',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '16px',
      color: '#c9d1d9',
      marginTop: '12px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, color: '#00d2ff', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🧠</span> ChromaDB Vector Vault Manager (Topic 0x0005)
        </h4>
        <select
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          style={{
            backgroundColor: '#161b22',
            border: '1px solid #30363d',
            color: '#58a6ff',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px'
          }}
        >
          <option value="stehouwer_vector_memory">stehouwer_vector_memory (1,420 docs)</option>
          <option value="web_research_vault">web_research_vault (850 docs)</option>
          <option value="ast_codebase_embeddings">ast_codebase_embeddings (3,200 docs)</option>
        </select>
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          type="text"
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          placeholder="Search vector embeddings..."
          style={{
            flex: 1,
            backgroundColor: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '4px',
            color: '#f0f6fc',
            padding: '8px 12px',
            fontSize: '12px'
          }}
        />
        <button
          type="submit"
          disabled={isSearching}
          style={{
            backgroundColor: '#238636',
            border: 'none',
            borderRadius: '4px',
            color: '#fff',
            padding: '8px 16px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          {isSearching ? 'Querying...' : '🔍 Vector Search'}
        </button>
      </form>

      {/* Results List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {results.map((item, idx) => (
          <div key={idx} style={{
            backgroundColor: '#161b22',
            border: '1px solid #21262d',
            borderRadius: '6px',
            padding: '10px 12px',
            fontSize: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: '#58a6ff', fontWeight: 600 }}>{item.id} • {item.source || item.metadata?.source}</span>
              <span style={{ color: '#7ee787', fontSize: '11px' }}>Dist: {item.distance}</span>
            </div>
            <div style={{ color: '#8b949e', fontSize: '11px', fontFamily: 'Consolas, monospace' }}>
              {item.content}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### UnifiedOsintHub.jsx
```jsx
import React, { useState } from 'react';
import RapidApiReconTab from './RapidApiReconTab';
import BrettDataTab from './BrettDataTab';
import LostPropertyTab from './LostPropertyTab';
import OsintDataVaultTab from './OsintDataVaultTab';

export default function UnifiedOsintHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('recon');

  const tabs = [
    { id: 'recon', label: 'RapidAPI Recon OSINT', icon: '🌐' },
    { id: 'lost_property', label: 'Lost Property & Breach Scanner', icon: '🔍' },
    { id: 'api_hub', label: 'API Keys & Data Hub', icon: '🔑' },
    { id: 'saved_vault', label: 'Data Saved Vault', icon: '🗄️' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      {/* Top Navigation Header */}
      <div style={{ display: 'flex', gap: '10px', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeSubTab === tab.id ? '#238636' : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeSubTab === 'recon' && <RapidApiReconTab {...props} />}
        {activeSubTab === 'lost_property' && <LostPropertyTab {...props} />}
        {activeSubTab === 'api_hub' && <BrettDataTab {...props} />}
        {activeSubTab === 'saved_vault' && (
          <div style={{ padding: '20px', height: '100%', overflowY: 'auto' }}>
            <OsintDataVaultTab {...props} />
          </div>
        )}
      </div>
    </div>
  );
}
```

### UnifiedCryptoHub.jsx
```jsx
import React, { useState } from 'react';
import CryptoSwarmMobileController from './CryptoSwarmMobileController';
import MiningDashboardTab from './MiningDashboardTab';
import GpuNetworkTab from './GpuNetworkTab';

export default function UnifiedCryptoHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('trader');

  const tabs = [
    { id: 'trader', label: 'Crypto Trader & Swarm', icon: '💎' },
    { id: 'mining', label: 'Mining, Hardware & Chia', icon: '⛏️' },
    { id: 'network', label: 'GPU Network & AI Renting', icon: '⚡' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      <div style={{ display: 'flex', gap: '10px', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeSubTab === tab.id ? '#238636' : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeSubTab === 'trader' && <CryptoSwarmMobileController {...props} />}
        {activeSubTab === 'mining' && <MiningDashboardTab {...props} />}
        {activeSubTab === 'network' && <GpuNetworkTab {...props} />}
      </div>
    </div>
  );
}
```

### UnifiedCalendarHub.jsx
```jsx
import React, { useState } from 'react';
import WorkspaceCalendarTab from './WorkspaceCalendarTab';
import AutomatedClientSchedulerTab from './AutomatedClientSchedulerTab';

export default function UnifiedCalendarHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('calendar');

  const tabs = [
    { id: 'calendar', label: 'Master Workspace Calendar', icon: '📅' },
    { id: 'scheduler', label: 'Client Content Scheduler', icon: '📝' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      <div style={{ display: 'flex', gap: '10px', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeSubTab === tab.id ? '#238636' : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeSubTab === 'calendar' && <WorkspaceCalendarTab {...props} />}
        {activeSubTab === 'scheduler' && <AutomatedClientSchedulerTab {...props} />}
      </div>
    </div>
  );
}
```

### UnifiedCreationHub.jsx
```jsx
import React, { useState } from 'react';
import StehouwerCMSTab from './StehouwerCMSTab';
import UniversalCreationSuite from './UniversalCreationSuite';

export default function UnifiedCreationHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('creation');

  const tabs = [
    { id: 'creation', label: 'Universal Creation Suite (Drafting)', icon: '🎨' },
    { id: 'cms', label: 'Stehouwer CMS (Publishing)', icon: '🌐' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      <div style={{ display: 'flex', gap: '10px', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeSubTab === tab.id ? '#238636' : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeSubTab === 'creation' && <UniversalCreationSuite {...props} />}
        {activeSubTab === 'cms' && <StehouwerCMSTab {...props} />}
      </div>
    </div>
  );
}
```

### UnifiedFinancialHub.jsx
```jsx
import React, { useState } from 'react';
import MasterAccountingTab from './MasterAccountingTab';
import MoneyTrackTab from './MoneyTrackTab';

export default function UnifiedFinancialHub(props) {
  const [activeSubTab, setActiveSubTab] = useState('fiat');

  const tabs = [
    { id: 'fiat', label: 'Master Accounting & Taxes (Fiat)', icon: '🏛️' },
    { id: 'crypto', label: 'Passive Yields & Mining (Crypto)', icon: '⛏️' },
  ];

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117', color: '#c9d1d9' }}>
      <div style={{ display: 'flex', gap: '10px', padding: '10px 20px', backgroundColor: '#161b22', borderBottom: '1px solid #30363d' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeSubTab === tab.id ? '#238636' : 'transparent',
              color: activeSubTab === tab.id ? '#ffffff' : '#8b949e',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeSubTab === 'fiat' && <MasterAccountingTab {...props} />}
        {activeSubTab === 'crypto' && <MoneyTrackTab {...props} />}
      </div>
    </div>
  );
}
```

### LearningMaterialHub.jsx
```jsx
import React, { useState } from 'react';
import AeoTracker from '../src/components/AeoTracker.jsx';
import SeoOptimizer from '../src/clients/action_glass/SeoOptimizer.jsx';

export default function LearningMaterialHub() {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

  const [activeSubTab, setActiveSubTab] = useState('aeo_tracker');

  return (
    <div style={{ padding: '20px', color: '#c9d1d9', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>📘 Learning Material & Educational Tools</h2>
      <p style={{ color: '#8b949e', marginBottom: '20px' }}>
        Interactive educational modules and information explainers.
      </p>

      {/* Internal Tab Navigation */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
        <button
          onClick={() => setActiveSubTab('aeo_tracker')}
          style={{
            padding: '8px 16px',
            background: activeSubTab === 'aeo_tracker' ? '#1f6feb' : 'transparent',
            color: activeSubTab === 'aeo_tracker' ? '#ffffff' : '#c9d1d9',
            border: '1px solid',
            borderColor: activeSubTab === 'aeo_tracker' ? '#1f6feb' : '#30363d',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          🔍 AEO Tracker Explainer
        </button>
        <button
          onClick={() => setActiveSubTab('seo_optimizer')}
          style={{
            padding: '8px 16px',
            background: activeSubTab === 'seo_optimizer' ? '#1f6feb' : 'transparent',
            color: activeSubTab === 'seo_optimizer' ? '#ffffff' : '#c9d1d9',
            border: '1px solid',
            borderColor: activeSubTab === 'seo_optimizer' ? '#1f6feb' : '#30363d',
            borderRadius: '6px',
            cursor: 'pointer'
          }}
        >
          📈 SEO Optimizer Explainer
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ background: '#0d1117', padding: '20px', borderRadius: '8px', border: '1px solid #30363d' }}>
        {activeSubTab === 'aeo_tracker' && <AeoTracker />}
        {activeSubTab === 'seo_optimizer' && <SeoOptimizer backendUrl={`${backendUrl}/api/proxy/3000`} />}
      </div>
    </div>
  );
}
```

### WorkspaceCalendarTab.css
```css
.workspace-calendar-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 20px;
  padding: 10px;
}

.calendar-header-panel {
  display: flex;
  gap: 15px;
  align-items: center;
  justify-content: space-between;
  background: #161b22;
  padding: 15px 20px;
  border-radius: 12px;
  border: 1px solid #30363d;
}

.nlp-input-wrapper {
  display: flex;
  align-items: center;
  flex: 1;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  overflow: hidden;
  padding-left: 10px;
}

.nlp-icon {
  font-size: 1.2rem;
  margin-right: 10px;
}

.nlp-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #c9d1d9;
  padding: 12px;
  font-size: 0.95rem;
  outline: none;
}

.nlp-btn {
  background: #238636;
  color: #fff;
  border: none;
  padding: 0 20px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.nlp-btn:hover {
  background: #2ea043;
}
.nlp-btn:disabled {
  background: #484f58;
  cursor: not-allowed;
}

.manual-add-btn {
  background: #1f6feb;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}
.manual-add-btn:hover {
  background: #388bfd;
}

.calendar-container {
  flex: 1;
  background: #0d1117;
  border-radius: 12px;
  border: 1px solid #30363d;
  padding: 20px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

/* Big Calendar Dark Mode Overrides */
.rbc-month-view, .rbc-time-view, .rbc-agenda-view {
  border-color: #30363d !important;
}
.rbc-day-bg, .rbc-header {
  border-color: #30363d !important;
}
.rbc-off-range-bg {
  background: #090c10 !important;
}
.rbc-today {
  background: rgba(31, 111, 235, 0.1) !important;
}
.rbc-toolbar button {
  color: #c9d1d9;
  border-color: #30363d;
}
.rbc-toolbar button.rbc-active {
  background: #1f6feb;
  border-color: #1f6feb;
  color: white;
}
.rbc-toolbar button:hover {
  background: #21262d;
}

/* Modal Styles */
.calendar-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.calendar-modal-content {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
  width: 500px;
  max-width: 90vw;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
}

.calendar-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #30363d;
}

.calendar-modal-header h3 {
  margin: 0;
  color: #c9d1d9;
}

.close-btn {
  background: transparent;
  border: none;
  color: #8b949e;
  font-size: 1.5rem;
  cursor: pointer;
}

.calendar-form {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.calendar-form label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: #8b949e;
  font-size: 0.9rem;
}

.calendar-form input, .calendar-form select, .calendar-form textarea {
  background: #0d1117;
  border: 1px solid #30363d;
  color: #c9d1d9;
  padding: 10px;
  border-radius: 6px;
  font-family: inherit;
}

.form-row {
  display: flex;
  gap: 15px;
}
.form-row label {
  flex: 1;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.delete-btn {
  background: #da3633;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 6px;
  cursor: pointer;
}
.cancel-btn {
  background: transparent;
  color: #c9d1d9;
  border: 1px solid #30363d;
  padding: 10px 15px;
  border-radius: 6px;
  cursor: pointer;
}
.save-btn {
  background: #238636;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}
```

### AdvertisingTabWrapper.jsx
```jsx
/**
 * AdvertisingTabWrapper — legacy shim.
 *
 * The old god-props architecture passed 130+ props through this wrapper.
 * The app now uses AppContext + direct backendUrl prop injection via App.jsx.
 * This file is kept only to prevent broken imports in any external reference.
 * App.jsx mounts AdvertisingTab directly — this wrapper is no longer in the render tree.
 */
import AdvertisingTab from './AdvertisingTab';
export default AdvertisingTab;
```

---

**End of Batch 1 (35 files)**

All original source code from the first batch has been included under the 4 merged categories.
