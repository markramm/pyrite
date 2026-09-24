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

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

PUBLIC, PRIVATE = "public-kb", "private-kb"


@pytest.fixture
def env():
    """One public KB, one private KB.

    Every test here passes `readable_kbs` directly (as the per-connection
    closure `build_sdk_server` builds it already resolved), so there is no
    caller to authenticate -- unlike `test_mcp_read_scoping.py`, which drives
    calls *as* a named user and so needs `AuthService` to resolve that user's
    readable set. No auth setup here.
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
            settings=Settings(index_path=tmp / "index.db"),
        )
        db = PyriteDB(config.settings.index_path)
        svc = KBService(config, db)
        svc.create_entry(PUBLIC, "public-note", "Public note", "note", "zebra in the open")
        svc.create_entry(PRIVATE, "secret-note", "Secret note", "note", "zebra behind the wall")

        server = PyriteMCPServer(config=config, tier="read")

        try:
            yield {"server": server}
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
    and reading it directly is refused -- not served.

    Each refusal asserts the *specific* message `_read_resource` (the
    internal method) returns for an unreadable KB, not just "some McpError
    was raised". Before #217's fix, every resource read -- refused or not --
    raised `McpError` (the internal method's `{"error": ...}` payload was
    turned into a bare `ValueError` and re-raised, which the SDK reports as a
    protocol error same as any other exception from the handler): a bare
    `pytest.raises(McpError)` passed just as well against the broken
    pre-#217 code, proving nothing about scoping. Matching the message pins
    it to the *refusal* specifically, and to the same message a genuinely
    absent KB gets (`_kb_not_found`'s byte-identical-to-absent contract,
    covered directly in `test_mcp_read_scoping.py`), not some other error
    that happens to also raise.
    """

    def test_kbs_list_omits_the_private_kb(self, env):
        result = _read_resource(env, "pyrite://kbs", readable_kbs={PUBLIC})
        payload = json.loads(result.contents[0].text)
        names = {k["name"] for k in payload}
        assert names == {PUBLIC}

    def test_kb_entries_on_the_private_kb_is_refused(self, env):
        from mcp import McpError

        with pytest.raises(McpError, match=r"KB 'private-kb' not found"):
            _read_resource(env, f"pyrite://kbs/{PRIVATE}/entries", readable_kbs={PUBLIC})

    def test_entry_in_the_private_kb_is_refused(self, env):
        from mcp import McpError

        with pytest.raises(McpError, match=r"Entry 'secret-note' not found"):
            _read_resource(env, "pyrite://entries/secret-note", readable_kbs={PUBLIC})

    def test_a_missing_kb_and_a_private_kb_give_the_same_message_shape(self, env):
        """The refusal must be indistinguishable from genuine absence (the
        `_kb_not_found` contract): same wording, whether the KB does not
        exist at all or exists but is unreadable."""
        from mcp import McpError

        with pytest.raises(McpError, match=r"KB 'no-such-kb' not found") as absent:
            _read_resource(env, "pyrite://kbs/no-such-kb/entries", readable_kbs={PUBLIC})
        with pytest.raises(McpError, match=r"KB 'private-kb' not found") as private:
            _read_resource(env, f"pyrite://kbs/{PRIVATE}/entries", readable_kbs={PUBLIC})

        absent_shape = str(absent.value).replace("no-such-kb", "{kb}")
        private_shape = str(private.value).replace(PRIVATE, "{kb}")
        assert absent_shape == private_shape

    def test_a_readable_entry_still_works(self, env):
        result = _read_resource(env, "pyrite://entries/public-note", readable_kbs={PUBLIC})
        assert "zebra in the open" in result.contents[0].text
