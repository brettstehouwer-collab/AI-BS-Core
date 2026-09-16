import React, { useState, useEffect } from 'react';
import './GlobalWalkthroughGuide.css';

export const AI_BS_TOOL_GUIDES = [
  // =========================================================================
  // HUB 1: STEHOUWER PUBLISHING (ADMIN HQ & COMMERCIAL OPERATIONS)
  // =========================================================================
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'dashboard',
    title: 'Command Center & Mission Control',
    icon: '📊',
    summary: 'Executive overview of server health, active background AI agents, GPU VRAM load, and primary quick actions.',
    steps: [
      'Inspect the top telemetry ribbon to verify backend server connection (FastAPI port 8080) and ComfyUI status (port 8189).',
      'Review active background agent tasks, disk storage statistics, and local LLM model weights.',
      'Use quick-action tiles to launch terminal sessions, switch hubs, or run system-wide diagnostics.'
    ],
    buttons: [
      { name: '🔄 Refresh Metrics', action: 'Fetches live CPU/GPU temperatures, VRAM consumption, and active WebSocket connections.' },
      { name: '⚡ Emergency Stop All', action: 'Instantly halts all background scraping, model inference, and video rendering processes.' },
      { name: '🚀 Quick Launch IDE', action: 'Switches directly to BS-CHAT Developer IDE workspace.' }
    ],
    proTips: [
      'Green server pills indicate full local hardware acceleration on the RTX 4090.',
      'Clicking any metric card drills directly into that specific subsystem.'
    ]
  },
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'shared_cloud_drive',
    title: 'Admin Shared Cloud Drive & Document Workspace',
    icon: '☁️',
    summary: 'Enterprise Google Drive / Dropbox-style file storage with in-drive document creation, AI co-pilot, and multi-format media previewing.',
    steps: [
      'Navigate the enterprise folders (01_Screenplays, 02_Media, 03_Audio, 04_Hospitality, 05_Corporate, 06_Marketing, 07_AI_Models).',
      'Drag and drop any files or entire folders onto the canvas to upload without extension restrictions.',
      'Click "+ New" to create Screenplays (.fountain), Markdown (.md), Text (.txt), JSON (.json), or Python (.py) files directly in the drive.',
      'Double-click any file to open the interactive live editor or media lightbox.',
      'Use the AI Co-Pilot toolbar inside the document editor to expand scenes, polish dialogue, or generate story bibles with 1 click.'
    ],
    buttons: [
      { name: '➕ New ▾', action: 'Opens creation dropdown for new folders, documents (Fountain, Markdown, Text, JSON, Python), or file/folder uploads.' },
      { name: '📁 New Folder', action: 'Creates a new directory in the current cloud path.' },
      { name: '💾 Save Document', action: 'Persists active in-drive editor content directly to host disk at C:\\AI-BS\\shared_cloud_drive.' },
      { name: '🤖 AI Co-Pilot (Expand / Polish)', action: 'Sends active document text to local Ollama LLMs to enrich dialogue or structure notes.' },
      { name: '📦 Download ZIP Bundle', action: 'Compiles all selected files/folders into a streaming ZIP archive on the fly.' },
      { name: '🚚 Move Items', action: 'Relocates selected files into any destination enterprise folder.' },
      { name: '🗑️ Delete Selected', action: 'Removes selected items with confirmation safety.' },
      { name: '🎬 Open in Screenplay Studio', action: 'Bridges active Fountain script directly into Universal Screenwriting Studio.' },
      { name: '💻 Open in BS-CHAT IDE', action: 'Bridges active code or config file directly into the developer IDE.' }
    ],
    proTips: [
      'Hold Ctrl or Shift while clicking to multi-select items for batch operations.',
      'Files uploaded here are accessible across all AI-BS studios without duplicating storage on disk.'
    ]
  },
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'power_washing',
    title: 'Prestige Mobile Services (Power Washing Suite)',
    icon: '💦',
    summary: 'Commercial & residential pressure washing CRM, CV chemical ratio estimator, GIS parcel quoting with route density discounts, GVWR payload optimizer, and commercial fleet portal.',
    steps: [
      'Select Tool 1 (CV Estimator) to choose substrate (vinyl, brick, shingles, concrete) and get exact Sodium Hypochlorite (SH %) batch mixing recipes.',
      'Select Tool 2 (GIS Quoting) to calculate building perimeter, roof pitch factor (4/12 to 12/12), and apply 10%-15% route density neighborhood discounts.',
      'Select Tool 3 (Water Payload) to verify rig Gross Vehicle Weight Rating (GVWR) with 8.34 lbs/gal water and view West Michigan hydrant fill depots.',
      'Select Tool 4 (Weather Dispatch) to check sub-34°F freeze risk holds, high wind warnings (>15 mph), and launch seasonal re-engagement campaigns.',
      'Select Tool 5 (Fleet Portal) to log GPS-verified wash completions and generate monthly commercial fleet invoices.',
      'Select Tool 6 (Client CRM) to manage residential/commercial clients and transition jobs across the Kanban pipeline.'
    ],
    buttons: [
      { name: '⚡ Generate Chemical Batch Recipe', action: 'Computes exact SH bleach %, surfactant oz/gal, max safe PSI, and 50-gallon tank mix.' },
      { name: '⚡ Calculate Instant GIS Proposal', action: 'Generates itemized proposal with roof pitch multipliers and 60-second SMS quote preview.' },
      { name: '🔄 Re-Calculate Legal Payload', action: 'Recalculates total truck weight vs 14,000 lbs legal GVWR ceiling for Chevy 3500 HD Dually.' },
      { name: '🚀 Launch Campaign', action: 'Triggers automated seasonal re-engagement SMS & email blasts for spring, summer, fall, or winter.' },
      { name: '📸 Log Wash', action: 'Opens GPS-verified modal to record unit wash completion, soap type, water temp, and technician name.' },
      { name: '🧾 Generate Monthly Fleet Invoices', action: 'Compiles recurring monthly commercial fleet batch billing statement.' },
      { name: '➕ Add New Client', action: 'Registers a new residential or commercial property client with gate codes and water spigot details.' },
      { name: '▶ Start Job / ✓ Complete / 💵 Mark Paid', action: 'Quickly advances job state across the interactive Kanban board.' }
    ],
    proTips: [
      'Direct customer booking line is integrated at 616-901-6536.',
      'Always check Tool 4 during West Michigan spring/fall months to prevent unheated pump freeze cracking.'
    ]
  },
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'unified_calendar',
    title: 'Master Calendar & Action Items',
    icon: '📅',
    summary: 'Unified scheduling engine for client appointments, production milestones, and high-priority action tasks.',
    steps: [
      'View daily, weekly, and monthly schedule grids.',
      'Click on any calendar day to add a new event, meeting, or service booking.',
      'Check off action items in the real-time task matrix.'
    ],
    buttons: [
      { name: '➕ New Event', action: 'Opens event scheduling modal with reminder triggers.' },
      { name: '🗓️ Sync External Calendar', action: 'Synchronizes appointments with Google Calendar or Apple iCal via ICS feed.' },
      { name: '✓ Mark Complete', action: 'Checks off task and logs completion timestamp.' }
    ],
    proTips: [
      'Events scheduled here automatically sync across the Client Scheduler and Banquet Architect.'
    ]
  },
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'unified_financial',
    title: 'Financial Ledger, Taxes & Yields',
    icon: '💰',
    summary: 'Master accounting and taxation hub tracking corporate cash flow, publishing royalties, Stripe payments, and expense deductions.',
    steps: [
      'Inspect total monthly revenue, operational expenditures, and estimated quarterly tax liabilities.',
      'Add or import transactional line items with category tagging.',
      'Export formatted Schedule C and profit-and-loss reports.'
    ],
    buttons: [
      { name: '💳 Sync Stripe Accounts', action: 'Pulls live transaction fees, gross customer payments, and pending deposits.' },
      { name: '➕ Add Transaction', action: 'Manually logs an income or expense receipt with attachment support.' },
      { name: '📊 Export P&L (CSV/PDF)', action: 'Generates accounting balance sheet for tax filing.' }
    ],
    proTips: [
      'Power washing invoices and book sales automatically credit the master ledger upon marked completion.'
    ]
  },
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'stehouwer_cms',
    title: 'Stehouwer Book Catalog & CMS',
    icon: '📖',
    summary: 'Central publishing management for author bibliographies, chapter manuscripts, cover art assets, and distributor feeds.',
    steps: [
      'Select a title (e.g. Echoes Within) from the active catalog list.',
      'Edit synopsis, ISBN metadata, pricing, and distribution channels.',
      'Upload updated manuscript EPUB or print-ready PDF files.'
    ],
    buttons: [
      { name: '➕ New Book Title', action: 'Creates a new publication entry with metadata schema.' },
      { name: '📤 Push to Amazon KDP / Ingram', action: 'Formats and packages metadata for book distributor ingestion.' },
      { name: '💾 Save CMS Changes', action: 'Commits manuscript updates to the publishing database.' }
    ],
    proTips: [
      'Manuscript chapters edited in the CMS can be bridged directly to Universal Screenwriting Studio.'
    ]
  },
  {
    hubKey: 'stehouwer_publishing',
    hubLabel: 'Stehouwer Publishing (Admin HQ)',
    hubIcon: '📚',
    key: 'personal_brand',
    title: 'Personal Brand & Social Ghostwriter',
    icon: '✍️',
    summary: 'AI-assisted ghostwriting suite tailored to author voice for LinkedIn, X (Twitter), Substack, and press releases.',
    steps: [
      'Select target channel (LinkedIn thought leadership, X thread, newsletter essay).',
      'Enter theme, core insight, or paste recent book excerpts.',
      'Generate multi-variant drafts and schedule automated publication.'
    ],
    buttons: [
      { name: '✨ Generate 3 Variants', action: 'Produces distinct tonal drafts using local LLMs.' },
      { name: '📅 Schedule Post', action: 'Queues post into the Automated Client Content Scheduler.' }
    ],
    proTips: [
      'Trained on author writing voice to preserve authentic cadence and storytelling nuance.'
    ]
  },

  // =========================================================================
  // HUB 2: ENTERTAINMENT INDUSTRY (CINEMA, 3D & THEATRICAL)
  // =========================================================================
  {
    hubKey: 'entertainment_industry',
    hubLabel: 'Entertainment Industry Hub',
    hubIcon: '🎬',
    key: 'unified_creation',
    title: 'Universal Screenwriting Studio',
    icon: '🖋️',
    summary: 'Final Draft 12/13 industry-grade screenplay studio with real-time AST parsing, page-by-page review doctor, ElevenLabs audio player, and ChromaDB vector RAG.',
    steps: [
      'Write screenplays in standard Fountain syntax or use element buttons/hotkeys (Ctrl+1 to Ctrl+6).',
      'Click "🔍 Review Pg X" in the top ribbon to run the AI Page Doctor for character cues and formatting.',
      'Toggle "🎙️ Audio Drama" in the top bar to play Brett Stehouwer’s 2h 39m Master ElevenLabs adaptation.',
      'Open the "🤖 Script Co-Pilot" drawer to query original book manuscript vectors in isolated ChromaDB memory.'
    ],
    buttons: [
      { name: '🔍 Review Pg X', action: 'Opens side-by-side Page Doctor to capitalize character names and polish scene headings.' },
      { name: '🎙️ Audio Drama', action: 'Expands the 2h 39m Master ElevenLabs Audio Player with scrubbable timecodes.' },
      { name: '🤖 Script Co-Pilot', action: 'Opens isolated project vector RAG drawer with 1-click script insertion.' },
      { name: '💾 Save Script', action: 'Saves active .fountain file to local disk and triggers automatic vector re-indexing.' },
      { name: '📄 Export Final Draft / PDF', action: 'Compiles formatted industry screenplay with proper pagination.' }
    ],
    proTips: [
      'Type "!proof" anywhere in an action or dialogue block to trigger instant page formatting repair.',
      'Use Ctrl+Z / Ctrl+Y for full in-memory undo/redo history.'
    ]
  },
  {
    hubKey: 'entertainment_industry',
    hubLabel: 'Entertainment Industry Hub',
    hubIcon: '🎬',
    key: 'unreal_3d',
    title: 'Unreal Engine 5.8 3D Scene Studio',
    icon: '🎮',
    summary: 'Direct Python scripting and WebRTC Pixel Streaming bridge into Unreal Engine 5.8 (AI_BS_Hub.uproject) on the local RTX 4090.',
    steps: [
      'Select a screenplay scene to auto-generate Unreal Python actor placement scripts.',
      'Click "🚀 Build Scene in Unreal Engine 5.8" to run headless level generation via UnrealEditor-Cmd.exe.',
      'Click "🎮 Open 3D Unreal Editor" to launch interactive UnrealEditor.exe with the loaded scene.',
      'Stream live interactive viewport directly over WebRTC pixel streaming.'
    ],
    buttons: [
      { name: '🚀 Build Scene in UE 5.8', action: 'Spawns CineCameraActor, Characters, PointLights, and Meshes into the level.' },
      { name: '🎮 Open 3D Unreal Editor', action: 'Launches full interactive desktop Unreal Engine 5.8 editor window.' },
      { name: '🎥 Render Camera Track', action: 'Outputs cinematic camera animation trajectory.' }
    ],
    proTips: [
      'Uses valid UE5 Python modules (unreal.EditorLevelLibrary, unreal.CineCameraActor).'
    ]
  },
  {
    hubKey: 'entertainment_industry',
    hubLabel: 'Entertainment Industry Hub',
    hubIcon: '🎬',
    key: 'video_studio',
    title: 'Wan2.1 Diffusion & Video Studio',
    icon: '🎞️',
    summary: 'Local video generation studio powered by Wan2.1 ComfyUI diffusion models (port 8189) on RTX 4090.',
    steps: [
      'Enter visual prompt, camera angle, and scene lighting parameters.',
      'Select resolution (832x480 or 1280x720) and generation steps (20-30 steps).',
      'Click "Render Video" to dispatch execution to ComfyUI and view live progress.',
      'Inspect rendered MP4 video in the integrated VLC preview monitor.'
    ],
    buttons: [
      { name: '🎬 Render Video', action: 'Queues prompt into ComfyUI Wan2.1 text-to-video workflow.' },
      { name: '📥 Download MP4', action: 'Saves rendered high-definition video locally.' },
      { name: '✂️ Send to Video Editor', action: 'Transfers video clips into the multi-track timeline editor.' }
    ],
    proTips: [
      'Uses the intact 10.8 GB umt5_xxl_fp16.safetensors text encoder for prompt fidelity.'
    ]
  },
  {
    hubKey: 'entertainment_industry',
    hubLabel: 'Entertainment Industry Hub',
    hubIcon: '🎬',
    key: 'noco_vision',
    title: 'Theatrical Projector & Teleprompter',
    icon: '🎭',
    summary: 'Dual-monitor live stage performance suite with scrolling teleprompter and audience theatrical projection.',
    steps: [
      'Load stage script or speech text into prompter.',
      'Adjust scroll speed, font size, and mirror reflection for stage glass.',
      'Launch projector window to cast synchronized visual cues onto auditorium screens.'
    ],
    buttons: [
      { name: '▶ Start Scrolling', action: 'Initiates smooth constant-velocity text progression.' },
      { name: '🪞 Mirror Display', action: 'Flips text horizontally for glass teleprompter beam-splitter rigs.' },
      { name: '📽️ Open Stage Projector', action: 'Spawns clean borderless window for external HDMI output.' }
    ],
    proTips: [
      'Use spacebar to pause/resume scrolling during live performance.'
    ]
  },

  // =========================================================================
  // HUB 3: HOSPITALITY INDUSTRY (BANQUETS, DINING & EVENTS)
  // =========================================================================
  {
    hubKey: 'hospitality_industry',
    hubLabel: 'Hospitality Industry Hub',
    hubIcon: '🍽️',
    key: 'banquet_architect',
    title: 'Banquet Floorplan Architect & Seating Solver',
    icon: '🏛️',
    summary: 'Interactive 2D generative floorplan architect with automatic collision avoidance and VIP seating assignment algorithms.',
    steps: [
      'Select hall dimensions and choose table archetypes (60" rounds, 8ft rectangles, serpentine buffet).',
      'Drag and position tables on the canvas grid with real-time clearance compliance checking.',
      'Import guest list and click "Solve Seating" to assign seats based on dietary restrictions and VIP affinity scores.'
    ],
    buttons: [
      { name: '➕ Add Table', action: 'Places a new table with customizable seat counts on the floorplan.' },
      { name: '🧠 Auto-Solve Seating Matrix', action: 'Runs heuristic assignment algorithm to seat guests optimally.' },
      { name: '🖨️ Export PDF Floorplan', action: 'Outputs high-resolution blueprint with banquet server table numbers.' }
    ],
    proTips: [
      'Ensures mandatory 60" aisle clearance between table edges for banquet server cart access.'
    ]
  },
  {
    hubKey: 'hospitality_industry',
    hubLabel: 'Hospitality Industry Hub',
    hubIcon: '🍽️',
    key: 'notos_enterprise',
    title: 'Noto Hospitality OS & Kitchen Dispatch',
    icon: '🍷',
    summary: 'Real-time dining room table status, kitchen ticket display (KDS), and dynamic recipe plate costing.',
    steps: [
      'Monitor live dining room tables (Seated, Appetizer, Entree, Check Dropped).',
      'Track kitchen ticket queue times and dispatch course firings.',
      'Audit recipe ingredient costs and theoretical food cost percentages.'
    ],
    buttons: [
      { name: '🔔 Fire Next Course', action: 'Alerts kitchen expo station to begin plating entrees.' },
      { name: '🧾 Print Guest Check', action: 'Calculates subtotal, tax, and generates split checks.' },
      { name: '🥗 Recalculate Recipe Cost', action: 'Updates plate margin based on live purveyor invoice prices.' }
    ],
    proTips: [
      'Maintains target 28%-32% food cost margins with automatic inflation warnings.'
    ]
  },

  // =========================================================================
  // HUB 4: GENERAL OPERATIONS & COMMUNICATION
  // =========================================================================
  {
    hubKey: 'general_operations',
    hubLabel: 'General Operations Hub',
    hubIcon: '💼',
    key: 'chat',
    title: 'BS-CHAT & Split-Pane Developer IDE',
    icon: '💬',
    summary: 'Universal conversational AI console and full Monaco code editor with multi-engine switching and live shell execution.',
    steps: [
      'Select your AI model (Local Ollama, Claude, GPT, Gemini) in the top bar.',
      'Chat naturally to brainstorm, code, debug, or control system subagents.',
      'Toggle split-pane mode to view the Monaco code editor alongside terminal output.'
    ],
    buttons: [
      { name: '⚡ Toggle Efficiency Mode', action: 'Halts local GPU models to free VRAM for crypto mining or cloud GPU renting.' },
      { name: '💻 Split-Pane IDE', action: 'Expands side-by-side Monaco code editor and terminal console.' },
      { name: '🧹 Clear Chat History', action: 'Resets conversation context window.' }
    ],
    proTips: [
      'Use slash commands (/goal, /schedule, /browser) to activate advanced agent workflows.'
    ]
  },
  {
    hubKey: 'general_operations',
    hubLabel: 'General Operations Hub',
    hubIcon: '💼',
    key: 'client_scheduler',
    title: 'Automated Client Content Scheduler',
    icon: '📢',
    summary: 'Automated social media queue and appointment scheduler for commercial client accounts.',
    steps: [
      'Review pending scheduled social posts across Facebook, LinkedIn, Instagram, and X.',
      'Edit post copy, approved image creatives, and release time windows.',
      'Approve batch posts for autonomous dispatch.'
    ],
    buttons: [
      { name: '➕ Schedule New Post', action: 'Opens social publisher modal with image attachment.' },
      { name: '🚀 Publish Now', action: 'Bypasses queue to dispatch social post immediately.' }
    ],
    proTips: [
      'Integrates directly with Personal Brand Studio for 1-click draft scheduling.'
    ]
  },
  {
    hubKey: 'general_operations',
    hubLabel: 'General Operations Hub',
    hubIcon: '💼',
    key: 'unified_media_gallery',
    title: 'Universal Media & Asset Vault',
    icon: '🖼️',
    summary: 'Central repository for generated image renders, video clips, logos, audio tracks, and document attachments.',
    steps: [
      'Browse media assets organized by tags (Render, Texture, Audio, Photo).',
      'Click any thumbnail for full-screen zoom, metadata inspection, and download.',
      'Batch tag and export assets to client project folders.'
    ],
    buttons: [
      { name: '📤 Upload Media', action: 'Ingests new media files into the global asset vault.' },
      { name: '🏷️ Batch Tag', action: 'Applies organizational metadata labels to selected assets.' }
    ],
    proTips: [
      'All ComfyUI and Unreal Engine scene renders automatically archive here.'
    ]
  },

  // =========================================================================
  // HUB 5: SYSTEM, HARDWARE & AI OPERATIONS
  // =========================================================================
  {
    hubKey: 'system_ai_operations',
    hubLabel: 'System & AI Operations Hub',
    hubIcon: '⚙️',
    key: 'system_health',
    title: 'System Health & GPU Network Monitor',
    icon: '🖥️',
    summary: 'Hardware telemetry dashboard monitoring RTX 4090 thermals, VRAM allocation, and Clore.ai / Vast.ai compute node hosting.',
    steps: [
      'Monitor real-time GPU core temperature, power wattage, and VRAM utilization.',
      'Check Clore.ai / Vast.ai mining server connection and rental yields.',
      'Toggle between active local AI inference and background compute sharing.'
    ],
    buttons: [
      { name: '⚡ Start Clore Server', action: 'Launches Clore.ai background daemon to monetize idle RTX 4090 compute.' },
      { name: '🛑 Stop Background Server', action: 'Terminates mining daemon to dedicate 100% VRAM to local video/LLM generation.' },
      { name: '🔄 Refresh Telemetry', action: 'Queries nvidia-smi for instant hardware metrics.' }
    ],
    proTips: [
      'Enable Efficiency Mode in the top navbar before starting high-throughput video rendering jobs.'
    ]
  },
  {
    hubKey: 'system_ai_operations',
    hubLabel: 'System & AI Operations Hub',
    hubIcon: '⚙️',
    key: 'security_monitor',
    title: 'AI Security & Anti-Tamper Guard',
    icon: '🛡️',
    summary: 'Role-based access control (RBAC), subscription tier simulator, and audit logging engine.',
    steps: [
      'Inspect user permissions (Root Admin, Stehouwer Publishing, Entertainment, Hospitality, Standard).',
      'Use the top navbar "👁️ Preview Tier" dropdown to simulate what lower tiers see.',
      'Review security audit logs for unauthorized endpoint requests.'
    ],
    buttons: [
      { name: '👑 Reset Admin Access', action: 'Restores master permissions to Brett Stehouwer.' },
      { name: '📜 Export Audit Log', action: 'Downloads timestamped security transaction ledger.' }
    ],
    proTips: [
      'Anti-tamper guard automatically protects sensitive root accounting and database settings.'
    ]
  }
];

