/**
 * AppContext — owns all shared application state and provides it via React Context.
 *
 * Replaces the "god props" anti-pattern where every tab received 80+ drilled-down props.
 * Each tab now calls useContext(AppContext) and picks only what it needs.
 */

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { getApiBase } from '../config/api.js';

const BACKEND_URL = getApiBase();

// ─── Initial State Defaults ────────────────────────────────────────────────

const defaultTelemetry = {
  deviceTelemetry: { primary: '15.5%', secondary: '39%', label: 'ANTOKRES', detail: 'Local matrix deconvolution stable' },
  processManager: { primary: '13.29%', secondary: '1.79%', subtitle: 'Mvmoeor 7.55% · Nxeerr 97°C', detail: 'Ceonunace GOHH · Atnosuce 1.43°C' },
  deviceTelemetry2: { value: '0.5% / 0.96% / 8.7%', subtitle: 'Dsrvmoee · Dhnooe · Arceut surion', detail: 'Ffaoo 1.77% · Totel grace 0.09%' },
  matrixSummary: [
    { title: 'Diagnostic Status', value: '1.24% / 0.9% / 0.34%' },
    { title: 'Elewoan Status', value: 'Nominal · 92.1%' },
    { title: 'Device Two Ponops', value: '14.2% / 82.1% / Active' }
  ],
  ideTree: [
    { label: 'C:\\Program Files\\Google\\Chrome\\Application', expanded: true, children: [
      { label: '150.0.7871.47', expanded: false },
      { label: 'PlatformExperienceHelper', expanded: false },
      { label: 'SetupMetrics', expanded: false },
      { label: 'chrome.exe', expanded: false },
      { label: 'chrome.VisualElementsManifest.xml', expanded: false },
      { label: 'chrome_proxy.exe', expanded: false },
      { label: 'initial_preferences', expanded: false }
    ]}
  ],
  ideVariables: [
    { name: 'natioe_pcer', value: '0.8372006.90%' },
    { name: 'pacle_tyce', value: '123012.43%' },
    { name: 'cacie_cocconbotct', value: '0.245.35%' },
    { name: 'pacle_comonewrt', value: '0.345.22%' }
  ],
  ideCode: `// ii selectwmerly\npublic ereetters(/Reevers Enes): forceelioctos,\nif (!ontectcet)(/c/Inietion/EeelingRurgorI)\n   sub(itons = vvels.booor());\n\nif (costvstures == incwrrnnt("Incretazr")) {\n   ift ( reture *beone );\n   return reton(*poome.retos/erating/"Necratpeleson");\n}`
};

// ─── Context Creation ──────────────────────────────────────────────────────

const AppContext = createContext(null);

