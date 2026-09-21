/**
 * Master Navigation Configuration for AI-BS Matrix.
 * Cleanly organized into 4 primary operating pillars:
 * 1. 🧠 Intelligence & Code (BS-CHAT, Models, DAG Builder, Terminal, Telemetry)
 * 2. 🎨 Creative Media Studio (BV-Media Creator, BsMedia-Chat, Screenplay, DAW Beatmaker, Autonomous Media)
 * 3. 💼 Business & Operations (Command Center, Cloud Drive, Clients CRM, Accounting, NDA, Email)
 * 4. 🛠️ Engineering & Specialized Labs (Phone Repair, Mobile Wash, Project NoCo, Crypto Swarm, Gaming Lab)
 */

export const PINNED_QUICK_TABS = [
  { key: 'ide', label: 'BS-CHAT', icon: '💻', badge: 'AI CORE' },
  { key: 'bv_media_creator', label: 'BV-Media Studio', icon: '🎨', badge: 'CREATOR' },
  { key: 'dashboard', label: 'Command Center', icon: '📊', badge: 'HQ' },
  { key: 'shared_cloud_drive', label: 'Cloud Drive', icon: '☁️', badge: 'STORAGE' },
  { key: 'workflow_dag', label: 'DAG Builder', icon: '⚡', badge: 'AGENTS' },
  { key: 'terminal', label: 'Host Terminal', icon: '⌨️', badge: 'SHELL' }
];

