import assert from 'node:assert/strict';
import test from 'node:test';

const { createNovelizerDraftStore } = await import('../../frontend/src/utils/novelizerDrafts.js');
function fixture() {
  const retained = new Map();
  const store = createNovelizerDraftStore({ getItem:k=>retained.get(k), setItem:(k,v)=>retained.set(k,v) });
  return { store, retained };
}
const saved = (prose='Remote saved prose.', revision='a'.repeat(64)) => ({ chapter_number:1,
  chapter_title:'One', prose_content:prose, revision, word_count:3 });

test('draft state is isolated by owner, backend, project and chapter', () => {
  const {store}=fixture();store.edit('origin:userA','ProjectA',1,'One','Retained local text.');
  assert.equal(store.get('origin:userA','ProjectA',1).text,'Retained local text.');
  for (const args of [['origin:userB','ProjectA',1],['origin:userA','ProjectB',1],['other:userA','ProjectA',1],['origin:userA','ProjectA',2]])
    assert.equal(store.get(...args).text,'');
});

test('late draft loads never erase dirty text or silently rebase its revision', () => {
  const {store}=fixture();const ticket=store.stamp();store.edit('scope','P',1,'One','Unsaved work.');
  store.mergeSaved('scope','P',saved(),ticket);
  assert.equal(store.get('scope','P',1).text,'Unsaved work.');
  assert.equal(store.get('scope','P',1).revision,'missing');
});

test('save acknowledgement advances revision while retaining edits made in flight', () => {
  const {store}=fixture();store.edit('scope','P',1,'One','First version.');
  const snapshot=store.beginSave('scope','P',1,'One');store.edit('scope','P',1,'One','A newer local version.');
  store.ack(snapshot,{status:'saved',project_name:'P',chapter_number:1,revision:'b'.repeat(64),request_id:snapshot.request_id});
  assert.equal(store.get('scope','P',1).revision,'b'.repeat(64));
  assert.equal(store.get('scope','P',1).text,'A newer local version.');
  assert.equal(store.get('scope','P',1).dirty,true);
});

test('old load cannot roll back a newly acknowledged revision', () => {
  const {store}=fixture();store.edit('scope','P',1,'One','First version.');const ticket=store.stamp();
  const snapshot=store.beginSave('scope','P',1,'One');
  store.ack(snapshot,{status:'saved',project_name:'P',chapter_number:1,revision:'c'.repeat(64),request_id:snapshot.request_id});
  store.mergeSaved('scope','P',saved(),ticket);
  assert.equal(store.get('scope','P',1).revision,'c'.repeat(64));
  assert.equal(store.get('scope','P',1).text,'First version.');
});

test('missing or wrong save acknowledgements never clear a dirty draft', () => {
  const {store}=fixture();store.edit('scope','P',1,'One','Retain me.');const snapshot=store.beginSave('scope','P',1,'One');
  for (const response of [{status:'saved'},{status:'saved',project_name:'Other',chapter_number:1,revision:'d'.repeat(64)}])
    assert.throws(()=>store.ack(snapshot,response));
  assert.equal(store.get('scope','P',1).dirty,true);
});

test('same failed save reuses request identity but edited inputs receive another', () => {
  const {store}=fixture();store.edit('scope','P',1,'One','Retain me.');
  const first=store.beginSave('scope','P',1,'One');assert.equal(store.beginSave('scope','P',1,'One').request_id,first.request_id);
  store.edit('scope','P',1,'One','Changed me.');assert.notEqual(store.beginSave('scope','P',1,'One').request_id,first.request_id);
});

test('late generation becomes a retained candidate instead of replacing newer prose', () => {
  const {store}=fixture();const snapshot=store.beginConversion('scope','P',1,'One');
  store.edit('scope','P',1,'One','My unsaved text.');store.generated(snapshot,'Generated candidate.',true);
  assert.equal(store.get('scope','P',1).text,'My unsaved text.');
  assert.equal(store.get('scope','P',1).candidate,'Generated candidate.');
});

test('recoverable buffers survive remount and saved-version review retains the local draft', () => {
  const {store,retained}=fixture();store.edit('scope','P',1,'One','Recovery text.');
  const remount=createNovelizerDraftStore({getItem:k=>retained.get(k),setItem:(k,v)=>retained.set(k,v)});
  assert.equal(remount.get('scope','P',1).text,'Recovery text.');
  remount.useSaved('scope','P',1,saved());assert.equal(remount.get('scope','P',1).recovery.at(-1).text,'Recovery text.');
  remount.restore('scope','P',1);assert.equal(remount.get('scope','P',1).text,'Recovery text.');
});

test('a saved recovery buffer accepts fresh server state after a remount', () => {
  const {store,retained}=fixture();store.edit('scope','P',1,'One','Saved text.');
  const snapshot=store.beginSave('scope','P',1,'One');
  store.ack(snapshot,{status:'saved',project_name:'P',chapter_number:1,revision:'a'.repeat(64),request_id:snapshot.request_id});
  const remount=createNovelizerDraftStore({getItem:k=>retained.get(k),setItem:(k,v)=>retained.set(k,v)});
  remount.mergeSaved('scope','P',saved('New remote text.','b'.repeat(64)),remount.stamp());
  assert.equal(remount.get('scope','P',1).text,'New remote text.');
});

test('unverified server draft shapes cannot replace an editor buffer', () => {
  const {store}=fixture();assert.throws(()=>store.mergeSaved('scope','P',{chapter_number:1,prose_content:'bad'},store.stamp()));
});
