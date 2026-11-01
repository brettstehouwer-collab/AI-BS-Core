const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const html = fs.readFileSync(path.resolve(__dirname, '../../October7_VocalStudio_DAW/source/VOICECOACH PROGRAM.html'), 'utf8');
function declaration(name) {
  const start = html.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `Missing function ${name}`);
  const end = html.indexOf('\n}', start);
  assert.ok(end > start);
  return html.slice(start, end + 2);
}
function callback(button) {
  const start = html.indexOf(`${button}.addEventListener("click",`);
  assert.ok(start >= 0);
  const end = html.indexOf('\n});', start);
  return html.slice(start, end + 4);
}
function evaluate(code, bindings = {}) {
  const context = vm.createContext(bindings);
  vm.runInContext(code, context, {timeout: 1000});
  return context;
}
test('all embedded JavaScript parses without running the page', () => {
  for (const script of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)) {
    if (script[1].trim()) new vm.Script(script[1]);
  }
});
test('stored cues recover from invalid JSON, storage errors and invalid shapes without deleting saved data', () => {
  const context = evaluate(declaration('loadSavedBlueprint'));
  const fallback = [{time: 0, section: 'Verse', breath: false, text: 'example'}];
  for (const raw of ['{broken', '{}', '[{"time":-1,"section":"x","text":"x"}]', '[{"time":0,"section":{},"text":"x"}]']) {
    const result = context.loadSavedBlueprint({getItem: () => raw}, fallback);
    assert.equal(JSON.stringify(result), JSON.stringify(fallback));
    result[0].text = 'changed';
    assert.equal(fallback[0].text, 'example');
  }
  assert.equal(context.loadSavedBlueprint({getItem: () => {throw new Error('denied');}}, fallback)[0].text, 'example');
  const saved = [{time: 3, section: 'custom', breath: true, text: '<b>literal</b>'}];
  assert.equal(JSON.stringify(context.loadSavedBlueprint({getItem: () => JSON.stringify(saved)}, fallback)), JSON.stringify(saved));
});
test('prompter treats user cue text and section names as text', () => {
  const created = [];
  const container = () => ({innerHTML: '', children: [], appendChild(child) {this.children.push(child);}});
  const bindings = {
    SONG_BLUEPRINT: [{time: 3, section: '<img src=x onerror=alert(1)>', breath: true, text: '<script>bad()</script>&'}],
    document: {createElement: () => {const node = container(); created.push(node); return node;}},
    prompterContainer: container(), sectionPills: container(), seekToTime() {},
  };
  evaluate(declaration('escapeCueHTML') + '\n' + declaration('initPrompter') + '\ninitPrompter();', bindings);
  const rendered = created.map(node => node.innerHTML).join('\n');
  assert.ok(!rendered.includes('<img'));
  assert.ok(!rendered.includes('<script>'));
  assert.ok(rendered.includes('&lt;script&gt;'));
  assert.ok(rendered.includes('&amp;'));
});
test('cue editor escapes quoted section and lyric attribute values', () => {
  let open;
  const rows = [];
  evaluate(declaration('escapeCueHTML') + '\n' + callback('btnEditCues'), {
    btnEditCues: {addEventListener: (_event, fn) => {open = fn;}},
    SONG_BLUEPRINT: [{time: 1, section: '" onfocus="bad()', text: '<img src=x>&"', breath: true}],
    cuesEditorList: {innerHTML: '', appendChild: row => rows.push(row)},
    modalCues: {style: {}}, document: {createElement: () => ({style: {}})},
  });
  open();
  assert.ok(rows[0].innerHTML.includes('&quot; onfocus=&quot;bad()'));
  assert.ok(!rows[0].innerHTML.includes('value="" onfocus='));
  assert.ok(rows[0].innerHTML.includes('&lt;img'));
});
test('comping renders saved cue and take labels without executable markup', () => {
  const container = {innerHTML: '', querySelectorAll: () => []};
  evaluate(declaration('escapeCueHTML') + '\n' + declaration('renderCompingSections') + '\nrenderCompingSections();', {
    document: {getElementById: id => id === 'comping-sections-grid' ? container : null},
    SONG_BLUEPRINT: [{time: 0, section: '\"><img src=x onerror=bad()>'}],
    takes: [{name: '<script>bad()</script>', metrics: {overall: '<img src=x>'}}],
    playbackDuration: 10, compSelections: {},
  });
  assert.ok(!container.innerHTML.includes('<img'));
  assert.ok(!container.innerHTML.includes('<script>'));
  assert.ok(container.innerHTML.includes('&lt;img'));
});
test('offline master rendering connects every active vocal through its bus to the destination', async () => {
  let render;
  let context;
  const vocal = {name: 'vocal'};
  const nodes = [];
  class GraphNode {
    constructor() {this.edges = []; for (const k of ['gain','frequency','Q','threshold','ratio','pan']) this[k] = {value: 0}; nodes.push(this);}
    connect(node) {this.edges.push(node);}
    start() {}
  }
  class OfflineContext {
    constructor() {context = this; this.destination = new GraphNode();}
    createBufferSource() {return new GraphNode();}
    createGain() {return new GraphNode();}
    createBiquadFilter() {return new GraphNode();}
    createDynamicsCompressor() {return new GraphNode();}
    createStereoPanner() {return new GraphNode();}
    async startRendering() {
      const source = nodes.find(node => node.buffer === vocal);
      const visited = new Set();
      function reaches(node, target) {if (node === target) return true; if (visited.has(node)) return false; visited.add(node); return node.edges.some(next => reaches(next, target));}
      assert.ok(source && reaches(source, this.destination), 'Vocal bus is disconnected; exported mix omits vocals');
      return {length: 1};
    }
  }
  evaluate(callback('btnExportMix'), {
    btnExportMix: {addEventListener: (_event, fn) => {render = fn;}},
    backingAudioBuffer: {sampleRate: 48000}, playbackDuration: 1,
    OfflineAudioContext: OfflineContext,
    document: {getElementById: () => ({checked: false, value: '0'})},
    TRACKS: [{buffer: vocal, muted: false, vol: 0.8, pan: -0.5}],
    showToast() {}, bufferToWave() {}, downloadBlob() {}, alert() {},
  });
  await render();
  assert.ok(context);
});
test('heartbeat failure has a bounded timeout and reports unavailable instead of a fabricated fallback', async () => {
  const badge = {style: {}};
  const timers = [];
  const script = declaration('pollAiHeartbeat').replace('function ', 'async function ');
  const context = evaluate('let aiPollBackoffSec = 5;\n' + script, {
    fetch: async () => {throw new Error('offline');},
    AbortController,
    setTimeout: (_fn, delay) => {timers.push(delay); return timers.length;},
    clearTimeout() {},
    document: {getElementById: () => badge},
  });
  await context.pollAiHeartbeat();
  assert.match(badge.innerText, /unavailable/i);
  assert.ok(timers.includes(5000), 'Request must be cancellable after five seconds');
  assert.ok(timers.every(delay => delay > 0 && delay <= 60000));
});
