// Execute the actual component's non-JSX body with inert React/Firebase hooks.
// No credentials, network, browser navigation, or real authentication are used.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.env.AIBS_AUDIT_SOURCE_ROOT || path.resolve(__dirname, '../..');
const parser = require(path.join(root, 'frontend/node_modules/@babel/parser'));
const source = fs.readFileSync(path.join(root, 'frontend/src/components/LoginModal.jsx'), 'utf8');
const program = parser.parse(source, { sourceType: 'module', plugins: ['jsx'] }).program;
const component = program.body.find(n => n.type === 'ExportDefaultDeclaration').declaration;
const renderReturn = component.body.body.find(n => n.type === 'ReturnStatement');
const helpers = program.body.filter(n => n.type === 'VariableDeclaration' || n.type === 'FunctionDeclaration')
  .map(n => source.slice(n.start, n.end)).join('\n');
const body = source.slice(component.body.start + 1, renderReturn.start);
const key = 'aibs_google_redirect_intent_v1';
const admin = { email: 'owner@fixture.invalid', emailVerified: true, uid: 'fixture-admin', displayName: 'Fixture', photoURL: null };
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };

function harness(options = {}) {
  const slots = [], effects = [], writes = [], logins = [], changes = [];
  const storage = new Map(options.intent ? [[key, options.intent]] : []);
  let cursor = 0, reloads = 0, redirects = 0, popups = 0, signouts = 0, redirectChecks = 0;
  const scope = {
    Promise, Error, JSON, String, Boolean,
    ADMIN_EMAILS: ['owner@fixture.invalid'], ADMIN_UIDS: ['fixture-admin'],
    auth: { signOut: async () => { signouts++; } }, googleProvider: { providerId: 'google.com' },
    localStorage: { setItem: (name, value) => writes.push([name, value]) },
    sessionStorage: {
      getItem: name => { if (options.storageFailure) throw new Error('storage unavailable'); return storage.get(name) ?? null; },
      setItem: (name, value) => { if (options.storageFailure) throw new Error('storage unavailable'); storage.set(name, value); },
      removeItem: name => { if (options.storageFailure) throw new Error('storage unavailable'); storage.delete(name); },
    },
    window: { location: { hostname: '127.0.0.1', reload: () => { reloads++; if (options.reloadFailure) throw new Error('reload unavailable'); } } },
    signInWithPopup: (...args) => { popups++; return options.popup ? options.popup(...args) : new Promise(() => {}); },
    signInWithRedirect: (...args) => { redirects++; return options.redirect ? options.redirect(...args) : new Promise(() => {}); },
    getRedirectResult: (...args) => { redirectChecks++; return options.result ? options.result(...args) : Promise.resolve(null); },
    useState: initial => {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], value => { slots[index] = value; changes.push([index, value]); }];
    },
    useRef: initial => { const index = cursor++; if (!(index in slots)) slots[index] = { current: initial }; return slots[index]; },
    useEffect: (setup, deps) => { const index = cursor++; if (!(index in slots)) { slots[index] = deps; effects.push({ setup, cleanup: null }); } },
  };
  const factory = vm.runInNewContext(`(function () { ${helpers}\nreturn function (onLoginSuccess) { ${body}\nreturn { handleGoogleSignIn, reloadSignIn }; }; })()`, scope);
  let actions;
  const render = (callback = user => logins.push(user)) => { cursor = 0; actions = factory(callback); return actions; };
  render();
  const mount = () => { for (const effect of effects) effect.cleanup = effect.setup(); };
  const unmount = () => { for (const effect of effects) effect.cleanup?.(); };
  return {
    render, mount, unmount, storage, writes, logins, changes,
    get actions() { return actions; }, get error() { return slots[0]; }, get pending() { return slots[1]; },
    get counts() { return { reloads, redirects, popups, signouts, redirectChecks }; },
  };
}

