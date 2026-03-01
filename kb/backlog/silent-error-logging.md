---
id: silent-error-logging
title: "Silent Error Logging"
type: backlog_item
tags:
- improvement
- error-handling
- code-hardening
- code-quality
kind: improvement
priority: high
effort: M
status: planned
links:
- roadmap
---

# Silent Error Logging

**Wave 5 of 0.9 Code Hardening.** Replace `except Exception: pass` with `logger.warning()` across ~10 sites. Each site is an independent change.

## Sites

| Site | File | Lines | Issue |
|------|------|-------|-------|
| Plugin registration | `mcp_server.py:100` | Silent plugin load failure |
| Plugin validator execution (3 nested) | `schema.py:1093-1098` | Validation silently incomplete |
| Token expiry parse | `config.py:209` | Expired tokens treated as valid |
| Auth config load | `config.py:543` | Auth silently missing |
| YAML frontmatter parse | `formats/importers/markdown_importer.py:76` | Malformed files yield `{}` |
| Semantic search fallback | `plugins/context.py:76` | Search failure silent |
| Admin plugin info (5 blocks) | `endpoints/admin.py:169-199` | Dashboard data silently dropped |
| Plugin relationship/metadata lookups | `schema.py:419,464` | Empty results on error |

## Approach

- Add `import logging; logger = logging.getLogger(__name__)` where missing
- Replace bare `except: pass` / `except Exception: pass` with `except Exception: logger.warning("...", exc_info=True)`
- Preserve existing fallback behavior (return defaults) — just add visibility
- No behavioral changes, only observability

## Definition of Done

- Zero bare `except: pass` patterns remaining in codebase
- All replaced sites log at WARNING level with context
- All existing tests still pass (no behavioral changes)
