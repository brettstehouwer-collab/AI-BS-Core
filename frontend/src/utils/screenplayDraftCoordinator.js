/**
 * @typedef {{kind: string; id: string; source_branch: string; target_branch: string; before_revision: string; after_revision: string; [key: string]: unknown}} WorkflowOperation
 * @typedef {{initialized?: boolean; workflow_revision?: number; active_branch?: string; pending_operation?: WorkflowOperation | null}} WorkflowResponse
 * @typedef {{workflowAvailable: false; workflowInitialized: false; workflowRevision: undefined; activeBranch: undefined; pendingOperation: null} | {workflowAvailable: true; workflowInitialized: boolean; workflowRevision: number; activeBranch: string; pendingOperation: WorkflowOperation | null}} WorkflowState
 * @typedef {WorkflowState & {revision: string; savedContent: string; context: number; blocked: boolean; error: unknown}} DraftState
 * @typedef {{project_name: string; expected_revision: string; expected_workflow_revision?: number; content?: string; branch?: string; branch_name?: string}} DraftWrite
 * @typedef {WorkflowResponse & {revision?: string; project?: string; content?: string; unchanged?: boolean; status?: string; parsed?: import("/types/screenwriting").ParsedScreenplay; warning?: string}} DraftResponse
 * @typedef {(payload: DraftWrite) => Promise<DraftResponse>} DraftRequest
 */
