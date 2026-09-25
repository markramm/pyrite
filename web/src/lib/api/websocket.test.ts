/**
 * The live-update socket follows the signed-in user (#336).
 *
 * A fake `WebSocket` stands in for the browser's: it records every socket the
 * client opens, and the test decides when each one opens, delivers a message
 * or closes. A real browser fires `onclose` asynchronously after `close()`,
 * so the fake never fires it from `close()` itself -- a test that wants the
 * late close calls `fireClose()` on the old socket, which invokes whatever
 * handler is still attached to it.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { WebSocketClient, type WSEvent, type WSStatus } from './websocket';

class FakeWebSocket {
	static instances: FakeWebSocket[] = [];
	url: string;
	closeCalled = false;
	/** Set when the far end closed it (`fireClose`). */
	closedByPeer = false;
	onopen: ((ev: Event) => void) | null = null;
	onmessage: ((ev: MessageEvent) => void) | null = null;
	onclose: ((ev: CloseEvent) => void) | null = null;
	onerror: ((ev: Event) => void) | null = null;

	constructor(url: string) {
		this.url = url;
		FakeWebSocket.instances.push(this);
	}

	close() {
		this.closeCalled = true;
	}

	fireOpen() {
		this.onopen?.(new Event('open'));
	}

	fireMessage(data: unknown) {
		this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
	}

	/** What the browser reports for a refused upgrade: 1006, never 1008. */
	fireClose(code = 1006) {
		this.closedByPeer = true;
		this.onclose?.(new CloseEvent('close', { code }));
	}
}

/** Sockets neither end has closed: at most one may ever be live. */
function live(): FakeWebSocket[] {
	return FakeWebSocket.instances.filter((s) => !s.closeCalled && !s.closedByPeer);
}

function latest(): FakeWebSocket {
	return FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
}

const EVENT: WSEvent = { type: 'entry_created', entry_id: 'e1', kb_name: 'kb' };

let client: WebSocketClient;

beforeEach(() => {
	vi.useFakeTimers();
	FakeWebSocket.instances = [];
	vi.stubGlobal('WebSocket', FakeWebSocket);
	client = new WebSocketClient();
});

afterEach(() => {
	client.disconnect();
	vi.unstubAllGlobals();
	vi.useRealTimers();
});

describe('follow: one socket per signed-in identity', () => {
	it('opens exactly one socket for an identity', () => {
		client.follow('user:1');
		expect(FakeWebSocket.instances).toHaveLength(1);
		expect(client.status).toBe('connecting');
	});

	it('does not reopen when the same identity is followed again', () => {
		client.follow('user:1');
		latest().fireOpen();
		client.follow('user:1');
		expect(FakeWebSocket.instances).toHaveLength(1);
		expect(client.status).toBe('open');
	});

	it('closes the old socket and opens exactly one new one when the user changes', () => {
		client.follow('user:1');
		const old = latest();
		old.fireOpen();

		client.follow('user:2');

		expect(old.closeCalled).toBe(true);
		expect(FakeWebSocket.instances).toHaveLength(2);
		expect(live()).toEqual([latest()]);
	});

	it('detaches every handler from the socket it replaces', () => {
		client.follow('user:1');
		const old = latest();
		old.fireOpen();

		client.follow('user:2');

		expect(old.onopen).toBeNull();
		expect(old.onmessage).toBeNull();
		expect(old.onclose).toBeNull();
		expect(old.onerror).toBeNull();
	});

	it('delivers nothing from the old socket after the user changes', () => {
		const seen: WSEvent[] = [];
		client.onEvent((e) => seen.push(e));
		client.follow('user:1');
		const old = latest();
		old.fireOpen();

		client.follow('user:2');
		old.fireMessage(EVENT);

		expect(seen).toEqual([]);
	});

	it('closes the socket and opens none when the identity becomes null (logged out)', () => {
		client.follow('user:1');
		const old = latest();
		old.fireOpen();

		client.follow(null);

		expect(old.closeCalled).toBe(true);
		expect(live()).toEqual([]);
		expect(client.status).toBe('idle');
		vi.advanceTimersByTime(60_000);
		expect(FakeWebSocket.instances).toHaveLength(1);
	});

	it('reopens for the same identity after an explicit disconnect (a remounted layout)', () => {
		client.follow('user:1');
		client.disconnect();
		client.follow('user:1');
		expect(FakeWebSocket.instances).toHaveLength(2);
		expect(live()).toEqual([latest()]);
	});

	it('opens a socket once an identity appears (logged in)', () => {
		client.follow(null);
		expect(FakeWebSocket.instances).toHaveLength(0);
		client.follow('user:1');
		expect(FakeWebSocket.instances).toHaveLength(1);
	});
});

