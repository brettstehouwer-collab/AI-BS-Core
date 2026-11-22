const fs=require('node:fs'),assert=require('node:assert/strict');
const esbuild=require('C:/AI-BS/frontend/node_modules/esbuild');
const cp=fs.readFileSync(__dirname+'/proposal_ui_v47_checkpoint.txt','utf8').trim();
const apiPath=cp+'/live_client.cjs';
esbuild.buildSync({entryPoints:['C:/AI-BS/frontend/src/utils/projectPreparation.js'],bundle:true,platform:'node',format:'cjs',outfile:apiPath});
const {createPreparationClient}=require(apiPath),checks=[],calls=[];
function check(name,passed){checks.push({name,passed:Boolean(passed)});assert(passed,name);}
async function main(){
 const key=process.env.AI_BS_ADMIN_KEY;assert(key,'Configured admin identity missing');
 const client=createPreparationClient({getContext:()=>({backendUrl:'http://127.0.0.1:8000',actor:'configured-local-admin'}),fetchImpl:async(url,options={})=>{
  calls.push({path:new URL(url).pathname,method:options.method||'GET'});
  return fetch(url,{...options,headers:{...options.headers,'X-Admin-Key':key,'X-Client-ID':'stehouwer_publishing'}});
 }});
 try{
  await client.open();check('Actual configured administrator identity',client.getState().owner==='local_admin');
  await client.inspect('aee4d15396514b7884c7133f37a023be');check('Actual retained preparation',client.getState().receipt.state==='PREPARED');
  await client.inspectPlan('86c02dd0e2904fe39b6b26a83957f886');check('Actual retained question-free plan',client.getState().planRecord.state==='PLAN_PROPOSED');
  await client.reviewProposal();check('Actual full-source review',client.getState().proposalReview.source_complete===true);
  await client.inspectProposal('5f71b54a2b4f43fdabb792609ec425b7');
  const proposal=client.getState().proposalRecord;
  check('Actual two-file proposal accepted after Web Crypto validation',proposal.state==='PROPOSAL_READY'&&proposal.proposal.files.length===2);
  check('Explicit no test/apply/execute claim',proposal.verification_status==='not_run'&&proposal.apply_authorized===false&&proposal.execution_authorized===false);
  await client.recoverProposal(proposal.proposal_id);check('Actual terminal recovery returns identical evidence',JSON.stringify(client.getState().proposalRecord)===JSON.stringify(proposal));
  await client.inspectProposal('10066c6d7fa04db492ecf7d431e569c3');check('Actual cancelled proposal stays cancelled',client.getState().proposalRecord.state==='CANCELLED'&&client.getState().proposalRecord.proposal===null);
  await client.inspectProposal(proposal.proposal_id);check('Actual saved candidate remains immutable after inspecting another ID',JSON.stringify(client.getState().proposalRecord)===JSON.stringify(proposal));
  check('No inference request was sent',calls.every(c=>c.method==='GET'||c.path.endsWith('/recover')));
  const React=require('C:/AI-BS/frontend/node_modules/react'),{renderToStaticMarkup}=require('C:/AI-BS/frontend/node_modules/react-dom/server');
  const View=require(cp+'/view_green.cjs').PreparationView;
  const html=renderToStaticMarkup(View({state:client.getState(),canCopyDraft:false}));
  fs.writeFileSync(cp+'/actual_fixture_ssr.html',html,{flag:'wx'});
  check('Actual retained diff appears in offline React view',html.includes('+value = 42')&&html.includes('exports.value = 42'));
  check('Actual view labels Not run and Not applied',html.includes('Tests not run')&&html.includes('Not applied'));
  check('No Run Apply or Execute button in actual fixture view',!/<button\b[^>]*>\s*(?:Run|Apply|Execute|Verify)\b/i.test(html));
  check('Exactly the same backend used for every actual read',calls.every(c=>c.path.startsWith('/api/chat/coding-tasks/preparations')));
 }finally{client.close();}
}
main().then(()=>{fs.writeFileSync(cp+'/client_live.json',JSON.stringify({status:'passed',checks,count:checks.length,scope:'Actual8000/source46fixture reads and offline SSR of that data; not browser DOM acceptance',calls},null,2),{flag:'wx'});process.stdout.write(JSON.stringify({passed:checks.length,count:checks.length}));}).catch(error=>{
 fs.writeFileSync(cp+'/client_live_failed.json',JSON.stringify({status:'failed',checks,error_type:error.name,error:error.message,calls},null,2),{flag:'wx'});process.stderr.write(error.stack);process.exitCode=1;
});
