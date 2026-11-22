import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Script } from 'node:vm';
import { masterHubs } from '../src/components/navigationConfig.js';
import { canAccessTab } from '../src/components/accessControl.js';
import { resolveInitialWorkspaceTab } from '../src/components/portalRouting.js';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');

test('BS Game is reachable through engineering navigation and a direct workspace link', () => {
  const hub = masterHubs.find(item => item.key === 'engineering_labs');
  assert.ok(hub.subTabs.some(tab => tab.key === 'bs_game'));
  assert.equal(canAccessTab('free_demo', 'bs_game'), true);
  assert.equal(resolveInitialWorkspaceTab('?tab=bs_game', null), 'bs_game');
  const app = readFileSync(resolve(frontend, 'App.jsx'), 'utf8');
  assert.match(app, /key: 'bs_game'.*Component: BSGameHubTab/);
});

test('playground is deployable without an external runtime CDN', () => {
  const path = resolve(frontend, 'public/bs-game/index.html');
  const html = readFileSync(path, 'utf8');
  assert.match(html, /simulated concept values/);
  assert.match(html, /no connection to native saves/);
  assert.match(html, /interaction-prompt/);
  assert.match(html, /Right-drag/);
  assert.match(html, /KeyE/);
  assert.doesNotMatch(html, /<script[^>]+src=["']https?:/i);
  const references = [...html.matchAll(/<script[^>]+src=["']([^"']+)/g)].map(match => match[1]);
  assert.deepEqual(references, ['./vendor/three-r128.min.js']);
  assert.ok(existsSync(resolve(dirname(path), references[0])));
  for (const block of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
    if (block[1].trim()) new Script(block[1]);
  }
  const vendor = readFileSync(resolve(dirname(path), references[0]), 'utf8');
  assert.match(vendor, /REVISION.*128|128.*REVISION/);
  assert.deepEqual(readdirSync(dirname(path)).sort(), ['index.html', 'vendor']);
});

test('published native preview is a real PNG and the snapshot distinguishes it from browser play', () => {
  const component = readFileSync(resolve(frontend, 'src/components/BSGameHubTab.jsx'), 'utf8');
  assert.match(component, /SDK 0\.3/);
  assert.match(component, /src="\/assets\/bs-game-native-preview\.png"/);
  assert.doesNotMatch(component, /currently headless|full game, renderer and companion are being developed/);
  const preview = readFileSync(resolve(frontend, 'public/assets/bs-game-native-preview.png'));
  assert.equal(preview.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  assert.ok(preview.length > 10000);
  assert.match(component, /separate creative playground/);
});