describe('a late onclose from a replaced socket', () => {
	it('schedules no reconnect and does not clear the new socket', () => {
		const seen: WSEvent[] = [];
		client.onEvent((e) => seen.push(e));
		client.connect();
		const old = latest();
		old.fireOpen();

		client.disconnect();
		client.connect();
		const current = latest();
		current.fireOpen();

		// The browser delivers the old socket's close after the new one exists.
		old.fireClose(1000);
		vi.advanceTimersByTime(60_000);

		expect(FakeWebSocket.instances).toHaveLength(2);
		expect(client.status).toBe('open');
		current.fireMessage(EVENT);
		expect(seen).toEqual([EVENT]);
	});

	it('a reconnect already scheduled for the old identity does not fire after a change', () => {
		client.follow('user:1');
		const first = latest();
		first.fireOpen();
		first.fireClose(1001); // server restart: a reconnect is now scheduled

		client.follow('user:2');
		vi.advanceTimersByTime(60_000);

		expect(FakeWebSocket.instances).toHaveLength(2);
		expect(live()).toEqual([latest()]);
	});
});

/**
 * Fail the current handshake and every retry the client makes, until it
 * settles on `refused`: the first attempt plus two retries (1 s, then 2 s).
 */
function refuseEveryAttempt() {
	const before = FakeWebSocket.instances.length;
	latest().fireClose(1006);
	vi.advanceTimersByTime(1000);
	expect(FakeWebSocket.instances).toHaveLength(before + 1);
	latest().fireClose(1006);
	vi.advanceTimersByTime(2000);
	expect(FakeWebSocket.instances).toHaveLength(before + 2);
	latest().fireClose(1006);
	expect(client.status).toBe('refused');
}

describe('a refused handshake', () => {
	it('is retried twice with the backoff before it counts as refused', () => {
		const statuses: WSStatus[] = [];
		client.onStatus((s) => statuses.push(s));
		client.follow('anonymous');

		latest().fireClose(1006); // closed without ever opening
		expect(client.status).toBe('closed');
		vi.advanceTimersByTime(999);
		expect(FakeWebSocket.instances).toHaveLength(1);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances).toHaveLength(2);

		latest().fireClose(1006);
		expect(client.status).toBe('closed');
		vi.advanceTimersByTime(1999);
		expect(FakeWebSocket.instances).toHaveLength(2);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances).toHaveLength(3);

		latest().fireClose(1006);
		expect(client.status).toBe('refused');
		expect(statuses).toContain('refused');
		vi.advanceTimersByTime(10 * 60_000);
		expect(FakeWebSocket.instances).toHaveLength(3);
	});

	it('a transient failure of the first handshake recovers (a backend restarting at page load)', () => {
		client.follow('user:1');
		latest().fireClose(1006); // 502 from a proxy mid-deploy
		vi.advanceTimersByTime(1000);
		expect(FakeWebSocket.instances).toHaveLength(2);
		latest().fireOpen();
		expect(client.status).toBe('open');
	});

	it('stays refused when the same identity is followed again', () => {
		client.follow('anonymous');
		refuseEveryAttempt();
		client.follow('anonymous');
		expect(FakeWebSocket.instances).toHaveLength(3);
		expect(client.status).toBe('refused');
	});

	it('is retried once the user changes', () => {
		client.follow('anonymous');
		refuseEveryAttempt();

		client.follow('user:1');

		expect(FakeWebSocket.instances).toHaveLength(4);
		expect(client.status).toBe('connecting');
		latest().fireOpen();
		expect(client.status).toBe('open');
	});

	it("a refusal does not use up the next user's retries", () => {
		client.follow('anonymous');
		refuseEveryAttempt();

		client.follow('user:1');
		latest().fireClose(1006);

		expect(client.status).toBe('closed');
		vi.advanceTimersByTime(1000);
		expect(FakeWebSocket.instances).toHaveLength(5);
	});

	it('an error before open counts like a close (the browser fires error, then close)', () => {
		client.follow('anonymous');
		const s = latest();
		s.onerror?.(new Event('error'));
		expect(s.closeCalled).toBe(true);
		s.fireClose();
		expect(client.status).toBe('closed');
	});

	it('is retried once when the browser comes back online', () => {
		client.follow('anonymous');
		refuseEveryAttempt();

		window.dispatchEvent(new Event('online'));
		expect(FakeWebSocket.instances).toHaveLength(4);
		expect(client.status).toBe('connecting');

		// Once: a second refusal settles at once, with no further retries.
		latest().fireClose(1006);
		expect(client.status).toBe('refused');
		vi.advanceTimersByTime(10 * 60_000);
		expect(FakeWebSocket.instances).toHaveLength(4);
	});

	it('the online retry can recover', () => {
		client.follow('anonymous');
		refuseEveryAttempt();
		window.dispatchEvent(new Event('online'));
		expect(FakeWebSocket.instances).toHaveLength(4);
		latest().fireOpen();
		expect(client.status).toBe('open');
	});

	it('is retried once when the tab becomes visible, not when it is hidden', () => {
		const visibility = vi.spyOn(document, 'visibilityState', 'get');
		client.follow('anonymous');
		refuseEveryAttempt();

		visibility.mockReturnValue('hidden');
		document.dispatchEvent(new Event('visibilitychange'));
		expect(FakeWebSocket.instances).toHaveLength(3);

		visibility.mockReturnValue('visible');
		document.dispatchEvent(new Event('visibilitychange'));
		expect(FakeWebSocket.instances).toHaveLength(4);
		visibility.mockRestore();
	});

	it('online or visibility does nothing unless refused', () => {
		client.follow('user:1');
		latest().fireOpen();
		window.dispatchEvent(new Event('online'));
		document.dispatchEvent(new Event('visibilitychange'));
		expect(FakeWebSocket.instances).toHaveLength(1);

		client.follow(null);
		window.dispatchEvent(new Event('online'));
		expect(FakeWebSocket.instances).toHaveLength(1);
	});

	it('a disconnected client removes its online and visibility listeners', () => {
		const removedFromWindow = vi.spyOn(window, 'removeEventListener');
		const removedFromDocument = vi.spyOn(document, 'removeEventListener');
		client.follow('anonymous');
		client.disconnect();
		expect(removedFromWindow.mock.calls.map((c) => c[0])).toContain('online');
		expect(removedFromDocument.mock.calls.map((c) => c[0])).toContain('visibilitychange');
		removedFromWindow.mockRestore();
		removedFromDocument.mockRestore();
	});
});