test('stalled popup recovery reloads with one-shot intent, without redirecting the old context', async () => {
  const popup = deferred();
  const h = harness({ popup: () => popup.promise }); h.mount(); await flush();
  const pending = h.actions.handleGoogleSignIn();
  assert.equal(h.pending, 'popup');
  h.actions.reloadSignIn(true);
  assert.equal(h.storage.get(key), 'google');
  assert.equal(h.counts.reloads, 1);
  assert.equal(h.counts.redirects, 0);
  const changed = h.changes.length;
  popup.resolve({ user: admin }); await pending;
  assert.equal(h.changes.length, changed, 'late popup cannot change replacement progress');
  assert.equal(h.logins.length, 0); assert.equal(h.writes.length, 0);
});

test('late popup failure is ignored after same-tab recovery', async () => {
  const popup = deferred();
  const h = harness({ popup: () => popup.promise }); h.mount(); await flush();
  const pending = h.actions.handleGoogleSignIn(); h.actions.reloadSignIn(true);
  const changed = h.changes.length;
  popup.reject(new Error('late failure')); await pending;
  assert.equal(h.changes.length, changed); assert.equal(h.pending, 'reload');
});

test('StrictMode abandoned effect neither consumes intent nor starts a duplicate redirect', async () => {
  const h = harness({ intent: 'google' });
  h.mount(); h.unmount(); h.mount(); await flush();
  assert.equal(h.storage.has(key), false);
  assert.equal(h.counts.redirects, 1); assert.equal(h.counts.redirectChecks, 0);
  assert.equal(h.pending, 'redirect');
});

test('consumed intent does not redirect again on the return document', async () => {
  const first = harness({ intent: 'google' }); first.mount(); await flush();
  const returned = harness({ result: async () => ({ user: admin }) }); returned.mount(); await flush();
  assert.equal(first.counts.redirects, 1); assert.equal(returned.counts.redirects, 0);
  assert.equal(returned.counts.redirectChecks, 1); assert.equal(returned.logins.length, 1);
});

test('redirect rejection stays visible and releases pending state for explicit retry', async () => {
  const h = harness({ intent: 'google', redirect: async () => { throw new Error('provider refused'); } });
  h.mount(); await flush();
  assert.match(h.error, /provider refused/); assert.equal(h.pending, '');
  assert.equal(h.storage.has(key), false); assert.equal(h.logins.length, 0);
  h.actions.reloadSignIn(true); assert.equal(h.counts.reloads, 1);
});

test('unexpected non-navigating redirect does not leave a permanently pending button', async () => {
  const h = harness({ intent: 'google', redirect: async () => undefined }); h.mount(); await flush();
  assert.match(h.error, /did not open/); assert.equal(h.pending, ''); assert.equal(h.logins.length, 0);
});

test('verified allowlisted popup accepts real identity and caches only existing identity fields', async () => {
  const h = harness({ popup: async () => ({ user: admin }) }); h.mount(); await flush();
  await h.actions.handleGoogleSignIn();
  assert.equal(h.logins[0], admin); assert.equal(h.counts.signouts, 0); assert.equal(h.pending, '');
  assert.deepEqual(JSON.parse(h.writes[0][1]), { email: admin.email, displayName: admin.displayName, uid: admin.uid, photoURL: admin.photoURL });
});

for (const user of [{ ...admin, emailVerified: false }, { ...admin, email: 'other@fixture.invalid', uid: 'other' }]) {
  test(`popup refuses ${user.emailVerified ? 'nonallowlisted' : 'unverified'} identity`, async () => {
    const h = harness({ popup: async () => ({ user }) }); h.mount(); await flush();
    await h.actions.handleGoogleSignIn();
    assert.equal(h.logins.length, 0); assert.equal(h.writes.length, 0); assert.equal(h.counts.signouts, 1);
    assert.match(h.error, /administrator list/);
  });
}