// One request queue for every interactive manuscript mutation. Revision baselines
// advance only after an acknowledged write, never by silently rereading the server.
/** @param {{write: DraftRequest}} options */
export function createScreenplayDraftCoordinator({ write }) {
  /** @type {Map<string, DraftState>} */
  const projects = new Map();
  // Comparison only: no original text is normalized or written here.
  /** @param {string} left @param {string} right */
  const sameEditorText = (left, right) => left.replace(/\r\n?/g, '\n') === right.replace(/\r\n?/g, '\n');
  /** @type {Promise<unknown>} */
  let pending = Promise.resolve();
  /** @template T @param {() => Promise<T>} operation */
  const enqueue = operation => {
    const result = pending.then(operation);
    pending = result.catch(() => {});
    return result;
  };
  const workflowFields = ['initialized', 'workflow_revision', 'active_branch', 'pending_operation'];
  /** @param {WorkflowResponse | undefined | null} value @param {boolean} [required] @returns {WorkflowState} */
  const readWorkflow = (value, required = false) => {
    if (!value || !workflowFields.some(field => Object.hasOwn(value, field))) {
      if (required) throw new Error('Response is missing workflow metadata; reload explicitly before another change.');
      return { workflowAvailable: false, workflowInitialized: false, workflowRevision: undefined, activeBranch: undefined, pendingOperation: null };
    }
    const { initialized, workflow_revision: epoch, active_branch: branch, pending_operation: operation } = value;
    if (typeof initialized !== 'boolean' || typeof epoch !== 'number' || !Number.isSafeInteger(epoch) || epoch < 0 ||
        typeof branch !== 'string' || !branch.trim() || branch !== branch.trim() ||
        operation === undefined || (!initialized && (epoch !== 0 || operation !== null))) {
      throw new Error('Invalid project workflow metadata; saving is disabled.');
    }
    if (operation !== null && (typeof operation !== 'object' ||
        !['WRITE', 'SWITCH'].includes(operation.kind) ||
        !['id', 'source_branch', 'target_branch', 'before_revision', 'after_revision'].every(key => typeof operation[key] === 'string' && operation[key]))) {
      throw new Error('Invalid pending workflow operation; preserve the project for recovery.');
    }
    return { workflowAvailable: true, workflowInitialized: initialized, workflowRevision: epoch, activeBranch: branch,
      pendingOperation: operation ? Object.freeze({ ...operation }) : null };
  };
  /** @param {string} project */
  const baseline = project => {
    const state = projects.get(project);
    if (!state?.revision) throw new Error('Load the project before saving. Its revision is unavailable.');
    if (state.blocked) throw state.error;
    return state;
  };
  /** @param {WorkflowState} state */
  const workflowPayload = state => state.workflowAvailable ? {
    initialized: state.workflowInitialized, workflow_revision: state.workflowRevision,
    active_branch: state.activeBranch, pending_operation: state.pendingOperation,
  } : {};
  /** @param {string} project @param {string | undefined} content @param {DraftRequest} request @param {string} [branch] @param {string} [mode] @param {boolean} [skipUnchanged] */
  const mutate = (project, content, request, branch, mode = 'write', skipUnchanged = false) => {
    // Capture the load/branch context when queued, not when eventually dispatched.
    // Metadata-only acknowledgements may advance the epoch of this same context.
    const captured = projects.get(project);
    const context = captured?.context;
    const assertContext = () => {
      if (projects.get(project) !== captured || captured?.context !== context) {
        throw new Error('Project or branch context changed; keep your draft and reload before saving it.');
      }
    };
    return enqueue(async () => {
      assertContext();
      const state = baseline(project);
      if (mode !== 'write' && !state.workflowAvailable) throw new Error('Workflow controls require a fresh project workflow response.');
      if (mode === 'write' && branch !== undefined && state.workflowAvailable && branch !== state.activeBranch) {
        throw new Error('The draft belongs to a different branch; preserve it before switching.');
      }
      if (mode === 'write' && typeof content !== 'string') throw new Error('A manuscript change requires text content.');
      if (mode === 'switch' && (typeof branch !== 'string' || !branch.trim())) throw new Error('A target branch is required.');
      if (skipUnchanged && state.savedContent === content) return { revision: state.revision, unchanged: true, ...workflowPayload(state) };
      /** @type {DraftWrite} */
      const payload = { project_name: project, expected_revision: state.revision };
      if (state.workflowAvailable) payload.expected_workflow_revision = state.workflowRevision;
      if (mode === 'write') Object.assign(payload, { content, branch });
      if (mode === 'switch') payload.branch_name = branch;
      try {
        const result = await request(payload);
        assertContext();
        if (typeof result?.revision !== 'string' || !result.revision) {
          throw new Error('Save response has no revision. Your local draft is retained; reload explicitly before another save.');
        }
        if (result.project !== undefined && result.project !== project) throw new Error('Save response belongs to a different project.');
        if (result.content !== undefined && typeof result.content !== 'string') throw new Error('Save response contains invalid manuscript content.');
        const next = readWorkflow(result, state.workflowAvailable || mode !== 'write');
        if (next.pendingOperation) throw new Error('An interrupted workflow operation requires explicit recovery.');
        if (!state.workflowAvailable && next.workflowInitialized) throw new Error('Reload initialized workflow state before saving this project.');
        const sameBranchSwitch = mode === 'switch' && branch === state.activeBranch;
        if (result.unchanged === true && mode === 'switch' && !sameBranchSwitch) {
          throw new Error('An unchanged acknowledgement cannot switch the active branch.');
        }
        const unchanged = result.unchanged === true || sameBranchSwitch;
        if ((unchanged || mode === 'metadata') && result.revision !== state.revision) {
          throw new Error('An unchanged or metadata-only action unexpectedly changed the manuscript revision.');
        }
        if (result.unchanged === true && mode === 'write' &&
            (!sameEditorText(content ?? '', state.savedContent) ||
             (typeof result.content === 'string' && !sameEditorText(result.content, state.savedContent)))) {
          throw new Error('Unchanged acknowledgement does not match the manuscript content.');
        }
        if (state.workflowAvailable) {
          const expectedEpoch = unchanged ? state.workflowRevision :
            mode !== 'write' || state.workflowInitialized ? state.workflowRevision + 1 : 0;
          if (next.workflowRevision !== expectedEpoch ||
              next.activeBranch !== (mode === 'switch' ? branch : state.activeBranch) ||
              (mode === 'write' && next.workflowInitialized !== state.workflowInitialized) ||
              (mode !== 'write' && !next.workflowInitialized)) {
            throw new Error('Save response has an unexpected workflow epoch or branch; reload explicitly.');
          }
        }
        if (mode === 'switch' && typeof result.content !== 'string') throw new Error('Branch response is missing manuscript content.');
        if ((mode === 'metadata' || (mode === 'switch' && branch === state.activeBranch)) &&
            result.content !== undefined && !sameEditorText(result.content, state.savedContent)) {
          throw new Error('Workflow action unexpectedly replaced manuscript content.');
        }
        const savedContent = mode === 'metadata' || sameBranchSwitch ? state.savedContent :
          result.unchanged === true ? content : typeof result.content === 'string' ? result.content : content;
        if (mode === 'switch' && branch !== state.activeBranch) state.context++;
        Object.assign(state, next, { revision: result.revision, savedContent });
        return result;
      } catch (error) {
        // A lost response may have committed on the server. Never re-read and
        // silently rebase a local draft, or poison a separately reloaded state.
        if (projects.get(project) === state && state.context === context) {
          state.blocked = true;
          state.error = error;
        }
        throw error;
      }
    });
  };
  return {
    /** @param {string} project @param {string} content @param {string} revision @param {WorkflowResponse} [workflow] */
    load(project, content, revision, workflow) {
      try {
        if (!project || typeof content !== 'string' || typeof revision !== 'string' || !revision) {
          throw new Error('Project response is missing its content or revision; saving is disabled.');
        }
        const metadata = readWorkflow(workflow, workflow !== undefined);
        const error = metadata.pendingOperation ? new Error('An interrupted writing operation requires explicit recovery before saving.') : null;
        projects.set(project, { revision, savedContent: content, ...metadata, context: 0, blocked: Boolean(error), error });
      } catch (error) {
        const previous = projects.get(project);
        if (previous) {
          previous.context++;
          previous.blocked = true;
          previous.error = error;
        }
        throw error;
      }
    },
    /** @param {string} project @returns {DraftState | null} */
    snapshot(project) { const state = projects.get(project); return state ? {...state} : null; },
    /** @param {string} project @param {string} content */
    isDirty(project, content) { return !projects.has(project) || projects.get(project)?.savedContent !== content; },
    /** @param {string} project @param {string} content @param {string} [branch] */
    save(project, content, branch) { return mutate(project, content, write, branch, 'write', true); },
    /** @param {string} project @param {string} content @param {DraftRequest} request */
    mutate(project, content, request) { return mutate(project, content, request); },
    /** @param {string} project @param {DraftRequest} request */
    updateWorkflow(project, request) { return mutate(project, undefined, request, undefined, 'metadata'); },
    /** @param {string} project @param {string} branch @param {DraftRequest} request */
    switchBranch(project, branch, request) { return mutate(project, undefined, request, branch, 'switch'); },
    idle() { return pending; },
  };
}
