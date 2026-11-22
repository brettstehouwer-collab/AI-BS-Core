// Static, loopback-only trusted fixture. Does not load application HTML, auth, or analytics.
const fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const { createRequire } = require('node:module');
const localRequire = createRequire('C:/AI-BS/frontend/package.json'), esbuild = localRequire('esbuild');
const checkpoint = process.argv[2], phase = process.argv[3];
if (!/^C:\\AI-BS\\backups\\notos_demo_seed_\d{8}T\d{6,}Z$/.test(checkpoint) || !fs.statSync(checkpoint).isDirectory() || !/^(red|red_validated|red_final|green|green_final)$/.test(phase)) throw Error('Fresh fixed fixture checkpoint required');
(async () => {
  const built = await esbuild.build({ entryPoints: [path.join(__dirname, 'notos_demo_seed_fixture.jsx')], bundle: true, write: false, platform: 'browser', format: 'esm', target: 'es2022', jsx: 'automatic', nodePaths: ['C:/AI-BS/frontend/node_modules'], define: { 'import.meta.env.VITE_BACKEND_URL': '"http://fixture.invalid"' }, plugins: [{ name: 'installed-react', setup(build) {
    build.onResolve({ filter: /^react(?:-dom)?(?:\/.*)?$/ }, args => ({ path: localRequire.resolve(args.path) }));
    if (phase === 'red_final') build.onResolve({ filter: /NotosEnterpriseOSTab\.jsx$/ }, () => ({ path: path.join(checkpoint, 'original_1.jsx') }));
  } }] });
  const js = built.outputFiles[0].contents;
  fs.writeFileSync(path.join(checkpoint, phase + '.bundle.js'), js, { flag: 'wx' });
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; connect-src 'none'; img-src 'self'; style-src 'unsafe-inline'");
    res.setHeader('Cache-Control', 'no-store');
    if (req.method === 'GET' && req.url === '/') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end('<!doctype html><title>Controlled demo verification</title><div id="component"></div><script type="module" src="/fixture.js"></script>'); }
    else if (req.method === 'GET' && req.url === '/fixture.js') { res.setHeader('Content-Type', 'text/javascript'); res.end(js); }
    else { res.statusCode = 404; res.end(); }
  });
  server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ url: 'http://127.0.0.1:' + server.address().port + '/', pid: process.pid, phase })));
  setTimeout(() => server.close(), 180000).unref();
})().catch(() => { console.error(JSON.stringify({ fixtureBuildFailed: true })); process.exitCode = 1; });
