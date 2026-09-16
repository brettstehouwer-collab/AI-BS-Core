import React, { useState, useEffect, useRef } from 'react';
import { theme } from '../../styles/theme';
import { 
  LayoutGrid, Layers, Film, Video, Plus, Music2, Scissors, 
  MoveHorizontal, VolumeX, Trash2, Edit3, Paintbrush, ZoomIn, 
  ZoomOut, Sparkles, MoreVertical, Sliders, Check
} from 'lucide-react';
import { useDawStore } from './dawStore';
import EdisonAudioEditorModal from './EdisonAudioEditorModal';
import SlicexChopperModal from './SlicexChopperModal';
import ClipSettingsModal from './ClipSettingsModal';

const DEFAULT_VIDEO_TRACKS = [
  { id: 'v1', name: 'V1: Main Video', type: 'video', clips: [{ id: 'vc1', bar: 0, length: 8, title: 'Cyber City Drone.mp4', color: '#00f0ff' }, { id: 'vc2', bar: 8, length: 8, title: 'Matrix Tunnel.mp4', color: '#00f0ff' }] },
  { id: 'v2', name: 'V2: B-Roll & Overlays', type: 'video', clips: [{ id: 'vc3', bar: 4, length: 4, title: 'Glitch Overlay.mp4', color: '#ff007f' }] }
];

