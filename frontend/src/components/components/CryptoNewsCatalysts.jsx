import React, { useEffect, useState } from 'react';

// Public advisory telemetry. This component has no order, strategy or flag APIs.
export default function CryptoNewsCatalysts({ apiBase = '' }) {
  const [view, setView] = useState({ status: 'loading', items: [] });
  useEffect(() => {
    let active = true;
    let pollTimer;
    let controller;
    const poll = async () => {
      controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 6000);
      try {
        const response = await fetch(`${apiBase.replace(/\/$/, '')}/api/telemetry/news-catalysts`, {
          signal: controller.signal, cache: 'no-store',
        });
        if (!response.ok) throw new Error('unavailable');
        const data = await response.json();
        if (!Array.isArray(data.items)) throw new Error('invalid telemetry');
        if (active) setView({ ...data, status: data.configured ? data.worker_state : 'not_configured' });
      } catch {
        if (active) setView({ status: 'unavailable', items: [] });
      } finally {
        clearTimeout(timeout);
        if (active) pollTimer = setTimeout(poll, 45000);
      }
    };
    poll();
    return () => { active = false; clearTimeout(pollTimer); controller?.abort(); };
  }, [apiBase]);

  const statusText = {
    loading: 'Checking news telemetry…',
    not_configured: 'News monitoring is not configured.',
    unavailable: 'News telemetry is unavailable.',
    no_recent_poll: 'No recent feed poll observed. Stored signals may be stale.',
    recent_poll_observed: 'Recent public feed poll observed.',
  }[view.status] || 'News telemetry status unknown.';
  return (
    <section aria-label="Crypto news catalysts" style={{ padding: 18, border: '1px solid #30363d', borderRadius: 10, background: '#161b22' }}>
      <h3 style={{ margin: '0 0 8px', color: '#c9d1d9' }}>Crypto news catalysts</h3>
      <p role="status" style={{ color: '#8b949e', margin: '0 0 8px' }}>{statusText}</p>
      <p style={{ color: '#8b949e', fontSize: 12 }}>Advisory only · Local model estimates · Trading remains disabled</p>
      {!!view.counts?.RETRY && <p style={{ color: '#e3b341' }}>Analysis retries pending: {view.counts.RETRY}</p>}
      {!!view.counts?.FAILED && <p style={{ color: '#e3b341' }}>Analysis unavailable for {view.counts.FAILED} articles.</p>}
      {view.feeds?.some(feed => feed.status !== 'OK') && <p style={{ color: '#e3b341' }}>Some feeds could not be read.</p>}
      {view.items.length === 0 ? <p style={{ color: '#8b949e' }}>No recent signals meet the display threshold.</p> : (
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {view.items.slice(0, 10).map(item => (
            <li key={item.article_hash} style={{ marginBottom: 12, color: '#c9d1d9' }}>
              <strong>{item.title}</strong>
              <div style={{ color: '#8b949e', fontSize: 12 }}>
                {item.source} · {Array.isArray(item.detected_tokens) ? item.detected_tokens.join(', ') : ''}
                {' · '}{item.catalyst_category} · Impact {Number(item.sentiment_score).toFixed(2)}
                {' · '}Model confidence {Math.round(Number(item.confidence) * 100)}% (uncalibrated)
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
