import { useState, useEffect, useCallback } from "react";
import './ScriptToBookNovelizerModal.css';

const DEFAULT_STYLES = {
  memoir_first_person: {
    label: '1st Person Authentic Memoir',
    icon: '🎙️',
    description: 'Raw, emotionally resonant first-person biographical prose ("I looked at the judge...").'
  },
  cinematic_thriller_third: {
    label: '3rd Person Cinematic Thriller',
    icon: '🎬',
    description: 'Fast-paced, deep-POV commercial fiction style (Michael Crichton / Dennis Lehane).'
  },
  literary_atmospheric: {
    label: 'Atmospheric Literary Fiction',
    icon: '📖',
    description: 'Rich, poetic prose with expanded world-building and character history.'
  },
  episodic_ya_drama: {
    label: 'Fast-Paced Episodic & Commercial',
    icon: '⚡',
    description: 'Modern high-engagement pacing with sharp dialogue and chapter cliffhangers.'
  }
};

/** @param {{"isOpen": boolean, "onClose"?: () => void, "backendUrl"?: string, "currentProject"?: string, "activeScript"?: string}} props */
export default function ScriptToBookNovelizerModal({
  isOpen,
  onClose,
  backendUrl = 'http://127.0.0.1:8000',
  currentProject = 'Echoes_Within',
  activeScript = ''
}) {
  const [activeStep, setActiveStep] = useState('plan'); // 'setup' | 'plan' | 'studio' | 'export'
  const [projects, setProjects] = useState(/** @type {Array<{"name": string, "scene_count": number}>} */ ([]));
  const [selectedProject, setSelectedProject] = useState(currentProject || 'Echoes_Within');
  
  // Setup Config
  const [styleProfile, setStyleProfile] = useState('memoir_first_person');
  const [expansionMultiplier, setExpansionMultiplier] = useState(2.5);
  const [povCharacter, setPovCharacter] = useState('Brett');
  const [bookTitle, setBookTitle] = useState('Echoes Within: The Novel');
  const [authorName] = useState('Brett Stehouwer');

  // Chapter Planning & Conversion State
  const [chapters, setChapters] = useState(/** @type {Array<{"chapter_number": number, "combined_script": string, "title": string, "scene_count": number, "estimated_words": number, "scenes": Array<{"id": string, "heading": string}>}>} */ ([]));
  const [selectedChapterIndex, setSelectedChapterIndex] = useState(0);
  const [isGrouping, setIsGrouping] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [activeProse, setActiveProse] = useState('');
  const [savedChapters, setSavedChapters] = useState(/** @type {Array<{"chapter_number": number, "prose_content": string, "word_count": number}>} */ ([]));
  const [saveStatus, setSaveStatus] = useState('idle');

  // Load Projects & Existing Drafts
  const loadProjects = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/novelizer/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch (e) {
      console.warn('Failed to fetch novelizer projects:', e);
    }
  }, [backendUrl]);

  const loadSavedDrafts = useCallback(/** @param {string} proj */
async ( proj) => {
    try {
      const res = await fetch(`${backendUrl}/api/novelizer/get_drafts/${proj}`);
      if (res.ok) {
        const data = await res.json();
        setSavedChapters(data.chapters || []);
      }
    } catch (e) {
      console.warn('Failed to load drafts:', e);
    }
  }, [backendUrl]);

  const groupScriptChapters = useCallback(/** @param {string} proj */
async ( proj) => {
    setIsGrouping(true);
    try {
      const res = await fetch(`${backendUrl}/api/novelizer/group_chapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: proj,
          script_content: activeScript || null
        })
      });
      if (res.ok) {
        const data = await res.json();
        setChapters(data.chapters || []);
        if (data.chapters && data.chapters.length > 0) {
          setSelectedChapterIndex(0);
        }
      }
    } catch (e) {
      console.error('Failed to group chapters:', e);
    } finally {
      setIsGrouping(false);
    }
  }, [backendUrl, activeScript]);

  useEffect(() => {
    if (isOpen) {
      loadProjects();
      loadSavedDrafts(selectedProject);
      groupScriptChapters(selectedProject);
    }
  }, [isOpen, selectedProject, loadProjects, loadSavedDrafts, groupScriptChapters]);

  // When chapter selection changes, load existing prose if saved
  useEffect(() => {
    if (!chapters || chapters.length === 0) return;
    const currChap = chapters[selectedChapterIndex];
    if (!currChap) return;

    const saved = savedChapters.find(c => c.chapter_number === currChap.chapter_number);
    if (saved && saved.prose_content) {
      setActiveProse(saved.prose_content);
    } else {
      setActiveProse('');
    }
  }, [selectedChapterIndex, chapters, savedChapters]);

  // Convert Active Chapter to Prose
  const handleConvertChapter = async () => {
    const currChap = chapters[selectedChapterIndex];
    if (!currChap) return;

    setIsConverting(true);
    try {
      const res = await fetch(`${backendUrl}/api/novelizer/convert_chapter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_number: currChap.chapter_number,
          chapter_title: currChap.title,
          scenes_text: currChap.combined_script,
          project_name: selectedProject,
          style_profile: styleProfile,
          expansion_multiplier: expansionMultiplier,
          pov_character: povCharacter
        })
      });
      if (res.ok) {
        const data = await res.json();
        setActiveProse(data.prose || '');
        // Auto save to disk
        await handleSaveDraft(currChap.chapter_number, currChap.title, data.prose);
      }
    } catch (e) {
      alert(`Novelization conversion error: ${(e instanceof Error ? e.message : String(e))}`);
    } finally {
      setIsConverting(false);
    }
  };

  // Save Draft to disk
  /** @param {number} chapNum @param {string} chapTitle @param {string} prose */
