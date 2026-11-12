import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {parseFDX,fdxTitlePageFountain} from '../../frontend/utils/FDXParser.js';
import {serializeFDX} from '../../frontend/utils/FDXSerializer.js';
import {fountainToAST,astToFountain} from '../../frontend/utils/FountainAdapter.js';
import {paginateScreenplayBlocks} from '../../frontend/utils/screenplayPagination.js';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
globalThis.DOMParser=require('@xmldom/xmldom').DOMParser;
globalThis.XMLSerializer=require('@xmldom/xmldom').XMLSerializer;
const xml=`<FinalDraft><TitlePage><Content><Paragraph Type="Title"><Text>Literal &lt;title&gt;</Text></Paragraph><Paragraph Type="Author"><Text>Original author</Text></Paragraph></Content></TitlePage><HeaderAndFooter><Header><Paragraph><Text>2.</Text></Paragraph></Header></HeaderAndFooter><Content><Paragraph Type="Action"><Text>First body page.</Text></Paragraph><Paragraph Type="Dialogue" StartsNewPage="Yes"><Text>Next page; punctuation .</Text></Paragraph></Content></FinalDraft>`;
test('FDX parser excludes title/header content and retains real manual break',()=>{
  const ast=parseFDX(xml);assert.deepEqual(ast.map(block=>block.text),['First body page.','Next page; punctuation .']);
  assert.equal(ast[1].startsNewPage,true);assert.equal(paginateScreenplayBlocks(ast).length,2);
  assert.match(fdxTitlePageFountain(xml),/Title: Literal <title>\nAuthor: Original author/);
  const threeActionTitle=xml.replace('<Paragraph Type="Author"><Text>Original author</Text></Paragraph>','<Paragraph Type="Action"><Text>Written by</Text></Paragraph><Paragraph Type="Action"><Text>Original author</Text></Paragraph>');
  assert.match(fdxTitlePageFountain(threeActionTitle),/Notes: Written by\n    Original author/);
  assert.throws(()=>parseFDX('<Other><Content/></Other>'),/Final Draft/);
  assert.throws(()=>parseFDX('<!DOCTYPE FinalDraft><FinalDraft><Content/></FinalDraft>'),/declarations/);
});
test('Fountain conversion retains forced page boundaries while metadata stays outside body',()=>{
  const ast=fountainToAST('Title: Title text\nAuthor: Writer\n\nFirst action.\n\n===\n\nSecond action.');
  assert.deepEqual(ast.map(block=>block.text),['First action.','Second action.']);assert.equal(ast[1].startsNewPage,true);
  const roundtrip=fountainToAST(astToFountain(ast));assert.equal(roundtrip[1].startsNewPage,true);
  assert.equal(paginateScreenplayBlocks(roundtrip).length,2);
  assert.equal(parseFDX(serializeFDX(ast))[1].startsNewPage,true);
});
test('source 85-body-page model retains boundaries even beyond the heuristic line budget',()=>{
  const ast=Array.from({length:85},(_,i)=>({id:String(i),type:'Action',text:'X'.repeat(6000),sourcePage:i+2,startsNewPage:i>0}));
  const pages=paginateScreenplayBlocks(ast);assert.equal(pages.length,85);assert.deepEqual(pages.flatMap(page=>page.blocks),ast);
});
