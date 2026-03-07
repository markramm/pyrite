---
id: per-user-fork-directories
title: "Per-User Fork Directories on Server"
type: backlog_item
tags:
- feature
- collaboration
- git
kind: feature
priority: medium
effort: M
status: proposed
links:
- adr-0018
- web-kb-management
---

## Problem

ADR-0018 envisions per-user shallow forks on the server filesystem (`users/alice/forks/acme-corp--knowledge/`) so each user has an isolated working copy. Currently, forks go to GitHub and repos clone into a shared workspace directory — there's no per-user directory isolation on the server side.

## Solution

Implement the org/user directory structure from ADR-0018:

- `orgs/{org}/repos/{repo}/` for upstream repos
- `users/{username}/forks/{org}--{repo}/` for per-user shallow forks
- Lazy fork creation: forks are created on first write, not first read
- Read-only users can read directly from upstream without a fork
- TTL-based cleanup: inactive forks (no commits in 30+ days) garbage-collected and recreated on next access

### Key Changes

- Extend `RepoService` to manage per-user fork directories
- Update `UserService` to track user workspace paths
- Add fork creation on first write (lazy)
- Add GC logic for stale forks

## Prerequisites

- Web KB management (completed)
- GitHub integration (completed)
