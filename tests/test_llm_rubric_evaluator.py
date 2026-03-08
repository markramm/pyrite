"""Tests for LLM-assisted rubric evaluation.

Covers prompt construction, response parsing, evaluation flow,
and batching behavior.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from pyrite.services.llm_rubric_evaluator import LLMRubricEvaluator


@pytest.fixture
def mock_llm():
    """Mock LLMService with configurable status and complete."""
    llm = MagicMock()
    llm.status.return_value = {
        "configured": True,
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
    }
    llm.complete = AsyncMock(return_value="[]")
    return llm


@pytest.fixture
def evaluator(mock_llm):
    return LLMRubricEvaluator(mock_llm)


@pytest.fixture
def sample_entry():
    return {
        "id": "test-entry-1",
        "kb_name": "test-kb",
        "entry_type": "note",
        "title": "Test Entry",
        "body": "This is a test entry body with some content.",
        "metadata": json.dumps({"tags": ["test"]}),
    }


SAMPLE_RUBRIC_ITEMS = [
    "Entry body explains the why, not just the what",
    "Confidence level matches evidence strength",
]


# =========================================================================
# Prompt Construction
# =========================================================================


class TestPromptConstruction:
    def test_system_prompt_includes_json_format(self, evaluator):
        prompt = evaluator._build_system_prompt()
        assert "JSON" in prompt
        assert '"pass"' in prompt
        assert '"confidence"' in prompt
        assert '"reasoning"' in prompt

    def test_user_prompt_includes_entry_content(self, evaluator, sample_entry):
        prompt = evaluator._build_user_prompt(sample_entry, SAMPLE_RUBRIC_ITEMS, "")
        assert "Test Entry" in prompt
        assert "test entry body" in prompt
        assert "note" in prompt

    def test_user_prompt_includes_rubric_items(self, evaluator, sample_entry):
        prompt = evaluator._build_user_prompt(sample_entry, SAMPLE_RUBRIC_ITEMS, "")
        for item in SAMPLE_RUBRIC_ITEMS:
            assert item in prompt

    def test_user_prompt_includes_guidelines(self, evaluator, sample_entry):
        guidelines = "Entries should be thorough and well-sourced."
        prompt = evaluator._build_user_prompt(sample_entry, SAMPLE_RUBRIC_ITEMS, guidelines)
        assert guidelines in prompt

    def test_user_prompt_includes_metadata(self, evaluator, sample_entry):
        prompt = evaluator._build_user_prompt(sample_entry, SAMPLE_RUBRIC_ITEMS, "")
        assert "tags" in prompt

    def test_user_prompt_truncates_long_body(self, evaluator, sample_entry):
        sample_entry["body"] = "x" * 10000
        prompt = evaluator._build_user_prompt(sample_entry, SAMPLE_RUBRIC_ITEMS, "")
        assert "[... truncated]" in prompt


# =========================================================================
# Response Parsing
# =========================================================================


class TestResponseParsing:
    def test_valid_json_array(self, evaluator, sample_entry):
        response = json.dumps([
            {
                "item": "Entry body explains the why, not just the what",
                "pass": False,
                "confidence": 0.8,
                "reasoning": "Body only states facts",
            },
            {
                "item": "Confidence level matches evidence strength",
                "pass": True,
                "confidence": 0.9,
                "reasoning": "Matches well",
            },
        ])
        issues = evaluator._parse_response(response, sample_entry, SAMPLE_RUBRIC_ITEMS)
        assert len(issues) == 1
        assert issues[0]["rule"] == "llm_rubric_violation"
        assert issues[0]["rubric_item"] == "Entry body explains the why, not just the what"
        assert issues[0]["confidence"] == 0.8
        assert issues[0]["message"] == "Body only states facts"

    def test_json_in_code_fence(self, evaluator, sample_entry):
        response = '```json\n[{"item": "Entry body explains the why, not just the what", "pass": false, "confidence": 0.7, "reasoning": "No why"}]\n```'
        issues = evaluator._parse_response(response, sample_entry, SAMPLE_RUBRIC_ITEMS)
        assert len(issues) == 1
        assert issues[0]["confidence"] == 0.7

    def test_malformed_json(self, evaluator, sample_entry):
        issues = evaluator._parse_response("not json at all", sample_entry, SAMPLE_RUBRIC_ITEMS)
        assert issues == []

    def test_empty_response(self, evaluator, sample_entry):
        assert evaluator._parse_response("", sample_entry, SAMPLE_RUBRIC_ITEMS) == []
        assert evaluator._parse_response("  ", sample_entry, SAMPLE_RUBRIC_ITEMS) == []

    def test_all_pass_no_issues(self, evaluator, sample_entry):
        response = json.dumps([
            {"item": "Entry body explains the why, not just the what", "pass": True, "confidence": 0.9, "reasoning": "ok"},
        ])
        issues = evaluator._parse_response(response, sample_entry, SAMPLE_RUBRIC_ITEMS)
        assert issues == []

    def test_unknown_item_filtered_out(self, evaluator, sample_entry):
        """Items not in rubric_items list are filtered out."""
        response = json.dumps([
            {"item": "Some unknown rubric item", "pass": False, "confidence": 0.8, "reasoning": "bad"},
        ])
        issues = evaluator._parse_response(response, sample_entry, SAMPLE_RUBRIC_ITEMS)
        assert issues == []


# =========================================================================
# Evaluation Flow
# =========================================================================


class TestEvaluation:
    def test_stub_provider_returns_empty(self, sample_entry):
        """Stub provider (not configured) returns empty list."""
        llm = MagicMock()
        llm.status.return_value = {"configured": False, "provider": "stub", "model": ""}
        ev = LLMRubricEvaluator(llm)
        result = asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        assert result == []
        llm.complete.assert_not_called()

    def test_is_available_reflects_status(self, mock_llm):
        ev = LLMRubricEvaluator(mock_llm)
        assert ev.is_available() is True

        mock_llm.status.return_value = {"configured": False, "provider": "stub", "model": ""}
        assert ev.is_available() is False

    def test_failed_items_produce_issues(self, mock_llm, sample_entry):
        mock_llm.complete = AsyncMock(return_value=json.dumps([
            {"item": "Entry body explains the why, not just the what", "pass": False, "confidence": 0.72, "reasoning": "lacks rationale"},
        ]))
        ev = LLMRubricEvaluator(mock_llm)
        issues = asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        assert len(issues) == 1
        assert issues[0]["rule"] == "llm_rubric_violation"
        assert issues[0]["severity"] == "info"
        assert issues[0]["confidence"] == 0.72
        assert issues[0]["message"] == "lacks rationale"

    def test_evaluator_field_shows_provider_model(self, mock_llm, sample_entry):
        mock_llm.complete = AsyncMock(return_value=json.dumps([
            {"item": "Entry body explains the why, not just the what", "pass": False, "confidence": 0.8, "reasoning": "bad"},
        ]))
        ev = LLMRubricEvaluator(mock_llm)
        issues = asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        assert issues[0]["evaluator"] == "anthropic/claude-sonnet-4-20250514"

    def test_llm_error_returns_empty(self, mock_llm, sample_entry):
        """LLM call failure returns empty list, doesn't crash."""
        mock_llm.complete = AsyncMock(side_effect=RuntimeError("API error"))
        ev = LLMRubricEvaluator(mock_llm)
        issues = asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        assert issues == []


