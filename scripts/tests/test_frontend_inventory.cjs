// Parse synthetic JS/TS only; source must never be evaluated.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { collectFrontend } = require('../../workspace/reviews/frontend_inventory.cjs');

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'aibs-inventory-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  function write(rel, text) {
    const target = path.join(root, rel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, text);
  }
  return { root, write };
}

test('follows current entry imports including lazy TSX and associates tabs', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'import App from "./App.jsx";');
  write('frontend/App.jsx', 'const Chat = safeLazy(() => import("./src/Chat.tsx")); const tabs = [{key:"chat", label:"Chat", Component:Chat}]; const TAB_ALIASES = {old:"chat"};');
  write('frontend/src/Chat.tsx', 'const x: string = "typed"; fetch(`${base}/api/chat/${id}?secret=PRIVATE_CANARY`);');
  const r = collectFrontend(root);
  assert.equal(r.source_file_count, 3);
  assert.equal(r.tabs[0].component_file, 'frontend/src/Chat.tsx');
  assert.equal(r.tabs[0].evidence, 'source_declared');
  assert.equal(r.aliases.old, 'chat');
  assert.equal(r.api_references[0].path, '/api/chat/{dynamic}');
  assert.equal(r.api_references[0].dynamic, true);
  assert.ok(!JSON.stringify(r).includes('PRIVATE_CANARY'));
  assert.equal(r.runtime_coverage_verified, false);
});

test('never evaluates source and exposes parse failures and missing imports', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'throw Error("NEVER_RUN_CANARY"); import App from "./App.jsx"; import "./Missing.jsx";');
  write('frontend/App.jsx', 'const broken = (');
  const r = collectFrontend(root);
  assert.equal(r.parse_errors.length, 1);
  assert.equal(r.unresolved_imports.length, 1);
  assert.equal(r.complete_source_parse, false);
  assert.ok(!JSON.stringify(r).includes('NEVER_RUN_CANARY'));
});

test('rejects outside-root and redirected imports before reading', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'import "../../outside.jsx";');
  const r = collectFrontend(root);
  assert.equal(r.unresolved_imports[0].reason, 'outside_frontend');
});

test('cycles, reexports and repeated imports have bounded deduplicated coverage', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'import "./App.jsx"; import "./App.jsx";');
  write('frontend/App.jsx', 'export {a} from "./A.js";');
  write('frontend/A.js', 'import "./App.jsx"; export const a = 1;');
  const r = collectFrontend(root);
  assert.equal(r.source_file_count, 3);
  assert.equal(r.parse_errors.length, 0);
});

test('follows Vite root-relative frontend imports and records their API references', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'import "./App.jsx";');
  write('frontend/App.jsx', 'import "/src/localHelper.js"; import "/components/Panel.jsx"; import React from "react";');
  write('frontend/src/localHelper.js', 'fetch("/api/root-helper");');
  write('frontend/components/Panel.jsx', 'export default () => null;');
  const r = collectFrontend(root);
  assert.equal(r.source_file_count, 4);
  assert.ok(r.api_references.some(ref => ref.path === '/api/root-helper'));
  assert.equal(r.unresolved_imports.length, 0);
});

test('rejects oversized source before any unbounded full-file read', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'x'.repeat(8 * 1024 * 1024 + 1));
  const originalRead = fs.readFileSync;
  let oversizedReads = 0;
  fs.readFileSync = function(file, ...args) {
    if (file === path.join(root, 'frontend/main.jsx')) oversizedReads++;
    return originalRead.call(this, file, ...args);
  };
  try {
    assert.throws(() => collectFrontend(root), /byte bound/);
    assert.equal(oversizedReads, 0, 'Source bytes must be bounded before allocation');
  } finally { fs.readFileSync = originalRead; }
});

test('joins navigation and pinned keys to canonical component keys without calling missing keys functional', t => {
  const { root, write } = fixture(t);
  write('frontend/main.jsx', 'import "./App.jsx";');
  write('frontend/App.jsx', 'import "./components/navigationConfig.js"; const Chat=lazy(()=>import("./Chat.jsx")); const tabs=[{key:"chat",label:"Chat",Component:Chat}]; const TAB_ALIASES={old:"chat"};');
  write('frontend/Chat.jsx', 'export default () => null;');
  write('frontend/components/navigationConfig.js', 'export const PINNED_QUICK_TABS=[{key:"missing",label:"Missing"}]; export const masterHubs=[{key:"hub",label:"Hub",defaultTab:"old",subTabs:[{key:"old",label:"Alias"}]}];');
  const r = collectFrontend(root);
  assert.equal(r.navigation_entries.length, 3);
  assert.equal(r.navigation_entries.find(n => n.kind === 'subtab').component_key, 'chat');
  assert.equal(r.navigation_entries.find(n => n.kind === 'pinned').resolution, 'missing_component');
  assert.equal(r.navigation_entries.find(n => n.kind === 'default').component_key, 'chat');
});
