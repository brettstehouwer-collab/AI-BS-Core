import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getApiBase } from '../config/api.js';
import { db, auth } from '../firebase.js';
import { collection, doc, getDoc, setDoc, deleteDoc } from 'firebase/firestore';

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
  try {
    const raw = localStorage.getItem('ai-bs-osint-vault-storage');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.state?.BACKEND_URL) {
        const isMobileOrHttps = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || 
          window.location.protocol === 'capacitor:' || 
          window.location.protocol === 'https:' ||
          !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
        if (isMobileOrHttps && (parsed.state.BACKEND_URL.includes('127.0.0.1') || parsed.state.BACKEND_URL.includes('localhost'))) {
          parsed.state.BACKEND_URL = 'https://api.brettstehouwer.live';
          localStorage.setItem('ai-bs-osint-vault-storage', JSON.stringify(parsed));
        }
      }
    }
  } catch (e) {}
  window.__setBackendUrl = (url) => useAppStore.getState().setBackendUrl(url);
}

import { masterHubs } from './navigationConfig';

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
  currentUser: null,
  setCurrentUser: (user) => set({ currentUser: user }),

  // ── Team Chat & Presence State ──────────────────────────────────────────
  teamUsers: [],
  setTeamUsers: (users) => set({ teamUsers: users }),
  isChatDrawerOpen: false,
  setIsChatDrawerOpen: (isOpen) => set({ isChatDrawerOpen: isOpen }),
  activeChatChannel: 'general',
  setActiveChatChannel: (channel) => set({ activeChatChannel: channel }),

  // ── Navigation State ────────────────────────────────────────────────────
  activeTab: 'dashboard',
  setActiveTab: (activeTab) => set({ activeTab }),
  phaseStep: -1,
  setPhaseStep: (phaseStep) => set({ phaseStep }),

  // ── Layout Edit State ───────────────────────────────────────────────────
  isEditingLayout: false,
  toggleEditMode: () => set((state) => ({ isEditingLayout: !state.isEditingLayout })),
  setEditingLayout: (val) => set({ isEditingLayout: val }),
  navigationLayout: masterHubs,
  setNavigationLayout: (layout) => set({ navigationLayout: layout }),
  reorderMasterHubs: (newHubs) => set({ navigationLayout: newHubs }),
  reorderSubTabs: (hubKey, newSubTabs) => set((state) => {
    const newLayout = state.navigationLayout.map(hub => {
      if (hub.key === hubKey) {
        return { ...hub, subTabs: newSubTabs };
      }
      return hub;
    });
    return { navigationLayout: newLayout };
  }),

  // ── Global Widget Layouts (Phase 4) ─────────────────────────────────────
  globalWidgetLayouts: {},
  setGlobalWidgetLayouts: (layouts) => set({ globalWidgetLayouts: layouts }),
  fetchGlobalLayouts: async () => {
    try {
      const docRef = doc(db, 'global_ui_layouts', 'tabs');
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        set({ globalWidgetLayouts: docSnap.data() });
      } else {
        set({ globalWidgetLayouts: {} });
      }
    } catch (e) {
      console.error('Failed to fetch global layouts:', e);
    }
  },
  saveGlobalLayout: async (tabKey, layout) => {
    try {
      const current = useAppStore.getState().globalWidgetLayouts;
      const newLayouts = { ...current, [tabKey]: layout };
      set({ globalWidgetLayouts: newLayouts });
      
      const docRef = doc(db, 'global_ui_layouts', 'tabs');
      await setDoc(docRef, newLayouts, { merge: true });
    } catch (e) {
      console.error('Failed to save global layout:', e);
    }
  },
  resetGlobalLayout: async (tabKey) => {
    try {
      const current = { ...useAppStore.getState().globalWidgetLayouts };
      delete current[tabKey];
      set({ globalWidgetLayouts: current });
      
      const docRef = doc(db, 'global_ui_layouts', 'tabs');
      await setDoc(docRef, current); // Override with the deleted key removed
    } catch (e) {
      console.error('Failed to reset global layout:', e);
    }
  },
  
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
  partialize: (state) => ({ osintVaultItems: state.osintVaultItems }),
  onRehydrateStorage: () => (state) => {
    if (state) {
      const isMobileOrHttps = typeof window !== 'undefined' && (
        /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || 
        window.location.protocol === 'capacitor:' || 
        window.location.protocol === 'https:' ||
        !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform())
      );
      if (isMobileOrHttps && (!state.BACKEND_URL || state.BACKEND_URL.includes('127.0.0.1') || state.BACKEND_URL.includes('localhost'))) {
        state.BACKEND_URL = 'https://api.brettstehouwer.live';
      }
    }
  }
}));
