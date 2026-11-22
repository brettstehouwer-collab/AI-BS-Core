// Render actual component handlers with synthetic auth, deferred HTTP and browser recovery.
import assert from 'node:assert/strict';
import { test as nodeTest } from 'node:test';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createNovelizerDraftStore} from '../../frontend/src/utils/novelizerDrafts.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const test=(name,run)=>nodeTest(name,{timeout:3000},run);
const require=createRequire(path.join(root,'frontend/package.json'));const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');const {transformSync}=require('esbuild');
const filename=path.join(root,'frontend/src/components/ScriptToBookNovelizerModal.jsx');
const compiled=transformSync(await readFile(filename,'utf8'),{loader:'jsx',jsx:'automatic',format:'cjs',target:'es2022'}).code;
const response=data=>({ok:true,status:200,json:async()=>data});
const failure=message=>({ok:false,status:503,json:async()=>({detail:{message}})});
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};}
const text=e=>typeof e==='string'||typeof e==='number'?String(e):React.isValidElement(e)?React.Children.toArray(e.props.children).map(text).join(''):'';
const descendants=e=>React.isValidElement(e)?[e,...React.Children.toArray(e.props.children).flatMap(descendants)]:[];

function harness(){
  const slots=[];let cursor=0,dirty=true,tree,effects=[];const calls=[],conversions=[],saves=[],draftLoads=[];
  const storage=new Map();const props={isOpen:true,currentProject:'Project A',activeScript:'INT. EDITOR A - DAY\nFixture A.',backendUrl:'http://fixture',onClose:()=>update({isOpen:false})};
  const auth={currentUser:{uid:'fixture-owner'}};
  const hooks={
    useState(initial){const n=cursor++;if(!slots[n])slots[n]={value:typeof initial==='function'?initial():initial};return[slots[n].value,v=>{const next=typeof v==='function'?v(slots[n].value):v;if(!Object.is(next,slots[n].value)){slots[n].value=next;dirty=true;}}];},
    useRef(value){const n=cursor++;return slots[n]||(slots[n]={current:value});},
    useCallback(fn,deps){const n=cursor++;if(!slots[n]||deps.some((v,i)=>!Object.is(v,slots[n].deps[i])))slots[n]={fn,deps};return slots[n].fn;},
    useEffect(callback,deps){const n=cursor++;if(!slots[n]||deps.some((v,i)=>!Object.is(v,slots[n].deps[i]))){const previous=slots[n];slots[n]={deps};effects.push(()=>{previous?.cleanup?.();slots[n].cleanup=callback();});}}
  };
  async function fetchMock(url,options={}){
    const body=options.body?JSON.parse(options.body):null;calls.push({url,body,options});
    if(url.endsWith('/projects'))return response({projects:[{name:'Project A',scene_count:2},{name:'Project B',scene_count:2}]});
    if(url.includes('/get_drafts/')){const pending=deferred();draftLoads.push({...pending,url});return pending.promise;}
    if(url.endsWith('/group_chapters'))return response({source_project:body.project_name,chapters:[1,2].map(n=>({chapter_number:n,title:`Chapter ${n}`,combined_script:`INT. ${body.project_name} - DAY\nSource ${n}.`,scene_count:1,estimated_words:10,scenes:[]}))});
    if(url.endsWith('/convert_chapter')){const pending=deferred();conversions.push({...pending,body,options});return pending.promise;}
    if(url.endsWith('/save_draft')){const pending=deferred();saves.push({...pending,body,options});return pending.promise;}
    throw new Error('Unexpected request '+url);
  }
  const module={exports:{}};
  const mockedRequire=name=>name==='react'?{...React,...hooks}:name.endsWith('.css')?{}
    :name==='/src/utils/chatAuth.js'?{chatAuthHeaders:async headers=>({...headers,Authorization:'Bearer fixture-owner'})}
    :name==='/src/firebase.js'?{auth}:name==='firebase/auth'?{onAuthStateChanged:(_a,callback)=>{callback(auth.currentUser);return()=>{};}}
    :name==='/src/utils/novelizerDrafts.js'?{createNovelizerDraftStore}:require(name);
  new Function('require','module','exports','fetch','sessionStorage','alert',compiled)(mockedRequire,module,module.exports,fetchMock,
    {getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},()=>{});
  const Component=module.exports.default;
  function render(){let count=0;do{assert.ok(count++<25,'render did not settle');dirty=false;cursor=0;effects=[];tree=Component(props);effects.forEach(effect=>effect());}while(dirty);}
  function update(values){Object.assign(props,values);dirty=true;render();}
  async function flush(){for(let i=0;i<20;i++){await Promise.resolve();if(dirty)render();}}
  function find(type,predicate=()=>true){const value=descendants(tree).find(e=>e.type===type&&predicate(e));assert.ok(value,`Missing ${type}`);return value;}
  render();
  return{calls,conversions,saves,draftLoads,flush,update,markup:()=>renderToStaticMarkup(tree),
    studio(){find('button',e=>text(e).includes('Chapter Prose Studio')).props.onClick();render();},
    select(project){find('select').props.onChange({target:{value:project}});render();},
    edit(prose){find('textarea').props.onChange({target:{value:prose}});render();},
    prose(){return find('textarea').props.value;},
    convert(){return find('button',e=>text(e).includes('Convert Script to Book Prose')||text(e).includes('Novelizing Chapter')).props.onClick();},
    save(){return find('button',e=>text(e).includes('Save Chapter Draft')).props.onClick();},
    next(){find('button',e=>text(e).includes('Next')).props.onClick();render();}
  };
}

