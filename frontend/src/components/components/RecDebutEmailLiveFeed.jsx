import { useEffect, useState } from "react";

/** @param {string | number | null | undefined} value */
const time =  value => value ? new Date(value).toLocaleString() : 'Not yet recorded';
/** @param {Record<string, number> | undefined} states */
const total =  states => Object.values(states || {}).reduce((a, b) => a + Number(b), 0);
/** @param {Record<string, number> | undefined} states @param {string} key */
const count = ( states,  key) => states?.[key] || 0;

/** @param {{"backendUrl": string}} props */
export default function RecDebutEmailLiveFeed({ backendUrl }) {
  const [snapshot, setSnapshot] = useState(/** @type {{primary: Record<string, number>, outgoing_copies: Record<string, number>, reply_copies: Record<string, number>, reply_forwarding?: {enabled: boolean, configured: boolean, status?: string, attempted_at?: string | null, succeeded_at?: string | null, details?: {last_uid?: number, highest_uid?: number, scanned?: number, matched?: number, opt_out_warning?: string}}, observed_at: string, sending_enabled: boolean, sender: string, copy_to: string, outgoing_copies_missing: number, tracked_link_requests: number, email_suppressions: number, sender_blockers: string[], drafts: Array<{id: string, audience: number, eligible: number, blockers: string[]}>, legacy_email_status: Record<string, number>, notice: string, events: Array<{updated_at: string, category: string, state: string, code?: string}>} | null} */ (null));
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let stopped = false;
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let timer;
    const controller = new AbortController();
    async function poll() {
      try {
        const response = await fetch(`${backendUrl}/api/v1/recdebut/workflow/email/live`, {
          cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
        });
        if (!response.ok) throw new Error([401, 403].includes(response.status)
          ? 'Sign in as an administrator to view private campaign activity.'
          : `Campaign monitor unavailable (HTTP ${response.status}).`);
        const data = await response.json();
        if (!stopped) { setSnapshot(data); setError(''); }
      } catch (failure) {
        if (!stopped) setError(failure instanceof Error ? (failure instanceof Error ? failure.message : String(failure)) : 'Campaign monitor unavailable.');
      } finally {
        if (!stopped) timer = setTimeout(poll, 5000);
      }
    }
    poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, [backendUrl, refresh]);
  const p = snapshot?.primary;
  const c = snapshot?.outgoing_copies;
  const r = snapshot?.reply_copies;
  const connector = snapshot?.reply_forwarding;
  const connectorStale = connector?.enabled && connector?.attempted_at
    && Date.now() - Date.parse(connector.attempted_at) > 180000;
  /** @type {import('react').CSSProperties} */
