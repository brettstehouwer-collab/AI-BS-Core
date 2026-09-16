/**
 * Master Navigation Configuration for AI-BS Matrix.
 * Cleanly organized into 5 primary operating hubs:
 * 1. Stehouwer Publishing (Admin HQ & Business Operations)
 * 2. Hollywood Creation Suite (Screenwriting, Adaptation & Story Bible)
 * 3. Noto Hospitality OS (Venues, Banquets & Floor Plans)
 * 4. Creator Studio & Revenue (Storefront, Advertising & Video Studio)
 * 5. Neural Intelligence & Dev IDE (BS-CHAT, Deep Learning & Vector Memory)
 */

export const masterHubs = [
  {
    key: 'stehouwer_publishing',
    label: 'Stehouwer Publishing',
    icon: '📚',
    defaultTab: 'dashboard',
    subTabs: [
      { key: 'dashboard', label: 'Command Center', icon: '📊', description: 'Executive Mission Control & System Overview' },
      { key: 'ecosystem_blueprint', label: 'Matrix Blueprint & ROI', icon: '🌐', description: 'Systemic Architecture, 5-Pillar Matrix & TCO ROI Simulator' },
      { key: 'shared_cloud_drive', label: 'Shared Cloud Drive', icon: '☁️', description: 'Google Drive-Style Cloud Storage, Document Creator & Asset Sharing' },
      { key: 'power_washing', label: 'Prestige Mobile Wash', icon: '💦', description: 'Commercial & Residential Pressure Washing CRM, Chemical Estimator & Fleet Portal' },
      { key: 'phone_repair', label: 'Phone & Tablet Repair Lab', icon: '🔧', description: 'Master technical teardowns, Face ID serialization & diagnostic trees for Apple, Android & Tablets' },
      { key: 'bible_hub', label: 'Sovereign Bible Hub', icon: '📖', description: 'Dual KJV & NIV Canonical New Testament Reader, Parallel Comparison & Verse Concordance' },
      { key: 'unified_calendar', label: 'Calendar & Action Items', icon: '📅', description: 'Master Calendar, Schedule & Task Matrix' },
      { key: 'client_scheduler', label: 'Client & Event Scheduler', icon: '🗓️', description: 'Multi-Service Booking & Appointments' },
      { key: 'lost_property', label: 'Lost Property Vault', icon: '🔍', description: 'Guest Claim Logging & Asset Tracking' },
      { key: 'unified_financial', label: 'Financial Ledger & Taxes', icon: '💰', description: 'Master Accounting, P&L, Expense Tracking' },
      { key: 'clients', label: 'Clients Hub & CRM', icon: '🏢', description: 'Client Contracts, Profiles & Directory' },
      { key: 'nda_module', label: 'Sovereign NDA & Anti-Tamper', icon: '📜', description: 'Interactive Master NDA Signer, Clause Reviewer, Watermarking & Cryptographic Tamper Seal' },
      { key: 'leadmatrix', label: 'Lead Matrix & Growth', icon: '🎯', description: 'Automated B2B Lead Scoring & Funnels' },
      { key: 'unified_osint', label: 'OSINT Recon & API Hub', icon: '🌐', description: 'Deep Intelligence, Domain Recon & RapidAPI' },
      { key: 'email_client', label: 'Business Email Client', icon: '📧', description: 'Integrated IMAP/SMTP Local Business Mail' },
      { key: 'beta', label: 'Web Traffic & Telemetry Suite', icon: '📈', description: 'Stehouwer Web Traffic, Wire Packet Hashes & Over-The-Air Wave Sensors' },
      { key: 'system_economics', label: 'System Economics', icon: '💎', description: 'Compute Costs, GPU Hashrates & Yields' },
      { key: 'security_monitor', label: 'Admin Security & Telemetry', icon: '🛡️', description: 'Hardware Telemetry & Anti-Tamper Audit' },
      { key: 'system_health', label: 'System Health & Audit', icon: '🏥', description: 'Live Server Diagnostics & Database Health' },
      { key: 'vms', label: 'Virtual Machines & VNC', icon: '🖥️', description: 'Direct Virtual Machine GUI Management' },
      { key: 'terminal', label: 'Host System Terminal', icon: '⌨️', description: 'Virtual Shell & Powershell Execution' },
      { key: 'unified_crypto', label: 'Crypto Swarm & Mining', icon: '⚡', description: 'Clore/Vast Node Telemetry & Mining Rig' }
    ]
  },
  {
    key: 'hollywood_creation_suite',
    label: 'Hollywood Creation Suite',
    icon: '🎬',
    defaultTab: 'unified_creation',
    subTabs: [
      { key: 'unified_creation', label: 'Universal Screenwriting Studio', icon: '✍️', description: 'Hollywood AST Editor, Book-to-Script AI Matrix & FDX Serializer' },
      { key: 'stehouwer_cms', label: 'Stehouwer CMS & Publications', icon: '📖', description: 'Story Bibles, Character Vault & Headless Publishing' },
      { key: 'project_noco', label: 'Project NoCo & Living Stage Studio', icon: '🏛️', description: 'Autonomous Acoustic-Agricultural Enclave & Living Stage Studio' },
      { key: 'unified_media_gallery', label: 'Media & Asset Vault', icon: '🖼️', description: 'Screenplay Graphics, Audio Stems & Storyboards' }
    ]
  },
  {
    key: 'noto_hospitality_os',
    label: 'Noto Hospitality OS',
    icon: '🍷',
    defaultTab: 'banquet_architect',
    subTabs: [
      { key: 'banquet_architect', label: 'Banquet Architect Studio', icon: '💒', description: '2D/3D Floor Plans, Seating Charts & Dietary Registry' },
      { key: 'notos_enterprise', label: "Noto's Enterprise OS", icon: '🍷', description: 'Internal Hospitality Operating Platform for GR & GH' },
      { key: 'noto_inventory', label: 'Notō Multi-Bar Stock & Dispatch', icon: '🍸', description: 'Live Multi-Bar Inventory, Barback Dispatch & MLCC Distributor PO Engine' },
      { key: 'project_noco_studio', label: 'Project NoCo Studio', icon: '🏛️', description: 'Autonomous Acoustic-Agricultural Enclave & Living Stage Studio' }
    ]
  },
  {
    key: 'creator_media_studio',
    label: 'Creator Studio & Revenue',
    icon: '🎨',
    defaultTab: 'digital_storefront',
    subTabs: [
      { key: 'digital_storefront', label: 'Digital Storefront & Pricing', icon: '🏪', description: 'Public Cart, Passes, Stripe & Web3 Crypto Checkout' },
      { key: 'public_playground', label: 'AI Studio & Playground', icon: '🎨', description: 'Customer Creative Sandbox & Multi-Modal Generation' },
      { key: 'personal_brand', label: 'Personal Brand Studio', icon: '🔥', description: 'Social Media Ghostwriter & Content Calendar' },
      { key: 'advertising', label: 'Advertising Campaign Studio', icon: '📢', description: 'AI Ad Copy, Headline Matrix & Funnel Creatives' },
      { key: 'syndication', label: 'Automated Syndication & Ads', icon: '🌐', description: '1-Click Fire Send Broadcaster & Multi-Channel Ad Suite' },
      { key: 'universal_studio', label: 'Universal AV Omni-Studio', icon: '🎛️', description: 'Consolidated Video, Broadcast, Neural Audio, & DAW Master Studio' },
      { key: 'media_studio', label: '🎬 Autonomous Media Studio', icon: '🎬', description: 'Autonomous Headless Media Production Studio, 13-Domain NLE & Visual Editor' }
    ]
  },
  {
    key: 'neural_intelligence',
    label: 'Neural Intelligence & IDE',
    icon: '🧠',
    defaultTab: 'ide',
    subTabs: [
      { key: 'ide', label: 'BS-CHAT Developer IDE', icon: '💻', description: 'Split-Pane Code Editor & IPC Telemetry Hub' },
      { key: 'gaming_lab', label: '🎮 Gaming & Process Memory Lab', icon: '🎮', description: 'Win32 Runtime Memory Manipulation, Pointer Tracking & Game Trainer Suite' },
      { key: 'deep_learning_studio', label: 'Deep Learning Studio', icon: '🧠', description: 'Computation Graphs & Model Fine-Tuning' },
      { key: 'agent_memory', label: 'Agent Memory & ChromaDB Vault', icon: '💾', description: 'Semantic Vector Memory & RAG Explorer' },
      { key: 'reasoning_attention', label: 'Self-Refinement & Attention', icon: '⚡', description: 'Transformer Heatmaps & Contextual Encodings' },
      { key: 'lexicon_dashboard', label: '🎭 Lexicon Engine Dashboard', icon: '🎭', description: 'Real-time semantic expansion and Persona trigger visualization' },
      { key: 'definitions', label: 'Definitions & Architectural Lore', icon: '📖', description: 'Knowledge Wiki, Glossaries & History Ledger' },
      { key: 'learning_material_hub', label: 'Educational Modules', icon: '🎓', description: 'Interactive Guides & System Explainers' }
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
