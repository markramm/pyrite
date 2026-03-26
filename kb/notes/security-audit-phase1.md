---
id: security-audit-phase1
title: "Security audit Phase 1: Static analysis of journalist threat model gaps"
type: backlog_item
tags: [security, audit, journalism]
kind: feature
status: done
priority: high
effort: S
---

## Problem

The hosting-security-hardening epic defines 8 requirement areas (REQ-1 through REQ-8) but no work has started. Before implementing fixes, we need to understand the current gap.

## Scope

Run a static analysis audit against the codebase:

1. **REQ-1: No IP logging** — grep for IP address handling, request.client.host usage, access logs
2. **REQ-2: Encrypted at rest** — check if SQLite DB and site-cache are on encrypted volumes, or if encryption is configurable
3. **REQ-3: No plaintext credentials** — grep for hardcoded secrets, API keys, tokens in source
4. **REQ-4: Metadata minimization** — check what metadata is stored per-request (timestamps, user agents, etc.)
5. **REQ-5: Warrant canary support** — check if there's a mechanism for canary pages
6. **REQ-6: Audit trail integrity** — check if git history can be tampered with by admin users

## Output

A report listing each REQ with:
- Current status (pass/fail/partial)
- Specific files/lines with issues
- Recommended fixes with effort estimates
