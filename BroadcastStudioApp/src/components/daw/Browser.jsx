import React, { useState, useEffect, useRef } from 'react';
import { theme } from '../../styles/theme';
import { 
  Folder, FileAudio, FileVideo, Image as ImageIcon, Database, Sparkles, 
  Volume2, Music, Disc, ArrowLeft, Loader, Search, X, Grid, List, 
  Maximize2, Minimize2, Plus, ChevronRight, HardDrive, RefreshCw,
  SlidersHorizontal, Zap, Play, Square, Filter
} from 'lucide-react';
import { useDawStore } from './dawStore';

const CATEGORIES = [
  'All',
  'Melody Loop',
  'Drum / Percussion',
  '808 / Bass',
  'Guitar',
  'Vocal',
  'MIDI',
  'One-Shot',
  'FX / Atmosphere',
  'Stem'
];

const MUSICAL_KEYS = [
  'All', 'C Maj', 'C Min', 'C# Maj', 'C# Min', 'D Maj', 'D Min', 'D# Maj', 'D# Min',
  'E Maj', 'E Min', 'F Maj', 'F Min', 'F# Maj', 'F# Min', 'G Maj', 'G Min',
  'G# Maj', 'G# Min', 'A Maj', 'A Min', 'A# Maj', 'A# Min', 'B Maj', 'B Min'
];

