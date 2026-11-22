// Isolated rendering of real suite/document components. No production app or API.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontendRequire = createRequire(path.resolve('frontend/package.json'));
const esbuild = frontendRequire('esbuild');
const { chromium } = require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out = path.resolve('backups/creation_suite_audit_20261025_record96');
const phase = process.argv[2] || 'after';

(async () => {
  const actual = new Set(['PlaywrightTab.jsx','StudioWorkspaceTab.jsx','DocumentsTab.jsx']);
  const entry = `import React from 'react';import {createRoot} from 'react-dom/client';import Studio from './frontend/src/components/PlaywrightTab.jsx';createRoot(document.getElementById('root')).render(<Studio backendUrl="http://fixture.invalid"/>);`;
  const bundle = await esbuild.build({ stdin: { contents: entry, loader: 'jsx', resolveDir: process.cwd() },
    bundle: true, write: false, format: 'iife', nodePaths: [path.resolve('frontend/node_modules')], define: { 'process.env.NODE_ENV': '"production"' },
    plugins: [{ name: 'isolated-studio', setup(build) {
      build.onResolve({ filter: /.*/ }, args => {
        if (args.importer.includes('node_modules') || ['react','react-dom/client'].includes(args.path) || actual.has(path.basename(args.path))) return;
        return { path: args.path, namespace: 'fixture-stub' };
      });
      build.onLoad({ filter: /.*/, namespace: 'fixture-stub' }, () => ({ loader: 'js', contents:
        'export default ()=>null;export const isDriveIntakeOriginal=()=>false;export const createIntakeWorkingCopy=()=>{throw Error("not used")};export const AuthenticatedDriveMedia=()=>null;export const AuthenticatedDriveDownload=()=>null;' }));
    }}] });
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  const rows = [];
  try {
    for (const width of [390,768,1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      await context.route('**/*', route => route.abort());
      const page = await context.newPage();
      const errors=[];page.on('pageerror', error => errors.push(error.message));
      await page.setContent('<style>*{box-sizing:border-box}html,body,#root{margin:0;width:100%;height:100%;font-family:Arial}button{font-size:14px}</style><div id="root"></div>');
      await page.evaluate(() => {
        window.__fixtureRequests=[];
        window.fetch=async (url,options={}) => {
          window.__fixtureRequests.push({url:String(url),method:options.method||'GET'});
          if (options.method && options.method!=='GET') throw Error('Mutation forbidden in layout fixture');
          return new Response(JSON.stringify({ tree:[], files:[], tasks:[] }), {status:200,headers:{'Content-Type':'application/json'}});
        };
      });
      const css='frontend/src/components/StudioLayout.css';
      if(fs.existsSync(css))await page.addStyleTag({content:fs.readFileSync(css,'utf8')});
      const started=Date.now();await page.addScriptTag({content:bundle.outputFiles[0].text});
      await page.getByTitle('Studio Workspace (Documents/PDFs)').click();
      await page.getByText('No document open',{exact:true}).first().waitFor();
      const measured=await page.evaluate(() => {
        const heading=[...document.querySelectorAll('span')].find(e=>e.textContent.includes('Document Editor & Creator'));
        const workspace=heading?.parentElement.parentElement;
        return {document_width:document.documentElement.scrollWidth,viewport:innerWidth,
          workspace_width:workspace?.getBoundingClientRect().width, explorer_visible:[...document.querySelectorAll('div')].some(e=>e.textContent.trim()==='📂 Explorer' && e.getBoundingClientRect().width>0),
          requests:window.__fixtureRequests};
      });
      measured.width=width;measured.fixture_ready_ms=Date.now()-started;measured.errors=errors;
      await page.screenshot({path:path.join(out,`layout_${phase}_${width}.png`)});
      rows.push(measured);await context.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(out,`layout_${phase}.json`),JSON.stringify(rows,null,2));
  console.log(JSON.stringify(rows));
  if(rows.some(r=>r.errors.length || r.document_width>r.viewport || (r.width<=900 && r.workspace_width<r.viewport-4)))process.exitCode=1;
})().catch(error=>{console.error(error.message);process.exitCode=1;});
