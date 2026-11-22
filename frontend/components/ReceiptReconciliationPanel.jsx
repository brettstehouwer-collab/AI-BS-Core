import { useEffect, useRef, useState } from "react";

/** @param {number | string | null | undefined} value @returns {bigint | null} */
function receiptAmountCents(value) {
  if (value == null || (typeof value === 'number' && (!Number.isFinite(value) || Math.abs(value) > Number.MAX_SAFE_INTEGER / 100))) return null;
  const match = /^(\d+)(?:\.(\d+))?$/.exec(String(value));
  if (!match) return null;
  const fraction = (match[2] || '').replace(/0+$/, '');
  if (fraction.length > 2) return null;
  return BigInt(match[1]) * 100n + BigInt(fraction.padEnd(2, '0'));
}
/** @param {number | string | null | undefined} left @param {number | string | null | undefined} right */
function receiptAmountsEqual(left, right) {
  const leftCents = receiptAmountCents(left), rightCents = receiptAmountCents(right);
  return leftCents !== null && rightCents !== null && leftCents === rightCents;
}

/** @param {{backendUrl?: string, financialRequest: ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"], entries: Array<{entry_type: string, amount: number | string, id: string | number, description: string}>}} props */
export default function ReceiptReconciliationPanel({ backendUrl = '', financialRequest, entries }) {
  const [receipts, setReceipts] = useState(/** @type {Array<{"id": string, "provider": string, "mode": string, "status": string, "gross": string, "fee": string | null, "net": string | null}>} */ ([]));
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [selection, setSelection] = useState(/** @type {Record<string, Partial<Record<string, string>>>} */ ({}));
  const generation = useRef(0);
  const refresh = async () => {
    const current = ++generation.current; setLoading(true); setError(''); setReceipts([]);
    try {
      const response = await financialRequest(`${backendUrl}/api/accounting/receipts`);
      const data = await response.json();
      if (!Array.isArray(data.receipts)) throw new Error('Receipt records are unavailable.');
      if (current === generation.current) setReceipts(data.receipts);
    } catch (err) { if (current === generation.current) setError((err instanceof Error ? err.message : String(err))); }
    finally { if (current === generation.current) setLoading(false); }
  };
  useEffect(() => { refresh(); return () => { generation.current++; }; }, [backendUrl, entries]);
  /** @param {{"id": string}} receipt */
const match = async  receipt => {
    if (busy) return;
    const chosen = selection[receipt.id] || {};
    if (!chosen.income) { setError('Choose the matching manual income record.'); return; }
    setBusy(true); setError('');
    try {
      await financialRequest(`${backendUrl}/api/accounting/receipts/${receipt.id}/reconcile`, {
        method:'POST', body:JSON.stringify({entry_id:Number(chosen.income),fee_entry_id:chosen.fee ? Number(chosen.fee) : null})
      });
      await refresh();
    } catch (err) { setError((err instanceof Error ? err.message : String(err))); }
    finally { setBusy(false); }
  };
  return <section aria-label="Payment receipt matching" style={{background:'#0f172a',padding:16,borderRadius:12}}>
    <h3>Payment receipt matching</h3>
    <p>Match confirmed provider receipts to your manual income and fee records. Test receipts remain test only. Overall financial totals remain Unavailable until coverage is verified. Access and fulfillment remain held.</p>
    <button disabled={loading || busy} onClick={refresh}>Refresh receipts</button>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Loading receipt records…</p> : !receipts.length && !error ? <p>No owned receipts returned. This does not establish zero payments.</p> : null}
    {receipts.map( 
receipt => <article key={receipt.id} style={{borderTop:'1px solid #334155',marginTop:12,paddingTop:12}}>
      <p>{receipt.provider} · {receipt.mode === 'test' ? 'Test receipt' : 'Provider receipt'} · {receipt.status.replaceAll('_',' ')}</p>
      <p>Gross: {receipt.gross} USD · Fee: {receipt.fee ?? 'Unavailable'} · Net: {receipt.net ?? 'Unavailable'}</p>
      {receipt.status === 'ready_to_match' && <>
        {['income','fee'].map(kind => <label key={kind} style={{display:'inline-block',marginRight:12}}>
          {kind === 'income' ? 'Income record' : 'Fee expense record'}
          <select aria-label={kind === 'income' ? 'Income record' : 'Fee expense record'} value={selection[receipt.id]?.[kind] || ''}
            onChange={e => setSelection(previous => ({...previous,[receipt.id]:{...previous[receipt.id],[kind]:e.target.value}}))}>
            <option value="">Choose record</option>
            {entries.filter(entry => entry.entry_type === (kind === 'income' ? 'income' : 'expense') && receiptAmountsEqual(entry.amount, kind === 'income' ? receipt.gross : receipt.fee)).map(entry =>
              <option key={entry.id} value={entry.id}>#{entry.id} · {entry.description} · {entry.amount} USD</option>)}
          </select>
        </label>)}
        <button disabled={busy} onClick={() => match(receipt)}>Match receipt</button>
      </>}
    </article>)}
  </section>;
}
