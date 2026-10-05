import React, { useState, useEffect, useCallback } from 'react';
import { 
  Activity, 
  Cpu, 
  Zap, 
  Thermometer, 
  Wind, 
  Database, 
  RefreshCw, 
  ShieldAlert, 
  CheckCircle2, 
  Sliders, 
  History,
  Lock,
  RotateCcw
} from 'lucide-react';

export default function GpuHardwareTelemetryTab() {
  const [telemetry, setTelemetry] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchTelemetry = useCallback(async () => {
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/hardware/gpu/telemetry');
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      if (data.status === 'success') {
        setTelemetry(data.telemetry);
        setHistory(data.history || []);
        setError(null);
      }
    } catch (err) {
      console.warn('GPU Telemetry fetch warning:', err.message);
      setError('Live NVML Telemetry Gateway Offline (Port 8080)');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2500);
    return () => clearInterval(interval);
  }, [fetchTelemetry]);

  const handleFanControl = async (speed, auto) => {
    setActionLoading(true);
    setActionMessage(null);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/v1/hardware/gpu/fan-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed, auto })
      });
      const data = await res.json();
      if (data.status === 'success' || data.status === 'warning') {
        setActionMessage(data.result?.message || 'Fan setting updated successfully');
        fetchTelemetry();
      } else {
        setActionMessage('Failed to update fan speed');
      }
    } catch (err) {
      setActionMessage(`Error: ${err.message}`);
    } finally {
      setActionLoading(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

  const temp = telemetry?.core_temp_c ?? 32;
  const fanPct = telemetry?.fan_speed_pct ?? 100;
  const memUsed = telemetry?.memory_used_mb ?? 4096;
  const memTotal = telemetry?.memory_total_mb ?? 24564;
  const memPct = memTotal > 0 ? Math.round((memUsed / memTotal) * 100) : 0;
  const power = telemetry?.power_usage_w ?? 45.2;
  const util = telemetry?.gpu_util_pct ?? 12;

  const getTempColor = (t) => {
    if (t >= 75) return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
    if (t >= 60) return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
    return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
  };

  return (
    <div className="w-full min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6 font-sans">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-lg shadow-cyan-500/10">
              <Cpu className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Sovereign GPU & Hardware Telemetry Hub
              </h1>
              <p className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                NVIDIA GeForce RTX 4090 24GB VRAM • NVML Hardware Binding • SQLite Vault Sync
              </p>
            </div>
          </div>
        </div>

        {/* Header Quick Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleFanControl(100, false)}
            disabled={actionLoading}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-rose-600 to-orange-600 hover:from-rose-500 hover:to-orange-500 text-white shadow-md shadow-rose-600/20 transition-all active:scale-95 disabled:opacity-50"
          >
            <Lock className="w-3.5 h-3.5" />
            🔥 Lock Fans 100%
          </button>

          <button
            onClick={() => handleFanControl(0, true)}
            disabled={actionLoading}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all active:scale-95 disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5 text-cyan-400" />
            ❄️ Auto Curve
          </button>

          <button
            onClick={fetchTelemetry}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Refresh Telemetry"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alert Notices */}
      {actionMessage && (
        <div className="p-3.5 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs flex items-center gap-2 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
          {actionMessage}
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Core Temp */}
        <div className={`p-4 rounded-xl border transition-all ${getTempColor(temp)} shadow-lg`}>
          <div className="flex items-center justify-between text-xs font-medium opacity-80 mb-2">
            <span>GPU Core Temp</span>
            <Thermometer className="w-4 h-4" />
          </div>
          <div className="text-3xl font-extrabold tracking-tight">
            {temp}°C
          </div>
          <p className="text-[11px] mt-1.5 opacity-75">
            {temp >= 70 ? 'High Thermal Load' : temp >= 50 ? 'Warm Operation' : 'Frosty / Optimal'}
          </p>
        </div>

        {/* Fan Speed */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>Fan Speed</span>
            <Wind className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-cyan-400 tracking-tight">
            {fanPct}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            {telemetry?.status_flag === 'FAN_LOCKED_100' ? 'Locked to 100%' : 'Driver Controlled'}
          </p>
        </div>

        {/* VRAM Usage */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>VRAM Allocated</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-indigo-400 tracking-tight">
            {(memUsed / 1024).toFixed(1)} <span className="text-sm font-normal text-slate-400">/ 24.5 GB</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2.5 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-full transition-all duration-500" 
              style={{ width: `${memPct}%` }}
            />
          </div>
        </div>

        {/* Power Draw */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>Power Usage</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-amber-400 tracking-tight">
            {power} <span className="text-sm font-normal text-slate-400">W</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            Target Cap: 450W Limit
          </p>
        </div>

        {/* GPU Utilization */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>Core Utilization</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 tracking-tight">
            {util}%
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            Active Compute Pipeline
          </p>
        </div>
      </div>

      {/* Main Content Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hardware Status Panel */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200 border-b border-slate-800 pb-3">
            <Sliders className="w-4 h-4 text-cyan-400" />
            Hardware Controller & Clocks
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Device Target</span>
              <span className="font-semibold text-slate-200">{telemetry?.gpu_name || 'NVIDIA GeForce RTX 4090'}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">NVML Direct Access</span>
              <span className={`font-semibold ${telemetry?.nvml_online ? 'text-emerald-400' : 'text-amber-400'}`}>
                {telemetry?.nvml_online ? '✓ Active (nvml.dll)' : 'Simulated / Standby'}
              </span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">GPU Core Clock</span>
              <span className="font-semibold text-cyan-400">{telemetry?.core_clock_mhz || 2520} MHz</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Memory Clock</span>
              <span className="font-semibold text-cyan-400">{telemetry?.memory_clock_mhz || 10501} MHz</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Thermal Guard Status</span>
              <span className="font-semibold text-emerald-400">Active (Doctor Sentinel Enabled)</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-400 leading-relaxed">
            💡 <strong className="text-slate-200">Thermal Protection:</strong> If GPU core temperature reaches 75°C, Matrix Doctor automatically locks fan speeds to 100% until core temperature cools below 50°C.
          </div>
        </div>

        {/* Historical Thermal Logs Table */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <History className="w-4 h-4 text-cyan-400" />
              SQLite Thermal History Vault (`gpu_thermal_logs`)
            </div>
            <span className="text-xs text-slate-400">
              Pruned to 500 records max
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">Temp (°C)</th>
                  <th className="py-2.5 px-3">Fan Speed</th>
                  <th className="py-2.5 px-3">Power (W)</th>
                  <th className="py-2.5 px-3">VRAM Used</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {history.length > 0 ? (
                  history.slice(0, 10).map((log, idx) => (
                    <tr key={log.id || idx} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-2 px-3 text-slate-400 font-mono text-[11px]">{log.timestamp}</td>
                      <td className="py-2 px-3 font-semibold text-slate-200">{log.core_temp_c}°C</td>
                      <td className="py-2 px-3 text-cyan-400 font-medium">{log.fan_speed_pct}%</td>
                      <td className="py-2 px-3 text-amber-400">{log.power_usage_w}W</td>
                      <td className="py-2 px-3 text-indigo-300">{(log.memory_used_mb / 1024).toFixed(1)} GB</td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                          log.status_flag === 'CRITICAL_WARM' ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' :
                          log.status_flag === 'FAN_LOCKED_100' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' :
                          'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        }`}>
                          {log.status_flag}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500 italic">
                      No thermal history logged yet. Polling active...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
