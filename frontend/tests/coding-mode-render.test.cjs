const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const esbuild = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

test('Plan view hides code proposal generation; Implement view exposes explicit generation', async () => {
  const result = await esbuild.build({entryPoints:[path.resolve(__dirname, '../src/components/CodingPreparationPanel.jsx')],
    bundle:true, write:false, format:'cjs', platform:'node', external:['react'], plugins:[{
      name:'inert-owner-services', setup(build) {
        build.onResolve({filter:/useAppStore|projectPreparation/}, args => ({path:args.path, namespace:'inert'}));
        build.onLoad({filter:/.*/,namespace:'inert'}, () => ({contents:'export const useAppStore = {}; export const preparationClientFor = () => { throw Error("No service calls during render"); };'}));
      }
    }]});
  const compiled = {exports:{}};
  new Function('require','module','exports',result.outputFiles[0].text)(require,compiled,compiled.exports);
  const state = {connected:true, busy:false, form:{}, items:[], unconfirmedIds:[], receipt:{state:'PREPARED',durable:true,request_id:'a'.repeat(32),files:[],checks:[]},
    planRecord:{state:'PLAN_PROPOSED',plan_id:'b'.repeat(32),proposal:{summary:'Bounded change',steps:[],questions:[]}},
    planItems:[], proposalItems:[], proposalSeen:[]};
  const render = allowCodeProposal => renderToStaticMarkup(React.createElement(compiled.exports.PreparationView,{state,allowCodeProposal}));
  assert.doesNotMatch(render(false), /Generate code proposal/);
  assert.match(render(true), /Generate code proposal/);
  assert.match(render(false), /Tests not run/);
});
