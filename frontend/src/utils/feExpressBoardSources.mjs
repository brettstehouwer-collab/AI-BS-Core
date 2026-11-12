/** Classify saved provenance labels only; this does not attest a provider connection.
 * @param {unknown} source
 * @returns {'trulos'|'freightfinder'|'directfreight'|'sylectus'|'other'}
 */
export function boardForSource(source) {
  const text = String(source || '').trim();
  if (/^Trulos(?: Public Board)?(?: \((?:Live|cached)\))?$/i.test(text)) return 'trulos';
  if (/^FreightFinder$/i.test(text)) return 'freightfinder';
  if (/^Direct Freight$/i.test(text)) return 'directfreight';
  if (/^Sylectus$/i.test(text)) return 'sylectus';
  return 'other';
}