test('other selected projects never receive the current editor screenplay',async()=>{
  const h=harness();await h.flush();h.select('Project B');await h.flush();
  const call=h.calls.filter(c=>c.url.endsWith('/group_chapters')).at(-1);
  assert.equal(call.body.project_name,'Project B');assert.equal(call.body.script_content,null);
  assert.ok(call.options.headers.Authorization);
});

test('a late saved-draft load never erases unsaved prose',async()=>{
  const h=harness();await h.flush();h.studio();h.edit('My unsaved prose.');
  h.draftLoads[0].resolve(response({project_name:'Project A',chapters:[{chapter_number:1,chapter_title:'One',prose_content:'Older saved text.',revision:'a'.repeat(64),word_count:3}]}));
  await h.flush();assert.equal(h.prose(),'My unsaved prose.');
});

test('conversion completing after chapter navigation never auto-saves or replaces the new chapter',async()=>{
  const h=harness();await h.flush();h.studio();const pending=h.convert();await h.flush();h.next();h.edit('Chapter two draft.');
  h.conversions[0].resolve(response({status:'success',generation_verified:true,provider:'ollama',model:'fixture',prose:'Generated chapter one.'}));
  await pending;await h.flush();assert.equal(h.prose(),'Chapter two draft.');assert.equal(h.saves.length,0);
});

test('HTTP conversion and save failures remain visible and keep the local draft',async()=>{
  const h=harness();await h.flush();h.studio();h.edit('Retain this draft.');
  const saving=h.save();await h.flush();h.saves[0].resolve(failure('Storage unavailable fixture'));
  await saving;await h.flush();assert.match(h.markup(),/Storage unavailable fixture/);assert.equal(h.prose(),'Retain this draft.');
  const converting=h.convert();await h.flush();h.conversions[0].resolve(failure('Model unavailable fixture'));
  await converting;await h.flush();assert.match(h.markup(),/Model unavailable fixture/);assert.equal(h.prose(),'Retain this draft.');
});

test('saving captures the original project and sends revision plus stable request identity',async()=>{
  const h=harness();await h.flush();h.studio();h.edit('A draft for project A.');const saving=h.save();await h.flush();
  h.select('Project B');await h.flush();assert.equal(h.saves[0].body.project_name,'Project A');
  assert.equal(h.saves[0].body.expected_revision,'missing');assert.match(h.saves[0].body.request_id,/^[a-f0-9]{32}$/);
  h.saves[0].resolve(response({status:'saved',project_name:'Project A',chapter_number:1,revision:'b'.repeat(64),request_id:h.saves[0].body.request_id,word_count:5}));
  await saving;await h.flush();assert.doesNotMatch(h.markup(),/A draft for project A/);
});

test('saved chapter titles survive editing and saving under a newly grouped outline',async()=>{
  const h=harness();await h.flush();
  h.draftLoads[0].resolve(response({project_name:'Project A',chapters:[{chapter_number:1,chapter_title:'An authored chapter title',prose_content:'Saved prose.',revision:'a'.repeat(64),word_count:2}]}));
  await h.flush();h.studio();h.edit('An edited draft.');const pending=h.save();await h.flush();
  assert.equal(h.saves[0].body.chapter_title,'An authored chapter title');
  h.saves[0].resolve(failure('Synthetic save stopped'));await pending;
});

test('typing while generation is pending keeps the draft and retains a separate candidate',async()=>{
  const h=harness();await h.flush();h.studio();const pending=h.convert();await h.flush();h.edit('My newer typing.');
  h.conversions[0].resolve(response({status:'success',generation_verified:true,provider:'ollama',model:'fixture',prose:'A generated candidate.'}));
  await pending;await h.flush();assert.equal(h.prose(),'My newer typing.');assert.match(h.markup(),/candidate is retained separately/);assert.equal(h.saves.length,0);
});

test('closing and reopening retains the unsaved chapter buffer',async()=>{
  const h=harness();await h.flush();h.studio();h.edit('Recovered after closing.');h.update({isOpen:false});h.update({isOpen:true});
  await h.flush();assert.equal(h.prose(),'Recovered after closing.');
});
