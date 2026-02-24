/**
 * WebSocket client for multi-tab awareness.
 *
 * Auto-connects on init, auto-reconnects with exponential backoff.
 * Dispatches custom events for entry changes.
 */

export interface WSEvent {
	type: 'entry_created' | 'entry_updated' | 'entry_deleted' | 'kb_synced';
	entry_id: string;
	kb_name: string;
}

type WSEventHandler = (event: WSEvent) => void;

class WebSocketClient {
	private ws: WebSocket | null = null;
	private url: string;
	private reconnectDelay = 1000;
	private maxReconnectDelay = 30000;
	private handlers: Set<WSEventHandler> = new Set();
	private shouldConnect = false;

	constructor() {
		const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8088';
		this.url = `${protocol}//${host}/ws`;
	}

	connect() {
		if (typeof window === 'undefined') return;
		this.shouldConnect = true;
		this.doConnect();
	}

	private doConnect() {
		if (!this.shouldConnect) return;
		try {
			this.ws = new WebSocket(this.url);

			this.ws.onopen = () => {
				this.reconnectDelay = 1000;
			};

			this.ws.onmessage = (event) => {
				try {
					const data: WSEvent = JSON.parse(event.data);
					this.handlers.forEach((handler) => handler(data));
				} catch {
					// Ignore malformed messages
				}
			};

			this.ws.onclose = () => {
				this.ws = null;
				if (this.shouldConnect) {
					setTimeout(() => this.doConnect(), this.reconnectDelay);
					this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
				}
			};

			this.ws.onerror = () => {
				this.ws?.close();
			};
		} catch {
			// Connection failed, will retry via onclose
		}
	}

	disconnect() {
		this.shouldConnect = false;
		this.ws?.close();
		this.ws = null;
	}

	onEvent(handler: WSEventHandler): () => void {
		this.handlers.add(handler);
		return () => this.handlers.delete(handler);
	}
}

export const wsClient = new WebSocketClient();
