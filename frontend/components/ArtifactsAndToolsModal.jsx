/** @typedef {{name: string, content?: string}} ArtifactFile */
/** @typedef {{name?: string, display_name?: string, path?: string, modified_at?: string, size_bytes?: number, description?: string, preview?: string, project_name?: string, files?: ArtifactFile[], language?: string, created_at?: string}} Artifact */
/** @typedef {{id: string | number, category: string, fact_key: string, fact_text: string, importance_score: number, is_pinned: boolean, source?: string}} PersonalMemory */
/** @typedef {{id: string | number, event_type: string, summary: string, timestamp: string, metadata?: unknown}} ActivityEvent */
import { useState, useEffect, useRef } from 'react';

/** @param {{isOpen: boolean, onClose: () => void, onInsertText?: (text: string) => void, onAttachFile?: (file: {name: string, path: string, type?: string}) => void, backendUrl?: string}} props */
export default function ArtifactsAndToolsModal({ isOpen, onClose, onInsertText, backendUrl }) {
  const modalRef = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [activeTab, setActiveTab] = useState('tasks');
  const [artifacts, setArtifacts] = useState({
    tasks: /** @type {Artifact[]} */ ([]),
    plans: /** @type {Artifact[]} */ ([]),
    manuals: /** @type {Artifact[]} */ ([]),
    media: /** @type {Artifact[]} */ ([]),
    programs: /** @type {Artifact[]} */ ([]),
    timestamp: ''
  });
  const [personalMemories, setPersonalMemories] = useState(/** @type {PersonalMemory[]} */ ([]));
  const [activityTimeline, setActivityTimeline] = useState(/** @type {ActivityEvent[]} */ ([]));
  const [memorySubTab, setMemorySubTab] = useState('facts'); // 'facts' or 'timeline'
  const [memoryFilter, setMemoryFilter] = useState('all');
  const [memorySearch, setMemorySearch] = useState('');
  const [isAddingMemory, setIsAddingMemory] = useState(false);
  const [newMemory, setNewMemory] = useState({
    category: 'directives',
    fact_key: '',
    fact_text: '',
    importance_score: 8,
    is_pinned: false
  });

  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [selectedItem, setSelectedItem] = useState(/** @type {Artifact | null} */ (null));
  const [runningProgram, setRunningProgram] = useState(/** @type {string | null} */ (null));
  const [programOutput, setProgramOutput] = useState(/** @type {{exit_code?: number, status: string, stdout?: string, stderr?: string} | null} */ (null));

  const fetchArtifacts = async () => {
    setLoading(true);
    setLoadError('');
    try {
      const res = await fetch(`${backendUrl || 'http://127.0.0.1:8080'}/api/artifacts/live`, {
        headers: {
          
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (!res.ok) throw new Error(res.status===401||res.status===403?'Sign in to open workspace artifacts.':`Artifacts unavailable (HTTP ${res.status}).`);
      if (res.ok) {
        const data = await res.json();
        setArtifacts(data);
        if (data.tasks.length > 0 && !selectedItem && activeTab === 'tasks') {
          setSelectedItem(data.tasks[0]);
        }
      }
    } catch (err) {
      setArtifacts({tasks:[],plans:[],manuals:[],media:[],programs:[],timestamp:''});setSelectedItem(null);
      setLoadError(errorMessage(err) || 'Artifacts unavailable.');
    } finally {
      setLoading(false);
    }
  };

  const fetchMemories = async () => {
    try {
      const res = await fetch(`${backendUrl || 'http://127.0.0.1:8080'}/api/memory/personal`, {
        headers: {
          
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        setPersonalMemories(data.memories || []);
      }
    } catch (err) {
      console.error("Error fetching personal memories:", err);
    }
  };

  const fetchActivity = async () => {
    try {
      const res = await fetch(`${backendUrl || 'http://127.0.0.1:8080'}/api/memory/personal/activity?limit=50`, {
        headers: {
          
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        const data = await res.json();
        setActivityTimeline(data.events || []);
      }
    } catch (err) {
      console.error("Error fetching activity timeline:", err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchArtifacts();
      fetchMemories();
      fetchActivity();
    }
  }, [isOpen, backendUrl]);

  /** @param {string} projectName */
const handleRunProgram = async (projectName) => {
    setRunningProgram(projectName);
    setProgramOutput(null);
    try {
      const res = await fetch(`${backendUrl || 'http://127.0.0.1:8080'}/api/artifacts/programs/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify({ project_name: projectName })
      });
      const data = await res.json();
      setProgramOutput(data);
    } catch (err) {
      setProgramOutput({ status: 'error', stderr: String(err) });
    } finally {
      setRunningProgram(null);
    }
  };

  const handleSaveMemory = async (/** @type {import("react").FormEvent} */ e) => {
    e.preventDefault();
    if (!newMemory.fact_key.trim() || !newMemory.fact_text.trim()) return;

    try {
      const res = await fetch(`${backendUrl || 'http://127.0.0.1:8080'}/api/memory/personal/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          
          'X-Client-ID': 'stehouwer_publishing'
        },
        body: JSON.stringify(newMemory)
      });
      if (res.ok) {
        setNewMemory({
          category: 'directives',
          fact_key: '',
          fact_text: '',
          importance_score: 8,
          is_pinned: false
        });
        setIsAddingMemory(false);
        fetchMemories();
      }
    } catch (err) {
      console.error("Error adding memory:", err);
    }
  };

  /** @param {string | number} factId */
const handleDeleteMemory = async (factId) => {
    if (!window.confirm("Delete this personal intelligence memory fact permanently from local NVMe vault?")) return;
    try {
      const res = await fetch(`${backendUrl || 'http://127.0.0.1:8080'}/api/memory/personal/delete/${factId}`, {
        method: 'DELETE',
        headers: {
          
          'X-Client-ID': 'stehouwer_publishing'
        }
      });
      if (res.ok) {
        fetchMemories();
      }
    } catch (err) {
      console.error("Error deleting memory:", err);
    }
  };

  const filteredMemories = personalMemories.filter(m => {
    const matchesCat = memoryFilter === 'all' || m.category === memoryFilter;
    const matchesSearch = !memorySearch || 
      m.fact_key.toLowerCase().includes(memorySearch.toLowerCase()) || 
      m.fact_text.toLowerCase().includes(memorySearch.toLowerCase());
    return matchesCat && matchesSearch;
  });

  useEffect(() => {
    if (!isOpen) return;
    const previous=document.activeElement;
    modalRef.current?.querySelector('button')?.focus();
    /** @param {KeyboardEvent} event */
const keydown=event=>{
      if(event.key==='Escape'){event.preventDefault();onClose();}
      if(event.key!=='Tab')return;
      const items=[...(modalRef.current?.querySelectorAll('button,input,select,textarea,a[href]') || [])].filter((el) => el instanceof HTMLElement && !('disabled' in el && el.disabled) && el.getClientRects().length);
      const first=items[0],last=items[items.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();if (last instanceof HTMLElement) last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();if (first instanceof HTMLElement) first.focus();}
    };
    document.addEventListener('keydown',keydown);
    return()=>{document.removeEventListener('keydown',keydown);if(previous instanceof HTMLElement)previous.focus();};
  },[isOpen]);

  const downloadProgram = async () => {
    if (!selectedItem?.project_name || downloadBusy) return;
    setDownloadBusy(true);setLoadError('');
    try {
      const response=await fetch(`${backendUrl}/api/artifacts/programs/download/${encodeURIComponent(selectedItem.project_name)}`,{redirect:'error',cache:'no-store'});
      if(!response.ok)throw new Error(response.status===401||response.status===403?'Sign in to download this artifact.':`Download unavailable (HTTP ${response.status}).`);
      const blob=await response.blob();
      if(!blob.size || !['application/zip','application/octet-stream','application/x-zip-compressed'].includes(blob.type.split(';')[0]))throw new Error('The service did not return a ZIP archive.');
      const url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;anchor.download=selectedItem.project_name+'.zip';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
    } catch(error){setLoadError(errorMessage(error)||'Download unavailable.');}finally{setDownloadBusy(false);}
  };

  if (!isOpen) return null;

  return (
    <div className="chat-artifacts-backdrop" style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(7, 11, 20, 0.88)',
      backdropFilter: 'blur(10px)',
      zIndex: 99999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px'
    }}>
      <div ref={modalRef} role="dialog" aria-modal="true" aria-label="Workspace artifacts" className="chat-artifacts-drawer" style={{
        width: '95%',
        maxWidth: '1150px',
        height: '88vh',
        background: 'linear-gradient(180deg, #0d1322 0%, #080d18 100%)',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: '16px',
        boxShadow: '0 24px 60px rgba(0,0,0,0.8), 0 0 30px rgba(56, 189, 248, 0.1)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.6)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '1.4rem' }}>🧠</span>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.15rem', color: '#f8fafc', fontWeight: 800, letterSpacing: '-0.02em' }}>
                AI-BS Workspace Artifacts & Personal Intelligence Bank
              </h2>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
                100% Local Sovereign Memory • NVMe SQLite FTS5 • Last Synced: <span style={{ color: '#38bdf8' }}>{artifacts.timestamp || 'Real-Time'}</span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={() => { fetchArtifacts(); fetchMemories(); }}
              disabled={loading}
              style={{
                background: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                color: '#38bdf8',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              {loading ? '🔄 Syncing...' : '🔄 Refresh All'}
            </button>
            <button
              onClick={onClose}
              aria-label="Close artifacts"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#94a3b8',
                borderRadius: '8px',
                width: '32px',
                height: '32px',
                fontSize: '1rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {loadError && <p role="alert" style={{padding:12,color:'#fca5a5',margin:0}}>{loadError}</p>}
        {/* Tab Navigation */}
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '10px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          background: 'rgba(0, 0, 0, 0.2)'
        }}>
          {[
            { id: 'memory', label: `🧠 Personal Intelligence (${personalMemories.length})` },
            { id: 'tasks', label: `📋 Tasks (${artifacts.tasks?.length || 0})` },
            { id: 'plans', label: `📐 Plans (${artifacts.plans?.length || 0})` },
            { id: 'programs', label: `⚡ Built Programs (${artifacts.programs?.length || 0})` },
            { id: 'media', label: `🖼️ Media & Artifacts (${artifacts.media?.length || 0})` },
            { id: 'manuals', label: `📖 Manuals & Ledgers (${artifacts.manuals?.length || 0})` }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                const list = (tab.id === 'tasks' ? artifacts.tasks : tab.id === 'plans' ? artifacts.plans : tab.id === 'manuals' ? artifacts.manuals : tab.id === 'programs' ? artifacts.programs : artifacts.media);
                setSelectedItem(list.length > 0 ? list[0] : null);
              }}
              style={{
                background: activeTab === tab.id ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(99, 102, 241, 0.2))' : 'transparent',
                border: `1px solid ${activeTab === tab.id ? '#38bdf8' : 'transparent'}`,
                color: activeTab === tab.id ? '#ffffff' : '#94a3b8',
                borderRadius: '8px',
                padding: '6px 14px',
                fontSize: '0.82rem',
                fontWeight: activeTab === tab.id ? 700 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Main Content Pane */}
        {activeTab === 'memory' ? (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, padding: '20px', overflowY: 'auto' }}>
            {/* Sub-tab switcher for Knowledge Bank vs Activity Timeline */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '10px' }}>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => setMemorySubTab('facts')}
                  style={{
                    background: memorySubTab === 'facts' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                    border: `1px solid ${memorySubTab === 'facts' ? '#38bdf8' : 'rgba(255,255,255,0.1)'}`,
                    color: memorySubTab === 'facts' ? '#fff' : '#94a3b8',
                    padding: '5px 12px',
                    borderRadius: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  🧠 Knowledge Bank & Directives ({personalMemories.length})
                </button>
                <button
                  onClick={() => { setMemorySubTab('timeline'); fetchActivity(); }}
                  style={{
                    background: memorySubTab === 'timeline' ? 'rgba(52, 211, 153, 0.2)' : 'transparent',
                    border: `1px solid ${memorySubTab === 'timeline' ? '#34d399' : 'rgba(255,255,255,0.1)'}`,
                    color: memorySubTab === 'timeline' ? '#fff' : '#94a3b8',
                    padding: '5px 12px',
                    borderRadius: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  📜 Activity Timeline & Episodic Lore ({activityTimeline.length})
                </button>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: '#34d399' }}>
                <span style={{ fontSize: '0.7rem' }}>🟢</span> Continuous Auto-Save Active (NVMe SQLite)
              </div>
            </div>

            {memorySubTab === 'timeline' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {activityTimeline.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
                    No episodic events recorded yet. Every action, chat, scan, and build is saved automatically.
                  </div>
                ) : (
                  activityTimeline.map(ev => (
                    <div key={ev.id} style={{
                      background: 'rgba(15, 23, 42, 0.7)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: '8px',
                      padding: '12px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{
                          fontSize: '0.7rem',
                          fontWeight: 800,
                          textTransform: 'uppercase',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: ev.event_type === 'chat_interaction' ? 'rgba(56, 189, 248, 0.2)' :
                                     ev.event_type === 'program_built' ? 'rgba(16, 185, 129, 0.2)' :
                                     ev.event_type === 'matrix_doctor_scan' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                          color: ev.event_type === 'chat_interaction' ? '#38bdf8' :
                                 ev.event_type === 'program_built' ? '#34d399' :
                                 ev.event_type === 'matrix_doctor_scan' ? '#c084fc' : '#facc15'
                        }}>
                          {ev.event_type}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{ev.timestamp}</span>
                      </div>
                      <div style={{ fontSize: '0.82rem', color: '#f1f5f9', fontWeight: 600 }}>
                        {ev.summary}
                      </div>
                      {typeof ev.metadata === 'object' && ev.metadata !== null && Object.keys(ev.metadata).length > 0 && (
                        <div style={{ fontSize: '0.7rem', color: '#94a3b8', background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '4px', marginTop: '4px' }}>
                          <code>{JSON.stringify(ev.metadata)}</code>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            ) : (
              <>
                {/* Memory Toolbar & Categories */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', gap: '12px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {['all', 'directives', 'preferences', 'hardware', 'businesses', 'coding_patterns'].map(cat => (
                      <button
                        key={cat}
                        onClick={() => setMemoryFilter(cat)}
                        style={{
                          background: memoryFilter === cat ? '#0284c7' : 'rgba(255,255,255,0.05)',
                          color: memoryFilter === cat ? '#fff' : '#94a3b8',
                          border: `1px solid ${memoryFilter === cat ? '#38bdf8' : 'rgba(255,255,255,0.1)'}`,
                          padding: '4px 10px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          textTransform: 'capitalize'
                        }}
                      >
                        {cat}
                      </button>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="🔍 Search stored memories..."
                      value={memorySearch}
                      onChange={(e) => setMemorySearch(e.target.value)}
                      style={{
                        background: '#090d16',
                        border: '1px solid rgba(255,255,255,0.15)',
                        color: '#f8fafc',
                        padding: '6px 12px',
                        borderRadius: '8px',
                        fontSize: '0.8rem',
                        width: '220px'
                      }}
                    />
                    <button
                      onClick={() => setIsAddingMemory(!isAddingMemory)}
                      style={{
                        background: 'linear-gradient(135deg, #10b981, #059669)',
                        color: '#fff',
                        border: 'none',
                        padding: '6px 14px',
                        borderRadius: '8px',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        cursor: 'pointer'
                      }}
                    >
                      {isAddingMemory ? '✕ Cancel' : '➕ Add Custom Rule'}
                    </button>
                  </div>
                </div>

                {/* Add Memory Form */}
                {isAddingMemory && (
                  <form onSubmit={handleSaveMemory} style={{
                    background: 'rgba(15, 23, 42, 0.9)',
                    border: '1px solid rgba(52, 211, 153, 0.4)',
                    borderRadius: '12px',
                    padding: '16px',
                    marginBottom: '18px'
                  }}>
                    <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', color: '#34d399' }}>➕ Teach AI-BS a New Memory Fact or Rule</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '150px 200px 1fr', gap: '10px', marginBottom: '10px' }}>
                      <div>
                        <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Category</label>
                        <select
                          value={newMemory.category}
                          onChange={(e) => setNewMemory({ ...newMemory, category: e.target.value })}
                          style={{ width: '100%', background: '#090d16', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.2)', padding: '6px', borderRadius: '6px', fontSize: '0.78rem' }}
                        >
                          <option value="directives">Directives</option>
                          <option value="preferences">Preferences</option>
                          <option value="hardware">Hardware</option>
                          <option value="businesses">Businesses</option>
                          <option value="coding_patterns">Coding Patterns</option>
                        </select>
                      </div>
                      <div>
                        <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Fact Key</label>
                        <input
                          type="text"
                          placeholder="e.g. preferred_color_palette"
                          value={newMemory.fact_key}
                          onChange={(e) => setNewMemory({ ...newMemory, fact_key: e.target.value })}
                          style={{ width: '100%', background: '#090d16', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.2)', padding: '6px', borderRadius: '6px', fontSize: '0.78rem' }}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>Memory Statement / Rule</label>
                        <input
                          type="text"
                          placeholder="e.g. Always generate modern dark mode charts with emerald green and cyan highlights"
                          value={newMemory.fact_text}
                          onChange={(e) => setNewMemory({ ...newMemory, fact_text: e.target.value })}
                          style={{ width: '100%', background: '#090d16', color: '#f8fafc', border: '1px solid rgba(255,255,255,0.2)', padding: '6px', borderRadius: '6px', fontSize: '0.78rem' }}
                        />
                      </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#cbd5e1', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={newMemory.is_pinned}
                          onChange={(e) => setNewMemory({ ...newMemory, is_pinned: e.target.checked })}
                        />
                        <span>★ Pin into all System Prompts (High Priority)</span>
                      </label>
                      <button
                        type="submit"
                        style={{
                          background: '#10b981',
                          color: '#fff',
                          border: 'none',
                          padding: '6px 16px',
                          borderRadius: '6px',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        💾 Save to Personal Intelligence
                      </button>
                    </div>
                  </form>
                )}

                {/* Memories Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '12px' }}>
                  {filteredMemories.map(m => (
                    <div key={m.id} style={{
                      background: 'rgba(15, 23, 42, 0.7)',
                      border: `1px solid ${m.is_pinned ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255,255,255,0.06)'}`,
                      borderRadius: '10px',
                      padding: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      boxShadow: m.is_pinned ? '0 4px 15px rgba(56, 189, 248, 0.1)' : 'none'
                    }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{
                            fontSize: '0.68rem',
                            fontWeight: 800,
                            textTransform: 'uppercase',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            background: m.category === 'directives' ? 'rgba(239, 68, 68, 0.2)' :
                                       m.category === 'hardware' ? 'rgba(168, 85, 247, 0.2)' :
                                       m.category === 'businesses' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                            color: m.category === 'directives' ? '#f87171' :
                                   m.category === 'hardware' ? '#c084fc' :
                                   m.category === 'businesses' ? '#34d399' : '#38bdf8'
                          }}>
                            {m.category}
                          </span>
                          {m.is_pinned ? (
                            <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 700 }}>★ PINNED</span>
                          ) : (
                            <span style={{ fontSize: '0.68rem', color: '#64748b' }}>Score: {m.importance_score}/10</span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '6px' }}>
                          {m.fact_key}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.45' }}>
                          {m.fact_text}
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                        <span style={{ fontSize: '0.68rem', color: '#64748b' }}>
                          Source: {m.source}
                        </span>
                        <button
                          onClick={() => handleDeleteMemory(m.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#f87171',
                            fontSize: '0.72rem',
                            cursor: 'pointer',
                            padding: '2px 6px',
                            fontWeight: 600
                          }}
                          title="Forget this memory"
                        >
                          🗑️ Forget
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="chat-artifacts-content" style={{ display: 'grid', gridTemplateColumns: '320px 1fr', flex: 1, overflow: 'hidden' }}>
            {/* Item List Sidebar */}
            <div style={{
              borderRight: '1px solid rgba(255, 255, 255, 0.08)',
              overflowY: 'auto',
              padding: '12px',
              background: 'rgba(0, 0, 0, 0.15)'
            }}>
              {activeTab === 'programs' ? (
                artifacts.programs?.length === 0 ? (
                  <div style={{ padding: '20px', color: '#64748b', fontSize: '0.82rem', textAlign: 'center' }}>
                    No autonomous programs built yet. Ask BS-Chat to "Build a program for..." to generate one.
                  </div>
                ) : (
                  artifacts.programs.map((p, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedItem(p)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        marginBottom: '6px',
                        background: selectedItem?.project_name === p.project_name ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${selectedItem?.project_name === p.project_name ? '#38bdf8' : 'rgba(255,255,255,0.06)'}`,
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>{p.display_name || p.project_name}</span>
                        <span style={{ fontSize: '0.68rem', background: '#0284c7', color: '#fff', padding: '1px 6px', borderRadius: '4px' }}>
                          {p.language || 'Python'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
                        {p.files?.length || 0} files • {p.created_at}
                      </div>
                    </div>
                  ))
                )
              ) : (
                (artifacts[/** @type {'tasks' | 'plans' | 'manuals' | 'media' | 'programs'} */ (activeTab)] || []).length === 0 ? (
                  <div style={{ padding: '20px', color: '#64748b', fontSize: '0.82rem', textAlign: 'center' }}>
                    No items found in this category.
                  </div>
                ) : (
                  (artifacts[/** @type {'tasks' | 'plans' | 'manuals' | 'media' | 'programs'} */ (activeTab)] || []).map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => setSelectedItem(item)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        marginBottom: '6px',
                        background: selectedItem?.path === item.path ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${selectedItem?.path === item.path ? '#38bdf8' : 'rgba(255,255,255,0.06)'}`,
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', wordBreak: 'break-all' }}>
                        {item.name}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b', marginTop: '4px' }}>
                        <span>{item.size_bytes === undefined ? 'Unavailable' : (item.size_bytes / 1024).toFixed(1)} KB</span>
                        <span>{item.modified_at}</span>
                      </div>
                    </div>
                  ))
                )
              )}
            </div>

            {/* Details & Action Pane */}
            <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
              {selectedItem ? (
                activeTab === 'programs' ? (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <div>
                        <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#38bdf8' }}>{selectedItem.display_name || selectedItem.project_name}</h3>
                        <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>
                          {selectedItem.description}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleRunProgram(selectedItem.project_name || '')}
                          disabled={runningProgram === selectedItem.project_name}
                          style={{
                            background: 'linear-gradient(135deg, #10b981, #059669)',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '8px',
                            padding: '8px 14px',
                            fontSize: '0.82rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          {runningProgram === selectedItem.project_name ? '⚡ Executing...' : '▶ Run Program'}
                        </button>
                        <button type="button" onClick={downloadProgram} disabled={downloadBusy}
                          style={{
                            background: 'rgba(56, 189, 248, 0.15)',
                            border: '1px solid rgba(56, 189, 248, 0.4)',
                            color: '#38bdf8',
                            borderRadius: '8px',
                            padding: '8px 14px',
                            fontSize: '0.82rem',
                            fontWeight: 700,
                            textDecoration: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          📥 Download ZIP
                        </button>
                      </div>
                    </div>

                    {/* Program Output Banner if Run */}
                    {programOutput && (
                      <div style={{
                        background: '#0a0f1d',
                        border: `1px solid ${programOutput.status === 'success' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                        borderRadius: '8px',
                        padding: '12px',
                        marginBottom: '16px'
                      }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: programOutput.status === 'success' ? '#34d399' : '#f87171', marginBottom: '6px' }}>
                          Execution Result ({programOutput.status.toUpperCase()}) • Exit Code: {programOutput.exit_code ?? 0}
                        </div>
                        <pre style={{ margin: 0, fontSize: '0.8rem', color: '#f1f5f9', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                          {programOutput.stdout || programOutput.stderr || '[Process finished with no output]'}
                        </pre>
                      </div>
                    )}

                    <h4 style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '8px' }}>Project Source Files</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {(selectedItem.files || []).map((f, i) => (
                        <div key={i} style={{ background: '#090d16', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', overflow: 'hidden' }}>
                          <div style={{ padding: '6px 12px', background: 'rgba(255,255,255,0.04)', fontSize: '0.75rem', fontWeight: 700, color: '#93c5fd' }}>
                            📄 {f.name}
                          </div>
                          {f.content && (
                            <pre style={{ margin: 0, padding: '10px 12px', fontSize: '0.8rem', color: '#cbd5e1', overflowX: 'auto', background: 'transparent' }}>
                              {f.content}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                      <div>
                        <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#f8fafc' }}>{selectedItem.name}</h3>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
                          Location: <code style={{ color: '#94a3b8' }}>{selectedItem.path}</code>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => {
                            onInsertText?.(`\n[Reference Artifact: ${selectedItem.name}]\nPath: ${selectedItem.path}\n`);
                            onClose();
                          }}
                          style={{
                            background: 'rgba(56, 189, 248, 0.15)',
                            border: '1px solid rgba(56, 189, 248, 0.4)',
                            color: '#38bdf8',
                            borderRadius: '8px',
                            padding: '6px 12px',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          ➕ Insert Reference into Prompt
                        </button>
                      </div>
                    </div>

                    {selectedItem.preview && (
                      <div style={{
                        background: '#070b14',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '8px',
                        padding: '14px',
                        maxHeight: '420px',
                        overflowY: 'auto'
                      }}>
                        <pre style={{ margin: 0, fontSize: '0.82rem', color: '#cbd5e1', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                          {selectedItem.preview}
                        </pre>
                      </div>
                    )}
                  </div>
                )
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
                  Select an artifact or program on the left to inspect
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