const Browser = ({ 
  browserWidth = 340, 
  setBrowserWidth, 
  isExpanded = false, 
  onToggleExpand 
}) => {
  // Modes: 'catalog' (100K Fast Search) | 'drive' (Folder Vault)
  const [activeTab, setActiveTab] = useState('catalog');
  
  // Catalog Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedKey, setSelectedKey] = useState('All');
  const [bpmMin, setBpmMin] = useState(60);
  const [bpmMax, setBpmMax] = useState(180);
  const [enableBpmFilter, setEnableBpmFilter] = useState(false);
  const [catalogItems, setCatalogItems] = useState([]);
  const [catalogTotal, setCatalogTotal] = useState(0);

  // Drive Tree State
  const [currentPath, setCurrentPath] = useState('/4 media');
  const [driveItems, setDriveItems] = useState([]);

  // Common UI State
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('list'); // 'list' | 'grid'
  const [activeAuditionPath, setActiveAuditionPath] = useState(null);
  const [backendBase, setBackendBase] = useState('http://127.0.0.1:8088');

  const addAudioChannel = useDawStore(state => state.addAudioChannel);
  const fileInputRef = useRef(null);
  const activeAudioRef = useRef(null);

  // Detect Active Backend (8088 Kernel or 8080 Central)
  useEffect(() => {
    const checkBackends = async () => {
      const candidates = ['http://127.0.0.1:8088', 'http://127.0.0.1:8080', 'http://localhost:8088', 'http://localhost:8080'];
      for (const host of candidates) {
        try {
          const res = await fetch(`${host}/api/audio/stats`, { signal: AbortSignal.timeout(1200) });
          if (res.ok) {
            setBackendBase(host);
            break;
          }
        } catch {}
      }
    };
    checkBackends();
  }, []);

  // Fetch Catalog Items with Debounce
  useEffect(() => {
    if (activeTab !== 'catalog') return;

    const timer = setTimeout(() => {
      fetchCatalog();
    }, 200);

    return () => clearTimeout(timer);
  }, [activeTab, searchQuery, selectedCategory, selectedKey, enableBpmFilter, bpmMin, bpmMax, backendBase]);

  const fetchCatalog = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('q', searchQuery.trim());
      if (selectedCategory !== 'All') params.append('category', selectedCategory);
      if (selectedKey !== 'All') params.append('musical_key', selectedKey);
      if (enableBpmFilter) {
        params.append('bpm_min', bpmMin);
        params.append('bpm_max', bpmMax);
      }
      params.append('limit', '60');

      const url = `${backendBase}/api/audio/search?${params.toString()}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setCatalogItems(data.items || []);
        setCatalogTotal(data.total || 0);
      } else {
        setError('Error querying audio catalog.');
      }
    } catch (e) {
      setError('Cannot connect to audio catalog API.');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch Drive Files
  useEffect(() => {
    if (activeTab !== 'drive') return;

    const fetchDrive = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const url = `${backendBase}/api/drive/files?path=${encodeURIComponent(currentPath)}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setDriveItems(data.items || []);
        } else {
          // Fallback to 8080 if on 8088
          const fbRes = await fetch(`http://127.0.0.1:8080/api/drive/files?path=${encodeURIComponent(currentPath)}`);
          if (fbRes.ok) {
            const data = await fbRes.json();
            setDriveItems(data.items || []);
          }
        }
      } catch (e) {
        setError('Error loading drive folder.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDrive();
  }, [activeTab, currentPath, backendBase]);

  const auditionSound = (item, autoAdd = false) => {
    let previewUrl = '';
    if (item.stream_url) {
      previewUrl = `${backendBase}${item.stream_url}`;
    } else if (item.path) {
      previewUrl = item.path.startsWith('http') 
        ? item.path 
        : `${backendBase}/api/drive/stream?path=${encodeURIComponent(item.path)}`;
    }

    if (!previewUrl) return;

    try {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause();
        activeAudioRef.current = null;
      }

      if (activeAuditionPath === item.path) {
        setActiveAuditionPath(null);
        return;
      }

      const audio = new Audio(previewUrl);
      activeAudioRef.current = audio;
      setActiveAuditionPath(item.path);
      audio.play().catch(e => console.warn("Audition error:", e));
      audio.onended = () => setActiveAuditionPath(null);

      if (autoAdd) {
        addAudioChannel(previewUrl, item.filename || item.name);
      }
    } catch (err) {
      console.warn("Audio play failed:", err);
    }
  };

  const handleDragStart = (e, item) => {
    if (item.is_dir) return;
    const url = item.stream_url ? `${backendBase}${item.stream_url}` : item.path;
    const dragPayload = {
      name: item.filename || item.name,
      path: item.path,
      url: url,
      bpm: item.bpm,
      key: item.musical_key,
      category: item.category
    };
    const jsonStr = JSON.stringify(dragPayload);
    e.dataTransfer.setData('application/json', jsonStr);
    e.dataTransfer.setData('text/plain', jsonStr);
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div style={{
      width: `${browserWidth}px`,
      minWidth: '280px',
      maxWidth: '560px',
      height: '100%',
      backgroundColor: '#18191d',
      borderRight: '1px solid rgba(255,255,255,0.08)',
      display: 'flex',
      flexDirection: 'column',
      color: '#e2e8f0',
      userSelect: 'none',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Header Bar */}
      <div style={{
        padding: '10px 12px',
        backgroundColor: '#121316',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Disc size={16} color="#ff7b00" />
          <span style={{ fontWeight: '700', fontSize: '12px', letterSpacing: '0.5px', color: '#f8fafc' }}>
            OMNI AUDIO VAULT
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            onClick={() => onToggleExpand?.()}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px'
            }}
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </div>

      {/* Mode Tabs */}
      <div style={{
        display: 'flex',
        backgroundColor: '#15161a',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        padding: '4px'
      }}>
        <button
          onClick={() => setActiveTab('catalog')}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '6px 8px',
            fontSize: '11px',
            fontWeight: '600',
            backgroundColor: activeTab === 'catalog' ? '#24272f' : 'transparent',
            color: activeTab === 'catalog' ? '#00ff88' : '#94a3b8',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          <Zap size={13} /> 100K Catalog
        </button>

        <button
          onClick={() => setActiveTab('drive')}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '6px 8px',
            fontSize: '11px',
            fontWeight: '600',
            backgroundColor: activeTab === 'drive' ? '#24272f' : 'transparent',
            color: activeTab === 'drive' ? '#38bdf8' : '#94a3b8',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          <Folder size={13} /> Drive Vault
        </button>
      </div>

      {/* Catalog Search Controls */}
      {activeTab === 'catalog' && (
        <div style={{ padding: '8px 10px', borderBottom: '1px solid rgba(255,255,255,0.06)', backgroundColor: '#141518' }}>
          {/* Search Input */}
          <div style={{ position: 'relative', marginBottom: '8px' }}>
            <Search size={13} color="#64748b" style={{ position: 'absolute', left: '8px', top: '8px' }} />
            <input
              type="text"
              placeholder="Search 101,063 samples, loops, stems..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 26px 6px 28px',
                backgroundColor: '#0c0d0f',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px',
                color: '#f8fafc',
                fontSize: '11px',
                outline: 'none'
              }}
            />
            {searchQuery && (
              <X 
                size={13} 
                color="#94a3b8" 
                onClick={() => setSearchQuery('')}
                style={{ position: 'absolute', right: '8px', top: '8px', cursor: 'pointer' }} 
              />
            )}
          </div>

          {/* Category Filter Chips */}
          <div style={{
            display: 'flex',
            gap: '4px',
            overflowX: 'auto',
            paddingBottom: '6px',
            scrollbarWidth: 'none'
          }}>
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '10px',
                  border: 'none',
                  fontSize: '10px',
                  fontWeight: selectedCategory === cat ? 'bold' : 'normal',
                  backgroundColor: selectedCategory === cat ? '#00ff88' : 'rgba(255,255,255,0.05)',
                  color: selectedCategory === cat ? '#000' : '#94a3b8',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Key and BPM Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
            <select
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
              style={{
                flex: 1,
                padding: '4px 6px',
                backgroundColor: '#0c0d0f',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '4px',
                color: '#f8fafc',
                fontSize: '10px'
              }}
            >
              <option value="All">Key: All</option>
              {MUSICAL_KEYS.slice(1).map(k => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>

            <button
              onClick={() => setEnableBpmFilter(!enableBpmFilter)}
              style={{
                padding: '4px 8px',
                borderRadius: '4px',
                border: '1px solid rgba(255,255,255,0.1)',
                backgroundColor: enableBpmFilter ? 'rgba(0,255,136,0.15)' : '#0c0d0f',
                color: enableBpmFilter ? '#00ff88' : '#94a3b8',
                fontSize: '10px',
                cursor: 'pointer'
              }}
            >
              BPM: {enableBpmFilter ? `${bpmMin}-${bpmMax}` : 'Off'}
            </button>
          </div>
        </div>
      )}

      {/* Catalog Results Header */}
      {activeTab === 'catalog' && (
        <div style={{
          padding: '6px 10px',
          fontSize: '10px',
          color: '#64748b',
          display: 'flex',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(255,255,255,0.04)'
        }}>
          <span>{catalogTotal.toLocaleString()} Matching Audio Assets</span>
          <span style={{ color: '#00ff88' }}>Drag to Sequencer / Arranger</span>
        </div>
      )}

      {/* List / Results Container */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '6px'
      }}>
        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '24px', color: '#94a3b8', fontSize: '11px' }}>
            <Loader size={16} className="animate-spin" /> Scanning Catalog...
          </div>
        )}

        {error && (
          <div style={{ padding: '12px', color: '#f87171', fontSize: '11px', textAlign: 'center' }}>
            {error}
          </div>
        )}

        {/* Catalog Items */}
        {activeTab === 'catalog' && !isLoading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {catalogItems.map(item => {
              const isAuditioning = activeAuditionPath === item.path;
              return (
                <div
                  key={item.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, item)}
                  onDoubleClick={() => auditionSound(item, true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '5px 8px',
                    borderRadius: '4px',
                    backgroundColor: isAuditioning ? 'rgba(0,255,136,0.12)' : 'rgba(255,255,255,0.02)',
                    border: isAuditioning ? '1px solid rgba(0,255,136,0.3)' : '1px solid transparent',
                    cursor: 'grab',
                    fontSize: '11px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                    <button
                      onClick={() => auditionSound(item)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: isAuditioning ? '#00ff88' : '#94a3b8',
                        cursor: 'pointer',
                        padding: '2px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                    >
                      {isAuditioning ? <Square size={11} fill="#00ff88" /> : <Play size={11} />}
                    </button>
                    
                    <span 
                      style={{ 
                        whiteSpace: 'nowrap', 
                        overflow: 'hidden', 
                        textOverflow: 'ellipsis', 
                        color: isAuditioning ? '#00ff88' : '#f1f5f9',
                        fontWeight: isAuditioning ? '600' : 'normal'
                      }}
                      title={item.filename}
                    >
                      {item.filename}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                    {item.bpm && (
                      <span style={{ fontSize: '9px', backgroundColor: 'rgba(255,123,0,0.15)', color: '#ff7b00', padding: '1px 4px', borderRadius: '3px' }}>
                        {item.bpm}
                      </span>
                    )}
                    {item.musical_key && (
                      <span style={{ fontSize: '9px', backgroundColor: 'rgba(56,189,248,0.15)', color: '#38bdf8', padding: '1px 4px', borderRadius: '3px' }}>
                        {item.musical_key}
                      </span>
                    )}
                    <button
                      onClick={() => addAudioChannel(`${backendBase}${item.stream_url}`, item.filename)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#64748b',
                        cursor: 'pointer',
                        padding: '2px'
                      }}
                      title="Add to Channel Rack"
                    >
                      <Plus size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Drive Items */}
        {activeTab === 'drive' && !isLoading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {driveItems.map(item => (
              <div
                key={item.id}
                draggable={!item.is_dir}
                onDragStart={(e) => handleDragStart(e, item)}
                onClick={() => {
                  if (item.is_dir) {
                    setCurrentPath(item.path);
                  } else {
                    auditionSound(item);
                  }
                }}
                onDoubleClick={() => {
                  if (!item.is_dir) auditionSound(item, true);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(255,255,255,0.02)',
                  cursor: item.is_dir ? 'pointer' : 'grab',
                  fontSize: '11px'
                }}
              >
                {item.is_dir ? <Folder size={13} color="#38bdf8" /> : <FileAudio size={13} color="#00ff88" />}
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {item.name}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div style={{
        padding: '6px 10px',
        backgroundColor: '#101114',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        fontSize: '10px',
        color: '#64748b',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <span>Engine: AI-BS Audio Core</span>
        <span style={{ color: '#00ff88' }}>101K Samples Indexed</span>
      </div>
    </div>
  );
};

export default Browser;