const box = { background: '#161b22', border: '1px solid #30363d', borderRadius: 7, padding: '8px 12px' };
  return <section aria-label="RecDebut campaign live monitor" style={{ padding: 14, background: '#0d1117', color: '#c9d1d9', borderBottom: '1px solid #30363d', flexShrink: 0, minWidth: 0, maxHeight: '48vh', overflowY: 'auto', overflowWrap: 'anywhere', boxSizing: 'border-box' }}>
    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
      <strong>RecDebut email activity · all guarded campaigns</strong>
      <span style={{ color: error ? '#ff7b72' : snapshot ? '#3fb950' : '#e3b341' }}>{error ? 'Feed stale / unavailable' : snapshot ? 'Live ledger · refreshes every 5 seconds' : 'Connecting…'}</span>
      <button type="button" onClick={() => setRefresh(n => n + 1)} style={{ marginLeft: 'auto', ...box, color: '#c9d1d9', cursor: 'pointer' }}>Refresh</button>
    </div>
    {error && <p role="alert" style={{ color: '#ff7b72', margin: '8px 0' }}>{error}{snapshot && ` Last good snapshot: ${time(snapshot.observed_at)}.`}</p>}
    {snapshot && <>
      <div style={{ margin: '8px 0', color: snapshot.sending_enabled ? '#ff7b72' : '#e3b341' }}>
        Athlete sending: <strong>{snapshot.sending_enabled ? 'Enabled' : 'HELD'}</strong> · From {snapshot.sender} · Dennis copies: {snapshot.copy_to}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(165px, 100%), 1fr))', gap: 8, fontSize: 12 }}>
        <div style={box}><strong>Campaign attempts: {total(p)}</strong><div>SMTP accepted {count(p, 'ACCEPTED')} · Pending {count(p, 'RESERVED') + count(p, 'ATTEMPTING')}</div><div>Blocked {count(p, 'BLOCKED')} · Uncertain {count(p, 'UNCERTAIN')}</div></div>
        <div style={box}><strong>Dennis outgoing copies</strong><div>SMTP accepted {count(c, 'ACCEPTED')} · Uncertain {count(c, 'UNCERTAIN')}</div><div>Pending {count(c, 'RESERVED') + count(c, 'ATTEMPTING')} · Blocked {count(c, 'BLOCKED')} · Missing {snapshot.outgoing_copies_missing}</div></div>
        <div style={box}><strong>Matched athlete replies: {total(r)}</strong><div>Copies accepted {count(r, 'ACCEPTED')} · Pending {count(r, 'ATTEMPTING')}</div><div>Blocked {count(r, 'BLOCKED')} · Uncertain {count(r, 'UNCERTAIN')}</div></div>
        <div style={box}><strong>Engagement / opt-outs</strong><div>Tracked link requests {snapshot.tracked_link_requests}</div><div>Email suppressions {snapshot.email_suppressions} · Delivery / opens: unverified</div></div>
      </div>
      <details style={{ marginTop: 8, fontSize: 12 }} open>
        <summary style={{ cursor: 'pointer' }}>Reply connector: {connector?.enabled && connector?.configured ? 'Enabled' : 'Disabled / configuration incomplete'} · {connector?.status || 'No poll recorded'}</summary>
        <div style={{ marginTop: 6 }}>Last attempt: {time(connector?.attempted_at)} · Last successful poll: {time(connector?.succeeded_at)} · Dashboard: {time(snapshot.observed_at)}</div>
        <div>Mailbox UID progress: {connector?.details?.last_uid ?? '—'} / {connector?.details?.highest_uid ?? '—'} · Last poll scanned {connector?.details?.scanned ?? 0} · Matching replies {connector?.details?.matched ?? 0}</div>
        {connectorStale && <div role="alert" style={{ color: '#ff7b72' }}>Reply worker has not recorded a poll in over 3 minutes. Check its status before sending.</div>}
        {connector?.details?.opt_out_warning && <div role="alert" style={{ color: '#e3b341' }}>Opt-out intake needs review: {connector.details.opt_out_warning}. Matching campaign replies are checked separately for opt-outs.</div>}
        {!!snapshot.sender_blockers.length && <p style={{ color: '#ff7b72' }}>Sender checks: {snapshot.sender_blockers.join(', ')}</p>}
        {snapshot.drafts.map(draft => <div key={draft.id}>Draft {draft.id}: {draft.audience} contacts enrolled, {draft.eligible} with workflow checks clear. {draft.blockers.join('; ') || (draft.audience ? 'Additional delivery checks still apply.' : 'Roster permission evidence required before enrollment.')}</div>)}
        {!!snapshot.legacy_email_status && <div>Earlier roster status labels: {Object.entries(snapshot.legacy_email_status).map(([key, value]) => `${key}: ${value}`).join(' · ')}. These are historical labels, not current delivery confirmation.</div>}
        <p style={{ color: '#8b949e', margin: '6px 0' }}>{snapshot.notice}</p>
      </details>
      <details style={{ fontSize: 12 }}>
        <summary style={{ cursor: 'pointer' }}>Recent send / copy events ({snapshot.events.length})</summary>
        <div aria-live="polite" style={{ maxHeight: 145, overflowY: 'auto' }}>
          {snapshot.events.length ? snapshot.events.map((event, i) => <div key={`${event.updated_at}-${i}`} style={{ borderBottom: '1px solid #21262d', padding: 4 }}>{time(event.updated_at)} · {event.category} · {event.state}{event.code && ` · ${event.code}`}</div>) : <div>No guarded campaign submissions or reply copies recorded.</div>}
        </div>
      </details>
    </>}
  </section>;
}
