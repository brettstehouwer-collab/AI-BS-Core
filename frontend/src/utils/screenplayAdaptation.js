/** Ownership and truthful state handling for protected manuscript adaptations. */
const TERMINAL = new Set(['complete', 'completed', 'success', 'error', 'failed', 'canceled', 'cancelled', 'interrupted', 'reset', 'not_found']);
const ACTIVE = new Set(['queued', 'processing']);
/** @param {unknown} value */
const validToken = value => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);
/** @param {unknown} status */
export const isAdaptationTerminal = status => typeof status === 'string' && TERMINAL.has(status);
/** @param {unknown} status */
export const isAdaptationComplete = status => status === 'complete' || status === 'completed' || status === 'success';

/** @param {any} data @param {string} projectName */
export function validateAdaptationAcceptance(data, projectName) {
  if (!data || data.status !== 'success' || data.contract !== 'create-only-v1' || !validToken(data.job_id)
      || !['project_name', 'project', 'current'].some(key => data[key] === projectName)
      || ['project_name', 'project', 'current'].some(key => data[key] !== undefined && data[key] !== projectName)
      || (data.task?.job_id !== undefined && data.task.job_id !== data.job_id)) {
    throw new Error('Adaptation acceptance was not confirmed. Check its status before retrying.');
  }
  return { projectName, job_id: data.job_id };
}

/** @param {any} data @param {string} projectName @param {string | undefined} [expectedJobId] */
export function readAdaptationJob(data, projectName, expectedJobId) {
  if (!data || typeof data !== 'object' || Array.isArray(data)
      || (data.project_name !== undefined && data.project_name !== projectName)
      || (data.job_id !== undefined && expectedJobId !== undefined && data.job_id !== expectedJobId)) {
    throw new Error('Adaptation ownership changed. Review the project before continuing.');
  }
  if (data.status === 'not_found' && validToken(expectedJobId)) {
    return { ...data, projectName, job_id: expectedJobId };
  }
  if (data.contract !== 'create-only-v1' || !validToken(data.job_id)
      || (!ACTIVE.has(data.status) && !TERMINAL.has(data.status))) {
    throw new Error('Adaptation status could not be verified. Existing files are retained.');
  }
  return { ...data, projectName };
}

/** @param {string} baseUrl @param {any} job @param {'cancel' | 'reset'} action @param {typeof fetch} [fetchImpl] */
export async function requestAdaptationAction(baseUrl, job, action, fetchImpl = fetch) {
  if (!['cancel', 'reset'].includes(action) || !validToken(job?.job_id) || typeof job?.projectName !== 'string') {
    throw new Error('Load a confirmed adaptation job before changing its state.');
  }
  const response = await fetchImpl(`${baseUrl}/api/screenplay/adapt/${action}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: job.projectName, job_id: job.job_id }),
  });
  const data = await response.json();
  if (!response.ok || data?.status !== 'success' || data.project_name !== job.projectName) {
    throw new Error(typeof data?.detail === 'string' ? data.detail : 'The adaptation state change was not confirmed. Refresh its status before retrying.');
  }
  return { ...job, status: action === 'cancel' ? 'canceled' : 'reset', connectionError: undefined,
    error: action === 'cancel' ? 'Canceled by user; retained files are preserved.' : 'Job ownership reset; retained files are preserved.' };
}

/**
 * Follow one job through SSE plus a bounded status poll. Polling also catches a
 * terminal record when an intermediary closes the SSE response without an error.
 * @param {{baseUrl: string, projectName: string, jobId: string, onStatus: (value: any) => any,
 * onError: (error: unknown) => void, eventSourceFactory: (url: string) => any,
 * fetchImpl?: typeof fetch, setIntervalImpl?: any, clearIntervalImpl?: any}} options
 */
export function monitorAdaptation({ baseUrl, projectName, jobId, onStatus, onError, eventSourceFactory,
  fetchImpl = fetch, setIntervalImpl = setInterval, clearIntervalImpl = clearInterval }) {
  if (!validToken(jobId)) throw new Error('A confirmed adaptation job is required before monitoring.');
  let closed = false;
  let polling = false;
  /** @type {AbortController | null} */
  let pending = null;
  /** @type {any} */
  let source = null;
  /** @type {any} */
  let interval = null;
  const stop = () => {
    if (closed) return;
    closed = true;
    if (interval !== null) clearIntervalImpl(interval);
    pending?.abort();
    source?.close();
  };
  /** @param {unknown} error */
  const fail = error => { if (!closed) { stop(); onError(error); } };
  /** @param {any} data */
  const deliver = data => {
    if (closed) return;
    const value = readAdaptationJob(data, projectName, jobId);
    if (isAdaptationTerminal(value.status)) stop();
    Promise.resolve(onStatus(value)).catch(onError);
  };
  const poll = async () => {
    if (closed || polling) return;
    polling = true;
    pending = new AbortController();
    const timeout = setTimeout(() => pending?.abort(), 15000);
    try {
      const response = await fetchImpl(`${baseUrl}/api/screenplay/adapt/status?project_name=${encodeURIComponent(projectName)}`,
        { signal: pending.signal });
      if (closed) return;
      if (!response.ok) throw new Error(`Adaptation status returned HTTP ${response.status}.`);
      const data = await response.json();
      if (!closed) deliver(data);
    } catch (error) { fail(error); }
    finally { clearTimeout(timeout); pending = null; polling = false; }
  };
  try {
    source = eventSourceFactory(`${baseUrl}/api/screenplay/adapt/stream?project_name=${encodeURIComponent(projectName)}`);
    source.onmessage = /** @param {{data: string}} event */ event => {
      try { deliver(JSON.parse(event.data)); } catch (error) { fail(error); }
    };
    source.onerror = fail;
    interval = setIntervalImpl(poll, 3500);
  } catch (error) { fail(error); }
  return stop;
}
