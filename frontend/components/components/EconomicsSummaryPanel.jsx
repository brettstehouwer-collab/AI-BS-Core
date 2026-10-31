/** @typedef {{owner:string|null,status:string,summary:import("/types/domain").EconomicsSummary|null,error:string|null}} EconomicsViewState */
import { useEffect, useState } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '/src/firebase.js';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';
import { getApiBase } from '/src/config/api';
import { createEconomicsPoller, readEconomicsSummary, presentEconomicsMetric } from '/src/utils/economicsSummary.js';

/** @type {[string,[string,string,string][]][]} */
const GROUPS = [
  ['Revenue', [
    ['revenue.monthly_recurring_revenue', 'Monthly recurring revenue', 'USD'],
    ['revenue.active_subscriptions', 'Active subscriptions', 'count'],
    ['revenue.recent_invoices_paid', 'Paid invoices in window', 'count'],
    ['revenue.total_volume_30d', 'Revenue in window', 'USD'],
  ]],
  ['Compute and energy', [
    ['llm_costs.openai_gpt4_cost', 'OpenAI costs', 'USD'],
    ['llm_costs.anthropic_claude_cost', 'Anthropic costs', 'USD'],
    ['llm_costs.local_ollama_vram_kwh', 'Local model energy', 'kWh'],
    ['llm_costs.total_compute_30d', 'Total compute costs', 'USD'],
  ]],
  ['Security and service', [
    ['security_telemetry.total_api_requests_30d', 'API requests', 'count'],
    ['security_telemetry.unauthorized_access_attempts', 'Unauthorized attempts', 'count'],
    ['security_telemetry.rate_limit_hits', 'Rate limit events', 'count'],
    ['security_telemetry.avg_latency_ms', 'Average latency', 'ms'],
  ]],
  ['Profitability', [
    ['margins.net_profit_30d', 'Net profit in window', 'USD'],
    ['margins.profit_margin_pct', 'Profit margin', 'percent'],
  ]],
];
/** @type {EconomicsViewState} */
const idle = { owner: null, status: 'signed_out', summary: null, error: null };
const dateLabel = (/** @type {string|undefined} */ value) => new Date(value || '').toLocaleString();

/** @param {{title?:string,apiBase?:string}} props */
export default function EconomicsSummaryPanel({ title = 'System economics', apiBase }) {
  const [state, setState] = useState(idle);
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    let disposed = false;
    /** @type {ReturnType<typeof createEconomicsPoller>|undefined} */
    let poller;
    const unsubscribe = onAuthStateChanged(auth, user => {
      poller?.stop();
      if (disposed) return;
      setState(user ? { owner: user.uid, status: 'loading', summary: null, error: null } : idle);
      if (!user) return;
      const owner = user.uid;
      poller = createEconomicsPoller({
        request: ({ signal }) => readEconomicsSummary({ apiBase: apiBase || getApiBase(), signal,
          getHeaders: () => chatAuthHeaders({}, owner), isCurrentIdentity: () => auth.currentUser?.uid === owner }),
        onState: next => {
          if (!disposed && auth.currentUser?.uid === owner) {
            setState({ ...next, owner }); setClock(Date.now());
          }
        },
      });
      poller.start();
    });
    // Evidence must expire even while the page waits for its next request.
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => { disposed = true; unsubscribe(); poller?.stop(); clearInterval(timer); };
  }, [apiBase]);

  // Do not expose the prior account while Firebase delivers an identity change.
  const visible = state.owner && state.owner === auth.currentUser?.uid ? state : idle;
  return <EconomicsSummaryView state={visible} clock={clock} title={title} />;
}

/** @param {{state:EconomicsViewState,clock?:number,title?:string}} props */
export function EconomicsSummaryView({ state, clock = Date.now(), title = 'System economics' }) {
  const summary = state.summary;
  return (
    <section className="p-6 text-slate-200 bg-slate-900 rounded-xl" aria-label={title}>
      <h2 className="text-2xl font-bold mb-3">{title}</h2>
      <p className="text-sm text-slate-400 mb-4">Only current, reconciled records support financial values. Missing evidence is shown as unavailable.</p>
      <p role="status" className="text-sm mb-4">
        {state.status === 'signed_out' ? 'Sign in to view financial record availability.'
          : state.status === 'loading' ? 'Checking financial records…'
            : state.status === 'error' ? state.error
              : 'Financial record availability checked.'}
      </p>
      {summary && <p className="text-sm text-slate-400 mb-4">
        Requested window: {dateLabel(summary.window.start)} – {dateLabel(summary.window.end)}. Currency: USD.
        {' '}Source coverage: {summary.window.coverage}. Checked: {dateLabel(summary.timestamp)}.
      </p>}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {GROUPS.map(([label, metrics]) => (
          <section key={label} className="border border-slate-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3">{label}</h3>
            <dl className="space-y-4">
              {metrics.map(([key, name, unit]) => {
                const presentation = presentEconomicsMetric(summary?.metrics?.[key], unit, clock);
                return <div key={key}>
                  <div className="flex flex-wrap justify-between gap-2">
                    <dt className="text-sm text-slate-300">{name}</dt>
                    <dd className={`font-semibold ${presentation.status === 'verified' ? 'text-emerald-300' : 'text-slate-400'}`}>{presentation.value}</dd>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{presentation.reason}</p>
                  {presentation.status === 'verified' && <p className="text-xs text-slate-400 mt-1">
                    Source: {presentation.source}. Observed: {dateLabel(presentation.observedAt)}. Valid until: {dateLabel(presentation.freshUntil)}.
                  </p>}
                </div>;
              })}
            </dl>
          </section>
        ))}
      </div>
    </section>
  );
}
