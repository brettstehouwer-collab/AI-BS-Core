import React, { useState, useEffect, Suspense, lazy } from 'react';
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels';
import Sidebar from './components/Sidebar.jsx';
import TopNavbar from './components/TopNavbar.jsx';
import SubTabBar from './components/SubTabBar.jsx';

import { onAuthStateChanged } from 'firebase/auth';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { auth, db } from './firebase.js';
import { useBackendHealth } from './components/useBackendHealth.js';
import { useAppStore } from './components/useAppStore.js';
import { getUserTier, canAccessTab, ADMIN_EMAILS, USER_TIERS } from './components/accessControl.js';
import FeatureGateLockedCard from './components/FeatureGateLockedCard.jsx';
import MomAccessibilityHUD from './components/MomAccessibilityHUD.jsx';
import './components/MomMode.css';
import { setAntiTamperUser } from './utils/antiTamperGuard.js';
import { applyLayoutConfigToDom, DEFAULT_LAYOUT_CONFIG } from './components/GlobalLayoutCustomizerModal.jsx';
import MobileStehouwerChat from './components/MobileStehouwerChat.jsx';
import { isNativeMobile } from './config/api.js';
import { useUserSessionTelemetry } from './src/hooks/useUserSessionTelemetry.js';

// Loading placeholder
const TabLoader = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#888' }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>⚡</div>
      <div>Loading Subsystem...</div>
    </div>
  </div>
);

// Safe lazy import wrapper with auto-reload recovery for new production deployments
function safeLazy(importFn) {
  return lazy(() => 
    importFn().catch((err) => {
      console.warn("Failed to load component chunk, auto-reloading page for new deployment...", err);
      const lastReload = sessionStorage.getItem('chunk_reload_timestamp');
      const now = Date.now();
      if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
        sessionStorage.setItem('chunk_reload_timestamp', now.toString());
        window.location.reload();
      }
      return { default: () => <TabLoader /> };
    })
  );
}

// Lazy load modal & drawer components
const LoginModal = safeLazy(() => import('./components/LoginModal.jsx'));
const ThoughtfulFrictionModal = safeLazy(() => import('./components/ThoughtfulFrictionModal.jsx'));
const TeamChatDrawer = safeLazy(() => import('./components/TeamChatDrawer.jsx'));
const ClientBanquetPortalModal = safeLazy(() => import('./components/ClientBanquetPortalModal.jsx'));
const ClientServicePortalModal = safeLazy(() => import('./components/ClientServicePortalModal.jsx'));

// Lazy load components
const BullshitLeadMatrix = safeLazy(() => import('./components/BullshitLeadMatrix.jsx'));
const VisualScriptingTab = safeLazy(() => import('./components/VisualScriptingTab.jsx'));
const VisualWorkflowDAGTab = safeLazy(() => import('./src/components/VisualWorkflowDAGTab.jsx'));
const TerminalPanelWrapper = safeLazy(() => import('./components/TerminalPanelWrapper.jsx'));
const AutomationConsole = safeLazy(() => import('./components/AutomationConsole.jsx'));
const PhoneRepairGuideTab = safeLazy(() => import('./src/components/PhoneRepairGuideTab.jsx'));
const BibleStudyTab = safeLazy(() => import('./src/components/BibleStudyTab.jsx'));
const DashboardView = safeLazy(() => import('./components/CommandCenterTab'));
const IdeView = safeLazy(() => import('./components/SplitPaneIDEWorkspace.jsx'));
const ChatTab = safeLazy(() => import('./components/ChatTab'));

const AdvertisingTab = safeLazy(() => import('./components/AdvertisingTab'));
const SyndicationTab = safeLazy(() => import('./components/SyndicationTab.jsx'));
const StudioWorkspaceTab = safeLazy(() => import('./components/StudioWorkspaceTab.jsx'));
const VirtualMachineTab = safeLazy(() => import('./src/components/VirtualMachineTab.jsx'));
const ClientsModuleTab = safeLazy(() => import('./src/clients/ClientsModule.jsx'));
const MoneyTrackTab = safeLazy(() => import('./components/MoneyTrackTab.jsx'));
const BullshitEvolutionHistory = safeLazy(() => import('./components/BullshitEvolutionHistory.jsx'));
const BetaAnalyticsTab = safeLazy(() => import('./components/BetaAnalyticsTab'));
const AgentMemoryDashboardTab = safeLazy(() => import('./components/AgentMemoryDashboardTab.jsx'));
const UniversalCreationSuite = safeLazy(() => import('./components/UniversalCreationSuite.jsx'));
const BrettDataTab = safeLazy(() => import('./components/BrettDataTab.jsx'));
const WorkspaceCalendarTab = safeLazy(() => import('./components/WorkspaceCalendarTab.jsx'));
const StehouwerCMSTab = safeLazy(() => import('./components/StehouwerCMSTab.jsx'));
const AdminSecurityMonitorTab = safeLazy(() => import('./components/AdminSecurityMonitorTab.jsx'));
const MasterAccountingTab = safeLazy(() => import('./components/MasterAccountingTab.jsx'));
const PublicCheckoutTab = safeLazy(() => import('./components/PublicCheckoutTab.jsx'));
const PublicPlaygroundTab = safeLazy(() => import('./components/PublicPlaygroundTab.jsx'));
const PersonalBrandStudioTab = safeLazy(() => import('./components/PersonalBrandStudioTab.jsx'));
const AutomatedClientSchedulerTab = safeLazy(() => import('./components/AutomatedClientSchedulerTab.jsx'));
const DeepLearningStudioTab = safeLazy(() => import('./components/DeepLearningStudioTab.jsx'));
const ReasoningAttentionTab = safeLazy(() => import('./components/ReasoningAttentionTab.jsx'));
const VideoStreamingTab = safeLazy(() => import('./components/VideoStreamingTab.jsx'));
const DigitalStorefrontTab = safeLazy(() => import('./components/DigitalStorefrontTab.jsx'));
const GpuNetworkTab = safeLazy(() => import('./components/GpuNetworkTab.jsx'));
const DefinitionsModuleTab = safeLazy(() => import('./components/DefinitionsModuleTab.jsx'));
const CryptoSwarmMobileController = safeLazy(() => import('./components/CryptoSwarmMobileController.jsx'));
const LearningMaterialHub = safeLazy(() => import('./components/LearningMaterialHub.jsx'));
const RapidApiReconTab = safeLazy(() => import('./components/RapidApiReconTab.jsx'));
const NoCoVisionTab = safeLazy(() => import('./components/NoCoVisionTab.jsx'));
const TheatricalTeleprompter = safeLazy(() => import('./components/TheatricalTeleprompter.jsx'));
const TheatricalProjector = safeLazy(() => import('./components/TheatricalProjector.jsx'));
const LostPropertyTab = safeLazy(() => import('./components/LostPropertyTab.jsx'));
const EmailClientTab = safeLazy(() => import('./components/EmailClientTab.jsx'));
const UnifiedMediaVaultTab = safeLazy(() => import('./components/UnifiedMediaVaultTab.jsx'));
const AdminSharedDriveTab = safeLazy(() => import('./components/AdminSharedDriveTab.jsx'));
const PowerWashingTab = safeLazy(() => import('./components/PowerWashingTab.jsx'));
const ProcessMemoryLabTab = safeLazy(() => import('./components/ProcessMemoryLabTab.jsx'));

