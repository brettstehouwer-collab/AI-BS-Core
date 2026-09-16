import React from 'react';
import TerminalPanel from './TerminalPanel';
import AdvertisingTab from './AdvertisingTab';
import VisualScriptingTab from './VisualScriptingTab';

export default function NocoTelemetryTab(props) {
  const { BACKEND_URL, ORCHESTRATOR_COMMANDS, activeTab, availableModels, canvasRef, categorizeModels, chatInput, comfyuiModels, comfyuiStatus, deployMessage, devBottomTab, devChatInput, devChatMessages, devCodeInput, devCodeOutput, devCodeType, devFileName, devLeftTab, devMode, documents, fetchComfyuiModels, fetchComfyuiStatus, fetchDocuments, fetchGallery, fetchModels, fileInputRef, fireProfile, fireTextFormatted, fireTextRaw, formatTime, galleryMedia, genDimensionality, genObjective, genPhysicsTarget, gitStatus, handleChatFileUpload, handleCreateLocalAI, handleCreateLocalImage, handleCreateLocalSimulation, handleCreateMedia, handleDeleteDocument, handleDeployBlueprint, handleDevChatSubmit, handleDownloadMedia, handleDragOver, handleDrop, handleEditorDidMount, handleEnhancePrompt, handleExecuteCode, handleExecutePowershell, handleExportFireWriting, handleFileUpload, handleFormatFireWriting, handleGenerateNocoCode, handleGradeItInterview, handleOpenDocPreview, handlePaste, handleSaveFile, handleSendMessage, handleStartItInterview, handleTriggerNocoAlert, isChatUploading, isCreatingMedia, isDeploying, isDevChatLoading, isEnhancingPrompt, isExecutingCode, isExecutingPs, isFormatting, isGeneratingNocoCode, isGlobalLoading, isGrading, isItActive, isListening, isPreviewLoading, isSavingFile, isUploading, itScorecard, itTimer, kbSearchQuery, kbSearchResults, localAiCfgScale, localAiHeight, localAiNegativePrompt, localAiSeed, localAiSteps, localAiWidth, localGenProgress, localSimDuration, localSimMode, localSimTheme, mediaAspectRatio, mediaError, mediaPrompt, mediaResultUrl, mediaType, messageFeedRef, messages, monacoRef, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode, nocoTelemetry, parseSources, pollingStatusMsg, previewDocContent, previewDocName, psCommand, psOutput, saveMessage, selectedComfyModel, selectedModel, setActiveTab, setAvailableModels, setChatInput, setComfyuiModels, setComfyuiStatus, setDeployMessage, setDevBottomTab, setDevChatInput, setDevChatMessages, setDevCodeInput, setDevCodeOutput, setDevCodeType, setDevFileName, setDevLeftTab, setDevMode, setDocuments, setFireProfile, setFireTextFormatted, setFireTextRaw, setGalleryMedia, setGenDimensionality, setGenObjective, setGenPhysicsTarget, setGitStatus, setIsChatUploading, setIsCreatingMedia, setIsDeploying, setIsDevChatLoading, setIsEnhancingPrompt, setIsExecutingCode, setIsExecutingPs, setIsFormatting, setIsGeneratingNocoCode, setIsGlobalLoading, setIsGrading, setIsItActive, setIsPreviewLoading, setIsSavingFile, setIsUploading, setItScorecard, setItTimer, setKbSearchQuery, setKbSearchResults, setLocalAiCfgScale, setLocalAiHeight, setLocalAiNegativePrompt, setLocalAiSeed, setLocalAiSteps, setLocalAiWidth, setLocalGenProgress, setLocalSimDuration, setLocalSimMode, setLocalSimTheme, setMediaAspectRatio, setMediaError, setMediaPrompt, setMediaResultUrl, setMediaType, setMessages, setNocoAlert, setNocoCodePrompt, setNocoCodeType, setNocoGeneratedCode, setNocoTelemetry, setPollingStatusMsg, setPreviewDocContent, setPreviewDocName, setPsCommand, setPsOutput, setSaveMessage, setSelectedComfyModel, setSelectedModel, setShowModelModal, setSystemGitStatus, setUseAgent, setUseRag, setUseTTS, setUseWebSearch, setWorkflowMode, showModelModal, speakText, systemGitStatus, toggleListening, useAgent, useRag, useTTS, useWebSearch, workflowMode } = props;
  
  return (
    <>
      {activeTab === 'noco' && (
            <div className="noco-workspace-grid">
              
              {/* Telemetry Dials Grid */}
              <div className="noco-panel glass-panel">
                <h3>🌱 Live Aero-Agri Telemetry</h3>
                <p className="subtitle">Simulating vertical farming loop automated sensor arrays</p>
                
                <div className="telemetry-grid">
                  <div className="telemetry-card">
                    <span className="tele-icon">🌡️</span>
                    <div className="tele-lbl">Temperature</div>
                    <div className="tele-val">{nocoTelemetry.temp} °C</div>
                    <div className="tele-bar"><div className="tele-fill green" style={{width: `${(nocoTelemetry.temp/40)*100}%`}}></div></div>
                  </div>

                  <div className="telemetry-card">
                    <span className="tele-icon">⚡</span>
                    <div className="tele-lbl">Microbial Fuel Cell (MFC)</div>
                    <div className="tele-val">{nocoTelemetry.mfcOutput} mW</div>
                    <div className="tele-bar"><div className="tele-fill yellow" style={{width: `${(nocoTelemetry.mfcOutput/200)*100}%`}}></div></div>
                  </div>

                  <div className="telemetry-card">
                    <span className="tele-icon">🪴</span>
                    <div className="tele-lbl">Aeroponic Layers</div>
                    <div className="tele-val">{nocoTelemetry.aeroponicLayers} Layers</div>
                    <div className="tele-bar"><div className="tele-fill green" style={{width: `${(nocoTelemetry.aeroponicLayers/10)*100}%`}}></div></div>
                  </div>

                  <div className="telemetry-card">
                    <span className="tele-icon">💨</span>
                    <div className="tele-lbl">Carbon Dioxide</div>
                    <div className="tele-val">{nocoTelemetry.co2} ppm</div>
                    <div className="tele-bar"><div className="tele-fill orange" style={{width: `${(nocoTelemetry.co2/1500)*100}%`}}></div></div>
                  </div>

                  <div className="telemetry-card">
                    <span className="tele-icon">☀️</span>
                    <div className="tele-lbl">Lighting Intensity</div>
                    <div className="tele-val">{nocoTelemetry.lux.toLocaleString()} lx</div>
                    <div className="tele-bar"><div className="tele-fill yellow" style={{width: `${(nocoTelemetry.lux/30000)*100}%`}}></div></div>
                  </div>

                  <div className="telemetry-card">
                    <span className="tele-icon">🧪</span>
                    <div className="tele-lbl">Nutrient pH</div>
                    <div className="tele-val">{nocoTelemetry.ph} pH</div>
                    <div className="tele-bar"><div className="tele-fill green" style={{width: `${(nocoTelemetry.ph/14)*100}%`}}></div></div>
                  </div>
                </div>

                <div className="noco-alerts-card">
                  <h4>⚠️ Telemetry Diagnostic Alerts</h4>
                  {nocoAlert ? (
                    <div className="alert-message active-alert animate-pulse-border">
                      <strong>ALERT:</strong> {nocoAlert}
                    </div>
                  ) : (
                    <div className="alert-message normal-state">
                      🟢 All automated grow systems report nominal state.
                    </div>
                  )}
                  <button className="noco-alert-btn" onClick={handleTriggerNocoAlert}>
                    💥 Trigger Simulated Telemetry Anomaly
                  </button>
                </div>
              </div>

              {/* Schematic and Code builder */}
              <div className="noco-panel glass-panel">
                <h3>🛠️ Microcontroller Automation Coder</h3>
                <p className="subtitle">Synthesize micro-firmware for automated corrections</p>
                
                <div className="noco-coder-controls">
                  <div className="coder-row">
                    <label>Target Hardware Platform:</label>
                    <select value={nocoCodeType} onChange={(e) => setNocoCodeType(e.target.value)}>
                      <option value="arduino">Arduino Nano / Uno (C++)</option>
                      <option value="raspberry_pi">Raspberry Pi Pico (MicroPython)</option>
                    </select>
                  </div>

                  <textarea 
                    className="noco-prompt-input"
                    placeholder="Enter automated controller instructions..."
                    value={nocoCodePrompt}
                    onChange={(e) => setNocoCodePrompt(e.target.value)}
                  />

                  <button 
                    className="noco-btn-code" 
                    onClick={handleGenerateNocoCode}
                    disabled={isGeneratingNocoCode}
                  >
                    {isGeneratingNocoCode ? 'Compiling Instructions...' : '💾 Generate Automation Code'}
                  </button>
                </div>

                {nocoGeneratedCode && (
                  <div className="noco-code-output animate-slide-in">
                    <div className="code-header">
                      <span>Generated Firmware Snippet ({nocoCodeType})</span>
                      <button 
                        className="copy-btn" 
                        onClick={() => {
                          navigator.clipboard.writeText(nocoGeneratedCode)
                          alert("Code copied to clipboard!")
                        }}
                      >
                        📋 Copy Code
                      </button>
                    </div>
                    <pre className="code-pre"><code>{nocoGeneratedCode}</code></pre>
                  </div>
                )}
              </div>
            </div>
          )}
    </>
  );
}
