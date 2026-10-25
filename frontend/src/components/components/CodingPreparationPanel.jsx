import React, { useState, useSyncExternalStore } from 'react';
import { useAppStore } from './useAppStore';
import { preparationClientFor } from '/src/utils/projectPreparation.js';

const planLabels = { RUNNING: 'Planning', INCOMPLETE: 'Incomplete', PLAN_PROPOSED: 'Plan proposed', NEEDS_CLARIFICATION: 'Needs clarification',
  FAILED: 'Failed', TIMED_OUT: 'Timed out', CANCELLED: 'Cancelled', INTERRUPTED: 'Interrupted' };
const terminalPlans = new Set(['PLAN_PROPOSED', 'NEEDS_CLARIFICATION', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'INTERRUPTED']);
const proposalLabels = { PROPOSAL_READY: 'Saved proposal', RUNNING: 'Generating proposal', INCOMPLETE: 'Incomplete',
  FAILED: 'Failed', TIMED_OUT: 'Timed out', CANCELLED: 'Cancelled', INTERRUPTED: 'Interrupted' };
const terminalProposals = new Set(['PROPOSAL_READY', 'FAILED', 'TIMED_OUT', 'CANCELLED', 'INTERRUPTED']);

function InputEvidence({ record }) {
  return <div className="mt-3 text-xs">
    <table className="w-full text-left"><caption className="text-left font-semibold">Reviewed inputs</caption>
      <thead><tr><th>File</th><th>Role</th><th>Bytes</th><th>SHA-256</th></tr></thead>
      <tbody>{record.files.map(file => <tr key={file.relative_path} className="border-t border-slate-700">
        <td className="break-all py-1">{file.relative_path}</td><td>{file.role}</td><td>{file.length}</td>
        <td><code title={file.sha256}>{file.sha256.slice(0, 12)}…</code></td>
      </tr>)}</tbody>
    </table>
    <div className="mt-2 font-semibold">Selected checks</div>
    {record.checks.map((check, index) => <code key={index} className="block break-all">{check.argv.join(' ')}</code>)}
  </div>;
}

