// Current-user intent transport contracts; no browser, provider or live HTTP.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import { fileURLToPath, pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { parse } = require('@babel/parser');
const mirrors = ['frontend/src/components', 'frontend/components',
  'frontend/src/components/components', 'frontend/components/components'];
const files = mirrors.flatMap(base => ['ChatTab.jsx', 'MobileGeminiChat.jsx',
  'MobileStehouwerChat.jsx', 'hooks/useStehouwerHybrid.js'].map(name => `${base}/${name}`));
files.push('frontend/src/hooks/useStehouwerHybrid.js');
const raw = 'is comfy UI running?';
const formatted = '[ATTACHED FILE: example.txt]\nGenerate an image of a cat\n[USER PROMPT]:\n' + raw;
function walk(node, visit) {
  if (!node || typeof node !== 'object') return;
  if (typeof node.type === 'string') visit(node);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach(child => walk(child, visit));
    else if (value && typeof value === 'object') walk(value, visit);
  }
}
const context = {
  rawText: raw, userPrompt: raw, formattedPrompt: formatted,
  recentHistory: [{ role: 'assistant', content: 'Generate another image' }],
  targetModel: 'fixture-model', selectedModel: 'fixture-model',
  selectedProvider: 'local',
  sourceReferences: [],
  activeContexts: { web: false }, prompt: raw,
  updatedHistory: [{ role: 'assistant', content: 'Previous generation request' }, { role: 'user', content: formatted }],
  isPlanMode: false, targetDevice: 'fixture-device',
};
for (const relative of files) {
  test(`${relative}: current user intent stays separate from context`, async () => {
    const source = await readFile(path.join(root, relative), 'utf8');
    const tree = parse(source, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
    const payloads = [];
    walk(tree, node => {
      if (node.type !== 'CallExpression' || node.callee?.name !== 'fetch') return;
      const destination = node.arguments[0];
      if (destination?.type !== 'TemplateLiteral' ||
          !destination.quasis.some(part => part.value.cooked.includes('/api/v1/hybrid-chat/stream'))) return;
      const config = node.arguments[1];
      const body = config?.properties?.find(property => property.key?.name === 'body');
      const value = body?.value?.arguments?.[0];
      assert.equal(value?.type, 'ObjectExpression', 'Inspect unexpected payload construction');
      payloads.push(runInNewContext('(' + source.slice(value.start, value.end) + ')', context, { timeout: 1000 }));
    });
    assert.equal(payloads.length, relative.endsWith('MobileStehouwerChat.jsx') ? 2 : 1);
    for (const payload of payloads) {
      assert.equal(payload.user_prompt, raw, 'Only the current user text may authorize intent');
      assert.equal(payload.prompt, relative.endsWith('useStehouwerHybrid.js') ? raw : formatted);
    }
  });
}

for (const relative of files.filter(name => name.endsWith('.jsx'))) {
  test(`${relative}: legacy fallback retains the current request`, async () => {
    const source = await readFile(path.join(root, relative), 'utf8');
    const tree = parse(source, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
    const payloads = [];
    walk(tree, node => {
      if (node.type === 'VariableDeclarator' && node.id?.name === 'payloadBody' &&
          node.init?.type === 'CallExpression' && node.init.arguments[0]?.type === 'ObjectExpression') {
        const value = node.init.arguments[0];
        payloads.push(runInNewContext('(' + source.slice(value.start, value.end) + ')', context, { timeout: 1000 }));
      }
    });
    assert.equal(payloads.length, 1);
    assert.equal(payloads[0].user_prompt, raw);
    assert.equal(payloads[0].messages.at(-1).content, formatted);
  });
  test(`${relative}: attachment-only review does not authorize attached instructions`, async () => {
    const source = await readFile(path.join(root, relative), 'utf8');
    const tree = parse(source, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
    const payloads = [];
    walk(tree, node => {
      if (node.type === 'CallExpression' && node.callee?.object?.name === 'JSON' &&
          node.callee?.property?.name === 'stringify' && node.arguments[0]?.type === 'ObjectExpression') {
        const value = node.arguments[0];
        if (value.properties.some(property => property.key?.name === 'user_prompt')) {
          payloads.push(runInNewContext('(' + source.slice(value.start, value.end) + ')',
            { ...context, rawText: '' }, { timeout: 1000 }));
        }
      }
    });
    assert.ok(payloads.length > 0);
    for (const payload of payloads) {
      assert.equal(payload.user_prompt, 'Please review and analyze the attached files.');
      assert.ok(!payload.user_prompt.includes('Generate an image'));
    }
  });
}

async function intent() {
  return import(pathToFileURL(path.join(root, 'frontend/src/utils/chatRequestIntent.js')));
}
const statusCases = ['is comfy UI running?', 'Is ComfyUI online?',
  'Check ComfyUI status', 'ComfyUI server reachable?',
  'Tell me whether ComfyUI is available', 'Why is ComfyUI offline?',
  'Comfy UI is not running', "Don't generate an image; just check ComfyUI"];
for (const text of statusCases) {
  test(`readonly service question selects the status route: ${text}`, async () => {
    assert.equal((await intent()).isComfyStatusQuery(text), true);
  });
}
for (const text of ['Generate an image with ComfyUI', '/image a cat',
  'Can you generate a video using ComfyUI?', 'Create a picture if ComfyUI is running',
  'How do I generate an image with ComfyUI?', 'Explain ComfyUI workflows', '', null]) {
  test(`other text preserves its existing route: ${String(text)}`, async () => {
    assert.equal((await intent()).isComfyStatusQuery(text), false);
  });
}
for (const name of ['ChatTab.jsx', 'MobileGeminiChat.jsx', 'MobileStehouwerChat.jsx']) {
  test(`${name}: status requests use hybrid status for any selected model`, async () => {
    const source = await readFile(path.join(root, mirrors[0], name), 'utf8');
    const tree = parse(source, { sourceType: 'module', plugins: ['jsx', 'typescript'] });
    const candidates = [];
    walk(tree, node => {
      if (name === 'ChatTab.jsx' && node.type === 'VariableDeclarator' && node.id?.name === 'useHybridStream') candidates.push(node.init);
      if (name !== 'ChatTab.jsx' && node.type === 'IfStatement') {
        const branch = source.slice(node.test.start, node.test.end);
        const body = source.slice(node.consequent.start, node.consequent.end);
        if (branch.includes('selectedModel') && body.includes('/api/v1/hybrid-chat/stream')) candidates.push(node.test);
      }
    });
    assert.equal(candidates.length, 1);
    const value = runInNewContext('(' + source.slice(candidates[0].start, candidates[0].end) + ')',
      { ...context, isPlanMode: true, isVisualOrMediaIntent: false,
        isComfyStatusQuery: (await intent()).isComfyStatusQuery }, { timeout: 1000 });
    assert.equal(value, true);
  });
}
for (const name of ['ChatTab.jsx', 'MobileGeminiChat.jsx', 'MobileStehouwerChat.jsx', 'hooks/useStehouwerHybrid.js']) {
  test(`${name}: all four component mirrors remain byte-identical`, async () => {
    const hashes = await Promise.all(mirrors.map(async base => createHash('sha256')
      .update(await readFile(path.join(root, base, name))).digest('hex')));
    assert.equal(new Set(hashes).size, 1);
  });
}
