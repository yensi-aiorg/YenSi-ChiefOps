import { useEffect, useRef, useState, useCallback } from "react";

/* ------------------------------------------------------------------ */
/*  useWebSocket – managed WebSocket connection with auto-reconnect    */
/* ------------------------------------------------------------------ */

/** WebSocket ready states mirroring the native enum */
export enum ReadyState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}

export interface UseWebSocketOptions {
  /** Called when a message is received */
  onMessage?: (event: MessageEvent) => void;
  /** Called when the connection opens */
  onOpen?: (event: Event) => void;
  /** Called when the connection closes */
  onClose?: (event: CloseEvent) => void;
  /** Called on connection error */
  onError?: (event: Event) => void;
  /** Whether to automatically reconnect on close (default: true) */
  autoReconnect?: boolean;
  /** Initial reconnect delay in ms (default: 1000). Doubles on each attempt up to 30s. */
  reconnectDelay?: number;
  /** Maximum number of reconnect attempts (default: Infinity) */
  maxReconnectAttempts?: number;
}

export interface UseWebSocketReturn {
  /** Send a string or serializable message over the socket */
  sendMessage: (data: string | ArrayBufferLike | Blob) => void;
  /** The most recently received MessageEvent (or null) */
  lastMessage: MessageEvent | null;
  /** Current ready state of the WebSocket */
  readyState: ReadyState;
  /** Manually disconnect (prevents auto-reconnect) */
  disconnect: () => void;
}

export function useWebSocket(
  url: string,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect = true,
    reconnectDelay = 1000,
    maxReconnectAttempts = Infinity,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isMountedRef = useRef(true);
  const shouldReconnectRef = useRef(autoReconnect);

  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [readyState, setReadyState] = useState<ReadyState>(ReadyState.CLOSED);

  // Keep latest callbacks in refs to avoid reconnect on callback identity change
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  onMessageRef.current = onMessage;
  onOpenRef.current = onOpen;
  onCloseRef.current = onClose;
  onErrorRef.current = onError;

  const connect = useCallback(() => {
    if (!isMountedRef.current) return;

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;
    setReadyState(ReadyState.CONNECTING);

    ws.onopen = (event) => {
      if (!isMountedRef.current) return;
      setReadyState(ReadyState.OPEN);
      reconnectAttemptsRef.current = 0;
      onOpenRef.current?.(event);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!isMountedRef.current) return;
      setLastMessage(event);
      onMessageRef.current?.(event);
    };

    ws.onerror = (event) => {
      if (!isMountedRef.current) return;
      onErrorRef.current?.(event);
    };

    ws.onclose = (event) => {
      if (!isMountedRef.current) return;
      setReadyState(ReadyState.CLOSED);
      onCloseRef.current?.(event);

      // Auto-reconnect with exponential backoff
      if (
        shouldReconnectRef.current &&
        reconnectAttemptsRef.current < maxReconnectAttempts
      ) {
        const delay = Math.min(
          reconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
          30_000, // cap at 30 seconds
        );
        reconnectAttemptsRef.current += 1;

        reconnectTimerRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            connect();
          }
        }, delay);
      }
    };
  }, [url, reconnectDelay, maxReconnectAttempts]);

  // Connect on mount / url change
  useEffect(() => {
    isMountedRef.current = true;
    shouldReconnectRef.current = autoReconnect;
    connect();

    return () => {
      isMountedRef.current = false;
      shouldReconnectRef.current = false;

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect, autoReconnect]);

  const sendMessage = useCallback(
    (data: string | ArrayBufferLike | Blob) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      } else if (import.meta.env.DEV) {
        console.warn(
          "[useWebSocket] Cannot send message: WebSocket is not open.",
        );
      }
    },
    [],
  );

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setReadyState(ReadyState.CLOSED);
  }, []);

  return { sendMessage, lastMessage, readyState, disconnect };
}
