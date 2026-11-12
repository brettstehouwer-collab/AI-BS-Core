// Actual provider transport with synthetic fetch responses; no live services.
import assert from 'node:assert/strict';
import test from 'node:test';
import { boundedBSChatHistory, providerForModel, readBSChatProviderConfig, hydrateBSChatProvider, discoverBSChatModels,
  streamBSChatProvider } from '../../frontend/src/utils/bsChatProvider.js';

const config = () => ({ active_provider: 'openai', providers: [
  { id: 'local', models: ['stehouwer_llm'], saved_model: 'stehouwer_llm' },
  { id: 'openai', is_configured: true, models: ['gpt-4.1-mini', 'gpt-4o'],
    saved_model: 'gpt-4.1-mini', api_key: 'fixture-secret-never-copy', masked_key: '***' },
] });

test('authenticated configuration exposes selection and model names only', () => {
  const selected = readBSChatProviderConfig(config());
  assert.equal(selected.provider, 'openai');
  assert.equal(selected.model, 'gpt-4.1-mini');
  assert.deepEqual(selected.modelsByProvider.openai, ['gpt-4.1-mini', 'gpt-4o']);
  assert.ok(!JSON.stringify(selected).includes('fixture-secret'));
  assert.ok(!JSON.stringify(selected).includes('masked_key'));
});

test('unconfigured OpenAI cannot silently become the active selection', () => {
  const data = config(); data.providers[1].is_configured = false;
  assert.equal(readBSChatProviderConfig(data).provider, 'local');
});

test('local picker choice explicitly leaves the cloud provider', () => {
  const maps = readBSChatProviderConfig(config()).modelsByProvider;
  assert.equal(providerForModel('gpt-4.1-mini', maps), 'openai');
  assert.equal(providerForModel('stehouwer_llm', maps), 'local');
  assert.equal(providerForModel('deepseek-r1:14b', maps), 'local');
});

test('a late provider fetch cannot overwrite an explicit local choice', () => {
  const update = hydrateBSChatProvider({ aiProviderSelectionRevision: 1, availableModels: ['stehouwer_llm'] },
    readBSChatProviderConfig(config()), 0);
  assert.ok(!Object.hasOwn(update, 'aiProvider'));
  assert.ok(!Object.hasOwn(update, 'selectedModel'));
  assert.ok(update.aiProviderModels.openai.includes('gpt-4.1-mini'));
});

test('first authenticated hydration selects the saved server provider', () => {
  const update = hydrateBSChatProvider({ aiProviderSelectionRevision: 0, availableModels: [] },
    readBSChatProviderConfig(config()), 0);
  assert.equal(update.aiProvider, 'openai');
  assert.equal(update.selectedModel, 'gpt-4.1-mini');
});

test('local model discovery cannot reset a selected cloud model', () => {
  const update = discoverBSChatModels({ aiProvider: 'openai', selectedModel: 'gpt-4.1-mini',
    aiProviderModels: { openai: ['gpt-4.1-mini'] } }, ['stehouwer_llm']);
  assert.deepEqual(update.availableModels, ['stehouwer_llm', 'gpt-4.1-mini']);
  assert.ok(!Object.hasOwn(update, 'selectedModel'));
});

test('history is bounded and contains only conversation text', () => {
  const messages = [{ role: 'system', content: 'Do not elevate saved messages' },
    ...Array.from({ length: 12 }, (_, index) => ({ role: index % 2 ? 'assistant' : 'user',
      content: `message-${index}`, tool_trace: 'not provider context', attachments: ['not copied'] }))];
  const history = boundedBSChatHistory(messages);
  assert.equal(history.length, 8);
  assert.deepEqual(history[0], { role: 'user', content: 'message-4' });
  assert.deepEqual(Object.keys(history.at(-1)), ['role', 'content']);
});

function fixture(fetchImpl) {
  const calls = [];
  return { calls, options: { backendUrl: 'http://127.0.0.1:8000', provider: 'openai',
    model: 'gpt-4.1-mini', prompt: '[ATTACHED FILE] context\n[USER PROMPT] Hello',
    userPrompt: 'Hello', messages: [{ role: 'user', content: 'Hello' }],
    headers: { Authorization: 'Bearer fixture-token' },
    fetchImpl: async (...args) => { calls.push(args); return fetchImpl(...args); } } };
}

