import type { User } from 'firebase/auth';
export type Update<T> = T | ((previous: T) => T);
export interface ChatAttachment { name: string; type: string; size?: number; url?: string; path?: string; content?: string; encoding?: string; isLocal?: boolean; localText?: string; previewUrl?: string; ext?: string; is_image?: boolean }
export interface ToolTrace { tool_name?: string; name?: string; tool?: string; arguments?: Record<string, unknown>; status?: string }
export interface PlanData {plan_id: string; title?: string; summary?: string; affected_files?: string[]; steps?: {step_num: number; description: string; risk?: string}[]}
export interface MissionData {mission_id?: string; goal?: string; status?: string; completed_tasks?: number; total_tasks?: number; total_duration_ms?: number; error?: string; tasks?: {task_id: number; title: string; phase?: number; status?: string; duration_ms?: number; result?: unknown}[]}
export interface GrillSession {grill_id?: string; status?: string; spec_locked?: boolean; proposal?: string; spec_content?: string; context_explored?: {summary?: string; verified_files?: {name: string; path: string}[]; verified_schemas?: string[]}; questions?: {branch: string; question: string; recommendation: string}[]; decisions_agreed?: unknown[]}
export interface ChatMessage {
  role: string; content: string; context?: string | null; isComfyLoading?: boolean; comfyImageUrl?: string; id?: string | number; timestamp?: string | number;
  attachments?: ChatAttachment[]; client_elapsed_ms?: number; codingTaskId?: string;
  displayContent?: string; editorData?: {path: string; content: string; lines?: number}; execution_time_ms?: number | null;
  meta?: {coding_task_id?: string}; model?: string; tool_trace?: ToolTrace;
  decision_context?: Record<string, unknown>; grillData?: GrillSession; grillHelpExamples?: string[];
  missionData?: MissionData; planData?: PlanData;
  [field: string]: unknown;
}
export interface Model { id?: string; name?: string; type: string; [field: string]: unknown }
export interface VaultItem { id: string; timestamp: number; source: string; category: string; data: unknown }
export interface TeamUser { id: string; email: string; displayName: string; isOnline: boolean; activeTab?: string | null; lastSeen?: number | string | { seconds: number } | import("firebase/firestore").Timestamp }
export interface KnowledgeDocument { id?: string; name: string; filename?: string; size?: number; content?: string; [field: string]: unknown }
export interface KnowledgeResult { text?: string; content: string; source: string; distance: number; score?: number; [field: string]: unknown }
export interface GalleryItem { id?: string; url?: string; type?: string; filename?: string; [field: string]: unknown }
export interface AgentSummary { agent?: string; pid?: number; ram_usage?: number; id?: string; name?: string; status?: string; [field: string]: unknown }
export interface LostPropertyAccount { category: string; [field: string]: unknown }
export interface AppStore {
  comfyuiStatus: { status: string; gpu: string; vram_total: number; vram_free: number };
  setComfyuiStatus(value: AppStore["comfyuiStatus"]): void;
  efficiencyMode: boolean;
  loggedIn: boolean;
  currentUser: User | null;
  teamUsers: TeamUser[];
  isChatDrawerOpen: boolean;
  activeChatChannel: string;
  activeTab: string;
  phaseStep: number;
  isEditingLayout: boolean;
  transitioning: boolean;
  chatMessages: ChatMessage[];
  footerInput: string;
  messageFeedRef: HTMLDivElement | null;
  exportCode: string;
  exportLanguage: string;
  devChatInput: string;
  devChatMessages: ChatMessage[];
  devLeftTab: string;
  devBottomTab: string;
  devMode: boolean;
  devFileName: string;
  devCodeInput: string;
  devCodeOutput: string;
  devCodeType: string;
  gitStatus: string;
  systemGitStatus: string;
  psCommand: string;
  psOutput: string;
  isExecutingPs: boolean;
  isExecutingCode: boolean;
  selectedModel: string;
  aiProvider: string;
  aiProviderModels: Record<string, string[]>;
  aiProviderSelectionRevision: number;
  setAIProviderSelection(provider: string, model: string): void;
  setAIProviderConfiguration(configuration: import('../src/utils/bsChatProvider.js').BSChatProviderConfig, expectedRevision?: number): void;
  availableModels: string[];
  comfyuiModels: string[];
  isGeneratingNocoCode: boolean;
  deployMessage: string | null;
  isDeploying: boolean;
  genDimensionality: string;
  genPhysicsTarget: string;
  genObjective: string;
  mediaType: string;
  mediaPrompt: string;
  mediaAspectRatio: string;
  mediaResultUrl: string | null;
  mediaError: string | null;
  isCreatingMedia: boolean;
  localGenProgress: number;
  localAiWidth: number;
  localAiHeight: number;
  localAiSteps: number;
  localAiCfgScale: number;
  localAiNegativePrompt: string;
  localAiSeed: number;
  selectedComfyModel: string;
  localSimMode: string;
  localSimTheme: string;
  localSimDuration: number;
  documents: string[];
  kbSearchQuery: string;
  kbSearchResults: KnowledgeResult[];
  isUploading: boolean;
  isPreviewLoading: boolean;
  previewDocName: string | null;
  previewDocContent: string | null;
  isChatUploading: boolean;
  fileInputRef: HTMLInputElement | null;
  monacoRef: unknown;
  canvasRef: HTMLCanvasElement | null;
  nocoAlert: string | null;
  nocoCodePrompt: string;
  nocoCodeType: string;
  nocoGeneratedCode: string;
  isItActive: boolean;
  itTimer: number;
  isGrading: boolean;
  itScorecard: Record<string, unknown> | null;
  fireProfile: string;
  fireTextRaw: string;
  fireTextFormatted: string;
  isFormatting: boolean;
  isEnhancingPrompt: boolean;
  leads: Record<string, unknown>[];
  loading: boolean;
  pollingStatusMsg: string;
  ssdRamPath: string;
  ssdRamSize: number;
  ssdRamCount: number;
  isSsdLoading: boolean;
  pullModelInput: string;
  pullingStatus: Record<string, {status: string; progress: number; log: string}>;
  activeAgents: AgentSummary[];
  telegramToken: string;
  safetySkipPermissions: boolean;
  customLoopTime: string;
  customLoopTask: string;
  workflowMode: string;
  galleryMedia: GalleryItem[];
  osintVaultItems: VaultItem[];
  rapidApiIsFetching: boolean;
  rapidApiResultData: unknown;
  rapidApiError: string;
  lostPropertyLoading: boolean;
  lostPropertyAccounts: LostPropertyAccount[];
  lostPropertyScanStatus: string;
  lostPropertyError: string | null;
  lostPropertyWebLoading: boolean;
  lostPropertyWebResults: Record<string, unknown>[];
  lostPropertyWebError: string | null;
  BACKEND_URL: string;
  telemetry: typeof import('../components/useAppStore').defaultTelemetry;
  navigationLayout: typeof import('../components/navigationConfig').masterHubs;
  globalWidgetLayouts: Record<string, import("react-grid-layout").Layout>;
  nocoTelemetry: { temp: number; mfcOutput: number; aeroponicLayers: number; co2: number; lux: number; ph: number };
  setBackendUrl: (value: string) => void;
  setEfficiencyMode: (value: boolean) => void;
  setLoggedIn: (value: boolean) => void;
  setCurrentUser: (value: User | null) => void;
  setTeamUsers: (value: TeamUser[]) => void;
  setIsChatDrawerOpen: (value: boolean) => void;
  setActiveChatChannel: (value: string) => void;
  setActiveTab: (value: string) => void;
  setPhaseStep: (value: number) => void;
  setEditingLayout: (value: boolean) => void;
  setNavigationLayout: (value: typeof import('../components/navigationConfig').masterHubs) => void;
  setGlobalWidgetLayouts: (value: Record<string, import("react-grid-layout").Layout>) => void;
  setTransitioning: (value: boolean) => void;
  setExportCode: (value: string) => void;
  setExportLanguage: (value: string) => void;
  setDevChatInput: (value: string) => void;
  setDevLeftTab: (value: string) => void;
  setDevBottomTab: (value: string) => void;
  setDevMode: (value: boolean) => void;
  setDevFileName: (value: string) => void;
  setDevCodeInput: (value: string) => void;
  setDevCodeOutput: (value: string) => void;
  setDevCodeType: (value: string) => void;
  setGitStatus: (value: Update<string>) => void;
  setSystemGitStatus: (value: Update<string>) => void;
  setPsCommand: (value: string) => void;
  setPsOutput: (value: Update<string>) => void;
  setIsExecutingPs: (value: boolean) => void;
  setIsExecutingCode: (value: boolean) => void;
  setSelectedModel: (value: string) => void;
  setAvailableModels: (value: string[]) => void;
  setComfyuiModels: (value: string[]) => void;
  setIsGeneratingNocoCode: (value: boolean) => void;
  setDeployMessage: (value: string | null) => void;
  setIsDeploying: (value: boolean) => void;
  setGenDimensionality: (value: string) => void;
  setGenPhysicsTarget: (value: string) => void;
  setGenObjective: (value: string) => void;
  setMediaType: (value: string) => void;
  setMediaPrompt: (value: string) => void;
  setMediaAspectRatio: (value: string) => void;
  setMediaResultUrl: (value: string | null) => void;
  setMediaError: (value: string | null) => void;
  setIsCreatingMedia: (value: boolean) => void;
  setLocalGenProgress: (value: number) => void;
  setLocalAiWidth: (value: number) => void;
  setLocalAiHeight: (value: number) => void;
  setLocalAiSteps: (value: number) => void;
  setLocalAiCfgScale: (value: number) => void;
  setLocalAiNegativePrompt: (value: string) => void;
  setLocalAiSeed: (value: number) => void;
  setSelectedComfyModel: (value: string) => void;
  setLocalSimMode: (value: string) => void;
  setLocalSimTheme: (value: string) => void;
  setLocalSimDuration: (value: number) => void;
  setDocuments: (value: string[]) => void;
  setKbSearchQuery: (value: string) => void;
  setKbSearchResults: (value: KnowledgeResult[]) => void;
  setIsUploading: (value: boolean) => void;
  setIsPreviewLoading: (value: boolean) => void;
  setPreviewDocName: (value: string | null) => void;
  setPreviewDocContent: (value: string | null) => void;
  setIsChatUploading: (value: boolean) => void;
  setNocoTelemetry: (value: { temp: number; mfcOutput: number; aeroponicLayers: number; co2: number; lux: number; ph: number }) => void;
  setNocoAlert: (value: string | null) => void;
  setNocoCodePrompt: (value: string) => void;
  setNocoCodeType: (value: string) => void;
  setNocoGeneratedCode: (value: string) => void;
  setIsItActive: (value: boolean) => void;
  setItTimer: (value: number) => void;
  setIsGrading: (value: boolean) => void;
  setItScorecard: (value: Record<string, unknown> | null) => void;
  setFireProfile: (value: string) => void;
  setFireTextRaw: (value: string) => void;
  setFireTextFormatted: (value: string) => void;
  setIsFormatting: (value: boolean) => void;
  setIsEnhancingPrompt: (value: boolean) => void;
  setLeads: (value: Record<string, unknown>[]) => void;
  setLoading: (value: boolean) => void;
  setPollingStatusMsg: (value: string) => void;
  setSsdRamPath: (value: string) => void;
  setSsdRamSize: (value: number) => void;
  setSsdRamCount: (value: number) => void;
  setIsSsdLoading: (value: boolean) => void;
  setPullModelInput: (value: string) => void;
  setPullingStatus: (value: Update<AppStore["pullingStatus"]>) => void;
  setActiveAgents: (value: Update<AgentSummary[]>) => void;
  setTelegramToken: (value: string) => void;
  setSafetySkipPermissions: (value: boolean) => void;
  setCustomLoopTime: (value: string) => void;
  setCustomLoopTask: (value: string) => void;
  setWorkflowMode: (value: string) => void;
  setGalleryMedia: (value: GalleryItem[]) => void;
  setOsintVaultItems: (value: VaultItem[]) => void;
  setRapidApiIsFetching: (value: boolean) => void;
  setRapidApiResultData: (value: unknown) => void;
  setRapidApiError: (value: string) => void;
  setLostPropertyLoading: (value: boolean) => void;
  setLostPropertyAccounts: (value: LostPropertyAccount[]) => void;
  setLostPropertyScanStatus: (value: string) => void;
  setLostPropertyError: (value: string | null) => void;
  setLostPropertyWebLoading: (value: boolean) => void;
  setLostPropertyWebResults: (value: Record<string, unknown>[]) => void;
  setLostPropertyWebError: (value: string | null) => void;
  setChatMessages(value: Update<ChatMessage[]>): void;
  setDevChatMessages(value: Update<ChatMessage[]>): void;
  setFooterInput(value: Update<string>): void;
  setBackendUrl(value: string): void;
  toggleEfficiencyMode(): Promise<void>;
  toggleEditMode(): void;
  reorderMasterHubs(value: AppStore['navigationLayout']): void;
  reorderSubTabs(hubKey: string, tabs: AppStore['navigationLayout'][number]['subTabs']): void;
  fetchGlobalLayouts(): Promise<void>;
  saveGlobalLayout(tabKey: string, layout: import('react-grid-layout').Layout): Promise<void>;
  resetGlobalLayout(tabKey: string): Promise<void>;
  parseSources(context?: string | null): string[];
  formatTime(seconds: number): string;
  categorizeModels(models: Model[]): { chat: Model[]; image: Model[]; video: Model[]; local: Model[] };
  fetchPastSavedData(): Promise<void>;
  runRapidApiRecon(taskType: string, targetId: string, apiKey: string): Promise<void>;
  runLostPropertyScan(): Promise<void>;
  runLostPropertyWebScan(targetEmail: string, scanType: string): Promise<void>;
}



