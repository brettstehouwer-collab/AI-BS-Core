/** @typedef {{id: string | number, date: string, source_account: string, dest_account: string, asset: string, amount: string, usd_price_at_transfer: string, usd_total_value: string, fee_amount: string, fee_asset: string, tx_hash: string, category: string, notes: string}} CryptoTransfer */
import { useState, useEffect, useRef } from 'react';
import FinancialAccountBoundary from '/src/components/FinancialAccountBoundary.jsx';
import { decimalProductUSD } from '/src/utils/accountingSession.js';

const getEffectiveApiBase = () => {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'https:' || (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1')) {
      return 'https://api.brettstehouwer.live';
    }
    if (window.location.protocol === 'http:' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      return 'http://localhost:8080';
    }
  }
  return 'https://api.brettstehouwer.live';
};

export default function CryptoAccountingTab() {
  return <FinancialAccountBoundary>{request => <CryptoAccountingContent financialRequest={request} />}</FinancialAccountBoundary>;
}
/** @param {{financialRequest: ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"]}} props */
function CryptoAccountingContent({ financialRequest }) {
  const [transfers, setTransfers] = useState(/** @type {CryptoTransfer[]} */ ([]));
  const [readError, setReadError] = useState('');
  const readGeneration = useRef(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [assetFilter, setAssetFilter] = useState('all');
  const [showModal, setShowModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMsg, setToastMsg] = useState('');
  useState('');

  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    source_account: '',
    dest_account: '',
    asset: 'PRL',
    amount: '',
    usd_price_at_transfer: '',
    usd_total_value: '',
    fee_amount: '0.00',
    fee_asset: 'USD',
    tx_hash: '',
    category: 'mining_income',
    notes: ''
  });

  const fetchTransfers = async () => {
    const generation = ++readGeneration.current;
    setTransfers([]); setReadError(''); setLoading(true);
    try {
      const res = await financialRequest(`${getEffectiveApiBase()}/api/accounting/crypto-transfers`);
      const data = await res.json();
      if (generation === readGeneration.current) setTransfers(data.transfers || []);
    } catch (err) {
      if (generation === readGeneration.current) setReadError(errorMessage(err));
    } finally {
      if (generation === readGeneration.current) setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransfers();
    // Manual refresh avoids overlapping financial reads.
  }, []);

  

  /** @param {'mining' | 'exchange_transfer' | 'swap_usdc' | 'sofi_ach'} presetType */
const handlePreset = (presetType) => {
    setFormData({date: new Date().toISOString().split('T')[0], source_account: '', dest_account: '',
      asset: '', amount: '', usd_price_at_transfer: '', usd_total_value: '', fee_amount: '0', fee_asset: 'USD',
      tx_hash: '', category: ({mining:'mining_income',exchange_transfer:'wallet_transfer',swap_usdc:'exchange_swap',sofi_ach:'direct_deposit_ach'})[presetType] || 'wallet_transfer', notes: ''});
    setShowModal(true);
  };

  /** @param {string} amt @param {string} price */
const handleAmountChange = (amt, price) => {

    setFormData(prev => ({
      ...prev,
      amount: amt,
      usd_price_at_transfer: price,
      usd_total_value: decimalProductUSD(amt, price)
    }));
  };

  /** @param {import("react").FormEvent} e */
