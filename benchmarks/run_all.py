#!/usr/bin/env python3
"""
Backend benchmark suite for SearchBackend implementations.

Measures:
- Index build time (full reindex at various corpus sizes)
- Query latency (p50/p95 for keyword, semantic, hybrid)
- Search quality (Recall@10, MRR, nDCG@10) using synthetic queries
- Disk footprint

Usage:
    python benchmarks/run_all.py [--sizes 500,1000] [--queries 50] [--repeats 20]
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import tempfile
import time
from pathlib import Path

from benchmarks.corpus import find_relevant, generate_entries, generate_queries


def _make_sqlite_backend(tmpdir: Path):
    from pyrite.storage.database import PyriteDB

    db = PyriteDB(tmpdir / "bench.db")
    db.register_kb("bench", "generic", "/tmp/bench", "Benchmark KB")
    return db.backend, db


def _make_lancedb_backend(tmpdir: Path):
    from pyrite.storage.backends.lancedb_backend import LanceDBBackend

    return LanceDBBackend(tmpdir / "lance_data"), None


def _make_postgres_backend(tmpdir: Path):
    """Create a PostgresBackend for benchmarks.

    Requires PYRITE_BENCH_PG_URL env var (e.g. postgresql://localhost/pyrite_bench).
    The tmpdir is unused — Postgres stores data server-side.
    """
    import os

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from pyrite.storage.backends.postgres_backend import PostgresBackend, ensure_schema
    from pyrite.storage.models import KB, Base

    url = os.environ.get("PYRITE_BENCH_PG_URL")
    if not url:
        raise RuntimeError("PYRITE_BENCH_PG_URL not set")

    engine = create_engine(url)
    # Reset schema for clean benchmark
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    ensure_schema(engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    # Register benchmark KB
    session.add(KB(name="bench", kb_type="generic", path="/tmp/bench", description="Benchmark KB"))
    session.commit()

    return PostgresBackend(session, engine), engine


def _generate_fake_embedding(entry_id: str, dim: int = 384) -> list[float]:
    """Deterministic pseudo-embedding from entry ID hash."""
    import hashlib
    h = hashlib.sha256(entry_id.encode()).digest()
    # Use hash bytes to seed values
    values = []
    for i in range(dim):
        byte_idx = i % len(h)
        values.append((h[byte_idx] + i) / 256.0 - 0.5)
    # Normalize
    norm = math.sqrt(sum(v * v for v in values))
    if norm > 0:
        values = [v / norm for v in values]
    return values


# --------------- Quality Metrics ---------------

def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 10) -> float:
    if not relevant_ids:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    return len(set(retrieved_k) & relevant_ids) / len(relevant_ids)


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for i, rid in enumerate(retrieved_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 10) -> float:
    def dcg(ids):
        return sum(
            (1.0 if rid in relevant_ids else 0.0) / math.log2(i + 2)
            for i, rid in enumerate(ids[:k])
        )
    actual = dcg(retrieved_ids)
    # Ideal: all relevant first
    ideal_ids = [rid for rid in retrieved_ids if rid in relevant_ids]
    ideal_ids.extend([rid for rid in retrieved_ids if rid not in relevant_ids])
    ideal = dcg(ideal_ids)
    if ideal == 0:
        return 0.0
    return actual / ideal


# --------------- Benchmark Functions ---------------

def bench_index(backend_factory, entries: list[dict], label: str) -> dict:
    """Measure time to index all entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend, db = backend_factory(Path(tmpdir))
        start = time.perf_counter()
        for entry in entries:
            backend.upsert_entry(entry)
        elapsed = time.perf_counter() - start
        if db:
            db.close()
    return {
        "backend": label,
        "entries": len(entries),
        "index_time_s": round(elapsed, 3),
        "entries_per_sec": round(len(entries) / elapsed, 1),
    }


def bench_query_latency(
    backend_factory,
    entries: list[dict],
    queries: list[dict],
    repeats: int,
    label: str,
) -> dict:
    """Measure keyword search latency (p50, p95)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend, db = backend_factory(Path(tmpdir))
        for entry in entries:
            backend.upsert_entry(entry)

        # Keyword search latency
        keyword_times = []
        for _ in range(repeats):
            for q in queries:
                start = time.perf_counter()
                backend.search(q["query"], kb_name="bench", limit=10)
                keyword_times.append(time.perf_counter() - start)

        # Semantic search latency (with fake embeddings)
        # First, upsert embeddings for a subset
        for entry in entries[:100]:
            emb = _generate_fake_embedding(entry["id"])
            backend.upsert_embedding(entry["id"], "bench", emb)

        semantic_times = []
        for _ in range(repeats):
            for q in queries[:10]:  # Fewer semantic queries (expensive)
                emb = _generate_fake_embedding(q["query"])
                start = time.perf_counter()
                backend.search_semantic(emb, kb_name="bench", limit=10)
                semantic_times.append(time.perf_counter() - start)

        if db:
            db.close()

    keyword_times.sort()
    semantic_times.sort()

    def percentile(times, p):
        if not times:
            return 0
        idx = int(len(times) * p / 100)
        return round(times[min(idx, len(times) - 1)] * 1000, 2)  # ms

    return {
        "backend": label,
        "entries": len(entries),
        "keyword_p50_ms": percentile(keyword_times, 50),
        "keyword_p95_ms": percentile(keyword_times, 95),
        "semantic_p50_ms": percentile(semantic_times, 50),
        "semantic_p95_ms": percentile(semantic_times, 95),
    }


def bench_search_quality(
    backend_factory,
    entries: list[dict],
    queries: list[dict],
    label: str,
) -> dict:
    """Measure search quality: Recall@10, MRR, nDCG@10."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend, db = backend_factory(Path(tmpdir))
        for entry in entries:
            backend.upsert_entry(entry)

        recalls = []
        mrrs = []
        ndcgs = []

        for q in queries:
            relevant = find_relevant(entries, q)
            if not relevant:
                continue
            results = backend.search(q["query"], kb_name="bench", limit=10)
            retrieved_ids = [r.get("id", r.get("entry_id", "")) for r in results]
            recalls.append(recall_at_k(retrieved_ids, relevant))
            mrrs.append(mrr(retrieved_ids, relevant))
            ndcgs.append(ndcg_at_k(retrieved_ids, relevant))

        if db:
            db.close()

    return {
        "backend": label,
        "queries_evaluated": len(recalls),
        "recall_at_10": round(statistics.mean(recalls), 3) if recalls else 0,
        "mrr": round(statistics.mean(mrrs), 3) if mrrs else 0,
        "ndcg_at_10": round(statistics.mean(ndcgs), 3) if ndcgs else 0,
    }


def bench_disk(backend_factory, entries: list[dict], label: str) -> dict:
    """Measure disk footprint after indexing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        backend, db = backend_factory(tmppath)
        for entry in entries:
            backend.upsert_entry(entry)
        if db:
            db.close()

        # Measure total size of tmpdir
        total = sum(f.stat().st_size for f in tmppath.rglob("*") if f.is_file())

    return {
        "backend": label,
        "entries": len(entries),
        "disk_bytes": total,
        "disk_mb": round(total / (1024 * 1024), 2),
    }


# --------------- Main ---------------

def run_benchmarks(sizes: list[int], n_queries: int, repeats: int, backend_filter: list[str] | None = None) -> dict:
    all_backends = {
        "sqlite": _make_sqlite_backend,
        "lancedb": _make_lancedb_backend,
        "postgres": _make_postgres_backend,
    }
    if backend_filter:
        backends = {k: v for k, v in all_backends.items() if k in backend_filter}
    else:
        backends = all_backends
    queries = generate_queries(n_queries)
    results = {
        "index": [],
        "latency": [],
        "quality": [],
        "disk": [],
    }

    for size in sizes:
        entries = generate_entries(size)
        for label, factory in backends.items():
            print(f"  [{label}] {size} entries: indexing...")
            results["index"].append(bench_index(factory, entries, label))

            print(f"  [{label}] {size} entries: latency ({repeats} repeats)...")
            results["latency"].append(
                bench_query_latency(factory, entries, queries, repeats, label)
            )

            print(f"  [{label}] {size} entries: search quality...")
            results["quality"].append(
                bench_search_quality(factory, entries, queries, label)
            )

            print(f"  [{label}] {size} entries: disk footprint...")
            results["disk"].append(bench_disk(factory, entries, label))

    return results


def format_markdown(results: dict) -> str:
    lines = ["# Backend Benchmark Results\n"]

    lines.append("## Index Build Time\n")
    lines.append("| Backend | Entries | Time (s) | Entries/sec |")
    lines.append("|---------|---------|----------|-------------|")
    for r in results["index"]:
        lines.append(f"| {r['backend']} | {r['entries']} | {r['index_time_s']} | {r['entries_per_sec']} |")

    lines.append("\n## Query Latency\n")
    lines.append("| Backend | Entries | Keyword p50 (ms) | Keyword p95 (ms) | Semantic p50 (ms) | Semantic p95 (ms) |")
    lines.append("|---------|---------|------------------|------------------|-------------------|-------------------|")
    for r in results["latency"]:
        lines.append(f"| {r['backend']} | {r['entries']} | {r['keyword_p50_ms']} | {r['keyword_p95_ms']} | {r['semantic_p50_ms']} | {r['semantic_p95_ms']} |")

    lines.append("\n## Search Quality (Keyword FTS)\n")
    lines.append("| Backend | Queries | Recall@10 | MRR | nDCG@10 |")
    lines.append("|---------|---------|-----------|-----|---------|")
    for r in results["quality"]:
        lines.append(f"| {r['backend']} | {r['queries_evaluated']} | {r['recall_at_10']} | {r['mrr']} | {r['ndcg_at_10']} |")

    lines.append("\n## Disk Footprint\n")
    lines.append("| Backend | Entries | Size (MB) |")
    lines.append("|---------|---------|-----------|")
    for r in results["disk"]:
        lines.append(f"| {r['backend']} | {r['entries']} | {r['disk_mb']} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run backend benchmarks")
    parser.add_argument("--sizes", default="500,1000", help="Comma-separated corpus sizes")
    parser.add_argument("--queries", type=int, default=25, help="Number of test queries")
    parser.add_argument("--repeats", type=int, default=10, help="Latency measurement repeats")
    parser.add_argument("--backends", default=None, help="Comma-separated backends (sqlite,lancedb,postgres)")
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    backend_filter = args.backends.split(",") if args.backends else None

    print("Backend Benchmark Suite")
    print("=" * 40)
    results = run_benchmarks(sizes, args.queries, args.repeats, backend_filter)

    # Print markdown report
    md = format_markdown(results)
    print("\n" + md)

    # Save JSON
    out_path = args.output or "benchmarks/results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nJSON results saved to {out_path}")


if __name__ == "__main__":
    main()
