// Controlled browser fixture server derived from the retained v23/v24 server.
const fs = require('node:fs'), path = require('node:path'), http = require('node:http'), crypto = require('node:crypto');
const { createRequire } = require('node:module');
const localRequire = createRequire('C:/AI-BS/frontend/package.json'), esbuild = localRequire('esbuild');
const checkpoint = process.argv[2], phase = process.argv[3], fixtureArg = process.argv[4];
if (!checkpoint || !/^C:\\AI-BS\\backups\\coding_actor_scope_\d{8}T\d{6,}Z$/.test(checkpoint) || !fs.statSync(checkpoint).isDirectory() || !/^(red|green|strict_green|regression_review|regression_history)$/.test(phase)) throw Error('Fixed fresh fixture evidence required');
const ownFixture = path.join(__dirname, 'coding_actor_scope_fixture.jsx');
const oldRoot = 'C:/Users/footb/Documents/Codex/2026-10-22/c-ai-bs/work/';
const fixtures = { actor: ownFixture, strict: path.join(__dirname, 'coding_actor_scope_strict_fixture.jsx'), review: oldRoot + 'coding_review_scope_fixture.jsx', history: oldRoot + 'coding_history_scope_fixture.jsx' };
const fixture = fixtures[fixtureArg || 'actor'];
if (!fixture) throw Error('Unknown trusted fixture');
const reportPath = path.join(checkpoint, phase + '.json'); if (fs.existsSync(reportPath)) throw Error('Preserve previous report');
const reportRoute = '/report/' + crypto.randomUUID();
const store = `import {useSyncExternalStore} from 'react';
let state={BACKEND_URL:'http://fixture-a.invalid',currentUser:{uid:'actor-A'}};const listeners=new Set();
const getState=()=>({...state,BACKEND_URL:window.__fixtureBackend||state.BACKEND_URL});
const subscribe=fn=>{listeners.add(fn);return()=>listeners.delete(fn)};
window.__fixtureSetState=patch=>{const previous=getState();state={...state,...patch};if('BACKEND_URL'in patch)window.__fixtureBackend=patch.BACKEND_URL;const next=getState();listeners.forEach(fn=>fn(next,previous));};
export const useAppStore=Object.assign(selector=>useSyncExternalStore(subscribe,()=>selector(getState()),()=>selector(getState())),{getState,subscribe});`;
(async () => {
  const built = await esbuild.build({ entryPoints: [fixture], bundle: true, write: false, platform: 'browser', format: 'esm', target: 'es2022', jsx: 'automatic',
    nodePaths: ['C:/AI-BS/frontend/node_modules'], define: { __REPORT_URL__: JSON.stringify(reportRoute) },
    plugins: [{ name: 'controlled-store-and-installed-react', setup(build) {
      build.onResolve({ filter: /^react(?:-dom)?(?:\/.*)?$/ }, args => ({ path: localRequire.resolve(args.path) }));
      build.onResolve({ filter: /^\.\/useAppStore$/ }, () => ({ path: 'controlled-store', namespace: 'fixture' }));
      build.onLoad({ filter: /.*/, namespace: 'fixture' }, () => ({ contents: store, loader: 'js' }));
      build.onResolve({ filter: /^\/src\/utils\/chatHttpResponse\.js$/ }, () => ({ path: 'C:/AI-BS/frontend/src/utils/chatHttpResponse.js' }));
    } }] });
  const js = built.outputFiles[0].contents; fs.writeFileSync(path.join(checkpoint, phase + '.bundle.js'), js, { flag: 'wx' });
  let saved = false;
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'"); res.setHeader('Cache-Control', 'no-store');
    if (req.method === 'GET' && req.url === '/') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end('<!doctype html><title>AI-BS synthetic actor scope verification</title><h1>Controlled React actor scope fixture</h1><p>No real accounts, APIs, models or VM activity.</p><h2 id="status">Running</h2><pre id="results"></pre><div id="component"></div><pre id="test-report" hidden></pre><script type="module" src="/fixture.js"></script>'); }
    else if (req.method === 'GET' && req.url === '/fixture.js') { res.setHeader('Content-Type', 'text/javascript'); res.end(js); }
    else if (req.method === 'POST' && req.url === reportRoute && !saved) {
      let count = 0; const chunks = []; req.on('data', chunk => { count += chunk.length; if (count > 65536) req.destroy(); else chunks.push(chunk); });
      req.on('end', () => { try { const value = JSON.parse(Buffer.concat(chunks)); if (!Array.isArray(value.results) || value.realBackendRequests !== 0 || value.modelRequests !== 0 || value.vmOperations !== 0) throw Error('Unexpected report'); fs.writeFileSync(reportPath, JSON.stringify(value, null, 2), { flag: 'wx' }); saved = true; res.end('saved'); console.log(JSON.stringify({ report: reportPath, passed: value.results.filter(row => row.passed).length, total: value.results.length, failures: value.results.filter(row => !row.passed) })); } catch (error) { res.statusCode = 400; res.end('Invalid report'); console.error(error.message); } });
    } else { res.statusCode = 404; res.end('Not found'); }
  });
  server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ url: 'http://127.0.0.1:' + server.address().port + '/', pid: process.pid, phase })));
  setTimeout(() => server.close(), 300000).unref();
})();
