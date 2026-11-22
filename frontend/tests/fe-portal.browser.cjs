// Offline component regression: no business backend, credentials or providers are used.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const esbuild = require('../node_modules/esbuild');
const {chromium} = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const sourceRoot = path.resolve(__dirname, '..');
  const component = path.join(sourceRoot, 'src/components/FEExpressPinPortal.jsx').replaceAll('\\', '/');
  const bundle = await esbuild.build({
    stdin: {contents: `import React from 'react';import{createRoot}from'react-dom/client';import Portal from ${JSON.stringify(component)};
      function Fixture(){const[open,setOpen]=React.useState(true);const[base,setBase]=React.useState('https://aibs-test.invalid');React.useEffect(()=>{window.__setBackend=setBase},[]);return open?<Portal backendUrl={base} onExit={()=>setOpen(false)}/>:<h1>Main AI-BS sign-in</h1>};
      createRoot(document.getElementById('root')).render(<Fixture/>);`, resolveDir: sourceRoot, loader: 'jsx'},
    bundle: true, write: false, format: 'iife', logLevel: 'silent', jsx: 'automatic', metafile:true,
    alias:{react:path.dirname(require.resolve('react',{paths:[sourceRoot]})),'react-dom':path.dirname(require.resolve('react-dom/package.json',{paths:[sourceRoot]}))},
    plugins: [{name: 'synthetic-dispatcher', setup(build) {
      build.onResolve({filter: /^\/src\/components\/FEExpressDispatcher\.jsx$/}, () => ({path:'dispatcher',namespace:'fixture'}));
      build.onLoad({filter: /.*/,namespace:'fixture'}, () => ({contents: `import React from 'react';export default function Dispatcher({request}){React.useEffect(()=>{window.__portalRequest=request;return()=>{delete window.__portalRequest}},[request]);return <h2>FE synthetic dispatcher</h2>}`,loader:'jsx',resolveDir:sourceRoot}));
    }}]
  });
  const script = bundle.outputFiles[0].text.replaceAll('</script', '<\\/script');
  const html = `<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0"><div id="root"></div><script>${script}</script></body></html>`;
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const results=[];
  const failures=[];
  try {
    for (const width of [1440,390]) {
      const context = await browser.newContext({viewport:{width,height:width===390?500:740}});
      const requests=[];
      let loginLifetime=3600, sessionStatus=200, logoutFails=false;
      let delayLogin=false, delayLogout=false, pendingLogin=null, pendingLogout=null, pendingSession=null;
      const fakeToken='wp1.synthetic_component_test';
      await context.route('**/*', async route => {
        const request=route.request(), url=new URL(request.url());
        if (!['https://aibs-test.invalid','https://api-two.aibs-test.invalid'].includes(url.origin)) throw new Error('Unexpected external request in offline fixture');
        if (url.pathname==='/fixture') return route.fulfill({contentType:'text/html',body:html});
        requests.push({path:url.pathname,method:request.method(),authorization:request.headers().authorization||''});
        const json=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
        if (url.pathname==='/api/website-access/login') {
          assert.deepEqual(request.postDataJSON(),{phone:'2025550199',pin:'8642'});
          if(delayLogin) await new Promise(resolve=>{pendingLogin={release:resolve}});
          return json({access_token:fakeToken,scope:'website_pages',expires_in:loginLifetime});
        }
        assert.equal(request.headers().authorization,'Bearer '+fakeToken);
        if (url.pathname==='/api/website-access/logout') {
          if(delayLogout) await new Promise(resolve=>{pendingLogout={release:resolve}});
          if(logoutFails) return route.abort('failed');
          return json({ok:true});
        }
        if (url.pathname==='/api/website-access/session') {
          if(url.searchParams.has('late')) { await new Promise(resolve=>{pendingSession={release:resolve}}); return json({ok:false},401); }
          return json({ok:sessionStatus===200},sessionStatus);
        }
        if(url.pathname==='/api/v1/fe-express/status') return json({ok:true});
        if(url.pathname==='/api/v1/fe-express/redirect') return route.fulfill({status:302,headers:{Location:'/api/executive/run'}});
        throw new Error('Unexpected API path');
      });
      const page=await context.newPage();
      page.setDefaultTimeout(5000);
      page.on('pageerror',error=>failures.push(error.message));
      async function open() {
        sessionStatus=200;logoutFails=false;
        await page.goto('https://aibs-test.invalid/fixture',{waitUntil:'load'});
        if(process.env.PORTAL_BROWSER_DIAGNOSTIC==='1') {
          console.log(JSON.stringify({diagnostic:true,body:await page.locator('body').innerText(),failures,reactInputs:Object.keys(bundle.metafile.inputs).filter(p=>/react[\\/]/.test(p))}));
          return;
        }
        await page.getByRole('heading',{name:'Devin’s FE Express'}).waitFor();
      }
      async function enterLogin() {
        await page.getByLabel('Phone number',{exact:true}).fill('2025550199');
        await page.getByLabel('Four-digit PIN',{exact:true}).fill('8642');
        await page.getByRole('button',{name:'Sign in with phone + PIN',exact:true}).click();
      }
      async function login() {
        await enterLogin();
        await page.getByRole('heading',{name:'FE synthetic dispatcher'}).waitFor();
      }
      async function waitPending(getPending) {
        for(let n=0;n<100&&!getPending();n++) await new Promise(resolve=>setTimeout(resolve,10));
        assert(getPending(),'Expected held synthetic request');
      }
      const back=()=>page.getByRole('button',{name:'Back to AI-BS / administrator sign-in',exact:true});
      await open();
      if(process.env.PORTAL_BROWSER_DIAGNOSTIC==='1') return;
      await back().click();
      await page.getByRole('heading',{name:'Main AI-BS sign-in'}).waitFor();
      assert.equal(requests.length,0);
      await open();await login();
      assert.equal(await page.evaluate(()=>localStorage.getItem('aibs_cached_user')),null);
      const allowed=await page.evaluate(async()=>{const r=await window.__portalRequest('https://aibs-test.invalid/api/v1/fe-express/status');return r.ok;});
      assert.equal(allowed,true);
      const count=requests.length;
      for(const url of ['https://unrelated.invalid/api/v1/fe-express/status','https://aibs-test.invalid/api/executive/run','https://aibs-test.invalid/api/website-access/login','https://aibs-test.invalid/api/v1/fe-express/../admin']) {
        const error=await page.evaluate(async url=>{try{await window.__portalRequest(url);return null}catch(e){return e.message}},url);
        assert.equal(error,'This session only opens FE Express.');
      }
      assert.equal(requests.length,count);
      const redirectBlocked=await page.evaluate(async()=>{try{await window.__portalRequest('https://aibs-test.invalid/api/v1/fe-express/redirect',{redirect:'follow'});return false}catch{return true}});
      assert.equal(redirectBlocked,true);
      assert.equal(requests.some(r=>r.path==='/api/executive/run'),false);
      await back().click();
      await page.getByRole('heading',{name:'Main AI-BS sign-in'}).waitFor();
      assert(requests.some(r=>r.path==='/api/website-access/logout'));
      await open();await login();
      logoutFails=true;
      await page.getByRole('button',{name:'Lock portal',exact:true}).click();
      await page.getByRole('button',{name:'Sign in with phone + PIN',exact:true}).waitFor();
      assert.equal(await page.evaluate(()=>Boolean(window.__portalRequest)),false);
      await open();
      delayLogin=true;await enterLogin();await waitPending(()=>pendingLogin);
      await back().click();
      await page.getByRole('heading',{name:'Main AI-BS sign-in'}).waitFor();
      pendingLogin.release();delayLogin=false;pendingLogin=null;
      await page.waitForTimeout(100);
      assert.equal(await page.getByRole('heading',{name:'FE synthetic dispatcher'}).count(),0);
      await open();delayLogin=true;await enterLogin();await waitPending(()=>pendingLogin);
      await page.evaluate(()=>window.__setBackend('https://api-two.aibs-test.invalid'));
      await page.waitForFunction(()=>document.querySelector('#website-pin').value==='' && document.querySelector('button[type=submit]').textContent==='Sign in with phone + PIN');
      pendingLogin.release();delayLogin=false;pendingLogin=null;
      await page.waitForTimeout(100);
      assert.equal(await page.getByRole('heading',{name:'FE synthetic dispatcher'}).count(),0);
      await login();
      delayLogout=true;
      await page.getByRole('button',{name:'Lock portal',exact:true}).click();
      await page.getByRole('button',{name:'Sign in with phone + PIN',exact:true}).waitFor();
      assert.equal(await page.evaluate(()=>Boolean(window.__portalRequest)),false);
      await waitPending(()=>pendingLogout);
      pendingLogout.release();delayLogout=false;pendingLogout=null;
      await login();
      await page.evaluate(()=>{window.__stale=window.__portalRequest('https://api-two.aibs-test.invalid/api/website-access/session?late=1')});
      await waitPending(()=>pendingSession);
      await page.getByRole('button',{name:'Lock portal',exact:true}).click();
      await page.getByRole('button',{name:'Sign in with phone + PIN',exact:true}).waitFor();
      await login();
      pendingSession.release();pendingSession=null;
      await page.evaluate(()=>window.__stale);
      await page.getByRole('heading',{name:'FE synthetic dispatcher'}).waitFor();
      sessionStatus=401;
      await page.evaluate(async()=>{await window.__portalRequest('https://api-two.aibs-test.invalid/api/website-access/session')});
      await page.getByText('Your session ended. Enter your phone number and PIN again.').waitFor();
      assert.equal(await page.evaluate(()=>Boolean(window.__portalRequest)),false);
      loginLifetime=.2;sessionStatus=200;
      await login();
      await page.getByRole('button',{name:'Sign in with phone + PIN',exact:true}).waitFor();
      assert.equal(await page.evaluate(()=>Boolean(window.__portalRequest)),false);
      loginLifetime=3600;
      await login();await page.reload();
      await page.getByRole('button',{name:'Sign in with phone + PIN',exact:true}).waitFor();
      const canScroll=await page.locator('main').evaluate(node=>node.scrollHeight>node.clientHeight);
      if(width===390) assert(canScroll,'Mobile portal retains vertical scrolling');
      assert.equal(await page.evaluate(()=>localStorage.getItem('aibs_cached_user')),null);
      results.push({width,preLoginExit:true,postLoginExit:true,existingPhonePinContract:true,originAndPathIsolation:true,redirectBlocked:true,logoutFailureLocksLocally:true,slowLogoutLocksImmediately:true,delayedLoginCannotReopen:true,backendChangeDiscardsLogin:true,stale401CannotLockNewSession:true,revokedSessionLocks:true,expiryLocks:true,reloadRequiresLogin:true,noFirebaseIdentity:true,scrollable:canScroll});
      await context.close();
    }
    assert.deepEqual(failures,[]);
    const report={passed:true,offlineSynthetic:true,providerCalls:0,businessWrites:0,results,errors:failures};
    if(process.argv[2]) fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2),{flag:'wx'});
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1});
