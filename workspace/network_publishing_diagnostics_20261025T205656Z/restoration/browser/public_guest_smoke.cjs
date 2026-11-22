// Owner-authorized public-site smoke. Fresh guest contexts; no user actions.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const entry=process.argv[2],phase=process.argv[3]||'public';
assert(entry&&/^[a-z0-9_-]+$/.test(phase),'Exact public entry and fresh phase required');
const origin=new URL(entry);
assert.equal(origin.protocol,'https:');
assert.equal(origin.hostname,'stehouwer-publishing.com');
assert.equal(origin.pathname,'/');
assert(!origin.username&&!origin.password&&!origin.search&&!origin.hash);
const out=__dirname;
assert(!fs.existsSync(path.join(out,`${phase}_metrics.json`)),'Retain earlier evidence; use a new phase label');
const privatePattern=/(?:^|\/)(?:analytics\.js|security-shield\.js|ledger(?:\.html)?|invoice(?:\.[^/]+)?|indexnow_key\.txt|stehouwer_aibs_indexing_key_2026\.txt|\.env(?:\.[^/]*)?)(?:$|\/)/i;
const sanitize=message=>String(message).slice(0,600).replace(/https?:\/\/[^\s)]+/g,'[URL omitted]').replace(/Bearer\s+\S+/gi,'Bearer [redacted]').replace(/\b(?:eyJ|sk-|gh[pousr]_)[A-Za-z0-9_.-]{16,}/g,'[redacted]');
const safeTarget=value=>{try{const url=new URL(value);return {origin:url.origin,path:url.pathname};}catch{return {origin:'[invalid]',path:'[invalid]'};}};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const rows=[];
 try{
  for(const width of [390,1440]){
   const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
   const requests={total:0,blocked_non_read:0,private_or_tracking_attempts:0,expected_cf_beacon_blocks:0,external_reads:0,failed_reads:[],http_errors:[],assets:[]};
   await context.route('**/*',async route=>{
    const request=route.request(),target=safeTarget(request.url());requests.total++;
    // Cloudflare injects this edge telemetry script independently of the staged
    // source. Block it before load and classify it separately from app failures.
    if(target.origin==='https://static.cloudflareinsights.com'){
     requests.expected_cf_beacon_blocks++;await route.abort('blockedbyclient');return;
    }
    if(!['GET','HEAD'].includes(request.method())){requests.blocked_non_read++;await route.abort('blockedbyclient');return;}
    if(privatePattern.test(target.path)){requests.private_or_tracking_attempts++;await route.abort('blockedbyclient');return;}
    if(target.origin!==origin.origin)requests.external_reads++;
    await route.continue();
   });
   const page=await context.newPage(),errors=[],dialogs=[];
   let consoleErrors=0;
   page.on('pageerror',error=>errors.push({name:error.name,message:sanitize(error.message)}));
   page.on('console',message=>{if(message.type()==='error')consoleErrors++;});
   page.on('dialog',async dialog=>{dialogs.push(dialog.type());await dialog.dismiss();});
   page.on('requestfailed',request=>{const target=safeTarget(request.url());if(target.origin==='https://static.cloudflareinsights.com')return;if(['GET','HEAD'].includes(request.method()))requests.failed_reads.push({...target,errorType:sanitize(request.failure()?.errorText||'request failed')});});
   page.on('response',response=>{
    const request=response.request();if(!['GET','HEAD'].includes(request.method()))return;
    const target=safeTarget(response.url());
    if(response.status()>=400)requests.http_errors.push({...target,status:response.status()});
    if(target.origin===origin.origin&&/\/assets\/[^/]+\.(?:js|css)$/.test(target.path))requests.assets.push({path:target.path,status:response.status(),kind:target.path.endsWith('.css')?'css':'js'});
   });
   const row={actor:'/root/asset_reconciliation',phase,width,utc:new Date().toISOString(),timezone:'UTC',confidence:'OBSERVED',target:origin.origin,method:'Fresh Chrome guest context, entry navigation only; GET/HEAD guard; no forms or clicks',scope:'Public homepage smoke; not authenticated publishing, APIs, media playback or physical-device acceptance'};
   try{
    const response=await page.goto(entry,{waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForFunction(()=>document.querySelector('#root')?.children.length>0&&(document.body.innerText||'').trim().length>=100,null,{timeout:30000});
    await page.waitForTimeout(1500);
    const metrics=await page.evaluate(()=>({title:document.title,body_characters:(document.body.innerText||'').trim().length,root_children:document.querySelector('#root')?.children.length||0,body_width:document.body.scrollWidth,viewport_width:innerWidth,branding:/Stehouwer/i.test(document.title+' '+(document.body.innerText||'')),fatal_error_shell:/something went wrong|application error|uncaught (?:reference|type)error/i.test(document.body.innerText||''),private_script_elements:[...document.scripts].filter(script=>/analytics\.js|security-shield\.js/i.test(script.src)).length}));
    Object.assign(row,{http_status:response?.status(),final_origin:new URL(page.url()).origin,...metrics,uncaught_page_errors:errors,console_error_count:consoleErrors,dialogs,requests});
    await page.screenshot({path:path.join(out,`${phase}_${width}.png`),fullPage:false});
    assert.equal(response?.status(),200);
    assert.equal(new URL(page.url()).origin,origin.origin);
    assert(metrics.branding&&metrics.body_characters>=100&&metrics.root_children>0,'Expected publishing homepage missing');
    assert.equal(metrics.fatal_error_shell,false);
    assert.equal(errors.length,0,'Uncaught page errors');
    assert.equal(requests.private_or_tracking_attempts,0,'Private/tracking resource requested');
    assert.equal(metrics.private_script_elements,0,'Tracking script element retained');
    assert(requests.assets.some(item=>item.path==='/assets/index-NQ4u1ogD.js'&&item.status===200),'Main JS did not load');
    assert(requests.assets.some(item=>item.path==='/assets/index-DiVaW3ll.css'&&item.status===200),'Main CSS did not load');
    row.status='pass';
   }catch(error){Object.assign(row,{status:'failed',failure_type:error.name,failure:sanitize(error.message),uncaught_page_errors:errors,console_error_count:consoleErrors,dialogs,requests});}
   rows.push(row);
   fs.writeFileSync(path.join(out,`${phase}_metrics.json`),JSON.stringify(rows,null,2));
   await context.close();
  }
 }finally{await browser.close();}
 console.log(JSON.stringify({phase,viewports:rows.map(row=>({width:row.width,status:row.status,errors:row.uncaught_page_errors?.length,private_requests:row.requests.private_or_tracking_attempts,http_errors:row.requests.http_errors,body_width:row.body_width})),scope:'Public guest homepage only; no forms/actions'}));
 if(!rows.every(row=>row.status==='pass'))process.exitCode=1;
})().catch(error=>{fs.writeFileSync(path.join(out,`${phase}_fixture_failure.json`),JSON.stringify({name:error.name,message:sanitize(error.message)}));process.exitCode=1;});
