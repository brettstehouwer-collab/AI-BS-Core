import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createScreenplayWorkflowClient } from '../../frontend/src/utils/screenplayWorkflowClient.js';

const project = 'Synthetic Fixture';
const original = 'Title: Fixture\r\n\r\nINT. LAB - DAY\r\nAn original.\r\n';
async function setup(t) {
  const child = spawn(process.env.AIBS_TEST_PYTHON || 'python', ['-u', fileURLToPath(new URL('./screenplay_workflow_route_bridge.py', import.meta.url))],
    { stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
  const waiting = [];
  let errors = '';
  let ended = false;
  child.stderr.on('data', data => { errors = (errors + data).slice(-4096); });
  createInterface({ input: child.stdout }).on('line', line => {
    const entry = waiting.shift();
    if (entry) {
      try { entry.resolve(JSON.parse(line)); } catch (error) { entry.reject(error); }
    }
  });
  const closed = new Promise(resolve => child.once('close', code => {
    ended = true;
    for (const entry of waiting.splice(0)) entry.reject(Error(`Fixture closed: ${code}; ${errors}`));
    resolve(code);
  }));
  child.on('error', error => { for (const entry of waiting.splice(0)) entry.reject(error); });
  t.after(async () => {
    child.stdin.end();
    const timer = setTimeout(() => child.kill(), 5000);
    timer.unref();
    const code = await closed;
    clearTimeout(timer);
    assert.equal(code, 0, errors);
  });
  const exchange = message => new Promise((resolve, reject) => {
    if (ended) return reject(Error('Fixture already closed'));
    waiting.push({ resolve, reject });
    child.stdin.write(`${JSON.stringify(message)}\n`);
  });
  const calls = [];
  const requestFetch = async (url, options = {}) => {
    const message = { url, ...options };
    calls.push(message);
    const response = await exchange(message);
    return { ok: response.status >= 200 && response.status < 300, status: response.status, json: async () => response.body };
  };
  const client = createScreenplayWorkflowClient({ baseUrl: 'https://fixture.invalid', fetch: requestFetch });
  const read = await client.read(project);
  client.acceptSnapshot(read);
  return { client, calls, exchange, requestFetch };
}

test('read is explicit, URL-encoded and does not silently replace an accepted baseline', async t => {
  const { client, calls, exchange } = await setup(t);
  assert.match(calls[0].url, /project_name=Synthetic%20Fixture$/);
  assert.equal(client.snapshot(project).savedContent, original);
  await exchange({ fixture: 'external_write', content: 'external\r\n' });
  const fresh = await client.read(project);
  assert.equal(fresh.content, 'external\r\n');
  assert.equal(client.snapshot(project).savedContent, original);
});

test('actual branch/sprint/write/switch contracts preserve independent manuscript versions', async t => {
  const { client, exchange, calls } = await setup(t);
  const created = await client.createBranch(project, 'Draft B');
  assert.deepEqual(created.branches, ['main', 'Draft B']);
  assert.equal(created.active_branch, 'main');
  const sprint = await client.startSprint(project, 'Morning', 10);
  assert.equal(sprint.active_sprint.name, 'Morning');
  await client.save(project, 'main version\r\n');
  const ended = await client.endSprint(project, sprint.active_sprint.id);
  assert.equal(ended.active_sprint, null);
  assert.equal(ended.sprints[0].status, 'ENDED');
  const switched = await client.switchBranch(project, 'Draft B');
  assert.equal(switched.content, original);
  await client.save(project, 'alternate version\r\n');
  const main = await client.switchBranch(project, 'main');
  assert.equal(main.content, 'main version\r\n');
  assert.equal(Buffer.from((await exchange({ fixture: 'bytes' })).body.hex, 'hex').toString(), main.content);
  assert.deepEqual(calls.filter(c => c.method === 'POST').map(c => JSON.parse(c.body).expected_workflow_revision), [0, 1, 2, 3, 4, 5, 6]);
});

test('metadata-only workflows and newline-only saves never rewrite original bytes', async t => {
  const { client, exchange } = await setup(t);
  const before = (await exchange({ fixture: 'bytes' })).body.hex;
  await client.createBranch(project, 'Alternate');
  const sprint = await client.startSprint(project, 'Sprint', 1);
  await client.endSprint(project, sprint.active_sprint.id);
  const saved = await client.save(project, original.replaceAll('\r\n', '\n'));
  assert.equal(saved.unchanged, true);
  assert.equal((await exchange({ fixture: 'bytes' })).body.hex, before);
  assert.equal(client.snapshot(project).workflowRevision, 3);
});

test('stale manuscript rejection retains local baseline and prevents repeated mutation', async t => {
  const { client, exchange, calls } = await setup(t);
  await client.createBranch(project, 'Alternate');
  await exchange({ fixture: 'external_write', content: 'external edit\r\n' });
  await assert.rejects(client.save(project, 'my draft'), error => error.status === 409);
  const count = calls.length;
  await assert.rejects(client.startSprint(project, 'Later', 1));
  assert.equal(calls.length, count);
  assert.equal(client.snapshot(project).savedContent, original);
});

test('lost commit acknowledgement blocks retries without silently loading the server', async t => {
  const { requestFetch } = await setup(t);
  let fail = true;
  let requests = 0;
  const client = createScreenplayWorkflowClient({ baseUrl: 'https://fixture.invalid', fetch: async (...args) => {
    requests++;
    const result = await requestFetch(...args);
    if (args[1]?.method === 'POST' && fail) { fail = false; throw Error('Synthetic lost acknowledgement'); }
    return result;
  }});
  client.acceptSnapshot(await client.read(project));
  await assert.rejects(client.createBranch(project, 'Committed'), /lost acknowledgement/);
  const count = requests;
  await assert.rejects(client.createBranch(project, 'Retry'));
  assert.equal(requests, count);
  const fresh = await client.read(project);
  assert.deepEqual(fresh.branches, ['main', 'Committed']);
  assert.equal(client.snapshot(project).blocked, true);
});

test('explicit interrupted-write recovery does not discard or automatically rebase a local draft', async t => {
  const { client, exchange } = await setup(t);
  await client.createBranch(project, 'Alternate');
  await exchange({ fixture: 'interrupt_next_write' });
  await assert.rejects(client.save(project, 'retained interrupted draft\r\n'), error => error.status === 500);
  const pending = await client.read(project);
  client.acceptSnapshot(pending);
  assert.equal(client.snapshot(project).blocked, true);
  const restored = await client.recoverPending(project, pending.pending_operation.id, 'complete');
  assert.equal(restored.content, 'retained interrupted draft\r\n');
  assert.equal(client.snapshot(project).blocked, true);
  assert.equal(client.snapshot(project).savedContent, original);
  client.acceptSnapshot(restored);
  assert.equal(client.snapshot(project).blocked, false);
});

test('unrelated and implicit recovery attempts do not reach the route', async t => {
  const { client, calls } = await setup(t);
  const count = calls.length;
  await assert.rejects(client.recoverPending(project, 'invented', 'complete'));
  await assert.rejects(client.recoverPending(project, 'invented', 'automatic'));
  assert.equal(calls.length, count);
});

test('real payload validation rejects noninteger sprint target without changing manuscript', async t => {
  const { client, exchange } = await setup(t);
  const before = (await exchange({ fixture: 'bytes' })).body.hex;
  await assert.rejects(client.startSprint(project, 'Bad sprint', '10'), error => error.status === 422);
  assert.equal((await exchange({ fixture: 'bytes' })).body.hex, before);
  assert.equal(client.snapshot(project).blocked, true);
});

test('a workflow acknowledgement from another project cannot become a saved baseline', async t => {
  const { requestFetch } = await setup(t);
  const client = createScreenplayWorkflowClient({ baseUrl: 'https://fixture.invalid', fetch: async (url, options) => {
    const response = await requestFetch(url, options);
    const body = await response.json();
    return { ...response, json: async () => options?.method === 'POST' ? { ...body, project: 'Other' } : body };
  }});
  client.acceptSnapshot(await client.read(project));
  await assert.rejects(client.createBranch(project, 'Alternate'), /project/i);
  assert.equal(client.snapshot(project).blocked, true);
  assert.equal(client.snapshot(project).savedContent, original);
});

test('an uncertain recovery acknowledgement cannot be replayed until an explicit fresh snapshot', async t => {
  const { client: writer, exchange, requestFetch } = await setup(t);
  await writer.createBranch(project, 'Alternate');
  await exchange({ fixture: 'interrupt_next_write' });
  await assert.rejects(writer.save(project, 'interrupted draft'));
  let recoveries = 0;
  const client = createScreenplayWorkflowClient({ baseUrl: 'https://fixture.invalid', fetch: async (url, options) => {
    const response = await requestFetch(url, options);
    if (url.endsWith('/workflow/recover')) {
      recoveries++;
      throw Error('Synthetic lost recovery acknowledgement');
    }
    return response;
  }});
  const loaded = await client.read(project);
  client.acceptSnapshot(loaded);
  const id = loaded.pending_operation.id;
  await assert.rejects(client.recoverPending(project, id, 'complete'), /lost recovery/);
  await assert.rejects(client.recoverPending(project, id, 'complete'));
  assert.equal(recoveries, 1);
  assert.equal(client.snapshot(project).blocked, true);
  const fresh = await client.read(project);
  assert.equal(fresh.pending_operation, null);
  assert.equal(fresh.content, 'interrupted draft');
  client.acceptSnapshot(fresh);
  assert.equal(client.snapshot(project).blocked, false);
});

test('a second client workflow change is rejected by its stale epoch despite unchanged manuscript', async t => {
  const { client, requestFetch, exchange } = await setup(t);
  const second = createScreenplayWorkflowClient({ baseUrl: 'https://fixture.invalid', fetch: requestFetch });
  second.acceptSnapshot(await second.read(project));
  await client.createBranch(project, 'First');
  await assert.rejects(second.createBranch(project, 'Stale'), error => error.status === 409);
  assert.equal(second.snapshot(project).blocked, true);
  assert.deepEqual((await client.read(project)).branches, ['main', 'First']);
  assert.equal(Buffer.from((await exchange({ fixture: 'bytes' })).body.hex, 'hex').toString(), original);
});

test('documented activation gate: the actual reorder route lacks the initialized workflow guard', async t => {
  const { client, requestFetch, exchange } = await setup(t);
  await client.createBranch(project, 'Alternate');
  const baseline = client.snapshot(project);
  const before = (await exchange({ fixture: 'bytes' })).body.hex;
  const response = await requestFetch('https://fixture.invalid/api/screenwriting/beats/reorder', {
    method: 'POST', body: JSON.stringify({ project_name: project, content: original,
      source_index: 0, target_index: 0, expected_revision: baseline.revision,
      expected_workflow_revision: baseline.workflowRevision }),
  });
  assert.equal(response.status, 428);
  assert.match((await response.json()).detail, /workflow/i);
  assert.equal((await exchange({ fixture: 'bytes' })).body.hex, before);
  assert.equal((await client.read(project)).workflow_revision, baseline.workflowRevision);
});
