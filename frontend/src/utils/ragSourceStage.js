import { readChatHttpResponse } from './chatHttpResponse.js';
import { chatAuthHeaders } from './chatAuth.js';

const COLLECTION = 'bschat_sources_v1';
/** @typedef {{source:string, chunk_index:number, byte_start:number, byte_end:number, source_sha256:string}} RagHit */
/** @param {Uint8Array<ArrayBuffer>} bytes */
const sourceHash = async bytes => Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', bytes)),
  byte => byte.toString(16).padStart(2, '0')).join('');
/** @param {string} url */
const endpoint = url => url.replace(/\/+$/, '');

/** @param {{backendUrl:string, query:string}} options @returns {Promise<{count:number, results:RagHit[]}>} */
export async function searchRagSources({ backendUrl, query }) {
  const response = await fetch(`${endpoint(backendUrl)}/api/memory/query`, {
    method:'POST', headers:await chatAuthHeaders({ 'Content-Type':'application/json' }),
    body:JSON.stringify({ query, collection:COLLECTION, top_k:5 }),
  });
  const data = await readChatHttpResponse(response);
  if (data?.status !== 'success' || data.search_type !== 'lexical_scan' || !Array.isArray(data.results)) {
    throw new Error('Owner-scoped source retrieval was not confirmed.');
  }
  return data;
}

/** @param {{backendUrl:string, text:string, sourceName:string, sha256:string, headers:Record<string,string>}} options */
async function indexText({ backendUrl, text, sourceName, sha256, headers }) {
  const response = await fetch(`${endpoint(backendUrl)}/api/memory`, {
    method:'POST', headers,
    body:JSON.stringify({ content:text, metadata:{ kind:'bschat_source_v1', source_name:sourceName, source_sha256:sha256 } }),
  });
  const indexed = await readChatHttpResponse(response);
  if (indexed?.status !== 'success' || indexed.memory_index_status !== 'lexical_chunks_indexed' ||
      indexed.parsing_status !== 'complete' || indexed.source_sha256 !== sha256 || !(indexed.chunk_count > 0)) {
    throw new Error('Complete source parsing and lexical indexing were not confirmed.');
  }
  const bytes = new TextEncoder().encode(text);
  const lookupResponse = await fetch(`${endpoint(backendUrl)}/api/memory/query`, {
    method:'POST', headers, body:JSON.stringify({ query:sourceName, collection:COLLECTION, top_k:5 }),
  });
  const lookup = await readChatHttpResponse(lookupResponse);
  const hits = lookup?.status === 'success' && lookup.search_type === 'lexical_scan' && Array.isArray(lookup.results)
    ? lookup.results : [];
  let verifiedHits = 0;
  for (const hit of hits) {
    if (hit.source_sha256 !== sha256 || typeof hit.content !== 'string' ||
        !Number.isInteger(hit.byte_start) || !Number.isInteger(hit.byte_end) ||
        hit.byte_start < 0 || hit.byte_end > bytes.length || hit.byte_end <= hit.byte_start) continue;
    const excerpt = bytes.subarray(hit.byte_start, hit.byte_end);
    if (new TextDecoder('utf-8', { fatal:true }).decode(excerpt) === hit.content &&
        await sourceHash(excerpt) === hit.chunk_sha256) verifiedHits++;
  }
  if (!verifiedHits) throw new Error('Source was indexed, but matching passage retrieval was not confirmed.');
  return { ...indexed, indexing_status:'lexical_chunks_indexed', retrieval_status:'source_passage_readback_verified',
    retrieval_hits:verifiedHits, source_name:sourceName, sha256, bytes_written:bytes.length,
    chars:text.length, model_context_expanded:false };
}

/** @param {{backendUrl:string, filename:string, expectedSha256?:string}} options */
export async function indexSavedRagSource({ backendUrl, filename, expectedSha256 = '' }) {
  if (!/^context_[a-f0-9]{32}\.txt$/.test(filename)) {
    throw new Error('Use a saved context_<32 hexadecimal characters>.txt basename.');
  }
  if (expectedSha256 && !/^[a-f0-9]{64}$/.test(expectedSha256)) throw new Error('Expected source SHA-256 is invalid.');
  const headers = await chatAuthHeaders({ 'Content-Type':'application/json' });
  const path = `C:\\AI-BS\\workspace\\rag_inputs\\${filename}`;
  const response = await fetch(`${endpoint(backendUrl)}/api/executive/run`, {
    method:'POST', headers,
    body:JSON.stringify({ command_type:'tool', target:'read_host_file', payload:{ file_path:path } }),
  });
  const data = await readChatHttpResponse(response);
  const result = data?.result;
  if (data?.status !== 'success' || result?.status !== 'success' || typeof result.content !== 'string' ||
      result.decoding_errors_replaced !== false || result.truncated !== false) {
    throw new Error('Complete strict UTF-8 saved source read was not confirmed.');
  }
  const bytes = new TextEncoder().encode(result.content);
  const sha256 = await sourceHash(bytes);
  if (result.size_bytes !== bytes.length || result.sha256 !== sha256 ||
      (expectedSha256 && expectedSha256 !== sha256)) throw new Error('Saved source byte/fingerprint check failed.');
  return { ...await indexText({ backendUrl, text:result.content, sourceName:filename, sha256, headers }), path };
}

// Preservation, lexical indexing and bounded retrieval have separate receipts.
/** @param {{backendUrl: string; text: string}} options */
export async function stageRagSource({ backendUrl, text }) {
  if (typeof backendUrl !== 'string' || typeof text !== 'string' || !text.length) {
    throw new Error('A selected backend and nonempty source are required.');
  }
  const bytes = new TextEncoder().encode(text);
  if (bytes.length > 16 * 1024 * 1024) throw new Error('Source exceeds the 16 MiB staging limit; nothing was truncated.');
  const random = new Uint8Array(16);
  globalThis.crypto.getRandomValues(random);
  const id = Array.from(random, byte => byte.toString(16).padStart(2, '0')).join('');
  const path = `C:\\AI-BS\\workspace\\rag_inputs\\context_${id}.txt`;
  const sha256 = await sourceHash(bytes);
  const headers = await chatAuthHeaders({ 'Content-Type':'application/json' });
  const response = await fetch(`${backendUrl.replace(/\/+$/, '')}/api/executive/run`, {
    method:'POST', headers,
    body:JSON.stringify({ command_type:'file_write', target:path, payload:{ content:text, exclusive:true } }),
    signal:typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined,
  });
  const data = await readChatHttpResponse(response);
  const result = data?.result;
  /** @param {unknown} value */
  const normalized = value => typeof value === 'string' ? value.replace(/\//g, '\\').toLowerCase() : '';
  if (data?.status !== 'success' || result?.status !== 'success' ||
      normalized(result.path) !== normalized(path) || result.bytes_written !== bytes.length || result.sha256 !== sha256) {
    throw new Error('The backend did not confirm the complete source bytes at the requested path.');
  }
  const preserved = { path:result.path, sha256, bytes_written:bytes.length, chars:text.length };
  try {
    const indexed = await indexText({ backendUrl, text, sourceName:path.split('\\').pop() || 'pasted_source.txt', sha256, headers });
    return { ...preserved, ...indexed };
  } catch (error) {
    return { ...preserved, indexing_status:'unverified', retrieval_status:'unverified',
      indexing_error:error instanceof Error ? error.message : 'Indexing/retrieval could not be confirmed.' };
  }
}
