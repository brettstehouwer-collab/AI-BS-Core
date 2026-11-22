import { auth } from '../firebase.js';
import { chatAuthHeaders } from './chatAuth.js';
const SUMMARY_ORIGIN = 'https://jkx1rh2sm8.execute-api.us-east-2.amazonaws.com';

export async function loadProductionsCloudAnalytics({ fetchImpl = globalThis.fetch, signal } = {}) {
  const user = auth.currentUser;
  if (!user) throw new Error('Sign in to read Productions analytics.');
  const guard = () => {
    if (signal?.aborted || auth.currentUser !== user) {
      throw new DOMException('Analytics request cancelled because its account or abort state changed.', 'AbortError');
    }
  };
  guard();
  const configResponse = await fetchImpl('/productions-analytics.json', {
    signal, cache: 'no-store', credentials: 'omit', redirect: 'error'
  });
  guard();
  if (!configResponse.ok) throw new Error('Productions cloud analytics is not configured.');
  const config = await configResponse.json();
  guard();
  let url;
  try { url = new URL(config.summary_url); } catch { throw new Error('Invalid Productions analytics endpoint.'); }
  if (url.origin !== SUMMARY_ORIGIN ||
      url.port || url.username || url.password || url.pathname !== '/summary' || url.search || url.hash) {
    throw new Error('Invalid Productions analytics endpoint.');
  }
  const headers = await chatAuthHeaders({}, user.uid);
  guard();
  const response = await fetchImpl(url.href, {
    headers, signal, cache: 'no-store', credentials: 'omit', redirect: 'error'
  });
  guard();
  if (!response.ok) {
    throw new Error([401, 403].includes(response.status)
      ? 'Productions analytics requires an authorized administrator session. Sign in again.'
      : `Productions cloud analytics could not refresh (HTTP ${response.status}).`);
  }
  const data = await response.json();
  guard();
  if (!data || !Number.isFinite(data.total_pageviews) || data.total_pageviews < 0 ||
      !Number.isFinite(data.unique_visitors) || data.unique_visitors < 0 || !Array.isArray(data.live_events)) {
    throw new Error('Invalid Productions cloud analytics response.');
  }
  return data;
}