export const masterHubs = [
  {
    key: 'intelligence_and_code',
    label: 'Intelligence & Code',
    icon: '🧠',
    defaultTab: 'ide',
    subTabs: [
      { key: 'ide', label: 'BS-CHAT Interface', icon: '💻', description: 'Split-Pane Sovereign AI Chat & IPC Telemetry Hub' },
      { key: 'workflow_dag', label: 'Multi-Agent DAG Builder', icon: '⚡', description: 'Visual Node-Based Autonomous Agent Pipeline & DAG Builder' },
      { key: 'terminal', label: 'Host Terminal Shell', icon: '⌨️', description: 'Interactive Windows 11 PowerShell Virtual Terminal' },
      { key: 'deep_learning_studio', label: 'Deep Learning Studio', icon: '🧠', description: '17-Model Fleet Topology & Dynamic Graph Visualizer' },
      { key: 'agent_memory', label: 'Agent Vector Memory', icon: '💾', description: 'ChromaDB Vector Store Explorer & Memory Bank' },
      { key: 'reasoning_attention', label: 'Self-Refinement & Attention', icon: '⚡', description: 'Contextual Encodings & Attention Heatmaps' },
      { key: 'system_health', label: 'System Health & Audit Logs', icon: '🏥', description: 'Real-time Server Telemetry, Lifespan Logs & DB Status' },
      { key: 'vms', label: 'Virtual Machines & VNC', icon: '🖥️', description: 'Local VM GUI Management & Hypervisor Bridge' },
      { key: 'automation_console', label: 'Automation Console', icon: '⚙️', description: 'Trusted Windows Job Queue & Task Automation' },
      { key: 'definitions', label: 'System Lore & Glossaries', icon: '📖', description: 'Interactive AI-BS Architectural Wiki & Lexicon' }
    ]
  },
  {
    key: 'creative_media_studio',
    label: 'Creative Media Studio',
    icon: '🎨',
    defaultTab: 'bv_media_creator',
    subTabs: [
      { key: 'bv_media_creator', label: 'BV-Media Creator Studio', icon: '🎨', description: 'Unified Media Creator Studio, Dedicated BsMedia-Chat & ChromaDB Media Vault' },
      { key: 'media_studio', label: 'Autonomous Media Studio', icon: '🎬', description: 'Autonomous Headless Media Production Studio across 13 Domains' },
      { key: 'unified_creation', label: 'Universal Screenwriting Studio', icon: '✍️', description: 'Hollywood AST Screenplay Editor, Book Adaptation & Story Bible' },
      { key: 'music_daw', label: 'FL Music Studio (DAW)', icon: '🎵', description: 'Pattern-Based DAW, Synthesizer & Beat Maker' },
      { key: 'personal_brand', label: 'Personal Brand Studio', icon: '🔥', description: 'AI Ghostwriter & Multi-Channel Social Content Matrix' },
      { key: 'advertising', label: 'Advertising Studio', icon: '📢', description: 'Targeted Ad Copy, Campaign Funnels & Creative Variants' },
      { key: 'syndication', label: 'Automated Syndication', icon: '🌐', description: '1-Click Multi-Channel Broadcaster & Ad Distribution' },
      { key: 'stehouwer_cms', label: 'Stehouwer Publications & CMS', icon: '📖', description: 'Headless Publishing, Character Bibles & KDP Stream' },
      { key: 'unified_media_gallery', label: 'Media & Asset Vault', icon: '🖼️', description: 'Asset Archive, Visual Renders & Audio Stems' },
      { key: 'digital_storefront', label: 'Digital Storefront & Pricing', icon: '🏪', description: 'Monetize Local Compute, Passes & Crypto Checkout' }
    ]
  },
  {
    key: 'business_operations',
    label: 'Business & Operations',
    icon: '💼',
    defaultTab: 'dashboard',
    subTabs: [
      { key: 'dashboard', label: 'Command Center', icon: '📊', description: 'Executive Mission Control & Ecosystem Status' },
      { key: 'shared_cloud_drive', label: 'Shared Cloud Drive', icon: '☁️', description: 'Google Drive-Style Cloud Storage & Asset Sharing' },
      { key: 'operations_audit', label: 'Omni Operations Audit Hub', icon: '📋', description: 'Live Tasks, Media Queue, Autosaves & Daemon Diagnostics' },
      { key: 'clients', label: 'Clients Hub & CRM', icon: '🏢', description: 'Client Profiles, Interaction History & Contract Matrix' },
      { key: 'onboarding', label: 'Client Onboarding', icon: '🚀', description: 'Intelligent Client Intake & Onboarding Portal' },
      { key: 'unified_financial', label: 'Financial Ledger & Taxes', icon: '💰', description: 'Master Accounting, P&L, Expense Tracking & Tax Suite' },
      { key: 'nda_module', label: 'Sovereign NDA & Anti-Tamper', icon: '📜', description: 'Interactive Master NDA Generator, Cryptographic Tamper Seal' },
      { key: 'email_client', label: 'Business Email Client', icon: '📧', description: 'Integrated IMAP/SMTP Local Business Mail' },
      { key: 'unified_calendar', label: 'Master Schedule & Calendar', icon: '📅', description: 'Unified Appointments, Calendar & Event Pipeline' },
      { key: 'beta', label: 'Web Traffic & Telemetry', icon: '📈', description: 'Live Web Analytics, Wire Hashes & Wave Telemetry' },
      { key: 'ecosystem_blueprint', label: 'Matrix Blueprint & ROI', icon: '🌐', description: 'Systemic Architecture, 5-Pillar Matrix & Financial ROI' }
    ]
  },
  {
    key: 'engineering_labs',
    label: 'Engineering & Specialized Labs',
    icon: '🛠️',
    defaultTab: 'phone_repair',
    subTabs: [
      { key: 'phone_repair', label: 'Phone & Tablet Repair Lab', icon: '🔧', description: 'Master Teardowns, Face ID Diagnostics & Diode Values' },
      { key: 'power_washing', label: 'Prestige Mobile Wash', icon: '💦', description: 'Commercial Pressure Washing CRM, Chemical Estimator & Fleet' },
      { key: 'banquet_architect', label: 'Banquet Architect Studio', icon: '💒', description: '2D/3D Floor Plans, Seating Charts & BEO Generator' },
      { key: 'notos_enterprise', label: "Noto's Enterprise OS", icon: '🍷', description: 'Internal Hospitality Operating Platform for GR & GH' },
      { key: 'noto_inventory', label: 'Notō Multi-Bar Stock', icon: '🍸', description: 'Live Inventory, Barback Dispatch & Distributor POs' },
      { key: 'project_noco', label: 'Project NoCo Living Stage', icon: '🏛️', description: 'Autonomous Acoustic-Agricultural Enclave & Studio' },
      { key: 'unified_crypto', label: 'Crypto Swarm & Mining', icon: '⚡', description: 'Clore/Vast Node Telemetry & Fast-Scalping Bot' },
      { key: 'gaming_lab', label: 'Gaming & Process Memory Lab', icon: '🎮', description: 'Win32 Runtime Memory Manipulation & Trainer Suite' },
      { key: 'bible_hub', label: 'Sovereign Bible Hub', icon: '📖', description: 'Dual KJV & NIV Canonical New Testament Reader' },
      { key: 'lost_property', label: 'Lost Property Vault', icon: '🔍', description: 'Guest Claim Logging & Asset Recovery Tracking' }
    ]
  }
];

