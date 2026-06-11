---
id: cross-kb-wikilink-rewrite-redirect-stub-move-subdir-change-for-entry-rename-r1700-follow-ups
title: Cross-KB wikilink rewrite + redirect-stub + move (subdir-change) for entry rename (r1700 follow-ups)
type: backlog_item
tags:
- cli
- wikilinks
- refactor
- external-links
- kb-hygiene
importance: 5
status: proposed
priority: medium
rank: 0
---

Follow-up from r1700 rename-move-support, which landed the same-KB slice: file rename + frontmatter id rewrite + same-KB wikilink rewrite + dry-run, exposed via 'pyrite rename <old> <new> -k <kb>' and KBService.rename_entry / KBRepository.rename. Tests pin the contract in tests/test_repository_rename.py (10 cases).

Remaining ticket asks for this fire to cover:

1. **Cross-KB wikilink rewrite.** Today's same-KB slice only rewrites links in the renaming KB. The ticket calls out cross-KB wikilinks ('rewrite all [[old-id]] wikilinks across every KB in the pyrite index'). Implementation: iterate every KBConfig in config.knowledge_bases and run the rewrite. Add a flag --cross-kb that defaults to True (the point of the feature) but is bypassable.

2. **Redirect-stub creation.** Ticket spec: when --redirect (default true), leave a stub at the old path with frontmatter:
     id: <old-id>
     title: Redirected: see [[new-id]]
     type: redirect
     status: redirect
     redirect_to: <new-id>
     redirect_reason: Renamed YYYY-MM-DD - <reason>
   Needs: (a) RedirectEntry type in core (or as a generic type with declared schema), (b) flag --redirect/--no-redirect on rename, (c) optional --reason flag for the redirect_reason metadata, (d) get/search resolution behavior: a redirect entry should optionally auto-follow to the target, or be visibly marked as a redirect in the UI.

3. **pyrite move (subdir-change variant).** 'pyrite entry move <kb> <entry-id> <new-subdir>': handles type/subdir changes. Re-runs KB-schema validation on the move target to ensure the entry-type matches the new subdir. Currently KBRepository.rename keeps the subdir; move would change it explicitly.

4. **REST + MCP plumbing.** Surface rename as POST /api/kb/<name>/entries/<id>/rename and as a write-tier MCP tool. Required for the web UI 'Rename' button.

5. **Regression tests called out in the ticket.** (a) rename an entry wikilinked from 5+ other entries across 2+ KBs and verify all links resolve to the new ID. (b) external URL to old slug continues to resolve via redirect stub.

Acceptance per cite:
  - rename rewrites wikilinks across every configured KB - depends on cross-kb flag
  - --redirect creates an indexed stub at the old path
  - --dry-run plan shows cross-KB stats too
  - move handles subdir + revalidation
  - REST + MCP endpoints
  - cross-KB + redirect regression tests

Effort: M. The cross-KB rewrite is the highest leverage piece; redirect stub is the public-link preservation piece; move is least urgent. Worth splitting into 3 separate fires if it eats more than one window.
