"""Tests for relevance-aware search snippets."""

import pytest

from pyrite.services.embedding_service import _best_passage, _generate_snippet


class TestBestPassage:
    def test_finds_most_relevant_paragraph(self):
        body = """
Introduction to the document about various topics.

Trust enables decentralized coordination without hierarchy.
Organizations that build trust can operate with less oversight.

Cooking pasta requires boiling water and adding salt.
Always use good quality olive oil for best results.

Systems thinking reveals feedback loops that amplify behavior.
        """.strip()
        result = _best_passage(body, "trust coordination hierarchy")
        assert "trust" in result.lower() or "coordination" in result.lower()
        assert "pasta" not in result.lower()

    def test_returns_empty_for_no_match(self):
        body = "Nothing relevant here at all."
        result = _best_passage(body, "quantum mechanics entanglement")
        assert result == ""

    def test_returns_empty_for_empty_body(self):
        result = _best_passage("", "trust")
        assert result == ""

    def test_returns_empty_for_short_query(self):
        result = _best_passage("Some body text here.", "a b")
        assert result == ""

    def test_respects_max_length(self):
        body = "Trust enables coordination. " * 50  # Very long paragraph
        result = _best_passage(body, "trust coordination", max_len=100)
        assert len(result) <= 103  # 100 + "..."

    def test_strips_markdown_formatting(self):
        body = """
## Trust and Coordination

**Trust** enables *decentralized* coordination without hierarchy.
"""
        result = _best_passage(body, "trust coordination")
        assert "**" not in result
        assert "##" not in result


class TestGenerateSnippetWithQuery:
    def test_prefers_relevant_passage_over_summary(self):
        entry = {
            "summary": "A general entry about organizational topics.",
            "body": """
Introduction paragraph about the entry.

Trust as a coordination mechanism enables teams to work without
rigid hierarchical oversight. This is the key insight.

Other unrelated content about cooking recipes and gardening tips.
""",
        }
        result = _generate_snippet(entry, query="trust coordination mechanism")
        assert "trust" in result.lower()

    def test_falls_back_to_summary_without_query(self):
        entry = {
            "summary": "A general entry about organizations.",
            "body": "Some body text about trust and coordination.",
        }
        result = _generate_snippet(entry)
        assert result == "A general entry about organizations."

    def test_falls_back_to_summary_when_no_passage_matches(self):
        entry = {
            "summary": "A general entry about organizations.",
            "body": "Some body text with no relevant content.",
        }
        result = _generate_snippet(entry, query="quantum physics")
        assert result == "A general entry about organizations."
