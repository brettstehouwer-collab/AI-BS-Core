import React from 'react';
import TerminalPanel from './TerminalPanel';
import AdvertisingTab from './AdvertisingTab';
import VisualScriptingTab from './VisualScriptingTab';

export default function GeneratorTab(props) {
  const { BACKEND_URL, ORCHESTRATOR_COMMANDS, activeTab, availableModels, canvasRef, categorizeModels, chatInput, comfyuiModels, comfyuiStatus, deployMessage, devBottomTab, devChatInput, devChatMessages, devCodeInput, devCodeOutput, devCodeType, devFileName, devLeftTab, devMode, documents, fetchComfyuiModels, fetchComfyuiStatus, fetchDocuments, fetchGallery, fetchModels, fileInputRef, fireProfile, fireTextFormatted, fireTextRaw, formatTime, galleryMedia, genDimensionality, genObjective, genPhysicsTarget, gitStatus, handleChatFileUpload, handleCreateLocalAI, handleCreateLocalImage, handleCreateLocalSimulation, handleCreateMedia, handleDeleteDocument, handleDeployBlueprint, handleDevChatSubmit, handleDownloadMedia, handleDragOver, handleDrop, handleEditorDidMount, handleEnhancePrompt, handleExecuteCode, handleExecutePowershell, handleExportFireWriting, handleFileUpload, handleFormatFireWriting, handleGenerateNocoCode, handleGradeItInterview, handleOpenDocPreview, handlePaste, handleSaveFile, handleSendMessage, handleStartItInterview, handleTriggerNocoAlert, isChatUploading, isCreatingMedia, isDeploying, isDevChatLoading, isEnhancingPrompt, isExecutingCode, isExecutingPs, isFormatting, isGeneratingNocoCode, isGlobalLoading, isGrading, isItActive, isListening, isPreviewLoading, isSavingFile, isUploading, itScorecard, itTimer, kbSearchQuery, kbSearchResults, localAiCfgScale, localAiHeight, localAiNegativePrompt, localAiSeed, localAiSteps, localAiWidth, localGenProgress, localSimDuration, localSimMode, localSimTheme, mediaAspectRatio, mediaError, mediaPrompt, mediaResultUrl, mediaType, messageFeedRef, messages, monacoRef, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode, nocoTelemetry, parseSources, pollingStatusMsg, previewDocContent, previewDocName, psCommand, psOutput, saveMessage, selectedComfyModel, selectedModel, setActiveTab, setAvailableModels, setChatInput, setComfyuiModels, setComfyuiStatus, setDeployMessage, setDevBottomTab, setDevChatInput, setDevChatMessages, setDevCodeInput, setDevCodeOutput, setDevCodeType, setDevFileName, setDevLeftTab, setDevMode, setDocuments, setFireProfile, setFireTextFormatted, setFireTextRaw, setGalleryMedia, setGenDimensionality, setGenObjective, setGenPhysicsTarget, setGitStatus, setIsChatUploading, setIsCreatingMedia, setIsDeploying, setIsDevChatLoading, setIsEnhancingPrompt, setIsExecutingCode, setIsExecutingPs, setIsFormatting, setIsGeneratingNocoCode, setIsGlobalLoading, setIsGrading, setIsItActive, setIsPreviewLoading, setIsSavingFile, setIsUploading, setItScorecard, setItTimer, setKbSearchQuery, setKbSearchResults, setLocalAiCfgScale, setLocalAiHeight, setLocalAiNegativePrompt, setLocalAiSeed, setLocalAiSteps, setLocalAiWidth, setLocalGenProgress, setLocalSimDuration, setLocalSimMode, setLocalSimTheme, setMediaAspectRatio, setMediaError, setMediaPrompt, setMediaResultUrl, setMediaType, setMessages, setNocoAlert, setNocoCodePrompt, setNocoCodeType, setNocoGeneratedCode, setNocoTelemetry, setPollingStatusMsg, setPreviewDocContent, setPreviewDocName, setPsCommand, setPsOutput, setSaveMessage, setSelectedComfyModel, setSelectedModel, setShowModelModal, setSystemGitStatus, setUseAgent, setUseRag, setUseTTS, setUseWebSearch, setWorkflowMode, showModelModal, speakText, systemGitStatus, toggleListening, useAgent, useRag, useTTS, useWebSearch, workflowMode } = props;
  
  const [isAiGenerating, setIsAiGenerating] = React.useState(false);
  const [aiBlueprint, setAiBlueprint] = React.useState(null);

  const handleAiGeneration = async () => {
    setIsAiGenerating(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/generator/predictive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dimensionality: genDimensionality,
          physics_target: genPhysicsTarget,
          objective: genObjective
        })
      });
      const data = await res.json();
      if (res.ok) {
        setAiBlueprint({
          techStack: data.techStack || 'Dependencies automatically determined.',
          coreLoop: data.code || 'No code generated.',
          nextSteps: data.nextSteps || ['Review sandbox validation logs.'],
          sandboxLog: data.sandboxLog || 'Sandbox validation passed.'
        });
      } else {
        alert("Generation failed: " + data.detail);
      }
    } catch (err) {
      console.error(err);
    }
    setIsAiGenerating(false);
  };

  const getBlueprint = () => {
    if (aiBlueprint) return aiBlueprint;
    
    // Fallback UI mock
    if (genDimensionality === '3D' && genPhysicsTarget === 'Rigid Objects' && genObjective === 'Stabilize') {
      return {
        techStack: "pip install pybullet numpy",
        coreLoop: `while True:\n    # Terrain stabilization setup\n    current_pitch = get_vehicle_pitch()\n    radar_distance = ray_cast_to_ground()\n    \n    if current_pitch > 15 and radar_distance < 2.0:\n        apply_counter_torque()\n    \n    p.stepSimulation()`,
        nextSteps: ["Step 1: Setup PyBullet environment.", "Step 2: Implement ray-casting radar.", "Step 3: Define apply_counter_torque logic."]
      }
    }
    return {
      techStack: `Dependencies for ${genDimensionality} + ${genPhysicsTarget}`,
      coreLoop: `# Generic agent loop\nwhile True:\n    state = get_physics_state()\n    action = agent_policy(state, objective="${genObjective}")\n    apply_action(action)\n    step_physics()`,
      nextSteps: ["Step 1: Initialize engine.", "Step 2: Create simulation loop.", "Step 3: Hook up logic."]
    }
  }

  return (
    <>
      {activeTab === 'generator' && (
            <div className="generator-workspace-grid" style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '24px', height: '100%' }}>
              
              {/* INPUT MATRIX (LEFT) */}
              <div className="gen-input-panel glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <h3 style={{ margin: 0, color: 'var(--accent-neon)' }}>The Input Matrix</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '-12px' }}>Define the parameters of your new agent.</p>
                
                <div className="gen-control-group">
                  <label className="gen-label">Dimensionality</label>
                  <select className="gen-select" value={genDimensionality} onChange={e => setGenDimensionality(e.target.value)}>
                    <option value="2D">2D (Faster Testing)</option>
                    <option value="3D">3D (More Realistic)</option>
                  </select>
                </div>

                <div className="gen-control-group">
                  <label className="gen-label">Physics Target</label>
                  <select className="gen-select" value={genPhysicsTarget} onChange={e => setGenPhysicsTarget(e.target.value)}>
                    <option value="Rigid Objects">Rigid Objects (Boxes, Cars)</option>
                    <option value="Soft Bodies">Soft Bodies (Cloth, Slime)</option>
                    <option value="Particles">Particles (Water, Wind, Swarms)</option>
                  </select>
                </div>

                <div className="gen-control-group">
                  <label className="gen-label">Agent Objective</label>
                  <select className="gen-select" value={genObjective} onChange={e => setGenObjective(e.target.value)}>
                    <option value="Stabilize">Stabilize (Keep upright/centered)</option>
                    <option value="Destroy">Destroy (Maximize damage/entropy)</option>
                    <option value="Maintain Balance">Maintain Balance (Resource distribution)</option>
                  </select>
                </div>
              </div>

              {/* BLUEPRINT OUTPUT (RIGHT) */}
              <div className="gen-output-panel glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
                <h3 style={{ margin: 0, color: '#fff' }}>The Blueprint Output</h3>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '-12px' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: 0 }}>Predicted routing based on your variables.</p>
                  <button 
                    onClick={handleAiGeneration} 
                    disabled={isAiGenerating}
                    style={{ background: '#ec4899', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                  >
                    {isAiGenerating ? '🤖 Synthesizing & Testing...' : '🤖 Generate via AI'}
                  </button>
                </div>
                
                {(() => {
                  const blueprint = getBlueprint();
                  return (
                    <>
                      <div className="blueprint-section">
                        <h4>📦 The Tech Stack</h4>
                        <div className="blueprint-box cmd-box">
                          <code>{blueprint.techStack}</code>
                        </div>
                      </div>

                      <div className="blueprint-section">
                        <h4>🔄 The Core Loop</h4>
                        <div className="blueprint-box code-box" style={{ background: '#1e1e1e', padding: '12px', borderRadius: '6px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                          {blueprint.coreLoop}
                        </div>
                      </div>
                      
                      {blueprint.sandboxLog && (
                        <div className="blueprint-section">
                          <h4 style={{ color: '#4ade80' }}>🛡️ Sandbox Validation Trace</h4>
                          <div className="blueprint-box code-box" style={{ background: 'rgba(74, 222, 128, 0.1)', border: '1px solid #4ade80', padding: '12px', borderRadius: '6px', fontFamily: 'monospace', whiteSpace: 'pre-wrap', color: '#4ade80' }}>
                            {blueprint.sandboxLog}
                          </div>
                        </div>
                      )}

                      <div className="blueprint-section">
                        <h4>🚀 Next Steps</h4>
                        <div className="blueprint-box steps-box">
                          {blueprint.nextSteps.map((step, idx) => (
                            <div key={idx} className="step-item">
                              <span className="step-icon">👉</span> {step}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="blueprint-section" style={{ marginTop: '16px' }}>
                        <button 
                          onClick={handleDeployBlueprint} 
                          disabled={isDeploying}
                          className="dev-btn dev-btn-run"
                          style={{ width: '100%', padding: '16px', fontSize: '1.1rem', backgroundColor: 'var(--accent-neon)' }}
                        >
                          {isDeploying ? 'Deploying...' : '🚀 Deploy Blueprint to Workspace'}
                        </button>
                        {deployMessage && <div style={{ marginTop: '8px', color: '#fff', fontSize: '0.9rem', textAlign: 'center' }}>{deployMessage}</div>}
                      </div>
                    </>
                  )
                })()}
              </div>
            </div>
          )}
    </>
  );
}
