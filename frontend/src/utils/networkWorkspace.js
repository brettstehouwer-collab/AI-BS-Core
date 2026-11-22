// This workspace accepts only the held contract. It never books or estimates earnings.
/** @param {{schema_version: number; status: string; payouts_enabled: boolean; job_dispatch_enabled: boolean; registration_enabled: boolean; ledger: Record<string, unknown>; hardware: unknown; treasury: unknown; idle_policy?: {status: string; enforced: boolean}} | null} data */
export function validateNetworkAvailability(data) {
  const fields = ['total_earned_usd', 'pending_usd', 'redeemed_usd', 'total_compute_hours'];
  if (!data || data.schema_version !== 1 || data.status !== 'unavailable'
    || data.payouts_enabled !== false || data.job_dispatch_enabled !== false || data.registration_enabled !== false
    || !data.ledger || fields.some(key => data.ledger[key] !== null)
    || data.hardware !== null || data.treasury !== null
    || data.idle_policy?.status !== 'unavailable' || data.idle_policy.enforced !== false) {
    throw new Error('Unrecognized network availability record.');
  }
}

/** @param {{request: (url: string, options?: RequestInit) => Promise<Pick<Response, "json">>; backendUrl?: string; onState: (state: {status: string; error?: string}) => void}} options */
export function createNetworkWorkspaceLoader({ request, backendUrl = '', onState }) {
  let active = true;
  let generation = 0;
  /** @type {Promise<void> | null} */
  let inFlight = null;
  function refresh() {
    if (!active) return Promise.resolve();
    if (inFlight) return inFlight;
    const current = ++generation;
    onState({ status: 'loading' });
    inFlight = (async () => {
      try {
        const response = await request(`${backendUrl.replace(/\/$/, '')}/v1/network/earnings/held-node`);
        validateNetworkAvailability(await response.json());
        if (active && current === generation) onState({ status: 'unavailable' });
      } catch {
        if (active && current === generation) onState({ status: 'error',
          error: 'Network status is unavailable. Sign in with an authorized account or refresh to retry.' });
      } finally {
        if (current === generation) inFlight = null;
      }
    })();
    return inFlight;
  }
  return { refresh, stop() { active = false; generation++; inFlight = null; } };
}

export function resolveCreationTool(search = '') {
  const tool = new URLSearchParams(search).get('subtab');
  if (!tool) return 'playwright';
  return ['playwright', 'video', 'comfyui', 'visual', 'network'].includes(tool) ? tool : 'unknown';
}

/** @param {{request: (url: string, options?: RequestInit) => Promise<Pick<Response, "json">>; backendUrl?: string; speed: number; auto: boolean}} options */
export async function requestFanControl({ request, backendUrl = '', speed, auto }) {
  if (!Number.isInteger(speed) || speed < 0 || speed > 100 || typeof auto !== 'boolean' || (!auto && speed < 30)) {
    throw new Error('Choose automatic control or a manual fan speed between 30 and 100 percent.');
  }
  const response = await request(`${backendUrl.replace(/\/$/, '')}/api/v1/hardware/gpu/fan-control`, {
    method: 'POST', body: JSON.stringify({ speed, auto }),
  });
  const data = await response.json();
  if (!['success', 'warning'].includes(data?.status) || typeof data.result?.success !== 'boolean'
    || (data.status === 'success') !== data.result.success) {
    throw new Error('Fan control response is unavailable. Refresh telemetry before retrying.');
  }
  return { success: data.result.success, enforcement_verified: data.result.enforcement_verified === true,
    message: typeof data.result.message === 'string' && data.result.message
    ? data.result.message : 'Fan control acknowledgement is unavailable. Refresh telemetry before retrying.' };
}

/** @param {{nvml_online?: boolean; field_status?: Record<string, string>; [key: string]: unknown} | null} telemetry @param {string} key @param {number} [maximum] */
export function reportedHardwareValue(telemetry, key, maximum = Infinity) {
  const value = telemetry?.[key];
  return telemetry?.nvml_online === true && telemetry.field_status?.[key] === 'measured'
    && typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= maximum ? value : null;
}
