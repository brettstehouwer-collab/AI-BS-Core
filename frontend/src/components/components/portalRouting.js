const PUBLIC_PORTAL_TABS = new Set(['fe_express', 'website_home']);

/** @param {string} tab @returns {string} */
function migratedTab(tab) {
  if (tab === 'steam_gaming' || tab === 'gaming_lab') return 'central_gaming_hub';
  if (['crypto', 'wallets', 'wallet', 'crypto_accounting', 'accounting', 'transfers'].includes(tab)) return 'unified_crypto';
  return tab;
}

/**
 * A saved public portal must not replace the main AI-BS entry point.
 * @param {string} search
 * @param {string | null} storedTab
 * @returns {string}
 */
export function resolveInitialWorkspaceTab(search, storedTab) {
  const params = new URLSearchParams(search);
  const requestedTab = params.get('tab') || (params.get('portal') === 'nda' ? 'nda_module' : null);
  if (requestedTab) return migratedTab(requestedTab === 'website_home' ? 'dashboard' : requestedTab);
  return storedTab && PUBLIC_PORTAL_TABS.has(storedTab) ? 'dashboard' : migratedTab(storedTab || 'dashboard');
}

/**
 * Keep the main workspace preference separate from restricted portal visits.
 * @param {string} activeTab
 * @returns {string | null}
 */
export function rememberedWorkspaceTab(activeTab) {
  return PUBLIC_PORTAL_TABS.has(activeTab) ? null : activeTab;
}
