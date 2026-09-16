import React, { useState } from 'react';
import { useDawStore } from './dawStore';
import StepSequencer from './StepSequencer';
import SoundDesigner from './SoundDesigner';
import { theme } from '../../styles/theme';
import { Sliders, Volume2, Sparkles, Trash2, Music, Activity } from 'lucide-react';

const ChannelRack = () => {
  const channels = useDawStore((state) => state.channels);
  const activeChannelId = useDawStore((state) => state.activeChannelId);
  const setActiveChannelId = useDawStore((state) => state.setActiveChannelId);
  const toggleChannelMute = useDawStore((state) => state.toggleChannelMute);
  const toggleChannelSolo = useDawStore((state) => state.toggleChannelSolo);
  const setChannelVolume = useDawStore((state) => state.setChannelVolume);
  const setChannelPan = useDawStore((state) => state.setChannelPan);
  const stepCount = useDawStore((state) => state.stepCount);
  const setStepCount = useDawStore((state) => state.setStepCount);
  const generateAIBeat = useDawStore((state) => state.generateAIBeat);
  const clearAllSteps = useDawStore((state) => state.clearAllSteps);

  const [designerOpen, setDesignerOpen] = useState(false);
  const activeChannel = channels.find(c => c.id === activeChannelId);

  return (
    <div style={{
      position: 'relative',
      background: 'rgba(15, 18, 24, 0.95)',
      border: `1px solid ${theme.colors.border}`,
      borderRadius: '8px',
      padding: '12px',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflowY: 'auto'
    }}>
      {/* Top Header & Quick Presets */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={16} color={theme.colors.accent} />
          <h3 style={{ margin: 0, color: theme.colors.accent, fontSize: '13px', fontWeight: 'bold' }}>
            CHANNEL RACK
          </h3>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button
            onClick={() => generateAIBeat('trap')}
            title="Generate AI Trap Groove"
            style={{
              background: 'rgba(0, 255, 255, 0.1)',
              border: `1px solid ${theme.colors.accent}`,
              borderRadius: '4px',
              color: theme.colors.accent,
              padding: '3px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Sparkles size={11} /> AI Trap
          </button>

          <button
            onClick={() => generateAIBeat('synthwave')}
            title="Generate AI Synthwave Groove"
            style={{
              background: 'rgba(255, 0, 127, 0.1)',
              border: '1px solid #ff007f',
              borderRadius: '4px',
              color: '#ff007f',
              padding: '3px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Music size={11} /> AI Synthwave
          </button>

          <button
            onClick={() => setDesignerOpen(prev => !prev)}
            title="Open Sound Designer"
            style={{
              background: designerOpen ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255,255,255,0.05)',
              border: designerOpen ? `1px solid ${theme.colors.accent}` : '1px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              color: designerOpen ? '#fff' : '#bbb',
              padding: '3px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Activity size={11} /> Sound Designer
          </button>

          <button
            onClick={() => setStepCount(stepCount === 16 ? 32 : 16)}
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              color: '#bbb',
              padding: '3px 8px',
              fontSize: '11px',
              cursor: 'pointer'
            }}
          >
            {stepCount} Steps
          </button>

          <button
            onClick={clearAllSteps}
            title="Clear Pattern Grid"
            style={{
              background: 'rgba(255, 59, 48, 0.1)',
              border: '1px solid rgba(255, 59, 48, 0.3)',
              borderRadius: '4px',
              color: '#ff5e5e',
              padding: '3px 6px',
              fontSize: '11px',
              cursor: 'pointer'
            }}
          >
            <Trash2 size={11} />
          </button>
        </div>
      </div>

      {/* Channel Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
        {channels.map((channel, i) => {
          const isFocused = activeChannelId === channel.id;

          return (
            <div
              key={channel.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: isFocused ? 'rgba(0, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.35)',
                border: isFocused ? `1px solid ${theme.colors.accent}` : '1px solid rgba(255, 255, 255, 0.05)',
                padding: '4px 8px',
                borderRadius: '4px',
                transition: 'border 0.2s'
              }}
            >
              {/* Mute / Solo Controls */}
              <div style={{ display: 'flex', gap: '2px' }}>
                <button
                  onClick={() => toggleChannelMute(channel.id)}
                  title="Mute Track"
                  style={{
                    background: channel.mute ? '#ff3b30' : 'rgba(255, 255, 255, 0.08)',
                    color: channel.mute ? '#fff' : '#888',
                    border: 'none',
                    borderRadius: '2px',
                    width: '16px',
                    height: '24px',
                    fontSize: '9px',
                    cursor: 'pointer',
                    fontWeight: 'bold'
                  }}
                >
                  M
                </button>
                <button
                  onClick={() => toggleChannelSolo(channel.id)}
                  title="Solo Track"
                  style={{
                    background: channel.solo ? '#5eff7b' : 'rgba(255, 255, 255, 0.08)',
                    color: channel.solo ? '#000' : '#888',
                    border: 'none',
                    borderRadius: '2px',
                    width: '16px',
                    height: '24px',
                    fontSize: '9px',
                    cursor: 'pointer',
                    fontWeight: 'bold'
                  }}
                >
                  S
                </button>
              </div>

              {/* Volume / Pan Small Sliders */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', width: '40px' }}>
                <input
                  type="range"
                  min="-24"
                  max="6"
                  value={channel.volume}
                  onChange={(e) => setChannelVolume(channel.id, Number(e.target.value))}
                  title={`Vol: ${channel.volume} dB`}
                  style={{ width: '100%', height: '4px', accentColor: channel.color, cursor: 'pointer' }}
                />
                <input
                  type="range"
                  min="-1"
                  max="1"
                  step="0.1"
                  value={channel.pan}
                  onChange={(e) => setChannelPan(channel.id, Number(e.target.value))}
                  title={`Pan: ${channel.pan}`}
                  style={{ width: '100%', height: '4px', accentColor: '#888', cursor: 'pointer' }}
                />
              </div>

              {/* Channel Button / Name (Click to focus in Piano Roll) */}
              <div
                onClick={() => setActiveChannelId(channel.id)}
                title={`Click to open ${channel.name} in Piano Roll`}
                style={{
                  width: '110px',
                  background: isFocused ? 'rgba(0, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '3px',
                  padding: '4px 6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  borderLeft: `4px solid ${channel.color}`
                }}
              >
                <span style={{ fontSize: '11px', fontWeight: 'bold', color: isFocused ? '#fff' : '#ccc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {channel.name}
                </span>
                <span style={{ fontSize: '9px', color: '#666' }}>
                  #{i + 1}
                </span>
              </div>

              {/* Step Sequencer */}
              <div style={{ flex: 1, overflowX: 'auto' }}>
                <StepSequencer channel={channel} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Sound Designer Modal Overlay */}
      {designerOpen && (
        <SoundDesigner channel={activeChannel} onClose={() => setDesignerOpen(false)} />
      )}
    </div>
  );
};

export default ChannelRack;
