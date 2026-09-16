import React, { useState } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { Radio, Music, Mic, Video, Columns, Grid, Maximize2, Activity } from 'lucide-react';

// Importing the individual studio components
import VideoStreamingTab from './VideoStreamingTab.jsx';
import BroadcastStudio from '../src/components/BroadcastStudio.jsx';
import NeuralAudioStudioTab from './NeuralAudioStudioTab.jsx';
import MusicDAWStudioTab from '../src/components/daw/MusicDAWStudioTab.jsx';
import ThematicVstVisualizer from '../src/components/ThematicVstVisualizer.jsx';

const STUDIO_TABS = [
  { id: 'broadcast', label: 'Broadcast Studio (OBS)', icon: Radio, color: '#00e5ff', desc: 'OBS DXGI Hook, NVENC RTMP, Scene Switcher' },
  { id: 'daw', label: 'Music DAW & VST3 Studio', icon: Music, color: '#10b981', desc: '16-Step Arranger, Tone.js Workstation, DSP FX' },
  { id: 'neural', label: 'Neural Voice & Audio AI', icon: Mic, color: '#a855f7', desc: 'F5-TTS, Voice Cloner, Zero-Shot Vocals' },
  { id: 'video', label: 'Video Meetings & WebRTC', icon: Video, color: '#3b82f6', desc: 'P2P Encrypted Video Calls & Screen Share' },
];

const MULTI_PRESETS = [
  { id: 'split_broadcast_daw', label: 'Dual: Broadcast + DAW', icon: Columns },
  { id: 'split_broadcast_video', label: 'Dual: Broadcast + Video Meet', icon: Columns },
  { id: 'matrix_quad', label: '4-Grid Master Matrix', icon: Grid },
];