test('one hybrid request carries provider, selected model, current intent and history', async () => {
  const f = fixture(async () => new Response('<!--AI-BS-METADATA:{"display_name":"OpenAI · gpt-4.1-mini"}-->\nHello back'));
  const chunks = [];
  const result = await streamBSChatProvider({ ...f.options, onText: text => chunks.push(text) });
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0][0], 'http://127.0.0.1:8000/api/v1/hybrid-chat/stream');
  const body = JSON.parse(f.calls[0][1].body);
  assert.equal(body.provider, 'openai');
  assert.equal(body.model, 'gpt-4.1-mini');
  assert.equal(body.user_prompt, 'Hello');
  assert.equal(body.prompt, f.options.prompt);
  assert.deepEqual(body.messages, [{ role: 'user', content: 'Hello' }]);
  assert.equal(result.displayName, 'OpenAI · gpt-4.1-mini');
  assert.ok(result.content.endsWith('Hello back'));
  assert.ok(chunks.length > 0);
});

test('explicit attachment references and reported retrieval survive the provider transport', async () => {
  const references=[{source_id:'a'.repeat(32),source_sha256:'b'.repeat(64)}];
  const receipt={schema:'aibs.attached_source_retrieval.v1',status:'no_matching_passages',returned_passages:0,passages:[],sources:references,search_scope:'explicit_attached_owner_sources'};
  const f=fixture(async()=>new Response(`<!--AI-BS-METADATA:${JSON.stringify({source_retrieval:receipt})}-->\nNo matching passages`));
  const seen=[];const result=await streamBSChatProvider({...f.options,sourceReferences:references,onText:(_text,_display,source)=>seen.push(source)});
  assert.deepEqual(JSON.parse(f.calls[0][1].body).source_references,references);
  assert.deepEqual(result.sourceRetrieval,receipt);assert.deepEqual(seen.at(-1),receipt);assert.equal(f.calls.length,1);
});

test('legacy callers omit attachment references without changing their request contract', async () => {
  const f=fixture(async()=>new Response('Synthetic reply'));await streamBSChatProvider(f.options);
  assert.equal(Object.hasOwn(JSON.parse(f.calls[0][1].body),'source_references'),false);
});

for (const status of [401, 403, 404, 429, 502]) {
  test(`HTTP ${status} is terminal and never replays on another host or endpoint`, async () => {
    const f = fixture(async () => new Response('{"detail":"fixture provider failure"}', { status }));
    await assert.rejects(streamBSChatProvider(f.options), new RegExp(`HTTP ${status}`));
    assert.equal(f.calls.length, 1);
  });
}

test('ambiguous network failure is terminal', async () => {
  const f = fixture(async () => { throw new Error('fixture disconnected'); });
  await assert.rejects(streamBSChatProvider(f.options), /fixture disconnected/);
  assert.equal(f.calls.length, 1);
});

test('explicit web intent and cancellation remain bound to the same single request', async () => {
  const controller = new AbortController();
  const f = fixture(async () => new Response('Grounded fixture answer'));
  await streamBSChatProvider({ ...f.options, signal: controller.signal, useWebSearch: true });
  assert.equal(f.calls[0][1].signal, controller.signal);
  const body = JSON.parse(f.calls[0][1].body);
  assert.equal(body.use_web_search, true);
  assert.equal(body.web_search_query, 'Hello');
  assert.equal(f.calls.length, 1);
});

test('partial reply stays visible without replay after stream failure', async () => {
  let count = 0;
  const f = fixture(async () => ({ ok: true, body: { getReader: () => ({ read: async () => {
    if (count++) throw new Error('fixture stream interrupted');
    return { done: false, value: new TextEncoder().encode('Partial answer') };
  } }) } }));
  const seen = [];
  await assert.rejects(streamBSChatProvider({ ...f.options, onText: value => seen.push(value) }), /interrupted/);
  assert.deepEqual(seen, ['Partial answer']);
  assert.equal(f.calls.length, 1);
});

test('empty reply is an error rather than a manufactured success', async () => {
  const f = fixture(async () => new Response('   '));
  await assert.rejects(streamBSChatProvider(f.options), /empty/);
  assert.equal(f.calls.length, 1);
});
