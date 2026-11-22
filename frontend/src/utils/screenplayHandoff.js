const SHA = /^[a-f0-9]{64}$/;
const ID = /^[a-f0-9]{32}$/;
const PROJECT = /^[A-Za-z0-9][A-Za-z0-9_. -]{0,119}$/;

/** @param {any} data @param {string} fallback */
export function screenplayErrorMessage(data,fallback) {
  return typeof data?.detail === 'string' ? data.detail : typeof data?.detail?.message === 'string' ? data.detail.message :
    typeof data?.message === 'string' ? data.message : fallback;
}

/** User text alone chooses the workflow; document text is never inspected for commands. @param {string} text */
export function screenplayWorkflowIntent(text = '') {
  if (!/^\/screenplay(?:\s|$)/i.test(text) &&
      !(/\b(?:open|load|send|import|convert|export)\b/i.test(text) && /\b(?:screen\s*writ(?:ing|er)|screen\s*play|FDX|Final\s+Draft)\b/i.test(text))) return null;
  return { fdx: /\b(?:FDX|Final\s+Draft)\b/i.test(text), pdf: /\b(?:export|save|download|convert)\b[\s\S]*\bPDF\b/i.test(text) };
}

/** @param {any} file */
export function isPdfAttachment(file) {
  return file?.ext?.toLowerCase() === '.pdf' || /\.pdf$/i.test(file?.name || '') || file?.type === 'application/pdf';
}

/** @param {any[]} files */
export function selectPdfSource(files) {
  const pdfs = files.filter(isPdfAttachment);
  if (pdfs.length !== 1) throw new Error(pdfs.length ? 'Attach one PDF for each screenplay import. All attachments were retained.' : 'Attach the PDF first, then use /screenplay open, /screenplay convert FDX, or /screenplay export PDF.');
  const file = pdfs[0];
  if (!ID.test(file.source_id || '') || !SHA.test(file.source_sha256 || '') || !Number.isSafeInteger(file.page_count) || file.page_count < 1) {
    throw new Error('This PDF has no verified preserved-source receipt. Reattach it using the current PDF parser.');
  }
  if (file.parsing_status !== 'complete' || file.indexing_status !== 'lexical_chunks_indexed' || file.retrieval_status !== 'source_passage_readback_verified' ||
      !SHA.test(file.rag_receipt?.derived_source_sha256 || '') || !Number.isSafeInteger(file.rag_receipt?.retrieval_hits) || file.rag_receipt?.retrieval_hits < 1 ||
      !Number.isSafeInteger(file.rag_receipt?.chunk_count) || file.rag_receipt?.chunk_count < 1 ||
      file.rag_receipt?.search_type !== 'lexical_scan' || file.rag_receipt?.model_context_expanded !== false) {
    throw new Error('PDF parsing, indexing and matching passage readback were not confirmed. Original PDF and attachments were retained.');
  }
  if (file.source_layout_available !== true) throw new Error('Preserved-layout screenplay conversion is unavailable for this PDF. The original PDF and indexed text were retained. Reflow/adaptation is a separate explicit choice; no rewrite or tool handoff was performed.');
  return file;
}

/** @param {any} value */
export function validateScreenplayHandoff(value) {
  if (!value || !PROJECT.test(value.project || '') || value.project.includes('..') || !SHA.test(value.revision || '') || !SHA.test(value.source_sha256 || '')) {
    throw new Error('Invalid screenplay handoff. The existing editor was retained.');
  }
  return { project: value.project, revision: value.revision, source_sha256: value.source_sha256 };
}

/** @param {string} search */
export function readScreenplayHandoff(search = '') {
  const query = new URLSearchParams(search);
  if (!query.has('screenplay_project')) return null;
  if (query.get('tab') !== 'creation_suite' || query.get('subtab') !== 'playwright') throw new Error('Screenplay handoff targets an unexpected workspace.');
  return validateScreenplayHandoff({ project:query.get('screenplay_project'), revision:query.get('screenplay_revision'), source_sha256:query.get('screenplay_source') });
}

