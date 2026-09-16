import React from 'react';
import Editor from '@monaco-editor/react';
import TerminalPanel from './TerminalPanel';
import AdvertisingTab from '../components/AdvertisingTab';
import VisualScriptingTab from '../components/VisualScriptingTab';

export default function TerminalPanelWrapper(props) {
  const { BACKEND_URL, ORCHESTRATOR_COMMANDS, activeTab, availableModels, canvasRef, categorizeModels, chatInput, comfyuiModels, comfyuiStatus, deployMessage, devBottomTab, devChatInput, devChatMessages, devCodeInput, devCodeOutput, devCodeType, devFileName, devLeftTab, devMode, documents, fetchComfyuiModels, fetchComfyuiStatus, fetchDocuments, fetchGallery, fetchModels, fileInputRef, fireProfile, fireTextFormatted, fireTextRaw, formatTime, galleryMedia, genDimensionality, genObjective, genPhysicsTarget, gitStatus, handleChatFileUpload, handleCreateLocalAI, handleCreateLocalImage, handleCreateLocalSimulation, handleCreateMedia, handleDeleteDocument, handleDeployBlueprint, handleDevChatSubmit, handleDownloadMedia, handleDragOver, handleDrop, handleEditorDidMount, handleEnhancePrompt, handleExecuteCode, handleExecutePowershell, handleExportFireWriting, handleFileUpload, handleFormatFireWriting, handleGenerateNocoCode, handleGradeItInterview, handleOpenDocPreview, handlePaste, handleSaveFile, handleSendMessage, handleStartItInterview, handleTriggerNocoAlert, isChatUploading, isCreatingMedia, isDeploying, isDevChatLoading, isEnhancingPrompt, isExecutingCode, isExecutingPs, isFormatting, isGeneratingNocoCode, isGlobalLoading, isGrading, isItActive, isListening, isPreviewLoading, isSavingFile, isUploading, itScorecard, itTimer, kbSearchQuery, kbSearchResults, localAiCfgScale, localAiHeight, localAiNegativePrompt, localAiSeed, localAiSteps, localAiWidth, localGenProgress, localSimDuration, localSimMode, localSimTheme, mediaAspectRatio, mediaError, mediaPrompt, mediaResultUrl, mediaType, messageFeedRef, messages, monacoRef, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode, nocoTelemetry, parseSources, pollingStatusMsg, previewDocContent, previewDocName, psCommand, psOutput, saveMessage, selectedComfyModel, selectedModel, setActiveTab, setAvailableModels, setChatInput, setComfyuiModels, setComfyuiStatus, setDeployMessage, setDevBottomTab, setDevChatInput, setDevChatMessages, setDevCodeInput, setDevCodeOutput, setDevCodeType, setDevFileName, setDevLeftTab, setDevMode, setDocuments, setFireProfile, setFireTextFormatted, setFireTextRaw, setGalleryMedia, setGenDimensionality, setGenObjective, setGenPhysicsTarget, setGitStatus, setIsChatUploading, setIsCreatingMedia, setIsDeploying, setIsDevChatLoading, setIsEnhancingPrompt, setIsExecutingCode, setIsExecutingPs, setIsFormatting, setIsGeneratingNocoCode, setIsGlobalLoading, setIsGrading, setIsItActive, setIsPreviewLoading, setIsSavingFile, setIsUploading, setItScorecard, setItTimer, setKbSearchQuery, setKbSearchResults, setLocalAiCfgScale, setLocalAiHeight, setLocalAiNegativePrompt, setLocalAiSeed, setLocalAiSteps, setLocalAiWidth, setLocalGenProgress, setLocalSimDuration, setLocalSimMode, setLocalSimTheme, setMediaAspectRatio, setMediaError, setMediaPrompt, setMediaResultUrl, setMediaType, setMessages, setNocoAlert, setNocoCodePrompt, setNocoCodeType, setNocoGeneratedCode, setNocoTelemetry, setPollingStatusMsg, setPreviewDocContent, setPreviewDocName, setPsCommand, setPsOutput, setSaveMessage, setSelectedComfyModel, setSelectedModel, setShowModelModal, setSystemGitStatus, setUseAgent, setUseRag, setUseTTS, setUseWebSearch, setWorkflowMode, showModelModal, speakText, systemGitStatus, toggleListening, useAgent, useRag, useTTS, useWebSearch, workflowMode } = props;
  
  return (
    <>
      {activeTab === 'powershell' && (
            <div className="powershell-container" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '16px', background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <h3 style={{ margin: 0, color: '#fff' }}>Windows Administrative PowerShell</h3>
                <p style={{ margin: '4px 0 0 0', color: '#888', fontSize: '0.85rem' }}>Execute raw PowerShell commands directly against your backend infrastructure. Warning: This shell inherits the backend's privileges.</p>
              </div>
              <TerminalPanel backendUrl={BACKEND_URL} />
            </div>
          )}
    </>
  );
}