export default function Playlist() {
  const playlistTracks = useDawStore(state => state.playlistTracks);
  const setPlaylistTracks = useDawStore(state => state.setPlaylistTracks);
  const addPlaylistClip = useDawStore(state => state.addPlaylistClip);
  const activePatternId = useDawStore(state => state.activePatternId);
  const isPlaying = useDawStore(state => state.isPlaying);
  const currentBar = useDawStore(state => state.currentBar);
  const currentStep = useDawStore(state => state.currentStep);
  const playMode = useDawStore(state => state.playMode);
  const setActiveView = useDawStore(state => state.setActiveView);

  const [totalBars, setTotalBars] = useState(32);
  const [videoTracks, setVideoTracks] = useState(DEFAULT_VIDEO_TRACKS);
  
  // Arrangement Tools: 'draw' (P), 'paint' (B), 'slice' (C), 'slip' (S), 'mute' (T), 'delete' (D)
  const [activeTool, setActiveTool] = useState('draw');
  const [snapGrid, setSnapGrid] = useState('1_bar'); // '1_bar' | '1/2_beat' | '1/4_beat' | 'none'
  const [zoomScale, setZoomScale] = useState(64); // pixels per bar (default 64px)

  // Modals & Active Clip State
  const [activeEditingClip, setActiveEditingClip] = useState(null);
  const [showEdisonModal, setShowEdisonModal] = useState(false);
  const [showSlicexModal, setShowSlicexModal] = useState(false);
  const [showClipSettingsModal, setShowClipSettingsModal] = useState(false);
  const [clipMenuOpenId, setClipMenuOpenId] = useState(null);

  // Dragging & Slipping State
  const [draggingClipInfo, setDraggingClipInfo] = useState(null);
  const [hoverSliceBar, setHoverSliceBar] = useState(null);

  // Keyboard Shortcuts (P, B, C, S, T, D, Ctrl+E)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      
      const key = e.key.toLowerCase();
      if (e.ctrlKey && key === 'e') {
        e.preventDefault();
        // Open Edison on first audio clip
        const firstClip = playlistTracks.flatMap(t => t.clips)[0];
        if (firstClip) {
          setActiveEditingClip(firstClip);
          setShowEdisonModal(true);
        }
      } else if (key === 'p') {
        setActiveTool('draw');
      } else if (key === 'b') {
        setActiveTool('paint');
      } else if (key === 'c') {
        setActiveTool('slice');
      } else if (key === 's') {
        setActiveTool('slip');
      } else if (key === 't') {
        setActiveTool('mute');
      } else if (key === 'd') {
        setActiveTool('delete');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [playlistTracks]);

  // Click on Track Lane with Draw / Paint tool to add pattern clip
  const handleLaneClick = (trackId, e) => {
    if (activeTool !== 'draw' && activeTool !== 'paint') return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickBar = Math.floor(clickX / zoomScale);

    if (clickBar >= 0 && clickBar < totalBars) {
      const newClip = {
        id: `clip_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
        bar: clickBar,
        length: 4,
        patternId: activePatternId || 1,
        title: `Pattern ${activePatternId || 1}`,
        color: '#00f0ff',
        slipOffset: 0,
        muted: false
      };
      addPlaylistClip(trackId, newClip);
    }
  };

  // Slicing Tool Click: Splits clip into two pieces at exact slice point
  const handleClipClick = (trackId, clip, e) => {
    e.stopPropagation();

    if (activeTool === 'delete') {
      // Delete clip
      setPlaylistTracks(prev => prev.map(t => 
        t.id === trackId ? { ...t, clips: t.clips.filter(c => c.id !== clip.id) } : t
      ));
      return;
    }

    if (activeTool === 'mute') {
      // Toggle clip mute
      setPlaylistTracks(prev => prev.map(t => 
        t.id === trackId ? {
          ...t,
          clips: t.clips.map(c => c.id === clip.id ? { ...c, muted: !c.muted } : c)
        } : t
      ));
      return;
    }

    if (activeTool === 'slice') {
      // Calculate exact slice offset in bars
      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const sliceOffsetBar = Math.max(0.5, Math.min(clip.length - 0.5, Math.round((clickX / zoomScale) * 2) / 2));

      if (sliceOffsetBar > 0 && sliceOffsetBar < clip.length) {
        const leftClip = {
          ...clip,
          id: `${clip.id}_part1`,
          length: sliceOffsetBar
        };
        const rightClip = {
          ...clip,
          id: `${clip.id}_part2`,
          bar: clip.bar + sliceOffsetBar,
          length: clip.length - sliceOffsetBar,
          slipOffset: (clip.slipOffset || 0) + sliceOffsetBar
        };

        setPlaylistTracks(prev => prev.map(t => 
          t.id === trackId ? {
            ...t,
            clips: [...t.clips.filter(c => c.id !== clip.id), leftClip, rightClip]
          } : t
        ));
      }
      return;
    }

    if (activeTool === 'draw' || activeTool === 'paint') {
      setActiveEditingClip(clip);
    }
  };

  // Double Click: Open Channel / Clip Settings
  const handleClipDoubleClick = (clip, e) => {
    e.stopPropagation();
    setActiveEditingClip(clip);
    setShowClipSettingsModal(true);
  };

  // Make Unique Action
  const handleMakeUnique = (clipToClone) => {
    setPlaylistTracks(prev => prev.map(t => ({
      ...t,
      clips: t.clips.map(c => {
        if (c.id === clipToClone.id) {
          return {
            ...c,
            id: `clip_unique_${Date.now()}`,
            title: `${c.title || 'Clip'} #unique`,
            color: '#a855f7',
            isUnique: true
          };
        }
        return c;
      })
    })));
  };

  // Update Clip from Modal
  const handleUpdateClip = (updatedClip) => {
    setPlaylistTracks(prev => prev.map(t => ({
      ...t,
      clips: t.clips.map(c => c.id === updatedClip.id ? updatedClip : c)
    })));
  };

  // Send edited audio from Edison back to playlist
  const handleEdisonSendToPlaylist = (edisonClip) => {
    const newClip = {
      id: `edison_${Date.now()}`,
      bar: currentBar || 0,
      length: Math.max(2, Math.ceil((edisonClip.duration || 4) / 2)),
      title: edisonClip.title,
      color: '#ff7b00',
      audioBuffer: edisonClip.audioBuffer,
      slipOffset: 0,
      muted: false
    };
    // Add to first audio track or create new track
    addPlaylistClip(1, newClip);
  };

  // Dump Slices from Slicex
  const handleDumpSlices = (slices, originClip) => {
    let currentOffset = 0;
    const dumpedClips = slices.map((s, idx) => {
      const sliceLength = 1; // 1 bar each
      const c = {
        id: `slice_${Date.now()}_${idx}`,
        bar: currentOffset,
        length: sliceLength,
        title: `${originClip?.title || 'Beat'} [${s.label}]`,
        color: s.color,
        slipOffset: s.start,
        muted: false
      };
      currentOffset += sliceLength;
      return c;
    });

    setPlaylistTracks(prev => [
      ...prev,
      {
        id: Date.now(),
        name: `Chops: ${originClip?.title || 'Slicex'}`,
        clips: dumpedClips
      }
    ]);
  };

  // Timeline File Drop (Drag whole song or audio onto tracks)
  const handleTimelineDrop = (trackId, e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('audio/')) {
      const url = URL.createObjectURL(file);
      const rect = e.currentTarget.getBoundingClientRect();
      const dropX = e.clientX - rect.left;
      const dropBar = Math.max(0, Math.floor(dropX / zoomScale));

      const audioClip = {
        id: `audioclip_${Date.now()}`,
        bar: dropBar,
        length: 8,
        title: file.name,
        color: '#ffc107',
        url,
        slipOffset: 0,
        muted: false
      };
      addPlaylistClip(trackId, audioClip);
    }
  };

  return (
    <div style={{
      background: 'rgba(12, 15, 20, 0.98)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderRadius: '8px',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* Top Header & Pro Tools Toolbar */}
      <div style={{
        padding: '6px 12px',
        borderBottom: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(20, 24, 30, 0.9)',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <LayoutGrid size={16} color={theme.colors.primary} />
          <h3 style={{ margin: 0, fontSize: '12px', color: '#fff', fontWeight: 'bold' }}>
            PLAYLIST ARRANGER
          </h3>
          <span style={{ fontSize: '10px', background: '#21262d', color: '#00f0ff', padding: '1px 6px', borderRadius: '3px', fontWeight: 'bold' }}>
            F5 TIMELINE
          </span>
        </div>

        {/* FL Studio Style Arrangement Tools Ribbon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#0a0d14', padding: '2px 6px', borderRadius: '4px', border: '1px solid #30363d' }}>
          {[
            { id: 'draw', key: 'P', icon: <Edit3 size={12} />, label: 'Draw' },
            { id: 'paint', key: 'B', icon: <Paintbrush size={12} />, label: 'Paint' },
            { id: 'slice', key: 'C', icon: <Scissors size={12} />, label: 'Slice' },
            { id: 'slip', key: 'S', icon: <MoveHorizontal size={12} />, label: 'Slip' },
            { id: 'mute', key: 'T', icon: <VolumeX size={12} />, label: 'Mute' },
            { id: 'delete', key: 'D', icon: <Trash2 size={12} />, label: 'Delete' }
          ].map(tool => (
            <button
              key={tool.id}
              onClick={() => setActiveTool(tool.id)}
              title={`${tool.label} Tool (${tool.key})`}
              style={{
                background: activeTool === tool.id ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                border: activeTool === tool.id ? '1px solid #00f0ff' : '1px solid transparent',
                color: activeTool === tool.id ? '#00f0ff' : '#888',
                borderRadius: '3px',
                padding: '3px 6px',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '3px'
              }}
            >
              {tool.icon} {tool.label} <span style={{ opacity: 0.6, fontSize: '8px' }}>({tool.key})</span>
            </button>
          ))}
        </div>

        {/* Snap & Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#000', padding: '2px 6px', borderRadius: '3px', border: '1px solid #30363d' }}>
            <span style={{ fontSize: '9px', color: '#888' }}>SNAP:</span>
            <select
              value={snapGrid}
              onChange={(e) => setSnapGrid(e.target.value)}
              style={{ background: 'transparent', border: 'none', color: '#00f0ff', fontSize: '10px', outline: 'none', cursor: 'pointer' }}
            >
              <option value="1_bar">1 Bar</option>
              <option value="1/2_beat">1/2 Beat</option>
              <option value="1/4_beat">1/4 Beat</option>
              <option value="none">None (Free)</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            <button
              onClick={() => setZoomScale(Math.max(32, zoomScale - 16))}
              title="Zoom Out Timeline"
              style={{ background: '#21262d', color: '#aaa', border: 'none', borderRadius: '3px', padding: '3px 6px', cursor: 'pointer' }}
            >
              <ZoomOut size={11} />
            </button>
            <button
              onClick={() => setZoomScale(Math.min(128, zoomScale + 16))}
              title="Zoom In Timeline"
              style={{ background: '#21262d', color: '#aaa', border: 'none', borderRadius: '3px', padding: '3px 6px', cursor: 'pointer' }}
            >
              <ZoomIn size={11} />
            </button>
          </div>

          <select
            value={totalBars}
            onChange={(e) => setTotalBars(Number(e.target.value))}
            style={{ background: '#161b22', border: '1px solid #30363d', color: '#fff', fontSize: '10px', padding: '2px 6px', borderRadius: '3px' }}
          >
            <option value="16">16 Bars</option>
            <option value="32">32 Bars</option>
            <option value="64">64 Bars</option>
            <option value="128">128 Bars</option>
          </select>

          {/* Quick Stehouwer Wave Studio Link */}
          <button
            onClick={() => setActiveView('wave_studio')}
            title="Open Stehouwer Multi-Track Linear Waveform Studio"
            style={{
              background: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid #38bdf8',
              color: '#38bdf8',
              borderRadius: '3px',
              padding: '3px 8px',
              fontSize: '10px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginLeft: 'auto'
            }}
          >
            🎙️ Wave Studio
          </button>
        </div>
      </div>

      {/* Main Arranger Timeline Canvas */}
      <div style={{ display: 'flex', flex: 1, overflow: 'auto', position: 'relative' }}>
        
        {/* Left Track Headers */}
        <div style={{
          width: '140px',
          borderRight: `1px solid ${theme.colors.border}`,
          background: '#0d1117',
          position: 'sticky',
          left: 0,
          zIndex: 5,
          flexShrink: 0
        }}>
          {/* Bar Ruler Corner */}
          <div style={{ height: '24px', borderBottom: '1px solid #30363d', background: '#161b22', padding: '4px 8px', fontSize: '9px', color: '#888', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>TRACKS</span>
            <span style={{ color: activeTool === 'slice' ? '#ff7b00' : '#00f0ff', fontSize: '8px' }}>
              [{activeTool.toUpperCase()}]
            </span>
          </div>

          {/* Video Tracks Section */}
          {videoTracks.map(track => (
            <div
              key={track.id}
              style={{
                height: '42px',
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
          {playlistTracks.map((track, tIdx) => (
            <div
              key={track.id}
              style={{
                height: '42px',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 8px',
                fontSize: '11px',
                color: '#ccc',
                fontWeight: '500',
                background: 'rgba(255,255,255,0.02)',
                borderLeft: '3px solid rgba(255, 255, 255, 0.2)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <Music2 size={11} style={{ marginRight: '6px', opacity: 0.7, flexShrink: 0 }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{track.name}</span>
              </div>
              <span style={{ fontSize: '9px', color: '#666' }}>A{tIdx + 1}</span>
            </div>
          ))}
        </div>

        {/* Right Timeline Grid */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: `${totalBars * zoomScale}px`,
          background: '#12161f',
          position: 'relative',
          cursor: activeTool === 'slice' ? 'col-resize' : activeTool === 'delete' ? 'not-allowed' : 'default'
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
                  width: `${zoomScale}px`,
                  borderRight: '1px solid rgba(255, 255, 255, 0.08)',
                  paddingLeft: '4px',
                  fontSize: '9px',
                  color: currentBar === barIdx && isPlaying ? theme.colors.accent : '#8b949e',
                  display: 'flex',
                  alignItems: 'center',
                  fontWeight: currentBar === barIdx && isPlaying ? 'bold' : 'normal',
                  userSelect: 'none'
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
                height: '42px',
                borderBottom: '1px solid rgba(0, 240, 255, 0.1)',
                position: 'relative',
                display: 'flex',
                background: 'rgba(0, 240, 255, 0.02)'
              }}
            >
              {Array.from({ length: totalBars }).map((_, b) => (
                <div key={b} style={{ width: `${zoomScale}px`, height: '100%', borderRight: '1px solid rgba(255, 255, 255, 0.04)' }} />
              ))}

              {track.clips.map((clip) => (
                <div
                  key={clip.id}
                  style={{
                    position: 'absolute',
                    left: `${clip.bar * zoomScale + 2}px`,
                    width: `${clip.length * zoomScale - 4}px`,
                    top: '3px',
                    height: '36px',
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

          {/* Audio Track Lanes (Interactive Drop & Slicing Targets) */}
          {playlistTracks.map(track => (
            <div
              key={track.id}
              onClick={(e) => handleLaneClick(track.id, e)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleTimelineDrop(track.id, e)}
              style={{
                height: '42px',
                borderBottom: '1px solid rgba(255,255,255,0.04)',
                position: 'relative',
                display: 'flex',
                background: 'rgba(255,255,255,0.01)'
              }}
            >
              {Array.from({ length: totalBars }).map((_, b) => (
                <div key={b} style={{ width: `${zoomScale}px`, height: '100%', borderRight: '1px solid rgba(255, 255, 255, 0.04)' }} />
              ))}

              {track.clips.map((clip) => {
                const isMuted = clip.muted;

                return (
                  <div
                    key={clip.id}
                    onClick={(e) => handleClipClick(track.id, clip, e)}
                    onDoubleClick={(e) => handleClipDoubleClick(clip, e)}
                    title={`[${clip.title}] Click with active tool: ${activeTool.toUpperCase()} (Double click for Channel Settings)`}
                    style={{
                      position: 'absolute',
                      left: `${clip.bar * zoomScale + 2}px`,
                      width: `${clip.length * zoomScale - 4}px`,
                      top: '3px',
                      height: '36px',
                      background: isMuted 
                        ? 'rgba(50, 50, 50, 0.5)' 
                        : `linear-gradient(135deg, ${clip.color || '#00f0ff'}33, ${clip.color || '#00f0ff'}11)`,
                      border: isMuted ? '1px solid #555' : `1px solid ${clip.color || '#00f0ff'}`,
                      borderRadius: '4px',
                      boxShadow: isMuted ? 'none' : `0 0 10px ${clip.color || '#00f0ff'}22`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0 6px',
                      fontSize: '10px',
                      fontWeight: 'bold',
                      color: isMuted ? '#888' : '#fff',
                      cursor: activeTool === 'slice' ? 'col-resize' : activeTool === 'slip' ? 'ew-resize' : 'grab',
                      zIndex: 2,
                      overflow: 'hidden',
                      whiteSpace: 'nowrap',
                      opacity: isMuted ? 0.5 : 1
                    }}
                  >
                    {/* Left: Waveform Icon & Title */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <span 
                        onClick={(e) => {
                          e.stopPropagation();
                          setClipMenuOpenId(clipMenuOpenId === clip.id ? null : clip.id);
                        }}
                        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                        title="Open Clip Menu (Make Unique, Edison, Settings)"
                      >
                        <Layers size={11} color={clip.color || '#00f0ff'} />
                      </span>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {clip.title || track.name}
                      </span>
                      {clip.slipOffset ? (
                        <span style={{ fontSize: '8px', color: '#ffaa00' }}>[Slip: +{clip.slipOffset}]</span>
                      ) : null}
                    </div>

                    {/* Clip Quick Action Trigger */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveEditingClip(clip);
                        setShowClipSettingsModal(true);
                      }}
                      style={{ background: 'transparent', border: 'none', color: '#aaa', cursor: 'pointer', padding: '2px' }}
                      title="Clip Settings"
                    >
                      <Sliders size={11} />
                    </button>

                    {/* Clip Dropdown Context Menu */}
                    {clipMenuOpenId === clip.id && (
                      <div 
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          position: 'absolute',
                          top: '36px',
                          left: '4px',
                          background: '#161b22',
                          border: '1px solid #30363d',
                          borderRadius: '6px',
                          padding: '4px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px',
                          zIndex: 99,
                          boxShadow: '0 10px 25px rgba(0,0,0,0.8)'
                        }}
                      >
                        <button
                          onClick={() => {
                            handleMakeUnique(clip);
                            setClipMenuOpenId(null);
                          }}
                          style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '10px', textAlign: 'left', padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Layers size={10} color="#00f0ff" /> Make Unique
                        </button>

                        <button
                          onClick={() => {
                            setActiveEditingClip(clip);
                            setShowClipSettingsModal(true);
                            setClipMenuOpenId(null);
                          }}
                          style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '10px', textAlign: 'left', padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Sliders size={10} color="#a855f7" /> Channel Settings
                        </button>

                        <button
                          onClick={() => {
                            setActiveEditingClip(clip);
                            setShowEdisonModal(true);
                            setClipMenuOpenId(null);
                          }}
                          style={{ background: 'transparent', border: 'none', color: '#ff7b00', fontSize: '10px', textAlign: 'left', padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Scissors size={10} /> Edit in Edison (Ctrl+E)
                        </button>

                        <button
                          onClick={() => {
                            setActiveEditingClip(clip);
                            setShowSlicexModal(true);
                            setClipMenuOpenId(null);
                          }}
                          style={{ background: 'transparent', border: 'none', color: '#00f0ff', fontSize: '10px', textAlign: 'left', padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Sparkles size={10} /> Slice in Slicex
                        </button>

                        <button
                          onClick={() => {
                            setPlaylistTracks(prev => prev.map(t => 
                              t.id === track.id ? { ...t, clips: t.clips.filter(c => c.id !== clip.id) } : t
                            ));
                            setClipMenuOpenId(null);
                          }}
                          style={{ background: 'transparent', border: 'none', color: '#ff5e5e', fontSize: '10px', textAlign: 'left', padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', borderTop: '1px solid #21262d' }}
                        >
                          <Trash2 size={10} /> Delete Clip
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}

          {/* Master Volume & Filter Automation Lane */}
          <div style={{
            height: '42px',
            borderBottom: '1px solid rgba(168, 85, 247, 0.2)',
            position: 'relative',
            display: 'flex',
            background: 'rgba(168, 85, 247, 0.03)'
          }}>
            {Array.from({ length: totalBars }).map((_, b) => (
              <div key={b} style={{ width: `${zoomScale}px`, height: '100%', borderRight: '1px solid rgba(255, 255, 255, 0.04)' }} />
            ))}

            {/* Automation Curve Visualization */}
            <svg style={{ position: 'absolute', top: 0, left: 0, width: `${totalBars * zoomScale}px`, height: '100%', pointerEvents: 'none' }}>
              <path
                d={`M 0 35 Q ${totalBars * (zoomScale / 4)} 5, ${totalBars * (zoomScale / 2)} 20 T ${totalBars * zoomScale} 10`}
                fill="none"
                stroke="#c084fc"
                strokeWidth="2"
                strokeDasharray="4 2"
              />
              <circle cx="0" cy="35" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
              <circle cx={`${totalBars * (zoomScale / 4)}`} cy="15" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
              <circle cx={`${totalBars * (zoomScale / 2)}`} cy="20" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
              <circle cx={`${totalBars * zoomScale}`} cy="10" r="4" fill="#a855f7" stroke="#fff" strokeWidth="1" />
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
                left: `${(currentBar * zoomScale) + (currentStep * (zoomScale / 16))}px`,
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

      {/* Edison Audio Editor Modal */}
      {showEdisonModal && (
        <EdisonAudioEditorModal
          clip={activeEditingClip}
          onClose={() => setShowEdisonModal(false)}
          onSendToPlaylist={handleEdisonSendToPlaylist}
        />
      )}

      {/* Slicex Transient Chopper Modal */}
      {showSlicexModal && (
        <SlicexChopperModal
          clip={activeEditingClip}
          onClose={() => setShowSlicexModal(false)}
          onDumpSlices={handleDumpSlices}
        />
      )}

      {/* Clip / Channel Settings Modal */}
      {showClipSettingsModal && (
        <ClipSettingsModal
          clip={activeEditingClip}
          onClose={() => setShowClipSettingsModal(false)}
          onUpdateClip={handleUpdateClip}
          onMakeUnique={handleMakeUnique}
          onOpenEdison={(clip) => {
            setActiveEditingClip(clip);
            setShowEdisonModal(true);
          }}
          onOpenSlicex={(clip) => {
            setActiveEditingClip(clip);
            setShowSlicexModal(true);
          }}
        />
      )}
    </div>
  );
}