// Unified Hub Wrappers
const UnifiedOsintHub = safeLazy(() => import('./components/UnifiedOsintHub.jsx'));
const UnifiedCalendarHub = safeLazy(() => import('./components/UnifiedCalendarHub.jsx'));
const UnifiedFinancialHub = safeLazy(() => import('./components/UnifiedFinancialHub.jsx'));
const UnifiedCreationHub = safeLazy(() => import('./components/UnifiedCreationHub.jsx'));
const UnifiedCryptoHub = safeLazy(() => import('./components/UnifiedCryptoHub.jsx'));
const UnifiedSystemEconomics = safeLazy(() => import('./components/UnifiedSystemEconomics.jsx'));
const NotosEnterpriseOSTab = safeLazy(() => import('./components/NotosEnterpriseOSTab.jsx'));
const NotoBarInventoryHub = safeLazy(() => import('./components/NotoBarInventoryHub.jsx'));
const NeuralAudioStudioTab = safeLazy(() => import('./components/NeuralAudioStudioTab.jsx'));
const CampaignAutomationTab = safeLazy(() => import('./components/CampaignAutomationTab.jsx'));
const BanquetArchitectTab = safeLazy(() => import('./components/BanquetArchitectTab.jsx'));
const SystemHealthTab = safeLazy(() => import('./components/SystemHealthTab.jsx'));
const EnterpriseIndustryHubTab = safeLazy(() => import('./components/EnterpriseIndustryHubTab.jsx'));
const UnrealViewport = safeLazy(() => import('./src/components/UnrealViewport.jsx'));
const OnboardingTab = safeLazy(() => import('./components/OnboardingTab.jsx'));
const ClientsTab = safeLazy(() => import('./components/ClientsTab.jsx'));
const FuturisticNeonLoungeStudio = safeLazy(() => import('./src/components/FuturisticNeonLoungeStudio.jsx'));
const ProjectNoCoStudioTab = safeLazy(() => import('./components/ProjectNoCoStudioTab.jsx'));
const OmniStudioTab = safeLazy(() => import('./components/OmniStudioTab.jsx'));
const MusicDAWStudioTab = safeLazy(() => import('./src/components/daw/MusicDAWStudioTab.jsx'));
const EcosystemBlueprintTab = safeLazy(() => import('./src/components/EcosystemBlueprintTab.jsx'));
const LexiconTheatricalDashboard = safeLazy(() => import('./src/components/LexiconTheatricalDashboard.jsx'));
const OperationsAuditHubTab = safeLazy(() => import('./components/OperationsAuditHubTab.jsx'));
const NdaModuleTab = safeLazy(() => import('./components/NdaModuleTab.jsx'));
const MediaStudioTab = safeLazy(() => import('./components/MediaStudioTab.jsx'));

class TabErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("Tab ErrorBoundary caught error:", error, errorInfo);
    const errStr = error?.toString() || '';
    if (errStr.includes("Failed to fetch dynamically imported module") || errStr.includes("Importing a module script failed")) {
      const lastReload = sessionStorage.getItem('chunk_reload_timestamp');
      const now = Date.now();
      if (!lastReload || now - parseInt(lastReload, 10) > 10000) {
        sessionStorage.setItem('chunk_reload_timestamp', now.toString());
        window.location.reload();
      }
    }
  }
  render() {
    if (this.state.hasError) {
      const isChunkError = this.state.error?.toString().includes("Failed to fetch dynamically imported module");
      return (
        <div style={{ padding: '30px', color: '#ff7b72', background: '#161b22', borderRadius: '12px', border: '1px solid #f85149', margin: '20px' }}>
          <h3 style={{ margin: '0 0 10px 0' }}>⚠️ Subsystem Rendering Error</h3>
          <p style={{ color: '#c9d1d9', fontSize: '0.95rem' }}>
            {isChunkError 
              ? "A new version of AI-BS Dashboard was deployed! Clicking update will load the latest release assets." 
              : "An unexpected error occurred while rendering this tab view:"}
          </p>
          <pre style={{ background: '#0d1117', padding: '12px', borderRadius: '8px', overflowX: 'auto', fontSize: '0.85rem', color: '#ff7b72' }}>
            {this.state.error?.toString()}
          </pre>
          <button 
            onClick={() => {
              if (isChunkError) {
                window.location.reload();
              } else {
                this.setState({ hasError: false, error: null });
              }
            }} 
            style={{ background: '#238636', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', marginTop: '10px', fontWeight: 'bold' }}
          >
            🔄 {isChunkError ? "Update & Reload Dashboard" : "Retry Tab View"}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const ACTIVE_TAB_STORAGE_KEY = 'sp-ai-active-tab';

const tabs = [
  { key: 'dashboard', label: 'Command Center', description: 'System overview and live status at a glance', Component: DashboardView },
  { key: 'operations_audit', label: 'Omni Operations & Live Audit Hub', description: 'Live User Tasks, Media Queue, Continuous Autosaves, Admin Vault & Daemon Error Diagnostics', Component: OperationsAuditHubTab },
  { key: 'workflow_dag', label: '⚡ Multi-Agent DAG Builder', description: 'Visual Node-Based Autonomous Agent Pipeline & DAG Builder', Component: VisualWorkflowDAGTab },
  { key: 'shared_cloud_drive', label: 'Shared Cloud Drive', description: 'Google Drive-Style Cloud Storage, Document Creator & Asset Sharing', Component: AdminSharedDriveTab },
  { key: 'power_washing', label: 'Prestige Mobile Wash', description: 'Commercial & Residential Pressure Washing CRM, Chemical Estimator & Fleet Portal', Component: PowerWashingTab },
  { key: 'phone_repair', label: '🔧 Phone & Tablet Repair Lab', description: 'Master technical teardowns, Face ID serialization & diagnostic trees for Apple, Android & Tablets', Component: PhoneRepairGuideTab },
  { key: 'bible_hub', label: '📖 Sovereign Bible Hub', description: 'Dual KJV & NIV Canonical New Testament Reader, Parallel Comparison & Verse Concordance', Component: BibleStudyTab },
  { key: 'system_health', label: 'System Health & Logs', description: 'Real-time SSE Logs and SQLite Audit', Component: SystemHealthTab },
  { key: 'onboarding', label: 'Client Onboarding', description: 'Smart Onboarding Portal', Component: OnboardingTab },
  { key: 'client_directory', label: 'Client Directory', description: 'Live Client Directory', Component: ClientsTab },
  { key: 'system_economics', label: 'System Economics', description: 'Analyze system telemetry vs LLM costs & Agency revenue', Component: UnifiedSystemEconomics },
  { key: 'unified_crypto', label: 'Crypto & Mining Suite', description: 'Trading, Harvesting, and Network Hardware Control', Component: UnifiedCryptoHub },
  { key: 'security_monitor', label: 'Admin Security & Telemetry Interceptor', description: 'Live hardware stream and process monitoring', Component: AdminSecurityMonitorTab },
  { key: 'vms', label: 'Virtual Machines', description: 'Interact with local virtual machines via VNC', Component: VirtualMachineTab },
  { key: 'ide', label: 'BS-CHAT Interface', description: 'Split-Pane Code Editor & Telemetry Hub', Component: IdeView },
  { key: 'creation_suite', label: 'Creation Suite', description: 'Universal creation workspace', Component: UniversalCreationSuite },
  { key: 'leadmatrix', label: 'Lead Matrix', description: 'Inspect generated acquisition leads and sweep the matrix', Component: BullshitLeadMatrix },
  { key: 'terminal', label: 'Terminal', description: 'Interactive virtual terminal shell', Component: TerminalPanelWrapper },
  { key: 'automation_console', label: 'Automation Console', description: 'Trusted local Windows automation runner and live job queue', Component: AutomationConsole },
  { key: 'advertising', label: 'Advertising', description: 'Local business lead management and AI ad copy', Component: AdvertisingTab },
  { key: 'syndication', label: '🌐 Automated Syndication', description: '1-Click Fire Send Broadcaster & Multi-Channel Ad Suite', Component: SyndicationTab },
  { key: 'clients', label: 'Clients Hub', description: 'Master Workspace for all clients', Component: ClientsModuleTab },
  { key: 'nda_module', label: '📜 Sovereign NDA & Anti-Tamper', description: 'Interactive Master NDA Signer, Clause Reviewer, Watermarking & Cryptographic Tamper Seal', Component: NdaModuleTab },
  { key: 'moneytrack', label: 'Money Track', description: 'Financial dashboard for revenue, expenses, and invoices', Component: MoneyTrackTab },
  { key: 'definitions', label: 'Definitions & Lore', description: 'Interactive AI-BS dictionary and architectural timeline', Component: DefinitionsModuleTab },
  { key: 'beta', label: '📈 Web Traffic & Telemetry', description: 'Stehouwer Web Traffic, Wire Packet Hashes & Over-The-Air Wave Telemetry', Component: BetaAnalyticsTab },
  { key: 'agent_memory', label: 'Agent Memory', description: 'Vector Memory Dashboard and Danger Zone', Component: AgentMemoryDashboardTab },
  { key: 'public_checkout', label: 'Pricing & Passes', description: '1-Click PayPal Compute Passes', Component: PublicCheckoutTab },
  { key: 'digital_storefront', label: 'Digital Storefront', description: 'Monetize local AI infrastructure via micro-SaaS and credit tools', Component: DigitalStorefrontTab },
  { key: 'public_playground', label: 'AI Studio & Playground', description: 'Isolated Public Creator Studio', Component: PublicPlaygroundTab },
  { key: 'personal_brand', label: 'Personal Brand Studio', description: 'AI-assisted social media Ghostwriter optimized for organic reach', Component: PersonalBrandStudioTab },
  { key: 'calendar', label: 'Workspace Calendar', description: 'Stehouwer Publishing Master Schedule', Component: WorkspaceCalendarTab },
  { key: 'client_scheduler', label: 'Client Content Scheduler', description: 'Weekly Social Media Automation', Component: AutomatedClientSchedulerTab },
  { key: 'deep_learning_studio', label: 'Deep Learning Studio', description: 'Define-by-Run Dynamic Computation Graphs', Component: DeepLearningStudioTab },
  { key: 'reasoning_attention', label: 'Self-Refinement & Attention Studio', description: 'Self-Attention Heatmaps & Contextual Encodings', Component: ReasoningAttentionTab },
  { key: 'stehouwer_cms', label: 'Stehouwer CMS', description: 'Live Content Management System', Component: StehouwerCMSTab },
  { key: 'brett_data_hub', label: 'Brett Stehouwer Data', description: 'Data testing and organization hub', Component: BrettDataTab },
  { key: 'master_accounting', label: 'Master Accounting & Taxes', description: 'Excel-Style Spreadsheet Ledger & US Tax Suite', Component: MasterAccountingTab },
  { key: 'api_recon', label: 'RapidAPI Recon', description: 'OSINT Data & API Hub', Component: RapidApiReconTab },
  { key: 'learning_material_hub', label: 'Educational Modules', description: 'Information explainers and learning material', Component: LearningMaterialHub },
  { key: 'noco_vision', label: 'Project NoCo & Living Stage Studio', description: 'Autonomous Acoustic-Agricultural Enclave & Living Stage Studio', Component: ProjectNoCoStudioTab },
  { key: 'lost_property', label: 'Lost Property', description: 'Surf your email history to discover forgotten accounts', Component: LostPropertyTab },
  { key: 'email_client', label: 'Local Email', description: 'Integrated IMAP Email Client', Component: EmailClientTab },
  { key: 'unified_osint', label: 'OSINT Recon & API Hub', description: 'Unified Intelligence Suite', Component: UnifiedOsintHub },
  { key: 'unified_calendar', label: 'Master Calendar & Scheduler', description: 'Unified Scheduling Suite', Component: UnifiedCalendarHub },
  { key: 'unified_financial', label: 'Financial Ledger & Yields', description: 'Unified Financial Suite', Component: UnifiedFinancialHub },
  { key: 'unified_creation', label: 'Universal Screenwriting Studio', description: 'Universal creation workspace', Component: UniversalCreationSuite },
  { key: 'notos_enterprise', label: "Noto's Enterprise OS", description: "Internal Hospitality Operating Platform for Grand Rapids & Grand Haven", Component: NotosEnterpriseOSTab },
  { key: 'noto_inventory', label: 'Notō Multi-Bar Stock & Dispatch', description: 'Live Multi-Bar Inventory, Barback Dispatch & MLCC Distributor PO Engine', Component: NotoBarInventoryHub },
  { key: 'banquet_architect', label: 'Banquet Architect Studio', description: '2D Generative & 3D Unreal Engine Studio', Component: BanquetArchitectTab },
  { key: 'industry_grid', label: '70-Vertical Module Grid', description: 'Enterprise Expansion Suite', Component: EnterpriseIndustryHubTab },
  { key: 'campaign_automation', label: 'Campaign & Audience Engine', description: 'Mailchimp-Style Event Campaign Automation & Telemetry', Component: CampaignAutomationTab },
  { key: 'unified_media_gallery', label: 'Unified Media Gallery', description: 'Unified Media and Asset Vault', Component: UnifiedMediaVaultTab },
  { key: 'neon_lounge_studio', label: 'Neon Lounge Studio', description: 'Futuristic Neon Lounge Architectural Design Studio & AI Autograd Engine', Component: FuturisticNeonLoungeStudio },
  { key: 'project_noco', label: 'Project NoCo & Living Stage Studio', description: 'Autonomous Acoustic-Agricultural Enclave & Living Stage Studio', Component: ProjectNoCoStudioTab },
  { key: 'universal_studio', label: 'Universal AV Studio', description: 'Master Broadcast, Video WebRTC, DAW & Neural Voice Engine', Component: OmniStudioTab },
  { key: 'media_studio', label: '🎬 Autonomous Media Studio', description: 'Autonomous Headless Media Production Studio, 13-Domain NLE & Visual Editor', Component: MediaStudioTab },
  { key: 'music_daw', label: 'FL Music Studio (DAW)', description: 'Pattern-based Digital Audio Workspace & FL Studio-Style Beat Maker', Component: MusicDAWStudioTab },
  { key: 'workflow_dag', label: '⚡ Multi-Agent DAG Builder', description: 'Autonomous 5-Node Visual Pipeline Engine', Component: VisualWorkflowDAGTab },
  { key: 'ecosystem_blueprint', label: 'Matrix Blueprint & ROI', description: 'Interactive Ecosystem Architecture, 5-Pillar Matrix & Financial ROI Simulator', Component: EcosystemBlueprintTab },
  { key: 'lexicon_dashboard', label: '🎭 Lexicon Engine Dashboard', description: 'Real-time semantic expansion and Persona trigger visualization', Component: LexiconTheatricalDashboard },
  { key: 'gaming_lab', label: '🎮 Gaming & Process Memory Lab', description: 'Win32 Runtime Memory Manipulation, Pointer Tracking & Game Trainer Suite', Component: ProcessMemoryLabTab }
];

export default function App() {
  const selectedModel = useAppStore(state => state.selectedModel);
  const setSelectedModel = useAppStore(state => state.setSelectedModel);
  const availableModels = useAppStore(state => state.availableModels);
  const setAvailableModels = useAppStore(state => state.setAvailableModels);
  const efficiencyMode = useAppStore(state => state.efficiencyMode);
  const isEditingLayout = useAppStore(state => state.isEditingLayout);
  const toggleEditMode = useAppStore(state => state.toggleEditMode);
  const [zenMode, setZenMode] = useState(false);
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlTab = params.get('tab') || (params.get('portal') === 'nda' ? 'nda_module' : null);
      if (urlTab) return urlTab;
    }
    return localStorage.getItem(ACTIVE_TAB_STORAGE_KEY) || 'dashboard';
  });
  const { backendUrl, backendStatus } = useBackendHealth();
  const [localTrustState, setLocalTrustState] = useState({ enabled: false, allowedUsers: [] });
  const [authLoading, setAuthLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const cached = localStorage.getItem('aibs_cached_user');
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  // Mobile View Mode: 'chat' (default on mobile devices/APK) vs 'desktop'
  const isMobileDevice = typeof window !== 'undefined' && (isNativeMobile() || window.innerWidth <= 768);
  const [mobileViewMode, setMobileViewMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('aibs_mobile_view_mode');
      if (saved) return saved === 'gemini' ? 'chat' : saved;
      return (isNativeMobile() || window.innerWidth <= 768) ? 'chat' : 'desktop';
    }
    return 'desktop';
  });

  const handleSetMobileViewMode = (mode) => {
    setMobileViewMode(mode);
    try {
      localStorage.setItem('aibs_mobile_view_mode', mode);
    } catch {}
  };

  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    try {
      if (typeof window !== 'undefined' && (isNativeMobile() || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
        return true;
      }
      return !!localStorage.getItem('aibs_cached_user');
    } catch {
      return false;
    }
  });
  const [viewMode, setViewMode] = useState('2D');
  const [workspaceMode, setWorkspaceMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const view = params.get('view') || params.get('mode');
      if (view === 'simple' || view === 'pro') return view;
      const saved = localStorage.getItem('aibs_workspace_mode');
      if (saved === 'simple' || saved === 'pro') return saved;
    }
    return 'simple';
  });

  const handleToggleWorkspaceMode = () => {
    const nextMode = workspaceMode === 'simple' ? 'pro' : 'simple';
    setWorkspaceMode(nextMode);
    localStorage.setItem('aibs_workspace_mode', nextMode);
  };

  useEffect(() => {
    const readLocalTrustState = async () => {
      try {
        if (typeof window !== 'undefined' && window.aibsAutomation?.getLocalTrustState) {
          const state = await window.aibsAutomation.getLocalTrustState();
          setLocalTrustState({ enabled: !!state?.enabled, allowedUsers: Array.isArray(state?.allowedUsers) ? state.allowedUsers : [] });
          return;
        }
        const saved = localStorage.getItem('aibs_local_trust_state');
        if (!saved) {
          setLocalTrustState({ enabled: false, allowedUsers: [] });
          return;
        }
        const parsed = JSON.parse(saved);
        setLocalTrustState({ enabled: !!parsed.enabled, allowedUsers: Array.isArray(parsed.allowedUsers) ? parsed.allowedUsers : [] });
      } catch (err) {
        console.warn('[App] Failed to load local trust state:', err);
        setLocalTrustState({ enabled: false, allowedUsers: [] });
      }
    };
    readLocalTrustState();
  }, []);

  const [simulatedTier, setSimulatedTier] = useState(
    () => localStorage.getItem('aibs_preview_tier') || 'ADMIN'
  );

  // 🌸 MOM VERSION — MAXIMUM ACCESSIBILITY & READABILITY STATE
  const [momMode, setMomMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('mom') === 'true') return true;
      return localStorage.getItem('aibs_mom_mode') === 'true';
    }
    return false;
  });

  const [momZoomLevel, setMomZoomLevel] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedZoom = localStorage.getItem('aibs_mom_zoom');
      if (savedZoom) return parseInt(savedZoom, 10);
    }
    return 125;
  });

  const [activePortal, setActivePortal] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      return params.get('portal'); // 'banquet' | 'service' | null
    }
    return null;
  });

  const handleToggleMomMode = () => {
    setMomMode(prev => {
      const next = !prev;
      localStorage.setItem('aibs_mom_mode', next ? 'true' : 'false');
      return next;
    });
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const savedLayout = localStorage.getItem('aibs_layout_customizer_settings');
        if (savedLayout) {
          applyLayoutConfigToDom({ ...DEFAULT_LAYOUT_CONFIG, ...JSON.parse(savedLayout) });
        } else {
          applyLayoutConfigToDom(DEFAULT_LAYOUT_CONFIG);
        }
      } catch (e) {
        console.warn("Failed to apply initial layout config", e);
      }

      window.__aibs_toggle_mom_mode = handleToggleMomMode;
      if (momMode) {
        document.body.classList.add('mom-mode-active');
        document.documentElement.style.fontSize = `${(momZoomLevel / 100) * 16}px`;
      } else {
        document.body.classList.remove('mom-mode-active');
        document.documentElement.style.fontSize = '';
      }
    }
  }, [momMode, momZoomLevel]);

  const handleZoomChange = (newZoom) => {
    setMomZoomLevel(newZoom);
    localStorage.setItem('aibs_mom_zoom', newZoom.toString());
  };

  const handleSimulateTier = (tierKey) => {
    setSimulatedTier(tierKey);
    localStorage.setItem('aibs_preview_tier', tierKey);
  };

  const isMasterAdmin = Boolean(
    currentUser && (
      ADMIN_EMAILS.includes((currentUser.email || '').toLowerCase()) ||
      currentUser.email === 'brettstehouwer@gmail.com' ||
      (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
    )
  );

  const userTier = getUserTier(currentUser, isMasterAdmin ? simulatedTier : null);

  // Persistent Firebase Authentication State Listener
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user && user.email) {
        const email = user.email.toLowerCase();
        // Any user authenticated with Firebase or present in ADMIN_EMAILS or localhost is authorized
        const isAuthorized = Boolean(user && user.email) || ADMIN_EMAILS.includes(email) ||
          (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'));

        if (isAuthorized) {
          setIsAuthenticated(true);
          setCurrentUser(user);
          useAppStore.getState().setCurrentUser(user);
          try {
            localStorage.setItem('aibs_cached_user', JSON.stringify({
              email: user.email,
              displayName: user.displayName,
              uid: user.uid,
              photoURL: user.photoURL
            }));
          } catch (e) {
            console.warn('Failed to cache user session:', e);
          }
          setAntiTamperUser(user.email);

          // Update Firestore Presence (Online)
          if (user && user.uid && db) {
            try {
              const userRef = doc(db, 'users', user.uid);
              setDoc(userRef, {
                uid: user.uid,
                email: user.email.toLowerCase(),
                displayName: user.displayName || user.email.split('@')[0],
                photoURL: user.photoURL || '',
                role: ADMIN_EMAILS.includes(email) ? 'Master Admin' : 'Authorized Operator',
                isOnline: true,
                lastSeen: serverTimestamp()
              }, { merge: true }).catch(err => console.warn('Presence update failed', err));
            } catch (presenceErr) {
              console.warn('Presence initialization error:', presenceErr);
            }
          }

          // Trigger Real-Time Multi-Channel Login Notification Sentinel
          try {
            if (typeof window !== 'undefined' && window.sendDashboardLoginNotification) {
              window.sendDashboardLoginNotification({
                email: user.email,
                displayName: user.displayName,
                uid: user.uid,
                photoURL: user.photoURL
              });
            } else {
              const isLocalHost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
              const targetUrl = isLocalHost ? 'http://127.0.0.1:8080/api/analytics/notify-login' : 'https://api.brettstehouwer.live/api/analytics/notify-login';
              fetch(targetUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  email: user.email,
                  displayName: user.displayName || user.email.split('@')[0],
                  uid: user.uid,
                  photoURL: user.photoURL || '',
                  url: typeof window !== 'undefined' ? window.location.href : 'https://ai-bs-dashboard.web.app/',
                  timestamp: new Date().toISOString()
                }),
                keepalive: true,
                mode: 'cors'
              }).catch(() => {});
            }
          } catch (loginNotifyErr) {
            console.warn('Login notification sentinel error:', loginNotifyErr);
          }

        } else {
          setIsAuthenticated(false);
          setCurrentUser(null);
          useAppStore.getState().setCurrentUser(null);
          localStorage.removeItem('aibs_cached_user');
        }
      } else {
        if (typeof window !== 'undefined' && (isNativeMobile() || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
          setIsAuthenticated(true);
          setCurrentUser({ email: 'brettstehouwer@gmail.com', displayName: 'Brett Stehouwer (Local Admin)', uid: 'local_admin_brett' });
        } else {
          setIsAuthenticated(false);
          setCurrentUser(null);
          localStorage.removeItem('aibs_cached_user');
        }
      }
      setAuthLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Update Presence Active Tab and Offline Hook
  useEffect(() => {
    if (currentUser && currentUser.uid && db && !currentUser.uid.startsWith('local_')) {
      try {
        const userRef = doc(db, 'users', currentUser.uid);
        setDoc(userRef, { activeTab: activeTab }, { merge: true }).catch(() => {});

        const handleBeforeUnload = () => {
          setDoc(userRef, { isOnline: false, lastSeen: serverTimestamp() }, { merge: true }).catch(() => {});
        };
        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => {
          window.removeEventListener('beforeunload', handleBeforeUnload);
          setDoc(userRef, { isOnline: false, lastSeen: serverTimestamp() }, { merge: true }).catch(() => {});
        };
      } catch (err) {
        console.warn('Presence tab sync error:', err);
      }
    }
  }, [currentUser, activeTab]);

  // Live User Presence, Session Dwell-Time & Activity Telemetry
  useUserSessionTelemetry({ currentUser, activeTab });

  // Universal Deep Linking & URL Search Parameter Synchronization
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (url.searchParams.get('tab') !== activeTab) {
        url.searchParams.set('tab', activeTab);
        window.history.replaceState({ tab: activeTab }, '', url.toString());
      }
      if (window.sendDashboardAnalyticsBeacon) {
        window.sendDashboardAnalyticsBeacon('tab_switch', activeTab);
      }
    }
    localStorage.setItem(ACTIVE_TAB_STORAGE_KEY, activeTab);
  }, [activeTab]);

  // Handle Browser Back / Forward Button Navigation
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const urlTab = params.get('tab');
      if (urlTab && urlTab !== activeTab) {
        setActiveTab(urlTab);
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [activeTab]);

  useEffect(() => {
    useAppStore.getState().fetchGlobalLayouts();
  }, []);

  useEffect(() => {
    fetch(`${backendUrl}/api/models`)
      .then(res => res.json())
      .then(data => {
        let modelList = [];
        if (Array.isArray(data.models)) {
          modelList = data.models;
        } else if (Array.isArray(data.data)) {
          modelList = data.data.map(m => typeof m === 'string' ? m : (m.id || m.name));
        } else if (Array.isArray(data)) {
          modelList = data.map(m => typeof m === 'string' ? m : (m.id || m.name));
        }

        // Append Gemini backup fallback models
        const geminiModels = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash'];
        modelList = [...new Set([...modelList, ...geminiModels])];

        if (modelList.length > 0) {
          setAvailableModels(modelList);
          if (!selectedModel || !modelList.includes(selectedModel)) {
            setSelectedModel(modelList[0]);
          }
        }
      })
      .catch(err => console.error('Failed to fetch models:', err));
  }, [backendUrl, setAvailableModels, selectedModel, setSelectedModel]);

  const [navLayout, setNavLayout] = useState(
    () => localStorage.getItem('sp-ai-nav-layout') || 'top'
  );

  const handleToggleNavLayout = () => {
    const nextLayout = navLayout === 'top' ? 'sidebar' : 'top';
    setNavLayout(nextLayout);
    localStorage.setItem('sp-ai-nav-layout', nextLayout);
  };

  const activeTabConfig = tabs.find((tab) => tab.key === activeTab) ?? tabs[0];
  const ActiveComponent = activeTabConfig.Component;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const currentPath = typeof window !== 'undefined' ? window.location.pathname.toLowerCase() : '';
  const isPublicStandaloneRoute = currentPath.includes('/playground') || currentPath.includes('/checkout');
  const isNoCoStandaloneRoute = currentPath.includes('/nocovision/teleprompter') || currentPath.includes('/nocovision/projector');
  const isOverlayRoute = currentPath.includes('/overlay');
  const isMobileWriterRoute = typeof window !== 'undefined' && window.location.search.includes('standalone_writer=true');

  if (isMobileWriterRoute) {
    return (
      <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#090d16' }}>
        <TabErrorBoundary key="mobile-writer">
          <Suspense fallback={<TabLoader />}>
            <UniversalCreationSuite backendUrl={backendUrl} />
          </Suspense>
        </TabErrorBoundary>
      </div>
    );
  }

  if (isOverlayRoute) {
    const UnifiedChatOverlay = lazy(() => import('./src/components/UnifiedChat.jsx'));
    return (
      <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: 'transparent' }}>
        <TabErrorBoundary key="overlay">
          <Suspense fallback={<div style={{color:'white'}}>Loading Widget...</div>}>
            <UnifiedChatOverlay />
          </Suspense>
        </TabErrorBoundary>
      </div>
    );
  }

  if (isPublicStandaloneRoute) {
    const isCheckout = currentPath.includes('/checkout');
    return (
      <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#090d16' }}>
        <TabErrorBoundary key={isCheckout ? 'checkout' : 'playground'}>
          <Suspense fallback={<TabLoader />}>
            {isCheckout ? <PublicCheckoutTab backendUrl={backendUrl} /> : <PublicPlaygroundTab backendUrl={backendUrl} />}
          </Suspense>
        </TabErrorBoundary>
      </div>
    );
  }

  if (isNoCoStandaloneRoute) {
    const isTeleprompter = currentPath.includes('/teleprompter');
    return (
      <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#000' }}>
        <TabErrorBoundary key={isTeleprompter ? 'teleprompter' : 'projector'}>
          <Suspense fallback={<TabLoader />}>
            {isTeleprompter ? <TheatricalTeleprompter /> : <TheatricalProjector />}
          </Suspense>
        </TabErrorBoundary>
      </div>
    );
  }

  if (authLoading && !isAuthenticated) {
    return (
      <div style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#090d16',
        color: '#38bdf8',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif'
      }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '16px' }}>⚡</div>
        <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#f8fafc', letterSpacing: '0.5px' }}>
          Restoring AI-BS Secure Session...
        </div>
        <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '6px' }}>
          Verifying security perimeter credentials
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginModal 
        onLoginSuccess={(user) => {
          setIsAuthenticated(true);
          setCurrentUser(user);
          try {
            localStorage.setItem('aibs_cached_user', JSON.stringify({
              email: user.email,
              displayName: user.displayName,
              uid: user.uid,
              photoURL: user.photoURL
            }));
          } catch {}
          setAntiTamperUser(user.email);
        }} 
        backendUrl={backendUrl} 
      />
    );
  }

  // Mobile Stehouwer Chat View (Default on Phone / APK)
  if (isMobileDevice && mobileViewMode === 'chat') {
    return (
      <MobileStehouwerChat
        backendUrl={backendUrl}
        onSwitchToDesktop={() => handleSetMobileViewMode('desktop')}
        currentUser={currentUser}
      />
    );
  }

  return (
    <>
      <div className={`app-shell ${isMobileMenuOpen ? 'mobile-menu-open' : ''}`} style={{ flexDirection: navLayout === 'top' ? 'column' : 'row', height: '100vh', width: '100vw' }}>
        {!zenMode && navLayout === 'top' && (
          <TopNavbar 
            activeTab={activeTab}
            onTabChange={(t) => { setActiveTab(t); setIsMobileMenuOpen(false); }}
            navLayout={navLayout}
            onToggleNavLayout={handleToggleNavLayout}
            selectedModel={selectedModel}
            onSelectModel={setSelectedModel}
            availableModels={availableModels}
            backendStatus={backendStatus}
            localTrustEnabled={localTrustState.enabled}
            trustedUserEmails={localTrustState.allowedUsers}
            currentUser={currentUser}
            userTier={userTier}
            isAdmin={isMasterAdmin}
            simulatedTier={simulatedTier}
            onSimulateTier={handleSimulateTier}
            workspaceMode={workspaceMode}
            onToggleWorkspaceMode={handleToggleWorkspaceMode}
            momMode={momMode}
            onToggleMomMode={handleToggleMomMode}
            zoomLevel={momZoomLevel}
            onZoomChange={handleZoomChange}
            zenMode={zenMode}
            onToggleZenMode={() => setZenMode(!zenMode)}
          />
        )}

        {navLayout === 'sidebar' ? (
          <PanelGroup direction="horizontal" style={{ flex: 1, width: '100%', height: '100%', overflow: 'hidden' }}>
            {!zenMode && (
              <>
                <Panel key="sidebar-panel" id="sidebar-panel" order={1} defaultSize={15} minSize={10} maxSize={30}>
                  <aside className="sidebar-panel" style={{ height: '100%', overflow: 'hidden' }}>
                    <Sidebar activeTab={activeTab} onTabChange={(t) => { setActiveTab(t); setIsMobileMenuOpen(false); }} />
                  </aside>
                </Panel>

                <PanelResizeHandle key="sidebar-resize-handle" id="sidebar-resize-handle" className={`resize-handle ${isEditingLayout ? 'editing' : ''}`} disabled={!isEditingLayout} style={{ width: '4px', background: isEditingLayout ? '#58a6ff' : 'transparent', cursor: isEditingLayout ? 'col-resize' : 'default', transition: 'background 0.2s' }} />
              </>
            )}

            <Panel key="main-panel" id="main-panel" order={2} minSize={50}>
              <main className="main-panel" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {!zenMode && (
                  <div className="topbar">
                    <button className="mobile-menu-toggle" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
                    ☰
                  </button>
                  <div className="brand-menu">
                    <div className="brand-block">
                      <h1>Stehouwer Publishing AI <span className="version-pill">v5.259.0</span></h1>
                    </div>
                  </div>
                  <div className="status-pill-group">
                    {isEditingLayout && (
                      <button
                        className="hide-mobile"
                        onClick={() => useAppStore.getState().resetGlobalLayout(activeTab)}
                        style={{ background: '#f85149', color: '#ffffff', border: '1px solid #b62324', padding: '4px 8px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', marginRight: '8px', fontWeight: 'bold' }}
                      >
                        🔄 Reset Layout
                      </button>
                    )}
                    <button
                      className="hide-mobile"
                      onClick={toggleEditMode}
                      style={{ background: isEditingLayout ? '#238636' : '#21262d', color: isEditingLayout ? '#ffffff' : '#c9d1d9', border: '1px solid #30363d', padding: '4px 8px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', marginRight: '8px', fontWeight: 'bold' }}
                    >
                      {isEditingLayout ? '💾 Save Layout' : '⚙️ Edit Workspace'}
                    </button>
                    <button
                      className="hide-mobile"
                      onClick={handleToggleNavLayout}
                      style={{ background: '#21262d', color: '#c9d1d9', border: '1px solid #30363d', padding: '4px 8px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.75rem', marginRight: '8px' }}
                    >
                      📌 Switch to Top Bar
                    </button>
                    <button
                      className="hide-mobile"
                      onClick={() => useAppStore.getState().toggleEfficiencyMode()}
                      style={{
                        background: efficiencyMode ? '#122e1a' : '#21262d',
                        color: efficiencyMode ? '#3fb950' : '#8b949e',
                        border: `1px solid ${efficiencyMode ? '#238636' : '#30363d'}`,
                        padding: '4px 8px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        marginRight: '8px',
                        fontWeight: 'bold',
                        transition: 'all 0.2s ease'
                      }}
                      title="Toggle Efficiency Mode (API Offload)"
                    >
                      ⚡ {efficiencyMode ? 'Efficiency: ON' : 'Efficiency: OFF'}
                    </button>
                    <button
                      className="hide-mobile"
                      onClick={() => setViewMode(viewMode === '2D' ? '3D' : '2D')}
                      style={{
                        background: viewMode === '3D' ? '#6366f1' : '#21262d',
                        color: 'white',
                        border: `1px solid ${viewMode === '3D' ? '#4f46e5' : '#30363d'}`,
                        padding: '4px 8px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        marginRight: '8px',
                        fontWeight: 'bold',
                        transition: 'all 0.2s ease'
                      }}
                      title="Toggle Unreal Engine 3D Environment"
                    >
                      {viewMode === '3D' ? '🎮 3D Viewport' : '🖥️ 2D Mode'}
                    </button>
                    <span className={`status-pill ${backendStatus === 'online' ? 'online' : backendStatus === 'offline' ? 'offline' : ''}`}>
                      ● Backend {backendStatus.toUpperCase()}
                    </span>
                    <span className="identity-pill">
                      {currentUser ? `${currentUser.displayName || currentUser.email.split('@')[0]} (Admin / Partner)` : 'Brett Adam Stehouwer (CTO)'}
                    </span>
                  </div>
                </div>
                )}

                {!zenMode && <SubTabBar activeTab={activeTab} onTabChange={setActiveTab} />}

                <div className="content-area flex-1 w-full h-full m-0 p-0" style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', padding: 0 }}>
                  <div
                    key={activeTabConfig.key}
                    className={`tab-subinterface ${activeTabConfig.key}-subinterface`}
                    role="tabpanel"
                    style={{ width: '100%', minHeight: '100%', display: 'flex', flexDirection: 'column' }}
                  >
                    <div className="subinterface-content w-full flex flex-col box-border" style={{ flex: 1, width: '100%', minHeight: '100%', padding: 0 }}>
                      <TabErrorBoundary key={activeTabConfig.key}>
                        <Suspense fallback={<TabLoader />}>
                          {canAccessTab(userTier.id, activeTabConfig.key) ? (
                            <ActiveComponent 
                              backendUrl={backendUrl} 
                              currentUser={currentUser} 
                              selectedModel={selectedModel} 
                              onNavigateTab={setActiveTab}
                              workspaceMode={workspaceMode}
                              onToggleWorkspaceMode={handleToggleWorkspaceMode}
                            />
                          ) : (
                            <FeatureGateLockedCard
                              tabKey={activeTabConfig.key}
                              tabLabel={activeTabConfig.label}
                              activeTier={userTier}
                              onNavigateToPricing={() => setActiveTab('public_checkout')}
                            />
                          )}
                        </Suspense>
                      </TabErrorBoundary>
                    </div>
                  </div>
                </div>
              </main>
            </Panel>
          </PanelGroup>
        ) : (
          <main className="main-panel" style={{ flex: 1, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {!zenMode && <SubTabBar activeTab={activeTab} onTabChange={setActiveTab} />}

            <div className="content-area flex-1 w-full h-full m-0 p-0" style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', padding: 0 }}>
              <div
                key={activeTabConfig.key}
                className={`tab-subinterface ${activeTabConfig.key}-subinterface`}
                role="tabpanel"
                style={{ width: '100%', minHeight: '100%', display: 'flex', flexDirection: 'column' }}
              >
                <div className="subinterface-content w-full flex flex-col box-border" style={{ flex: 1, width: '100%', minHeight: '100%', padding: 0 }}>
                  <TabErrorBoundary key={activeTabConfig.key}>
                    <Suspense fallback={<TabLoader />}>
                      {canAccessTab(userTier.id, activeTabConfig.key) ? (
                        <ActiveComponent 
                          backendUrl={backendUrl} 
                          currentUser={currentUser} 
                          selectedModel={selectedModel} 
                          onNavigateTab={setActiveTab}
                          workspaceMode={workspaceMode}
                          onToggleWorkspaceMode={handleToggleWorkspaceMode}
                        />
                      ) : (
                        <FeatureGateLockedCard
                          tabKey={activeTabConfig.key}
                          tabLabel={activeTabConfig.label}
                          activeTier={userTier}
                          onNavigateToPricing={() => setActiveTab('public_checkout')}
                        />
                      )}
                    </Suspense>
                  </TabErrorBoundary>
                </div>
              </div>
            </div>
          </main>
        )}
        
        <Suspense fallback={null}>
          <TeamChatDrawer momMode={momMode} />

          {/* Global Modal Overlay for High Stakes Daemon Actions */}
          <ThoughtfulFrictionModal currentUser={currentUser} />

          {/* 🌐 Client-Facing Interactive Portals (?portal=banquet / ?portal=service) */}
          {activePortal === 'banquet' && (
            <ClientBanquetPortalModal
              isOpen={true}
              onClose={() => setActivePortal(null)}
            />
          )}

          {activePortal === 'service' && (
            <ClientServicePortalModal
              isOpen={true}
              onClose={() => setActivePortal(null)}
            />
          )}
        </Suspense>

        {/* 🌸 Floating Mom Mode Accessibility & Zoom HUD */}
        <MomAccessibilityHUD
          momMode={momMode}
          onToggleMomMode={handleToggleMomMode}
          zoomLevel={momZoomLevel}
          onZoomChange={handleZoomChange}
        />

        {/* Sleek Floating Exit Button ONLY when in Zen Mode (Top Right) */}
        {zenMode && (
          <button
            onClick={() => setZenMode(false)}
            style={{
              position: 'fixed',
              top: '16px',
              right: '16px',
              zIndex: 99999,
              backgroundColor: 'rgba(239, 68, 68, 0.9)',
              color: '#fff',
              border: '1px solid #f87171',
              borderRadius: '8px',
              padding: '8px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              fontSize: '0.82rem',
              fontWeight: '700'
            }}
            title="Exit Zen Mode (Show Navigation)"
          >
            ❌ Exit Zen Mode
          </button>
        )}

        {/* Floating Toggle to return to Gemini Mobile Chat Mode when in Desktop view on phone */}
        {isMobileDevice && mobileViewMode === 'desktop' && (
          <button
            onClick={() => handleSetMobileViewMode('chat')}
            style={{
              position: 'fixed',
              bottom: '20px',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 99999,
              background: 'linear-gradient(135deg, #4285f4, #9b72cf)',
              color: '#fff',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              borderRadius: '24px',
              padding: '10px 20px',
              fontSize: '0.85rem',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
              cursor: 'pointer'
            }}
          >
            <span>✦</span>
            <span>Switch to Stehouwer Mobile Chat</span>
          </button>
        )}
      </div>
    </>
  );
}






