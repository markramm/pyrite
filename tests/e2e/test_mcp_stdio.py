"""MCP over stdio: `pyrite mcp --tier read` as a subprocess, spoken to directly.

This is the transport Claude Desktop and Claude Code actually use. Nothing
exercised it end to end: `tests/test_mcp_tool_dispatch_smoke.py` calls the
handlers in process, which proves the handlers work and says nothing about
whether the console script starts, finds its config, negotiates a protocol
version, or keeps stdout clean enough to carry JSON-RPC.

That last one is the real risk of this transport: stdout *is* the protocol
stream, so a stray print anywhere in startup corrupts the session. The CLI
writes its banner to stderr for exactly this reason, and this test is what
would notice if that stopped being true.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import pytest

from .conftest import console_script, index_kb, seed_kb, smoke_env

pytestmark = pytest.mark.e2e

STDIO_TIMEOUT = 90.0


class StdioClient:
    """A `pyrite mcp` subprocess spoken to over newline-delimited JSON-RPC."""

    def __init__(self, data_dir: Path, tier: str = "read"):
        self.data_dir = data_dir
        self.proc = subprocess.Popen(
            [console_script("pyrite"), "mcp", "--tier", tier],
            env=smoke_env(data_dir),
            cwd=str(data_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._stderr: list[str] = []
        self._drain = threading.Thread(target=self._drain_stderr, daemon=True)
        self._drain.start()

    def _drain_stderr(self) -> None:
        # Drained on a thread so a chatty server cannot deadlock on a full pipe.
        assert self.proc.stderr is not None
        for line in self.proc.stderr:
            self._stderr.append(line)

    def stderr(self) -> str:
        return "".join(self._stderr) or "<no stderr>"

    def send(self, message: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def read(self) -> dict:
        """Read one JSON-RPC message from stdout.

        Non-JSON lines are a failure, not something to skip past: on this
        transport they mean something printed to the protocol stream.
        """
        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        if not line:
            raise AssertionError(
                f"`pyrite mcp` closed stdout (exit={self.proc.poll()}); stderr:\n{self.stderr()}"
            )
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"non-JSON line on the MCP stdout stream -- something printed to "
                f"stdout, which IS the protocol: {line!r}\nstderr:\n{self.stderr()}"
            ) from exc

    def request(self, id_: int, method: str, params: dict | None = None) -> dict:
        msg: dict = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        self.send(msg)
        while True:
            reply = self.read()
            if reply.get("id") == id_:
                return reply

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=10)


@pytest.fixture(scope="module")
def stdio_data_dir(tmp_path_factory) -> Path:
    data_dir = tmp_path_factory.mktemp("pyrite-smoke-stdio")
    kb_dir = data_dir / "smoke-kb"
    seed_kb(
        kb_dir,
        "smoke",
        title="Analytical Engine",
        body="Charles Babbage designed a mechanical general-purpose computer.",
    )
    import yaml

    (data_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "knowledge_bases": [
                    {
                        "name": "smoke",
                        "path": str(kb_dir),
                        "kb_type": "generic",
                        "description": "smoke",
                    }
                ],
                "settings": {"auto_embed": False},
            }
        )
    )
    index_kb(data_dir)
    return data_dir


@pytest.fixture(scope="module")
def stdio_session(stdio_data_dir) -> dict:
    """One complete read-tier stdio session; its findings, for several asserts."""
    client = StdioClient(stdio_data_dir, tier="read")
    try:
        init = client.request(
            1,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pyrite-smoke", "version": "0"},
            },
        )
        assert "result" in init, init
        client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        listed = client.request(2, "tools/list")
        assert "result" in listed, listed
        names = {tool["name"] for tool in listed["result"]["tools"]}

        called = client.request(
            3,
            "tools/call",
            {"name": "kb_search", "arguments": {"query": "Babbage", "kb_name": "smoke"}},
        )
        assert "result" in called, called
        text = "".join(block.get("text", "") for block in called["result"].get("content", []))
        return {"server_info": init["result"], "tool_names": names, "search_text": text}
    finally:
        client.close()


def test_stdio_session_initializes(stdio_session):
    assert "serverInfo" in stdio_session["server_info"], stdio_session["server_info"]


def test_stdio_exposes_every_declared_read_tool(stdio_session):
    """Superset of READ_TOOLS, for the same plugin reason as the SSE test."""
    from pyrite.server.tool_schemas import READ_TOOLS

    missing = set(READ_TOOLS) - stdio_session["tool_names"]
    assert not missing, f"declared read tools absent over stdio: {sorted(missing)}"


def test_stdio_read_tier_exposes_no_write_or_admin_tools(stdio_session):
    """`--tier read` must mean read. A leak here is a privilege bug."""
    from pyrite.server.tool_schemas import ADMIN_TOOLS, WRITE_TOOLS

    leaked = (set(WRITE_TOOLS) | set(ADMIN_TOOLS)) & stdio_session["tool_names"]
    assert not leaked, f"--tier read exposed write/admin tools: {sorted(leaked)}"


def test_kb_search_over_stdio_returns_the_seeded_entry(stdio_session):
    assert "Analytical Engine" in stdio_session["search_text"], stdio_session["search_text"]


def test_stdio_and_sse_advertise_the_same_read_tier_tools(stdio_session, sse_session_result):
    """The two transports must not drift.

    Both are the read tier of the same PyriteMCPServer, so any difference is a
    transport-layer bug (a tier resolved differently, a plugin registered on
    one path only) rather than a difference of intent.
    """
    if sse_session_result["unreachable"]:
        pytest.skip("the SSE endpoint is unroutable; test_mcp_sse.py reports why")
    assert stdio_session["tool_names"] == sse_session_result["tool_names"], {
        "stdio_only": sorted(stdio_session["tool_names"] - sse_session_result["tool_names"]),
        "sse_only": sorted(sse_session_result["tool_names"] - stdio_session["tool_names"]),
    }
