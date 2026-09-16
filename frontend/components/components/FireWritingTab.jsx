import React from 'react';
import TerminalPanel from './TerminalPanel';
import AdvertisingTab from './AdvertisingTab';
import VisualScriptingTab from './VisualScriptingTab';

export default function FireWritingTab(props) {
  const { BACKEND_URL, ORCHESTRATOR_COMMANDS, activeTab, availableModels, canvasRef, categorizeModels, chatInput, comfyuiModels, comfyuiStatus, deployMessage, devBottomTab, devChatInput, devChatMessages, devCodeInput, devCodeOutput, devCodeType, devFileName, devLeftTab, devMode, documents, fetchComfyuiModels, fetchComfyuiStatus, fetchDocuments, fetchGallery, fetchModels, fileInputRef, fireProfile, fireTextFormatted, fireTextRaw, formatTime, galleryMedia, genDimensionality, genObjective, genPhysicsTarget, gitStatus, handleChatFileUpload, handleCreateLocalAI, handleCreateLocalImage, handleCreateLocalSimulation, handleCreateMedia, handleDeleteDocument, handleDeployBlueprint, handleDevChatSubmit, handleDownloadMedia, handleDragOver, handleDrop, handleEditorDidMount, handleEnhancePrompt, handleExecuteCode, handleExecutePowershell, handleExportFireWriting, handleFileUpload, handleFormatFireWriting, handleGenerateNocoCode, handleGradeItInterview, handleOpenDocPreview, handlePaste, handleSaveFile, handleSendMessage, handleStartItInterview, handleTriggerNocoAlert, isChatUploading, isCreatingMedia, isDeploying, isDevChatLoading, isEnhancingPrompt, isExecutingCode, isExecutingPs, isFormatting, isGeneratingNocoCode, isGlobalLoading, isGrading, isItActive, isListening, isPreviewLoading, isSavingFile, isUploading, itScorecard, itTimer, kbSearchQuery, kbSearchResults, localAiCfgScale, localAiHeight, localAiNegativePrompt, localAiSeed, localAiSteps, localAiWidth, localGenProgress, localSimDuration, localSimMode, localSimTheme, mediaAspectRatio, mediaError, mediaPrompt, mediaResultUrl, mediaType, messageFeedRef, messages, monacoRef, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode, nocoTelemetry, parseSources, pollingStatusMsg, previewDocContent, previewDocName, psCommand, psOutput, saveMessage, selectedComfyModel, selectedModel, setActiveTab, setAvailableModels, setChatInput, setComfyuiModels, setComfyuiStatus, setDeployMessage, setDevBottomTab, setDevChatInput, setDevChatMessages, setDevCodeInput, setDevCodeOutput, setDevCodeType, setDevFileName, setDevLeftTab, setDevMode, setDocuments, setFireProfile, setFireTextFormatted, setFireTextRaw, setGalleryMedia, setGenDimensionality, setGenObjective, setGenPhysicsTarget, setGitStatus, setIsChatUploading, setIsCreatingMedia, setIsDeploying, setIsDevChatLoading, setIsEnhancingPrompt, setIsExecutingCode, setIsExecutingPs, setIsFormatting, setIsGeneratingNocoCode, setIsGlobalLoading, setIsGrading, setIsItActive, setIsPreviewLoading, setIsSavingFile, setIsUploading, setItScorecard, setItTimer, setKbSearchQuery, setKbSearchResults, setLocalAiCfgScale, setLocalAiHeight, setLocalAiNegativePrompt, setLocalAiSeed, setLocalAiSteps, setLocalAiWidth, setLocalGenProgress, setLocalSimDuration, setLocalSimMode, setLocalSimTheme, setMediaAspectRatio, setMediaError, setMediaPrompt, setMediaResultUrl, setMediaType, setMessages, setNocoAlert, setNocoCodePrompt, setNocoCodeType, setNocoGeneratedCode, setNocoTelemetry, setPollingStatusMsg, setPreviewDocContent, setPreviewDocName, setPsCommand, setPsOutput, setSaveMessage, setSelectedComfyModel, setSelectedModel, setShowModelModal, setSystemGitStatus, setUseAgent, setUseRag, setUseTTS, setUseWebSearch, setWorkflowMode, showModelModal, speakText, systemGitStatus, toggleListening, useAgent, useRag, useTTS, useWebSearch, workflowMode } = props;
  
  return (
    <>
      {activeTab === 'firewrite' && (
            <div className="fire-writing-container">
              <div className="fire-writing-toolbar glass-panel" style={{ padding: '16px', borderRadius: '8px', marginBottom: '20px' }}>
                <div className="fire-controls-left">
                  <span style={{ fontWeight: '600', marginRight: '10px' }}>Formatting Style Profile:</span>
                  <select 
                    value={fireProfile}
                    onChange={(e) => setFireProfile(e.target.value)}
                    style={{ background: 'var(--bg-main)', border: '1px solid var(--border-glow)', color: 'white', padding: '6px 12px', borderRadius: '4px' }}
                  >
                    <option value="fire_writing">🔥 Strict Structural Formatting (No words altered)</option>
                    <option value="professional">💼 Professional Polish (Emails, Cover Letters)</option>
                    <option value="creative">📖 Creative Prose (Narrative & Story polish)</option>
                    <option value="journal">📓 Journal Outline (Summaries & Action points)</option>
                  </select>
                </div>

                <div className="fire-buttons-right" style={{ display: 'flex', gap: '12px' }}>
                  <button className="format-button" onClick={handleFormatFireWriting}>
                    {isFormatting ? 'Processing AI...' : '✨ Execute Formatting'}
                  </button>
                  <button 
                    className="export-button" 
                    onClick={handleExportFireWriting}
                    disabled={!fireTextFormatted}
                  >
                    📥 Download Export (.md)
                  </button>
                </div>
              </div>

              <div className="split-pane">
                <div className="pane input-pane">
                  <div className="pane-title">Raw Fire Writing</div>
                  <textarea 
                    placeholder="Pour out your raw, unfiltered stream of consciousness here..."
                    value={fireTextRaw}
                    onChange={(e) => setFireTextRaw(e.target.value)}
                  />
                </div>
                <div className="pane output-pane">
                  <div className="pane-title">Structured Output</div>
                  <textarea 
                    readOnly
                    placeholder="AI formatted structured text outputs will appear here..."
                    value={fireTextFormatted}
                  />
                </div>
              </div>
            </div>
          )}
    </>
  );
}
