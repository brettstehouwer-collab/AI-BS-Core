import assert from 'node:assert/strict';
import test from 'node:test';
import {resolveInitialWorkspaceTab, rememberedWorkspaceTab} from '../src/components/portalRouting.js';

test('main entry recovers from a saved FE portal without changing explicit FE links', () => {
  assert.equal(resolveInitialWorkspaceTab('', 'fe_express'), 'dashboard');
  assert.equal(resolveInitialWorkspaceTab('?tab=fe_express', 'chat'), 'fe_express');
  assert.equal(resolveInitialWorkspaceTab('?tab=chat', 'fe_express'), 'chat');
});

test('former website portal entries return to main sign-in', () => {
  assert.equal(resolveInitialWorkspaceTab('', 'website_home'), 'dashboard');
  assert.equal(resolveInitialWorkspaceTab('?tab=website_home', 'chat'), 'dashboard');
});

test('main workspace preferences and existing deep-link migrations remain usable', () => {
  assert.equal(resolveInitialWorkspaceTab('', 'chat'), 'chat');
  assert.equal(resolveInitialWorkspaceTab('', null), 'dashboard');
  assert.equal(resolveInitialWorkspaceTab('?portal=nda', 'chat'), 'nda_module');
  assert.equal(resolveInitialWorkspaceTab('?tab=gaming_lab', null), 'central_gaming_hub');
  assert.equal(resolveInitialWorkspaceTab('', 'wallets'), 'unified_crypto');
});

test('FE visits cannot overwrite the main workspace preference', () => {
  let remembered = 'chat';
  for (const tab of ['fe_express', 'website_home']) {
    const next = rememberedWorkspaceTab(tab);
    if (next) remembered = next;
  }
  assert.equal(remembered, 'chat');
  assert.equal(rememberedWorkspaceTab('dashboard'), 'dashboard');
});
