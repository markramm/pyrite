/**
 * WebSocket client for multi-tab awareness.
 *
 * The server fixes a socket's readable KBs at handshake, for the connection's
 * life (#218, #323). So the socket must follow the signed-in user: the root
 * layout calls `follow(identity)` whenever `authStore.socketIdentity` changes,
 * and a change closes the current socket and opens exactly one new one (#336).
 *
 * Reconnects with exponential backoff after a socket that had opened drops.
 * A handshake the server refuses is closed before `accept`, which a browser
 * reports as close code 1006 (not 1008), so the client cannot tell a refusal
 * from a dropped connection by code. It uses the one signal it has: no socket
 * has opened for this identity yet. That is a refusal, reported as the
 * `refused` status and not retried until the identity changes -- nothing else
 * could change the server's answer.
 */

export interface WSEvent {
	type: 'entry_created' | 'entry_updated' | 'entry_deleted' | 'kb_synced';
	entry_id: string;
	kb_name: string;
}

/**
 * `idle`: no socket wanted (signed out with no anonymous access, or torn
 * down). `connecting`: a socket is opening. `open`: live. `closed`: dropped,
 * a reconnect is scheduled. `refused`: the server would not admit this
 * identity; not retried until it changes.
 */
export type WSStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'refused';

type WSEventHandler = (event: WSEvent) => void;

const INITIAL_RECONNECT_DELAY = 1000;

export class WebSocketClient {
	private ws: WebSocket | null = null;
	private url: string;
	private reconnectDelay = INITIAL_RECONNECT_DELAY;
	private maxReconnectDelay = 30000;
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private handlers: Set<WSEventHandler> = new Set();
	private shouldConnect = false;
	/** Whether any socket has opened since the last `connect()`. */
	private everOpened = false;
	/** The identity the current socket was opened for; undefined before any `follow`. */
	private identity: string | null | undefined = undefined;
	private _status: WSStatus = 'idle';
	private statusListeners: Set<(status: WSStatus) => void> = new Set();

	constructor() {
		const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8088';
		this.url = `${protocol}//${host}/ws`;
	}

	get status(): WSStatus {
		return this._status;
	}

	get connected(): boolean {
		return this._status === 'open';
	}

	private setStatus(value: WSStatus) {
		if (this._status !== value) {
			this._status = value;
			this.statusListeners.forEach((fn) => fn(value));
		}
	}

	onStatus(handler: (status: WSStatus) => void): () => void {
		this.statusListeners.add(handler);
		return () => this.statusListeners.delete(handler);
	}

	/**
	 * Hold one socket for `identity`, or none for `null`.
	 *
	 * The same identity again is a no-op, including while refused. A different
	 * one tears the current socket down and, unless it is `null`, opens a new
	 * one with a fresh backoff and a fresh refusal check.
	 */
	follow(identity: string | null) {
		if (identity === this.identity) return;
		this.disconnect();
		this.identity = identity;
		if (identity !== null) this.connect();
	}

	connect() {
		if (typeof window === 'undefined') return;
		this.shouldConnect = true;
		this.everOpened = false;
		this.doConnect();
	}

	private doConnect() {
		this.reconnectTimer = null;
		if (!this.shouldConnect) return;
		this.setStatus('connecting');
		try {
			const ws = new WebSocket(this.url);
			this.ws = ws;

			ws.onopen = () => {
				this.everOpened = true;
				this.reconnectDelay = INITIAL_RECONNECT_DELAY;
				this.setStatus('open');
			};

			ws.onmessage = (event) => {
				try {
					const data: WSEvent = JSON.parse(event.data);
					this.handlers.forEach((handler) => handler(data));
				} catch {
					// Ignore malformed messages
				}
			};

			ws.onclose = () => {
				this.ws = null;
				if (!this.everOpened) {
					// Closed without this identity's socket ever opening: the
					// server refused the handshake. Retrying cannot help.
					this.shouldConnect = false;
					this.setStatus('refused');
					return;
				}
				this.setStatus('closed');
				if (this.shouldConnect) {
					this.reconnectTimer = setTimeout(() => this.doConnect(), this.reconnectDelay);
					this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
				}
			};

			ws.onerror = () => {
				ws.close();
			};
		} catch {
			// The constructor threw (bad URL, blocked scheme): nothing to retry.
			this.ws = null;
			this.shouldConnect = false;
			this.setStatus('refused');
		}
	}

	/**
	 * Close the current socket for good.
	 *
	 * Its handlers are detached first: a browser fires `onclose`
	 * asynchronously after `close()`, and a late `onclose` from a socket being
	 * replaced would otherwise null out the new socket and schedule a second
	 * one -- still carrying the old identity's scope. A pending reconnect is
	 * cancelled for the same reason.
	 */
	disconnect() {
		// Forgotten, so a later `follow` of the same identity reopens.
		this.identity = undefined;
		this.shouldConnect = false;
		if (this.reconnectTimer !== null) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		const ws = this.ws;
		this.ws = null;
		if (ws) {
			ws.onopen = null;
			ws.onmessage = null;
			ws.onclose = null;
			ws.onerror = null;
			ws.close();
		}
		this.setStatus('idle');
	}

	onEvent(handler: WSEventHandler): () => void {
		this.handlers.add(handler);
		return () => this.handlers.delete(handler);
	}
}

export const wsClient = new WebSocketClient();
