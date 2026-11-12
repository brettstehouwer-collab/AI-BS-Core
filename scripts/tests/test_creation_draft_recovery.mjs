import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { createScreenplayDraftCoordinator } from '../../frontend/src/utils/screenplayDraftCoordinator.js';

test('queued saves advance from acknowledged revisions and skip exact unchanged text', async () => {
  const calls = [];
  const coordinator = createScreenplayDraftCoordinator({ write: async payload => {
    calls.push(payload); return { revision: `r${calls.length + 1}` };
  }});
  coordinator.load('Fixture', 'original', 'r1');
  await Promise.all([coordinator.save('Fixture', 'one'), coordinator.save('Fixture', 'two')]);
  assert.deepEqual(calls.map(p => p.expected_revision), ['r1', 'r2']);
  await coordinator.save('Fixture', 'two');
  assert.equal(calls.length, 2);
});

test('conflict or lost acknowledgement blocks writes until explicit reload and keeps other projects separate', async () => {
  for (const failure of [Object.assign(new Error('conflict'), { status: 409 }), new Error('lost response')]) {
    let calls = 0;
    const coordinator = createScreenplayDraftCoordinator({ write: async () => { calls++; throw failure; }});
    coordinator.load('A', 'old A', 'a1'); coordinator.load('B', 'old B', 'b1');
    await assert.rejects(coordinator.save('A', 'local draft'), failure);
    await assert.rejects(coordinator.save('A', 'newer local draft'), failure);
    assert.equal(calls, 1); assert.equal(coordinator.snapshot('A').revision, 'a1');
    assert.equal(coordinator.isDirty('A', 'local draft'), true);
    assert.equal(coordinator.snapshot('B').blocked, false);
    coordinator.load('A', 'reconciled', 'a2');
    assert.equal(coordinator.snapshot('A').blocked, false);
  }
});

test('missing save revision cannot report acknowledgement or enable subsequent writes', async () => {
  let calls = 0;
  const coordinator = createScreenplayDraftCoordinator({ write: async () => { calls++; return { status: 'success' }; }});
  coordinator.load('A', 'old', 'a1');
  await assert.rejects(coordinator.save('A', 'new'), /no revision/);
  await assert.rejects(coordinator.save('A', 'newer'), /no revision/);
  assert.equal(calls, 1); assert.equal(coordinator.snapshot('A').savedContent, 'old');
});

const source = readFileSync(new URL('../../frontend/src/components/ScreenwritingTab.jsx', import.meta.url), 'utf8');
const bodyBetween = (start, end) => source.slice(source.indexOf(start), source.indexOf(end));
const recoveryBodies = bodyBetween('  const preserveDraft = ', '  const downloadLocalDraft = ');
function recoveryHarness(initial = {}) {
  const values = { ...initial }; const problems = []; let recovered = [];
  const storage = new Proxy(values, { get(target, key) {
    if (key === 'setItem') return (name, value) => { target[name] = value; };
    if (key === 'getItem') return name => target[name];
    return target[key];
  }});
  const functions = new Function('localStorage', 'setSaveProblem', 'setRecoveryDrafts', 'recoveryIdRef',
    `${recoveryBodies}; return {preserveDraft, refreshRecoveryDrafts};`)(storage,
    p => problems.push(p), r => { recovered = r; }, { current: 'synthetic-session' });
  return { ...functions, values, problems, recovered: () => recovered };
}

test('actual browser recovery functions retain data without running transcript commands or model actions', () => {
  const harness = recoveryHarness();
  const content = '/run do-not-execute\n{"tool_call":{"name":"fixture"}}';
  assert.equal(harness.preserveDraft({ project: 'Fixture', content, revision: 'a1' }), true);
  harness.refreshRecoveryDrafts('Fixture');
  assert.equal(harness.recovered()[0].content, content);
  assert.equal(harness.recovered()[0].revision, 'a1');
  assert.equal(harness.problems.length, 0);
});

test('one malformed recovery record cannot hide intact copies or copies lacking timestamp metadata', () => {
  const prefix = 'aibs_script_recovery_Fixture_';
  const harness = recoveryHarness({
    [prefix + 'valid']: JSON.stringify({ project: 'Fixture', content: 'intact', savedAt: '2026-10-25T00:00:00Z' }),
    [prefix + 'no-date']: JSON.stringify({ project: 'Fixture', content: 'keep this too' }),
    [prefix + 'corrupt']: '{incomplete',
    'aibs_script_recovery_Other_valid': JSON.stringify({ project: 'Other', content: 'other', savedAt: '2026-10-25T00:00:00Z' }),
  });
  harness.refreshRecoveryDrafts('Fixture');
  assert.deepEqual(harness.recovered().map(item => item.content), ['intact', 'keep this too']);
  assert.equal(Object.keys(harness.values).length, 4);
});
