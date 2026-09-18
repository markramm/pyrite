"""A minimal MCP-over-SSE client, enough to drive a live server as Claude does.

Not a test module: the SSE session fixture in conftest.py and the assertions in
test_mcp_sse.py both need it, and the stdio module compares against the tool
list it produces.
"""

from __future__ import annotations

import json
import queue
import threading

import httpx

SESSION_TIMEOUT = 60.0


class SSESession:
    """A live `GET /mcp/sse` stream, read on a background thread.

    The MCP SSE transport is genuinely asynchronous: responses to POSTed
    JSON-RPC requests come back down the SSE channel, not in the POST's own
    response body (which is a bare 202). So the stream has to be read
    concurrently with the POSTs, which is why this is a thread and not a loop.
    """

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.endpoint_path: str | None = None
        self._messages: queue.Queue[dict] = queue.Queue()
        self._ready = threading.Event()
        self._error: BaseException | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._read, daemon=True)

    def _read(self) -> None:
        try:
            with httpx.Client(
                base_url=self.base_url, timeout=SESSION_TIMEOUT, headers=self.headers
            ) as client:
                with client.stream("GET", "/mcp/sse") as resp:
                    resp.raise_for_status()
                    assert resp.headers["content-type"].startswith("text/event-stream")
                    event = None
                    for raw in resp.iter_lines():
                        if self._stop.is_set():
                            return
                        line = raw.rstrip("\r")
                        if line.startswith("event:"):
                            event = line[len("event:") :].strip()
                        elif line.startswith("data:"):
                            data = line[len("data:") :].strip()
                            if event == "endpoint":
                                self.endpoint_path = data
                                self._ready.set()
                            elif event == "message":
                                self._messages.put(json.loads(data))
                        elif line == "":
                            event = None
        except BaseException as exc:  # noqa: BLE001 - re-raised on the main thread
            self._error = exc
            self._ready.set()

    def __enter__(self) -> SSESession:
        self._thread.start()
        if not self._ready.wait(SESSION_TIMEOUT):
            raise AssertionError("no `event: endpoint` arrived on /mcp/sse")
        if self._error is not None:
            raise AssertionError(f"SSE stream failed: {self._error!r}")
        return self

    def __exit__(self, *exc_info) -> None:
        self._stop.set()

    def post(self, message: dict) -> httpx.Response:
        assert self.endpoint_path, "no endpoint event yet"
        with httpx.Client(
            base_url=self.base_url, timeout=SESSION_TIMEOUT, headers=self.headers
        ) as client:
            return client.post(self.endpoint_path, json=message)

    def request(self, id_: int, method: str, params: dict | None = None) -> dict:
        """POST a JSON-RPC request and wait for its reply on the SSE stream."""
        msg: dict = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        resp = self.post(msg)
        assert resp.status_code in (200, 202), (method, resp.status_code, resp.text)
        return self._await_response(id_)

    def _await_response(self, request_id: int) -> dict:
        seen: list[dict] = []
        while True:
            try:
                msg = self._messages.get(timeout=SESSION_TIMEOUT)
            except queue.Empty:
                raise AssertionError(
                    f"no response to request id={request_id} within {SESSION_TIMEOUT}s; saw {seen}"
                ) from None
            if msg.get("id") == request_id:
                return msg
            seen.append(msg)


def handshake(session: SSESession) -> dict:
    """initialize + notifications/initialized, as a real client does."""
    reply = session.request(
        1,
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pyrite-smoke", "version": "0"},
        },
    )
    assert "result" in reply, reply
    session.post({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return reply["result"]