describe('a socket the browser will not even construct', () => {
	it('is refused, not retried', () => {
		let attempts = 0;
		vi.stubGlobal(
			'WebSocket',
			class {
				constructor() {
					attempts++;
					throw new DOMException('blocked', 'SecurityError');
				}
			}
		);
		client.follow('user:1');
		expect(client.status).toBe('refused');
		vi.advanceTimersByTime(10 * 60_000);
		expect(attempts).toBe(1);
	});
});

describe('any other disconnect keeps the backoff', () => {
	it('a socket that had opened reconnects after 1s, then 2s', () => {
		client.follow('user:1');
		latest().fireOpen();
		latest().fireClose(1001);

		expect(client.status).toBe('closed');
		vi.advanceTimersByTime(999);
		expect(FakeWebSocket.instances).toHaveLength(1);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances).toHaveLength(2);

		// The server is still down: this attempt closes without opening. A
		// server restart is not a refusal, because this identity's socket has
		// opened before -- so the client keeps retrying, at the next delay.
		latest().fireClose(1006);
		expect(client.status).toBe('closed');
		vi.advanceTimersByTime(1999);
		expect(FakeWebSocket.instances).toHaveLength(2);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances).toHaveLength(3);
	});

	it('the backoff resets to 1s once a socket opens again', () => {
		client.follow('user:1');
		latest().fireOpen();
		latest().fireClose(1001);
		vi.advanceTimersByTime(1000);
		latest().fireClose(1006);
		vi.advanceTimersByTime(2000);
		latest().fireOpen();
		latest().fireClose(1001);

		vi.advanceTimersByTime(999);
		expect(FakeWebSocket.instances).toHaveLength(3);
		vi.advanceTimersByTime(1);
		expect(FakeWebSocket.instances).toHaveLength(4);
	});

	it('a new identity gets a fresh refusal count, even after the old one had opened', () => {
		client.follow('user:1');
		latest().fireOpen();
		latest().fireClose(1001);
		vi.advanceTimersByTime(1000);
		latest().fireClose(1006); // backoff now 2s

		client.follow('user:2');
		refuseEveryAttempt(); // never opened for user:2: refused after its retries

		expect(client.status).toBe('refused');
	});
});

describe('status', () => {
	it('connected is true only while a socket is open', () => {
		expect(client.connected).toBe(false);
		client.follow('user:1');
		expect(client.connected).toBe(false);
		latest().fireOpen();
		expect(client.connected).toBe(true);
		client.follow(null);
		expect(client.connected).toBe(false);
	});

	it('notifies each transition once', () => {
		const statuses: WSStatus[] = [];
		client.onStatus((s) => statuses.push(s));
		client.follow('user:1');
		latest().fireOpen();
		latest().fireClose(1001);
		expect(statuses).toEqual(['connecting', 'open', 'closed']);
	});
});
