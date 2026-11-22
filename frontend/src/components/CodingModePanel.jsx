import { useEffect, useState, useSyncExternalStore } from 'react';
import { useAppStore } from './useAppStore';
import { PreparationView } from './CodingPreparationPanel';
import CodingTaskHistory from './CodingTaskHistory';
import { preparationClientFor } from '/src/utils/projectPreparation.js';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';
import { createCodingModeClient } from '/src/utils/codingModeClient.js';

/** A focused view over the existing owner-scoped preparation journal.
 * @param {{memory: ReturnType<typeof import('/src/hooks/useConversationMemory.jsx').useConversationMemory>}} props
 */
export default function CodingModePanel({ memory }) {
  const client = preparationClientFor(useAppStore);
  const state = useSyncExternalStore(client.subscribe, client.getState, client.getState);
  const [mode, setMode] = useState('chat');
  const [stage, setStage] = useState('plan');
  const [modeClient] = useState(() => createCodingModeClient({
    getContext: () => ({backendUrl:useAppStore.getState().BACKEND_URL,actor:useAppStore.getState().currentUser?.uid || ''}),
    headers: actor => chatAuthHeaders({'Content-Type':'application/json'},actor),
  }));
  const executionState = useSyncExternalStore(modeClient.subscribe,modeClient.getState,modeClient.getState);
  const {execution,executionId,busy:executionBusy,error:executionError,capabilities} = executionState;
  useEffect(() => {
    const unsubscribe = useAppStore.subscribe(() => modeClient.syncContext());
    return () => { unsubscribe(); modeClient.disconnect(); };
  }, [modeClient]);
  const control = 'rounded border border-slate-600 px-3 py-1 text-xs disabled:opacity-40';
  /** @param {()=>unknown} action */
  const run = action => { Promise.resolve().then(action).catch(() => {}); };
  /** @param {string} action */
  const executionAction = action => modeClient.execution(action, {
    request_id:state.receipt?.request_id,plan_id:state.planRecord?.plan_id,proposal_id:state.proposalRecord?.proposal_id,
  });
  const connectCoding = async () => {
    const connected = await modeClient.connect();
    if (connected?.enabled && connected === modeClient.getState().capabilities && !client.getState().connected) await client.open();
  };
  const canCopyDraft = Boolean(memory?.viewReady && memory.isCurrent() && memory.owner === state.owner && state.connected);
  const copyDraft = () => {
    if (memory?.viewReady && memory.isCurrent() && memory.owner === client.getState().owner) {
      client.updateForm({ objective: useAppStore.getState().footerInput || '' });
    }
  };
  return <div className="px-3 py-1 text-slate-200">
    <div role="group" aria-label="BS Chat workspace" className="flex gap-2">
      <button type="button" className={control} aria-pressed={mode === 'chat'} onClick={() => setMode('chat')}>Chat</button>
      <button type="button" className={control} aria-pressed={mode === 'coding'} onClick={() => { setMode('coding'); run(connectCoding); }}>Coding</button>
    </div>
    <div hidden={mode !== 'coding'} className="mt-2 max-h-[65vh] overflow-auto rounded border border-slate-700 bg-slate-950 p-3">
      <h2 className="text-sm font-semibold">BS Chat Coding</h2>
      <div className="my-2 rounded border border-slate-700 p-2 text-xs" aria-label="Coding capabilities">
        {capabilities ? <>
          <p>Selected backend: Coding mode {capabilities.enabled ? 'enabled' : 'disabled'} · {capabilities.languages.join(', ')}</p>
          <p className="mt-1 text-amber-300">{capabilities.blocked_reason || 'Inspect individual verification results before applying any change.'}</p>
          <p className="mt-1">Project execution: {capabilities.execution_available ? 'available' : 'unavailable'} · Application: {capabilities.apply_available ? 'available' : 'unavailable'}</p>
        </> : <p>Connect to confirm Coding mode support for the selected backend and account.</p>}
        <button type="button" className={`${control} mt-2`} disabled={executionBusy} onClick={() => run(connectCoding)}>Refresh Coding connection</button>
        {executionBusy && stage === 'plan' && <p role="status" className="mt-2">Checking selected backend capabilities and retained history…</p>}
        {executionError && stage === 'plan' && <p role="alert" className="mt-2 text-amber-300">{executionError}</p>}
      </div>
      <fieldset disabled={capabilities?.enabled !== true}>
      <label className="mt-2 block text-xs">Project
        <select aria-label="Coding project" value="ai-bs" className="ml-2 rounded bg-slate-800 p-1" onChange={() => {}}>
          <option value="ai-bs">AI-BS</option>
        </select>
      </label>
      <p className="mt-2 text-xs text-slate-400">Python and JavaScript/React · Selected source only · Originals stay unchanged until reviewed application.</p>
      <div role="group" aria-label="Coding actions" className="my-3 flex gap-2">
        {['plan', 'implement', 'review'].map(value => <button key={value} type="button" className={control}
          aria-pressed={stage === value} onClick={() => setStage(value)}>{value[0].toUpperCase() + value.slice(1)}</button>)}
      </div>
      {stage === 'plan' && <p className="mb-2 text-xs">Select files and checks, save reviewed inputs, then explicitly request a plan. No project code runs during planning.</p>}
      {stage === 'implement' && <p className="mb-2 text-xs">Review a saved plan and explicitly generate a candidate below. A saved proposal alone does not establish passing checks.</p>}
      {stage !== 'review' && <PreparationView state={state} allowCodeProposal={stage === 'implement'}
        onField={(name, value) => client.updateForm({ [name]: value })} onPreview={() => run(client.preview)}
        onSave={() => run(client.save)} onRefresh={() => run(client.refresh)} onMore={() => run(client.more)}
        onInspect={id => run(() => client.inspect(id))} onRecover={id => run(() => client.recover(id))}
        onGeneratePlan={() => run(client.generatePlan)} onPlanInspect={id => run(() => client.inspectPlan(id))}
        onPlanRecover={id => run(() => client.recoverPlan(id))} onPlanCancel={id => run(() => client.cancelPlan(id))}
        onPlansRefresh={() => run(client.refreshPlans)} onPlansMore={() => run(client.morePlans)} onPlanId={client.setPlanId}
        onProposalReview={() => run(client.reviewProposal)} onProposalGenerate={() => run(client.generateProposal)}
        onProposalInspect={id => run(() => client.inspectProposal(id))} onProposalRecover={id => run(() => client.recoverProposal(id))}
        onProposalCancel={id => run(() => client.cancelProposal(id))} onProposalId={client.setProposalId}
        onProposalsRefresh={() => run(client.refreshProposals)} onProposalsMore={() => run(client.moreProposals)}
        onKeepPending={client.keepPending} onCopyDraft={copyDraft} canCopyDraft={canCopyDraft} onReconnect={() => run(client.open)} />}
      {stage === 'implement' && <section aria-label="Candidate verification" className="mt-3 rounded border border-slate-700 p-3 text-xs">
        <label className="block">Checks for this task
          <select aria-label="Coding execution mode" value={executionState.executionBackend} disabled={executionBusy}
            onChange={event => modeClient.selectExecutionBackend(event.target.value)} className="ml-2 rounded bg-slate-800 p-1">
            <option value="isolated">Isolated checks (default)</option>
            <option value="trusted_host" disabled={capabilities?.trusted_local_available !== true}>Trusted local checks · no VM</option>
          </select>
        </label>
        {executionState.executionBackend === 'trusted_host' ? <label className="mt-2 flex items-start gap-2 text-amber-200">
          <input type="checkbox" aria-label="Acknowledge trusted local checks for this task" checked={executionState.trustedLocalAck} disabled={executionBusy}
            onChange={event => modeClient.acknowledgeTrustedLocal(event.target.checked)} />
          <span>I authorize these selected checks to run on this computer with my Windows account's file and network access. This is not a VM. This choice applies to this task only.</span>
        </label> : <p className="mt-2">Isolated checks require the qualified isolated worker. If it is unavailable, this task stays blocked; trusted local checks are never selected automatically.</p>}
        <button type="button" className={`${control} mt-2`} disabled={executionBusy || execution?.state === 'RUNNING' || capabilities?.enabled !== true || state.proposalRecord?.state !== 'PROPOSAL_READY'
          || (executionState.executionBackend === 'trusted_host' && !executionState.trustedLocalAck)}
          onClick={() => executionAction('create')}>{executionState.executionBackend === 'trusted_host' ? 'Run selected trusted local checks' : 'Prepare isolated candidate verification'}</button>
      </section>}
      {stage === 'review' && <>
        <p className="mb-2 text-xs">Inspect recorded checks and diffs. Application requires the backend's current review token; stale originals reject.</p>
        <CodingTaskHistory />
      </>}
      {stage !== 'plan' && <section aria-label="Coding execution evidence" className="mt-3 text-xs">
        <h3 className="font-semibold">Saved candidate verifications</h3>
        <p className="mt-1 text-slate-400">History lists retained IDs. Inspect a record to recheck its complete evidence; reopening never reruns a task.</p>
        <button type="button" className={`${control} my-2`} disabled={executionBusy || capabilities?.enabled !== true}
          onClick={() => run(() => modeClient.refresh())}>Refresh saved verifications</button>
        {capabilities?.enabled === true && !executionBusy && executionState.items.length === 0 && <p className="mb-2 text-slate-400">No saved candidate verifications were returned for this account.</p>}
        {executionState.items.map(item => <div key={item.execution_id} className="mb-2 rounded border border-slate-700 p-2">
          <p className="break-all">{item.execution_id} · {item.state} · Project checks: {item.verification_status}</p>
          <button type="button" className={`${control} mt-1`} disabled={executionBusy}
            onClick={() => run(() => modeClient.execution('inspect',{execution_id:item.execution_id}))}>Inspect saved verification</button>
        </div>)}
        {executionState.nextCursor && <button type="button" className={`${control} mb-2`} disabled={executionBusy}
          onClick={() => run(() => modeClient.refresh(true))}>Load more saved verifications</button>}
        <label>Saved execution ID<input aria-label="Saved coding execution ID" value={executionId} maxLength={32}
          onChange={event => modeClient.setExecutionId(event.target.value)} disabled={executionBusy}
          className="ml-2 rounded bg-slate-800 p-1 font-mono" /></label>
        <div className="mt-2 flex flex-wrap gap-2">{['inspect', 'recover', 'cancel', 'review'].map(action =>
          <button type="button" key={action} className={control} disabled={executionBusy || !/^[a-f0-9]{32}$/.test(executionId)}
            onClick={() => executionAction(action)}>{action[0].toUpperCase() + action.slice(1)} saved execution</button>)}</div>
        {executionBusy && <p role="status">Waiting for retained execution evidence…</p>}
        {executionState.polling && <p role="status" className="mt-2">Refreshing running-check status every two seconds for up to ten minutes. Refreshing status never reruns checks.</p>}
        {executionError && <p role="alert" className="mt-2 text-amber-300">{executionError}</p>}
        {execution && <div className="mt-2"><p role="status">{execution.state} · Verification: {execution.verification_status}</p>
          <p className="mt-1 text-amber-300">{execution.blocked_reason || execution.reason || (execution.verification_status === 'passed' ? 'Recorded project checks passed. Review the candidate before applying changes.' : execution.execution_authorized ? 'Inspect the recorded checks below.' : 'Project checks have not run.')}</p>
          <p className="mt-1">Recorded execution mode: {execution.execution_mode || execution.execution_backend || 'unconfirmed'}{(execution.execution_mode || execution.execution_backend) === 'trusted_host' ? ' · Local account access; no VM isolation.' : ''}</p>
          <p>Execution authorized: {String(execution.execution_authorized)} · Application authorized: {String(execution.apply_authorized)}</p>
          {!!execution.static_checks?.length && <div className="mt-2"><h3 className="font-semibold">Static validation · separate from project tests</h3>
            {execution.static_checks.map((check, index) => <p key={index}>{check.path} · {check.kind}: {check.status}{check.reason ? ` · ${check.reason}` : ''}</p>)}
          </div>}
          {!!execution.checks?.length && <div className="mt-2"><h3 className="font-semibold">Selected project checks</h3>
            {execution.checks.map((check, index) => <div key={index} className="mt-2"><p>{check.argv?.join(' ')} · {check.status || (check.returncode === 0 ? 'passed' : Number.isInteger(check.returncode) ? 'failed' : 'not_run')} · Exit {check.returncode ?? 'unconfirmed'}</p>
              {(check.stdout || check.stderr || check.error) && <details><summary>Recorded check output</summary>
                <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap">{[check.stdout,check.stderr,check.error].filter(Boolean).join('\n')}</pre></details>}</div>)}
          </div>}
          {execution.review_diff && <details className="mt-2"><summary>Review candidate diff</summary>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap">{execution.review_diff}</pre></details>}
          {executionState.reviewToken && execution.can_apply === true && <button type="button" className={`${control} mt-3 border-amber-500 text-amber-100`} disabled={executionBusy}
            onClick={() => executionAction('apply')}>Apply reviewed changes</button>}
          {execution.application?.state && <p className="mt-2" role="status">Application: {execution.application.state}. Running services were not restarted by this action.</p>}
          <details className="mt-2"><summary>Recorded execution receipt</summary>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap">{JSON.stringify(execution, null, 2)}</pre></details>
        </div>}
      </section>}
      </fieldset>
    </div>
  </div>;
}
