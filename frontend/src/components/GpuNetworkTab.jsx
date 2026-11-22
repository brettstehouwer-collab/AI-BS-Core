import { useEffect, useRef, useState } from 'react';
import FinancialAccountBoundary from '/src/components/FinancialAccountBoundary.jsx';
import { createNetworkWorkspaceLoader } from '/src/utils/networkWorkspace.js';

const panelStyle = { background: '#161b22', border: '1px solid #30363d', borderRadius: 10, padding: 20 };

/** @param {{backendUrl?: string}} props */
export default function GpuNetworkTab({ backendUrl }) {
  return <FinancialAccountBoundary>{request =>
    <NetworkWorkspace key={backendUrl || ''} backendUrl={backendUrl} financialRequest={request} />
  }</FinancialAccountBoundary>;
}

/** @param {{backendUrl?:string,financialRequest:ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"]}} props */
function NetworkWorkspace({ backendUrl, financialRequest }) {
  const [state, setState] = useState(/** @type {{status:string,error?:string}} */ ({ status: 'loading' }));
  const loaderRef = useRef(/** @type {ReturnType<typeof createNetworkWorkspaceLoader>|null} */ (null));
  useEffect(() => {
    const loader = createNetworkWorkspaceLoader({ request: financialRequest, backendUrl, onState: setState });
    loaderRef.current = loader;
    loader.refresh();
    return () => { loader.stop(); if (loaderRef.current === loader) loaderRef.current = null; };
  }, [backendUrl, financialRequest]);
  return <NetworkWorkspaceView state={state} onRefresh={() => loaderRef.current?.refresh()} />;
}

/** @param {{state?:{status:string,error?:string},onRefresh:()=>void}} props */
export function NetworkWorkspaceView({ state = { status: 'loading' }, onRefresh }) {
  return <div style={{ width: '100%', height: '100%', background: '#090d16', color: '#c9d1d9',
    padding: 24, overflowY: 'auto', boxSizing: 'border-box' }}>
    <h2 style={{ color: '#58a6ff', marginTop: 0 }}>GPU Network</h2>
    <p>Compute earnings, treasury balances and worker controls require verified records.</p>
    <button type="button" disabled={state.status === 'loading'} onClick={onRefresh}>Refresh status</button>
    {state.status === 'loading' && <p role="status">Checking network availability…</p>}
    {state.status === 'error' && <p role="alert">{state.error}</p>}
    {state.status === 'unavailable' && <p role="status">Network records are unavailable. Payments and job dispatch remain held.</p>}

    <section aria-label="Compute records" style={{ ...panelStyle, marginTop: 20 }}>
      <h3>Compute records</h3>
      <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        {['Available balance', 'Total earned', 'Payouts redeemed', 'GPU earning rate', 'Compute hours', 'Treasury balance'].map(label =>
          <div key={label}><dt>{label}</dt><dd style={{ margin: '6px 0', fontWeight: 700 }}>Unavailable</dd></div>)}
      </dl>
      <p>Missing records do not establish a zero balance or completed payment.</p>
    </section>

    <section aria-label="Worker controls" style={{ ...panelStyle, marginTop: 20 }}>
      <h3>Worker controls</h3>
      <p>Hardware and worker activity: Unavailable</p>
      <p>Idle policy: Unavailable</p>
      <p>A worker must acknowledge an enforced idle policy before idle-only execution can be offered.</p>
    </section>

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 20, marginTop: 20 }}>
      <section aria-label="Payout hold" style={panelStyle}>
        <h3>Payouts held</h3>
        <p>Verified owned earnings, payment reconciliation and durable payout recovery are required.</p>
        <button type="button" disabled>Redeem payout — held</button>
      </section>
      <section aria-label="Job dispatch hold" style={panelStyle}>
        <h3>Job dispatch held</h3>
        <p>Verified ownership, reserved budgets and approved worker isolation are required.</p>
        <p>Job queue and assignment status: Unavailable</p>
        <button type="button" disabled>Submit job — held</button>
      </section>
    </div>
  </div>;
}