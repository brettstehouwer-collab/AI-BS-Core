const ID=/^[a-f0-9]{32}$/,SHA=/^[a-f0-9]{64}$/;
/** @param {any} file */
const isPdf=file=>file?.ext?.toLowerCase()==='.pdf'||/\.pdf$/i.test(file?.name||'')||file?.type==='application/pdf';
/** @param {any} value */
function references(value){
 if(!Array.isArray(value)||value.length>4)throw Error('Attach at most four verified PDFs for a chat turn.');
 const result=new Map();
 for(const row of value){
  if(!row||Object.keys(row).sort().join(',')!=='source_id,source_sha256'||!ID.test(row.source_id||'')||!SHA.test(row.source_sha256||''))throw Error('PDF source references are invalid. Original attachments were retained.');
  if(result.has(row.source_id)&&result.get(row.source_id)!==row.source_sha256)throw Error('Conflicting PDF source revisions were retained. Reattach the intended source.');
  result.set(row.source_id,row.source_sha256);
 }
 return [...result].map(([source_id,source_sha256])=>({source_id,source_sha256}));
}
/** IDs are copied only from verified upload receipts or this same conversation's explicit scope.
 * @param {any[]} files @param {any[]} history @param {{owner:string,conversation_id:string,backend_url:string}} scope */
export function attachmentSourceReferences(files,history,scope){
 if(!scope?.owner||!scope?.conversation_id||!scope?.backend_url)throw Error('Chat identity is not ready. Attachments were retained.');
 if(files.length){
  const pdfs=files.filter(isPdf);
  for(const file of pdfs){
   if(file.parsing_status!=='complete'||file.indexing_status!=='lexical_chunks_indexed'||file.retrieval_status!=='source_passage_readback_verified'||
      !SHA.test(file.rag_receipt?.derived_source_sha256||'')||file.rag_receipt?.search_type!=='lexical_scan'||file.rag_receipt?.model_context_expanded!==false||
      !Number.isSafeInteger(file.rag_receipt?.chunk_count)||file.rag_receipt.chunk_count<1||!Number.isSafeInteger(file.rag_receipt?.retrieval_hits)||file.rag_receipt.retrieval_hits<1)
    throw Error('PDF parsing/index/readback was not confirmed. Reattach the PDF; input and attachments were retained.');
  }
  return references(pdfs.map(file=>({source_id:file.source_id,source_sha256:file.source_sha256})));
 }
 for(let position=history.length-1;position>=0;position--){
  const row=history[position];
  if(row?.role!=='user'||!Object.hasOwn(row,'source_references'))continue;
  const saved=row.source_reference_scope;
  if(!saved||saved.owner!==scope.owner||saved.conversation_id!==scope.conversation_id||saved.backend_url!==scope.backend_url)return [];
  return references(row.source_references);
 }
 return [];
}
/** A reported receipt is data for display, never permission to execute a tool. @param {any} value */
export function sourceRetrievalSummary(value){
 if(value?.schema!=='aibs.attached_source_retrieval.v1'||value.search_scope!=='explicit_attached_owner_sources'||
    !Array.isArray(value.sources)||value.sources.length>4||!Array.isArray(value.passages)||!Number.isSafeInteger(value.returned_passages)||
    value.returned_passages!==value.passages.length||value.returned_passages<0||value.returned_passages>2)return null;
 if(value.status==='no_matching_passages'&&value.returned_passages===0)return 'No matching passages were reported for the attached PDF sources. No alternative PDF was substituted.';
 if(value.status==='context_budget_exhausted'&&value.returned_passages===0)return 'Matching passages did not fit the bounded context budget; no excerpts were supplied.';
 if(value.status!=='retrieved'||!value.returned_passages)return null;
 const passages=/** @type {{source_id:string}[]} */(value.passages);
 const covered=new Set(passages.map(row=>row.source_id)).size;
 return `Reported attached-PDF retrieval: ${value.returned_passages} bounded passage${value.returned_passages===1?'':'s'}; ${covered} of ${value.sources.length} explicitly scoped source${value.sources.length===1?'':'s'} contributed excerpts. This does not establish a full-document review.`;
}
