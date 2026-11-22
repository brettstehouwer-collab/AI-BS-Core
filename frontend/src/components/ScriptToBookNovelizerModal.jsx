import { useState, useEffect, useRef } from "react";
import './ScriptToBookNovelizerModal.css';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';
import { createNovelizerDraftStore } from '/src/utils/novelizerDrafts.js';
import { auth } from '/src/firebase.js';
import { onAuthStateChanged } from 'firebase/auth';

const DEFAULT_STYLES = {
  memoir_first_person: {
    label: '1st Person Source-Bound Memoir',
    icon: '🎙️',
    description: 'Use supported facts only; missing memories and sensory details need author review.'
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

/** @param {{isOpen:boolean,onClose?:()=>void,backendUrl?:string,currentProject?:string,activeScript?:string}} props */
export default function ScriptToBookNovelizerModal({isOpen,onClose,backendUrl='http://127.0.0.1:8000',currentProject='Echoes_Within',activeScript=''}) {
  const [activeStep,setActiveStep]=useState('plan');
  const [projects,setProjects]=useState(/** @type {any[]} */([]));
  const [selectedProject,setSelectedProject]=useState(currentProject || 'Echoes_Within');
  const [styleProfile,setStyleProfile]=useState('memoir_first_person');
  const [expansionMultiplier,setExpansionMultiplier]=useState(2.5);
  const [povCharacter,setPovCharacter]=useState('');
  const [bookTitle,setBookTitle]=useState('');
  const [authorName,setAuthorName]=useState('');
  const [chapterPlan,setChapters]=useState(/** @type {any[]} */([]));
  const [selectedChapterIndex,setSelectedChapterIndex]=useState(0);
  const [isGrouping,setIsGrouping]=useState(false);
  const [isConverting,setIsConverting]=useState(false);
  const [,setActiveProse]=useState('');
  const [savedChapters,setSavedChapters]=useState(/** @type {any[]} */([]));
  const [saveStatus,setSaveStatus]=useState('idle');
  const [error,setError]=useState('');
  const [generationReceipt,setGenerationReceipt]=useState(/** @type {any} */(null));
  const [identity,setIdentity]=useState(auth.currentUser?.uid || '');
  const [,setDraftVersion]=useState(0);
  const storeRef=useRef(/** @type {any} */(null));
  if (!storeRef.current) storeRef.current=createNovelizerDraftStore(typeof sessionStorage==='undefined'?null:sessionStorage);
  const store=storeRef.current;
  const contextRef=useRef(/** @type {any} */(null));
  const epochRef=useRef(0);
  const selectedRef=useRef(/** @type {any} */(null));
  const savesRef=useRef(/** @type {Map<string,Promise<any>>} */(new Map()));
  const planRef=useRef(/** @type {any} */(null));
  const scope=JSON.stringify([backendUrl,identity]);
  const context=[isOpen,backendUrl,identity,selectedProject,currentProject,activeScript];
  if (!contextRef.current || context.some((value,index)=>!Object.is(value,contextRef.current[index]))) {
    contextRef.current=context;epochRef.current++;
  }
  const chapters=planRef.current?.scope===scope && planRef.current?.project===selectedProject
    && planRef.current?.epoch===epochRef.current?chapterPlan:[];
  const chapter=chapters[selectedChapterIndex];
  selectedRef.current={epoch:epochRef.current,scope,project:selectedProject,chapter:chapter?.chapter_number,open:isOpen,identity};
  const currentDraft=chapter?store.get(scope,selectedProject,chapter.chapter_number):null;
  useEffect(()=>onAuthStateChanged(auth,user=>setIdentity(user?.uid || '')),[]);
  /** @param {unknown} failure */
  const errorText=failure=>failure instanceof Error?failure.message:String(failure);
  /** @param {number} epoch */
  const current=(epoch)=>selectedRef.current.open && selectedRef.current.epoch===epoch
    && (auth.currentUser?.uid || '')===selectedRef.current.identity;
  /** @param {any} buffer */
  const showDraft=(buffer)=>{setActiveProse(buffer?.text || '');setDraftVersion(value=>value+1);};
  /** @param {string} route @param {any} body @param {string} method */
  async function authenticatedFetch(route,body,method='POST') {
    const headers=await chatAuthHeaders(body?{'Content-Type':'application/json'}:{},identity);
    if ((auth.currentUser?.uid || '')!==identity) throw new Error('The signed-in account changed. Your draft was retained.');
    const response=await fetch(`${backendUrl}${route}`,{method,headers,...(body?{body:JSON.stringify(body)}:{})});
    if (!response.ok) {
      let detail;
      try { detail=(await response.json()).detail; } catch { detail=null; }
      throw new Error(typeof detail==='string'?detail:detail?.message || `Request failed (${response.status}). Your draft was retained.`);
    }
    return response;
  }
  /** @param {number} epoch */
  async function loadProjects(epoch) {
    try {const response=await authenticatedFetch('/api/novelizer/projects',null,'GET');const data=await response.json();
      if (current(epoch)) setProjects(data.projects || []);
    } catch (failure) {if(current(epoch))setError(errorText(failure));}
  }
  /** @param {string} project @param {number} epoch */
  async function loadSavedDrafts(project,epoch) {
    const ticket=store.stamp();
    try {
      const response=await authenticatedFetch(`/api/novelizer/get_drafts/${encodeURIComponent(project)}`,null,'GET');
      const data=await response.json();
      if (!current(epoch) || selectedRef.current.project!==project) return;
      if (data.project_name!==project || !Array.isArray(data.chapters)) throw new Error('The saved draft response did not match the selected project.');
      data.chapters.forEach(/** @param {any} row */ row=>store.mergeSaved(scope,project,row,ticket));
      setSavedChapters(data.chapters);
      const selected=selectedRef.current;
      if(selected.chapter)showDraft(store.get(scope,project,selected.chapter));
    } catch (failure) {if(current(epoch))setError(errorText(failure));}
  }
  /** @param {string} project @param {number} epoch */
  async function groupScriptChapters(project,epoch=epochRef.current) {
    setIsGrouping(true);
    try {
      const fromEditor=project===currentProject && Boolean(activeScript);
      const response=await authenticatedFetch('/api/novelizer/group_chapters',{
        project_name:project,script_content:fromEditor?activeScript:null,script_project_name:fromEditor?project:null});
      const data=await response.json();
      if(!current(epoch) || selectedRef.current.project!==project)return;
      if(data.source_project!==project || !Array.isArray(data.chapters))throw new Error('The chapter plan did not match its source project.');
      planRef.current={scope,project,epoch};
      setChapters(data.chapters);setSelectedChapterIndex(0);
    } catch(failure){if(current(epoch))setError(errorText(failure));}
    finally {if(current(epoch))setIsGrouping(false);}
  }
  useEffect(()=>{
    if(!isOpen)return;
    const epoch=epochRef.current;
    setError('');setSaveStatus('idle');setGenerationReceipt(null);setIsConverting(false);
    setChapters([]);setSavedChapters([]);setSelectedChapterIndex(0);setActiveProse('');
    loadProjects(epoch);loadSavedDrafts(selectedProject,epoch);groupScriptChapters(selectedProject,epoch);
  },[isOpen,backendUrl,identity,selectedProject,currentProject,activeScript]);
  useEffect(()=>{
    if(chapter)showDraft(store.get(scope,selectedProject,chapter.chapter_number));
  },[scope,selectedProject,chapter?.chapter_number]);
  /** @param {string} value */
  function handleProseChange(value) {
    if(!chapter)return;
    const existing=store.get(scope,selectedProject,chapter.chapter_number);
    const buffer=store.edit(scope,selectedProject,chapter.chapter_number,existing.title || chapter.title,value);
    showDraft(buffer);setSaveStatus('unsaved');
  }
  async function handleConvertChapter() {
    const selected=chapters[selectedChapterIndex];if(!selected)return;
    const epoch=epochRef.current;
    const snapshot=store.beginConversion(scope,selectedProject,selected.chapter_number,
      store.get(scope,selectedProject,selected.chapter_number).title || selected.title);
    setIsConverting(true);setError('');
    try {
      const response=await authenticatedFetch('/api/novelizer/convert_chapter',{
        project_name:snapshot.project,chapter_number:snapshot.chapter,chapter_title:snapshot.title,
        scenes_text:selected.combined_script,style_profile:styleProfile,expansion_multiplier:expansionMultiplier,pov_character:povCharacter});
      const data=await response.json();
      if(data.status!=='success' || data.generation_verified!==true || typeof data.prose!=='string' || !data.prose.trim())
        throw new Error('Generation was not verified. Existing prose was retained.');
      const visible=current(epoch) && selectedRef.current.chapter===snapshot.chapter;
      const buffer=store.generated(snapshot,data.prose,visible);
      if(visible){showDraft(buffer);setGenerationReceipt(data);setSaveStatus('unsaved');}
      // Generation is a local candidate. Saving always requires the explicit save action.
    } catch(failure){if(current(epoch))setError(errorText(failure));}
    finally {if(current(epoch))setIsConverting(false);}
  }
  /** @param {number} chapterNumber @param {string} chapterTitle @param {string} prose */
  async function handleSaveDraft(chapterNumber,chapterTitle,prose) {
    const epoch=epochRef.current, project=selectedProject;
    const buffer=store.get(scope,project,chapterNumber);
    const retainedTitle=buffer.title || chapterTitle;
    if(buffer.text!==prose)store.edit(scope,project,chapterNumber,retainedTitle,prose);
    const key=JSON.stringify([scope,project,chapterNumber]);
    if(savesRef.current.has(key))return savesRef.current.get(key);
    const snapshot=store.beginSave(scope,project,chapterNumber,retainedTitle);
    setSaveStatus('saving');setError('');
    const pending=(async()=>{
      try {
        const response=await authenticatedFetch('/api/novelizer/save_draft',{
          project_name:snapshot.project,chapter_number:snapshot.chapter,chapter_title:snapshot.title,
          prose_content:snapshot.text,expected_revision:snapshot.expected_revision,request_id:snapshot.request_id});
        const data=await response.json();const updated=store.ack(snapshot,data);
        updated.error='';
        if(current(epoch) && selectedRef.current.chapter===snapshot.chapter){
          setSaveStatus(updated.dirty?'unsaved':'saved');showDraft(updated);
          setSavedChapters(previous=>[...previous.filter(row=>row.chapter_number!==snapshot.chapter),
            {chapter_number:snapshot.chapter,chapter_title:snapshot.title,prose_content:snapshot.text,revision:data.revision,word_count:data.word_count}]);
        }
      } catch(failure){
        buffer.error=errorText(failure);
        if(current(epoch) && selectedRef.current.chapter===snapshot.chapter){setSaveStatus('error');setError(errorText(failure));}
      } finally {savesRef.current.delete(key);}
    })();
    savesRef.current.set(key,pending);return pending;
  }
  /** @param {string} format */
  async function handleExportBook(format) {
    const project=selectedProject;
    try {
      const response=await authenticatedFetch('/api/novelizer/export_book',{
        project_name:project,book_title:bookTitle || project.replaceAll('_',' '),author_name:authorName,format_type:format});
      const blob=await response.blob();const url=URL.createObjectURL(blob);const anchor=document.createElement('a');
      anchor.href=url;anchor.download=`${project}_Book_Manuscript.${format==='markdown'?'md':'html'}`;
      document.body.appendChild(anchor);anchor.click();document.body.removeChild(anchor);URL.revokeObjectURL(url);
    } catch(failure){setError(errorText(failure));}
  }
  function useGeneratedCandidate() {
    if(!chapter || !currentDraft?.candidate)return;
    if(currentDraft.dirty)currentDraft.recovery.push({text:currentDraft.text,title:currentDraft.title});
    const candidate=currentDraft.candidate;currentDraft.candidate='';
    showDraft(store.edit(scope,selectedProject,chapter.chapter_number,currentDraft.title || chapter.title,candidate));setSaveStatus('unsaved');
  }
  if (!isOpen) return null;

  const currentChapObj = chapter || {};
  const visibleProse=currentDraft?.text || '';
  const totalNovelWords = savedChapters.reduce((acc, c) => acc + (c.word_count || 0), 0);
  const estBookPages = Math.ceil(totalNovelWords / 250);

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
            <span>📚 4. Manuscript Vault & Export ({totalNovelWords.toLocaleString()} Words · ~{estBookPages} pgs)</span>
          </button>
        </div>

        {/* Modal Main Content Body */}
        <div className="novelizer-body">
          {(error || currentDraft?.error || currentDraft?.recoveryError) && <p role="alert" style={{color:'#fca5a5'}}>{error || currentDraft?.error || currentDraft?.recoveryError}</p>}
          {generationReceipt && <p>Generated by {generationReceipt.provider} · {generationReceipt.model}. {generationReceipt.word_count} measured words. Factual accuracy requires author review.</p>}
          {generationReceipt?.completion_verified===false && <p>Model completion was not confirmed ({generationReceipt.completion_reason}). The returned text is a draft, not a verified complete chapter.</p>}
          {currentDraft?.candidate && <div><p>A generated candidate is retained separately from your current draft.</p><button onClick={useGeneratedCandidate}>Use generated candidate (keep a recovery copy)</button></div>}
          {currentDraft?.remote && <details><summary>Saved chapter differs from this local draft</summary><pre>{currentDraft.remote.prose_content}</pre><button onClick={()=>showDraft(store.useSaved(scope,selectedProject,chapter.chapter_number,currentDraft.remote))}>Use saved version (keep a recovery copy)</button></details>}
          {currentDraft?.recovery?.length>0 && <button onClick={()=>showDraft(store.restore(scope,selectedProject,chapter.chapter_number))}>Restore previous local draft</button>}
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
                          {chap.scenes.map(/** @param {any} s */ s => (
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
                    {currentDraft?.title || currentChapObj.title || `Chapter ${selectedChapterIndex + 1}`}
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
                    {saveStatus === 'saving' ? '🟡 Saving...' : saveStatus === 'saved' ? '🟢 Draft Saved' : saveStatus === 'error' ? 'Save not confirmed — draft retained' : currentDraft?.dirty ? 'Unsaved draft retained in this browser session' : ''}
                  </div>

                  <button
                    onClick={handleConvertChapter}
                    disabled={isConverting}
                    className="novelizer-btn-primary"
                  >
                    {isConverting ? '✨ Novelizing Chapter...' : '✨ Convert Script to Book Prose'}
                  </button>

                  <button
                    onClick={() => handleSaveDraft(currentChapObj.chapter_number, currentChapObj.title, visibleProse)}
                    disabled={!visibleProse.trim()}
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
                      {visibleProse.trim() ? visibleProse.trim().split(/\s+/).length : 0} Words
                    </span>
                  </div>
                  <textarea
                    value={visibleProse}
                    onChange={(e) => handleProseChange(e.target.value)}
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
                <p>Approximate length target. Memoir adapts supported details only and must not invent memories or sensory evidence.</p>
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
                    {expansionMultiplier}x target estimate
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
                <label>Book author <input type="text" value={authorName} onChange={event=>setAuthorName(event.target.value)} className="setup-input" placeholder="Author name for this export" /></label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '12px' }}>
                  <div>
                    <label style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'block', marginBottom: '6px' }}>Point-of-View Protagonist:</label>
                    <input
                      type="text"
                      value={povCharacter}
                      onChange={(e) => setPovCharacter(e.target.value)}
                      className="setup-input"
                      placeholder="Source-established perspective"
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
                  <span className="stat-label">Rough pages at 250 words/page; layout not measured</span>
                </div>
                <div className="stat-box">
                  <span className="stat-num">{Math.round(totalNovelWords / 200)}m</span>
                  <span className="stat-label">Rough reading time at 200 words/min</span>
                </div>
              </div>

              <div className="export-download-options">
                <h3>Publishing & Export Formats</h3>
                <p>Export saved manuscript text or an HTML print layout. Publication layout and platform acceptance require separate checks.</p>

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
                      <strong>HTML Print Layout (.html)</strong>
                      <p>Escaped manuscript text for browser printing; final PDF size and pagination are not verified.</p>
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
                        <span>{saved?.chapter_title || c.title}</span>
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
