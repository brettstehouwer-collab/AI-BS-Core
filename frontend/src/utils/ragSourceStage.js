import { readChatHttpResponse } from './chatHttpResponse.js';

// Confirm source preservation only. A disk write is not an embedding/indexing
// or full-context retrieval receipt, and must never be presented as one.
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
  const hash = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  const sha256 = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  const response = await fetch(`${backendUrl.replace(/\/+$/, '')}/api/executive/run`, {
    method:'POST', headers:{ 'Content-Type':'application/json', 'X-Client-ID':'stehouwer_publishing' },
    body:JSON.stringify({ command_type:'file_write', target:path, payload:{ content:text, exclusive:true } }),
    signal:typeof AbortSignal !== 'undefined' && AbortSignal.timeout ? AbortSignal.timeout(15000) : undefined,
  });
  const data = await readChatHttpResponse(response);
  const result = data?.result;
  const normalized = value => typeof value === 'string' ? value.replace(/\//g, '\\').toLowerCase() : '';
  if (data?.status !== 'success' || result?.status !== 'success' ||
      normalized(result.path) !== normalized(path) || result.bytes_written !== bytes.length || result.sha256 !== sha256) {
    throw new Error('The backend did not confirm the complete source bytes at the requested path.');
  }
  return { path:result.path, sha256, bytes_written:bytes.length, chars:text.length, indexing_status:'unverified' };
}
