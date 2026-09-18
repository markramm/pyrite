---
id: codeql-triage-and-close-the-56-open-code-scanning-alerts-on-dev
title: 'CodeQL: triage and close the 56 open code-scanning alerts on dev'
type: backlog_item
tags:
- security
- codeql
- quality
kind: tech_debt
status: proposed
priority: high
effort: M
---

## Problem

GitHub's default CodeQL setup (languages: actions, javascript/typescript, python; weekly + on push) reports **56 open alerts** on `dev` (2026-09-18 10:05Z). None is triaged; some are certainly noise (a path that is validated by `_validate_entry_id` two frames up still trips `py/path-injection`), some are certainly real (`str(e)` of a subprocess failure returned in an HTTP 500 body), and the page is public. Security-adjacent by definition: **never `good first issue`, always a cold read, Opus for anything that changes a check.**

## Inventory (rule · alert · path:line)

```
error    py/clear-text-logging-sensitive-data       #10   pyrite/server/mcp_routes.py:182
error    py/clear-text-storage-sensitive-data       #9    scripts/scrape_appointee_details.py:627
error    py/command-line-injection                  #41   pyrite/services/git_service.py:102
error    py/command-line-injection                  #42   pyrite/services/git_service.py:522
error    py/full-ssrf                               #33   pyrite/services/clipper.py:188
error    py/path-injection                          #11   pyrite/server/branding_endpoints.py:61
error    py/path-injection                          #12   pyrite/services/branding_service.py:132
error    py/path-injection                          #13   pyrite/services/branding_service.py:139
error    py/path-injection                          #14   pyrite/services/export_service.py:64
error    py/path-injection                          #15   pyrite/services/export_service.py:69
error    py/path-injection                          #16   pyrite/services/export_service.py:83
error    py/path-injection                          #17   pyrite/services/export_service.py:112
error    py/path-injection                          #18   pyrite/services/export_service.py:161
error    py/path-injection                          #19   pyrite/services/kb_registry_service.py:118
error    py/path-injection                          #20   pyrite/server/static.py:132
error    py/path-injection                          #21   pyrite/server/static.py:138
error    py/path-injection                          #22   pyrite/server/static.py:139
error    py/path-injection                          #23   pyrite/server/static.py:239
error    py/path-injection                          #24   pyrite/server/static.py:245
error    py/path-injection                          #25   pyrite/server/static.py:247
error    py/stack-trace-exposure                    #44   pyrite/server/endpoints/admin.py:136
error    py/stack-trace-exposure                    #45   pyrite/server/endpoints/ai_ep.py:376
error    py/stack-trace-exposure                    #46   pyrite/server/endpoints/entries.py:597
error    py/stack-trace-exposure                    #47   pyrite/server/endpoints/git_ops.py:39
error    py/stack-trace-exposure                    #48   pyrite/server/endpoints/git_ops.py:61
error    py/stack-trace-exposure                    #49   pyrite/server/endpoints/git_ops.py:82
error    py/stack-trace-exposure                    #50   pyrite/server/endpoints/kbs.py:182
error    py/stack-trace-exposure                    #51   pyrite/server/endpoints/repos.py:79
error    py/stack-trace-exposure                    #52   pyrite/server/endpoints/repos.py:103
error    py/stack-trace-exposure                    #53   pyrite/server/endpoints/repos.py:224
error    py/stack-trace-exposure                    #54   pyrite/server/endpoints/worktree.py:176
error    py/stack-trace-exposure                    #55   pyrite/server/endpoints/worktree.py:184
error    py/stack-trace-exposure                    #56   pyrite/server/endpoints/worktree.py:303
warning  actions/missing-workflow-permissions       #1    .github/workflows/ci.yml:28
warning  actions/missing-workflow-permissions       #2    .github/workflows/ci.yml:57
warning  actions/missing-workflow-permissions       #3    .github/workflows/ci.yml:78
warning  actions/missing-workflow-permissions       #4    .github/workflows/ci.yml:199
warning  actions/missing-workflow-permissions       #5    .github/workflows/ci.yml:232
warning  actions/missing-workflow-permissions       #6    .github/workflows/ci.yml:271
warning  actions/missing-workflow-permissions       #7    .github/workflows/ci.yml:366
warning  actions/missing-workflow-permissions       #8    .github/workflows/ci.yml:424
warning  py/incomplete-url-substring-sanitization   #34   pyrite/config.py:155
warning  py/incomplete-url-substring-sanitization   #35   pyrite/github_auth.py:363
warning  py/incomplete-url-substring-sanitization   #36   tests/test_git_service.py:50
warning  py/incomplete-url-substring-sanitization   #37   tests/test_llm_service.py:186
warning  py/incomplete-url-substring-sanitization   #38   tests/test_llm_service.py:191
warning  py/incomplete-url-substring-sanitization   #39   tests/test_notebooklm_renderer.py:254
warning  py/incomplete-url-substring-sanitization   #40   pyrite/services/user_service.py:83
warning  py/polynomial-redos                        #43   pyrite/services/search_service.py:98
warning  py/weak-sensitive-data-hashing             #26   pyrite/server/api.py:392
warning  py/weak-sensitive-data-hashing             #27   pyrite/server/api.py:400
warning  py/weak-sensitive-data-hashing             #28   pyrite/server/api.py:401
warning  py/weak-sensitive-data-hashing             #29   tests/e2e/conftest.py:253
warning  py/weak-sensitive-data-hashing             #30   pyrite/server/mcp_routes.py:67
warning  py/weak-sensitive-data-hashing             #31   pyrite/server/mcp_routes.py:110
warning  py/weak-sensitive-data-hashing             #32   pyrite/server/mcp_routes.py:118
```

