import { useState, useEffect, useCallback, useRef } from 'react';
import FinancialAccountBoundary from '/src/components/FinancialAccountBoundary.jsx';
import { reportedHardwareValue, requestFanControl } from '/src/utils/networkWorkspace.js';
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

/** @param {{backendUrl?:string}} props */
export default function GpuHardwareTelemetryTab({ backendUrl }) {
  return <FinancialAccountBoundary>{request => <GpuHardwareContent key={backendUrl || ''} backendUrl={backendUrl || ''} financialRequest={request} />}</FinancialAccountBoundary>;
}

/** @param {{backendUrl:string,financialRequest:ReturnType<typeof import("/src/utils/accountingSession.js").createAccountingSession>["request"]}} props */
function GpuHardwareContent({ backendUrl, financialRequest }) {
  const [telemetry, setTelemetry] = useState(/** @type {{nvml_online?:boolean,field_status?:Record<string,string>,gpu_name?:string,[key:string]:unknown}|null} */ (null));
  const [history, setHistory] = useState(/** @type {{id?:string|number,timestamp:string,core_temp_c:number,fan_speed_pct:number,power_usage_w:number,memory_used_mb:number,status_flag:string}[]} */ ([]));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(/** @type {string|null} */ (null));
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(/** @type {{kind:string,text:string}|null} */ (null));
  const readGeneration = useRef(0);
  const readPending = useRef(/** @type {Promise<void>|null} */ (null));
  const actionPending = useRef(false);
  const apiBase = backendUrl.replace(/\/$/, '');

  const fetchTelemetry = useCallback(() => {
    if (readPending.current) return readPending.current;
    const generation = ++readGeneration.current;
    setLoading(true);
    readPending.current = (async () => {
      try {
        const response = await financialRequest(`${apiBase}/api/v1/hardware/gpu/telemetry`);
        const data = await response.json();
        if (data.status !== 'success' || !data.telemetry || typeof data.telemetry !== 'object' || !Array.isArray(data.history)) {
          throw new Error('Hardware telemetry response is unavailable.');
        }
        if (generation === readGeneration.current) {
          setTelemetry(data.telemetry); setHistory(data.history); setError(null);
        }
      } catch {
        if (generation === readGeneration.current) {
          setTelemetry(null); setHistory([]);
          setError('Hardware telemetry is unavailable. Sign in with an authorized account or refresh to retry.');
        }
      } finally {
        if (generation === readGeneration.current) { setLoading(false); readPending.current = null; }
      }
    })();
    return readPending.current;
  }, [apiBase, financialRequest]);

  useEffect(() => {
    let active = true;
    /** @type {ReturnType<typeof setTimeout>|undefined} */
    let timer;
    const poll = async () => {
      await fetchTelemetry();
      if (active) timer = setTimeout(poll, 2500);
    };
    poll();
    return () => { active = false; clearTimeout(timer); readGeneration.current++; readPending.current = null; };
  }, [fetchTelemetry]);

  /** @param {number} speed @param {boolean} auto */
  const handleFanControl = async (speed, auto) => {
    if (actionPending.current) return;
    actionPending.current = true; setActionLoading(true); setActionMessage(null);
    try {
      const result = await requestFanControl({ request: financialRequest, backendUrl: apiBase, speed, auto });
      setActionMessage({ kind: result.enforcement_verified ? 'success' : result.success ? 'accepted' : 'warning',
        text: `${result.message} ${result.enforcement_verified ? 'Enforcement verified by readback.' : result.success ? 'Request accepted; enforcement unverified.' : 'Request was not accepted.'}` });
      fetchTelemetry();
    } catch (err) {
      setActionMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Fan control is unavailable. Refresh telemetry before retrying.' });
    } finally { actionPending.current = false; setActionLoading(false); }
  };

  // The current engine does not attest individual sensor/history provenance.
  const reported = telemetry?.nvml_online === true ? telemetry : null;
  /** @param {string} key */
  const metric = (key, maximum = Infinity) => reportedHardwareValue(telemetry, key, maximum);
  const temp = metric('core_temp_c', 150);
  const fanPct = metric('fan_speed_pct', 100);
  const memUsed = metric('memory_used_mb');
  const memTotal = metric('memory_total_mb');
  const memPct = memUsed !== null && memTotal !== null && memTotal > 0 ? Math.min(100, Math.round((memUsed / memTotal) * 100)) : null;
  const power = metric('power_usage_w');
  const util = metric('gpu_util_pct', 100);
  /** @param {number|null} value */
  const display = (value, unit = '') => value === null ? 'Unavailable' : `${value}${unit}`;

  /** @param {number|null} t */
  const getTempColor = (t) => {
    if (t === null) return 'text-slate-400 bg-slate-900 border-slate-800';
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
                <span className="inline-block w-2 h-2 rounded-full bg-slate-400" />
                Server-reported sensor values and history • Measurement provenance unverified
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
        <div role={actionMessage.kind === 'error' ? 'alert' : 'status'} className="p-3.5 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs flex items-center gap-2 animate-fade-in">
          {actionMessage.kind === 'success' ? <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" /> : <ShieldAlert className="w-4 h-4 shrink-0" />}
          {actionMessage.text}
        </div>
      )}

      {error && (
        <div role="alert" className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
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
            {display(temp, '°C')}
          </div>
          <p className="text-[11px] mt-1.5 opacity-75">
            {temp === null ? 'Sensor unavailable' : 'Server-reported temperature'}
          </p>
        </div>

        {/* Fan Speed */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>Fan Speed</span>
            <Wind className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-cyan-400 tracking-tight">
            {display(fanPct, '%')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            {fanPct === null ? 'Control state unavailable' : 'Server-reported fan speed'}
          </p>
        </div>

        {/* VRAM Usage */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>VRAM Allocated</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-extrabold text-indigo-400 tracking-tight">
            {memUsed === null || memTotal === null ? 'Unavailable' : `${(memUsed / 1024).toFixed(1)} / ${(memTotal / 1024).toFixed(1)} GB`}
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2.5 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-indigo-500 to-cyan-400 h-full transition-all duration-500" 
              style={{ width: `${memPct ?? 0}%` }}
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
            {display(power, ' W')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            Power limit: Unavailable
          </p>
        </div>

        {/* GPU Utilization */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium mb-2">
            <span>Core Utilization</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 tracking-tight">
            {display(util, '%')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5">
            Server-reported utilization
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
              <span className="font-semibold text-slate-200">{reported?.field_status?.gpu_name === 'measured' && typeof reported.gpu_name === 'string' ? reported.gpu_name : 'Unavailable'}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">NVML Direct Access</span>
              <span className={`font-semibold ${telemetry?.nvml_online ? 'text-emerald-400' : 'text-amber-400'}`}>
                {telemetry?.nvml_online === true ? 'Reported online' : 'Unavailable'}
              </span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">GPU Core Clock</span>
              <span className="font-semibold text-cyan-400">{display(metric('core_clock_mhz'), ' MHz')}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Memory Clock</span>
              <span className="font-semibold text-cyan-400">{display(metric('memory_clock_mhz'), ' MHz')}</span>
            </div>

            <div className="flex justify-between py-2 border-b border-slate-800/60">
              <span className="text-slate-400">Thermal Guard Status</span>
              <span className="font-semibold text-emerald-400">Unavailable</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-400 leading-relaxed">
            💡 <strong className="text-slate-200">Thermal Protection:</strong> Automatic protection is unverified in this view. Manual fan controls require an authorized account.
          </div>
        </div>

        {/* Historical Thermal Logs Table */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <History className="w-4 h-4 text-cyan-400" />
              Server-reported thermal history (unverified)
            </div>
            <span className="text-xs text-slate-400">
              Record provenance unverified
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
                      Thermal history unavailable or no records returned. This does not establish zero activity.
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
