import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const source=fs.readFileSync('frontend/src/components/VLCPreviewMonitor.jsx','utf8');
const start=source.indexOf('export async function requestVideoMediaUrl(');
const end=source.indexOf('export default function VLCPreviewMonitor',start);
assert.ok(start>=0&&end>start);
const code=source.slice(start,end).replace('export async function','async function')+'\nglobalThis.issue=requestVideoMediaUrl;';
function fixture(reply,ok=true){
 const requests=[];
 const context={URL,window:{location:{href:'https://dashboard.example/'}},fetch:async(url,options)=>{
   requests.push({url,options});return {ok,json:async()=>reply};
 }};
 vm.createContext(context);vm.runInContext(code,context);
 return {context,requests};
}
test('actual client function requests the video-specific grant and preserves abort signal',async()=>{
 const f=fixture({url:'/api/video/stream?path=C%3A%5Cfixture.webm&ticket=fixture-only'});
 const signal=new AbortController().signal;
 const url=await f.context.issue('https://api.example','C:\\fixture.webm',signal);
 assert.equal(f.requests.length,1);assert.equal(f.requests[0].url,'https://api.example/api/video/media-ticket');
 assert.equal(f.requests[0].options.method,'POST');
 assert.deepEqual(JSON.parse(f.requests[0].options.body),{video_path:'C:\\fixture.webm'});
 assert.equal(f.requests[0].options.signal,signal);
 assert.equal(new URL(url).origin,'https://api.example');
 assert.equal(new URL(url).pathname,'/api/video/stream');
});
test('actual client function rejects failed, foreign, credentialed and unscoped responses',async()=>{
 const failures=[
  [{detail:'Fixture denial'},false],
  [{url:'https://foreign.example/api/video/stream?path=x&ticket=fixture-only'},true],
  [{url:'https://name:fixture@api.example/api/video/stream?path=x&ticket=fixture-only'},true],
  [{url:'/api/drive/preview?path=x&ticket=fixture-only'},true],
  [{url:'/api/video/stream?path=x'},true],
 ];
 for(const [reply,ok] of failures){
  const f=fixture(reply,ok);await assert.rejects(f.context.issue('https://api.example','fixture.webm'));
 }
});