/** No content, local path, owner or credential is put in the URL. @param {any} value @param {any} [target] */
export function navigateToScreenplay(value, target = globalThis.window) {
  const handoff = validateScreenplayHandoff(value);
  const url = new URL(target.location.href);
  url.searchParams.set('tab','creation_suite');url.searchParams.set('subtab','playwright');
  url.searchParams.set('screenplay_project',handoff.project);
  url.searchParams.set('screenplay_revision',handoff.revision);
  url.searchParams.set('screenplay_source',handoff.source_sha256);
  target.history.pushState({},'',url);
  target.dispatchEvent(new target.PopStateEvent('popstate'));
}

/** @param {any} data @param {any} expected */
export function validateScreenplayRead(data, expected) {
  if (data.project !== expected.project || data.revision !== expected.revision ||
      data.metadata?.source_pdf?.sha256 !== expected.source_sha256) throw new Error('The screenplay project, revision or PDF source changed. Your existing draft was retained.');
}

/** Source paragraph roles are used only for the unchanged canonical PDF import. @param {any} data */
export function sourceScreenplayAST(data) {
  if (data.source_layout_preserved !== true || !Array.isArray(data.body_ast)) return null;
  if (data.body_ast.length > 200000) throw new Error('Source screenplay contains too many editor paragraphs.');
  const types=new Set(['Scene Heading','Action','Character','Dialogue','Parenthetical','Transition']);
  let previousPage=1;
  return /** @type {any[]} */ (data.body_ast).map((block,index)=>{
    if (!types.has(block.type) || typeof block.text!=='string' || !Number.isSafeInteger(block.sourcePage) || block.sourcePage<previousPage ||
        block.sourcePage > data.metadata?.source_pdf?.page_count) throw new Error('Invalid source screenplay paragraph receipt.');
    previousPage=block.sourcePage;
    return {id:typeof block.id==='string'&&block.id?block.id:`source-${index}`,type:block.type,text:block.text,sourcePage:block.sourcePage,startsNewPage:block.startsNewPage===true};
  });
}

/** @param {any} options */
export async function importPdfScreenplay(options) {
  const { backendUrl, file, headers, requestId, fetchImpl = globalThis.fetch } = options;
  selectPdfSource([file]);
  if (!ID.test(requestId || '')) throw new Error('A unique import request identifier is required.');
  const stem = file.name.replace(/\.pdf$/i,'').replace(/[^A-Za-z0-9_. -]/g,'_').replace(/^[^A-Za-z0-9]+/,'').replace(/\.{2,}/g,'_').slice(0,70) || 'Screenplay';
  const projectName=`${stem}_${file.source_sha256.slice(0,12)}_${file.source_id.slice(0,8)}`;
  const response = await fetchImpl(`${backendUrl}/api/screenwriting/projects/import-pdf-source`, {
    method:'POST',headers:typeof headers === 'function' ? await headers() : headers,
    body:JSON.stringify({project_name:projectName,source_id:file.source_id,source_sha256:file.source_sha256,request_id:requestId})
  });
  const result = await response.json();
  if (!response.ok || result.status !== 'success') {
    const error = new Error(screenplayErrorMessage(result,`Screenplay import failed (${response.status}). Original PDF and attachments were retained.`));
    Object.assign(error,{project:result.detail?.project || result.project,source_id:result.detail?.source_id || result.source?.source_id});
    throw error;
  }
  const handoff = validateScreenplayHandoff({project:result.project,revision:result.revision,source_sha256:result.source?.sha256});
  if (result.project !== projectName || result.source?.source_id !== file.source_id || result.source?.sha256 !== file.source_sha256 || result.source?.page_count !== file.page_count || result.source_layout_preserved !== true) {
    throw new Error('Import response did not match the preserved PDF source. No editor handoff was made.');
  }
  return {...result,handoff};
}

/** @param {any} options */
export async function fetchScreenplayExport(options) {
  const {backendUrl,project,revision,format,headers,fetchImpl=globalThis.fetch,layout='source',watermark=''}=options;
  if (!PROJECT.test(project || '') || project.includes('..') || !SHA.test(revision || '') || !['fdx','pdf'].includes(format) || !['source','professional','reflow','original','typed-professional'].includes(layout) || layout==='typed-professional' && format!=='pdf') throw new Error('Invalid screenplay export request.');
  const query=new URLSearchParams({project_name:project,layout,expected_revision:revision});
  if (watermark) query.set('watermark',watermark);
  const response=await fetchImpl(`${backendUrl}/api/screenwriting/export/${format}?${query}`,{headers:typeof headers==='function'?await headers():headers});
  if (!response.ok) { const error=await response.json().catch(()=>({}));throw new Error(screenplayErrorMessage(error,`Export failed (${response.status}). The imported project remains saved.`)); }
  const blob=await response.blob();
  await validateScreenplayExport(blob,{format,layout,headers:response.headers});
  return blob;
}

