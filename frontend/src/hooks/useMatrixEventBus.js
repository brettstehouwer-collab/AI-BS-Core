import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useMatrixEventBus: Unified Go ⇄ Python ⇄ React Multiplexed EventBus Hook
 * Connects to /ws/matrix WebSocket on Port 8080.
 */
export const useMatrixEventBus = (defaultChannels = ['general']) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const subscribersRef = useRef({});

  // Establish WebSocket connection
  const connect = useCallback(() => {
    try {
      const wsUrl = 'ws://127.0.0.1:8080/ws/matrix';
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('[Matrix EventBus] Connected to /ws/matrix multiplexer.');
        setIsConnected(true);

        // Subscribe to requested default channels
        defaultChannels.forEach((ch) => {
          ws.send(JSON.stringify({ action: 'subscribe', channel: ch }));
        });
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setLastEvent(payload);

          const channel = payload.channel;
          if (channel && subscribersRef.current[channel]) {
            subscribersRef.current[channel].forEach((cb) => cb(payload));
          }
          if (subscribersRef.current['all']) {
            subscribersRef.current['all'].forEach((cb) => cb(payload));
          }
        } catch (err) {
          console.warn('[Matrix EventBus] Failed to parse message JSON:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.warn('[Matrix EventBus] Socket closed. Reconnecting in 3s...');
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('[Matrix EventBus] WebSocket Error:', err);
        ws.close();
      };
    } catch (e) {
      console.error('[Matrix EventBus] Connection initialization failed:', e);
      reconnectTimeoutRef.current = setTimeout(connect, 4000);
    }
  }, [defaultChannels]);

  // Subscribe to specific channel
  const subscribe = useCallback((channel, callback) => {
    if (!subscribersRef.current[channel]) {
      subscribersRef.current[channel] = new Set();
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ action: 'subscribe', channel }));
      }
    }
    subscribersRef.current[channel].add(callback);

    return () => {
      if (subscribersRef.current[channel]) {
        subscribersRef.current[channel].delete(callback);
      }
    };
  }, []);

  // Publish event through EventBus
  const publish = useCallback((channel, eventType, data = {}) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        action: 'publish',
        channel,
        event: eventType,
        payload: data,
      }));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();

    // Heartbeat ping interval
    const pingInterval = setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ action: 'ping' }));
      }
    }, 15000);

    return () => {
      clearInterval(pingInterval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) socketRef.current.close();
    };
  }, [connect]);

  return {
    isConnected,
    lastEvent,
    subscribe,
    publish,
  };
};

export default useMatrixEventBus;