/** Preparation evidence only. This view has no run/apply action. */
export function PreparationView({ state, onField, onPreview, onSave, onRefresh, onMore, onInspect, onRecover,
  onKeepPending, onCopyDraft, onReconnect, canCopyDraft, onGeneratePlan, onPlanInspect, onPlanRecover, onPlanCancel,
  onPlansRefresh, onPlansMore, onPlanId, onProposalReview, onProposalGenerate, onProposalInspect, onProposalRecover,
  onProposalCancel, onProposalId, onProposalsRefresh, onProposalsMore }) {
  const control = 'rounded border border-slate-600 px-2 py-1 text-xs disabled:opacity-40';
  if (!state.connected) return <section aria-label="Coding preparation" className="rounded border border-slate-700 bg-slate-900 p-3 text-sm text-slate-200">
    <p>{state.busy ? 'Checking preparation access…' : 'Connect to view preparations for the selected backend and account.'}</p>
    <button type="button" className={control} disabled={state.busy} onClick={onReconnect}>Connect to selected backend</button>
    {state.error && <p role="alert" className="mt-2 text-amber-300">{state.error}</p>}
  </section>;
  const planning = Boolean(state.planBusy || state.planCancelBusy || state.proposalBusy || state.proposalCancelBusy);
  const locked = state.busy || planning || Boolean(state.pendingId);
  const activePlanId = state.planPendingId || state.planRecord?.plan_id;
  const canCancel = Boolean(activePlanId && (state.planPendingId || !terminalPlans.has(state.planRecord?.state)));
  const activeProposalId = state.proposalPendingId || state.proposalRecord?.proposal_id;
  const canCancelProposal = Boolean(activeProposalId && (state.proposalPendingId || !terminalProposals.has(state.proposalRecord?.state)));
  const fields = [['editable', 'Files to change', 'src/example.py'], ['verification', 'Tests to keep', 'tests/test_example.py'],
    ['dependencies', 'Dependencies or configuration', 'package.json\npackage-lock.json'], ['python', 'Python test modules', 'tests.test_example'],
    ['node', 'Node test files', 'tests/example.test.js'], ['npm', 'Existing npm script', 'test']];
  return <section aria-label="Coding preparation" className="rounded border border-slate-700 bg-slate-900 p-3 text-sm text-slate-200">
    <h3 className="font-semibold">Prepare a code change</h3>
    <p className="mt-1 text-xs text-slate-400">Repository: AI-BS. Select files and checks, preview them, then save the reviewed inputs.</p>
    <p className="mt-1 text-xs text-amber-300">Tests not run. Project execution requires the isolated worker.</p>
    <fieldset disabled={locked} className="mt-3">
      <label className="block text-xs">What should change?
        <textarea aria-label="What should change?" value={state.form.objective} maxLength={8000} rows={2}
          onChange={event => onField('objective', event.target.value)} className="mt-1 w-full rounded border border-slate-600 bg-slate-950 p-2" />
      </label>
      <button type="button" className={`${control} mt-1`} disabled={!canCopyDraft || locked} onClick={onCopyDraft}>Use current chat draft</button>
      <p className="mt-2 text-xs text-slate-400">Enter one relative path or check target per line. Keep tests and configuration out of the files to change.</p>
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {fields.map(([name, label, placeholder]) => <label key={name} className="block text-xs">{label}
          <textarea aria-label={label} value={state.form[name]} maxLength={10000} rows={2} placeholder={placeholder}
            onChange={event => onField(name, event.target.value)} className="mt-1 w-full rounded border border-slate-600 bg-slate-950 p-2 font-mono" />
        </label>)}
      </div>
    </fieldset>
    <div className="mt-3 flex flex-wrap gap-2">
      <button type="button" className={control} disabled={locked} onClick={onPreview}>Preview inputs</button>
      <button type="button" className={control} disabled={state.busy || planning || (!state.preview && !state.pendingId)} onClick={onSave}>
        {state.pendingId ? 'Retry same save' : 'Save reviewed inputs'}
      </button>
      <button type="button" className={control} disabled={state.busy || planning} onClick={onRefresh}>Refresh saved preparations</button>
    </div>
    {state.pendingId && <div className="mt-2 text-xs text-amber-300">
      <p>Save not yet confirmed: {state.pendingId}. Retain this ID and inspect its saved state.</p>
      <button type="button" className={`${control} mr-2 mt-1`} disabled={state.busy} onClick={() => onInspect(state.pendingId)}>Inspect pending preparation</button>
      <button type="button" className={`${control} mt-1`} disabled={state.busy} onClick={onKeepPending}>Keep pending ID and edit a new request</button>
    </div>}
    {state.preview && <InputEvidence record={state.preview} />}
    {state.receipt && <div className="mt-3 rounded border border-slate-600 p-2">
      <div role="status">{state.receipt.state} · Tests not run</div>
      <div className="break-all text-xs">Preparation {state.receipt.request_id}</div>
      <p className="mt-1 text-xs text-slate-400">This inspects saved inputs. Current project files were not rechecked.</p>
      <InputEvidence record={state.receipt} />
      {state.receipt.state === 'PREPARED' && <div className="mt-3 border-t border-slate-600 pt-3">
        <h4 className="font-semibold">Stehouwer implementation plan</h4>
        <p className="mt-1 text-xs text-slate-400">Uses these saved inputs. A proposed plan does not change code or verify tests.</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" className={control} disabled={Boolean(state.busy || planning || state.receipt.durable !== true)} onClick={onGeneratePlan}>
            {state.planPendingId ? 'Retry same plan request' : 'Generate Stehouwer plan'}
          </button>
          <button type="button" className={control} disabled={state.busy || planning} onClick={onPlansRefresh}>Load saved plans</button>
          <button type="button" className={control} disabled={Boolean(!canCancel || state.busy || state.planCancelBusy)}
            onClick={() => onPlanCancel(activePlanId)}>Cancel planning</button>
        </div>
        {state.planBusy && <p role="status" className="mt-2 text-xs">Waiting for planning evidence…</p>}
        {state.planCancelRequested && <p className="mt-2 text-xs text-amber-300">Cancellation requested. Inspect saved state to confirm the outcome.</p>}
        {state.planPendingId && <div className="mt-2 break-all text-xs text-amber-300">
          Plan request not yet confirmed: {state.planPendingId}. Keep this ID for inspection or the same-ID retry.
          <button type="button" className={`${control} ml-2`} disabled={state.busy || planning}
            onClick={() => onPlanInspect(state.planPendingId)}>Inspect pending plan</button>
        </div>}
        {state.planRecord && <div className="mt-3 rounded border border-slate-600 p-2 text-xs">
          <div role="status">{planLabels[state.planRecord.state] || 'Unconfirmed'} · Tests not run</div>
          <div className="mt-1 break-all text-slate-400">Plan {state.planRecord.plan_id}</div>
          {state.planRecord.error_code && <p className="mt-1 text-amber-300">{state.planRecord.error_code}</p>}
          {state.planRecord.proposal && <>
            <p className="mt-2 whitespace-pre-wrap break-words">{state.planRecord.proposal.summary}</p>
            <ol className="mt-2 list-inside list-decimal space-y-2">
              {state.planRecord.proposal.steps.map(step => <li key={step.path}><strong>{step.path}</strong>
                <p className="mt-1 whitespace-pre-wrap break-words">{step.change}</p></li>)}
            </ol>
            {state.planRecord.proposal.questions.length > 0 && <div className="mt-3 text-amber-200">
              <h5 className="font-semibold">Questions to resolve</h5>
              <ul className="mt-1 list-inside list-disc">{state.planRecord.proposal.questions.map((question, index) => <li key={index}>{question}</li>)}</ul>
              <p className="mt-2 text-slate-400">Update the objective above, then preview and save a new preparation before requesting a revised plan. This saved plan is preserved.</p>
            </div>}
          </>}
          <button type="button" className={`${control} mt-2`} disabled={state.busy || planning}
            onClick={() => onPlanRecover(state.planRecord.plan_id)}>Recover current plan</button>
          {state.planRecord.state === 'PLAN_PROPOSED' && !state.planRecord.proposal?.questions.length && <div className="mt-3 border-t border-slate-600 pt-3">
            <h5 className="font-semibold">Code proposal · Review only</h5>
            <p className="mt-1 text-slate-400">Review this saved plan before asking Stehouwer for code. Nothing is applied, and tests have not run.</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button type="button" className={control} disabled={Boolean(state.busy || planning)} onClick={onProposalReview}>Review saved plan</button>
              <button type="button" className={control} disabled={Boolean(state.busy || planning || !state.proposalReview)} onClick={onProposalGenerate}>
                {state.proposalPendingId ? 'Retry same proposal request' : 'Generate code proposal'}
              </button>
              <button type="button" className={control} disabled={Boolean(!canCancelProposal || state.busy || state.planBusy || state.planCancelBusy || state.proposalCancelBusy)}
                onClick={() => onProposalCancel(activeProposalId)}>Cancel proposal</button>
            </div>
            {state.proposalReview && <p className="mt-2 break-all text-slate-400">Complete saved inputs reviewed · {state.proposalReview.reviewed_plan_sha256}</p>}
            {state.proposalBusy && <p role="status" className="mt-2">Waiting for proposal evidence…</p>}
            {state.proposalCancelRequested && <p className="mt-2 text-amber-300">Cancellation requested. Inspect the saved proposal to confirm its outcome.</p>}
            {state.proposalPendingId && <div className="mt-2 break-all text-amber-300">
              Proposal request not yet confirmed: {state.proposalPendingId}. Keep this ID to inspect after a reload or retry the same request.
              <button type="button" className={`${control} ml-2`} disabled={Boolean(state.busy || planning)}
                onClick={() => onProposalInspect(state.proposalPendingId)}>Inspect pending proposal</button>
            </div>}
            {state.proposalRecord && <div className="mt-3 rounded border border-slate-600 p-2">
              <div role="status">{proposalLabels[state.proposalRecord.state] || 'Unconfirmed'} · Tests not run · Not applied</div>
              <div className="mt-1 break-all text-slate-400">Proposal {state.proposalRecord.proposal_id}</div>
              {state.proposalRecord.error_code && <p className="mt-1 text-amber-300">{state.proposalRecord.error_code}</p>}
              {state.proposalRecord.proposal && <>
                <p className="mt-2 whitespace-pre-wrap break-words">{state.proposalRecord.proposal.summary}</p>
                {state.proposalRecord.proposal.files.map(file => <div key={file.path} className="mt-3 border-t border-slate-700 pt-2">
                  <strong className="break-all">{file.path}</strong>
                  <details className="mt-1"><summary className="cursor-pointer">Saved file hashes</summary>
                    <p className="break-all">Base SHA-256: <code>{file.base_sha256}</code></p>
                    <p className="break-all">Candidate SHA-256: <code>{file.proposed_sha256}</code></p>
                  </details>
                  <pre aria-label={'Diff for ' + file.path} className="mt-2 max-h-64 overflow-auto rounded bg-slate-950 p-2 text-xs">{file.diff}</pre>
                  <details className="mt-2"><summary className="cursor-pointer">Candidate source</summary>
                    <pre aria-label={'Candidate source for ' + file.path} className="mt-2 max-h-64 overflow-auto rounded bg-slate-950 p-2 text-xs">{file.content}</pre>
                  </details>
                </div>)}
              </>}
              <button type="button" className={`${control} mt-2`} disabled={Boolean(state.busy || planning)}
                onClick={() => onProposalRecover(state.proposalRecord.proposal_id)}>Recover current proposal</button>
            </div>}
            <details className="mt-3"><summary className="cursor-pointer">Inspect a saved proposal</summary>
              <button type="button" className={`${control} mt-2`} disabled={Boolean(state.busy || planning)} onClick={onProposalsRefresh}>Load saved proposals</button>
              {!state.proposalsLoaded && <p className="mt-2 text-slate-400">Load saved IDs and status for this plan. Inspection rechecks the candidate separately.</p>}
              {state.proposalsLoaded && !(state.proposalItems || []).length && <p className="mt-2 text-slate-400">No saved code proposals for this plan.</p>}
              {(state.proposalItems || []).map(item => <div key={item.proposal_id} className="mt-2 border-t border-slate-700 pt-2">
                <p className="break-all">{item.proposal_id} · {proposalLabels[item.state] || 'Unconfirmed'}</p>
                <p className="text-slate-400">Candidate not rechecked</p>
                <button type="button" className={`${control} mr-2 mt-1`} disabled={Boolean(state.busy || planning)}
                  onClick={() => onProposalInspect(item.proposal_id)}>Inspect saved proposal</button>
                <button type="button" className={`${control} mt-1`} disabled={Boolean(state.busy || planning)}
                  onClick={() => onProposalRecover(item.proposal_id)}>Recover saved proposal</button>
              </div>)}
              {state.proposalNextCursor && <button type="button" className={`${control} mt-2`} disabled={Boolean(state.busy || planning)} onClick={onProposalsMore}>Load more proposals</button>}
              <p className="mt-2 text-slate-400">IDs seen in this session are temporary. Keep a proposal ID to inspect or recover it after a reload under this same preparation and plan.</p>
              {(state.proposalSeen || []).map(item => <div key={item.proposal_id} className="mt-2 break-all">
                {item.proposal_id} · {proposalLabels[item.state] || 'Unconfirmed'}
                <button type="button" className={`${control} ml-2`} disabled={Boolean(state.busy || planning)}
                  onClick={() => onProposalInspect(item.proposal_id)}>Inspect seen proposal</button>
              </div>)}
              <label className="mt-2 block">Saved proposal ID
                <input aria-label="Saved proposal ID" value={state.proposalIdInput || ''} maxLength={32} disabled={Boolean(state.busy || planning)}
                  onChange={event => onProposalId(event.target.value)} className="mt-1 w-full rounded border border-slate-600 bg-slate-950 p-1 font-mono" />
              </label>
              <div className="mt-1 flex flex-wrap gap-2">
                <button type="button" className={control} disabled={Boolean(state.busy || planning || !/^[a-f0-9]{32}$/.test(state.proposalIdInput || ''))}
                  onClick={() => onProposalInspect(state.proposalIdInput)}>Inspect entered proposal ID</button>
                <button type="button" className={control} disabled={Boolean(state.busy || planning || !/^[a-f0-9]{32}$/.test(state.proposalIdInput || ''))}
                  onClick={() => onProposalRecover(state.proposalIdInput)}>Recover entered proposal ID</button>
              </div>
            </details>
            {state.proposalError && state.proposalError !== state.error && <p role="alert" className="mt-2 text-amber-300">{state.proposalError}</p>}
          </div>}
        </div>}
        <details className="mt-3"><summary className="cursor-pointer">Saved model plans</summary>
          {!state.plansLoaded && <p className="mt-2 text-xs">Load saved plans to discover retained IDs after a restart or reload.</p>}
          {state.plansLoaded && !(state.planItems || []).length && <p className="mt-2 text-xs">No saved plans for these inputs.</p>}
          {(state.planItems || []).map(item => <div key={item.plan_id} className="mt-2 border-t border-slate-700 pt-2 text-xs">
            <div className="break-all">{item.plan_id} · {planLabels[item.state] || 'Unconfirmed'}</div>
            <p className="text-slate-400">Proposal not rechecked</p>
            <button type="button" className={`${control} mr-2 mt-1`} disabled={state.busy || planning}
              onClick={() => onPlanInspect(item.plan_id)}>Inspect saved plan</button>
            <button type="button" className={`${control} mt-1`} disabled={state.busy || planning}
              onClick={() => onPlanRecover(item.plan_id)}>Recover saved plan</button>
          </div>)}
          {state.planNextCursor && <button type="button" className={`${control} mt-2`} disabled={state.busy || planning} onClick={onPlansMore}>Load more plans</button>}
          <label className="mt-3 block text-xs">Saved plan ID
            <input aria-label="Saved plan ID" value={state.planIdInput || ''} maxLength={32} disabled={state.busy || planning}
              onChange={event => onPlanId(event.target.value)} className="mt-1 w-full rounded border border-slate-600 bg-slate-950 p-1 font-mono" />
          </label>
          <button type="button" className={`${control} mt-1`} disabled={state.busy || planning || !/^[a-f0-9]{32}$/.test(state.planIdInput || '')}
            onClick={() => onPlanInspect(state.planIdInput)}>Inspect entered plan ID</button>
        </details>
        {state.planError && state.planError !== state.error && <p role="alert" className="mt-2 text-amber-300">{state.planError}</p>}
      </div>}
    </div>}
    <details className="mt-3"><summary className="cursor-pointer">Saved preparations</summary>
      {!state.historyLoaded && <p className="mt-2 text-xs">Saved history has not loaded.</p>}
      {state.historyLoaded && !state.items.length && <p className="mt-2 text-xs">No saved preparations for this backend and account.</p>}
      {state.items.map(item => <div key={item.request_id} className="mt-2 border-t border-slate-700 pt-2 text-xs">
        <div>{item.title} · {item.state}</div><div className="break-all text-slate-400">{item.request_id} · Inputs not rechecked</div>
        <button type="button" className={`${control} mr-2 mt-1`} disabled={state.busy || planning} onClick={() => onInspect(item.request_id)}>Inspect</button>
        <button type="button" className={`${control} mt-1`} disabled={state.busy || planning} onClick={() => onRecover(item.request_id)}>Recover saved state</button>
      </div>)}
      {state.nextCursor && <button type="button" className={`${control} mt-2`} disabled={state.busy || planning} onClick={onMore}>Load more</button>}
      {state.unconfirmedIds.map(id => <div key={id} className="mt-2 break-all text-xs text-amber-300">Unconfirmed request {id}
        <button type="button" className={`${control} ml-2`} disabled={state.busy} onClick={() => onInspect(id)}>Inspect</button>
      </div>)}
    </details>
    {state.busy && <p role="status" className="mt-2 text-xs">Checking preparation evidence…</p>}
    {state.error && <p role="alert" className="mt-2 text-amber-300">{state.error}</p>}
  </section>;
}

export default function CodingPreparationPanel({ memory }) {
  const client = preparationClientFor(useAppStore);
  const state = useSyncExternalStore(client.subscribe, client.getState, client.getState);
  const [open, setOpen] = useState(false);
  const run = action => { Promise.resolve().then(action).catch(() => {}); };
  const canCopyDraft = Boolean(memory?.viewReady && memory.isCurrent() && memory.owner === state.owner && state.connected);
  const copyDraft = () => {
    if (memory?.viewReady && memory.isCurrent() && memory.owner === client.getState().owner) {
      client.updateForm({ objective: useAppStore.getState().footerInput || '' });
    }
  };
  return <div className="px-3 py-1 text-xs">
    <button type="button" className="rounded border border-slate-600 px-2 py-1 text-slate-300" aria-expanded={open}
      onClick={() => { setOpen(!open); if (open) client.close(); else run(client.open); }}>Prepare code change</button>
    {open && <div className="mt-2 max-h-[65vh] overflow-auto"><PreparationView state={state}
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
      onKeepPending={client.keepPending} onCopyDraft={copyDraft} canCopyDraft={canCopyDraft} onReconnect={() => run(client.open)} />
    </div>}
  </div>;
}
