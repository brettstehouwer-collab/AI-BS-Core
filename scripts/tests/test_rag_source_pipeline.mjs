import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { webcrypto } from 'node:crypto';
import { createRequire } from 'node:module';
import { createContext, SourceTextModule, SyntheticModule } from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const source = await readFile(path.join(root, 'frontend/src/utils/ragSourceStage.js'), 'utf8');
const hash = async text => Buffer.from(await webcrypto.subtle.digest('SHA-256', new TextEncoder().encode(text))).toString('hex');
const filename = `context_${'a'.repeat(32)}.txt`;

async function utility(handler) {
  const calls = [];
  const context = createContext({ TextEncoder, TextDecoder, AbortSignal, crypto:webcrypto,
    fetch:async (url, options) => { calls.push({ url, ...options }); return handler(url, options); } });
  const module = new SourceTextModule(source, { context });
  await module.link(async specifier => {
    if (specifier.endsWith('/chatAuth.js')) {
      const auth = new SyntheticModule(['chatAuthHeaders'], function () {
        this.setExport('chatAuthHeaders', async headers => ({ ...headers, Authorization:'Bearer synthetic-user' }));
      }, { context });
      return auth;
    }
    if (specifier.endsWith('/chatHttpResponse.js')) {
      const response = new SyntheticModule(['readChatHttpResponse'], function () {
        this.setExport('readChatHttpResponse', async data => data);
      }, { context });
      return response;
    }
    throw new Error('Unexpected dependency');
  });
  await module.evaluate();
  return { api:module.namespace, calls };
}

test('saved-source pipeline verifies authenticated read, index and retrieved Unicode bytes', async () => {
  const text = 'Ω🌲 source bytes\r\nretained';
  const sha256 = await hash(text);
  const { api, calls } = await utility(async (url, options) => {
    assert.equal(options.headers.Authorization, 'Bearer synthetic-user');
    if (url.endsWith('/api/executive/run')) return { status:'success', result:{ status:'success', content:text,
      size_bytes:new TextEncoder().encode(text).length, sha256, decoding_errors_replaced:false, truncated:false } };
    if (url.endsWith('/api/memory')) return { status:'success', memory_index_status:'lexical_chunks_indexed',
      parsing_status:'complete', source_sha256:sha256, chunk_count:1 };
    return { status:'success', search_type:'lexical_scan', results:[{ content:text, source_sha256:sha256,
      byte_start:0, byte_end:new TextEncoder().encode(text).length, chunk_sha256:sha256 }] };
  });
  const result = await api.indexSavedRagSource({ backendUrl:'http://fixture', filename, expectedSha256:sha256 });
  assert.equal(calls.length, 3);
  assert.equal(result.retrieval_status, 'source_passage_readback_verified');
  assert.equal(result.retrieval_hits, 1);
  assert.equal(result.model_context_expanded, false);
});

test('wrong saved-source fingerprint and replaced decoding never reach index', async () => {
  for (const replaced of [false, true]) {
    const text = 'preserved';
    const { api, calls } = await utility(async () => ({ status:'success', result:{ status:'success', content:text,
      size_bytes:text.length, sha256:await hash(text), decoding_errors_replaced:replaced, truncated:false } }));
    await assert.rejects(api.indexSavedRagSource({ backendUrl:'http://fixture', filename, expectedSha256:'0'.repeat(64) }));
    assert.equal(calls.length, 1);
  }
});

test('saved-source import rejects arbitrary paths before host access', async () => {
  const { api, calls } = await utility(() => { throw new Error('Host access must not occur'); });
  await assert.rejects(api.indexSavedRagSource({ backendUrl:'http://fixture', filename:'../private.txt' }));
  assert.equal(calls.length, 0);
});

test('retrieval mismatch is not presented as a successful passage readback', async () => {
  const text = 'source';
  const sha256 = await hash(text);
  const { api } = await utility(async url => url.endsWith('/api/executive/run')
    ? { status:'success', result:{ status:'success', content:text, size_bytes:text.length, sha256,
        decoding_errors_replaced:false, truncated:false } }
    : url.endsWith('/api/memory')
      ? { status:'success', memory_index_status:'lexical_chunks_indexed', parsing_status:'complete', source_sha256:sha256, chunk_count:1 }
      : { status:'success', search_type:'lexical_scan', results:[{ content:'wrong', source_sha256:sha256, byte_start:0, byte_end:6, chunk_sha256:sha256 }] });
  await assert.rejects(api.indexSavedRagSource({ backendUrl:'http://fixture', filename }), /retrieval was not confirmed/);
});

test('large-paste source guard precedes tool dispatch and removes unsupported activation labels', async () => {
  const chat = await readFile(path.join(root, 'frontend/src/components/ChatTab.jsx'), 'utf8');
  const requireFrontend = createRequire(path.join(root, 'frontend/package.json'));
  const tree = requireFrontend('@babel/parser').parse(chat, { sourceType:'module', plugins:['jsx'] });
  function nodes(rootNode, predicate) {
    const pending = [rootNode], found = [];
    while (pending.length) {
      const node = pending.pop();
      if (!node || typeof node !== 'object') continue;
      if (predicate(node)) found.push(node);
      for (const [key, value] of Object.entries(node)) {
        if (['loc','comments','tokens'].includes(key)) continue;
        if (Array.isArray(value)) pending.push(...value);
        else if (value && typeof value === 'object') pending.push(value);
      }
    }
    return found;
  }
  const handlers = nodes(tree, node => node.type==='VariableDeclarator' && node.id?.name==='handleSendMessage');
  assert.equal(handlers.length, 1);
  const statements = handlers[0].init.body.body;
  const guards = statements.filter(node => node.type==='IfStatement'
    && nodes(node.test, child => child.type==='BinaryExpression' && child.operator==='>' && child.right?.value===16000).length
    && nodes(node.consequent, child => child.type==='CallExpression' && child.callee?.name==='stageRagSource').length);
  const dispatches = statements.filter(node => node.type==='IfStatement'
    && nodes(node.test, child => child.type==='CallExpression'
      && child.callee?.object?.name==='rawText' && child.callee?.property?.name==='startsWith'
      && child.arguments[0]?.value==='/').length);
  assert.equal(guards.length, 1);
  assert.equal(dispatches.length, 1);
  assert.ok(guards[0].start > 0 && dispatches[0].start > guards[0].end);
  assert.equal(nodes(guards[0].test, node => node.type==='UnaryExpression'
    && node.operator==='!' && node.argument?.name==='openCodeWorkerCommand').length, 1);
  const guard = chat.slice(guards[0].start, guards[0].end);
  assert.match(guard, /stageRagSource/);
  assert.match(guard, /return;/);
  assert.match(guard, /plan_and_review/);
  assert.doesNotMatch(chat, /1M\+ RAG Active|QLoRA Active/);
});
