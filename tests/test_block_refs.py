"""Tests for block reference (Phase 2) — [[entry#heading]] and [[entry^block-id]] syntax."""
import pytest

from pyrite.storage.index import _WIKILINK_RE


class TestWikilinkRegexPhase2:
    """Test extended wikilink regex with heading and block-id groups."""

    def test_simple_wikilink(self):
        """[[entry]] still works (regression)."""
        m = _WIKILINK_RE.search("see [[my-entry]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(3) is None  # no heading
        assert m.group(4) is None  # no block-id

    def test_wikilink_with_heading(self):
        """[[entry#heading]] extracts heading group."""
        m = _WIKILINK_RE.search("see [[my-entry#introduction]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(3) == "introduction"
        assert m.group(4) is None

    def test_wikilink_with_block_id(self):
        """[[entry^block-id]] extracts block-id group."""
        m = _WIKILINK_RE.search("see [[my-entry^abc123]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(3) is None
        assert m.group(4) == "abc123"

    def test_wikilink_combined(self):
        """[[kb:entry#heading|display]] extracts all groups."""
        m = _WIKILINK_RE.search("see [[wiki:my-entry#intro|My Link]]")
        assert m is not None
        assert m.group(1) == "wiki"
        assert m.group(2) == "my-entry"
        assert m.group(3) == "intro"
        assert m.group(5) == "My Link"

    def test_wikilink_with_display(self):
        """[[entry|display]] still works."""
        m = _WIKILINK_RE.search("see [[my-entry|click here]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(5) == "click here"

    def test_wikilink_kb_prefix(self):
        """[[kb:entry]] still works."""
        m = _WIKILINK_RE.search("see [[wiki:my-entry]]")
        assert m is not None
        assert m.group(1) == "wiki"
        assert m.group(2) == "my-entry"

    def test_wikilink_heading_with_display(self):
        """[[entry#heading|display]] extracts heading and display."""
        m = _WIKILINK_RE.search("see [[my-entry#section|See Section]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(3) == "section"
        assert m.group(5) == "See Section"

    def test_wikilink_block_with_display(self):
        """[[entry^block|display]] extracts block and display."""
        m = _WIKILINK_RE.search("see [[my-entry^abc|Quote]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(4) == "abc"
        assert m.group(5) == "Quote"

    def test_multiple_wikilinks_in_text(self):
        """Multiple wikilinks with fragments in same text."""
        text = "Link to [[a#heading]] and [[b^block]] and [[c]]"
        matches = list(_WIKILINK_RE.finditer(text))
        assert len(matches) == 3
        assert matches[0].group(2) == "a"
        assert matches[0].group(3) == "heading"
        assert matches[1].group(2) == "b"
        assert matches[1].group(4) == "block"
        assert matches[2].group(2) == "c"


class TestIndexWikilinksWithFragments:
    """Test that indexing stores entry-level link + fragment in note."""

    def test_index_wikilinks_heading_fragment(self):
        """Wikilinks with #heading store fragment in link note field."""
        from pyrite.storage.index import _WIKILINK_RE

        body = "See [[target-entry#section-one]] for details"
        links = []
        for match in _WIKILINK_RE.finditer(body):
            kb_prefix = match.group(1)
            target = match.group(2).strip()
            heading = match.group(3)
            block_id = match.group(4)
            note = ""
            if heading:
                note = f"#{heading}"
            elif block_id:
                note = f"^{block_id}"
            links.append({"target": target, "note": note})

        assert len(links) == 1
        assert links[0]["target"] == "target-entry"
        assert links[0]["note"] == "#section-one"

    def test_index_wikilinks_block_fragment(self):
        """Wikilinks with ^block store fragment in link note field."""
        from pyrite.storage.index import _WIKILINK_RE

        body = "See [[target-entry^def456]] for details"
        links = []
        for match in _WIKILINK_RE.finditer(body):
            target = match.group(2).strip()
            heading = match.group(3)
            block_id = match.group(4)
            note = ""
            if heading:
                note = f"#{heading}"
            elif block_id:
                note = f"^{block_id}"
            links.append({"target": target, "note": note})

        assert len(links) == 1
        assert links[0]["target"] == "target-entry"
        assert links[0]["note"] == "^def456"


class TestResolveEndpoint:
    """Test resolve endpoint with fragment parsing."""

    def test_resolve_response_schema_has_fragment_fields(self):
        """ResolveResponse has heading, block_id, block_content fields."""
        from pyrite.server.schemas import ResolveResponse

        resp = ResolveResponse(
            resolved=True,
            entry=None,
            heading="my-heading",
            block_id="abc123",
            block_content="Some content",
        )
        assert resp.heading == "my-heading"
        assert resp.block_id == "abc123"
        assert resp.block_content == "Some content"

    def test_resolve_response_defaults_none(self):
        """ResolveResponse fragment fields default to None."""
        from pyrite.server.schemas import ResolveResponse

        resp = ResolveResponse(resolved=False)
        assert resp.heading is None
        assert resp.block_id is None
        assert resp.block_content is None


class TestBlocksEndpointFilter:
    """Test blocks endpoint block_id filter parameter."""

    def test_blocks_endpoint_accepts_block_id_param(self):
        """Verify the blocks endpoint source code accepts block_id parameter."""
        import ast
        from pathlib import Path

        blocks_path = Path(__file__).parent.parent / "pyrite" / "server" / "endpoints" / "blocks.py"
        source = blocks_path.read_text()
        tree = ast.parse(source)

        # Find the get_entry_blocks function
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_entry_blocks":
                param_names = [arg.arg for arg in node.args.args]
                assert "block_id" in param_names, f"block_id not in params: {param_names}"
                return

        pytest.fail("get_entry_blocks function not found in blocks.py")


class TestTransclusionRegex:
    """Test transclusion regex: ![[entry#heading]] and ![[entry^block-id]]."""

    def test_transclusion_regex_heading(self):
        """![[entry#heading]] matches."""
        from pyrite.storage.index import _TRANSCLUSION_RE

        m = _TRANSCLUSION_RE.search("embed ![[my-entry#introduction]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(3) == "introduction"
        assert m.group(4) is None

    def test_transclusion_regex_block_id(self):
        """![[entry^block-id]] matches."""
        from pyrite.storage.index import _TRANSCLUSION_RE

        m = _TRANSCLUSION_RE.search("embed ![[my-entry^abc123]]")
        assert m is not None
        assert m.group(2) == "my-entry"
        assert m.group(3) is None
        assert m.group(4) == "abc123"

    def test_transclusion_not_regular_link(self):
        """![[...]] is distinguished from [[...]]."""
        from pyrite.storage.index import _TRANSCLUSION_RE, _WIKILINK_RE

        text = "see [[link]] and embed ![[transclusion#heading]]"
        wikilinks = list(_WIKILINK_RE.finditer(text))
        transclusions = list(_TRANSCLUSION_RE.finditer(text))
        # Wikilink regex matches both [[link]] AND the [[transclusion...]] inside ![[...]]
        # But transclusion regex only matches ![[...]]
        assert len(transclusions) == 1
        assert transclusions[0].group(2) == "transclusion"

    def test_index_transclusion_as_link(self):
        """Transclusion stored with relation='transclusion' in index links."""
        from pyrite.storage.index import _TRANSCLUSION_RE

        body = "Embed this: ![[other-entry#summary]]"
        links = []
        for match in _TRANSCLUSION_RE.finditer(body):
            target = match.group(2).strip()
            heading = match.group(3)
            block_id = match.group(4)
            note = ""
            if heading:
                note = f"#{heading}"
            elif block_id:
                note = f"^{block_id}"
            links.append({"target": target, "relation": "transclusion", "note": note})
        assert len(links) == 1
        assert links[0]["target"] == "other-entry"
        assert links[0]["relation"] == "transclusion"
        assert links[0]["note"] == "#summary"
