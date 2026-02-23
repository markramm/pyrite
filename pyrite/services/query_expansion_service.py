"""
Query Expansion Service for AI-Powered Search Enhancement

Uses LLM APIs (Anthropic or OpenAI) to generate additional search terms
for a given query, improving recall in full-text search.

Gracefully degrades: stub/none providers return empty list, missing SDKs
return empty list, API errors return empty list.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Maximum expansion terms and term length
MAX_TERMS = 10
MAX_TERM_LENGTH = 50

EXPANSION_PROMPT = """Given the search query below, generate up to {max_terms} additional search terms \
that would help find relevant results. Return ONLY the terms, one per line, no numbering or bullets. \
Each term should be under {max_len} characters. Focus on synonyms, related concepts, and alternative \
phrasings. Do not repeat the original query.

Query: {query}"""


def is_available(provider: str) -> bool:
    """Check if the SDK for the given provider is installed."""
    if provider in ("stub", "none", "local", ""):
        return True
    if provider == "anthropic":
        try:
            import anthropic  # noqa: F401

            return True
        except ImportError:
            return False
    if provider == "openai":
        try:
            import openai  # noqa: F401

            return True
        except ImportError:
            return False
    return False


class QueryExpansionService:
    """
    Service for AI-powered query expansion.

    Generates additional search terms via LLM to improve search recall.
    Supports Anthropic and OpenAI providers, with graceful fallback
    for stub/none providers or when SDKs are unavailable.
    """

    def __init__(
        self,
        provider: str = "stub",
        model: str = "",
        api_key: str = "",
        api_base: str = "",
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-load the LLM client."""
        if self._client is not None:
            return self._client

        if self.provider == "anthropic":
            import anthropic

            kwargs: dict[str, Any] = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.api_base:
                kwargs["base_url"] = self.api_base
            self._client = anthropic.Anthropic(**kwargs)

        elif self.provider == "openai":
            import openai

            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.api_base:
                kwargs["base_url"] = self.api_base
            self._client = openai.OpenAI(**kwargs)

        return self._client

    def expand(self, query: str) -> list[str]:
        """
        Generate additional search terms for the given query.

        Returns a list of expansion terms (may be empty on error or
        for stub/none providers).
        """
        if not query or not query.strip():
            return []

        if self.provider in ("stub", "none", "local", ""):
            return []

        if not is_available(self.provider):
            logger.debug("Provider %s SDK not available, skipping expansion", self.provider)
            return []

        try:
            return self._call_llm(query.strip())
        except Exception as e:
            logger.warning("Query expansion failed: %s", e)
            return []

    def _call_llm(self, query: str) -> list[str]:
        """Call the LLM and parse expansion terms from the response."""
        prompt = EXPANSION_PROMPT.format(query=query, max_terms=MAX_TERMS, max_len=MAX_TERM_LENGTH)

        client = self._get_client()
        if client is None:
            return []

        if self.provider == "anthropic":
            model = self.model or "claude-haiku-4-5-20251001"
            response = client.messages.create(
                model=model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text

        elif self.provider == "openai":
            model = self.model or "gpt-4o-mini"
            response = client.chat.completions.create(
                model=model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content

        else:
            return []

        return self._parse_terms(text)

    @staticmethod
    def _parse_terms(text: str) -> list[str]:
        """Parse LLM response into a list of clean search terms."""
        terms = []
        for line in text.strip().splitlines():
            term = line.strip().lstrip("•-*0123456789.) ")
            if term and len(term) <= MAX_TERM_LENGTH:
                terms.append(term)
            if len(terms) >= MAX_TERMS:
                break
        return terms
