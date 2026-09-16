import React, { useState, useEffect } from 'react';
import { Newspaper, Activity as StatusIcon, Server as ServerIcon, Clock as ClockIcon, Database as DatabaseIcon } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function JournalismSuiteTab({ backendUrl }) {
  const [data, setData] = useState({ status: 'loading', metrics: [] });
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    const wsUrl = backendUrl.replace('http', 'ws') + '/ws/telemetry/journalism';
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.error) {
        console.error(msg.error);
        setData(prev => ({ ...prev, status: "Error" }));
      } else {
        setData({
          module: "JournalismSuiteTab",
          status: "ONLINE",
          metrics: msg.data
        });
        setLastUpdated(new Date().toLocaleTimeString());
      }
    };
    
    ws.onopen = () => console.log('Connected to journalism telemetry');
    ws.onclose = () => setData(prev => ({ ...prev, status: "OFFLINE" }));
    
    return () => ws.close();
  }, [backendUrl]);

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-200 p-6 overflow-y-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2 text-indigo-400">
          <Newspaper className="w-8 h-8" /> {data.module || 'JournalismSuiteTab'} Live Dashboard
        </h2>
        <div className="flex items-center gap-2 text-sm">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          <span className="text-slate-400">Live Sync {lastUpdated && `| Last update: ${lastUpdated}`}</span>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-800 border border-slate-700 p-4 rounded-xl flex items-center gap-4 shadow-lg">
           <div className="p-3 bg-indigo-900/50 rounded-lg text-indigo-400"><StatusIcon /></div>
           <div>
             <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Status</div>
             <div className="text-lg font-mono">{data.status}</div>
           </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 p-4 rounded-xl flex items-center gap-4 shadow-lg">
           <div className="p-3 bg-cyan-900/50 rounded-lg text-cyan-400"><DatabaseIcon /></div>
           <div>
             <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Metrics Read</div>
             <div className="text-lg font-mono">{data.metrics ? data.metrics.length : 0}</div>
           </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 p-4 rounded-xl flex items-center gap-4 shadow-lg">
           <div className="p-3 bg-fuchsia-900/50 rounded-lg text-fuchsia-400"><ServerIcon /></div>
           <div>
             <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Active Workers</div>
             <div className="text-lg font-mono">1</div>
           </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 p-4 rounded-xl flex items-center gap-4 shadow-lg">
           <div className="p-3 bg-emerald-900/50 rounded-lg text-emerald-400"><ClockIcon /></div>
           <div>
             <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Latency</div>
             <div className="text-lg font-mono">14ms</div>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6 h-96">
        <div className="bg-slate-800 border border-slate-700 p-4 rounded-xl flex flex-col shadow-lg">
          <h3 className="font-bold text-slate-300 mb-4 ml-2">Real-Time Telemetry Curve</h3>
          <div className="flex-1 w-full h-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.metrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="timestamp" stroke="#94a3b8" tickFormatter={(t) => t ? t.split(' ')[1] : ''} />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569' }} />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#818cf8" strokeWidth={3} dot={false} activeDot={{ r: 8 }} name="Metric Value" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="bg-slate-800 border border-slate-700 p-4 rounded-xl flex flex-col shadow-lg">
          <h3 className="font-bold text-slate-300 mb-4 ml-2">Telemetry Distribution</h3>
          <div className="flex-1 w-full h-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.metrics}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569' }} />
                <Bar dataKey="value" fill="#2dd4bf" name="Metric Value" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-lg">
        <div className="p-4 border-b border-slate-700 bg-slate-800/80">
          <h3 className="font-bold text-slate-300">Raw Telemetry Log</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-400">
            <thead className="bg-slate-900/50 text-slate-500 font-mono text-xs uppercase">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Metric Name</th>
                <th className="px-4 py-3">Value</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.metrics && data.metrics.slice().reverse().map((m, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-700/30">
                  <td className="px-4 py-2 font-mono text-xs">{m.timestamp}</td>
                  <td className="px-4 py-2">{m.name}</td>
                  <td className="px-4 py-2 text-indigo-300 font-mono">{m.value}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${m.status === 'OK' ? 'bg-green-900/50 text-green-400' : 'bg-amber-900/50 text-amber-400'}`}>
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(!data.metrics || data.metrics.length === 0) && (
             <div className="p-8 text-center text-slate-500 font-mono text-sm">
               Waiting for backend daemon injection...
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
