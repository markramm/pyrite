"""
Synthetic corpus generator for backend benchmarks.

Produces deterministic entries with realistic field distributions
so benchmarks are reproducible across runs.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta

# Deterministic topics for title/body generation
_TOPICS = [
    "quantum computing", "machine learning", "distributed systems",
    "graph databases", "neural networks", "cryptography",
    "compiler design", "operating systems", "network protocols",
    "signal processing", "robotics", "natural language processing",
    "computer vision", "game theory", "information retrieval",
    "bioinformatics", "climate modeling", "astrophysics",
    "materials science", "protein folding", "genomics",
    "economics", "philosophy", "linguistics", "cognitive science",
]

_ENTRY_TYPES = ["note", "event", "article", "reference", "log"]

_TAG_POOL = [
    "science", "engineering", "math", "physics", "biology",
    "history", "design", "research", "review", "tutorial",
    "architecture", "devops", "security", "performance", "testing",
    "python", "rust", "typescript", "database", "api",
]

_BODY_FRAGMENTS = [
    "Recent advances in {topic} have shown promising results.",
    "A comprehensive review of {topic} literature reveals key patterns.",
    "This entry documents our investigation into {topic}.",
    "The intersection of {topic} and practical applications.",
    "Notes from the conference session on {topic}.",
    "Key findings related to {topic} and emerging trends.",
    "An overview of current approaches to {topic}.",
    "Detailed analysis of {topic} with benchmarks and metrics.",
]


def _deterministic_hash(seed: str) -> str:
    return hashlib.md5(seed.encode()).hexdigest()[:8]


def generate_entries(
    n: int,
    kb_name: str = "bench",
    seed: int = 42,
) -> list[dict]:
    """Generate n deterministic entries for benchmarking."""
    rng = random.Random(seed)
    base_date = date(2023, 1, 1)
    entries = []

    for i in range(n):
        topic = rng.choice(_TOPICS)
        entry_type = rng.choice(_ENTRY_TYPES)
        num_tags = rng.randint(1, 4)
        tags = rng.sample(_TAG_POOL, num_tags)
        body_template = rng.choice(_BODY_FRAGMENTS)
        body = body_template.format(topic=topic)
        # Add more body text for realistic sizes
        extra_sentences = rng.randint(2, 8)
        for _ in range(extra_sentences):
            extra_topic = rng.choice(_TOPICS)
            body += f" Further exploration of {extra_topic} is warranted."

        entry_date = base_date + timedelta(days=rng.randint(0, 730))
        importance = rng.randint(1, 5)

        entries.append({
            "id": f"bench-{i:05d}",
            "kb_name": kb_name,
            "entry_type": entry_type,
            "title": f"{topic.title()} — Entry {i}",
            "body": body,
            "summary": f"Summary of {topic} (entry {i})",
            "tags": tags,
            "date": entry_date.isoformat(),
            "importance": importance,
            "source_path": f"entries/{topic.replace(' ', '-')}/{i}.md",
            "metadata": {},
        })

    return entries


def generate_queries(n: int = 50, seed: int = 99) -> list[dict]:
    """Generate query/relevant-entry-ids pairs for search quality evaluation.

    Each query is a topic keyword. Relevant entries are those whose title
    contains that topic (case-insensitive).
    """
    rng = random.Random(seed)
    queries = []
    topics_sampled = rng.sample(_TOPICS, min(n, len(_TOPICS)))
    # Repeat if we need more
    while len(topics_sampled) < n:
        topics_sampled.extend(rng.sample(_TOPICS, min(n - len(topics_sampled), len(_TOPICS))))

    for topic in topics_sampled[:n]:
        queries.append({
            "query": topic,
            "topic": topic,
        })
    return queries


def find_relevant(entries: list[dict], query: dict) -> set[str]:
    """Return entry IDs relevant to a query (title contains the topic)."""
    topic = query["topic"].lower()
    return {e["id"] for e in entries if topic in e["title"].lower()}
