import React, { useState } from 'react';
import { Search, ShieldAlert, FileText, Database, Code, ExternalLink, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';
import { useAppStore } from './useAppStore.js';

export default function LostPropertyTab({ backendUrl: propBackendUrl }) {
  const backendUrl = propBackendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : 'https://ai-bs-dashboard.web.app');
  
  const [targetEmail, setTargetEmail] = useState('');
  const [scanType, setScanType] = useState('all');

  const {
    lostPropertyLoading: loading,
    lostPropertyAccounts: accounts,
    lostPropertyScanStatus: scanStatus,
    lostPropertyError: error,
    runLostPropertyScan,
    lostPropertyWebLoading: webLoading,
    lostPropertyWebResults: webResults,
    lostPropertyWebError: webError,
    runLostPropertyWebScan,
    osintVaultItems
  } = useAppStore();

  const triggerScan = async () => {
    await runLostPropertyScan();
  };

  const triggerWebScan = async (selectedType = scanType) => {
    if (!targetEmail) return;
    await runLostPropertyWebScan(targetEmail, selectedType);
  };

  const getCategoryColor = (cat) => {
    switch (cat?.toLowerCase()) {
      case 'crypto': return '#f59e0b';
      case 'finance': return '#10b981';
      case 'social': return '#3b82f6';
      case 'utility': return '#8b5cf6';
      default: return '#6b7280';
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'CRITICAL_LEAK':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 rounded flex items-center gap-1"><AlertTriangle className="w-3 h-3"/> CRITICAL LEAK</span>;
      case 'PASTEBIN_LEAK':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded flex items-center gap-1"><FileText className="w-3 h-3"/> PASTEBIN EXPOSURE</span>;
      case 'CODE_LEAK':
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded flex items-center gap-1"><Code className="w-3 h-3"/> REPO CODE LEAK</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded">PUBLIC INDEX</span>;
    }
  };

  return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', color: '#fff' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 'bold' }}>Lost Property Scanner</h2>
          <p style={{ opacity: 0.7, margin: '0.5rem 0 0', fontSize: '0.9rem' }}>Surf your email history using Stehouwer LLM to discover forgotten Crypto, Finance, and Social accounts.</p>
        </div>
        <button 
          onClick={triggerScan}
          disabled={loading}
          style={{ 
            padding: '0.8rem 1.5rem', 
            background: loading ? '#4b5563' : 'linear-gradient(90deg, #8b5cf6 0%, #d946ef 100%)', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '6px', 
            fontWeight: 'bold', 
            cursor: loading ? 'not-allowed' : 'pointer' 
          }}
        >
          {loading ? 'Scanning...' : 'Run Email Scanner'}
        </button>
      </div>

      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.2)', borderLeft: '4px solid #ef4444', borderRadius: '4px' }}>
          {error}
        </div>
      )}

      {scanStatus && !error && (
        <div style={{ padding: '1rem', background: 'rgba(139, 92, 246, 0.2)', borderLeft: '4px solid #8b5cf6', borderRadius: '4px' }}>
          {scanStatus}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {accounts.length === 0 && !loading && !error && (
          <div style={{ opacity: 0.5, gridColumn: '1 / -1', textAlign: 'center', padding: '3rem' }}>
            No accounts found in cache. Click "Run Email Scanner" to begin.
          </div>
        )}
        
        {accounts.map((acc, i) => (
          <div key={i} className="glass-panel" style={{ padding: '1.5rem', borderRadius: '8px', borderTop: `3px solid ${getCategoryColor(acc.category)}`, background: '#111' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{acc.company}</h3>
              <span style={{ 
                fontSize: '0.8rem', 
                padding: '0.2rem 0.6rem', 
                borderRadius: '12px', 
                background: `${getCategoryColor(acc.category)}40`,
                color: getCategoryColor(acc.category),
                fontWeight: 'bold'
              }}>
                {acc.category}
              </span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem', opacity: 0.8 }}>
              <div><strong>From:</strong> <span style={{ fontFamily: 'monospace' }}>{acc.sender}</span></div>
              <div><strong>Subject:</strong> {acc.subject}</div>
            </div>
            
            <div style={{ marginTop: '1.5rem' }}>
              <a 
                href={`https://google.com/search?q=${encodeURIComponent(acc.company + ' login')}`} 
                target="_blank" 
                rel="noreferrer"
                style={{
                  display: 'block',
                  textAlign: 'center',
                  padding: '0.5rem',
                  background: 'rgba(255,255,255,0.1)',
                  color: '#fff',
                  textDecoration: 'none',
                  borderRadius: '4px',
                  transition: 'background 0.2s'
                }}
              >
                Search Login Page
              </a>
            </div>
          </div>
        ))}
      </div>

      <hr style={{ borderColor: '#333', margin: '2rem 0' }} />

      {/* Web OSINT & Pastebin Leak Sniffer */}
      <div className="space-y-4">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ margin: 0, color: '#f87171', fontSize: '1.4rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldAlert className="w-5 h-5 text-red-400" />
              DuckDuckGo OSINT & Leak Sniffer
            </h2>
            <p style={{ opacity: 0.7, margin: '0.5rem 0 0', fontSize: '0.85rem' }}>
              Search public web indexes, Pastebin dumps, breach collections, and code repositories for exposed credentials.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'center' }}>
            <input 
              type="email" 
              placeholder="Enter target email address..." 
              value={targetEmail}
              onChange={(e) => setTargetEmail(e.target.value)}
              style={{ padding: '0.7rem 1rem', borderRadius: '6px', border: '1px solid #444', background: '#111', color: '#fff', width: '280px', fontSize: '0.85rem' }}
            />
            <button 
              onClick={() => triggerWebScan(scanType)}
              disabled={webLoading || !targetEmail}
              style={{ 
                padding: '0.7rem 1.4rem', 
                background: webLoading || !targetEmail ? '#4b5563' : 'linear-gradient(90deg, #ef4444 0%, #b91c1c 100%)', 
                color: '#fff', 
                border: 'none', 
                borderRadius: '6px', 
                fontWeight: 'bold', 
                cursor: webLoading || !targetEmail ? 'not-allowed' : 'pointer',
                fontSize: '0.85rem'
              }}
            >
              {webLoading ? 'Sniffing Leaks...' : 'Run OSINT Scan'}
            </button>
          </div>
        </div>

        {/* Scan Type Filter Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {[
            { id: 'all', label: 'All Sources', icon: Search },
            { id: 'pastebin', label: 'Pastebin & Text Dumps', icon: FileText },
            { id: 'breach', label: 'Breach Databases', icon: Database },
            { id: 'code_leaks', label: 'Code & Token Leaks', icon: Code },
          ].map(type => {
            const Icon = type.icon;
            const active = scanType === type.id;
            return (
              <button
                key={type.id}
                onClick={() => {
                  setScanType(type.id);
                  if (targetEmail) triggerWebScan(type.id);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                  active 
                    ? 'bg-red-600 text-white shadow' 
                    : 'bg-[#1a1a1a] text-gray-400 hover:bg-[#252525] border border-[#333]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {type.label}
              </button>
            );
          })}
        </div>

        {webError && (
          <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.2)', borderLeft: '4px solid #ef4444', borderRadius: '4px', fontSize: '0.85rem' }}>
            {webError}
          </div>
        )}

        {webResults.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.2rem', marginTop: '1rem' }}>
            {webResults.map((hit, i) => (
              <div key={i} style={{ padding: '1.2rem', borderRadius: '8px', borderTop: `3px solid #f87171`, background: '#121212', border: '1px solid #222' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.8rem', gap: '0.5rem' }}>
                  <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 'bold', color: '#fff', lineClamp: 1 }}>{hit.title}</h3>
                  {getSeverityBadge(hit.severity)}
                </div>

                <div style={{ marginBottom: '0.8rem' }}>
                  <a href={hit.url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', fontSize: '0.8rem', wordBreak: 'break-all', display: 'flex', itemsCenter: 'center', gap: '0.3rem' }}>
                    <ExternalLink className="w-3 h-3 inline shrink-0" /> {hit.url}
                  </a>
                </div>

                <div style={{ fontSize: '0.8rem', opacity: 0.85, background: '#1a1a1a', padding: '0.8rem', borderRadius: '4px', border: '1px solid #2a2a2a', color: '#d1d5db', fontFamily: 'sans-serif', whiteSpace: 'pre-wrap' }}>
                  {hit.snippet}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historical Vault Data */}
      <div style={{ marginTop: '40px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '20px', paddingLeft: '1.5rem', paddingRight: '1.5rem', paddingBottom: '2rem' }}>
        <h4 style={{ margin: '0 0 16px 0', color: '#94a3b8' }}>Saved Recon Data (from Vault)</h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
          {osintVaultItems
            .filter(item => item.category.includes('Lost Property') || item.category === 'Breach Leak')
            .map(item => (
              <div key={item.id} style={{ background: 'rgba(30, 41, 59, 0.5)', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '8px', padding: '16px', wordBreak: 'break-word' }}>
                <div style={{ marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <span style={{ fontSize: '0.7rem', color: '#10b981', textTransform: 'uppercase', display: 'block' }}>{item.source} - {item.category}</span>
                  <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{new Date(item.timestamp).toLocaleString()}</span>
                </div>
                {item.data ? Object.entries(item.data).filter(([key]) => key !== 'snippet' && key !== 'url').slice(0, 10).map(([key, val]) => (
                  <div key={key} style={{ marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', display: 'block' }}>{key}</span>
                    <span style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>{typeof val === 'object' ? JSON.stringify(val) : String(val).substring(0, 150)}{String(val).length > 150 ? '...' : ''}</span>
                  </div>
                )) : (
                  <div style={{ color: '#64748b', fontSize: '0.8rem' }}>No structured data found.</div>
                )}
                {item.data && item.data.url && (
                  <div style={{ marginTop: '8px' }}>
                    <a href={item.data.url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', fontSize: '0.8rem', wordBreak: 'break-all' }}>View Source</a>
                  </div>
                )}
              </div>
            ))}
          {osintVaultItems.filter(item => item.category.includes('Lost Property') || item.category === 'Breach Leak').length === 0 && (
            <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No historical data saved yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}
