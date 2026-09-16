import React, { useMemo, useEffect } from 'react';
import { useAppStore } from './useAppStore.js';
import { Archive, ExternalLink, ShieldAlert, KeyRound, Database, RefreshCw, Eye, AlertTriangle } from 'lucide-react';

export default function OsintDataVaultTab() {
  const { osintVaultItems, setOsintVaultItems, fetchPastSavedData } = useAppStore();

  useEffect(() => {
    fetchPastSavedData();
  }, []);

  const groupedItems = useMemo(() => {
    return osintVaultItems.reduce((acc, item) => {
      const cat = item.category || 'Uncategorized';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(item);
      return acc;
    }, {});
  }, [osintVaultItems]);

  const handleClearVault = () => {
    if (confirm("Are you sure you want to clear the entire OSINT Data Vault? This cannot be undone.")) {
      setOsintVaultItems([]);
    }
  };

  const renderIconForCategory = (category) => {
    if (category.toLowerCase().includes('crypto')) return <Database size={16} className="text-yellow-400" />;
    if (category.toLowerCase().includes('finance') || category.toLowerCase().includes('bank')) return <Database size={16} className="text-green-400" />;
    if (category.toLowerCase().includes('breach') || category.toLowerCase().includes('leak')) return <ShieldAlert size={16} className="text-red-400" />;
    if (category.toLowerCase().includes('rapidapi')) return <RefreshCw size={16} className="text-blue-400" />;
    return <Archive size={16} className="text-gray-400" />;
  };

  const renderActionButtons = (item) => {
    if (item.category.toLowerCase().includes('rapidapi')) {
      return (
        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 text-blue-300 hover:bg-blue-500/40 rounded border border-blue-500/30 text-xs transition-colors">
          <Eye size={14} /> Review Raw Data
        </button>
      );
    }
    if (item.category.toLowerCase().includes('breach')) {
      return (
        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-300 hover:bg-red-500/40 rounded border border-red-500/30 text-xs transition-colors">
          <ShieldAlert size={14} /> Investigate Breach
        </button>
      );
    }
    return (
      <button className="flex items-center gap-1.5 px-3 py-1.5 bg-yellow-500/20 text-yellow-300 hover:bg-yellow-500/40 rounded border border-yellow-500/30 text-xs transition-colors">
        <KeyRound size={14} /> Initiate Password Reset
      </button>
    );
  };

  if (osintVaultItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400 border border-dashed border-white/20 rounded-xl bg-black/20 backdrop-blur-md p-6 shadow-2xl">
        <Archive size={48} className="mb-4 text-cyan-500 opacity-50" />
        <h3 className="text-xl font-bold text-gray-200" style={{ textShadow: '0 0 10px rgba(0,255,255,0.3)' }}>Vault is Empty</h3>
        <p className="text-sm mt-2 text-center max-w-sm text-gray-400">
          Run RapidAPI Recon or Lost Property scans. The collected intelligence will be automatically sorted and safely stored here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Archive size={20} className="text-blue-400" />
          <h2 className="text-xl font-semibold text-gray-100">OSINT Data Vault</h2>
        </div>
        <button 
          onClick={handleClearVault}
          className="text-xs px-3 py-1.5 bg-red-500/10 text-red-400 hover:bg-red-500/20 rounded border border-red-500/30 transition-colors"
        >
          Clear Vault
        </button>
      </div>

      <div className="space-y-8">
        {Object.entries(groupedItems).map(([category, items]) => (
          <div key={category} className="bg-black/30 backdrop-blur-xl border border-white/10 rounded-xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
            <div className="flex items-center gap-2 mb-6 pb-3 border-b border-white/5">
              {renderIconForCategory(category)}
              <h3 className="text-lg font-bold text-white uppercase tracking-widest drop-shadow-md">{category} <span className="text-cyan-400 text-sm ml-2">({items.length})</span></h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {items.map((item) => (
                <div key={item.id} className="bg-gradient-to-b from-gray-900/80 to-black/80 backdrop-blur-md border border-white/10 rounded-lg p-4 flex flex-col justify-between hover:border-cyan-500/50 hover:shadow-[0_0_15px_rgba(0,255,255,0.15)] transition-all duration-300">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-mono text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                      <span className="text-[10px] text-gray-500 uppercase tracking-wider">{item.source}</span>
                    </div>
                    
                    <div className="text-sm text-gray-300 font-mono mb-3 relative" style={{ wordBreak: 'break-word' }}>
                      {item.data && (item.data.message || item.data.detail) ? (
                        <div className="mb-2 p-2 bg-red-900/20 border border-red-500/30 rounded flex items-start gap-2">
                          <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                          <span className="text-xs text-red-200">{item.data.message || item.data.detail}</span>
                        </div>
                      ) : item.data ? (
                        Object.entries(item.data).filter(([key]) => key !== 'snippet' && key !== 'url').slice(0, 10).map(([key, val]) => (
                          <div key={key} className="mb-2 bg-black/40 p-2 rounded border border-white/5">
                            <span className="text-[10px] text-cyan-500/70 uppercase tracking-wider block mb-1 font-sans">{key}</span>
                            <span className="text-xs text-gray-200">
                              {typeof val === 'object' ? JSON.stringify(val).substring(0, 80) : String(val).substring(0, 100)}{String(val).length > 100 ? '...' : ''}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="text-xs text-gray-500">No structured data found.</div>
                      )}
                      
                      {item.data && item.data.url && (
                        <div className="mt-2">
                          <a href={item.data.url} target="_blank" rel="noreferrer" className="text-cyan-400 text-xs break-all hover:underline drop-shadow-sm">
                            View Source
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="pt-3 border-t border-white/10 flex justify-end">
                    {renderActionButtons(item)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
