import React, { useState } from 'react';
import { theme } from '../../styles/theme';
import { LayoutGrid, Layers, Film, Video, Plus, Music2 } from 'lucide-react';
import { useDawStore } from './dawStore';

const DEFAULT_VIDEO_TRACKS = [
  { id: 'v1', name: 'V1: Main Video', type: 'video', clips: [{ bar: 0, length: 8, title: 'Cyber City Drone.mp4', color: '#00f0ff' }, { bar: 8, length: 8, title: 'Matrix Tunnel.mp4', color: '#00f0ff' }] },
  { id: 'v2', name: 'V2: B-Roll & Overlays', type: 'video', clips: [{ bar: 4, length: 4, title: 'Glitch Overlay.mp4', color: '#ff007f' }] }
];

export default function Playlist() {
  const playlistTracks = useDawStore(state => state.playlistTracks);
  const addAudioClipToPlaylist = useDawStore(state => state.addAudioClipToPlaylist);
  const activePatternId = useDawStore(state => state.activePatternId);
  const isPlaying = useDawStore(state => state.isPlaying);
  const currentBar = useDawStore(state => state.currentBar);
  const currentStep = useDawStore(state => state.currentStep);
  const playMode = useDawStore(state => state.playMode);

  const [totalBars, setTotalBars] = useState(16);
  const [videoTracks, setVideoTracks] = useState(DEFAULT_VIDEO_TRACKS);
  const [dragOverTrackId, setDragOverTrackId] = useState(null);

  const handleDropOnTrack = (e, trackId) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverTrackId(null);
    try {
      const dataStr = e.dataTransfer.getData('application/json') || e.dataTransfer.getData('text/plain');
      if (dataStr) {
        const sample = JSON.parse(dataStr);
        const rect = e.currentTarget.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const droppedBar = Math.max(0, Math.floor(offsetX / 64));
        addAudioClipToPlaylist(trackId, droppedBar, sample);
      }
    } catch (err) {
      console.warn("Drop on playlist track error:", err);
    }
  };

  return (
    <div style={{
      background: 'rgba(12, 15, 20, 0.98)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Top Playlist Header */}
      <div style={{
        padding: '8px 12px',
        borderBottom: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(20, 24, 30, 0.8)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <LayoutGrid size={16} color={theme.colors.primary} />
          <h3 style={{ margin: 0, fontSize: '13px', color: '#fff', fontWeight: 'bold' }}>
            UNIFIED MULTIMEDIA TIMELINE ARRANGER
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '11px', color: '#888' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#00f0ff' }}>
            <Film size={12} /> VIDEO TRACKS (V1-V2)
          </span>
          <span>•</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: theme.colors.accent }}>
            <Music2 size={12} /> AUDIO PATTERNS (A1-A6)
          </span>
          <span>• MODE: <b style={{ color: playMode === 'SONG' ? '#5eff7b' : theme.colors.accent }}>{playMode}</b></span>
        </div>
      </div>

      {/* Main Arranger Timeline Canvas */}
      <div style={{ display: 'flex', flex: 1, overflow: 'auto', position: 'relative' }}>
        
        {/* Left Track Headers */}
        <div style={{
          width: '130px',
          borderRight: `1px solid ${theme.colors.border}`,
          background: '#0d1117',
          position: 'sticky',
          left: 0,
          zIndex: 5
        }}>
          {/* Bar Ruler Corner */}
          <div style={{ height: '24px', borderBottom: '1px solid #30363d', background: '#161b22', padding: '4px 8px', fontSize: '10px', color: '#888', fontWeight: 'bold' }}>
            TRACKS
          </div>

          {/* Video Tracks Section */}
          {videoTracks.map(track => (
            <div
              key={track.id}
              style={{
                height: '38px',
                borderBottom: '1px solid rgba(0, 240, 255, 0.15)',
                display: 'flex',
                alignItems: 'center',
                padding: '0 8px',
                fontSize: '11px',
                color: '#00f0ff',
                fontWeight: 'bold',
                background: 'rgba(0, 240, 255, 0.04)',
                borderLeft: '3px solid #00f0ff'
              }}
            >
              <Video size={12} style={{ marginRight: '6px' }} />
              {track.name}
            </div>
          ))}

          {/* Audio Tracks Section */}
          {playlistTracks.map(track => (
            <div
              key={track.id}
              style={{
                height: '38px',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                alignItems: 'center',
                padding: '0 8px',
                fontSize: '11px',
                color: '#ccc',
                fontWeight: '500',
                background: 'rgba(255,255,255,0.02)'
              }}
            >
              <Music2 size={11} style={{ marginRight: '6px', opacity: 0.7 }} />
              {track.name}
            </div>
          ))}
        </div>

        {/* Right Timeline Grid */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: `${totalBars * 64}px`,
          background: '#12161f',
          position: 'relative'
        }}>
          {/* Top Bar Ruler */}
          <div style={{
            height: '24px',
            borderBottom: '1px solid #30363d',
            background: '#161b22',
            display: 'flex'
          }}>
            {Array.from({ length: totalBars }).map((_, barIdx) => (
              <div
                key={barIdx}
                style={{
                  width: '64px',
                  borderRight: '1px solid rgba(255, 255, 255, 0.1)',
                  paddingLeft: '4px',
                  fontSize: '9px',
                  color: currentBar === barIdx && isPlaying ? theme.colors.accent : '#8b949e',
                  display: 'flex',
                  alignItems: 'center',
                  fontWeight: currentBar === barIdx && isPlaying ? 'bold' : 'normal'
                }}
              >
                {barIdx + 1}
              </div>
            ))}
          </div>

          {/* Video Track Lanes */}
          {videoTracks.map(track => (
            <div
              key={track.id}
              style={{
                height: '38px',
                borderBottom: '1px solid rgba(0, 240, 255, 0.1)',
                position: 'relative',
                display: 'flex',
                background: 'rgba(0, 240, 255, 0.02)'
              }}
            >
              {Array.from({ length: totalBars }).map((_, b) => (
                <div key={b} style={{ width: '64px', height: '100%', borderRight: '1px solid rgba(255, 255, 255, 0.04)' }} />
              ))}

              {track.clips.map((clip, cIdx) => (
                <div
                  key={cIdx}
                  style={{
                    position: 'absolute',
                    left: `${clip.bar * 64 + 2}px`,
                    width: `${clip.length * 64 - 4}px`,
                    top: '3px',
                    height: '32px',
                    background: `linear-gradient(135deg, ${clip.color}33, ${clip.color}15)`,
                    border: `1px solid ${clip.color}`,
                    borderRadius: '4px',
                    boxShadow: `0 0 8px ${clip.color}22`,
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0 8px',
                    fontSize: '10px',
                    fontWeight: 'bold',
                    color: '#fff',
                    cursor: 'grab',
                    zIndex: 2,
                    overflow: 'hidden',
                    whiteSpace: 'nowrap'
                  }}
                >
                  <Film size={11} style={{ marginRight: '6px', flexShrink: 0 }} />
                  {clip.title}
                </div>
              ))}
            </div>
          ))}

          {/* Audio Track Lanes */}
          {playlistTracks.map(track => {
            const isDraggedOver = dragOverTrackId === track.id;

            return (
              <div
                key={track.id}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  e.dataTransfer.dropEffect = 'copy';
                  setDragOverTrackId(track.id);
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDragOverTrackId(null);
                }}
                onDrop={(e) => handleDropOnTrack(e, track.id)}
                style={{
                  height: '38px',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  position: 'relative',
                  display: 'flex',
                  backgroundColor: isDraggedOver ? 'rgba(0, 255, 136, 0.12)' : 'transparent',
                  transition: 'background-color 0.15s'
                }}
              >
                {Array.from({ length: totalBars }).map((_, b) => (
                  <div key={b} style={{ width: '64px', height: '100%', borderRight: '1px solid rgba(255, 255, 255, 0.04)' }} />
                ))}

                {track.clips.map((clip, cIdx) => (
                  <div
                    key={cIdx}
                    style={{
                      position: 'absolute',
                      left: `${clip.bar * 64 + 2}px`,
                      width: `${clip.length * 64 - 4}px`,
                      top: '3px',
                      height: '32px',
                      background: `linear-gradient(135deg, ${clip.color}33, ${clip.color}11)`,
                      border: `1px solid ${clip.color}`,
                      borderRadius: '4px',
                      boxShadow: `0 0 10px ${clip.color}22`,
                      display: 'flex',
                      alignItems: 'center',
                      padding: '0 8px',
                      fontSize: '10px',
                      fontWeight: 'bold',
                      color: '#fff',
                      cursor: 'grab',
                      zIndex: 2
                    }}
                  >
                    <Layers size={11} style={{ marginRight: '6px' }} />
                    {clip.title || `${track.name} (Pat ${clip.patternId})`}
                  </div>
                ))}
              </div>
            );
          })}

          {/* Master Volume & Filter Automation Lane */}
          <div style={{
            height: '42px',
            borderBottom: '1px solid rgba(168, 85, 247, 0.2)',
            position: 'relative',
            display: 'flex',
            background: 'rgba(168, 85, 247, 0.03)'
          }}>
            {Array.from({ length: totalBars }).map((_, b) => (
              <div key={b} style={{ width: '64px', height: '100%', borderRight: '1px solid rgba(255, 255, 255, 0.04)' }} />
            ))}

            {/* Automation Curve Visualization */}
            <svg style={{ position: 'absolute', top: 0, left: 0, width: `${totalBars * 64}px`, height: '100%', pointerEvents: 'none' }}>
              <path
                d={`M 0 35 Q ${totalBars * 16} 5, ${totalBars * 32} 20 T ${totalBars * 64} 10`}
                fill="none"
                stroke="#c084fc"
                strokeWidth="2"
                strokeDasharray="4 2"
              />
              {/* Keyframe Nodes */}
              <circle cx="0" cy="35" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
              <circle cx={`${totalBars * 16}`} cy="15" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
              <circle cx={`${totalBars * 32}`} cy="20" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
              <circle cx={`${totalBars * 64}`} cy="10" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
            </svg>
            <div style={{ position: 'absolute', left: '8px', top: '2px', fontSize: '9px', color: '#c084fc', fontWeight: 'bold' }}>
              ⚡ AUTO: Master Dynamic Energy & Filter Sweep
            </div>
          </div>

          {/* Synchronized Playhead Cursor */}
          {isPlaying && (
            <div
              style={{
                position: 'absolute',
                left: `${(currentBar * 64) + (currentStep * 4)}px`,
                top: 0,
                bottom: 0,
                width: '2px',
                background: '#5eff7b',
                boxShadow: '0 0 10px #5eff7b',
                zIndex: 10,
                pointerEvents: 'none'
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

