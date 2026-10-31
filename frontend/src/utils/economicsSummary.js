// Accept only explicitly reconciled, fresh evidence. Never coerce absence to zero.
const DAY = 86400000;
/** @param {unknown} value */
const dateValue = value => typeof value === 'string' && /(?:Z|\+00:00)$/.test(value) ? Date.parse(value) : NaN;
/** @param {string} value */
const group = value => value.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
/** @param {string} reason @returns {import("/types/domain").EconomicsMetricPresentation} */
const unavailable = reason => ({ value: 'Unavailable', status: 'unavailable', reason });

/** @param {unknown} rawMetric @param {string} expectedUnit @param {number} [now] @returns {import("/types/domain").EconomicsMetricPresentation} */
export function presentEconomicsMetric(rawMetric, expectedUnit, now = Date.now()) {
  const metric = rawMetric !== null && typeof rawMetric === "object" ? /** @type {Record<string, unknown>} */ (rawMetric) : null;
  if (metric?.status === 'stale') return { value: 'Stale', status: 'stale', reason: 'Evidence is no longer current.' };
  if (!metric || metric.status !== 'verified' || metric.verification !== 'reconciled'
    || metric.unit !== expectedUnit || typeof metric.source !== 'string'
    || !metric.source.trim() || metric.source.length > 500) {
    return unavailable(typeof metric?.reason === 'string' ? metric.reason.slice(0, 300) : 'Verified evidence is unavailable.');
  }
  if (typeof metric.observed_at !== "string" || typeof metric.fresh_until !== "string") return unavailable("Evidence dates are missing or invalid.");
  const observed = dateValue(metric.observed_at);
  const expires = dateValue(metric.fresh_until);
  if (!Number.isFinite(observed) || !Number.isFinite(expires) || observed > now + 60000 || expires <= observed) {
    return unavailable('Evidence dates are missing or invalid.');
  }
  if (expires <= now) return { value: 'Stale', status: 'stale', reason: 'Evidence has expired.' };
  const value = metric.value;
  // Keep financial strings exact, including amounts above Number.MAX_SAFE_INTEGER.
  /** @type {Record<string, RegExp>} */
  const formats = {
    USD: /^-?(?:0|[1-9]\d*)\.\d{2}$/,
    count: /^(?:0|[1-9]\d*)$/,
    percent: /^-?(?:0|[1-9]\d*)\.\d{2}$/,
    kWh: /^(?:0|[1-9]\d*)(?:\.\d{1,6})?$/,
    ms: /^(?:0|[1-9]\d*)(?:\.\d{1,3})?$/,
  };
  if (typeof value !== 'string' || value.length > 80 || !formats[expectedUnit]?.test(value) || /^-0\.0+$/.test(value)) {
    return unavailable('The source value has an invalid format or precision.');
  }
  const negative = value.startsWith('-');
  const [integer, fraction] = (negative ? value.slice(1) : value).split('.');
  const amount = `${negative ? '-' : ''}${expectedUnit === 'USD' ? '$' : ''}${group(integer)}${fraction === undefined ? '' : `.${fraction}`}`;
  const suffix = /** @type {Record<string, string>} */ ({ percent: '%', kWh: ' kWh', ms: ' ms' })[expectedUnit] || '';
  return { value: amount + suffix, status: 'verified', reason: 'Reconciled evidence', source: metric.source,
    observedAt: metric.observed_at, freshUntil: metric.fresh_until };
}

/** @returns {Promise<import("/types/domain").EconomicsSummary>} @param {{apiBase?: string; getHeaders: () => Promise<HeadersInit>; signal?: AbortSignal; fetchImpl?: typeof fetch; now?: () => number; isCurrentIdentity?: () => boolean}} options */
export async function readEconomicsSummary({ apiBase = '', getHeaders, signal, fetchImpl = fetch, now = Date.now,
  isCurrentIdentity = () => true }) {
  const requireCurrentIdentity = () => {
    signal?.throwIfAborted();
    if (!isCurrentIdentity()) throw new Error('Financial account changed.');
  };
  requireCurrentIdentity();
  const headers = await getHeaders();
  // Token lookup can finish after an identity change or timeout.
  requireCurrentIdentity();
  const response = await fetchImpl(`${apiBase.replace(/\/+$/, '')}/api/v1/economics/summary`, {
    method: 'GET', headers, signal, cache: 'no-store',
  });
  if (!response.ok) throw Object.assign(new Error(`Economics request failed (${response.status}).`), { status: response.status });
  const body = await response.json();
  requireCurrentIdentity();
  const timestamp = dateValue(body?.timestamp);
  const start = dateValue(body?.window?.start);
  const end = dateValue(body?.window?.end);
  const current = now();
  if (body?.schema !== 'aibs.economics.summary.v1' || body.currency !== 'USD'
    || !['unavailable', 'partial', 'verified'].includes(body.status)
    || !Number.isFinite(timestamp) || timestamp < current - 120000 || timestamp > current + 60000
    || end !== timestamp || end - start !== 30 * DAY
    || !['unconfirmed', 'partial', 'complete'].includes(body?.window?.coverage)
    || !body.metrics || typeof body.metrics !== 'object' || Array.isArray(body.metrics)) {
    throw new Error('Economics response has no current, supported evidence contract.');
  }
  return body;
}

/** @template T @param {{ request: (options: {signal: AbortSignal}) => Promise<T>; onState: (state: {status: string; summary: T | null; error: string | null}) => void; setTimer?: typeof setTimeout; clearTimer?: typeof clearTimeout }} options */
export function createEconomicsPoller({ request, onState, setTimer = setTimeout, clearTimer = clearTimeout }) {
  let active = false;
  let generation = 0;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let retryTimer;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let timeoutTimer;
  /** @type {AbortController | undefined} */
  let controller;
  /** @param {number} session */
  async function run(session) {
    if (!active || session !== generation) return;
    controller = new AbortController();
    const signal = controller.signal;
    onState({ status: 'loading', summary: null, error: null });
    try {
      /** @type {Promise<never>} */
      const timeout = new Promise((_, reject) => {
        timeoutTimer = setTimer(() => {
          controller?.abort();
          reject(new Error('Economics request timed out.'));
        }, 8000);
      });
      const summary = await Promise.race([Promise.resolve().then(() => request({ signal })), timeout]);
      if (active && session === generation) onState({ status: 'ready', summary, error: null });
    } catch (error) {
      if (active && session === generation) onState({ status: 'error', summary: null,
        error: error instanceof Error && 'status' in error && typeof error.status === 'number' && [401, 403].includes(error.status)
          ? 'Sign in with an authorized account to view financial records.'
          : 'Financial records are unavailable. The next check will retry automatically.' });
    } finally {
      if (active && session === generation) {
        clearTimer(timeoutTimer);
        retryTimer = setTimer(() => run(session), 30000);
      }
    }
  }
  return {
    start() { if (active) return; active = true; run(++generation); },
    stop() {
      active = false; generation++;
      clearTimer(retryTimer); clearTimer(timeoutTimer); controller?.abort();
    },
  };
}
