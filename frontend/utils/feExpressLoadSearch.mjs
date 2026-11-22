import { boardForSource } from './feExpressBoardSources.mjs';

// Rank only actual saved listings. Missing provider values remain unknown.
/** @param {any[]} loads @param {any} options */
export function rankLoads(loads, options = {}) {
  const o = options;
  /** @param {any} value @param {any} query */
  const text = (value, query) => {
    const a = String(value || '').toLowerCase(), b = String(query || '').trim().toLowerCase();
    if (!b) return null;
    if (!a || a === 'unknown') return 0;
    if (a.includes(b)) return 1;
    const terms = b.split(/[^a-z0-9]+/).filter(Boolean);
    return terms.length ? terms.filter(t => a.includes(t)).length / terms.length * 0.8 : 0;
  };
  /** @param {any} value @param {any} query @param {boolean} maximum */
  const bound = (value, query, maximum = false) => {
    if (query === '' || query == null || !Number.isFinite(Number(query))) return null;
    if (value === '' || value == null || !Number.isFinite(Number(value)) || Number(value) <= 0) return 0;
    const actual = Number(value), target = Number(query);
    if (maximum ? actual <= target : actual >= target) return 1;
    return Math.max(0, 1 - Math.abs(actual - target) / Math.max(Math.abs(target), 1));
  };
  /** @param {any} value */
  const received = value => {
    if (!value) return -Infinity;
    const s = String(value);
    // SQLite CURRENT_TIMESTAMP is UTC; do not reinterpret it as each browser's local time.
    const parsed = Date.parse(/^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(s) ? s.replace(' ', 'T') + 'Z' : s);
    return Number.isFinite(parsed) ? parsed : -Infinity;
  };
  return loads.map((load, index) => {
    const distance = o.searchMiles === '' || o.searchMiles == null ? null : load.total_miles > 0 ? Math.max(0, 1 - Math.abs(Number(load.total_miles) - Number(o.searchMiles)) / Math.max(Number(o.searchMiles), 1)) : 0;
    const matches = [distance, text(load.origin_city_state, o.searchOrigin), text(load.dest_city_state, o.searchDest),
      text(load.equipment_type, o.searchEquipment), text(load.broker_name, o.searchBroker),
      bound(load.true_rpm ?? load.rpm, o.minRpm), bound(load.flat_rate_pay, o.minFlatPay),
      bound(load.weight_lbs, o.maxWeight, true), bound(load.deadhead_miles, o.maxDeadhead, true)];
    if (o.vehicleFilter && o.vehicleFilter !== 'ALL') matches.push(load.vehicle_match === o.vehicleFilter ? 1 : 0);
    const specified = matches.filter(v => v !== null);
    return { load, index, match: specified.length ? specified.reduce((n, v) => n + v, 0) / specified.length : 0, received: received(load.created_at) };
  }).filter(({ load }) => (!o.selectedBoard || o.selectedBoard === 'all' || boardForSource(load.source) === o.selectedBoard)
    && (!o.filterScore || o.filterScore === 'ALL' || load.score === o.filterScore))
    .sort((a, b) => b.match - a.match || (a.received === b.received ? 0 : b.received > a.received ? 1 : -1) || a.index - b.index)
    .map(item => item.load);
}
