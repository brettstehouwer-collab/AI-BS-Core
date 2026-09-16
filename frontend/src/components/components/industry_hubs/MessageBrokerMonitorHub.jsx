import React, { useState, useEffect } from 'react';
import { Activity, Database, Server, RefreshCw } from 'lucide-react';

export default function MessageBrokerMonitorHub({ BACKEND_URL }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      // The broker runs on port 8085
      const res = await fetch(`http://127.0.0.1:8085/stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error(e);
      setStats({ error: "Broker offline or unreachable." });
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 h-full overflow-y-auto bg-slate-900 text-slate-200">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-emerald-400">Message Broker Telemetry</h2>
        <button onClick={fetchStats} className="bg-slate-800 p-2 rounded hover:bg-slate-700">
          <RefreshCw size={18} className="text-slate-400" />
        </button>
      </div>
      
      <p className="mb-8 text-slate-400">
        Live telemetry monitoring for the native Python `asyncio` message broker handling massive IoT and API ping ingestion.
      </p>

      {stats?.error ? (
        <div className="bg-red-900/20 border border-red-500/50 p-4 rounded-xl text-red-400">
          {stats.error} (Ensure bullshit_message_broker.py is running on port 8085)
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg flex items-center gap-4">
            <Activity size={32} className={stats?.status === "online" ? "text-emerald-500" : "text-amber-500"} />
            <div>
              <p className="text-sm text-slate-400 uppercase tracking-wider">Status</p>
              <p className="text-2xl font-bold">{stats?.status || "Loading..."}</p>
            </div>
          </div>
          
          <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg flex items-center gap-4">
            <Database size={32} className="text-blue-500" />
            <div>
              <p className="text-sm text-slate-400 uppercase tracking-wider">Queue Depth</p>
              <p className="text-2xl font-bold">{stats?.current_queue_depth ?? 0}</p>
            </div>
          </div>

          <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg flex items-center gap-4">
            <Server size={32} className="text-purple-500" />
            <div>
              <p className="text-sm text-slate-400 uppercase tracking-wider">Total Processed</p>
              <p className="text-2xl font-bold">{stats?.total_messages_processed ?? 0}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
