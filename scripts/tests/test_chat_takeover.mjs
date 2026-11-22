// Exercise the recovered source branches with synthetic state; no app or service startup.
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { runInNewContext } from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { parse } = require('@babel/parser');
const traverse = require('@babel/traverse').default;
const { transformSync } = require('esbuild');
const source = await readFile(path.join(root, 'frontend/src/components/ChatTab.jsx'), 'utf8');
const tree = parse(source, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
const nodes = [];
traverse(tree, { enter(p) { nodes.push(p); } });
const fragment = node => source.slice(node.start, node.end);

test('rendered provider menu identifiers resolve to component bindings', () => {
  const menuReference = nodes.find(p => p.isIdentifier({ name: 'providerModels' }) && p.isReferencedIdentifier());
  assert.ok(menuReference, 'The provider model menu must remain present');
  assert.ok(menuReference.scope.getBinding('providerModels'), 'Runtime model-menu lookup must have a binding');
  const binding = menuReference.scope.getBinding('providerModels');
  assert.match(fragment(binding.path.node), /state\.aiProviderModels/);
  const transportReference = nodes.find(p => p.isIdentifier({ name: 'streamBSChatProvider' }) && p.isReferencedIdentifier());
  assert.ok(transportReference?.scope.getBinding('streamBSChatProvider'), 'Selected provider transport must be imported');
});

function providerBranch() {
  const found = nodes.find(p => p.isIfStatement() && fragment(p.node.test).includes("selectedProvider === 'openai'") &&
    fragment(p.node.consequent).includes('streamBSChatProvider'));
  assert.ok(found, 'Ordinary OpenAI turns require their dedicated no-replay branch');
  return found.node;
}

test('selected OpenAI branch preserves request context and returns before generic fallback', async () => {
  const branch = providerBranch();
  let messages = [{ role: 'user', content: 'hello' }];
  let calls = 0;
  const signal = new AbortController().signal;
  const context = { selectedProvider: 'openai', isPlanMode: false, targetModel: 'fixture-model',
    BACKEND_URL: 'http://fixture.invalid', formattedPrompt: 'attachment context + hello', rawText: 'hello',
    activeContexts: { web: false }, updatedHistory: messages, reqHeaders: { Authorization: 'fixture' },
    controller: { signal }, autoSpeak: false,
    setChatMessages: update => { messages = update(messages); },
    streamBSChatProvider: async options => {
      calls++;
      assert.equal(options.provider, 'openai');
      assert.equal(options.model, 'fixture-model');
      assert.equal(options.userPrompt, 'hello');
      assert.equal(options.prompt, 'attachment context + hello');
      assert.equal(options.signal, signal);
      options.onText('partial reply', 'OpenAI · fixture-model');
      return { content: 'partial reply' };
    },
  };
  const result = await runInNewContext(`(async () => { ${fragment(branch)}; return 'generic fallback reached'; })()`, context);
  assert.equal(result, undefined);
  assert.equal(calls, 1);
  assert.equal(messages.at(-1).content, 'partial reply');
});

test('uncertain OpenAI request propagates without a second provider request', async () => {
  let calls = 0;
  const context = { selectedProvider: 'openai', isPlanMode: false, targetModel: 'fixture-model', BACKEND_URL: 'fixture',
    formattedPrompt: 'hello', rawText: 'hello', activeContexts: {}, updatedHistory: [], reqHeaders: {},
    controller: {}, autoSpeak: false, setChatMessages() {}, streamBSChatProvider: async () => { calls++; throw new Error('uncertain outcome'); } };
  await assert.rejects(runInNewContext(`(async () => { ${fragment(providerBranch())}; throw new Error('replayed'); })()`, context), /uncertain outcome/);
  assert.equal(calls, 1);
});

function runRecovery({ draft = '', attachments = [], reply = '' } = {}) {
  const caught = nodes.find(p => p.isCatchClause() && fragment(p.node.body).includes("console.error('Chat error:'"));
  assert.ok(caught);
  const originalAttachments = [{ name: 'retained.txt' }];
  let currentAttachments = attachments;
  let messages = [{ role: 'assistant', content: reply }];
  const context = { selectedProvider: 'openai', rawText: 'original draft', attachments: originalAttachments,
    useAppStore: { getState: () => ({ footerInput: draft }) },
    setFooterInput: value => { draft = value; },
    setAttachments: update => { currentAttachments = update(currentAttachments); },
    setChatMessages: update => { messages = update(messages); },
    setErrorPopup() {}, errorMessage: err => err.message, console: { error() {} } };
  runInNewContext(`try { throw new Error('fixture failure'); } ${fragment(caught.node)}`, context);
  return { draft, attachments: currentAttachments, messages };
}

test('provider failure restores cleared input and attachments and removes only empty reply', () => {
  const result = runRecovery();
  assert.equal(result.draft, 'original draft');
  assert.equal(result.attachments[0].name, 'retained.txt');
  assert.equal(result.messages.length, 1);
  assert.match(result.messages[0].content, /fixture failure/);
});

test('provider failure preserves a newer draft, attachments and partial reply', () => {
  const result = runRecovery({ draft: 'new draft', attachments: [{ name: 'new.txt' }], reply: 'received partial response' });
  assert.equal(result.draft, 'new draft');
  assert.equal(result.attachments[0].name, 'new.txt');
  assert.equal(result.messages[0].content, 'received partial response');
});

function codeRenderer() {
  const method = nodes.find(p => p.isObjectMethod() && p.node.key.name === 'code' && fragment(p.node).includes('CodeBlock'));
  assert.ok(method);
  const compiled = transformSync(`globalThis.render = ({${fragment(method.node)}}).code`, { loader: 'jsx', jsxFactory: 'h', target: 'es2022' }).code;
  const context = { h: (type, props, ...children) => ({ type, props, children }), CodeBlock: 'code-block',
    InteractiveFileLinkPill: 'file-link', BACKEND_URL: 'fixture', isLikelyHostFilePath: () => false };
  runInNewContext(compiled, context);
  return context.render;
}

test('streaming absent children do not render a block or literal undefined', () => {
  const render = codeRenderer();
  assert.equal(render({ className: 'language-python', children: undefined }), null);
  assert.equal(render({ className: 'language-python', children: null }), null);
  assert.equal(render({ className: 'language-python', children: [null, undefined] }), null);
});

test('streamed real code including null and undefined stays visible', () => {
  const render = codeRenderer();
  for (const value of ['null', 'undefined', 'value = 1']) {
    assert.equal(render({ className: 'language-javascript', children: [value, '\n'] }).props.code, value);
  }
});

test('mobile navbar uses independent padding sides so branch changes cannot conflict', async () => {
  const navbar = await readFile(path.join(root, 'frontend/src/components/TopNavbar.jsx'), 'utf8');
  const ast = parse(navbar, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
  let conflict = false;
  traverse(ast, { ObjectExpression(p) {
    const keys = p.node.properties.map(item => item.key?.name ?? item.key?.value);
    if (keys.includes('padding') && keys.some(key => /^padding(?:Top|Right|Bottom|Left)$/.test(key))) conflict = true;
  } });
  assert.equal(conflict, false, 'React shorthand/longhand padding updates must not overlap');
});

async function swarmSource() {
  const text = await readFile(path.join(root, 'frontend/src/components/SpecialistSwarmExplorer.jsx'), 'utf8');
  const ast = parse(text, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
  const found = [];
  traverse(ast, { enter(p) { found.push(p); } });
  return { text, nodes: found };
}

test('specialist requests acquire auth and preserve request headers before fetching', async () => {
  const swarm = await swarmSource();
  const helper = swarm.nodes.find(p => p.isFunctionDeclaration() && p.node.id.name === 'swarmRequest');
  assert.ok(helper, 'Protected specialist endpoints must use the shared authenticated transport');
  let calls = 0;
  const request = runInNewContext(`(${swarm.text.slice(helper.node.start, helper.node.end)})`, {
    chatAuthHeaders: async headers => ({ ...headers, Authorization: 'Bearer synthetic-user' }),
    fetch: async (url, options) => { calls++; assert.equal(url, '/fixture');
      assert.equal(options.headers.Authorization, 'Bearer synthetic-user');
      assert.equal(options.headers['Content-Type'], 'application/json');
      assert.equal(options.method, 'POST'); return 'retained response'; },
  });
  assert.equal(await request('/fixture', { method: 'POST', headers: { 'Content-Type': 'application/json' } }), 'retained response');
  assert.equal(calls, 1);
  const component = swarm.nodes.find(p => p.isFunctionDeclaration() && p.node.id.name === 'SpecialistSwarmExplorer');
  assert.ok(!swarm.nodes.some(p => p.isCallExpression() && p.node.callee.name === 'fetch' && p.node.start > component.node.start),
    'Every component request must use the auth helper');
});

test('unconfigured specialist gate is unavailable while a configured gate remains selectable', async () => {
  const swarm = await swarmSource();
  const handler = swarm.nodes.find(p => p.isJSXAttribute() && p.node.name.name === 'onClick' &&
    swarm.text.slice(p.node.start, p.node.end).includes('handleRunVerification(selectedSpecialist)'));
  assert.ok(handler);
  const disabled = handler.parentPath.node.attributes.find(attribute => attribute.name?.name === 'disabled').value.expression;
  const check = selectedSpecialist => runInNewContext(swarm.text.slice(disabled.start, disabled.end), { selectedSpecialist, verifyingId: null });
  assert.equal(check({ agent_id: 'fixture', check_status: 'unconfigured_check' }), true);
  assert.equal(check({ agent_id: 'fixture', check_status: 'configured' }), false);
  assert.equal(check({ agent_id: 'fixture' }), false, 'Absence of a readiness field must not disable a previously configured gate');
});

test('structured specialist and chapter errors become readable text', async () => {
  const swarm = await swarmSource();
  const helper = swarm.nodes.find(p => p.isFunctionDeclaration() && p.node.id.name === 'formatSwarmError');
  assert.ok(helper);
  const format = runInNewContext(`(${swarm.text.slice(helper.node.start, helper.node.end)})`);
  assert.equal(format('known error'), 'known error');
  assert.equal(JSON.parse(format({ reason: 'lexical mismatch' })).reason, 'lexical mismatch');
});

test('chapter success displays the chapter identifier returned in the backend record', async () => {
  const swarm = await swarmSource();
  const identifier = swarm.nodes.find(p => p.isJSXElement() && p.node.openingElement.name.name === 'strong' &&
    swarm.text.slice(p.node.start, p.node.end).includes('sealStatus.data'));
  assert.ok(identifier);
  const compiled = transformSync(`globalThis.output = ${swarm.text.slice(identifier.node.start, identifier.node.end)}`,
    { loader: 'jsx', jsxFactory: 'h', target: 'es2022' }).code;
  const context = { h: (_type, _props, ...children) => children,
    sealStatus: { passed: true, data: { record: { chapter_id: 'synthetic-chapter' } } } };
  runInNewContext(compiled, context);
  assert.equal(context.output[0], 'synthetic-chapter');
});
