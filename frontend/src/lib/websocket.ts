/**
 * WebSocket connection states.
 */
export type ConnectionState = "connecting" | "connected" | "disconnected" | "reconnecting";

/**
 * Event listener callback type.
 */
type EventCallback = (data: unknown) => void;

/**
 * Incoming WebSocket message envelope.
 */
interface WSMessage {
  event: string;
  data: unknown;
  timestamp?: string;
}

/**
 * Configuration options for the WebSocket client.
 */
interface WebSocketClientOptions {
  /** WebSocket server URL (ws:// or wss://) */
  url: string;
  /** Maximum number of reconnection attempts (default: 10) */
  maxReconnectAttempts?: number;
  /** Base delay between reconnection attempts in ms (default: 1000) */
  reconnectBaseDelay?: number;
  /** Maximum delay between reconnection attempts in ms (default: 30000) */
  reconnectMaxDelay?: number;
  /** Heartbeat / ping interval in ms (default: 30000) */
  heartbeatInterval?: number;
  /** Protocols to pass to the WebSocket constructor */
  protocols?: string | string[];
}

/**
 * WebSocket client with automatic reconnection, event-based messaging,
 * and connection state management.
 *
 * Usage:
 * ```ts
 * const ws = new WebSocketClient({
 *   url: "ws://localhost:23101/ws",
 * });
 *
 * ws.on("health_update", (data) => {
 *   console.log("Health update:", data);
 * });
 *
 * ws.onStateChange((state) => {
 *   console.log("Connection state:", state);
 * });
 *
 * ws.connect();
 * ```
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private readonly options: Required<WebSocketClientOptions>;
  private listeners: Map<string, Set<EventCallback>> = new Map();
  private stateListeners: Set<(state: ConnectionState) => void> = new Set();
  private state: ConnectionState = "disconnected";
  private reconnectAttempts = 0;
  private reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private heartbeatIntervalId: ReturnType<typeof setInterval> | null = null;
  private manualClose = false;

  constructor(options: WebSocketClientOptions) {
    this.options = {
      maxReconnectAttempts: 10,
      reconnectBaseDelay: 1000,
      reconnectMaxDelay: 30000,
      heartbeatInterval: 30000,
      protocols: [],
      ...options,
    };
  }

  /**
   * Get the current connection state.
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Register a listener for connection state changes.
   */
  onStateChange(callback: (state: ConnectionState) => void): () => void {
    this.stateListeners.add(callback);
    return () => {
      this.stateListeners.delete(callback);
    };
  }

  /**
   * Register an event listener for a specific event type.
   * Returns an unsubscribe function.
   */
  on(event: string, callback: EventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  /**
   * Remove all listeners for a specific event, or all listeners if no event is specified.
   */
  off(event?: string): void {
    if (event) {
      this.listeners.delete(event);
    } else {
      this.listeners.clear();
    }
  }

  /**
   * Open the WebSocket connection.
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.manualClose = false;
    this.setState("connecting");

    try {
      this.ws = new WebSocket(
        this.options.url,
        this.options.protocols.length > 0 ? this.options.protocols : undefined,
      );
    } catch (error) {
      console.error("[WS] Failed to create WebSocket:", error);
      this.setState("disconnected");
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setState("connected");
      this.startHeartbeat();
      console.log("[WS] Connected to", this.options.url);
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this.handleMessage(event);
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.stopHeartbeat();

      if (this.manualClose) {
        this.setState("disconnected");
        console.log("[WS] Connection closed manually.");
        return;
      }

      console.warn(
        `[WS] Connection closed: code=${event.code} reason=${event.reason || "none"}`,
      );
      this.setState("disconnected");
      this.scheduleReconnect();
    };

    this.ws.onerror = (event: Event) => {
      console.error("[WS] Connection error:", event);
    };
  }

  /**
   * Send a typed message through the WebSocket.
   */
  send(event: string, data: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn("[WS] Cannot send message: not connected.");
      return;
    }

    const message: WSMessage = {
      event,
      data,
      timestamp: new Date().toISOString(),
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Close the WebSocket connection cleanly.
   */
  disconnect(): void {
    this.manualClose = true;
    this.clearReconnectTimeout();
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }

    this.setState("disconnected");
  }

  /**
   * Force a reconnection attempt.
   */
  reconnect(): void {
    this.disconnect();
    this.manualClose = false;
    this.reconnectAttempts = 0;
    this.connect();
  }

  /**
   * Destroy the client, removing all listeners and closing the connection.
   */
  destroy(): void {
    this.disconnect();
    this.listeners.clear();
    this.stateListeners.clear();
  }

  /* ---------------------------------------------------------------- */
  /*  Private methods                                                 */
  /* ---------------------------------------------------------------- */

  private setState(newState: ConnectionState): void {
    if (this.state === newState) return;
    this.state = newState;
    this.stateListeners.forEach((cb) => cb(newState));
  }

  private handleMessage(event: MessageEvent): void {
    let parsed: WSMessage;

    try {
      parsed = JSON.parse(event.data as string) as WSMessage;
    } catch {
      console.warn("[WS] Received non-JSON message:", event.data);
      return;
    }

    if (!parsed.event) {
      console.warn("[WS] Received message without event type:", parsed);
      return;
    }

    // Notify specific event listeners
    const callbacks = this.listeners.get(parsed.event);
    if (callbacks) {
      callbacks.forEach((cb) => cb(parsed.data));
    }

    // Notify wildcard listeners
    const wildcardCallbacks = this.listeners.get("*");
    if (wildcardCallbacks) {
      wildcardCallbacks.forEach((cb) => cb(parsed));
    }
  }

  private scheduleReconnect(): void {
    if (this.manualClose) return;
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error(
        `[WS] Max reconnection attempts (${this.options.maxReconnectAttempts}) reached. Giving up.`,
      );
      this.setState("disconnected");
      return;
    }

    this.reconnectAttempts++;
    this.setState("reconnecting");

    // Exponential backoff with jitter
    const baseDelay = this.options.reconnectBaseDelay;
    const maxDelay = this.options.reconnectMaxDelay;
    const exponentialDelay = baseDelay * Math.pow(2, this.reconnectAttempts - 1);
    const jitter = Math.random() * 0.3 * exponentialDelay;
    const delay = Math.min(exponentialDelay + jitter, maxDelay);

    console.log(
      `[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`,
    );

    this.reconnectTimeoutId = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeoutId !== null) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatIntervalId = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send("ping", { ts: Date.now() });
      }
    }, this.options.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatIntervalId !== null) {
      clearInterval(this.heartbeatIntervalId);
      this.heartbeatIntervalId = null;
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Default singleton instance                                        */
/* ------------------------------------------------------------------ */

/**
 * Resolve the WebSocket URL for the ChiefOps backend.
 */
function getDefaultWsUrl(): string {
  if (typeof import.meta !== "undefined" && import.meta.env?.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

/**
 * Default WebSocket client instance for the ChiefOps platform.
 * Import and use directly, or create your own instance with custom options.
 */
let defaultClient: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!defaultClient) {
    defaultClient = new WebSocketClient({
      url: getDefaultWsUrl(),
      maxReconnectAttempts: 10,
      reconnectBaseDelay: 1000,
      reconnectMaxDelay: 30000,
      heartbeatInterval: 30000,
    });
  }
  return defaultClient;
}

export default WebSocketClient;
