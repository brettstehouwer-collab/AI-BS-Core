import React, { useState, useEffect } from 'react';
import TerminalPanel from './TerminalPanel';
import AdvertisingTab from './AdvertisingTab';
import VisualScriptingTab from './VisualScriptingTab';

export default function KnowledgeBaseTab(props) {
  const { BACKEND_URL, ORCHESTRATOR_COMMANDS, activeTab, availableModels, canvasRef, categorizeModels, chatInput, comfyuiModels, comfyuiStatus, deployMessage, devBottomTab, devChatInput, devChatMessages, devCodeInput, devCodeOutput, devCodeType, devFileName, devLeftTab, devMode, documents, fetchComfyuiModels, fetchComfyuiStatus, fetchDocuments, fetchGallery, fetchModels, fileInputRef, fireProfile, fireTextFormatted, fireTextRaw, formatTime, galleryMedia, genDimensionality, genObjective, genPhysicsTarget, gitStatus, handleChatFileUpload, handleCreateLocalAI, handleCreateLocalImage, handleCreateLocalSimulation, handleCreateMedia, handleDeleteDocument, handleDeployBlueprint, handleDevChatSubmit, handleDownloadMedia, handleDragOver, handleDrop, handleEditorDidMount, handleEnhancePrompt, handleExecuteCode, handleExecutePowershell, handleExportFireWriting, handleFileUpload, handleFormatFireWriting, handleGenerateNocoCode, handleGradeItInterview, handleOpenDocPreview, handlePaste, handleSaveFile, handleSendMessage, handleStartItInterview, handleTriggerNocoAlert, isChatUploading, isCreatingMedia, isDeploying, isDevChatLoading, isEnhancingPrompt, isExecutingCode, isExecutingPs, isFormatting, isGeneratingNocoCode, isGlobalLoading, isGrading, isItActive, isListening, isPreviewLoading, isSavingFile, isUploading, itScorecard, itTimer, kbSearchQuery, kbSearchResults, localAiCfgScale, localAiHeight, localAiNegativePrompt, localAiSeed, localAiSteps, localAiWidth, localGenProgress, localSimDuration, localSimMode, localSimTheme, mediaAspectRatio, mediaError, mediaPrompt, mediaResultUrl, mediaType, messageFeedRef, messages, monacoRef, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode, nocoTelemetry, parseSources, pollingStatusMsg, previewDocContent, previewDocName, psCommand, psOutput, saveMessage, selectedComfyModel, selectedModel, setActiveTab, setAvailableModels, setChatInput, setComfyuiModels, setComfyuiStatus, setDeployMessage, setDevBottomTab, setDevChatInput, setDevChatMessages, setDevCodeInput, setDevCodeOutput, setDevCodeType, setDevFileName, setDevLeftTab, setDevMode, setDocuments, setFireProfile, setFireTextFormatted, setFireTextRaw, setGalleryMedia, setGenDimensionality, setGenObjective, setGenPhysicsTarget, setGitStatus, setIsChatUploading, setIsCreatingMedia, setIsDeploying, setIsDevChatLoading, setIsEnhancingPrompt, setIsExecutingCode, setIsExecutingPs, setIsFormatting, setIsGeneratingNocoCode, setIsGlobalLoading, setIsGrading, setIsItActive, setIsPreviewLoading, setIsSavingFile, setIsUploading, setItScorecard, setItTimer, setKbSearchQuery, setKbSearchResults, setLocalAiCfgScale, setLocalAiHeight, setLocalAiNegativePrompt, setLocalAiSeed, setLocalAiSteps, setLocalAiWidth, setLocalGenProgress, setLocalSimDuration, setLocalSimMode, setLocalSimTheme, setMediaAspectRatio, setMediaError, setMediaPrompt, setMediaResultUrl, setMediaType, setMessages, setNocoAlert, setNocoCodePrompt, setNocoCodeType, setNocoGeneratedCode, setNocoTelemetry, setPollingStatusMsg, setPreviewDocContent, setPreviewDocName, setPsCommand, setPsOutput, setSaveMessage, setSelectedComfyModel, setSelectedModel, setShowModelModal, setSystemGitStatus, setUseAgent, setUseRag, setUseTTS, setUseWebSearch, setWorkflowMode, showModelModal, speakText, systemGitStatus, toggleListening, useAgent, useRag, useTTS, useWebSearch, workflowMode } = props;

  const [contextStatus, setContextStatus] = useState(null);
  const [recoveredData, setRecoveredData] = useState(null);
  const [isIngestingManual, setIsIngestingManual] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState([]);
  const [isRagSearching, setIsRagSearching] = useState(false);
  const [ragPage, setRagPage] = useState(1);

  const fetchContextStatus = async () => {
    try {
      const res = await fetch(`${getApiBase()}/api/context/status`);
      if (res.ok) {
        const data = await res.json();
        setContextStatus(data);
      }
    } catch (e) {
      console.warn('Context ingest telemetry offline:', e);
    }
  };

  const fetchRecoveredData = async () => {
    try {
      const res = await fetch(`${getApiBase()}/api/context/recovered`);
      if (res.ok) {
        const data = await res.json();
        setRecoveredData(data);
      }
    } catch (e) {
      console.warn('Recovered data endpoint offline:', e);
    }
  };

  const handleRagSearch = async (e) => {
    e.preventDefault();
    if (!ragQuery.trim()) return;
    setIsRagSearching(true);
    try {
      const res = await fetch(`${getApiBase()}/api/context/search?q=${encodeURIComponent(ragQuery)}`);
      if (res.ok) {
        const data = await res.json();
        setRagResults(data.results || []);
        setRagPage(1);
      }
    } catch (err) {
      console.error('RAG Search failed:', err);
    } finally {
      setIsRagSearching(false);
    }
  };

  const handleForceIngest = async () => {
    setIsIngestingManual(true);
    try {
      await fetch(`${getApiBase()}/api/context/trigger`, { method: 'POST' });
      await fetchContextStatus();
      await fetchRecoveredData();
    } catch (e) {
      console.error(e);
    } finally {
      setIsIngestingManual(false);
    }
  };

  useEffect(() => {
    fetchContextStatus();
    fetchRecoveredData();
    const interval = setInterval(fetchContextStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const filteredDocs = documents ? documents.filter(doc => 
    doc.toLowerCase().includes((kbSearchQuery || '').toLowerCase())
  ) : [];

  return (
    <>
      {activeTab === 'knowledge' && (
            <div className="kb-container">
              {/* LIVE CONTEXT INGESTOR TELEMETRY STREAM PANEL */}
              <div className="kb-search-panel glass-panel" style={{ padding: '20px', borderRadius: '12px', marginBottom: '24px', border: '1px solid rgba(0, 240, 255, 0.25)', background: 'linear-gradient(135deg, rgba(10,15,30,0.9), rgba(5,10,20,0.95))' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.25rem', color: '#00f0ff' }}>
                      ⚡ Full PC 5-Drive Context Ingestor & RAG Vector Engine
                    </h3>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Auto-indexing across drives: <strong>C:\, D:\ (Server), E:\ (space), F:\, G:\ (Data)</strong>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <span style={{ padding: '4px 10px', borderRadius: '20px', background: 'rgba(0, 255, 128, 0.15)', color: '#00ff80', border: '1px solid rgba(0, 255, 128, 0.3)', fontSize: '0.8rem', fontWeight: 600 }}>
                      🟢 5-Drive Ingest Active
                    </span>
                    <button 
                      onClick={handleForceIngest}
                      disabled={isIngestingManual}
                      style={{ padding: '6px 14px', background: 'linear-gradient(135deg, #00f0ff, #7000ff)', border: 'none', borderRadius: '6px', color: '#fff', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', opacity: isIngestingManual ? 0.6 : 1 }}
                    >
                      {isIngestingManual ? '⏳ Ingesting & Auditing...' : '🔄 Force 5-Drive Ingest Now'}
                    </button>
                  </div>
                </div>

                {/* INTERACTIVE RAG VECTOR SEARCH BAR */}
                <form onSubmit={handleRagSearch} style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
                  <input 
                    type="text"
                    value={ragQuery}
                    onChange={(e) => setRagQuery(e.target.value)}
                    placeholder="🔍 Search all 5 PC drives for code, book snippets, scripts, or API keys..."
                    style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(0, 240, 255, 0.3)', color: '#fff', fontSize: '0.95rem', outline: 'none' }}
                  />
                  <button type="submit" disabled={isRagSearching} style={{ padding: '12px 24px', background: '#00f0ff', color: '#050a14', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
                    {isRagSearching ? 'Searching...' : 'Search RAG Memory'}
                  </button>
                </form>

                {/* RAG SEARCH RESULTS FEED */}
                {ragResults.length > 0 && (
                  <div style={{ background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(0, 240, 255, 0.2)', marginBottom: '20px' }}>
                    <h4 style={{ margin: '0 0 12px 0', color: '#00f0ff', fontSize: '0.95rem' }}>
                      🔎 Found {ragResults.length} Matching Files Across 5 Drives (Showing {Math.min(ragPage * 10, ragResults.length)} of {ragResults.length}):
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {ragResults.slice(0, ragPage * 10).map((resItem, idx) => (
                        <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <strong style={{ color: '#00ff80', fontSize: '0.9rem' }}>{resItem.path}</strong>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{resItem.mtime}</span>
                          </div>
                          <pre style={{ margin: 0, fontSize: '0.8rem', color: '#cbd5e1', whiteSpace: 'pre-wrap', maxHeight: '100px', overflow: 'hidden' }}>
                            {resItem.snippet}
                          </pre>
                        </div>
                      ))}
                    </div>
                    {ragPage * 10 < ragResults.length && (
                      <button onClick={() => setRagPage(prev => prev + 1)} style={{ marginTop: '12px', padding: '8px 16px', background: 'rgba(255,255,255,0.08)', color: '#fff', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}>
                        📄 Load Next 10 Results
                      </button>
                    )}
                  </div>
                )}

                {/* RECOVERED INTELLIGENCE VAULT CARD */}
                {recoveredData && recoveredData.total_recovered_assets > 0 && (
                  <div style={{ background: 'rgba(245, 158, 11, 0.08)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.3)', marginBottom: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <h4 style={{ margin: 0, color: '#f59e0b', fontSize: '0.95rem' }}>
                        🔑 Recovered Intelligence & Lost API Key Vault ({recoveredData.total_recovered_assets} Found)
                      </h4>
                      <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>Last Audited: {recoveredData.last_audited}</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {recoveredData.recovered_items.slice(0, 5).map((item, i) => (
                        <div key={i} style={{ fontSize: '0.85rem', color: '#e2e8f0', background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
                          <span><strong>{item.type}:</strong> <code>{item.key_snippet}</code></span>
                          <span style={{ opacity: 0.7, fontSize: '0.75rem' }}>{item.source_file}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {contextStatus && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Ingested Files</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#00f0ff' }}>
                        {contextStatus.total_files ? contextStatus.total_files.toLocaleString() : '0'}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Payload Size</div>
                      <div style={{ fontSize: '1.3rem', fontWeight: 'bold', color: '#a855f7' }}>
                        {contextStatus.total_bytes ? (contextStatus.total_bytes / (1024 * 1024)).toFixed(2) + ' MB' : '0 MB'}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Last Ingest Timestamp</div>
                      <div style={{ fontSize: '0.95rem', fontWeight: '600', color: '#00ff80', marginTop: '4px' }}>
                        {contextStatus.last_updated || 'Active'}
                      </div>
                    </div>
                  </div>
                )}

                {/* LIVE GRABBED FILE FEED */}
                <h4 style={{ margin: '14px 0 10px 0', fontSize: '0.9rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  📥 Live Ingested File Stream
                </h4>
                <div style={{ maxHeight: '220px', overflowY: 'auto', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)', padding: '10px' }}>
                  {contextStatus && contextStatus.recent_grabbed_files ? (
                    contextStatus.recent_grabbed_files.map((item, fIdx) => (
                      <div key={fIdx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 10px', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: '0.85rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                          <span>{item.ext === '.md' || item.ext === '.pdf' ? '📄' : item.ext === '.py' ? '🐍' : '💻'}</span>
                          <span style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>{item.path}</span>
                        </div>
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexShrink: 0 }}>
                          <span style={{ color: '#00f0ff', fontSize: '0.75rem' }}>{(item.size / 1024).toFixed(1)} KB</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{item.mtime}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic', padding: '10px' }}>
                      Loading live grabbed file feed...
                    </div>
                  )}
                </div>
              </div>

              <div className="upload-box" onClick={() => document.getElementById('kb-file-input').click()}>
                <div className="upload-icon">📄</div>
                <h3>{isUploading ? 'Ingesting Document...' : 'Upload DOCX, PDF, TXT or MD'}</h3>
                <p style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
                  Click to select a file to ingest into the local vector database.
                </p>
                <input 
                  type="file" 
                  id="kb-file-input" 
                  accept=".txt,.pdf,.docx,.md" 
                  style={{ display: 'none' }} 
                  onChange={handleFileUpload} 
                  disabled={isUploading}
                />
              </div>

              {/* SOVEREIGN VAULTS STATUS */}
              <div className="kb-search-panel glass-panel" style={{ padding: '20px', borderRadius: '8px', marginBottom: '20px', borderLeft: '4px solid var(--primary)' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '1.1rem' }}>🛡️ Sovereign Knowledge Vaults Status</h4>
                <p style={{ margin: '0 0 15px 0', color: 'var(--text-muted)' }}>
                  Successfully ingested <strong>49 semantic chunks</strong> into ChromaDB from the Stehouwer Reality architecture.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
                  <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}>
                    <strong>📁 NoCo_Ventures/</strong>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No co.md, Nocorf1.md</div>
                  </div>
                  <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}>
                    <strong>📁 Fire_Writing/</strong>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>The Master Plan, Consolidation</div>
                  </div>
                  <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}>
                    <strong>📁 Marketing_and_Publishing/</strong>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>WebDesign.md (Django Roadmap)</div>
                  </div>
                </div>
              </div>

              {/* SEARCH BLOCK */}
              <div className="kb-search-panel glass-panel" style={{ padding: '20px', borderRadius: '8px', marginBottom: '32px' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <span style={{ fontSize: '1.2rem' }}>🔍</span>
                  <input 
                    type="text"
                    placeholder="Search document index or search deep text contents..."
                    value={kbSearchQuery}
                    onChange={(e) => setKbSearchQuery(e.target.value)}
                    style={{ flex: 1, padding: '10px 16px', background: 'var(--bg-main)' }}
                  />
                </div>

                {kbSearchResults.length > 0 && (
                  <div className="kb-search-results animate-slide-in" style={{ marginTop: '16px' }}>
                    <h4 style={{ color: 'var(--accent-neon)', marginBottom: '10px' }}>Deep Content Matches:</h4>
                    <div style={{ display: 'flex', flex_direction: 'column', gap: '10px' }}>
                      {kbSearchResults.map((res, rIdx) => (
                        <div key={rIdx} className="search-result-item" style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', border: '1px solid var(--border-glow)', borderRadius: '6px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                            <strong>Source File: {res.source}</strong>
                            <span>Similarity Match: {((1 - res.distance) * 100).toFixed(1)}%</span>
                          </div>
                          <p style={{ fontSize: '0.85rem', fontStyle: 'italic', color: 'var(--text-primary)' }}>"{res.content}"</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <h3>Current Indexed Documents</h3>
              <div className="doc-list" style={{ marginTop: '16px' }}>
                {filteredDocs.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    {kbSearchQuery ? 'No documents match your search query.' : 'No documents uploaded yet.'}
                  </p>
                ) : (
                  filteredDocs.map((doc, idx) => (
                    <div key={idx} className="doc-item">
                      <span>📄</span>
                      <strong 
                        className="preview-doc-link" 
                        onClick={() => handleOpenDocPreview(doc)}
                        title="Click to preview file"
                        style={{ cursor: 'pointer', color: 'var(--accent-neon)' }}
                      >
                        {doc}
                      </strong>
                      <span style={{ marginLeft: 'auto', color: 'var(--success-color)', fontSize: '0.9rem', marginRight: '16px' }}>Indexed</span>
                      <button 
                        className="delete-doc-button"
                        onClick={() => handleDeleteDocument(doc)}
                        style={{ color: '#ef4444', fontSize: '1.2rem', padding: '0 8px', background: 'transparent', border: 'none', cursor: 'pointer' }}
                      >
                        🗑️
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
    </>
  );
}
