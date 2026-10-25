// Read a fallback response exactly once. Failed HTTP requests remain errors.
export async function readChatHttpResponse(response) {
  if (!response) throw new Error('AI-BS backend connection is offline.');
  const raw = await response.text();
  let data;
  try { data = JSON.parse(raw); } catch { data = { response: raw }; }
  if (!response.ok) {
    const detail = data?.detail || data?.message || data?.error || '';
    const text = typeof detail === 'string' ? detail : JSON.stringify(detail);
    throw new Error(`AI-BS backend returned HTTP ${response.status}${text ? ': ' + text.slice(0, 500) : ''}`);
  }
  if (raw.trim().startsWith('data:')) {
    let content = '';
    for (const line of raw.split('\n')) {
      if (!line.trim().startsWith('data:')) continue;
      const payload = line.trim().replace(/^data:\s*/, '');
      if (!payload || payload === '[DONE]') continue;
      let chunk;
      try { chunk = JSON.parse(payload); } catch { content += payload; continue; }
      if (chunk.error) throw new Error(typeof chunk.error === 'string' ? chunk.error : JSON.stringify(chunk.error));
      content += chunk.content || chunk.response || chunk.choices?.[0]?.delta?.content || '';
    }
    return { response: content };
  }
  return data;
}

export function chatResponseText(data, isPlanMode = false) {
  const message = typeof data?.message === 'string' ? data.message : data?.message?.content;
  const content = data?.choices?.[0]?.message?.content || message || data?.response;
  if (typeof content === 'string' && content.trim()) return content;
  if (isPlanMode && typeof data?.plan_id === 'string' && data.plan_id) return 'Plan generated.';
  throw new Error('AI-BS returned an empty or unsupported response. No model answer was received.');
}
