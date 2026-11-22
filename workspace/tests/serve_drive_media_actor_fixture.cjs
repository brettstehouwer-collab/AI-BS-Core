const fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const { createRequire } = require('node:module'), localRequire = createRequire('C:/AI-BS/frontend/package.json'), esbuild = localRequire('esbuild');
const checkpoint = process.argv[2], phase = process.argv[3];
if (!/^C:\\AI-BS\\backups\\drive_media_actor_\d{8}T\d{6,}Z$/.test(checkpoint) || !fs.statSync(checkpoint).isDirectory() || !/^(red|red_validated|red_final|guard_red|guard_red_validated|green|green_final|guard_green)$/.test(phase)) throw Error('Fresh controlled checkpoint required');
const source = phase === 'red_final' ? path.join(checkpoint, 'original_1.jsx') : 'C:/AI-BS/frontend/src/components/AuthenticatedDriveMedia.jsx';
const store = `import{useSyncExternalStore}from'react';let state={BACKEND_URL:'http://fixture.invalid',currentUser:{uid:'actor-A'}};const listeners=new Set(),getState=()=>state,subscribe=f=>{listeners.add(f);return()=>listeners.delete(f)};window.__mediaSetState=patch=>{const previous=state;state={...state,...patch};listeners.forEach(f=>f(state,previous))};export const useAppStore=Object.assign(selector=>useSyncExternalStore(subscribe,()=>selector(state),()=>selector(state)),{getState,subscribe});`;
(async () => {
  const built = await esbuild.build({ entryPoints: [path.join(__dirname, 'drive_media_actor_fixture.jsx')], bundle: true, write: false, platform: 'browser', format: 'esm', target: 'es2022', jsx: 'automatic', nodePaths: ['C:/AI-BS/frontend/node_modules'], plugins: [{ name: 'controlled-fixture', setup(build) {
    build.onResolve({ filter: /^react(?:-dom)?(?:\/.*)?$/ }, args => ({ path: localRequire.resolve(args.path) }));
    build.onResolve({ filter: /^\.\/useAppStore$/ }, () => ({ path: 'store', namespace: 'fixture' }));
    build.onResolve({ filter: /^fixture-media-store$/ }, () => ({ path: 'store', namespace: 'fixture' }));
    if (phase === 'red_final') {
      build.onResolve({ filter: /^\.\.\/\.\.\/frontend\/src\/components\/AuthenticatedDriveMedia\.jsx$/ }, () => ({ path: source }));
      build.onResolve({ filter: /^\.\.\/\.\.\/frontend\/src\/components\/AdminSharedDriveTab\.jsx$/ }, () => ({ path: path.join(checkpoint, 'consumer_original_1.jsx') }));
    }
    build.onResolve({ filter: /^\/src\/components\/AuthenticatedDriveMedia\.jsx$/ }, () => ({ path: 'interposer', namespace: 'fixture' }));
    build.onResolve({ filter: /^actual-media-helper$/ }, () => ({ path: source }));
    build.onResolve({ filter: /^\/src\/utils\/driveIntakeDocuments\.js$/ }, () => ({ path: 'intake', namespace: 'fixture' }));
    build.onResolve({ filter: /WordDocsPaperCanvas\.jsx$/ }, () => ({ path: 'canvas', namespace: 'fixture' }));
    build.onResolve({ filter: /\.css$/ }, () => ({ path: 'style', namespace: 'fixture' }));
    build.onLoad({ filter: /.*/, namespace: 'fixture' }, args => ({ loader: 'js', contents: args.path === 'store' ? store : args.path === 'interposer' ? `export*from'actual-media-helper';import{requestDriveMediaUrl as actual}from'actual-media-helper';export function requestDriveMediaUrl(...args){return actual(...args).then(value=>{if(window.__mediaSwitchAfterReturn){window.__mediaSwitchAfterReturn=false;window.__mediaSetState({currentUser:{uid:'actor-B'}})}return value})}` : args.path === 'intake' ? 'export const isDriveIntakeOriginal=()=>false;' : args.path === 'canvas' ? 'export default function Canvas(){return null}' : '' }));
    build.onLoad({ filter: /AdminSharedDriveTab\.jsx$|consumer_original_1\.jsx$/ }, args => ({ loader: 'jsx', contents: fs.readFileSync(args.path, 'utf8').replaceAll('window.location.assign(', 'window.__fixtureNavigate(') }));
  } }] });
  const js = built.outputFiles[0].contents; fs.writeFileSync(path.join(checkpoint, phase + '.bundle.js'), js, { flag: 'wx' });
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; connect-src 'none'; frame-src 'none'; media-src 'none'; img-src 'none'; style-src 'unsafe-inline'"); res.setHeader('Cache-Control', 'no-store');
    if (req.method === 'GET' && req.url === '/') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end('<!doctype html><title>Controlled media session verification</title><div id="component"></div><script type="module" src="/fixture.js"></script>'); }
    else if (req.method === 'GET' && req.url === '/fixture.js') { res.setHeader('Content-Type', 'text/javascript'); res.end(js); } else { res.statusCode = 404; res.end(); }
  });
  server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ pid: process.pid, url: 'http://127.0.0.1:' + server.address().port + '/', phase })));
  setTimeout(() => server.close(), 180000).unref();
})().catch(() => { console.error(JSON.stringify({ fixtureBuildFailed: true })); process.exitCode = 1; });
