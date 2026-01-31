import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage, WebSocketState } from '../types';

interface UseWebSocketOptions {
  url: string;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export const useWebSocket = (options: UseWebSocketOptions) => {
  const {
    url,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onMessage,
    onConnect,
    onDisconnect,
    onError
  } = options;

  const [state, setState] = useState<WebSocketState>({
    connected: false,
    connecting: false,
    error: null,
    last_message: null,
    reconnect_attempts: 0,
    max_reconnect_attempts: reconnectAttempts
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    setState(prev => ({ ...prev, connecting: true, error: null }));

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        
        setState(prev => ({
          ...prev,
          connected: true,
          connecting: false,
          error: null,
          reconnect_attempts: 0
        }));
        
        onConnect?.();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;

        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setState(prev => ({ ...prev, last_message: message }));
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;

        setState(prev => ({ ...prev, connected: false, connecting: false }));
        onDisconnect?.();

        // Attempt reconnection if we haven't exceeded max attempts
        if (state.reconnect_attempts < reconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              setState(prev => ({ 
                ...prev, 
                reconnect_attempts: prev.reconnect_attempts + 1 
              }));
              connect();
            }
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        if (!mountedRef.current) return;

        setState(prev => ({
          ...prev,
          connected: false,
          connecting: false,
          error: 'WebSocket connection error'
        }));
        
        onError?.(error);
      };

    } catch (error) {
      setState(prev => ({
        ...prev,
        connected: false,
        connecting: false,
        error: 'Failed to create WebSocket connection'
      }));
    }
  }, [url, reconnectAttempts, reconnectInterval, onMessage, onConnect, onDisconnect, onError, state.reconnect_attempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState(prev => ({
      ...prev,
      connected: false,
      connecting: false,
      reconnect_attempts: 0
    }));
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && state.connected) {
      try {
        wsRef.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
        return false;
      }
    }
    return false;
  }, [state.connected]);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage
  };
};