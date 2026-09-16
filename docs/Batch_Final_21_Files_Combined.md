# AI-BS Frontend — Final Batch Combined Source (21 Files)
**Project:** Stehouwer AI-BS Matrix / Stehouwer Publishing v1.6.2  
**Generated:** Combined markdown of the final file group  
**File count:** 21  
**Categories:** 6 merged groups

---

## Table of Contents
1. [Core State & Context](#core-state--context)   - useAppStore.js   - AppContext.jsx2. [Creative & Writing Studios](#creative--writing-studios)   - ScreenwritingTab.jsx   - DocumentsTab.jsx   - MediaStudioTab.jsx   - KnowledgeBaseTab.jsx3. [Chat & Communication](#chat--communication)   - ChatTab.jsx   - EmailClientTab.jsx4. [Business, Commerce & Analytics](#business-commerce--analytics)   - DigitalStorefrontTab.jsx   - MasterAccountingTab.jsx   - AdvertisingTab.jsx   - AutomatedClientSchedulerTab.jsx   - BetaAnalyticsTab.jsx   - PublicPlaygroundTab.jsx5. [Data, OSINT & API Tools](#data-osint--api-tools)   - BrettDataTab.jsx6. [System, Admin & Infrastructure](#system-admin--infrastructure)   - AdminSecurityMonitorTab.jsx   - CommandCenterTab.jsx   - DeveloperWorkspaceTab.jsx   - GpuNetworkTab.jsx   - CryptoSwarmMobileController.jsx   - DefinitionsModuleTab.jsx
---

# Core State & Context
*2 file(s) in this category*

## useAppStore.js
```javascript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
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

// ─── Utility Functions ───────────────────────────────────────────────────
const parseSources = (ctx) => {
  if (!ctx) return [];
  return ctx.split(',').map(s => s.trim()).filter(Boolean);
};

const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
};

const categorizeModels = (models) => {
  return {
    chat: models.filter(m => m.type === 'chat'),
    image: models.filter(m => m.type === 'image'),
    video: models.filter(m => m.type === 'video'),
    local: models.filter(m => m.type === 'local'),
  };
};

if (typeof window !== 'undefined') {
  window.__setBackendUrl = (url) => useAppStore.getState().setBackendUrl(url);
}

export const useAppStore = create(
  persist(
    (set) => ({
      BACKEND_URL,
      setBackendUrl: (url) => set({ BACKEND_URL: url }),
      telemetry: defaultTelemetry,
  
  // ── Efficiency Mode State ────────────────────────────────────────────────
  efficiencyMode: false,
  setEfficiencyMode: (val) => set({ efficiencyMode: val }),
  toggleEfficiencyMode: async () => {
    const currentMode = useAppStore.getState().efficiencyMode;
    const newMode = !currentMode;
    set({ efficiencyMode: newMode });
    try {
      await fetch(`${useAppStore.getState().BACKEND_URL}/api/system/efficiency-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newMode })
      });
    } catch (e) {
      console.error("Failed to toggle efficiency mode", e);
    }
  },

  parseSources,
  formatTime,
  categorizeModels,

  // ── Auth State ──────────────────────────────────────────────────────────
  loggedIn: false,
  setLoggedIn: (loggedIn) => set({ loggedIn }),

  // ── Navigation State ────────────────────────────────────────────────────
  activeTab: 'dashboard',
  setActiveTab: (activeTab) => set({ activeTab }),
  phaseStep: -1,
  setPhaseStep: (phaseStep) => set({ phaseStep }),
  transitioning: false,
  setTransitioning: (transitioning) => set({ transitioning }),

  // ── Chat State ──────────────────────────────────────────────────────────
  chatMessages: [],
  setChatMessages: (updater) => set(state => ({ chatMessages: typeof updater === 'function' ? updater(state.chatMessages) : updater })),
  footerInput: '',
  setFooterInput: (updater) => set(state => ({ footerInput: typeof updater === 'function' ? updater(state.footerInput) : updater })),
  messageFeedRef: null,

  // ── Export / IDE State ──────────────────────────────────────────────────
  exportCode: '',
  setExportCode: (exportCode) => set({ exportCode }),
  exportLanguage: 'javascript',
  setExportLanguage: (exportLanguage) => set({ exportLanguage }),

  // ── Dev Workspace State ─────────────────────────────────────────────────
  devChatInput: '',
  setDevChatInput: (devChatInput) => set({ devChatInput }),
  devChatMessages: [],
  setDevChatMessages: (updater) => set(state => ({ devChatMessages: typeof updater === 'function' ? updater(state.devChatMessages) : updater })),
  devLeftTab: 'chat',
  setDevLeftTab: (devLeftTab) => set({ devLeftTab }),
  devBottomTab: 'code',
  setDevBottomTab: (devBottomTab) => set({ devBottomTab }),
  devMode: false,
  setDevMode: (devMode) => set({ devMode }),
  devFileName: 'untitled.py',
  setDevFileName: (devFileName) => set({ devFileName }),
  devCodeInput: '',
  setDevCodeInput: (devCodeInput) => set({ devCodeInput }),
  devCodeOutput: '',
  setDevCodeOutput: (devCodeOutput) => set({ devCodeOutput }),
  devCodeType: 'python',
  setDevCodeType: (devCodeType) => set({ devCodeType }),
  gitStatus: 'Clean working tree.',
  setGitStatus: (gitStatus) => set({ gitStatus }),
  systemGitStatus: 'Clean working tree.',
  setSystemGitStatus: (systemGitStatus) => set({ systemGitStatus }),

  // ── Terminal / PowerShell State ─────────────────────────────────────────
  psCommand: '',
  setPsCommand: (psCommand) => set({ psCommand }),
  psOutput: '',
  setPsOutput: (psOutput) => set({ psOutput }),
  isExecutingPs: false,
  setIsExecutingPs: (isExecutingPs) => set({ isExecutingPs }),

  // ── Code Execution State ────────────────────────────────────────────────
  isExecutingCode: false,
  setIsExecutingCode: (isExecutingCode) => set({ isExecutingCode }),

  // ── Model / Generation State ────────────────────────────────────────────
  selectedModel: '',
  setSelectedModel: (selectedModel) => set({ selectedModel }),
  availableModels: [],
  setAvailableModels: (availableModels) => set({ availableModels }),
  comfyuiModels: [],
  setComfyuiModels: (comfyuiModels) => set({ comfyuiModels }),
  comfyuiStatus: { status: 'offline', gpu: '', vram_total: 0, vram_free: 0 },
  setComfyuiStatus: (comfyuiStatus) => set({ comfyuiStatus }),
  isGeneratingNocoCode: false,
  setIsGeneratingNocoCode: (isGeneratingNocoCode) => set({ isGeneratingNocoCode }),
  deployMessage: null,
  setDeployMessage: (deployMessage) => set({ deployMessage }),
  isDeploying: false,
  setIsDeploying: (isDeploying) => set({ isDeploying }),

  // ── Generator Tab State ─────────────────────────────────────────────────
  genDimensionality: '2D',
  setGenDimensionality: (genDimensionality) => set({ genDimensionality }),
  genPhysicsTarget: 'Rigid Objects',
  setGenPhysicsTarget: (genPhysicsTarget) => set({ genPhysicsTarget }),
  genObjective: 'Stabilize',
  setGenObjective: (genObjective) => set({ genObjective }),

  // ── Media Studio State ──────────────────────────────────────────────────
  mediaType: 'local_ai',
  setMediaType: (mediaType) => set({ mediaType }),
  mediaPrompt: '',
  setMediaPrompt: (mediaPrompt) => set({ mediaPrompt }),
  mediaAspectRatio: '1:1',
  setMediaAspectRatio: (mediaAspectRatio) => set({ mediaAspectRatio }),
  mediaResultUrl: null,
  setMediaResultUrl: (mediaResultUrl) => set({ mediaResultUrl }),
  mediaError: null,
  setMediaError: (mediaError) => set({ mediaError }),
  isCreatingMedia: false,
  setIsCreatingMedia: (isCreatingMedia) => set({ isCreatingMedia }),
  localGenProgress: 0,
  setLocalGenProgress: (localGenProgress) => set({ localGenProgress }),

  // ── Local AI Params ─────────────────────────────────────────────────────
  localAiWidth: 512,
  setLocalAiWidth: (localAiWidth) => set({ localAiWidth }),
  localAiHeight: 512,
  setLocalAiHeight: (localAiHeight) => set({ localAiHeight }),
  localAiSteps: 20,
  setLocalAiSteps: (localAiSteps) => set({ localAiSteps }),
  localAiCfgScale: 7,
  setLocalAiCfgScale: (localAiCfgScale) => set({ localAiCfgScale }),
  localAiNegativePrompt: '',
  setLocalAiNegativePrompt: (localAiNegativePrompt) => set({ localAiNegativePrompt }),
  localAiSeed: -1,
  setLocalAiSeed: (localAiSeed) => set({ localAiSeed }),
  selectedComfyModel: '',
  setSelectedComfyModel: (selectedComfyModel) => set({ selectedComfyModel }),

  // ── Local Simulation State ──────────────────────────────────────────────
  localSimMode: 'Rigid Bodies',
  setLocalSimMode: (localSimMode) => set({ localSimMode }),
  localSimTheme: 'Default',
  setLocalSimTheme: (localSimTheme) => set({ localSimTheme }),
  localSimDuration: 10,
  setLocalSimDuration: (localSimDuration) => set({ localSimDuration }),

  // ── Knowledge Base State ────────────────────────────────────────────────
  documents: [],
  setDocuments: (documents) => set({ documents }),
  kbSearchQuery: '',
  setKbSearchQuery: (kbSearchQuery) => set({ kbSearchQuery }),
  kbSearchResults: [],
  setKbSearchResults: (kbSearchResults) => set({ kbSearchResults }),
  isUploading: false,
  setIsUploading: (isUploading) => set({ isUploading }),
  isPreviewLoading: false,
  setIsPreviewLoading: (isPreviewLoading) => set({ isPreviewLoading }),
  previewDocName: null,
  setPreviewDocName: (previewDocName) => set({ previewDocName }),
  previewDocContent: null,
  setPreviewDocContent: (previewDocContent) => set({ previewDocContent }),

  // ── Chat / File Upload State ────────────────────────────────────────────
  isChatUploading: false,
  setIsChatUploading: (isChatUploading) => set({ isChatUploading }),
  fileInputRef: null,
  monacoRef: null,
  canvasRef: null,

  // ── Noco Telemetry State ────────────────────────────────────────────────
  nocoTelemetry: { temp: 24.5, mfcOutput: 12.3, aeroponicLayers: 5, co2: 420, lux: 15000, ph: 6.2 },
  setNocoTelemetry: (nocoTelemetry) => set({ nocoTelemetry }),
  nocoAlert: null,
  setNocoAlert: (nocoAlert) => set({ nocoAlert }),
  nocoCodePrompt: '',
  setNocoCodePrompt: (nocoCodePrompt) => set({ nocoCodePrompt }),
  nocoCodeType: 'arduino',
  setNocoCodeType: (nocoCodeType) => set({ nocoCodeType }),
  nocoGeneratedCode: '',
  setNocoGeneratedCode: (nocoGeneratedCode) => set({ nocoGeneratedCode }),

  // ── IT Interview State ──────────────────────────────────────────────────
  isItActive: false,
  setIsItActive: (isItActive) => set({ isItActive }),
  itTimer: 0,
  setItTimer: (itTimer) => set({ itTimer }),
  isGrading: false,
  setIsGrading: (isGrading) => set({ isGrading }),
  itScorecard: null,
  setItScorecard: (itScorecard) => set({ itScorecard }),

  // ── Fire Writing State ──────────────────────────────────────────────────
  fireProfile: '',
  setFireProfile: (fireProfile) => set({ fireProfile }),
  fireTextRaw: '',
  setFireTextRaw: (fireTextRaw) => set({ fireTextRaw }),
  fireTextFormatted: '',
  setFireTextFormatted: (fireTextFormatted) => set({ fireTextFormatted }),
  isFormatting: false,
  setIsFormatting: (isFormatting) => set({ isFormatting }),
  isEnhancingPrompt: false,
  setIsEnhancingPrompt: (isEnhancingPrompt) => set({ isEnhancingPrompt }),

  // ── Advertising / Lead Matrix State ─────────────────────────────────────
  leads: [],
  setLeads: (leads) => set({ leads }),
  loading: true,
  setLoading: (loading) => set({ loading }),
  pollingStatusMsg: '',
  setPollingStatusMsg: (pollingStatusMsg) => set({ pollingStatusMsg }),

  // ── SSD Virtual RAM State ───────────────────────────────────────────────
  ssdRamPath: '',
  setSsdRamPath: (ssdRamPath) => set({ ssdRamPath }),
  ssdRamSize: 4,
  setSsdRamSize: (ssdRamSize) => set({ ssdRamSize }),
  ssdRamCount: 0,
  setSsdRamCount: (ssdRamCount) => set({ ssdRamCount }),
  isSsdLoading: false,
  setIsSsdLoading: (isSsdLoading) => set({ isSsdLoading }),

  // ── Pull Model State ────────────────────────────────────────────────────
  pullModelInput: '',
  setPullModelInput: (pullModelInput) => set({ pullModelInput }),
  pullingStatus: '',
  setPullingStatus: (pullingStatus) => set({ pullingStatus }),

  // ── Agent Launcher State ────────────────────────────────────────────────
  activeAgents: [],
  setActiveAgents: (activeAgents) => set({ activeAgents }),
  telegramToken: '',
  setTelegramToken: (telegramToken) => set({ telegramToken }),
  safetySkipPermissions: false,
  setSafetySkipPermissions: (safetySkipPermissions) => set({ safetySkipPermissions }),
  customLoopTime: '15m',
  setCustomLoopTime: (customLoopTime) => set({ customLoopTime }),
  customLoopTask: '',
  setCustomLoopTask: (customLoopTask) => set({ customLoopTask }),

  // ── Workflow Mode (for sub-tabs) ────────────────────────────────────────
  workflowMode: 'standard',
  setWorkflowMode: (workflowMode) => set({ workflowMode }),

  // ── Gallery / Media State ───────────────────────────────────────────────
  galleryMedia: [],
  setGalleryMedia: (galleryMedia) => set({ galleryMedia }),

  // ── OSINT & Data Vault State ────────────────────────────────────────────
  osintVaultItems: [],
  setOsintVaultItems: (osintVaultItems) => set({ osintVaultItems }),
  
  fetchPastSavedData: async () => {
    try {
      const { BACKEND_URL, osintVaultItems } = useAppStore.getState();
      const res = await fetch(`${BACKEND_URL}/api/vault/saved_data`);
      const data = await res.json();
      if (data.status === 'success' && data.results) {
        // Merge without duplicates by ID
        const existingIds = new Set(osintVaultItems.map(item => item.id));
        const newItems = data.results.filter(item => !existingIds.has(item.id));
        
        if (newItems.length > 0) {
          set({ osintVaultItems: [...newItems, ...osintVaultItems] });
        }
      }
    } catch (e) {
      console.error("Failed to fetch past saved data:", e);
    }
  },
  
  // RapidAPI Global State
  rapidApiIsFetching: false,
  setRapidApiIsFetching: (rapidApiIsFetching) => set({ rapidApiIsFetching }),
  rapidApiResultData: null,
  setRapidApiResultData: (rapidApiResultData) => set({ rapidApiResultData }),
  rapidApiError: '',
  setRapidApiError: (rapidApiError) => set({ rapidApiError }),

  runRapidApiRecon: async (taskType, targetId, apiKey) => {
    set({ rapidApiIsFetching: true, rapidApiError: '', rapidApiResultData: null });
    const { BACKEND_URL, osintVaultItems } = useAppStore.getState();
    try {
      const res = await fetch(`${BACKEND_URL}/api/proxy/3001/api/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskType, targetId, apiKey })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to fetch data');
      set({ rapidApiResultData: data });

      // Automatically sort and save to vault if valid list found
      let parsed = null;
      if (data.data && data.data.videos) parsed = data.data.videos;
      else if (data.data && Array.isArray(data.data)) parsed = data.data;
      else if (data.videos) parsed = data.videos;
      else if (data.records && Array.isArray(data.records)) parsed = data.records;
      else if (data.results && Array.isArray(data.results)) parsed = data.results;
      else if (data.result && Array.isArray(data.result)) parsed = data.result;
      
      if (parsed) {
        const newVaultItems = parsed.map(item => ({
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          source: `RapidAPI - ${taskType}`,
          category: 'RapidAPI',
          data: item
        }));
        set({ osintVaultItems: [...newVaultItems, ...osintVaultItems] });
      } else {
        // Fallback for non-list data
        const singleItem = {
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          source: `RapidAPI - ${taskType}`,
          category: 'RapidAPI',
          data: data.data !== undefined ? data.data : data
        };
        set({ osintVaultItems: [singleItem, ...osintVaultItems] });
      }
    } catch (err) {
      set({ rapidApiError: err.message });
    } finally {
      set({ rapidApiIsFetching: false });
    }
  },

  // Lost Property Scanner Global State
  lostPropertyLoading: false,
  setLostPropertyLoading: (lostPropertyLoading) => set({ lostPropertyLoading }),
  lostPropertyAccounts: [],
  setLostPropertyAccounts: (lostPropertyAccounts) => set({ lostPropertyAccounts }),
  lostPropertyScanStatus: '',
  setLostPropertyScanStatus: (lostPropertyScanStatus) => set({ lostPropertyScanStatus }),
  lostPropertyError: null,
  setLostPropertyError: (lostPropertyError) => set({ lostPropertyError }),

  runLostPropertyScan: async () => {
    set({ lostPropertyLoading: true, lostPropertyScanStatus: 'Connecting to Gmail API via OAuth and categorizing...', lostPropertyError: null });
    const { BACKEND_URL, osintVaultItems } = useAppStore.getState();
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/lost-property/scan`, { method: 'POST' });
      const json = await res.json();
      if (res.ok) {
        set({ 
          lostPropertyAccounts: json.data || [],
          lostPropertyScanStatus: `Scan complete! Found ${json.count} potential accounts.`
        });
        const newVaultItems = (json.data || []).map(acc => ({
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          source: 'Lost Property Scanner',
          category: `Lost Property - ${acc.category}`,
          data: acc
        }));
        set({ osintVaultItems: [...newVaultItems, ...useAppStore.getState().osintVaultItems] });
      } else {
        set({ lostPropertyError: json.error || 'Scan failed.', lostPropertyScanStatus: '' });
      }
    } catch (e) {
      set({ lostPropertyError: e.message, lostPropertyScanStatus: '' });
    } finally {
      set({ lostPropertyLoading: false });
    }
  },

  // Lost Property Web/Breach Scanner Global State
  lostPropertyWebLoading: false,
  setLostPropertyWebLoading: (lostPropertyWebLoading) => set({ lostPropertyWebLoading }),
  lostPropertyWebResults: [],
  setLostPropertyWebResults: (lostPropertyWebResults) => set({ lostPropertyWebResults }),
  lostPropertyWebError: null,
  setLostPropertyWebError: (lostPropertyWebError) => set({ lostPropertyWebError }),

  runLostPropertyWebScan: async (targetEmail, scanType) => {
    set({ lostPropertyWebLoading: true, lostPropertyWebError: null });
    const { BACKEND_URL, osintVaultItems } = useAppStore.getState();
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/lost-property/web-scan`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_email: targetEmail, scan_type: scanType })
      });
      const json = await res.json();
      if (res.ok) {
        set({ lostPropertyWebResults: json.data || [] });
        const newVaultItems = (json.data || []).map(hit => ({
          id: crypto.randomUUID(),
          timestamp: Date.now(),
          source: 'Breach/Web Leak Scanner',
          category: 'Breach Leak',
          data: hit
        }));
        set({ osintVaultItems: [...newVaultItems, ...useAppStore.getState().osintVaultItems] });
      } else {
        set({ lostPropertyWebError: json.error || json.message || 'Web scan failed.' });
      }
    } catch (e) {
      set({ lostPropertyWebError: e.message });
    } finally {
      set({ lostPropertyWebLoading: false });
    }
  },
}), {
  name: 'ai-bs-osint-vault-storage',
  partialize: (state) => ({ osintVaultItems: state.osintVaultItems, BACKEND_URL: state.BACKEND_URL }),
}));
```

*End of useAppStore.js*

---

## AppContext.jsx
```jsx
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
```

*End of AppContext.jsx*

---

# Creative & Writing Studios
*4 file(s) in this category*

## ScreenwritingTab.jsx
```jsx
import React, { useState, useEffect, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Fountain } from 'fountain-js';
const fountainParser = new Fountain();
import { useAppStore } from './useAppStore';
import CharacterVaultModal from './CharacterVaultModal';
import CoverageReportModal from './CoverageReportModal';

const StoryboardModal = ({ isOpen, onClose, storyboards }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-6 text-white shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
            🎬 AI Storyboard Generator
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {storyboards.map((sb, idx) => (
            <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700 shadow-lg">
              <div className="text-sm text-gray-300 mb-3 h-16 overflow-y-auto italic">"{sb.action}"</div>
              <img src={sb.image_url} alt="Storyboard Panel" className="w-full h-auto rounded-lg shadow-md border border-gray-600" />
            </div>
          ))}
        </div>
        
        {storyboards.length === 0 && (
          <div className="text-center text-gray-500 py-10">
            No storyboards generated.
          </div>
        )}
      </div>
    </div>
  );
};

import './ScreenwritingTab.css';

export default function ScreenwritingTab({ backendUrl, sharedContent, setSharedContent, sharedActiveDoc, onSendToVideoStudio }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  // Screenplay State uses sharedWorkspace state if available
  const screenplay = sharedContent !== undefined ? sharedContent : '';
  const setScreenplay = setSharedContent || (() => {});
  const [parsed, setParsed] = useState(null);
  const [liveHtml, setLiveHtml] = useState('');
  const [projectMetadata, setProjectMetadata] = useState(null);
  const [animatingBeats, setAnimatingBeats] = useState({});
  
  // Layout State
  const [leftPanelVisible, setLeftPanelVisible] = useState(true);
  const [activeView, setActiveView] = useState('editor'); // editor, preview, beats
  const [splitMode, setSplitMode] = useState('none'); // none, vertical, horizontal
  const [zoomLevel, setZoomLevel] = useState(100);

  // Branch & Sprint State
  const [branches, setBranches] = useState([]);
  const [currentBranch, setCurrentBranch] = useState('main');
  const [sprints, setSprints] = useState([]);
  const [activeSprint, setActiveSprint] = useState(null);
  const [sprintName, setSprintName] = useState('');
  const [newBranchName, setNewBranchName] = useState('');
  
  // Projects State
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState('');
  const fileInputRef = useRef(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const editorRef = useRef(null);
  const [draggedBeatIndex, setDraggedBeatIndex] = useState(null);
  const [isProofing, setIsProofing] = useState(false);

  // AI Adapter State
  const [showAdaptModal, setShowAdaptModal] = useState(false);
  const [adaptFile, setAdaptFile] = useState(null);
  const [adaptProjectName, setAdaptProjectName] = useState('');
  const [adaptType, setAdaptType] = useState('Feature Film');
  const [adaptProgress, setAdaptProgress] = useState(null);
  const [isAdapting, setIsAdapting] = useState(false);

  // AI Ghostwriter State
  const [isGhostwriting, setIsGhostwriting] = useState(false);
  const [showCoverage, setShowCoverage] = useState(false);
  const [showStoryboards, setShowStoryboards] = useState(false);
  const [storyboards, setStoryboards] = useState([]);
  const [generatingStoryboards, setGeneratingStoryboards] = useState(false);
  const [coverageData, setCoverageData] = useState(null);
  const [isGeneratingCoverage, setIsGeneratingCoverage] = useState(false);
  const [showCharacterVault, setShowCharacterVault] = useState(false);
  const [characters, setCharacters] = useState([]);

  // Parse Screenplay helper
  const parseScreenplay = async (contentToParse) => {
    try {
      // Local real-time fountain-js parse for split-pane preview
      const htmlOutput = fountainParser.parse(contentToParse || screenplay);
      if (htmlOutput && htmlOutput.html && htmlOutput.html.script) {
        setLiveHtml(htmlOutput.html.script);
      }

      // Backend parse for Beat Board extraction, scene analysis, CMS
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: contentToParse || screenplay }),
      });
      const data = await res.json();
      setParsed(data);
    } catch (err) {
      console.error('Parse failed:', err);
    }
  };

  // Instantaneous parse effect
  useEffect(() => {
    const htmlOutput = fountainParser.parse(screenplay);
    if (htmlOutput && htmlOutput.html && htmlOutput.html.script) {
        setLiveHtml(htmlOutput.html.script);
    }
  }, [screenplay]);

  const loadProjects = async () => {
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects`);
          const data = await res.json();
          setProjects(data.projects || []);
          setCurrentProject(data.current || '');
      } catch (err) {
          console.error('Failed to load projects:', err);
      }
  };

  const loadScreenplay = async () => {
    try {
      // If we have an active doc from the Studio Workspace, parse it directly!
      if (sharedActiveDoc && sharedContent) {
        await parseScreenplay(sharedContent);
        return;
      }
      
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/read`);
      const data = await res.json();
      setScreenplay(data.content);
      setCurrentBranch(data.metadata?.current_branch || 'main');
      setProjectMetadata(data.metadata || {});
      await parseScreenplay(data.content);
    } catch (err) {
      console.error('Failed to load screenplay:', err);
    }
  };

  const loadBranches = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/branches`);
      const data = await res.json();
      setBranches(data.branches || []);
      setCurrentBranch(data.current || 'main');
    } catch (err) {
      console.error('Failed to load branches:', err);
    }
  };


  const loadCharacters = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/projects/characters`);
      const data = await res.json();
      if (data.status === 'success') setCharacters(data.characters || []);
    } catch (err) {
      console.error('Failed to load characters:', err);
    }
  };

  const loadSprints = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprints`);
      const data = await res.json();
      setSprints(data.sprints || []);
    } catch (err) {
      console.error('Failed to load sprints:', err);
    }
  };

  // Initial Load
  useEffect(() => {
    loadProjects();
    loadScreenplay();
    loadBranches();
    loadSprints();
    loadCharacters();
  }, []);

  const handleSaveScreenplay = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: screenplay }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        await parseScreenplay(screenplay);
      }
    } catch (err) {
      console.error('Save failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBranch = async () => {
    if (!newBranchName.trim()) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/branch/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branch_name: newBranchName }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        await loadBranches();
        setNewBranchName('');
      }
    } catch (err) {
      console.error('Branch creation failed:', err);
    }
  };

  const handleStartSprint = async () => {
    if (!sprintName.trim()) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprint/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sprintName, target_pages: 10 }),
      });
      const data = await res.json();
      if (data.sprint) {
        setActiveSprint(data.sprint);
        setSprintName('');
        await loadSprints();
      }
    } catch (err) {
      console.error('Sprint start failed:', err);
    }
  };

  const handleEndSprint = async () => {
    if (!activeSprint) return;
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/sprint/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sprint_id: activeSprint.id }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setActiveSprint(null);
        await loadSprints();
      }
    } catch (err) {
      console.error('Sprint end failed:', err);
    }
  };

  // Drag and Drop Beat Reordering
  const handleDragStart = (e, index) => {
    setDraggedBeatIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    if (draggedBeatIndex === null || draggedBeatIndex === targetIndex) return;
    
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/screenwriting/beats/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_index: draggedBeatIndex, target_index: targetIndex }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        setParsed(data.parsed);
        await loadScreenplay();
      }
    } catch (err) {
      console.error('Reorder failed:', err);
    } finally {
      setIsLoading(false);
      setDraggedBeatIndex(null);
    }
  };

  const handleSwitchProject = async (proj) => {
      setIsLoading(true);
      try {
          await fetch(`${BACKEND_URL}/api/screenwriting/projects/switch`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ project_name: proj })
          });
          await loadProjects();
          await loadScreenplay();
          await loadBranches();
          await loadSprints();
          await loadCharacters();
      } catch (e) { console.error(e); }
      setIsLoading(false);
  };

  const handleAnimateBeat = async (beat) => {
      setAnimatingBeats(prev => ({...prev, [beat.id]: true}));
      try {
          const prompt = beat.heading + " " + beat.summary;
          const res = await fetch(`${BACKEND_URL}/api/video/test_pipeline`, {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({ prompt: prompt })
          });
          const data = await res.json();
          if (data.status === 'success') {
               // Hardcoded HLS stream for now as output from VLC transcoder
               const videoUrl = `${BACKEND_URL}/streams/test_output.m3u8`;
               
               await fetch(`${BACKEND_URL}/api/screenwriting/projects/scene_video`, {
                   method: 'POST',
                   headers: {'Content-Type': 'application/json'},
                   body: JSON.stringify({ beat_id: beat.id, video_url: videoUrl })
               });
               
               await loadScreenplay(); // refresh metadata
          }
      } catch(err) {
          console.error(err);
      } finally {
          setAnimatingBeats(prev => ({...prev, [beat.id]: false}));
      }
  };

  const convertFdxToFountain = (xmlString) => {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlString, "text/xml");
      const paragraphs = xmlDoc.getElementsByTagName("Paragraph");
      let fountain = "";
      
      for (let i = 0; i < paragraphs.length; i++) {
          const p = paragraphs[i];
          const type = p.getAttribute("Type");
          const texts = p.getElementsByTagName("Text");
          let content = "";
          for (let j = 0; j < texts.length; j++) {
              content += texts[j].textContent;
          }
          
          if (!content.trim()) {
              fountain += "\n";
              continue;
          }
          
          if (type === "Scene Heading") {
              fountain += content.toUpperCase() + "\n\n";
          } else if (type === "Action") {
              fountain += content + "\n\n";
          } else if (type === "Character") {
              fountain += content.toUpperCase() + "\n";
          } else if (type === "Parenthetical") {
              if (content.startsWith('(') && content.endsWith(')')) {
                  fountain += content + "\n";
              } else {
                  fountain += "(" + content + ")\n";
              }
          } else if (type === "Dialogue") {
              fountain += content + "\n\n";
          } else if (type === "Transition") {
              fountain += "> " + content.toUpperCase() + "\n\n";
          } else {
              fountain += content + "\n\n";
          }
      }
      return fountain.trim();
  };

  const handleImportClick = () => {
      fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      
      const defaultName = file.name.replace('.fountain', '').replace('.txt', '').replace('.fdx', '').replace('.pdf', '');
      
      if (file.name.toLowerCase().endsWith('.pdf')) {
          setAdaptFile(file);
          setAdaptProjectName(defaultName);
          setShowAdaptModal(true);
          e.target.value = '';
          return;
      }
      
      const projName = prompt("Enter a name for this new project:", defaultName);
      if (!projName) return;
      
      const reader = new FileReader();
      reader.onload = async (ev) => {
          let text = ev.target.result;
          
          if (file.name.toLowerCase().endsWith('.fdx')) {
              text = convertFdxToFountain(text);
          }
          
          setIsLoading(true);
          try {
              await fetch(`${BACKEND_URL}/api/screenwriting/projects/import`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ project_name: projName, content: text })
              });
              await loadProjects();
              await loadScreenplay();
              await loadBranches();
              await loadSprints();
              await loadCharacters();
          } catch(err) { console.error(err); }
          setIsLoading(false);
      };
      reader.readAsText(file);
      e.target.value = '';
  };

  const handleStartAdaptation = async () => {
      if (!adaptFile || !adaptProjectName) return;
      setIsAdapting(true);
      setShowAdaptModal(false);
      setAdaptProgress({ status: 'processing', progress: 0, current_chunk: 0, total_chunks: 0 });
      
      const formData = new FormData();
      formData.append('file', adaptFile);
      formData.append('project_name', adaptProjectName);
      formData.append('adaptation_type', adaptType);
      
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenplay/adapt`, {
              method: 'POST',
              body: formData
          });
          const resData = await res.json();
          if (!res.ok || resData.status === 'error') {
              throw new Error(resData.message || `HTTP error! status: ${res.status}`);
          }
          pollAdaptationStatus(adaptProjectName);
      } catch (err) {
          console.error('Adaptation failed to start:', err);
          setIsAdapting(false);
          setAdaptProgress(null);
          alert(`Adaptation failed to start: ${err.message}`);
      }
  };

  const pollAdaptationStatus = (projName) => {
      const interval = setInterval(async () => {
          try {
              const res = await fetch(`${BACKEND_URL}/api/screenplay/adapt/status?project_name=${projName}`);
              const data = await res.json();
              
              if (data.status && data.status !== 'not_found') {
                  setAdaptProgress(data);
                  
                  // Reload UI to show new chunks live!
                  if (data.status === 'processing') {
                      setCurrentProject(projName);
                      await loadProjects();
                      await loadScreenplay();
                  }

                  if (data.status === 'complete' || data.status === 'error') {
                      clearInterval(interval);
                      setIsAdapting(false);
                      setTimeout(() => setAdaptProgress(null), 3000);
                      
                      if (data.status === 'error') {
                          alert(`AI Adaptation Failed: ${data.error || 'Unknown error'}`);
                      }
                      
                      setCurrentProject(projName);
                      await loadProjects();
                      await loadScreenplay();
                      await loadBranches();
                  }
              }
          } catch(err) {
              console.error(err);
              clearInterval(interval);
          }
      }, 3000);
  };

  const insertSyntax = (syntax) => {
      if (!editorRef.current) return;
      const editor = editorRef.current;
      const position = editor.getPosition();
      const selection = editor.getSelection();
      editor.executeEdits("toolbar", [{
          range: selection,
          text: syntax,
          forceMoveMarkers: true
      }]);
      editor.focus();
  };

  const exportFDX = () => {
    window.open(`${BACKEND_URL}/api/screenwriting/export/fdx`, '_blank');
  };

  const exportPDF = () => {
    window.open(`${BACKEND_URL}/api/screenwriting/export/pdf`, '_blank');
  };

  const handleClipboard = async (action) => {
    if (!editorRef.current) return;
    const editor = editorRef.current;
    
    if (action === 'copy' || action === 'cut') {
        const selection = editor.getSelection();
        const text = editor.getModel().getValueInRange(selection);
        if (text) {
            await navigator.clipboard.writeText(text);
            if (action === 'cut') {
                editor.executeEdits("toolbar", [{ range: selection, text: "", forceMoveMarkers: true }]);
            }
        }
    } else if (action === 'paste') {
        try {
            const text = await navigator.clipboard.readText();
            const selection = editor.getSelection();
            editor.executeEdits("toolbar", [{ range: selection, text: text, forceMoveMarkers: true }]);
        } catch (err) {
            console.error("Paste failed", err);
        }
    }
    editor.focus();
  };

  const handleFormat = (type) => {
      if (!editorRef.current) return;
      const editor = editorRef.current;
      const selection = editor.getSelection();
      const selectedText = editor.getModel().getValueInRange(selection);
      
      let newText = selectedText;
      if (type === 'bold') newText = `**${selectedText}**`;
      else if (type === 'italic') newText = `*${selectedText}*`;
      else if (type === 'underline') newText = `_${selectedText}_`;
      else if (type === 'dual') newText = selectedText ? selectedText + ' ^' : '^'; 
      
      editor.executeEdits("toolbar", [{
          range: selection,
          text: newText,
          forceMoveMarkers: true
      }]);
      editor.focus();
  };

  const handleProofing = async (mode) => {
      if (!editorRef.current) return;
      const editor = editorRef.current;
      const selection = editor.getSelection();
      const text = editor.getModel().getValueInRange(selection);
      if (!text) {
          alert("Highlight some text in the editor first!");
          return;
      }
      
      setIsProofing(true);
      const prompt = mode === 'spell' 
          ? `Fix spelling and grammar for the following script excerpt. Return ONLY the corrected text. Do not add any introductory or conversational text:\n\n${text}`
          : `Suggest a better, more evocative phrasing/synonym for the following script excerpt. Return ONLY the new text. Do not add any introductory or conversational text:\n\n${text}`;
          
      try {
          const res = await fetch(`${BACKEND_URL}/api/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: prompt, model: "llama3:latest" }),
          });
          const data = await res.json();
          
          if (data.status === 'success') {
              const responseText = data.message?.content || data.response || '';
              editor.executeEdits("toolbar", [{ range: selection, text: responseText.trim(), forceMoveMarkers: true }]);
          }
      } catch (err) {
          console.error(err);
      } finally {
          setIsProofing(false);
          editor.focus();
      }
  };


  const getCharacterContextString = () => {
      if (!characters || characters.length === 0) return "";
      let ctx = "\n\n--- CHARACTER LORE & SPEAKING STYLES ---\n";
      characters.forEach(c => {
          ctx += `Name: ${c.name}\n`;
          if (c.bio) ctx += `Bio: ${c.bio}\n`;
          if (c.speaking_style) ctx += `Speaking Style: ${c.speaking_style}\n`;
          ctx += "\n";
      });
      return ctx;
  };

  const handleGhostwriter = async (editor) => {
      const position = editor.getPosition();
      const model = editor.getModel();
      
      // Get context from the beginning up to the cursor (up to ~2000 chars to save time/tokens)
      let textToCursor = model.getValueInRange({
          startLineNumber: Math.max(1, position.lineNumber - 100),
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column
      });
      
      setIsGhostwriting(true);
      const charContext = getCharacterContextString();
      const prompt = `You are an expert Hollywood screenwriter. Continue the following screenplay excerpt. 
Provide exactly ONE logical next beat (either a short action paragraph or a character's dialogue).
If you write dialogue for an existing character, you MUST adopt their specified Speaking Style and lore.
Format it in Fountain. 
Do NOT include any introductory or conversational text, just the script continuation:
${charContext}

--- SCRIPT SO FAR ---
${textToCursor}`;

      try {
          const res = await fetch(`${BACKEND_URL}/api/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: prompt, model: "llama3:latest" }),
          });
          const data = await res.json();
          
          if (data.status === 'success') {
              let responseText = data.message?.content || data.response || '';
              responseText = responseText.trim();
              
              // If the cursor is not at the start of a line, we might want to prepend a newline
              const lineContent = model.getLineContent(position.lineNumber);
              if (lineContent.trim() !== '') {
                  responseText = '\n\n' + responseText;
              }
              
              editor.executeEdits("ghostwriter", [{
                  range: {
                      startLineNumber: position.lineNumber,
                      startColumn: position.column,
                      endLineNumber: position.lineNumber,
                      endColumn: position.column
                  },
                  text: responseText,
                  forceMoveMarkers: true
              }]);
          }
      } catch (err) {
          console.error('Ghostwriter failed', err);
      } finally {
          setIsGhostwriting(false);
          editor.focus();
      }
  };


  
  const [isExporting, setIsExporting] = useState(false);

  const handleExportUnreal = async (type) => {
      if (!screenplay || screenplay.trim() === '') {
          alert("No script to export!");
          return;
      }
      setIsExporting(true);
      try {
          const endpoint = type === 'csv' ? '/api/screenwriting/export/unreal-csv' : '/api/screenwriting/export/unreal-python';
          const res = await fetch(`${BACKEND_URL}${endpoint}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: screenplay })
          });
          const data = await res.json();
          if (data.status === 'success') {
              const blob = new Blob([data.data], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = type === 'csv' ? 'Unreal_DataTable.csv' : 'build_scene.py';
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
          } else {
              alert("Export failed: " + data.message);
          }
      } catch (err) {
          console.error(err);
          alert("Export failed.");
      } finally {
          setIsExporting(false);
      }
  };

  const handleGenerateCoverage = async () => {
      if (!screenplay || screenplay.trim() === '') {
          alert("No script to analyze!");
          return;
      }
      setIsGeneratingCoverage(true);
      try {
          const res = await fetch(`${BACKEND_URL}/api/screenwriting/coverage`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ content: screenplay })
          });
          const data = await res.json();
          if (data.status === 'success') {
              setCoverageData(data.coverage);
              setShowCoverage(true);
          } else {
              alert("Failed to generate coverage: " + data.message);
          }
      } catch (err) {
          console.error("Coverage failed", err);
          alert("Failed to generate coverage.");
      } finally {
          setIsGeneratingCoverage(false);
      }
  };

  const handleAltTake = async () => {
      if (!editorRef.current) return;
      const editor = editorRef.current;
      const selection = editor.getSelection();
      const text = editor.getModel().getValueInRange(selection);
      
      if (!text || text.trim() === '') {
          alert("Please highlight dialogue or action to generate an Alt-Take.");
          return;
      }
      
      setIsProofing(true);
      const charContext = getCharacterContextString();
      const prompt = `You are an expert Hollywood screenwriter. Rewrite the following excerpt from a screenplay to provide a single, strong "Alt-Take" that is perhaps punchier, funnier, or more dramatic. 
Crucially, you MUST maintain the character's exact voice, using the Speaking Styles provided below if applicable.
Return ONLY the Fountain syntax for the rewritten text. Do not include introductory text or explanations.
${charContext}

--- ORIGINAL TEXT ---
${text}`;

      try {
          const res = await fetch(`${BACKEND_URL}/api/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: prompt, model: "llama3:latest" }),
          });
          const data = await res.json();
          
          if (data.status === 'success') {
              const responseText = data.message?.content || data.response || '';
              editor.executeEdits("toolbar", [{ range: selection, text: responseText.trim(), forceMoveMarkers: true }]);
          }
      } catch (err) {
          console.error('Alt-Take failed', err);
      } finally {
          setIsProofing(false);
          editor.focus();
      }
  };

  const handleTitlePage = () => {
      if (!editorRef.current) return;
      const editor = editorRef.current;
      const currentVal = editor.getValue();
      if (!currentVal.startsWith("Title:")) {
          const titleBlock = "Title:\n    _Title_\nAuthor:\n    _Author_\nDraft date:\n    _Date_\n\n";
          editor.executeEdits("toolbar", [{
              range: { startLineNumber: 1, startColumn: 1, endLineNumber: 1, endColumn: 1 },
              text: titleBlock,
              forceMoveMarkers: true
          }]);
      }
      editor.revealLine(1);
      editor.focus();
  };

  const handleSendToVideo = () => {
    if (!editorRef.current) return;
    const editor = editorRef.current;
    const selection = editor.getSelection();
    let text = editor.getModel().getValueInRange(selection);
    
    // Fallback: If nothing is selected, try to send the whole line.
    if (!text || text.trim() === "") {
        const position = editor.getPosition();
        if (position) {
            const lineContent = editor.getModel().getLineContent(position.lineNumber);
            if (lineContent.trim() !== "") {
                text = lineContent;
            }
        }
    }
    
    if (!text || text.trim() === "") {
        alert("Please highlight the scene/text you want to send to Video Studio!");
        return;
    }
    
    if (onSendToVideoStudio) {
        onSendToVideoStudio(text);
    }
  };

  const handleEditorWillMount = (monaco) => {
    monaco.languages.register({ id: 'fountain' });

    monaco.languages.setMonarchTokensProvider('fountain', {
        tokenizer: {
            root: [
                // Scene Headings
                [/^(INT|EXT|EST|INT\/EXT|I\/E|int|ext|est)[\.\s].*$/, 'scene-heading'],
                [/^\..*$/, 'scene-heading'],
                
                // Transitions
                [/^>.*$/, 'transition'],
                [/^[A-Z\s]+ TO:$/, 'transition'],
                
                // Forced Character
                [/^@[A-Z0-9\s\.\(\)\-]+$/, 'character'],
                
                // Character Names (Heuristic: All caps line, but let's avoid matching every all-cap line perfectly, we can just do A-Z with optional parens)
                [/^[A-Z0-9\s\.\-]+(\s\(.*?\))?$/, 'character'],
                
                // Parentheticals
                [/^\s*\([^)]*\)\s*$/, 'parenthetical'],
                
                // Emphasis
                [/\*\*.*?\*\*/, 'bold'],
                [/\*.*?\*/, 'italic'],
                [/_.*?_/, 'underline'],
                
                // Notes/Boneyard
                [/\[\[.*?\]\]/, 'note'],
                [/\/\*/, 'comment', '@boneyard']
            ],
            boneyard: [
                [/[^\/*]+/, 'comment'],
                [/\*\//, 'comment', '@pop'],
                [/[\/*]/, 'comment']
            ]
        }
    });

    monaco.editor.defineTheme('fountain-theme', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'scene-heading', foreground: '58a6ff', fontStyle: 'bold' },
            { token: 'transition', foreground: 'd2a8ff', fontStyle: 'italic' },
            { token: 'character', foreground: 'facc15', fontStyle: 'bold' },
            { token: 'parenthetical', foreground: '9ca3af', fontStyle: 'italic' },
            { token: 'note', foreground: 'ff7b72' },
            { token: 'comment', foreground: '6e7681', fontStyle: 'italic' },
            { token: 'bold', fontStyle: 'bold' },
            { token: 'italic', fontStyle: 'italic' },
            { token: 'underline', fontStyle: 'underline' }
        ],
        colors: {
            'editor.background': '#0d1117'
        }
    });
  };

  const handlePublishToCMS = async () => {
      if (!parsed || !parsed.html) {
          alert("No parsed HTML available to publish.");
          return;
      }
      
      const filename = prompt("Enter the filename for the CMS (e.g. script.html):", `${currentProject || 'draft'}.html`);
      if (!filename) return;

      setIsLoading(true);
      try {
          const res = await fetch(`${BACKEND_URL}/api/cms/page/save`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  filename: filename,
                  content: `<div class="script-content" style="max-width: 800px; margin: 0 auto; font-family: 'Courier Prime', Courier, monospace; background: white; padding: 40px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">\n${parsed.html}\n</div>`
              })
          });
          const data = await res.json();
          if (data.status === 'success') {
              alert(`Successfully published ${filename} to CMS!`);
          } else {
              alert(`Error publishing to CMS: ${data.message || 'Unknown error'}`);
          }
      } catch (err) {
          console.error("Publish failed", err);
          alert("Failed to publish to CMS");
      } finally {
          setIsLoading(false);
      }
  };

  return (
    <div className="screenwriting-container">
      {/* Adaptation Modal */}
      
      {/* Coverage Modal */}
      {showCoverage && (
        <CoverageReportModal 
          coverageData={coverageData}
          onClose={() => setShowCoverage(false)}
        />
      )}

      {/* Character Vault Modal */}
      {showCharacterVault && (
        <CharacterVaultModal 
          backendUrl={BACKEND_URL}
          onClose={() => setShowCharacterVault(false)}
          onCharactersUpdate={(chars) => {
             setCharacters(chars);
          }}
        />
      )}

      {showAdaptModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#1f2937', padding: '24px', borderRadius: '8px', width: '400px', boxShadow: '0 4px 20px rgba(0,0,0,0.5)' }}>
            <h3 style={{ color: '#fff', marginTop: 0 }}>Adapt PDF to Screenplay</h3>
            <p style={{ color: '#9ca3af', fontSize: '0.9rem' }}>The AI-BS Matrix will process your book and convert the prose into a structured screenplay using LLaMA3.</p>
            
            <label style={{ color: '#fff', display: 'block', marginBottom: '8px' }}>Project Name:</label>
            <input type="text" value={adaptProjectName} onChange={e => setAdaptProjectName(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '16px', boxSizing: 'border-box' }} />
            
            <label style={{ color: '#fff', display: 'block', marginBottom: '8px' }}>Format Target:</label>
            <select value={adaptType} onChange={e => setAdaptType(e.target.value)} className="sw-panel-input" style={{ width: '100%', marginBottom: '24px', boxSizing: 'border-box' }}>
              <option value="Feature Film">Feature Film</option>
              <option value="TV Pilot">TV Pilot</option>
              <option value="Short Film">Short Film</option>
            </select>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button onClick={() => setShowAdaptModal(false)} style={{ background: 'transparent', border: '1px solid #555', color: '#fff', padding: '6px 12px', cursor: 'pointer', borderRadius: '4px' }}>Cancel</button>
              <button onClick={handleStartAdaptation} style={{ background: '#facc15', color: '#000', border: 'none', padding: '6px 12px', fontWeight: 'bold', cursor: 'pointer', borderRadius: '4px' }}>Start Adaptation</button>
            </div>
          </div>
        </div>
      )}
      
      {/* 1. Main Menu Bar */}
      <div className="sw-menu-bar">
        {['File', 'Edit', 'View', 'Format', 'Insert', 'Document', 'Tools', 'Production', 'Help'].map(item => (
          <span key={item} className="sw-menu-item">{item}</span>
        ))}
      </div>

      {/* 2. The Ribbon */}
      <div className="sw-ribbon">
        
        {/* File / Export */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '4px' }}>
            <button className="sw-ribbon-btn sw-ribbon-btn-blue" onClick={exportFDX}>⬇️ Export .fdx</button>
            <button className="sw-ribbon-btn sw-ribbon-btn-red" onClick={exportPDF}>📄 Export .pdf</button>
            <button className="sw-ribbon-btn sw-ribbon-btn-green" onClick={handlePublishToCMS} style={{ background: '#238636', color: 'white', border: 'none' }}>🚀 Publish to CMS</button>
          </div>
          <span className="sw-ribbon-label">File</span>
        </div>
        
        {/* Proofing */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '4px' }}>
            <button className="sw-ribbon-btn" onClick={() => handleProofing('spell')} disabled={isProofing}>{isProofing ? '⏳' : '📝'} Spell</button>
            <button className="sw-ribbon-btn" onClick={() => handleProofing('thesaurus')} disabled={isProofing}>{isProofing ? '⏳' : '📖'} Thesaurus</button>
            <button className="sw-ribbon-btn" onClick={handleAltTake} disabled={isProofing} style={{ color: '#facc15' }}>{isProofing ? '⏳' : '✨'} Alt-Take</button>
          </div>
          <span className="sw-ribbon-label">Proofing</span>
        </div>

        {/* Clipboard */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '2px' }}>
            <button className="sw-ribbon-btn" onClick={() => handleClipboard('cut')}>✂️ Cut</button>
            <button className="sw-ribbon-btn" onClick={() => handleClipboard('copy')}>📋 Copy</button>
            <button className="sw-ribbon-btn" onClick={() => handleClipboard('paste')}>📋 Paste</button>
          </div>
          <span className="sw-ribbon-label">Clipboard</span>
        </div>

        {/* Font */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '2px' }}>
            <button className="sw-ribbon-btn" style={{fontWeight: 'bold'}} onClick={() => handleFormat('bold')}>B</button>
            <button className="sw-ribbon-btn" style={{fontStyle: 'italic'}} onClick={() => handleFormat('italic')}>I</button>
            <button className="sw-ribbon-btn" style={{textDecoration: 'underline'}} onClick={() => handleFormat('underline')}>U</button>
          </div>
          <span className="sw-ribbon-label">Font</span>
        </div>

        {/* Insert */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '4px' }}>
            <button className="sw-ribbon-btn" onClick={() => insertSyntax('[[Image: path/to/img.png]]\n')}>🖼️ Image</button>
            <button className="sw-ribbon-btn" onClick={() => insertSyntax('[[Note: Your note here]]\n')}>📌 ScriptNote</button>
          </div>
          <span className="sw-ribbon-label">Insert</span>
        </div>

        {/* Script Elements */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <button onClick={() => { insertSyntax('\n[  ]\n'); editorRef.current?.focus(); }} className="sw-toolbar-btn" title="Add Beatboard Tag">🔖 Beat</button>
            <button onClick={handleSendToVideo} className="sw-toolbar-btn" style={{ background: '#2ea043', color: '#fff' }} title="Send highlighted text to Video Studio">🎥 Send to Video Studio</button>
            <select 
              onChange={(e) => { insertSyntax(e.target.value); e.target.value=""; }}
              className="sw-ribbon-select"
              defaultValue=""
            >
              <option value="" disabled>Insert Element...</option>
              <option value="INT. ">Scene Heading</option>
              <option value="\n\nAction text...\n">Action</option>
              <option value="\n\nCHARACTER\n">Character</option>
              <option value="Dialogue text\n">Dialogue</option>
              <option value="(parenthetical)\n">Parenthetical</option>
              <option value="\n\nCUT TO:\n">Transition</option>
            </select>
            <button className="sw-ribbon-btn" onClick={() => handleFormat('dual')}>🗣️ Dual</button>
          </div>
          <span className="sw-ribbon-label">Script Elements</span>
        </div>

        
        
        {/* Export Dropdown */}
        <div className="sw-ribbon-group" style={{ position: 'relative' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <button className="sw-ribbon-btn" onClick={() => handleExportUnreal('csv')} disabled={isExporting} style={{ background: '#2563eb', padding: '4px 8px', fontSize: '0.8rem' }}>
              🎮 Export CSV (Data Table)
            </button>
            <button className="sw-ribbon-btn" onClick={() => handleExportUnreal('python')} disabled={isExporting} style={{ background: '#047857', padding: '4px 8px', fontSize: '0.8rem' }}>
              🎮 Export Python (Sequencer)
            </button>
          </div>
          <span className="sw-ribbon-label">Unreal Engine</span>
        </div>

        {/* Production */}
        <div className="sw-ribbon-group">
          <button className="sw-ribbon-btn" onClick={handleGenerateCoverage} disabled={isGeneratingCoverage}>
            {isGeneratingCoverage ? '⏳ Analyzing...' : '📊 Script Coverage'}
          </button>
          <span className="sw-ribbon-label">Production</span>
        </div>

        {/* Title Page */}
        <div className="sw-ribbon-group">
          <button className="sw-ribbon-btn" onClick={handleTitlePage}>📄 Title Page</button>
          <span className="sw-ribbon-label">Title Page</span>
        </div>

        
        {/* Lore / Worldbuilding */}
        <div className="sw-ribbon-group">
          <button className="sw-ribbon-btn" onClick={() => setShowCharacterVault(true)}>🎭 Character Vault</button>
          <span className="sw-ribbon-label">Worldbuilding</span>
        </div>

        {/* Views */}
        <div className="sw-ribbon-group">
          <div style={{ display: 'flex', gap: '2px' }}>
            <button className={`sw-ribbon-btn ${activeView === 'preview' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('preview')}>👁️ Scene View</button>
            <button className={`sw-ribbon-btn ${activeView === 'beats' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('beats')}>🗂️ Beat Board</button>
            <button className={`sw-ribbon-btn ${activeView === 'editor' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setActiveView('editor')}>📝 Editor</button>
            <button className="sw-ribbon-btn" onClick={() => setLeftPanelVisible(!leftPanelVisible)}>{leftPanelVisible ? '◀ Outline' : '▶ Outline'}</button>
            <button className="sw-ribbon-btn">🧭 Navigator</button>
          </div>
          <span className="sw-ribbon-label">Views</span>
        </div>

        {/* Split */}
        <div className="sw-ribbon-group" style={{borderRight: 'none'}}>
          <div style={{ display: 'flex', gap: '2px' }}>
            <button className={`sw-ribbon-btn ${splitMode === 'none' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('none')}>None</button>
            <button className={`sw-ribbon-btn ${splitMode === 'vertical' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('vertical')}>Split V</button>
            <button className={`sw-ribbon-btn ${splitMode === 'horizontal' ? 'sw-ribbon-btn-active' : ''}`} onClick={() => setSplitMode('horizontal')}>Split H</button>
          </div>
          <span className="sw-ribbon-label">Split Screen</span>
        </div>

        {/* Save Button */}
        <div style={{ marginLeft: 'auto', paddingLeft: '16px' }}>
          <button onClick={handleSaveScreenplay} disabled={isLoading} className="sw-save-btn">
            {isLoading ? 'Saving...' : '💾 Save'}
          </button>
        </div>
      </div>

      {/* 3. Main Workspace */}
      <div className="sw-workspace">
        
        {/* Outline Panel (Left) */}
        {leftPanelVisible && (
          <div className="sw-left-panel">
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button className="sw-ribbon-btn" style={{background: '#1f2937', flex: 1}}>Outline 1</button>
              <button className="sw-ribbon-btn" style={{background: 'transparent', flex: 1, border: '1px solid #1f2937'}}>Outline 2</button>
            </div>

            {/* Projects */}
            <h4 className="sw-panel-header" style={{color: '#facc15'}}>📁 Saved Projects</h4>
            <div style={{ marginBottom: '16px' }}>
              <select value={currentProject} onChange={(e) => handleSwitchProject(e.target.value)} className="sw-panel-input" style={{width: '100%', marginBottom: '8px'}}>
                {projects.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <button onClick={handleImportClick} style={{ width: '100%', background: 'transparent', border: '1px solid #facc15', color: '#facc15', padding: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>+ Import (.fountain, .fdx, .pdf)</button>
              <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".fountain,.txt,.fdx,.pdf" onChange={handleFileChange} />
            </div>

            {/* Adaptation Progress */}
            {isAdapting && adaptProgress && (
              <div style={{ marginBottom: '16px', background: '#374151', padding: '12px', borderRadius: '6px' }}>
                <div style={{ color: '#facc15', fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '4px' }}>AI ADAPTATION IN PROGRESS...</div>
                <div style={{ width: '100%', background: '#1f2937', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${adaptProgress.progress}%`, background: '#facc15', height: '100%', transition: 'width 0.5s' }} />
                </div>
                <div style={{ color: '#9ca3af', fontSize: '0.7rem', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Chunk {adaptProgress.current_chunk || 0} of {adaptProgress.total_chunks || 0}</span>
                  <span>{adaptProgress.progress || 0}%</span>
                </div>
              </div>
            )}

            {/* Git Branching */}
            <h4 className="sw-panel-header" style={{color: '#4ade80'}}>🌿 Branches</h4>
            <div style={{ marginBottom: '16px' }}>
              <select value={currentBranch} onChange={(e) => setCurrentBranch(e.target.value)} className="sw-panel-input" style={{width: '100%', marginBottom: '8px'}}>
                {branches.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
              <div style={{ display: 'flex', gap: '4px' }}>
                <input type="text" value={newBranchName} onChange={(e) => setNewBranchName(e.target.value)} placeholder="New branch..." className="sw-panel-input" style={{flex: 1}} />
                <button onClick={handleCreateBranch} style={{ background: '#38bdf8', color: '#000', border: 'none', padding: '0 8px', fontWeight: 'bold', cursor: 'pointer' }}>+</button>
              </div>
            </div>

            {/* Sprints */}
            <h4 className="sw-panel-header" style={{color: '#38bdf8'}}>⏱️ Sprints</h4>
            {!activeSprint ? (
              <div style={{ marginBottom: '16px' }}>
                <input type="text" value={sprintName} onChange={(e) => setSprintName(e.target.value)} placeholder="Sprint name..." className="sw-panel-input" style={{width: '100%', marginBottom: '4px', boxSizing: 'border-box'}} />
                <button onClick={handleStartSprint} style={{ width: '100%', background: '#a78bfa', color: '#000', padding: '4px', border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 'bold' }}>Start Sprint</button>
              </div>
            ) : (
              <div className="sw-sprint-active">
                <div style={{ color: '#a78bfa', fontSize: '0.8rem', marginBottom: '4px', fontWeight: 'bold' }}>▶️ {activeSprint.name}</div>
                <button onClick={handleEndSprint} style={{ width: '100%', background: 'transparent', border: '1px solid #a78bfa', color: '#a78bfa', padding: '4px', cursor: 'pointer', fontSize: '0.8rem' }}>End Sprint</button>
              </div>
            )}
            
            {/* Outline AST extraction */}
            <h4 className="sw-panel-header" style={{color: '#9ca3af'}}>Scenes</h4>
            <div className="sw-scene-list">
                {parsed?.beats?.map((b, i) => (
                    <div key={i} className="sw-scene-item">
                        {b.heading.substring(0, 20)}...
                    </div>
                ))}
            </div>
          </div>
        )}

        {/* Central Area (Supports Split) */}
        <div className="sw-central-area" style={{ flexDirection: splitMode === 'horizontal' ? 'column' : 'row' }}>
            
            {/* Primary View (Editor) */}
            {(activeView === 'editor' || splitMode !== 'none') && (
                <div className="sw-editor-container" style={{ borderRight: splitMode === 'vertical' ? '1px solid #1f2937' : 'none', borderBottom: splitMode === 'horizontal' ? '1px solid #1f2937' : 'none' }}>
                    <Editor
                        height="100%"
                        language="fountain"
                        theme="fountain-theme"
                        value={screenplay}
                        beforeMount={handleEditorWillMount}
                        onChange={(value) => setScreenplay(value || '')}
                        onMount={(editor, monaco) => {
                            editorRef.current = editor;
                            editor.addAction({
                                id: 'ghostwriter-trigger',
                                label: 'Trigger AI Ghostwriter',
                                keybindings: [
                                    monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyJ
                                ],
                                run: (ed) => handleGhostwriter(ed)
                            });
                        }}
                        options={{
                            minimap: { enabled: false },
                            fontSize: 14 * (zoomLevel / 100),
                            wordWrap: 'on',
                            scrollBeyondLastLine: false,
                            automaticLayout: true,
                        }}
                    />
                </div>
            )}

            {/* Secondary View (Preview or Beats) */}
            {(activeView !== 'editor' || splitMode !== 'none') && (
                <div className="sw-preview-container" style={{ background: (activeView === 'preview' || (splitMode !== 'none' && activeView !== 'beats')) ? '#fff' : '#0a0a0a' }}>
                    {(activeView === 'preview' || (splitMode !== 'none' && activeView !== 'beats')) ? (
                         liveHtml && <div style={{ padding: '32px', color: '#000', fontSize: `${12 * (zoomLevel / 100)}pt` }} dangerouslySetInnerHTML={{ __html: liveHtml }} />
                    ) : (
                         <div className="sw-beat-board" style={{ padding: `${20 * (zoomLevel / 100)}px`, gap: `${20 * (zoomLevel / 100)}px` }}>
                            <div className="sw-beat-timeline" />
                            
                            {(parsed?.beats || []).map((beat, idx) => {
                                const scale = zoomLevel / 100;
                                const isDragging = draggedBeatIndex === idx;
                                return (
                                    <div 
                                        key={idx}
                                        draggable
                                        onDragStart={(e) => handleDragStart(e, idx)}
                                        onDragOver={handleDragOver}
                                        onDrop={(e) => handleDrop(e, idx)}
                                        className="sw-beat-card"
                                        style={{
                                            width: `${140 * scale}px`,
                                            height: `${110 * scale}px`,
                                            background: isDragging ? '#1a1a1a' : '#1e1e1e',
                                            border: `2px solid ${isDragging ? '#555' : 'rgba(56, 189, 248, 0.4)'}`,
                                            padding: `${10 * scale}px`,
                                            boxShadow: isDragging ? 'none' : '0 4px 12px rgba(56, 189, 248, 0.1)',
                                            opacity: isDragging ? 0.5 : 1,
                                        }}
                                    >
                                        <div className="sw-beat-index" style={{ top: `-${25 * scale}px`, fontSize: `${12 * scale}px` }}>
                                            {idx + 1}
                                        </div>
                                        <div style={{ fontSize: `${18 * scale}px`, marginBottom: `${4 * scale}px` }}>{beat.emoji || '🎬'}</div>
                                        <div className="sw-beat-heading" style={{ fontSize: `${11 * scale}px` }}>
                                            {beat.heading}
                                        </div>
                                        <div className="sw-beat-page" style={{ fontSize: `${10 * scale}px` }}>
                                            p.{Math.floor(beat.page)}
                                        </div>
                                        
                                        {/* Video Attachment Logic */}
                                        <div style={{ marginTop: 'auto', borderTop: '1px solid #333', paddingTop: '4px' }}>
                                            {projectMetadata?.beat_videos?.[beat.id] ? (
                                                <div style={{ fontSize: `${9 * scale}px`, color: '#4ade80', textAlign: 'center', background: '#112211', padding: '2px', borderRadius: '4px' }}>
                                                    ✅ Video Generated
                                                </div>
                                            ) : (
                                                <button 
                                                    onClick={() => handleAnimateBeat(beat)}
                                                    disabled={animatingBeats[beat.id]}
                                                    style={{ width: '100%', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', fontSize: `${9 * scale}px`, padding: '2px', cursor: animatingBeats[beat.id] ? 'not-allowed' : 'pointer' }}
                                                >
                                                    {animatingBeats[beat.id] ? '⏳ Generating...' : '🎥 Animate Scene'}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                         </div>
                    )}
                </div>
            )}

        </div>
      </div>

      {/* 4. Bottom Panel */}
      <div className="sw-bottom-panel">
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span>SCRIPT</span>
          <span>{parsed ? `${parsed.page_count} Pages` : '0 Pages'}</span>
          <span>{parsed ? `${parsed.characters?.length || 0} Characters` : '0 Characters'}</span>
          <span style={{ color: '#4ade80' }}>Branch: {currentBranch}</span>
          {isGhostwriting && <span style={{ color: '#facc15', fontStyle: 'italic', marginLeft: '10px' }}>🤖 Ghostwriter is thinking...</span>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Zoom: {zoomLevel}%</span>
          <input 
            type="range" 
            min="50" max="200" step="10" 
            value={zoomLevel} 
            onChange={(e) => setZoomLevel(parseInt(e.target.value))} 
            style={{ width: '100px', cursor: 'pointer' }}
          />
        </div>
      </div>

    </div>
  );
}
```

*End of ScreenwritingTab.jsx*

---

## DocumentsTab.jsx
```jsx
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import MonacoEditor from '@monaco-editor/react';

const API_BASE = import.meta.env.VITE_BACKEND_URL || 'https://api.brettstehouwer.live';

// ═══════════════════════════════════════════════════════════════════════
// DOCUMENT TEMPLATES — Create new documents from scratch
// ═══════════════════════════════════════════════════════════════════════

const TEMPLATES = [
  {
    id: 'blank',
    label: 'Blank Document',
    icon: '📄',
    description: 'Empty document — start from scratch',
    ext: '.txt',
    mimeType: 'text/plain',
    content: '',
  },
  {
    id: 'screenplay',
    label: 'Screenplay',
    icon: '🎬',
    description: 'Standard Hollywood screenplay format (8.5" × 11")',
    ext: '.fdx',
    mimeType: 'application/xml',
    content: '<?xml version="1.0" encoding="UTF-8"?>\n<FinalDraft type="draft" name="" date="" id="">\n<PageBreaks>\n</PageBreaks>\n<Content>\n<Paragraph>\n<Text>INT. LOCATION - DAY</Text>\n</Paragraph>\n<Paragraph>\n<Text></Text>\n</Paragraph>\n</Content>\n</FinalDraft>',
  },
  {
    id: 'markdown',
    label: 'Markdown Document',
    icon: '📝',
    description: 'Rich markdown with headings, lists, and formatting',
    ext: '.md',
    mimeType: 'text/markdown',
    content: '# Untitled Document\n\n## Section\n\nStart writing your content here...\n\n- Bullet point 1\n- Bullet point 2\n- Bullet point 3\n\n### Subsection\n\nMore detailed content goes here.\n',
  },
  {
    id: 'json',
    label: 'JSON Configuration',
    icon: '⚙️',
    description: 'Structured JSON data file',
    ext: '.json',
    mimeType: 'application/json',
    content: '{\n  "name": "untitled",\n  "version": "1.0.0",\n  "description": "",\n  "settings": {}\n}',
  },
  {
    id: 'python',
    label: 'Python Script',
    icon: '🐍',
    description: 'Python source file with boilerplate',
    ext: '.py',
    mimeType: 'text/x-python',
    content: '#!/usr/bin/env python3\n"""Module docstring."""\n\ndef main():\n    """Entry point.""">\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n',
  },
  {
    id: 'html',
    label: 'HTML Page',
    icon: '🌐',
    description: 'Basic HTML5 document structure',
    ext: '.html',
    mimeType: 'text/html',
    content: '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Untitled Page</title>\n    <style>\n        body {\n            font-family: system-ui, sans-serif;\n            max-width: 800px;\n            margin: 2rem auto;\n            padding: 0 1rem;\n        }\n    </style>\n</head>\n<body>\n    <h1>Untitled Page</h1>\n    <p>Start editing this file...</p>\n</body>\n</html>',
  },
  {
    id: 'css',
    label: 'CSS Stylesheet',
    icon: '🎨',
    description: 'Cascading stylesheet with reset',
    ext: '.css',
    mimeType: 'text/css',
    content: '/* Reset */\n*, *::before, *::after {\n    box-sizing: border-box;\n    margin: 0;\n    padding: 0;\n}\n\nbody {\n    font-family: system-ui, -apple-system, sans-serif;\n    line-height: 1.6;\n    color: #333;\n}\n',
  },
  {
    id: 'readme',
    label: 'README',
    icon: '📖',
    description: 'Project documentation template',
    ext: '.md',
    mimeType: 'text/markdown',
    content: '# Project Name\n\n## Description\n\nBrief description of the project.\n\n## Installation\n\n```bash\nnpm install\n```\n\n## Usage\n\n```bash\nnpm start\n```\n\n## License\n\nMIT\n',
  },
];

// ═══════════════════════════════════════════════════════════════════════
// FILE TYPE REGISTRY
// ═══════════════════════════════════════════════════════════════════════

const FILE_TYPE_MAP = {
  '.txt': { label: 'Text', language: 'plaintext', icon: '📄' },
  '.md': { label: 'Markdown', language: 'markdown', icon: '📝' },
  '.json': { label: 'JSON', language: 'javascript', icon: '⚙️' },
  '.py': { label: 'Python', language: 'python', icon: '🐍' },
  '.html': { label: 'HTML', language: 'html', icon: '🌐' },
  '.css': { label: 'CSS', language: 'css', icon: '🎨' },
  '.js': { label: 'JavaScript', language: 'javascript', icon: '⚡' },
  '.jsx': { label: 'JSX', language: 'javascript', icon: '⚛️' },
  '.ts': { label: 'TypeScript', language: 'typescript', icon: '🔷' },
  '.tsx': { label: 'TSX', language: 'typescript', icon: '⚛️' },
  '.xml': { label: 'XML', language: 'xml', icon: '📋' },
  '.fdx': { label: 'Final Draft', language: 'xml', icon: '🎬' },
  '.pdf': { label: 'PDF', language: 'plaintext', icon: '📕' },
  '.csv': { label: 'CSV', language: 'plaintext', icon: '📊' },
  '.yaml': { label: 'YAML', language: 'yaml', icon: '⚙️' },
  '.yml': { label: 'YAML', language: 'yaml', icon: '⚙️' },
  '.log': { label: 'Log', language: 'plaintext', icon: '📃' },
};

function getLanguageForExt(ext) {
  return FILE_TYPE_MAP[ext]?.language || 'plaintext';
}

function getFileTypeInfo(ext) {
  return FILE_TYPE_MAP[ext] || { label: 'Unknown', language: 'plaintext', icon: '📄' };
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN COMPONENT — DOCUMENT EDITOR & CREATOR
// ═══════════════════════════════════════════════════════════════════════

export default function DocumentsTab({ backendUrl, sharedContent, setSharedContent, sharedActiveDoc, setSharedActiveDoc }) {
  const baseUrl = backendUrl || `${backendUrl}/api/proxy/6081`;

  // Shared Document State
  const activeDoc = sharedActiveDoc;
  const setActiveDoc = setSharedActiveDoc;
  const content = sharedContent;
  const setContent = setSharedContent;
  const [loading, setLoading] = useState(false);

  // ── UI state ──
  const [showFileTree, setShowFileTree] = useState(true);
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [error, setError] = useState(null);
  const [showNewDocModal, setShowNewDocModal] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);

  // ── Signature Canvas State ──
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);

  const startDrawing = (e) => {
    const { offsetX, offsetY } = e.nativeEvent;
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#e8e8f0";
    ctx.beginPath();
    ctx.moveTo(offsetX, offsetY);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const { offsetX, offsetY } = e.nativeEvent;
    const ctx = canvasRef.current.getContext("2d");
    ctx.lineTo(offsetX, offsetY);
    ctx.stroke();
  };

  const stopDrawing = () => {
    if (isDrawing) {
      const ctx = canvasRef.current.getContext("2d");
      ctx.closePath();
      setIsDrawing(false);
    }
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };


  const [fileTree, setFileTree] = useState([]);
  const [showTemplates, setShowTemplates] = useState(false);
  const [recentFiles, setRecentFiles] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('ai-bs-recent-files')) || [];
      return stored.filter(f => f && f !== 'undefined');
    } catch { return []; }
  });
  const [zoom, setZoom] = useState(100);
  const [viewMode, setViewMode] = useState('editor'); // 'editor' | 'preview' | 'split'
  const [showProperties, setShowProperties] = useState(false);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: SPRINT TRACKER (Chronometric Writing Timer)
  // ═══════════════════════════════════════════════════════════════════
  const [sprintActive, setSprintActive] = useState(false);
  const [sprintPaused, setSprintPaused] = useState(false);
  const [sprintElapsed, setSprintElapsed] = useState(0); // seconds
  const [sprintWords, setSprintWords] = useState(0);
  const [sprintPages, setSprintPages] = useState(0);
  const [sprintStartTime, setSprintStartTime] = useState(null);
  const sprintTimerRef = useRef(null);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: TYPEWRITER VIEW (Active Line Centering)
  // ═══════════════════════════════════════════════════════════════════
  const [typewriterView, setTypewriterView] = useState(false);
  const editorContainerRef = useRef(null);

  // ═══════════════════════════════════════════════════════════════════
  // FD13 FEATURE: GOAL TRACKING (Writing Milestones)
  // ═══════════════════════════════════════════════════════════════════
  const [showGoals, setShowGoals] = useState(false);
  const [goals, setGoals] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('ai-bs-writing-goals') || '[]');
    } catch { return []; }
  });
  const [dailyGoal, setDailyGoal] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('ai-bs-daily-goal') || '{"pages":1,"date":""}');
      const today = new Date().toISOString().slice(0, 10);
      return saved.date === today ? saved.pages : 1;
    } catch { return 1; }
  });

  // ── Sprint Tracker Logic ──
  useEffect(() => {
    if (sprintActive && !sprintPaused) {
      sprintTimerRef.current = setInterval(() => {
        setSprintElapsed((prev) => prev + 1);
      }, 1000);
    }
    return () => { if (sprintTimerRef.current) clearInterval(sprintTimerRef.current); };
  }, [sprintActive, sprintPaused]);

  // Track word count changes
  useEffect(() => {
    if (content) {
      const words = content.trim().split(/\s+/).filter((w) => w.length > 0).length;
      setSprintWords(words);
    }
  }, [content]);

  // Track page count (~500 words per screenplay page)
  useEffect(() => {
    if (content) {
      const pages = Math.max(1, Math.ceil(content.trim().split(/\s+/).filter((w) => w.length > 0).length / 250));
      setSprintPages(pages);
    }
  }, [content]);

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const startSprint = () => {
    setSprintActive(true);
    setSprintPaused(false);
    setSprintElapsed(0);
    setSprintStartTime(Date.now());
  };

  const pauseSprint = () => setSprintPaused(true);
  const resumeSprint = () => setSprintPaused(false);
  const stopSprint = () => {
    setSprintActive(false);
    setSprintPaused(false);
    if (sprintTimerRef.current) clearInterval(sprintTimerRef.current);
  };

  // ── Typewriter View Logic ──
  useEffect(() => {
    if (typewriterView && editorContainerRef.current) {
      const container = editorContainerRef.current;
      const scrollHeight = container.scrollHeight;
      const clientHeight = container.clientHeight;
      container.scrollTop = (scrollHeight - clientHeight) / 2;
    }
  }, [typewriterView, content]);

  // ── Goal Tracking Logic ──
  useEffect(() => {
    localStorage.setItem('ai-bs-writing-goals', JSON.stringify(goals));
  }, [goals]);

  const addGoal = (targetPages) => {
    const newGoal = {
      id: Date.now(),
      target: targetPages,
      current: 0,
      completed: false,
      createdAt: new Date().toISOString(),
    };
    setGoals((prev) => [...prev, newGoal]);
  };

  const completeGoal = (goalId) => {
    setGoals((prev) => prev.map((g) => g.id === goalId ? { ...g, completed: true } : g));
  };

  const deleteGoal = (goalId) => {
    setGoals((prev) => prev.filter((g) => g.id !== goalId));
  };

  // ── File tree refresh ──
  const refreshFileTree = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/api/tree`);
      if (res.ok) {
        const data = await res.json();
        setFileTree(data.files || []);
      }
    } catch { /* tree unavailable */ }
  }, []);

  useEffect(() => { refreshFileTree(); }, [refreshFileTree]);

  // ── Load file from backend ──
  const loadFile = useCallback(async (filePath) => {
    setLoading(true);
    setError('');
    try {
      const ext = filePath.split('.').pop().toLowerCase();
      
      if (ext === 'pdf') {
        setActiveDoc({
          name: filePath.split('/').pop().split('\\').pop(),
          path: filePath,
          ext,
          isPdf: true,
          created: new Date().toISOString(),
          modified: new Date().toISOString(),
        });
        setContent('');
        setViewMode('editor');
      } else {
        const res = await fetch(`${baseUrl}/api/read?filepath=${encodeURIComponent(filePath)}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();

        setActiveDoc({
          name: filePath.split('/').pop().split('\\').pop(),
          path: filePath,
          ext,
          isPdf: false,
          created: new Date().toISOString(),
          modified: new Date().toISOString(),
        });
        setContent(data.content);
        setViewMode('editor');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Create new document from template ──
  const createDocument = useCallback((template) => {
    const timestamp = new Date().toISOString().slice(0, 10);
    const name = `untitled${template.ext}`;
    const path = `E:/AI-BS/Documents/${name}`;

    setActiveDoc({
      name,
      path,
      ext: template.ext.slice(1),
      created: new Date().toISOString(),
      modified: new Date().toISOString(),
    });
    setContent(template.content);
    setShowNewDocModal(false);
    setViewMode('editor');
  }, []);

  // ── Save file to backend ──
  const saveFile = useCallback(async () => {
    if (!activeDoc) return;
    try {
      const res = await fetch(`${baseUrl}/api/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: activeDoc.path, content }),
      });
      if (!res.ok) throw new Error('Save failed');

      setActiveDoc((prev) => ({ ...prev, modified: new Date().toISOString() }));
    } catch (err) {
      setError(`Save failed: ${err.message}`);
    }
  }, [activeDoc, content]);

  // ── Convert PDF ──
  const convertPdf = useCallback(async () => {
    if (!activeDoc || !activeDoc.isPdf) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${baseUrl}/api/convert-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath: activeDoc.path }),
      });
      if (!res.ok) throw new Error('Conversion failed');
      const data = await res.json();
      await refreshFileTree();
      await loadFile(data.new_filepath);
    } catch (err) {
      setError(`Convert failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [activeDoc, refreshFileTree, loadFile]);

  // ── Save As ──
  const saveAs = useCallback(() => {
    if (!activeDoc) return;
    const newName = prompt('Save as:', activeDoc.name);
    if (!newName) return;

    const ext = newName.split('.').pop();
    const newPath = `E:/AI-BS/Documents/${newName}`;

    setActiveDoc((prev) => ({ ...prev, name: newName, path: newName, ext: `.${ext}` }));
    saveFile();
  }, [activeDoc, saveFile]);

  // ── Sign & File ──
  const signDocument = useCallback(() => {
    if (!activeDoc) return;
    setShowSignModal(true);
    // We clear it after it opens, using a small timeout so the DOM has the canvas.
    setTimeout(clearCanvas, 100);
  }, [activeDoc]);

  const submitSignature = useCallback(async (includeGraphic) => {
    if (!activeDoc) return;
    try {
      let signature_image = null;
      if (includeGraphic && canvasRef.current) {
        signature_image = canvasRef.current.toDataURL('image/png');
      }

      setShowSignModal(false);

      const res = await fetch(`${baseUrl}/api/documents/sign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          filename: activeDoc.name, 
          content,
          signature_image: signature_image 
        }),
      });
      if (!res.ok) throw new Error('Signing failed');
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${activeDoc.name.split('.')[0]}_signed.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      alert("Document cryptographically signed and securely filed in vault!");
    } catch (err) {
      setError(`Signing failed: ${err.message}`);
    }
  }, [activeDoc, content]);

  // ── File Tree Management ──
  const deleteFile = useCallback(() => {
    if (!activeDoc) return;
    if (!confirm(`Delete "${activeDoc.name}"?`)) return;

    setActiveDoc(null);
    setContent('');
    refreshFileTree();
  }, [activeDoc, refreshFileTree]);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveFile();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        setShowNewDocModal(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [saveFile]);

  // ── Render file tree ──
  const renderFileTree = (files, depth = 0) => {
    if (!Array.isArray(files)) return null;
    return files.map((item) => (
      <div key={item.path} style={{ marginLeft: depth * 16 }}>
        {item.type === 'directory' ? (
          <>
            <div style={{ padding: '4px 8px', cursor: 'pointer', color: '#58a6ff', fontSize: 12, borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              📁 {item.name}
            </div>
            {renderFileTree(item.children || [], depth + 1)}
          </>
        ) : (
          <div onClick={() => loadFile(item.path)} style={{
            padding: '3px 8px', cursor: 'pointer', color: '#c9d1d9', fontSize: 12,
            borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6,
            opacity: activeDoc?.path === item.path ? 0.8 : 1,
          }}>
            {getFileTypeInfo(item.name.split('.').pop())?.icon || '📄'} {item.name}
          </div>
        )}
      </div>
    ));
  };

  // ═══════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0a0a0f' }}>
      {/* ── Top Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 16px', background: '#1a1a2e', borderBottom: '1px solid #2a2a3e',
        fontSize: 12, color: '#8b949e',
      }}>
        <span style={{ fontWeight: 700, color: '#58a6ff' }}>📂 Document Editor & Creator</span>
        <span>{activeDoc ? activeDoc.name : 'No document open'}</span>
      </div>

      {/* ── Toolbar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
        background: '#12121e', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap',
      }}>
        {/* Create */}
        <button onClick={() => setShowNewDocModal(true)} style={{
          padding: '6px 14px', fontSize: 12, fontWeight: 600, border: '1px solid #238636',
          borderRadius: 6, background: '#238636', color: '#fff', cursor: 'pointer',
        }}>+ New Document</button>

        {/* Open */}
        <button onClick={() => document.getElementById('file-input')?.click()} style={{
          padding: '6px 14px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 6,
          background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
        }}>📂 Open</button>
        <input id="file-input" type="file" style={{ display: 'none' }} onChange={async (e) => {
          const file = e.target.files?.[0];
          if (file) {
            try {
              const text = await file.text();
              const ext = file.name.split('.').pop() || 'txt';
              setActiveDoc({
                path: `C:/Users/footb/AI-BS_Matrix/${file.name}`,
                name: file.name,
                ext: ext,
                content: text
              });
              setContent(text);
              setError('');
            } catch (err) {
              setError(`Failed to read file: ${err.message}`);
            }
          }
        }} />

        {/* Save */}
        {activeDoc && (
          <>
            {activeDoc.isPdf ? (
              <button onClick={convertPdf} style={{
                padding: '6px 14px', fontSize: 12, border: '1px solid #d29922', borderRadius: 6,
                background: '#d2992222', color: '#d29922', cursor: 'pointer', fontWeight: 600,
              }}>🔄 Convert to Text</button>
            ) : (
              <>
                <button onClick={saveFile} style={{
                  padding: '6px 14px', fontSize: 12, border: '1px solid #58a6ff', borderRadius: 6,
                  background: '#1f6feb22', color: '#58a6ff', cursor: 'pointer', fontWeight: 600,
                }}>💾 Save</button>
                <button onClick={saveAs} style={{
                  padding: '6px 14px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 6,
                  background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
                }}>Save As</button>
              </>
            )}
            <button onClick={signDocument} style={{
              padding: '6px 14px', fontSize: 12, border: '1px solid #2ea043', borderRadius: 6,
              background: '#2ea04322', color: '#2ea043', cursor: 'pointer', fontWeight: 600,
            }}>🖋️ Sign & File</button>
            <button onClick={deleteFile} style={{
              padding: '6px 14px', fontSize: 12, border: '1px solid #f8514966', borderRadius: 6,
              background: '#da363322', color: '#f85149', cursor: 'pointer',
            }}>🗑️ Delete</button>
          </>
        )}

        <div style={{ width: 1, height: 24, background: '#3a3a4e', margin: '0 8px' }} />

        {/* View modes */}
        <span style={{ fontSize: 10, color: '#8b949e', marginRight: 4 }}>VIEW:</span>
        {['editor', 'split', 'preview'].map((mode) => (
          <button key={mode} onClick={() => setViewMode(mode)} style={{
            padding: '4px 10px', fontSize: 11, border: viewMode === mode ? '1px solid #58a6ff' : '1px solid #3a3a4e',
            borderRadius: 4, background: viewMode === mode ? '#1f6feb22' : '#1c1c2e',
            color: viewMode === mode ? '#58a6ff' : '#c9d1d9', cursor: 'pointer', textTransform: 'capitalize',
          }}>{mode}</button>
        ))}

        {/* Sprint Tracker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
          <span style={{ fontSize: 12, color: '#8b949e', minWidth: 60 }}>⏱️</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#58a6ff' }}>{formatTime(sprintElapsed)}</span>
          <div style={{ display: 'flex', gap: 4, marginLeft: 12 }}>
            <button onClick={() => startSprint()} disabled={sprintActive} style={{ padding: '4px 10px', fontSize: 11, border: sprintActive ? '1px solid #58a6ff' : '1px solid #3a3a4e', borderRadius: 4, background: sprintActive ? '#238636' : '#1c1c2e', color: sprintActive ? '#fff' : '#c9d1d9', cursor: 'pointer', opacity: sprintActive ? 0.7 : 1 }}>Start</button>
            <button onClick={() => pauseSprint()} disabled={!sprintActive} style={{ padding: '4px 10px', fontSize: 11, border: !sprintActive ? '1px solid #3a3a4e' : '1px solid #58a6ff', borderRadius: 4, background: !sprintActive ? '#1c1c2e' : '#f9b700', color: !sprintActive ? '#c9d1d9' : '#fff', cursor: 'pointer', opacity: !sprintActive ? 1 : 0.7 }}>Pause</button>
            <button onClick={() => resumeSprint()} disabled={!sprintPaused} style={{ padding: '4px 10px', fontSize: 11, border: !sprintPaused ? '1px solid #3a3a4e' : '1px solid #58a6ff', borderRadius: 4, background: !sprintPaused ? '#1c1c2e' : '#238636', color: !sprintPaused ? '#c9d1d9' : '#fff', cursor: 'pointer', opacity: !sprintPaused ? 1 : 0.7 }}>Resume</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 24, marginTop: 8, fontSize: 11, color: '#8b949e' }}>
            <span>Words: {sprintWords}</span>
            <span>Pages: {sprintPages}</span>
        </div>

        {/* Zoom */}
        <span style={{ fontSize: 10, color: '#8b949e', marginLeft: 8 }}>Zoom:</span>
        <button onClick={() => setZoom((z) => Math.max(50, z - 10))} style={{
          padding: '2px 8px', fontSize: 11, border: '1px solid #3a3a4e', borderRadius: 4,
          background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
        }}>−</button>
        <span style={{ fontSize: 11, color: '#c9d1d9', minWidth: 32, textAlign: 'center' }}>{zoom}%</span>
        <button onClick={() => setZoom((z) => Math.min(200, z + 10))} style={{
          padding: '2px 8px', fontSize: 11, border: '1px solid #3a3a4e', borderRadius: 4,
          background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
        }}>+</button>
      </div>

      {/* ── Error Display ── */}
      {error && (
        <div style={{ padding: '8px 16px', background: '#da363322', border: '1px solid #f8514966', color: '#f85149', fontSize: 12 }}>
          {error}
        </div>
      )}

      {/* ── Main Content ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* File Tree */}
        {showFileTree && (
          <div style={{
            width: 240, background: '#161b22', borderRight: '1px solid #2a2a3e',
            overflow: 'auto', display: 'flex', flexDirection: 'column',
          }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1 }}>
              📂 Explorer
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
              {renderFileTree(fileTree)}
            </div>

            {/* Recent files */}
            {recentFiles.length > 0 && (
              <div style={{ borderTop: '1px solid #2a2a3e', padding: '12px 16px' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Recent</div>
                {recentFiles.slice(0, 5).map((f, idx) => (
                  <div key={idx} onClick={() => loadFile(f)} style={{
                    padding: '3px 8px', cursor: 'pointer', color: '#c9d1d9', fontSize: 11, borderRadius: 4,
                  }}>📄 {f.split('/').pop()}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Editor / Preview Area */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Editor Panel */}
          {(viewMode === 'editor' || viewMode === 'split') && (
            <div style={{
              flex: viewMode === 'split' ? '50%' : '100%',
              minWidth: 200, position: 'relative', background: '#0d1117',
            }}>
              {activeDoc ? (
                activeDoc.isPdf ? (
                  <iframe 
                    src={`${baseUrl}/api/serve-file?filepath=${encodeURIComponent(activeDoc.path)}#toolbar=0&navpanes=0&scrollbar=1`}
                    width="100%" 
                    height="100%" 
                    style={{ border: 'none', background: '#e1e4e8' }}
                    title="PDF Viewer"
                  />
                ) : (
                  <MonacoEditor
                    value={content}
                    language={getLanguageForExt(activeDoc.ext)}
                    theme="vs-dark"
                    onChange={setContent}
                    options={{
                      fontSize: 13,
                      fontFamily: "'JetBrains Mono', Consolas, monospace",
                      minimap: { enabled: viewMode === 'editor' },
                      scrollBeyondLastLine: false,
                      renderWhitespace: 'selection',
                      lineNumbers: showProperties ? 'on' : 'off',
                    }}
                  />
                )
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#484f58' }}>
                  <div style={{ fontSize: 64, marginBottom: 24 }}>📄</div>
                  <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No document open</div>
                  <button onClick={() => setShowNewDocModal(true)} style={{
                    padding: '10px 24px', fontSize: 13, border: '1px solid #58a6ff', borderRadius: 8,
                    background: '#1f6feb22', color: '#58a6ff', cursor: 'pointer', fontWeight: 600,
                  }}>+ Create New Document</button>
                </div>
              )}
            </div>
          )}

          {/* Resizer */}
          {viewMode === 'split' && (
            <div style={{ width: 4, cursor: 'col-resize', background: '#21262d' }} />
          )}

          {/* Preview Panel */}
          {(viewMode === 'preview' || viewMode === 'split') && (
            <div style={{
              flex: viewMode === 'split' ? '50%' : '100%',
              minWidth: 200, overflow: 'auto', background: '#0d1117',
            }}>
              <div style={{ padding: '8px 16px', borderBottom: '1px solid #2a2a3e', fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1 }}>
                Preview — {activeDoc ? getFileTypeInfo(activeDoc.ext)?.label : '—'}
              </div>
              <div style={{ padding: 20 }}>
                {activeDoc ? (
                  activeDoc.ext === '.md' ? (
                    <div dangerouslySetInnerHTML={{ __html: content }} style={{ color: '#c9d1d9', lineHeight: 1.6 }} />
                  ) : (
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: "'JetBrains Mono', Consolas, monospace", fontSize: 12, lineHeight: 1.5, color: '#c9d1d9' }}>
                      {content}
                    </pre>
                  )
                ) : (
                  <p style={{ color: '#4b5563', fontStyle: 'italic' }}>Open a document to preview</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Properties Panel */}
        {showProperties && activeDoc && (
          <div style={{
            width: 240, background: '#161b22', borderLeft: '1px solid #2a2a3e',
            overflow: 'auto', padding: 16,
          }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 }}>📋 Document Properties</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Name</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{activeDoc.name}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Path</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4, fontFamily: 'monospace', wordBreak: 'break-all' }}>{activeDoc.path}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Type</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{getFileTypeInfo(activeDoc.ext)?.label}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Size</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{(content.length / 1024).toFixed(1)} KB</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Lines</label>
                <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 4 }}>{content.split('\n').length}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Created</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4 }}>{new Date(activeDoc.created).toLocaleString()}</div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Modified</label>
                <div style={{ fontSize: 11, color: '#c9d1d9', marginTop: 4 }}>{new Date(activeDoc.modified).toLocaleString()}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Status Bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '4px 16px', background: '#161b22', borderTop: '1px solid #2a2a3e',
        fontSize: 11, color: '#8b949e',
      }}>
        <span>
          {activeDoc ? `${activeDoc.name} • ${getFileTypeInfo(activeDoc.ext)?.label}` : 'Ready — press Ctrl+N to create a new document'}
        </span>
        <span>Ctrl+S Save • Ctrl+N New • Ctrl+B Toggle Tree</span>
      </div>

      {/* ── New Document Modal ── */}
      {showNewDocModal && (
        <div style={{
          position: 'fixed', inset: 0, background: '#000000cc', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 3000,
        }} onClick={() => setShowNewDocModal(false)}>
          <div style={{
            background: '#1c1c2e', border: '1px solid #3a3a4e', borderRadius: 16,
            boxShadow: '0 16px 64px rgba(0,0,0,0.8)', width: 700, maxHeight: '80vh', overflow: 'auto',
          }} onClick={(e) => e.stopPropagation()}>
            {/* Modal header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #2a2a3e' }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#e8e8f0' }}>Create New Document</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8b949e' }}>Choose a template to get started</p>
            </div>

            {/* Template grid */}
            <div style={{ padding: 24, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {TEMPLATES.map((template) => (
                <button key={template.id} onClick={() => createDocument(template)} style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                  padding: 20, border: '1px solid #3a3a4e', borderRadius: 12,
                  background: '#0d1117', color: '#c9d1d9', cursor: 'pointer',
                  transition: 'all 0.15s ease', textAlign: 'center',
                }}>
                  <span style={{ fontSize: 36 }}>{template.icon}</span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{template.label}</span>
                  <span style={{ fontSize: 11, color: '#8b949e' }}>{template.description}</span>
                  <span style={{ fontSize: 10, color: '#58a6ff', fontFamily: 'monospace' }}>{template.ext}</span>
                </button>
              ))}
            </div>

            {/* Modal footer */}
            <div style={{ padding: '12px 24px', borderTop: '1px solid #2a2a3e', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setShowNewDocModal(false)} style={{
                padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Signature Modal */}
      {showSignModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          backdropFilter: 'blur(4px)'
        }}>
          <div style={{
            background: '#1c1c2e', border: '1px solid #3a3a4e', borderRadius: 16,
            width: 500, overflow: 'hidden', boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            display: 'flex', flexDirection: 'column'
          }}>
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #2a2a3e' }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#e8e8f0' }}>Sign Document</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#8b949e' }}>Draw your signature below (optional)</p>
            </div>

            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <canvas 
                ref={canvasRef}
                width={400}
                height={200}
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onMouseUp={stopDrawing}
                onMouseOut={stopDrawing}
                style={{ 
                  border: '1px solid #3a3a4e', 
                  borderRadius: 8, 
                  background: '#0d1117', 
                  cursor: 'crosshair',
                  touchAction: 'none'
                }}
              />
              <div style={{ width: '100%', display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                <button onClick={clearCanvas} style={{
                  background: 'none', border: 'none', color: '#58a6ff', fontSize: 12, cursor: 'pointer'
                }}>Clear Canvas</button>
              </div>
            </div>

            <div style={{ padding: '12px 24px', borderTop: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between' }}>
              <button onClick={() => setShowSignModal(false)} style={{
                padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                background: '#1c1c2e', color: '#c9d1d9', cursor: 'pointer',
              }}>Cancel</button>
              
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={() => submitSignature(false)} style={{
                  padding: '8px 20px', fontSize: 12, border: '1px solid #3a3a4e', borderRadius: 8,
                  background: '#232338', color: '#c9d1d9', cursor: 'pointer',
                }}>Skip & Cryptographic Sign</button>
                <button onClick={() => submitSignature(true)} style={{
                  padding: '8px 20px', fontSize: 12, border: 'none', borderRadius: 8,
                  background: '#238636', color: '#ffffff', cursor: 'pointer',
                }}>Approve & Sign</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

*End of DocumentsTab.jsx*

---

## MediaStudioTab.jsx
```jsx
import React from 'react';
import TerminalPanel from './TerminalPanel';
import AdvertisingTab from './AdvertisingTab';
import VisualScriptingTab from './VisualScriptingTab';

export default function MediaStudioTab(props) {
  const { BACKEND_URL, ORCHESTRATOR_COMMANDS, activeTab, availableModels, canvasRef, categorizeModels, chatInput, comfyuiModels, comfyuiStatus, deployMessage, devBottomTab, devChatInput, devChatMessages, devCodeInput, devCodeOutput, devCodeType, devFileName, devLeftTab, devMode, documents, fetchComfyuiModels, fetchComfyuiStatus, fetchDocuments, fetchGallery, fetchModels, fileInputRef, fireProfile, fireTextFormatted, fireTextRaw, formatTime, galleryMedia, genDimensionality, genObjective, genPhysicsTarget, gitStatus, handleChatFileUpload, handleCreateLocalAI, handleCreateLocalImage, handleCreateLocalSimulation, handleCreateMedia, handleDeleteDocument, handleDeployBlueprint, handleDevChatSubmit, handleDownloadMedia, handleDragOver, handleDrop, handleEditorDidMount, handleEnhancePrompt, handleExecuteCode, handleExecutePowershell, handleExportFireWriting, handleFileUpload, handleFormatFireWriting, handleGenerateNocoCode, handleGradeItInterview, handleOpenDocPreview, handlePaste, handleSaveFile, handleSendMessage, handleStartItInterview, handleTriggerNocoAlert, isChatUploading, isCreatingMedia, isDeploying, isDevChatLoading, isEnhancingPrompt, isExecutingCode, isExecutingPs, isFormatting, isGeneratingNocoCode, isGlobalLoading, isGrading, isItActive, isListening, isPreviewLoading, isSavingFile, isUploading, itScorecard, itTimer, kbSearchQuery, kbSearchResults, localAiCfgScale, localAiHeight, localAiNegativePrompt, localAiSeed, localAiSteps, localAiWidth, localGenProgress, localSimDuration, localSimMode, localSimTheme, mediaAspectRatio, mediaError, mediaPrompt, mediaResultUrl, mediaType, messageFeedRef, messages, monacoRef, nocoAlert, nocoCodePrompt, nocoCodeType, nocoGeneratedCode, nocoTelemetry, parseSources, pollingStatusMsg, previewDocContent, previewDocName, psCommand, psOutput, saveMessage, selectedComfyModel, selectedModel, setActiveTab, setAvailableModels, setChatInput, setComfyuiModels, setComfyuiStatus, setDeployMessage, setDevBottomTab, setDevChatInput, setDevChatMessages, setDevCodeInput, setDevCodeOutput, setDevCodeType, setDevFileName, setDevLeftTab, setDevMode, setDocuments, setFireProfile, setFireTextFormatted, setFireTextRaw, setGalleryMedia, setGenDimensionality, setGenObjective, setGenPhysicsTarget, setGitStatus, setIsChatUploading, setIsCreatingMedia, setIsDeploying, setIsDevChatLoading, setIsEnhancingPrompt, setIsExecutingCode, setIsExecutingPs, setIsFormatting, setIsGeneratingNocoCode, setIsGlobalLoading, setIsGrading, setIsItActive, setIsPreviewLoading, setIsSavingFile, setIsUploading, setItScorecard, setItTimer, setKbSearchQuery, setKbSearchResults, setLocalAiCfgScale, setLocalAiHeight, setLocalAiNegativePrompt, setLocalAiSeed, setLocalAiSteps, setLocalAiWidth, setLocalGenProgress, setLocalSimDuration, setLocalSimMode, setLocalSimTheme, setMediaAspectRatio, setMediaError, setMediaPrompt, setMediaResultUrl, setMediaType, setMessages, setNocoAlert, setNocoCodePrompt, setNocoCodeType, setNocoGeneratedCode, setNocoTelemetry, setPollingStatusMsg, setPreviewDocContent, setPreviewDocName, setPsCommand, setPsOutput, setSaveMessage, setSelectedComfyModel, setSelectedModel, setShowModelModal, setSystemGitStatus, setUseAgent, setUseRag, setUseTTS, setUseWebSearch, setWorkflowMode, showModelModal, speakText, systemGitStatus, toggleListening, useAgent, useRag, useTTS, useWebSearch, workflowMode } = props;
  
  return (
    <>
      {activeTab === 'media' && (
            <div className="media-workspace-grid">
              {/* Creator Panel */}
              <div className="media-panel creator-panel glass-panel">
                <h3>🎨 Media Studio</h3>
                <p className="subtitle">Generate with Imagen 3, Veo 3.1, or Local AI (ComfyUI + RTX 4090)</p>
                
                <div className="creator-controls">
                  <div className="control-group">
                    <label>Generate Type:</label>
                    <div className="media-type-toggle" style={{ flexWrap: 'wrap', gap: '8px' }}>
                      <button 
                        className={`type-btn ${mediaType === 'local_ai' ? 'active' : ''}`}
                        onClick={() => { setMediaType('local_ai'); }}
                        style={{ minWidth: '140px', position: 'relative' }}
                      >
                        <span className={`comfyui-status-dot ${comfyuiStatus.status === 'online' ? 'online' : 'offline'}`} />
                        🤖 Local AI (ComfyUI)
                      </button>
                      <button 
                        className={`type-btn ${mediaType === 'image' ? 'active' : ''}`}
                        onClick={() => { setMediaType('image'); setMediaAspectRatio('1:1'); }}
                        style={{ minWidth: '140px' }}
                      >
                        🖼️ Image (Imagen 3)
                      </button>
                      <button 
                        className={`type-btn ${mediaType === 'local_image' ? 'active' : ''}`}
                        onClick={() => { setMediaType('local_image'); }}
                        style={{ minWidth: '140px' }}
                      >
                        🎨 Local Sketch
                      </button>
                      <button 
                        className={`type-btn ${mediaType === 'video' ? 'active' : ''}`}
                        onClick={() => { setMediaType('video'); setMediaAspectRatio('16:9'); }}
                        style={{ minWidth: '140px' }}
                      >
                        🎬 Video (Veo 3.1)
                      </button>
                      <button 
                        className={`type-btn ${mediaType === 'local' ? 'active' : ''}`}
                        onClick={() => { setMediaType('local'); }}
                        style={{ minWidth: '140px' }}
                      >
                        💻 Local Animation
                      </button>
                    </div>
                  </div>

                  {mediaType === 'local_ai' ? (
                    <>
                      {/* ComfyUI Status Bar */}
                      <div className={`comfyui-status-bar ${comfyuiStatus.status === 'online' ? 'online' : 'offline'}`}>
                        <div className="status-info">
                          <span className={`status-dot-lg ${comfyuiStatus.status === 'online' ? 'online' : 'offline'}`} />
                          <span className="status-text">
                            {comfyuiStatus.status === 'online' 
                              ? `Online — ${comfyuiStatus.gpu || 'GPU'}` 
                              : 'ComfyUI Offline'}
                          </span>
                        </div>
                        {comfyuiStatus.status === 'online' && comfyuiStatus.vram_total > 0 && (
                          <span className="vram-info">
                            VRAM: {((comfyuiStatus.vram_total - (comfyuiStatus.vram_free || 0)) / 1073741824).toFixed(1)}GB / {(comfyuiStatus.vram_total / 1073741824).toFixed(0)}GB
                          </span>
                        )}
                      </div>

                      {comfyuiStatus.status !== 'online' ? (
                        <div className="comfyui-offline-card">
                          <div className="offline-icon">🔌</div>
                          <h4>ComfyUI is not running</h4>
                          <p>Start ComfyUI to enable local AI image generation with your RTX 4090.</p>
                          <div className="offline-instructions">
                            <code>start_comfyui.bat</code>
                            <span className="instruction-note">Located in AI_Agent/backend/</span>
                          </div>
                          <button className="retry-status-btn" onClick={fetchComfyuiStatus}>
                            🔄 Check Again
                          </button>
                        </div>
                      ) : (
                        <>
                          {/* Model Selector */}
                          {comfyuiModels.length > 0 && (
                            <div className="control-group">
                              <label>Checkpoint Model:</label>
                              <select 
                                value={selectedComfyModel} 
                                onChange={(e) => setSelectedComfyModel(e.target.value)}
                              >
                                {comfyuiModels.map(m => (
                                  <option key={m} value={m}>{m}</option>
                                ))}
                              </select>
                            </div>
                          )}

                          {/* Prompt */}
                          <div className="control-group">
                            <label>Prompt:</label>
                            <textarea 
                              className="media-prompt-input"
                              placeholder="Describe the image you want to generate in detail..."
                              value={mediaPrompt}
                              onChange={(e) => setMediaPrompt(e.target.value)}
                            />
                            <button 
                              className="enhance-prompt-btn"
                              onClick={handleEnhancePrompt}
                              disabled={isEnhancingPrompt || !mediaPrompt.trim()}
                            >
                              {isEnhancingPrompt ? '⏳ Enhancing...' : '✨ Enhance with Ollama'}
                            </button>
                          </div>

                          {/* Negative Prompt */}
                          <div className="control-group">
                            <label>Negative Prompt:</label>
                            <textarea 
                              className="media-prompt-input negative-prompt"
                              placeholder="Things to avoid in the generation..."
                              value={localAiNegativePrompt}
                              onChange={(e) => setLocalAiNegativePrompt(e.target.value)}
                              style={{ minHeight: '48px', fontSize: '0.85rem' }}
                            />
                            <div className="negative-prompt-presets">
                              <button onClick={() => setLocalAiNegativePrompt('low quality, blurry, distorted, deformed, bad anatomy, watermark, text, logo')}>Quality</button>
                              <button onClick={() => setLocalAiNegativePrompt('cartoon, anime, illustration, painting, drawing, art, sketch, 3d render')}>Photorealism</button>
                              <button onClick={() => setLocalAiNegativePrompt('nsfw, nude, violent, gore, disturbing, offensive')}>Safe</button>
                              <button onClick={() => setLocalAiNegativePrompt('')}>Clear</button>
                            </div>
                          </div>

                          {/* Resolution Presets */}
                          <div className="control-group">
                            <label>Resolution:</label>
                            <div className="resolution-preset-grid">
                              {[
                                { w: 512, h: 512, label: '512²' },
                                { w: 768, h: 768, label: '768²' },
                                { w: 1024, h: 1024, label: '1024²' },
                                { w: 1024, h: 768, label: '1024×768' },
                                { w: 768, h: 1024, label: '768×1024' },
                                { w: 1280, h: 720, label: '1280×720' },
                                { w: 3840, h: 2160, label: '4K UHD' },
                                { w: 4096, h: 2160, label: '4K DCI' },
                                { w: 7680, h: 4320, label: '8K UHD' },
                              ].map(({ w, h, label }) => (
                                <button 
                                  key={label}
                                  className={`res-btn ${localAiWidth === w && localAiHeight === h ? 'active' : ''}`}
                                  onClick={() => { setLocalAiWidth(w); setLocalAiHeight(h); }}
                                >
                                  {label}
                                </button>
                              ))}
                            </div>
                            <div className="custom-resolution-inputs" style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                              <div style={{ flex: 1 }}>
                                <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)' }}>Width (px)</label>
                                <input 
                                  type="number" 
                                  value={localAiWidth} 
                                  onChange={(e) => setLocalAiWidth(Number(e.target.value))} 
                                  style={{ width: '100%', padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-glow)', color: 'var(--text-primary)', outline: 'none' }}
                                />
                              </div>
                              <div style={{ flex: 1 }}>
                                <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)' }}>Height (px)</label>
                                <input 
                                  type="number" 
                                  value={localAiHeight} 
                                  onChange={(e) => setLocalAiHeight(Number(e.target.value))} 
                                  style={{ width: '100%', padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-glow)', color: 'var(--text-primary)', outline: 'none' }}
                                />
                              </div>
                            </div>
                          </div>

                          {/* Steps & CFG Sliders */}
                          <div className="control-group param-row">
                            <div className="param-slider-group">
                              <label>Steps: <strong>{localAiSteps}</strong></label>
                              <input 
                                type="range" min="1" max="50" value={localAiSteps}
                                onChange={(e) => setLocalAiSteps(Number(e.target.value))}
                                className="param-slider"
                              />
                            </div>
                            <div className="param-slider-group">
                              <label>CFG Scale: <strong>{localAiCfgScale.toFixed(1)}</strong></label>
                              <input 
                                type="range" min="1" max="20" step="0.5" value={localAiCfgScale}
                                onChange={(e) => setLocalAiCfgScale(Number(e.target.value))}
                                className="param-slider"
                              />
                            </div>
                          </div>

                          {/* Seed */}
                          <div className="control-group">
                            <label>Seed: <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(-1 = random)</span></label>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <input 
                                type="number"
                                value={localAiSeed}
                                onChange={(e) => setLocalAiSeed(Number(e.target.value))}
                                style={{ flex: 1, padding: '8px 12px', background: 'var(--bg-main)', border: '1px solid var(--border-glow)', color: 'white', borderRadius: '6px' }}
                              />
                              <button 
                                className="seed-random-btn"
                                onClick={() => setLocalAiSeed(-1)}
                                title="Set to random"
                              >
                                🎲
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </>
                  ) : mediaType === 'local' || mediaType === 'local_image' ? (
                    <>
                      <div className="control-group">
                        <label>{mediaType === 'local_image' ? 'Custom Image Request:' : 'Custom Video Request:'}</label>
                        <textarea 
                          className="media-prompt-input"
                          placeholder={mediaType === 'local_image' ? "Describe the illustration you want to generate (e.g. 'growing seedling under pink grow lights')..." : "Describe the simulation you want to generate (e.g. 'water flowing in vertical farm', 'growing seedling', 'temperature chart')..."}
                          value={mediaPrompt}
                          onChange={(e) => setMediaPrompt(e.target.value)}
                        />
                      </div>

                      <div className="control-group">
                        <label>Simulation Mode:</label>
                        <select 
                          value={localSimMode} 
                          onChange={(e) => setLocalSimMode(e.target.value)}
                        >
                          <option value="auto">🤖 Auto-detect from request</option>
                          <option value="seedling">🌱 Seedling Growth Loop</option>
                          <option value="nutrient">🧪 Aero-Agri Nutrient Loop</option>
                          <option value="telemetry">📈 Telemetry Sensor Compass</option>
                          <option value="watch">⌚ Vintage Mechanical Watch</option>
                          <option value="face">👤 Biometric Cybernetic Face</option>
                        </select>
                      </div>

                      {mediaType === 'local' && (
                        <div className="control-group">
                          <label>Duration (Seconds):</label>
                          <select 
                            value={localSimDuration} 
                            onChange={(e) => setLocalSimDuration(Number(e.target.value))}
                          >
                            <option value={5}>5 Seconds</option>
                            <option value={10}>10 Seconds</option>
                            <option value={15}>15 Seconds</option>
                          </select>
                        </div>
                      )}

                      <div className="control-group">
                        <label>Color Theme:</label>
                        <select 
                          value={localSimTheme} 
                          onChange={(e) => setLocalSimTheme(e.target.value)}
                        >
                          <option value="auto">🤖 Auto-detect from request</option>
                          <option value="neon_grow">🌸 Neon Grow (Pink/Purple)</option>
                          <option value="laser_green">🟢 Laser Green (Matrix)</option>
                          <option value="ocean_blue">🔵 Ocean Blue (Cyber)</option>
                          <option value="cyber_amber">🟠 Cyber Amber (Vibrant)</option>
                        </select>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="control-group">
                        <label>Aspect Ratio:</label>
                        <select 
                          value={mediaAspectRatio} 
                          onChange={(e) => setMediaAspectRatio(e.target.value)}
                        >
                          {mediaType === 'image' ? (
                            <>
                              <option value="1:1">1:1 (Square)</option>
                              <option value="16:9">16:9 (Landscape)</option>
                              <option value="9:16">9:16 (Vertical)</option>
                              <option value="4:3">4:3 (Classic)</option>
                              <option value="3:4">3:4 (Portrait)</option>
                            </>
                          ) : (
                            <>
                              <option value="16:9">16:9 (Landscape)</option>
                              <option value="9:16">9:16 (Vertical)</option>
                              <option value="21:9">21:9 (Cinematic)</option>
                            </>
                          )}
                        </select>
                      </div>

                      <div className="control-group">
                        <label>Artistic Prompt:</label>
                        <textarea 
                          className="media-prompt-input"
                          placeholder={mediaType === 'image' ? "Describe the image you want to generate in detail..." : "Describe the motion, scene, and subjects for the video..."}
                          value={mediaPrompt}
                          onChange={(e) => setMediaPrompt(e.target.value)}
                        />
                      </div>
                    </>
                  )}

                  <button 
                    className="generate-media-btn" 
                    onClick={mediaType === 'local_ai' ? handleCreateLocalAI : mediaType === 'local' ? handleCreateLocalSimulation : mediaType === 'local_image' ? handleCreateLocalImage : handleCreateMedia}
                    disabled={isCreatingMedia || !mediaPrompt.trim() || (mediaType === 'local_ai' && comfyuiStatus.status !== 'online')}
                  >
                    {isCreatingMedia ? '🎨 Processing...' : `💾 Generate ${mediaType === 'local_ai' ? 'Local AI Image' : mediaType === 'image' ? 'Image' : mediaType === 'local_image' ? 'Local Sketch' : mediaType === 'video' ? 'Video' : 'Local Animation'}`}
                  </button>
                </div>

                {mediaError && (
                  <div className="media-error-card animate-slide-in">
                    <strong>Error:</strong> {mediaError}
                  </div>
                )}
              </div>

              {/* Preview Panel */}
              <div className="media-panel preview-panel glass-panel">
                <h3>👀 Output Preview</h3>
                <canvas ref={canvasRef} width="1280" height="720" style={{ display: 'none' }} />
                
                <div className="media-display-box">
                  {isCreatingMedia ? (
                    <div className="media-loading-container">
                      <div className="media-spinner">🎨</div>
                      <p className="loading-text">{pollingStatusMsg}</p>
                      {mediaType === 'local' && (
                        <div className="local-progress-container" style={{ width: '80%', marginTop: '12px' }}>
                          <div className="local-progress-bar" style={{ width: '100%', background: 'rgba(255,255,255,0.1)', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${localGenProgress}%`, background: 'var(--accent-neon)', height: '100%', transition: 'width 0.1s ease' }} />
                          </div>
                          <div style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                            {localGenProgress}% Complete
                          </div>
                        </div>
                      )}
                    </div>
                  ) : mediaResultUrl ? (
                    <div className="completed-media-container animate-slide-in">
                      {mediaResultUrl.endsWith('.mp4') || mediaResultUrl.endsWith('.webm') ? (
                        <video 
                          key={mediaResultUrl}
                          src={`${BACKEND_URL}${mediaResultUrl}`} 
                          controls 
                          autoPlay 
                          loop 
                          className="preview-media"
                        />
                      ) : (
                        <img 
                          src={`${BACKEND_URL}${mediaResultUrl}`} 
                          alt="Generated Art" 
                          className="preview-media"
                        />
                      )}
                      <div className="media-actions">
                        <button 
                          onClick={() => handleDownloadMedia(mediaResultUrl)}
                          className="action-btn-download"
                        >
                          📥 Save to Disk
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="media-placeholder">
                      <p>{mediaType === 'local' ? 'Select simulator settings and click Generate on the left.' : 'Enter a prompt on the left to begin generation.'}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Gallery Section */}
              <div className="gallery-section glass-panel">
                <h3>📜 Media Studio Gallery</h3>
                {galleryMedia.length === 0 ? (
                  <p className="empty-gallery-text">Your generated art gallery is empty.</p>
                ) : (
                  <div className="gallery-grid">
                    {galleryMedia.map((item, idx) => (
                      <div key={idx} className="gallery-card" onClick={() => setMediaResultUrl(item.url)}>
                        <div className="gallery-media-preview">
                          {item.type === 'video' ? (
                            <video src={`${BACKEND_URL}${item.url}`} muted className="gallery-thumb" />
                          ) : (
                            <img src={`${BACKEND_URL}${item.url}`} alt={item.filename} className="gallery-thumb" />
                          )}
                        </div>
                        <div className="gallery-card-info">
                          <span>{item.type === 'video' ? '🎬 Video' : '🖼️ Image'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
    </>
  );
}
```

*End of MediaStudioTab.jsx*

---

## KnowledgeBaseTab.jsx
```jsx
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
```

*End of KnowledgeBaseTab.jsx*

---

# Chat & Communication
*2 file(s) in this category*

## ChatTab.jsx
```jsx
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useAppStore } from './useAppStore';
import ChatToolControlBar from './ChatToolControlBar';
import ChatContextToolbar from './ChatContextToolbar';
import AgentPlanReviewCard from './AgentPlanReviewCard';

const CodeBlock = React.memo(function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(code);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = code;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <div style={{
      margin: '12px 0',
      borderRadius: '8px',
      overflow: 'hidden',
      border: '1px solid rgba(255, 255, 255, 0.12)',
      background: '#0d1117'
    }}>
      <div style={{
        display: 'flex',
        justify: 'space-between',
        alignItems: 'center',
        padding: '6px 14px',
        background: 'rgba(255, 255, 255, 0.04)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        fontSize: '0.75rem',
        color: '#94a3b8',
        fontFamily: 'monospace'
      }}>
        <span style={{ fontWeight: 700, textTransform: 'uppercase', color: '#60a5fa', letterSpacing: '0.5px' }}>
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          style={{
            background: copied ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.08)',
            border: `1px solid ${copied ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255, 255, 255, 0.15)'}`,
            borderRadius: '4px',
            color: copied ? '#34d399' : '#cbd5e1',
            padding: '3px 10px',
            fontSize: '0.72rem',
            cursor: 'pointer',
            fontWeight: 600,
            transition: 'all 0.15s ease'
          }}
        >
          {copied ? '✓ Copied!' : '📋 Copy Code'}
        </button>
      </div>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language || 'text'}
        customStyle={{
          margin: 0,
          padding: '12px 14px',
          fontSize: '0.85rem',
          background: 'transparent',
          lineHeight: '1.5'
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
});

function FormattedMessageContent({ content, role }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);

  if (role === 'user') {
    return <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{content}</div>;
  }

  return (
    <div className="chat-markdown-content" style={{ wordBreak: 'break-word' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            const isMultiLine = codeString.includes('\n');

            if (!inline && (match || isMultiLine)) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  code={codeString}
                />
              );
            }
            return (
              <code
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: '#93c5fd',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.85em',
                  fontFamily: 'monospace'
                }}
                {...props}
              >
                {children}
              </code>
            );
          },
          img({ node, src, alt, ...props }) {
            let finalSrc = src || '';
            const isLocalHost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

            if (finalSrc.includes('127.0.0.1:8188') || finalSrc.includes('localhost:8188') || finalSrc.includes('127.0.0.1:8189') || finalSrc.includes('localhost:8189')) {
              if (!isLocalHost) {
                try {
                  const urlObj = new URL(finalSrc);
                  finalSrc = `${BACKEND_URL}/api/comfyui/view${urlObj.search}`;
                } catch (e) {
                  finalSrc = src;
                }
              }
            } else if (!finalSrc.startsWith('http') && !finalSrc.startsWith('data:')) {
              finalSrc = finalSrc.startsWith('/') ? `${BACKEND_URL}${finalSrc}` : `${BACKEND_URL}/${finalSrc}`;
            }

            if (finalSrc && (finalSrc.includes('.mp4') || finalSrc.includes('.webm') || finalSrc.includes('.mov'))) {
              return (
                <div style={{ marginTop: '12px', marginBottom: '12px' }}>
                  <video
                    src={finalSrc}
                    controls
                    autoPlay
                    loop
                    muted
                    style={{
                      maxWidth: '100%',
                      maxHeight: '600px',
                      borderRadius: '12px',
                      border: '1px solid rgba(59, 130, 246, 0.4)',
                      boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
                      display: 'block'
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>
                    <span>🔍 HD Video Rendered via AI-BS Backend</span>
                    <a
                      href={finalSrc}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#60a5fa', textDecoration: 'none', fontWeight: 'bold' }}
                    >
                      📥 Open / Save Video
                    </a>
                  </div>
                </div>
              );
            }

            return (
              <div style={{ marginTop: '12px', marginBottom: '12px' }}>
                <img
                  src={finalSrc}
                  alt={alt || 'Generated Image'}
                  onError={(e) => {
                    if (src && e.currentTarget.src !== src) {
                      e.currentTarget.src = src;
                    }
                  }}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '600px',
                    borderRadius: '12px',
                    border: '1px solid rgba(59, 130, 246, 0.4)',
                    boxShadow: '0 8px 25px rgba(0,0,0,0.5)',
                    cursor: 'pointer',
                    display: 'block',
                  }}
                  onClick={() => window.open(finalSrc, '_blank')}
                  title="Click to view full HD render"
                  {...props}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#94a3b8', marginTop: '6px' }}>
                  <span>🔍 Click photo for full HD view</span>
                  <a
                    href={finalSrc}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#60a5fa', textDecoration: 'none', fontWeight: 'bold' }}
                  >
                    📥 Open / Save Photo
                  </a>
                </div>
              </div>
            );
          },
          table({ children }) {
            return (
              <div style={{ overflowX: 'auto', margin: '14px 0', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return <thead style={{ background: 'rgba(30, 41, 59, 0.8)', color: '#93c5fd', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>{children}</thead>;
          },
          th({ children }) {
            return <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: '600' }}>{children}</th>;
          },
          td({ children }) {
            return <td style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', color: '#e2e8f0' }}>{children}</td>;
          },
          blockquote({ children }) {
            return (
              <blockquote style={{
                borderLeft: '4px solid #60a5fa',
                background: 'rgba(59, 130, 246, 0.08)',
                margin: '12px 0',
                padding: '8px 16px',
                borderRadius: '0 8px 8px 0',
                color: '#cbd5e1',
                fontSize: '0.88rem'
              }}>
                {children}
              </blockquote>
            );
          },
          ul({ children }) {
            return <ul style={{ paddingLeft: '20px', margin: '8px 0' }}>{children}</ul>;
          },
          ol({ children }) {
            return <ol style={{ paddingLeft: '20px', margin: '8px 0' }}>{children}</ol>;
          },
          li({ children }) {
            return <li style={{ marginBottom: '4px' }}>{children}</li>;
          },
          p({ node, ...props }) {
            return <div style={{ margin: '6px 0', lineHeight: '1.6' }} {...props} />;
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                style={{ color: '#60a5fa', textDecoration: 'underline', fontWeight: '500' }}
              >
                {children}
              </a>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function ReasoningInspector({ msg }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ marginTop: '10px', borderTop: '1px dashed rgba(255,255,255,0.12)', paddingTop: '6px' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '6px',
          color: '#60a5fa',
          fontSize: '0.72rem',
          padding: '3px 8px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontWeight: 600
        }}
      >
        <span>🧠 {isOpen ? 'Hide AI Decision Inspector' : 'Inspect AI Reasoning & Execution Trace'}</span>
        <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
          ({msg.execution_time_ms ? `${msg.execution_time_ms} ms` : 'Fast API Edge'})
        </span>
      </button>

      {isOpen && (
        <div style={{
          marginTop: '8px',
          background: '#07090e',
          border: '1px solid rgba(96, 165, 250, 0.3)',
          borderRadius: '8px',
          padding: '10px 14px',
          fontSize: '0.78rem',
          color: '#cbd5e1'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', color: '#93c5fd', fontWeight: 600 }}>
            <span>Model: {msg.model || 'stehouwer_llm'}</span>
            <span>Latency: {msg.execution_time_ms || 120} ms</span>
          </div>

          {msg.tool_trace && msg.tool_trace.tool_name !== 'none' ? (
            <div style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              <div style={{ color: '#34d399', fontWeight: 700, marginBottom: '4px' }}>
                🛠️ Dispatched Tool: {msg.tool_trace.tool_name}
              </div>
              <div style={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                Arguments: {JSON.stringify(msg.tool_trace.arguments)}
              </div>
              <div style={{ color: msg.tool_trace.status === 'success' ? '#34d399' : '#f87171', fontSize: '0.72rem', marginTop: '4px' }}>
                Status: {msg.tool_trace.status}
              </div>
            </div>
          ) : (
            <div style={{ color: '#94a3b8', fontStyle: 'italic' }}>
              Direct neural response generated without external tool invocation.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatTab({ isNested = false }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const chatMessages = useAppStore(state => state.chatMessages);
  const setChatMessages = useAppStore(state => state.setChatMessages);
  const footerInput = useAppStore(state => state.footerInput);
  const setFooterInput = useAppStore(state => state.setFooterInput);
  const messageFeedRef = useAppStore(state => state.messageFeedRef);
  const selectedModel = useAppStore(state => state.selectedModel);

  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [errorPopup, setErrorPopup] = useState(null);

  // File Upload State (GPT Style)
  const [attachments, setAttachments] = useState([]);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef(null);

  const [activeTools, setActiveTools] = useState({});
  const [activeContexts, setActiveContexts] = useState({
    file: false,
    terminal: false,
    codebase: false,
    web: false
  });
  const [targetDevice, setTargetDevice] = useState('Host PC (Local)');
  const toggleContext = (ctx) => setActiveContexts(p => ({ ...p, [ctx]: !p[ctx] }));

  const handleExecutePlan = async (plan_id, steps) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/v1/ide/execute-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id, approved_steps: steps })
      });
      const data = await res.json();
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `🚀 Plan Execution Result:\n\`\`\`json\n${JSON.stringify(data, null, 2)}\n\`\`\`` }
      ]);
    } catch (err) {
      setErrorPopup(err.message || 'Failed to execute plan.');
    } finally {
      setIsLoading(false);
    }
  };

  const recognitionRef = useRef(null);

  const speakText = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*_#`\[\]()]/g, ' ');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // Auto-scroll on new messages
  useEffect(() => {
    if (messageFeedRef?.current) {
      messageFeedRef.current.scrollTop = messageFeedRef.current.scrollHeight;
    }
  }, [chatMessages, isLoading]);

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setIsUploadingFile(true);
    const newAttachments = [];

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch(`${BACKEND_URL}/api/chat/attach`, {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          newAttachments.push(data.file);
        } else {
          setErrorPopup(`Failed to upload ${file.name}: ${data.message || 'Error'}`);
        }
      } catch (err) {
        setErrorPopup(`Upload error for ${file.name}: ${err.message}`);
      }
    }

    setAttachments(prev => [...prev, ...newAttachments]);
    setIsUploadingFile(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleSendMessage = async (customText = null) => {
    const rawText = customText !== null ? customText : footerInput.trim();
    if ((!rawText && attachments.length === 0) || isLoading) return;

    // Format attachments into prompt context
    let formattedPrompt = rawText;
    let attachmentBadges = [];

    if (attachments.length > 0) {
      let attachmentText = attachments.map(att => (
        `\n[ATTACHED FILE: ${att.name} (${(att.size/1024).toFixed(1)} KB)]\n\`\`\`${(att.ext || '').replace('.', '')}\n${att.content}\n\`\`\`\n`
      )).join('\n');

      formattedPrompt = `${attachmentText}\n[USER PROMPT]:\n${rawText || 'Please review and analyze the attached files in detail.'}`;
      attachmentBadges = attachments.map(att => ({ name: att.name, size: att.size, is_image: att.is_image }));
    }

    const userMsg = {
      role: 'user',
      content: formattedPrompt,
      displayContent: rawText || 'Attached Files Analysis',
      attachments: attachmentBadges
    };

    const updatedHistory = [...useAppStore.getState().chatMessages || chatMessages, userMsg];
    setChatMessages(updatedHistory);

    setFooterInput('');
    setAttachments([]);
    setIsLoading(true);

    await new Promise(r => setTimeout(r, 100));

    try {
      const isPlanMode = activeTools?.plan_and_review;
      const endpoint = isPlanMode ? '/v1/ide/plan' : '/api/chat';
      
      const payloadBody = JSON.stringify({
        messages: updatedHistory.map(m => ({ role: m.role, content: m.content })),
        model: selectedModel || 'stehouwer_llm',
        prompt: isPlanMode ? rawText : undefined,
        active_file: isPlanMode ? 'C:\\AI-BS\\backend\\AI_BS_Backend.py' : undefined,
        context_flags: isPlanMode ? activeContexts : undefined,
        target_device: targetDevice
      });

      const reqHeaders = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer sk_aibs_dev_master_key_2026'
      };

      let res = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: 'POST',
        headers: reqHeaders,
        body: payloadBody,
      }).catch(() => null);

      if (!res || !res.ok) {
        res = await fetch(`${BACKEND_URL}/v1/chat/completions`, {
          method: 'POST',
          headers: reqHeaders,
          body: payloadBody,
        }).catch(() => null);
      }

      if (!res || !res.ok) {
        throw new Error(`Server returned HTTP ${res ? res.status : 'Offline'}`);
      }

      const data = await res.json();
      const rawContent = data.choices?.[0]?.message?.content || data.message || '';
      const botResponse = rawContent.trim() !== '' ? rawContent : (isPlanMode ? 'Plan generated.' : `Online and operational (${selectedModel || 'stehouwer_llm'}).`);
      const planData = isPlanMode ? (data.plan_id ? data : (data.planData || null)) : null;

      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: botResponse,
          model: data.model || selectedModel || 'stehouwer_llm',
          execution_time_ms: data.execution_time_ms || 120,
          tool_trace: data.tool_trace || null,
          planData: planData
        }
      ]);

      if (autoSpeak) {
        speakText(botResponse);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setErrorPopup(err.message || 'Failed to reach AI-BS backend.');
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: `❌ **Error:** ${err.message}` }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleListening = () => {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      setErrorPopup('Speech recognition is not supported in this browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setFooterInput(prev => (prev ? `${prev} ${transcript}` : transcript));
      setIsListening(false);
    };
    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setErrorPopup(`Speech error: ${event.error}`);
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
  };

  const starterCards = [
    {
      title: "🔍 Query 200GB Mainnet DB",
      desc: "Run 2ms SELECT queries against 413M coin records & 8.9M block headers.",
      prompt: "Query the blockchain_v2_mainnet.sqlite database and show me the latest 5 block heights and their status."
    },
    {
      title: "🎨 Generate ComfyUI Image",
      desc: "Dispatch visual scene prompts to local SDXL renderer on port 8189.",
      prompt: "Use your generate_comfy_image tool to create a futuristic AI server matrix room."
    },
    {
      title: "📎 Attach & Analyze Code/Docs",
      desc: "Upload python scripts, JSON, CSV, PDFs, or images for AI review.",
      prompt: "I am going to attach code files for you to review and optimize."
    },
    {
      title: "🧠 Search Master Memory Vault",
      desc: "Retrieve historical baselines & verified scripts from living SSD memory.",
      prompt: "Search your master memory for historical baseline python scripts."
    }
  ];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 170px)',
      minHeight: '600px',
      background: 'linear-gradient(180deg, #0d0f14 0%, #07090e 100%)',
      borderRadius: '12px',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
      overflow: 'hidden',
      color: '#e2e8f0',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        multiple
        style={{ display: 'none' }}
      />

      {/* System Status Dashboard Bar */}
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(15, 19, 28, 0.95)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '10px', height: '10px', borderRadius: '50%',
            background: isLoading ? '#f59e0b' : '#10b981',
            boxShadow: isLoading ? '0 0 10px #f59e0b' : '0 0 10px #10b981',
          }} />
          <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc', letterSpacing: '0.5px' }}>
            STEHOUWER LLM CENTRAL HUB
          </span>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>Active Model:</span>
            <select
              value={selectedModel || 'stehouwer_llm'}
              onChange={(e) => useAppStore.getState().setSelectedModel(e.target.value)}
              style={{
                fontSize: '0.75rem',
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                color: '#60a5fa',
                padding: '4px 12px',
                borderRadius: '8px',
                fontWeight: 700,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="stehouwer_llm" style={{ background: '#0d1117', color: '#60a5fa' }}>⚡ Stehouwer LLM (Unified Swarm System)</option>
              <option value="gemini-1.5-pro" style={{ background: '#0d1117', color: '#60a5fa' }}>✨ Google Gemini 1.5 Pro (Cloud Backup)</option>
              <option value="gemini-1.5-flash" style={{ background: '#0d1117', color: '#38bdf8' }}>⚡ Google Gemini 1.5 Flash (Fast Backup)</option>
              <option value="gemini-2.0-flash" style={{ background: '#0d1117', color: '#a855f7' }}>🚀 Google Gemini 2.0 Flash (Next-Gen)</option>
              <option value="stehouwer_qwen:latest" style={{ background: '#0d1117', color: '#a855f7' }}>🚀 Stehouwer Qwen 23B (High Capacity)</option>
              <option value="stehouwer_dolphin:latest" style={{ background: '#0d1117', color: '#f43f5e' }}>🐬 Stehouwer Dolphin 8.5B (Uncensored)</option>
              <option value="stehouwer_hermes:latest" style={{ background: '#0d1117', color: '#38bdf8' }}>🔮 Stehouwer Hermes 8.5B (Reasoning)</option>
              <option value="qwen2.5-coder:latest" style={{ background: '#0d1117', color: '#34d399' }}>💻 Qwen 2.5 Coder (Polyglot Engineer)</option>
              <option value="gemma4:12b" style={{ background: '#0d1117', color: '#fbbf24' }}>💎 Google Gemma 4 12B</option>
              <option value="qwen3.6:latest" style={{ background: '#0d1117', color: '#c084fc' }}>🧠 Qwen 3.6 23B (Heavy Reasoning)</option>
              <option value="command-r:latest" style={{ background: '#0d1117', color: '#818cf8' }}>📚 Cohere Command-R (RAG Specialist)</option>
              <option value="mixtral:latest" style={{ background: '#0d1117', color: '#f472b6' }}>🧩 Mixtral 8x7B (MoE Architecture)</option>
              <option value="llama3.1:latest" style={{ background: '#0d1117', color: '#cbd5e1' }}>🦙 Llama 3.1 8B (Base Model)</option>
            </select>
          </div>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 600 }}>Target:</span>
            <select
              value={targetDevice}
              onChange={(e) => setTargetDevice(e.target.value)}
              style={{
                fontSize: '0.75rem',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                color: '#34d399',
                padding: '4px 12px',
                borderRadius: '8px',
                fontWeight: 700,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value="Host PC (Local)" style={{ background: '#0d1117', color: '#34d399' }}>🖥️ Host PC (Local)</option>
              <option value="Mobile Phone (ADB)" style={{ background: '#0d1117', color: '#f59e0b' }}>📱 Mobile Phone (ADB)</option>
            </select>
          </div>
        </div>

        {/* Feature Badges */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', color: '#34d399', padding: '3px 8px', borderRadius: '6px' }}>
            ⚡ 200GB DB Ready
          </span>
          <span style={{ fontSize: '0.72rem', background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.3)', color: '#c084fc', padding: '3px 8px', borderRadius: '6px' }}>
            🛠️ 8 Master Tools
          </span>
          <span style={{ fontSize: '0.72rem', background: 'rgba(236,72,153,0.12)', border: '1px solid rgba(236,72,153,0.3)', color: '#f472b6', padding: '3px 8px', borderRadius: '6px' }}>
            🎨 ComfyUI Port 8189
          </span>
        </div>
      </div>

      {/* Error Popup */}
      {errorPopup && (
        <div style={{
          padding: '10px 20px', background: 'rgba(239,68,68,0.15)',
          borderBottom: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5',
          fontSize: '0.82rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>⚠️ {errorPopup}</span>
          <button onClick={() => setErrorPopup(null)} style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Main Chat Feed */}
      <div
        ref={messageFeedRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}
      >
        {chatMessages.length === 0 ? (
          <div style={{
            maxWidth: '900px', margin: 'auto', width: '100%', padding: '20px 0',
          }}>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <div style={{
                fontSize: '2.5rem', marginBottom: '12px',
                background: 'linear-gradient(135deg, #60a5fa, #c084fc)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                fontWeight: 800
              }}>
                Stehouwer LLM Assistant
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.95rem', maxWidth: '600px', margin: '0 auto' }}>
                Your unified cognitive AI system. Select a quick starter action below, upload files/code for instant review, or type a custom prompt.
              </p>
            </div>

            {/* Quick Action Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '14px',
            }}>
              {starterCards.map((card, idx) => (
                <div
                  key={idx}
                  onClick={() => handleSendMessage(card.prompt)}
                  style={{
                    background: 'rgba(22, 27, 38, 0.7)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '10px',
                    padding: '16px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease-in-out',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(96, 165, 250, 0.5)';
                    e.currentTarget.style.background = 'rgba(30, 41, 59, 0.9)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                    e.currentTarget.style.background = 'rgba(22, 27, 38, 0.7)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '0.92rem', color: '#f1f5f9', marginBottom: '6px' }}>
                    {card.title}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: '1.4' }}>
                    {card.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          chatMessages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '82%',
              }}
            >
              {/* Role Header */}
              <div style={{
                fontSize: '0.75rem', color: '#64748b', marginBottom: '4px', fontWeight: 500,
                textAlign: msg.role === 'user' ? 'right' : 'left',
              }}>
                {msg.role === 'user' ? '👤 You' : '🤖 Stehouwer LLM'}
              </div>

              {/* Message Bubble */}
              <div style={{
                padding: '14px 18px',
                borderRadius: msg.role === 'user' ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                background: msg.role === 'user' ? 'linear-gradient(135deg, #2563eb, #1d4ed8)' : 'rgba(26, 33, 48, 0.95)',
                border: msg.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
                color: '#f8fafc', fontSize: '0.92rem', lineHeight: '1.6',
              }}>
                {/* Attachment Badges */}
                {msg.attachments && msg.attachments.length > 0 && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                    {msg.attachments.map((att, i) => (
                      <div key={i} style={{
                        fontSize: '0.75rem', background: 'rgba(255,255,255,0.15)',
                        padding: '4px 10px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '6px',
                      }}>
                        {att.is_image ? '🖼️' : '📎'} {att.name} ({(att.size/1024).toFixed(1)} KB)
                      </div>
                    ))}
                  </div>
                )}

                {/* Formatted Content */}
                {msg.planData && Object.keys(msg.planData).length > 0 && msg.planData.plan_id ? (
                  <AgentPlanReviewCard 
                    planData={msg.planData} 
                    onExecutePlan={(plan_id, steps) => handleExecutePlan(plan_id, steps)}
                    onRequestRevisions={() => { setFooterInput(`@Developer revise plan ${msg.planData.plan_id}: `); document.querySelector('textarea')?.focus(); }}
                  />
                ) : (
                  <FormattedMessageContent
                    content={msg.displayContent || msg.content || ''}
                    role={msg.role}
                  />
                )}

                {/* Reasoning Inspector for Assistant Messages */}
                {msg.role === 'assistant' && (
                  <ReasoningInspector msg={msg} />
                )}
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div style={{ alignSelf: 'flex-start', color: '#60a5fa', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 14px', borderRadius: '12px' }}>
            <span style={{ animation: 'spin 1s linear infinite' }}>⚙️</span> Stehouwer LLM is reasoning & executing tools...
          </div>
        )}
      </div>

      {/* Footer Input Controls */}
      <div style={{
        padding: '16px 20px',
        borderTop: '1px solid rgba(255,255,255,0.08)',
        background: 'rgba(12, 15, 22, 0.98)',
      }}>
        {/* Attached Files Preview Bar (GPT Style) */}
        {attachments.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            {attachments.map((att, index) => (
              <div key={index} style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                background: 'rgba(30, 41, 59, 0.95)',
                border: '1px solid rgba(59,130,246,0.5)',
                borderRadius: '8px', padding: '6px 12px', fontSize: '0.82rem', color: '#93c5fd',
              }}>
                <span>{att.is_image ? '🖼️' : '📄'}</span>
                <span style={{ fontWeight: 600 }}>{att.name}</span>
                <span style={{ color: '#64748b', fontSize: '0.72rem' }}>({(att.size / 1024).toFixed(1)} KB)</span>
                <button
                  onClick={() => removeAttachment(index)}
                  style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', marginLeft: '4px', fontSize: '0.9rem' }}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* @Tag Quick Actions */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
          {['@Developer', '@Calendar', '@Documents', '@Email'].map(tag => (
            <button
              key={tag}
              onClick={() => setFooterInput(prev => (prev ? prev + ' ' + tag + ' ' : tag + ' '))}
              style={{
                background: 'rgba(59, 130, 246, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.4)',
                color: '#93c5fd',
                borderRadius: '12px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                cursor: 'pointer',
                fontWeight: 600,
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Phase 7.1 Control Bar Injected Above Input */}
        <ChatToolControlBar onToolToggle={setActiveTools} />
        <ChatContextToolbar activeContexts={activeContexts} onToggleContext={toggleContext} />

        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          {/* Attachment Button 📎 */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploadingFile || isLoading}
            title="Attach code or document for LLM analysis"
            style={{
              width: '42px', height: '42px',
              background: isUploadingFile ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '10px', cursor: 'pointer', fontSize: '1.2rem',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8',
              transition: 'background 0.2s',
            }}
          >
            📎
          </button>

          <textarea
            value={footerInput}
            onChange={(e) => setFooterInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder={attachments.length > 0 ? "Add instructions for attached files..." : "Message Stehouwer LLM or attach files... (Enter to send)"}
            rows={2}
            style={{
              flex: 1,
              background: 'rgba(0,0,0,0.5)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '10px',
              color: '#f8fafc',
              padding: '10px 14px',
              fontSize: '0.9rem',
              resize: 'none',
              outline: 'none',
              fontFamily: 'inherit',
              lineHeight: '1.5',
            }}
          />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                onClick={toggleListening}
                title="Toggle Voice Input (STT)"
                style={{
                  width: '42px', height: '40px',
                  background: isListening ? 'rgba(239,68,68,0.25)' : 'rgba(255,255,255,0.06)',
                  border: `1px solid ${isListening ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.12)'}`,
                  borderRadius: '10px', cursor: 'pointer', fontSize: '1.1rem',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                🎙️
              </button>
              <button
                onClick={() => setAutoSpeak(!autoSpeak)}
                title={autoSpeak ? "Auto Readout (TTS) Enabled" : "Enable Auto Readout (TTS)"}
                style={{
                  width: '42px', height: '40px',
                  background: autoSpeak ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.06)',
                  border: `1px solid ${autoSpeak ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.12)'}`,
                  borderRadius: '10px', cursor: 'pointer', fontSize: '1.1rem',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                🔊
              </button>
            </div>
            <button
              onClick={() => handleSendMessage()}
              disabled={(!footerInput.trim() && attachments.length === 0) || isLoading}
              style={{
                width: '42px', height: '40px',
                background: (footerInput.trim() || attachments.length > 0) && !isLoading ? '#2563eb' : 'rgba(255,255,255,0.06)',
                border: 'none',
                borderRadius: '10px',
                cursor: (footerInput.trim() || attachments.length > 0) && !isLoading ? 'pointer' : 'not-allowed',
                fontSize: '1.1rem',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: (footerInput.trim() || attachments.length > 0) && !isLoading ? '#fff' : '#475569',
                transition: 'background 0.2s',
              }}
            >
              ➤
            </button>
          </div>
        </div>

        {/* Clear screen & Action Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
          {chatMessages.length > 0 ? (
            <button
              onClick={() => setChatMessages([])}
              style={{
                background: 'none', border: 'none', color: '#64748b', fontSize: '0.75rem', cursor: 'pointer',
              }}
            >
              Clear Screen (Retains Memory)
            </button>
          ) : <span />}

          <span style={{ color: '#475569', fontSize: '0.72rem' }}>
            Stehouwer LLM v1.6.2 • RTX 4090 GPU Accelerated
          </span>
        </div>
      </div>
    </div>
  );
}
```

*End of ChatTab.jsx*

---

## EmailClientTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import { 
    Mail, Loader, Inbox, RotateCcw, Search, ShieldCheck, ShieldAlert, 
    Sparkles, CheckCircle2, AlertTriangle, Send, Copy, Check, Filter, 
    FileText, Tag, MessageSquare, ExternalLink, RefreshCw, Cpu, Clock, Trash2, Shield
} from 'lucide-react';
import { useBackendHealth } from './useBackendHealth';

const EmailClientTab = () => {
    const { isBackendHealthy, backendUrl } = useBackendHealth();
    const [emails, setEmails] = useState([]);
    const [outboxItems, setOutboxItems] = useState([]);
    const [oauthStatus, setOauthStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [selectedEmail, setSelectedEmail] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('All');
    const [activeTab, setActiveTab] = useState('content'); // 'content' | 'insights' | 'reply' | 'outbox'
    
    // AI Reply & Outbox state
    const [replyNotes, setReplyNotes] = useState('');
    const [replyTone, setReplyTone] = useState('Professional');
    const [generatingReply, setGeneratingReply] = useState(false);
    const [generatedDraft, setGeneratedDraft] = useState('');
    const [copiedReply, setCopiedReply] = useState(false);
    const [queuingDraft, setQueuingDraft] = useState(false);
    
    // Thoughtful Friction Modal State
    const [approvalModalItem, setApprovalModalItem] = useState(null);
    const [dispatching, setDispatching] = useState(false);
    
    // On-demand analysis state
    const [analyzingEmail, setAnalyzingEmail] = useState(false);

    const fetchEmails = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${backendUrl}/api/v1/emails`);
            if (res.ok) {
                const data = await res.json();
                const fetchedEmails = data.data || [];
                setEmails(fetchedEmails);
                if (fetchedEmails.length > 0 && !selectedEmail) {
                    setSelectedEmail(fetchedEmails[0]);
                }
            }
        } catch (e) {
            console.error("Failed to fetch emails:", e);
        }
        setLoading(false);
    };

    const fetchOutbox = async () => {
        try {
            const res = await fetch(`${backendUrl}/api/v1/emails/outbox`);
            if (res.ok) {
                const data = await res.json();
                setOutboxItems(data.data || []);
            }
        } catch (e) {
            console.error("Failed to fetch outbox:", e);
        }
    };

    const fetchOauthStatus = async () => {
        try {
            const res = await fetch(`${backendUrl}/api/v1/emails/oauth-status`);
            if (res.ok) {
                const data = await res.json();
                setOauthStatus(data.data);
            }
        } catch (e) {
            console.error("Failed to fetch OAuth status:", e);
        }
    };

    const triggerSync = async () => {
        setSyncing(true);
        try {
            await fetch(`${backendUrl}/api/v1/emails/sync`, { method: 'POST' });
            await fetchEmails();
            await fetchOauthStatus();
        } catch (e) {
            console.error("Failed to trigger sync:", e);
        }
        setSyncing(false);
    };

    const reAnalyzeSelectedEmail = async () => {
        if (!selectedEmail) return;
        setAnalyzingEmail(true);
        try {
            const res = await fetch(`${backendUrl}/api/v1/emails/analyze-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email_id: selectedEmail.id })
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'success') {
                    const updatedNlp = data.data;
                    setSelectedEmail(prev => ({ ...prev, nlp_analysis: updatedNlp }));
                    setEmails(prev => prev.map(e => e.id === selectedEmail.id ? { ...e, nlp_analysis: updatedNlp } : e));
                }
            }
        } catch (e) {
            console.error("Failed to re-analyze email:", e);
        }
        setAnalyzingEmail(false);
    };

    const generateSmartReply = async () => {
        if (!selectedEmail) return;
        setGeneratingReply(true);
        setGeneratedDraft('');
        setCopiedReply(false);
        try {
            const res = await fetch(`${backendUrl}/api/v1/emails/generate-reply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sender: selectedEmail.sender,
                    subject: selectedEmail.subject,
                    body_snippet: selectedEmail.body || selectedEmail.snippet,
                    user_notes: replyNotes,
                    tone_preference: replyTone
                })
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'success') {
                    setGeneratedDraft(data.draft);
                }
            }
        } catch (e) {
            console.error("Failed to generate smart reply:", e);
        }
        setGeneratingReply(false);
    };

    const queueDraftToOutbox = async () => {
        if (!selectedEmail || !generatedDraft) return;
        setQueuingDraft(true);
        try {
            const recipient = selectedEmail.sender.match(/<(.+?)>/)?.[1] || selectedEmail.sender;
            const res = await fetch(`${backendUrl}/api/v1/emails/outbox/queue`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipient: recipient,
                    subject: `Re: ${selectedEmail.subject}`,
                    body: generatedDraft
                })
            });
            if (res.ok) {
                await fetchOutbox();
                setActiveTab('outbox');
            }
        } catch (e) {
            console.error("Failed to queue draft:", e);
        }
        setQueuingDraft(false);
    };

    const handleApproveAndSend = async (draftId) => {
        setDispatching(true);
        try {
            const res = await fetch(`${backendUrl}/api/v1/emails/outbox/approve-send`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ draft_id: draftId })
            });
            if (res.ok) {
                await fetchOutbox();
                setApprovalModalItem(null);
            }
        } catch (e) {
            console.error("Failed to dispatch email:", e);
        }
        setDispatching(false);
    };

    const handleRejectDraft = async (draftId) => {
        try {
            await fetch(`${backendUrl}/api/v1/emails/outbox/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ draft_id: draftId })
            });
            await fetchOutbox();
        } catch (e) {
            console.error("Failed to reject draft:", e);
        }
    };

    useEffect(() => {
        fetchEmails();
        fetchOutbox();
        fetchOauthStatus();
    }, [backendUrl]);

    // Filter emails
    const filteredEmails = emails.filter(em => {
        const query = searchQuery.toLowerCase();
        const matchesQuery = 
            em.sender.toLowerCase().includes(query) ||
            em.subject.toLowerCase().includes(query) ||
            em.snippet.toLowerCase().includes(query) ||
            (em.nlp_analysis?.summary && em.nlp_analysis.summary.toLowerCase().includes(query));

        if (!matchesQuery) return false;

        if (activeCategory === 'All') return true;
        if (activeCategory === 'High Urgency') return em.nlp_analysis?.urgency === 'High';
        if (activeCategory === 'Has Actions') return (em.nlp_analysis?.action_items || []).length > 0;
        return em.nlp_analysis?.category === activeCategory;
    });

    const getUrgencyBadge = (urgency) => {
        switch (urgency) {
            case 'High':
                return <span className="px-2 py-0.5 text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30 rounded">HIGH URGENCY</span>;
            case 'Medium':
                return <span className="px-2 py-0.5 text-[10px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded">MED URGENCY</span>;
            default:
                return <span className="px-2 py-0.5 text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700 rounded">LOW URGENCY</span>;
        }
    };

    const getCategoryBadge = (category) => {
        return (
            <span className="px-2 py-0.5 text-[10px] font-medium bg-blue-500/10 text-blue-300 border border-blue-500/20 rounded">
                {category || 'Other'}
            </span>
        );
    };

    return (
        <div className="flex flex-col h-full bg-[#0a0a0a] text-gray-200 font-sans relative">
            {/* Thoughtful Friction Confirmation Modal */}
            {approvalModalItem && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#121212] border border-amber-500/40 rounded-xl p-6 max-w-lg w-full shadow-2xl space-y-4">
                        <div className="flex items-center gap-3 text-amber-400 border-b border-[#222] pb-3">
                            <Shield className="w-6 h-6 shrink-0" />
                            <div>
                                <h3 className="font-bold text-base text-white">Thoughtful Friction Security Gate</h3>
                                <p className="text-xs text-gray-400">Explicit User Authorization Required Before Dispatch</p>
                            </div>
                        </div>

                        <div className="space-y-2 text-xs text-gray-300 bg-[#1a1a1a] p-3 rounded border border-[#333]">
                            <div><span className="font-semibold text-gray-400">Recipient:</span> {approvalModalItem.recipient}</div>
                            <div><span className="font-semibold text-gray-400">Subject:</span> {approvalModalItem.subject}</div>
                            <div className="mt-2 text-[11px] text-gray-400 border-t border-[#2a2a2a] pt-2 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
                                {approvalModalItem.body}
                            </div>
                        </div>

                        <p className="text-[11px] text-amber-300/80 bg-amber-500/10 p-2.5 rounded border border-amber-500/20">
                            <strong>Note:</strong> Approving will execute an immediate OAuth 2.0 Gmail API call to dispatch this message directly to external recipients.
                        </p>

                        <div className="flex justify-end gap-3 pt-2">
                            <button
                                onClick={() => setApprovalModalItem(null)}
                                className="px-4 py-2 text-xs font-semibold bg-[#222] hover:bg-[#333] text-gray-300 rounded border border-[#444] transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleApproveAndSend(approvalModalItem.id)}
                                disabled={dispatching}
                                className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white rounded transition-colors disabled:opacity-50"
                            >
                                <Send className={`w-3.5 h-3.5 ${dispatching ? 'animate-spin' : ''}`} />
                                {dispatching ? 'Dispatching Gmail...' : 'Approve & Send Now'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Top Status Header */}
            <div className="px-6 py-3 border-b border-[#222] bg-[#111] flex flex-wrap justify-between items-center gap-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-600/20 border border-blue-500/30 rounded-lg text-blue-400">
                        <Mail className="w-5 h-5" />
                    </div>
                    <div>
                        <h1 className="text-base font-bold text-white flex items-center gap-2">
                            Gmail Intelligence Client
                            <span className="px-2 py-0.5 text-xs bg-blue-900/40 text-blue-400 border border-blue-500/30 rounded-full font-mono">
                                OAuth 2.0
                            </span>
                        </h1>
                        <p className="text-xs text-gray-400">
                            Stehouwer LLM NLP Pattern Mining & Communications Engine
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* OAuth Health Badge */}
                    <div className="flex items-center gap-2 bg-[#1a1a1a] px-3 py-1.5 rounded-md border border-[#333] text-xs">
                        {oauthStatus?.is_valid ? (
                            <>
                                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                                <div>
                                    <span className="text-emerald-400 font-medium">OAuth Active</span>
                                    {oauthStatus.last_sync_timestamp && (
                                        <span className="text-gray-500 ml-2 text-[10px]">
                                            Synced: {new Date(oauthStatus.last_sync_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    )}
                                </div>
                            </>
                        ) : (
                            <>
                                <ShieldAlert className="w-4 h-4 text-amber-400" />
                                <span className="text-amber-400 font-medium">{oauthStatus?.status_message || "Checking OAuth..."}</span>
                            </>
                        )}
                    </div>

                    <button
                        onClick={triggerSync}
                        disabled={syncing}
                        className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-md transition-all shadow-sm disabled:opacity-50"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                        {syncing ? 'Syncing Gmail...' : 'Sync Gmail'}
                    </button>
                </div>
            </div>

            {/* Main Content Layout */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left Sidebar - Inbox & Filters */}
                <div className="w-1/3 border-r border-[#222] flex flex-col h-full bg-[#0d0d0d]">
                    {/* Search Bar */}
                    <div className="p-3 border-b border-[#222] bg-[#141414] space-y-2">
                        <div className="relative">
                            <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-500" />
                            <input 
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search sender, subject, summary..."
                                className="w-full bg-[#1e1e1e] border border-[#333] text-xs rounded-md pl-9 pr-3 py-2 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                            />
                        </div>

                        {/* Category Filter Pills */}
                        <div className="flex gap-1 overflow-x-auto pb-1 custom-scrollbar text-[11px]">
                            {['All', 'High Urgency', 'Has Actions', 'Work', 'Financial', 'Crypto', 'Utility'].map(cat => (
                                <button
                                    key={cat}
                                    onClick={() => setActiveCategory(cat)}
                                    className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-colors ${
                                        activeCategory === cat 
                                            ? 'bg-blue-600 text-white font-medium' 
                                            : 'bg-[#222] text-gray-400 hover:bg-[#2b2b2b]'
                                    }`}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Email List */}
                    <div className="overflow-y-auto flex-1 custom-scrollbar divide-y divide-[#1c1c1c]">
                        {loading && emails.length === 0 ? (
                            <div className="flex justify-center items-center h-40 text-gray-500 text-xs">
                                <Loader className="w-5 h-5 animate-spin mr-2 text-blue-500" /> Loading emails...
                            </div>
                        ) : filteredEmails.length === 0 ? (
                            <div className="p-6 text-center text-gray-500 text-xs">
                                No matching emails found.
                            </div>
                        ) : (
                            filteredEmails.map((email) => {
                                const nlp = email.nlp_analysis || {};
                                const isSelected = selectedEmail?.id === email.id;
                                return (
                                    <div 
                                        key={email.id} 
                                        onClick={() => {
                                            setSelectedEmail(email);
                                            setGeneratedDraft('');
                                        }}
                                        className={`p-3.5 cursor-pointer transition-all ${
                                            isSelected 
                                                ? 'bg-[#1e2430] border-l-4 border-l-blue-500' 
                                                : 'hover:bg-[#141414] border-l-4 border-l-transparent'
                                        }`}
                                    >
                                        <div className="flex justify-between items-baseline mb-1">
                                            <h4 className="font-semibold text-xs text-white truncate pr-2" title={email.sender}>
                                                {email.sender.replace(/<.*>/, '') || email.sender}
                                            </h4>
                                            <span className="text-[10px] text-gray-500 whitespace-nowrap">
                                                {new Date(email.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                            </span>
                                        </div>

                                        <div className="text-xs font-medium text-gray-200 mb-1 line-clamp-1">
                                            {email.subject || "(No Subject)"}
                                        </div>

                                        {nlp.summary ? (
                                            <p className="text-[11px] text-gray-400 line-clamp-2 mb-2 italic bg-[#151820] p-1.5 rounded border border-[#252b38]">
                                                "{nlp.summary}"
                                            </p>
                                        ) : (
                                            <p className="text-[11px] text-gray-500 line-clamp-2 mb-2">
                                                {email.snippet}
                                            </p>
                                        )}

                                        <div className="flex flex-wrap items-center gap-1.5">
                                            {getUrgencyBadge(nlp.urgency)}
                                            {getCategoryBadge(nlp.category)}
                                            {nlp.action_items?.length > 0 && (
                                                <span className="px-1.5 py-0.5 text-[9px] bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded flex items-center gap-1">
                                                    <CheckCircle2 className="w-2.5 h-2.5" />
                                                    {nlp.action_items.length} Actions
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>

                {/* Right Pane - Email Detail & Stehouwer Intelligence Hub */}
                <div className="w-2/3 flex flex-col h-full bg-[#0a0a0a]">
                    {selectedEmail ? (
                        <div className="flex flex-col h-full">
                            {/* Email Header */}
                            <div className="p-5 border-b border-[#222] bg-[#111]">
                                <div className="flex justify-between items-start mb-3">
                                    <h2 className="text-lg font-bold text-white leading-snug">
                                        {selectedEmail.subject || "(No Subject)"}
                                    </h2>
                                    <button 
                                        onClick={reAnalyzeSelectedEmail}
                                        disabled={analyzingEmail}
                                        className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium bg-[#222] hover:bg-[#333] text-gray-300 rounded border border-[#444] transition-all disabled:opacity-50"
                                    >
                                        <Sparkles className={`w-3 h-3 text-amber-400 ${analyzingEmail ? 'animate-spin' : ''}`} />
                                        {analyzingEmail ? 'Analyzing...' : 'Re-Analyze NLP'}
                                    </button>
                                </div>

                                <div className="flex items-center justify-between text-xs text-gray-400">
                                    <div className="flex items-center gap-2">
                                        <div className="w-8 h-8 rounded-full bg-blue-600/30 text-blue-400 font-bold flex items-center justify-center border border-blue-500/40 text-sm">
                                            {selectedEmail.sender.charAt(0).toUpperCase()}
                                        </div>
                                        <div>
                                            <span className="font-semibold text-gray-200">{selectedEmail.sender}</span>
                                            <div className="text-[10px] text-gray-500">{new Date(selectedEmail.date).toLocaleString()}</div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        {getUrgencyBadge(selectedEmail.nlp_analysis?.urgency)}
                                        {getCategoryBadge(selectedEmail.nlp_analysis?.category)}
                                    </div>
                                </div>

                                {/* View Switcher Tabs */}
                                <div className="flex gap-2 mt-4 border-t border-[#222] pt-3">
                                    <button
                                        onClick={() => setActiveTab('content')}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                            activeTab === 'content'
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-[#1e1e1e] text-gray-400 hover:bg-[#2a2a2a]'
                                        }`}
                                    >
                                        <FileText className="w-3.5 h-3.5" /> Body Content
                                    </button>

                                    <button
                                        onClick={() => setActiveTab('insights')}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                            activeTab === 'insights'
                                                ? 'bg-purple-600 text-white'
                                                : 'bg-[#1e1e1e] text-purple-400 hover:bg-[#2a2a2a]'
                                        }`}
                                    >
                                        <Cpu className="w-3.5 h-3.5" /> Stehouwer AI Insights
                                    </button>

                                    <button
                                        onClick={() => setActiveTab('reply')}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                            activeTab === 'reply'
                                                ? 'bg-emerald-600 text-white'
                                                : 'bg-[#1e1e1e] text-emerald-400 hover:bg-[#2a2a2a]'
                                        }`}
                                    >
                                        <Send className="w-3.5 h-3.5" /> Smart Reply Generator
                                    </button>

                                    <button
                                        onClick={() => setActiveTab('outbox')}
                                        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                            activeTab === 'outbox'
                                                ? 'bg-amber-600 text-white'
                                                : 'bg-[#1e1e1e] text-amber-400 hover:bg-[#2a2a2a]'
                                        }`}
                                    >
                                        <Clock className="w-3.5 h-3.5" /> Outbox Queue ({outboxItems.filter(i => i.status === 'PENDING_APPROVAL').length})
                                    </button>
                                </div>
                            </div>

                            {/* View Panel Content */}
                            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                                {activeTab === 'content' && (
                                    <div className="bg-[#141414] p-5 rounded-lg border border-[#222] text-xs text-gray-300 leading-relaxed font-sans whitespace-pre-wrap">
                                        {selectedEmail.body || "No email body content parsed."}
                                    </div>
                                )}

                                {activeTab === 'insights' && (
                                    <div className="space-y-4">
                                        {/* Executive Summary Card */}
                                        <div className="bg-[#141824] border border-blue-500/30 p-4 rounded-lg">
                                            <h3 className="text-xs font-bold text-blue-400 flex items-center gap-2 mb-2">
                                                <Sparkles className="w-4 h-4 text-blue-400" />
                                                Executive Summary
                                            </h3>
                                            <p className="text-xs text-gray-200 leading-relaxed italic">
                                                "{selectedEmail.nlp_analysis?.summary || "Summary pending analysis."}"
                                            </p>
                                        </div>

                                        {/* NLP Metrics Grid */}
                                        <div className="grid grid-cols-3 gap-3">
                                            <div className="bg-[#141414] p-3 rounded-lg border border-[#222]">
                                                <div className="text-[10px] text-gray-500 font-semibold mb-1">TONE</div>
                                                <div className="text-xs font-bold text-purple-400">
                                                    {selectedEmail.nlp_analysis?.tone || 'Neutral'}
                                                </div>
                                            </div>

                                            <div className="bg-[#141414] p-3 rounded-lg border border-[#222]">
                                                <div className="text-[10px] text-gray-500 font-semibold mb-1">SENTIMENT</div>
                                                <div className="text-xs font-bold text-emerald-400">
                                                    {selectedEmail.nlp_analysis?.sentiment || 'Neutral'}
                                                </div>
                                            </div>

                                            <div className="bg-[#141414] p-3 rounded-lg border border-[#222]">
                                                <div className="text-[10px] text-gray-500 font-semibold mb-1">CATEGORY</div>
                                                <div className="text-xs font-bold text-blue-400">
                                                    {selectedEmail.nlp_analysis?.category || 'Other'}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Action Items List */}
                                        <div className="bg-[#141414] p-4 rounded-lg border border-[#222]">
                                            <h4 className="text-xs font-bold text-gray-200 flex items-center gap-2 mb-3">
                                                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                                Extracted Action Items ({selectedEmail.nlp_analysis?.action_items?.length || 0})
                                            </h4>
                                            {selectedEmail.nlp_analysis?.action_items?.length > 0 ? (
                                                <ul className="space-y-2">
                                                    {selectedEmail.nlp_analysis.action_items.map((item, idx) => (
                                                        <li key={idx} className="flex items-start gap-2 text-xs text-gray-300 bg-[#1c1c1c] p-2 rounded border border-[#2a2a2a]">
                                                            <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-[10px] shrink-0 mt-0.5">
                                                                {idx + 1}
                                                            </span>
                                                            <span>{item}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p className="text-xs text-gray-500">No pending action items identified in this message.</p>
                                            )}
                                        </div>

                                        {/* Key Entities & Reference Links */}
                                        <div className="bg-[#141414] p-4 rounded-lg border border-[#222]">
                                            <h4 className="text-xs font-bold text-gray-200 flex items-center gap-2 mb-3">
                                                <Tag className="w-4 h-4 text-amber-400" />
                                                Extracted Entities & References
                                            </h4>
                                            {selectedEmail.nlp_analysis?.entities?.length > 0 ? (
                                                <div className="flex flex-wrap gap-2">
                                                    {selectedEmail.nlp_analysis.entities.map((entity, idx) => (
                                                        <span key={idx} className="px-2 py-1 text-xs bg-[#1e1e1e] text-amber-300 border border-[#333] rounded font-mono">
                                                            {entity}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : (
                                                <p className="text-xs text-gray-500">No entity metrics extracted.</p>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'reply' && (
                                    <div className="space-y-4">
                                        <div className="bg-[#141414] p-4 rounded-lg border border-[#222] space-y-3">
                                            <h3 className="text-xs font-bold text-emerald-400 flex items-center gap-2">
                                                <Sparkles className="w-4 h-4" />
                                                Draft Reply with Stehouwer LLM
                                            </h3>

                                            <div>
                                                <label className="block text-[11px] font-medium text-gray-400 mb-1">
                                                    Tone Preference
                                                </label>
                                                <select
                                                    value={replyTone}
                                                    onChange={(e) => setReplyTone(e.target.value)}
                                                    className="w-full bg-[#1e1e1e] border border-[#333] text-xs text-gray-200 rounded p-2 focus:outline-none focus:border-emerald-500"
                                                >
                                                    <option value="Professional">Professional & Courteous</option>
                                                    <option value="Concise">Concise & Direct</option>
                                                    <option value="Friendly">Warm & Friendly</option>
                                                    <option value="Firm">Firm & Decisive</option>
                                                </select>
                                            </div>

                                            <div>
                                                <label className="block text-[11px] font-medium text-gray-400 mb-1">
                                                    Guidance / Key Points to Include (Optional)
                                                </label>
                                                <textarea
                                                    rows={3}
                                                    value={replyNotes}
                                                    onChange={(e) => setReplyNotes(e.target.value)}
                                                    placeholder="e.g. Accept invitation for Tuesday, ask for agenda attached..."
                                                    className="w-full bg-[#1e1e1e] border border-[#333] text-xs text-gray-200 rounded p-2 focus:outline-none focus:border-emerald-500"
                                                />
                                            </div>

                                            <button
                                                onClick={generateSmartReply}
                                                disabled={generatingReply}
                                                className="w-full flex items-center justify-center gap-2 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded transition-colors disabled:opacity-50"
                                            >
                                                <Sparkles className={`w-3.5 h-3.5 ${generatingReply ? 'animate-spin' : ''}`} />
                                                {generatingReply ? 'Generating Response Draft...' : 'Generate Smart Draft'}
                                            </button>
                                        </div>

                                        {/* Generated Response Output */}
                                        {generatedDraft && (
                                            <div className="bg-[#121c16] border border-emerald-500/40 p-4 rounded-lg space-y-3">
                                                <div className="flex justify-between items-center">
                                                    <h4 className="text-xs font-bold text-emerald-400">Generated Draft Response</h4>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            onClick={queueDraftToOutbox}
                                                            disabled={queuingDraft}
                                                            className="flex items-center gap-1 px-2.5 py-1 text-[11px] bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded transition-colors disabled:opacity-50"
                                                        >
                                                            <Clock className="w-3 h-3" />
                                                            {queuingDraft ? 'Queuing...' : 'Queue to Outbox'}
                                                        </button>
                                                        <button
                                                            onClick={() => {
                                                                navigator.clipboard.writeText(generatedDraft);
                                                                setCopiedReply(true);
                                                                setTimeout(() => setCopiedReply(false), 2000);
                                                            }}
                                                            className="flex items-center gap-1 px-2.5 py-1 text-[11px] bg-[#1c2e22] hover:bg-[#253d2d] text-emerald-300 rounded border border-emerald-500/30 transition-colors"
                                                        >
                                                            {copiedReply ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                                            {copiedReply ? 'Copied!' : 'Copy'}
                                                        </button>
                                                    </div>
                                                </div>

                                                <div className="bg-[#0a120c] p-4 rounded border border-[#1b3323] text-xs text-gray-200 whitespace-pre-wrap leading-relaxed font-sans">
                                                    {generatedDraft}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {activeTab === 'outbox' && (
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center">
                                            <h3 className="text-xs font-bold text-amber-400 flex items-center gap-2">
                                                <Clock className="w-4 h-4" />
                                                Outbox Approval Queue (Thoughtful Friction Protection)
                                            </h3>
                                            <span className="text-[10px] text-gray-400">
                                                {outboxItems.length} Drafts Total
                                            </span>
                                        </div>

                                        {outboxItems.length === 0 ? (
                                            <div className="bg-[#141414] p-8 rounded-lg border border-[#222] text-center text-gray-500 text-xs">
                                                No drafts currently in Outbox Queue.
                                            </div>
                                        ) : (
                                            outboxItems.map((item) => (
                                                <div key={item.id} className="bg-[#141414] border border-[#262626] p-4 rounded-lg space-y-3">
                                                    <div className="flex justify-between items-start">
                                                        <div>
                                                            <div className="text-xs font-bold text-white">{item.subject}</div>
                                                            <div className="text-[11px] text-gray-400">To: {item.recipient}</div>
                                                        </div>
                                                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                                                            item.status === 'SENT' 
                                                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                                                                : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                                        }`}>
                                                            {item.status}
                                                        </span>
                                                    </div>

                                                    <div className="bg-[#0c0c0c] p-3 rounded border border-[#1f1f1f] text-xs text-gray-300 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto">
                                                        {item.body}
                                                    </div>

                                                    {item.status === 'PENDING_APPROVAL' && (
                                                        <div className="flex justify-end gap-2 pt-1">
                                                            <button
                                                                onClick={() => handleRejectDraft(item.id)}
                                                                className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-950/40 hover:bg-red-900/60 text-red-400 border border-red-800/40 rounded transition-colors"
                                                            >
                                                                <Trash2 className="w-3.5 h-3.5" /> Reject
                                                            </button>
                                                            <button
                                                                onClick={() => setApprovalModalItem(item)}
                                                                className="flex items-center gap-1 px-4 py-1.5 text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white rounded transition-colors shadow"
                                                            >
                                                                <Send className="w-3.5 h-3.5" /> Review & Send
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            ))
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
                            <Mail className="w-16 h-16 mb-4 text-[#222]" />
                            <p className="text-xs">Select an email to inspect AI insights, generate replies, or review outbox drafts</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default EmailClientTab;
```

*End of EmailClientTab.jsx*

---

# Business, Commerce & Analytics
*6 file(s) in this category*

## DigitalStorefrontTab.jsx
```jsx
import React, { useState, useEffect } from 'react';

// Lightweight Inline Icons with explicit SVG dimensions
const ZapIcon = ({ color = "#58a6ff", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
  </svg>
);

const BriefcaseIcon = ({ color = "#3fb950", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
  </svg>
);

const ChartIcon = ({ color = "#a371f7", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
);

const CreditCardIcon = ({ color = "#d29922", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
    <line x1="1" y1="10" x2="23" y2="10"></line>
  </svg>
);

const CheckIcon = ({ color = "#3fb950", size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

const CopyIcon = ({ color = "#8b949e", size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
  </svg>
);

const DigitalStorefrontTab = ({ backendUrl, currentUser, selectedModel, subView = 'storefront_hub' }) => {
  const [activeApp, setActiveApp] = useState(subView);
  const [credits, setCredits] = useState(500);
  const [userEmail] = useState(currentUser?.email || "brettstehouwer@gmail.com");

  // AI Content State
  const [prompt, setPrompt] = useState('');
  const [contentType, setContentType] = useState('ad_copy');
  const [generatedContent, setGeneratedContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  // ROI Diagnostic State
  const [hoursPerWeek, setHoursPerWeek] = useState(15);
  const [hourlyRate, setHourlyRate] = useState(45);
  const [numEmployees, setNumEmployees] = useState(3);
  const [isUnlocked, setIsUnlocked] = useState(false);

  // Lead Tracker State
  const [leads, setLeads] = useState([
    { id: 1, name: 'Ottawa Valley Plumbing', contact: 'mike@ottawaplumbing.com', status: 'Active Trial', revenue: '$29/mo' },
    { id: 2, name: 'Lakeshore Landscaping', contact: 'sarah@lakeshoreland.com', status: 'Subscribed', revenue: '$29/mo' },
    { id: 3, name: 'Grand Haven Auto Care', contact: 'steve@ghauto.com', status: 'Pending Intake', revenue: '$0/mo' },
  ]);
  const [newLeadName, setNewLeadName] = useState('');
  const [newLeadContact, setNewLeadContact] = useState('');

  useEffect(() => {
    if (subView) setActiveApp(subView);
  }, [subView]);

  useEffect(() => {
    fetch(`${backendUrl}/api/storefront/balance?user_email=${encodeURIComponent(userEmail)}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && typeof data.credits === 'number') {
          setCredits(data.credits);
        }
      })
      .catch(err => console.error("Error fetching credit balance:", err));
  }, [backendUrl, userEmail]);

  const handleGenerate = async () => {
    if (!prompt) return;
    setIsGenerating(true);
    setGeneratedContent('');
    setCopied(false);
    
    try {
      const fullPrompt = `[Format: ${contentType.toUpperCase().replace('_', ' ')}] ${prompt}`;
      const res = await fetch(`${backendUrl}/api/storefront/generate-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_email: userEmail, prompt: fullPrompt, model: selectedModel })
      });
      
      const data = await res.json();
      if (data.status === 'success') {
        setGeneratedContent(data.content);
        if (typeof data.credits_remaining === 'number') {
          setCredits(data.credits_remaining);
        }
      } else {
        setGeneratedContent('Error generating content. Please try again.');
      }
    } catch (err) {
      console.error(err);
      setGeneratedContent('Failed to connect to backend.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!generatedContent) return;
    navigator.clipboard.writeText(generatedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleAddLead = (e) => {
    e.preventDefault();
    if (!newLeadName || !newLeadContact) return;
    setLeads([...leads, {
      id: Date.now(),
      name: newLeadName,
      contact: newLeadContact,
      status: 'Active Trial',
      revenue: '$29/mo'
    }]);
    setNewLeadName('');
    setNewLeadContact('');
  };

  // Calculations for ROI Calculator
  const annualHours = hoursPerWeek * 52 * numEmployees;
  const annualCost = annualHours * hourlyRate;
  const estimatedSavings = Math.round(annualCost * 0.65);
  const paybackDays = Math.max(1, Math.round((19 / (estimatedSavings / 365))));

  // --- RENDERERS ---

  const renderHub = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {/* Top Banner */}
      <div style={{ 
        background: 'linear-gradient(135deg, rgba(88, 166, 255, 0.1) 0%, rgba(163, 113, 247, 0.15) 100%)',
        border: '1px solid rgba(88, 166, 255, 0.3)',
        borderRadius: '16px',
        padding: '24px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.8rem', color: '#f0f6fc', fontWeight: '800' }}>🚀 Stehouwer Digital Resale & SaaS Marketplace</h1>
          <p style={{ margin: '6px 0 0 0', color: '#8b949e', fontSize: '0.95rem' }}>
            High-margin digital products & micro-SaaS applications running on your home PC compute with zero marginal cost.
          </p>
        </div>
        <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '30px', padding: '10px 20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ZapIcon color="#d29922" size={22} />
          <span style={{ color: '#f0f6fc', fontWeight: 'bold', fontSize: '1.2rem' }}>{credits} Credits</span>
        </div>
      </div>

      {/* Product Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        
        {/* App 1: AI Content Engine */}
        <div 
          onClick={() => setActiveApp('ai_content_engine')}
          style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '24px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = '#58a6ff'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
        >
          <div>
            <div style={{ background: 'rgba(88, 166, 255, 0.15)', width: '48px', height: '48px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyCenter: 'center', marginBottom: '16px' }}>
              <ZapIcon color="#58a6ff" size={26} />
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.3rem' }}>AI Content Engine</h3>
            <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Credit-based API wrapper for hyper-niche prompts, ad copy, and blog posts. Wraps local GPU Ollama inference with 100% profit margins.
            </p>
          </div>
          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', color: '#58a6ff', fontWeight: 'bold', fontSize: '0.9rem' }}>
            Open App Workspace →
          </div>
        </div>

        {/* App 2: Auto Lead Tracker */}
        <div 
          onClick={() => setActiveApp('lead_tracker')}
          style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '24px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = '#3fb950'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
        >
          <div>
            <div style={{ background: 'rgba(63, 185, 80, 0.15)', width: '48px', height: '48px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyCenter: 'center', marginBottom: '16px' }}>
              <BriefcaseIcon color="#3fb950" size={26} />
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.3rem' }}>Auto Lead Tracker</h3>
            <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Single-feature B2B Micro-SaaS CRM for local service businesses. Monitored via $29/mo recurring subscriptions.
            </p>
          </div>
          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', color: '#3fb950', fontWeight: 'bold', fontSize: '0.9rem' }}>
            Open App Workspace →
          </div>
        </div>

        {/* App 3: AI ROI Diagnostic */}
        <div 
          onClick={() => setActiveApp('roi_diagnostic')}
          style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '16px',
            padding: '24px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = '#a371f7'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = '#30363d'}
        >
          <div>
            <div style={{ background: 'rgba(163, 113, 247, 0.15)', width: '48px', height: '48px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyCenter: 'center', marginBottom: '16px' }}>
              <ChartIcon color="#a371f7" size={26} />
            </div>
            <h3 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.3rem' }}>AI ROI Diagnostic</h3>
            <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem', lineHeight: '1.5' }}>
              Interactive calculator & lead magnet. Generates instant labor cost savings estimates with a $19 one-time paywall for PDF export.
            </p>
          </div>
          <div style={{ marginTop: '20px', display: 'flex', alignItems: 'center', color: '#a371f7', fontWeight: 'bold', fontSize: '0.9rem' }}>
            Open App Workspace →
          </div>
        </div>

      </div>

      {/* Metrics Row */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px' }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#f0f6fc' }}>📊 Real-Time Resale Performance</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Active Customers</span>
            <div style={{ color: '#f0f6fc', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>14</div>
          </div>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Monthly Recurring (MRR)</span>
            <div style={{ color: '#3fb950', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>$406.00</div>
          </div>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Credits Consumed (24h)</span>
            <div style={{ color: '#58a6ff', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>1,420</div>
          </div>
          <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '16px', borderRadius: '12px' }}>
            <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Margin per Request</span>
            <div style={{ color: '#d29922', fontSize: '1.5rem', fontWeight: 'bold', marginTop: '4px' }}>100% (Local)</div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAiContentEngine = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexWrap: 'wrap', gap: '20px', boxSizing: 'border-box', overflowY: 'auto' }}>
      {/* Left Pane: Controls */}
      <div style={{ flex: '1 1 320px', maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: '16px', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', boxSizing: 'border-box' }}>
        <h2 style={{ margin: 0, color: '#f0f6fc', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ZapIcon color="#58a6ff" size={24} /> AI Content Engine
        </h2>
        <p style={{ margin: 0, color: '#8b949e', fontSize: '0.85rem' }}>
          Generates ad copy, blog posts, and prompts. 10 credits deducted per generation.
        </p>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '6px' }}>Content Format</label>
          <select 
            value={contentType} 
            onChange={(e) => setContentType(e.target.value)}
            style={{ width: '100%', background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: '8px', padding: '10px', outline: 'none' }}
          >
            <option value="ad_copy">📢 Facebook & Instagram Ad Copy</option>
            <option value="seo_blog">📝 SEO Blog Outline & Draft</option>
            <option value="cold_email">✉️ Cold Outreach Email</option>
            <option value="social_hook">⚡ Viral Social Media Hooks</option>
          </select>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '6px' }}>Topic or Business Prompt</label>
          <textarea
            style={{ 
              width: '100%', 
              flex: 1, 
              background: '#0d1117', 
              color: '#f0f6fc', 
              border: '1px solid #30363d', 
              borderRadius: '8px', 
              padding: '12px', 
              outline: 'none', 
              resize: 'none',
              fontFamily: 'inherit',
              boxSizing: 'border-box'
            }}
            placeholder="e.g. Write a high-converting Facebook ad for a Ottawa County plumbing service offering 15% off first service call."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating || !prompt || credits < 10}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '8px',
            border: 'none',
            background: isGenerating || !prompt || credits < 10 ? '#21262d' : '#238636',
            color: isGenerating || !prompt || credits < 10 ? '#8b949e' : '#ffffff',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: isGenerating || !prompt || credits < 10 ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          {isGenerating ? '⏳ Processing on GPU...' : credits < 10 ? 'Insufficient Credits' : 'Generate (10 Credits)'}
        </button>

        <div style={{ background: '#0d1117', border: '1px solid #21262d', padding: '12px 16px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#8b949e', fontSize: '0.85rem' }}>Balance:</span>
          <span style={{ color: '#58a6ff', fontWeight: 'bold', fontSize: '1.1rem' }}>{credits} Credits</span>
        </div>
      </div>

      {/* Right Pane: Output */}
      <div style={{ flex: '2 1 400px', maxWidth: '100%', minHeight: '400px', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ background: '#0d1117', borderBottom: '1px solid #30363d', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#f0f6fc', fontWeight: 'bold' }}>Generated Output ({selectedModel})</span>
          {generatedContent && (
            <button 
              onClick={handleCopy}
              style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}
            >
              {copied ? <CheckIcon color="#3fb950" size={16} /> : <CopyIcon color="#8b949e" size={16} />}
              {copied ? 'Copied!' : 'Copy Result'}
            </button>
          )}
        </div>
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto', color: '#c9d1d9', lineHeight: '1.7', whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.95rem' }}>
          {isGenerating ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyCenter: 'center', color: '#58a6ff' }}>
              <div style={{ fontSize: '2rem', marginBottom: '12px' }}>⚙️</div>
              <div>Processing request via local Ollama engine...</div>
            </div>
          ) : generatedContent ? (
            generatedContent
          ) : (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyCenter: 'center', color: '#484f58' }}>
              <ZapIcon color="#30363d" size={48} />
              <p style={{ marginTop: '16px' }}>Enter a prompt on the left to generate content.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderLeadTracker = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px' }}>
        <h2 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <BriefcaseIcon color="#3fb950" size={24} /> Auto Lead Tracker (Micro-SaaS CRM)
        </h2>
        <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem' }}>
          Automated client intake portal for local service businesses. Retainer price: $29/month per account.
        </p>
      </div>

      {/* Add Lead Form */}
      <form onSubmit={handleAddLead} style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '20px', display: 'flex', gap: '16px', alignItems: 'center' }}>
        <input 
          type="text" 
          placeholder="Business Name (e.g. Ottawa Valley Heating)" 
          value={newLeadName}
          onChange={(e) => setNewLeadName(e.target.value)}
          style={{ flex: 1, background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: '8px', padding: '10px', outline: 'none' }}
        />
        <input 
          type="email" 
          placeholder="Contact Email" 
          value={newLeadContact}
          onChange={(e) => setNewLeadContact(e.target.value)}
          style={{ flex: 1, background: '#0d1117', color: '#f0f6fc', border: '1px solid #30363d', borderRadius: '8px', padding: '10px', outline: 'none' }}
        />
        <button type="submit" style={{ background: '#238636', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px 20px', fontWeight: 'bold', cursor: 'pointer' }}>
          + Add Business
        </button>
      </form>

      {/* Leads Table */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', flex: 1 }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#f0f6fc' }}>Active Managed Accounts</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', color: '#c9d1d9', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', fontSize: '0.85rem', textTransform: 'uppercase' }}>
              <th style={{ padding: '12px' }}>Business Name</th>
              <th style={{ padding: '12px' }}>Contact Email</th>
              <th style={{ padding: '12px' }}>Status</th>
              <th style={{ padding: '12px' }}>Subscription Value</th>
            </tr>
          </thead>
          <tbody>
            {leads.map(lead => (
              <tr key={lead.id} style={{ borderBottom: '1px solid #21262d' }}>
                <td style={{ padding: '14px 12px', fontWeight: 'bold', color: '#f0f6fc' }}>{lead.name}</td>
                <td style={{ padding: '14px 12px', color: '#8b949e' }}>{lead.contact}</td>
                <td style={{ padding: '14px 12px' }}>
                  <span style={{ 
                    padding: '4px 10px', 
                    borderRadius: '12px', 
                    fontSize: '0.75rem', 
                    fontWeight: 'bold',
                    background: lead.status === 'Subscribed' ? 'rgba(63, 185, 80, 0.2)' : 'rgba(210, 153, 34, 0.2)',
                    color: lead.status === 'Subscribed' ? '#3fb950' : '#d29922'
                  }}>
                    ● {lead.status}
                  </span>
                </td>
                <td style={{ padding: '14px 12px', color: '#3fb950', fontWeight: 'bold' }}>{lead.revenue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderRoiDiagnostic = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexWrap: 'wrap', gap: '20px', boxSizing: 'border-box', overflowY: 'auto' }}>
      {/* Left Pane: Interactive Inputs */}
      <div style={{ flex: '1 1 320px', maxWidth: '100%', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', boxSizing: 'border-box' }}>
        <div>
          <h2 style={{ margin: '0 0 6px 0', color: '#f0f6fc', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ChartIcon color="#a371f7" size={24} /> AI ROI Diagnostic Calculator
          </h2>
          <p style={{ margin: 0, color: '#8b949e', fontSize: '0.85rem' }}>
            Calculates estimated manual labor cost savings and outputs a paywalled $19 report.
          </p>
        </div>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '8px' }}>
            Manual Task Hours / Week per Employee: <span style={{ color: '#a371f7' }}>{hoursPerWeek} hrs</span>
          </label>
          <input 
            type="range" 
            min="5" 
            max="40" 
            value={hoursPerWeek} 
            onChange={(e) => setHoursPerWeek(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: '#a371f7' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '8px' }}>
            Average Hourly Employee Rate ($): <span style={{ color: '#3fb950' }}>${hourlyRate}/hr</span>
          </label>
          <input 
            type="range" 
            min="20" 
            max="150" 
            value={hourlyRate} 
            onChange={(e) => setHourlyRate(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: '#3fb950' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.85rem', fontWeight: 'bold', marginBottom: '8px' }}>
            Number of Team Members: <span style={{ color: '#58a6ff' }}>{numEmployees} employees</span>
          </label>
          <input 
            type="range" 
            min="1" 
            max="25" 
            value={numEmployees} 
            onChange={(e) => setNumEmployees(parseInt(e.target.value, 10))}
            style={{ width: '100%', accentColor: '#58a6ff' }}
          />
        </div>

        <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '12px', padding: '16px' }}>
          <span style={{ color: '#8b949e', fontSize: '0.8rem', textTransform: 'uppercase' }}>Estimated Annual AI Savings</span>
          <div style={{ color: '#3fb950', fontSize: '2rem', fontWeight: '800', marginTop: '4px' }}>
            ${estimatedSavings.toLocaleString()} / yr
          </div>
        </div>
      </div>

      {/* Right Pane: Report Preview */}
      <div style={{ flex: '2 1 400px', maxWidth: '100%', minHeight: '500px', background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '32px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxSizing: 'border-box' }}>
        <div style={{ overflowX: 'hidden' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '12px' }}>
            <h3 style={{ margin: 0, color: '#f0f6fc', fontSize: '1.5rem' }}>📋 Customized Executive AI Audit Report</h3>
            <span style={{ background: 'rgba(163, 113, 247, 0.2)', color: '#a371f7', padding: '4px 12px', borderRadius: '12px', fontWeight: 'bold', fontSize: '0.8rem' }}>
              Generated for Stehouwer Client
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '32px' }}>
            <div style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #21262d' }}>
              <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>Current Annual Waste</span>
              <p style={{ margin: '4px 0 0 0', color: '#ff7b72', fontSize: '1.2rem', fontWeight: 'bold' }}>${annualCost.toLocaleString()}</p>
            </div>
            <div style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #21262d' }}>
              <span style={{ color: '#8b949e', fontSize: '0.8rem' }}>Estimated Payback Period</span>
              <p style={{ margin: '4px 0 0 0', color: '#58a6ff', fontSize: '1.2rem', fontWeight: 'bold' }}>{paybackDays} Days</p>
            </div>
          </div>

          <div style={{ color: '#c9d1d9', lineHeight: '1.6', fontSize: '0.95rem' }}>
            <p style={{ fontWeight: 'bold', color: '#f0f6fc' }}>Key Optimization Recommendations:</p>
            <ul style={{ paddingLeft: '20px', color: '#8b949e' }}>
              <li>Automate client intake emails and appointment scheduling via AI-BS daemons.</li>
              <li>Deploy specialized document summarizers for invoice processing.</li>
              <li>Integrate local LLM prompt templates to eliminate repetitive team reporting.</li>
            </ul>
          </div>
        </div>

        {/* Paywall Trigger */}
        <div style={{ background: '#0d1117', border: '1px solid #a371f7', borderRadius: '12px', padding: '20px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <div style={{ flex: '1 1 250px' }}>
            <h4 style={{ margin: 0, color: '#f0f6fc', fontSize: '1.1rem' }}>Unlock Full 12-Page Comprehensive PDF Report</h4>
            <p style={{ margin: '4px 0 0 0', color: '#8b949e', fontSize: '0.85rem' }}>Includes step-by-step implementation guide & software architecture blueprint.</p>
          </div>
          <button 
            onClick={() => setIsUnlocked(true)}
            style={{ background: '#a371f7', color: '#fff', border: 'none', borderRadius: '8px', padding: '12px 24px', fontWeight: 'bold', fontSize: '1rem', cursor: 'pointer', flex: '0 0 auto' }}
          >
            {isUnlocked ? '✓ PDF Unlocked' : 'Unlock Report ($19 via PayPal)'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderResaleLedger = () => (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: '0 0 6px 0', color: '#f0f6fc', fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <CreditCardIcon color="#d29922" size={24} /> Credit & Revenue Ledger
          </h2>
          <p style={{ margin: 0, color: '#8b949e', fontSize: '0.9rem' }}>
            Account holder: <strong style={{ color: '#58a6ff' }}>{userEmail}</strong>
          </p>
        </div>
        <div style={{ background: '#0d1117', border: '1px solid #d29922', borderRadius: '12px', padding: '12px 24px', textAlign: 'right' }}>
          <span style={{ color: '#8b949e', fontSize: '0.75rem', textTransform: 'uppercase' }}>Available Balance</span>
          <div style={{ color: '#d29922', fontSize: '1.8rem', fontWeight: '800' }}>{credits} CRD</div>
        </div>
      </div>

      {/* Credit Purchase Packs */}
      <h3 style={{ margin: '0', color: '#f0f6fc' }}>Refill Credit Packages</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', textCenter: 'center', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.2rem' }}>Starter Pack</h4>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#58a6ff', margin: '12px 0' }}>100 Credits</div>
          <p style={{ color: '#8b949e', fontSize: '0.85rem', marginBottom: '20px' }}>$5.00 One-time ($0.05 / generation)</p>
          <button style={{ width: '100%', background: '#238636', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontWeight: 'bold', cursor: 'pointer' }}>
            Buy 100 Credits ($5)
          </button>
        </div>

        <div style={{ background: '#161b22', border: '2px solid #58a6ff', borderRadius: '16px', padding: '24px', textCenter: 'center', textAlign: 'center', position: 'relative' }}>
          <span style={{ position: 'absolute', top: '-12px', left: '50%', transform: 'translateX(-50%)', background: '#58a6ff', color: '#0d1117', padding: '2px 12px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 'bold' }}>MOST POPULAR</span>
          <h4 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.2rem' }}>Pro Pack</h4>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#58a6ff', margin: '12px 0' }}>500 Credits</div>
          <p style={{ color: '#8b949e', fontSize: '0.85rem', marginBottom: '20px' }}>$19.00 One-time ($0.038 / generation)</p>
          <button style={{ width: '100%', background: '#58a6ff', color: '#0d1117', border: 'none', borderRadius: '8px', padding: '10px', fontWeight: 'bold', cursor: 'pointer' }}>
            Buy 500 Credits ($19)
          </button>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '16px', padding: '24px', textCenter: 'center', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#f0f6fc', fontSize: '1.2rem' }}>Agency Pack</h4>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#a371f7', margin: '12px 0' }}>2,000 Credits</div>
          <p style={{ color: '#8b949e', fontSize: '0.85rem', marginBottom: '20px' }}>$49.00 One-time ($0.024 / generation)</p>
          <button style={{ width: '100%', background: '#a371f7', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontWeight: 'bold', cursor: 'pointer' }}>
            Buy 2,000 Credits ($49)
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ width: '100%', height: '100%', background: '#0d1117', color: '#c9d1d9', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif', padding: '20px', boxSizing: 'border-box', overflow: 'hidden' }}>
      {(activeApp === 'hub' || activeApp === 'storefront_hub') && renderHub()}
      {(activeApp === 'ai-content' || activeApp === 'ai_content_engine') && renderAiContentEngine()}
      {(activeApp === 'lead-tracker' || activeApp === 'lead_tracker') && renderLeadTracker()}
      {(activeApp === 'roi-diagnostic' || activeApp === 'roi_diagnostic') && renderRoiDiagnostic()}
      {(activeApp === 'resale-ledger' || activeApp === 'resale_ledger') && renderResaleLedger()}
    </div>
  );
};

export default DigitalStorefrontTab;
```

*End of DigitalStorefrontTab.jsx*

---

## MasterAccountingTab.jsx
```jsx
import React, { useState, useEffect } from "react";

// Resilient Inline SVG Icon Helpers with explicit width & height
const DollarSignIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#34d399', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V6m0 12v-2m0 0c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const FileSpreadsheetIcon = () => (
  <svg style={{ width: '16px', height: '16px', color: '#38bdf8', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const CalculatorIcon = () => (
  <svg style={{ width: '16px', height: '16px', color: '#c084fc', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
  </svg>
);

const SparklesIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#fbbf24', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

const LockIcon = () => (
  <svg style={{ width: '48px', height: '48px', color: '#f87171', marginBottom: '12px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
  </svg>
);

const ShieldCheckIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#34d399', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
  </svg>
);

const TrashIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#f87171' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

const SendIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#ffffff' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>
);

const RefreshIcon = ({ spinning }) => (
  <svg style={{ width: '14px', height: '14px', color: '#9ca3af' }} className={spinning ? "animate-spin" : ""} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

export default function MasterAccountingTab({ backendUrl }) {
  const authorizedEmails = [
    "footballstar0325@gmail.com",
    "brettstehouwer@gmail.com",
    "theseandaley@gmail.com",
    "stehouwerjulie@gmail.com"
  ];
  
  const [currentUserEmail] = useState("brettstehouwer@gmail.com");
  const isAuthorized = authorizedEmails.includes(currentUserEmail.toLowerCase());

  const [activeSubPage, setActiveSubPage] = useState("spreadsheet");
  const [isChatOpen, setIsChatOpen] = useState(false);
  
  const [entries, setEntries] = useState([]);
  const [taxSummary, setTaxSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editingRowId, setEditingRowId] = useState(null);
  const [editingRowData, setEditingRowData] = useState({});

  const [chatMessages, setChatMessages] = useState([
    { sender: "ai", text: "Welcome to Stehouwer Financial AI! Ask tax questions or command: 'Log an expense of $1,599.99 for RTX 4090 GPU'." }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [sendingChat, setSendingChat] = useState(false);

  const [newEntry, setNewEntry] = useState({
    date: new Date().toISOString().split("T")[0],
    category: "Hardware & Electronics",
    description: "",
    entry_type: "expense",
    amount: "",
    is_tax_deductible: true,
    schedule_c_code: "Sec179_Hardware",
    receipt_note: ""
  });

  const fetchAccountingData = async () => {
    try {
      setLoading(true);
      const [entriesRes, taxRes] = await Promise.all([
        fetch(`${backendUrl}/api/accounting/entries`),
        fetch(`${backendUrl}/api/accounting/tax-summary`)
      ]);
      
      if (entriesRes.ok) {
        const data = await entriesRes.json();
        setEntries(data.entries || []);
      }
      if (taxRes.ok) {
        const taxData = await taxRes.json();
        setTaxSummary(taxData);
      }
    } catch (err) {
      console.error("Error fetching accounting data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccountingData();
  }, []);

  const handleAddEntry = async (e) => {
    e.preventDefault();
    if (!newEntry.description || !newEntry.amount) return;

    try {
      const payload = {
        ...newEntry,
        amount: parseFloat(newEntry.amount)
      };

      const res = await fetch(`${backendUrl}/api/accounting/entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setNewEntry({
          date: new Date().toISOString().split("T")[0],
          category: "Hardware & Electronics",
          description: "",
          entry_type: "expense",
          amount: "",
          is_tax_deductible: true,
          schedule_c_code: "Sec179_Hardware",
          receipt_note: ""
        });
        fetchAccountingData();
      }
    } catch (err) {
      console.error("Failed to save entry:", err);
    }
  };

  const handleDeleteEntry = async (id) => {
    if (!window.confirm("Delete this row from the ledger?")) return;
    try {
      const res = await fetch(`${backendUrl}/api/accounting/entry/${id}`, { method: "DELETE" });
      if (res.ok) {
        fetchAccountingData();
      }
    } catch (err) {
      console.error("Failed to delete entry:", err);
    }
  };

  const handleStartEdit = (row) => {
    setEditingRowId(row.id);
    setEditingRowData({ ...row });
  };

  const handleSaveEdit = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/accounting/entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editingRowData)
      });
      if (res.ok) {
        setEditingRowId(null);
        fetchAccountingData();
      }
    } catch (err) {
      console.error("Failed to update entry:", err);
    }
  };

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || sendingChat) return;

    const userText = chatInput;
    setChatInput("");
    setChatMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setSendingChat(true);

    try {
      const res = await fetch(`${backendUrl}/api/accounting/chat-assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText })
      });

      if (res.ok) {
        const data = await res.json();
        setChatMessages((prev) => [...prev, { sender: "ai", text: data.reply }]);
        fetchAccountingData();
      }
    } catch (err) {
      setChatMessages((prev) => [...prev, { sender: "ai", text: "Service temporarily unavailable." }]);
    } finally {
      setSendingChat(false);
    }
  };

  if (!isAuthorized) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px', background: '#0f172a', color: '#ffffff', borderRadius: '16px', padding: '32px', border: '1px solid #7f1d1d' }}>
        <LockIcon />
        <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#f87171' }}>Master Accounting Access Restricted</h2>
        <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '8px' }}>
          Locked to authorized partners of Stehouwer Publishing LLC / NoCo.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#020617', color: '#f8fafc', padding: '16px', gap: '16px', overflowY: 'auto', boxSizing: 'border-box' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', background: '#0f172a', padding: '12px 16px', borderRadius: '12px', border: '1px solid #1e293b' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem', fontWeight: '800', background: 'linear-gradient(to right, #34d399, #38bdf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Stehouwer Publishing LLC Master Accounting
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: '600', background: 'rgba(52, 211, 153, 0.1)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
              <ShieldCheckIcon /> Authorized
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: '2px 0 0 0' }}>
            Interactive Excel Grid • US Federal & Michigan State (4.25% Flat) Tax Engine
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '8px', fontSize: '0.75rem', fontWeight: '600', background: 'linear-gradient(to right, #9333ea, #4f46e5)', color: '#ffffff', border: 'none', cursor: 'pointer', boxShadow: '0 4px 12px rgba(147, 51, 234, 0.3)' }}
          >
            <SparklesIcon /> {isChatOpen ? "Hide AI Assistant" : "AI Tax Advisor"}
          </button>
          <button
            onClick={fetchAccountingData}
            style={{ padding: '6px 10px', borderRadius: '8px', background: '#1e293b', color: '#cbd5e1', border: '1px solid #334155', cursor: 'pointer' }}
            title="Refresh Data"
          >
            <RefreshIcon spinning={loading} />
          </button>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        <div style={{ background: '#0f172a', padding: '12px', borderRadius: '12px', border: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', justify: 'space-between', color: '#94a3b8', fontSize: '0.68rem', fontWeight: '600', textTransform: 'uppercase' }}>
            <span>GROSS REVENUE</span> <DollarSignIcon />
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#34d399', marginTop: '4px' }}>
            ${taxSummary ? taxSummary.gross_income.toLocaleString('en-US', {minimumFractionDigits: 2}) : "0.00"}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '2px' }}>PayPal & API Payouts</div>
        </div>

        <div style={{ background: '#0f172a', padding: '12px', borderRadius: '12px', border: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', justify: 'space-between', color: '#94a3b8', fontSize: '0.68rem', fontWeight: '600', textTransform: 'uppercase' }}>
            <span>DEDUCTIBLE EXPENSES</span> <FileSpreadsheetIcon />
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#38bdf8', marginTop: '4px' }}>
            ${taxSummary ? taxSummary.tax_deductible_expenses.toLocaleString('en-US', {minimumFractionDigits: 2}) : "0.00"}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '2px' }}>IRS Sec 179 GPU Write-offs</div>
        </div>

        <div style={{ background: '#0f172a', padding: '12px', borderRadius: '12px', border: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', justify: 'space-between', color: '#94a3b8', fontSize: '0.68rem', fontWeight: '600', textTransform: 'uppercase' }}>
            <span>MICHIGAN STATE TAX (4.25%)</span> <CalculatorIcon />
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#c084fc', marginTop: '4px' }}>
            ${taxSummary ? taxSummary.estimated_michigan_state_tax.toLocaleString('en-US', {minimumFractionDigits: 2}) : "0.00"}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '2px' }}>MI Business Flat Rate</div>
        </div>

        <div style={{ background: '#0f172a', padding: '12px', borderRadius: '12px', border: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', justify: 'space-between', color: '#94a3b8', fontSize: '0.68rem', fontWeight: '600', textTransform: 'uppercase' }}>
            <span>TAX SAVINGS</span> <SparklesIcon />
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#fbbf24', marginTop: '4px' }}>
            ${taxSummary ? taxSummary.estimated_tax_savings_from_writeoffs.toLocaleString('en-US', {minimumFractionDigits: 2}) : "0.00"}
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '2px' }}>Deduction Savings</div>
        </div>
      </div>

      {/* Sub-Tab Selector */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
        <button
          onClick={() => setActiveSubPage("spreadsheet")}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '600', background: activeSubPage === "spreadsheet" ? '#0284c7' : '#0f172a', color: '#ffffff', border: '1px solid #1e293b', cursor: 'pointer' }}
        >
          <FileSpreadsheetIcon /> Interactive Excel Ledger Grid
        </button>
        <button
          onClick={() => setActiveSubPage("tax_suite")}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '600', background: activeSubPage === "tax_suite" ? '#7e22ce' : '#0f172a', color: '#ffffff', border: '1px solid #1e293b', cursor: 'pointer' }}
        >
          <CalculatorIcon /> US Federal & Michigan State Tax Engine
        </button>
      </div>

      {/* Main Body */}
      <div style={{ display: 'flex', gap: '16px', flex: 1, position: 'relative' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {activeSubPage === "spreadsheet" && (
            <>
              {/* Operational Guide Note */}
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '8px', border: '1px solid #1e293b', fontSize: '0.72rem', color: '#94a3b8' }}>
                💡 <strong>How to use this Excel Ledger:</strong> Click any cell's <strong>Edit</strong> button to modify row values inline, click <strong>Save Row</strong> to persist changes to SQLite, or click <strong>Quick Add</strong> below to add new hardware/electricity expenses or API income.
              </div>

              {/* Add New Entry Row Form */}
              <form onSubmit={handleAddEntry} style={{ background: '#0f172a', padding: '12px', borderRadius: '10px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#cbd5e1' }}>
                  + Quick Add New Transaction Entry
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
                  <input
                    type="date"
                    value={newEntry.date}
                    onChange={(e) => setNewEntry({...newEntry, date: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                    required
                  />
                  <select
                    value={newEntry.entry_type}
                    onChange={(e) => setNewEntry({...newEntry, entry_type: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                  >
                    <option value="expense">Expense (-)</option>
                    <option value="income">Income (+)</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Description (e.g. RTX 4090 GPU)"
                    value={newEntry.description}
                    onChange={(e) => setNewEntry({...newEntry, description: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                    required
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Amount ($)"
                    value={newEntry.amount}
                    onChange={(e) => setNewEntry({...newEntry, amount: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                    required
                  />
                  <select
                    value={newEntry.category}
                    onChange={(e) => setNewEntry({...newEntry, category: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                  >
                    <option value="Hardware & Electronics">Hardware / GPU</option>
                    <option value="Cloud Infrastructure">Cloud / Servers</option>
                    <option value="Utilities & Electricity">Electricity</option>
                    <option value="Software Subscriptions">Software</option>
                    <option value="Commercial API Payouts">API Income</option>
                    <option value="Other Business">Other Business</option>
                  </select>
                  <button
                    type="submit"
                    style={{ background: '#059669', color: '#ffffff', border: 'none', borderRadius: '6px', padding: '6px 12px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}
                  >
                    Add Row
                  </button>
                </div>
              </form>

              {/* Excel Grid Table */}
              <div style={{ background: '#0f172a', borderRadius: '10px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.75rem', color: '#cbd5e1' }}>
                    <thead>
                      <tr style={{ background: '#020617', borderBottom: '1px solid #1e293b', color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.65rem', fontWeight: 'bold' }}>
                        <th style={{ padding: '8px 12px' }}>Date</th>
                        <th style={{ padding: '8px 12px' }}>Category</th>
                        <th style={{ padding: '8px 12px' }}>Description</th>
                        <th style={{ padding: '8px 12px' }}>Type</th>
                        <th style={{ padding: '8px 12px' }}>Amount ($)</th>
                        <th style={{ padding: '8px 12px' }}>Tax Write-Off</th>
                        <th style={{ padding: '8px 12px' }}>Schedule C Code</th>
                        <th style={{ padding: '8px 12px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entries.length === 0 ? (
                        <tr>
                          <td colSpan="8" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                            No ledger entries found. Use the quick add form above to log transactions.
                          </td>
                        </tr>
                      ) : (
                        entries.map((item) => {
                          const isEditing = editingRowId === item.id;
                          return (
                            <tr key={item.id} style={{ borderBottom: '1px solid rgba(30, 41, 59, 0.6)', background: isEditing ? 'rgba(30, 41, 59, 0.8)' : 'transparent' }}>
                              <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>
                                {isEditing ? (
                                  <input type="date" value={editingRowData.date} onChange={(e) => setEditingRowData({...editingRowData, date: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px' }} />
                                ) : item.date}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                {isEditing ? (
                                  <input type="text" value={editingRowData.category} onChange={(e) => setEditingRowData({...editingRowData, category: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px' }} />
                                ) : item.category}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                {isEditing ? (
                                  <input type="text" value={editingRowData.description} onChange={(e) => setEditingRowData({...editingRowData, description: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px' }} />
                                ) : item.description}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem', fontWeight: 'bold', background: item.entry_type === 'income' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(248, 113, 113, 0.15)', color: item.entry_type === 'income' ? '#34d399' : '#f87171' }}>
                                  {item.entry_type.toUpperCase()}
                                </span>
                              </td>
                              <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontWeight: 'bold', color: item.entry_type === 'income' ? '#34d399' : '#f8fafc' }}>
                                {isEditing ? (
                                  <input type="number" step="0.01" value={editingRowData.amount} onChange={(e) => setEditingRowData({...editingRowData, amount: parseFloat(e.target.value)})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px', width: '80px' }} />
                                ) : `$${parseFloat(item.amount).toFixed(2)}`}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                {item.is_tax_deductible ? (
                                  <span style={{ color: '#34d399', fontWeight: '600' }}>Deductible</span>
                                ) : (
                                  <span style={{ color: '#64748b' }}>Standard</span>
                                )}
                              </td>
                              <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{item.schedule_c_code}</td>
                              <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                                {isEditing ? (
                                  <button onClick={handleSaveEdit} style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>
                                    Save
                                  </button>
                                ) : (
                                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                                    <button onClick={() => handleStartEdit(item)} style={{ background: 'transparent', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.7rem' }}>
                                      Edit
                                    </button>
                                    <button onClick={() => handleDeleteEntry(item.id)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }} title="Delete">
                                      <TrashIcon />
                                    </button>
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {activeSubPage === "tax_suite" && taxSummary && (
            <div style={{ background: '#0f172a', padding: '16px', borderRadius: '10px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '10px' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}>
                  <CalculatorIcon /> US Federal & Michigan State Tax Engine Summary
                </h3>
                <span style={{ padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: 'bold', background: 'rgba(192, 132, 252, 0.15)', color: '#c084fc' }}>
                  MI Business Flat Tax Rate: 4.25%
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
                <div style={{ background: '#020617', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: '#94a3b8', uppercase: 'true', marginBottom: '8px' }}>Business Revenue & Profit</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                    <span style={{ color: '#94a3b8' }}>Gross Income:</span>
                    <span style={{ fontFamily: 'monospace', color: '#34d399', fontWeight: 'bold' }}>${taxSummary.gross_income.toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justify: 'space-between', fontSize: '0.75rem', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                    <span style={{ color: '#94a3b8' }}>Total Write-Offs:</span>
                    <span style={{ fontFamily: 'monospace', color: '#38bdf8', fontWeight: 'bold' }}>-${taxSummary.tax_deductible_expenses.toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justify: 'space-between', fontSize: '0.75rem', padding: '6px 0 0 0', fontWeight: 'bold', color: '#f8fafc' }}>
                    <span>Net Taxable Income:</span>
                    <span style={{ fontFamily: 'monospace', color: '#c084fc' }}>${taxSummary.net_taxable_income.toFixed(2)}</span>
                  </div>
                </div>

                <div style={{ background: '#020617', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: '#94a3b8', uppercase: 'true', marginBottom: '8px' }}>Estimated Tax Breakdown</div>
                  <div style={{ display: 'flex', justify: 'space-between', fontSize: '0.75rem', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                    <span style={{ color: '#94a3b8' }}>Michigan State Tax (4.25%):</span>
                    <span style={{ fontFamily: 'monospace', color: '#c084fc' }}>${taxSummary.estimated_michigan_state_tax.toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justify: 'space-between', fontSize: '0.75rem', padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                    <span style={{ color: '#94a3b8' }}>US Federal SE Tax (15.3%):</span>
                    <span style={{ fontFamily: 'monospace', color: '#818cf8' }}>${taxSummary.estimated_federal_se_tax.toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justify: 'space-between', fontSize: '0.75rem', padding: '6px 0 0 0', fontWeight: 'bold', color: '#f8fafc' }}>
                    <span>Total Tax Liability:</span>
                    <span style={{ fontFamily: 'monospace', color: '#fbbf24' }}>${taxSummary.total_estimated_tax_liability.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Embedded AI Advisor Chat Drawer */}
        {isChatOpen && (
          <div style={{ width: '320px', background: '#0f172a', borderRadius: '10px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', height: '450px' }}>
            <div style={{ padding: '10px', background: '#020617', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <SparklesIcon />
                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#f8fafc' }}>Stehouwer Financial AI</span>
              </div>
              <button onClick={() => setIsChatOpen(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.75rem' }}>✕</button>
            </div>

            <div style={{ flex: 1, padding: '10px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.7rem' }}>
              {chatMessages.map((msg, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                  <div style={{ maxWidth: '85%', padding: '8px', borderRadius: '8px', background: msg.sender === "user" ? '#9333ea' : '#1e293b', color: '#ffffff' }}>
                    {msg.text}
                  </div>
                </div>
              ))}
            </div>

            <form onSubmit={handleSendChat} style={{ padding: '8px', background: '#020617', borderTop: '1px solid #1e293b', display: 'flex', gap: '6px' }}>
              <input
                type="text"
                placeholder="Command: 'Log $150 electricity'"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px', fontSize: '0.7rem' }}
              />
              <button type="submit" disabled={sendingChat} style={{ background: '#9333ea', border: 'none', color: '#fff', borderRadius: '6px', padding: '6px 10px', cursor: 'pointer' }}>
                <SendIcon />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
```

*End of MasterAccountingTab.jsx*

---

## AdvertisingTab.jsx
```jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';

// ─── Canonical lead shape ────────────────────────────────────────────────────
// { id, business_name, contact, url, email, status, value, heuristic_match, date_acquired }
// This matches what BullshitLeadMatrix reads from the backend. Both components
// now share the same store: GET/POST /api/advertising/leads.
// ─────────────────────────────────────────────────────────────────────────────

const LEADS_LS_KEY = 'advertising_leads_v2';   // v2 to avoid conflict with old shape
const BUDGETS_LS_KEY = 'advertising_budgets';
const SAVE_DEBOUNCE_MS = 800;

const AdvertisingTab = ({ backendUrl, selectedModel = 'stehouwer_llm' }) => {
  const [activeSubTab, setActiveSubTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [leadsLoaded, setLeadsLoaded] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');       // 'saving' | 'saved' | 'offline'
  const saveTimerRef = useRef(null);
  const isFirstLeadLoad = useRef(true);

  // AI Campaign Generator
  const [businessName, setBusinessName] = useState('');
  const [campaignGoal, setCampaignGoal] = useState('');
  const [generatedCopy, setGeneratedCopy] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [genError, setGenError] = useState('');

  // Platform Post Generator
  const [postBizName, setPostBizName] = useState('Stehouwer Advertising');
  const [postIndustry, setPostIndustry] = useState('Marketing / Advertising Agency');
  const [postCounty, setPostCounty] = useState('Ottawa County');
  const [postPromo, setPostPromo] = useState('We help West Michigan local businesses dominate Google, Facebook, Instagram, and TikTok with AI-powered ad campaigns. First month FREE for new clients — call us today and get a custom strategy built for your neighborhood.');
  const [generatedPosts, setGeneratedPosts] = useState(null);
  const [isGeneratingPosts, setIsGeneratingPosts] = useState(false);
  const [copiedPlatform, setCopiedPlatform] = useState('');


  // Budget Tracker
  const [budgets, setBudgets] = useState(() => {
    const saved = localStorage.getItem(BUDGETS_LS_KEY);
    return saved ? JSON.parse(saved) : [{ id: 1, event: 'Summer SEO Push', spent: 1500, roi: 4500 }];
  });

  // ── Load leads from backend on mount, fall back to localStorage ─────────────
  const fetchLeads = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/advertising/leads`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status === 'success') {
        const fetched = data.leads;
        setLeads(fetched);
        localStorage.setItem(LEADS_LS_KEY, JSON.stringify(fetched));   // warm the fallback
        setLeadsLoaded(true);
        return;
      }
    } catch (_) {
      // Backend unreachable — use localStorage fallback
    }
    const cached = localStorage.getItem(LEADS_LS_KEY);
    setLeads(cached ? JSON.parse(cached) : []);
    setLeadsLoaded(true);
    setSaveStatus('offline');
  }, [backendUrl]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  // ── Debounced save to backend (skip the very first load-triggered effect) ───
  useEffect(() => {
    if (!leadsLoaded) return;
    if (isFirstLeadLoad.current) { isFirstLeadLoad.current = false; return; }

    clearTimeout(saveTimerRef.current);
    setSaveStatus('saving');
    saveTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/advertising/leads`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(leads),
        });
        if (!res.ok) throw new Error();
        localStorage.setItem(LEADS_LS_KEY, JSON.stringify(leads));
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus(''), 2000);
      } catch (_) {
        localStorage.setItem(LEADS_LS_KEY, JSON.stringify(leads));
        setSaveStatus('offline');
      }
    }, SAVE_DEBOUNCE_MS);

    return () => clearTimeout(saveTimerRef.current);
  }, [leads, leadsLoaded, backendUrl]);

  // Budgets stay localStorage-only (no backend endpoint yet)
  useEffect(() => {
    localStorage.setItem(BUDGETS_LS_KEY, JSON.stringify(budgets));
  }, [budgets]);

  // ── Lead CRUD ────────────────────────────────────────────────────────────────
  const addLead = () => {
    const newLead = {
      id: `manual-${Date.now()}`,
      business_name: 'New Business',
      contact: '',
      url: '',
      email: '',
      status: 'New',
      value: '$0',
      heuristic_match: 'Manual Entry',
      date_acquired: new Date().toISOString(),
    };
    setLeads(prev => [newLead, ...prev]);
  };

  const updateLead = (id, field, value) =>
    setLeads(prev => prev.map(l => l.id === id ? { ...l, [field]: value } : l));

  const deleteLead = (id) =>
    setLeads(prev => prev.filter(l => l.id !== id));

  // ── Campaign generator ───────────────────────────────────────────────────────
  const generateCampaign = async () => {
    if (!businessName.trim()) { setGenError('Enter a business name first.'); return; }
    setIsGenerating(true);
    setGenError('');
    setGeneratedCopy('Generating...');
    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: `Write a high-converting Facebook ad and 5 Google SEO keywords for a business named "${businessName}" whose goal is "${campaignGoal}". Keep it highly professional and punchy.` }],
          use_rag: false,
          use_web_search: false,
          model: 'stehouwer_llm',
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const content = (typeof data.message === 'string' ? data.message : data.message?.content) || data.response || data.choices?.[0]?.message?.content || (typeof data === 'string' ? data : '');
      setGeneratedCopy(content || 'No response received. Check backend logs.');
    } catch (err) {
      setGenError('Backend unreachable. Ensure uvicorn and Ollama are running.');
      setGeneratedCopy('');
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Platform Post Generator ──────────────────────────────────────────────────
  const handleGeneratePlatformPosts = async () => {
    setIsGeneratingPosts(true);
    setGeneratedPosts(null);
    const systemPrompt = `You are an expert platform-native content strategist and local SEO specialist for West Michigan businesses. Your posts must be engineered to be indexed and ranked FAST by each platform's algorithm — not generic, not templated, algorithmically precise.

Business: "${postBizName}" | Industry: "${postIndustry}" | County: "${postCounty}"
Promotion: "${postPromo}"

CRITICAL ALGORITHM RULES PER PLATFORM (follow exactly):

ALL PLATFORMS: You MUST include the specific Promotion/Offer provided above in every single post naturally. Do not ignore the promo.

GOOGLE: Front-load geo-intent keywords (people search "near me" or "[city] [service]"). NAP-consistent phrasing. schema_title must be under 60 chars and include the county name. meta_description must be under 155 chars, include a local intent phrase, and end with a micro-CTA. local_keywords must be long-tail geo-modified phrases someone in ${postCounty} would actually type (not brand names).

FACEBOOK: The entire headline + first sentence of body must be under 90 characters (this is what shows before "See More" — the algo rewards early engagement on visible text). Body is 2-3 sentences, conversational, no jargon. CTA drives a comment or message (comments boost reach 3x). Include 3-5 highly targeted, algorithmically optimized hashtags (mix of local, industry, and niche tags) to maximize organic outreach.

INSTAGRAM: caption_hook must be under 125 characters (this is the preview before "more" tap — the algo scores retention here). Body is 2-4 lines max. hashtags: use EXACTLY 3-5 highly targeted hashtags (2024 Instagram algo penalizes hashtag spam; 3-5 niche tags outperform 20+ generic ones). Mix one local tag, one industry tag, one niche tag.

TIKTOK: hook_text is the FIRST 1-3 SECONDS spoken aloud — TikTok transcribes audio and indexes it for search, so include the primary keyword in the spoken hook. script is a 30-45 second natural spoken script (TikTok rewards watch time and loop completion). caption_keywords: write 3-5 words as a search-optimized caption — TikTok's search engine indexes captions exactly like Google, so use phrases people search for (e.g. "Ottawa County marketing tips").

TWITTER / X: tweet must be under 220 characters. Zero external links (the X algorithm heavily suppresses tweets with external links). Use reply-bait wording to drive 30-min engagement velocity. card_title under 50 chars, card_description under 100 chars.

PINTEREST: pin_title must be keyword front-loaded. pin_description 2-3 sentences, search-intent driven, zero fluff.

YELP: Category-exact language. Business description 100-150 words. Mention the county name 2-3x naturally. Highlight special offer in Check-In Offer format.

Respond ONLY with a single, raw, valid JSON object with NO markdown, NO code block ticks, NO intro text, matching this exact shape:
{
  "_thought_process": "Verify promo inclusion, Facebook <90 chars, Instagram exactly 3-5 tags, Yelp 100+ words...",
  "google": { "schema_title": "...", "meta_description": "...", "local_keywords": ["...", "...", "..."] },
  "facebook": { "headline": "...", "body": "...", "cta": "...", "hashtags": "..." },
  "instagram": { "caption_hook": "...", "body": "...", "hashtags": "..." },
  "tiktok": { "hook_text": "...", "script": "...", "caption_keywords": "..." },
  "twitter": { "tweet": "..." , "card_title": "...", "card_description": "..." },
  "pinterest": { "pin_title": "...", "pin_description": "..." },
  "yelp": { "business_description": "...", "category_tags": ["...", "..."], "special_offer": "..." }
}`;

    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: systemPrompt }],
          use_rag: false,
          use_web_search: false,
          model: selectedModel || 'stehouwer_llm',
          format: 'json'
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const raw = data.message?.content || data.response || data.content || data.choices?.[0]?.message?.content || '{}';
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try { setGeneratedPosts(JSON.parse(jsonMatch[0])); }
        catch { setGeneratedPosts({ error: 'AI returned malformed JSON — try again.' }); }
      } else {
        setGeneratedPosts({ error: 'No JSON in AI response — try again.' });
      }
    } catch (e) {
      setGeneratedPosts({ error: `Backend error: ${e.message}` });
    }
    setIsGeneratingPosts(false);
  };


  const handleCopyPost = (key, text) => {
    navigator.clipboard.writeText(text);
    setCopiedPlatform(key);
    setTimeout(() => setCopiedPlatform(''), 2000);
  };

  const statusColor = saveStatus === 'saved' ? '#10b981'
    : saveStatus === 'offline' ? '#ef4444'
    : saveStatus === 'saving' ? '#f59e0b'
    : 'transparent';

  const statusLabel = saveStatus === 'saved' ? '✓ Saved'
    : saveStatus === 'offline' ? '⚠ Offline (local only)'
    : saveStatus === 'saving' ? '↑ Saving...'
    : '';

  return (
    <div className="advertising-workspace" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div className="adv-header glass-panel" style={{ flexShrink: 0 }}>
        <div className="adv-title-area">
          <h3>📈 Stehouwer Advertising Dashboard</h3>
          <p className="subtitle">
            Manage local business leads, generate ad copy, and track ROI.
            {statusLabel && (
              <span style={{ marginLeft: '16px', color: statusColor, fontSize: '0.8em', fontWeight: 600 }}>
                {statusLabel}
              </span>
            )}
          </p>
        </div>
        <div className="adv-tabs">
          <button className={`adv-tab-btn ${activeSubTab === 'leads' ? 'active' : ''}`} onClick={() => setActiveSubTab('leads')}>🏢 Lead Manager</button>
          <button className={`adv-tab-btn ${activeSubTab === 'campaign' ? 'active' : ''}`} onClick={() => setActiveSubTab('campaign')}>🤖 AI Campaign Generator</button>
          <button className={`adv-tab-btn ${activeSubTab === 'posts' ? 'active' : ''}`} onClick={() => setActiveSubTab('posts')} style={{ background: activeSubTab === 'posts' ? 'linear-gradient(135deg, #7c3aed, #4f46e5)' : '' }}>🌐 Platform Post Generator</button>
          <button className={`adv-tab-btn ${activeSubTab === 'budget' ? 'active' : ''}`} onClick={() => setActiveSubTab('budget')}>💰 Budget Tracker</button>
        </div>
      </div>

      <div className="adv-content-area" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '20px 0 0 0' }}>


        {/* ── LEADS TAB ─────────────────────────────────────────────────────── */}
        {activeSubTab === 'leads' && (
          <div className="adv-panel glass-panel">
            <div className="panel-header">
              <h4>Secure Leads Vault <span style={{ fontSize: '0.75em', fontWeight: 400, color: '#888' }}>(synced with Lead Matrix)</span></h4>
              <button className="action-btn" onClick={addLead}>+ Add Lead</button>
            </div>
            <div className="table-container">
              {!leadsLoaded ? (
                <p className="empty-state">Loading leads from backend...</p>
              ) : (
                <table className="adv-table">
                  <thead>
                    <tr>
                      <th>Business Name</th>
                      <th>Contact</th>
                      <th>Email</th>
                      <th>Website</th>
                      <th>Status</th>
                      <th>Est. Value</th>
                      <th>Heuristic</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map(lead => (
                      <tr key={lead.id}>
                        <td><input type="text" aria-label="Business Name" placeholder="Business Name" value={lead.business_name || ''} onChange={e => updateLead(lead.id, 'business_name', e.target.value)} /></td>
                        <td><input type="text" aria-label="Contact Name" placeholder="Contact Name" value={lead.contact || ''} onChange={e => updateLead(lead.id, 'contact', e.target.value)} /></td>
                        <td><input type="email" aria-label="Contact Email" placeholder="Contact Email" value={lead.email || ''} onChange={e => updateLead(lead.id, 'email', e.target.value)} /></td>
                        <td><input type="text" aria-label="Website Domain Vector" placeholder="Website URL" value={lead.url || ''} onChange={e => updateLead(lead.id, 'url', e.target.value)} /></td>
                        <td>
                          <select aria-label="CRM Lead Status" value={lead.status || 'New'} onChange={e => updateLead(lead.id, 'status', e.target.value)}>
                            <option value="New">New</option>
                            <option value="Contacted">Contacted</option>
                            <option value="In Negotiations">In Negotiations</option>
                            <option value="Closed (Won)">Closed (Won)</option>
                            <option value="Closed (Lost)">Closed (Lost)</option>
                          </select>
                        </td>
                        <td><input type="text" aria-label="Estimated Value" placeholder="$0" value={lead.value || '$0'} onChange={e => updateLead(lead.id, 'value', e.target.value)} /></td>
                        <td><input type="text" aria-label="Heuristic Match Profile" placeholder="Heuristic" value={lead.heuristic_match || ''} onChange={e => updateLead(lead.id, 'heuristic_match', e.target.value)} /></td>
                        <td><button className="del-btn" aria-label={`Delete Lead ${lead.business_name || lead.id}`} onClick={() => deleteLead(lead.id)}>🗑️</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {leadsLoaded && leads.length === 0 && (
                <p className="empty-state">No leads found. Click "+ Add Lead" or trigger a sweep in the Lead Matrix tab.</p>
              )}
            </div>
          </div>
        )}

        {/* ── CAMPAIGN TAB ──────────────────────────────────────────────────── */}
        {activeSubTab === 'campaign' && (
          <div className="adv-grid-2">
            <div className="adv-panel glass-panel">
              <h4>AI Copywriter Setup</h4>
              <p className="field-desc">Powered by Local Llama 3 Engine</p>

              <div className="form-group">
                <label>Business Name</label>
                <input type="text" placeholder="e.g. Grandville Plumbing" value={businessName} onChange={e => setBusinessName(e.target.value)} />
              </div>

              <div className="form-group">
                <label>Campaign Goal / Key Selling Point</label>
                <textarea rows="4" placeholder="e.g. We offer 24/7 emergency pipe repair with 0 callout fees." value={campaignGoal} onChange={e => setCampaignGoal(e.target.value)} />
              </div>

              {genError && <p style={{ color: '#ef4444', fontSize: '0.85em', margin: '8px 0' }}>{genError}</p>}

              <button className="action-btn full-width" onClick={generateCampaign} disabled={isGenerating || !businessName.trim()}>
                {isGenerating ? 'Generating Copy...' : '⚡ Generate Advertising Copy'}
              </button>
            </div>

            <div className="adv-panel glass-panel">
              <h4>Generated Ad Copy &amp; SEO</h4>
              <div className="generated-output-box">
                {generatedCopy ? (
                  <pre>{generatedCopy}</pre>
                ) : (
                  <p className="empty-state">Your generated Facebook Ads and SEO keywords will appear here.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── BUDGET TAB ────────────────────────────────────────────────────── */}
        {activeSubTab === 'budget' && (
          <div className="adv-panel glass-panel">
            <div className="panel-header">
              <h4>Marketing Event Budgets</h4>
              <button className="action-btn" onClick={() => setBudgets(prev => [...prev, { id: Date.now(), event: 'New Event', spent: 0, roi: 0 }])}>
                + Add Event
              </button>
            </div>

            <div className="budget-cards">
              {budgets.map(budget => (
                <div key={budget.id} className="budget-card">
                  <input className="budget-title-input" type="text" value={budget.event}
                    onChange={e => setBudgets(prev => prev.map(b => b.id === budget.id ? { ...b, event: e.target.value } : b))} />

                  <div className="budget-metrics">
                    <div className="metric">
                      <span>Amount Spent</span>
                      <input type="number" value={budget.spent}
                        onChange={e => setBudgets(prev => prev.map(b => b.id === budget.id ? { ...b, spent: parseFloat(e.target.value) || 0 } : b))} />
                    </div>
                    <div className="metric">
                      <span>Estimated ROI</span>
                      <input type="number" value={budget.roi}
                        onChange={e => setBudgets(prev => prev.map(b => b.id === budget.id ? { ...b, roi: parseFloat(e.target.value) || 0 } : b))} />
                    </div>
                  </div>

                  <div className="roi-indicator" style={{ color: budget.roi >= budget.spent ? '#10b981' : '#ef4444' }}>
                    {budget.roi >= budget.spent ? '▲ Profitable' : '▼ Loss'}
                    <span style={{ marginLeft: '10px' }}>${(budget.roi - budget.spent).toFixed(2)}</span>
                  </div>

                  <button className="del-btn-card" onClick={() => setBudgets(prev => prev.filter(b => b.id !== budget.id))}>Remove</button>
                </div>
              ))}
              {budgets.length === 0 && <p className="empty-state">No budgets tracked yet.</p>}
            </div>
          </div>
        )}

        {/* ── PLATFORM POST GENERATOR TAB ──────────────────────────────────── */}
        {activeSubTab === 'posts' && (
          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20, height: '100%', minHeight: 0 }}>
            {/* LEFT: Form */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 20, background: 'rgba(0,0,0,0.35)', borderRadius: 16, border: '1px solid rgba(124,58,237,0.3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #7c3aed, #4f46e5)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🌐</div>
                <div>
                  <h4 style={{ margin: 0, color: '#00f0ff' }}>Platform Post Generator</h4>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: '#94a3b8' }}>One promo → 7 platforms</p>
                </div>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Business Name</label>
                <input type="text" value={postBizName} onChange={e => setPostBizName(e.target.value)} placeholder="e.g. Holland Hardware & Supply" style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Industry</label>
                <select value={postIndustry} onChange={e => setPostIndustry(e.target.value)} style={{ width: '100%', padding: '9px 12px', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none' }}>
                  <option>Local Business</option><option>Restaurant / Food</option><option>Auto Repair</option><option>Real Estate</option><option>Health & Wellness</option><option>Retail / Shop</option><option>Home Services</option><option>Legal / Financial</option><option>Beauty & Salon</option><option>Event Venue</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Target County</label>
                <select value={postCounty} onChange={e => setPostCounty(e.target.value)} style={{ width: '100%', padding: '9px 12px', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none' }}>
                  <option>Ottawa County</option><option>Kent County</option><option>Muskegon County</option><option>Allegan County</option><option>Kalamazoo County</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem', color: '#94a3b8' }}>Promotion / Offer</label>
                <textarea value={postPromo} onChange={e => setPostPromo(e.target.value)} placeholder="e.g. First month FREE for new clients. AI-powered campaigns built for your neighborhood." rows={5} style={{ width: '100%', boxSizing: 'border-box', padding: '9px 12px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: 'white', outline: 'none', resize: 'vertical' }} />
              </div>
              <button onClick={handleGeneratePlatformPosts} disabled={isGeneratingPosts || !postBizName.trim() || !postPromo.trim()} style={{ marginTop: 'auto', padding: '13px', background: isGeneratingPosts ? 'rgba(124,58,237,0.3)' : 'linear-gradient(135deg, #7c3aed, #4f46e5)', border: 'none', borderRadius: 10, color: 'white', fontWeight: 700, cursor: isGeneratingPosts ? 'not-allowed' : 'pointer', fontSize: '1rem' }}>
                {isGeneratingPosts ? '⚙️ Generating...' : '⚡ Generate All 7 Platforms'}
              </button>
            </div>

            {/* RIGHT: 2-column card grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, alignContent: 'start', overflowY: 'auto' }}>
              {[
                {
                  key: 'google',
                  label: 'Google Business Profile',
                  url: 'https://business.google.com/',
                  icon: '🔍',
                  color: '#4285F4',
                  algoTip: 'Geo-intent keywords · NAP-consistent · <60 char title · <155 char meta',
                  content: g => {
                    const title = g.schema_title || g.title || '';
                    const desc = g.meta_description || g.description || '';
                    const kws = (g.local_keywords || g.keywords || []).join(' · ');
                    return [title, desc, kws ? `📍 ${kws}` : ''].filter(Boolean).join('\n\n');
                  }
                },

                {
                  key: 'facebook',
                  label: 'Facebook',
                  url: 'https://business.facebook.com/',
                  icon: '📘',
                  color: '#1877F2',
                  algoTip: '90-char hook visible · 3-5 targeted hashtags · comment-bait CTA for 3x reach',
                  content: f => [f.headline, f.body || f.text, f.cta, f.hashtags].filter(Boolean).join('\n\n')
                },
                {
                  key: 'instagram',
                  label: 'Instagram',
                  url: 'https://business.instagram.com/',
                  icon: '📸',
                  color: '#E1306C',
                  algoTip: '125-char preview · 3-5 niche hashtags (2024 algo) · hook drives retention',
                  content: i => [
                    i.caption_hook || i.hook,
                    i.body || i.caption,
                    i.hashtags
                  ].filter(Boolean).join('\n\n')
                },
                {
                  key: 'tiktok',
                  label: 'TikTok',
                  url: 'https://www.tiktok.com/business/en',
                  icon: '🎵',
                  color: '#69C9D0',
                  algoTip: 'Spoken keywords indexed by audio · search-phrase caption · loop-completion hook',
                  content: t => [
                    t.hook_text || t.hook,
                    t.script,
                    t.caption_keywords || t.caption
                  ].filter(Boolean).join('\n\n')
                },
                {
                  key: 'twitter',
                  label: 'X / Twitter',
                  url: 'https://ads.x.com/',
                  icon: '𝕏',
                  color: '#e7e9ea',
                  algoTip: '<220 chars · no external links · reply-bait for 30-min velocity',
                  content: t => t.tweet || t.text || ''
                },
                {
                  key: 'pinterest',
                  label: 'Pinterest',
                  url: 'https://business.pinterest.com/',
                  icon: '📌',
                  color: '#E60023',
                  algoTip: 'Keyword front-loaded in title · used 2-3x in description · search-intent driven',
                  content: p => [p.pin_title || p.title, p.pin_description || p.description].filter(Boolean).join('\n\n')
                },
                {
                  key: 'yelp',
                  label: 'Yelp',
                  url: 'https://biz.yelp.com/',
                  icon: '⭐',
                  color: '#d32323',
                  algoTip: 'Category-exact language · county mentioned 2-3x · Check-In Offer format',
                  content: y => {
                    const desc = y.business_description || y.description || '';
                    const offer = y.special_offer || y.offer || '';
                    return [desc, offer ? `🎁 ${offer}` : ''].filter(Boolean).join('\n\n');
                  }
                },
              ].map(({ key, label, url, icon, color, algoTip, content }) => {

                const data = generatedPosts?.[key];
                const text = data && !generatedPosts?.error ? content(data) : '';
                return (
                  <div key={key} style={{ padding: 16, background: 'rgba(0,0,0,0.35)', borderRadius: 14, border: `1px solid ${data ? color + '55' : 'rgba(255,255,255,0.06)'}`, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <span style={{ fontWeight: 700, color: data ? color : '#555', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {icon} <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none', transition: 'opacity 0.2s' }} onMouseOver={e => e.currentTarget.style.opacity = '0.8'} onMouseOut={e => e.currentTarget.style.opacity = '1'}>{label}</a>
                        </span>
                        <div style={{ fontSize: '0.68rem', color: '#4a6070', marginTop: 3, lineHeight: 1.4 }}>⚡ {algoTip}</div>
                      </div>
                      {data && !generatedPosts?.error && (
                        <button onClick={() => handleCopyPost(key, text)} style={{ flexShrink: 0, marginLeft: 8, padding: '4px 10px', background: copiedPlatform === key ? '#10b981' : `${color}22`, border: `1px solid ${color}66`, borderRadius: 6, color: copiedPlatform === key ? 'white' : color, cursor: 'pointer', fontSize: '0.73rem', fontWeight: 600 }}>
                          {copiedPlatform === key ? '✅ Copied!' : '📋 Copy'}
                        </button>
                      )}
                    </div>
                    {!generatedPosts && !isGeneratingPosts && <p style={{ margin: 0, fontSize: '0.78rem', color: '#444' }}>Awaiting generation...</p>}
                    {isGeneratingPosts && <p style={{ margin: 0, fontSize: '0.78rem', color: '#7c3aed', animation: 'pulse 1s infinite' }}>Generating...</p>}
                    {generatedPosts?.error && key === 'google' && <p style={{ margin: 0, fontSize: '0.78rem', color: '#ef4444' }}>{generatedPosts.error}</p>}
                    {text && <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.6, flex: 1 }}>{text}</pre>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default AdvertisingTab;

```

*End of AdvertisingTab.jsx*

---

## AutomatedClientSchedulerTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

export default function AutomatedClientSchedulerTab({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;

  // Client Profiles State
  const [clients, setClients] = useState([]);
  const [selectedClientName, setSelectedClientName] = useState('Stehouwer Publishing');
  const [activeClientProfile, setActiveClientProfile] = useState({
    name: 'Stehouwer Publishing',
    industry: 'Book Publishing & Literary Media',
    website: 'https://stehouwer-publishing.com',
    target_audience: 'Authors, Readers & Book Buyers',
    brand_voice: 'Professional, Inspiring, Authoritative',
    preferred_channels: 'Twitter, LinkedIn, Facebook, Email Newsletter',
    contact_email: 'contact@stehouwer-publishing.com'
  });

  // Client Email Ingestion State
  const [emailSubject, setEmailSubject] = useState('Weekly Book Launch & Publishing Push');
  const [emailSender, setEmailSender] = useState('julie@stehouwer-publishing.com');
  const [emailBody, setEmailBody] = useState('Hi Brett, for this week we need 3 posts promoting our new fall book releases and author manuscript submission drive.');
  const [isIngestingEmail, setIsIngestingEmail] = useState(false);

  // Weekly Schedule State
  const [weeklySchedule, setWeeklySchedule] = useState([]);
  const [isGeneratingSchedule, setIsGeneratingSchedule] = useState(false);

  // Stehouwer Publishing Promo Templates
  const [selectedPromoTemplate, setSelectedPromoTemplate] = useState('book_release');

  // Load clients on mount
  const fetchClients = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/scheduler/clients`);
      if (res.ok) {
        const data = await res.json();
        if (data.clients && data.clients.length > 0) {
          setClients(data.clients);
          const found = data.clients.find(c => c.name === selectedClientName);
          if (found) setActiveClientProfile(found);
        }
      }
    } catch (e) {
      console.warn('Failed to fetch clients:', e);
    }
  };

  const fetchWeeklyQueue = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/scheduler/queue?client_name=${encodeURIComponent(selectedClientName)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.posts) setWeeklySchedule(data.posts);
      }
    } catch (e) {
      console.warn('Failed to fetch queue:', e);
    }
  };

  useEffect(() => {
    fetchClients();
    fetchWeeklyQueue();
  }, [selectedClientName]);

  const handleSelectClient = (name) => {
    setSelectedClientName(name);
    const found = clients.find(c => c.name === name);
    if (found) {
      setActiveClientProfile(found);
      setEmailSender(found.contact_email || 'client@example.com');
    }
  };

  const handleSaveClientProfile = async () => {
    try {
      const res = await fetch(`${apiHost}/v1/scheduler/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeClientProfile)
      });
      const data = await res.json();
      if (data.status === 'success') {
        alert(`Client Profile '${activeClientProfile.name}' saved successfully!`);
        fetchClients();
      }
    } catch (e) {
      alert('Error saving client profile: ' + e.message);
    }
  };

  const handleIngestEmailAndGenerate = async () => {
    setIsIngestingEmail(true);
    try {
      // 1. Ingest Email Request
      await fetch(`${apiHost}/v1/scheduler/ingest-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: selectedClientName,
          sender_email: emailSender,
          subject: emailSubject,
          raw_request_text: emailBody
        })
      });

      // 2. Generate Weekly 7-Day Content Schedule
      setIsGeneratingSchedule(true);
      const resSched = await fetch(`${apiHost}/v1/scheduler/generate-weekly-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: selectedClientName,
          custom_instructions: `${emailSubject}: ${emailBody}`
        })
      });

      const dataSched = await resSched.json();
      if (dataSched.schedule) {
        setWeeklySchedule(dataSched.schedule);
        alert(`Weekly schedule generated for ${selectedClientName} (${dataSched.schedule_count} daily posts queued)!`);
      }
    } catch (e) {
      alert('Email Ingestion & Schedule Generation Error: ' + e.message);
    } finally {
      setIsIngestingEmail(false);
      setIsGeneratingSchedule(false);
    }
  };

  const handleTriggerPromoTemplate = async (templateType) => {
    let promoSubject = "";
    let promoBody = "";

    if (templateType === 'book_release') {
      promoSubject = "Stehouwer Publishing - New Fall Book Release Spotlight";
      promoBody = "Promote new fall book releases, author interviews, and distribution network for Stehouwer Publishing.";
    } else if (templateType === 'author_submission') {
      promoSubject = "Stehouwer Publishing - Manuscript Submissions Open";
      promoBody = "Call for author manuscript submissions. Free publishing evaluation and global distribution.";
    } else {
      promoSubject = "AI-BS Sovereign Cloud - RTX 4090 GPU Compute Service";
      promoBody = "Promote 44.1kHz RVQ Neural Audio, SDXL visual generation, and commercial developer API passkeys.";
    }

    setEmailSubject(promoSubject);
    setEmailBody(promoBody);
    handleSelectClient(templateType === 'aibs_gpu' ? 'AI-BS Sovereign Cloud' : 'Stehouwer Publishing');
  };

  return (
    <div style={{ padding: '24px', color: '#e6edf3', height: '100%', overflowY: 'auto', background: '#090d16', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Brand Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '800', margin: 0, color: '#38bdf8' }}>
            📅 Automated Client Content Scheduler & Stehouwer Publishing Suite
          </h1>
          <p style={{ fontSize: '13px', color: '#8b949e', margin: '4px 0 0 0' }}>
            Weekly Social Media Automation, Client Email Request Ingestion & Stehouwer Publishing Advertising Campaigns
          </p>
        </div>

        <button
          onClick={fetchWeeklyQueue}
          style={{ padding: '8px 16px', background: '#1f6feb', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
        >
          ⚡ Refresh Queue
        </button>
      </div>

      {/* SECTION 1: CLIENT SELECTOR & PROFILE EDITOR */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 4px 0', color: '#f0f6fc' }}>👥 Client Profile Selection</h2>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
              Select an existing client to auto-populate brand voice, channels, and audience profile.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <select
              value={selectedClientName}
              onChange={(e) => handleSelectClient(e.target.value)}
              style={{ padding: '8px 16px', background: '#0d1117', border: '1px solid #38bdf8', borderRadius: '6px', color: '#38bdf8', fontWeight: '700', fontSize: '13px' }}
            >
              {clients.length === 0 ? (
                <option value="Stehouwer Publishing">Stehouwer Publishing</option>
              ) : (
                clients.map(c => (
                  <option key={c.id || c.name} value={c.name}>{c.name}</option>
                ))
              )}
            </select>

            <button
              onClick={() => {
                const newName = prompt('Enter New Client Business Name:');
                if (newName) {
                  const newProfile = {
                    name: newName,
                    industry: 'General Commercial',
                    website: 'https://example.com',
                    target_audience: 'Local Customers & Clients',
                    brand_voice: 'Professional, Engaging',
                    preferred_channels: 'Twitter, LinkedIn, Facebook, Instagram',
                    contact_email: `contact@${newName.toLowerCase().replace(/[^a-z]/g, '')}.com`
                  };
                  setActiveClientProfile(newProfile);
                  setSelectedClientName(newName);
                }
              }}
              style={{ padding: '8px 14px', background: '#238636', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '12px', cursor: 'pointer' }}
            >
              ➕ Add New Client
            </button>
          </div>
        </div>

        {/* Client Business Profile Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Business Name:</label>
            <input
              type="text"
              value={activeClientProfile.name}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, name: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Industry:</label>
            <input
              type="text"
              value={activeClientProfile.industry}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, industry: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Website URL:</label>
            <input
              type="text"
              value={activeClientProfile.website}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, website: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#38bdf8', fontSize: '12px' }}
            />
          </div>

          <div>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Brand Voice / Tone:</label>
            <input
              type="text"
              value={activeClientProfile.brand_voice}
              onChange={(e) => setActiveClientProfile({ ...activeClientProfile, brand_voice: e.target.value })}
              style={{ width: '100%', padding: '8px', background: '#161b22', border: '1px solid #30363d', borderRadius: '4px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
            <button
              onClick={handleSaveClientProfile}
              style={{ padding: '6px 16px', background: '#1f6feb', color: '#ffffff', border: 'none', borderRadius: '4px', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
            >
              💾 Save Client Profile Changes
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 2: CLIENT EMAIL INGESTION & STEHOUWER PROMO SUITE */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        
        {/* Email Ingestion Box */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 6px 0', color: '#38bdf8' }}>📩 Ingest Client Email & Request Notes</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 14px 0' }}>
            Paste incoming client email instructions to automatically build and queue their weekly posts.
          </p>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Sender Email:</label>
            <input
              type="text"
              value={emailSender}
              onChange={(e) => setEmailSender(e.target.value)}
              style={{ width: '100%', padding: '8px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Email Subject:</label>
            <input
              type="text"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
              style={{ width: '100%', padding: '8px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '12px' }}
            />
          </div>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '11px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Client Request Text / Notes:</label>
            <textarea
              rows={4}
              value={emailBody}
              onChange={(e) => setEmailBody(e.target.value)}
              style={{ width: '100%', padding: '8px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '12px', fontFamily: 'sans-serif' }}
            />
          </div>

          <button
            onClick={handleIngestEmailAndGenerate}
            disabled={isIngestingEmail || isGeneratingSchedule}
            style={{ width: '100%', padding: '12px', background: 'linear-gradient(90deg, #1f6feb, #38bdf8)', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}
          >
            {isIngestingEmail || isGeneratingSchedule ? '🤖 Synthesizing 7-Day Schedule...' : '⚡ Ingest & Auto-Generate 7-Day Posts'}
          </button>
        </div>

        {/* Stehouwer Publishing Promotional Campaign Suite */}
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', margin: '0 0 6px 0', color: '#a78bfa' }}>📢 Stehouwer Publishing Promotional Suite</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 14px 0' }}>
            1-Click automated campaign generators for book releases, manuscript calls, and AI-BS Cloud.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <button
              onClick={() => handleTriggerPromoTemplate('book_release')}
              style={{ padding: '12px', background: '#0d1117', border: '1px solid #8957e5', borderRadius: '8px', color: '#e6edf3', textAlign: 'left', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#a78bfa' }}>📚 Fall Book Release & Author Spotlight</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Auto-generates weekly spotlights for new book catalog releases.</div>
            </button>

            <button
              onClick={() => handleTriggerPromoTemplate('author_submission')}
              style={{ padding: '12px', background: '#0d1117', border: '1px solid #38bdf8', borderRadius: '8px', color: '#e6edf3', textAlign: 'left', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#38bdf8' }}>✍️ Author Manuscript Submissions Drive</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Call for indie authors looking for formatting and global publishing.</div>
            </button>

            <button
              onClick={() => handleTriggerPromoTemplate('aibs_gpu')}
              style={{ padding: '12px', background: '#0d1117', border: '1px solid #238636', borderRadius: '8px', color: '#e6edf3', textAlign: 'left', cursor: 'pointer' }}
            >
              <div style={{ fontSize: '13px', fontWeight: '700', color: '#4ade80' }}>⚡ AI-BS Sovereign GPU Cloud Promotion</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Promote RTX 4090 neural audio, SDXL, and developer passkey APIs.</div>
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 3: WEEKLY 7-DAY SCHEDULE QUEUE DISPLAY */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '16px', margin: '0 0 4px 0', color: '#f0f6fc' }}>
              📆 Weekly Content Queue for {selectedClientName} ({weeklySchedule.length} Posts)
            </h2>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
              Automated 7-day schedule with platform-specific formatting and optimized posting timestamps.
            </p>
          </div>
        </div>

        {weeklySchedule.length === 0 ? (
          <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '30px', textAlign: 'center', color: '#8b949e', fontSize: '13px' }}>
            No scheduled posts for {selectedClientName}. Click "Ingest & Auto-Generate 7-Day Posts" above to build this week's queue!
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {weeklySchedule.map((post, idx) => (
              <div key={post.id || idx} style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '800', color: '#38bdf8' }}>{post.scheduled_day} ({post.scheduled_time})</span>
                    <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700', background: '#1f6feb', color: '#ffffff' }}>
                      {post.platform}
                    </span>
                  </div>

                  <div style={{ fontSize: '13px', fontWeight: '700', color: '#f0f6fc', marginBottom: '8px' }}>
                    {post.post_topic}
                  </div>

                  <div style={{ fontSize: '12px', color: '#8b949e', background: '#161b22', padding: '10px', borderRadius: '6px', border: '1px solid #21262d', whiteSpace: 'pre-wrap', lineHeight: '1.4', marginBottom: '12px' }}>
                    {post.post_copy}
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #21262d', paddingTop: '10px' }}>
                  <span style={{ fontSize: '11px', color: '#238636', fontWeight: '700' }}>✓ {post.status}</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(post.post_copy);
                      alert('Post copy copied to clipboard!');
                    }}
                    style={{ background: 'none', border: '1px solid #30363d', borderRadius: '4px', color: '#38bdf8', padding: '4px 10px', fontSize: '11px', cursor: 'pointer' }}
                  >
                    📋 Copy Text
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
```

*End of AutomatedClientSchedulerTab.jsx*

---

## BetaAnalyticsTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api';

export default function BetaAnalyticsTab({ backendUrl, currentUser }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;
  const [activeSubView, setActiveSubView] = useState('site_traffic'); // 'site_traffic' | 'api_compute'
  
  // Site Traffic Telemetry State (10-Layer Suite)
  const [trafficData, setTrafficData] = useState({
    total_pageviews: 0,
    unique_visitors: 0,
    avg_dwell_time_sec: 0,
    scroll_completion_rate: 0,
    human_traffic_pct: 100,
    top_pages: [],
    top_referrers: [],
    geo_distribution: [],
    top_gpus: [],
    web_vitals: { lcp_ms: 0, cls_score: 0 },
    form_abandonment_leads: [],
    heatmap_points: [],
    live_events: []
  });

  // API Compute Telemetry State
  const [apiData, setApiData] = useState({
    total_security_events: 0,
    total_banned_ips: 0,
    security_events: [],
    active_ip_bans: [],
    live_stream: []
  });

  const [isLoading, setIsLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchTrafficData = async () => {
    try {
      const res = await fetch(`${apiHost}/api/analytics/traffic-summary?limit=50`);
      if (res.ok) {
        const json = await res.json();
        setTrafficData(json);
      }
    } catch (e) {
      console.warn('Failed to fetch site traffic telemetry:', e);
    }
  };

  const [pubSecurityEvents, setPubSecurityEvents] = useState([]);

  const fetchApiData = async () => {
    try {
      const res = await fetch(`${apiHost}/api/admin/security-telemetry`, {
        headers: { 'x-admin-email': currentUser?.email || 'footballstar0325@gmail.com' }
      });
      if (res.ok) {
        const json = await res.json();
        setApiData(json);
      }
    } catch (e) {
      console.warn('Failed to fetch API security telemetry:', e);
    }

    try {
      const res = await fetch(`${apiHost}/api/analytics/publishing-events`);
      if (res.ok) {
        const json = await res.json();
        setPubSecurityEvents(json.events || []);
      }
    } catch (e) {
      console.warn('Failed to fetch publishing security events:', e);
    }
  };

  const refreshAll = async () => {
    setIsLoading(true);
    await Promise.all([fetchTrafficData(), fetchApiData()]);
    setLastRefreshed(new Date().toLocaleTimeString());
    setIsLoading(false);
  };

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ padding: '24px', color: '#e6edf3', height: '100%', overflowY: 'auto', background: '#090d16', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '22px', fontWeight: '800', color: '#38bdf8' }}>📈 Web Analytics & Telemetry Suite</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#8b949e' }}>
            Real-time dwell times, scroll depths, Geo-IP, hardware specs, Web Vitals, form drop-offs & GPU telemetry
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {lastRefreshed && (
            <span style={{ fontSize: '12px', color: '#8b949e' }}>Updated: {lastRefreshed}</span>
          )}
          <button
            onClick={refreshAll}
            disabled={isLoading}
            style={{
              background: '#238636',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: isLoading ? 'not-allowed' : 'pointer'
            }}
          >
            {isLoading ? '⏳ Refreshing...' : '🔄 Live Sync'}
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveSubView('site_traffic')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'site_traffic' ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: activeSubView === 'site_traffic' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          🌐 Stehouwer-Publishing.com Telemetry ({trafficData.total_pageviews} Hits)
        </button>
        <button
          onClick={() => setActiveSubView('api_compute')}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            background: activeSubView === 'api_compute' ? '#1f6feb' : '#161b22',
            color: '#fff',
            border: activeSubView === 'api_compute' ? '1px solid #38bdf8' : '1px solid #30363d',
            fontWeight: '600',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          ⚡ Commercial API & Security Logs ({apiData.live_stream.length} Calls)
        </button>
      </div>

      {/* VIEW 1: WEBSITE TRAFFIC ANALYTICS */}
      {activeSubView === 'site_traffic' && (
        <div>
          {/* Summary Stat Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Total Pageviews</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#38bdf8', marginTop: '4px' }}>{trafficData.total_pageviews}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Total web visits</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Unique Visitors</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#4ade80', marginTop: '4px' }}>{trafficData.unique_visitors}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Session tokens</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>⏱️ Avg Dwell Time</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#f59e0b', marginTop: '4px' }}>{trafficData.avg_dwell_time_sec}s</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Active reading time</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>📜 Scroll Depth</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#a855f7', marginTop: '4px' }}>{trafficData.scroll_completion_rate}%</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Hit 75%+ scroll milestone</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>⚡ Web Vitals (LCP)</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#10b981', marginTop: '4px' }}>{trafficData.web_vitals?.lcp_ms || 420}ms</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>CLS: {trafficData.web_vitals?.cls_score || 0.01}</div>
            </div>

            <div style={{ background: '#161b22', padding: '16px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '11px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>🤖 Human Ratio</div>
              <div style={{ fontSize: '28px', fontWeight: '800', color: '#ec4899', marginTop: '4px' }}>{trafficData.human_traffic_pct}%</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Verified human sessions</div>
            </div>
          </div>

          {/* Breakdown Grid 1: Pages & Referrers */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>📑 Popular Site Pages</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Total Hits</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.top_pages.length === 0 ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No page hits recorded yet.</td></tr>
                  ) : (
                    trafficData.top_pages.map((p, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#38bdf8', fontFamily: 'monospace' }}>{p.path}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#4ade80' }}>{p.hits}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>🔗 Traffic Referral Sources</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Referrer</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Visitors</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.top_referrers.length === 0 ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No referral source data recorded yet.</td></tr>
                  ) : (
                    trafficData.top_referrers.map((r, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#c9d1d9' }}>{r.referrer}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#38bdf8' }}>{r.hits}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Breakdown Grid 2: Geo-IP & Hardware Specs */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>🌍 Geo-IP Location Distribution</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Country</th>
                    <th style={{ padding: '8px' }}>City / Region</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Visits</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.geo_distribution.length === 0 ? (
                    <tr><td colSpan={3} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No Geo-IP locations recorded yet.</td></tr>
                  ) : (
                    trafficData.geo_distribution.map((g, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '600' }}>🇺🇸 {g.country}</td>
                        <td style={{ padding: '8px', color: '#c9d1d9' }}>{g.city}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#4ade80' }}>{g.hits}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>💻 Hardware & WebGL GPU Telemetry</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>GPU Renderer Model</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Devices</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.top_gpus.length === 0 ? (
                    <tr><td colSpan={2} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No GPU renderer telemetry recorded yet.</td></tr>
                  ) : (
                    trafficData.top_gpus.map((gpu, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#a855f7', fontFamily: 'monospace', fontSize: '11px' }}>{gpu.gpu}</td>
                        <td style={{ padding: '8px', textAlign: 'right', fontWeight: '700', color: '#38bdf8' }}>{gpu.count}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Form Field Abandonment Lead Card */}
          {trafficData.form_abandonment_leads.length > 0 && (
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(245, 158, 11, 0.4)', marginBottom: '24px' }}>
              <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f59e0b' }}>🎯 Form Field Abandonment Leads</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Session ID</th>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px' }}>Target Field</th>
                    <th style={{ padding: '8px' }}>Partial Input Lead</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.form_abandonment_leads.map((lead, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{lead.formatted_time}</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace', color: '#38bdf8', fontSize: '11px' }}>{lead.session_id}</td>
                      <td style={{ padding: '8px', color: '#4ade80' }}>{lead.page_path}</td>
                      <td style={{ padding: '8px', color: '#a855f7', fontFamily: 'monospace' }}>{lead.field_name}</td>
                      <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '700', fontFamily: 'monospace' }}>{lead.partial_email}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Live Visitor Event Stream Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f0f6fc' }}>🔴 Live 10-Layer Visitor Event Telemetry Stream</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Session ID</th>
                    <th style={{ padding: '8px' }}>Location</th>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px' }}>Event</th>
                    <th style={{ padding: '8px' }}>Dwell</th>
                    <th style={{ padding: '8px' }}>Scroll</th>
                    <th style={{ padding: '8px' }}>GPU Renderer</th>
                  </tr>
                </thead>
                <tbody>
                  {trafficData.live_events.length === 0 ? (
                    <tr><td colSpan={8} style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>No live website traffic recorded yet.</td></tr>
                  ) : (
                    trafficData.live_events.map(ev => (
                      <tr key={ev.id} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{ev.formatted_time}</td>
                        <td style={{ padding: '8px', fontFamily: 'monospace', color: '#38bdf8', fontSize: '11px' }}>{ev.session_id}</td>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '600' }}>🇺🇸 {ev.city}</td>
                        <td style={{ padding: '8px', color: '#4ade80', fontWeight: '600' }}>{ev.page_path}</td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: '700', background: ev.event_type === 'click' ? '#d97706' : ev.event_type === 'form_field_input' ? '#8957e5' : '#238636', color: '#ffffff' }}>
                            {ev.event_type.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#f59e0b', fontWeight: '700' }}>{ev.dwell_time_sec || 0}s</td>
                        <td style={{ padding: '8px', color: '#a855f7', fontWeight: '700' }}>{ev.scroll_depth_pct || 0}%</td>
                        <td style={{ padding: '8px', color: '#8b949e', fontSize: '11px', fontFamily: 'monospace' }}>{ev.gpu_renderer || 'WebGL'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 2: AI-BS API COMPUTE & SECURITY TELEMETRY */}
      {activeSubView === 'api_compute' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Logged API Calls</div>
              <div style={{ fontSize: '32px', fontWeight: '800', color: '#38bdf8', marginTop: '6px' }}>{apiData.live_stream ? apiData.live_stream.length : 0}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>Commercial gateway requests</div>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Security Shields Triggered</div>
              <div style={{ fontSize: '32px', fontWeight: '800', color: '#f87171', marginTop: '6px' }}>{apiData.total_security_events || 0}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>Automated firewall blocks</div>
            </div>

            <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid #30363d' }}>
              <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: '700' }}>Active Banned IPs</div>
              <div style={{ fontSize: '32px', fontWeight: '800', color: '#fbbf24', marginTop: '6px' }}>{apiData.total_banned_ips || 0}</div>
              <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>Blocked hostile hosts</div>
            </div>
          </div>

          {/* Security Events Audit Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(248, 113, 113, 0.4)', marginBottom: '24px' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#f87171' }}>🛡️ Security Shield Firewall Audit Log</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Event ID</th>
                    <th style={{ padding: '8px' }}>IP Address</th>
                    <th style={{ padding: '8px' }}>Event Type</th>
                    <th style={{ padding: '8px' }}>Severity</th>
                    <th style={{ padding: '8px' }}>Attack Vector / Trigger Details</th>
                  </tr>
                </thead>
                <tbody>
                  {(!apiData.security_events || apiData.security_events.length === 0) ? (
                    <tr><td colSpan={5} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No security firewall blocks recorded.</td></tr>
                  ) : (
                    apiData.security_events.map(ev => (
                      <tr key={ev.id} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>#{ev.id}</td>
                        <td style={{ padding: '8px', color: '#38bdf8', fontWeight: 'bold', fontFamily: 'monospace' }}>{ev.ip_address}</td>
                        <td style={{ padding: '8px', color: '#f87171', fontWeight: 'bold' }}>{ev.event_type}</td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: '700', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.4)' }}>
                            {ev.severity}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#e2e8f0', fontFamily: 'monospace' }}>{ev.details}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Active Banned Hostile IPs Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(251, 191, 36, 0.4)', marginBottom: '24px' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#fbbf24' }}>🚫 Active Banned Hostile IP Blacklist</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Banned IP</th>
                    <th style={{ padding: '8px' }}>Ban Timestamp</th>
                    <th style={{ padding: '8px' }}>Ban Enforcement Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {(!apiData.active_ip_bans || apiData.active_ip_bans.length === 0) ? (
                    <tr><td colSpan={3} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No banned IP addresses.</td></tr>
                  ) : (
                    apiData.active_ip_bans.map((b, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#ef4444', fontWeight: 'bold', fontFamily: 'monospace' }}>{b.ip_address}</td>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{b.banned_at ? new Date(b.banned_at * 1000).toLocaleString() : 'Active'}</td>
                        <td style={{ padding: '8px', color: '#fbbf24', fontWeight: '500' }}>{b.reason}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Stehouwer-Publishing.com Live Web Security Shield Telemetry Table */}
          <div style={{ background: '#161b22', padding: '20px', borderRadius: '10px', border: '1px solid rgba(56, 189, 248, 0.4)' }}>
            <h3 style={{ margin: '0 0 14px 0', fontSize: '15px', color: '#38bdf8' }}>🌐 Stehouwer-Publishing.com Live Security Telemetry</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                    <th style={{ padding: '8px' }}>Time</th>
                    <th style={{ padding: '8px' }}>Origin IP</th>
                    <th style={{ padding: '8px' }}>Page Path</th>
                    <th style={{ padding: '8px' }}>Event Type</th>
                    <th style={{ padding: '8px' }}>Severity</th>
                    <th style={{ padding: '8px' }}>Details / Attack Vector</th>
                  </tr>
                </thead>
                <tbody>
                  {pubSecurityEvents.length === 0 ? (
                    <tr><td colSpan={6} style={{ padding: '16px', color: '#8b949e', textAlign: 'center' }}>No publishing web security events logged yet (Shield active).</td></tr>
                  ) : (
                    pubSecurityEvents.map((pev, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '8px', color: '#8b949e', fontFamily: 'monospace' }}>{pev.timestamp ? new Date(pev.timestamp).toLocaleTimeString() : 'Live'}</td>
                        <td style={{ padding: '8px', color: '#38bdf8', fontFamily: 'monospace', fontWeight: 'bold' }}>{pev.ip_address}</td>
                        <td style={{ padding: '8px', color: '#4ade80' }}>{pev.page_path}</td>
                        <td style={{ padding: '8px', color: pev.severity === 'HIGH' || pev.severity === 'CRITICAL' ? '#ef4444' : '#f59e0b', fontWeight: 'bold' }}>{pev.event_type}</td>
                        <td style={{ padding: '8px' }}>
                          <span style={{ padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: '700', background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8' }}>
                            {pev.severity}
                          </span>
                        </td>
                        <td style={{ padding: '8px', color: '#e2e8f0', fontFamily: 'monospace' }}>{pev.details}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
```

*End of BetaAnalyticsTab.jsx*

---

## PublicPlaygroundTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import { getApiBase } from '../config/api.js';

export default function PublicPlaygroundTab({ backendUrl }) {
  const apiHost = backendUrl || getApiBase() || `${backendUrl}`;
  const [passKey, setPassKey] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('aibs_active_pass_key') || '';
      // Sanitize stored key if it contains private key string
      if (stored.includes('a2f7c2b0') || stored.length > 50) {
        localStorage.removeItem('aibs_active_pass_key');
        return '';
      }
      return stored;
    }
    return '';
  });


  const [activeSubTab, setActiveSubTab] = useState('image'); // 'image', 'video', 'chat'

  // Image Gen State
  const [imagePrompt, setImagePrompt] = useState('A futuristic glowing crystal synthwave city in Michigan');
  const [imageSize, setImageSize] = useState('1024x1024');
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [generatedImage, setGeneratedImage] = useState(null);

  // Video Gen State
  const [videoPrompt, setVideoPrompt] = useState('Cinematic drone flight through neon clouds, 4k');
  const [videoDuration, setVideoDuration] = useState(300); // 4s to 300s (5 Minutes)
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [generatedVideo, setGeneratedVideo] = useState(null);

  // Audio Gen State
  const [audioPrompt, setAudioPrompt] = useState('Relaxing retro synthwave background track with soft chill pads');
  const [audioLyrics, setAudioLyrics] = useState('');
  const [audioGenre, setAudioGenre] = useState('synthwave');
  const [audioDuration, setAudioDuration] = useState(0); // 0 = Dynamic Auto-Timing
  const [audioTempo, setAudioTempo] = useState(110); // 70 to 160 BPM
  const [audioVocalStyle, setAudioVocalStyle] = useState('lead'); // 'lead', 'harmonies', 'whispered', 'vocoder', 'instrumental'
  const [audioArrangement, setAudioArrangement] = useState('verse_chorus'); // 'verse_chorus', 'build_drop', 'continuous_loop'
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [generatedAudio, setGeneratedAudio] = useState(null);


  // Chat State
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI-BS Studio Assistant. How can I help you generate audio, video, images, or code today?' }
  ]);
  const [isChatting, setIsChatting] = useState(false);

  // Developer Portal State
  const [devClientName, setDevClientName] = useState('My Creative App');
  const [devTier, setDevTier] = useState('starter');
  const [newGeneratedPasskey, setNewGeneratedPasskey] = useState(null);
  const [passkeyUsageInfo, setPasskeyUsageInfo] = useState(null);
  const [isGeneratingPasskey, setIsGeneratingPasskey] = useState(false);

  // Speculative VRAM Pre-loader trigger
  useEffect(() => {
    fetch(`${apiHost}/v1/media/warmup`, { method: 'POST' }).catch(() => {});
  }, [apiHost]);

  const handleRequestPasskey = async () => {
    if (!devClientName.trim()) return alert('Please enter a Client or Company Name!');
    setIsGeneratingPasskey(true);
    try {
      const res = await fetch(`${apiHost}/v1/auth/request-passkey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: devClientName, tier: devTier })
      });
      const data = await res.json();
      if (data.passkey) {
        setNewGeneratedPasskey(data);
        setPassKey(data.passkey);
        if (typeof window !== 'undefined') localStorage.setItem('aibs_active_pass_key', data.passkey);
      } else {
        alert('Error generating passkey: ' + (data.message || JSON.stringify(data)));
      }
    } catch (e) {
      alert('Passkey Request Failed: ' + e.message);
    } finally {
      setIsGeneratingPasskey(false);
    }
  };

  const handleCheckPasskeyUsage = async () => {
    if (!passKey.trim()) return alert('Please enter a Pass Key to check usage!');
    try {
      const res = await fetch(`${apiHost}/v1/user/usage`, {
        headers: { 'Authorization': `Bearer ${passKey}` }
      });
      const data = await res.json();
      setPasskeyUsageInfo(data);
    } catch (e) {
      alert('Usage check error: ' + e.message);
    }
  };


  // Saved Media Vault State
  const [mediaVault, setMediaVault] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('aibs_created_media_vault');
        return stored ? JSON.parse(stored) : [];
      } catch (e) {
        return [];
      }
    }
    return [];
  });
  const [vaultFilter, setVaultFilter] = useState('all'); // 'all', 'image', 'video', 'audio'

  const saveToMediaVault = (type, prompt, url, metadata = {}) => {
    const newItem = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString() + ' ' + new Date().toLocaleDateString(),
      type,
      prompt,
      url,
      metadata
    };
    const updated = [newItem, ...mediaVault];
    setMediaVault(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aibs_created_media_vault', JSON.stringify(updated));
    }
  };

  const deleteFromVault = (id) => {
    const updated = mediaVault.filter(item => item.id !== id);
    setMediaVault(updated);
    if (typeof window !== 'undefined') {
      localStorage.setItem('aibs_created_media_vault', JSON.stringify(updated));
    }
  };

  const clearVault = () => {
    if (confirm('Are you sure you want to clear your Created Media Vault?')) {
      setMediaVault([]);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('aibs_created_media_vault');
      }
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('aibs_active_pass_key');
      if (stored) setPassKey(stored);
    }
  }, []);

  const handleGenerateImage = async () => {
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');
    setIsGeneratingImage(true);
    setGeneratedImage(null);

    try {
      const res = await fetch(`${apiHost}/v1/images/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({ prompt: imagePrompt, size: imageSize })
      });

      const data = await res.json();
      let rawUrl = null;

      if (data.data && Array.isArray(data.data) && data.data.length > 0) {
        const item = data.data[0];
        if (typeof item === 'string') {
          rawUrl = item;
        } else if (item.url) {
          rawUrl = item.url;
        } else if (item.b64_json) {
          rawUrl = `data:image/png;base64,${item.b64_json}`;
        }
      } else if (data.url) {
        rawUrl = data.url;
      } else if (data.image_url) {
        rawUrl = data.image_url;
      } else if (data.image) {
        rawUrl = data.image;
      } else if (data.output) {
        rawUrl = typeof data.output === 'string' ? data.output : (Array.isArray(data.output) ? data.output[0] : null);
      }

      if (rawUrl) {
        const fullUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('data:')) ? rawUrl : `${apiHost}${rawUrl}`;
        setGeneratedImage(fullUrl);
        saveToMediaVault('image', imagePrompt, fullUrl, { size: imageSize });
      } else if (data.error) {
        alert('Generation Error: ' + (data.error.message || JSON.stringify(data.error)));
      } else {
        alert('Image generation completed, but no media URL could be extracted from server response: ' + JSON.stringify(data));
      }
    } catch (e) {
      alert('Network Error: ' + e.message);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const handleSendChat = async () => {
    if (!chatInput.trim() || isChatting) return;
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');

    const userMsg = { role: 'user', content: chatInput };
    const updatedMessages = [...chatMessages, userMsg];
    setChatMessages(updatedMessages);
    setChatInput('');
    setIsChatting(true);

    try {
      const res = await fetch(`${apiHost}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({
          model: 'stehouwer_llm',
          messages: updatedMessages
        })
      });

      const data = await res.json();
      if (data.choices && data.choices[0] && data.choices[0].message) {
        setChatMessages(prev => [...prev, data.choices[0].message]);
      } else if (data.error) {
        alert('Chat Error: ' + data.error.message);
      }
    } catch (e) {
      alert('Chat fault: ' + e.message);
    } finally {
      setIsChatting(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');
    setIsGeneratingVideo(true);
    setGeneratedVideo(null);

    try {
      const res = await fetch(`${apiHost}/v1/videos/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({ prompt: videoPrompt, duration_sec: videoDuration, fps: 24 })
      });

      const data = await res.json();
      let rawUrl = null;

      if (data.data && Array.isArray(data.data) && data.data.length > 0) {
        const item = data.data[0];
        if (typeof item === 'string') rawUrl = item;
        else if (item.url) rawUrl = item.url;
      } else if (data.url) rawUrl = data.url;
      else if (data.video) rawUrl = data.video;
      else if (data.output) rawUrl = typeof data.output === 'string' ? data.output : (Array.isArray(data.output) ? data.output[0] : null);

      if (rawUrl) {
        const fullUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('data:')) ? rawUrl : `${apiHost}${rawUrl}`;
        setGeneratedVideo(fullUrl);
        saveToMediaVault('video', videoPrompt, fullUrl, { duration_sec: videoDuration, fps: 24 });
      } else if (data.error) {
        alert('Video Generation Error: ' + (data.error.message || JSON.stringify(data.error)));
      } else {
        alert('Video generation completed!');
      }
    } catch (e) {
      alert('Network Error: ' + e.message);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  const handleGenerateAudio = async () => {
    if (!passKey) return alert('Please enter or purchase an active Pass Key first!');
    setIsGeneratingAudio(true);
    setGeneratedAudio(null);

    try {
      const res = await fetch(`${apiHost}/v1/audio/generations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${passKey}`
        },
        body: JSON.stringify({
          prompt: audioPrompt,
          genre: audioGenre,
          duration_sec: audioDuration,
          lyrics: audioLyrics,
          tempo_bpm: audioTempo,
          vocal_style: audioVocalStyle,
          arrangement: audioArrangement
        })
      });

      const data = await res.json();
      let rawUrl = null;

      if (data.data && Array.isArray(data.data) && data.data.length > 0) {
        const item = data.data[0];
        if (typeof item === 'string') rawUrl = item;
        else if (item.url) rawUrl = item.url;
      } else if (data.url) rawUrl = data.url;
      else if (data.audio) rawUrl = data.audio;
      else if (data.output) rawUrl = typeof data.output === 'string' ? data.output : (Array.isArray(data.output) ? data.output[0] : null);

      if (rawUrl) {
        const fullUrl = (rawUrl.startsWith('http') || rawUrl.startsWith('data:')) 
          ? rawUrl 
          : `${apiHost}${rawUrl}`;
        const actualDur = (data.data && data.data[0] && data.data[0].duration_sec) ? data.data[0].duration_sec : audioDuration;
        setGeneratedAudio(fullUrl);
        saveToMediaVault('audio', audioPrompt, fullUrl, { genre: audioGenre, duration_sec: actualDur, tempo_bpm: audioTempo, vocal_style: audioVocalStyle });

      } else if (data.error) {
        alert('Audio Generation Error: ' + (data.error.message || JSON.stringify(data.error)));
      } else {
        alert('Audio synthesis completed!');
      }
    } catch (e) {
      alert('Network Error: ' + e.message);
    } finally {
      setIsGeneratingAudio(false);
    }
  };

  return (

    <main id="main-content" style={{ padding: '24px', background: '#090d16', color: '#e6edf3', minHeight: '100vh', fontFamily: 'Inter, system-ui, sans-serif' }}>
      
      {/* Brand Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #30363d', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: '800', margin: 0, color: '#38bdf8' }}>🎨 Stehouwer AI Studio & Playground</h1>
          <p style={{ fontSize: '13px', color: '#8b949e', margin: '4px 0 0 0' }}>Isolated Creator Studio — Powered by NVIDIA GeForce RTX 4090 GPU Compute</p>
        </div>

        {/* Pass Key Header Bar */}
        <form onSubmit={(e) => e.preventDefault()} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input type="text" name="username" value="aibs_passkey_user" readOnly autoComplete="username" style={{ display: 'none' }} />
          <label htmlFor="pass-key-input" style={{ fontSize: '12px', color: '#8b949e' }}>Pass Key:</label>
          <input
            id="pass-key-input"
            aria-label="Pass Key Input"
            type="password"
            autoComplete="current-password"
            value={passKey}
            onChange={(e) => {
              setPassKey(e.target.value);
              if (typeof window !== 'undefined') localStorage.setItem('aibs_active_pass_key', e.target.value);
            }}
            placeholder="sk_aibs_live_..."
            style={{
              padding: '6px 12px',
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#38bdf8',
              fontSize: '12px',
              width: '180px',
              fontFamily: 'monospace'
            }}
          />
        </form>
      </div>

      {/* Paid API Key Security Gate Banner if Key is Missing */}
      {!passKey.trim() && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(137, 87, 229, 0.15), rgba(56, 189, 248, 0.15))',
          border: '1px solid #8957e5',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          <div style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '18px' }}>🔑</span>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '800', color: '#e6edf3' }}>Paid API Key Required for Web Studio Access</h3>
            </div>
            <p style={{ margin: 0, fontSize: '13px', color: '#8b949e', lineHeight: '1.5' }}>
              Web Studio GPU rendering requires an active Stehouwer AI Pass Key (<code style={{ color: '#38bdf8' }}>sk_aibs_...</code>). Enter your paid key above to unlock rendering or purchase a 1-click flexibility pass.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <a
              href="/checkout"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: 'linear-gradient(90deg, #8957e5, #38bdf8)',
                color: '#ffffff',
                padding: '10px 20px',
                borderRadius: '6px',
                fontWeight: '700',
                fontSize: '13px',
                textDecoration: 'none',
                boxShadow: '0 4px 12px rgba(137, 87, 229, 0.3)'
              }}
            >
              💳 Get Pass Key (From $4.99)
            </a>
          </div>
        </div>
      )}


      {/* Sub Navigation Bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {[
          { id: 'image', label: '🎨 Image Studio (SDXL)', desc: '2-Sec Render' },
          { id: 'video', label: '🎬 Video Studio (WanVideo)', desc: '4s Render' },
          { id: 'audio', label: '🎵 Audio & Music Studio', desc: '13 Genres' },
          { id: 'chat', label: '💬 AI Assistant Chat', desc: 'Fast LLM' },
          { id: 'developer', label: '🚀 API Developer & Passkey Portal', desc: 'Commercial Gateway' },
          { id: 'vault', label: `📁 My Created Media Vault (${mediaVault.length})`, desc: 'History' }

        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveSubTab(tab.id)}
            style={{
              padding: '10px 18px',
              background: activeSubTab === tab.id ? '#1f6feb' : '#161b22',
              color: '#ffffff',
              border: activeSubTab === tab.id ? '1px solid #38bdf8' : '1px solid #30363d',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '13px'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUB-TAB 1: IMAGE STUDIO */}
      {activeSubTab === 'image' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 16px 0', color: '#f0f6fc' }}>High-Resolution SDXL Image Generation</h2>
          
          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="image-prompt-input" style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Image Prompt:</label>
            <textarea
              id="image-prompt-input"
              aria-label="Image Prompt Input"
              value={imagePrompt}
              onChange={(e) => setImagePrompt(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <label htmlFor="image-size-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Aspect Ratio:</label>
              <select
                id="image-size-select"
                aria-label="Aspect Ratio Select"
                value={imageSize}
                onChange={(e) => setImageSize(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3' }}
              >
                <option value="1024x1024">Square (1024x1024)</option>
                <option value="1280x720">Landscape (1280x720)</option>
                <option value="720x1280">Portrait (720x1280)</option>
              </select>
            </div>

            <button
              onClick={handleGenerateImage}
              disabled={isGeneratingImage}
              style={{
                padding: '12px 24px',
                background: 'linear-gradient(90deg, #238636, #2ea043)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '700',
                cursor: isGeneratingImage ? 'wait' : 'pointer',
                marginTop: '16px'
              }}
            >
              {isGeneratingImage ? '⚡ RTX 4090 Rendering Image...' : '✨ Generate Image'}
            </button>
          </div>

          {/* Rendered Result Output */}
          {generatedImage && (
            <div style={{ marginTop: '24px', textAlign: 'center', background: '#0d1117', padding: '16px', borderRadius: '12px', border: '1px solid #30363d' }}>
              <img src={generatedImage} alt="Generated AI" style={{ maxWidth: '100%', maxHeight: '500px', borderRadius: '8px' }} />
              <div style={{ marginTop: '12px' }}>
                <a href={generatedImage} download="stehouwer_ai_image.png" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '600', fontSize: '13px' }}>
                  📥 Download High-Res Image
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 2: VIDEO STUDIO */}
      {activeSubTab === 'video' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 16px 0', color: '#f0f6fc' }}>WanVideo / AnimateDiff Motion Studio</h2>
          
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Video Motion Prompt:</label>
            <textarea
              value={videoPrompt}
              onChange={(e) => setVideoPrompt(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
            <div>
              <label htmlFor="video-duration-select" style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '4px' }}>Video Clip Duration:</label>
              <select
                id="video-duration-select"
                aria-label="Video Clip Duration"
                value={videoDuration}
                onChange={(e) => setVideoDuration(Number(e.target.value))}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value={4}>⚡ 4-Second Quick Clip</option>
                <option value={15}>🎬 15-Second Motion Scene</option>
                <option value={30}>📺 30-Second Commercial Spot</option>
                <option value={60}>🎥 60-Second Short Film</option>
                <option value={180}>🍿 3-Minute Epic Scene (180s)</option>
                <option value={300}>🌟 5-Minute Master Production (300s)</option>
              </select>
            </div>

            <button
              onClick={handleGenerateVideo}
              disabled={isGeneratingVideo}
              style={{
                padding: '10px 24px',
                background: 'linear-gradient(90deg, #8957e5, #6e40c9)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '700',
                cursor: isGeneratingVideo ? 'wait' : 'pointer',
                marginTop: '16px'
              }}
            >
              {isGeneratingVideo ? `⚡ RTX 4090 Rendering ${videoDuration}s Video...` : `🎬 Generate ${videoDuration}s AI Video`}
            </button>
          </div>


          {/* Rendered Video Result Output */}
          {generatedVideo && (
            <div style={{ marginTop: '24px', textAlign: 'center', background: '#0d1117', padding: '16px', borderRadius: '12px', border: '1px solid #30363d' }}>
              <video controls autoPlay loop src={generatedVideo} style={{ maxWidth: '100%', maxHeight: '450px', borderRadius: '8px' }} />
              <div style={{ marginTop: '12px' }}>
                <a href={generatedVideo} download="wanvideo_ai_clip.mp4" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '600', fontSize: '13px' }}>
                  📥 Download WanVideo MP4 Clip
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: AUDIO STUDIO */}
      {activeSubTab === 'audio' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 4px 0', color: '#f0f6fc' }}>AI Multi-Genre Music & Audio Texture Studio</h2>
          <p style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>
            Combine primary subgenres, niche hybrid blends, acoustic texture modifiers, vocal timbres, and rhythm descriptors into a custom tag stack.
          </p>

          <div style={{ marginBottom: '16px' }}>
            <label htmlFor="audio-prompt-input" style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Custom Tag-Stacked Audio Prompt:</label>
            <textarea
              id="audio-prompt-input"
              aria-label="Custom Tag-Stacked Audio Prompt"
              value={audioPrompt}
              onChange={(e) => setAudioPrompt(e.target.value)}
              rows={3}
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px', resize: 'vertical' }}
            />
          </div>

          {/* Custom Song Lyrics & Vocal Verses Input */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label htmlFor="audio-lyrics-input" style={{ fontSize: '12px', color: '#38bdf8', fontWeight: '600' }}>🎤 Custom Song Lyrics & Vocal Verses (Optional):</label>
              <button
                onClick={() => setAudioLyrics('[Verse 1]\nNeon lights in the midnight rain\nDriving fast down memory lane\n\n[Chorus]\nWe are the dreamers of the night\nElectric hearts burning bright\n\n[Bridge]\nFade away into the sound\nNo looking back, we own this town')}
                style={{ background: 'transparent', border: 'none', color: '#a855f7', fontSize: '11px', cursor: 'pointer', textDecoration: 'underline' }}
              >
                + Insert Sample Verse & Chorus Lyrics
              </button>
            </div>
            <textarea
              id="audio-lyrics-input"
              aria-label="Custom Song Lyrics & Vocal Verses"
              value={audioLyrics}
              onChange={(e) => setAudioLyrics(e.target.value)}
              rows={4}
              placeholder="[Verse 1]&#10;Type or paste your custom song lyrics here...&#10;&#10;[Chorus]&#10;Add your chorus lyrics here..."
              style={{ width: '100%', padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '13px', fontFamily: 'monospace', resize: 'vertical' }}
            />
          </div>

          {/* Quick Tag-Stacking Helper Chips */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '8px' }}>⚡ Quick Tag-Stacking Helper Chips (Click to append to prompt):</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {[
                "boom bap 808 sub-bass", "darksynth cyberpunk", "bluegrass trap hybrid", "epic dark orchestral",
                "1970s analog vinyl", "1980s cassette saturation", "90s lo-fi tape", "sidechain compression",
                "raspy gritty vocal", "silky whispered vocal", "vocoder effect", "gang vocals background",
                "syncopated beat", "half-time bounce", "relentless momentum", "explosive crescendo"
              ].map(tag => (
                <button
                  key={tag}
                  onClick={() => setAudioPrompt(prev => prev ? `${prev}, ${tag}` : tag)}
                  style={{
                    padding: '4px 10px',
                    background: '#21262d',
                    border: '1px solid #30363d',
                    borderRadius: '12px',
                    color: '#38bdf8',
                    fontSize: '11px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap' }}>
            <div>
              <label htmlFor="audio-genre-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Primary Genre Category:</label>
              <select
                id="audio-genre-select"
                aria-label="Primary Genre Category"
                value={audioGenre}
                onChange={(e) => setAudioGenre(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value="hip_hop">🎤 Hip Hop & Rap (Boom Bap, Trap, Drill, Phonk, 808s)</option>
                <option value="rock_metal">🎸 Rock & Metal (Alt Rock, Grunge, Heavy Metal, Metalcore)</option>
                <option value="electronic_edm">⚡ Electronic & EDM (Synthwave, Techno, DnB, Dubstep)</option>
                <option value="pop_dance">💃 Pop & Dance (Synth-Pop, K-Pop, Electropop)</option>
                <option value="rb_soul">🎷 R&B & Soul (Neo-Soul, Funk, Disco, Smooth Soul)</option>
                <option value="folk_country">🌿 Folk & Country (Americana, Bluegrass, Celtic Folk)</option>
                <option value="jazz_blues">🎺 Jazz & Blues (Smooth Jazz, Bebop, Bossa Nova, Blues)</option>
                <option value="global_rhythms">🌍 Global Rhythms (Afrobeats, Reggaeton, Dancehall, Amapiano)</option>
                <option value="cyberpunk_synthmetal">🔥 Hybrid: Cyberpunk / Synth-Metal (Industrial, Darksynth)</option>
                <option value="acoustic_hybrid">🪕 Hybrid: Acoustic / Hybrid (Bluegrass Trap, Folk-Pop)</option>
                <option value="atmospheric_ambient">🌌 Hybrid: Atmospheric / Ambient (Downtempo, Trip-Hop)</option>
                <option value="cinematic_orchestral">🎬 Hybrid: Cinematic / Orchestral (Epic Film Score, Trailer Music)</option>
                <option value="heavy_distorted">💥 Hybrid: Heavy / Distorted (Sludge Metal, Deathcore, Nu-Metal)</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-duration-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Song Length / Duration:</label>
              <select
                id="audio-duration-select"
                aria-label="Song Length / Duration"
                value={audioDuration}
                onChange={(e) => setAudioDuration(Number(e.target.value))}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value={0}>✨ Dynamic Auto-Timing (Calculated from Lyrics & BPM)</option>
                <option value={10}>10 Seconds Quick Clip</option>

                <option value={30}>30 Seconds Short Track</option>
                <option value={60}>60 Seconds Full Verse</option>
                <option value={180}>3 Minutes Full Song (180s)</option>
                <option value={300}>5 Minutes Extended Master (300s)</option>
                <option value={600}>10 Minutes Epic Suite (600s)</option>
                <option value={1200}>♾️ Unlimited Continuous Stream (1200s / 20 Mins)</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-vocal-style-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Vocal Mix Style:</label>
              <select
                id="audio-vocal-style-select"
                aria-label="Vocal Mix Style"
                value={audioVocalStyle}
                onChange={(e) => setAudioVocalStyle(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value="lead">🎙️ Lead Vocals (Clean & Clear)</option>
                <option value="harmonies">🎶 Layered Harmonies & Backing</option>
                <option value="whispered">🤫 Whispered & Soft Vocal</option>
                <option value="vocoder">🤖 Vocoder & Auto-Tune Synth</option>
                <option value="instrumental">🎻 Instrumental Only (No Vocals)</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-arrangement-select" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Song Arrangement:</label>
              <select
                id="audio-arrangement-select"
                aria-label="Song Arrangement"
                value={audioArrangement}
                onChange={(e) => setAudioArrangement(e.target.value)}
                style={{ padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
              >
                <option value="verse_chorus">🎼 Verse - Chorus - Bridge - Outro</option>
                <option value="build_drop">🔥 Intro - Build-Up - Explosive Drop</option>
                <option value="continuous_loop">🔁 Continuous Ambient Soundscape</option>
              </select>
            </div>

            <div>
              <label htmlFor="audio-tempo-range" style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Tempo / Speed: <strong style={{ color: '#38bdf8' }}>{audioTempo} BPM</strong></label>
              <input
                id="audio-tempo-range"
                aria-label="Tempo Speed BPM"
                type="range"
                min="70"
                max="160"
                value={audioTempo}
                onChange={(e) => setAudioTempo(Number(e.target.value))}
                style={{ width: '160px', accentColor: '#38bdf8', cursor: 'pointer' }}
              />
            </div>

            <button
              onClick={handleGenerateAudio}
              disabled={isGeneratingAudio}
              style={{
                padding: '12px 24px',
                background: 'linear-gradient(90deg, #d97706, #b45309)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '700',
                cursor: isGeneratingAudio ? 'wait' : 'pointer',
                marginTop: '16px'
              }}
            >
              {isGeneratingAudio 
                ? `⚡ Synthesizing ${audioDuration === 0 ? 'Auto-Timed' : audioDuration + 's'} Song (${audioTempo} BPM)...` 
                : `🎵 Synthesize ${audioDuration === 0 ? 'Auto-Timed' : audioDuration + 's'} Track (${audioTempo} BPM)`
              }
            </button>
          </div>





          {/* Rendered Audio Result Output */}
          {generatedAudio && (
            <div style={{ marginTop: '24px', textAlign: 'center', background: '#0d1117', padding: '20px', borderRadius: '12px', border: '1px solid #30363d' }}>
              <audio controls autoPlay src={generatedAudio} style={{ width: '100%', maxWidth: '500px', marginBottom: '12px' }} />
              <div>
                <a href={generatedAudio} download={`stehouwer_ai_${audioGenre}.wav`} style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '600', fontSize: '13px' }}>
                  📥 Download Tag-Stacked High-Quality WAV Audio
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUB-TAB 3: CHAT STUDIO */}
      {activeSubTab === 'chat' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', height: '600px' }}>
          <h2 style={{ fontSize: '18px', margin: '0 0 16px 0', color: '#f0f6fc' }}>Stehouwer AI Chat Assistant</h2>
          
          {/* Chat Messages */}
          <div style={{ flex: 1, overflowY: 'auto', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
            {chatMessages.map((msg, idx) => (
              <div key={idx} style={{ marginBottom: '12px', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                <div style={{
                  display: 'inline-block',
                  maxWidth: '80%',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: msg.role === 'user' ? '#1f6feb' : '#21262d',
                  color: '#ffffff',
                  fontSize: '14px',
                  lineHeight: '1.5'
                }}>
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {/* Chat Input */}
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
              placeholder="Ask anything or request creative assistance..."
              style={{ flex: 1, padding: '12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: '8px', color: '#e6edf3', fontSize: '14px' }}
            />
            <button
              onClick={handleSendChat}
              disabled={isChatting}
              style={{ padding: '12px 20px', background: '#238636', color: '#ffffff', border: 'none', borderRadius: '8px', fontWeight: '700', cursor: 'pointer' }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* SUB-TAB 6: COMMERCIAL API DEVELOPER & PASSKEY PORTAL */}
      {activeSubTab === 'developer' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <div style={{ marginBottom: '24px', borderBottom: '1px solid #21262d', paddingBottom: '16px' }}>
            <h2 style={{ fontSize: '20px', margin: '0 0 6px 0', color: '#38bdf8', fontWeight: '800' }}>
              🚀 Commercial API Developer & Passkey Portal
            </h2>
            <p style={{ fontSize: '13px', color: '#8b949e', margin: 0, lineHeight: '1.5' }}>
              Integrate AI-BS 44.1kHz RVQ Neural Audio, SDXL Visual Generation, WanVideo 5-Min Clips, and LLM Chat directly into your applications via sovereign API endpoints.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '24px' }}>
            {/* Card 1: Request Passkey */}
            <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
              <h3 style={{ fontSize: '16px', color: '#f0f6fc', marginTop: 0 }}>🔑 Self-Service Passkey Generator</h3>
              <p style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>
                Instantly provision a sovereign API key to access live endpoints over HTTPS.
              </p>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Client / Company Name:</label>
                <input
                  type="text"
                  value={devClientName}
                  onChange={(e) => setDevClientName(e.target.value)}
                  placeholder="e.g. Grand Rapids Creative Studio"
                  style={{ width: '100%', padding: '10px', background: '#161b22', border: '1px solid #30363d', borderRadius: '6px', color: '#e6edf3', fontSize: '13px' }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Target Usage Tier:</label>
                <select
                  value={devTier}
                  onChange={(e) => setDevTier(e.target.value)}
                  style={{ width: '100%', padding: '10px', background: '#161b22', border: '1px solid #30363d', borderRadius: '6px', color: '#38bdf8', fontSize: '13px' }}
                >
                  <option value="starter">Starter Tier (1,000 requests/day - $19/mo)</option>
                  <option value="pro">Pro Tier (10,000 requests/day - $49/mo)</option>
                  <option value="enterprise">Enterprise Tier (100,000 requests/day - $199/mo)</option>
                </select>
              </div>

              <button
                onClick={handleRequestPasskey}
                disabled={isGeneratingPasskey}
                style={{ width: '100%', padding: '12px', background: 'linear-gradient(90deg, #1f6feb, #38bdf8)', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer' }}
              >
                {isGeneratingPasskey ? 'Provisioning Passkey...' : '⚡ Generate Developer Passkey'}
              </button>

              {newGeneratedPasskey && (
                <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid #38bdf8', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: '4px' }}>YOUR NEW PASSKEY:</div>
                  <code style={{ fontSize: '12px', color: '#38bdf8', wordBreak: 'break-all', fontWeight: 'bold' }}>{newGeneratedPasskey.passkey}</code>
                  <div style={{ fontSize: '11px', color: '#238636', marginTop: '6px' }}>✓ Key automatically active and saved to your studio browser context!</div>
                </div>
              )}
            </div>

            {/* Card 2: Quota & Usage Monitor */}
            <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
              <h3 style={{ fontSize: '16px', color: '#f0f6fc', marginTop: 0 }}>📊 Live Quota & Usage Inspector</h3>
              <p style={{ fontSize: '12px', color: '#8b949e', marginBottom: '16px' }}>
                Check daily unit usage, remaining request balance, and active rate limits.
              </p>

              <button
                onClick={handleCheckPasskeyUsage}
                style={{ width: '100%', padding: '12px', background: '#238636', color: '#ffffff', border: 'none', borderRadius: '6px', fontWeight: '700', fontSize: '13px', cursor: 'pointer', marginBottom: '16px' }}
              >
                🔍 Inspect Active Passkey Usage
              </button>

              {passkeyUsageInfo ? (
                <div style={{ background: '#161b22', padding: '12px', borderRadius: '6px', fontSize: '12px', border: '1px solid #30363d' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>Client Name:</span>
                    <strong style={{ color: '#f0f6fc' }}>{passkeyUsageInfo.client_name}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>Active Tier:</span>
                    <span style={{ color: '#38bdf8', fontWeight: 'bold', textTransform: 'uppercase' }}>{passkeyUsageInfo.tier}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ color: '#8b949e' }}>Total Requests Recorded:</span>
                    <span style={{ color: '#e6edf3' }}>{passkeyUsageInfo.total_requests_recorded}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#8b949e' }}>Daily Quota Remaining:</span>
                    <span style={{ color: '#238636', fontWeight: 'bold' }}>{passkeyUsageInfo.remaining_units_today} / {passkeyUsageInfo.tier_daily_quota}</span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '12px', color: '#8b949e', fontStyle: 'italic', textAlign: 'center', padding: '20px 0' }}>
                  Click inspect button to view current passkey telemetry.
                </div>
              )}
            </div>
          </div>

          {/* Quickstart Code Snippets */}
          <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '16px', color: '#f0f6fc', marginTop: 0, marginBottom: '8px' }}>💻 Developer Quickstart cURL Snippet</h3>
            <p style={{ fontSize: '12px', color: '#8b949e', margin: '0 0 12px 0' }}>
              Execute requests directly against our live production proxy endpoint (<code style={{ color: '#38bdf8' }}>https://stehouwer-publishing.com/v1/</code>):
            </p>

            <pre style={{ background: '#161b22', padding: '16px', borderRadius: '8px', color: '#38bdf8', fontSize: '12px', fontFamily: 'monospace', overflowX: 'auto', border: '1px solid #30363d', margin: 0 }}>
{`curl -X POST https://stehouwer-publishing.com/v1/audio/generations \\
  -H "Authorization: Bearer ${newGeneratedPasskey?.passkey || 'sk_aibs_live_YOUR_PASSKEY_HERE'}" \\
  -H "Content-Type: application/json" \\

  -d '{
    "prompt": "Retro acoustic guitar and cellos",
    "genre": "acoustic",
    "duration_sec": 0,
    "tempo_bpm": 95,
    "lyrics": "[Verse 1]\\nGolden sunlight on the trees"
  }'`}
            </pre>
          </div>
        </div>
      )}

      {/* SUB-TAB 5: CREATED MEDIA VAULT */}

      {activeSubTab === 'vault' && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '12px', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '18px', margin: '0 0 4px 0', color: '#f0f6fc' }}>📁 My Created Media Vault</h2>
              <p style={{ fontSize: '12px', color: '#8b949e', margin: 0 }}>
                Persistent local gallery of all your rendered images, motion video clips, and synthesized audio tracks.
              </p>
            </div>

            {mediaVault.length > 0 && (
              <button
                onClick={clearVault}
                style={{ padding: '6px 14px', background: '#da3633', color: '#ffffff', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
              >
                🗑️ Clear Entire Vault
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
            {[
              { id: 'all', label: 'All Media' },
              { id: 'image', label: '🎨 Images' },
              { id: 'video', label: '🎬 Videos' },
              { id: 'audio', label: '🎵 Audio Tracks' }
            ].map(filter => (
              <button
                key={filter.id}
                onClick={() => setVaultFilter(filter.id)}
                style={{
                  padding: '6px 14px',
                  background: vaultFilter === filter.id ? '#1f6feb' : '#0d1117',
                  color: '#ffffff',
                  border: vaultFilter === filter.id ? '1px solid #38bdf8' : '1px solid #30363d',
                  borderRadius: '20px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {/* Media Items Grid */}
          {mediaVault.filter(item => vaultFilter === 'all' || item.type === vaultFilter).length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 24px', background: '#0d1117', borderRadius: '12px', border: '1px solid #30363d', color: '#8b949e' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>📁</div>
              <h3 style={{ fontSize: '16px', margin: '0 0 8px 0', color: '#e6edf3' }}>No Media Items Saved Yet</h3>
              <p style={{ fontSize: '13px', margin: 0 }}>
                Generate images, videos, or audio tracks in the playground to automatically save them into your vault!
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
              {mediaVault
                .filter(item => vaultFilter === 'all' || item.type === vaultFilter)
                .map(item => (
                  <div
                    key={item.id}
                    style={{
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: '12px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      justify: 'space-between'
                    }}
                  >
                    <div>
                      {/* Header Badge & Date */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '12px',
                          fontSize: '11px',
                          fontWeight: '700',
                          background: item.type === 'image' ? '#1f6feb' : item.type === 'video' ? '#8957e5' : '#d97706',
                          color: '#ffffff'
                        }}>
                          {item.type === 'image' ? '🎨 IMAGE' : item.type === 'video' ? '🎬 VIDEO' : '🎵 AUDIO'}
                        </span>
                        <span style={{ fontSize: '11px', color: '#8b949e' }}>{item.timestamp}</span>
                      </div>

                      {/* Prompt */}
                      <p style={{ fontSize: '13px', color: '#e6edf3', margin: '0 0 14px 0', lineHeight: '1.4', fontWeight: '500' }}>
                        "{item.prompt}"
                      </p>

                      {/* Media Display */}
                      {(() => {
                        const mediaSrc = (item.url && !item.url.startsWith('http') && !item.url.startsWith('data:')) ? `${apiHost}${item.url}` : item.url;
                        return (
                          <div style={{ marginBottom: '14px', textAlign: 'center', background: '#161b22', borderRadius: '8px', padding: '8px', overflow: 'hidden' }}>
                            {item.type === 'image' && (
                              <img src={mediaSrc} alt={item.prompt} style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '6px', objectFit: 'contain' }} />
                            )}
                            {item.type === 'video' && (
                              <video controls autoPlay loop src={mediaSrc} style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '6px' }} />
                            )}
                            {item.type === 'audio' && (
                              <audio controls src={mediaSrc} style={{ width: '100%' }} />
                            )}
                          </div>
                        );
                      })()}
                    </div>

                    {/* Footer Actions */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #21262d', paddingTop: '12px' }}>
                      <a
                        href={(item.url && !item.url.startsWith('http') && !item.url.startsWith('data:')) ? `${apiHost}${item.url}` : item.url}
                        download={`stehouwer_${item.type}_${item.id}.${item.type === 'image' ? 'png' : item.type === 'video' ? 'mp4' : 'wav'}`}
                        style={{ color: '#38bdf8', textDecoration: 'none', fontSize: '12px', fontWeight: '600' }}
                      >
                        📥 Download File
                      </a>
                      <button
                        onClick={() => deleteFromVault(item.id)}
                        style={{ background: 'none', border: 'none', color: '#f85149', cursor: 'pointer', fontSize: '12px', fontWeight: '600' }}
                      >
                        ❌ Remove
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

    </main>
  );
}
```

*End of PublicPlaygroundTab.jsx*

---

# Data, OSINT & API Tools
*1 file(s) in this category*

## BrettDataTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

const RAPID_CATEGORIES = [
  { id: 'data', label: 'Data', icon: '📈' },
  { id: 'sports', label: 'Sports', icon: '🏀' },
  { id: 'ai', label: 'AI & ML', icon: '🤖' },
  { id: 'finance', label: 'Finance', icon: '💰' },
  { id: 'entertainment', label: 'Entertainment', icon: '🎬' },
  { id: 'travel', label: 'Travel', icon: '✈️' },
  { id: 'location', label: 'Location', icon: '📍' },
  { id: 'science', label: 'Science', icon: '🔬' },
  { id: 'food', label: 'Food', icon: '🍔' },
  { id: 'transportation', label: 'Transportation', icon: '🚌' },
  { id: 'music', label: 'Music', icon: '🎵' },
  { id: 'business', label: 'Business', icon: '💼' },
  { id: 'visual', label: 'Visual Recog.', icon: '👁️' },
  { id: 'tools', label: 'Tools', icon: '🛠️' },
  { id: 'text', label: 'Text Analysis', icon: '📝' },
  { id: 'weather', label: 'Weather', icon: '⛅' },
  { id: 'gaming', label: 'Gaming', icon: '🎮' },
  { id: 'sms', label: 'SMS', icon: '📱' },
  { id: 'events', label: 'Events', icon: '🎫' },
  { id: 'health', label: 'Health', icon: '🏃' }
];

const TASK_MAPPINGS = {
  entertainment: [
    { value: 'facebook_group_videos', label: 'Facebook Group Videos' },
    { value: 'facebook_user_search', label: 'Facebook User Search' },
    { value: 'tiktok_oldest_posts', label: 'TikTok Oldest Posts' },
    { value: 'instagram_followings', label: 'Instagram Followings' }
  ],
  business: [
    { value: 'email_finder', label: 'Email Finder (Hunter/Snovio)' },
    { value: 'phone_lookup', label: 'Phone Number Lookup' },
    { value: 'domain_search', label: 'Domain Search' },
    { value: 'linkedin_profile', label: 'LinkedIn Profile Data' },
    { value: 'linkedin_company', label: 'LinkedIn Company Data' },
    { value: 'linkedin_jobs', label: 'LinkedIn Job Search' }
  ],
  tools: [
    { value: 'google_search', label: 'Google Search' },
    { value: 'subdomain_finder', label: 'Subdomain Finder' },
    { value: 'skip_tracing_email', label: 'Skip Tracing by Email' }
  ],
  finance: [
    { value: 'crypto_account_balance', label: 'Crypto.com Balances (Mock)' },
    { value: 'crypto_market_data', label: 'Crypto Market Ticker' },
    { value: 'yahoo_finance', label: 'Yahoo Finance (YH Finance)' }
  ]
};

export default function BrettDataTab({ backendUrl }) {
  const [activeSubTab, setActiveSubTab] = useState('api_hub');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [rawJson, setRawJson] = useState('');
  const [parsedData, setParsedData] = useState(null);
  const [parseError, setParseError] = useState('');

  // Live Fetch State
  const [apis, setApis] = useState([]);
  const [selectedApiId, setSelectedApiId] = useState('');
  const [manualApiKey, setManualApiKey] = useState('');
  const [taskType, setTaskType] = useState('facebook_group_videos');
  const [targetId, setTargetId] = useState('');
  const [isFetching, setIsFetching] = useState(false);

  // Test & Sort State
  const [testEndpoint, setTestEndpoint] = useState('');
  const [testSelectedApiId, setTestSelectedApiId] = useState('');
  const [testManualApiKey, setTestManualApiKey] = useState('');
  const [testIsFetching, setTestIsFetching] = useState(false);
  const [testRawJson, setTestRawJson] = useState('');
  const [testParsedList, setTestParsedList] = useState(null);
  const [testError, setTestError] = useState('');

  const [vaultItems, setVaultItems] = useState([]);

  // API Manager States
  const [newApi, setNewApi] = useState({ clientName: '', apiName: '', apiKey: '', baseUrl: '', category: '' });
  const [query, setQuery] = useState('');
  const [recommenderResponse, setRecommenderResponse] = useState('');
  const [isLoadingRecommender, setIsLoadingRecommender] = useState(false);
  const [testerApiId, setTesterApiId] = useState('');
  const [testerEndpoint, setTesterEndpoint] = useState('');
  const [testerMethod, setTesterMethod] = useState('GET');
  const [testerAuthType, setTesterAuthType] = useState('Query Parameter');
  const [testerAuthKeyName, setTesterAuthKeyName] = useState('access_token');
  const [testerBody, setTesterBody] = useState('');
  const [testerResponse, setTesterResponse] = useState('');
  const [isTesting, setIsTesting] = useState(false);

  useEffect(() => {
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/keys`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setApis(data.keys);
        }
      })
      .catch(err => console.error("Failed to fetch keys:", err));

    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/data`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setVaultItems(data.vault);
        }
      })
      .catch(err => console.error("Failed to fetch vault data:", err));
  }, [backendUrl]);

  const handleSaveToVault = (item, source) => {
    const payload = {
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      source,
      data: item
    };
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/data`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(() => {
      setVaultItems([payload, ...vaultItems]);
      alert('Saved to Vault!');
    });
  };

  const handleDeleteFromVault = (id) => {
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/data/${id}`, { method: "DELETE" }).then(() => {
      setVaultItems(vaultItems.filter(i => i.id !== id));
    });
  };

  const handleSendToClipboard = (item) => {
    const formatted = JSON.stringify(item.data, null, 2);
    navigator.clipboard.writeText(formatted).then(() => {
      alert('Copied to clipboard! You can now paste this anywhere.');
    }).catch(() => {
      alert('Failed to copy to clipboard.');
    });
  };

  const handleAddApi = (e) => {
    e.preventDefault();
    if (!newApi.apiName || !newApi.apiKey) return;
    const apiObj = { id: Date.now().toString(), clientName: newApi.clientName || 'Custom', ...newApi };
    
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(apiObj)
    }).then(() => {
      setApis([...apis, apiObj]);
      setNewApi({ clientName: '', apiName: '', apiKey: '', baseUrl: '', category: '' });
    });
  };

  const handleDeleteApi = (id) => {
    fetch(`${backendUrl}/api/proxy/8001/api/v1/vault/keys/${id}`, { method: "DELETE" }).then(() => {
      setApis(apis.filter(api => api.id !== id));
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleAskRecommender = async (e) => {
    e.preventDefault();
    if (!query) return;
    setIsLoadingRecommender(true);
    setRecommenderResponse('');
    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `I need an API recommendation. ${query}. Please list 2-3 public or RapidAPI APIs that could solve this, with their general capabilities and where to find them. Format as markdown.`,
          model: 'stehouwer_llm',
          persona: 'Brett Stehouwer (CTO)'
        })
      });
      if (!res.ok) throw new Error("Failed to fetch recommendation");
      const data = await res.json();
      setRecommenderResponse(data.reply);
    } catch (err) {
      setRecommenderResponse("Error contacting AI for recommendation.");
    } finally {
      setIsLoadingRecommender(false);
    }
  };

  const handleRunTest = async (e) => {
    e.preventDefault();
    if (!testerApiId || !testerEndpoint) return;
    const apiToTest = apis.find(a => a.id === testerApiId);
    if (!apiToTest) return;
    setIsTesting(true);
    setTesterResponse('Running test...');
    try {
      let finalUrl = testerEndpoint;
      const headers = { 'Accept': 'application/json' };
      if (testerAuthType === 'Query Parameter') {
        const separator = finalUrl.includes('?') ? '&' : '?';
        finalUrl = `${finalUrl}${separator}${testerAuthKeyName}=${encodeURIComponent(apiToTest.apiKey)}`;
      } else if (testerAuthType === 'Bearer Token') {
        headers['Authorization'] = `Bearer ${apiToTest.apiKey}`;
      } else if (testerAuthType === 'Custom Header') {
        headers[testerAuthKeyName] = apiToTest.apiKey;
      }
      try {
        const urlObj = new URL(finalUrl);
        if (urlObj.hostname.includes('rapidapi.com')) {
          headers['x-rapidapi-host'] = urlObj.hostname;
          headers['x-rapidapi-key'] = apiToTest.apiKey;
        }
      } catch (e) {}
      const options = { method: testerMethod, headers };
      if (testerMethod !== 'GET' && testerMethod !== 'HEAD' && testerBody) {
        options.body = testerBody;
        headers['Content-Type'] = 'application/json';
      }
      const res = await fetch(finalUrl, options);
      const data = await res.json().catch(() => null);
      const responsePayload = {
        status: res.status,
        statusText: res.statusText,
        headers: Object.fromEntries(res.headers.entries()),
        data: data || "No JSON returned or failed to parse JSON"
      };
      setTesterResponse(JSON.stringify(responsePayload, null, 2));
    } catch (err) {
      setTesterResponse(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setIsTesting(false);
    }
  };

  const handleFetchLive = async () => {
    let finalApiKey = '';
    if (selectedApiId) {
      const api = apis.find(a => a.id === selectedApiId);
      if (api) finalApiKey = api.apiKey;
    } else if (manualApiKey) {
      finalApiKey = manualApiKey;
    }

    if (!finalApiKey || !taskType || !targetId) return;

    setIsFetching(true);
    setParseError('');
    setParsedData(null);

    try {
      const res = await fetch(`${backendUrl}/api/proxy/3001/api/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskType,
          targetId,
          apiKey: finalApiKey
        })
      });
      
      const backendData = await res.json();
      
      if (!res.ok) {
        throw new Error(backendData.error || 'Backend failed');
      }

      setRawJson(JSON.stringify(backendData, null, 2));
      const data = backendData.data;

      if (data && data.data && data.data.videos) {
        setParsedData(data.data.videos);
      } else if (Array.isArray(data)) {
        setParsedData(data);
      } else if (data && data.videos) {
        setParsedData(data.videos);
      } else {
        setParseError('Fetched successfully, but could not find a recognized list to render. File saved to: ' + backendData.savedPath);
        setParsedData(null);
      }
    } catch (err) {
      setParseError('Failed to fetch data: ' + err.message);
      setParsedData(null);
    } finally {
      setIsFetching(false);
    }
  };

  const getTaskHelperText = (type) => {
    switch (type) {
      case 'facebook_group_videos': return "Fetches videos from a Facebook group. Target ID: The numerical ID of the group (e.g., 1571965316444595).";
      case 'facebook_user_search': return "Searches for a user on Facebook. Target ID: The user's name or search term.";
      case 'tiktok_oldest_posts': return "Fetches the oldest posts from a TikTok user. Target ID: The 'secUid' of the TikTok user.";
      case 'instagram_followings': return "Fetches the list of people an Instagram user follows. Target ID: The exact Instagram username.";
      case 'google_search': return "Performs a Google Search. Target ID: Your search query (e.g., 'plumbers in NY').";
      case 'subdomain_finder': return "Finds subdomains for a given website. Target ID: The domain name (e.g., 'example.com').";
      case 'skip_tracing_email': return "Performs a skip trace lookup based on an email. Target ID: The email address to look up.";
      default: return "";
    }
  };

  const extractArrayFromJSON = (obj) => {
    if (Array.isArray(obj)) return obj;
    if (obj && typeof obj === 'object') {
      for (const key of Object.keys(obj)) {
        if (Array.isArray(obj[key])) return obj[key];
        const nested = extractArrayFromJSON(obj[key]);
        if (nested) return nested;
      }
    }
    return null;
  };

  const handleTestFetchLive = async () => {
    let finalApiKey = '';
    if (testSelectedApiId) {
      const api = apis.find(a => a.id === testSelectedApiId);
      if (api) finalApiKey = api.apiKey;
    } else if (testManualApiKey) {
      finalApiKey = testManualApiKey;
    }

    if (!finalApiKey || !testEndpoint) return;

    setTestIsFetching(true);
    setTestError('');
    setTestParsedList(null);

    try {
      const headers = { 'Accept': 'application/json' };
      const urlObj = new URL(testEndpoint);
      if (urlObj.hostname.includes('rapidapi.com')) {
        headers['x-rapidapi-host'] = urlObj.hostname;
        headers['x-rapidapi-key'] = finalApiKey;
      }

      const res = await fetch(testEndpoint, { headers });
      const data = await res.json();
      setTestRawJson(JSON.stringify(data, null, 2));

      const foundArray = extractArrayFromJSON(data);
      if (foundArray && foundArray.length > 0) {
        setTestParsedList(foundArray);
      } else {
        setTestError('Fetched successfully, but could not automatically detect an array of items in the JSON to render.');
        setTestParsedList(null);
      }
    } catch (err) {
      setTestError('Failed to fetch data: ' + err.message);
      setTestParsedList(null);
    } finally {
      setTestIsFetching(false);
    }
  };

  const handleParseJson = () => {
    setParseError('');
    try {
      const data = JSON.parse(rawJson);
      
      // Handle the specific facebook scraper payload we saw
      if (data && data.data && data.data.videos) {
        setParsedData(data.data.videos);
      } else if (data && data.videos) {
        setParsedData(data.videos);
      } else if (Array.isArray(data)) {
        setParsedData(data); // Generic array
      } else {
        setParseError('Parsed successfully, but could not find a "videos" array or a standard list of items in the JSON.');
        setParsedData(null);
      }
    } catch (err) {
      setParseError('Invalid JSON format. Please paste valid JSON output from the API Tester.');
      setParsedData(null);
    }
  };

  return (
    <div className="tab-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <h2 className="tab-header" style={{ color: 'var(--accent)' }}>Brett Stehouwer Data Hub</h2>
      <p style={{ color: 'var(--text-muted)' }}>Skim, organize, and visualize data gathered from your APIs.</p>

      {/* Sub-Navigation */}
      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '16px' }}>
        <button 
          onClick={() => setActiveSubTab('api_hub')}
          style={{ 
            background: activeSubTab === 'api_hub' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'api_hub' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'api_hub' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
          }}>
          🌐 API Catalog
        </button>
        <button 
          onClick={() => setActiveSubTab('test_sort')}
          style={{ 
            background: activeSubTab === 'test_sort' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'test_sort' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'test_sort' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
          }}>
          🧪 Test & Sort
        </button>
        <button 
          onClick={() => setActiveSubTab('api_manager')}
          style={{ 
            background: activeSubTab === 'api_manager' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'api_manager' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'api_manager' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s'
          }}>
          🔑 API Vault & Discovery
        </button>
        <button 
          onClick={() => setActiveSubTab('vault')}
          style={{ 
            background: activeSubTab === 'vault' ? 'rgba(255,255,255,0.1)' : 'transparent',
            border: activeSubTab === 'vault' ? '1px solid var(--accent)' : '1px solid transparent',
            color: activeSubTab === 'vault' ? 'white' : 'var(--text-muted)',
            padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s',
            marginLeft: 'auto'
          }}>
          🗄️ Data Vault ({vaultItems.length})
        </button>
      </div>

      {activeSubTab === 'api_hub' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {!selectedCategory ? (
            <div className="glass-card">
              <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>API Catalog</h3>
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '24px' }}>
                Select a category to view and run live API connections.
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '16px' }}>
                {RAPID_CATEGORIES.map(cat => (
                  <button 
                    key={cat.id}
                    onClick={() => { setSelectedCategory(cat.id); setTaskType(TASK_MAPPINGS[cat.id]?.[0]?.value || ''); }}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '12px',
                      padding: '24px 16px',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '12px',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.borderColor = 'var(--accent)'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(0,0,0,0.3)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
                  >
                    <span style={{ fontSize: '2.5rem' }}>{cat.icon}</span>
                    <span style={{ color: '#e2e8f0', fontSize: '0.95rem', fontWeight: '500', textAlign: 'center' }}>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <button 
                onClick={() => setSelectedCategory(null)}
                style={{ alignSelf: 'flex-start', background: 'transparent', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                ← Back to Categories
              </button>
              
              <div className="glass-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '1.5rem' }}>{RAPID_CATEGORIES.find(c => c.id === selectedCategory)?.icon}</span>
                  <h3 className="glass-card-title" style={{color: 'white', margin: 0}}>
                    {RAPID_CATEGORIES.find(c => c.id === selectedCategory)?.label} Data Connection
                  </h3>
                </div>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
                  Connect directly to your API and pull data automatically.
                </p>
                
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>API Key to Use</label>
                    <select 
                      className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white', marginBottom: '8px' }}
                      value={selectedApiId} onChange={e => setSelectedApiId(e.target.value)}
                    >
                      <option value="" style={{color: 'black'}}>-- Select API Key --</option>
                      {apis.map(api => (
                        <option key={api.id} value={api.id} style={{color: 'black'}}>{api.apiName}</option>
                      ))}
                    </select>
                    <input 
                      type="text" placeholder="Or paste API key manually..." className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                      value={manualApiKey} onChange={e => setManualApiKey(e.target.value)}
                      disabled={!!selectedApiId}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '150px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Task Type</label>
                    <select 
                      className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                      value={taskType} onChange={e => setTaskType(e.target.value)}
                    >
                      {TASK_MAPPINGS[selectedCategory] ? (
                        TASK_MAPPINGS[selectedCategory].map(t => (
                          <option key={t.value} value={t.value} style={{color: 'black'}}>{t.label}</option>
                        ))
                      ) : (
                        <option value="" style={{color: 'black'}}>No specific tasks configured yet</option>
                      )}
                    </select>
                  </div>
                  <div style={{ flex: 2, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Target ID / Search Query</label>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <input 
                        type="text" placeholder="e.g. 1571965316444595 or full URL" className="chat-input"
                        style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', flex: 1, width: '100%' }}
                        value={targetId} onChange={e => setTargetId(e.target.value)}
                      />
                      {taskType === 'facebook_group_videos' && (
                        <button 
                          onClick={async () => {
                             if (!targetId.includes('facebook.com')) { alert('Please paste a full Facebook URL to extract the ID'); return; }
                             try {
                               const res = await fetch(`${backendUrl}/api/proxy/3001/api/utils/fb-group-id`, {
                                 method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: targetId })
                               });
                               const data = await res.json();
                               if (data.success) {
                                  setTargetId(data.groupId);
                               } else {
                                  alert(data.error);
                               }
                             } catch (err) { alert('Failed: ' + err.message); }
                          }}
                          style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid var(--accent)', color: 'white', borderRadius: '8px', padding: '0 12px', cursor: 'pointer', whiteSpace: 'nowrap' }}
                          title="Extract Group ID from URL"
                        >
                          🔍 Extract ID
                        </button>
                      )}
                    </div>
                  </div>
                </div>
    
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', marginBottom: '16px', borderLeft: '4px solid var(--accent)' }}>
                  <strong style={{color: 'white'}}>💡 Tip:</strong> <span style={{ color: '#94a3b8', fontSize: '0.9rem', marginLeft: '8px' }}>{getTaskHelperText(taskType)}</span>
                </div>
    
                <button onClick={handleFetchLive} className="send-button" style={{ padding: '8px 24px' }} disabled={isFetching || (!selectedApiId && !manualApiKey) || !targetId || !taskType}>
                  {isFetching ? 'Fetching...' : '⚡ Fetch & Organize Live Data'}
                </button>
              </div>
    
              <div className="glass-card">
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>Manual Data Input (Fallback)</h3>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
                  Or, you can paste the raw JSON response manually here.
                </p>
                <textarea 
                  className="chat-input"
                  placeholder='Paste JSON here...'
                  value={rawJson}
                  onChange={(e) => setRawJson(e.target.value)}
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', minHeight: '120px', fontFamily: 'monospace', color: '#c9d1d9', marginBottom: '16px' }}
                />
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <button onClick={handleParseJson} className="send-button" style={{ padding: '8px 24px' }}>
                    Parse Data
                  </button>
                  {parseError && <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>{parseError}</span>}
                </div>
              </div>
    
              {parsedData && (
                <div className="glass-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h3 className="glass-card-title" style={{color: 'white', margin: 0}}>Organized Feed</h3>
                    <span className="status-pill active">{parsedData.length} items found</span>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                    {parsedData.map((item, idx) => (
                      <div key={item.id || idx} style={{ 
                        background: 'rgba(0,0,0,0.4)', 
                        borderRadius: '12px', 
                        border: '1px solid rgba(255,255,255,0.05)',
                        overflow: 'hidden',
                        display: 'flex',
                        flexDirection: 'column'
                      }}>
                        {item.image && item.image.uri ? (
                          <div style={{ width: '100%', height: '200px', backgroundImage: `url(${item.image.uri})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
                        ) : (
                          <div style={{ width: '100%', height: '200px', background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                            No Image
                          </div>
                        )}
                        
                        <div style={{ padding: '16px', flex: 1, display: 'flex', flexDirection: 'column' }}>
                          <p style={{ color: '#e2e8f0', fontSize: '0.95rem', marginBottom: '16px', flex: 1, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                            {item.message || "No caption provided."}
                          </p>
                          
                          {item.url && (
                            <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ 
                              display: 'inline-block', 
                              background: 'rgba(255,255,255,0.1)', 
                              color: 'var(--accent)', 
                              padding: '8px 16px', 
                              borderRadius: '6px', 
                              textDecoration: 'none', 
                              textAlign: 'center',
                              fontSize: '0.9rem',
                              fontWeight: 'bold',
                              transition: 'background 0.2s',
                              marginBottom: '8px'
                            }}
                            onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.2)'}
                            onMouseOut={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                            >
                              Watch on Source
                            </a>
                          )}
                          <button onClick={() => handleSaveToVault(item, 'Extracted Data')} style={{
                            background: 'transparent',
                            border: '1px solid rgba(255,255,255,0.2)',
                            color: 'white',
                            padding: '8px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.9rem'
                          }}
                          onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                          onMouseOut={(e) => e.target.style.background = 'transparent'}>
                            💾 Save to Vault
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeSubTab === 'test_sort' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-card">
            <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>API Test Sandbox</h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
              Test any API endpoint here. The system will attempt to automatically find and render any list of items it returns.
            </p>
            
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
              <div style={{ flex: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>API Key to Use</label>
                <select 
                  className="chat-input"
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white', marginBottom: '8px' }}
                  value={testSelectedApiId} onChange={e => setTestSelectedApiId(e.target.value)}
                >
                  <option value="" style={{color: 'black'}}>-- Select API Key --</option>
                  {apis.map(api => (
                    <option key={api.id} value={api.id} style={{color: 'black'}}>{api.apiName}</option>
                  ))}
                </select>
                <input 
                  type="text" placeholder="Or paste API key manually..." className="chat-input"
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                  value={testManualApiKey} onChange={e => setTestManualApiKey(e.target.value)}
                  disabled={!!testSelectedApiId}
                />
              </div>
              <div style={{ flex: 2, minWidth: '300px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Endpoint URL</label>
                <input 
                  type="url" placeholder="Paste any RapidAPI endpoint here..." className="chat-input"
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                  value={testEndpoint} onChange={e => setTestEndpoint(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <button onClick={handleTestFetchLive} className="send-button" style={{ padding: '8px 24px' }} disabled={testIsFetching || (!testSelectedApiId && !testManualApiKey) || !testEndpoint}>
                {testIsFetching ? 'Fetching...' : '🧪 Fetch & Auto-Sort'}
              </button>
              {testError && <span style={{ color: '#ef4444', fontSize: '0.9rem' }}>{testError}</span>}
            </div>
          </div>

          {testRawJson && !testParsedList && (
            <div className="glass-card">
               <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>Raw JSON Response</h3>
               <textarea 
                  className="chat-input"
                  readOnly
                  value={testRawJson}
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', minHeight: '300px', fontFamily: 'monospace', color: '#c9d1d9', marginBottom: '16px' }}
                />
            </div>
          )}

          {testParsedList && (
            <div className="glass-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h3 className="glass-card-title" style={{color: 'white', margin: 0}}>Auto-Discovered Data Cards</h3>
                <span className="status-pill active">{testParsedList.length} items found</span>
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                {testParsedList.map((item, idx) => (
                  <div key={item.id || idx} style={{ 
                    background: 'rgba(0,0,0,0.4)', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.05)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column'
                  }}>
                    <div style={{ flex: 1, marginBottom: '16px', overflow: 'hidden', fontSize: '0.85rem', color: '#e2e8f0' }}>
                      {Object.keys(item).slice(0, 5).map(key => (
                        <div key={key} style={{ marginBottom: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          <strong style={{ color: 'var(--accent)' }}>{key}:</strong> {typeof item[key] === 'object' ? JSON.stringify(item[key]).substring(0, 50) + '...' : String(item[key])}
                        </div>
                      ))}
                      {Object.keys(item).length > 5 && <div style={{ color: '#94a3b8', fontStyle: 'italic', marginTop: '4px' }}>+ {Object.keys(item).length - 5} more fields...</div>}
                    </div>
                    
                    <button onClick={() => handleSaveToVault(item, 'Auto-Sorted Data API')} style={{
                      background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white',
                      padding: '8px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem'
                    }}
                    onMouseOver={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                    onMouseOut={(e) => e.target.style.background = 'transparent'}>
                      💾 Save to Vault
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'api_manager' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px', marginBottom: '8px', borderLeft: '4px solid var(--accent)' }}>
            <h4 style={{ color: 'white', marginTop: 0, marginBottom: '8px' }}>📖 How to use this tab:</h4>
            <ul style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0, paddingLeft: '20px', lineHeight: '1.5' }}>
              <li><strong>Add New API Key:</strong> Store your RapidAPI or custom API keys securely here. They will be saved locally.</li>
              <li><strong>AI API Recommender:</strong> Not sure which API to use? Ask the AI to suggest one based on your goal.</li>
              <li><strong>API Tester Workbench:</strong> Test an endpoint directly from the dashboard to see what raw JSON data it returns before building a full integration for it.</li>
            </ul>
          </div>

          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
            {/* Left Column: Vault & Form */}
            <div style={{ flex: '2', minWidth: '350px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              <div className="glass-card">
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '16px'}}>Add New API Key</h3>
                <form onSubmit={handleAddApi} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <input type="text" placeholder="Client Name (e.g. Action Glass)" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.clientName} onChange={e => setNewApi({...newApi, clientName: e.target.value})} />
                  <input type="text" placeholder="API Name (e.g. Facebook Graph API) *" className="chat-input" required
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.apiName} onChange={e => setNewApi({...newApi, apiName: e.target.value})} />
                  <input type="text" placeholder="Category (e.g. Social, SEO, Weather)" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.category} onChange={e => setNewApi({...newApi, category: e.target.value})} />
                  <input type="text" placeholder="Base URL (optional)" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.baseUrl} onChange={e => setNewApi({...newApi, baseUrl: e.target.value})} />
                  <input type="password" placeholder="API Key / Token *" className="chat-input" required
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    value={newApi.apiKey} onChange={e => setNewApi({...newApi, apiKey: e.target.value})} />
                  <button type="submit" className="send-button" style={{ marginTop: '8px', alignSelf: 'flex-start' }}>Save API Config</button>
                </form>
              </div>

              <div className="glass-card" style={{ flex: 1 }}>
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '16px'}}>Saved APIs</h3>
                {apis.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>No APIs saved yet.</p>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    {apis.map(api => (
                      <div key={api.id} style={{ 
                        background: 'rgba(0,0,0,0.4)', padding: '16px', borderRadius: '8px',
                        border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '8px'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong style={{ fontSize: '1.1rem', color: 'var(--accent-neon)' }}>{api.apiName}</strong>
                          {api.id !== 'system-rapidapi' && (
                            <button onClick={() => handleDeleteApi(api.id)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1.2rem' }} title="Delete API">×</button>
                          )}
                        </div>
                        {api.clientName && <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Client: {api.clientName}</div>}
                        {api.category && <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Category: <span className="status-pill new">{api.category}</span></div>}
                        {api.baseUrl && <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Base URL: {api.baseUrl}</div>}
                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                          <input type="password" value={api.apiKey} readOnly className="chat-input" style={{ background: 'rgba(255,255,255,0.05)', border: 'none', flex: 1, padding: '8px', borderRadius: '4px' }} />
                          <button onClick={() => copyToClipboard(api.apiKey)} className="tool-toggle-btn" title="Copy API Key">📋 Copy</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: AI Recommender */}
            <div style={{ flex: '1', minWidth: '300px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>AI API Recommender</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
                  Describe what kind of data or functionality you need, and the AI will suggest the best APIs for the job.
                </p>
                <form onSubmit={handleAskRecommender} style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                  <input type="text" placeholder="E.g. I need an API for real estate listings" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', flex: 1 }}
                    value={query} onChange={e => setQuery(e.target.value)} />
                  <button type="submit" className="send-button" disabled={isLoadingRecommender}>
                    {isLoadingRecommender ? '...' : 'Ask'}
                  </button>
                </form>
                <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: '8px', padding: '16px', border: '1px solid rgba(255,255,255,0.05)', overflowY: 'auto', minHeight: '200px' }} className="artifact-markdown-container">
                  {isLoadingRecommender ? (
                    <div style={{ color: 'var(--accent)', fontStyle: 'italic' }}>Searching API directories...</div>
                  ) : recommenderResponse ? (
                    <ReactMarkdown>{recommenderResponse}</ReactMarkdown>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', marginTop: '40px' }}>
                      Ask me for API recommendations!
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* API Tester Workbench */}
          <div className="glass-card" style={{ marginTop: '0px' }}>
            <h3 className="glass-card-title" style={{color: 'white', marginBottom: '16px'}}>API Tester Workbench</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Select a saved API key and enter an endpoint to test the connection.
            </p>
            <form onSubmit={handleRunTest} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Saved API</label>
                  <select className="chat-input" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                    value={testerApiId} onChange={e => setTesterApiId(e.target.value)} required>
                    <option value="" style={{color: 'black'}}>-- Select API --</option>
                    {apis.map(api => (
                      <option key={api.id} value={api.id} style={{color: 'black'}}>{api.apiName} ({api.clientName || 'No Client'})</option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 2, minWidth: '300px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Endpoint URL</label>
                  <input type="url" placeholder="https://graph.facebook.com/v19.0/me" className="chat-input"
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                    value={testerEndpoint} onChange={e => setTesterEndpoint(e.target.value)} required />
                </div>
                <div style={{ flex: '0 1 120px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Method</label>
                  <select className="chat-input" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                    value={testerMethod} onChange={e => setTesterMethod(e.target.value)}>
                    <option value="GET" style={{color: 'black'}}>GET</option>
                    <option value="POST" style={{color: 'black'}}>POST</option>
                    <option value="PUT" style={{color: 'black'}}>PUT</option>
                    <option value="DELETE" style={{color: 'black'}}>DELETE</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Auth Type</label>
                  <select className="chat-input" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', color: 'white' }}
                    value={testerAuthType} onChange={e => setTesterAuthType(e.target.value)}>
                    <option value="Query Parameter" style={{color: 'black'}}>Query Parameter</option>
                    <option value="Bearer Token" style={{color: 'black'}}>Bearer Token</option>
                    <option value="Custom Header" style={{color: 'black'}}>Custom Header</option>
                  </select>
                </div>
                {(testerAuthType === 'Query Parameter' || testerAuthType === 'Custom Header') && (
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>Key Name</label>
                    <input type="text" placeholder={testerAuthType === 'Query Parameter' ? 'access_token' : 'x-api-key'} className="chat-input"
                      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%' }}
                      value={testerAuthKeyName} onChange={e => setTesterAuthKeyName(e.target.value)} />
                  </div>
                )}
              </div>
              {testerMethod !== 'GET' && testerMethod !== 'DELETE' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: '#94a3b8' }}>JSON Body (Optional)</label>
                  <textarea className="chat-input" placeholder='{"key": "value"}'
                    style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', width: '100%', minHeight: '80px', fontFamily: 'monospace' }}
                    value={testerBody} onChange={e => setTesterBody(e.target.value)} />
                </div>
              )}
              <button type="submit" className="send-button" style={{ alignSelf: 'flex-start', padding: '10px 24px' }} disabled={isTesting || !testerApiId}>
                {isTesting ? 'Testing...' : '▶ Run Test'}
              </button>
            </form>
            {testerResponse && (
              <div style={{ marginTop: '24px' }}>
                <h4 style={{ color: '#94a3b8', marginBottom: '8px' }}>Response Output</h4>
                <pre style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid #30363d', overflowX: 'auto', color: '#c9d1d9', fontFamily: 'monospace', fontSize: '0.85rem', maxHeight: '400px', overflowY: 'auto' }}>
                  {testerResponse}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSubTab === 'vault' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-card">
            <h3 className="glass-card-title" style={{color: 'white', marginBottom: '8px'}}>Data Vault</h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '16px' }}>
              Saved items are stored here. Use the "Send To" button to copy them to your clipboard and paste them into any form or prompt.
            </p>
            {vaultItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
                Your vault is empty. Save items from the live feeds to see them here!
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '24px' }}>
                {vaultItems.map(item => (
                  <div key={item.id} style={{ 
                    background: 'rgba(0,0,0,0.4)', 
                    borderRadius: '12px', 
                    border: '1px solid rgba(255,255,255,0.05)',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '1px' }}>{item.source}</span>
                      <button onClick={() => handleDeleteFromVault(item.id)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer' }} title="Delete">🗑️</button>
                    </div>
                    
                    <div style={{ flex: 1, background: 'rgba(0,0,0,0.3)', borderRadius: '6px', padding: '8px', overflow: 'hidden', marginBottom: '16px', fontSize: '0.8rem', color: '#e2e8f0', fontFamily: 'monospace' }}>
                      {item.source === 'Facebook Video' && item.data.message ? (
                        <div style={{ display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {item.data.message}
                        </div>
                      ) : (
                        <div style={{ display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {JSON.stringify(item.data).substring(0, 150)}...
                        </div>
                      )}
                    </div>
                    
                    <button onClick={() => handleSendToClipboard(item)} style={{
                      background: 'var(--accent)',
                      border: 'none',
                      color: 'white',
                      padding: '10px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: 'bold',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px'
                    }}>
                      📤 Send To Clipboard
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
```

*End of BrettDataTab.jsx*

---

# System, Admin & Infrastructure
*6 file(s) in this category*

## AdminSecurityMonitorTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import SHMTelemetryWidget from './SHMTelemetryWidget';


const AUTHORIZED_ADMIN_EMAILS = [
  'footballstar0325@gmail.com',
  'brettstehouwer@gmail.com',
  'theseandaley@gmail.com'
];

export default function AdminSecurityMonitorTab({ currentUser }) {
  const backendUrl = import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
  const userEmail = (currentUser?.email || '').toLowerCase().trim();
  const isAuthorized = AUTHORIZED_ADMIN_EMAILS.includes(userEmail);

  const [activeSubPage, setActiveSubPage] = useState('threat_monitor'); // 'threat_monitor', 'billing_paypal', 'dev_portal', 'tunnel_status'

  // Telemetry State
  const [telemetry, setTelemetry] = useState({
    security_events: [],
    active_ip_bans: [],
    live_stream: []
  });
  
  // Billing Simulator State
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [payProvider, setPayProvider] = useState('paypal');
  const [payTier, setPayTier] = useState('pro');
  const [payAmount, setPayAmount] = useState('29.99');
  const [billingResult, setBillingResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  // Manual IP Ban State
  const [manualIp, setManualIp] = useState('');
  const [banReason, setBanReason] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  // Authorized Auditor Passkey State
  const [testerEmail, setTesterEmail] = useState('');
  const [testerIps, setTesterIps] = useState('127.0.0.1');
  const [testerProfile, setTesterProfile] = useState(null);
  const [isGeneratingTester, setIsGeneratingTester] = useState(false);

  const fetchTelemetry = async () => {
    if (!isAuthorized) return;
    try {
      const res = await fetch(`${getApiBase()}/api/admin/security-telemetry`, {
        headers: { 'X-Admin-Email': userEmail }
      });
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {
      console.error('Failed to fetch admin telemetry:', err);
    }
  };

  const handleGenerateTesterPasskey = async (e) => {
    e.preventDefault();
    if (!testerEmail.trim()) return;
    setIsGeneratingTester(true);
    try {
      const ipsArray = testerIps.split(',').map(ip => ip.trim()).filter(Boolean);
      const res = await fetch(`${getApiBase()}/api/admin/tester-passkey/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Email': userEmail
        },
        body: JSON.stringify({
          tester_email: testerEmail.trim(),
          allowed_ips: ipsArray,
          duration_days: 30
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTesterProfile(data.tester_profile);
      }
    } catch (err) {
      console.error('Failed to generate tester passkey:', err);
    } finally {
      setIsGeneratingTester(false);
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      fetchTelemetry();
      const interval = setInterval(fetchTelemetry, 3000);
      return () => clearInterval(interval);
    }
  }, [isAuthorized]);

  const handleManualBan = async (e) => {
    e.preventDefault();
    if (!manualIp) return;
    try {
      const res = await fetch(`${getApiBase()}/api/admin/ip-ban`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Email': userEmail
        },
        body: JSON.stringify({ ip_address: manualIp, reason: banReason || 'Manual Admin Ban' })
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMsg(`IP ${manualIp} successfully banned.`);
        setManualIp('');
        setBanReason('');
        fetchTelemetry();
      } else {
        setStatusMsg(`Error: ${data.detail?.message || 'Ban failed.'}`);
      }
    } catch (err) {
      setStatusMsg(`Exception: ${err.message}`);
    }
  };

  const handleSimulatePayment = async (e) => {
    e.preventDefault();
    if (!clientName || !clientEmail) return alert('Please enter client name and email.');
    setIsSimulating(true);
    setBillingResult(null);
    try {
      const res = await fetch(`${getApiBase()}/api/v1/billing/simulate-checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_name: clientName,
          email: clientEmail,
          payment_provider: payProvider,
          tier: payTier,
          amount_paid: parseFloat(payAmount) || 29.99
        })
      });
      const data = await res.json();
      if (res.ok) {
        setBillingResult(data);
      } else {
        alert('Payment Simulation Error: ' + JSON.stringify(data));
      }
    } catch (err) {
      alert('Simulation Exception: ' + err.message);
    } finally {
      setIsSimulating(false);
    }
  };

  if (!isAuthorized) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        background: '#0d1117',
        color: '#f85149',
        fontFamily: 'Consolas, monospace',
        padding: '40px'
      }}>
        <div style={{ fontSize: '64px', marginBottom: '20px' }}>🔒</div>
        <h2>ACCESS RESTRICTED: SECURITY & COMMERCIAL SUITE</h2>
        <p style={{ color: '#8b949e', maxWidth: '500px', textAlign: 'center', marginTop: '10px' }}>
          This interface is protected under strict Role-Based Access Control (RBAC). Access is exclusively restricted to verified administrators:
        </p>
        <div style={{ background: '#161b22', padding: '15px 25px', borderRadius: '8px', border: '1px solid #30363d', marginTop: '20px', color: '#58a6ff' }}>
          {AUTHORIZED_ADMIN_EMAILS.map(email => (
            <div key={email}>• {email}</div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#0d1117',
      color: '#c9d1d9',
      fontFamily: 'Consolas, monospace',
      overflow: 'hidden'
    }}>
      {/* Header Bar */}
      <div style={{
        padding: '12px 24px',
        background: '#161b22',
        borderBottom: '1px solid #30363d',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '24px' }}>🛡️</span>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', color: '#58a6ff' }}>ADMIN SECURITY & COMMERCIAL INTERCEPTOR SUITE</h2>
            <span style={{ fontSize: '12px', color: '#7d8590' }}>Active Hardware Monitor • Admin User: {userEmail}</span>
          </div>
        </div>

        {/* Sub-Page Navigation Tabs */}
        <div style={{ display: 'flex', gap: '8px', background: '#0d1117', padding: '4px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <button
            onClick={() => setActiveSubPage('threat_monitor')}
            style={{
              background: activeSubPage === 'threat_monitor' ? '#1f6feb' : 'transparent',
              color: activeSubPage === 'threat_monitor' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            🛡️ Live Threat Stream
          </button>
          <button
            onClick={() => setActiveSubPage('billing_paypal')}
            style={{
              background: activeSubPage === 'billing_paypal' ? '#238636' : 'transparent',
              color: activeSubPage === 'billing_paypal' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            💳 Billing & PayPal Payouts
          </button>
          <button
            onClick={() => setActiveSubPage('dev_portal')}
            style={{
              background: activeSubPage === 'dev_portal' ? '#8957e5' : 'transparent',
              color: activeSubPage === 'dev_portal' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            🌐 Developer API Docs
          </button>
          <button
            onClick={() => setActiveSubPage('tunnel_status')}
            style={{
              background: activeSubPage === 'tunnel_status' ? '#d29922' : 'transparent',
              color: activeSubPage === 'tunnel_status' ? 'white' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            ☁️ Cloudflare Tunnel
          </button>
          <button
            onClick={() => setActiveSubPage('shm_telemetry')}
            style={{
              background: activeSubPage === 'shm_telemetry' ? '#00d2ff' : 'transparent',
              color: activeSubPage === 'shm_telemetry' ? 'black' : '#8b949e',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '12px'
            }}
          >
            ⚡ SHM Telemetry
          </button>
        </div>
      </div>


      {/* Main Content Area rendering Sub-Pages */}
      <div style={{ flex: 1, overflow: 'hidden', padding: '16px' }}>

        {/* SUB-PAGE 1: LIVE THREAT STREAM */}
        {activeSubPage === 'threat_monitor' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflowY: 'auto' }}>
            
            {/* Authorized Security Auditor Passkey Card */}
            <div style={{ background: '#161b22', padding: '20px', borderRadius: '12px', border: '1px solid rgba(56, 189, 248, 0.4)' }}>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🔑 Authorized Security Auditor & Pen Tester Management
              </h3>
              <p style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#8b949e' }}>
                Generate temporary Passkeys and secret authorization rules for authorized security auditors. Automatically bypasses IP bans during testing windows.
              </p>

              <form onSubmit={handleGenerateTesterPasskey} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
                <input
                  type="email"
                  placeholder="Auditor Email (e.g. tester@securityfirm.com)"
                  value={testerEmail}
                  onChange={(e) => setTesterEmail(e.target.value)}
                  required
                  style={{ flex: 1, minWidth: '240px', padding: '10px 14px', borderRadius: '6px', background: '#0d1117', border: '1px solid #30363d', color: '#fff', fontSize: '13px' }}
                />
                <input
                  type="text"
                  placeholder="Allowed IPs (comma separated or 127.0.0.1)"
                  value={testerIps}
                  onChange={(e) => setTesterIps(e.target.value)}
                  style={{ flex: 1, minWidth: '200px', padding: '10px 14px', borderRadius: '6px', background: '#0d1117', border: '1px solid #30363d', color: '#fff', fontSize: '13px' }}
                />
                <button
                  type="submit"
                  disabled={isGeneratingTester}
                  style={{ padding: '10px 20px', background: 'linear-gradient(135deg, #38bdf8, #818cf8)', color: '#000', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px' }}
                >
                  {isGeneratingTester ? 'Generating...' : '⚡ Generate Auditor Passkey'}
                </button>
              </form>

              {testerProfile && (
                <div style={{ background: '#0d1117', padding: '16px', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.3)', fontSize: '13px' }}>
                  <div style={{ color: '#4ade80', fontWeight: 'bold', marginBottom: '8px' }}>✨ Active Auditor Security Profile Generated:</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontFamily: 'monospace' }}>
                    <div><strong>Auditor Email:</strong> <span style={{ color: '#38bdf8' }}>{testerProfile.tester_email}</span></div>
                    <div><strong>Secret Header Name:</strong> <span style={{ color: '#f59e0b' }}>{testerProfile.secret_header_name}</span></div>
                    <div style={{ gridColumn: 'span 2' }}><strong>Secret Header Value:</strong> <code style={{ color: '#a855f7', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{testerProfile.secret_header_value}</code></div>
                    <div style={{ gridColumn: 'span 2' }}><strong>Tester API Passkey:</strong> <code style={{ color: '#4ade80', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>{testerProfile.tester_api_passkey}</code></div>
                    <div style={{ gridColumn: 'span 2', fontSize: '11px', color: '#8b949e' }}>Testing Window: {testerProfile.window_start} to {testerProfile.window_end}</div>
                  </div>
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '16px', minHeight: '400px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflow: 'hidden' }}>
                
                {/* Live Request Interceptor */}
                <div style={{ flex: 1, background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', background: '#21262d', borderBottom: '1px solid #30363d', fontWeight: 'bold', color: '#79c0ff', display: 'flex', justifyContent: 'space-between' }}>
                    <span>📡 LIVE HARDWARE & API INTERACTION STREAM</span>
                    <span>{telemetry.live_stream.length} Events Logged</span>
                  </div>
                  <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {telemetry.live_stream.length === 0 ? (
                      <div style={{ color: '#8b949e', textAlign: 'center', marginTop: '40px' }}>Waiting for incoming tenant requests...</div>
                    ) : (
                      telemetry.live_stream.map((item) => (
                        <div key={item.id} style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: '6px', padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '13px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e' }}>
                            <span>IP: <strong style={{ color: '#f0883e' }}>{item.ip_address}</strong> • Key: {item.key_prefix}</span>
                            <span>{new Date(item.timestamp * 1000).toLocaleTimeString()}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: '#58a6ff', fontWeight: 'bold' }}>{item.endpoint}</span>
                            <span style={{ color: item.status_code === 200 ? '#7ee787' : '#f85149', background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: '4px' }}>
                              HTTP {item.status_code} ({item.response_time_ms} ms)
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Threat Interception Panel */}
                <div style={{ height: '220px', background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '10px 16px', background: '#21262d', borderBottom: '1px solid #30363d', fontWeight: 'bold', color: '#ff7b72' }}>
                    ⚠️ ACTIVE DEFENSE & INJECTION INTERCEPTIONS
                  </div>
                  <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {telemetry.security_events.length === 0 ? (
                      <div style={{ color: '#8b949e', textAlign: 'center', marginTop: '20px' }}>No active threat detections logged. Zero-Trust Shield Operational.</div>
                    ) : (
                      telemetry.security_events.map((ev) => (
                        <div key={ev.id} style={{ background: '#21262d', padding: '8px 12px', borderRadius: '4px', borderLeft: '3px solid #f85149', fontSize: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#ff7b72' }}>
                            <strong>[{ev.event_type}] Severity: {ev.severity}</strong>
                            <span>{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                          </div>
                          <div style={{ color: '#c9d1d9', marginTop: '4px' }}>
                            IP: <code>{ev.ip_address}</code> — {ev.details}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Manual IP Ban */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '16px' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#d2a8ff' }}>🚫 MANUAL IP BAN CONTROLS</h3>
                  <form onSubmit={handleManualBan} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <input
                      type="text"
                      placeholder="Target IP Address"
                      value={manualIp}
                      onChange={(e) => setManualIp(e.target.value)}
                      style={{ background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', fontFamily: 'inherit' }}
                    />
                    <input
                      type="text"
                      placeholder="Ban Reason"
                      value={banReason}
                      onChange={(e) => setBanReason(e.target.value)}
                      style={{ background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', fontFamily: 'inherit' }}
                    />
                    <button type="submit" style={{ background: '#da3633', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
                      EXECUTE IMMEDIATE BAN
                    </button>
                  </form>
                  {statusMsg && <div style={{ marginTop: '10px', fontSize: '12px', color: '#7ee787' }}>{statusMsg}</div>}
                </div>

                <div style={{ flex: 1, background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <div style={{ padding: '10px 16px', background: '#21262d', borderBottom: '1px solid #30363d', fontWeight: 'bold', color: '#f0883e' }}>
                    🛑 BLACKLISTED IP ADDRESSES ({telemetry.active_ip_bans.length})
                  </div>
                  <div style={{ flex: 1, padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {telemetry.active_ip_bans.map((ban) => (
                      <div key={ban.ip_address} style={{ background: '#0d1117', padding: '8px 12px', borderRadius: '4px', border: '1px solid #30363d', fontSize: '12px' }}>
                        <div style={{ color: '#ff7b72', fontWeight: 'bold' }}>{ban.ip_address}</div>
                        <div style={{ color: '#8b949e', fontSize: '11px', marginTop: '2px' }}>{ban.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SUB-PAGE 2: Billing & PayPal Provisioner */}
        {activeSubPage === 'billing_paypal' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', height: '100%', overflowY: 'auto' }}>
            
            {/* Payment & Key Provisioner Simulator */}
            <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px' }}>
              <h3 style={{ margin: '0 0 16px 0', color: '#7ee787', display: 'flex', alignItems: 'center', gap: '8px' }}>
                💳 PAYPAL & STRIPE KEY PROVISIONER SIMULATOR
              </h3>
              <p style={{ color: '#8b949e', fontSize: '13px', lineHeight: '1.5' }}>
                Test immediate API key issuance and income credit triggers when clients rent your hardware or purchase tokens. Deposits directly to your PayPal account balance upon live checkout.
              </p>
              
              <form onSubmit={handleSimulatePayment} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#7d8590' }}>Client Name / Company</label>
                  <input
                    type="text"
                    placeholder="e.g. Acme Corp AI Lab"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#7d8590' }}>Client PayPal Email</label>
                  <input
                    type="email"
                    placeholder="client@paypal.com"
                    value={clientEmail}
                    onChange={(e) => setClientEmail(e.target.value)}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '12px', color: '#7d8590' }}>Payout Channel</label>
                    <select
                      value={payProvider}
                      onChange={(e) => setPayProvider(e.target.value)}
                      style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px', borderRadius: '6px', marginTop: '4px' }}
                    >
                      <option value="paypal">PayPal Payout</option>
                      <option value="stripe">Stripe Payout</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: '#7d8590' }}>Hardware Tier</label>
                    <select
                      value={payTier}
                      onChange={(e) => setPayTier(e.target.value)}
                      style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px', borderRadius: '6px', marginTop: '4px' }}
                    >
                      <option value="starter">Starter ($9.99/mo)</option>
                      <option value="pro">Pro ($29.99/mo)</option>
                      <option value="enterprise">Enterprise ($149.99/mo)</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', color: '#7d8590' }}>Amount ($ USD)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={payAmount}
                      onChange={(e) => setPayAmount(e.target.value)}
                      style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: 'white', padding: '8px', borderRadius: '6px', marginTop: '4px' }}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSimulating}
                  style={{
                    background: '#238636',
                    color: 'white',
                    border: 'none',
                    padding: '10px 20px',
                    borderRadius: '6px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    marginTop: '8px'
                  }}
                >
                  {isSimulating ? 'Processing Payout...' : 'SIMULATE PAYPAL CHECKOUT & ISSUE KEY'}
                </button>
              </form>

              {billingResult && (
                <div style={{ marginTop: '20px', background: '#0d1117', padding: '16px', borderRadius: '6px', border: '1px solid #7ee787' }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#7ee787' }}>🎉 PAYOUT RECEIVED & KEY PROVISIONED</h4>
                  <div style={{ fontSize: '12px', color: '#c9d1d9', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div><strong>Raw Key Issued:</strong> <code style={{ color: '#58a6ff' }}>{billingResult.api_key_details.raw_key}</code></div>
                    <div><strong>Tier Allocated:</strong> {billingResult.api_key_details.tier} ({billingResult.api_key_details.daily_quota} units/day)</div>
                    <div><strong>Client:</strong> {billingResult.api_key_details.client_name}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Payout Credentials Status */}
            <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px' }}>
              <h3 style={{ margin: '0 0 16px 0', color: '#58a6ff' }}>⚙️ LIVE PAYOUT CONFIGURATION</h3>
              <p style={{ color: '#8b949e', fontSize: '13px', lineHeight: '1.5' }}>
                Your live PayPal and Stripe credentials are safely stored in your local <code>C:\AI-BS\.env</code> environment file.
              </p>
              
              <div style={{ background: '#0d1117', padding: '14px', borderRadius: '6px', border: '1px solid #30363d', fontSize: '12px', marginTop: '14px' }}>
                <div style={{ color: '#79c0ff', fontWeight: 'bold', marginBottom: '8px' }}>Active Local Environment (.env):</div>
                <pre style={{ margin: 0, color: '#8b949e' }}>
{`PAYPAL_CLIENT_ID=BAAmicjyvk5iBoTJTebv5fi9wSGXdv3JeENHw31HNcum6Jtv1dWKK5PxfnBdFCESVmKz25GSnCkjwOvkj4
PAYPAL_PRIMARY_EMAIL=footballstar0325@gmail.com
PAYPAL_WEBHOOK_ID=webhook_paypal_v6_active_2026
STRIPE_WEBHOOK_SECRET=whsec_live_active_2026
AIBS_HMAC_SALT=AI_BS_SECURE_HMAC_SALT_2026`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* SUB-PAGE 3: Developer Portal & API Docs */}
        {activeSubPage === 'dev_portal' && (
          <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px', height: '100%', overflowY: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#8957e5' }}>🌐 COMMERCIAL DEVELOPER PORTAL & API SPECS</h3>
            <p style={{ color: '#8b949e', fontSize: '13px' }}>
              Public OpenAI-compliant REST endpoints for clients renting your RTX 4090 GPU hardware.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
              <div style={{ background: '#0d1117', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
                <h4 style={{ color: '#58a6ff', margin: '0 0 8px 0' }}>POST /v1/images/generations</h4>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>GPU-accelerated ComfyUI image synthesis.</div>
                <pre style={{ background: '#161b22', padding: '10px', borderRadius: '4px', fontSize: '11px', color: '#7ee787', marginTop: '8px' }}>
{`curl -X POST http://localhost:8000/v1/images/generations \\
  -H "Authorization: Bearer sk_aibs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "futuristic matrix room"}'`}
                </pre>
              </div>

              <div style={{ background: '#0d1117', padding: '14px', borderRadius: '6px', border: '1px solid #30363d' }}>
                <h4 style={{ color: '#d2a8ff', margin: '0 0 8px 0' }}>POST /v1/chat/completions</h4>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>Stehouwer LLM / Ollama text completion.</div>
                <pre style={{ background: '#161b22', padding: '10px', borderRadius: '4px', fontSize: '11px', color: '#7ee787', marginTop: '8px' }}>
{`curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Authorization: Bearer sk_aibs_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'`}
                </pre>
              </div>
            </div>
          </div>
        )}

        {/* SUB-PAGE 4: Cloudflare Tunnel Status */}
        {activeSubPage === 'tunnel_status' && (
          <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px', height: '100%', overflowY: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#d29922' }}>☁️ CLOUDFLARE ZERO-TRUST TUNNEL STATUS</h3>
            <p style={{ color: '#8b949e', fontSize: '13px' }}>
              Exposes <code>http://localhost:8000/v1</code> securely to the public internet without opening home router ports.
            </p>
            <div style={{ background: '#0d1117', padding: '16px', borderRadius: '6px', border: '1px solid #30363d', marginTop: '16px' }}>
              <div style={{ color: '#7ee787', fontWeight: 'bold', fontSize: '14px' }}>● Local Gateway Port: 8000 (Active)</div>
              <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '8px' }}>
                Run the quick tunnel command to launch your free public HTTPS endpoint:
              </div>
              <pre style={{ background: '#161b22', padding: '10px', borderRadius: '4px', color: '#58a6ff', marginTop: '8px' }}>
cloudflared tunnel --url http://localhost:8000
              </pre>
            </div>
          </div>
        )}

        {/* SUB-PAGE 5: Polyglot SHM Telemetry */}
        {activeSubPage === 'shm_telemetry' && (
          <div style={{ background: '#161b22', borderRadius: '8px', border: '1px solid #30363d', padding: '20px', height: '100%', overflowY: 'auto' }}>
            <h3 style={{ margin: '0 0 12px 0', color: '#00d2ff' }}>⚡ LOW-LEVEL POLYGLOT SHM BUS TELEMETRY</h3>
            <p style={{ color: '#8b949e', fontSize: '13px' }}>
              Real-time multiplexed Shared Memory ring buffer (0x0001 - 0x0004) streamed directly from <code>Local\AI_BS_IPC_SHM_RING</code> over WebSockets.
            </p>
            <SHMTelemetryWidget />
          </div>
        )}

      </div>
    </div>
  );
}

```

*End of AdminSecurityMonitorTab.jsx*

---

## CommandCenterTab.jsx
```jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAppStore } from './useAppStore';
import './CommandCenterTab.css';

// ---------------------------------------------------------------------------
// Daemon status colours
// ---------------------------------------------------------------------------
const STATUS_STYLES = {
  running: { dot: '#4ade80', label: 'RUNNING',  bg: 'rgba(74,222,128,0.08)',  border: 'rgba(74,222,128,0.25)' },
  stopped: { dot: '#f87171', label: 'STOPPED',  bg: 'rgba(248,113,113,0.08)', border: 'rgba(248,113,113,0.25)' },
  loading: { dot: '#fbbf24', label: 'CHECKING', bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.25)' },
};

// Friendly display names for each daemon key
const DAEMON_LABELS = {
  trainer_daemon: { icon: '📼', name: 'Trainer Daemon',  desc: 'Tails agent transcripts → structured JSONL logs' },
  memory_daemon:  { icon: '🧠', name: 'Memory Daemon',   desc: 'Vectorizes session history → ChromaDB embeddings' },
  chroma_daemon:  { icon: '🗄️', name: 'ChromaDB Server', desc: 'Serves Stehouwer Vector Memory on port 8001' },
};

function DaemonSupervisor({ backendUrl }) {
  const [daemons, setDaemons]       = useState({});
  const [polling, setPolling]       = useState(true);
  const [restarting, setRestarting] = useState({});
  const [lastFetch, setLastFetch]   = useState(null);
  const [fetchError, setFetchError] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${backendUrl}/api/health`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDaemons(data.daemons || {});
      setLastFetch(new Date());
      setFetchError(null);
    } catch (err) {
      setFetchError(err.message);
    }
  }, [backendUrl]);

  // Poll every 5 seconds when polling is enabled
  useEffect(() => {
    fetchStatus();
    if (!polling) return;
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, [fetchStatus, polling]);

  const handleRestart = async (name) => {
    setRestarting(prev => ({ ...prev, [name]: true }));
    try {
      const res = await fetch(`${backendUrl}/api/daemons/${name}/restart`, {
        method: 'POST',
        signal: AbortSignal.timeout(10000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // Give the backend a moment then re-poll
      setTimeout(fetchStatus, 1500);
    } catch (err) {
      alert(`Restart failed for ${name}: ${err.message}`);
    } finally {
      setRestarting(prev => ({ ...prev, [name]: false }));
    }
  };

  const daemonEntries = Object.entries(daemons);

  return (
    <div className="daemon-panel">
      {/* Panel header */}
      <div className="daemon-header">
        <div>
          <h3 className="daemon-title">
            🛰️ DAEMON SUPERVISOR
          </h3>
          <p className="daemon-subtitle">
            Live process health — auto-refreshes every 5s
            {lastFetch && ` · last sync ${lastFetch.toLocaleTimeString()}`}
          </p>
        </div>
        <div className="daemon-actions">
          {fetchError && (
            <span className="daemon-error">
              ⚠ {fetchError}
            </span>
          )}
          <button
            onClick={() => setPolling(p => !p)}
            className={`daemon-btn-pause ${polling ? 'active' : 'inactive'}`}
          >
            {polling ? '⏸ Pause' : '▶ Resume'}
          </button>
          <button
            onClick={fetchStatus}
            className="daemon-btn-refresh"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Daemon rows */}
      {daemonEntries.length === 0 ? (
        <div className="daemon-loading">
          {fetchError ? 'Cannot reach backend — start AI_BS_Backend.py first.' : 'Loading daemon status…'}
        </div>
      ) : (
        <div className="daemon-list">
          {daemonEntries.map(([name, info]) => {
            const state  = info.running ? 'running' : 'stopped';
            const style  = STATUS_STYLES[state];
            const meta   = DAEMON_LABELS[name] ?? { icon: '⚙️', name, desc: '' };
            const isRestarting = restarting[name];

            return (
              <div key={name} className="daemon-row" style={{
                background: style.bg,
                border: `1px solid ${style.border}`
              }}>
                {/* Left: icon + name + desc */}
                <div className="daemon-row-left">
                  <span className="daemon-icon">{meta.icon}</span>
                  <div style={{ minWidth: 0 }}>
                    <div className="daemon-name">{meta.name}</div>
                    <div className="daemon-desc">{meta.desc}</div>
                  </div>
                </div>

                {/* Right: status badge + PID + restart button */}
                <div className="daemon-row-right">
                  {info.pid && (
                    <span className="daemon-pid">PID {info.pid}</span>
                  )}
                  {info.restart_count > 0 && (
                    <span className="daemon-restarts" title="Auto-restart count">
                      ↺ {info.restart_count}
                    </span>
                  )}
                  <span className="daemon-status-badge" style={{
                    color: style.dot,
                    border: `1px solid ${style.border}`,
                  }}>
                    <span className="daemon-dot" style={{
                      background: style.dot,
                      boxShadow: info.running ? `0 0 6px ${style.dot}` : 'none',
                      animation: info.running ? 'pulse-dot 2s infinite' : 'none',
                    }} />
                    {style.label}
                  </span>
                  <button
                    onClick={() => handleRestart(name)}
                    disabled={isRestarting}
                    title={`Restart ${meta.name}`}
                    className={`daemon-btn-restart ${isRestarting ? 'restarting' : 'idle'}`}
                  >
                    {isRestarting ? '…' : '⟳ Restart'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const ORCHESTRATOR_COMMANDS = [
  {
    title: '🧠 Full System Audit',
    description: 'Run a comprehensive audit across all subsystems — code quality, telemetry, agent logs, and memory health.',
    prompt: 'Perform a full system audit: check all Python modules for syntax errors, review the telemetry checkpoint database for anomalies, summarize agent transcript logs, and report findings.',
  },
  {
    title: '📦 Auto-Package Project',
    description: 'Bundle the current workspace into a distributable archive with dependencies.',
    prompt: 'Package the AI-BS Matrix project: freeze Python dependencies to requirements.txt, run npm build in the frontend, and create a zip archive of the distributable files.',
  },
  {
    title: '🌱 Vertical Farm Optimizer',
    description: 'Analyze Noco telemetry data and generate optimization recommendations for the aeroponic system.',
    prompt: 'Analyze the Noco telemetry data from the last session. Identify CO2, temperature, and MFC output trends. Recommend parameter adjustments to optimize yield.',
  },
  {
    title: '🎵 Audio Production Assistant',
    description: 'Generate a structured audio production workflow for a new track.',
    prompt: 'Create a detailed audio production workflow for an electronic track: BPM selection, key and scale, layering strategy, mix structure, and mastering checklist.',
  },
  {
    title: '🐛 Codebase Bug Sweep',
    description: 'Scan all Python files for common bugs, anti-patterns, and security issues.',
    prompt: 'Scan all Python files in the project for: syntax errors, undefined variable references, insecure subprocess calls, hardcoded secrets, and missing error handling. Report by file.',
  },
  {
    title: '📈 Lead Generation Strategy',
    description: 'Generate a West Michigan B2B lead acquisition strategy using the heuristics engine.',
    prompt: 'Generate a 30-day B2B lead acquisition strategy targeting West Michigan small businesses. Focus on: industries with weak digital presence, outreach templates, follow-up cadence, and value propositions.',
  },
];

export default function CommandCenterTab({ backendUrl: propBackendUrl }) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const setChatMessages = useAppStore(state => state.setChatMessages);
  const setFooterInput = useAppStore(state => state.setFooterInput);
  const activeAgents = useAppStore(state => state.activeAgents);
  const setActiveAgents = useAppStore(state => state.setActiveAgents);
  const telegramToken = useAppStore(state => state.telegramToken);
  const setTelegramToken = useAppStore(state => state.setTelegramToken);
  const safetySkipPermissions = useAppStore(state => state.safetySkipPermissions);
  const setSafetySkipPermissions = useAppStore(state => state.setSafetySkipPermissions);
  const customLoopTime = useAppStore(state => state.customLoopTime);
  const setCustomLoopTime = useAppStore(state => state.setCustomLoopTime);
  const customLoopTask = useAppStore(state => state.customLoopTask);
  const setCustomLoopTask = useAppStore(state => state.setCustomLoopTask);
  const pullModelInput = useAppStore(state => state.pullModelInput);
  const setPullModelInput = useAppStore(state => state.setPullModelInput);
  const pullingStatus = useAppStore(state => state.pullingStatus);
  const setPullingStatus = useAppStore(state => state.setPullingStatus);
  const ssdRamPath = useAppStore(state => state.ssdRamPath);
  const setSsdRamPath = useAppStore(state => state.setSsdRamPath);
  const ssdRamSize = useAppStore(state => state.ssdRamSize);
  const setSsdRamSize = useAppStore(state => state.setSsdRamSize);
  const ssdRamCount = useAppStore(state => state.ssdRamCount);
  const setSsdRamCount = useAppStore(state => state.setSsdRamCount);
  const isSsdLoading = useAppStore(state => state.isSsdLoading);
  const setIsSsdLoading = useAppStore(state => state.setIsSsdLoading);

  // Prefer the explicit prop (passed from App.jsx); fall back to context value
  const backendUrl = propBackendUrl || BACKEND_URL;

  const [localSsdPath, setLocalSsdPath] = useState('');

  const handleLaunchAgent = async (agentType, extraArgs = '') => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/agents/launch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: agentType, args: extraArgs }),
      });
      const data = await res.json();
      if (data.pid) {
        setActiveAgents(prev => [...prev.filter(a => a.agent !== agentType), { agent: agentType, pid: data.pid, is_running: true }]);
      }
    } catch (err) {
      alert(`Failed to launch agent: ${err.message}`);
    }
  };

  const handleKillAgent = async (agentType) => {
    try {
      await fetch(`${BACKEND_URL}/api/agents/kill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: agentType }),
      });
      setActiveAgents(prev => prev.map(a => a.agent === agentType ? { ...a, is_running: false } : a));
    } catch (err) {
      alert(`Failed to kill agent: ${err.message}`);
    }
  };

  const handlePullModel = async () => {
    const model = pullModelInput.trim();
    if (!model) return;
    setPullingStatus(prev => ({ ...prev, [model]: { status: 'Downloading', progress: 0, log: 'Connecting...' } }));
    try {
      const res = await fetch(`${BACKEND_URL}/api/models/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      const data = await res.json();
      setPullingStatus(prev => ({ ...prev, [model]: { status: data.status || 'Complete', progress: 100, log: data.message || 'Done.' } }));
      setTimeout(() => setPullingStatus(prev => { const n = { ...prev }; delete n[model]; return n; }), 5000);
    } catch (err) {
      setPullingStatus(prev => ({ ...prev, [model]: { status: 'Error', progress: 0, log: err.message } }));
    }
    setPullModelInput('');
  };

  const updateSsdSettings = async (path) => {
    setIsSsdLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/ssd-ram/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      const data = await res.json();
      setSsdRamPath(data.path || path);
      setSsdRamSize(data.size_bytes || 0);
      setSsdRamCount(data.turn_count || 0);
    } catch (err) {
      alert(`SSD RAM config failed: ${err.message}`);
    } finally {
      setIsSsdLoading(false);
    }
  };

  const wipeSsdRam = async () => {
    if (!confirm('Wipe all SSD RAM cache? This cannot be undone.')) return;
    setIsSsdLoading(true);
    try {
      await fetch(`${BACKEND_URL}/api/ssd-ram/wipe`, { method: 'POST' });
      setSsdRamSize(0);
      setSsdRamCount(0);
    } catch (err) {
      alert(`Wipe failed: ${err.message}`);
    } finally {
      setIsSsdLoading(false);
    }
  };

  return (
    <div className="cc-container">


      {/* ── DAEMON SUPERVISOR ── live process health panel */}
      <DaemonSupervisor backendUrl={backendUrl} />

      <h2 className="cc-header-title">Orchestrator Command Library & Agentic Manager</h2>
      <p className="cc-header-desc">
        Manage background agent daemons, pull HuggingFace/Ollama models, and execute pre-engineered agentic workflows.
      </p>

      {/* TOP SECTIONS */}
      <div className="top-sections-grid">

        {/* AGENT LAUNCHER */}
        <div className="agent-launcher-panel glass-panel">
          <h3 className="agent-launcher-title">⚡ Local Agent Launcher</h3>

          <div className="launcher-section">
            <h4 className="launcher-h4">VS Code IDE Synchronization</h4>
            <p className="launcher-p">Expose local models to VS Code Copilot Chat backend for real-time coding alignment.</p>
            <button onClick={() => handleLaunchAgent('vscode')} className="btn-blue">
              Launch VS Code Sync
            </button>
          </div>

          <div className="launcher-section">
            <h4 className="launcher-h4">Autonomous Background Loop</h4>
            <p className="launcher-p">Launch a background instance to recursively review code or logs.</p>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
              <select value={customLoopTime} onChange={(e) => setCustomLoopTime(e.target.value)} className="input-dark">
                <option value="15m">Every 15m</option>
                <option value="30m">Every 30m</option>
                <option value="1h">Every 1h</option>
                <option value="4h">Every 4h</option>
              </select>
              <input type="text" value={customLoopTask} onChange={(e) => setCustomLoopTask(e.target.value)} placeholder="Task description..." className="input-dark" style={{ flexGrow: 1 }} />
            </div>
            <button onClick={() => handleLaunchAgent('claude', `/loop ${customLoopTime} ${customLoopTask}`)} className="btn-purple">
              Start Autonomous Loop
            </button>
          </div>

          <div className="launcher-section">
            <h4 className="launcher-h4">Remote Telegram Bot Bridge</h4>
            <p className="launcher-p">Bind Claude Code agent to Telegram for remote mobile control.</p>
            <input type="password" value={telegramToken} onChange={(e) => setTelegramToken(e.target.value)} placeholder="Telegram Bot Token..." className="input-dark" style={{ width: '100%', marginBottom: '12px' }} />
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
              <input type="checkbox" id="safety-toggle" checked={safetySkipPermissions} onChange={(e) => setSafetySkipPermissions(e.target.checked)} style={{ marginRight: '8px' }} />
              <label htmlFor="safety-toggle" style={{ fontSize: '0.8rem', color: '#ccc', cursor: 'pointer' }}>Dangerously Skip Permissions</label>
            </div>
            {safetySkipPermissions && (
              <div style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', padding: '10px', borderRadius: '6px', fontSize: '0.75rem', marginBottom: '16px', border: '1px solid rgba(239,68,68,0.2)' }}>
                ⚠️ <strong>WARNING:</strong> This bypasses remote authorization. Keep disabled for safety.
              </div>
            )}
            <button
              onClick={() => {
                if (!telegramToken.trim()) return alert('Enter your Telegram Bot Token first.');
                handleLaunchAgent('claude', `--channels plugin:telegram@claude-plugins-official --token ${telegramToken} ${safetySkipPermissions ? '--dangerously-skip-permissions' : ''}`);
              }}
              className="btn-green"
            >Launch Telegram Bridge</button>
          </div>
        </div>

        {/* MODEL REGISTRY + ACTIVE PROCESSES */}
        <div className="model-registry-col">
          <div className="registry-panel glass-panel">
            <h3 className="registry-title">📥 Model Registry & HF Ingestion</h3>
            <p className="launcher-p">Pull GGUF models from HuggingFace or ingest Ollama models to maximize RTX 4090 VRAM.</p>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
              <input type="text" value={pullModelInput} onChange={(e) => setPullModelInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handlePullModel()} placeholder="e.g. gemma4:12b-it-qat or hf.co/QuantFactory/..." className="input-dark" style={{ flexGrow: 1 }} />
              <button onClick={handlePullModel} className="btn-blue">Pull</button>
            </div>
            {Object.keys(pullingStatus).length > 0 && (
              <div>
                {Object.entries(pullingStatus).map(([model, info]) => (
                  <div key={model} style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#fff', marginBottom: '6px' }}>
                      <span style={{ fontFamily: 'monospace' }}>{model}</span>
                      <span style={{ color: '#38bdf8' }}>{info.status} ({info.progress}%)</span>
                    </div>
                    <div className="pull-progress-bar">
                      <div className="pull-progress-fill" style={{ width: `${info.progress}%` }} />
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '4px', fontFamily: 'monospace' }}>{info.log}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="registry-panel glass-panel" style={{ flexGrow: 1 }}>
            <h3 className="active-sessions-title">🤖 Active Background Sessions</h3>
            {activeAgents.filter(a => a.is_running).length === 0 ? (
              <div className="session-empty">No active background agent sessions.</div>
            ) : (
              activeAgents.filter(a => a.is_running).map(agent => (
                <div key={agent.agent} className="session-row">
                  <div>
                    <div className="session-name">{agent.agent.toUpperCase()} Sync Daemon</div>
                    <div className="session-meta">PID: {agent.pid} | ACTIVE</div>
                  </div>
                  <button onClick={() => handleKillAgent(agent.agent)} className="btn-red-outline">
                    Terminate
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* SSD VIRTUAL RAM */}
      <div className="ssd-panel glass-panel">
        <h3 className="ssd-title">💾 SSD Virtual RAM — Context Memory</h3>
        <p className="launcher-p" style={{ marginBottom: '24px' }}>Long-term conversation turns offloaded to local SSD and indexed into the vector database.</p>
        <div className="ssd-grid">
          {[
            { label: 'Storage Path', value: ssdRamPath || '—', mono: true },
            { label: 'Cache Size', value: `${(ssdRamSize / 1024).toFixed(1)} KB` },
            { label: 'Archived Turns', value: `${ssdRamCount} turn pairs` },
            { label: 'Tokenizer', value: 'Stehouwer LLM v2' },
          ].map((item, i) => (
            <div key={i} className="ssd-item">
              <div className="ssd-label">{item.label}</div>
              <div className="ssd-val" style={{ fontFamily: item.mono ? 'monospace' : 'inherit' }}>{item.value}</div>
            </div>
          ))}
        </div>
        <div className="ssd-actions">
          <input type="text" value={localSsdPath} onChange={(e) => setLocalSsdPath(e.target.value)} placeholder={ssdRamPath || 'Enter SSD path (e.g. D:\\AI_RAM_Cache)...'} className="input-dark" style={{ flexGrow: 1, fontFamily: 'monospace', minWidth: '240px' }} />
          <button onClick={() => { const p = localSsdPath.trim(); if (!p) return alert('Enter a valid path first.'); updateSsdSettings(p); setLocalSsdPath(''); }} disabled={isSsdLoading} className="btn-purple-save" style={{ opacity: isSsdLoading ? 0.6 : 1, cursor: isSsdLoading ? 'not-allowed' : 'pointer' }}>
            {isSsdLoading ? 'Saving...' : '💾 Set Path'}
          </button>
          <button onClick={wipeSsdRam} disabled={isSsdLoading} className="btn-red-wipe" style={{ opacity: isSsdLoading ? 0.6 : 1, cursor: isSsdLoading ? 'not-allowed' : 'pointer' }}>
            🗑️ Wipe Cache
          </button>
        </div>
      </div>

      {/* ORCHESTRATOR COMMAND LIBRARY */}
      <h3 className="cmd-lib-title">🧠 Orchestrator Command Library</h3>
      <div className="cmd-grid">
        {ORCHESTRATOR_COMMANDS.map((cmd, idx) => (
          <div key={idx} className="cmd-card glass-panel">
            <h4 className="cmd-title">{cmd.title}</h4>
            <p className="cmd-desc">{cmd.description}</p>
            <div className="cmd-prompt">
              {cmd.prompt}
            </div>
            <button
              onClick={() => {
                setChatMessages(prev => [...prev, { role: 'user', content: cmd.prompt }]);
                // Trigger the chat floating panel open
                setFooterInput('');
              }}
              className="btn-green"
              style={{ width: '100%', padding: '12px', borderRadius: '8px' }}
            >
              Send to AI Chat ➤
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

*End of CommandCenterTab.jsx*

---

## DeveloperWorkspaceTab.jsx
```jsx
import React, { useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import TerminalPanel from './TerminalPanel';
import VisualScriptingTab from './VisualScriptingTab';
import TrainerLogViewer from './TrainerLogViewer';
import { useAppStore } from './useAppStore';
import './DeveloperWorkspaceTab.css';

function renderDevChatMessage(content) {
  return content;
}

export default function DeveloperWorkspaceTab() {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL);
  const devChatInput = useAppStore(state => state.devChatInput);
  const setDevChatInput = useAppStore(state => state.setDevChatInput);
  const devChatMessages = useAppStore(state => state.devChatMessages);
  const setDevChatMessages = useAppStore(state => state.setDevChatMessages);
  const devLeftTab = useAppStore(state => state.devLeftTab);
  const setDevLeftTab = useAppStore(state => state.setDevLeftTab);
  const devBottomTab = useAppStore(state => state.devBottomTab);
  const setDevBottomTab = useAppStore(state => state.setDevBottomTab);
  const devMode = useAppStore(state => state.devMode);
  const setDevMode = useAppStore(state => state.setDevMode);
  const devFileName = useAppStore(state => state.devFileName);
  const setDevFileName = useAppStore(state => state.setDevFileName);
  const devCodeInput = useAppStore(state => state.devCodeInput);
  const setDevCodeInput = useAppStore(state => state.setDevCodeInput);
  const devCodeOutput = useAppStore(state => state.devCodeOutput);
  const setDevCodeOutput = useAppStore(state => state.setDevCodeOutput);
  const devCodeType = useAppStore(state => state.devCodeType);
  const setDevCodeType = useAppStore(state => state.setDevCodeType);
  const gitStatus = useAppStore(state => state.gitStatus);
  const setGitStatus = useAppStore(state => state.setGitStatus);
  const systemGitStatus = useAppStore(state => state.systemGitStatus);
  const setSystemGitStatus = useAppStore(state => state.setSystemGitStatus);
  const isExecutingCode = useAppStore(state => state.isExecutingCode);
  const setIsExecutingCode = useAppStore(state => state.setIsExecutingCode);
  const monacoRef = useAppStore(state => state.monacoRef);
  const selectedModel = useAppStore(state => state.selectedModel);

  const [isDevChatLoading, setIsDevChatLoading] = useState(false);
  const [isSavingFile, setIsSavingFile] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const handleEditorDidMount = useCallback((editor) => {
    if (monacoRef) monacoRef.current = editor;
  }, [monacoRef]);

  const handleDevChatSubmit = async () => {
    const text = devChatInput.trim();
    if (!text || isDevChatLoading) return;

    const userMsg = { role: 'user', content: text };
    setDevChatMessages(prev => [...prev, userMsg]);
    setDevChatInput('');
    setIsDevChatLoading(true);

    const contextPrompt = devCodeInput
      ? `You are a coding assistant. The user currently has this code open (${devCodeType}):\n\`\`\`${devCodeType}\n${devCodeInput}\n\`\`\`\n\nUser request: ${text}`
      : text;

    try {
      const res = await fetch(`${BACKEND_URL}/v1/ide/reason-and-code`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': 'Bearer sk_aibs_dev_master_key_2026'
        },
        body: JSON.stringify({ 
          user_prompt: text, 
          code_context: devCodeInput,
          file_name: devFileName || 'main.py',
          language: devCodeType || 'python',
          model: selectedModel || 'qwen2.5-coder:latest' 
        }),
      });
      const data = await res.json();
      const responseText = data.response || data.message || 'No response generated.';
      
      let headerText = '';
      if (data.refinement_quality_score) {
        headerText = `🧠 [Self-Solving Verified: ${data.refinement_quality_score}% Quality | Model: ${data.model_used}]\n\n`;
      }
      
      const fullResponse = headerText + responseText;
      setDevChatMessages(prev => [...prev, { role: 'assistant', content: fullResponse }]);
      
      const codeMatch = responseText?.match(/```(?:\w+)?\n([\s\S]+?)```/);
      if (codeMatch) {
        setDevCodeInput(codeMatch[1].trim());
      }
    } catch (err) {
      setDevChatMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${err.message}` }]);
    } finally {
      setIsDevChatLoading(false);
    }
  };

  const handleSaveFile = async () => {
    if (!devFileName.trim()) return;
    setIsSavingFile(true);
    setSaveMessage('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/save-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: devFileName, content: devCodeInput, language: devCodeType }),
      });
      const data = await res.json();
      setSaveMessage(data.status === 'success' ? `✅ Saved to ${data.path}` : `❌ ${data.detail || 'Save failed'}`);
    } catch (err) {
      setSaveMessage(`❌ ${err.message}`);
    } finally {
      setIsSavingFile(false);
      setTimeout(() => setSaveMessage(''), 4000);
    }
  };

  const handleExecuteCode = async () => {
    if (!devCodeInput.trim() || isExecutingCode) return;
    setIsExecutingCode(true);
    setDevCodeOutput([{ type: 'system', content: `Running ${devCodeType}...` }]);
    try {
      const res = await fetch(`${BACKEND_URL}/api/execute-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: devCodeInput, language: devCodeType }),
      });
      const data = await res.json();
      const steps = [];
      if (data.stdout) steps.push({ type: 'stdout', content: data.stdout });
      if (data.stderr) steps.push({ type: 'error', content: data.stderr });
      if (data.error) steps.push({ type: 'error', content: data.error });
      if (!data.stdout && !data.stderr && !data.error) steps.push({ type: 'complete', content: 'Execution complete — no output.' });
      setDevCodeOutput(steps);
    } catch (err) {
      setDevCodeOutput([{ type: 'error', content: err.message }]);
    } finally {
      setIsExecutingCode(false);
    }
  };

  return (
    <div className="dev-workspace-grid">

      {/* DEV CHAT PANEL (LEFT) */}
      <div className="dev-chat-panel glass-panel">
        <div className="dev-tabs-row">
          <button
            className={`dev-tab-btn ${devLeftTab === 'chat' ? 'dev-tab-btn-active' : 'dev-tab-btn-inactive'}`}
            onClick={() => setDevLeftTab('chat')}
          >🤖 Assistant</button>
          <button
            className={`dev-tab-btn ${devLeftTab === 'git' ? 'dev-tab-btn-active' : 'dev-tab-btn-inactive'}`}
            onClick={() => {
              setDevLeftTab('git');
              fetch(`${BACKEND_URL}/api/git/status`).then(r => r.json()).then(d => setGitStatus(d.status || d.error || 'Clean working tree.'));
              fetch(`${BACKEND_URL}/api/git/system/status`).then(r => r.json()).then(d => setSystemGitStatus(d.status || d.error || 'Clean working tree.'));
            }}
          >🌿 Source Control</button>
          <button
            className={`dev-tab-btn ${devLeftTab === 'trainer' ? 'dev-tab-btn-active' : 'dev-tab-btn-inactive'}`}
            onClick={() => setDevLeftTab('trainer')}
          >🧠 Trainer</button>
        </div>

        {devLeftTab === 'chat' ? (
          <>
            <div className="message-feed">
              {devChatMessages.length === 0 && (
                <div style={{ color: '#555', fontSize: '0.85rem', marginTop: '20px', textAlign: 'center' }}>
                  Ask the Dev Assistant to write, fix, explain, or run code.<br />
                  Your current editor code is sent as context.
                </div>
              )}
              {devChatMessages.map((msg, idx) => (
                <div key={idx} className={`chat-message ${msg.role}`}>
                  <div className={`chat-avatar ${msg.role}`}>
                    {msg.role === 'user' ? 'B' : 'AI'}
                  </div>
                  <div className={`chat-bubble ${msg.role}`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isDevChatLoading && (
                <div style={{ color: '#38bdf8', fontSize: '0.82rem', fontStyle: 'italic', paddingLeft: '40px' }}>Working...</div>
              )}
            </div>
            <div className="chat-input-area">
              <div className="chat-input-row">
                <textarea
                  className="chat-input"
                  placeholder="Ask the Dev Assistant to write, fix, or run code..."
                  value={devChatInput}
                  onChange={(e) => setDevChatInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleDevChatSubmit(); } }}
                />
                <button
                  className="send-button"
                  onClick={handleDevChatSubmit}
                  disabled={isDevChatLoading || !devChatInput.trim()}
                >Send</button>
              </div>
            </div>
          </>
        ) : devLeftTab === 'git' ? (
          <div className="git-panel">
            <h4 className="git-header">AI-BS System</h4>
            <pre className="git-output">{systemGitStatus}</pre>
            <div style={{ marginTop: '8px', marginBottom: '24px', display: 'flex', gap: '8px' }}>
              <button className="dev-btn" onClick={() => fetch(`${BACKEND_URL}/api/git/system/status`).then(r => r.json()).then(d => setSystemGitStatus(d.status || d.error || 'OK'))}>Refresh</button>
              <button className="dev-btn dev-btn-run" onClick={() => { setSystemGitStatus('Pulling...'); fetch(`${BACKEND_URL}/api/git/system/pull`, { method: 'POST' }).then(r => r.json()).then(d => setSystemGitStatus(d.stdout || d.stderr || d.error || 'Done.')); }}>⬇️ Pull</button>
              <button className="dev-btn dev-btn-run" onClick={() => { setSystemGitStatus('Pushing...'); fetch(`${BACKEND_URL}/api/git/system/push`, { method: 'POST' }).then(r => r.json()).then(d => setSystemGitStatus(d.stdout || d.stderr || d.error || 'Done.')); }}>⬆️ Push</button>
            </div>
            <h4 className="git-header" style={{ color: '#fff' }}>Projects Workspace</h4>
            <pre className="git-output" style={{ flex: 1 }}>{gitStatus}</pre>
            <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
              <button className="dev-btn" onClick={() => fetch(`${BACKEND_URL}/api/git/status`).then(r => r.json()).then(d => setGitStatus(d.status || d.error || 'OK'))}>Refresh</button>
              <button className="dev-btn dev-btn-run" onClick={() => setDevCodeInput(`import subprocess\nres = subprocess.run(["git", "add", "."], capture_output=True, text=True)\nprint(res.stdout)\nres2 = subprocess.run(["git", "commit", "-m", "Auto-commit from IDE"], capture_output=True, text=True)\nprint(res2.stdout)`)}>Auto-Commit Script</button>
            </div>
          </div>
        ) : (
          <div className="git-panel">
            <h4 className="git-header">Background Trainer Status</h4>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0', marginBottom: '12px' }}>Logs from the offline self-learning daemon.</p>
            <TrainerLogViewer BACKEND_URL={BACKEND_URL} />
          </div>
        )}
      </div>

      {/* CODE EDITOR PANEL (RIGHT) */}
      <div className="dev-code-panel glass-panel">
        <div className="dev-header-row">
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>{devMode === 'visual' ? 'Visual Scripting' : 'Code Editor'}</h3>
            <div className="dev-toggle-group">
              <button className={`dev-toggle-btn ${devMode === 'text' ? 'active' : 'inactive'}`} onClick={() => setDevMode('text')}>Text Editor</button>
              <button className={`dev-toggle-btn ${devMode === 'visual' ? 'active' : 'inactive'}`} onClick={() => setDevMode('visual')}>Visual Scripting</button>
            </div>
          </div>
          {devMode === 'text' && (
            <select
              value={devCodeType}
              onChange={(e) => {
                const t = e.target.value;
                setDevCodeType(t);
                const extMap = { python: '.py', javascript: '.js', css: '.css', cpp: '.cpp', html: '.html', lua: '.lua', go: '.go' };
                const ext = extMap[t] || '.txt';
                if (!devFileName.endsWith(ext)) setDevFileName(`script${ext}`);
              }}
              className="dev-select"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="cpp">C++</option>
              <option value="lua">Lua</option>
              <option value="go">Go</option>
              <option value="html">HTML (WebGL)</option>
              <option value="css">CSS</option>
            </select>
          )}
        </div>

        {devMode === 'visual' ? (
          <div style={{ flex: 1, minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
            <VisualScriptingTab onExportCode={(code, type) => {
              setDevCodeType(type);
              setDevCodeInput(code);
              setDevFileName(type === 'html' ? 'visual_scene.html' : 'visual_script.js');
              setDevMode('text');
            }} />
          </div>
        ) : (
          <>
            {/* File save row */}
            <div className="file-save-row">
              <input
                type="text"
                value={devFileName}
                onChange={(e) => setDevFileName(e.target.value)}
                placeholder="Filename (e.g. app.py)"
                className="file-input"
              />
              <button
                onClick={handleSaveFile}
                disabled={isSavingFile || !devFileName.trim()}
                className="file-save-btn"
                style={{ opacity: isSavingFile ? 0.6 : 1 }}
              >
                {isSavingFile ? 'Saving...' : '💾 Save File'}
              </button>
              {saveMessage && <span style={{ fontSize: '0.8rem', color: saveMessage.startsWith('✅') ? '#4ade80' : '#f87171' }}>{saveMessage}</span>}
            </div>

            {/* Monaco Editor */}
            <div className="editor-wrapper">
              <Editor
                height="100%"
                language={devCodeType === 'cpp' ? 'cpp' : devCodeType}
                theme="vs-dark"
                value={devCodeInput}
                onChange={(value) => setDevCodeInput(value || '')}
                onMount={handleEditorDidMount}
                options={{ minimap: { enabled: false }, fontSize: 14, wordWrap: 'on', scrollBeyondLastLine: false, automaticLayout: true }}
              />
            </div>

            {/* Run button */}
            <div className="run-row">
              {devCodeType !== 'css' && devCodeType !== 'html' && (
                <button
                  onClick={handleExecuteCode}
                  disabled={isExecutingCode}
                  className={`run-btn ${isExecutingCode ? 'running' : 'idle'}`}
                >
                  {isExecutingCode ? 'Running...' : `▶️ Run ${devCodeType}`}
                </button>
              )}
            </div>

            {/* Bottom output/terminal panel */}
            <div className="bottom-panel">
              <div className="bottom-tabs">
                <button
                  className={`bottom-tab-btn ${devBottomTab === 'output' ? 'active' : 'inactive'}`}
                  onClick={() => setDevBottomTab('output')}
                >Console Output</button>
                <button
                  className={`bottom-tab-btn ${devBottomTab === 'terminal' ? 'active' : 'inactive'}`}
                  onClick={() => setDevBottomTab('terminal')}
                >Terminal</button>
              </div>
              <div className="bottom-content">
                {devBottomTab === 'output' && (
                  <div className="console-output">
                    {devCodeType === 'html' ? (
                      <iframe
                        title="HTML Preview"
                        srcDoc={devCodeInput}
                        sandbox="allow-scripts allow-modals"
                        style={{ width: '100%', height: '100%', background: '#fff', border: 'none', borderRadius: '4px' }}
                      />
                    ) : !Array.isArray(devCodeOutput) || devCodeOutput.length === 0 ? (
                      <div style={{ color: '#888' }}>Ready. Click Run to execute.</div>
                    ) : (
                      devCodeOutput.map((step, idx) => (
                        <div key={idx} className={`console-step ${step.type === 'error' ? 'error' : step.type === 'complete' ? 'complete' : 'default'}`}>
                          <div className="console-step-header" style={{ color: step.type === 'error' ? '#ff6b6b' : step.type === 'complete' ? '#4ade80' : '#fff' }}>
                            {step.type === 'error' ? '🐛 Error' : step.type === 'complete' ? '✅ Complete' : step.type === 'stdout' ? '💻 Output' : '⚙️ System'}
                          </div>
                          <pre className="console-step-content">{step.content}</pre>
                        </div>
                      ))
                    )}
                  </div>
                )}
                {devBottomTab === 'terminal' && (
                  <TerminalPanel backendUrl={BACKEND_URL} />
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

*End of DeveloperWorkspaceTab.jsx*

---

## GpuNetworkTab.jsx
```jsx
import React, { useState, useEffect } from 'react';

export default function GpuNetworkTab({ backendUrl }) {
  const [activeSubTab, setActiveSubTab] = useState('provider'); // provider | renter | telemetry
  
  // Host Telemetry State
  const [nodeId, setNodeId] = useState('Brett-RTX4090-Desktop');
  const [gpuName, setGpuName] = useState('NVIDIA GeForce RTX 4090');
  const [vramTotalGb, setVramTotalGb] = useState(24.0);
  const [vramUsedGb, setVramUsedGb] = useState(3.4);
  const [gpuTempC, setGpuTempC] = useState(52);
  const [isIdleOnly, setIsIdleOnly] = useState(true);
  const [isIdleActive, setIsIdleActive] = useState(true);
  const [payoutRateHr, setPayoutRateHr] = useState(0.55);

  // Earnings Ledger (Synced directly with compute_telemetry.json)
  const [totalEarnedUsd, setTotalEarnedUsd] = useState(12.92);
  const [pendingUsd, setPendingUsd] = useState(12.92);
  const [redeemedUsd, setRedeemedUsd] = useState(0.00);
  const [totalComputeHours, setTotalComputeHours] = useState(0.9);

  // Payout Form State
  const [payoutAmount, setPayoutAmount] = useState(10.00);
  const [payoutMethod, setPayoutMethod] = useState('paypal');
  const [payoutStatusMsg, setPayoutStatusMsg] = useState('');
  const [isRedeeming, setIsRedeeming] = useState(false);

  // Job Submission State (Renter)
  const [renterJobType, setRenterJobType] = useState('sdxl_inference');
  const [renterTargetTier, setRenterTargetTier] = useState('ultra_rtx4090');
  const [renterPrompt, setRenterPrompt] = useState('Generate high-resolution 3D cyberpunk cityscape model rendering');
  const [renterBudgetUsd, setRenterBudgetUsd] = useState(2.50);
  const [submittedJobs, setSubmittedJobs] = useState([]);

  // Live On-Chain Treasury State
  const [treasuryData, setTreasuryData] = useState(null);

  const apiBase = backendUrl || `${backendUrl}`;

  // Fetch Live Node Earnings & Telemetry
  useEffect(() => {
    fetch(`${apiBase}/v1/network/earnings/${nodeId}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success' && data.ledger) {
          setTotalEarnedUsd(data.ledger.total_earned_usd);
          setPendingUsd(data.ledger.pending_usd);
          setRedeemedUsd(data.ledger.redeemed_usd);
          setTotalComputeHours(data.ledger.total_compute_hours);
        }
      })
      .catch(err => console.error("Failed to fetch earnings:", err));
  }, [apiBase, nodeId]);

  // Fetch Live On-Chain Treasury Data
  const fetchTreasury = () => {
    fetch(`${apiBase}/v1/network/treasury-status`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setTreasuryData(data);
        }
      })
      .catch(err => console.error("Failed to fetch treasury:", err));
  };

  useEffect(() => {
    fetchTreasury();
    const tInterval = setInterval(fetchTreasury, 15000);
    return () => clearInterval(tInterval);
  }, [apiBase]);

  // Simulate real-time compute earnings counter when active & idle
  useEffect(() => {
    const interval = setInterval(() => {
      if (isIdleActive) {
        const delta = (5 / 3600) * payoutRateHr;
        setTotalEarnedUsd(prev => Number((prev + delta).toFixed(4)));
        setPendingUsd(prev => Number((prev + delta).toFixed(4)));
        setTotalComputeHours(prev => Number((prev + (5 / 3600)).toFixed(3)));
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [isIdleActive, payoutRateHr]);

  // Handle Payout Redemption
  const handleRedeemPayout = async () => {
    setIsRedeeming(true);
    setPayoutStatusMsg('');
    try {
      const res = await fetch(`${apiBase}/v1/network/redeem-payout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          node_id: nodeId,
          amount_usd: Number(payoutAmount),
          payout_method: payoutMethod
        })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setPendingUsd(data.remaining_pending_usd);
        setRedeemedUsd(data.total_redeemed_usd);
        setPayoutStatusMsg(`✅ ${data.message}`);
      } else {
        setPayoutStatusMsg(`❌ ${data.message || 'Payout failed.'}`);
      }
    } catch (err) {
      setPayoutStatusMsg(`❌ Server error during payout redemption: ${err.message}`);
    } finally {
      setIsRedeeming(false);
    }
  };

  // Handle Job Submission (Renter)
  const handleSubmitJob = async () => {
    try {
      const res = await fetch(`${apiBase}/v1/network/submit-job`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          renter_id: "brett_publishing_renter",
          job_type: renterJobType,
          prompt_or_code: renterPrompt,
          target_tier: renterTargetTier,
          max_budget_usd: Number(renterBudgetUsd)
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setSubmittedJobs(prev => [data, ...prev]);
      }
    } catch (err) {
      console.error("Job submit error:", err);
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: '#090d16',
      color: '#c9d1d9',
      padding: '24px',
      overflowY: 'auto',
      boxSizing: 'border-box'
    }}>
      {/* Top Banner Header */}
      <div style={{
        background: 'linear-gradient(135deg, #1f293d 0%, #0d1117 100%)',
        border: '1px solid #30363d',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h2 style={{ margin: 0, color: '#58a6ff', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            ⚡ Decentralized GPU Compute Network
          </h2>
          <p style={{ margin: '6px 0 0 0', color: '#8b949e', fontSize: '0.88rem' }}>
            Monetize idle RTX 4090 GPU compute power for containerized AI inference & deep learning workloads.
          </p>
        </div>
        
        {/* Navigation Sub-Tabs */}
        <div style={{ display: 'flex', gap: '8px', background: '#161b22', padding: '4px', borderRadius: '8px', border: '1px solid #30363d' }}>
          <button
            onClick={() => setActiveSubTab('provider')}
            style={{
              background: activeSubTab === 'provider' ? '#238636' : 'transparent',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.85rem'
            }}
          >
            💰 Host Provider Dashboard
          </button>
          <button
            onClick={() => setActiveSubTab('renter')}
            style={{
              background: activeSubTab === 'renter' ? '#1f6feb' : 'transparent',
              color: '#fff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '0.85rem'
            }}
          >
            🚀 AI Renter Marketplace
          </button>
        </div>
      </div>

      {/* PROVIDER DASHBOARD VIEW */}
      {activeSubTab === 'provider' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
          
          {/* Left Column: Live Earnings & Node Hardware Telemetry */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Live Earnings Stat Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>Available Balance</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#3fb950', marginTop: '4px' }}>
                  ${pendingUsd.toFixed(2)}
                </div>
              </div>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>Total Earned</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#58a6ff', marginTop: '4px' }}>
                  ${totalEarnedUsd.toFixed(2)}
                </div>
              </div>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>GPU Earning Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#e3b341', marginTop: '4px' }}>
                  ${payoutRateHr.toFixed(2)} <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>/ hr</span>
                </div>
              </div>
              <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '16px' }}>
                <div style={{ fontSize: '0.75rem', color: '#8b949e', textTransform: 'uppercase' }}>Compute Hours</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#d2a8ff', marginTop: '4px' }}>
                  {totalComputeHours.toFixed(1)} <span style={{ fontSize: '0.75rem', color: '#8b949e' }}>hrs</span>
                </div>
              </div>
            </div>

            {/* Hardware Node Telemetry & Status */}
            <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#c9d1d9' }}>🖥️ Host Worker Node Telemetry</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: isIdleActive ? '#3fb950' : '#d29922'
                  }} />
                  <span style={{ fontSize: '0.85rem', fontWeight: '600', color: isIdleActive ? '#3fb950' : '#d29922' }}>
                    {isIdleActive ? 'IDLE & COMPUTING ($/hr Active)' : 'BUSY (Computing Paused)'}
                  </span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '0.88rem' }}>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>Host Node ID</div>
                  <div style={{ fontWeight: '600', color: '#58a6ff', marginTop: '2px' }}>{nodeId}</div>
                </div>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>GPU Acceleration Hardware</div>
                  <div style={{ fontWeight: '600', color: '#c9d1d9', marginTop: '2px' }}>{gpuName}</div>
                </div>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>VRAM Allocation & Allocation</div>
                  <div style={{ fontWeight: '600', color: '#c9d1d9', marginTop: '2px' }}>
                    {vramUsedGb} GB / {vramTotalGb} GB VRAM ({Math.round((vramUsedGb/vramTotalGb)*100)}%)
                  </div>
                </div>
                <div style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', border: '1px solid #21262d' }}>
                  <div style={{ color: '#8b949e', fontSize: '0.78rem' }}>GPU Operating Temperature</div>
                  <div style={{ fontWeight: '600', color: gpuTempC > 70 ? '#f85149' : '#3fb950', marginTop: '2px' }}>
                    {gpuTempC} °C (Optimal Cooling)
                  </div>
                </div>
              </div>

              {/* Safety Idle Switch */}
              <div style={{ marginTop: '16px', background: '#21262d', padding: '12px 16px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>🛡️ Windows Idle-Only Task Execution</div>
                  <div style={{ fontSize: '0.78rem', color: '#8b949e' }}>
                    Automatically pauses AI container tasks instantly when mouse/keyboard input is detected or gaming starts.
                  </div>
                </div>
                <button
                  onClick={() => setIsIdleOnly(!isIdleOnly)}
                  style={{
                    background: isIdleOnly ? '#238636' : '#da3633',
                    color: '#fff',
                    border: 'none',
                    padding: '6px 14px',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '0.8rem'
                  }}
                >
                  {isIdleOnly ? 'ACTIVE (Idle Only)' : 'ALWAYS ON'}
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Earnings Payout Redemption Module */}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#58a6ff' }}>💳 Payout & Rewards Redemption</h3>
            
            <p style={{ margin: 0, fontSize: '0.82rem', color: '#8b949e' }}>
              Redeem host GPU compute earnings directly via PayPal, Visa Prepaid Card, or Gift Cards.
            </p>

            <div>
              <label htmlFor="payout-amount-input" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                Redemption Amount ($ USD):
              </label>
              <input
                id="payout-amount-input"
                aria-label="Redemption Amount ($ USD)"
                type="number"
                min="1"
                max={pendingUsd}
                step="1"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  color: '#fff',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div>
              <label htmlFor="payout-method-select" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                Payout Destination Method:
              </label>
              <select
                id="payout-method-select"
                aria-label="Payout Destination Method"
                value={payoutMethod}
                onChange={(e) => setPayoutMethod(e.target.value)}
                style={{
                  width: '100%',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  color: '#fff',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box'
                }}
              >
                <option value="paypal">PayPal Direct Cash Transfer</option>
                <option value="giftcard">Visa Virtual Prepaid Card</option>
                <option value="amazon">Amazon Gift Card Code</option>
                <option value="crypto">USDC Crypto Deposit</option>
                <option value="cryptocom_app">Crypto.com App Direct Transfer</option>
              </select>
            </div>

            <button
              onClick={handleRedeemPayout}
              disabled={isRedeeming || pendingUsd < payoutAmount}
              style={{
                background: pendingUsd >= payoutAmount ? '#238636' : '#21262d',
                color: pendingUsd >= payoutAmount ? '#fff' : '#8b949e',
                border: 'none',
                padding: '12px',
                borderRadius: '8px',
                cursor: pendingUsd >= payoutAmount ? 'pointer' : 'not-allowed',
                fontWeight: '700',
                fontSize: '0.95rem',
                marginTop: '8px'
              }}
            >
              {isRedeeming ? 'Processing Payout...' : `Redeem $${payoutAmount} Payout`}
            </button>

            {payoutStatusMsg && (
              <div style={{
                background: payoutStatusMsg.includes('✅') ? '#122e1a' : '#3c1e1e',
                color: payoutStatusMsg.includes('✅') ? '#3fb950' : '#f85149',
                border: `1px solid ${payoutStatusMsg.includes('✅') ? '#238636' : '#da3633'}`,
                padding: '10px',
                borderRadius: '6px',
                fontSize: '0.8rem'
              }}>
                {payoutStatusMsg}
              </div>
            )}

            <div style={{ borderTop: '1px solid #21262d', paddingTop: '12px', fontSize: '0.78rem', color: '#8b949e' }}>
              <div>Total Payouts Redeemed: <strong style={{ color: '#c9d1d9' }}>${redeemedUsd.toFixed(2)}</strong></div>
              <div style={{ marginTop: '4px' }}>Payout Email: <strong style={{ color: '#58a6ff' }}>footballstar0325@mail.com</strong></div>
            </div>

            {/* LIVE ON-CHAIN TREASURY & BLOCKCHAIN TELEMETRY CARD */}
            <div style={{ background: '#0d1117', border: '1px solid #238636', borderRadius: '8px', padding: '14px', marginTop: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '700', color: '#3fb950', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  🏛️ Server On-Chain Treasury
                </div>
                <span style={{ fontSize: '0.7rem', background: '#122e1a', color: '#3fb950', border: '1px solid #238636', padding: '2px 6px', borderRadius: '4px' }}>
                  Polygon Mainnet
                </span>
              </div>

              {treasuryData ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.78rem' }}>
                  <div style={{ background: '#161b22', padding: '8px 10px', borderRadius: '6px', border: '1px solid #30363d' }}>
                    <div style={{ color: '#8b949e', fontSize: '0.7rem', marginBottom: '2px' }}>SERVER HOT WALLET TREASURY</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        USDC: <strong style={{ color: treasuryData.hot_wallet.usdc_balance > 0 ? '#3fb950' : '#f85149' }}>${treasuryData.hot_wallet.usdc_balance.toFixed(2)}</strong>
                      </div>
                      <div>
                        POL (Gas): <strong style={{ color: treasuryData.hot_wallet.pol_balance > 0.05 ? '#3fb950' : '#d29922' }}>{treasuryData.hot_wallet.pol_balance} POL</strong>
                      </div>
                    </div>
                    <div style={{ marginTop: '4px', fontSize: '0.72rem', color: '#58a6ff', wordBreak: 'break-all', display: 'flex', justifyContent: 'space-between' }}>
                      <span>{treasuryData.hot_wallet.address.slice(0, 10)}...{treasuryData.hot_wallet.address.slice(-8)}</span>
                      <a href={treasuryData.hot_wallet.explorer_url} target="_blank" rel="noreferrer" style={{ color: '#58a6ff', textDecoration: 'underline' }}>Explorer ↗</a>
                    </div>
                  </div>

                  <div style={{ background: '#161b22', padding: '8px 10px', borderRadius: '6px', border: '1px solid #30363d' }}>
                    <div style={{ color: '#8b949e', fontSize: '0.7rem', marginBottom: '2px' }}>DESTINATION WALLET (CRYPTO.COM)</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        USDC: <strong style={{ color: '#58a6ff' }}>${treasuryData.dest_wallet.usdc_balance.toFixed(2)}</strong>
                      </div>
                      <div>
                        POL: <strong style={{ color: '#8b949e' }}>{treasuryData.dest_wallet.pol_balance} POL</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#8b949e', paddingTop: '4px' }}>
                    <span>Block: <strong style={{ color: '#c9d1d9' }}>#{treasuryData.block_number}</strong></span>
                    <span>Node: <strong style={{ color: '#3fb950' }}>PublicNode Dedicated</strong></span>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: '0.78rem', color: '#8b949e', textAlign: 'center', padding: '8px' }}>
                  Connecting to Polygon Web3 Node...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* RENTER MARKETPLACE VIEW */}
      {activeSubTab === 'renter' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          
          {/* Submit Container Job Form */}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#58a6ff' }}>
              🚀 Submit Container Task to Consumer Network
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label htmlFor="renter-job-type-select" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Task Workload Type:
                </label>
                <select
                  id="renter-job-type-select"
                  aria-label="Task Workload Type"
                  value={renterJobType}
                  onChange={(e) => setRenterJobType(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px' }}
                >
                  <option value="sdxl_inference">ComfyUI SDXL Image / Video Generation</option>
                  <option value="pytorch_train">PyTorch Model Fine-Tuning Task</option>
                  <option value="ollama_llm">Ollama LLM Batch Inference Processing</option>
                </select>
              </div>

              <div>
                <label htmlFor="renter-target-tier-select" style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Target Hardware Tier:
                </label>
                <select
                  id="renter-target-tier-select"
                  aria-label="Target Hardware Tier"
                  value={renterTargetTier}
                  onChange={(e) => setRenterTargetTier(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px' }}
                >
                  <option value="ultra_rtx4090">Ultra Tier (RTX 4090 - 24GB VRAM) @ $0.55/hr</option>
                  <option value="high_rtx4080">High Tier (RTX 4080 - 16GB VRAM) @ $0.35/hr</option>
                  <option value="mid_rtx3070">Mid Tier (RTX 3070 - 8GB VRAM) @ $0.20/hr</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Container Execution Payload / Code / Prompt:
                </label>
                <textarea
                  rows={4}
                  value={renterPrompt}
                  onChange={(e) => setRenterPrompt(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontFamily: 'monospace' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#8b949e', marginBottom: '4px' }}>
                  Max Budget Limit ($ USD):
                </label>
                <input
                  type="number"
                  step="0.50"
                  value={renterBudgetUsd}
                  onChange={(e) => setRenterBudgetUsd(e.target.value)}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px' }}
                />
              </div>

              <button
                onClick={handleSubmitJob}
                style={{
                  background: '#1f6feb',
                  color: '#fff',
                  border: 'none',
                  padding: '12px',
                  borderRadius: '8px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  fontSize: '0.95rem'
                }}
              >
                Submit Job to Network Dispatcher
              </button>
            </div>
          </div>

          {/* Active Job Queue */}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#c9d1d9' }}>
              📊 Network Job Queue & Dispatch History
            </h3>

            {submittedJobs.length === 0 ? (
              <div style={{ color: '#8b949e', fontSize: '0.88rem', fontStyle: 'italic', textAlign: 'center', padding: '40px 0' }}>
                No active jobs submitted yet. Use the form on the left to queue container workloads.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {submittedJobs.map((job, idx) => (
                  <div key={idx} style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: '6px', padding: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: '600', color: '#58a6ff' }}>
                      <span>{job.job_id}</span>
                      <span style={{ color: '#3fb950' }}>Queued (Node Assigned)</span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#8b949e', marginTop: '4px' }}>
                      Position: #{job.queue_position} | Target Tier: {renterTargetTier}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

*End of GpuNetworkTab.jsx*

---

## CryptoSwarmMobileController.jsx
```jsx
import React, { useState, useEffect } from 'react';

const RefreshIcon = ({ size = 18, color = "#58a6ff" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10"></polyline>
    <polyline points="1 20 1 14 7 14"></polyline>
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
  </svg>
);

const SwapIcon = ({ size = 18, color = "#3fb950" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="17 1 21 5 17 9"></polyline>
    <path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
    <polyline points="7 23 3 19 7 15"></polyline>
    <path d="M21 13v2a4 4 0 0 1-4 4H3"></path>
  </svg>
);

const SlidersIcon = ({ size = 18, color = "#a371f7" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="21" x2="4" y2="14"></line>
    <line x1="4" y1="10" x2="4" y2="3"></line>
    <line x1="12" y1="21" x2="12" y2="12"></line>
    <line x1="12" y1="8" x2="12" y2="3"></line>
    <line x1="20" y1="21" x2="20" y2="16"></line>
    <line x1="20" y1="12" x2="20" y2="3"></line>
    <line x1="1" y1="14" x2="7" y2="14"></line>
    <line x1="9" y1="8" x2="15" y2="8"></line>
    <line x1="17" y1="16" x2="23" y2="16"></line>
  </svg>
);

const fmt = (num, decimals = 2) => {
  if (num === undefined || num === null || isNaN(Number(num))) return (0).toFixed(decimals);
  return Number(num).toFixed(decimals);
};

const CryptoSwarmMobileController = ({ backendUrl }) => {
  const apiHost = backendUrl || "https://ai-bs.brettstehouwer.live";
  let daemonHost = "http://localhost:8006";
  if (apiHost && apiHost.startsWith("http")) {
    const urlObj = new URL(apiHost);
    urlObj.port = "8006";
    daemonHost = urlObj.origin;
  }
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Control Parameter Form State
  const [buyDipPct, setBuyDipPct] = useState(1.5);
  const [takeProfitPct, setTakeProfitPct] = useState(2.0);
  const [tradeUsdAmount, setTradeUsdAmount] = useState(2.0);
  const [savingParams, setSavingParams] = useState(false);
  const [paramStatus, setParamStatus] = useState('');

  // Force Swap Form State
  const [fromSymbol, setFromSymbol] = useState('');
  const [toSymbol, setToSymbol] = useState('');
  const [swapping, setSwapping] = useState(false);
  const [swapMessage, setSwapMessage] = useState('');

  const fetchStatus = async () => {
    try {
      setLoading(true);
      
      const res = await fetch(`${daemonHost}/api/v1/telemetry`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json = await res.json();
      
      // Map the telemetry payload to the component's expected data structure
      const ledger = json.ledger || {};
      const positionsObj = ledger.positions || {};
      const refsObj = ledger.reference_prices || {};
      
      let totalEstValue = parseFloat(json.usd_balance || 0);
      const mappedPositions = Object.keys(positionsObj).map(symbol => {
        const amount = positionsObj[symbol]?.amount || 0;
        const avgBuy = positionsObj[symbol]?.avg_buy_price || 0;
        const currentRef = refsObj[symbol] || avgBuy;
        const estValue = amount * currentRef;
        totalEstValue += estValue;
        
        let unrealizedPct = 0;
        if (avgBuy > 0) {
          unrealizedPct = ((currentRef - avgBuy) / avgBuy) * 100;
        }
        
        return {
          symbol,
          amount,
          avg_buy_price: avgBuy,
          current_ref_price: currentRef,
          estimated_value_usd: estValue,
          unrealized_profit_pct: unrealizedPct
        };
      });
      
      const mappedData = {
        status: json.status || 'offline',
        total_active_positions: mappedPositions.length,
        tracked_symbols_count: Object.keys(refsObj).length,
        total_estimated_portfolio_usd: totalEstValue,
        total_profit_usd: ledger.total_profit_usd || 0.0,
        strategy_layer: ledger.strategy_layer || 'Market Making',
        last_action: ledger.last_action || 'Standing by',
        positions: mappedPositions,
        twaps: ledger.twap_orders || []
      };

      setData(mappedData);
      setError(null);
      setLastUpdated(new Date().toLocaleTimeString());
      
    } catch (err) {
      console.error("Crypto status fetch error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, [apiHost]);

  const handleSaveParameters = async (e) => {
    e.preventDefault();
    setSavingParams(true);
    setParamStatus('');
    try {
      const res = await fetch(`${daemonHost}/api/crypto/set-parameters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          buy_dip_pct: parseFloat(buyDipPct) / 100.0,
          take_profit_pct: parseFloat(takeProfitPct) / 100.0,
          trade_usd_amount: parseFloat(tradeUsdAmount)
        })
      });
      const resJson = await res.json();
      if (resJson.status === 'success') {
        setParamStatus('✅ Strategy parameters updated!');
        fetchStatus();
      } else {
        setParamStatus('❌ Update failed');
      }
    } catch (err) {
      setParamStatus(`❌ Error: ${err.message}`);
    } finally {
      setSavingParams(false);
    }
  };

  const handleForceSwap = async (e) => {
    e.preventDefault();
    if (!fromSymbol || !toSymbol) {
      setSwapMessage('⚠️ Select both from and to symbols.');
      return;
    }
    setSwapping(true);
    setSwapMessage('');
    try {
      const res = await fetch(`${daemonHost}/api/crypto/force-swap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_symbol: fromSymbol, to_symbol: toSymbol })
      });
      const resJson = await res.json();
      if (res.ok && resJson.status === 'success') {
        setSwapMessage(`✅ Swapped ${fromSymbol} -> ${toSymbol} ($${resJson.usd_value})`);
        setFromSymbol('');
        setToSymbol('');
        fetchStatus();
      } else {
        setSwapMessage(`❌ ${resJson.detail || 'Swap failed'}`);
      }
    } catch (err) {
      setSwapMessage(`❌ Error: ${err.message}`);
    } finally {
      setSwapping(false);
    }
  };

  const positions = data?.positions || [];
  const twaps = data?.twaps || [];
  const trackedSymbolsCount = data?.tracked_symbols_count || 0;

  return (
    <div style={{
      width: '100%',
      minHeight: '100vh',
      backgroundColor: '#0d1117',
      color: '#c9d1d9',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      padding: '20px',
      boxSizing: 'border-box'
    }}>
      {/* Header Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: '1px solid #30363d'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>⚡</span> Crypto Swarm Mobile Controller
          </h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#8b949e' }}>
            Real-Time Automated Trade Monitoring & Volatility Harvesting Daemon
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {lastUpdated && (
            <span style={{ fontSize: '12px', color: '#8b949e' }}>Updated: {lastUpdated}</span>
          )}
          <button
            onClick={fetchStatus}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#21262d',
              color: '#c9d1d9',
              border: '1px solid #30363d',
              borderRadius: '6px',
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <RefreshIcon size={16} color="#58a6ff" />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ backgroundColor: '#3d1619', border: '1px solid #f85149', color: '#ff7b72', padding: '12px 16px', borderRadius: '6px', marginBottom: '20px' }}>
          <strong>Connection Error:</strong> {error}
        </div>
      )}

      {/* Metrics Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
        marginBottom: '24px'
      }}>
        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Active Positions</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#58a6ff', marginTop: '6px' }}>
            {data ? (data.total_active_positions ?? 0) : '--'}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>Tracking {trackedSymbolsCount} Markets</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Est. Portfolio Value</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#3fb950', marginTop: '6px' }}>
            ${fmt(data?.total_estimated_portfolio_usd, 2)}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>USD Value across held coins</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Realized Profit</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#a371f7', marginTop: '6px' }}>
            ${fmt(data?.total_profit_usd, 2)}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>Cumulative profit banked</div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Active Strategy Layer</div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#ff7b72', marginTop: '6px', lineHeight: '1.2' }}>
            {data?.strategy_layer || 'Market Making'}
          </div>
          <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={data?.last_action}>
            {data?.last_action || 'Standing by'}
          </div>
        </div>

        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '12px', color: '#8b949e', textTransform: 'uppercase', fontWeight: 600 }}>Swarm Status</div>
          <div style={{ fontSize: '28px', fontWeight: 700, color: '#388bfd', marginTop: '6px', textTransform: 'capitalize' }}>
            {data ? data.status : 'Offline'}
          </div>
          <div style={{ fontSize: '12px', color: '#3fb950', marginTop: '4px' }}>● Bot Active</div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        
        {/* Active Positions Table Container */}
        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px', gridColumn: 'span 2' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📊</span> Active Coin Positions ({positions.length})
          </h2>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                  <th style={{ padding: '10px 12px' }}>Symbol</th>
                  <th style={{ padding: '10px 12px' }}>Holdings</th>
                  <th style={{ padding: '10px 12px' }}>Avg Buy Price</th>
                  <th style={{ padding: '10px 12px' }}>Ref Price</th>
                  <th style={{ padding: '10px 12px' }}>Est Value (USD)</th>
                  <th style={{ padding: '10px 12px' }}>P/L %</th>
                </tr>
              </thead>
              <tbody>
                {positions.length === 0 ? (
                  <tr>
                    <td colSpan="6" style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                      No active positions held currently.
                    </td>
                  </tr>
                ) : (
                  positions.map((pos) => {
                    const isProfit = (pos.unrealized_profit_pct ?? 0) >= 0;
                    return (
                      <tr key={pos.symbol} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>{pos.symbol}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>{fmt(pos.amount, 4)}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>${(pos.avg_buy_price || 0) < 0.01 ? fmt(pos.avg_buy_price, 6) : fmt(pos.avg_buy_price, 4)}</td>
                        <td style={{ padding: '12px', fontFamily: 'monospace' }}>${(pos.current_ref_price || 0) < 0.01 ? fmt(pos.current_ref_price, 6) : fmt(pos.current_ref_price, 4)}</td>
                        <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>${fmt(pos.estimated_value_usd, 2)}</td>
                        <td style={{ padding: '12px', fontWeight: 600, color: isProfit ? '#3fb950' : '#f85149' }}>
                          {isProfit ? '+' : ''}{fmt(pos.unrealized_profit_pct, 2)}%
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Active Drip Campaigns Table Container */}
        <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px', gridColumn: 'span 2' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>💧</span> Active Drip Campaigns ({twaps.length})
          </h2>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #30363d', color: '#8b949e' }}>
                  <th style={{ padding: '10px 12px' }}>Symbol</th>
                  <th style={{ padding: '10px 12px' }}>Total Ordered</th>
                  <th style={{ padding: '10px 12px' }}>Remaining USD</th>
                  <th style={{ padding: '10px 12px' }}>Drip Size</th>
                  <th style={{ padding: '10px 12px' }}>Interval (s)</th>
                </tr>
              </thead>
              <tbody>
                {twaps.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                      No active TWAP/Drip campaigns running.
                    </td>
                  </tr>
                ) : (
                  twaps.map((twap, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '12px', fontWeight: 600, color: '#f0f6fc' }}>{twap.symbol}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace' }}>${fmt(twap.total_usd, 2)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace', color: '#3fb950' }}>${fmt(twap.remaining_usd, 2)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace' }}>${fmt(twap.drip_size_usd, 2)}</td>
                      <td style={{ padding: '12px', fontFamily: 'monospace' }}>{twap.drip_interval_seconds}s</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Side Panel: Strategy Parameters & Manual Force Swap */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Strategy Parameter Tuning */}
          <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SlidersIcon size={18} color="#a371f7" /> Strategy Parameters
            </h2>

            <form onSubmit={handleSaveParameters} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Buy Dip Target (%): <strong>{buyDipPct}%</strong>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10.0"
                  value={buyDipPct}
                  onChange={(e) => setBuyDipPct(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Take Profit Target (%): <strong>{takeProfitPct}%</strong>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="20.0"
                  value={takeProfitPct}
                  onChange={(e) => setTakeProfitPct(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>
                  Trade USD Amount ($):
                </label>
                <input
                  type="number"
                  step="0.50"
                  min="1.00"
                  max="100.00"
                  value={tradeUsdAmount}
                  onChange={(e) => setTradeUsdAmount(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={savingParams}
                style={{
                  backgroundColor: '#238636',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 16px',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  marginTop: '8px'
                }}
              >
                {savingParams ? 'Updating...' : 'Save Parameters'}
              </button>

              {paramStatus && (
                <div style={{ fontSize: '12px', color: '#58a6ff', marginTop: '4px' }}>{paramStatus}</div>
              )}
            </form>
          </div>

          {/* Manual Force Swap Override */}
          <div style={{ backgroundColor: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '20px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f0f6fc', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SwapIcon size={18} color="#3fb950" /> Force Swap Override
            </h2>

            <form onSubmit={handleForceSwap} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>From Held Position:</label>
                <select
                  value={fromSymbol}
                  onChange={(e) => setFromSymbol(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="">-- Select Held Symbol --</option>
                  {positions.map(p => (
                    <option key={p.symbol} value={p.symbol}>
                      {p.symbol} (${fmt(p.estimated_value_usd, 2)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#8b949e', marginBottom: '6px' }}>Swap Into Target:</label>
                <select
                  value={toSymbol}
                  onChange={(e) => setToSymbol(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: '#f0f6fc',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="">-- Select Target Symbol --</option>
                  <option value="BTC/USD">BTC/USD</option>
                  <option value="ETH/USD">ETH/USD</option>
                  <option value="SOL/USD">SOL/USD</option>
                  <option value="DOGE/USD">DOGE/USD</option>
                  <option value="CRO/USD">CRO/USD</option>
                  <option value="AVAX/USD">AVAX/USD</option>
                  <option value="LINK/USD">LINK/USD</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={swapping || !fromSymbol || !toSymbol}
                style={{
                  backgroundColor: swapping ? '#30363d' : '#8957e5',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '10px 16px',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: swapping ? 'not-allowed' : 'pointer',
                  marginTop: '8px'
                }}
              >
                {swapping ? 'Executing Swap...' : 'Execute Force Swap'}
              </button>

              {swapMessage && (
                <div style={{ fontSize: '12px', marginTop: '4px' }}>{swapMessage}</div>
              )}
            </form>
          </div>

        </div>
      </div>
    </div>
  );
};

export default CryptoSwarmMobileController;
```

*End of CryptoSwarmMobileController.jsx*

---

## DefinitionsModuleTab.jsx
```jsx
import React, { useState, useEffect } from 'react';
import { BookOpen, History, Layers, GraduationCap, Search, Sparkles, CheckCircle2, XCircle, HelpCircle, ArrowRight, Shield, Zap, FileText, Cpu, Database, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';

export default function DefinitionsModuleTab({ backendUrl: propBackendUrl }) {
  const backendUrl = propBackendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://ai-bs-dashboard.web.app');
  
  const [activeTab, setActiveTab] = useState('timeline');

  return (
    <div className="p-6 lg:p-10 text-white min-h-screen bg-[#0b0f19] space-y-8">
      {/* Top Hero Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950 to-purple-950 p-8 border border-indigo-500/20 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 text-xs font-mono mb-3">
              <Sparkles className="w-3.5 h-3.5" /> AI-BS Matrix Knowledge System
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-300 to-pink-400">
              Definitions, Lore & Study Guide
            </h1>
            <p className="mt-2 text-gray-300 text-base max-w-2xl">
              Master the architectural timeline, jargon dictionary, and historical chronologies of the AI-BS ecosystem.
            </p>
          </div>
          
          <div className="flex items-center gap-3 bg-black/40 backdrop-blur-md px-4 py-3 rounded-xl border border-white/10">
            <Shield className="w-5 h-5 text-emerald-400" />
            <div>
              <div className="text-xs text-gray-400">System Manual Status</div>
              <div className="text-sm font-bold text-white font-mono">v8.20.0 Active</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Sub-Navigation Bar */}
      <div className="flex flex-wrap gap-3 border-b border-gray-800 pb-4">
        {[
          { id: 'timeline', label: 'Architectural Timeline', icon: History, color: 'from-blue-600 to-indigo-600' },
          { id: 'glossary', label: 'AI-BS Jargon Glossary', icon: BookOpen, color: 'from-purple-600 to-pink-600' },
          { id: 'chronology', label: 'Master Markdown Records', icon: Layers, color: 'from-emerald-600 to-teal-600' },
          { id: 'quiz', label: 'Interactive Study Guide', icon: GraduationCap, color: 'from-amber-600 to-orange-600' },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-300 ${
                isActive 
                  ? `bg-gradient-to-r ${tab.color} text-white shadow-lg shadow-indigo-500/20 scale-[1.02]` 
                  : 'bg-slate-900/80 text-gray-400 hover:text-white hover:bg-slate-800 border border-gray-800'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      {activeTab === 'timeline' && <ArchitecturalTimelinePanel backendUrl={backendUrl} />}
      {activeTab === 'glossary' && <JargonGlossaryPanel backendUrl={backendUrl} />}
      {activeTab === 'chronology' && <MasterRecordsChronologyPanel backendUrl={backendUrl} />}
      {activeTab === 'quiz' && <InteractiveStudyGuidePanel backendUrl={backendUrl} />}
    </div>
  );
}

// ----------------------------------------------------------------------
// 1. ARCHITECTURAL TIMELINE PANEL
// ----------------------------------------------------------------------
function ArchitecturalTimelinePanel({ backendUrl }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedIndex, setExpandedIndex] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/dictionary/ledger-history`);
        const json = await res.json();
        if (res.ok && json.data) {
          setHistory(json.data);
        } else {
          setError(json.message || 'Failed to fetch ledger history');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [backendUrl]);

  const filteredHistory = history.filter(item => 
    item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.version.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.body.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return <div className="text-indigo-400 p-12 text-center animate-pulse font-mono">Parsing Master Architectural Ledger (v1.0.0 – v8.20.0)...</div>;
  if (error) return <div className="text-red-400 p-6 bg-red-950/30 rounded-xl border border-red-500/30">{error}</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Left Column: Interactive Timeline */}
      <div className="lg:col-span-2 space-y-6">
        <div className="flex justify-between items-center flex-wrap gap-4">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <History className="w-6 h-6 text-indigo-400" /> Evolution Milestone Timeline
          </h2>
          
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
            <input 
              type="text" 
              placeholder="Filter milestones..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="relative border-l-2 border-indigo-500/30 ml-4 space-y-6">
          {filteredHistory.map((item, idx) => {
            const isExpanded = expandedIndex === idx;
            return (
              <div key={idx} className="ml-8 relative group">
                {/* Timeline node icon */}
                <div className={`absolute -left-12 top-2 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                  isExpanded ? 'bg-indigo-600 text-white shadow-[0_0_15px_rgba(99,102,241,0.6)] scale-110' : 'bg-slate-900 border border-indigo-500/40 text-indigo-400 group-hover:border-indigo-400'
                }`}>
                  ⚡
                </div>
                
                <div 
                  onClick={() => setExpandedIndex(isExpanded ? -1 : idx)}
                  className={`cursor-pointer bg-slate-900/70 backdrop-blur-md p-6 rounded-xl border transition-all duration-300 ${
                    isExpanded 
                      ? 'border-indigo-500/60 shadow-xl shadow-indigo-500/10' 
                      : 'border-gray-800/80 hover:border-gray-700'
                  }`}
                >
                  <div className="flex justify-between items-center mb-2 flex-wrap gap-2">
                    <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
                      {item.version}
                    </span>
                    <span className="text-xs text-gray-400 font-mono">{item.date}</span>
                  </div>

                  <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors flex items-center justify-between">
                    {item.title}
                    {isExpanded ? <ChevronDown className="w-5 h-5 text-indigo-400" /> : <ChevronRight className="w-5 h-5 text-gray-500" />}
                  </h3>
                  
                  {isExpanded ? (
                    <div className="mt-4 pt-4 border-t border-gray-800 space-y-4">
                      <div className="text-gray-300 text-sm whitespace-pre-wrap font-mono leading-relaxed bg-black/60 p-4 rounded-lg border border-gray-800/60 overflow-x-auto max-h-96">
                        {item.body}
                      </div>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-xs mt-2 italic">Click to inspect technical details and design rationale...</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Column: Ledger Metadata */}
      <div className="space-y-6">
        <div className="bg-slate-900/80 backdrop-blur-md p-6 rounded-2xl border border-gray-800 space-y-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
            <Cpu className="w-5 h-5 text-indigo-400" /> System Ledger Overview
          </h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            Real-time telemetry extracted directly from <span className="font-mono text-indigo-300">AI_BS_MASTER_ARCHITECTURAL_LEDGER.md</span>.
          </p>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-950 p-4 rounded-xl border border-gray-800">
              <div className="text-xs text-gray-500">Total Versions</div>
              <div className="text-2xl font-bold text-indigo-400 font-mono mt-1">{history.length}</div>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-gray-800">
              <div className="text-xs text-gray-500">Active Build</div>
              <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">{history[0]?.version || 'v8.20.0'}</div>
            </div>
          </div>

          <div className="bg-indigo-950/30 p-4 rounded-xl border border-indigo-500/20 text-xs text-indigo-200 space-y-2">
            <div className="font-bold text-indigo-300">Master Ledger Guarantee</div>
            <p className="text-gray-400">
              All codebase refactors automatically update timestamped development entries, ports, database schemas, and fallback contexts.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 2. JARGON GLOSSARY PANEL
// ----------------------------------------------------------------------
function JargonGlossaryPanel({ backendUrl }) {
  const [terms, setTerms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchTerms = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/dictionary/terms`);
        const json = await res.json();
        if (res.ok && json.data) setTerms(json.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchTerms();
  }, [backendUrl]);

  const categories = ['ALL', ...new Set(terms.map(t => t.category))];

  const filteredTerms = terms.filter(t => {
    const matchesCat = filterCategory === 'ALL' || t.category === filterCategory;
    const matchesSearch = t.term.toLowerCase().includes(search.toLowerCase()) || 
                          t.definition.toLowerCase().includes(search.toLowerCase()) ||
                          t.tag.toLowerCase().includes(search.toLowerCase());
    return matchesCat && matchesSearch;
  });

  if (loading) return <div className="text-purple-400 p-12 text-center animate-pulse font-mono">Loading AI-BS Glossary...</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-purple-400" /> AI-BS Jargon & Terminology Glossary
          </h2>
          <p className="text-xs text-gray-400 mt-1">Official terminology definitions and architectural impact specifications.</p>
        </div>

        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
          <input 
            type="text" 
            placeholder="Search jargon..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
          />
        </div>
      </div>

      {/* Category Pills */}
      <div className="flex gap-2 flex-wrap">
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filterCategory === cat
                ? 'bg-purple-600 text-white shadow-md shadow-purple-500/20'
                : 'bg-slate-900 text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Terms Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredTerms.map((t, idx) => (
          <div key={idx} className="bg-slate-900/80 backdrop-blur-md p-6 rounded-2xl border border-gray-800 hover:border-purple-500/40 transition-all space-y-4">
            <div className="flex justify-between items-start gap-2">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                  {t.category}
                </span>
                <h3 className="text-lg font-bold text-white mt-2">{t.term}</h3>
              </div>
              <span className="text-xs font-mono text-gray-400 bg-black/40 px-2.5 py-1 rounded-md border border-gray-800">
                {t.tag}
              </span>
            </div>

            <p className="text-gray-300 text-sm leading-relaxed">
              {t.definition}
            </p>

            <div className="pt-3 border-t border-gray-800/80 flex items-center gap-2 text-xs text-emerald-400">
              <Zap className="w-3.5 h-3.5 shrink-0" />
              <span><strong>Impact:</strong> {t.impact}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 3. MASTER RECORDS CHRONOLOGY PANEL
// ----------------------------------------------------------------------
function MasterRecordsChronologyPanel({ backendUrl }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState('tasks_chronology');

  useEffect(() => {
    const fetchChronology = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/dictionary/master-chronology`);
        const json = await res.json();
        if (res.ok && json.data) setData(json.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchChronology();
  }, [backendUrl]);

  if (loading) return <div className="text-emerald-400 p-12 text-center animate-pulse font-mono">Fetching Master Markdown Ledgers...</div>;

  const recordsList = [
    { key: 'tasks_chronology', label: 'MASTER_TASKS_CHRONOLOGY.md', path: 'Agent_Tasks_History/' },
    { key: 'plans_chronology', label: 'MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md', path: 'Agent_Implementation_Plans_History/' },
    { key: 'handoff_chronology', label: 'MASTER_HANDOFF_CHRONOLOGY.md', path: 'Agent_Handoff_Summaries/' },
    { key: 'artifact_history', label: 'artifact_history.md', path: 'NotebookLM_Records/' },
    { key: 'master_index', label: 'MASTER_HISTORICAL_INDEX.md', path: 'C:\\AI-BS\\' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <Layers className="w-6 h-6 text-emerald-400" /> Master Markdown Ledgers
        </h2>
        <p className="text-xs text-gray-400 mt-1">Direct view of all centralized chronological record archives.</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {recordsList.map(rec => (
          <button
            key={rec.key}
            onClick={() => setSelectedRecord(rec.key)}
            className={`px-4 py-2 rounded-xl text-xs font-semibold font-mono transition-all ${
              selectedRecord === rec.key
                ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/20'
                : 'bg-slate-900 text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            {rec.label}
          </button>
        ))}
      </div>

      <div className="bg-slate-950 p-6 rounded-2xl border border-gray-800">
        <div className="flex justify-between items-center mb-4 text-xs font-mono text-gray-400 border-b border-gray-800 pb-3">
          <span>Active View: <strong className="text-emerald-400">{recordsList.find(r => r.key === selectedRecord)?.label}</strong></span>
          <span>Path: {recordsList.find(r => r.key === selectedRecord)?.path}</span>
        </div>

        <pre className="text-gray-300 text-xs font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto max-h-[600px] p-4 bg-black/60 rounded-xl border border-gray-800/80">
          {data ? data[selectedRecord] : 'No record content found.'}
        </pre>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// 4. INTERACTIVE STUDY GUIDE & QUIZ PANEL
// ----------------------------------------------------------------------
function InteractiveStudyGuidePanel({ backendUrl }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [score, setScore] = useState(0);
  const [showExplanation, setShowExplanation] = useState(false);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    const fetchQuiz = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/dictionary/quiz`);
        const json = await res.json();
        if (res.ok && json.data) setQuestions(json.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchQuiz();
  }, [backendUrl]);

  if (loading) return <div className="text-amber-400 p-12 text-center animate-pulse font-mono">Preparing Study Guide Quiz...</div>;
  if (questions.length === 0) return <div className="text-gray-400 p-6">No study guide questions available.</div>;

  const q = questions[currentIndex];

  const handleSelectOption = (idx) => {
    if (selectedOption !== null) return;
    setSelectedOption(idx);
    setShowExplanation(true);
    if (idx === q.answerIndex) {
      setScore(score + 1);
    }
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setSelectedOption(null);
      setShowExplanation(false);
    } else {
      setCompleted(true);
    }
  };

  const handleRestart = () => {
    setCurrentIndex(0);
    setSelectedOption(null);
    setShowExplanation(false);
    setScore(0);
    setCompleted(false);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-extrabold text-white flex items-center justify-center gap-2">
          <GraduationCap className="w-8 h-8 text-amber-400" /> AI-BS Milestone Study Guide & Mastery Quiz
        </h2>
        <p className="text-xs text-gray-400">Test your mastery of sub-3µs SHM latency, Thoughtful Friction gates, and ATR risk calculations.</p>
      </div>

      {!completed ? (
        <div className="bg-slate-900/90 backdrop-blur-md p-8 rounded-3xl border border-gray-800 space-y-6 shadow-2xl">
          <div className="flex justify-between items-center text-xs font-mono text-gray-400 border-b border-gray-800 pb-4">
            <span>Question {currentIndex + 1} of {questions.length}</span>
            <span className="text-amber-400 font-bold">Current Score: {score}</span>
          </div>

          <h3 className="text-xl font-bold text-white leading-snug">
            {q.question}
          </h3>

          <div className="space-y-3">
            {q.options.map((opt, idx) => {
              let btnStyle = "bg-slate-950 hover:bg-slate-800 border-gray-800 text-gray-300";
              if (selectedOption !== null) {
                if (idx === q.answerIndex) {
                  btnStyle = "bg-emerald-950/80 border-emerald-500 text-emerald-300 font-bold";
                } else if (idx === selectedOption) {
                  btnStyle = "bg-red-950/80 border-red-500 text-red-300 font-bold";
                }
              }
              return (
                <button
                  key={idx}
                  onClick={() => handleSelectOption(idx)}
                  className={`w-full text-left p-4 rounded-xl border text-sm transition-all flex items-center justify-between ${btnStyle}`}
                >
                  <span>{opt}</span>
                  {selectedOption !== null && idx === q.answerIndex && <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
                  {selectedOption !== null && idx === selectedOption && idx !== q.answerIndex && <XCircle className="w-5 h-5 text-red-400 shrink-0" />}
                </button>
              );
            })}
          </div>

          {showExplanation && (
            <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200 space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-amber-300">
                <HelpCircle className="w-4 h-4" /> Architectural Rationale
              </div>
              <p>{q.explanation}</p>
            </div>
          )}

          {selectedOption !== null && (
            <div className="flex justify-end pt-4">
              <button
                onClick={handleNext}
                className="px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold rounded-xl text-sm transition-all flex items-center gap-2"
              >
                {currentIndex < questions.length - 1 ? 'Next Question' : 'View Final Score'} <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-slate-900/90 backdrop-blur-md p-10 rounded-3xl border border-amber-500/30 text-center space-y-6 shadow-2xl">
          <div className="w-20 h-20 bg-amber-500/20 text-amber-400 rounded-full flex items-center justify-center mx-auto border-2 border-amber-400">
            <GraduationCap className="w-10 h-10" />
          </div>
          <h3 className="text-3xl font-extrabold text-white">Quiz Complete!</h3>
          <p className="text-gray-300 text-lg">
            You scored <strong className="text-amber-400 text-2xl font-mono">{score}</strong> out of <strong className="text-white text-2xl font-mono">{questions.length}</strong>.
          </p>
          <button
            onClick={handleRestart}
            className="px-8 py-3 bg-amber-500 hover:bg-amber-600 text-black font-extrabold rounded-xl text-sm transition-all"
          >
            Restart Mastery Study Guide
          </button>
        </div>
      )}
    </div>
  );
}
```

*End of DefinitionsModuleTab.jsx*

---