const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
    if (!formData.amount || !formData.source_account || !formData.dest_account) return;

    setIsSubmitting(true);
    try {
      const apiBase = getEffectiveApiBase();
      const payload = {
        ...formData,
        amount: formData.amount,
        usd_price_at_transfer: formData.usd_price_at_transfer,
        usd_total_value: formData.usd_total_value,
        fee_amount: formData.fee_amount || "0"
      };

      const res = await financialRequest(`${apiBase}/api/accounting/crypto-transfers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setToastMsg('✅ Unreconciled manual transfer saved.');
        setShowModal(false);
        fetchTransfers();
      } else {
        setToastMsg('❌ Error saving transfer.');
      }
    } catch (err) {
      setToastMsg(`❌ Network error: ${errorMessage(err)}`);
    } finally {
      setIsSubmitting(false);
      setTimeout(() => setToastMsg(''), 4000);
    }
  };

  /** @param {string | number} id */
const handleDelete = async (id) => {
    if (!window.confirm('Delete this crypto transfer log?')) return;
    try {
      const apiBase = getEffectiveApiBase();
      const res = await financialRequest(`${apiBase}/api/accounting/crypto-transfers/${id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setToastMsg('🗑️ Transfer removed from ledger.');
        fetchTransfers();
      }
    } catch (err) {
      setToastMsg(`❌ Delete failed: ${errorMessage(err)}`);
    } finally {
      setTimeout(() => setToastMsg(''), 3000);
    }
  };

  const filteredTransfers = transfers.filter(t => {
    const matchesSearch = 
      t.source_account.toLowerCase().includes(search.toLowerCase()) ||
      t.dest_account.toLowerCase().includes(search.toLowerCase()) ||
      (t.tx_hash && t.tx_hash.toLowerCase().includes(search.toLowerCase())) ||
      (t.notes && t.notes.toLowerCase().includes(search.toLowerCase()));
    const matchesCategory = categoryFilter === 'all' || t.category === categoryFilter;
    const matchesAsset = assetFilter === 'all' || t.asset === assetFilter;
    return matchesSearch && matchesCategory && matchesAsset;
  });

  const getCategoryBadge = (/** @type {string} */ cat) => {
    switch (cat) {
      case 'mining_income':
        return <span style={{ background: '#122e1a', color: '#3fb950', border: '1px solid #238636', padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: '700' }}>⛏️ Mined Income</span>;
      case 'direct_deposit_ach':
        return <span style={{ background: '#1c2d42', color: '#58a6ff', border: '1px solid #1f6feb', padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: '700' }}>🏛️ Manual ACH category</span>;
      case 'exchange_swap':
        return <span style={{ background: '#301c38', color: '#d2a8ff', border: '1px solid #8957e5', padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: '700' }}>💱 Exchange Swap</span>;
      case 'wallet_transfer':
        return <span style={{ background: '#2d2212', color: '#d29922', border: '1px solid #9e6a03', padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: '700' }}>🔄 Wallet Transfer</span>;
      default:
        return <span style={{ background: '#21262d', color: '#8b949e', border: '1px solid #30363d', padding: '2px 8px', borderRadius: '4px', fontSize: '0.72rem' }}>{cat}</span>;
    }
  };

  return (
    <div style={{ padding: '24px', backgroundColor: '#0d1117', color: '#c9d1d9', minHeight: '100%', boxSizing: 'border-box', fontFamily: 'Segoe UI, sans-serif' }}>
      
      {/* Toast Alert */}
      {toastMsg && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          background: toastMsg.includes('✅') ? '#122e1a' : (toastMsg.includes('🗑️') ? '#301c38' : '#3c1e1e'),
          color: '#fff',
          border: '1px solid #30363d',
          padding: '12px 20px',
          borderRadius: '8px',
          zIndex: 9999,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          fontSize: '0.9rem',
          fontWeight: '600'
        }}>
          {toastMsg}
        </div>
      )}

      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, #161b22 0%, #0d1117 100%)',
        border: '1px solid #30363d',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div>
          <h2 style={{ margin: 0, color: '#58a6ff', fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>📊</span> Crypto Accounting & Tax Transfer Tracker
          </h2>
          <p style={{ margin: '6px 0 0 0', color: '#8b949e', fontSize: '0.85rem' }}>
            Record manual transfers. Wallet links, bank deposits, fees and tax treatment remain unverified.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <a
            href="#" onClick={async event => {
              event.preventDefault();
              try {
                const response = await financialRequest(`${getEffectiveApiBase()}/api/accounting/crypto-transfers/export-csv`);
                const url = URL.createObjectURL(await response.blob());
                const link = document.createElement('a'); link.href = url; link.download = 'AI_BS_Manual_Transfers.csv'; link.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              } catch (error) { setToastMsg(errorMessage(error)); }
            }}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#21262d',
              color: '#3fb950',
              border: '1px solid #238636',
              padding: '8px 16px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '0.85rem',
              textDecoration: 'none',
              cursor: 'pointer'
            }}
          >
            <span>📥</span> Export manual CSV
          </a>

          <button
            onClick={() => {
              handlePreset('mining');
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#238636',
              color: '#ffffff',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '0.85rem',
              cursor: 'pointer'
            }}
          >
            <span>➕</span> Log Transfer
          </button>
        </div>
      </div>

      <section role="status" style={{padding:16,border:'1px solid #30363d',borderRadius:8}}>
        Bank and wallet linkage: Unavailable. No verified bank connection or automatic payout is established here.
        <div style={{display:'flex',gap:12,marginTop:12}}>
          {(/** @type {('mining'|'exchange_transfer'|'swap_usdc'|'sofi_ach')[]} */ (['mining','exchange_transfer','swap_usdc','sofi_ach'])).map(kind => <button key={kind} onClick={() => handlePreset(kind)}>New manual {kind.replaceAll('_',' ')} record</button>)}
        </div>
      </section>

      {readError && <p role="alert">{readError} Records are unavailable.</p>}
      {/* Verified totals require independent reconciliation. */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '14px',
        marginBottom: '20px'
      }}>
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#8b949e', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '4px' }}>TOTAL TRANSFERRED VOLUME</div>
          <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#58a6ff' }}>
            Unavailable
          </div>
          <div style={{ fontSize: '0.72rem', color: '#8b949e', marginTop: '4px' }}>Verified coverage unavailable</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #238636', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#8b949e', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '4px' }}>VERIFIED MINING REVENUE</div>
          <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#3fb950' }}>
            Unavailable
          </div>
          <div style={{ fontSize: '0.72rem', color: '#8b949e', marginTop: '4px' }}>Manual values are unreconciled</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #1f6feb', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#8b949e', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '4px' }}>VERIFIED BANK DEPOSITS</div>
          <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#79c0ff' }}>
            Unavailable
          </div>
          <div style={{ fontSize: '0.72rem', color: '#8b949e', marginTop: '4px' }}>Bank receipt evidence unavailable</div>
        </div>

        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: '8px', padding: '16px' }}>
          <div style={{ color: '#8b949e', fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '4px' }}>NETWORK & EXCHANGE FEES</div>
          <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#d29922' }}>
            Unavailable
          </div>
          <div style={{ fontSize: '0.72rem', color: '#8b949e', marginTop: '4px' }}>Fee currency and tax treatment unverified</div>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div style={{
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '12px 16px',
        marginBottom: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Search account, note, or tx..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              background: '#0d1117',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '0.82rem',
              minWidth: '220px'
            }}
          />

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{
              background: '#0d1117',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              padding: '6px 10px',
              borderRadius: '6px',
              fontSize: '0.82rem'
            }}
          >
            <option value="all">All Categories</option>
            <option value="mining_income">⛏️ Mined Income</option>
            <option value="direct_deposit_ach">🏛️ Manual ACH category</option>
            <option value="exchange_swap">💱 Exchange Swap</option>
            <option value="wallet_transfer">🔄 Wallet Transfer</option>
          </select>

          <select
            value={assetFilter}
            onChange={(e) => setAssetFilter(e.target.value)}
            style={{
              background: '#0d1117',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              padding: '6px 10px',
              borderRadius: '6px',
              fontSize: '0.82rem'
            }}
          >
            <option value="all">All Assets</option>
            <option value="PRL">Pearl (PRL)</option>
            <option value="USDC">USDC</option>
            <option value="USD">USD (Cash)</option>
          </select>
        </div>

        <div style={{ color: '#8b949e', fontSize: '0.8rem' }}>
          Showing <strong>{filteredTransfers.length}</strong> of <strong>{transfers.length}</strong> entries
        </div>
      </div>

      {/* Ledger Table */}
      <div style={{
        background: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        overflowX: 'auto'
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: '#21262d', borderBottom: '1px solid #30363d', color: '#8b949e' }}>
              <th style={{ padding: '10px 14px' }}>Date</th>
              <th style={{ padding: '10px 14px' }}>Category</th>
              <th style={{ padding: '10px 14px' }}>Asset & Amount</th>
              <th style={{ padding: '10px 14px' }}>USD Value</th>
              <th style={{ padding: '10px 14px' }}>Source $\to$ Destination</th>
              <th style={{ padding: '10px 14px' }}>Fee</th>
              <th style={{ padding: '10px 14px' }}>Notes & Ref</th>
              <th style={{ padding: '10px 14px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#8b949e' }}>
                  Loading transfer ledger...
                </td>
              </tr>
            ) : filteredTransfers.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#8b949e' }}>
                  {readError ? "Manual records are unavailable. Refresh to retry." : transfers.length === 0 
                    ? "No manual records returned. This does not establish zero transfers or verified payouts."
                    : "No transfers match the selected filters."}
                </td>
              </tr>
            ) : (
              filteredTransfers.map(item => (
                <tr key={item.id} style={{ borderBottom: '1px solid #21262d' }}>
                  <td style={{ padding: '10px 14px', whiteSpace: 'nowrap', color: '#c9d1d9' }}>{item.date}</td>
                  <td style={{ padding: '10px 14px' }}>{getCategoryBadge(item.category)}</td>
                  <td style={{ padding: '10px 14px', fontWeight: '600', color: '#f0f6fc' }}>
                    {item.amount} {item.asset}
                  </td>
                  <td style={{ padding: '10px 14px', fontWeight: '700', color: item.category === 'mining_income' ? '#3fb950' : (item.category === 'direct_deposit_ach' ? '#79c0ff' : '#c9d1d9') }}>
                    ${item.usd_total_value}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ color: '#8b949e', fontSize: '0.75rem' }}>From: <span style={{ color: '#c9d1d9' }}>{item.source_account}</span></div>
                    <div style={{ color: '#8b949e', fontSize: '0.75rem' }}>To: <strong style={{ color: item.dest_account.includes('SoFi') ? '#58a6ff' : '#c9d1d9' }}>{item.dest_account}</strong></div>
                  </td>
                  <td style={{ padding: '10px 14px', color: '#d29922' }}>
                    {Number(item.fee_amount) > 0 ? `${item.fee_amount} ${item.fee_asset}` : '$0.00'}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <div style={{ color: '#c9d1d9', fontSize: '0.78rem' }}>{item.notes}</div>
                    {item.tx_hash && (
                      <code style={{ color: '#8b949e', fontSize: '0.7rem' }}>{item.tx_hash.slice(0, 16)}...</code>
                    )}
                  </td>
                  <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                    <button
                      onClick={() => handleDelete(item.id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#f85149',
                        cursor: 'pointer',
                        fontSize: '0.85rem'
                      }}
                      title="Delete entry"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Manual Entry / Preset Modal */}
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000
        }}>
          <div style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '12px',
            padding: '24px',
            width: '100%',
            maxWidth: '540px',
            boxShadow: '0 16px 32px rgba(0,0,0,0.8)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, color: '#58a6ff', fontSize: '1.1rem' }}>📝 Log Crypto Transfer</h3>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', fontSize: '1.1rem' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Date</label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                  >
                    <option value="mining_income">⛏️ Mined Income (Taxable)</option>
                    <option value="wallet_transfer">🔄 Wallet Transfer</option>
                    <option value="exchange_swap">💱 Exchange Swap</option>
                    <option value="direct_deposit_ach">🏛️ Manual ACH category</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Source Account</label>
                <input
                  type="text"
                  value={formData.source_account}
                  onChange={(e) => setFormData({ ...formData, source_account: e.target.value })}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Destination Account</label>
                <input
                  type="text"
                  value={formData.dest_account}
                  onChange={(e) => setFormData({ ...formData, dest_account: e.target.value })}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Asset</label>
                  <input
                    type="text"
                    value={formData.asset}
                    onChange={(e) => setFormData({ ...formData, asset: e.target.value.toUpperCase() })}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Amount</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.amount}
                    onChange={(e) => handleAmountChange(e.target.value, formData.usd_price_at_transfer)}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>USD Total Value</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.usd_total_value}
                    onChange={(e) => setFormData({ ...formData, usd_total_value: e.target.value })}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#3fb950', fontWeight: '700', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Fee Amount</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.fee_amount}
                    onChange={(e) => setFormData({ ...formData, fee_amount: e.target.value })}
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Tx Hash / Ref ID</label>
                  <input
                    type="text"
                    value={formData.tx_hash}
                    onChange={(e) => setFormData({ ...formData, tx_hash: e.target.value })}
                    placeholder="e.g. 0x... or ACH-ID"
                    style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#8b949e', marginBottom: '4px' }}>Notes / Description</label>
                <input
                  type="text"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  style={{ width: '100%', background: '#0d1117', border: '1px solid #30363d', color: '#fff', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', boxSizing: 'border-box' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  style={{ background: '#21262d', border: '1px solid #30363d', color: '#c9d1d9', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{ background: '#238636', border: 'none', color: '#fff', padding: '8px 18px', borderRadius: '6px', cursor: 'pointer', fontWeight: '700' }}
                >
                  {isSubmitting ? 'Saving...' : 'Save Transfer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Owned wallet evidence */}
      <section role="status">Owned wallet balances and custody records: Unavailable. Verified account evidence is required.</section>

    </div>
  );
}

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
