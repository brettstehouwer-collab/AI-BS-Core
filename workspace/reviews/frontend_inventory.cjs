/* Source-only import/tab inventory. Never require or evaluate application files. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const parser = require('../../frontend/node_modules/@babel/parser');

const EXTENSIONS = ['.jsx', '.tsx', '.js', '.ts', '.mjs', '.cjs'];
const MAX_BYTES = 8 * 1024 * 1024;
const MAX_FILES = 5000;
function walk(node, visit) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { for (const item of node) walk(item, visit); return; }
  if (typeof node.type === 'string') visit(node);
  for (const [key, value] of Object.entries(node)) {
    if (!['loc', 'start', 'end', 'extra', 'comments', 'tokens', 'errors'].includes(key)) walk(value, visit);
  }
}
function property(object, name) {
  return object?.properties?.find(p => (p.key?.name || p.key?.value) === name)?.value;
}
function literal(node) { return node?.type === 'StringLiteral' ? node.value : null; }
function relative(root, file) { return path.relative(root, file).split(path.sep).join('/'); }
function inside(directory, file) {
  const rel = path.relative(directory, file);
  return rel !== '..' && !rel.startsWith('..' + path.sep) && !path.isAbsolute(rel);
}
function redirected(directory, file) {
  let current = file;
  while (inside(directory, current)) {
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) return true;
    if (current === directory) break;
    current = path.dirname(current);
  }
  return false;
}
function readSource(file) {
  const descriptor = fs.openSync(file, 'r');
  try {
    const size = fs.fstatSync(descriptor).size;
    if (size > MAX_BYTES) throw Error('Source byte bound exceeded');
    // One extra byte detects growth without an unbounded read/allocation.
    const buffer = Buffer.alloc(size + 1);
    let length = 0;
    while (length < buffer.length) {
      const count = fs.readSync(descriptor, buffer, length, buffer.length - length, null);
      if (!count) break;
      length += count;
    }
    if (length > size) throw Error('Source changed during bounded read');
    return buffer.subarray(0, length);
  } finally { fs.closeSync(descriptor); }
}
function resolveImport(frontend, from, specifier) {
  const rootRelative = specifier.startsWith('/') && !specifier.startsWith('//');
  if (!rootRelative && !specifier.startsWith('.')) return { external: true };
  const base = rootRelative ? path.resolve(frontend, '.' + specifier) : path.resolve(path.dirname(from), specifier);
  if (!inside(frontend, base)) return { reason: 'outside_frontend' };
  const candidates = path.extname(base) ? [base] :
    [...EXTENSIONS.map(ext => base + ext), ...EXTENSIONS.map(ext => path.join(base, 'index' + ext))];
  for (const file of candidates) {
    if (redirected(frontend, file)) return { reason: 'redirected_source' };
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) continue;
    if (!inside(fs.realpathSync(frontend), fs.realpathSync(file))) return { reason: 'outside_frontend' };
    if (!EXTENSIONS.includes(path.extname(file))) return { asset: true };
    return { file };
  }
  return { reason: 'missing_source' };
}
function collectFrontend(root) {
  root = path.resolve(root);
  const frontend = path.join(root, 'frontend');
  if (!fs.existsSync(frontend) || fs.lstatSync(frontend).isSymbolicLink()) throw Error('Non-redirected frontend required');
  const queue = [path.join(frontend, 'main.jsx')], seen = new Set(), pins = [], imports = [];
  const parseErrors = [], unresolved = [], references = [], tabs = [], aliases = {}, navigation = [];
  while (queue.length) {
    const file = queue.shift();
    if (seen.has(file)) continue;
    if (seen.size >= MAX_FILES) throw Error('Source file bound exceeded');
    seen.add(file);
    if (redirected(frontend, file)) throw Error('Redirected entry source');
    const buffer = readSource(file);
    const name = relative(root, file);
    const pin = { file: name, bytes: buffer.length, sha256: crypto.createHash('sha256').update(buffer).digest('hex'), parse_status: 'ok' };
    pins.push(pin);
    let tree;
    try {
      tree = parser.parse(buffer.toString('utf8'), { sourceType: 'unambiguous', plugins: ['jsx', 'typescript', 'importAttributes'] });
    } catch (error) {
      pin.parse_status = 'error';
      parseErrors.push({ file: name, error_type: error.name, line: error.loc?.line || null });
      continue;
    }
    const sourceImports = [], providers = new Map();
    walk(tree, node => {
      if (['ImportDeclaration', 'ExportNamedDeclaration', 'ExportAllDeclaration'].includes(node.type) && literal(node.source)) {
        sourceImports.push({ specifier: node.source.value, line: node.loc.start.line });
        for (const spec of node.specifiers || []) if (spec.local) providers.set(spec.local.name, node.source.value);
      }
      if ((node.type === 'CallExpression' && node.callee.type === 'Import') || node.type === 'ImportExpression') {
        const specifier = literal(node.source || node.arguments[0]);
        if (specifier) sourceImports.push({ specifier, line: node.loc.start.line });
        else unresolved.push({ file: name, line: node.loc.start.line, reason: 'dynamic_import' });
      }
      if (node.type === 'VariableDeclarator' && node.id.type === 'Identifier') {
        const candidates = [];
        walk(node.init, child => {
          if (child.type === 'CallExpression' && child.callee.type === 'Import' && literal(child.arguments[0])) candidates.push(literal(child.arguments[0]));
        });
        if (candidates.length === 1) providers.set(node.id.name, candidates[0]);
      }
      let text = literal(node), dynamic = false;
      if (node.type === 'TemplateLiteral') {
        text = node.quasis.map((q, i) => q.value.raw + (i < node.expressions.length ? '{dynamic}' : '')).join('');
        dynamic = node.expressions.length > 0;
      }
      if (typeof text === 'string') {
        const start = text.indexOf('/api/');
        if (start >= 0) {
          const apiPath = text.slice(start).split(/[?#\s'"`]/)[0];
          if (/^\/api\/[A-Za-z0-9_./:{}$~%+&=,()\[\]-]*$/.test(apiPath)) references.push({ file: name, line: node.loc.start.line, path: apiPath, dynamic });
        }
      }
    });
    for (const item of sourceImports) {
      const resolved = resolveImport(frontend, file, item.specifier);
      if (resolved.external || resolved.asset) continue;
      if (resolved.file) {
        imports.push({ file: name, line: item.line, target: relative(root, resolved.file) });
        queue.push(resolved.file);
      } else unresolved.push({ file: name, line: item.line, reason: resolved.reason });
    }
    if (name === 'frontend/App.jsx') walk(tree, node => {
      if (node.type !== 'VariableDeclarator' || node.id.type !== 'Identifier') return;
      if (node.id.name === 'tabs' && node.init?.type === 'ArrayExpression') for (const item of node.init.elements) {
        const symbol = property(item, 'Component')?.name || null;
        const specifier = providers.get(symbol);
        const resolved = specifier ? resolveImport(frontend, file, specifier) : {};
        tabs.push({ key: literal(property(item, 'key')), label: literal(property(item, 'label')),
          component_symbol: symbol, component_file: resolved.file ? relative(root, resolved.file) : null,
          line: item.loc.start.line, evidence: 'source_declared', workflow_verified: false });
      }
      if (node.id.name === 'TAB_ALIASES' && node.init?.type === 'ObjectExpression') for (const item of node.init.properties) {
        const key = item.key?.name || literal(item.key), value = literal(item.value);
        if (key && value) aliases[key] = value;
      }
    });
    if (name === 'frontend/components/navigationConfig.js') walk(tree, node => {
      if (node.type !== 'VariableDeclarator' || node.init?.type !== 'ArrayExpression') return;
      if (node.id.name === 'PINNED_QUICK_TABS') for (const item of node.init.elements) navigation.push({
        kind: 'pinned', key: literal(property(item, 'key')), label: literal(property(item, 'label')),
        hub_key: null, line: item.loc.start.line });
      if (node.id.name === 'masterHubs') for (const hub of node.init.elements) {
        const hubKey = literal(property(hub, 'key')), hubLabel = literal(property(hub, 'label'));
        const defaultKey = literal(property(hub, 'defaultTab'));
        if (defaultKey) navigation.push({ kind: 'default', key: defaultKey, label: hubLabel, hub_key: hubKey, line: hub.loc.start.line });
        for (const item of property(hub, 'subTabs')?.elements || []) navigation.push({
          kind: 'subtab', key: literal(property(item, 'key')), label: literal(property(item, 'label')),
          hub_key: hubKey, line: item.loc.start.line });
      }
    });
  }
  const tabKeys = new Set(tabs.map(tab => tab.key));
  for (const entry of navigation) {
    const key = aliases[entry.key] || entry.key;
    entry.component_key = tabKeys.has(key) ? key : null;
    entry.resolution = tabKeys.has(key) ? 'source_declared' : 'missing_component';
  }
  return { schema_version: 1, evidence: 'source_declared', runtime_coverage_verified: false,
    complete_source_parse: parseErrors.length === 0, source_file_count: pins.length,
    source_pins: pins.sort((a, b) => a.file.localeCompare(b.file)), imports, tabs, aliases,
    api_references: references, parse_errors: parseErrors, unresolved_imports: unresolved,
    navigation_entries: navigation,
    limits: ['Literal entry-reachable imports include dormant code and do not prove UI reachability.',
      'API strings do not prove call method, runtime base URL, authorization or server matching.',
      'Computed imports, runtime selection, Firebase SDK operations and non-JS assets need separate review.'] };
}
module.exports = { collectFrontend };
if (require.main === module) {
  const args = process.argv.slice(2), root = args[args.indexOf('--root') + 1], output = args[args.indexOf('--output') + 1];
  if (!args.includes('--root') || !args.includes('--output')) throw Error('--root and --output required');
  const result = collectFrontend(root);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  process.stdout.write(JSON.stringify({ source_file_count: result.source_file_count, tab_count: result.tabs.length,
    complete_source_parse: result.complete_source_parse, unresolved_imports: result.unresolved_imports.length }) + '\n');
}
