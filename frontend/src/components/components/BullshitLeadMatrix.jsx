import React, { useState, useEffect, useCallback } from 'react';

const BullshitLeadMatrix = React.memo(function BullshitLeadMatrix({ backendUrl }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [invoices, setInvoices] = useState([]);

  const fetchLeads = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [leadsRes, accountingRes] = await Promise.all([
        fetch(`${backendUrl}/api/advertising/leads`),
        fetch(`${backendUrl}/api/accounting/entries`)
      ]);
      
      if (!leadsRes.ok) throw new Error(`HTTP ${leadsRes.status}`);
      const data = await leadsRes.json();
      
      if (data.status === 'success') {
        setLeads(data.leads);
      } else {
        setError(data.message || 'Unknown backend error');
      }

      if (accountingRes.ok) {
        const accData = await accountingRes.json();
        if (accData.entries) {
          const mappedInvoices = accData.entries.map(entry => ({
            id: `TRX-${entry.id}`,
            date: entry.date,
            client: entry.category,
            description: entry.description,
            amount: `$${parseFloat(entry.amount).toFixed(2)}`,
            type: entry.entry_type === 'income' ? 'revenue' : 'expense',
            status: 'Paid'
          }));
          setInvoices(mappedInvoices);
        }
      }
    } catch (err) {
      setError('Network fault accessing Lead Matrix. Ensure backend is running on port 8000.');
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const triggerSweep = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${backendUrl}/api/advertising/leads/generate`, { method: 'POST' });
      if (!res.ok) throw new Error(`Sweep HTTP ${res.status}`);
      await fetchLeads();
    } catch (err) {
      setError(`Sweep failed: ${err.message}`);
      setLoading(false);
    }
  };

  if (loading) return <div style={{ color: '#0f0', padding: '20px', fontFamily: 'monospace' }}>Aggregating Target Matrix...</div>;
  if (error) return (
    <div style={{ color: '#ff4444', padding: '20px', fontFamily: 'monospace' }}>
      <strong>Error:</strong> {error}
      <button onClick={fetchLeads} style={{ marginLeft: '16px', background: 'rgba(255,68,68,0.2)', color: '#ff4444', border: '1px solid #ff4444', padding: '4px 12px', cursor: 'pointer' }}>Retry</button>
    </div>
  );

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h2 style={{ margin: 0 }}>Lead Acquisition Matrix</h2>
          <p style={{ margin: '4px 0 0', color: '#666', fontSize: '0.8em' }}>
            {leads.length} lead{leads.length !== 1 ? 's' : ''} · shared store with Advertising CRM
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={fetchLeads} style={styles.refreshBtn}>↻ Refresh</button>
          <button onClick={triggerSweep} style={styles.sweepBtn}>⚡ Force Sweep Override</button>
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Target Identity</th>
              <th style={styles.th}>Contact</th>
              <th style={styles.th}>Domain Vector</th>
              <th style={styles.th}>Comms Link (Email)</th>
              <th style={styles.th}>CRM Status</th>
              <th style={styles.th}>Est. Value</th>
              <th style={styles.th}>Heuristic Profile</th>
              <th style={styles.th}>Acquired</th>
            </tr>
          </thead>
          <tbody>
            {leads.map(lead => (
              <tr key={lead.id} style={styles.tr}>
                <td style={styles.td}>{lead.business_name || '—'}</td>
                <td style={styles.td}>{lead.contact || '—'}</td>
                <td style={styles.td}>
                  {lead.url
                    ? <a href={lead.url.startsWith('http') ? lead.url : `https://${lead.url}`} target="_blank" rel="noreferrer" style={styles.link}>{lead.url}</a>
                    : '—'}
                </td>
                <td style={styles.td}>{lead.email || '—'}</td>
                <td style={styles.td}>
                  <span style={Object.assign({}, styles.statusBadge, statusColor(lead.status))}>
                    {lead.status || 'New'}
                  </span>
                </td>
                <td style={styles.td}>{lead.value || '—'}</td>
                <td style={styles.td}>{lead.heuristic_match || '—'}</td>
                <td style={styles.td}>
                  {lead.date_acquired
                    ? new Date(lead.date_acquired).toLocaleString()
                    : '—'}
                </td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td colSpan="8" style={Object.assign({}, styles.td, { textAlign: 'center', color: '#555' })}>
                  Matrix Empty. Click "Force Sweep Override" to seed leads, or add them in the Advertising CRM tab.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '40px', paddingTop: '20px', borderTop: '1px solid #333' }}>
        <h3 style={{ margin: '0 0 16px 0', color: '#0f0' }}>Lead Invoices & Transactions</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Invoice ID</th>
                <th style={styles.th}>Date</th>
                <th style={styles.th}>Client / Lead</th>
                <th style={styles.th}>Description</th>
                <th style={styles.th}>Amount</th>
                <th style={styles.th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv, idx) => (
                <tr key={inv.id} style={styles.tr}>
                  <td style={{...styles.td, color: '#00ffff'}}>{inv.id}</td>
                  <td style={styles.td}>{inv.date}</td>
                  <td style={styles.td}>{inv.client}</td>
                  <td style={styles.td}>{inv.description}</td>
                  <td style={{...styles.td, color: inv.type === 'revenue' ? '#10b981' : '#ef4444', fontWeight: 'bold'}}>
                    {inv.type === 'revenue' ? '+' : '-'}{inv.amount}
                  </td>
                  <td style={styles.td}>
                    <span style={Object.assign({}, styles.statusBadge, 
                      inv.status === 'Paid' ? { color: '#10b981', borderColor: '#10b981' } : { color: '#f59e0b', borderColor: '#f59e0b' }
                    )}>
                      {inv.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
});

function statusColor(status) {
  switch (status) {
    case 'Closed (Won)':   return { color: '#10b981', borderColor: '#10b981' };
    case 'Closed (Lost)':  return { color: '#ef4444', borderColor: '#ef4444' };
    case 'In Negotiations':return { color: '#f59e0b', borderColor: '#f59e0b' };
    case 'Contacted':      return { color: '#3b82f6', borderColor: '#3b82f6' };
    default:               return { color: '#9ca3af', borderColor: '#9ca3af' };
  }
}

const styles = {
  container: {
    padding: '20px',
    backgroundColor: '#0a0a0a',
    color: '#0f0',
    fontFamily: 'monospace',
    height: '100%',
    overflowY: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottom: '1px solid #333',
    paddingBottom: '12px',
    marginBottom: '20px',
  },
  sweepBtn: {
    backgroundColor: '#330000',
    color: '#ff4444',
    border: '1px solid #ff4444',
    padding: '8px 16px',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  refreshBtn: {
    backgroundColor: 'transparent',
    color: '#0f0',
    border: '1px solid #333',
    padding: '8px 14px',
    cursor: 'pointer',
    fontFamily: 'monospace',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    minWidth: '900px',
  },
  th: {
    borderBottom: '2px solid #0f0',
    padding: '10px 12px',
    textAlign: 'left',
    color: '#fff',
    whiteSpace: 'nowrap',
  },
  tr: {
    borderBottom: '1px solid #1a1a1a',
  },
  td: {
    padding: '10px 12px',
    color: '#0f0',
    fontSize: '0.88em',
  },
  link: {
    color: '#00ffff',
    textDecoration: 'none',
  },
  statusBadge: {
    border: '1px solid',
    borderRadius: '4px',
    padding: '2px 8px',
    fontSize: '0.8em',
    whiteSpace: 'nowrap',
  },
};

export default BullshitLeadMatrix;
