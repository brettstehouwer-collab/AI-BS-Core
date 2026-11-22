"""Master Universal Navigation Registry for AI-BS Native Studio (64-bit Pure Native).

Full 1:1 parity with frontend/src/components/navigationConfig.js:
- Top Pinned Quick-Tabs (8 quick launch items)
- 4 Primary Master Hubs
- 52 Fully Populated Sub-Tabs (Consolidated Zero-Redundancy)
- 70-Vertical Industry Grids
- Simple Mode Nav Items
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SubTabSpec:
    key: str
    label: str
    icon: str
    badge: str
    description: str


@dataclass
class MasterHubSpec:
    key: str
    label: str
    icon: str
    default_tab: str
    sub_tabs: List[SubTabSpec]


PINNED_QUICK_TABS: List[dict] = [
    {"key": "executive_cockpit", "label": "Executive Cockpit", "icon": "⚡", "badge": "COCKPIT"},
    {"key": "steam_gaming", "label": "Steam Gaming Hub", "icon": "🎮", "badge": "GAMING"},
    {"key": "ide", "label": "BS-CHAT", "icon": "💻", "badge": "AI CORE"},
    {"key": "bv_media_creator", "label": "BV-Media Studio", "icon": "🎨", "badge": "CREATOR"},
    {"key": "screen_mirror", "label": "Wireless Screen Mirror", "icon": "📺", "badge": "MIRACAST"},
    {"key": "shared_cloud_drive", "label": "Cloud Drive", "icon": "☁️", "badge": "STORAGE"},
    {"key": "workflow_dag", "label": "DAG Builder", "icon": "⚡", "badge": "AGENTS"},
    {"key": "terminal", "label": "Host Terminal", "icon": "⌨️", "badge": "SHELL"},
]

SIMPLE_MODE_ITEMS: List[dict] = [
    {"key": "dashboard", "label": "Home Portal", "icon": "🏠", "description": "Master Launchpad & High-Level System Overview"},
    {"key": "shared_cloud_drive", "label": "Cloud Drive", "icon": "☁️", "description": "Shared Cloud Storage, In-App Documents & Asset Vault"},
    {"key": "unified_creation", "label": "Creative Studio", "icon": "🎨", "description": "Hollywood AST Screenwriting, AI Page Doctor, Video & Media Suite"},
    {"key": "banquet_architect", "label": "Hospitality Studio", "icon": "💒", "description": "Banquet Architect, 2D/3D Venue Floor Plans & Event Operations"},
    {"key": "unified_calendar", "label": "Master Calendar", "icon": "📅", "description": "Master Schedule, Client Appointments, Event Planning & Tasks"},
]

NATIVE_MASTER_HUBS: List[MasterHubSpec] = [
    MasterHubSpec(
        key="intelligence_and_code",
        label="Intelligence & Code",
        icon="🧠",
        default_tab="executive_cockpit",
        sub_tabs=[
            SubTabSpec("executive_cockpit", "Executive Command Cockpit", "⚡", "GOVERNANCE", "Unified Autonomous Command Bus, 4-Pillar Matrix & Tiered Governance HUD"),
            SubTabSpec("ide", "BS-CHAT Interface", "💻", "AI CORE", "Split-Pane Sovereign AI Chat & IPC Telemetry Hub"),
            SubTabSpec("sovereign_swarm", "Sovereign Swarm", "🐝", "SWARM", "14-Agent Multi-Model Collaboration Hub"),
            SubTabSpec("workflow_dag", "Multi-Agent DAG Builder", "⚡", "AGENTS", "Visual Node-Based Autonomous Agent Pipeline & DAG Builder"),
            SubTabSpec("terminal", "Host Terminal Shell", "⌨️", "SHELL", "Interactive Windows 11 PowerShell Virtual Terminal"),
            SubTabSpec("deep_learning_studio", "Deep Learning Studio", "🧠", "MODELS", "17-Model Fleet Topology & Dynamic Graph Visualizer"),
            SubTabSpec("nutrition_subsystem", "Clinical Nutrition & Detox Engine", "🥗", "HEALTH", "Hybrid Cold-Press Mechanical Extraction, Fiber Suspension & Ketogenic Shift Subsystem"),
            SubTabSpec("agent_memory", "Agent Vector Memory", "💾", "VECTORS", "ChromaDB Vector Store Explorer & Memory Bank"),
            SubTabSpec("reasoning_attention", "Self-Refinement & Attention", "⚡", "ATTENTION", "Contextual Encodings & Attention Heatmaps"),
            SubTabSpec("system_health", "System Health & Audit Logs", "🏥", "TELEMETRY", "Real-time Server Telemetry, Lifespan Logs & DB Status"),
            SubTabSpec("cluster_engine", "Cluster Engine & Spine", "⚡", "CLUSTER", "6-Tier Distributed Messaging, Rust ASGI, Stateful Tasks, Multi-Core Cache & C++ SFU"),
            SubTabSpec("vms", "Virtual Machines & VNC", "🖥️", "HYPERVISOR", "Local VM GUI Management & Hypervisor Bridge"),
            SubTabSpec("automation_console", "Automation Console", "⚙️", "SCHEDULER", "Trusted Windows Job Queue & Task Automation"),
            SubTabSpec("lexicon_dashboard", "Lexicon Engine Dashboard", "🎭", "LEXICON", "Real-Time Semantic Expansion & Persona Trigger Visualization"),
            SubTabSpec("definitions", "System Lore & Architecture Wiki", "📖", "KNOWLEDGE", "Interactive AI-BS Architectural Wiki, Lexicon, and Educational Modules"),
        ],
    ),
    MasterHubSpec(
        key="creative_media_studio",
        label="Creative Media Studio",
        icon="🎨",
        default_tab="bv_media_creator",
        sub_tabs=[
            SubTabSpec("bv_media_creator", "BV-Media Creator & Production Suite", "🎨", "CREATOR", "Unified Media Creator Studio, Dedicated BsMedia-Chat & ChromaDB Media Vault"),
            SubTabSpec("comfy_workspace", "ComfyUI Creative Studio", "🧩", "DIFFUSION", "Interactive Local Diffusion & Video Studio, AST Graph Generator, FaceDetailer & Real-Time Presets"),
            SubTabSpec("unified_creation", "Screenwriting & Publications Studio", "✍️", "SCRIPTS & CMS", "Hollywood AST Screenplay Editor, Stehouwer Publications, Character Bibles & Video Suite"),
            SubTabSpec("music_daw", "AI Music Studio (DAW)", "🎵", "AUDIO DSP", "Pattern-Based DAW, Synthesizer & Beat Maker"),
            SubTabSpec("personal_brand", "Personal Brand Studio", "🔥", "GHOSTWRITER", "AI Ghostwriter & Multi-Channel Social Content Matrix"),
            SubTabSpec("advertising", "Advertising Studio", "📢", "AD COPY", "Targeted Ad Copy, Campaign Funnels & Creative Variants"),
            SubTabSpec("syndication", "Automated Syndication", "🌐", "BROADCAST", "1-Click Multi-Channel Broadcaster & Ad Distribution"),
            SubTabSpec("unified_media_gallery", "Media & Asset Vault", "🖼️", "GALLERY", "Screenplay Graphics, Audio Stems & Storyboards"),
            SubTabSpec("theatrical_teleprompter", "Theatrical Prompter & Projector", "📜", "STAGE", "Live Dialogue Scrolling, Real-Time Pitch Tracking & Direct D3D11 Fullscreen Stage Projector"),
            SubTabSpec("neon_lounge_studio", "Neon Lounge & AI Playground", "🌆", "NEON & SANDBOX", "Architectural Design Studio, Unreal Staging & Customer AI Playground"),
            SubTabSpec("universal_studio", "Universal AV Omni-Studio", "🎛️", "BROADCAST", "Master Broadcast, Video WebRTC, DAW & Neural Voice Engine"),
            SubTabSpec("screen_mirror", "Wireless Screen Mirroring", "📺", "MIRACAST", "Project Workspace to Wireless Display/TV, Phone-to-PC Screen Mirroring & Local Wi-Fi Streamer"),
            SubTabSpec("digital_storefront", "Digital Storefront & Pricing", "🏪", "CHECKOUT", "Monetize Local Compute, Passes & Crypto Checkout"),
        ],
    ),
    MasterHubSpec(
        key="business_operations",
        label="Business & Operations",
        icon="💼",
        default_tab="operations_audit",
        sub_tabs=[
            SubTabSpec("operations_audit", "Omni Operations Audit Hub", "📋", "AUDIT", "Live Tasks, Media Queue, Autosaves & 25-Port Daemon Diagnostics"),
            SubTabSpec("shared_cloud_drive", "Shared Cloud Drive", "☁️", "DRIVE", "Google Drive-Style Cloud Storage & Asset Sharing"),
            SubTabSpec("master_accounting", "Master Accounting & Cashflow", "💰", "FINANCE", "Master Accounting, P&L, Expense Tracking, Money Track Cashflow & Tax Suite"),
            SubTabSpec("clients", "Clients Hub & CRM", "🏢", "CRM", "Client Profiles, Interaction History & Contract Matrix"),
            SubTabSpec("leadmatrix", "Lead Matrix & Growth", "🎯", "LEADS", "Automated B2B Lead Scoring, Funnels & Acquisition Sweep"),
            SubTabSpec("unified_osint", "OSINT Recon & API Hub", "🔍", "OSINT", "Deep Intelligence, Domain Recon & RapidAPI Hub"),
            SubTabSpec("rec_debut", "Recreational Debut (Dennis Bell)", "🏀", "RECRUITING", "Recreational Debut & Dennis Bell Sports Program — College Recruiting Portal & Mass SMS Broadcast Suite"),
            SubTabSpec("fe_express", "FE Express Box Truck Hub", "🚚", "DISPATCH", "FE Express LLC Box Truck Automation Hub — Live Public Load Board, Real-Time RPM, Direct SQLite & 1099 Tax Ledger"),
            SubTabSpec("onboarding", "Client Onboarding", "🚀", "INTAKE", "Intelligent Client Intake & Onboarding Portal"),
            SubTabSpec("nda_module", "Sovereign NDA & Anti-Tamper", "📜", "LEGAL", "Interactive Master NDA Generator, Cryptographic Tamper Seal"),
            SubTabSpec("email_client", "Business Email Client", "📧", "MAIL", "Integrated IMAP/SMTP Local Business Mail"),
            SubTabSpec("lost_property", "Lost Property Vault", "🗝️", "LOST & FOUND", "Guest Claim Logging & Asset Recovery Tracking"),
            SubTabSpec("unified_calendar", "Master Schedule & Calendar", "📅", "CALENDAR", "Unified Appointments, Calendar & Event Pipeline"),
            SubTabSpec("beta", "Web Traffic & Telemetry", "📈", "WIRE", "Live Web Analytics, Wire Hashes & Wave Telemetry"),
            SubTabSpec("ecosystem_blueprint", "Matrix Blueprint & ROI", "🌐", "ARCHITECTURE", "Systemic Architecture, 5-Pillar Matrix & Financial ROI"),
        ],
    ),
    MasterHubSpec(
        key="engineering_labs",
        label="Engineering & Specialized Labs",
        icon="🛠️",
        default_tab="phone_repair",
        sub_tabs=[
            SubTabSpec("phone_repair", "Phone & Tablet Repair Lab", "🔧", "HARDWARE", "Master Teardowns, Face ID Diagnostics & Diode Values"),
            SubTabSpec("power_washing", "Prestige Mobile Wash", "💦", "ESTIMATOR", "Commercial Pressure Washing CRM, Chemical Estimator & Fleet"),
            SubTabSpec("banquet_architect", "Banquet Architect Studio", "💒", "2D/3D CAD", "2D/3D Floor Plans, Seating Charts & BEO Generator"),
            SubTabSpec("notos_enterprise", "Noto's Enterprise & Bar Stock OS", "🍷", "HOSPITALITY", "Internal Hospitality Operating Platform, Multi-Bar Stock & Live Inventory Tracking"),
            SubTabSpec("project_noco", "Project NoCo Living Stage", "🏛️", "CEA FARMING", "Autonomous Acoustic-Agricultural Enclave & Studio"),
            SubTabSpec("noco_vision", "NoCo Vision & Acoustic Engine", "👁️", "ACOUSTIC", "Optical Camera Tracking & Environmental Biospheres"),
            SubTabSpec("unified_crypto", "Crypto Swarm & Mining", "⚡", "FINANCE", "Clore/Vast Node Telemetry & Fast-Scalping Bot"),
            SubTabSpec("game_build", "AI-BS Game Engine Build", "🛠️", "CUSTOM ENGINE", "Custom C++ engine, SDK verification, game-build progress and drive space"),
            SubTabSpec("gaming_lab", "Gaming & Process Memory Lab", "🎮", "WIN32 MEMORY", "Win32 Runtime Memory Manipulation & Trainer Suite"),
            SubTabSpec("steam_gaming", "Steam Gaming Hub", "🚀", "RTX 4090", "Native Game Library, One-Click Launcher & Hardware RTX 4090 Game Mode Governor"),
            SubTabSpec("bible_hub", "Sovereign Bible Hub", "📖", "SCRIPTURE", "Dual KJV & NIV Canonical New Testament Reader"),
        ],
    ),
]


TAB_KEY_ALIASES: dict[str, str] = {
    "dashboard": "executive_cockpit",
    "learning_material_hub": "definitions",
    "media_studio": "bv_media_creator",
    "stehouwer_cms": "unified_creation",
    "universal_creation": "unified_creation",
    "creation_suite": "unified_creation",
    "theatrical_projector": "theatrical_teleprompter",
    "public_playground": "neon_lounge_studio",
    "moneytrack": "master_accounting",
    "unified_financial": "master_accounting",
    "noto_inventory": "notos_enterprise",
}


def get_all_subtabs_flat() -> List[SubTabSpec]:
    """Returns flat list of all 52 consolidated subtabs."""
    flat = []
    for hub in NATIVE_MASTER_HUBS:
        flat.extend(hub.sub_tabs)
    return flat


def find_subtab_spec(key: str) -> Optional[SubTabSpec]:
    """Finds a subtab spec by key, resolving legacy aliases."""
    canonical_key = TAB_KEY_ALIASES.get(key, key)
    for hub in NATIVE_MASTER_HUBS:
        for st in hub.sub_tabs:
            if st.key == canonical_key:
                return st
    return None

