import { updateFDXBlockText } from '../../utils/fdxDocumentFormat.js';
const SHA=/^[a-f0-9]{64}$/;
/** @param {any} value */
export const cloneRichFDX=value=>value?JSON.parse(JSON.stringify(value)):null;
/** Private, per-acknowledged-revision typed history; undo never invents a replacement run. @param {any} cache @param {any} baseline @param {any} current @param {string} revision */
export function richBlockHistory(cache,baseline,current,revision){
  cache.clock=(cache.clock||0)+1;let entry=cache.entries[current.id];
  if(!entry||entry.revision!==revision){entry={revision,states:[cloneRichFDX(baseline)],index:0,stamp:cache.clock};cache.entries[current.id]=entry;}
  entry.stamp=cache.clock;
  if(JSON.stringify(entry.states[entry.index])!==JSON.stringify(current))recordRichBlockHistory(entry,current);
  // Evict old undo data only; the current editor document/recovery draft is separate.
  const bytes=()=>new TextEncoder().encode(JSON.stringify(cache.entries)).length;
  for(const [key] of Object.entries(cache.entries).sort((a,b)=>a[1].stamp-b[1].stamp)){
    if(bytes()<=16*1024*1024)break;if(key!==current.id)delete cache.entries[key];
  }
  return entry;
}
/** @param {any} entry @param {any} block */
export function recordRichBlockHistory(entry,block){
  if(JSON.stringify(entry.states[entry.index])===JSON.stringify(block))return;
  entry.states=entry.states.slice(0,entry.index+1);entry.states.push(cloneRichFDX(block));entry.index=entry.states.length-1;
  while(entry.states.length>1&&(entry.states.length>32||new TextEncoder().encode(JSON.stringify(entry.states)).length>1024*1024)){entry.states.shift();entry.index--;}
}
/** Only a known typed state within the current acknowledged revision can be restored. @param {any} entry @param {string} text @param {string} inputType */
export function restoreRichBlockHistory(entry,text,inputType){
  const direction=inputType==='historyUndo'?-1:inputType==='historyRedo'?1:0;
  if(!direction)throw new Error('Unsupported rich history operation.');
  if(entry.states[entry.index].text===text)return cloneRichFDX(entry.states[entry.index]);
  for(let index=entry.index+direction;index>=0&&index<entry.states.length;index+=direction){
    if(entry.states[index].text===text){entry.index=index;return cloneRichFDX(entry.states[index]);}
  }
  throw new Error('This undo/redo goes beyond the retained typed history or an acknowledged save. The full text is retained; create a separate working copy.');
}
/** Metadata and operations remain draft data; derived run IDs never define document identity. @param {any} value */
export function richFDXIdentity(value){
  if(!value)return '';
  return JSON.stringify({schema:value.schema,source_sha256:value.source_sha256,title_page:value.title_page,preserved_sections:value.preserved_sections,
    blocks:value.blocks.map((/** @type {any} */ block)=>({id:block.id,type:block.type,text:block.text,notes:block.notes,runs:block.runs.map((/** @type {any} */ run)=>({text:run.text,attributes:run.attributes})),attributes:{...block.attributes,Type:block.type},dualGroup:block.dualGroup,dualSide:block.dualSide,startsNewPage:block.startsNewPage}))});
}
/** @param {any} document */
export function richFDXProjection(document){
  const title=document.title_page||[],header=[];
  if(title.length){header.push('Title: '+title[0].text.replaceAll('\n','\n    '));const authors=title.slice(1).filter((/** @type {any} */ b)=>b.type==='Author').map((/** @type {any} */ b)=>b.text);const other=title.slice(1).filter((/** @type {any} */ b)=>b.type!=='Author').map((/** @type {any} */ b)=>b.text);if(authors.length)header.push('Author: '+authors.join('\n').replaceAll('\n','\n    '));if(other.length)header.push('Notes: '+other.join('\n').replaceAll('\n','\n    '));}
  let text=header.length?header.join('\n')+'\n\n':'';
  for(const block of document.blocks){if(block.startsNewPage&&text)text+='\n\n===\n\n';text+=['Dialogue','Parenthetical'].includes(block.type)?'\n':text&&!text.endsWith('\n\n')?'\n\n':'';text+=block.text;}
  return text;
}
/** Rebase only against acknowledged saves, never against a silently reread server. @param {any} draft @param {any} saved */
export function prepareRichFDXWrite(draft,saved){
  if(!draft||!saved||draft.schema!=='aibs_rich_fdx_v1'||draft.source_sha256!==saved.source_sha256||draft.blocks.length!==saved.blocks.length)throw new Error('Rich FDX source/structure changed. Retain this draft as a separate working copy.');
  const result=cloneRichFDX(saved),accepted=new Set(saved.applied_operation_ids||[]);
  result.blocks=draft.blocks.map((/** @type {any} */ target,/** @type {number} */ index)=>{
    const baseline=saved.blocks[index];if(target.id!==baseline.id)throw new Error('Reordering FDX paragraphs requires a separate working copy.');
    let current=cloneRichFDX(baseline);current.edit_operations=[];
    for(const operation of target.edit_operations||[]){
      if(accepted.has(operation.id))continue;
      if(current.text!==operation.before_text)throw new Error('Pending FDX edit does not match its acknowledged paragraph. The local draft was retained.');
      const next=Array.from(current.text).slice(0,operation.start).join('')+operation.text+Array.from(current.text).slice(operation.end).join('');
      current=updateFDXBlockText(current,next,operation);current.edit_operations[current.edit_operations.length-1]={...operation};
    }
    if(current.text!==target.text)throw new Error('Unqualified FDX text/undo change retained locally. Use an explicit text edit or separate working copy.');
    // Preserve supplied readonly metadata so the server rejects unsupported mutation.
    return {...target,runs:current.runs,edit_operations:current.edit_operations};
  });
  return {...draft,document_sha256:saved.document_sha256,applied_operation_ids:[...(saved.applied_operation_ids||[])],blocks:result.blocks};
}
/** Confirm a browser textarea replacement at the actual selection, using Unicode codepoints. @param {string} before @param {string} after @param {number} from @param {number} to @param {string} inputType */
export function confirmedRichEdit(before,after,from,to,inputType){
  let start=Array.from(before.slice(0,from)).length,end=Array.from(before.slice(0,to)).length;const prior=Array.from(before),next=Array.from(after);
  if(from===to&&inputType==='deleteContentBackward')start=Math.max(0,start-1);
  else if(from===to&&inputType==='deleteContentForward')end=Math.min(prior.length,end+1);
  const suffix=prior.length-end,replacement=next.slice(start,next.length-suffix).join('');
  if(prior.slice(0,start).join('')+replacement+prior.slice(end).join('')!==after)throw new Error('This browser edit range could not be verified. The unsaved text remains available for a working copy.');
  return {start,end,text:replacement};
}
/** @param {any} options */
export async function importRichFDX({backendUrl,file,project,headers,fetchImpl=globalThis.fetch}){
  if(!file||file.size>16*1024*1024)throw new Error('FDX exceeds the16MiB original-source limit. Original file was retained.');
  const raw=await file.arrayBuffer(),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(byte=>byte.toString(16).padStart(2,'0')).join('');
  const form=new FormData();form.append('file',file);form.append('project_name',project);form.append('request_id',crypto.randomUUID().replaceAll('-',''));form.append('source_sha256',sha);
  const auth=new Headers(typeof headers==='function'?await headers():headers);auth.delete('Content-Type');
  const response=await fetchImpl(`${backendUrl}/api/screenwriting/projects/import-fdx-source`,{method:'POST',headers:auth,body:form});const data=await response.json();
  if(!response.ok||data.status!=='success')throw new Error(typeof data.detail==='string'?data.detail:data.detail?.message||'Original FDX import was not confirmed.');
  if(data.project!==project||data.source?.sha256!==sha||!SHA.test(data.revision||'')||data.fdx_document?.source_sha256!==sha)throw new Error('FDX import receipt did not match the original bytes; the existing editor was retained.');
  return data;
}