const handleSaveDraft = async ( chapNum,  chapTitle,  prose) => {
    setSaveStatus('saving');
    try {
      const res = await fetch(`${backendUrl}/api/novelizer/save_draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: selectedProject,
          chapter_number: chapNum,
          chapter_title: chapTitle,
          prose_content: prose,
          word_count: prose.trim() ? prose.trim().split(/\s+/).length : 0
        })
      });
      if (res.ok) {
        setSaveStatus('saved');
        loadSavedDrafts(selectedProject);
        setTimeout(() => setSaveStatus('idle'), 2500);
      }
    } catch (e) {
      setSaveStatus('error');
    }
  };

  // Export Complete Book
  /** @param {string} format */
const handleExportBook = async ( format) => {
    try {
      const res = await fetch(`${backendUrl}/api/novelizer/export_book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: selectedProject,
          book_title: bookTitle,
          author_name: authorName,
          format_type: format
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedProject}_Book_Manuscript.${format === 'markdown' ? 'md' : 'html'}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      alert(`Export error: ${(e instanceof Error ? e.message : String(e))}`);
    }
  };

  if (!isOpen) return null;

  const currentChapObj = chapters[selectedChapterIndex] || {};
  const totalNovelWords = savedChapters.reduce((acc, c) => acc + (c.word_count || 0), 0);
  const estBookPages = Math.max(1, Math.ceil(totalNovelWords / 250));

  return (
    <div className="novelizer-modal-overlay">
      <div className="novelizer-modal-container">
        {/* Header */}
        <div className="novelizer-header">
          <div className="novelizer-title-stack">
            <div className="novelizer-badge">
              <span>📖 NOVELIZER STUDIO</span>
              <span>•</span>
              <span>Screenplay-to-Book AI Conversion Engine</span>
            </div>
            <h2>Stehouwer Publishing — Book & Memoir Creator</h2>
          </div>

          <div className="novelizer-header-actions">
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="novelizer-project-select"
            >
              {projects.map(p => (
                <option key={p.name} value={p.name}>
                  🎬 {p.name.replace(/_/g, ' ')} ({p.scene_count} scenes)
                </option>
              ))}
            </select>

            <button onClick={onClose} className="novelizer-btn-close" title="Close Novelizer">✕</button>
          </div>
        </div>

        {/* Step Tabs Navigation Bar */}
        <div className="novelizer-nav-ribbon">
          <button
            className={`novelizer-tab-btn ${activeStep === 'plan' ? 'active' : ''}`}
            onClick={() => setActiveStep('plan')}
          >
            <span>📑 1. Chapter Plan ({chapters.length} Chapters)</span>
          </button>
          <button
            className={`novelizer-tab-btn ${activeStep === 'studio' ? 'active' : ''}`}
            onClick={() => setActiveStep('studio')}
          >
            <span>✍️ 2. Chapter Prose Studio</span>
          </button>
          <button
            className={`novelizer-tab-btn ${activeStep === 'setup' ? 'active' : ''}`}
            onClick={() => setActiveStep('setup')}
          >
            <span>🎙️ 3. Voice & Tone Setup</span>
          </button>
          <button
            className={`novelizer-tab-btn ${activeStep === 'export' ? 'active' : ''}`}
            onClick={() => setActiveStep('export')}
          >
            <span>📚 4. Book Vault & KDP Export ({totalNovelWords.toLocaleString()} Words · ~{estBookPages} pgs)</span>
          </button>
        </div>

        {/* Modal Main Content Body */}
        <div className="novelizer-body">
          {/* ══════════ STEP 1: CHAPTER & BEAT PLAN ══════════ */}
          {activeStep === 'plan' && (
            <div className="novelizer-plan-view">
              <div className="plan-header-bar">
                <div>
                  <h3>Screenplay Chapter Outline</h3>
                  <p>Auto-partitioned into {chapters.length} dramatic chapters with scene groupings and estimated novel words.</p>
                </div>
                <button
                  onClick={() => groupScriptChapters(selectedProject)}
                  disabled={isGrouping}
                  className="novelizer-btn-secondary"
                >
                  {isGrouping ? '⏳ Analyzing Script...' : '🔄 Re-Scan Script Scenes'}
                </button>
              </div>

              {isGrouping ? (
                <div className="novelizer-loading-box">
                  <span className="spinner">🌀</span>
                  <p>Decomposing screenplay scenes into book chapters...</p>
                </div>
              ) : (
                <div className="novelizer-chapter-grid">
                  {chapters.map((chap, idx) => {
                    const isSaved = savedChapters.some(c => c.chapter_number === chap.chapter_number);
                    return (
                      <div
                        key={chap.chapter_number}
                        className={`novelizer-chapter-card ${idx === selectedChapterIndex ? 'selected' : ''}`}
                        onClick={() => {
                          setSelectedChapterIndex(idx);
                          setActiveStep('studio');
                        }}
                      >
                        <div className="chapter-card-top">
                          <span className="chapter-number-badge">Ch. {chap.chapter_number}</span>
                          <span className={`chapter-status-pill ${isSaved ? 'completed' : 'pending'}`}>
                            {isSaved ? '🟢 Written' : '⚪ Screenplay Ready'}
                          </span>
                        </div>
                        <h4>{chap.title}</h4>
                        <div className="chapter-meta">
                          <span>🎬 {chap.scene_count} Scenes</span>
                          <span>📝 ~{chap.estimated_words.toLocaleString()} Est. Words</span>
                        </div>
                        <div className="chapter-scene-preview">
                          {chap.scenes.map(s => (
                            <span key={s.id} className="scene-chip">{s.heading}</span>
                          ))}
                        </div>
                        <span className="chapter-card-cta">Open in Prose Studio →</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ══════════ STEP 2: PROSE CONVERSION STUDIO ══════════ */}
          {activeStep === 'studio' && (
            <div className="novelizer-studio-view">
              {/* Top Studio Controls */}
              <div className="studio-top-bar">
                <div className="studio-chapter-stepper">
                  <button
                    disabled={selectedChapterIndex <= 0}
                    onClick={() => setSelectedChapterIndex(prev => prev - 1)}
                    className="stepper-btn"
                  >
                    ◀ Prev
                  </button>
                  <span className="stepper-title">
                    {currentChapObj.title || `Chapter ${selectedChapterIndex + 1}`}
                  </span>
                  <button
                    disabled={selectedChapterIndex >= chapters.length - 1}
                    onClick={() => setSelectedChapterIndex(prev => prev + 1)}
                    className="stepper-btn"
                  >
                    Next ▶
                  </button>
                </div>

                <div className="studio-action-cluster">
                  <div className="save-status-pill">
                    {saveStatus === 'saving' ? '🟡 Saving...' : saveStatus === 'saved' ? '🟢 Draft Saved' : ''}
                  </div>

                  <button
                    onClick={handleConvertChapter}
                    disabled={isConverting}
                    className="novelizer-btn-primary"
                  >
                    {isConverting ? '✨ Novelizing Chapter...' : '✨ Convert Script to Book Prose'}
                  </button>

                  <button
                    onClick={() => handleSaveDraft(currentChapObj.chapter_number, currentChapObj.title, activeProse)}
                    disabled={!activeProse.trim()}
                    className="novelizer-btn-save"
                  >
                    💾 Save Chapter Draft
                  </button>
                </div>
              </div>

              {/* Side-by-Side Canvas */}
              <div className="studio-split-canvas">
                {/* Left: Screenplay Source Reference */}
                <div className="studio-pane script-pane">
                  <div className="pane-header">
                    <span>🎬 Screenplay Scene Source ({currentChapObj.scene_count || 0} Scenes)</span>
                  </div>
                  <pre className="script-code-view">
                    {currentChapObj.combined_script || 'No scenes selected.'}
                  </pre>
                </div>

                {/* Right: Rich Novel Prose Editor */}
                <div className="studio-pane prose-pane">
                  <div className="pane-header">
                    <span>📖 Full Novel Prose Manuscript</span>
                    <span className="word-count-badge">
                      {activeProse.trim() ? activeProse.trim().split(/\s+/).length : 0} Words
                    </span>
                  </div>
                  <textarea
                    value={activeProse}
                    onChange={(e) => setActiveProse(e.target.value)}
                    placeholder="Click '✨ Convert Script to Book Prose' to generate full-length novel prose from the screenplay scenes, or begin writing directly..."
                    className="prose-editor-textarea"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ══════════ STEP 3: VOICE & TONE SETUP ══════════ */}
          {activeStep === 'setup' && (
            <div className="novelizer-setup-view">
              <div className="setup-section">
                <h3>Voice & Tone Preset</h3>
                <p>Choose how the screenplay's visual action and dialogue are translated into prose.</p>
                <div className="style-profiles-grid">
                  {Object.entries(DEFAULT_STYLES).map(([key, style]) => (
                    <div
                      key={key}
                      className={`style-card ${styleProfile === key ? 'active' : ''}`}
                      onClick={() => setStyleProfile(key)}
                    >
                      <div className="style-icon">{style.icon}</div>
                      <h4>{style.label}</h4>
                      <p>{style.description}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="setup-section" style={{ marginTop: '24px' }}>
                <h3>Prose Expansion Multiplier</h3>
                <p>Controls how deeply internal monologue, world-building, and sensory descriptions are expanded.</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginTop: '12px' }}>
                  <input
                    type="range"
                    min="1.5"
                    max="4.5"
                    step="0.5"
                    value={expansionMultiplier}
                    onChange={(e) => setExpansionMultiplier(parseFloat(e.target.value))}
                    style={{ flex: 1, accentColor: '#38bdf8' }}
                  />
                  <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#38bdf8', minWidth: '80px' }}>
                    {expansionMultiplier}x Words
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.75rem', marginTop: '4px' }}>
                  <span>1.5x (Novella / Fast)</span>
                  <span>2.5x (Standard Novel / Memoir)</span>
                  <span>4.5x (Epic Volume / Deep Lore)</span>
                </div>
              </div>

              <div className="setup-section" style={{ marginTop: '24px' }}>
                <h3>POV & Identity Binding</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '12px' }}>
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Point-of-View Protagonist:</label>
                    <input
                      type="text"
                      value={povCharacter}
                      onChange={(e) => setPovCharacter(e.target.value)}
                      className="setup-input"
                      placeholder="e.g. Brett"
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Book Title:</label>
                    <input
                      type="text"
                      value={bookTitle}
                      onChange={(e) => setBookTitle(e.target.value)}
                      className="setup-input"
                      placeholder="Book Title"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ══════════ STEP 4: BOOK VAULT & KDP EXPORT ══════════ */}
          {activeStep === 'export' && (
            <div className="novelizer-export-view">
              <div className="export-stats-hero">
                <div className="stat-box">
                  <span className="stat-num">{savedChapters.length} / {chapters.length}</span>
                  <span className="stat-label">Chapters Written</span>
                </div>
                <div className="stat-box">
                  <span className="stat-num">{totalNovelWords.toLocaleString()}</span>
                  <span className="stat-label">Total Book Words</span>
                </div>
                <div className="stat-box">
                  <span className="stat-num">~{estBookPages}</span>
                  <span className="stat-label">Estimated Book Pages</span>
                </div>
                <div className="stat-box">
                  <span className="stat-num">{Math.round(totalNovelWords / 200)}m</span>
                  <span className="stat-label">Estimated Reading Time</span>
                </div>
              </div>

              <div className="export-download-options">
                <h3>Publishing & Export Formats</h3>
                <p>Generate production-ready manuscripts for Amazon KDP, Apple Books, and IngramSpark.</p>

                <div className="export-buttons-row">
                  <button onClick={() => handleExportBook('markdown')} className="export-btn-large">
                    <span className="btn-icon">📝</span>
                    <div>
                      <strong>Markdown Manuscript (.md)</strong>
                      <p>Master editable text file with chapter headings and table of contents.</p>
                    </div>
                  </button>

                  <button onClick={() => handleExportBook('html_print')} className="export-btn-large highlight">
                    <span className="btn-icon">📕</span>
                    <div>
                      <strong>Print-Ready 6"×9" Trade Paperback (HTML/PDF)</strong>
                      <p>Formatted with chapter drop-caps, headers, and standard trade margins.</p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Table of Contents Summary */}
              <div className="export-toc-list">
                <h4>Manuscript Table of Contents</h4>
                <div className="toc-items">
                  {chapters.map(c => {
                    const saved = savedChapters.find(sc => sc.chapter_number === c.chapter_number);
                    return (
                      <div key={c.chapter_number} className="toc-row">
                        <span>{c.title}</span>
                        <span className="toc-words">{saved ? `${saved.word_count.toLocaleString()} words` : 'Draft Pending'}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
