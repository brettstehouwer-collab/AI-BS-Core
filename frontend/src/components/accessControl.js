/**
 * Access Control & Feature Gating Configuration for AI-BS Matrix.
 * Controls role-based access to the 30+ tools and enables multi-tenant SaaS packaging.
 */

export const USER_TIERS = {
  ADMIN: {
    id: 'admin',
    name: 'Master Admin (Full Root Access)',
    badge: '👑 Root Admin',
    color: '#f85149',
    description: 'Unrestricted access to all 32 tools, host system terminal, VMs, security, and hardware telemetry.'
  },
  ENTERPRISE_ALL_ACCESS: {
    id: 'enterprise_all_access',
    name: 'AI-BS Enterprise All-Access Pass',
    badge: '💎 Enterprise All-Access',
    color: '#a371f7',
    description: 'Full commercial access to Screenwriting, Hospitality, B2B Growth, Creator Studio, and Accounting.'
  },
  SCREENWRITING: {
    id: 'screenwriting',
    name: 'ScreenplayStudio.ai Pro',
    badge: '🎬 Screenwriter Tier',
    color: '#58a6ff',
    description: 'Hollywood AST Screenplay Editor, Book-to-Script AI Matrix, FDX Serializer, Character Vault, Coverage Engine.'
  },
  HOSPITALITY: {
    id: 'hospitality',
    name: 'BanquetArchitect.com & Noto OS',
    badge: '🍷 Hospitality & Venues',
    color: '#d29922',
    description: 'Banquet Architect Studio, Table & Floor Planner, Dietary Registry, Lost Property, Client Scheduler.'
  },
  B2B_GROWTH: {
    id: 'b2b_growth',
    name: 'GrowthMatrix B2B Suite',
    badge: '🎯 B2B Growth Tier',
    color: '#3fb950',
    description: 'Bullshit Lead Matrix, OSINT Recon Hub, Automated Email Outreach, Action Items & Calendar, Clients CRM.'
  },
  CREATOR_MEDIA: {
    id: 'creator_media',
    name: 'Creator Studio & Video Suite',
    badge: '🎨 Creator Studio',
    color: '#bc8cff',
    description: 'Digital Storefront, Public Playground, Personal Brand Studio, Video Streaming, Media Vault.'
  },
  FREE_DEMO: {
    id: 'free_demo',
    name: 'Free Community / Demo',
    badge: '🌱 Free Tier',
    color: '#8b949e',
    description: 'Limited public preview of AI Studio, Public Playground, and Pricing Passes.'
  }
};

// Map each tab key to the tiers allowed to access it
export const TAB_PERMISSIONS = {
  // --- Admin / Host Root Tools ---
  shared_cloud_drive: ['admin', 'enterprise_all_access'],
  power_washing: ['admin', 'enterprise_all_access', 'b2b_growth'],
  terminal: ['admin'],
  vms: ['admin'],
  security_monitor: ['admin'],
  unified_crypto: ['admin'],
  deep_learning_studio: ['admin'],
  reasoning_attention: ['admin'],
  system_health: ['admin'],
  system_economics: ['admin'],
  brett_data_hub: ['admin'],
  agent_memory: ['admin'],

  // --- Screenwriting & Creation Studio ---
  ide: ['admin', 'enterprise_all_access', 'screenwriting', 'creator_media'],
  creation_suite: ['admin', 'enterprise_all_access', 'screenwriting'],
  unified_creation: ['admin', 'enterprise_all_access', 'screenwriting'],
  stehouwer_cms: ['admin', 'enterprise_all_access', 'screenwriting', 'creator_media'],
  noco_vision: ['admin', 'enterprise_all_access', 'screenwriting', 'creator_media'],

  // --- Hospitality & Event Architecture ---
  banquet_architect: ['admin', 'enterprise_all_access', 'hospitality'],
  notos_enterprise: ['admin', 'enterprise_all_access', 'hospitality'],
  lost_property: ['admin', 'enterprise_all_access', 'hospitality', 'b2b_growth'],

  // --- B2B Growth, Sales & Outreach ---
  leadmatrix: ['admin', 'enterprise_all_access', 'b2b_growth'],
  unified_osint: ['admin', 'enterprise_all_access', 'b2b_growth'],
  api_recon: ['admin', 'enterprise_all_access', 'b2b_growth'],
  email_client: ['admin', 'enterprise_all_access', 'b2b_growth', 'screenwriting'],
  clients: ['admin', 'enterprise_all_access', 'b2b_growth'],
  client_directory: ['admin', 'enterprise_all_access', 'b2b_growth'],
  advertising: ['admin', 'enterprise_all_access', 'b2b_growth', 'creator_media'],

  // --- Productivity, Calendar & Tasks ---
  calendar: ['admin', 'enterprise_all_access', 'screenwriting', 'hospitality', 'b2b_growth', 'creator_media'],
  unified_calendar: ['admin', 'enterprise_all_access', 'screenwriting', 'hospitality', 'b2b_growth', 'creator_media'],
  client_scheduler: ['admin', 'enterprise_all_access', 'hospitality', 'b2b_growth', 'creator_media'],

  // --- Finance & Commerce ---
  master_accounting: ['admin', 'enterprise_all_access', 'b2b_growth'],
  moneytrack: ['admin', 'enterprise_all_access', 'b2b_growth'],
  unified_financial: ['admin', 'enterprise_all_access', 'b2b_growth'],
  digital_storefront: ['admin', 'enterprise_all_access', 'creator_media'],

  // --- Creator & Media Studio ---
  public_playground: ['admin', 'enterprise_all_access', 'creator_media', 'screenwriting', 'free_demo'],
  personal_brand: ['admin', 'enterprise_all_access', 'creator_media', 'b2b_growth'],
  unified_media_gallery: ['admin', 'enterprise_all_access', 'creator_media', 'screenwriting'],
  video_agent: ['admin', 'enterprise_all_access', 'creator_media'],

  // --- Public, Analytics & General ---
  dashboard: ['admin', 'enterprise_all_access', 'screenwriting', 'hospitality', 'b2b_growth', 'creator_media', 'free_demo'],
  public_checkout: ['admin', 'enterprise_all_access', 'screenwriting', 'hospitality', 'b2b_growth', 'creator_media', 'free_demo'],
  beta: ['admin', 'enterprise_all_access', 'b2b_growth'],
  definitions: ['admin', 'enterprise_all_access', 'screenwriting', 'hospitality', 'b2b_growth', 'creator_media', 'free_demo'],
  learning_material_hub: ['admin', 'enterprise_all_access', 'screenwriting', 'hospitality', 'b2b_growth', 'creator_media', 'free_demo'],
  industry_grid: ['admin', 'enterprise_all_access', 'b2b_growth'],
  onboarding: ['admin', 'enterprise_all_access', 'hospitality', 'b2b_growth']
};

