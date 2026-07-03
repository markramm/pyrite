"""
LLM Usage Service — per-user LLM cost/token tracking and quota enforcement.

llm-usage-tracking-and-quotas: pyrite/services/llm_service.py makes
provider calls without recording token usage, cost, or which user
initiated the request. This service is the recording + quota-check
layer (llm_usage table, migration v23); LLMService/endpoint callers
wire into it separately by calling record_usage() after a completion.
"""

from __future__ import annotations

from typing import Any

from ..storage.database import PyriteDB

# Price per million tokens, USD. Versioned here (not computed) so a
# price change is a one-line diff with a clear blame trail. Unknown
# models cost $0 rather than raising -- cost estimation is best-effort,
# not a hard dependency for usage recording to succeed.
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    "claude-opus-4-8": {"input": 15.0, "output": 75.0},
    "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a completion. Unknown models cost 0."""
    prices = PRICING.get(model)
    if not prices:
        return 0.0
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


class LLMUsageService:
    """Records LLM usage rows and checks per-user quotas."""

    def __init__(self, db: PyriteDB):
        self.db = db

    def record_usage(
        self,
        user_id: int | None,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        kind: str = "chat",
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> None:
        """Record one LLM call's token usage and estimated cost."""
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        self.db.execute_write_sql(
            """
            INSERT INTO llm_usage
                (user_id, provider, model, kind, input_tokens, output_tokens,
                 cache_read_tokens, cache_creation_tokens, estimated_cost_usd)
            VALUES
                (:user_id, :provider, :model, :kind, :input_tokens, :output_tokens,
                 :cache_read_tokens, :cache_creation_tokens, :estimated_cost_usd)
            """,
            {
                "user_id": user_id,
                "provider": provider,
                "model": model,
                "kind": kind,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "estimated_cost_usd": cost,
            },
        )

    def get_usage(self, user_id: int) -> dict[str, Any]:
        """Total usage for one user across all time."""
        rows = self.db.execute_sql(
            """
            SELECT
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                COUNT(*) AS request_count
            FROM llm_usage WHERE user_id = :user_id
            """,
            {"user_id": user_id},
        )
        return dict(rows[0])

    def get_all_usage(self) -> list[dict[str, Any]]:
        """Per-user usage totals across all users (admin view)."""
        rows = self.db.execute_sql(
            """
            SELECT
                user_id,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                COUNT(*) AS request_count
            FROM llm_usage
            GROUP BY user_id
            ORDER BY estimated_cost_usd DESC
            """
        )
        return [dict(r) for r in rows]

    def check_quota(self, user_id: int, kind: str, daily_limit: int | None) -> tuple[bool, str]:
        """Check whether user_id is within their daily request-count
        quota for the given kind. daily_limit=None means unlimited.

        Returns (allowed, message).
        """
        if daily_limit is None:
            return True, "No quota configured — unlimited"

        rows = self.db.execute_sql(
            """
            SELECT COUNT(*) AS request_count
            FROM llm_usage
            WHERE user_id = :user_id AND kind = :kind
              AND created_at >= datetime('now', '-1 day')
            """,
            {"user_id": user_id, "kind": kind},
        )
        count = rows[0]["request_count"]
        if count >= daily_limit:
            return False, f"Daily quota reached: {count}/{daily_limit} '{kind}' requests today"
        return True, "OK"
