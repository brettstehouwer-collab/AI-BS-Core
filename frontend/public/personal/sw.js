/* Public, fingerprinted application assets only. Never cache financial responses. */
const BUILD='__PERSONAL_BUILD__';
const CACHE='aibs-personal-shell-'+BUILD;
const MANIFEST='/personal/asset-manifest.json';
let shell;
const hex=bytes=>[...new Uint8Array(bytes)].map(value=>value.toString(16).padStart(2,'0')).join('');
function validate(value){
  if(value.version!==BUILD||value.entry!=='/personal/index.html'||!Array.isArray(value.assets)||!value.assets.length||value.assets.length>30)throw Error('Invalid personal shell manifest');
  const seen=new Set();
  for(const item of value.assets){
    if(!/^\/(?:personal\/index\.html|js\/[^/?#]+\.js|css\/[^/?#]+\.css)$/.test(item.url)||item.url.includes('..')||seen.has(item.url)||!/^[a-f0-9]{64}$/.test(item.sha256)||!Number.isSafeInteger(item.bytes)||item.bytes<0||item.bytes>16*1024*1024)throw Error('Unsafe personal shell asset');
    seen.add(item.url);
  }
  if(!seen.has(value.entry))throw Error('Missing personal entry');return value;
}
self.addEventListener('install',event=>event.waitUntil((async()=>{
  const response=await fetch(MANIFEST,{credentials:'omit',cache:'no-store',redirect:'error'});
  if(response.status!==200)throw Error('Personal manifest unavailable');
  const manifest=validate(await response.json()),responses=[];
  for(const item of manifest.assets){
    const asset=await fetch(item.url,{credentials:'omit',cache:'no-store',redirect:'error'});
    if(asset.status!==200||asset.type==='opaque')throw Error('Personal shell unavailable');
    const bytes=await asset.clone().arrayBuffer();
    if(bytes.byteLength!==item.bytes||hex(await crypto.subtle.digest('SHA-256',bytes))!==item.sha256)throw Error('Personal shell checksum mismatch');
    responses.push(asset);
  }
  try{
    const cache=await caches.open(CACHE);
    for(let i=0;i<manifest.assets.length;i++)await cache.put(manifest.assets[i].url,responses[i]);
    await cache.put(MANIFEST,new Response(JSON.stringify(manifest),{headers:{'Content-Type':'application/json'}}));shell=manifest;
  }catch(error){await caches.delete(CACHE);throw error;}
})()));
// A new build waits. Never reload, claim clients or delete another build's cache.
self.addEventListener('message',event=>{if(event.data?.type==='ACTIVATE_PERSONAL_UPDATE')self.skipWaiting();});
async function manifest(){
  if(!shell){const response=await(await caches.open(CACHE)).match(MANIFEST);if(!response)throw Error('Personal shell incomplete');shell=validate(await response.json());}
  return shell;
}
self.addEventListener('fetch',event=>{
  const request=event.request,url=new URL(request.url);
  if(request.method!=='GET'||url.origin!==self.location.origin||request.headers.has('Authorization')||request.headers.has('X-Admin-Key')||request.headers.has('X-Api-Key')||url.search)return;
  if(request.mode==='navigate'&&['/personal/','/personal/index.html'].includes(url.pathname)){
    event.respondWith(fetch(request).catch(async()=>{const current=await manifest();const value=await(await caches.open(CACHE)).match(current.entry);if(!value)throw Error('Personal offline entry unavailable');return value;}));return;
  }
  if(!/^\/(?:js\/[^/?#]+\.js|css\/[^/?#]+\.css)$/.test(url.pathname))return;
  event.respondWith((async()=>{const current=await manifest();if(!current.assets.some(item=>item.url===url.pathname))return fetch(request);return(await(await caches.open(CACHE)).match(url.pathname))||fetch(request);})());
});
