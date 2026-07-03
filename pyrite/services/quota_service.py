"""
Quota Service

Usage tier limit checking for KB and entry creation, and LLM request
quotas (llm-usage-tracking-and-quotas).
"""

from typing import TYPE_CHECKING

from ..config import PyriteConfig

if TYPE_CHECKING:
    from .llm_usage_service import LLMUsageService


class QuotaService:
    """Service for checking usage tier limits."""

    def __init__(self, config: PyriteConfig):
        self.config = config

    def check_kb_creation_allowed(
        self, user_id: int, user_tier: str, current_kb_count: int
    ) -> tuple[bool, str]:
        """Check if user is allowed to create another KB based on tier limits.

        Returns:
            (allowed, message) — allowed is True if within limits, message explains why not.
        """
        tiers = self.config.settings.auth.usage_tiers
        if not tiers:
            return True, "No usage tiers configured — unlimited"

        tier_config = tiers.get(user_tier)
        if not tier_config:
            return True, f"Tier '{user_tier}' not found — no limits enforced"

        if current_kb_count >= tier_config.max_personal_kbs:
            return False, (
                f"KB creation limit reached: {current_kb_count}/{tier_config.max_personal_kbs} "
                f"for tier '{user_tier}'"
            )
        return True, "OK"

    def check_entry_creation_allowed(
        self, kb_name: str, user_tier: str, current_entry_count: int
    ) -> tuple[bool, str]:
        """Check if adding another entry is within tier limits.

        Returns:
            (allowed, message) — allowed is True if within limits.
        """
        tiers = self.config.settings.auth.usage_tiers
        if not tiers:
            return True, "No usage tiers configured — unlimited"

        tier_config = tiers.get(user_tier)
        if not tier_config:
            return True, f"Tier '{user_tier}' not found — no limits enforced"

        if current_entry_count >= tier_config.max_entries_per_kb:
            return False, (
                f"Entry limit reached: {current_entry_count}/{tier_config.max_entries_per_kb} "
                f"for tier '{user_tier}'"
            )
        return True, "OK"

    def check_llm_quota(
        self,
        user_id: int,
        kind: str,
        user_tier: str,
        usage_service: "LLMUsageService",
    ) -> tuple[bool, str]:
        """Check if user is within their tier's daily LLM request quota.

        Delegates the actual counting to LLMUsageService.check_quota,
        which owns the llm_usage table this needs to query. No tiers
        configured, an unknown tier, or a tier that doesn't set
        daily_llm_requests (the default) all mean unlimited -- same
        fail-open-on-config-gap convention as check_kb_creation_allowed
        and check_entry_creation_allowed.

        Returns:
            (allowed, message) — allowed is True if within limits.
        """
        tiers = self.config.settings.auth.usage_tiers
        if not tiers:
            return True, "No usage tiers configured — unlimited"

        tier_config = tiers.get(user_tier)
        if not tier_config:
            return True, f"Tier '{user_tier}' not found — no limits enforced"

        return usage_service.check_quota(
            user_id=user_id, kind=kind, daily_limit=tier_config.daily_llm_requests
        )
