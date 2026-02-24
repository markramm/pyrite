#!/usr/bin/env python3
"""
pyrite: Full-access Knowledge Base CLI

Complete CLI for pyrite with read, write, and admin operations.
For researcher-owned KBs where you have full control.

For read-only access (safe for untrusted agents), use 'pyrite-read'.

Documentation: https://github.com/markramm/pyrite/blob/main/docs/ARCHITECTURE.md
"""

import argparse
import json
import sqlite3
import sys
from typing import Any

DOCS_URL = "https://github.com/markramm/pyrite/blob/main/docs"
VERSION = "0.2.0"

# Exit codes
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_KB_NOT_FOUND = 3
EXIT_PERMISSION = 4
EXIT_VALIDATION = 5
EXIT_INDEX = 10
EXIT_ERROR = 99


def get_config():
    from .config import load_config

    return load_config()


def get_db(config):
    from .storage.database import PyriteDB

    return PyriteDB(config.settings.index_path)


def get_index_mgr(db, config):
    from .storage.index import IndexManager

    return IndexManager(db, config)


def get_kb_service(config, db):
    from .services.kb_service import KBService

    return KBService(config, db)


class FullAccessCLI:
    """Full-access CLI for researcher-owned KBs."""

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
        result = {"ok": exit_code == EXIT_OK, "code": exit_code}
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
        """Output structured error with docs link."""
        err = {"error": {"code": code, "message": message}}
        if doc_path:
            err["error"]["docs"] = f"{DOCS_URL}/{doc_path}"
        if hint:
            err["error"]["hint"] = hint
        return self.output(err, exit_code)

    # =========================================================================
    # READ COMMANDS
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
                "Search query required",
                hint="pyrite search 'your query'",
                exit_code=EXIT_USAGE,
            )

        if self.svc.count_entries() == 0:
            return self.error(
                "INDEX_EMPTY",
                "Index empty - build it first",
                doc_path="ARCHITECTURE.md#indexing",
                hint="pyrite index build",
                exit_code=EXIT_INDEX,
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
                hint=f"pyrite search '{args.entry_id}'",
                exit_code=EXIT_NOT_FOUND,
            )

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

        return self.output({"count": len(results[: args.limit]), "events": results[: args.limit]})

    def cmd_tags(self, args) -> int:
        """Get tags with counts."""
        self._ensure_svc()
        tags = self.svc.get_tags(kb_name=args.kb, limit=args.limit)
        return self.output({"tags": tags})

    def cmd_backlinks(self, args) -> int:
        """Get backlinks to entry."""
        self._ensure_svc()
        if not args.kb:
            return self.error(
                "MISSING_KB", "KB required for backlinks", hint="--kb <name>", exit_code=EXIT_USAGE
            )
        backlinks = self.svc.get_backlinks(args.entry_id, args.kb)
        return self.output({"entry": args.entry_id, "backlinks": backlinks})

    # =========================================================================
    # WRITE COMMANDS
    # =========================================================================

    def cmd_create(self, args) -> int:
        """Create new entry."""
        self._ensure_svc()

        if args.type == "event" and not args.date:
            return self.error(
                "MISSING_DATE",
                "Events require --date",
                hint="--date YYYY-MM-DD",
                exit_code=EXIT_VALIDATION,
            )

        from .schema import generate_entry_id

        entry_id = generate_entry_id(args.title)

        extra = {}
        if args.date:
            extra["date"] = args.date
        if args.importance:
            extra["importance"] = args.importance
        if args.tags:
            extra["tags"] = args.tags.split(",")
        if getattr(args, "role", None):
            extra["role"] = args.role

        try:
            entry = self.svc.create_entry(
                args.kb, entry_id, args.title, args.type or "note", args.body or "", **extra
            )
            return self.output({"created": True, "id": entry.id, "path": "", "kb": args.kb})
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                return self.error("KB_NOT_FOUND", msg, hint="pyrite list", exit_code=EXIT_KB_NOT_FOUND)
            if "read-only" in msg.lower():
                return self.error("READ_ONLY", msg, exit_code=EXIT_PERMISSION)
            return self.error("CREATE_FAILED", msg, exit_code=EXIT_ERROR)
        except Exception as e:
            return self.error("CREATE_FAILED", str(e), exit_code=EXIT_ERROR)

    def cmd_update(self, args) -> int:
        """Update existing entry."""
        self._ensure_svc()

        updates = {}
        if args.title:
            updates["title"] = args.title
        if args.body:
            updates["body"] = args.body
        if args.importance:
            updates["importance"] = args.importance
        if args.tags:
            updates["tags"] = args.tags.split(",")

        try:
            entry = self.svc.update_entry(args.entry_id, args.kb, **updates)
            return self.output({"updated": True, "id": entry.id, "path": ""})
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                if "kb" in msg.lower():
                    return self.error("KB_NOT_FOUND", msg, exit_code=EXIT_KB_NOT_FOUND)
                return self.error("NOT_FOUND", msg, exit_code=EXIT_NOT_FOUND)
            if "read-only" in msg.lower():
                return self.error("READ_ONLY", msg, exit_code=EXIT_PERMISSION)
            return self.error("UPDATE_FAILED", msg, exit_code=EXIT_ERROR)

    def cmd_delete(self, args) -> int:
        """Delete entry."""
        self._ensure_svc()

        try:
            deleted = self.svc.delete_entry(args.entry_id, args.kb)
            if not deleted:
                return self.error(
                    "NOT_FOUND", f"Entry '{args.entry_id}' not found", exit_code=EXIT_NOT_FOUND
                )
            return self.output({"deleted": True, "id": args.entry_id, "kb": args.kb})
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                if "kb" in msg.lower():
                    return self.error("KB_NOT_FOUND", msg, exit_code=EXIT_KB_NOT_FOUND)
                return self.error("NOT_FOUND", msg, exit_code=EXIT_NOT_FOUND)
            if "read-only" in msg.lower():
                return self.error("READ_ONLY", msg, exit_code=EXIT_PERMISSION)
            return self.error("DELETE_FAILED", msg, exit_code=EXIT_ERROR)

    # =========================================================================
    # ADMIN COMMANDS
    # =========================================================================

    def cmd_index_build(self, args) -> int:
        """Build search index."""
        self._ensure_svc()
        index_mgr = get_index_mgr(self.db, self.config)

        try:
            if args.kb:
                count = index_mgr.index_kb(args.kb)
                return self.output({"action": "build", "kb": args.kb, "indexed": count})
            else:
                results = index_mgr.index_all()
                return self.output(
                    {"action": "build", "kbs": results, "total": sum(results.values())}
                )
        except Exception as e:
            return self.error("INDEX_FAILED", str(e), exit_code=EXIT_INDEX)

    def cmd_index_sync(self, args) -> int:
        """Incremental index sync."""
        self._ensure_svc()
        index_mgr = get_index_mgr(self.db, self.config)

        results = index_mgr.sync_incremental(args.kb)
        return self.output(
            {
                "action": "sync",
                "added": results["added"],
                "updated": results["updated"],
                "removed": results["removed"],
            }
        )

    def cmd_index_stats(self, args) -> int:
        """Index statistics."""
        self._ensure_svc()
        stats = get_index_mgr(self.db, self.config).get_index_stats()
        return self.output(stats)

    def cmd_index_health(self, args) -> int:
        """Check index health."""
        self._ensure_svc()
        health = get_index_mgr(self.db, self.config).check_health()
        is_healthy = not (
            health["missing_files"] or health["unindexed_files"] or health["stale_entries"]
        )
        return self.output(
            {
                "healthy": is_healthy,
                "missing": len(health["missing_files"]),
                "unindexed": len(health["unindexed_files"]),
                "stale": len(health["stale_entries"]),
                "details": health if args.verbose else None,
            }
        )


