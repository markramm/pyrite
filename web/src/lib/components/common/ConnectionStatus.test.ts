/**
 * ConnectionStatus shows a refused handshake (#336).
 *
 * The server closes a refused handshake before `accept`, so the browser sees
 * a socket that closes without ever opening. The old banner listened for a
 * change of a boolean that started `false`, so `false -> false` never armed
 * it and a refusal was invisible.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, act } from '@testing-library/svelte';

import { wsClient } from '$lib/api/websocket';
import ConnectionStatus from './ConnectionStatus.svelte';

class FakeWebSocket {
	static instances: FakeWebSocket[] = [];
	onopen: ((ev: Event) => void) | null = null;
	onmessage: ((ev: MessageEvent) => void) | null = null;
	onclose: ((ev: CloseEvent) => void) | null = null;
	onerror: ((ev: Event) => void) | null = null;
	constructor() {
		FakeWebSocket.instances.push(this);
	}
	close() {}
}

function latest(): FakeWebSocket {
	return FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
}

const close = (code: number) => latest().onclose?.(new CloseEvent('close', { code }));

/** Fail the first handshake and both of its retries: the client settles on refused. */
function refuseEveryAttempt() {
	close(1006);
	vi.advanceTimersByTime(1000);
	close(1006);
	vi.advanceTimersByTime(2000);
	close(1006);
	expect(wsClient.status).toBe('refused');
}

/**
 * jsdom has no Web Animations API, so a Svelte `transition:` outro never
 * finishes and the banner would stay in the DOM. This animation finishes on
 * the next microtask.
 */
const originalAnimate = Element.prototype.animate;

function stubAnimate() {
	Element.prototype.animate = function () {
		const animation = {
			onfinish: null as null | (() => void),
			currentTime: 0,
			cancel() {},
			finish() {}
		};
		queueMicrotask(() => animation.onfinish?.());
		return animation as unknown as Animation;
	};
}

beforeEach(() => {
	stubAnimate();
	vi.useFakeTimers();
	FakeWebSocket.instances = [];
	vi.stubGlobal('WebSocket', FakeWebSocket);
});

afterEach(() => {
	cleanup();
	wsClient.follow(null);
	vi.unstubAllGlobals();
	vi.useRealTimers();
	Element.prototype.animate = originalAnimate;
});

describe('ConnectionStatus', () => {
	it('shows a refused handshake', async () => {
		render(ConnectionStatus);
		wsClient.follow('anonymous');

		await act(() => refuseEveryAttempt());

		expect(screen.getByRole('status')).toHaveTextContent('Real-time updates unavailable');
	});

	it('shows a refusal that happened before it mounted', async () => {
		wsClient.follow('anonymous');
		refuseEveryAttempt();

		render(ConnectionStatus);
		await act(() => {});

		expect(screen.getByRole('status')).toHaveTextContent('Real-time updates unavailable');
	});

	it('shows a dropped connection after the grace period, not before', async () => {
		render(ConnectionStatus);
		wsClient.follow('user:1');
		await act(() => latest().onopen?.(new Event('open')));
		await act(() => latest().onclose?.(new CloseEvent('close', { code: 1001 })));

		expect(screen.queryByRole('status')).toBeNull();
		await act(() => vi.advanceTimersByTime(3000));
		expect(screen.getByRole('status')).toHaveTextContent('Connection lost');
	});

	it('a second drop after reconnecting waits out the grace period again', async () => {
		render(ConnectionStatus);
		wsClient.follow('user:1');
		await act(() => latest().onopen?.(new Event('open')));
		await act(() => latest().onclose?.(new CloseEvent('close', { code: 1001 })));
		await act(() => vi.advanceTimersByTime(3000));
		expect(screen.getByRole('status')).toBeInTheDocument();

		// The scheduled reconnect opens a new socket, which opens.
		await act(() => vi.advanceTimersByTime(1000));
		await act(() => latest().onopen?.(new Event('open')));
		expect(screen.queryByRole('status')).toBeNull();

		await act(() => latest().onclose?.(new CloseEvent('close', { code: 1001 })));
		expect(screen.queryByRole('status')).toBeNull();
	});

	it('a dismissed "Connection lost" stays dismissed through the reconnect attempts', async () => {
		render(ConnectionStatus);
		wsClient.follow('user:1');
		await act(() => latest().onopen?.(new Event('open')));
		await act(() => close(1001));
		await act(() => vi.advanceTimersByTime(3000));
		// The 1 s reconnect has fired and is still connecting.
		await act(() => screen.getByRole('button', { name: 'Dismiss' }).click());
		expect(screen.queryByRole('status')).toBeNull();

		// Each attempt fails (the server is still down): closed, connecting, ...
		await act(() => close(1006));
		await act(() => vi.advanceTimersByTime(2000));
		await act(() => close(1006));
		await act(() => vi.advanceTimersByTime(4000));
		expect(wsClient.status).toBe('connecting');
		expect(screen.queryByRole('status')).toBeNull();
	});

	it('a dismissal lasts only until the status changes kind', async () => {
		render(ConnectionStatus);
		wsClient.follow('user:1');
		await act(() => latest().onopen?.(new Event('open')));
		await act(() => close(1001));
		await act(() => vi.advanceTimersByTime(3000));
		await act(() => screen.getByRole('button', { name: 'Dismiss' }).click());

		// Reconnected, then lost again: a new loss, shown after its grace period.
		await act(() => latest().onopen?.(new Event('open')));
		await act(() => close(1001));
		await act(() => vi.advanceTimersByTime(3000));
		expect(screen.getByRole('status')).toHaveTextContent('Connection lost');
	});

	it('shows nothing while signed out with no socket', async () => {
		render(ConnectionStatus);
		wsClient.follow('user:1');
		await act(() => latest().onopen?.(new Event('open')));
		await act(() => wsClient.follow(null));
		await act(() => vi.advanceTimersByTime(10_000));

		expect(screen.queryByRole('status')).toBeNull();
	});

	it('hides the refusal once the user changes and the new socket opens', async () => {
		render(ConnectionStatus);
		wsClient.follow('anonymous');
		await act(() => refuseEveryAttempt());
		expect(screen.getByRole('status')).toBeInTheDocument();

		await act(() => wsClient.follow('user:1'));
		await act(() => latest().onopen?.(new Event('open')));

		expect(screen.queryByRole('status')).toBeNull();
	});
});
