/** @typedef {{id: string | number, date: string, category: string, description: string, entry_type: string, amount: string | number, is_tax_deductible: boolean, schedule_c_code?: string, receipt_note?: string, verification?: unknown}} AccountingEntry */
import { useState, useEffect, useRef } from "react";
import FinancialAccountBoundary from "/src/components/FinancialAccountBoundary.jsx";
import ReceiptReconciliationPanel from "/src/components/ReceiptReconciliationPanel.jsx";

// Resilient Inline SVG Icon Helpers with explicit width & height
const FileSpreadsheetIcon = () => (
  <svg style={{ width: '16px', height: '16px', color: '#38bdf8', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const CalculatorIcon = () => (
  <svg style={{ width: '16px', height: '16px', color: '#c084fc', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
  </svg>
);

const SparklesIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#fbbf24', display: 'inline-block' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
  </svg>
);

const TrashIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#f87171' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

const SendIcon = () => (
  <svg style={{ width: '14px', height: '14px', color: '#ffffff' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>
);

/** @param {{spinning: boolean}} props */
const RefreshIcon = ({ spinning }) => (
  <svg style={{ width: '14px', height: '14px', color: '#9ca3af' }} className={spinning ? "animate-spin" : ""} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

export function AccountingOverviewAvailability() {
  return <section aria-label="Verified accounting totals" style={{ background: '#0f172a', padding: '16px', borderRadius: '12px', border: '1px solid #1e293b' }}>
    <h3 style={{ marginTop: 0 }}>Verified accounting totals</h3>
    <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Manual entries are unreconciled. They do not establish provider payouts, deductible expenses or tax results.</p>
    <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
      {['Gross revenue', 'Deductible expenses', 'State tax', 'Tax savings'].map(label => <div key={label}>
        <dt style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{label}</dt>
        <dd style={{ margin: '4px 0', fontWeight: 'bold' }}>Unavailable</dd>
      </div>)}
    </dl>
  </section>;
}

export function AccountingTaxAvailability() {
  return <section aria-label="Tax record availability" style={{ background: '#0f172a', padding: '16px', borderRadius: '10px', border: '1px solid #1e293b' }}>
    <h3>Tax results: Unavailable</h3>
    <p style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Reconciled records and validated rules for the relevant year, entity and jurisdiction are required. Manual entries and fixed formulas do not establish tax liability, deductions or savings.</p>
  </section>;
}

/** @param {{backendUrl?: string}} props */
export default function MasterAccountingTab({ backendUrl }) {
  return <FinancialAccountBoundary>{request => <AccountingContent key={backendUrl} backendUrl={backendUrl} financialRequest={request} />}</FinancialAccountBoundary>;
}

/** @param {{backendUrl?: string, financialRequest: ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"]}} props */
function AccountingContent({ backendUrl, financialRequest }) {
  const [activeSubPage, setActiveSubPage] = useState("spreadsheet");
  const [isChatOpen, setIsChatOpen] = useState(false);
  
  const [entries, setEntries] = useState(/** @type {AccountingEntry[]} */ ([]));
  const [entriesError, setEntriesError] = useState(/** @type {string | null} */ (null));
  const [loading, setLoading] = useState(true);
  const [editingRowId, setEditingRowId] = useState(/** @type {string | number | null} */ (null));
  const [editingRowData, setEditingRowData] = useState(/** @type {Partial<AccountingEntry>} */ ({}));

  const [chatMessages, setChatMessages] = useState([
    { sender: "ai", text: "Use this assistant for manual ledger commands. Replies are unverified and do not establish payments, tax liability, deductions or savings." }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [sendingChat, setSendingChat] = useState(false);

  const chatEndRef = useRef(/** @type {HTMLDivElement | null} */ (null));
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, sendingChat]);

  const [newEntry, setNewEntry] = useState({
    date: new Date().toISOString().split("T")[0],
    category: "Hardware & Electronics",
    description: "",
    entry_type: "expense",
    amount: "",
    is_tax_deductible: false,
    schedule_c_code: "Other",
    receipt_note: ""
  });

  const readGeneration = useRef(0);
  const fetchAccountingData = async () => {
    const generation = ++readGeneration.current;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    setLoading(true);
    setEntries([]);
    setEntriesError(null);
    try {
      const response = await financialRequest(`${backendUrl}/api/accounting/entries`, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error('Manual entries unavailable');
      const data = await response.json();
      if (data.status !== 'success' || !Array.isArray(data.entries)) throw new Error('Invalid manual entries');
      if (generation === readGeneration.current) setEntries(data.entries);
    } catch {
      if (generation !== readGeneration.current) return;
      setEntries([]);
      setEntriesError('Manual entries are unavailable or this account lacks access. Refresh to retry.');
    } finally {
      clearTimeout(timeout);
      if (generation === readGeneration.current) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccountingData();
  }, [backendUrl]);

  /** @param {import("react").FormEvent} e */
const handleAddEntry = async (e) => {
    e.preventDefault();
    if (!newEntry.description || !newEntry.amount) return;

    try {
      const payload = {
        ...newEntry,
        amount: newEntry.amount.includes(".") ? newEntry.amount.padEnd(newEntry.amount.indexOf(".") + 3, "0") : `${newEntry.amount}.00`
      };

      const res = await financialRequest(`${backendUrl}/api/accounting/entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setNewEntry({
          date: new Date().toISOString().split("T")[0],
          category: "Hardware & Electronics",
          description: "",
          entry_type: "expense",
          amount: "",
          is_tax_deductible: false,
          schedule_c_code: "Other",
          receipt_note: ""
        });
        fetchAccountingData();
      }
    } catch (err) {
      setEntriesError(errorMessage(err));
    }
  };

  /** @param {string | number} id */
const handleDeleteEntry = async (id) => {
    if (!window.confirm("Delete this row from the ledger?")) return;
    try {
      const res = await financialRequest(`${backendUrl}/api/accounting/entry/${id}`, { method: "DELETE" });
      if (res.ok) {
        fetchAccountingData();
      }
    } catch (err) {
      setEntriesError(errorMessage(err));
    }
  };

  const handleStartEdit = (/** @type {AccountingEntry} */ row) => {
    setEditingRowId(row.id);
    setEditingRowData({ ...row });
  };

  const handleSaveEdit = async () => {
    try {
      const res = await financialRequest(`${backendUrl}/api/accounting/entry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(Object.entries(editingRowData).filter(([key]) => key !== "verification")))
      });
      if (res.ok) {
        setEditingRowId(null);
        fetchAccountingData();
      }
    } catch (err) {
      setEntriesError(errorMessage(err));
    }
  };

  const handleSendChat = async (/** @type {import("react").FormEvent} */ e) => {
    e.preventDefault();
    if (!chatInput.trim() || sendingChat) return;

    const userText = chatInput;
    setChatInput("");
    setChatMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setSendingChat(true);

    try {
      const res = await financialRequest(`${backendUrl}/api/accounting/chat-assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText })
      });

      if (res.ok) {
        const data = await res.json();
        setChatMessages((prev) => [...prev, { sender: "ai", text: data.reply }]);
        fetchAccountingData();
      }
    } catch (err) {
      setChatMessages((prev) => [...prev, { sender: "ai", text: errorMessage(err) }]);
    } finally {
      setSendingChat(false);
    }
  };


  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#020617', color: '#f8fafc', padding: '16px', gap: '16px', overflowY: 'auto', boxSizing: 'border-box' }}>
      
      {entriesError && <p role="alert">{entriesError}</p>}
      <ReceiptReconciliationPanel backendUrl={backendUrl} financialRequest={financialRequest} entries={entries} />
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', background: '#0f172a', padding: '12px 16px', borderRadius: '12px', border: '1px solid #1e293b' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem', fontWeight: '800', background: 'linear-gradient(to right, #34d399, #38bdf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Stehouwer Publishing LLC Master Accounting
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '12px', fontSize: '0.7rem', fontWeight: '600', background: 'rgba(52, 211, 153, 0.1)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
              Manual records
            </span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: '2px 0 0 0' }}>
            Manual ledger entries • Unreconciled records
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '8px', fontSize: '0.75rem', fontWeight: '600', background: 'linear-gradient(to right, #9333ea, #4f46e5)', color: '#ffffff', border: 'none', cursor: 'pointer', boxShadow: '0 4px 12px rgba(147, 51, 234, 0.3)' }}
          >
            <SparklesIcon /> {isChatOpen ? "Hide AI Assistant" : "Accounting assistant"}
          </button>
          <button
            onClick={fetchAccountingData}
            style={{ padding: '6px 10px', borderRadius: '8px', background: '#1e293b', color: '#cbd5e1', border: '1px solid #334155', cursor: 'pointer' }}
            title="Refresh Data"
          >
            <RefreshIcon spinning={loading} />
          </button>
        </div>
      </div>

      <AccountingOverviewAvailability />

      {/* Sub-Tab Selector */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
        <button
          onClick={() => setActiveSubPage("spreadsheet")}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '600', background: activeSubPage === "spreadsheet" ? '#0284c7' : '#0f172a', color: '#ffffff', border: '1px solid #1e293b', cursor: 'pointer' }}
        >
          <FileSpreadsheetIcon /> Interactive Excel Ledger Grid
        </button>
        <button
          onClick={() => setActiveSubPage("tax_suite")}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: '600', background: activeSubPage === "tax_suite" ? '#7e22ce' : '#0f172a', color: '#ffffff', border: '1px solid #1e293b', cursor: 'pointer' }}
        >
          <CalculatorIcon /> Tax record availability
        </button>
      </div>

      {/* Main Body */}
      <div style={{ display: 'flex', gap: '16px', flex: 1, position: 'relative' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {activeSubPage === "spreadsheet" && (
            <>
              {/* Operational Guide Note */}
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '8px', border: '1px solid #1e293b', fontSize: '0.72rem', color: '#94a3b8' }}>
                💡 <strong>Unreconciled manual ledger:</strong> Click any cell's <strong>Edit</strong> button to modify row values inline, click <strong>Save Row</strong> to persist changes to SQLite, or click <strong>Quick Add</strong> below to add new hardware/electricity expenses or API income.
              </div>

              {/* Add New Entry Row Form */}
              <form onSubmit={handleAddEntry} style={{ background: '#0f172a', padding: '12px', borderRadius: '10px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#cbd5e1' }}>
                  + Quick Add New Transaction Entry
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
                  <input
                    type="date"
                    value={newEntry.date}
                    onChange={(e) => setNewEntry({...newEntry, date: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                    required
                  />
                  <select
                    value={newEntry.entry_type}
                    onChange={(e) => setNewEntry({...newEntry, entry_type: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                  >
                    <option value="expense">Expense (-)</option>
                    <option value="income">Income (+)</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Description (e.g. RTX 4090 GPU)"
                    value={newEntry.description}
                    onChange={(e) => setNewEntry({...newEntry, description: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                    required
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Amount ($)"
                    value={newEntry.amount}
                    onChange={(e) => setNewEntry({...newEntry, amount: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                    required
                  />
                  <select
                    value={newEntry.category}
                    onChange={(e) => setNewEntry({...newEntry, category: e.target.value})}
                    style={{ background: '#020617', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px 8px', fontSize: '0.75rem' }}
                  >
                    <option value="Hardware & Electronics">Hardware / GPU</option>
                    <option value="Cloud Infrastructure">Cloud / Servers</option>
                    <option value="Utilities & Electricity">Electricity</option>
                    <option value="Software Subscriptions">Software</option>
                    <option value="Commercial API Payouts">API Income</option>
                    <option value="Other Business">Other Business</option>
                  </select>
                  <button
                    type="submit"
                    style={{ background: '#059669', color: '#ffffff', border: 'none', borderRadius: '6px', padding: '6px 12px', fontSize: '0.75rem', fontWeight: 'bold', cursor: 'pointer' }}
                  >
                    Add Row
                  </button>
                </div>
              </form>

              {/* Excel Grid Table */}
              <div style={{ background: '#0f172a', borderRadius: '10px', border: '1px solid #1e293b', overflow: 'hidden' }}>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.75rem', color: '#cbd5e1' }}>
                    <thead>
                      <tr style={{ background: '#020617', borderBottom: '1px solid #1e293b', color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.65rem', fontWeight: 'bold' }}>
                        <th style={{ padding: '8px 12px' }}>Date</th>
                        <th style={{ padding: '8px 12px' }}>Category</th>
                        <th style={{ padding: '8px 12px' }}>Description</th>
                        <th style={{ padding: '8px 12px' }}>Type</th>
                        <th style={{ padding: '8px 12px' }}>Amount ($)</th>
                        <th style={{ padding: '8px 12px' }}>Manual deduction flag</th>
                        <th style={{ padding: '8px 12px' }}>Schedule C Code</th>
                        <th style={{ padding: '8px 12px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {entries.length === 0 ? (
                        <tr>
                          <td colSpan={8} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                            {loading ? 'Loading manual entries…' : entriesError || 'No manual entries returned. This does not establish zero revenue or expenses.'}
                          </td>
                        </tr>
                      ) : (
                        entries.map((item) => {
                          const isEditing = editingRowId === item.id;
                          return (
                            <tr key={item.id} style={{ borderBottom: '1px solid rgba(30, 41, 59, 0.6)', background: isEditing ? 'rgba(30, 41, 59, 0.8)' : 'transparent' }}>
                              <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>
                                {isEditing ? (
                                  <input type="date" value={editingRowData.date} onChange={(e) => setEditingRowData({...editingRowData, date: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px' }} />
                                ) : item.date}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                {isEditing ? (
                                  <input type="text" value={editingRowData.category} onChange={(e) => setEditingRowData({...editingRowData, category: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px' }} />
                                ) : item.category}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                {isEditing ? (
                                  <input type="text" value={editingRowData.description} onChange={(e) => setEditingRowData({...editingRowData, description: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px' }} />
                                ) : item.description}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '0.65rem', fontWeight: 'bold', background: item.entry_type === 'income' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(248, 113, 113, 0.15)', color: item.entry_type === 'income' ? '#34d399' : '#f87171' }}>
                                  {item.entry_type.toUpperCase()}
                                </span>
                              </td>
                              <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontWeight: 'bold', color: item.entry_type === 'income' ? '#34d399' : '#f8fafc' }}>
                                {isEditing ? (
                                  <input type="number" step="0.01" value={editingRowData.amount} onChange={(e) => setEditingRowData({...editingRowData, amount: e.target.value})} style={{ background: '#020617', border: '1px solid #334155', color: '#fff', fontSize: '0.7rem', padding: '2px 4px', borderRadius: '4px', width: '80px' }} />
                                ) : `$${item.amount}`}
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                {item.is_tax_deductible ? (
                                  <span style={{ color: '#34d399', fontWeight: '600' }}>Flagged manually</span>
                                ) : (
                                  <span style={{ color: '#64748b' }}>Standard</span>
                                )}
                              </td>
                              <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{item.schedule_c_code}</td>
                              <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                                {isEditing ? (
                                  <button onClick={handleSaveEdit} style={{ background: '#0284c7', color: '#fff', border: 'none', padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', cursor: 'pointer' }}>
                                    Save
                                  </button>
                                ) : (
                                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                                    <button onClick={() => handleStartEdit(item)} style={{ background: 'transparent', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.7rem' }}>
                                      Edit
                                    </button>
                                    <button onClick={() => handleDeleteEntry(item.id)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }} title="Delete">
                                      <TrashIcon />
                                    </button>
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {activeSubPage === "tax_suite" && <AccountingTaxAvailability />}

        </div>

        {/* Embedded AI Advisor Chat Drawer */}
        {isChatOpen && (
          <div style={{ width: '320px', background: '#0f172a', borderRadius: '10px', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', height: '450px' }}>
            <div style={{ padding: '10px', background: '#020617', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <SparklesIcon />
                <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#f8fafc' }}>Stehouwer Financial AI</span>
              </div>
              <button onClick={() => setIsChatOpen(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.75rem' }}>✕</button>
            </div>

            <p style={{ padding: '0 10px', color: '#fbbf24', fontSize: '0.75rem' }}>Assistant replies are unverified manual ledger output. Payment and tax claims have not been validated.</p>
            <div style={{ flex: 1, padding: '10px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.7rem' }}>
              {chatMessages.map((msg, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: msg.sender === "user" ? "flex-end" : "flex-start" }}>
                  <div style={{ maxWidth: '85%', padding: '8px', borderRadius: '8px', background: msg.sender === "user" ? '#9333ea' : '#1e293b', color: '#ffffff' }}>
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleSendChat} style={{ padding: '8px', background: '#020617', borderTop: '1px solid #1e293b', display: 'flex', gap: '6px' }}>
              <input
                type="text"
                placeholder="Command: 'Log $150 electricity'"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                style={{ flex: 1, background: '#0f172a', border: '1px solid #334155', color: '#ffffff', borderRadius: '6px', padding: '6px', fontSize: '0.7rem' }}
              />
              <button type="submit" disabled={sendingChat} style={{ background: '#9333ea', border: 'none', color: '#fff', borderRadius: '6px', padding: '6px 10px', cursor: 'pointer' }}>
                <SendIcon />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
