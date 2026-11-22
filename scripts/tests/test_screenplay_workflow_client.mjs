import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createScreenplayDraftCoordinator } from '../../frontend/src/utils/screenplayDraftCoordinator.js';

const workflow = (epoch = 1, branch = 'main', extras = {}) => ({
  initialized: true, workflow_revision: epoch, active_branch: branch, pending_operation: null, ...extras,
});
const acknowledged = (revision, epoch, branch = 'main', extras = {}) => ({
  revision, ...workflow(epoch, branch), ...extras,
});
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};

test('queued workflow saves send acknowledged epochs and preserve exact text', async () => {
  const calls = [];
  const coordinator = createScreenplayDraftCoordinator({ write: async payload => {
    calls.push(payload);
    return acknowledged(`r${calls.length + 1}`, calls.length + 1);
  }});
  coordinator.load('Fixture', 'original\r\n', 'r1', workflow());
  await Promise.all([coordinator.save('Fixture', 'first\r\n', 'main'), coordinator.save('Fixture', 'second\n', 'main')]);
  assert.deepEqual(calls.map(p => p.expected_workflow_revision), [1, 2]);
  assert.deepEqual(calls.map(p => p.expected_revision), ['r1', 'r2']);
  assert.deepEqual(calls.map(p => p.content), ['first\r\n', 'second\n']);
  const result = await coordinator.save('Fixture', 'second\n', 'main');
  assert.equal(result.workflow_revision, 3);
  assert.equal(calls.length, 2);
});

test('uninitialized workflow epoch zero is sent; legacy reads still support ordinary saves', async () => {
  const calls = [];
  const coordinator = createScreenplayDraftCoordinator({ write: async payload => {
    calls.push(payload); return { revision: 'r2' };
  }});
  coordinator.load('Legacy', 'old', 'r1');
  await coordinator.save('Legacy', 'new');
  assert.equal(Object.hasOwn(calls[0], 'expected_workflow_revision'), false);
  coordinator.load('New', 'old', 'r1', workflow(0, 'main', { initialized: false }));
  await assert.rejects(coordinator.save('New', 'new'), /workflow/i);
  assert.equal(calls[1].expected_workflow_revision, 0);
});

test('missing, regressed, skipped or changed-branch acknowledgements block initialized saves', async () => {
  for (const response of [{ revision: 'r2' }, acknowledged('r2', 1), acknowledged('r2', 3), acknowledged('r2', 2, 'other')]) {
    let calls = 0;
    const coordinator = createScreenplayDraftCoordinator({ write: async () => { calls++; return response; }});
    coordinator.load('A', 'old', 'r1', workflow());
    await assert.rejects(coordinator.save('A', 'new'), /workflow|branch/i);
    await assert.rejects(coordinator.save('A', 'newer'));
    assert.equal(calls, 1);
    assert.equal(coordinator.snapshot('A').revision, 'r1');
    assert.equal(coordinator.snapshot('A').savedContent, 'old');
    assert.equal(coordinator.isDirty('A', 'new'), true);
  }
});

test('unchanged server acknowledgement must preserve revision and workflow epoch', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => acknowledged('r1', 1, 'main', { unchanged: true }) });
  coordinator.load('A', 'old\r\n', 'r1', workflow());
  await coordinator.save('A', 'old\n');
  assert.equal(coordinator.snapshot('A').workflowRevision, 1);
  assert.equal(coordinator.isDirty('A', 'old\n'), false);
  const invalid = createScreenplayDraftCoordinator({ write: async () => acknowledged('r2', 1, 'main', { unchanged: true }) });
  invalid.load('A', 'old', 'r1', workflow());
  await assert.rejects(invalid.save('A', 'new'), /unchanged|revision/i);
});

test('malformed workflow reads never become a writable baseline', () => {
  for (const metadata of [workflow(-1), workflow(true), workflow(1.5), workflow(Number.MAX_SAFE_INTEGER + 1),
    workflow(1, ''), workflow(1, 'main', { initialized: 'yes' }), { initialized: true },
    workflow(3, 'main', { initialized: false }), workflow(1, 'main', { pending_operation: {} })]) {
    const coordinator = createScreenplayDraftCoordinator({ write: async () => { throw Error('must not call'); } });
    assert.throws(() => coordinator.load('A', 'old', 'r1', metadata), /workflow/i);
    assert.equal(coordinator.snapshot('A'), null);
  }
});

