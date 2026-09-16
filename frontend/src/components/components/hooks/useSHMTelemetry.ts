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

export function useSHMTelemetry() {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [heartbeatActive, setHeartbeatActive] = useState<boolean>(true);
  const [lastHealedEvent, setLastHealedEvent] = useState<string | null>(null);
  const [astEvents, setAstEvents] = useState<ASTEvent[]>([]);
  const [tensorEvents, setTensorEvents] = useState<TensorEvent[]>([]);
  const [gpuStats, setGpuStats] = useState<GPUStats>({
    model: 'SDXL_Turbo',
    step: 18,
    total_steps: 30,
    vram_used_mb: 18432,
    vram_total_mb: 24576,
    fps: 24.5
  });

  const [telemetryData, setTelemetryData] = useState<any>({
    status: 'OFFLINE',
    head: 0,
    tail: 0,
    total_pushed: 0,
    total_popped: 0,
    topics: {
      '0x0001': { name: 'TOPIC_PREDICTIVE_TENSORS', latency_us: 2.61, status: 'OK' },
      '0x0002': { name: 'TOPIC_VNC_FRAME_METRICS', latency_us: 4.36, status: 'OK' },
      '0x0003': { name: 'TOPIC_HEURISTICS_TELEMETRY', latency_us: 5.06, status: 'OK' },
      '0x0004': { name: 'TOPIC_SYSTEM_STATE_HEARTBEAT', latency_us: 1.00, status: 'OK' },
      '0x0005': { name: 'TOPIC_ZERO_COPY_VECTOR_TENSORS', latency_us: 1.80, status: 'OK' },
      '0x0006': { name: 'TOPIC_COMFYUI_GPU_RENDER', latency_us: 3.20, status: 'OK' }
    }
  });

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let wsUrl = (import.meta as any).env?.VITE_WS_URL;
    if (!wsUrl) {
      if (typeof window !== 'undefined') {
        if ((import.meta as any).env?.DEV) {
          wsUrl = 'ws://127.0.0.1:8000/ws/shm_telemetry';
        } else {
          wsUrl = 'ws://localhost:8000/ws/shm_telemetry';
        }
      } else {
        wsUrl = 'ws://localhost:8000/ws/shm_telemetry';
      }
    }

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          setHeartbeatActive(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setTelemetryData(data);
            setIsConnected(true);
            setHeartbeatActive(true);

            if (data.ast_event) setAstEvents((prev) => [data.ast_event, ...prev.slice(0, 19)]);
            if (data.tensor_event) setTensorEvents((prev) => [data.tensor_event, ...prev.slice(0, 19)]);
            if (data.gpu_stats) setGpuStats(data.gpu_stats);
          } catch (e) {
            console.error('Failed to parse SHM telemetry frame', e);
          }
        };

        ws.onerror = () => setIsConnected(false);
        ws.onclose = () => {
          setIsConnected(false);
          setTimeout(connectWebSocket, 3000);
        };
      } catch (err) {
        setIsConnected(false);
        setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return {
    isConnected,
    heartbeatActive,
    lastHealedEvent,
    astEvents,
    tensorEvents,
    gpuStats,
    telemetryData
  };
}
