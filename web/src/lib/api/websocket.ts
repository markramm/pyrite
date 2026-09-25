/**
 * WebSocket client for multi-tab awareness.
 *
 * The server fixes a socket's readable KBs at handshake, for the connection's
 * life (#218, #323). So the socket must follow the signed-in user: the root
 * layout calls `follow(identity)` whenever `authStore.socketIdentity` changes,
 * and a change closes the current socket and opens exactly one new one (#336).
 *
 * Reconnects with exponential backoff (1 s doubling to 30 s) after a drop.
 *
 * A handshake the server refuses is closed before `accept`, which a browser
 * reports as close code 1006 (not 1008): the same code as a backend that is
 * restarting or a proxy answering 502 mid-deploy. So the client cannot tell a
 * refusal from a transient failure by code, and uses a heuristic instead. A
 * handshake that fails without any socket having opened for this identity is
 * retried twice with the backoff. After that it is reported as `refused` and
 * left alone until the identity changes, the browser comes back `online`, or
 * the tab becomes visible, each of which earns one more attempt. The
 * heuristic can be wrong both ways. A long outage at page load reads as a
 * refusal (recovered on the next of those events or a reload). A refusal
 * after this identity once connected reads as a drop and keeps backing off
 * (at most every 30 s).
 */

export interface WSEvent {
	type: 'entry_created' | 'entry_updated' | 'entry_deleted' | 'kb_synced';
	entry_id: string;
	kb_name: string;
}

/**
 * `idle`: no socket wanted (signed out with no anonymous access, or torn
 * down). `connecting`: a socket is opening. `open`: live. `closed`: dropped,
 * a reconnect is scheduled. `refused`: every handshake for this identity
 * failed without opening, retries included; see the header for when it is
 * tried again.
 */
export type WSStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'refused';

type WSEventHandler = (event: WSEvent) => void;

const INITIAL_RECONNECT_DELAY = 1000;
/** Retries of a handshake that has never opened for this identity, before `refused`. */
const UNOPENED_RETRIES = 2;

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
	/** Handshakes that failed without opening since the last `connect()`. */
	private unopenedFailures = 0;
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
		this.unopenedFailures = 0;
		this.reconnectDelay = INITIAL_RECONNECT_DELAY;
		window.addEventListener('online', this.retryIfRefused);
		document.addEventListener('visibilitychange', this.retryIfVisible);
		this.doConnect();
	}

	/**
	 * One more attempt for a refused socket, when something that could have
	 * changed the answer happened (network back, tab back). A failure of that
	 * attempt settles on `refused` again at once.
	 */
	private retryIfRefused = () => {
		if (this._status !== 'refused') return;
		// `unopenedFailures` is still at its limit, so this is one attempt.
		this.shouldConnect = true;
		this.doConnect();
	};

	private retryIfVisible = () => {
		if (document.visibilityState === 'visible') this.retryIfRefused();
	};

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
					// Closed without this identity's socket ever opening: a
					// refusal, or a transient failure at page load. Retry a
					// bounded number of times, then settle on refused.
					if (this.unopenedFailures >= UNOPENED_RETRIES) {
						this.shouldConnect = false;
						this.setStatus('refused');
						return;
					}
					this.unopenedFailures++;
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
		if (typeof window !== 'undefined') {
			window.removeEventListener('online', this.retryIfRefused);
			document.removeEventListener('visibilitychange', this.retryIfVisible);
		}
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
