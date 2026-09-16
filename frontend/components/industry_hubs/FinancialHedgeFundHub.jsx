import React, { useState, useEffect } from 'react';
import { Play, Activity, Shield, Zap, TrendingUp, Bitcoin } from 'lucide-react';

export default function FinancialHedgeFundHub({ BACKEND_URL = "http://127.0.0.1:8000" }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  // Live Feed State
  const [liveCrypto, setLiveCrypto] = useState(null);

  const runTool = async (toolId) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/industry_tools/financialhedgefund/${toolId}`, { method: 'POST' });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: "Backend connection failed." });
    }
    setLoading(false);
  };

  useEffect(() => {
    // Poll the backend data feed for finance_ticker
    const fetchFeed = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/feeds/latest/finance_ticker?limit=1`);
        const data = await res.json();
        if (data.status === 'success' && data.data && data.data.length > 0) {
          setLiveCrypto(data.data[0].payload);
        }
      } catch (e) {
        console.error("Failed to fetch live crypto feed", e);
      }
    };
    
    fetchFeed();
    const interval = setInterval(fetchFeed, 5000);
    return () => clearInterval(interval);
  }, [BACKEND_URL]);

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-900 text-slate-200">
      <h2 className="text-2xl font-bold mb-6 text-emerald-400">Financial & Hedge Fund Command Center</h2>
      
      {/* Live Market Feed Panel */}
      <div className="mb-8 bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
        <div className="flex items-center gap-3 mb-4 border-b border-slate-700 pb-3">
          <TrendingUp className="text-emerald-400" />
          <h3 className="text-lg font-bold">Live Market Feed (via Broker Ingestion)</h3>
          <span className="ml-auto flex items-center gap-2 text-xs text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            LIVE
          </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {liveCrypto ? (
            ['bitcoin', 'ethereum', 'solana'].map((coin) => {
              const data = liveCrypto[coin];
              if(!data) return null;
              const isUp = data.usd_24h_change > 0;
              return (
                <div key={coin} className="bg-slate-900 p-4 rounded-lg border border-slate-700 flex flex-col">
                  <div className="flex justify-between items-center mb-2">
                    <span className="uppercase font-bold text-slate-400 flex items-center gap-2">
                      <Bitcoin size={16} /> {coin}
                    </span>
                    <span className={`text-sm ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isUp ? '+' : ''}{data.usd_24h_change?.toFixed(2)}%
                    </span>
                  </div>
                  <span className="text-2xl font-bold text-slate-100">${data.usd?.toLocaleString()}</span>
                  <span className="text-xs text-slate-500 mt-2">Vol: ${(data.usd_24h_vol / 1000000).toFixed(2)}M</span>
                </div>
              );
            })
          ) : (
            <div className="col-span-3 text-center py-4 text-slate-500 animate-pulse">
              Awaiting payload from Message Broker...
            </div>
          )}
        </div>
      </div>
      
      <p className="mb-8 text-slate-400">Interactive diagnostic tools and remote-execution utilities for Financial & Hedge Fund.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <Activity className="text-blue-400" />
            <h3 className="text-lg font-bold">Deep Telemetry Scan</h3>
          </div>
          <p className="text-sm text-slate-400 mb-4">Run an extensive diagnostic overlay against the Financial & Hedge Fund database vectors.</p>
          <button 
            onClick={() => runTool('telemetry_scan')}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded font-semibold transition"
          >
            {loading ? "Scanning..." : "Execute Scan"}
          </button>
        </div>

        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <Zap className="text-amber-400" />
            <h3 className="text-lg font-bold">Autonomous Override</h3>
          </div>
          <p className="text-sm text-slate-400 mb-4">Deploy Swarm Agents to automatically resolve Financial & Hedge Fund system bottlenecks.</p>
          <button 
            onClick={() => runTool('autonomous_override')}
            disabled={loading}
            className="w-full bg-amber-600 hover:bg-amber-500 text-slate-900 py-2 rounded font-semibold transition"
          >
            {loading ? "Deploying..." : "Trigger Override"}
          </button>
        </div>
      </div>

      {result && (
        <div className="mt-8 p-4 bg-slate-950 rounded-xl border border-emerald-500/30 shadow-inner">
          <h4 className="font-bold text-emerald-500 mb-2">Execution Result</h4>
          <pre className="text-xs text-emerald-300 whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