test('redirect result preserves verification and administrator checks', async () => {
  const h = harness({ result: async () => ({ user: { ...admin, emailVerified: false } }) }); h.mount(); await flush();
  assert.equal(h.logins.length, 0); assert.equal(h.writes.length, 0); assert.equal(h.counts.signouts, 1);
  assert.match(h.error, /administrator list/);
});

test('popup closed or blocked displays the actual error and never silently redirects', async () => {
  const h = harness({ popup: async () => { throw { code: 'auth/popup-closed-by-user', message: 'Window closed' }; } }); h.mount(); await flush();
  await h.actions.handleGoogleSignIn();
  assert.match(h.error, /Window closed/); assert.equal(h.pending, '');
  assert.equal(h.counts.redirects, 0); assert.equal(h.counts.reloads, 0);
});

test('new popup supersedes a pending redirect-result check', async () => {
  const result = deferred(); const popup = deferred();
  const h = harness({ result: () => result.promise, popup: () => popup.promise }); h.mount(); await flush();
  const pending = h.actions.handleGoogleSignIn();
  result.resolve({ user: admin }); await flush();
  assert.equal(h.logins.length, 0); assert.equal(h.pending, 'popup');
  popup.resolve({ user: admin }); await pending; assert.equal(h.logins.length, 1);
});

for (const kind of ['popup', 'redirect-result', 'redirect']) {
  test(`unmounted ${kind} completion causes no state, cache, or callback updates`, async () => {
    const task = deferred();
    const options = kind === 'popup' ? { popup: () => task.promise }
      : kind === 'redirect' ? { intent: 'google', redirect: () => task.promise } : { result: () => task.promise };
    const h = harness(options); h.mount(); await flush();
    const pending = kind === 'popup' ? h.actions.handleGoogleSignIn() : null;
    h.unmount(); const changed = h.changes.length;
    task.resolve({ user: admin }); await pending; await flush();
    assert.equal(h.changes.length, changed); assert.equal(h.logins.length, 0); assert.equal(h.writes.length, 0);
  });
}

test('latest success callback is used without rechecking redirects on parent rerender', async () => {
  const popup = deferred(); const newest = [];
  const h = harness({ popup: () => popup.promise }); h.mount(); await flush();
  const pending = h.actions.handleGoogleSignIn(); h.render(user => newest.push(user));
  popup.resolve({ user: admin }); await pending;
  assert.equal(newest[0], admin); assert.equal(h.logins.length, 0); assert.equal(h.counts.redirectChecks, 1);
});

test('session-storage failure is visible, with no navigation or redirect', async () => {
  const h = harness({ storageFailure: true }); h.mount(); await flush(); h.actions.reloadSignIn(true);
  assert.match(h.error, /session storage/); assert.equal(h.counts.reloads, 0); assert.equal(h.counts.redirects, 0);
});

test('restart clears the intent; reload failure remains visible and can be retried', async () => {
  const h = harness({ reloadFailure: true }); h.mount(); await flush();
  h.actions.reloadSignIn(true); assert.match(h.error, /Could not restart/); assert.equal(h.pending, 'reload');
  h.actions.reloadSignIn(false); assert.equal(h.storage.has(key), false); assert.equal(h.counts.reloads, 2);
});

test('accessible explicit recovery and mirrored source remain present', () => {
  assert.match(source, /Continue sign-in in this tab/); assert.match(source, /Restart sign-in/);
  assert.match(source, /role="alert"/); assert.match(source, /role="status"/); assert.match(source, /aria-busy=\{isSubmitting\}/);
  assert.match(source, /fieldset disabled=\{isSubmitting\}/);
  assert.doesNotMatch(source, /URLSearchParams|location\.(?:search|href)\s*=/);
  for (const prefix of ['frontend/components', 'frontend/src/components/components', 'frontend/components/components']) {
    assert.equal(fs.readFileSync(path.join(root, prefix, 'LoginModal.jsx'), 'utf8'), source);
  }
});
