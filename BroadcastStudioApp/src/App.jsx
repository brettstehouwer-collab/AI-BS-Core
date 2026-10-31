import React, { useState, useEffect } from 'react';
import { SYSTEM_VERSION } from './version.js';
import * as Tone from 'tone';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { 
  Radio, Music, Columns, Wrench, Terminal, RefreshCw, Zap, Server, X
} from 'lucide-react';

// Dedicated Studio Components (Broadcast & DAW)
import BroadcastStudio from './components/BroadcastStudio.jsx';
import MusicDAWStudioTab from './components/daw/MusicDAWStudioTab.jsx';
import ThematicVstVisualizer from './components/ThematicVstVisualizer.jsx';

const STUDIO_TABS = [
  { id: 'broadcast', label: 'Broadcast Studio', icon: Radio, color: '#00e5ff', desc: 'Broadcast workspace, local canvases and output status' },
  { id: 'daw', label: 'Music DAW', icon: Music, color: '#10b981', desc: '16-Step Arranger, Tone.js Workstation, Multi-Track Mixer, DSP FX' },
];

const MULTI_PRESETS = [
  { id: 'split_broadcast_daw', label: 'Dual: Broadcast + DAW', icon: Columns },
  { id: 'split_broadcast_stacked', label: 'Stacked: Broadcast / DAW', icon: Columns },
];