/**
 * Known Admin Email Addresses
 */
export const ADMIN_EMAILS = [
  'brettstehouwer@gmail.com',
  'brett@stehouwerpublishing.com',
  'footballstar0325@gmail.com',
  'footballsyat0325@gmail.com',
  'stehouwer@gmail.com',
  'stehouwerjulie@gmail.com',
  'julie.a.stehouwer@gmail.com',
  'julieannstehouwer@gmail.com',
  'juliestehouwer@gmail.com',
  'stehouwer.julie@gmail.com',
  'julie@stehouwerpublishing.com',
  'theseandaley@gmail.com',
  'sean@stehouwerpublishing.com',
  'rottierannajoy@gmail.com',
  'keith@evolution6media.com'
];

/**
 * Verified Firebase Authentication UIDs for Executive Administrators
 */
export const ADMIN_UIDS = [
  'sEq0Yw9wRhZBYOsvgR0J5RjKjMJ3', // footballstar0325@gmail.com
  'RaAUbpN4OPMwv2wKgU6qxwSBciB2', // stehouwerjulie@gmail.com
  'P6aAPT5n0QdiinJsmPEMI5DVsqj1', // theseandaley@gmail.com
  'YlAH2rLCEcZ71b9WrVCM3rS4MvD3', // rottierannajoy@gmail.com
  'Kv1rQ1ftcybun9PSHDIX90o3KGl2', // keith@evolution6media.com / footballsyat0325@gmail.com
];

/**
 * Determine a user's active tier based on auth profile, simulated tier, or local environment.
 */
export const getUserTier = (currentUser, simulatedTier = null) => {
  if (simulatedTier) {
    return USER_TIERS[simulatedTier] || USER_TIERS.FREE_DEMO;
  }

  // Local admin override
  if (typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.protocol === 'file:'
  )) {
    // In local dev, check if admin chose a simulated preview tier in localStorage
    const savedPreview = localStorage.getItem('aibs_preview_tier');
    if (savedPreview && USER_TIERS[savedPreview]) {
      return USER_TIERS[savedPreview];
    }
    return USER_TIERS.ADMIN;
  }

  if (!currentUser) {
    return USER_TIERS.ENTERPRISE_ALL_ACCESS;
  }

  const email = (currentUser.email || '').toLowerCase().trim();
  const uid = currentUser.uid || '';
  if (ADMIN_EMAILS.includes(email) || ADMIN_UIDS.includes(uid)) {
    return USER_TIERS.ADMIN;
  }

  // Check custom user claims / subscription plan saved in profile
  const userPlan = (currentUser.plan || currentUser.subscriptionTier || '').toUpperCase();
  if (USER_TIERS[userPlan]) {
    return USER_TIERS[userPlan];
  }

  return USER_TIERS.ENTERPRISE_ALL_ACCESS;
};

/**
 * Check if a tier has permission to view a specific tab.
 */
export const canAccessTab = (tierId, tabKey) => {
  if (tierId === 'admin' || tierId === 'enterprise_all_access') return true;
  const allowedTiers = TAB_PERMISSIONS[tabKey] || [];
  return allowedTiers.includes(tierId) || allowedTiers.includes('free_demo') || allowedTiers.includes('enterprise_all_access');
};

/**
 * Filter the master navigation hubs and subTabs to only show items accessible to the active tier.
 */
export const filterNavigationByTier = (masterHubs, tierId) => {
  if (tierId === 'admin') return masterHubs;

  return masterHubs
    .map(hub => {
      const allowedSubTabs = (hub.subTabs || []).filter(sub => canAccessTab(tierId, sub.key));
      if (allowedSubTabs.length === 0) return null;
      return {
        ...hub,
        subTabs: allowedSubTabs,
        defaultTab: allowedSubTabs[0]?.key || hub.defaultTab
      };
    })
    .filter(Boolean);
};
