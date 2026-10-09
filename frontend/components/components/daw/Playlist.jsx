import React, { useState, useEffect, useRef } from 'react';
import { theme } from '../../styles/theme';
import { 
  LayoutGrid, Layers, Film, Video, Plus, Music2, Scissors, 
  MoveHorizontal, VolumeX, Trash2, Edit3, Paintbrush, ZoomIn, 
  ZoomOut, Sparkles, MoreVertical, Sliders, Check,
  UploadCloud, Play, Square, HardDrive, RefreshCw
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
  const addStemTracksToPlaylist = useDawStore(state => state.addStemTracksToPlaylist);

  // AI Stem Ingestion & Drag-Drop State
  const [showStemDrawer, setShowStemDrawer] = useState(false);
  const [isDragOverArranger, setIsDragOverArranger] = useState(false);
  const [isDragOverStemBox, setIsDragOverStemBox] = useState(false);
  const [isStemExtracting, setIsStemExtracting] = useState(false);
  const [stemProgress, setStemProgress] = useState(0);
  const [stemStatusMsg, setStemStatusMsg] = useState('Demucs v4 CUDA Engine Ready on RTX 4090');
  const [auditioningClipId, setAuditioningClipId] = useState(null);
  const stemFileInputRef = useRef(null);
  const auditionAudioRef = useRef(null);
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

  // Audition clip audio directly from timeline
  const handleAuditionClip = (clip) => {
    const url = clip.audioUrl || clip.url;
    if (!url) return;
    if (auditioningClipId === clip.id) {
      if (auditionAudioRef.current) {
        auditionAudioRef.current.pause();
        auditionAudioRef.current = null;
      }
      setAuditioningClipId(null);
      return;
    }

    if (auditionAudioRef.current) {
      auditionAudioRef.current.pause();
    }
    const audio = new Audio(url);
    auditionAudioRef.current = audio;
    setAuditioningClipId(clip.id);
    audio.play().catch(e => console.warn('Audition error:', e));
    audio.onended = () => {
      setAuditioningClipId(null);
      auditionAudioRef.current = null;
    };
  };

  // Upload and isolate stems directly from the Arranger Playlist
  const handleUploadAndSeparateInArranger = async (file) => {
    if (!file) return;
    setIsStemExtracting(true);
    setStemProgress(10);
    setShowStemDrawer(true);
    setStemStatusMsg(`Uploading "${file.name}" to RTX 4090 CUDA Demucs Engine...`);

    const progressInterval = setInterval(() => {
      setStemProgress(prev => (prev < 90 ? prev + 15 : prev));
    }, 500);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model_name', 'htdemucs');

      const res = await fetch('http://127.0.0.1:8080/api/v1/audio/demucs/upload_and_separate', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);
      setStemProgress(100);

      if (res.ok) {
        const data = await res.json();
        setStemStatusMsg(`✨ Separation Complete! All stems arranged into tracks for ${data.project_name || file.name}`);
        
        if (data.stems) {
          const stemColors = {
            vocals: '#00f0ff',
            drums: '#10b981',
            bass: '#f59e0b',
            other: '#a855f7',
            master_repaired: '#f43f5e'
          };
          const stemLabels = {
            vocals: 'Vocals',
            drums: 'Drums',
            bass: 'Bassline',
            other: 'Instruments / Synths',
            master_repaired: 'Master Repaired'
          };

          const stemTracksToAdd = Object.entries(data.stems).map(([key, stem]) => ({
            name: stemLabels[key] || key.toUpperCase(),
            url: stem.url ? `http://127.0.0.1:8080${stem.url}` : '',
            color: stemColors[key] || '#00f0ff',
            length: 32
          }));

          addStemTracksToPlaylist(stemTracksToAdd, data.project_name || file.name.replace(/\.[^/.]+$/, ''));
        }
      } else {
        const err = await res.json().catch(() => ({}));
        setStemStatusMsg(`⚠️ Demucs Error: ${err.detail || 'Backend error'}`);
      }
    } catch (err) {
      clearInterval(progressInterval);
      setStemStatusMsg(`⚠️ Error connecting to Demucs backend: ${err.message}`);
    } finally {
      setIsStemExtracting(false);
      setTimeout(() => {
        setStemProgress(0);
      }, 4000);
    }
  };

  // Quick 1-click Insert October 7v2 Remastered Stems into Arranger
  const handleInsertOctoberStems = () => {
    const octoberStems = [
      { name: 'Vocals', url: 'http://127.0.0.1:8080/api/v1/audio/demucs/file/october_7v2_remastered/vocals.wav', color: '#00f0ff', length: 32 },
      { name: 'Drums', url: 'http://127.0.0.1:8080/api/v1/audio/demucs/file/october_7v2_remastered/drums.wav', color: '#10b981', length: 32 },
      { name: 'Bassline', url: 'http://127.0.0.1:8080/api/v1/audio/demucs/file/october_7v2_remastered/bass.wav', color: '#f59e0b', length: 32 },
      { name: 'Instruments / Synths', url: 'http://127.0.0.1:8080/api/v1/audio/demucs/file/october_7v2_remastered/other.wav', color: '#a855f7', length: 32 },
      { name: 'Repaired Master (Auto-Tune Harmonic Fix)', url: 'http://127.0.0.1:8080/api/v1/audio/demucs/file/october_7v2_remastered/October_7v2_Master_Repaired.wav', color: '#f43f5e', length: 32 }
    ];
    addStemTracksToPlaylist(octoberStems, 'October 7v2 Remastered');
    setStemStatusMsg('✨ Inserted all 5 October 7v2 stems directly into Arranger Playlist tracks!');
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
    <div 
      onDragOver={(e) => {
        e.preventDefault();
        if (e.dataTransfer.types && Array.from(e.dataTransfer.types).includes('Files')) {
          setIsDragOverArranger(true);
        }
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
          setIsDragOverArranger(false);
        }
      }}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragOverArranger(false);
        const file = e.dataTransfer.files?.[0];
        if (file && (file.type.startsWith('audio/') || /\.(mp3|wav|flac|ogg|m4a)$/i.test(file.name))) {
          handleUploadAndSeparateInArranger(file);
        }
      }}
      style={{
        background: 'rgba(12, 15, 20, 0.98)',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '8px',
        overflow: 'hidden',
        position: 'relative'
      }}
    >
      {/* Global Drag-and-Drop Stem Overlay */}
      {isDragOverArranger && (
        <div
          onDragLeave={() => setIsDragOverArranger(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOverArranger(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleUploadAndSeparateInArranger(file);
          }}
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(5, 10, 20, 0.92)',
            zIndex: 100,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            border: '3px dashed #00f0ff',
            boxShadow: 'inset 0 0 50px rgba(0, 240, 255, 0.35)',
            backdropFilter: 'blur(5px)'
          }}
        >
          <Sparkles size={52} color="#00f0ff" />
          <h2 style={{ color: '#fff', fontSize: '18px', fontWeight: 'bold', marginTop: '14px', letterSpacing: '0.5px' }}>
            DROP AUDIO TO STEM OUT ONTO ARRANGER TRACKS
          </h2>
          <p style={{ color: '#00f0ff', fontSize: '13px', margin: '6px 0', fontWeight: '500' }}>
            Local Demucs v4 on NVIDIA RTX 4090 will isolate Vocals, Drums, Bass & Instruments into discrete Arranger lanes!
          </p>
          <span style={{ fontSize: '11px', color: '#888' }}>
            Supports .mp3, .wav, .flac, .ogg, .m4a
          </span>
        </div>
      )}
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

        {/* Pattern DAW Style Arrangement Tools Ribbon */}
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

          {/* Quick AI Stem Ingestion Drawer Button */}
          <button
            onClick={() => setShowStemDrawer(prev => !prev)}
            title="Open Drag & Drop AI Stem Extractor (Demucs v4 CUDA on RTX 4090)"
            style={{
              background: showStemDrawer ? 'rgba(0, 240, 255, 0.25)' : 'rgba(0, 240, 255, 0.12)',
              border: '1px solid #00f0ff',
              color: '#00f0ff',
              borderRadius: '3px',
              padding: '3px 8px',
              fontSize: '10px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: showStemDrawer ? '0 0 10px rgba(0, 240, 255, 0.3)' : 'none'
            }}
          >
            <Sparkles size={11} color="#00f0ff" />
            🎛️ Stem Ingestion
          </button>
        </div>
      </div>

      {/* AI Stem Ingestion Drawer */}
      {showStemDrawer && (
        <div style={{
          background: 'linear-gradient(180deg, rgba(13, 17, 23, 0.98), rgba(22, 27, 34, 0.98))',
          borderBottom: '1px solid #30363d',
          padding: '10px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          boxShadow: 'inset 0 -2px 10px rgba(0,0,0,0.5)',
          zIndex: 20
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={14} color="#00f0ff" />
              <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#fff' }}>
                AI STEM EXTRACTOR & MULTI-TRACK ARRANGER
              </span>
              <span style={{ fontSize: '9px', background: 'rgba(0, 240, 255, 0.15)', color: '#00f0ff', padding: '1px 6px', borderRadius: '3px', border: '1px solid rgba(0, 240, 255, 0.3)' }}>
                RTX 4090 CUDA (Demucs v4)
              </span>
            </div>
            <button
              onClick={() => setShowStemDrawer(false)}
              style={{ background: 'transparent', border: 'none', color: '#888', cursor: 'pointer', fontSize: '13px', padding: '2px 6px' }}
              title="Close Drawer"
            >
              ✕
            </button>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'stretch', flexWrap: 'wrap' }}>
            {/* Drag & Drop Box */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOverStemBox(true); }}
              onDragLeave={() => setIsDragOverStemBox(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOverStemBox(false);
                const file = e.dataTransfer.files?.[0];
                if (file) handleUploadAndSeparateInArranger(file);
              }}
              onClick={() => !isStemExtracting && stemFileInputRef.current?.click()}
              style={{
                flex: '1 1 360px',
                border: isDragOverStemBox ? '2px dashed #00f0ff' : '1px dashed #444c56',
                background: isDragOverStemBox ? 'rgba(0, 240, 255, 0.1)' : 'rgba(10, 13, 18, 0.7)',
                borderRadius: '6px',
                padding: '12px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: '6px',
                cursor: isStemExtracting ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <input
                ref={stemFileInputRef}
                type="file"
                accept="audio/*,.mp3,.wav,.flac,.ogg,.m4a"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUploadAndSeparateInArranger(file);
                }}
              />
              {isStemExtracting ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', width: '100%', maxWidth: '320px' }}>
                  <span style={{ fontSize: '11px', color: '#00f0ff', fontWeight: 'bold' }}>
                    ⚡ Isolating Stems on RTX 4090... ({stemProgress}%)
                  </span>
                  <div style={{ width: '100%', height: '5px', background: '#21262d', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${stemProgress}%`, height: '100%', background: 'linear-gradient(90deg, #00f0ff, #a855f7)', transition: 'width 0.25s ease' }} />
                  </div>
                  <span style={{ fontSize: '9px', color: '#888' }}>
                    Splitting Vocals, Drums, Bass, Instruments directly into Arranger Tracks...
                  </span>
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <UploadCloud size={16} color="#00f0ff" />
                    <span style={{ fontSize: '11px', color: '#fff', fontWeight: 'bold' }}>
                      Drag & Drop Audio File to Stem Out
                    </span>
                  </div>
                  <span style={{ fontSize: '9px', color: '#888' }}>
                    Drop .mp3, .wav, or .flac to isolate and automatically layout onto Arranger tracks
                  </span>
                </>
              )}
            </div>

            {/* Quick Insert from Vault Card */}
            <div style={{
              flex: '0 0 320px',
              background: 'rgba(10, 13, 18, 0.7)',
              borderRadius: '6px',
              border: '1px solid #30363d',
              padding: '10px 14px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '6px'
            }}>
              <div>
                <div style={{ fontSize: '10px', color: '#888', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between' }}>
                  <span>RECENT VAULT STEMS</span>
                  <span style={{ color: '#56d364' }}>● Ready</span>
                </div>
                <div style={{ fontSize: '11px', color: '#f0f6fc', fontWeight: 600, marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  October 7v2 (Add Vocal) (Remastered)
                </div>
                <div style={{ fontSize: '9px', color: '#8b949e' }}>
                  Includes 4 Stems + Repaired Master Track
                </div>
              </div>
              <button
                onClick={handleInsertOctoberStems}
                style={{
                  background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(168, 85, 247, 0.2))',
                  border: '1px solid #00f0ff',
                  color: '#00f0ff',
                  borderRadius: '4px',
                  padding: '5px 10px',
                  fontSize: '10px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <Plus size={11} /> ➕ Insert All 5 Stems into Arranger Tracks
              </button>
            </div>
          </div>

          {stemStatusMsg && (
            <div style={{ fontSize: '10px', color: stemStatusMsg.includes('⚠️') ? '#ff7b72' : '#8b949e', marginTop: '2px' }}>
              {stemStatusMsg}
            </div>
          )}
        </div>
      )}

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

                    {/* Right: Audition Play + Clip Quick Action Trigger */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                      {(clip.audioUrl || clip.url) && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAuditionClip(clip);
                          }}
                          style={{
                            background: auditioningClipId === clip.id ? '#5eff7b' : 'rgba(255,255,255,0.1)',
                            border: 'none',
                            color: auditioningClipId === clip.id ? '#000' : '#fff',
                            borderRadius: '2px',
                            cursor: 'pointer',
                            padding: '2px 4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}
                          title={auditioningClipId === clip.id ? "Stop Audition" : "Audition Stem Audio"}
                        >
                          {auditioningClipId === clip.id ? <Square size={9} fill="#000" /> : <Play size={9} fill="#fff" />}
                        </button>
                      )}
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
                    </div>

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

                        {(clip.audioUrl || clip.url) && (
                          <button
                            onClick={() => {
                              fetch(clip.audioUrl || clip.url)
                                .then(res => res.blob())
                                .then(blob => {
                                  const file = new File([blob], `${clip.title || 'audio'}.wav`, { type: 'audio/wav' });
                                  handleUploadAndSeparateInArranger(file);
                                })
                                .catch(err => console.warn('Could not extract from clip blob:', err));
                              setClipMenuOpenId(null);
                            }}
                            style={{ background: 'transparent', border: 'none', color: '#00f0ff', fontSize: '10px', textAlign: 'left', padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                          >
                            <Sparkles size={10} color="#00f0ff" /> Demucs Stem Split into Tracks
                          </button>
                        )}

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