def main():
    parser = argparse.ArgumentParser(
        prog="pyrite",
        description="pyrite KB CLI (full access)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Read Commands:
  list                    List all knowledge bases
  search QUERY            Full-text search (FTS5 syntax)
  get ID                  Get entry by ID
  timeline                Get timeline events
  tags                    Get tags with counts
  actors                  Get actors with counts
  backlinks ID            Get entries linking to ID

Write Commands:
  create                  Create new entry
  update ID               Update existing entry
  delete ID               Delete entry

Admin Commands:
  index build             Build/rebuild search index
  index sync              Incremental index sync
  index stats             Index statistics
  index health            Check index health

Examples:
  pyrite list
  pyrite search "immigration policy" --kb=timeline
  pyrite get miller-stephen --with-links
  pyrite timeline --from=2025-01-01 --actor=Miller
  pyrite create --kb=timeline --type=event --title="Event" --date=2025-01-20
  pyrite index build

For read-only access (safe for agents): pyrite-read
Docs: {DOCS_URL}/ARCHITECTURE.md
""",
    )
    parser.add_argument("--version", action="version", version=f"pyrite {VERSION}")

    subs = parser.add_subparsers(dest="command", metavar="COMMAND")

    # READ: list
    subs.add_parser("list", help="List KBs")

    # READ: search
    p = subs.add_parser("search", help="Search entries")
    p.add_argument("query", nargs="?")
    p.add_argument("--kb")
    p.add_argument("--type")
    p.add_argument("--tags")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--limit", type=int, default=20)
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

    # READ: get
    p = subs.add_parser("get", help="Get entry")
    p.add_argument("entry_id")
    p.add_argument("--kb")
    p.add_argument("--with-links", action="store_true")

    # READ: timeline
    p = subs.add_parser("timeline", help="Timeline events")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--min-importance", type=int)
    p.add_argument("--actor")
    p.add_argument("--limit", type=int, default=50)

    # READ: tags
    p = subs.add_parser("tags", help="List tags")
    p.add_argument("--kb")
    p.add_argument("--limit", type=int, default=100)

    # READ: backlinks
    p = subs.add_parser("backlinks", help="Get backlinks")
    p.add_argument("entry_id")
    p.add_argument("--kb", required=True)

    # WRITE: create
    p = subs.add_parser("create", help="Create entry")
    p.add_argument("--kb", required=True)
    p.add_argument("--type", required=True, help="event|actor|organization|theme")
    p.add_argument("--title", required=True)
    p.add_argument("--body")
    p.add_argument("--date", help="YYYY-MM-DD (required for events)")
    p.add_argument("--importance", type=int)
    p.add_argument("--tags")
    p.add_argument("--role")

    # WRITE: update
    p = subs.add_parser("update", help="Update entry")
    p.add_argument("entry_id")
    p.add_argument("--kb", required=True)
    p.add_argument("--title")
    p.add_argument("--body")
    p.add_argument("--importance", type=int)
    p.add_argument("--tags")

    # WRITE: delete
    p = subs.add_parser("delete", help="Delete entry")
    p.add_argument("entry_id")
    p.add_argument("--kb", required=True)

    # ADMIN: index
    p = subs.add_parser("index", help="Index management")
    idx_subs = p.add_subparsers(dest="index_cmd")

    pb = idx_subs.add_parser("build", help="Build index")
    pb.add_argument("--kb")

    ps = idx_subs.add_parser("sync", help="Sync index")
    ps.add_argument("--kb")

    idx_subs.add_parser("stats", help="Index stats")

    ph = idx_subs.add_parser("health", help="Index health")
    ph.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(EXIT_USAGE)

    cli = FullAccessCLI()

    handlers = {
        "list": cli.cmd_list,
        "search": cli.cmd_search,
        "get": cli.cmd_get,
        "timeline": cli.cmd_timeline,
        "tags": cli.cmd_tags,
        "backlinks": cli.cmd_backlinks,
        "create": cli.cmd_create,
        "update": cli.cmd_update,
        "delete": cli.cmd_delete,
    }

    if args.command == "index":
        if not args.index_cmd:
            parser.parse_args(["index", "--help"])
        idx_handlers = {
            "build": cli.cmd_index_build,
            "sync": cli.cmd_index_sync,
            "stats": cli.cmd_index_stats,
            "health": cli.cmd_index_health,
        }
        sys.exit(idx_handlers[args.index_cmd](args))
    else:
        sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
