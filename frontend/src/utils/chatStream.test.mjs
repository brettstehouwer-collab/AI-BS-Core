// Source-level tests (node:test). No browser, network or Ollama involved.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { ChatStreamParser, frameTextFor, stripMetadataFrames, parseFrames, META_PREFIX } from './chatStream.js';

const frame = (obj) => `\n${META_PREFIX}${JSON.stringify(obj)}-->\n`;
const RECEIPT = { schema: 'aibs.local_inference.v1', type: 'aibs_cognitive_meta', status: 'running' };

function run(chunks) {
  const p = new ChatStreamParser();
  let text = '';
  const frames = [];
  for (const c of chunks) { const r = p.feed(c); text += r.text; frames.push(...r.frames); }
  const tail = p.finish();
  return { text: text + tail.text, frames, malformed: tail.malformed };
}
const everyChar = (s) => [...s];

test('single frame is removed from prose and returned separately', () => {
  const out = run([`Hello${frame(RECEIPT)}world`]);
  assert.equal(out.text, `Hello\n\nworld`.replace('\n\n', '\n\n'));
  assert.ok(!out.text.includes('AI-BS-METADATA'));
  assert.deepEqual(parseFrames(out.frames), [RECEIPT]);
});

test('repeated frames (start + final receipt) are all isolated', () => {
  const out = run([frame(RECEIPT) + 'answer' + frame({ ...RECEIPT, status: 'completed' })]);
  assert.ok(out.text.includes('answer') && !out.text.includes('AI-BS-METADATA'));
  assert.equal(parseFrames(out.frames).length, 2);
});

test('frames fragmented at every character boundary produce identical output', () => {
  const whole = `> note\n${frame(RECEIPT)}The answer.${frame({ ...RECEIPT, status: 'completed' })}`;
  const a = run([whole]);
  const b = run(everyChar(whole));
  assert.equal(b.text, a.text);
  assert.deepEqual(b.frames, a.frames);
  assert.ok(!b.text.includes('<!--') && !b.text.includes('-->'));
});

test('split prefix and split terminator across chunks', () => {
  const out = run(['abc <!--AI-BS-MET', 'ADATA:{"a":1}-', '-> tail']);
  assert.equal(out.text, 'abc  tail');
  assert.deepEqual(parseFrames(out.frames), [{ a: 1 }]);
});

test('in-flight incomplete frame is never shown, and is discarded as malformed at end', () => {
  const p = new ChatStreamParser();
  const r = p.feed('Answer so far <!--AI-BS-METADATA:{"schema":"aibs.loc');
  assert.equal(r.text, 'Answer so far ');
  assert.equal(r.frames.length, 0);
  const end = p.finish();
  assert.equal(end.text, '');
  assert.equal(end.malformed, 1);
});

test('malformed JSON frame is ignored, not displayed', () => {
  const out = run([`x<!--AI-BS-METADATA:{not json}-->y`]);
  assert.equal(out.text, 'xy');
  assert.deepEqual(parseFrames(out.frames), []);
});

test('model-authored literal text and unrelated comments are preserved', () => {
  const literal = 'Example: &lt;!--AI-BS-METADATA:{"x":1}--> and <!-- my comment --> done';
  const out = run(everyChar(literal));
  assert.equal(out.text, literal);
  assert.equal(out.frames.length, 0);
});

test('held partial prefix at end of stream is released as ordinary text', () => {
  const out = run(['ends with <!--AI-BS-ME']);
  assert.equal(out.text, 'ends with <!--AI-BS-ME');
});

test('oversized unterminated frame body is bounded and discarded', () => {
  const p = new ChatStreamParser();
  p.feed(META_PREFIX);
  for (let i = 0; i < 6; i += 1) p.feed('z'.repeat(70000));
  const r = p.feed('-->visible');
  assert.equal(r.text, 'visible');
  assert.equal(r.frames.length, 0);
  assert.equal(p.finish().malformed, 1);
});

test('stripMetadataFrames cleans legacy stored content, including multiple and unterminated frames', () => {
  const legacy = `${frame(RECEIPT)}body${frame(RECEIPT)}more<!--AI-BS-METADATA:{"cut`;
  assert.equal(stripMetadataFrames(legacy).includes('AI-BS-METADATA'), false);
  assert.ok(stripMetadataFrames(legacy).includes('body') && stripMetadataFrames(legacy).includes('more'));
  assert.equal(stripMetadataFrames('plain text'), 'plain text');
});

// Mirrors the ChatTab/Mobile stream reducer: content = prose only, frames kept separately.
function reduceStream(chunks) {
  const parser = new ChatStreamParser();
  let content = '';
  let frameText = '';
  for (const chunk of chunks) {
    const r = parser.feed(chunk);
    content += r.text;
    if (r.frames.length) frameText += (frameText ? '\n' : '') + frameTextFor(r.frames);
  }
  content += parser.finish().text;
  return { content, frameText, persisted: { role: 'assistant', content }, spoken: content };
}

test('desktop/mobile reducer: displayed, persisted and spoken text never contain metadata', () => {
  const stream = `> Context note\n${frame(RECEIPT)}Because the budget changed.${frame({ ...RECEIPT, status: 'completed', generation_verified: true })}`;
  const r = reduceStream(everyChar(stream));
  for (const surface of [r.content, r.persisted.content, r.spoken]) {
    assert.ok(!surface.includes('AI-BS-METADATA') && !surface.includes('"generation_verified"'));
    assert.ok(surface.includes('Because the budget changed.'));
  }
  assert.ok(r.frameText.includes('"completed"'));   // receipt still available as structured data
});

test('recorded "Why" message from the vault renders with no metadata (replay)', (t) => {
  const path = 'C:/AI-BS/backend/scratch/m22_raw.txt';
  if (!fs.existsSync(path)) return t.skip('recorded fixture not present');
  const raw = fs.readFileSync(path, 'utf8');
  assert.equal((raw.match(/<!--AI-BS-METADATA:/g) || []).length, 2);
  const cleaned = stripMetadataFrames(raw);
  assert.ok(!cleaned.includes('AI-BS-METADATA') && cleaned.includes('The query "Why"'));
});

// Static guards on the actual component sources.
const read = (p) => fs.readFileSync(new URL(p, import.meta.url), 'utf8');
test('ChatTab source uses the stateful parser, excludes current message, speaks clean text', () => {
  const src = read('../../components/ChatTab.jsx');
  assert.ok(src.includes("from '/src/utils/chatStream.js'"));
  assert.ok(src.includes('streamParser.feed(chunk)') && src.includes('streamParser.finish()'));
  assert.ok(!src.includes('assistantMessage += chunk;'));
  assert.ok(src.includes('.filter(m => m !== userMsg)'));
  assert.ok(src.includes('readCognitiveMetadata(frameText)'));
  assert.ok(src.includes('text = stripMetadataFrames(text).trimStart();'));
  assert.equal((src.match(/meta=\{msg\.meta\}/g) || []).length, 2);
});

test('Mobile source uses the stateful parser and no non-global frame strip remains', () => {
  const src = read('../../components/MobileStehouwerChat.jsx');
  assert.ok(src.includes("from '/src/utils/chatStream.js'"));
  assert.ok(src.includes('streamParser.feed(chunk)') && src.includes('streamParser.finish()'));
  assert.ok(!src.includes("text.replace(/<!--AI-BS-METADATA:[\\s\\S]*?-->/, '')"));
  assert.ok(!src.includes('accumulated += chunk;'));
  assert.ok(src.includes('.slice(0, -1).slice(-32)'));
  assert.ok(src.includes('meta={msg.meta}'));
});
