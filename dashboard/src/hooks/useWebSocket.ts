import { useEffect, useRef, useState, useCallback } from 'react';

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://192.168.0.104:8000';

export interface WSMessage {
  type: string;
  [key: string]: any;
}

/**
 * React hook for authenticated WebSocket connection with auto-reconnect.
 * Provides real-time updates from the backend (leaderboard, task events, MCP).
 */
export function useWebSocket(channel: string = 'global') {
  const wsRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(null);
  const retryCount = useRef(0);

  const connect = useCallback(() => {
    const token = localStorage.getItem('desci_token');
    const url = `${WS_BASE}/ws/${channel}${token ? `?token=${token}` : ''}`;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setConnected(true);
        retryCount.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data: WSMessage = JSON.parse(event.data);
          setMessages(prev => {
            // Keep only last 100 messages in memory
            const next = [...prev, data];
            return next.length > 100 ? next.slice(-100) : next;
          });
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = (event) => {
        setConnected(false);
        wsRef.current = null;

        // Don't reconnect if auth failed (4001)
        if (event.code === 4001) {
          localStorage.removeItem('desci_token');
          window.location.reload();
          return;
        }

        // Exponential backoff reconnect
        const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
        retryCount.current++;
        reconnectTimer.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      // WebSocket constructor failed
      const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000);
      retryCount.current++;
      reconnectTimer.current = setTimeout(connect, delay);
    }
  }, [channel]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, connected, clearMessages };
}

/**
 * Filter WS messages by type.
 */
export function useWSEvent(messages: WSMessage[], type: string): WSMessage | null {
  const filtered = messages.filter(m => m.type === type);
  return filtered.length > 0 ? filtered[filtered.length - 1] : null;
}
