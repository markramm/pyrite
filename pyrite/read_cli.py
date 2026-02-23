#!/usr/bin/env python3
"""
crk-read: Read-only Knowledge Base CLI

A read-only CLI for pyrite, safe for untrusted agent workflows.
This tool cannot modify any data - only query and search.

Commands: list, search, get, timeline, tags, actors, backlinks, stats

For write operations, use 'crk-write' (requires elevated permissions).
"""

import argparse
import json
import sqlite3
import sys
from typing import Any

# Documentation base URL
DOCS_URL = "https://github.com/markramm/zettelkasten/blob/main/docs"

# Exit codes
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_KB_NOT_FOUND = 3
EXIT_INDEX_EMPTY = 10
EXIT_ERROR = 99


def get_config():
    from .config import load_config

    return load_config()


def get_db(config):
    from .storage.database import PyriteDB

    return PyriteDB(config.settings.index_path)


def get_kb_service(config, db):
    from .services.kb_service import KBService

    return KBService(config, db)


class ReadOnlyCLI:
    """Read-only CLI - safe for untrusted workflows."""

    def __init__(self):
        self.config = None
        self.db = None
        self.svc = None

    def _ensure_svc(self):
        if not self.config:
            self.config = get_config()
        if not self.db:
            self.db = get_db(self.config)
        if not self.svc:
            self.svc = get_kb_service(self.config, self.db)

    def output(self, data: dict[str, Any], exit_code: int = EXIT_OK) -> int:
        """Output JSON result."""
        result = {
            "ok": exit_code == EXIT_OK,
            "code": exit_code,
        }
        if exit_code == EXIT_OK:
            result["data"] = data
        else:
            result["error"] = data.get("error", {})
        print(json.dumps(result, indent=2, default=str))
        return exit_code

    def error(
        self,
        code: str,
        message: str,
        doc_path: str | None = None,
        hint: str | None = None,
        exit_code: int = EXIT_ERROR,
    ) -> int:
        """Output error with documentation link."""
        err = {
            "error": {
                "code": code,
                "message": message,
            }
        }
        if doc_path:
            err["error"]["docs"] = f"{DOCS_URL}/{doc_path}"
        if hint:
            err["error"]["hint"] = hint
        return self.output(err, exit_code)

    # =========================================================================
    # Read-only commands
    # =========================================================================

    def cmd_list(self, args) -> int:
        """List knowledge bases."""
        self._ensure_svc()

        kbs = self.svc.list_kbs()
        return self.output({"kbs": kbs, "total": len(kbs)})

    def cmd_search(self, args) -> int:
        """Full-text search."""
        self._ensure_svc()

        if not args.query:
            return self.error(
                "MISSING_QUERY",
                "Search query is required",
                doc_path="ARCHITECTURE.md#search",
                hint="Usage: crk-read search 'your query'",
                exit_code=EXIT_USAGE,
            )

        # Check index
        if self.svc.count_entries() == 0:
            return self.error(
                "INDEX_EMPTY",
                "Search index is empty. Build it first.",
                doc_path="ARCHITECTURE.md#indexing",
                hint="Run: crk index build",
                exit_code=EXIT_INDEX_EMPTY,
            )

        try:
            tags = args.tags.split(",") if args.tags else None
            mode = getattr(args, "mode", "keyword") or "keyword"

            from .services.search_service import SearchService

            expand = getattr(args, "expand", False)
            search_svc = SearchService(self.db, settings=self.config.settings)
            results = search_svc.search(
                query=args.query,
                kb_name=args.kb,
                entry_type=args.type,
                tags=tags,
                date_from=args.date_from,
                date_to=args.date_to,
                limit=args.limit,
                mode=mode,
                expand=expand,
            )

            return self.output({"query": args.query, "count": len(results), "results": results})
        except (sqlite3.OperationalError, ValueError) as e:
            return self.error(
                "SEARCH_FAILED",
                str(e),
                hint="Try simpler query or use quotes for phrases",
                exit_code=EXIT_ERROR,
            )

    def cmd_get(self, args) -> int:
        """Get entry by ID."""
        self._ensure_svc()

        result = self.svc.get_entry(args.entry_id, kb_name=args.kb)

        if not result:
            return self.error(
                "NOT_FOUND",
                f"Entry '{args.entry_id}' not found",
                hint=f"Search for it: crk-read search '{args.entry_id}'",
                exit_code=EXIT_NOT_FOUND,
            )

        # get_entry already includes outlinks/backlinks; strip if not requested
        if not args.with_links:
            result.pop("outlinks", None)
            result.pop("backlinks", None)

        return self.output({"entry": result})

    def cmd_timeline(self, args) -> int:
        """Get timeline events."""
        self._ensure_svc()

        results = self.svc.get_timeline(
            date_from=args.date_from, date_to=args.date_to, min_importance=args.min_importance or 1
        )

        if args.actor:
            actor_lower = args.actor.lower()
            results = [
                r for r in results if any(actor_lower in a.lower() for a in (r.get("actors") or []))
            ]

        results = results[: args.limit]

        return self.output(
            {"count": len(results), "from": args.date_from, "to": args.date_to, "events": results}
        )

    def cmd_tags(self, args) -> int:
        """Get tags with counts."""
        self._ensure_svc()

        tags = self.svc.get_tags(kb_name=args.kb, limit=args.limit)
        return self.output({"count": len(tags), "tags": tags})

    def cmd_backlinks(self, args) -> int:
        """Get backlinks to entry."""
        self._ensure_svc()

        if not args.kb:
            return self.error(
                "MISSING_KB",
                "KB name is required for backlinks",
                hint="Add --kb <name>",
                exit_code=EXIT_USAGE,
            )

        backlinks = self.svc.get_backlinks(args.entry_id, args.kb)
        return self.output(
            {"entry": args.entry_id, "kb": args.kb, "count": len(backlinks), "backlinks": backlinks}
        )

    def cmd_stats(self, args) -> int:
        """Get index statistics."""
        self._ensure_svc()

        stats = self.svc.get_index_stats()
        return self.output(stats)