export interface ScreenplayBlock {id: string; type: string; text: string; dual?: boolean; revision?: boolean; revisionColor?: string; startsNewPage?: boolean; sourcePage?: number; runs?: any[]; notes?: any[]; attributes?: any; dualGroup?: string; dualSide?: string; editable?: boolean; edit_operations?: any[]}
export interface ScreenplayBeat {id: string; heading: string; page: number; emoji?: string; summary?: string}
export interface ScreenplayViewerHandle {scrollToPage(page: number): void; scrollToScene(beat: ScreenplayBeat): void; handleNextSearch(): void; handlePrevSearch(): void; totalPages: number; currentPage: number; matchedCount: number; activeMatchIndex: number}

export interface DocumentSavePayload {path: string; content: string; create_only?: boolean; expected_revision?: string | null}
export interface DocumentSaveAck {path: string; revision: string; unchanged?: boolean}
export interface DocumentDraftState {revision: string | null; savedContent: string | null; isNew: boolean; blocked: boolean; error: Error | null}

export interface EconomicsSummary {schema: 'aibs.economics.summary.v1'; currency: 'USD'; status: 'unavailable' | 'partial' | 'verified'; timestamp: string; window: {start: string; end: string; coverage: 'unconfirmed' | 'partial' | 'complete'}; metrics: Record<string, unknown>}
export interface EconomicsMetricPresentation {value: string; status: 'unavailable' | 'stale' | 'verified'; reason: string; source?: string; observedAt?: string; freshUntil?: string}

