import { useState, useEffect, useRef } from 'react';

export function useSHMTelemetry() {
  const [isConnected, setIsConnected] = useState(false);
  const [heartbeatActive, setHeartbeatActive] = useState(true);
  const [lastHealedEvent, setLastHealedEvent] = useState(null);
  const [astEvents, setAstEvents] = useState([]);
  const [tensorEvents, setTensorEvents] = useState([]);
  const [gpuStats, setGpuStats] = useState({
    model: 'SDXL_Turbo',
    step: 18,
    total_steps: 30,
    vram_used_mb: 18432,
    vram_total_mb: 24576,
    fps: 24.5
  });

  const [telemetryData, setTelemetryData] = useState({
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

  const wsRef = useRef(null);

  useEffect(() => {
    let wsUrl = import.meta.env?.VITE_WS_URL;
    if (!wsUrl) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      if (backendUrl) {
        wsUrl = backendUrl.replace(/^http/, 'ws') + '/ws/shm_telemetry';
      } else if (typeof window !== 'undefined') {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        if (import.meta.env?.DEV) {
          wsUrl = 'ws://127.0.0.1:8010/ws/shm_telemetry';
        } else {
          wsUrl = 'ws://127.0.0.1:8010/ws/shm_telemetry';
        }
      } else {
        wsUrl = 'ws://127.0.0.1:8010/ws/shm_telemetry';
      }
    }

    let isMounted = true;
    let reconnectTimeout = null;

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setIsConnected(true);
          setHeartbeatActive(true);
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            setTelemetryData(data);
            setIsConnected(true);
            setHeartbeatActive(true);

            if (data.ast_event) {
              setAstEvents((prev) => [data.ast_event, ...prev.slice(0, 19)]);
            }
            if (data.tensor_event) {
              setTensorEvents((prev) => [data.tensor_event, ...prev.slice(0, 19)]);
            }
            if (data.gpu_stats) {
              setGpuStats(data.gpu_stats);
            }
          } catch (e) {
            console.error('Failed to parse SHM telemetry frame', e);
          }
        };

        ws.onerror = () => {
          if (isMounted) setIsConnected(false);
        };
        ws.onclose = () => {
          if (!isMounted) return;
          setIsConnected(false);
          reconnectTimeout = setTimeout(connectWebSocket, 5000);
        };
      } catch (err) {
        if (!isMounted) return;
        setIsConnected(false);
        reconnectTimeout = setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onerror = null;
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        } else if (wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.onopen = () => { try { wsRef.current.close(); } catch (e) {} };
        }
      }
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
