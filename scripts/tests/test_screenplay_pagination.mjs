import fs from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';
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

const helper=fs.readFileSync('frontend/utils/screenplayPagination.js','utf8');
const {paginateScreenplayBlocks,estimateScreenplayBlockLines}=await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'));
const fixture=Array.from({length:180},(_,i)=>({id:String(i),type:['Scene Heading','Action','Character','Parenthetical','Dialogue','Transition'][i%6],text:'X'.repeat(1+(i*67)%450)}));
function componentPages(name,ast){
  const source=fs.readFileSync(`frontend/src/components/${name}.jsx`,'utf8');
  const pages = sourceDeclaration(source, 'pages', init =>
    init?.type === 'CallExpression' && init.callee.type === 'MemberExpression' &&
    init.callee.object.type === 'CallExpression' && init.callee.object.callee.name === 'paginateScreenplayBlocks');
  return new Function('ast','paginateScreenplayBlocks',pages+'\nreturn pages;')(ast,paginateScreenplayBlocks);
}
function tabFunctions(ast){
  const source=fs.readFileSync('frontend/src/components/ScreenwritingTab.jsx','utf8');
  const total = sourceDeclaration(source, 'calculateTotalPages');
  const page = sourceDeclaration(source, 'getPageBlocks');
  return new Function('ast','paginateScreenplayBlocks',total+page+'\nreturn {count:calculateTotalPages(),page:getPageBlocks};')(ast,paginateScreenplayBlocks);
}
test('actual editor/viewer/count/proof ranges agree for mixed screenplay elements',()=>{
  const editor=componentPages('ScreenplayEditor',fixture),viewer=componentPages('ScreenplayViewer',fixture),tab=tabFunctions(fixture);
  assert.deepEqual(viewer,editor);
  assert.equal(tab.count,editor.length);
  let index=0;
  editor.forEach((blocks,page)=>{
    const span=tab.page(page+1);
    assert.equal(span.startIndex,index);
    assert.deepEqual(span.blocks,blocks);
    index+=blocks.length;
    assert.equal(span.endIndex,index);
  });
  assert.equal(index,fixture.length);
});
test('pagination keeps every block exactly once, handles empty input and exposes oversized blocks',()=>{
  assert.deepEqual(paginateScreenplayBlocks([]),[]);
  const oversized={id:'long',type:'Action',text:'X'.repeat(6000)};
  const ast=[...fixture.slice(0,7),oversized,...fixture.slice(7)];
  const pages=paginateScreenplayBlocks(ast);
  assert.deepEqual(pages.flatMap(p=>p.blocks),ast);
  assert.equal(pages.filter(p=>p.estimatedLines>54).length,1);
  assert.ok(estimateScreenplayBlockLines(oversized)>54);
});
