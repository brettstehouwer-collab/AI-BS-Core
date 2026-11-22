import { readChatHttpResponse } from './chatHttpResponse.js';

/** @typedef {{provider: string, model: string, modelsByProvider: Record<string, string[]>}} BSChatProviderConfig */
/** @param {{active_provider?: string, providers?: {id?: string, is_configured?: boolean, models?: string[], saved_model?: string}[]}|null|undefined} data
 * @returns {BSChatProviderConfig} */
export function readBSChatProviderConfig(data) {
  /** @type {Record<string, string[]>} */
  const modelsByProvider = {};
  const providers = Array.isArray(data?.providers) ? data.providers : [];
  for (const item of providers) {
    if (!item || typeof item.id !== 'string' || (item.id !== 'local' && !item.is_configured)) continue;
    const models = Array.isArray(item.models) ? item.models.filter(model => typeof model === 'string' && !!model.trim()) : [];
    if (typeof item.saved_model === 'string' && item.saved_model.trim() && !models.includes(item.saved_model)) models.unshift(item.saved_model);
    modelsByProvider[item.id] = models;
  }
  const provider = typeof data?.active_provider === 'string' && modelsByProvider[data.active_provider]
    ? data.active_provider : 'local';
  const active = providers.find(item => item?.id === provider);
  const model = active?.saved_model || modelsByProvider[provider]?.[0] || 'stehouwer_llm';
  return { provider, model, modelsByProvider };
}

/** @param {string} model @param {Record<string, string[]>} modelsByProvider */
export function providerForModel(model, modelsByProvider) {
  return Object.entries(modelsByProvider).find(([provider, models]) => provider !== 'local' && models.includes(model))?.[0] || 'local';
}

/** @param {{aiProviderSelectionRevision: number, availableModels: string[]}} state
 * @param {BSChatProviderConfig} configuration @param {number} expectedRevision */
export function hydrateBSChatProvider(state, configuration, expectedRevision) {
  return { aiProviderModels: configuration.modelsByProvider,
    availableModels: [...new Set([...state.availableModels, ...Object.values(configuration.modelsByProvider).flat()])],
    ...(state.aiProviderSelectionRevision === expectedRevision && expectedRevision === 0
      ? { aiProvider: configuration.provider, selectedModel: configuration.model } : {}),
  };
}

/** @param {{aiProvider: string, aiProviderModels: Record<string,string[]>, selectedModel: string}} state
 * @param {string[]} discoveredModels */
export function discoverBSChatModels(state, discoveredModels) {
  const availableModels = [...new Set([...discoveredModels, ...Object.values(state.aiProviderModels).flat()])];
  return { availableModels,
    ...(state.aiProvider === 'local' && availableModels.length &&
      (!state.selectedModel || !availableModels.includes(state.selectedModel))
      ? { selectedModel: availableModels[0] } : {}),
  };
}

/** @param {{role?: string, content?: string, displayContent?: string}[]|null|undefined} messages */
export function boundedBSChatHistory(messages) {
  return (Array.isArray(messages) ? messages : [])
    .filter(message => (message?.role === 'user' || message?.role === 'assistant') && typeof message.content === 'string')
    .slice(-8).map(message => ({ role: message.role, content: message.content }));
}

/** One selected backend request. A failed or uncertain reply is never replayed.
 * @param {{backendUrl: string, provider: string, model: string, prompt: string, userPrompt: string,
 * messages: {role?: string, content?: string}[], headers: Record<string,string>, signal?: AbortSignal,
 * sourceReferences?: {source_id:string,source_sha256:string}[],
 * useWebSearch?: boolean, onText?: (text: string, displayName: string, sourceRetrieval?: unknown) => void, fetchImpl?: typeof fetch}} options */
export async function streamBSChatProvider({ backendUrl, provider, model, prompt, userPrompt,
  messages, headers, signal, sourceReferences, useWebSearch = false, onText, fetchImpl = fetch }) {
  const response = await fetchImpl(`${backendUrl.replace(/\/$/, '')}/api/v1/hybrid-chat/stream`, {
    method: 'POST', headers, signal,
    body: JSON.stringify({ prompt, user_prompt: userPrompt, provider, model, source_references:sourceReferences,
      messages: boundedBSChatHistory(messages), stream: true,
      use_web_search: useWebSearch, web_search_query: useWebSearch ? userPrompt : undefined }),
  });
  if (!response.ok) await readChatHttpResponse(response);
  if (!response.body) throw new Error('AI-BS returned an empty provider response.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let content = '';
  let displayName = `OpenAI · ${model}`;
  let sourceRetrieval;
  try {
    while (true) {
      const { done, value } = await reader.read();
      content += done ? decoder.decode() : decoder.decode(value, { stream: true });
      const metadata = /<!--AI-BS-METADATA:([\s\S]*?)-->/.exec(content);
      if (metadata) {
        try {
          const parsed = JSON.parse(metadata[1]);
          if (typeof parsed.display_name === 'string' && parsed.display_name.trim()) displayName = parsed.display_name.slice(0, 160);
          sourceRetrieval = parsed.source_retrieval;
        } catch { /* A split metadata chunk is parsed after more bytes arrive. */ }
      }
      if (content) onText?.(content, displayName, sourceRetrieval);
      if (done) break;
    }
  } finally {
    reader.releaseLock?.();
  }
  if (!content.replace(/<!--AI-BS-METADATA:[\s\S]*?-->/g, '').trim()) {
    throw new Error('AI-BS returned an empty provider response.');
  }
  return { content, displayName, sourceRetrieval };
}
