// Isolated browser codec check. Reads the supplied MP4; launches no native player.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm');
const {chromium}=require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out=path.resolve('backups/creation_suite_audit_20261025_record96');
(async()=>{
 const bytes=fs.readFileSync('C:/Users/footb/Downloads/Test Screen Shots/AI_BS_Wan_Core_00004_ (1).mp4');
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const context=await browser.newContext({viewport:{width:390,height:844}});
  const requests=[];
  await context.route('**/*',async route=>{
   requests.push(route.request().url());
   if(route.request().url()!=='http://fixture.invalid/fixture.mp4')return route.abort();
   await route.fulfill({status:200,contentType:'video/mp4',body:bytes});
  });
  const page=await context.newPage();await page.setContent('<video muted playsinline controls src="http://fixture.invalid/fixture.mp4"></video>');
  await page.waitForFunction(()=>document.querySelector('video').readyState>=2,null,{timeout:10000});
  const result=await page.locator('video').evaluate(async v=>{await v.play();return {width:v.videoWidth,height:v.videoHeight,duration:v.duration,readyState:v.readyState};});
  assert.equal(result.width,832);assert.equal(result.height,480);assert.ok(result.duration>3&&result.duration<3.2);
  result.network_scope='All browser requests intercepted; no live API or native VLC';
  fs.writeFileSync(path.join(out,'media_codec_browser.json'),JSON.stringify(result,null,2));
  await context.close();console.log(JSON.stringify(result));
 }finally{await browser.close();}
 // Exercise the actual native-handoff function with download/protocol sinks replaced.
 const source=fs.readFileSync('frontend/src/components/VLCPreviewMonitor.jsx','utf8');
 const start=source.indexOf('    const launchInNativeVLC =');
 const end=source.indexOf('    const formatTime',start);
 let playlist,protocol,notice;
 const scope={activeSrc:'https://fixture.invalid/api/drive/preview?path=clip.mp4&ticket=fixture-only',activeItem:{title:'Fixture'},Blob,
  URL:{createObjectURL:blob=>{playlist=blob;return'blob:fixture'},revokeObjectURL:()=>{}},
  document:{createElement:()=>({click:()=>{}})},window:{open:url=>{protocol=url}},
  setVlcLaunchToast:value=>{notice=value},setTimeout:()=>{}};
 vm.runInNewContext(source.slice(start,end)+';launchInNativeVLC();',scope,{timeout:1000});
 const body=await playlist.text();assert.match(body,/ticket=fixture-only/);assert.match(protocol,/^vlc:\/\//);assert.match(notice,/not been confirmed/);
 fs.writeFileSync(path.join(out,'vlc_handoff_fixture.json'),JSON.stringify({playlist:body,protocol,notice,os_launch_performed:false},null,2));
 console.log('Actual VLC handoff function preserved the scoped URL and made no playback-success claim.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