# =========================================================================
# Batching
# =========================================================================


class TestBatching:
    def test_multiple_items_single_call(self, mock_llm, sample_entry):
        """Multiple rubric items result in a single LLM call."""
        mock_llm.complete = AsyncMock(return_value="[]")
        ev = LLMRubricEvaluator(mock_llm)
        asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        assert mock_llm.complete.call_count == 1

    def test_mixed_pass_fail(self, mock_llm, sample_entry):
        """Only failures returned as issues."""
        mock_llm.complete = AsyncMock(return_value=json.dumps([
            {"item": "Entry body explains the why, not just the what", "pass": False, "confidence": 0.8, "reasoning": "bad"},
            {"item": "Confidence level matches evidence strength", "pass": True, "confidence": 0.9, "reasoning": "ok"},
        ]))
        ev = LLMRubricEvaluator(mock_llm)
        issues = asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        assert len(issues) == 1
        assert issues[0]["rubric_item"] == "Entry body explains the why, not just the what"

    def test_empty_rubric_items_no_call(self, mock_llm, sample_entry):
        """No rubric items -> no LLM call."""
        ev = LLMRubricEvaluator(mock_llm)
        issues = asyncio.run(ev.evaluate(sample_entry, []))
        assert issues == []
        mock_llm.complete.assert_not_called()

    def test_body_truncated_in_prompt(self, mock_llm, sample_entry):
        """Long body is truncated in the prompt."""
        sample_entry["body"] = "x" * 10000
        mock_llm.complete = AsyncMock(return_value="[]")
        ev = LLMRubricEvaluator(mock_llm)
        asyncio.run(ev.evaluate(sample_entry, SAMPLE_RUBRIC_ITEMS))
        call_args = mock_llm.complete.call_args
        prompt = call_args[0][0]
        assert "[... truncated]" in prompt
