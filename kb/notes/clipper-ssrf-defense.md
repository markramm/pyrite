---
id: clipper-ssrf-defense
title: "Web clipper SSRF defense: block private IPs, cap response size"
type: backlog_item
tags: [security, ssrf, clipper, hosting]
importance: 5
kind: bug
status: proposed
priority: high
effort: S
rank: 1300
---

## Problem

`pyrite/services/clipper.py` and `pyrite/server/endpoints/clipper.py` fetch
arbitrary user-supplied URLs server-side via `httpx.AsyncClient().get(url)`
with only a scheme check (`http://` / `https://`). There is no host
allowlist or private-IP blocklist.

On the hosted instance (`investigate.transparencycascade.org` per the
publication-strategy epic), this is a server-side request forgery (SSRF)
vector:

- `http://127.0.0.1:8080/` — reach localhost services co-located on the box
- `http://169.254.169.254/latest/meta-data/` — AWS instance metadata endpoint
  (similar paths exist for GCP, Azure, DigitalOcean)
- `http://10.0.0.0/8`, `http://172.16.0.0/12`, `http://192.168.0.0/16` —
  private network ranges that may host internal admin panels
- `http://[::1]/`, `http://[fc00::]/` — IPv6 equivalents

There is also no cap on response body size — a malicious URL serving a
multi-GB stream could OOM the worker.

## Threat model

Pyrite is targeted at journalists and activists. The hosted instance will
have multi-user write access. Any authenticated user can call the clipper
endpoint with any URL. On a standard cloud VM, a metadata-endpoint hit
exposes instance credentials.

## Solution

1. Add a hostname/IP validator before `httpx.get()`:
   - Resolve the URL's host to its IP(s)
   - Reject IPs in: 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
     169.254.0.0/16, 100.64.0.0/10 (CGNAT), 0.0.0.0/8, ::1/128, fc00::/7,
     fe80::/10
   - Reject if *any* resolved IP is private (DNS rebinding defense)
   - Use a single resolver call and pass the resolved IP to httpx via
     `transport` to ensure no TOCTOU between resolution and connection
2. Add a max-response-body cap (default 10 MB, configurable). Stream the
   response and abort if it exceeds the cap.
3. Add a request timeout (default 30s connect + read).
4. Optional: deploy-level allowlist of permitted hostnames for tighter
   lockdown, off by default.

## Acceptance criteria

- Clipping `http://127.0.0.1/` returns 400 with `error_code:
  CLIPPER_BLOCKED_HOST`.
- Clipping a public URL still works end-to-end.
- DNS-rebinding test: a hostname that resolves to a public IP first and a
  private IP on follow-up is rejected.
- Response bodies > configured max are aborted, not buffered to memory.
- Tests for each rejection class (private v4, private v6, link-local,
  metadata endpoint, oversized body).

## Related

- `hosting-security-hardening` epic
- `security-audit-trail` — clipper requests should land in the audit log
  once it exists
