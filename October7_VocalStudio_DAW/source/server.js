// Legacy static UI only. Native Studio does not use this bridge.
'use strict';
const http=require('http'), fs=require('fs'), path=require('path');
const PORT=3000;
const MIME={'.html':'text/html; charset=UTF-8','.js':'text/javascript','.css':'text/css',
 '.mp3':'audio/mpeg','.wav':'audio/wav','.flac':'audio/flac','.ogg':'audio/ogg',
 '.m4a':'audio/mp4','.mid':'audio/midi','.png':'image/png','.jpg':'image/jpeg',
 '.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml','.ico':'image/x-icon'};
function inside(root,file){const r=path.relative(root,file);return r!=='..'&&!r.startsWith('..'+path.sep)&&!path.isAbsolute(r);}
function rangeOf(value,size){
 const m=/^bytes=(\d*)-(\d*)$/.exec(value);if(!m||(!m[1]&&!m[2])||!size)return null;
 let start,end;
 if(!m[1]){const n=Number(m[2]);if(!Number.isSafeInteger(n)||n<=0)return null;start=Math.max(0,size-n);end=size-1;}
 else{start=Number(m[1]);end=m[2]?Number(m[2]):size-1;if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>=size||end<start)return null;end=Math.min(end,size-1);}
 return {start,end};
}
const server=http.createServer((req,res)=>{
 function reject(status,message,extra={}){
  if(res.headersSent){if(typeof res.destroy==='function')res.destroy();else res.end();return;}
  res.writeHead(status,{'Content-Type':'text/plain; charset=UTF-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...extra});res.end(message);
 }
 const host=String(req.headers.host||'').toLowerCase();
 if(!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress)||![`localhost:${PORT}`,`127.0.0.1:${PORT}`].includes(host))return reject(403,'Loopback host required');
 if((req.headers.origin&&req.headers.origin!==`http://${host}`)||(req.headers['sec-fetch-site']&&!['same-origin','none'].includes(req.headers['sec-fetch-site'])))return reject(403,'Same-origin requests only');
 if(!['GET','HEAD'].includes(req.method))return reject(405,'Read-only server',{'Allow':'GET, HEAD'});
 let url;
 try{if(req.url.length>8192||/%(?![0-9a-fA-F]{2})/.test(req.url))return reject(400,'Invalid URL');url=decodeURIComponent(req.url.split('?')[0]);}catch{return reject(400,'Invalid URL');}
 if(!url.startsWith('/')||url.startsWith('//')||/[\\:\x00]/.test(url)||url.split('/').includes('..'))return reject(403,'Asset boundary denied');
 if(url==='/favicon.ico'){res.writeHead(204);res.end();return;}
 if(url==='/')url='/VOICECOACH PROGRAM.html';
 const ext=path.extname(url).toLowerCase();
 if(!MIME[ext]||(ext==='.html'&&url!=='/VOICECOACH PROGRAM.html'))return reject(403,'Private file type');
 const root=path.resolve(__dirname),candidate=path.resolve(root,'.'+url);
 if(!inside(root,candidate))return reject(403,'Asset boundary denied');
 fs.realpath(candidate,(error,real)=>{
  if(error)return reject(404,'Asset unavailable');if(!inside(root,real))return reject(403,'Linked asset outside root');
  fs.stat(real,(error,stat)=>{
   if(error||!stat.isFile())return reject(404,'Asset unavailable');let range=null;
   if(req.headers.range){range=rangeOf(req.headers.range,stat.size);if(!range)return reject(416,'Invalid range',{'Content-Range':`bytes */${stat.size}`});}
   const headers={'Content-Type':MIME[ext],'Accept-Ranges':'bytes','Content-Length':range?range.end-range.start+1:stat.size,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin'};
   if(range)headers['Content-Range']=`bytes ${range.start}-${range.end}/${stat.size}`;
   const stream=fs.createReadStream(real,range||{});stream.on('error',()=>reject(500,'Asset read failed'));res.writeHead(range?206:200,headers);
   if(req.method==='HEAD'){stream.destroy();res.end();return;}stream.pipe(res);
  });
 });
});
server.requestTimeout=5000;server.headersTimeout=5000;server.maxHeadersCount=64;
server.on('error',()=>{process.exitCode=1;});
server.listen(PORT,'127.0.0.1',()=>console.log(`October7 legacy static UI: http://127.0.0.1:${PORT}/`));