// Placeholder Industry Vertical Hubs (Hidden until populated down the road)
export const placeholderIndustryHubs = [
  {
    key: 'businessfinance',
    label: 'Business & Finance',
    icon: '🏢',
    defaultTab: 'financialhedgefund',
    subTabs: [
      { key: 'financialhedgefund', label: 'Financial & Hedge Fund', icon: '⚡' },
      { key: 'ecommerceretail', label: 'E-commerce & Retail', icon: '⚡' },
      { key: 'realestatearchitecture', label: 'Real Estate & Architecture', icon: '⚡' },
      { key: 'realestatedevelopment', label: 'Real Estate Development', icon: '⚡' },
      { key: 'insuranceclaims', label: 'Insurance & Claims', icon: '⚡' },
      { key: 'humanresourcesrecruiting', label: 'Human Resources & Recruiting', icon: '⚡' },
      { key: 'legalcompliance', label: 'Legal & Compliance', icon: '⚡' },
      { key: 'customersupportcallcenters', label: 'Customer Support & Call Centers', icon: '⚡' },
      { key: 'nonprofitngo', label: 'Non-Profit & NGO', icon: '⚡' },
      { key: 'traveltourism', label: 'Travel & Tourism', icon: '⚡' }
    ]
  },
  {
    key: 'deeptechscience',
    label: 'Deep Tech & Science',
    icon: '🏢',
    defaultTab: 'medicalbioinformatics',
    subTabs: [
      { key: 'medicalbioinformatics', label: 'Medical & Bioinformatics', icon: '⚡' },
      { key: 'pharmaceuticals', label: 'Pharmaceuticals', icon: '⚡' },
      { key: 'syntheticbiologycrispr', label: 'Synthetic Biology & CRISPR', icon: '⚡' },
      { key: 'quantumcomputingresearch', label: 'Quantum Computing Research', icon: '⚡' },
      { key: 'materialsscience', label: 'Materials Science', icon: '⚡' },
      { key: 'nanotechnology', label: 'Nanotechnology', icon: '⚡' },
      { key: 'nlpresearch', label: 'NLP Research', icon: '⚡' },
      { key: 'computervisionengineering', label: 'Computer Vision Engineering', icon: '⚡' },
      { key: 'roboticsautomation', label: 'Robotics & Automation', icon: '⚡' },
      { key: 'aerospacedefense', label: 'Aerospace & Defense', icon: '⚡' }
    ]
  },
  {
    key: 'infrastructureit',
    label: 'Infrastructure & IT',
    icon: '🏢',
    defaultTab: 'datacenteroperations',
    subTabs: [
      { key: 'datacenteroperations', label: 'Data Center Operations', icon: '⚡' },
      { key: 'devopscicd', label: 'DevOps & CI/CD', icon: '⚡' },
      { key: 'cloudinfrastructurefinops', label: 'Cloud Infrastructure & FinOps', icon: '⚡' },
      { key: 'edgeaiiot', label: 'Edge AI & IoT', icon: '⚡' },
      { key: 'telemetryobservability', label: 'Telemetry & Observability', icon: '⚡' },
      { key: 'embeddedsystems', label: 'Embedded Systems', icon: '⚡' },
      { key: 'networksecuritypentesting', label: 'Network Security & Pen Testing', icon: '⚡' },
      { key: 'cybersecurityinfosec', label: 'Cybersecurity & InfoSec', icon: '⚡' },
      { key: 'blockchainweb3security', label: 'Blockchain & Web3 Security', icon: '⚡' },
      { key: 'telecommunications', label: 'Telecommunications', icon: '⚡' }
    ]
  },
  {
    key: 'creativemedia',
    label: 'Creative & Media',
    icon: '🏢',
    defaultTab: 'entertainmentmedia',
    subTabs: [
      { key: 'entertainmentmedia', label: 'Entertainment & Media', icon: '⚡' },
      { key: 'gamingesports', label: 'Gaming & Esports', icon: '⚡' },
      { key: 'gameenginearchitecture', label: 'Game Engine Architecture', icon: '⚡' },
      { key: 'augmentedrealitydevelopment', label: 'Augmented Reality Development', icon: '⚡' },
      { key: 'animationvfx', label: 'Animation & VFX', icon: '⚡' },
      { key: 'videobroadcasting', label: 'Video & Broadcasting', icon: '⚡' },
      { key: 'audiopodcasting', label: 'Audio & Podcasting', icon: '⚡' },
      { key: 'photographyimaging', label: 'Photography & Imaging', icon: '⚡' },
      { key: 'journalismpublishing', label: 'Journalism & Publishing', icon: '⚡' },
      { key: 'creativewritingpublishing', label: 'Creative Writing & Publishing', icon: '⚡' }
    ]
  },
  {
    key: 'publicsectorutilities',
    label: 'Public Sector & Utilities',
    icon: '🏢',
    defaultTab: 'governmentpublicsector',
    subTabs: [
      { key: 'governmentpublicsector', label: 'Government & Public Sector', icon: '⚡' },
      { key: 'energyutilities', label: 'Energy & Utilities', icon: '⚡' },
      { key: 'electricalgrid', label: 'Electrical & Grid', icon: '⚡' },
      { key: 'wastemanagement', label: 'Waste Management', icon: '⚡' },
      { key: 'miningmetals', label: 'Mining & Metals', icon: '⚡' },
      { key: 'deepspacecommunications', label: 'Deep Space Communications', icon: '⚡' },
      { key: 'autonomousvehicles', label: 'Autonomous Vehicles', icon: '⚡' },
      { key: 'translationlocalization', label: 'Translation & Localization', icon: '⚡' },
      { key: 'educationedtech', label: 'Education & EdTech', icon: '⚡' },
      { key: 'semiconductorsvlsi', label: 'Semiconductors & VLSI', icon: '⚡' }
    ]
  },
  {
    key: 'marketingcomms',
    label: 'Marketing & Comms',
    icon: '🏢',
    defaultTab: 'seodigitalmarketing',
    subTabs: [
      { key: 'seodigitalmarketing', label: 'SEO & Digital Marketing', icon: '⚡' },
      { key: 'socialmediainfluencer', label: 'Social Media & Influencer', icon: '⚡' },
      { key: 'prcommunications', label: 'PR & Communications', icon: '⚡' },
      { key: 'eventsticketing', label: 'Events & Ticketing', icon: '⚡' },
      { key: 'fashionapparel', label: 'Fashion & Apparel', icon: '⚡' },
      { key: 'foodbeverage', label: 'Food & Beverage', icon: '⚡' },
      { key: 'sportsathletics', label: 'Sports & Athletics', icon: '⚡' },
      { key: 'wellnessfitness', label: 'Wellness & Fitness', icon: '⚡' },
      { key: 'logisticsshipping', label: 'Logistics & Shipping', icon: '⚡' },
      { key: 'deliverycourier', label: 'Delivery & Courier', icon: '⚡' }
    ]
  },
  {
    key: 'tradesfieldservices',
    label: 'Trades & Field Services',
    icon: '🏢',
    defaultTab: 'manufacturingsupplychain',
    subTabs: [
      { key: 'manufacturingsupplychain', label: 'Manufacturing & Supply Chain', icon: '⚡' },
      { key: 'agriculturefarming', label: 'Agriculture & Farming', icon: '⚡' },
      { key: 'constructionengineering', label: 'Construction & Engineering', icon: '⚡' },
      { key: 'automotivedealership', label: 'Automotive & Dealership', icon: '⚡' },
      { key: 'landscapinggrounds', label: 'Landscaping & Grounds', icon: '⚡' },
      { key: 'hvacclimatecontrol', label: 'HVAC & Climate Control', icon: '⚡' },
      { key: 'plumbingwatersystems', label: 'Plumbing & Water Systems', icon: '⚡' },
      { key: 'cleaningfacility', label: 'Cleaning & Facility', icon: '⚡' },
      { key: 'securitysurveillance', label: 'Security & Surveillance', icon: '⚡' },
      { key: 'pestcontrol', label: 'Pest Control', icon: '⚡' }
    ]
  }
];