export default function OmniStudioTab() {
  const [activeLayout, setActiveLayout] = useState('broadcast');

  return (
    <div style={{
      width: '100%',
      height: '100%',
      backgroundColor: '#07090e',
      color: '#f8fafc',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: 'Inter, system-ui, sans-serif',
      overflowY: 'auto',
      overflowX: 'hidden'
    }}>
      {/* Top Universal Control & Mode Bar */}
      <div style={{
        padding: '8px 16px',
        backgroundColor: '#0f172a',
        borderBottom: '1px solid #1e293b',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '12px',
        flexWrap: 'wrap',
        zIndex: 10
      }}>
        {/* Left: Studio Title & VST Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: '#00e5ff',
              boxShadow: '0 0 10px #00e5ff'
            }} />
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 800, letterSpacing: '0.04em', color: '#f8fafc' }}>
              UNIVERSAL AV OMNI-STUDIO
            </h2>
          </div>

          <ThematicVstVisualizer compact={true} />
        </div>

        {/* Center: Full-Screen Studio Tabs */}
        <div style={{
          display: 'flex',
          backgroundColor: '#090d16',
          padding: '3px',
          borderRadius: '8px',
          border: '1px solid #1e293b',
          gap: '4px'
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
                  padding: '6px 12px',
                  backgroundColor: isActive ? `${tab.color}22` : 'transparent',
                  border: isActive ? `1px solid ${tab.color}` : '1px solid transparent',
                  color: isActive ? tab.color : '#94a3b8',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: isActive ? 700 : 500,
                  transition: 'all 0.15s ease',
                  boxShadow: isActive ? `0 0 12px ${tab.color}33` : 'none'
                }}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Multi-View Presets & Telemetry */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            display: 'flex',
            backgroundColor: '#090d16',
            padding: '3px',
            borderRadius: '6px',
            border: '1px solid #1e293b',
            gap: '2px'
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
                    gap: '4px',
                    padding: '4px 8px',
                    backgroundColor: isActive ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
                    border: isActive ? '1px solid #94a3b8' : '1px solid transparent',
                    color: isActive ? '#fff' : '#64748b',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '10px',
                    fontWeight: isActive ? 600 : 400
                  }}
                >
                  <Icon size={12} />
                  <span>{preset.label}</span>
                </button>
              );
            })}
          </div>

          <span style={{ fontSize: '10px', color: '#64748b', fontFamily: 'monospace' }}>
            ZUSTAND SYNCED
          </span>
        </div>
      </div>

      {/* Main Workspace Render Engine */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {/* TAB 1: Focused Broadcast Studio */}
        {activeLayout === 'broadcast' && (
          <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
            <BroadcastStudio />
          </div>
        )}

        {/* TAB 2: Focused Music DAW */}
        {activeLayout === 'daw' && (
          <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
            <MusicDAWStudioTab />
          </div>
        )}

        {/* TAB 3: Focused Neural Audio Studio */}
        {activeLayout === 'neural' && (
          <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
            <NeuralAudioStudioTab />
          </div>
        )}

        {/* TAB 4: Focused Video Meetings */}
        {activeLayout === 'video' && (
          <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
            <VideoStreamingTab />
          </div>
        )}

        {/* PRESET 1: Split Broadcast (Left) + DAW (Right) */}
        {activeLayout === 'split_broadcast_daw' && (
          <PanelGroup direction="horizontal">
            <Panel defaultSize={50} minSize={25} order={1}>
              <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                <BroadcastStudio />
              </div>
            </Panel>
            <PanelResizeHandle style={{ width: '6px', backgroundColor: '#1e293b', cursor: 'col-resize' }} />
            <Panel defaultSize={50} minSize={25} order={2}>
              <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                <MusicDAWStudioTab />
              </div>
            </Panel>
          </PanelGroup>
        )}

        {/* PRESET 2: Split Broadcast (Left) + Video Meeting (Right) */}
        {activeLayout === 'split_broadcast_video' && (
          <PanelGroup direction="horizontal">
            <Panel defaultSize={55} minSize={25} order={1}>
              <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                <BroadcastStudio />
              </div>
            </Panel>
            <PanelResizeHandle style={{ width: '6px', backgroundColor: '#1e293b', cursor: 'col-resize' }} />
            <Panel defaultSize={45} minSize={25} order={2}>
              <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                <VideoStreamingTab />
              </div>
            </Panel>
          </PanelGroup>
        )}

        {/* PRESET 3: 4-Grid Master Matrix (Top: Video + Broadcast, Bottom: DAW + Neural) */}
        {activeLayout === 'matrix_quad' && (
          <PanelGroup direction="vertical">
            <Panel defaultSize={50} minSize={15} order={1}>
              <PanelGroup direction="horizontal">
                <Panel defaultSize={45} minSize={15} order={1}>
                  <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                    <VideoStreamingTab />
                  </div>
                </Panel>
                <PanelResizeHandle style={{ width: '6px', backgroundColor: '#1e293b', cursor: 'col-resize' }} />
                <Panel defaultSize={55} minSize={15} order={2}>
                  <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                    <BroadcastStudio />
                  </div>
                </Panel>
              </PanelGroup>
            </Panel>

            <PanelResizeHandle style={{ height: '6px', backgroundColor: '#1e293b', cursor: 'row-resize' }} />

            <Panel defaultSize={50} minSize={15} order={2}>
              <PanelGroup direction="horizontal">
                <Panel defaultSize={65} minSize={15} order={1}>
                  <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                    <MusicDAWStudioTab />
                  </div>
                </Panel>
                <PanelResizeHandle style={{ width: '6px', backgroundColor: '#1e293b', cursor: 'col-resize' }} />
                <Panel defaultSize={35} minSize={15} order={2}>
                  <div style={{ width: '100%', height: '100%', overflow: 'auto' }}>
                    <NeuralAudioStudioTab />
                  </div>
                </Panel>
              </PanelGroup>
            </Panel>
          </PanelGroup>
        )}
      </div>
    </div>
  );
}
