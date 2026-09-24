"""`resources/read` actually serves content over a real MCP session (#217).

`_read_resource` (the internal method) has always computed the right
answer -- `tests/test_mcp_read_scoping.py::TestResourcesAreScoped` calls it
directly and it has been correct throughout. What was broken is the SDK
adapter in `build_sdk_server`'s `@sdk.read_resource()` closure: it returned a
`ReadResourceResult`, but the installed SDK (`mcp` 1.26.0)'s
`lowlevel/server.py` `read_resource` decorator expects the handler to return
either a bare `str`/`bytes` (deprecated) or an `Iterable[ReadResourceContents]`
-- a dataclass with `.content`/`.mime_type` -- which it then wraps itself.
Returning a `ReadResourceResult` falls through the `case _:` branch and
raises `ValueError(f"Unexpected return type ...")` for every resource, on
every transport, since the resource was introduced.

This file drives a real `ClientSession` over the SDK's in-memory transport
(the same harness `test_mcp_read_scoping.py` uses for tools), rather than
calling `PyriteMCPServer._read_resource` directly, because that is exactly
the path that was dead: proving the internal method works again would prove
nothing about the wiring.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.services.auth_service import AuthService
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

PUBLIC, PRIVATE = "public-kb", "private-kb"


@pytest.fixture
def env():
    """One public KB, one private KB, a plain read-tier peer and a granted one.

    Mirrors the fixture in `test_mcp_read_scoping.py` so #201 criterion 6 is
    exercised against the same world the tool-scoping tests use.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / PUBLIC).mkdir()
        (tmp / PRIVATE).mkdir()
        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name=PUBLIC, path=tmp / PUBLIC, kb_type="generic", default_role="read"),
                KBConfig(name=PRIVATE, path=tmp / PRIVATE, kb_type="generic", default_role="none"),
            ],
            settings=Settings(
                index_path=tmp / "index.db",
                auth=AuthConfig(enabled=True, allow_registration=True, anonymous_tier="read"),
            ),
        )
        db = PyriteDB(config.settings.index_path)
        svc = KBService(config, db)
        svc.create_entry(PUBLIC, "public-note", "Public note", "note", "zebra in the open")
        svc.create_entry(PRIVATE, "secret-note", "Secret note", "note", "zebra behind the wall")

        auth = AuthService(db, config.settings.auth)
        auth.register("admin-user", "password123")  # first user is admin
        auth.register("peer", "password123")  # plain read-tier

        server = PyriteMCPServer(config=config, tier="read")

        try:
            yield {
                "server": server,
                "auth": auth,
                "users": {u["username"]: u for u in auth.list_users()},
            }
        finally:
            server.close()
            db.close()


def _read_resource(env, uri, *, readable_kbs=None):
    """Drive one real `resources/read` over the SDK's in-memory transport.

    A protocol-level error (`McpError`) raised inside the SDK's in-memory
    transport reaches the caller wrapped in an `anyio` `ExceptionGroup` when
    it unwinds the `async with` on the way out, rather than as a bare
    `McpError` -- an artifact of the transport, not something callers of
    this helper should have to know. Unwrap it so `pytest.raises(McpError)`
    at the call site sees the real exception.
    """
    from mcp import McpError
    from mcp.shared.memory import create_connected_server_and_client_session

    sdk = env["server"].build_sdk_server(client_id="tester", readable_kbs=readable_kbs)

    async def _run():
        async with create_connected_server_and_client_session(sdk) as session:
            return await session.read_resource(uri)

    try:
        return asyncio.run(_run())
    except BaseExceptionGroup as eg:
        mcp_errors = eg.exceptions
        # anyio may nest one ExceptionGroup inside another as each context
        # manager in the `async with` chain unwinds; walk down to the leaf.
        while len(mcp_errors) == 1 and isinstance(mcp_errors[0], BaseExceptionGroup):
            mcp_errors = mcp_errors[0].exceptions
        if len(mcp_errors) == 1 and isinstance(mcp_errors[0], McpError):
            raise mcp_errors[0] from eg
        raise


class TestResourcesReadOverARealSession:
    """Each of the three URI shapes returns content -- not the SDK's
    `ValueError(f"Unexpected return type from read_resource: ...")`."""

    def test_kbs_list(self, env):
        result = _read_resource(env, "pyrite://kbs")
        payload = json.loads(result.contents[0].text)
        names = {k["name"] for k in payload}
        assert names == {PUBLIC, PRIVATE}

    def test_kb_entries(self, env):
        result = _read_resource(env, f"pyrite://kbs/{PUBLIC}/entries")
        payload = json.loads(result.contents[0].text)
        assert any(e.get("id") == "public-note" for e in payload)

    def test_entry(self, env):
        result = _read_resource(env, "pyrite://entries/public-note")
        payload = json.loads(result.contents[0].text)
        assert payload.get("id") == "public-note" or "zebra in the open" in json.dumps(payload)


class TestResourcesAreScopedOverARealSession:
    """#201 criterion 6, over the session that was dead until now: a plain
    read-tier peer without a grant on the private KB does not see it listed,
    and reading it directly is refused -- not served."""

    def test_kbs_list_omits_the_private_kb(self, env):
        result = _read_resource(env, "pyrite://kbs", readable_kbs={PUBLIC})
        payload = json.loads(result.contents[0].text)
        names = {k["name"] for k in payload}
        assert names == {PUBLIC}

    def test_kb_entries_on_the_private_kb_is_refused(self, env):
        from mcp import McpError

        with pytest.raises(McpError):
            _read_resource(env, f"pyrite://kbs/{PRIVATE}/entries", readable_kbs={PUBLIC})

    def test_entry_in_the_private_kb_is_refused(self, env):
        from mcp import McpError

        with pytest.raises(McpError):
            _read_resource(env, "pyrite://entries/secret-note", readable_kbs={PUBLIC})

    def test_a_readable_entry_still_works(self, env):
        result = _read_resource(env, "pyrite://entries/public-note", readable_kbs={PUBLIC})
        assert "zebra in the open" in result.contents[0].text
