const PENDING_KEY = 'aibs.local-maintenance.pending.v1';
const TERMINAL = new Set(['succeeded', 'failed', 'interrupted']);
function safeStorage() { try { return globalThis.localStorage; } catch { return null; } }
/** @param {number} ms */
function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
/** @param {unknown} error */
function httpStatus(error) { return error && typeof error === 'object' && 'status' in error ? error.status : null; }

/** @param {string} target @param {string|null|undefined} command */
export function isLocalMaintenanceBuild(target, command) {
  if (command) return false;
  const normalized = String(target).trim().replaceAll('\\', '/').replace(/\/+$/, '').toLowerCase();
  return ['ai-bs', 'ai_bs', 'frontend', 'backend', 'c:/ai-bs', 'c:/ai-bs/frontend', 'c:/ai-bs/backend'].includes(normalized);
}

/** @param {Storage|null} storage */
export function pendingProjectMaintenance(storage = safeStorage()) {
  try {
    const value = JSON.parse(storage?.getItem(PENDING_KEY) || 'null');
    return value && /^[0-9a-f]{32}$/.test(value.job_id) && typeof value.target === 'string' ? value : null;
  } catch { return null; }
}

/** @param {Storage|null} storage @param {any} value */
function remember(storage, value) {
  try { value ? storage?.setItem(PENDING_KEY, JSON.stringify(value)) : storage?.removeItem(PENDING_KEY); } catch { /* Server job remains durable when browser storage is unavailable. */ }
}

/** @param {any} options */
async function request(options) {
  const { baseUrl, body, fetchImpl, headers } = options;
  const response = await fetchImpl(`${baseUrl}/api/executive/run`, {
    method: 'POST', headers: typeof headers === 'function' ? await headers() : headers,
    body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.detail || data.message || `Local maintenance request returned HTTP ${response.status}`);
    Object.assign(error, { status: response.status });
    throw error;
  }
  return data;
}

/** @param {any} options */
export async function waitForProjectMaintenance(options) {
  const { baseUrl, headers, pending, fetchImpl = globalThis.fetch, storage = safeStorage(), active = () => true,
    sleep = delay, now = () => Date.now(),
    maxWaitMs = 45 * 60 * 1000, outageLimitMs = 120000 } = options;
  const until = now() + maxWaitMs;
  let last = { job_id: pending.job_id, status: 'queued', state: 'queued', message: 'Local maintenance is queued.' };
  let outageSince = null;
  while (now() < until && active()) {
    try {
      const protocolResponse = await fetchImpl(`${baseUrl}/api/health`, {
        headers: typeof headers === 'function' ? await headers() : headers
      });
      const protocol = await protocolResponse.json();
      if (!protocolResponse.ok || protocol.local_maintenance_protocol !== 1) throw new Error('The durable local maintenance handler is temporarily unavailable.');
      const data = await request({ baseUrl, headers, fetchImpl, body: {
        command_type: 'build_project', target: pending.target,
        payload: { maintenance_action: 'status', maintenance_job_id: pending.job_id }
      } });
      const job = data.result || data;
      if (job.job_id !== pending.job_id) {
        throw new Error(job.message || 'The API did not return the requested durable maintenance receipt.');
      }
      last = job;outageSince = null;
      if (TERMINAL.has(job.state)) { remember(storage, null);return data; }
    } catch (error) {
      if (httpStatus(error) === 401 || httpStatus(error) === 403) throw error;
      outageSince ??= now();
      if (now() - outageSince >= outageLimitMs) break;
    }
    await sleep(1000);
  }
  return { result: { ...last, status: 'queued', message: `${last.message || ''} The worker keeps running independently; its saved receipt will be checked when this view reopens.` } };
}

/** @param {any} options */
export async function requestProjectBuild(options) {
  const { baseUrl, target, command = null, action = 'start', headers, fetchImpl = globalThis.fetch, storage = safeStorage(),
    makeId = () => globalThis.crypto.randomUUID().replaceAll('-', ''), ...pollOptions } = options;
  if (!['start','restart'].includes(action)) throw new Error('Unknown local maintenance action.');
  if (!isLocalMaintenanceBuild(target, command)) {
    if (action !== 'start') throw new Error('Backend restart requires the canonical local project.');
    const data = await request({ baseUrl, headers, fetchImpl, body: { command_type: 'build_project', target,
      payload: { build_command: command, timeout_seconds: 300 } } });
    const job = data.result || data;
    // The server resolves canonical relative paths more precisely than the
    // command UI. Follow any acknowledged durable job without replaying the
    // original custom/legacy request or treating queued work as a completed build.
    if (/^[0-9a-f]{32}$/.test(job.job_id) && !TERMINAL.has(job.state)) {
      const pending = { job_id: job.job_id, target };
      remember(storage, pending);
      return waitForProjectMaintenance({ baseUrl, headers, fetchImpl, storage, pending, ...pollOptions });
    }
    return data;
  }
  // Check a read-only versioned capability first. An old API must never treat
  // a status request as its legacy synchronous build command.
  const protocolResponse = await fetchImpl(`${baseUrl}/api/health`, {
    headers: typeof headers === 'function' ? await headers() : headers
  });
  const protocol = await protocolResponse.json();
  if (!protocolResponse.ok || protocol.local_maintenance_protocol !== 1) {
    throw new Error('The local build/update handler is not loaded in this API yet. No maintenance job was submitted.');
  }
  const pending = { job_id: makeId(), target };
  remember(storage, pending);
  const body = { command_type: 'build_project', target,
    payload: { maintenance_action: action, maintenance_job_id: pending.job_id } };
  // A single identical retry is safe only because the server journals this
  // identifier before dispatch. It cannot start a second build for that ID.
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const data = await request({ baseUrl, headers, fetchImpl, body });
      const job = data.result || data;
      if (job.job_id !== pending.job_id) throw new Error(job.message || 'The local build was not acknowledged with its durable identifier.');
      if (TERMINAL.has(job.state)) { remember(storage, null);return data; }
      break;
    } catch (error) {
      if (httpStatus(error) === 401 || httpStatus(error) === 403) throw error;
      if (attempt === 1) break;
    }
  }
  return waitForProjectMaintenance({ baseUrl, headers, fetchImpl, storage, pending, ...pollOptions });
}

/** @param {any} job */
export function projectMaintenanceReply(job) {
  const icon = job.state === 'succeeded' ? '✅' : TERMINAL.has(job.state) ? '❌' : '⏳';
  const title = job.state === 'succeeded' ? 'Local update completed' : TERMINAL.has(job.state) ? 'Local update failed' : 'Local update in progress';
  const restart = job.restart?.api_ready === true ? 'Verified ready' : job.state === 'failed' ? 'Not verified' : 'Pending';
  return `${icon} **${title}**\n- **Job:** \`${job.job_id}\`\n- **Stage:** ${job.state}\n- **Backend:** ${restart}\n- **Deployment:** Local\n\n${job.message || ''}`;
}
