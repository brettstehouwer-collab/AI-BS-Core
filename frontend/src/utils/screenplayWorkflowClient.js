import { createScreenplayDraftCoordinator } from './screenplayDraftCoordinator.js';

// Shared route adapter for the Writing Studio's pending workflow integration.
// Editor ownership, draft preservation and explicit user transitions remain the
// caller's responsibility. Reads/recovery never silently adopt a new baseline.
export function createScreenplayWorkflowClient({ baseUrl, fetch: requestFetch = globalThis.fetch }) {
  const generations = new Map();
  const recoveryAttempts = new Map();
  const projectName = project => {
    if (typeof project !== 'string' || !project.trim()) throw new Error('An explicit project is required.');
    return project;
  };
  const request = async (path, project, payload) => {
    projectName(project);
    const base = typeof baseUrl === 'function' ? baseUrl() : baseUrl;
    if (typeof base !== 'string' || !base) throw new Error('The screenplay service address is unavailable.');
    const options = payload === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    };
    const suffix = payload === undefined ? `?project_name=${encodeURIComponent(project)}` : '';
    const response = await requestFetch(`${base.replace(/\/$/, '')}/api/screenwriting/${path}${suffix}`, options);
    let data;
    try { data = await response.json(); } catch { throw new Error('The screenplay service returned an unreadable acknowledgement.'); }
    if (!response.ok) {
      const error = new Error(typeof data?.detail === 'string' ? data.detail : 'The screenplay request failed.');
      error.status = response.status;
      throw error;
    }
    if (!data || typeof data !== 'object' || Array.isArray(data) || data.project !== project) {
      throw new Error('The screenplay response does not match the requested project.');
    }
    return data;
  };
  const coordinator = createScreenplayDraftCoordinator({ write: payload => request('write', payload.project_name, payload) });
  const update = (project, path, fields) => coordinator.updateWorkflow(project,
    payload => request(path, project, { ...fields, ...payload }));
  return {
    read(project) { return request('read', project); },
    acceptSnapshot(data) {
      const project = projectName(data?.project);
      coordinator.load(project, data.content, data.revision, data);
      generations.set(project, (generations.get(project) || 0) + 1);
    },
    snapshot: project => coordinator.snapshot(project),
    isDirty: (project, content) => coordinator.isDirty(project, content),
    idle: () => coordinator.idle(),
    save(project, content) { return coordinator.save(project, content, coordinator.snapshot(project)?.activeBranch); },
    createBranch(project, branchName) { return update(project, 'branch/create', { branch_name: branchName }); },
    switchBranch(project, branchName) {
      return coordinator.switchBranch(project, branchName, payload => request('branch/switch', project, payload));
    },
    startSprint(project, name, targetPages) { return update(project, 'sprint/start', { name, target_pages: targetPages }); },
    endSprint(project, sprintId) { return update(project, 'sprint/end', { sprint_id: sprintId }); },
    async recoverPending(project, operationId, action) {
      const generation = generations.get(project);
      const pending = coordinator.snapshot(project)?.pendingOperation;
      if (!pending || pending.id !== operationId || !['complete', 'abort'].includes(action)) {
        throw new Error('Explicit recovery of the currently loaded operation is required.');
      }
      await coordinator.idle();
      if (generations.get(project) !== generation || coordinator.snapshot(project)?.pendingOperation?.id !== operationId) {
        throw new Error('The project changed before recovery; preserve the draft and review the current operation.');
      }
      if (recoveryAttempts.get(project) === generation) {
        throw new Error('Recovery was already attempted; explicitly read and accept the current state before another attempt.');
      }
      // A lost response may have committed recovery. Never automatically replay
      // it or treat an ordinary read as permission to replace the local draft.
      recoveryAttempts.set(project, generation);
      return request('workflow/recover', project, { project_name: project, operation_id: operationId, action });
    },
  };
}
