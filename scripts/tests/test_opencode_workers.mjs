import assert from 'node:assert/strict';
import test from 'node:test';
import { parseOpenCodeWorkerCommand, requestOpenCodeWorker } from '../../frontend/src/utils/opencodeWorkers.js';

test('worker command parses a multiline task without changing its content', () => {
  assert.deepEqual(parseOpenCodeWorkerCommand('/opencode opencode/beam-free Review:\nconst x = 1;'),
    { action: 'work', model: 'beam-free', prompt: 'Review:\nconst x = 1;' });
  assert.deepEqual(parseOpenCodeWorkerCommand('/opencode models'), { action: 'models' });
  assert.throws(() => parseOpenCodeWorkerCommand('/opencode --model bad'), /worker ID/);
  assert.throws(() => parseOpenCodeWorkerCommand('/opencode beam-free '), /task/);
  assert.throws(() => parseOpenCodeWorkerCommand('/opencode beam-free ' + '💻'.repeat(8193)), /32 KiB/);
});

test('one request sends only the explicit task, with cancellation and authentication', async () => {
  const calls = [];
  const signal = new AbortController().signal;
  const headers = { Authorization: 'test-only-token', 'Content-Type': 'application/json' };
  const result = await requestOpenCodeWorker({ command: '/opencode beam-free Review this loop', backendUrl: 'http://local/',
    headers, signal, history: ['private history must not travel'], attachments: ['private source'],
    fetchImpl: async (...args) => { calls.push(args); return Response.json({ status: 'completed', model: 'opencode/beam-free', content: 'Proposal', receipt: { complete: true } }); } });
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'http://local/api/ai/opencode/work');
  assert.deepEqual(JSON.parse(calls[0][1].body), { model: 'beam-free', prompt: 'Review this loop' });
  assert.equal(calls[0][1].signal, signal);
  assert.equal(calls[0][1].headers, headers);
  assert.match(result.displayName, /beam-free/);
  assert.match(result.content, /proposal/);
});

test('plan mode blocks a worker before any request but permits catalogue reads', async () => {
  let requests = 0;
  const fetchImpl = async () => { requests++; return Response.json({ models: [{ id: 'beam-free', label: 'Beam Free', privacy: '30-day safety retention' }] }); };
  await assert.rejects(requestOpenCodeWorker({ command: '/opencode beam-free Review', backendUrl: 'http://local', planOnly: true, fetchImpl }), /Plan mode/);
  assert.equal(requests, 0);
  const result = await requestOpenCodeWorker({ command: '/opencode models', backendUrl: 'http://local', planOnly: true, fetchImpl });
  assert.match(result.content, /30-day safety retention/);
  assert.match(result.content, /remain selected/);
  assert.equal(requests, 1);
});

test('quota errors, wrong models and partial output are never replayed', async () => {
  for (const response of [Response.json({ detail: 'Capacity exhausted' }, { status: 429 }),
    Response.json({ status: 'completed', model: 'other-model', content: 'Wrong model' }),
    Response.json({ status: 'incomplete', model: 'beam-free', content: 'Partial' })]) {
    let requests = 0;
    await assert.rejects(requestOpenCodeWorker({ command: '/opencode beam-free Review', backendUrl: 'http://local',
      fetchImpl: async () => { requests++; return response; } }));
    assert.equal(requests, 1);
  }
});

test('abort propagates without a second worker request', async () => {
  let calls = 0;
  const abort = new DOMException('Cancelled', 'AbortError');
  await assert.rejects(requestOpenCodeWorker({ command: '/opencode beam-free Review', backendUrl: 'http://local',
    fetchImpl: async () => { calls++; throw abort; } }), error => error === abort);
  assert.equal(calls, 1);
});

test('public input declaration is explicit and model limits are shown', async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push([url, options]);
    return options.method === 'POST'
      ? Response.json({ status: 'completed', model: 'nemotron-3.5-lightning-free', content: 'Public-code proposal' })
      : Response.json({ models: [{ id: 'nemotron-3.5-lightning-free', name: 'NVIDIA trial', privacy: 'Trial logging',
        limits: 'No personal or confidential input.', public_nonconfidential_input_only: true }] });
  };
  const list = await requestOpenCodeWorker({ command: '/opencode models', backendUrl: 'http://local', fetchImpl });
  assert.match(list.content, /No personal or confidential input/);
  assert.match(list.content, /Requires --public/);
  await requestOpenCodeWorker({ command: '/opencode nemotron-3.5-lightning-free --public Review public code', backendUrl: 'http://local', fetchImpl });
  assert.deepEqual(JSON.parse(calls[1][1].body), { model: 'nemotron-3.5-lightning-free', prompt: 'Review public code', public_input_only: true });
  assert.throws(() => parseOpenCodeWorkerCommand('/opencode beam-free --public'), /task/);
});
