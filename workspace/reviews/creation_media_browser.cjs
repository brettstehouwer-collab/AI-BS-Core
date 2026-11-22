// Browser decode/playlist test of actual monitor with a mocked scoped-grant service.
const fs=require('node:fs'),path=require('node:path');
const {createRequire}=require('node:module');
const fromFrontend=createRequire(path.resolve('frontend/package.json'));
const esbuild=fromFrontend('esbuild');
const {chromium}=require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const out=path.resolve('backups/creation_suite_audit_20261025_record96');
(async()=>{
  const entry=`import React from 'react';import{createRoot}from'react-dom/client';import Monitor from './frontend/src/components/VLCPreviewMonitor.jsx';createRoot(document.getElementById('root')).render(<Monitor videoPath="fixture.mp4" backendUrl="http://fixture.invalid" title="Fixture video"/>);`;
  const bundle=await esbuild.build({stdin:{contents:entry,loader:'jsx',resolveDir:process.cwd()},nodePaths:[path.resolve('frontend/node_modules')],bundle:true,write:false,format:'iife',define:{'process.env.NODE_ENV':'"production"'},
    plugins:[{name:'scoped-grant-fixture',setup(build){
      build.onResolve({filter:/AuthenticatedDriveMedia\.jsx$/},()=>({path:'grant',namespace:'fixture'}));
      build.onLoad({filter:/.*/,namespace:'fixture'},()=>({loader:'js',contents:`const session={key:'fixture',isCurrent:()=>true};export const useDriveMediaSession=()=>session;export async function requestDriveMediaUrl(backend,path,action){window.__grants.push({backend,path,action});return backend+'/api/drive/preview?path=fixture.mp4&ticket=fixture-only'}` }));
    }}]});
  const bytes=fs.readFileSync('C:/Users/footb/Downloads/Test Screen Shots/AI_BS_Wan_Core_00004_ (1).mp4');
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
  const requests=[];let page;const errors=[];
  try{
    await context.route('**/*',async route=>{
      const req=route.request(),url=new URL(req.url());requests.push({path:url.pathname,has_grant:url.searchParams.get('ticket')==='fixture-only'});
      if(url.hostname!=='fixture.invalid'||url.pathname!=='/api/drive/preview'||url.searchParams.get('ticket')!=='fixture-only')return route.abort();
      const range=/bytes=(\d+)-(\d*)/.exec(req.headers().range||'');
      const start=range?Number(range[1]):0,end=range&&range[2]?Math.min(bytes.length-1,Number(range[2])):bytes.length-1;
      await route.fulfill({status:range?206:200,headers:{'Content-Type':'video/mp4','Accept-Ranges':'bytes','Access-Control-Allow-Origin':'*',...(range?{'Content-Range':`bytes ${start}-${end}/${bytes.length}`}:{})},body:bytes.subarray(start,end+1)});
    });
    page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    await page.setContent('<div id="root"></div>');
    await page.evaluate(()=>{window.__grants=[];window.__vlc=[];window.open=url=>{window.__vlc.push(url);return null;};});
    await page.addScriptTag({content:bundle.outputFiles[0].text});
    await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2,{},{timeout:15000});
    const media=await page.locator('video').evaluate(async video=>{video.muted=true;await video.play();return {width:video.videoWidth,height:video.videoHeight,duration:video.duration,src:video.currentSrc,readyState:video.readyState};});
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:/In VLC App/}).click();
    const download=await downloadPromise;await download.saveAs(path.join(out,'fixture_playlist.m3u'));
    const state=await page.evaluate(()=>({grants:window.__grants,vlc:window.__vlc}));
    assert.equal(media.width,832);assert.equal(media.height,480);assert.ok(media.duration>3&&media.duration<3.2);
    assert.equal(state.grants.length,1);assert.ok(requests.every(r=>r.path==='/api/drive/preview'&&r.has_grant));
    assert.ok(state.vlc[0].startsWith('vlc://http://fixture.invalid/api/drive/preview'));
    assert.match(fs.readFileSync(path.join(out,'fixture_playlist.m3u'),'utf8'),/ticket=fixture-only/);
    assert.equal(errors.length,0);
    await page.screenshot({path:path.join(out,'media_fixture_390.png')});
    const result={status:'passed',media:{...media,src:'fixture scoped preview URL'},grant_requests:state.grants,media_requests:requests,native_launch:'intercepted protocol request; no VLC process launched',browser_errors:errors};
    fs.writeFileSync(path.join(out,'media_browser.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }catch(error){
    const diagnostic=page?await page.evaluate(()=>({grants:window.__grants,video:[...document.querySelectorAll('video')].map(v=>({src:v.currentSrc,readyState:v.readyState,error:v.error?{code:v.error.code,message:v.error.message}:null})),visible_error:document.body.innerText.slice(-1500)})).catch(()=>null):null;
    fs.writeFileSync(path.join(out,'media_browser_failure.json'),JSON.stringify({error:error.message,requests,errors,diagnostic},null,2));
    console.log(JSON.stringify({requests,errors,diagnostic}));throw error;
  }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
