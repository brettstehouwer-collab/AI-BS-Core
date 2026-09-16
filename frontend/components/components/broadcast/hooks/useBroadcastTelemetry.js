import { useState, useEffect, useRef } from 'react';

/**
 * Real-time Broadcast Studio Telemetry Hook with automatic reconnection backoff
 */
export function useBroadcastTelemetry(daemonPort = 8005) {
  const [telemetry, setTelemetry] = useState({
    fps: 60,
    bitrateKbps: 8000,
    cpuUsage: 14,
    gpuVramUsedGb: 6.4,
    droppedFrames: 0,
    status: 'connecting'
  });

  const retryTimeoutRef = useRef(null);

  useEffect(() => {
    let ws;
    let isMounted = true;
    let retryDelay = 1000;

    const connect = () => {
      try {
        ws = new WebSocket(`ws://127.0.0.1:${daemonPort}/ws/telemetry`);
        
        ws.onopen = () => {
          if (!isMounted) return;
          retryDelay = 1000;
          setTelemetry((prev) => ({ ...prev, status: 'connected' }));
        };

        ws.onmessage = (evt) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(evt.data);
            setTelemetry((prev) => ({ ...prev, ...data, status: 'connected' }));
          } catch (e) {}
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setTelemetry((prev) => ({ ...prev, status: 'disconnected' }));
          retryTimeoutRef.current = setTimeout(connect, Math.min(retryDelay * 1.5, 8000));
        };

        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (e) {
        retryTimeoutRef.current = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
      if (ws) ws.close();
    };
  }, [daemonPort]);

  return telemetry;
}