test('structured mutations receive the same workflow guard as ordinary saves', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => {} });
  coordinator.load('A', 'one\ntwo', 'r1', workflow(4));
  await coordinator.mutate('A', 'one\ntwo', async payload => {
    assert.equal(payload.expected_workflow_revision, 4);
    return acknowledged('r2', 5, 'main', { content: 'two\none' });
  });
  assert.equal(coordinator.snapshot('A').savedContent, 'two\none');
});

test('metadata actions serialize with saves and keep manuscript revision and text', async () => {
  const calls = [];
  const coordinator = createScreenplayDraftCoordinator({ write: async payload => {
    calls.push(payload); return acknowledged('r2', 3);
  }});
  coordinator.load('A', 'old', 'r1', workflow());
  const metadata = coordinator.updateWorkflow('A', async payload => {
    assert.equal(payload.project_name, 'A');
    assert.equal(payload.expected_revision, 'r1');
    assert.equal(payload.expected_workflow_revision, 1);
    return acknowledged('r1', 2, 'main', { content: 'old' });
  });
  await Promise.all([metadata, coordinator.save('A', 'new', 'main')]);
  assert.equal(calls[0].expected_workflow_revision, 2);
  assert.equal(coordinator.snapshot('A').savedContent, 'new');
});

test('metadata actions refuse unexpected manuscript replacement', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => {} });
  coordinator.load('A', 'old', 'r1', workflow());
  await assert.rejects(coordinator.updateWorkflow('A', async () => acknowledged('r2', 2, 'main', { content: 'different' })), /manuscript|revision|content/i);
  assert.equal(coordinator.snapshot('A').revision, 'r1');
  assert.equal(coordinator.snapshot('A').blocked, true);
});

test('queued old-branch saves are refused after switch without poisoning the new branch', async () => {
  let writes = 0;
  const coordinator = createScreenplayDraftCoordinator({ write: async () => { writes++; return acknowledged('r3', 3, 'draft'); } });
  coordinator.load('A', 'main text', 'r1', workflow());
  const switched = coordinator.switchBranch('A', 'draft', async payload => {
    assert.equal(payload.branch_name, 'draft');
    assert.equal(payload.expected_workflow_revision, 1);
    return acknowledged('r2', 2, 'draft', { content: 'draft text' });
  });
  const stale = coordinator.save('A', 'late main edit', 'main');
  await switched;
  await assert.rejects(stale, /branch|context|reload/i);
  assert.equal(writes, 0);
  assert.equal(coordinator.snapshot('A').blocked, false);
  await coordinator.save('A', 'new draft edit', 'draft');
  assert.equal(writes, 1);
});

test('branch switching requires full content and the exact target identity', async () => {
  for (const response of [acknowledged('r2', 2, 'draft'), acknowledged('r2', 2, 'other', { content: 'wrong' })]) {
    const coordinator = createScreenplayDraftCoordinator({ write: async () => {} });
    coordinator.load('A', 'old', 'r1', workflow());
    await assert.rejects(coordinator.switchBranch('A', 'draft', async () => response), /content|branch/i);
    assert.equal(coordinator.snapshot('A').savedContent, 'old');
  }
});

test('same-branch switch acknowledgements and unchanged saves do not invent an epoch', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => {} });
  coordinator.load('A', 'old', 'r1', workflow());
  await coordinator.switchBranch('A', 'main', async () => acknowledged('r1', 1, 'main', { content: 'old', unchanged: true }));
  assert.equal(coordinator.snapshot('A').workflowRevision, 1);
});

test('load during an in-flight write cannot turn a late acknowledgement into another project baseline', async () => {
  const started = deferred(), finish = deferred();
  const coordinator = createScreenplayDraftCoordinator({ write: async () => { started.resolve(); return finish.promise; } });
  coordinator.load('A', 'old', 'r1', workflow());
  const saving = coordinator.save('A', 'unsaved');
  await started.promise;
  coordinator.load('A', 'reloaded', 'r9', workflow(9));
  finish.resolve(acknowledged('r2', 2));
  await assert.rejects(saving, /reload|context/i);
  assert.equal(coordinator.snapshot('A').revision, 'r9');
  assert.equal(coordinator.snapshot('A').savedContent, 'reloaded');
  assert.equal(coordinator.snapshot('A').blocked, false);
});

