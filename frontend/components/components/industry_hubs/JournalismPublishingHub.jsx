import React, { useState, useEffect } from 'react';
import { Play, Activity, Zap, Newspaper, Rss } from 'lucide-react';

export default function JournalismPublishingHub({ BACKEND_URL = "http://127.0.0.1:8000" }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  
  // Live Feed State
  const [liveNews, setLiveNews] = useState(null);
  const [lastUpdate, setLastUpdate] = useState('');

  const runTool = async (toolId) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/industry_tools/journalismpublishing/${toolId}`, { method: 'POST' });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: "Backend connection failed." });
    }
    setLoading(false);
  };

  useEffect(() => {
    // Poll the backend data feed for news_feed
    const fetchFeed = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/feeds/latest/news_feed?limit=1`);
        const data = await res.json();
        if (data.status === 'success' && data.data && data.data.length > 0) {
          setLiveNews(data.data[0].payload);
          setLastUpdate(data.data[0].timestamp);
        }
      } catch (e) {
        console.error("Failed to fetch live news feed", e);
      }
    };
    
    fetchFeed();
    const interval = setInterval(fetchFeed, 10000);
    return () => clearInterval(interval);
  }, [BACKEND_URL]);

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-900 text-slate-200">
      <h2 className="text-2xl font-bold mb-6 text-emerald-400">Journalism & Publishing Command Center</h2>
      
      {/* Live Breaking News Panel */}
      <div className="mb-8 bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
        <div className="flex items-center gap-3 mb-4 border-b border-slate-700 pb-3">
          <Newspaper className="text-purple-400" />
          <h3 className="text-lg font-bold">Live Breaking News (RSS Ingestion)</h3>
          <span className="ml-auto flex items-center gap-2 text-xs text-purple-500 bg-purple-500/10 px-2 py-1 rounded">
            <Rss size={12} className="animate-pulse" />
            LIVE FEED
          </span>
        </div>
        
        {liveNews ? (
          <div>
            <div className="text-xs text-slate-400 mb-3 flex justify-between">
              <span>Source: {liveNews.source}</span>
              <span>Last Sync: {lastUpdate}</span>
            </div>
            <div className="flex flex-col gap-2">
              {liveNews.articles?.map((article, idx) => (
                <div key={idx} className="bg-slate-900 p-3 rounded border border-slate-800 hover:border-slate-600 transition">
                  <a href={article.link} target="_blank" rel="noopener noreferrer" className="font-semibold text-sm text-slate-200 hover:text-purple-400">
                    {article.title}
                  </a>
                  <div className="text-xs text-slate-500 mt-1">{article.published}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="py-4 text-center text-slate-500 animate-pulse">
            Awaiting RSS payload from Message Broker...
          </div>
        )}
      </div>
      
      <p className="mb-8 text-slate-400">Interactive diagnostic tools and remote-execution utilities for Journalism & Publishing.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <Activity className="text-blue-400" />
            <h3 className="text-lg font-bold">Deep Telemetry Scan</h3>
          </div>
          <p className="text-sm text-slate-400 mb-4">Run an extensive diagnostic overlay against the Journalism & Publishing database vectors.</p>
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
          <p className="text-sm text-slate-400 mb-4">Deploy Swarm Agents to automatically resolve Journalism & Publishing system bottlenecks.</p>
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