export function AppProvider({ children }) {
  // ── Auth State ──────────────────────────────────────────────────────────
  const [loggedIn, setLoggedIn] = useState(false);

  // ── Navigation State ────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('dashboard');
  const [phaseStep, setPhaseStep] = useState(-1);
  const [transitioning, setTransitioning] = useState(false);

  // ── Chat State ──────────────────────────────────────────────────────────
  const [chatMessages, setChatMessages] = useState([]);
  const [footerInput, setFooterInput] = useState('');
  const messageFeedRef = useRef(null);

  // ── Export / IDE State ──────────────────────────────────────────────────
  const [exportCode, setExportCode] = useState('');
  const [exportLanguage, setExportLanguage] = useState('javascript');

  // ── Dev Workspace State ─────────────────────────────────────────────────
  const [devChatInput, setDevChatInput] = useState('');
  const [devChatMessages, setDevChatMessages] = useState([]);
  const [devLeftTab, setDevLeftTab] = useState('chat');
  const [devBottomTab, setDevBottomTab] = useState('code');
  const [devMode, setDevMode] = useState(false);
  const [devFileName, setDevFileName] = useState('untitled.py');
  const [devCodeInput, setDevCodeInput] = useState('');
  const [devCodeOutput, setDevCodeOutput] = useState('');
  const [devCodeType, setDevCodeType] = useState('python');
  const [gitStatus, setGitStatus] = useState('Clean working tree.');
  const [systemGitStatus, setSystemGitStatus] = useState('Clean working tree.');

  // ── Terminal / PowerShell State ─────────────────────────────────────────
  const [psCommand, setPsCommand] = useState('');
  const [psOutput, setPsOutput] = useState('');
  const [isExecutingPs, setIsExecutingPs] = useState(false);

  // ── Code Execution State ────────────────────────────────────────────────
  const [isExecutingCode, setIsExecutingCode] = useState(false);

  // ── Model / Generation State ────────────────────────────────────────────
  const [selectedModel, setSelectedModel] = useState('');
  const [availableModels, setAvailableModels] = useState([]);
  const [comfyuiModels, setComfyuiModels] = useState([]);
  const [comfyuiStatus, setComfyuiStatus] = useState({ status: 'offline', gpu: '', vram_total: 0, vram_free: 0 });
  const [isGeneratingNocoCode, setIsGeneratingNocoCode] = useState(false);
  const [deployMessage, setDeployMessage] = useState(null);
  const [isDeploying, setIsDeploying] = useState(false);

  // ── Generator Tab State ─────────────────────────────────────────────────
  const [genDimensionality, setGenDimensionality] = useState('2D');
  const [genPhysicsTarget, setGenPhysicsTarget] = useState('Rigid Objects');
  const [genObjective, setGenObjective] = useState('Stabilize');

  // ── Media Studio State ──────────────────────────────────────────────────
  const [mediaType, setMediaType] = useState('local_ai');
  const [mediaPrompt, setMediaPrompt] = useState('');
  const [mediaAspectRatio, setMediaAspectRatio] = useState('1:1');
  const [mediaResultUrl, setMediaResultUrl] = useState(null);
  const [mediaError, setMediaError] = useState(null);
  const [isCreatingMedia, setIsCreatingMedia] = useState(false);
  const [localGenProgress, setLocalGenProgress] = useState(0);

  // ── Local AI Params ─────────────────────────────────────────────────────
  const [localAiWidth, setLocalAiWidth] = useState(512);
  const [localAiHeight, setLocalAiHeight] = useState(512);
  const [localAiSteps, setLocalAiSteps] = useState(20);
  const [localAiCfgScale, setLocalAiCfgScale] = useState(7);
  const [localAiNegativePrompt, setLocalAiNegativePrompt] = useState('');
  const [localAiSeed, setLocalAiSeed] = useState(-1);
  const [selectedComfyModel, setSelectedComfyModel] = useState('');

  // ── Local Simulation State ──────────────────────────────────────────────
  const [localSimMode, setLocalSimMode] = useState('Rigid Bodies');
  const [localSimTheme, setLocalSimTheme] = useState('Default');
  const [localSimDuration, setLocalSimDuration] = useState(10);

  // ── Knowledge Base State ────────────────────────────────────────────────
  const [documents, setDocuments] = useState([]);
  const [kbSearchQuery, setKbSearchQuery] = useState('');
  const [kbSearchResults, setKbSearchResults] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [previewDocName, setPreviewDocName] = useState(null);
  const [previewDocContent, setPreviewDocContent] = useState(null);

  // ── Chat / File Upload State ────────────────────────────────────────────
  const [isChatUploading, setIsChatUploading] = useState(false);
  const fileInputRef = useRef(null);
  const monacoRef = useRef(null);
  const canvasRef = useRef(null);

  // ── Noco Telemetry State ────────────────────────────────────────────────
  const [nocoTelemetry, setNocoTelemetry] = useState({
    temp: 24.5, mfcOutput: 12.3, aeroponicLayers: 5, co2: 420, lux: 15000, ph: 6.2
  });
  const [nocoAlert, setNocoAlert] = useState(null);
  const [nocoCodePrompt, setNocoCodePrompt] = useState('');
  const [nocoCodeType, setNocoCodeType] = useState('arduino');
  const [nocoGeneratedCode, setNocoGeneratedCode] = useState('');

  // ── IT Interview State ──────────────────────────────────────────────────
  const [isItActive, setIsItActive] = useState(false);
  const [itTimer, setItTimer] = useState(0);
  const [isGrading, setIsGrading] = useState(false);
  const [itScorecard, setItScorecard] = useState(null);

  // ── Fire Writing State ──────────────────────────────────────────────────
  const [fireProfile, setFireProfile] = useState('');
  const [fireTextRaw, setFireTextRaw] = useState('');
  const [fireTextFormatted, setFireTextFormatted] = useState('');
  const [isFormatting, setIsFormatting] = useState(false);
  const [isEnhancingPrompt, setIsEnhancingPrompt] = useState(false);

  // ── Advertising / Lead Matrix State ─────────────────────────────────────
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pollingStatusMsg, setPollingStatusMsg] = useState('');

  // ── SSD Virtual RAM State ───────────────────────────────────────────────
  const [ssdRamPath, setSsdRamPath] = useState('');
  const [ssdRamSize, setSsdRamSize] = useState(4);
  const [ssdRamCount, setSsdRamCount] = useState(0);
  const [isSsdLoading, setIsSsdLoading] = useState(false);

  // ── Pull Model State ────────────────────────────────────────────────────
  const [pullModelInput, setPullModelInput] = useState('');
  const [pullingStatus, setPullingStatus] = useState('');

  // ── Agent Launcher State ────────────────────────────────────────────────
  const [activeAgents, setActiveAgents] = useState([]);
  const [telegramToken, setTelegramToken] = useState('');
  const [safetySkipPermissions, setSafetySkipPermissions] = useState(false);
  const [customLoopTime, setCustomLoopTime] = useState('15m');
  const [customLoopTask, setCustomLoopTask] = useState('');

  // ── Workflow Mode (for sub-tabs) ────────────────────────────────────────
  const [workflowMode, setWorkflowMode] = useState('standard');

  // ── Gallery / Media State ───────────────────────────────────────────────
  const [galleryMedia, setGalleryMedia] = useState([]);

  // ── Utility: parse source tags from context strings ─────────────────────
  const parseSources = useCallback((ctx) => {
    if (!ctx) return [];
    return ctx.split(',').map(s => s.trim()).filter(Boolean);
  }, []);

  // ── Utility: format time seconds → MM:SS ────────────────────────────────
  const formatTime = useCallback((seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }, []);

  // ── Utility: categorize models by type ──────────────────────────────────
  const categorizeModels = useCallback((models) => {
    return {
      chat: models.filter(m => m.type === 'chat'),
      image: models.filter(m => m.type === 'image'),
      video: models.filter(m => m.type === 'video'),
      local: models.filter(m => m.type === 'local'),
    };
  }, []);

  // ── Value Object (memoized so consumers only re-render when their slice changes) ──
  const value = React.useMemo(() => ({
    BACKEND_URL,
    loggedIn, setLoggedIn,
    activeTab, setActiveTab,
    phaseStep, setPhaseStep, transitioning, setTransitioning,
    chatMessages, setChatMessages, footerInput, setFooterInput, messageFeedRef,
    exportCode, setExportCode, exportLanguage, setExportLanguage,
    devChatInput, setDevChatInput, devChatMessages, setDevChatMessages,
    devLeftTab, setDevLeftTab, devBottomTab, setDevBottomTab,
    devMode, setDevMode, devFileName, setDevFileName,
    devCodeInput, setDevCodeInput, devCodeOutput, setDevCodeOutput, devCodeType, setDevCodeType,
    gitStatus, setGitStatus, systemGitStatus, setSystemGitStatus,
    psCommand, setPsCommand, psOutput, setPsOutput, isExecutingPs, setIsExecutingPs,
    isExecutingCode, setIsExecutingCode,
    selectedModel, setSelectedModel, availableModels, setAvailableModels,
    comfyuiModels, setComfyuiModels, comfyuiStatus, setComfyuiStatus,
    isGeneratingNocoCode, setIsGeneratingNocoCode,
    deployMessage, setDeployMessage, isDeploying, setIsDeploying,
    genDimensionality, setGenDimensionality, genPhysicsTarget, setGenPhysicsTarget, genObjective, setGenObjective,
    mediaType, setMediaType, mediaPrompt, setMediaPrompt, mediaAspectRatio, setMediaAspectRatio,
    mediaResultUrl, setMediaResultUrl, mediaError, setMediaError, isCreatingMedia, setIsCreatingMedia, localGenProgress, setLocalGenProgress,
    localAiWidth, setLocalAiWidth, localAiHeight, setLocalAiHeight, localAiSteps, setLocalAiSteps,
    localAiCfgScale, setLocalAiCfgScale, localAiNegativePrompt, setLocalAiNegativePrompt, localAiSeed, setLocalAiSeed,
    selectedComfyModel, setSelectedComfyModel,
    localSimMode, setLocalSimMode, localSimTheme, setLocalSimTheme, localSimDuration, setLocalSimDuration,
    documents, setDocuments, kbSearchQuery, setKbSearchQuery, kbSearchResults, setKbSearchResults,
    isUploading, setIsUploading, isPreviewLoading, setIsPreviewLoading, previewDocName, setPreviewDocName, previewDocContent, setPreviewDocContent,
    isChatUploading, setIsChatUploading, fileInputRef, monacoRef, canvasRef,
    nocoTelemetry, setNocoTelemetry, nocoAlert, setNocoAlert,
    nocoCodePrompt, setNocoCodePrompt, nocoCodeType, setNocoCodeType, nocoGeneratedCode, setNocoGeneratedCode,
    isItActive, setIsItActive, itTimer, setItTimer, isGrading, setIsGrading, itScorecard, setItScorecard,
    fireProfile, setFireProfile, fireTextRaw, setFireTextRaw, fireTextFormatted, setFireTextFormatted,
    isFormatting, setIsFormatting, isEnhancingPrompt, setIsEnhancingPrompt,
    leads, setLeads, loading, setLoading, pollingStatusMsg, setPollingStatusMsg,
    ssdRamPath, setSsdRamPath, ssdRamSize, setSsdRamSize, ssdRamCount, setSsdRamCount, isSsdLoading, setIsSsdLoading,
    pullModelInput, setPullModelInput, pullingStatus, setPullingStatus,
    activeAgents, setActiveAgents, telegramToken, setTelegramToken, safetySkipPermissions, setSafetySkipPermissions,
    customLoopTime, setCustomLoopTime, customLoopTask, setCustomLoopTask,
    workflowMode, setWorkflowMode,
    galleryMedia, setGalleryMedia,
    parseSources, formatTime, categorizeModels,
    telemetry: defaultTelemetry,
  }), [
    loggedIn, activeTab, phaseStep, transitioning, chatMessages, footerInput,
    exportCode, exportLanguage, devChatInput, devChatMessages, devLeftTab, devBottomTab,
    devMode, devFileName, devCodeInput, devCodeOutput, devCodeType, gitStatus, systemGitStatus,
    psCommand, psOutput, isExecutingPs, isExecutingCode, selectedModel, availableModels,
    comfyuiModels, comfyuiStatus, isGeneratingNocoCode, deployMessage, isDeploying,
    genDimensionality, genPhysicsTarget, genObjective, mediaType, mediaPrompt, mediaAspectRatio,
    mediaResultUrl, mediaError, isCreatingMedia, localGenProgress, localAiWidth, localAiHeight,
    localAiSteps, localAiCfgScale, localAiNegativePrompt, localAiSeed, selectedComfyModel,
    localSimMode, localSimTheme, localSimDuration, documents, kbSearchQuery, kbSearchResults,
    isUploading, isPreviewLoading, previewDocName, previewDocContent, isChatUploading,
    nocoTelemetry, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode,
    isItActive, itTimer, isGrading, itScorecard, fireProfile, fireTextRaw, fireTextFormatted,
    isFormatting, isEnhancingPrompt, leads, loading, pollingStatusMsg, ssdRamPath, ssdRamSize,
    ssdRamCount, isSsdLoading, pullModelInput, pullingStatus, activeAgents, telegramToken,
    safetySkipPermissions, customLoopTime, customLoopTask, workflowMode, galleryMedia,
    parseSources, formatTime, categorizeModels
  ]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within <AppProvider>');
  return ctx;
}
