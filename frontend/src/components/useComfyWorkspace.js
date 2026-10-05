import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom React hook interfacing with ComfyUI REST and WebSocket APIs on Port 8189.
 * Handles schema introspection (/object_info), WebSocket progress/preview streaming,
 * workflow execution queueing (/prompt), and execution interruption (/interrupt).
 */
export const useComfyWorkspace = (initialBaseUrl = 'http://127.0.0.1:8189') => {
  const [baseUrl, setBaseUrl] = useState(() => {
    // Check localStorage or window protocol for hybrid resolution
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('AI_BS_COMFYUI_URL');
      if (saved) return saved;
      // If served over localhost/127.0.0.1, default to 8189 directly
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      return isLocal ? 'http://127.0.0.1:8189' : 'http://127.0.0.1:8189';
    }
    return initialBaseUrl;
  });

  const [nodeRegistry, setNodeRegistry] = useState({});
  const [activeWorkflow, setActiveWorkflow] = useState('SDXL 4K Master Cine');
  const [executingNode, setExecutingNode] = useState(null);
  const [progress, setProgress] = useState({ value: 0, max: 0 });
  const [outputs, setOutputs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [errorStatus, setErrorStatus] = useState(null);

  const clientId = useRef(
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `aibs_${Math.random().toString(36).substring(2, 15)}`
  );
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  // Persist baseUrl changes
  const updateBaseUrl = useCallback((newUrl) => {
    const cleaned = newUrl.replace(/\/+$/, '');
    setBaseUrl(cleaned);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('AI_BS_COMFYUI_URL', cleaned);
    }
  }, []);

  // 1. Fetch Object Info (All Registered Nodes from ComfyUI)
  const fetchSchema = useCallback(async () => {
    try {
      setErrorStatus(null);
      const res = await fetch(`${baseUrl}/object_info`, { mode: 'cors' });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const data = await res.json();
      setNodeRegistry(data || {});
    } catch (err) {
      console.warn('[useComfyWorkspace] Failed to load ComfyUI node definitions from', baseUrl, err);
      setErrorStatus(`Node schema unreachable at ${baseUrl}: ${err.message}`);
    }
  }, [baseUrl]);

  useEffect(() => {
    fetchSchema();
  }, [fetchSchema]);

  // 2. Establish WebSocket Stream for Telemetry & Real-Time Previews
  useEffect(() => {
    let isMounted = true;

    const connectWs = () => {
      try {
        const wsProtocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
        const hostPath = baseUrl.replace(/^https?:\/\//, '');
        const wsUrl = `${wsProtocol}://${hostPath}/ws?clientId=${clientId.current}`;

        if (ws.current) {
          try { ws.current.close(); } catch (_) {}
        }

        const socket = new WebSocket(wsUrl);
        ws.current = socket;

        socket.onopen = () => {
          if (isMounted) {
            setIsConnected(true);
            setErrorStatus(null);
          }
        };

        socket.onclose = () => {
          if (isMounted) {
            setIsConnected(false);
            // Attempt graceful reconnection after 4s
            reconnectTimeout.current = setTimeout(() => {
              if (isMounted) connectWs();
            }, 4000);
          }
        };

        socket.onerror = (e) => {
          if (isMounted) {
            setIsConnected(false);
          }
        };

        socket.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            switch (msg.type) {
              case 'status':
                // Queue status
                break;
              case 'execution_start':
                setProgress({ value: 0, max: 0 });
                break;
              case 'executing':
                setExecutingNode(msg.data?.node || null);
                if (!msg.data?.node) {
                  setProgress({ value: 0, max: 0 });
                }
                break;
              case 'progress':
                if (msg.data) {
                  setProgress({ value: msg.data.value || 0, max: msg.data.max || 0 });
                }
                break;
              case 'executed':
                if (msg.data?.output?.images && Array.isArray(msg.data.output.images)) {
                  const newImages = msg.data.output.images.map((img) => ({
                    url: `${baseUrl}/view?filename=${img.filename}&subfolder=${img.subfolder || ''}&type=${img.type || 'output'}`,
                    filename: img.filename,
                    subfolder: img.subfolder,
                    type: img.type,
                    timestamp: new Date().toLocaleTimeString()
                  }));
                  setOutputs((prev) => [...newImages, ...prev]);
                }
                break;
              default:
                break;
            }
          } catch (parseErr) {
            // Non-JSON or binary preview frame
          }
        };
      } catch (err) {
        if (isMounted) {
          setIsConnected(false);
        }
      }
    };

    connectWs();

    return () => {
      isMounted = false;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        try { ws.current.close(); } catch (_) {}
      }
    };
  }, [baseUrl]);

  // 3. Queue Execution (Prompt DAG Dispatch)
  const queueWorkflow = useCallback(async (promptDAG) => {
    try {
      const res = await fetch(`${baseUrl}/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptDAG,
          client_id: clientId.current
        }),
      });
      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Queue Failed (${res.status}): ${errText}`);
      }
      const data = await res.json();
      return data;
    } catch (err) {
      console.error('[useComfyWorkspace] Execution queue failed:', err);
      throw err;
    }
  }, [baseUrl]);

  // 4. Interrupt Running Queue
  const interrupt = useCallback(async () => {
    try {
      await fetch(`${baseUrl}/interrupt`, { method: 'POST' });
    } catch (err) {
      console.error('[useComfyWorkspace] Interrupt request failed:', err);
    }
  }, [baseUrl]);

  return {
    baseUrl,
    setBaseUrl: updateBaseUrl,
    nodeRegistry,
    activeWorkflow,
    setActiveWorkflow,
    executingNode,
    progress,
    outputs,
    isConnected,
    errorStatus,
    queueWorkflow,
    interrupt,
    refreshRegistry: fetchSchema,
    clientId: clientId.current
  };
};

export default useComfyWorkspace;
