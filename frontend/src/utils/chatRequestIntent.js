// This selects a read-only service route; the backend remains the intent authority.
// Only current user text belongs here, never attachments or conversation history.
/** @param {unknown} value @returns {boolean} */
export function isComfyStatusQuery(value) {
  if (typeof value !== 'string' || value.length > 128000) return false;
  const text = value.normalize('NFKC').trim().toLowerCase();
  if (!/\bcomfy(?:[\s_-]*ui)?\b/.test(text)) return false;
  // Explicit creation keeps its existing route even when availability is a condition.
  const creation = '(?:generate|create|render|draw|paint|make|produce|design|sketch)';
  if (new RegExp('^(?:please\\s+)?(?:' + creation + '\\b|/(?:image|video|voice|imagine|render|generate)\\b|(?:can|could|would|will)\\s+you\\s+(?:please\\s+)?' + creation + '\\b)').test(text)) return false;
  return /\b(?:status|health|running|online|offline|available|availability|reachable|responsive|working|up|check|ping)\b/.test(text);
}