test('queued work captured before explicit reload never writes against the new baseline', async () => {
  let writes = 0;
  const coordinator = createScreenplayDraftCoordinator({ write: async () => { writes++; return acknowledged('r10', 10); } });
  coordinator.load('A', 'old', 'r1', workflow());
  const saving = coordinator.save('A', 'unsaved');
  coordinator.load('A', 'reloaded', 'r9', workflow(9));
  await assert.rejects(saving, /reload|context/i);
  assert.equal(writes, 0);
});

test('pending operation reads stop ordinary writes and metadata actions', async () => {
  let writes = 0;
  const coordinator = createScreenplayDraftCoordinator({ write: async () => { writes++; } });
  const operation = { id: 'pending', kind: 'WRITE', source_branch: 'main', target_branch: 'main', before_revision: 'r1', after_revision: 'r2' };
  coordinator.load('A', 'old', 'r1', workflow(1, 'main', { pending_operation: operation }));
  await assert.rejects(coordinator.save('A', 'new'), /recover|interrupted/i);
  assert.equal(writes, 0);
  assert.equal(coordinator.snapshot('A').pendingOperation.id, 'pending');
  assert.equal(coordinator.snapshot('A').blocked, true);
});

test('wrong project acknowledgements are never accepted', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => acknowledged('r2', 2, 'main', { project: 'Other' }) });
  coordinator.load('A', 'old', 'r1', workflow());
  await assert.rejects(coordinator.save('A', 'new'), /project/i);
  assert.equal(coordinator.snapshot('A').revision, 'r1');
});

test('a malformed reload blocks the previous baseline and previously queued saves', async () => {
  let writes = 0;
  const coordinator = createScreenplayDraftCoordinator({ write: async () => { writes++; return acknowledged('r2', 2); } });
  coordinator.load('A', 'old', 'r1', workflow());
  const queued = coordinator.save('A', 'local draft');
  assert.throws(() => coordinator.load('A', 'remote', 'r9', workflow(-1)), /workflow/i);
  await assert.rejects(queued);
  await assert.rejects(coordinator.save('A', 'newer local draft'), /workflow/i);
  assert.equal(coordinator.snapshot('A').savedContent, 'old');
  assert.equal(coordinator.snapshot('A').blocked, true);
  assert.equal(writes, 0);
});

test('unchanged acknowledgement cannot silently mark a genuinely different draft saved', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => acknowledged('r1', 1, 'main', { unchanged: true }) });
  coordinator.load('A', 'original\r\n', 'r1', workflow());
  await assert.rejects(coordinator.save('A', 'different\n'), /unchanged|content/i);
  assert.equal(coordinator.snapshot('A').savedContent, 'original\r\n');
  assert.equal(coordinator.isDirty('A', 'different\n'), true);
});

test('metadata-only changes retain editor newline representation after byte-preserving no-op save', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => acknowledged('r1', 1, 'main', { unchanged: true }) });
  coordinator.load('A', 'original\r\n', 'r1', workflow());
  await coordinator.save('A', 'original\n');
  await coordinator.updateWorkflow('A', async () => acknowledged('r1', 2, 'main', { content: 'original\r\n' }));
  assert.equal(coordinator.snapshot('A').savedContent, 'original\n');
  assert.equal(coordinator.snapshot('A').workflowRevision, 2);
});

test('legacy baseline cannot silently adopt an initialized branch during save', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => acknowledged('r2', 7, 'other') });
  coordinator.load('A', 'old', 'r1');
  await assert.rejects(coordinator.save('A', 'new'), /workflow|reload/i);
  assert.equal(coordinator.snapshot('A').savedContent, 'old');
});

test('an unchanged acknowledgement cannot claim a different active branch', async () => {
  const coordinator = createScreenplayDraftCoordinator({ write: async () => {} });
  coordinator.load('A', 'original', 'r1', workflow());
  await assert.rejects(coordinator.switchBranch('A', 'draft', async () =>
    acknowledged('r1', 1, 'draft', { content: 'different branch', unchanged: true })), /unchanged|branch/i);
  assert.equal(coordinator.snapshot('A').activeBranch, 'main');
  assert.equal(coordinator.snapshot('A').savedContent, 'original');
});
