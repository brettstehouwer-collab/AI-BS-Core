import React, { useState } from 'react';
import { Play, Activity, Shield, Zap, Search, BrainCircuit } from 'lucide-react';
import PdfViewerComponent from '../PdfViewerComponent';

export default function QuantumComputingResearchHub({ BACKEND_URL = "http://127.0.0.1:8000" }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  // RAG State
  const [ragQuery, setRagQuery] = useState('');
  const [ragLoading, setRagLoading] = useState(false);
  const [ragResult, setRagResult] = useState(null);
  const [activePdf, setActivePdf] = useState(null);

  const runTool = async (toolId) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/industry_tools/quantumcomputingresearch/${toolId}`, { method: 'POST' });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: "Backend connection failed." });
    }
    setLoading(false);
  };

  const runRagQuery = async () => {
    if(!ragQuery.trim()) return;
    setRagLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/rag/query`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          industry_id: "quantum",
          query_text: ragQuery,
          synthesize: true
        })
      });
      const data = await res.json();
      setRagResult(data);
      
      // Auto-load the first source PDF if available
      if (data.sources && data.sources.length > 0) {
          const firstSource = data.sources[0]?.source;
          if (firstSource) {
              setActivePdf(`${BACKEND_URL}/datasets/DeepTech/${firstSource}`);
          }
      }
    } catch (e) {
      setRagResult({ error: "Backend RAG connection failed." });
    }
    setRagLoading(false);
  };

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-900 text-slate-200">
      <h2 className="text-2xl font-bold mb-6 text-emerald-400">Quantum Computing Command Center</h2>
      
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
        
        {/* Left Column: RAG Chat */}
        <div className="flex flex-col gap-4">
          <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
            <div className="flex items-center gap-3 mb-4 text-purple-400">
              <BrainCircuit size={24} />
              <h3 className="text-lg font-bold">Deep Tech Research RAG Agent</h3>
            </div>
            
            <div className="flex gap-2 mb-4">
              <input 
                type="text" 
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runRagQuery()}
                placeholder="Ask a quantum physics or cryptography research question..."
                className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
              />
              <button 
                onClick={runRagQuery}
                disabled={ragLoading}
                className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded flex items-center justify-center transition"
              >
                <Search size={18} />
              </button>
            </div>

            {ragLoading && (
              <div className="text-sm text-purple-400 animate-pulse flex items-center gap-2">
                <BrainCircuit size={16} className="animate-spin" /> Synthesizing with stehouwer_llm...
              </div>
            )}

            {ragResult && !ragLoading && (
              <div className="mt-4 p-4 bg-slate-950 rounded border border-purple-500/30">
                <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                  {ragResult.answer || ragResult.error}
                </p>
                {ragResult.sources && ragResult.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800">
                    <span className="text-xs text-slate-500 block mb-2">Sources Cited:</span>
                    <div className="flex flex-wrap gap-2">
                      {ragResult.sources.map((src, i) => (
                        <button 
                          key={i}
                          onClick={() => setActivePdf(`${BACKEND_URL}/datasets/DeepTech/${src.source}`)}
                          className="text-xs bg-slate-800 border border-slate-700 px-2 py-1 rounded hover:bg-slate-700 text-purple-300"
                        >
                          {src.source} (Chunk {src.page_chunk})
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: PDF Viewer */}
        <div className="flex flex-col">
          <PdfViewerComponent pdfUrl={activePdf} title="Deep Tech Research Reference" />
        </div>
      </div>
      
      {/* Existing Tools */}
      <h3 className="text-xl font-bold mb-4 text-emerald-400 border-b border-emerald-900 pb-2">Legacy Execution Utilities</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <Activity className="text-blue-400" />
            <h3 className="text-lg font-bold">Deep Telemetry Scan</h3>
          </div>
          <p className="text-sm text-slate-400 mb-4">Run an extensive diagnostic overlay against the Quantum Computing Research database vectors.</p>
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
          <p className="text-sm text-slate-400 mb-4">Deploy Swarm Agents to automatically resolve Quantum Computing Research system bottlenecks.</p>
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