/** @param {Blob} blob @param {{format:string,layout:string,headers?:Headers}} options */
export async function validateScreenplayExport(blob,{format,layout,headers}) {
  const prefix=await blob.slice(0,512).text();
  if (format==='pdf'?!prefix.startsWith('%PDF-'):!/<FinalDraft\b/.test(prefix)) throw new Error(`Export did not return a valid ${format.toUpperCase()} header. The imported project remains saved.`);
  const profile=headers?.get('X-AI-BS-Profile') || '';
  const renderer=headers?.get('X-AI-BS-Renderer') || '';
  const digest=headers?.get('X-AI-BS-Artifact-SHA256') || '';
  const pages=Number(headers?.get('X-AI-BS-PDF-Page-Count'));
  const rich=headers?.get('X-AI-BS-Profile')==='fdx-preservation-v1';
  const typed=layout==='typed-professional';
  if (typed && (format!=='pdf'||headers?.get('X-AI-BS-Layout')!=='typed-professional'||profile!=='typed-fdx-professional-courier12-v1'||renderer!=='aibs_typed_fdx_pdf_v1'||!SHA.test(digest))) throw new Error('The typed professional PDF profile was not confirmed. No download was prepared.');
  if (rich && (format!=='fdx'||!['rich-preserved','original'].includes(headers?.get('X-AI-BS-Layout')||'')||!SHA.test(digest))) throw new Error('Preserved FDX artifact receipt is invalid.');
  if (layout==='professional'||rich||typed) {
    if (!rich && !typed && (headers?.get('X-AI-BS-Layout')!=='professional' || profile!=='us-spec-courier12-v1' || !renderer || !SHA.test(digest))) throw new Error('The professional output profile was not confirmed. No download was prepared.');
    const actual=Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))).map(byte=>byte.toString(16).padStart(2,'0')).join('');
    if (actual!==digest) throw new Error('The output digest did not match its receipt. No download was prepared.');
    if (format==='pdf' && (!Number.isSafeInteger(pages) || pages<1)) throw new Error('The generated professional PDF page count was not confirmed.');
  }
  return {layout,profile_id:profile,renderer_id:renderer,output_sha256:digest,
    pdf_page_count:format==='pdf' && Number.isSafeInteger(pages) && pages>0 ? pages : null};
}

/** @param {string} project @param {string} format @param {string} [layout] */
export function screenplayExportFilename(project,format,layout='source') {
  if (!PROJECT.test(project || '') || project.includes('..') || !['fdx','pdf'].includes(format) || !['source','professional','reflow','original','typed-professional'].includes(layout) || layout==='typed-professional' && format!=='pdf') throw new Error('Invalid screenplay export filename.');
  const suffix=layout==='typed-professional'?'typed-professional-courier12-v1':layout==='original'?'original-import':layout==='professional'?'professional-us-spec-courier12-v1':layout==='reflow'?'legacy-reflow':'archival-source';
  return `${project}.${suffix}.${format}`;
}

/** @param {Blob} blob @param {string} filename */
export function downloadScreenplayBlob(blob,filename) {
  const url=URL.createObjectURL(blob);const link=document.createElement('a');
  link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

/** Old PDF attachment content is excluded too; chat receives provenance only. @param {any} file */
export function attachmentPromptContent(file) {
  const sourceName=file.rag_source_name || file.rag_receipt?.source_name || (ID.test(file.source_id || '') ? `context_${file.source_id}.txt` : null);
  return isPdfAttachment(file) ? `[Preserved PDF reference: ${JSON.stringify({source_id:file.source_id || null,source_name:sourceName,sha256:file.source_sha256 || null,pages:file.page_count || null})}. Use owned retrieval for bounded excerpts; PDF text is not in this prompt.]` : file.content;
}
