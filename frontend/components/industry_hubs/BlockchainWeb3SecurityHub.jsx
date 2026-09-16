import React, { useState } from 'react';
import { Play, Activity, Shield, Zap } from 'lucide-react';

export default function BlockchainWeb3SecurityHub({ BACKEND_URL }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const runTool = async (toolId) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/industry_tools/blockchainweb3security/${toolId}`, { method: 'POST' });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: "Backend connection failed." });
    }
    setLoading(false);
  };

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-900 text-slate-200">
      <h2 className="text-2xl font-bold mb-6 text-emerald-400">Blockchain & Web3 Security Command Center</h2>
      <p className="mb-8 text-slate-400">Interactive diagnostic tools and remote-execution utilities for Blockchain & Web3 Security.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Tool 1 */}
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <Activity className="text-blue-400" />
            <h3 className="text-lg font-bold">Deep Telemetry Scan</h3>
          </div>
          <p className="text-sm text-slate-400 mb-4">Run an extensive diagnostic overlay against the Blockchain & Web3 Security database vectors.</p>
          <button 
            onClick={() => runTool('telemetry_scan')}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded font-semibold transition"
          >
            {loading ? "Scanning..." : "Execute Scan"}
          </button>
        </div>

        {/* Tool 2 */}
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <Zap className="text-amber-400" />
            <h3 className="text-lg font-bold">Autonomous Override</h3>
          </div>
          <p className="text-sm text-slate-400 mb-4">Deploy Swarm Agents to automatically resolve Blockchain & Web3 Security system bottlenecks.</p>
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
