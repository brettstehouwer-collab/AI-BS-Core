import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { transformSync } = require('../../frontend/node_modules/esbuild');
const forbidden = name => { throw new Error(`Forbidden effect/import: ${name}`); };
function load(file, token = 'configured-test-token') {
  const apps = [];
  const express = () => { const app = { middleware: [], routes: [], use(fn) { this.middleware.push(fn); }, post(path, fn) { this.routes.push({path, fn}); }, listen() { forbidden('listen'); } }; apps.push(app); return app; };
  express.json = () => forbidden('JSON parser registration');
  const source = fs.readFileSync(file, 'utf8');
  const code = file.endsWith('.ts') ? transformSync(source, {loader:'ts', format:'cjs'}).code : source;
  const module = { exports: {} };
  vm.runInNewContext(code, {module, exports:module.exports, Buffer, process:{env:{AI_BS_LOCAL_ADMIN_TOKEN:token, PORT:'3001'}}, require(name) { if(name === 'express') return express; if(name === 'node:crypto') return require(name); return forbidden(name); }}, {filename:file});
  assert.equal(apps.length, 0, 'import must not create app');
  const app = module.exports.createApp();
  return {app, exports:module.exports};
}
function response() { return {code:200, headers:{}, set(name,value){this.headers[name]=value;return this;}, status(code){this.code=code;return this;}, json(value){this.value=value;return this;} }; }
for (const file of ['backend/server.js','genkit_server/index.ts']) {
  const {app, exports} = load(file);
  assert.ok(app.routes.length);
  for(const authorization of [undefined,'Bearer wrong','Bearer ' + 'x'.repeat(10000),'Bearer configured-test-token']) {
    const req = {headers:{authorization}, get body(){throw new Error('body accessed');}};
    const res = response(); let next = false;
    for(const middleware of app.middleware) { middleware(req,res,()=>{next=true;}); if(res.code !== 200) break; }
    if(authorization !== 'Bearer configured-test-token') assert.equal(res.code,401);
    else { assert.ok(next); for(const route of app.routes) { const held = response(); route.fn(req,held); assert.equal(held.code,503); assert.equal(held.value.code,'SERVICE_HELD'); } }
    assert.equal(res.headers['Cache-Control'],'private, no-store');
    assert.equal(res.headers['Access-Control-Allow-Origin'],undefined);
  }
  for(const token of [undefined, '', '   ']) {
    const unconfigured = load(file, token === undefined ? '' : token);
    const res = response();
    unconfigured.app.middleware[0]({headers:{}, get body(){throw new Error('body accessed');}},res,()=>{throw new Error('unconfigured auth bypass');});
    assert.equal(res.code,503);
    assert.equal(res.value.code,'ADMIN_UNCONFIGURED');
  }
  if(exports.actionGlassSeoFlow) await assert.rejects(exports.actionGlassSeoFlow({}), /held/i);
}
console.log('PASS: independent services import inertly; actual middleware authenticates before body access; all registered actions held without provider, filesystem, parser or socket effects.');
