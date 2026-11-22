const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root=process.env.AIBS_AUDIT_SOURCE_ROOT||path.resolve(__dirname,'../..');
const deps=path.resolve(__dirname,'../../frontend/node_modules');
const source=fs.readFileSync(path.join(root,'frontend/src/components/ExecutiveCockpitTab.jsx'),'utf8');
const parser=require(path.join(deps,'@babel/parser'));
const tree=parser.parse(source,{sourceType:'module',plugins:['jsx']});
const all=[];(function walk(n){if(!n||typeof n!=='object')return;if(n.type)all.push(n);for(const [k,v] of Object.entries(n)){if(['loc','comments','tokens'].includes(k))continue;if(Array.isArray(v))v.forEach(walk);else walk(v);}})(tree.program);
const helpers=tree.program.body.filter(n=>n.type==='FunctionDeclaration').map(n=>source.slice(n.start,n.end)).join('\n');
for(const response of [{ok:false,status:503},{ok:true,json:async()=>null},{ok:true,json:async()=>({hardware:null})}])test(`executive missing snapshot ${response.status||'malformed'} clears stale metrics`,async()=>{
 const n=all.find(n=>n.type==='VariableDeclarator'&&n.id.name==='fetchMatrixStatus');let value='stale';let requestCount=0;
 const fn=vm.runInNewContext(`(function(){${helpers};return (${source.slice(n.init.start,n.init.end)});})()`,{Number,Math,Error,activeBackend:'http://fixture.invalid',chatAuthHeaders:async()=>({Authorization:'Bearer synthetic-admin'}),fetch:async()=>{requestCount++;return response;},setMatrixStatus:x=>{value=x;},setAutonomyMode:()=>{},console:{warn(){}}});
 await fn();assert.equal(requestCount,1);assert.notEqual(value,'stale');assert.equal(value.hardware.temp_c,null);assert.equal(value.vault.sqlite_vault_records,null);
});
test('executive initial render has no fabricated health, trading, hardware or vault proof',()=>{
 const React=require(path.join(deps,'react'));const {renderToStaticMarkup}=require(path.join(deps,'react-dom/server'));const {transformSync}=require(path.join(deps,'esbuild'));
 const stripped=source.replace(/^import .*;\r?\n/gm,'').replace('export default function','function');
 const compiled=transformSync(stripped,{loader:'jsx',jsx:'transform'}).code;
 const version=fs.readFileSync(path.join(root,'frontend/version.js'),'utf8').match(/export const SYSTEM_VERSION = ['"]([^'"]+)['"]/)[1];
 const Component=Function('React','useState','useEffect','useRef','useAppStore','SYSTEM_VERSION',`${compiled};return ExecutiveCockpitTab;`)(React,React.useState,React.useEffect,React.useRef,()=> 'http://fixture.invalid',version);
 const markup=renderToStaticMarkup(React.createElement(Component,{backendUrl:'http://fixture.invalid'}));
 for(const claim of ['ALL SYSTEMS GREEN','PORT 8007 ACTIVE','ARMED (Max Slippage','42°C','305,654','ONLINE</span>','>PASSING<'])assert.equal(markup.includes(claim),false,claim);
 assert.match(markup,/Unavailable|UNVERIFIED/);
});
test('executive numeric formatter preserves measured zero and rejects invalid values',()=>{
 const f=vm.runInNewContext(`(function(){${helpers};return executiveMetric;})()`,{Number,Math});
 assert.equal(f(0,' MB'),'0 MB');for(const value of [null,undefined,-1,Infinity,'42',NaN])assert.equal(f(value,' MB'),'Unavailable');
});
test('executive four mirror copies match byte for byte',()=>{
 for(const prefix of ['frontend/components','frontend/src/components/components','frontend/components/components'])assert.equal(fs.readFileSync(path.join(root,prefix,'ExecutiveCockpitTab.jsx'),'utf8'),source);
});
