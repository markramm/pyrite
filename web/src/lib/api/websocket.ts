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
	private _connected = false;
	private statusListeners: Set<(connected: boolean) => void> = new Set();

	constructor() {
		const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8088';
		this.url = `${protocol}//${host}/ws`;
	}

	get connected(): boolean {
		return this._connected;
	}

	private setConnected(value: boolean) {
		if (this._connected !== value) {
			this._connected = value;
			this.statusListeners.forEach((fn) => fn(value));
		}
	}

	onStatusChange(handler: (connected: boolean) => void): () => void {
		this.statusListeners.add(handler);
		return () => this.statusListeners.delete(handler);
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
				this.setConnected(true);
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
				this.setConnected(false);
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
		this.setConnected(false);
	}

	onEvent(handler: WSEventHandler): () => void {
		this.handlers.add(handler);
		return () => this.handlers.delete(handler);
	}
}

export const wsClient = new WebSocketClient();
