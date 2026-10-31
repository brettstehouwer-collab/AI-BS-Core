const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const project = path.resolve(__dirname, '../..');
const sources = process.env.AIBS_AUDIT_SOURCE_ROOT || project;
const parser = require(path.join(project, 'frontend/node_modules/@babel/parser'));
const source = fs.readFileSync(path.join(sources, 'frontend/src/hooks/useUserSessionTelemetry.js'), 'utf8');
const tree = parser.parse(source, { sourceType: 'module' });
const fn = tree.program.body.find(n => n.type === 'ExportNamedDeclaration').declaration;
function mount(currentUser) {
  const effects = [], requests = [], listeners = new Map();
  const saved = new Map([['aibs_session_id', 'fixture-session'], ['aibs_session_start', '1000']]);
  let beacons = 0;
  const hook = vm.runInNewContext('(' + source.slice(fn.start, fn.end) + ')', {
    useEffect: f => effects.push(f), useRef: current => ({ current }),
    getApiBase: () => 'http://fixture.invalid',
    sessionStorage: { getItem: k => saved.get(k) ?? null, setItem: (k,v) => saved.set(k,v) },
    localStorage: { getItem: () => 'forged-owner@example.test' },
    getFriendlyUserName: () => 'Fixture', getFriendlyUserRole: () => 'fixture', getFriendlyUserAvatar: () => '',
    navigator: { userAgent: 'Fixture', sendBeacon: () => { beacons++; } },
    window: { addEventListener: (name,callback) => listeners.set(name,callback), removeEventListener() {} },
    fetch: (url,init) => { requests.push({ url, init }); return Promise.resolve({ ok:true }); },
    setInterval: () => 1, clearInterval() {}, Blob
  });
  hook({ currentUser, enabled: true });
  effects.forEach(effect => effect());
  return { requests, listeners, beacons: () => beacons };
}
test('anonymous session cannot adopt a localStorage or default administrator identity', () => {
  const result = mount(null);
  assert.equal(result.requests.length, 0);
  assert.equal(result.listeners.size, 0);
});
test('recorded session belongs to the current profile and closes once through authenticated fetch', () => {
  const result = mount({ email:'fixture@example.test', displayName:'Fixture' });
  assert.equal(result.requests.length, 1);
  assert.equal(JSON.parse(result.requests[0].init.body).user_email, 'fixture@example.test');
  result.listeners.get('beforeunload')();
  result.listeners.get('pagehide')();
  assert.equal(result.beacons(), 0);
  assert.equal(result.requests.length, 2);
  assert.equal(result.requests[1].init.keepalive, true);
});
