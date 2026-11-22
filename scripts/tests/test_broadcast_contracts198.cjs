const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const project = path.resolve(__dirname, '../..');
const sources = process.env.AIBS_AUDIT_SOURCE_ROOT || project;
const parser = require(path.join(project, 'frontend/node_modules/@babel/parser'));
const source = fs.readFileSync(path.join(sources, 'frontend/src/components/BroadcastStudio.jsx'), 'utf8');
const tree = parser.parse(source, { sourceType: 'module', plugins: ['jsx'] });
test('broadcast defaults contain no embedded stream credentials or enabled destinations', () => {
  const records = [];
  function visit(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'ObjectExpression' && node.properties.some(p => p.key?.name === 'url' && p.value?.type === 'StringLiteral' && /^rtmps?:/.test(p.value.value))) {
      records.push(node.properties);
    }
    for (const [key, value] of Object.entries(node)) {
      if (['start', 'end', 'loc', 'extra'].includes(key)) continue;
      if (Array.isArray(value)) value.forEach(visit);
      else if (value && typeof value === 'object') visit(value);
    }
  }
  visit(tree.program);
  assert.ok(records.length > 0);
  assert.ok(records.every(record => record.find(p => p.key?.name === 'key')?.value?.value === ''), 'Embedded credentials must be absent; values are deliberately not included in diagnostics.');
  assert.ok(records.every(record => record.find(p => p.key?.name === 'enabled')?.value?.value === false));
});
test('sticky state retains existing local draft values and setter semantics', () => {
  const hook = tree.program.body.find(node => node.type === 'FunctionDeclaration' && node.id.name === 'useStickyState');
  assert.ok(hook);
  const saved = { title: 'fixture draft', settings: { volume: 27 }, values: [1, 2] };
  const writes = [];
  const effects = [];
  const setter = () => {};
  const fn = vm.runInNewContext('(' + source.slice(hook.start, hook.end) + ')', {
    useState: initialize => [initialize(), setter],
    useEffect: callback => effects.push(callback),
    window: { localStorage: { getItem: () => JSON.stringify(saved), setItem: (...args) => writes.push(args) } },
    console: { error() {} }
  });
  const [value, update] = fn({ title: 'unused default' }, 'fixture-key');
  assert.equal(JSON.stringify(value), JSON.stringify(saved));
  assert.equal(update, setter);
  assert.equal(writes.length, 0);
  effects.forEach(effect => effect());
  assert.equal(writes.length, 1);
  assert.equal(writes[0][0], 'fixture-key');
  assert.equal(writes[0][1], JSON.stringify(saved));
});
