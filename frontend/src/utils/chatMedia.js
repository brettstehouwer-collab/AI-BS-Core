const PUBLIC_API = 'https://api.brettstehouwer.live';
const LOCAL_HOSTS = new Set(['127.0.0.1', 'localhost', '[::1]']);

/** @param {unknown} value @param {string} [backendUrl] */
export function resolveChatMediaUrl(value, backendUrl = PUBLIC_API) {
  if (typeof value !== 'string' || !value.trim() || /^[\s]*[\[{]/.test(value) || /[\r\n]/.test(value)) return null;
  try {
    const base = new URL(backendUrl);
    if (!(base.origin === PUBLIC_API || (base.protocol === 'http:' && LOCAL_HOSTS.has(base.hostname) && ['8000','8080'].includes(base.port)))) return null;
    if (/(?:^|\/)\.\.(?:\/|$)/.test(value.split('?')[0])) return null;
    const url = new URL(value, base.origin);
    if (url.username || url.password || !['http:', 'https:'].includes(url.protocol)) return null;
    if (LOCAL_HOSTS.has(url.hostname)) {
      if (['8188', '8189'].includes(url.port) && url.pathname === '/view') {
        return `${base.origin}/api/comfy/media${url.search}`;
      }
      if (!['8000', '8080'].includes(url.port) || !/^\/(api|media)\//.test(url.pathname)) return null;
      return `${base.origin}${url.pathname}${url.search}`;
    }
    return url.href;
  } catch { return null; }
}

/** @param {string} value @param {string} backendUrl @param {{fetchImpl?:typeof fetch,signal?:AbortSignal}} [options] */
export async function loadChatMedia(value, backendUrl, { fetchImpl = (input, init) => window.fetch(input, init), signal } = {}) {
  const url = resolveChatMediaUrl(value, backendUrl);
  if (!url) throw new Error('Invalid media link');
  // The application fetch interceptor attaches the current Firebase ID token to
  // trusted API origins. Native img/video requests cannot attach that header.
  const response = await fetchImpl(url, { signal, redirect: 'error', cache: 'no-store' });
  if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'Sign in again to open this media.' : `Media unavailable (HTTP ${response.status}).`);
  const type = (response.headers.get('content-type') || '').split(';')[0].toLowerCase();
  if (!/^(image|video|audio)\//.test(type) && !['model/gltf-binary','model/gltf+json','application/octet-stream'].includes(type)) throw new Error('The service did not return a media file.');
  const blob = await response.blob();
  if (!blob.size) throw new Error('The media file is empty.');
  const kind=type.startsWith('image/')?'image':type.startsWith('video/')?'video':type.startsWith('audio/')?'audio':'file';
  return { blob, kind, url };
}