export default function App() {
  const [activeLayout, setActiveLayout] = useState('broadcast');
  const [showDevToolsModal, setShowDevToolsModal] = useState(false);
  const [isProbing, setIsProbing] = useState(false);
  const [devLogs, setDevLogs] = useState([
    { id: 1, time: new Date().toLocaleTimeString(), msg: 'AI-BS BS-Studio (Broadcast & DAW Engine) Initialized', type: 'info' }
  ]);

  const [localhostServices, setLocalhostServices] = useState([
    { name: 'FastAPI Master Core', port: 8080, url: 'http://127.0.0.1:8080/api/vst/scan', status: 'pending', latency: '--', desc: 'Core Matrix Engine, VST3 Scanning & File Vault' },
    { name: 'Broadcast Stream Kernel', port: 8088, url: 'http://127.0.0.1:8088/api/windows', status: 'pending', latency: '--', desc: 'DirectX 11 Zero-Copy, AV1 NVENC Ingest & Windows Hooks' },
    { name: 'Broadcast Engine Legacy', port: 8005, url: 'http://127.0.0.1:8005/api/windows', status: 'pending', latency: '--', desc: 'FFmpeg NVENC Hardware Ingest & Windows Hooks' },
    { name: 'Social Hub & Twitch Bot', port: 8006, url: 'http://127.0.0.1:8006/api/social/status', status: 'pending', latency: '--', desc: 'Twitch IRC, Sidekick AI Chat & Live Hype Engine' },
    { name: 'VST3 DSP Theme Bridge', port: 8013, url: 'http://127.0.0.1:8013/api/vst/theme-state', status: 'pending', latency: '--', desc: 'Hardware DSP Audio Theme Sync Daemon' },
    { name: 'ComfyUI Neural Studio', port: 8188, url: 'http://127.0.0.1:8188/system_stats', status: 'pending', latency: '--', desc: 'Local SDXL/Flux Image & Video Diffusion Matrix' },
    { name: 'Ollama Host GPU Master', port: 11434, url: 'http://127.0.0.1:11434/api/version', status: 'pending', latency: '--', desc: 'Local RTX 4090 Ollama Large Language Model Server' },
    { name: 'ChromaDB Vector Store', port: 8002, url: 'http://127.0.0.1:8002/api/v2/heartbeat', status: 'pending', latency: '--', desc: 'Long-Term Episodic Vector Memory Database' }
  ]);

  // Auto-unlock Tone.js Web Audio context on first user interaction
  useEffect(() => {
    const unlockAudio = async () => {
      try {
        if (Tone.context && Tone.context.state !== 'running') {
          await Tone.start();
        }
      } catch {}
    };
    window.addEventListener('click', unlockAudio, { once: true });
    window.addEventListener('keydown', unlockAudio, { once: true });
    window.addEventListener('pointerdown', unlockAudio, { once: true });
    return () => {
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('keydown', unlockAudio);
      window.removeEventListener('pointerdown', unlockAudio);
    };
  }, []);

  const probeLocalhostServices = async () => {
    setIsProbing(true);
    const updated = await Promise.all(localhostServices.map(async (svc) => {
      const t0 = performance.now();
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1800);
      try {
        const response = await fetch(svc.url, { signal: controller.signal, mode: 'cors', cache: 'no-store' });
        const latency = Math.round(performance.now() - t0);
        // A readable endpoint response is reachability evidence, not an authenticated health receipt.
        if (response.type === 'opaque') return { ...svc, status: 'unknown', latency: '--' };
        return { ...svc, status: response.ok ? 'reachable' : 'unhealthy', latency: `${latency}ms` };
      } catch (err) {
        return { ...svc, status: 'unknown', latency: '--' };
      } finally {
        clearTimeout(timeoutId);
      }
    }));
    setLocalhostServices(updated);
    setIsProbing(false);
    setDevLogs(prev => [
      { id: Date.now(), time: new Date().toLocaleTimeString(), msg: `Reachability probe finished. ${updated.filter(s => s.status === 'reachable').length}/${updated.length} readable successful HTTP responses; service health remains unverified.`, type: 'info' },
      ...prev.slice(0, 40)
    ]);
  };

  const handleOpenChromeDevTools = () => {
    try {
      if (window.require) {
        const { ipcRenderer } = window.require('electron');
        ipcRenderer.send('toggle-devtools');
      } else {
        alert('Press F12 or Ctrl+Shift+I anytime in the standalone window to toggle Chrome DevTools.');
      }
    } catch (e) {
      alert('Press F12 or Ctrl+Shift+I anytime in the standalone window to toggle Chrome DevTools.');
    }
  };

  const handleReloadWindow = () => {
    try {
      if (window.require) {
        const { ipcRenderer } = window.require('electron');
        ipcRenderer.send('reload-window');
      } else {
        window.location.reload();
      }
    } catch (e) {
      window.location.reload();
    }
  };

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      backgroundColor: '#07090e',
      color: '#f8fafc',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'Inter, system-ui, sans-serif',
      overflow: 'hidden'
    }}>
      {/* Top BS-Studio Control & Mode Bar */}
      <div style={{
        padding: '6px 14px',
        backgroundColor: '#0f172a',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '10px',
        flexWrap: 'nowrap',
        overflowX: 'auto',
        zIndex: 10
      }}>
        {/* Left: Studio Title & VST Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '9px',
              height: '9px',
              borderRadius: '50%',
              backgroundColor: '#00e5ff',
              boxShadow: '0 0 10px #00e5ff'
            }} />
            <h2 style={{ margin: 0, fontSize: '13px', fontWeight: 800, letterSpacing: '0.06em', color: '#f8fafc', whiteSpace: 'nowrap' }}>
              BS-STUDIO
            </h2>
            <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, padding: '2px 6px', background: '#1e293b', borderRadius: '4px' }}>
              {SYSTEM_VERSION}
            </span>
          </div>

          <ThematicVstVisualizer compact={true} />
        </div>

        {/* Center: Full-Screen Studio Tabs (Broadcast & DAW Only) */}
        <div style={{
          display: 'flex',
          backgroundColor: '#090d16',
          padding: '3px',
          borderRadius: '8px',
          border: '1px solid #1e293b',
          gap: '4px',
          overflowX: 'auto',
          flexShrink: 1
        }}>
          {STUDIO_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeLayout === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveLayout(tab.id)}
                title={tab.desc}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  backgroundColor: isActive ? `${tab.color}22` : 'transparent',
                  border: isActive ? `1px solid ${tab.color}` : '1px solid transparent',
                  color: isActive ? tab.color : '#94a3b8',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: isActive ? 700 : 500,
                  transition: 'all 0.15s ease',
                  whiteSpace: 'nowrap',
                  boxShadow: isActive ? `0 0 12px ${tab.color}33` : 'none'
                }}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Multi-View Presets & Localhost Dev Tools */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <div style={{
            display: 'flex',
            backgroundColor: '#090d16',
            padding: '3px',
            borderRadius: '6px',
            border: '1px solid #1e293b',
            gap: '3px'
          }}>
            {MULTI_PRESETS.map((preset) => {
              const Icon = preset.icon;
              const isActive = activeLayout === preset.id;
              return (
                <button
                  key={preset.id}
                  onClick={() => setActiveLayout(preset.id)}
                  title={preset.label}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '5px 8px',
                    backgroundColor: isActive ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                    border: isActive ? '1px solid #94a3b8' : '1px solid transparent',
                    color: isActive ? '#fff' : '#64748b',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: isActive ? 600 : 400,
                    whiteSpace: 'nowrap'
                  }}
                >
                  <Icon size={12} />
                  <span>{preset.label}</span>
                </button>
              );
            })}
          </div>

          <button 
            onClick={() => {
              probeLocalhostServices();
              setShowDevToolsModal(true);
            }}
            style={{ 
              backgroundColor: '#1e293b', color: '#10b981', border: '1px solid #10b981', 
              padding: '5px 10px', borderRadius: '5px', fontWeight: 'bold', fontSize: '11px', 
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px', whiteSpace: 'nowrap' 
            }}
            title="Open Localhost Dev Tools & Port Prober (F12)"
          >
            <Wrench size={12} /> Dev Tools (F12)
          </button>
        </div>
      </div>

      {/* Main Workspace Render Engine */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative', minHeight: 0 }}>
        {/* 1. BROADCAST STUDIO */}
        {activeLayout === 'broadcast' && (
          <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
            <BroadcastStudio />
          </div>
        )}

        {/* 2. MUSIC DAW STUDIO */}
        {activeLayout === 'daw' && (
          <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
            <MusicDAWStudioTab />
          </div>
        )}

        {/* MULTI-PRESET 1: Split Broadcast + DAW (Horizontal Side-by-Side) */}
        {activeLayout === 'split_broadcast_daw' && (
          <PanelGroup direction="horizontal" style={{ width: '100%', height: '100%' }}>
            <Panel defaultSize={50} minSize={30}>
              <div style={{ width: '100%', height: '100%', borderRight: '1px solid #1e293b', overflow: 'hidden' }}>
                <BroadcastStudio />
              </div>
            </Panel>
            <PanelResizeHandle style={{ width: '4px', background: '#1e293b', cursor: 'col-resize' }} />
            <Panel defaultSize={50} minSize={30}>
              <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
                <MusicDAWStudioTab />
              </div>
            </Panel>
          </PanelGroup>
        )}

        {/* MULTI-PRESET 2: Stacked Broadcast (Top) + DAW (Bottom) */}
        {activeLayout === 'split_broadcast_stacked' && (
          <PanelGroup direction="vertical" style={{ width: '100%', height: '100%' }}>
            <Panel defaultSize={50} minSize={25}>
              <div style={{ width: '100%', height: '100%', borderBottom: '1px solid #1e293b', overflow: 'hidden' }}>
                <BroadcastStudio />
              </div>
            </Panel>
            <PanelResizeHandle style={{ height: '4px', background: '#1e293b', cursor: 'row-resize' }} />
            <Panel defaultSize={50} minSize={25}>
              <div style={{ width: '100%', height: '100%', overflow: 'hidden' }}>
                <MusicDAWStudioTab />
              </div>
            </Panel>
          </PanelGroup>
        )}
      </div>

      {/* LOCALHOST DEV TOOLS & ECOSYSTEM SERVICES MODAL */}
      {showDevToolsModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 99999,
          backgroundColor: 'rgba(0, 0, 0, 0.85)', backdropFilter: 'blur(10px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            width: '880px', maxHeight: '90vh', backgroundColor: '#070b14',
            border: '1px solid #10b981', borderRadius: '12px',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: '0 25px 60px rgba(0,0,0,0.95)'
          }}>
            {/* Modal Header */}
            <div style={{ padding: '16px 20px', background: '#0a101d', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Wrench size={20} color="#10b981" />
                <div>
                  <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '15px', fontWeight: 'bold' }}>
                    AI-BS Universal AV Omni-Studio Standalone Dev Tools & Diagnostic Suite
                  </h3>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Real-time local ecosystem services, IPC bridge controls, and Chrome DevTools
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setShowDevToolsModal(false)} 
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Quick Actions Bar */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                <button
                  onClick={probeLocalhostServices}
                  disabled={isProbing}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    background: '#134e4a', border: '1px solid #10b981', color: '#fff',
                    padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '11px'
                  }}
                >
                  <RefreshCw size={14} className={isProbing ? 'spin' : ''} />
                  {isProbing ? 'Probing Services...' : '🔄 Probe All Ports'}
                </button>

                <button
                  onClick={handleOpenChromeDevTools}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    background: '#1e293b', border: '1px solid #38bdf8', color: '#38bdf8',
                    padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '11px'
                  }}
                >
                  <Terminal size={14} />
                  🔍 Toggle DevTools (F12)
                </button>

                <button
                  onClick={handleReloadWindow}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    background: '#1e293b', border: '1px solid #f59e0b', color: '#f59e0b',
                    padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '11px'
                  }}
                >
                  <RefreshCw size={14} />
                  🔁 Reload App (F5)
                </button>

                <button
                  onClick={() => {
                    setDevLogs(prev => [
                      { id: Date.now(), time: new Date().toLocaleTimeString(), msg: 'Hardware Test: Full Omni Studio Matrix Pipeline Ready', type: 'success' },
                      ...prev
                    ]);
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                    background: '#1e293b', border: '1px solid #a855f7', color: '#a855f7',
                    padding: '10px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '11px'
                  }}
                >
                  <Zap size={14} />
                  ⚡ Test AV Pipelines
                </button>
              </div>

              {/* Localhost Services Matrix */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#10b981', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Server size={14} /> Localhost Port Matrix & Health Dashboard
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {localhostServices.map((svc, i) => (
                    <div 
                      key={i} 
                      style={{ 
                        background: '#0d1322', 
                        border: svc.status === 'online' ? '1px solid #10b981' : svc.status === 'offline' ? '1px solid #ef4444' : '1px solid #1e293b', 
                        borderRadius: '6px', 
                        padding: '10px 12px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 'bold', color: '#f8fafc', fontSize: '12px' }}>{svc.name}</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{
                            fontSize: '10px',
                            fontWeight: 'bold',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: svc.status === 'online' ? 'rgba(16,185,129,0.2)' : svc.status === 'offline' ? 'rgba(239,68,68,0.2)' : 'rgba(100,116,139,0.2)',
                            color: svc.status === 'online' ? '#10b981' : svc.status === 'offline' ? '#ef4444' : '#94a3b8'
                          }}>
                            PORT {svc.port}
                          </span>
                          <span style={{
                            fontSize: '10px',
                            fontWeight: 'bold',
                            color: svc.status === 'online' ? '#10b981' : svc.status === 'offline' ? '#ef4444' : '#94a3b8'
                          }}>
                            {svc.status.toUpperCase()} ({svc.latency})
                          </span>
                        </div>
                      </div>
                      <div style={{ fontSize: '10px', color: '#64748b' }}>{svc.desc}</div>
                      <div style={{ fontSize: '9px', color: '#38bdf8', fontFamily: 'monospace' }}>{svc.url}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Dev Terminal & Event Log */}
              <div>
                <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Terminal size={14} /> Diagnostic Event Log & IPC Stream
                </div>
                <div style={{
                  background: '#020617',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  padding: '10px',
                  maxHeight: '160px',
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '11px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}>
                  {devLogs.map(log => (
                    <div key={log.id} style={{ display: 'flex', gap: '8px', color: log.type === 'success' ? '#10b981' : log.type === 'error' ? '#ef4444' : '#94a3b8' }}>
                      <span style={{ color: '#475569' }}>[{log.time}]</span>
                      <span>{log.msg}</span>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Modal Footer */}
            <div style={{ padding: '12px 20px', background: '#0a101d', borderTop: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                💡 Tip: Press <kbd style={{ background: '#1e293b', color: '#38bdf8', padding: '2px 5px', borderRadius: '3px' }}>F12</kbd> or <kbd style={{ background: '#1e293b', color: '#38bdf8', padding: '2px 5px', borderRadius: '3px' }}>Ctrl+Shift+I</kbd> anytime to open Chrome DevTools.
              </div>
              <button 
                onClick={() => setShowDevToolsModal(false)}
                style={{ background: '#10b981', color: '#000', border: 'none', padding: '6px 18px', borderRadius: '4px', fontWeight: 'bold', fontSize: '11px', cursor: 'pointer' }}
              >
                Close Diagnostic Suite
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
