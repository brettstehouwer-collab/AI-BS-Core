import { useState, useEffect, useRef } from 'react';

export interface ASTEvent {
  rule_id: string;
  file_target: string;
  diff_type: string;
  status: string;
  timestamp: number;
}

export interface TensorEvent {
  source: string;
  dimensions: number;
  latency_us: number;
  tokens: string;
}

export interface GPUStats {
  model: string;
  step: number;
  total_steps: number;
  vram_used_mb: number;
  vram_total_mb: number;
  fps: number;
}

export interface SHMTelemetryFrame {
  timestamp: number; status: string; shm_active: true; magic: string;
  head: number; tail: number; total_pushed: number; total_popped: number;
  topics: Record<string, {name: string; latency_us: number; status: string}>;
}

function readFrame(value: unknown): SHMTelemetryFrame | null {
  if (!value || typeof value !== 'object') return null;
  const data = value as Record<string, unknown>;
  if (data.shm_active !== true || data.magic !== '0xA1B51996' || data.status !== 'HEALTHY'
      || typeof data.timestamp !== 'number' || !Number.isFinite(data.timestamp)) return null;
  const count = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
  if (!count(data.head) || !count(data.tail) || !count(data.total_pushed) || !count(data.total_popped)) return null;
  // The current gateway's topic timings are constants, not observations. It emits no event/GPU frames.
  return {timestamp: data.timestamp, status: data.status, shm_active: true, magic: data.magic,
    head: data.head, tail: data.tail, total_pushed: data.total_pushed, total_popped: data.total_popped, topics: {}};
}

export function useSHMTelemetry(options: {fallbackUrl?: string; useBackendUrl?: boolean; retryDelay?: number} = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [heartbeatActive, setHeartbeatActive] = useState(false);
  const [lastHealedEvent] = useState<string | null>(null);
  const [astEvents] = useState<ASTEvent[]>([]);
  const [tensorEvents] = useState<TensorEvent[]>([]);
  const [gpuStats] = useState<GPUStats | null>(null);
  const [telemetryData, setTelemetryData] = useState<SHMTelemetryFrame | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const {fallbackUrl, useBackendUrl, retryDelay = 3000} = options;

  useEffect(() => {
    const env = import.meta.env;
    const wsUrl = env.VITE_WS_URL || (useBackendUrl && env.VITE_BACKEND_URL
      ? env.VITE_BACKEND_URL.replace(/^http/, 'ws') + '/ws/shm_telemetry'
      : fallbackUrl || (env.DEV ? 'ws://127.0.0.1:8000/ws/shm_telemetry' : 'ws://localhost:8000/ws/shm_telemetry'));
    let mounted = true;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const unavailable = () => { setIsConnected(false); setHeartbeatActive(false); setTelemetryData(null); };
    const schedule = () => { if (mounted && retry === null) retry = setTimeout(() => {retry = null; connect();}, retryDelay); };
    const connect = () => {
      if (!mounted) return;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onopen = () => { if (mounted && wsRef.current === ws) setIsConnected(true); };
        ws.onmessage = event => {
          if (!mounted || wsRef.current !== ws) return;
          try {
            const data: unknown = typeof event.data === 'string' ? JSON.parse(event.data) : null;
            const frame = readFrame(data);
            if (!frame) {unavailable(); return;}
            setTelemetryData(frame); setIsConnected(true); setHeartbeatActive(true);
          } catch { unavailable(); }
        };
        ws.onerror = () => {if (mounted && wsRef.current === ws) unavailable();};
        ws.onclose = () => {if (mounted && wsRef.current === ws) {unavailable(); schedule();}};
      } catch {unavailable(); schedule();}
    };
    connect();
    return () => {
      mounted = false;
      if (retry !== null) clearTimeout(retry);
      const ws = wsRef.current;
      if (ws) {ws.onopen = null; ws.onmessage = null; ws.onerror = null; ws.onclose = null; ws.close();}
      wsRef.current = null;
    };
  }, [fallbackUrl, useBackendUrl, retryDelay]);
  return {isConnected, heartbeatActive, lastHealedEvent, astEvents, tensorEvents, gpuStats, telemetryData};
}
