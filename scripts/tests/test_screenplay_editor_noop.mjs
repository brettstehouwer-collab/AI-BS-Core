import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { createRequire } from 'node:module';
const fixtureRequire = createRequire(new URL('../../frontend/package.json', import.meta.url));
const fixtureParser = fixtureRequire('@babel/parser');
const fixtureTraverse = fixtureRequire('@babel/traverse').default;
function sourceDeclaration(source, name, predicate = () => true) {
  let declaration = '';
  const tree = fixtureParser.parse(source, { sourceType: 'module', plugins: ['jsx'] });
  fixtureTraverse(tree, { VariableDeclarator(path) {
    if (path.node.id.type === 'Identifier' && path.node.id.name === name && predicate(path.node.init)) {
      assert.equal(declaration, '', `duplicate fixture declaration: ${name}`);
      declaration = source.slice(path.parent.start, path.parent.end);
    }
  } });
  assert.ok(declaration, `actual source declaration missing: ${name}`);
  return declaration;
}

// Exercise the actual blur/input handler without mounting or a live service.
const source=fs.readFileSync(process.env.AIBS_EDITOR_SOURCE_FIXTURE || 'frontend/src/components/ScreenplayEditor.jsx','utf8');
const handlerDeclaration = sourceDeclaration(source, 'handleInput');

function fixture(block){
  const changes=[]; const timers=[];
  const context={ast:[block],isRevisionMode:false,editorRefs:{current:{}},
    debounceTimerRef:{current:null},onChange:value=>changes.push(value),
    setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},
    pushHistory:()=>{throw Error('Unexpected synchronous history call');}};
  vm.createContext(context);
  vm.runInContext(handlerDeclaration+'\nglobalThis.input=handleInput;',context);
  return {context,changes,timers};
}

test('focusing and blurring unchanged blocks never marks a draft dirty or starts serialization',()=>{
  for(const type of ['Action','Scene Heading','Character','Dialogue','Parenthetical']){
    const block={id:'fixture',type,text:type==='Action'?'INT. title-like literal action':'  Original text  '};
    const f=fixture(block);
    f.context.input('fixture',block.text);
    assert.equal(f.changes.length,0);
    assert.equal(f.timers.length,0);
  }
});

test('a real edit still reaches the parent once and schedules one history record',()=>{
  const f=fixture({id:'fixture',type:'Action',text:'Old text.'});
  f.context.input('fixture','Edited text.');
  assert.equal(f.changes.length,1);
  assert.equal(f.changes[0][0].text,'Edited text.');
  assert.equal(f.changes[0][0].type,'Action');
  assert.equal(f.timers.length,1);
});