def main():
    parser = argparse.ArgumentParser(
        prog="pyrite-read",
        description="Read-only pyrite KB access (safe for agents)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands (all read-only):
  list                 List all knowledge bases
  search QUERY         Full-text search (FTS5 syntax)
  get ENTRY_ID         Get entry by ID
  timeline             Get timeline events
  tags                 Get all tags with counts
  actors               Get all actors with mention counts
  backlinks ENTRY_ID   Get entries linking to this entry
  stats                Get index statistics

Examples:
  crk-read list
  crk-read search "immigration policy"
  crk-read search --kb=timeline --type=event "Miller"
  crk-read get miller-stephen
  crk-read timeline --from=2025-01-01 --actor=Miller
  crk-read tags --limit=20

Output: JSON with {ok, code, data} or {ok, code, error}
Docs: https://github.com/markramm/zettelkasten/blob/main/docs/ARCHITECTURE.md
""",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # list
    subparsers.add_parser("list", help="List knowledge bases")

    # search
    p = subparsers.add_parser("search", help="Full-text search")
    p.add_argument("query", nargs="?", help="Search query")
    p.add_argument("--kb", metavar="NAME", help="Limit to KB")
    p.add_argument("--type", metavar="TYPE", help="Entry type filter")
    p.add_argument("--tags", metavar="T1,T2", help="Tag filter (comma-sep)")
    p.add_argument("--from", dest="date_from", metavar="DATE", help="Start date")
    p.add_argument("--to", dest="date_to", metavar="DATE", help="End date")
    p.add_argument("--limit", type=int, default=20, metavar="N", help="Max results")
    p.add_argument(
        "--mode",
        choices=["keyword", "semantic", "hybrid"],
        default="keyword",
        help="Search mode (keyword, semantic, hybrid)",
    )
    p.add_argument(
        "--expand",
        "-x",
        action="store_true",
        default=False,
        help="Use AI query expansion for additional search terms",
    )

    # get
    p = subparsers.add_parser("get", help="Get entry by ID")
    p.add_argument("entry_id", help="Entry ID")
    p.add_argument("--kb", metavar="NAME", help="KB name (optional)")
    p.add_argument("--with-links", action="store_true", help="Include links")

    # timeline
    p = subparsers.add_parser("timeline", help="Get timeline events")
    p.add_argument("--from", dest="date_from", metavar="DATE", help="Start date")
    p.add_argument("--to", dest="date_to", metavar="DATE", help="End date")
    p.add_argument("--min-importance", type=int, metavar="N", help="Min importance 1-10")
    p.add_argument("--actor", metavar="NAME", help="Filter by actor")
    p.add_argument("--limit", type=int, default=50, metavar="N", help="Max results")

    # tags
    p = subparsers.add_parser("tags", help="Get tags with counts")
    p.add_argument("--kb", metavar="NAME", help="Filter to KB")
    p.add_argument("--limit", type=int, default=100, metavar="N", help="Max tags")

    # backlinks
    p = subparsers.add_parser("backlinks", help="Get backlinks to entry")
    p.add_argument("entry_id", help="Entry ID")
    p.add_argument("--kb", required=True, metavar="NAME", help="KB name")

    # stats
    subparsers.add_parser("stats", help="Get index statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(EXIT_USAGE)

    cli = ReadOnlyCLI()
    handlers = {
        "list": cli.cmd_list,
        "search": cli.cmd_search,
        "get": cli.cmd_get,
        "timeline": cli.cmd_timeline,
        "tags": cli.cmd_tags,
        "backlinks": cli.cmd_backlinks,
        "stats": cli.cmd_stats,
    }

    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
