// All requests use the application's existing Firebase-token fetch interceptor.
const routes = [
  ['stats', 'stats'], ['athletes', 'athletes'], ['campaigns', 'campaigns'],
  ['coaches', 'excluded-coaches'], ['quota', 'quota-status'],
  ['smtp', 'smtp-accounts'], ['emails', 'athlete-emails'],
  ['replies', 'sms/replies'], ['analytics', 'outreach-analytics'],
  ['emailConfig', 'email-api/config'],
];

export async function loadRecdebutSnapshot(baseUrl, { fetchImpl = globalThis.fetch, signal } = {}) {
  const entries = await Promise.all(routes.map(async ([name, route]) => {
    const response = await fetchImpl(`${baseUrl.replace(/\/$/, '')}/api/v1/recdebut/${route}`, {
      signal: signal || AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      const message = [401, 403].includes(response.status)
        ? 'RecDebut requires an authorized administrator session. Sign in again to continue.'
        : `RecDebut could not load ${route} (HTTP ${response.status}).`;
      throw Object.assign(new Error(message), { status: response.status });
    }
    const data = await response.json();
    if (!data || data.success !== true) throw new Error(`RecDebut could not load ${route}.`);
    const arrayKey = {athletes:'athletes', campaigns:'campaigns', coaches:'coaches', smtp:'accounts', replies:'replies'}[name];
    if (arrayKey && !Array.isArray(data[arrayKey])) throw new Error(`Invalid ${route} response.`);
    if (name === 'stats' && ['total','contacted','pending','emails','coaches','campaigns'].some(key =>
      !Number.isFinite(data[key]) || data[key] < 0)) throw new Error('Invalid stats response.');
    return [name, data];
  }));
  return Object.fromEntries(entries);
}
