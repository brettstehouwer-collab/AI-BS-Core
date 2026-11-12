import assert from 'node:assert/strict';
import { test } from 'node:test';
import { studioViewport, watchStudioViewport } from '../../frontend/src/utils/studioViewport.js';

test('narrow and large phones, portrait and landscape use compact studio', () => {
  for (const [width,height] of [[360,740],[393,852],[430,932],[844,390],[932,430],[1024,540]]) {
    assert.equal(studioViewport({width,height}).compact,true);
  }
});
test('wide desktop remains desktop and keyboard viewport supplies available height',()=>{
  assert.equal(studioViewport({width:1440,height:900}).compact,false);
  const keyboard=studioViewport({width:393,height:852,visualHeight:361,offsetTop:42});
  assert.equal(keyboard.height,361);assert.equal(keyboard.top,42);
  assert.equal(studioViewport({width:393,height:852,visualHeight:0,offsetTop:-1}).height,852);
});
test('rotation and visual keyboard resize are observed and every listener is removed on unmount',()=>{
  const target=new EventTarget();Object.assign(target,{innerWidth:393,innerHeight:852,visualViewport:new EventTarget()});
  Object.assign(target.visualViewport,{height:852,offsetTop:0});
  const values=[];const cleanup=watchStudioViewport(target,v=>values.push(v));
  target.visualViewport.height=361;target.visualViewport.offsetTop=40;target.visualViewport.dispatchEvent(new Event('resize'));
  assert.equal(values.at(-1).height,361);assert.equal(values.at(-1).top,40);
  target.innerWidth=932;target.innerHeight=430;target.dispatchEvent(new Event('orientationchange'));
  assert.equal(values.at(-1).compact,true);
  cleanup();const count=values.length;
  for(const node of [target,target.visualViewport])for(const event of ['resize','orientationchange','scroll'])node.dispatchEvent(new Event(event));
  assert.equal(values.length,count);
});
