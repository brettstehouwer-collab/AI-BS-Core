import React, { useState, useEffect, useRef } from 'react';
import { theme } from '../../styles/theme';
import { 
  Folder, FileAudio, FileVideo, Image as ImageIcon, Database, Sparkles, 
  Volume2, Music, Disc, ArrowLeft, Loader, Search, X, Grid, List, 
  Maximize2, Minimize2, Plus, ChevronRight, HardDrive, RefreshCw
} from 'lucide-react';
import { useDawStore } from './dawStore';

const Browser = ({ 
  browserWidth = 320, 
  setBrowserWidth, 
  isExpanded = false, 
  onToggleExpand 
}) => {
  const [currentPath, setCurrentPath] = useState('/4 media');
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('list'); // 'list' | 'grid'
  const [activeAuditionPath, setActiveAuditionPath] = useState(null);
  const [backendBase, setBackendBase] = useState('http://127.0.0.1:8080');

  const previewNote = useDawStore(state => state.previewNote);
  const generateAIBeat = useDawStore(state => state.generateAIBeat);
  const addAudioChannel = useDawStore(state => state.addAudioChannel);
  const fileInputRef = useRef(null);
  const activeAudioRef = useRef(null);

  // Fetch Drive Files with Multi-Endpoint Fallback
  useEffect(() => {
    if (currentPath === '__suno_stems__') {
      setIsLoading(false);
      return;
    }

    const fetchDrive = async () => {
      setIsLoading(true);
      setError(null);

      const candidateHosts = [
        'http://127.0.0.1:8080',
        'http://localhost:8080',
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        ''
      ];

      let loaded = false;
      for (const host of candidateHosts) {
        try {
          const url = `${host}/api/drive/files?path=${encodeURIComponent(currentPath)}`;
          const res = await fetch(url);
          if (res.ok) {
            const data = await res.json();
            setItems(data.items || []);
            setBackendBase(host);
            loaded = true;
            break;
          }
        } catch (e) {
          // try next candidate host
        }
      }

      if (!loaded) {
        setError('Error loading drive. Ensure AI-BS backend is active.');
      }
      setIsLoading(false);
    };

    fetchDrive();
  }, [currentPath]);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const url = URL.createObjectURL(file);
      addAudioChannel(url, file.name);
    }
    if (fileInputRef.current) fileInputRef.current.value = null;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith('audio/')) {
      const url = URL.createObjectURL(file);
      addAudioChannel(url, file.name);
    }
  };

  const handleDragOver = (e) => e.preventDefault();

  const handleItemClick = (item) => {
    if (item.is_dir) {
      setCurrentPath(item.path);
      setSearchQuery('');
    } else {
      auditionSound(item, true);
    }
  };

  const auditionSound = (item, autoAdd = false) => {
    const previewUrl = item.path.startsWith('http') 
      ? item.path 
      : `${backendBase}/api/drive/stream?path=${encodeURIComponent(item.path)}`;

    if (item.category === 'audio' || item.extension === '.wav' || item.extension === '.mp3' || item.extension === '.ogg' || item.extension === '.flac') {
      try {
        if (activeAudioRef.current) {
          activeAudioRef.current.pause();
          activeAudioRef.current = null;
        }
        const audio = new Audio(previewUrl);
        activeAudioRef.current = audio;
        setActiveAuditionPath(item.path);
        audio.play().catch(e => console.warn(e));
        audio.onended = () => setActiveAuditionPath(null);

        if (autoAdd) {
          addAudioChannel(previewUrl, item.name);
        }
      } catch (err) {
        console.warn("Audio play failed:", err);
      }
    }
  };

  const handleDragStart = (e, item) => {
    if (item.is_dir) return;
    e.dataTransfer.setData('application/json', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const goUp = () => {
    if (currentPath === '/' || currentPath === '' || currentPath === '/4 media') {
      setCurrentPath('/4 media');
      return;
    }
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    setCurrentPath('/' + parts.join('/'));
  };

  // Breadcrumb segment navigation
  const renderBreadcrumbs = () => {
    if (currentPath === '__suno_stems__') return null;
    const parts = currentPath.split('/').filter(Boolean);

    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '4px',
        fontSize: '11px',
        color: '#94a3b8',
        background: 'rgba(0,0,0,0.3)',
        padding: '6px 8px',
        borderRadius: '4px',
        border: '1px solid rgba(255,255,255,0.06)',
        marginBottom: '8px'
      }}>
        <button
          onClick={() => setCurrentPath('/4 media')}
          style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', padding: 0, fontWeight: 'bold', fontSize: '11px' }}
        >
          Media
        </button>
        {parts.slice(1).map((part, idx) => {
          const subPath = '/' + parts.slice(0, idx + 2).join('/');
          const isLast = idx === parts.length - 2;
          return (
            <React.Fragment key={subPath}>
              <ChevronRight size={10} color="#64748b" />
              <button
                onClick={() => setCurrentPath(subPath)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isLast ? '#f8fafc' : '#94a3b8',
                  fontWeight: isLast ? 'bold' : 'normal',
                  cursor: isLast ? 'default' : 'pointer',
                  padding: 0,
                  fontSize: '11px',
                  maxWidth: '130px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
                title={part}
              >
                {part.replace(/_/g, ' ')}
              </button>
            </React.Fragment>
          );
        })}
      </div>
    );
  };

  // Filter items by search query
  const filteredItems = items.filter(item => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return item.name.toLowerCase().includes(q) || (item.category && item.category.toLowerCase().includes(q));
  });

  const handleBrowserWheel = (e) => {
    const target = e.target;
    const soundList = document.querySelector('.daw-browser-scroll');
    if (soundList && soundList.scrollHeight > soundList.clientHeight && target && soundList.contains(target)) {
      return;
    }
    const canvas = document.querySelector('.daw-center-canvas');
    if (canvas) {
      canvas.scrollTop += e.deltaY;
    }
  };

  return (
    <div 
      onWheel={handleBrowserWheel}
      style={{
        background: 'rgba(13, 17, 23, 0.98)',
        borderRight: `1px solid ${theme.colors.border}`,
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: '10px',
        overflow: 'hidden',
        boxSizing: 'border-box'
      }}
    >
      {/* Scrollbar Customization CSS */}
      <style>{`
        .daw-browser-scroll::-webkit-scrollbar {
          width: 5px;
        }
        .daw-browser-scroll::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.2);
        }
        .daw-browser-scroll::-webkit-scrollbar-thumb {
          background: #30363d;
          border-radius: 4px;
        }
        .daw-browser-scroll::-webkit-scrollbar-thumb:hover {
          background: #00f0ff;
        }
      `}</style>

      {/* Header: Title, Width Presets & Expand / View Toggle */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        marginBottom: '10px',
        paddingBottom: '8px',
        borderBottom: '1px solid rgba(255,255,255,0.06)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Database size={15} color={theme.colors.accent} />
          <h3 style={{ margin: 0, fontSize: '11px', color: '#fff', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 'bold' }}>
            SOUND VAULT
          </h3>
        </div>

        {/* Size & Layout Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {/* Width Presets */}
          {setBrowserWidth && (
            <div style={{ display: 'flex', gap: '2px', background: 'rgba(0,0,0,0.4)', padding: '2px', borderRadius: '4px', border: '1px solid #30363d' }}>
              <button
                onClick={() => setBrowserWidth(280)}
                style={{
                  background: browserWidth <= 280 ? 'rgba(0,240,255,0.2)' : 'transparent',
                  color: browserWidth <= 280 ? '#00f0ff' : '#888',
                  border: 'none',
                  borderRadius: '2px',
                  padding: '2px 5px',
                  fontSize: '9px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
                title="Compact Width (280px)"
              >
                S
              </button>
              <button
                onClick={() => setBrowserWidth(380)}
                style={{
                  background: browserWidth > 280 && browserWidth <= 420 ? 'rgba(0,240,255,0.2)' : 'transparent',
                  color: browserWidth > 280 && browserWidth <= 420 ? '#00f0ff' : '#888',
                  border: 'none',
                  borderRadius: '2px',
                  padding: '2px 5px',
                  fontSize: '9px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
                title="Medium Width (380px)"
              >
                M
              </button>
              <button
                onClick={() => setBrowserWidth(520)}
                style={{
                  background: browserWidth > 420 ? 'rgba(0,240,255,0.2)' : 'transparent',
                  color: browserWidth > 420 ? '#00f0ff' : '#888',
                  border: 'none',
                  borderRadius: '2px',
                  padding: '2px 5px',
                  fontSize: '9px',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
                title="Wide Grid Width (520px)"
              >
                L
              </button>
            </div>
          )}

          {/* List / Grid Toggle */}
          <div style={{ display: 'flex', gap: '2px', background: 'rgba(0,0,0,0.4)', padding: '2px', borderRadius: '4px', border: '1px solid #30363d' }}>
            <button
              onClick={() => setViewMode('list')}
              style={{
                background: viewMode === 'list' ? 'rgba(0,240,255,0.2)' : 'transparent',
                color: viewMode === 'list' ? '#00f0ff' : '#888',
                border: 'none',
                borderRadius: '2px',
                padding: '3px 5px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
              title="List View"
            >
              <List size={11} />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              style={{
                background: viewMode === 'grid' ? 'rgba(0,240,255,0.2)' : 'transparent',
                color: viewMode === 'grid' ? '#00f0ff' : '#888',
                border: 'none',
                borderRadius: '2px',
                padding: '3px 5px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
              title="Grid View"
            >
              <Grid size={11} />
            </button>
          </div>

          {/* 1-Click Expand / Collapse Toggle */}
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              style={{
                background: isExpanded ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255,255,255,0.05)',
                border: isExpanded ? '1px solid #00f0ff' : '1px solid #30363d',
                color: isExpanded ? '#00f0ff' : '#888',
                borderRadius: '4px',
                padding: '3px 6px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                fontSize: '10px'
              }}
              title={isExpanded ? "Collapse Browser" : "Expand Browser"}
            >
              {isExpanded ? <Minimize2 size={11} /> : <Maximize2 size={11} />}
            </button>
          )}
        </div>
      </div>

      {/* 🎯 CYMATICS 100GB DROP SNIPER STATUS BADGE */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(245, 158, 11, 0.05))',
        border: '1px solid #f59e0b',
        borderRadius: '6px',
        padding: '6px 8px',
        marginBottom: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: '10px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }} />
          <div>
            <div style={{ fontWeight: 'bold', color: '#fbbf24', fontSize: '10px' }}>100GB DROP SNIPER: ACTIVE</div>
            <div style={{ color: '#94a3b8', fontSize: '9px' }}>Scanning cymatics-c86v every 3s</div>
          </div>
        </div>
        <a 
          href="https://cymatics.fm/pages/cymatics-c86v" 
          target="_blank" 
          rel="noopener noreferrer"
          style={{
            background: '#f59e0b',
            color: '#000',
            fontWeight: 'bold',
            padding: '3px 8px',
            borderRadius: '4px',
            textDecoration: 'none',
            fontSize: '9px',
            display: 'flex',
            alignItems: 'center',
            gap: '3px'
          }}
        >
          <span>OPEN</span>
        </a>
      </div>

      {/* Vertical & Multi-Column Library Navigation Buttons (No Horizontal Scrollbar) */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: browserWidth > 360 ? '1fr 1fr' : '1fr', 
        gap: '5px', 
        marginBottom: '10px' 
      }}>
        <button
          onClick={() => { setCurrentPath('/4 media'); setSearchQuery(''); }}
          style={{
            padding: '6px 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            background: currentPath === '/4 media' ? 'linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(0, 240, 255, 0.05))' : 'rgba(255,255,255,0.03)',
            color: currentPath === '/4 media' ? '#00f0ff' : '#cbd5e1',
            border: currentPath === '/4 media' ? '1px solid #00f0ff' : '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            textAlign: 'left'
          }}
        >
          <Folder size={12} color="#00f0ff" />
          <span>📁 All Media</span>
        </button>

        <button
          onClick={() => { setCurrentPath('/4 media/Cymatics_Sound_Banks'); setSearchQuery(''); }}
          style={{
            padding: '6px 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            background: currentPath.includes('Cymatics') ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(16, 185, 129, 0.05))' : 'rgba(255,255,255,0.03)',
            color: currentPath.includes('Cymatics') ? '#34d399' : '#cbd5e1',
            border: currentPath.includes('Cymatics') ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            textAlign: 'left'
          }}
        >
          <HardDrive size={12} color="#10b981" />
          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>🌊 Cymatics (31 Banks)</span>
        </button>

        <button
          onClick={() => { setCurrentPath('/4 media/Muse_Hub_Instruments'); setSearchQuery(''); }}
          style={{
            padding: '6px 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            background: currentPath.includes('Muse_Hub') ? 'linear-gradient(135deg, rgba(234, 179, 8, 0.25), rgba(234, 179, 8, 0.05))' : 'rgba(255,255,255,0.03)',
            color: currentPath.includes('Muse_Hub') ? '#fbbf24' : '#cbd5e1',
            border: currentPath.includes('Muse_Hub') ? '1px solid #eab308' : '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            textAlign: 'left'
          }}
        >
          <Music size={12} color="#fbbf24" />
          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>🎻 Muse Hub (15GB)</span>
        </button>

        <button
          onClick={() => { setCurrentPath('__suno_stems__'); setSearchQuery(''); }}
          style={{
            padding: '6px 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            background: currentPath === '__suno_stems__' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.25), rgba(168, 85, 247, 0.05))' : 'rgba(255,255,255,0.03)',
            color: currentPath === '__suno_stems__' ? '#c084fc' : '#cbd5e1',
            border: currentPath === '__suno_stems__' ? '1px solid #a855f7' : '1px solid rgba(255,255,255,0.06)',
            borderRadius: '4px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            textAlign: 'left'
          }}
        >
          <Sparkles size={12} color="#c084fc" />
          <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>🧠 Suno & Stems</span>
        </button>
      </div>

      {/* Instant Real-Time Search Bar */}
      {currentPath !== '__suno_stems__' && (
        <div style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          marginBottom: '8px'
        }}>
          <Search size={13} color="#64748b" style={{ position: 'absolute', left: '8px' }} />
          <input
            type="text"
            placeholder={`Filter ${items.length ? `${items.length} items` : 'sounds'}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              background: '#090d13',
              border: '1px solid #30363d',
              borderRadius: '4px',
              padding: '6px 26px 6px 26px',
              fontSize: '11px',
              color: '#f8fafc',
              outline: 'none',
              boxSizing: 'border-box'
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: '6px',
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>
      )}

      {/* SUNO & STEM SPLITTER VIEW */}
      {currentPath === '__suno_stems__' ? (
        <div className="daw-browser-scroll" style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {/* Suno Structure Generator Card */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(59, 130, 246, 0.1))',
            border: '1px solid #a855f766',
            borderRadius: '6px',
            padding: '10px'
          }}>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#c084fc', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <Sparkles size={13} /> Suno AI Prompt Composer
            </div>
            <div style={{ fontSize: '9px', color: '#94a3b8', marginBottom: '8px' }}>
              Generates high-fidelity structural brackets & lyric schemas.
            </div>
            <button
              onClick={async () => {
                try {
                  const res = await fetch(`${backendBase}/api/audio/suno/structure`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ genre: 'Cyberpunk Darksynth', theme: 'Matrix Escape', tempo: 138, vocal_style: 'Gritty Vocoder' })
                  });
                  if (res.ok) {
                    const data = await res.json();
                    alert(`[Suno Prompt Created!]\n\nStyle Tags: ${data.style_tags}\nSuggested Key: ${data.suggested_key}\n\nLyrics copied to clipboard!`);
                    if (navigator.clipboard) navigator.clipboard.writeText(data.lyrics);
                  }
                } catch (e) {
                  console.error(e);
                }
              }}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                padding: '6px',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              Compose & Copy Suno Schema
            </button>
          </div>

          {/* 4-Stem Audio Separator Card */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1))',
            border: '1px solid #10b98166',
            borderRadius: '6px',
            padding: '10px'
          }}>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <Disc size={13} /> Local 4-Stem Separator
            </div>
            <div style={{ fontSize: '9px', color: '#94a3b8', marginBottom: '8px' }}>
              Decomposes active track into Vocals, Drums, Bass, and Other.
            </div>
            <button
              onClick={async () => {
                try {
                  const res = await fetch(`${backendBase}/api/audio/stems/split`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ audio_path: 'Current_Master_Render.wav' })
                  });
                  if (res.ok) {
                    const data = await res.json();
                    data.stems.forEach(stem => {
                      addAudioChannel(stem.url, `[STEM] ${stem.name}`);
                    });
                    alert(`[SUCCESS] 4 Stems decomposed and loaded into DAW Playlist!`);
                  }
                } catch (e) {
                  console.error(e);
                }
              }}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #059669, #10b981)',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                padding: '6px',
                fontSize: '10px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              Split & Load 4 Stems
            </button>
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          
          {/* Breadcrumb Path & Navigation Bar */}
          {renderBreadcrumbs()}

          {/* Up One Level Button & Header Action */}
          {currentPath !== '/' && currentPath !== '' && currentPath !== '/4 media' && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <button 
                onClick={goUp}
                style={{ 
                  background: 'rgba(0, 240, 255, 0.1)', 
                  border: '1px solid rgba(0, 240, 255, 0.3)', 
                  color: '#00f0ff', 
                  cursor: 'pointer', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '4px', 
                  fontSize: '10px',
                  fontWeight: 'bold',
                  padding: '4px 8px',
                  borderRadius: '4px'
                }}
              >
                <ArrowLeft size={11} /> UP ONE LEVEL
              </button>

              <span style={{ fontSize: '10px', color: '#64748b' }}>
                {filteredItems.length} {filteredItems.length === 1 ? 'item' : 'items'}
              </span>
            </div>
          )}

          {/* AI Beat Assistant Box (Compact) */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.08), rgba(122, 40, 138, 0.12))',
            border: `1px solid rgba(0, 240, 255, 0.3)`,
            borderRadius: '4px',
            padding: '6px 8px',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Sparkles size={12} color={theme.colors.accent} />
              <span style={{ fontSize: '10px', fontWeight: 'bold', color: '#fff' }}>Quick Beat:</span>
            </div>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                onClick={() => generateAIBeat('trap')}
                style={{
                  background: 'rgba(0, 255, 255, 0.15)',
                  border: `1px solid ${theme.colors.accent}`,
                  borderRadius: '3px',
                  color: theme.colors.accent,
                  padding: '2px 6px',
                  fontSize: '9px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                Trap 808
              </button>
              <button
                onClick={() => generateAIBeat('synthwave')}
                style={{
                  background: 'rgba(255, 0, 127, 0.15)',
                  border: '1px solid #ff007f',
                  borderRadius: '3px',
                  color: '#ff007f',
                  padding: '2px 6px',
                  fontSize: '9px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                Synthwave
              </button>
            </div>
          </div>

          {/* Main Items Listing (Vertical Scroll Only - Zero Horizontal Scroll) */}
          <div 
            className="daw-browser-scroll" 
            style={{ 
              flex: 1, 
              overflowY: 'auto', 
              overflowX: 'hidden', 
              paddingRight: '2px' 
            }}
          >
            {isLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '140px', gap: '8px', color: '#64748b' }}>
                <Loader size={20} className="animate-spin" color="#00f0ff" />
                <span style={{ fontSize: '11px' }}>Loading sound vault...</span>
              </div>
            ) : error ? (
              <div style={{ 
                color: '#f87171', 
                fontSize: '11px', 
                padding: '12px', 
                background: 'rgba(239, 68, 68, 0.1)', 
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '6px',
                textAlign: 'center'
              }}>
                <div>{error}</div>
                <button
                  onClick={() => setCurrentPath(currentPath)}
                  style={{
                    marginTop: '8px',
                    background: '#ef4444',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 10px',
                    fontSize: '10px',
                    cursor: 'pointer',
                    fontWeight: 'bold'
                  }}
                >
                  Retry Connection
                </button>
              </div>
            ) : filteredItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 10px', color: '#64748b', fontSize: '11px' }}>
                {searchQuery ? `No items matching "${searchQuery}"` : 'No sound banks or files in this directory.'}
              </div>
            ) : viewMode === 'grid' ? (
              /* GRID VIEW (2-column cards) */
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: browserWidth > 380 ? 'repeat(auto-fill, minmax(130px, 1fr))' : '1fr 1fr', 
                gap: '6px', 
                paddingBottom: '8px' 
              }}>
                {filteredItems.map(item => (
                  <div
                    key={item.id}
                    onClick={() => handleItemClick(item)}
                    draggable={!item.is_dir}
                    onDragStart={(e) => handleDragStart(e, item)}
                    title={item.is_dir ? `Open ${item.name}` : `Audition / Drag ${item.name}`}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '10px 6px',
                      borderRadius: '6px',
                      background: activeAuditionPath === item.path ? 'rgba(0, 240, 255, 0.18)' : 'rgba(255, 255, 255, 0.03)',
                      border: activeAuditionPath === item.path ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.06)',
                      cursor: item.is_dir ? 'pointer' : 'grab',
                      color: '#cbd5e1',
                      fontSize: '11px',
                      textAlign: 'center',
                      transition: 'all 0.15s ease',
                      position: 'relative'
                    }}
                    onMouseOver={e => {
                      if (activeAuditionPath !== item.path) e.currentTarget.style.background = 'rgba(0, 240, 255, 0.08)';
                    }}
                    onMouseOut={e => {
                      if (activeAuditionPath !== item.path) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                    }}
                  >
                    <div style={{ marginBottom: '5px' }}>
                      {item.is_dir ? (
                        <Folder size={22} color="#fbbf24" />
                      ) : (
                        <FileAudio size={22} color="#38bdf8" />
                      )}
                    </div>
                    <span style={{ 
                      fontSize: '10px', 
                      fontWeight: '500',
                      width: '100%', 
                      whiteSpace: 'nowrap', 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis',
                      color: item.is_dir ? '#f8fafc' : '#38bdf8'
                    }}>
                      {item.name}
                    </span>
                    {!item.is_dir && (
                      <span style={{ fontSize: '8px', color: '#64748b', marginTop: '2px' }}>
                        {item.size_formatted || 'Audio'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              /* LIST VIEW (Vertical dense rows) */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', paddingBottom: '8px' }}>
                {filteredItems.map(item => (
                  <div
                    key={item.id}
                    onClick={() => handleItemClick(item)}
                    draggable={!item.is_dir}
                    onDragStart={(e) => handleDragStart(e, item)}
                    title={item.is_dir ? `Open ${item.name}` : `Drag to timeline or click to preview`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 8px',
                      borderRadius: '4px',
                      background: activeAuditionPath === item.path ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                      border: activeAuditionPath === item.path ? '1px solid #00f0ff' : '1px solid rgba(255, 255, 255, 0.04)',
                      cursor: item.is_dir ? 'pointer' : 'grab',
                      color: '#cbd5e1',
                      fontSize: '11px',
                      transition: 'all 0.12s ease'
                    }}
                    onMouseOver={e => {
                      if (activeAuditionPath !== item.path) e.currentTarget.style.background = 'rgba(0, 240, 255, 0.08)';
                    }}
                    onMouseOut={e => {
                      if (activeAuditionPath !== item.path) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', minWidth: 0, flex: 1 }}>
                      {item.is_dir ? (
                        <Folder size={14} color="#fbbf24" style={{ flexShrink: 0 }} />
                      ) : item.category === 'audio' ? (
                        <FileAudio size={14} color="#38bdf8" style={{ flexShrink: 0 }} />
                      ) : item.category === 'video' ? (
                        <FileVideo size={14} color="#f97316" style={{ flexShrink: 0 }} />
                      ) : item.category === 'image' ? (
                        <ImageIcon size={14} color="#06b6d4" style={{ flexShrink: 0 }} />
                      ) : (
                        <Disc size={14} color="#64748b" style={{ flexShrink: 0 }} />
                      )}
                      <span style={{ 
                        whiteSpace: 'nowrap', 
                        overflow: 'hidden', 
                        textOverflow: 'ellipsis', 
                        fontSize: '11px',
                        color: item.is_dir ? '#f8fafc' : '#e2e8f0',
                        fontWeight: item.is_dir ? '600' : '400'
                      }}>
                        {item.name}
                      </span>
                    </div>

                    {!item.is_dir && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px', flexShrink: 0 }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            auditionSound(item, false);
                          }}
                          style={{
                            background: activeAuditionPath === item.path ? '#00f0ff' : 'transparent',
                            color: activeAuditionPath === item.path ? '#000' : '#94a3b8',
                            border: 'none',
                            borderRadius: '3px',
                            padding: '2px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center'
                          }}
                          title="Audition Preview"
                        >
                          <Volume2 size={12} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const previewUrl = item.path.startsWith('http') 
                              ? item.path 
                              : `${backendBase}/api/drive/stream?path=${encodeURIComponent(item.path)}`;
                            addAudioChannel(previewUrl, item.name);
                          }}
                          style={{
                            background: 'rgba(56, 189, 248, 0.15)',
                            color: '#38bdf8',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            borderRadius: '3px',
                            padding: '2px 4px',
                            cursor: 'pointer',
                            fontSize: '9px',
                            fontWeight: 'bold',
                            display: 'flex',
                            alignItems: 'center'
                          }}
                          title="Add to Channel Rack"
                        >
                          <Plus size={10} /> ADD
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upload & Import Drop Zone */}
      <div 
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
        style={{
          marginTop: '8px',
          padding: '6px',
          background: 'rgba(255,255,255,0.02)',
          border: '1px dashed rgba(255,255,255,0.12)',
          borderRadius: '4px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
          flexShrink: 0
        }}
        onMouseOver={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
        onMouseOut={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
      >
        <input 
          type="file" 
          accept="audio/*" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={handleFileUpload} 
        />
        <div style={{ fontSize: '9px', color: '#64748b' }}>Drag & Drop Audio Files</div>
        <div style={{ fontSize: '10px', color: theme.colors.accent, fontWeight: 'bold' }}>+ Import WAV / MP3</div>
      </div>
    </div>
  );
};

export default Browser;