## What the spike must produce (written into this item as `## Groom`)

For each rule group: (1) true positive or noise, with the reasoning per alert (which sanitizer/validator, if any, sits on the data path — `_validate_entry_id`, `_contained`, the auth tier); (2) for the true positives, the exploit shape against the REST/MCP surface as deployed (which tier can reach it, what it yields); (3) themes a worker can execute — acceptance criteria, footprint, model, cold read (always yes), sequence against the themes in flight (`pyrite/server/endpoints/*`, `git_service.py`, `clipper.py`, `static.py`, `config.py`); (4) for the noise, the CodeQL dismissal reason per alert (`false positive` / `won't fix` / `used in tests`) so the conductor can dismiss them through the API with a comment, not silently. The `actions/missing-workflow-permissions` group (8) is already a separate Sonnet theme (`fix/workflow-permissions`) and is out of the spike's scope.

## Rule groups

- `py/stack-trace-exposure` ×13 (error) — `endpoints/{admin,ai_ep,entries,git_ops,kbs,repos,worktree}.py`: exception text or traceback reaching a response body.
- `py/path-injection` ×15 (error) — `branding_endpoints.py`, `branding_service.py`, `export_service.py`, `kb_registry_service.py`, `server/static.py` (6 in the static file server).
- `py/command-line-injection` ×2 (error) — `git_service.py:102, :522`.
- `py/full-ssrf` ×1 (error) — `clipper.py:188` (the backlog item `web-clipper-response-size-cap-and-dns-rebinding-toctou-defense` already covers part of this).
- `py/clear-text-logging-sensitive-data` ×1 (error) — `mcp_routes.py:182` (a password logged); `py/clear-text-storage-sensitive-data` ×1 — `scripts/scrape_appointee_details.py:627` (a script, not the product).
- `py/weak-sensitive-data-hashing` ×7 (warning) — `server/api.py:392–401`, `mcp_routes.py:67–118`, `tests/e2e/conftest.py:253` — API-key hashing; decide whether sha256 of a high-entropy key is the intended design (then dismiss with the reason) or whether a keyed hash is warranted.
- `py/incomplete-url-substring-sanitization` ×7 (warning) — `config.py:155`, `github_auth.py:363`, `user_service.py:83`, three tests.
- `py/polynomial-redos` ×1 (warning) — `search_service.py:98`.

## Also for the maintainer (kept)

Whether CodeQL should become a required PR check (a repo setting) once the count is at zero-or-dismissed; today it runs but does not gate.
