import assert from 'node:assert/strict';
import { test } from 'node:test';
import { resolveChatMediaUrl, loadChatMedia } from '../../frontend/src/utils/chatMedia.js';

const api='https://api.brettstehouwer.live';
test('phone resolves backend routes and every supported raw service port through public API',()=>{
  assert.equal(resolveChatMediaUrl('/api/comfy/media?filename=cup.png',api),api+'/api/comfy/media?filename=cup.png');
  for(const port of [8188,8189]) assert.equal(resolveChatMediaUrl(`http://127.0.0.1:${port}/view?filename=cup.png`,api),api+'/api/comfy/media?filename=cup.png');
  assert.equal(resolveChatMediaUrl('http://127.0.0.1:8080/api/music/file.wav',api),api+'/api/music/file.wav');
});
test('error JSON, executable URLs and credential-bearing URLs cannot render as media',()=>{
  for(const value of ['{"status":"error"}','javascript:alert(1)','https://user:pass@example.com/a.png','http://127.0.0.1:9999/anything','/../.env']) assert.equal(resolveChatMediaUrl(value,api),null);
});
test('loads protected bytes via app fetch without putting tokens in URLs',async()=>{
  let seen;
  const result=await loadChatMedia('/api/comfy/media?filename=cup.png',api,{fetchImpl:async(url,config)=>{seen={url,config};return new Response(new Blob(['png'],{type:'image/png'}));}});
  assert.equal(seen.url,api+'/api/comfy/media?filename=cup.png');
  assert.equal(seen.config.redirect,'error');
  assert.equal(result.kind,'image');assert.equal(result.blob.type,'image/png');
});
test('video/audio types survive delivery; HTTP failure and JSON error bodies never become blobs',async()=>{
  for(const type of ['video/webm','audio/wav']){
    const result=await loadChatMedia('/api/comfy/media?filename=test',api,{fetchImpl:async()=>new Response('bytes',{headers:{'Content-Type':type}})});
    assert.equal(result.kind,type.split('/')[0]);
  }
  for(const response of [new Response('Unauthorized',{status:401}),new Response('{"status":"error"}',{headers:{'Content-Type':'application/json'}})]){
    await assert.rejects(loadChatMedia('/api/comfy/media?filename=cup.png',api,{fetchImpl:async()=>response}));
  }
});
