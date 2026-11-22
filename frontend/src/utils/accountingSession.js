// One verified identity per session. No automatic financial mutation retries.
/** @param {{uid: string; currentUid: () => string; getHeaders: () => Promise<Record<string, string>>; fetchImpl?: typeof fetch; timeoutMs?: number}} options */
export function createAccountingSession({ uid, currentUid, getHeaders, fetchImpl = fetch, timeoutMs = 8000 }) {
  let active = true;
  let mutating = false;
  const requests = new Set(/** @type {(() => void)[]} */ ([]));
  const retryKeys = new Map();
  const current = () => active && currentUid() === uid;
  function check() { if (!current()) throw new Error('Accounting account changed. Sign in again.'); }
  /** @param {string} url @param {RequestInit} [options] */
  async function request(url, options = {}) {
    check();
    const method = options.method || 'GET';
    const mutation = method !== 'GET';
    if (mutation && mutating) throw new Error('An accounting update is in progress.');
    if (mutation) mutating = true;
    const controller = new AbortController();
    const key = `${method}:${url}:${options.body || ''}`;
    /** @type {(reason: Error) => void} */
    let rejectCancel = () => {};
    /** @type {Promise<never>} */
    const cancelled = new Promise((_, reject) => { rejectCancel = reject; });
    const cancel = () => { controller.abort(); rejectCancel(new Error('Accounting request timed out or account changed. Check records before retrying an update.')); };
    requests.add(cancel);
    const timer = setTimeout(cancel, timeoutMs);
    try {
      return await Promise.race([cancelled, (async () => {
        const headers = await getHeaders(); check();
        if (controller.signal.aborted) throw new Error('Accounting request expired.');
        if (!headers.Authorization) throw new Error('Sign in to access accounting.');
        if (mutation && !retryKeys.has(key)) retryKeys.set(key, globalThis.crypto.randomUUID());
        const response = await fetchImpl(url, { ...options, method, cache: 'no-store', signal: controller.signal,
          headers: { 'Content-Type': 'application/json', ...options.headers, ...headers,
            ...(mutation ? { 'Idempotency-Key': retryKeys.get(key) } : {}) } });
        check();
        if (!response.ok) throw new Error(response.status === 401 || response.status === 403
          ? 'This account cannot access accounting.' : `Accounting request failed (${response.status}). Check records before retrying an update.`);
        const isCsv = /export-csv/.test(url);
        const data = isCsv ? await response.blob() : await response.json();
        check();
        if (controller.signal.aborted) throw new Error('Accounting request expired.');
        if (mutation) retryKeys.delete(key);
        return { ok: true, status: response.status, json: async () => data, blob: async () => data };
      })()]);
    } finally {
      clearTimeout(timer); requests.delete(cancel); if (mutation) mutating = false;
    }
  }
  return { request, dispose() { active = false; for (const cancel of requests) cancel(); requests.clear(); } };
}

/** @param {string} quantity @param {string} price */
export function decimalProductUSD(quantity, price) {
  /** @param {string} value @returns {[bigint, bigint]} */
  const parse = value => {
    if (!/^(0|[1-9]\d{0,16})(\.\d{1,18})?$/.test(value)) throw Error('Invalid decimal');
    const [whole, fraction = ''] = value.split('.');
    return [BigInt(whole + fraction), 10n ** BigInt(fraction.length)];
  };
  try {
    const [a, ad] = parse(quantity), [b, bd] = parse(price);
    const n = a * b * 100n, d = ad * bd;
    let cents = n / d; const remainder = n % d;
    if (remainder * 2n > d || (remainder * 2n === d && cents % 2n)) cents++;
    return `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
  } catch { return ''; }
}
