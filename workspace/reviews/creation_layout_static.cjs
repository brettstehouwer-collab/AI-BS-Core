// Actual component SSR + isolated browser layout. No event handlers or services.
const fs=require('node:fs'), path=require('node:path'), vm=require('node:vm');
const {createRequire}=require('node:module');
const frontendRequire=createRequire(path.resolve('frontend/package.json'));
const React=frontendRequire('react'), {renderToStaticMarkup}=frontendRequire('react-dom/server');
const esbuild=frontendRequire('esbuild');
const {chromium}=require('C:/Users/footb/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const out=path.resolve('backups/creation_suite_audit_20261025_record96');
const phase=process.argv[2]||'after';

function markup(width) {
  const modules={};
  for(const name of ['DocumentsTab','StudioWorkspaceTab','PlaywrightTab']) {
    let source=fs.readFileSync(`frontend/src/components/${name}.jsx`,'utf8');
    if(name==='PlaywrightTab')source=source.replace("useState('screenwriting')","useState('studio')");
    const {code}=esbuild.transformSync(source,{loader:'jsx',format:'cjs',define:{'import.meta.env':'{}'}});
    const module={exports:{}};
    vm.runInNewContext(code,{module,exports:module.exports,console,
      window:{innerWidth:width,location:{search:''}}, localStorage:{getItem:()=>null},
      require:specifier=>{
        if(specifier==='react'||specifier.startsWith('react/'))return frontendRequire(specifier);
        const component=modules[path.basename(specifier).replace(/\.jsx$/,'')];
        return {__esModule:true,default:component||(()=>null),isDriveIntakeOriginal:()=>false,
          AuthenticatedDriveMedia:()=>null,AuthenticatedDriveDownload:()=>null};
      }},{timeout:1000});
    modules[name]=module.exports.default;
  }
  return renderToStaticMarkup(React.createElement(modules.PlaywrightTab,{backendUrl:'http://fixture.invalid'}));
}

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const rows=[];
  try {
    for(const width of [390,768,1440]){
      const context=await browser.newContext({viewport:{width,height:900}});
      let requests=0;await context.route('**/*',route=>{requests++;route.abort();});
      const page=await context.newPage();
      const started=performance.now();const html=markup(width);const ssrMs=performance.now()-started;
      const cssPath='frontend/src/components/StudioLayout.css';
      const css=fs.existsSync(cssPath)?fs.readFileSync(cssPath,'utf8'):'';
      await page.setContent(`<style>*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;font-family:Arial}${css}</style>${html}`);
      const row=await page.evaluate(()=>{
        const heading=[...document.querySelectorAll('span')].find(e=>e.textContent.includes('Document Editor & Creator'));
        return {viewport:innerWidth,document_width:document.documentElement.scrollWidth,
          workspace_width:heading?.parentElement.parentElement.getBoundingClientRect().width,
          explorer_visible:[...document.querySelectorAll('div')].some(e=>e.textContent.trim()==='📂 Explorer'&&e.getBoundingClientRect().width>0)};
      });
      row.ssr_ms=Number(ssrMs.toFixed(2));row.network_requests=requests;
      await page.screenshot({path:path.join(out,`layout_${phase}_${width}.png`)});
      rows.push(row);await context.close();
    }
  }finally{await browser.close();}
  fs.writeFileSync(path.join(out,`layout_${phase}.json`),JSON.stringify(rows,null,2));
  console.log(JSON.stringify(rows));
  if(rows.some(r=>r.document_width>r.viewport||(r.viewport<=900&&(r.workspace_width<r.viewport-4||r.explorer_visible))))process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1;});