export default function GlobalWalkthroughGuide({ isOpen, onClose, onNavigateTab, initialTab = 'dashboard', onStartTour }) {
  const [activeTabMode, setActiveTabMode] = useState('guide'); // 'guide' | 'ai_helper' | 'sandbox'
  const [selectedHub, setSelectedHub] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedToolKey, setSelectedToolKey] = useState(initialTab || 'dashboard');
  const [copiedUrl, setCopiedUrl] = useState(false);

  // AI Helper Conversational State
  const [helperQuery, setHelperQuery] = useState('');
  const [helperResults, setHelperResults] = useState([]);

  // Sandbox Calculator States
  // 1. Softwash Chemical Calc
  const [sbSubstrate, setSbSubstrate] = useState('vinyl');
  const [sbTankGal, setSbTankGal] = useState(50);
  const [sbBleachPct, setSbBleachPct] = useState(12.5);

  // 2. GVWR Weight Calc
  const [sbWaterGal, setSbWaterGal] = useState(275);
  const [sbShGal, setSbShGal] = useState(45);

  // 3. Screenplay Runtime Calc
  const [sbPageCount, setSbPageCount] = useState(110);
  const [sbDialoguePct, setSbDialoguePct] = useState(60);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlTool = params.get('tool');
      const urlMode = params.get('mode');
      if (urlTool) setSelectedToolKey(urlTool);
      if (urlMode && ['guide', 'ai_helper', 'sandbox'].includes(urlMode)) setActiveTabMode(urlMode);
    }
    if (initialTab && !new URLSearchParams(window.location.search).get('tool')) {
      setSelectedToolKey(initialTab);
    }
  }, [initialTab, isOpen]);

  // Synchronize URL search parameters while Guide modal is open
  useEffect(() => {
    if (isOpen && typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('guide', 'true');
      url.searchParams.set('tool', selectedToolKey);
      url.searchParams.set('mode', activeTabMode);
      window.history.replaceState({}, '', url.toString());
    }
  }, [isOpen, selectedToolKey, activeTabMode]);

  if (!isOpen) return null;

  // Filter tools based on Hub & Search
  const filteredTools = AI_BS_TOOL_GUIDES.filter((tool) => {
    const matchesHub = selectedHub === 'all' || tool.hubKey === selectedHub;
    const query = searchQuery.toLowerCase().trim();
    if (!query) return matchesHub;
    const matchesQuery =
      tool.title.toLowerCase().includes(query) ||
      tool.summary.toLowerCase().includes(query) ||
      tool.hubLabel.toLowerCase().includes(query) ||
      tool.buttons.some(b => b.name.toLowerCase().includes(query) || b.action.toLowerCase().includes(query));
    return matchesHub && matchesQuery;
  });

  const activeTool = AI_BS_TOOL_GUIDES.find(t => t.key === selectedToolKey) || filteredTools[0] || AI_BS_TOOL_GUIDES[0];

  // Copy Direct Link for this exact guide modal view
  const handleCopyToolLink = (toolKey) => {
    const shareUrl = `${window.location.origin}${window.location.pathname}?guide=true&tool=${toolKey}&mode=${activeTabMode}`;
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2500);
    });
  };

  // AI Helper Natural Language Q&A Search
  const handleAskHelper = (e) => {
    e.preventDefault();
    if (!helperQuery.trim()) return;

    const q = helperQuery.toLowerCase();
    const hits = AI_BS_TOOL_GUIDES.filter(t => 
      t.title.toLowerCase().includes(q) ||
      t.summary.toLowerCase().includes(q) ||
      t.steps.some(s => s.toLowerCase().includes(q)) ||
      t.buttons.some(b => b.name.toLowerCase().includes(q) || b.action.toLowerCase().includes(q)) ||
      t.proTips.some(p => p.toLowerCase().includes(q))
    );

    setHelperResults(hits);
  };

  // Calculations for Sandbox
  // 1. Softwash Bleach Mix
  const targetShPct = sbSubstrate === 'roof' ? 3.5 : sbSubstrate === 'concrete' ? 5.0 : 1.25;
  const gallonsBleachNeeded = ((targetShPct / sbBleachPct) * sbTankGal).toFixed(1);
  const gallonsWaterNeeded = (sbTankGal - gallonsBleachNeeded).toFixed(1);
  const surfactantOz = (sbTankGal * 0.5).toFixed(1);

  // 2. GVWR Rig Weight
  const curbWeight = 7450;
  const equipmentWeight = 1850;
  const waterWeight = sbWaterGal * 8.34;
  const shWeight = sbShGal * 10.05;
  const totalGrossWeight = (curbWeight + equipmentWeight + waterWeight + shWeight).toFixed(0);
  const isGvwrLegal = totalGrossWeight <= 14000;

  // 3. Screenplay Runtime
  const estimatedMinutes = Math.round(sbPageCount * (1 + (sbDialoguePct - 50) * 0.005));

  return (
    <div className="walkthrough-modal-overlay" onClick={onClose}>
      <div className="walkthrough-modal-container" onClick={(e) => e.stopPropagation()}>
        
        {/* ── 1. Top Brand Header Bar ── */}
        <div className="walkthrough-modal-header">
          <div className="walkthrough-header-title">
            <span className="walkthrough-header-icon">💡</span>
            <div>
              <h2>AI-BS Knowledge & Universal Guidance System</h2>
              <p>Comprehensive button dictionaries, step-by-step instructions, chemical math, and shareable tool links</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Direct Tool Share Hyperlink Button */}
            <button
              onClick={() => handleCopyToolLink(activeTool.key)}
              className="walkthrough-header-share-btn"
              title="Copy direct shareable link for this exact tool"
            >
              <span>🔗</span> {copiedUrl ? 'Copied Direct Link!' : 'Share Tool Link'}
            </button>

            {/* Start Interactive Tour Button */}
            {onStartTour && (
              <button
                onClick={() => {
                  onClose();
                  onStartTour(activeTool.key);
                }}
                className="walkthrough-header-tour-btn"
                title="Start Step-by-Step Interactive On-Screen Spotlight Tour"
              >
                <span>🎯</span> Start Interactive Tour
              </button>
            )}

            <button className="walkthrough-close-btn" onClick={onClose} title="Close Guide (Esc)">
              &times;
            </button>
          </div>
        </div>

        {/* ── 2. Top Tab Mode Switcher (Guide vs AI Assistant vs Formula Sandbox) ── */}
        <div className="walkthrough-mode-bar">
          <button
            className={`walkthrough-mode-tab ${activeTabMode === 'guide' ? 'active' : ''}`}
            onClick={() => setActiveTabMode('guide')}
          >
            <span>📚</span> Master Tool Dictionary
          </button>
          <button
            className={`walkthrough-mode-tab ${activeTabMode === 'ai_helper' ? 'active' : ''}`}
            onClick={() => setActiveTabMode('ai_helper')}
          >
            <span>🤖</span> Ask AI-BS Assistant
          </button>
          <button
            className={`walkthrough-mode-tab ${activeTabMode === 'sandbox' ? 'active' : ''}`}
            onClick={() => setActiveTabMode('sandbox')}
          >
            <span>🧪</span> Live Formula Sandbox
          </button>
        </div>

        {/* ========================================================================= */}
        {/* MODE 1: MASTER TOOL DICTIONARY & WALKTHROUGH */}
        {/* ========================================================================= */}
        {activeTabMode === 'guide' && (
          <>
            {/* Search & Hub Filter Bar */}
            <div className="walkthrough-filter-deck">
              <div className="walkthrough-search-box">
                <span className="walkthrough-search-icon">🔍</span>
                <input
                  type="text"
                  placeholder="Search 30+ tools, buttons, chemical formulas, shortcuts (e.g., 'power wash', 'fountain', 'unreal', 'gvwr')..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="walkthrough-search-input"
                />
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')} className="walkthrough-search-clear">&times;</button>
                )}
              </div>

              {/* Hub Filter Pills */}
              <div className="walkthrough-hub-pills">
                <button
                  className={`walkthrough-hub-pill ${selectedHub === 'all' ? 'active' : ''}`}
                  onClick={() => setSelectedHub('all')}
                >
                  🌐 All 5 Master Hubs
                </button>
                <button
                  className={`walkthrough-hub-pill ${selectedHub === 'stehouwer_publishing' ? 'active' : ''}`}
                  onClick={() => setSelectedHub('stehouwer_publishing')}
                >
                  📚 Stehouwer Publishing
                </button>
                <button
                  className={`walkthrough-hub-pill ${selectedHub === 'entertainment_industry' ? 'active' : ''}`}
                  onClick={() => setSelectedHub('entertainment_industry')}
                >
                  🎬 Entertainment & 3D
                </button>
                <button
                  className={`walkthrough-hub-pill ${selectedHub === 'hospitality_industry' ? 'active' : ''}`}
                  onClick={() => setSelectedHub('hospitality_industry')}
                >
                  🍽️ Hospitality Suite
                </button>
                <button
                  className={`walkthrough-hub-pill ${selectedHub === 'general_operations' ? 'active' : ''}`}
                  onClick={() => setSelectedHub('general_operations')}
                >
                  💼 General Operations
                </button>
                <button
                  className={`walkthrough-hub-pill ${selectedHub === 'system_ai_operations' ? 'active' : ''}`}
                  onClick={() => setSelectedHub('system_ai_operations')}
                >
                  ⚙️ System & AI Operations
                </button>
              </div>
            </div>

            {/* Split-Pane Body: Left Sidebar + Right Details */}
            <div className="walkthrough-body-grid">
              {/* Left Sidebar: Tool List */}
              <div className="walkthrough-sidebar">
                <div className="walkthrough-sidebar-label">
                  AVAILABLE TOOLS ({filteredTools.length})
                </div>
                <div className="walkthrough-tool-list">
                  {filteredTools.map((t) => (
                    <button
                      key={t.key}
                      className={`walkthrough-tool-item ${selectedToolKey === t.key ? 'active' : ''}`}
                      onClick={() => setSelectedToolKey(t.key)}
                    >
                      <span className="walkthrough-item-icon">{t.icon}</span>
                      <div className="walkthrough-item-text">
                        <span className="walkthrough-item-title">{t.title}</span>
                        <span className="walkthrough-item-hub">{t.hubLabel}</span>
                      </div>
                    </button>
                  ))}
                  {filteredTools.length === 0 && (
                    <div className="walkthrough-no-results">
                      No tools match "{searchQuery}". Try searching for 'bleach', 'screenplay', '3d', or 'calendar'.
                    </div>
                  )}
                </div>
              </div>

              {/* Right Detail Pane */}
              <div className="walkthrough-detail-pane">
                {activeTool && (
                  <>
                    <div className="walkthrough-detail-header">
                      <div>
                        <h3 className="walkthrough-detail-title">
                          <span>{activeTool.icon}</span> {activeTool.title}
                        </h3>
                        <div className="walkthrough-detail-badge">
                          <span>{activeTool.hubIcon}</span> {activeTool.hubLabel}
                        </div>
                      </div>

                      <div className="flex gap-2 flex-wrap">
                        {/* 1-Click Copy Direct Tool Link */}
                        <button
                          onClick={() => handleCopyToolLink(activeTool.key)}
                          className="walkthrough-share-pill-btn"
                          title="Copy Direct Shareable URL to Clipboard"
                        >
                          <span>🔗</span> {copiedUrl ? 'Copied Link!' : 'Copy Direct Link'}
                        </button>

                        {/* 1-Click Jump to Tool Navigation Bridge */}
                        <button
                          className="walkthrough-jump-btn"
                          onClick={() => {
                            if (onNavigateTab) onNavigateTab(activeTool.key);
                            onClose();
                          }}
                        >
                          🚀 Jump to Tool Workspace
                        </button>
                      </div>
                    </div>

                    {/* Summary Overview */}
                    <div className="walkthrough-card">
                      <h4 className="walkthrough-card-heading">📖 Tool Purpose & Overview</h4>
                      <p className="walkthrough-summary-text">{activeTool.summary}</p>
                    </div>

                    {/* Step-by-Step Instructions */}
                    <div className="walkthrough-card">
                      <h4 className="walkthrough-card-heading">🎯 Step-by-Step Operating Checklist</h4>
                      <ul className="walkthrough-steps-list">
                        {activeTool.steps.map((step, idx) => (
                          <li key={idx}>
                            <span className="walkthrough-step-number">{idx + 1}</span>
                            <span className="walkthrough-step-text">{step}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Comprehensive Button & Action Dictionary */}
                    <div className="walkthrough-card">
                      <h4 className="walkthrough-card-heading">🔘 Button & Control Dictionary</h4>
                      <div className="walkthrough-buttons-grid">
                        {activeTool.buttons.map((btn, idx) => (
                          <div key={idx} className="walkthrough-button-card">
                            <span className="walkthrough-btn-name">{btn.name}</span>
                            <span className="walkthrough-btn-desc">{btn.action}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Operational Pro Tips & Safety Rules */}
                    {activeTool.proTips && activeTool.proTips.length > 0 && (
                      <div className="walkthrough-card walkthrough-tips-card">
                        <h4 className="walkthrough-card-heading">💡 Operational Pro Tips & Best Practices</h4>
                        <ul className="walkthrough-tips-list">
                          {activeTool.proTips.map((tip, idx) => (
                            <li key={idx}>{tip}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </>
        )}

        {/* ========================================================================= */}
        {/* MODE 2: ASK AI-BS CONVERSATIONAL ASSISTANT */}
        {/* ========================================================================= */}
        {activeTabMode === 'ai_helper' && (
          <div className="walkthrough-helper-container">
            <div className="walkthrough-helper-hero">
              <h3>🤖 Ask AI-BS Assistant Anything</h3>
              <p>Type any natural language operational question to get instant step-by-step guidance, formulas, and tool links.</p>
              
              <form onSubmit={handleAskHelper} className="walkthrough-helper-form">
                <input
                  type="text"
                  placeholder="e.g. 'How do I mix bleach for a 3-story asphalt roof?' or 'How do I review screenplay formatting?'..."
                  value={helperQuery}
                  onChange={(e) => setHelperQuery(e.target.value)}
                  className="walkthrough-helper-input"
                />
                <button type="submit" className="walkthrough-helper-submit-btn">
                  Search Knowledge Base
                </button>
              </form>

              {/* Quick Sample Prompts */}
              <div className="walkthrough-quick-prompts">
                <span className="text-xs text-gray-400">Try asking:</span>
                <button type="button" onClick={() => { setHelperQuery('power wash chemical ratio'); }}>💦 Softwash Chemical Ratios</button>
                <button type="button" onClick={() => { setHelperQuery('screenplay proof doctor'); }}>🎬 Screenplay Page Doctor</button>
                <button type="button" onClick={() => { setHelperQuery('unreal python scene'); }}>🎮 Unreal Engine 3D Scene</button>
                <button type="button" onClick={() => { setHelperQuery('cloud drive zip upload'); }}>☁️ Cloud Drive ZIP Ingestion</button>
              </div>
            </div>

            {/* Assistant Search Results */}
            <div className="walkthrough-helper-results">
              {helperResults.length > 0 ? (
                <div className="walkthrough-helper-grid">
                  {helperResults.map((t) => (
                    <div key={t.key} className="walkthrough-helper-card">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-bold text-white text-base">
                          {t.icon} {t.title}
                        </span>
                        <span className="text-xs text-cyan-400 font-bold">{t.hubLabel}</span>
                      </div>
                      <p className="text-xs text-gray-300 mb-3">{t.summary}</p>
                      <div className="text-xs text-gray-400 mb-3">
                        <strong>Top Steps:</strong> {t.steps[0]}
                      </div>
                      <div className="flex justify-between items-center">
                        <button
                          onClick={() => handleCopyToolLink(t.key)}
                          className="text-xs text-gray-400 hover:text-white"
                        >
                          🔗 Copy Link
                        </button>
                        <button
                          onClick={() => {
                            if (onNavigateTab) onNavigateTab(t.key);
                            onClose();
                          }}
                          className="walkthrough-jump-btn text-xs py-1 px-3"
                        >
                          Open Workspace ➔
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500 text-sm">
                  {helperQuery ? 'No matching instructions found. Try a broader search term above.' : 'Enter a question above or click one of the quick suggestions!'}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* MODE 3: LIVE FORMULA SANDBOX CALCULATOR */}
        {/* ========================================================================= */}
        {activeTabMode === 'sandbox' && (
          <div className="walkthrough-sandbox-container">
            <div className="walkthrough-sandbox-grid">
              
              {/* 1. Softwash Chemical Batch Calculator */}
              <div className="walkthrough-sandbox-card">
                <div className="walkthrough-sb-header">
                  <span>🧪 Softwash Chemical Batch Calculator</span>
                  <span className="text-xs text-cyan-400">Prestige Formula</span>
                </div>
                <div className="walkthrough-sb-body">
                  <div className="mb-3">
                    <label className="text-xs text-gray-400">Substrate Application:</label>
                    <select
                      value={sbSubstrate}
                      onChange={(e) => setSbSubstrate(e.target.value)}
                      className="walkthrough-sb-select"
                    >
                      <option value="vinyl">Vinyl Siding / Gutters (1.25% SH Softwash)</option>
                      <option value="roof">Asphalt Shingle Roof (3.5% SH Gloeocapsa Magma)</option>
                      <option value="concrete">Concrete Driveway Flatwork (5.0% SH Post-Treat)</option>
                    </select>
                  </div>
                  <div className="flex gap-2 mb-3">
                    <div className="flex-1">
                      <label className="text-xs text-gray-400">Total Tank Mix (Gal):</label>
                      <input
                        type="number"
                        value={sbTankGal}
                        onChange={(e) => setSbTankGal(Number(e.target.value))}
                        className="walkthrough-sb-input"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-gray-400">Raw SH Bleach Conc (%):</label>
                      <input
                        type="number"
                        value={sbBleachPct}
                        onChange={(e) => setSbBleachPct(Number(e.target.value))}
                        className="walkthrough-sb-input"
                        step="0.5"
                      />
                    </div>
                  </div>

                  <div className="walkthrough-sb-result">
                    <div className="font-bold text-cyan-300 text-sm mb-1">
                      Target Recipe for {sbTankGal} Gallons:
                    </div>
                    <div className="text-xs text-gray-200">
                      • <strong>{gallonsBleachNeeded} Gal</strong> Raw 12.5% SH Pool Shock<br />
                      • <strong>{gallonsWaterNeeded} Gal</strong> Clean Buffer Water<br />
                      • <strong>{surfactantOz} oz</strong> High-Cling Surfactant Soap
                    </div>
                  </div>
                </div>
              </div>

              {/* 2. Rig GVWR Legal Weight Checker */}
              <div className="walkthrough-sandbox-card">
                <div className="walkthrough-sb-header">
                  <span>⚖️ Truck GVWR Legal Weight Checker</span>
                  <span className="text-xs text-cyan-400">Chevy 3500 HD Dually</span>
                </div>
                <div className="walkthrough-sb-body">
                  <div className="flex gap-2 mb-3">
                    <div className="flex-1">
                      <label className="text-xs text-gray-400">Buffer Water (Gal):</label>
                      <input
                        type="number"
                        value={sbWaterGal}
                        onChange={(e) => setSbWaterGal(Number(e.target.value))}
                        className="walkthrough-sb-input"
                        max="275"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-gray-400">SH Bleach (Gal):</label>
                      <input
                        type="number"
                        value={sbShGal}
                        onChange={(e) => setSbShGal(Number(e.target.value))}
                        className="walkthrough-sb-input"
                        max="55"
                      />
                    </div>
                  </div>

                  <div className="walkthrough-sb-result">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-bold text-white text-sm">Total Gross Weight:</span>
                      <span className={`font-bold text-base ${isGvwrLegal ? 'text-green-400' : 'text-red-400'}`}>
                        {totalGrossWeight} lbs
                      </span>
                    </div>
                    <div className="text-xs text-gray-300">
                      Legal GVWR Limit: 14,000 lbs • Status:{' '}
                      <strong className={isGvwrLegal ? 'text-green-400' : 'text-red-400'}>
                        {isGvwrLegal ? '✅ 100% ROAD LEGAL' : '⚠️ EXCEEDS GVWR CAPACITY'}
                      </strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* 3. Screenplay Page-to-Minute Estimator */}
              <div className="walkthrough-sandbox-card">
                <div className="walkthrough-sb-header">
                  <span>🎬 Screenplay Runtime Estimator</span>
                  <span className="text-xs text-cyan-400">Industry Standard</span>
                </div>
                <div className="walkthrough-sb-body">
                  <div className="flex gap-2 mb-3">
                    <div className="flex-1">
                      <label className="text-xs text-gray-400">Total Script Pages:</label>
                      <input
                        type="number"
                        value={sbPageCount}
                        onChange={(e) => setSbPageCount(Number(e.target.value))}
                        className="walkthrough-sb-input"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs text-gray-400">Dialogue Ratio (%):</label>
                      <input
                        type="number"
                        value={sbDialoguePct}
                        onChange={(e) => setSbDialoguePct(Number(e.target.value))}
                        className="walkthrough-sb-input"
                      />
                    </div>
                  </div>

                  <div className="walkthrough-sb-result">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-bold text-white text-sm">Estimated Screen Time:</span>
                      <span className="font-bold text-green-400 text-base">
                        ~{estimatedMinutes} min ({Math.floor(estimatedMinutes / 60)}h {estimatedMinutes % 60}m)
                      </span>
                    </div>
                    <div className="text-xs text-gray-300">
                      Standard industry formula calibrates ~1 minute per standard Fountain formatted page.
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* ── 4. Footer ── */}
        <div className="walkthrough-modal-footer">
          <div className="walkthrough-footer-tip">
            <span>💡 Pro-Tip: Press <kbd>?</kbd> or <kbd>F1</kbd> anywhere in AI-BS to open this guide • Deep link active for collaboration.</span>
          </div>
          <button className="walkthrough-btn-done" onClick={onClose}>
            Close Guide
          </button>
        </div>

      </div>
    </div>
  );
}
