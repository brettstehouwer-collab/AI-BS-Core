const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const parser = require(path.join(root, 'frontend/node_modules/@babel/parser'));
const source = fs.readFileSync(path.join(root, 'frontend/src/components/daw/dawStore.js'), 'utf8');
const tree = parser.parse(source, { sourceType: 'module', plugins: ['jsx'] });
const declaration = tree.program.body.find(node => node.type === 'ExportNamedDeclaration' && node.declaration?.declarations?.[0]?.id?.name === 'useDawStore');
const properties = declaration.declaration.declarations[0].init.arguments[0].body.properties;
function action(name, state, extra = {}) {
  const property = properties.filter(property => property.key.name === name).at(-1);
  const env = { get: () => state, set: update => Object.assign(state, typeof update === 'function' ? update(state) : update),
    console: { warn() {}, error() {}, debug() {} }, ...extra };
  return vm.runInNewContext('(' + source.slice(property.value.start, property.value.end) + ')', env);
}
test('DAW state has one effective implementation per action', () => {
  const keys = properties.map(property => property.key.name);
  assert.equal(new Set(keys).size, keys.length);
});
test('MIDI recording supplies note then step and ignores absent frame data', async () => {
  const calls = []; const input = {};
  const state = { isMidiRecording: false, activeChannelId: 'fixture-channel', currentStep: 5,
    previewNote() {}, addOrToggleMidiNote: (...args) => calls.push(args) };
  const record = action('toggleMidiRecording', state, {
    navigator: { requestMIDIAccess: async () => ({ inputs: new Map([['fixture', input]]) }) }
  });
  await record();
  input.onmidimessage({ data: Uint8Array.from([0x90, 60, 100]) });
  assert.equal(JSON.stringify(calls), JSON.stringify([['fixture-channel', 'C4', 5, 1]]));
  assert.doesNotThrow(() => input.onmidimessage({ data: null }));
  assert.equal(calls.length, 1);
});
test('MIDI duration parameter is retained in the recorded note', () => {
  const state = { channels: [{ id: 'fixture', midiNotes: [] }] };
  action('addOrToggleMidiNote', state)('fixture', 'C4', 3, 1);
  assert.equal(state.channels[0].midiNotes[0].duration, 1);
});
test('an absent solo channel does not mutate tracks or throw', () => {
  const state = { channels: [] };
  assert.doesNotThrow(() => action('toggleChannelSolo', state)('absent-fixture'));
  assert.equal(state.channels.length, 0);
});
test('acknowledged VST load updates both rendered plugin state and parameter selection', async () => {
  const effects = [];
  const state = { fxState: { vst: { enabled: false, pluginId: null, availablePlugins: [] } },
    activeLoadedVstId: null, fetchVstParameters: async id => effects.push(['params', id]) };
  const load = action('loadVstPlugin', state, {
    fetch: async () => ({ ok: true, json: async () => ({ status: 'success', plugin_id: 'fixture-plugin' }) }),
    vstBridgeFX: { setPlugin: async id => effects.push(['bridge', id]) }
  });
  await load('fixture-path');
  assert.equal(state.activeLoadedVstId, 'fixture-plugin');
  assert.equal(state.fxState.vst.pluginId, 'fixture-plugin');
  assert.equal(JSON.stringify(effects), JSON.stringify([['bridge', 'fixture-plugin'], ['params', 'fixture-plugin']]));
});
