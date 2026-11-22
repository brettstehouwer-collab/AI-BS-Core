import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import * as parser from '../../frontend/utils/FDXParser.js';
import * as serializer from '../../frontend/utils/FDXSerializer.js';
const require=createRequire(new URL('../../frontend/package.json',import.meta.url));
globalThis.DOMParser=require('@xmldom/xmldom').DOMParser;
globalThis.XMLSerializer=require('@xmldom/xmldom').XMLSerializer;
const xml=`<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Version="3"><DocumentInfo><Unrecognized Flag="keep">inert metadata</Unrecognized></DocumentInfo><HeaderAndFooter><Header><Paragraph><Text>Header only</Text></Paragraph></Header></HeaderAndFooter><TitlePage><Content><Paragraph Type="Title"><Text Style="Bold">A &amp; B: *literal*</Text></Paragraph><Paragraph Type="Author"><Text>Original Author</Text></Paragraph></Content></TitlePage><Content><Paragraph Type="Action" StartsNewPage="Yes"><Text Style="Bold" RevisionID="5">A &amp; </Text><Text Style="Italic">“quoted” *literal* 😀</Text><ScriptNote Color="Blue"><Paragraph><Text>NOTE ONLY</Text></Paragraph></ScriptNote></Paragraph><DualDialogue><Paragraph Type="Character"><Text>Left</Text></Paragraph><Paragraph Type="Dialogue"><Text>First voice.</Text></Paragraph><Paragraph Type="Character"><Text>Right</Text></Paragraph><Paragraph Type="Dialogue"><Text>Second voice.</Text></Paragraph></DualDialogue></Content></FinalDraft>`;
const read=()=>typeof parser.parseFDXDocument==='function'?parser.parseFDXDocument(xml):{blocks:parser.parseFDX(xml)};
test('body excludes nested notes/title/header while retaining ordered styled runs and note metadata',()=>{
 const doc=read();assert.equal(doc.blocks[0].text,'A & “quoted” *literal* 😀');
 assert.equal(doc.blocks[0].runs[0].attributes.Style,'Bold');assert.equal(doc.blocks[0].runs[0].attributes.RevisionID,'5');
 assert.equal(doc.blocks[0].runs[1].attributes.Style,'Italic');assert.equal(doc.blocks[0].notes[0].text,'NOTE ONLY');
 assert.equal(doc.blocks[0].startsNewPage,true);
});
test('dual speaker order and explicit left/right groups survive alongside title and author metadata',()=>{
 const doc=read();assert.deepEqual(doc.blocks.slice(1).map(block=>block.text),['Left','First voice.','Right','Second voice.']);
 assert.equal(doc.blocks[1].dualGroup,doc.blocks[3].dualGroup);assert.equal(doc.blocks[1].dualSide,'left');assert.equal(doc.blocks[3].dualSide,'right');
 assert.deepEqual(doc.title_page.map(block=>block.text),['A & B: *literal*','Original Author']);
});
test('unchanged rich document serializes exact original XML instead of a plain rebuilt copy',()=>{
 const doc=read();const output=typeof serializer.serializeFDXDocument==='function'?serializer.serializeFDXDocument(doc):serializer.serializeFDX(doc.blocks);
 assert.equal(output,xml);
});
test('a body edit keeps untouched runs/revisions, note/title/unknown nodes and dual dialogue content',()=>{
 const doc=read();assert.equal(typeof parser.updateFDXBlockText,'function');assert.equal(typeof serializer.serializeFDXDocument,'function');
 const blocks=doc.blocks.map((block,index)=>index===2?parser.updateFDXBlockText(block,'First revised voice.'):block);
 const output=serializer.serializeFDXDocument(doc,blocks);const result=parser.parseFDXDocument(output);
 assert.equal(result.blocks[2].text,'First revised voice.');assert.deepEqual(result.blocks[0].runs,doc.blocks[0].runs);
 assert.equal(result.blocks[0].notes[0].text,'NOTE ONLY');assert.match(output,/<Unrecognized Flag="keep">inert metadata<\/Unrecognized>/);
 assert.equal(result.title_page[1].text,'Original Author');assert.equal(result.blocks[4].text,'Second voice.');
});