/**
 * Curated navigation items for Simple / Beginner Mode.
 * Presents 5 primary operating pillars + Explore All Tools launcher.
 */
export const simpleModeNavItems = [
  {
    key: 'dashboard',
    label: 'Home Portal',
    icon: '🏠',
    description: 'Master Launchpad & High-Level System Overview'
  },
  {
    key: 'shared_cloud_drive',
    label: 'Cloud Drive',
    icon: '☁️',
    description: 'Shared Cloud Storage, In-App Documents & Asset Vault'
  },
  {
    key: 'unified_creation',
    label: 'Creative Studio',
    icon: '🎨',
    description: 'Hollywood AST Screenwriting, AI Page Doctor, Video & Media Suite'
  },
  {
    key: 'banquet_architect',
    label: 'Hospitality Studio',
    icon: '💒',
    description: 'Banquet Architect, 2D/3D Venue Floor Plans & Event Operations'
  },
  {
    key: 'unified_calendar',
    label: 'Master Calendar',
    icon: '📅',
    description: 'Master Schedule, Client Appointments, Event Planning & Tasks'
  }
];

/**
 * Returns a flattened array of all 32+ tools across all 5 Master Hubs.
 */
export const getAllToolsFlatList = () => {
  return masterHubs.flatMap(hub => 
    hub.subTabs.map(sub => ({
      ...sub,
      hubKey: hub.key,
      hubLabel: hub.label,
      hubIcon: hub.icon
    }))
  );
};
