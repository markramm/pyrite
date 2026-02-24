---
type: component
title: "Collaboration Services"
kind: service
path: "pyrite/services/"
owner: "markr"
dependencies: ["pyrite.config", "pyrite.storage.database", "pyrite.storage.index", "pyrite.github_auth", "pyrite.services.user_service", "httpx"]
tags: [core, collaboration, git]
---

# Collaboration Services

The collaboration layer consists of two services that together enable multi-user, multi-repo knowledge sharing. **GitService** handles low-level git operations via subprocess with no DB or config dependencies. **RepoService** orchestrates GitService with the database, config, and indexer to implement high-level workflows like subscribe, fork, sync, and unsubscribe.

## Key Files

| File | Purpose |
|------|---------|
| `pyrite/services/git_service.py` | Low-level git plumbing: clone, pull, log, diff, remote management, GitHub API fork |
| `pyrite/services/repo_service.py` | High-level workflows: subscribe, fork_and_subscribe, sync, unsubscribe, discover_kbs |

## API / Key Classes

### `GitService`

A stateless class with all `@staticmethod` methods. Token handling is done by injecting credentials into URLs or environment variables.

| Method | Description |
|--------|-------------|
| `clone(remote_url, local_path, branch, depth, token)` | Clone a repo with optional shallow depth and OAuth token injection. Returns `(success, message)` |
| `pull(local_path, token)` | Pull latest changes using `GIT_ASKPASS` env for auth. Returns `(success, message)` |
| `get_remote_url(local_path)` | Get the origin remote URL |
| `get_current_branch(local_path)` | Get HEAD branch name (defaults to "main") |
| `get_head_commit(local_path)` | Get HEAD commit SHA |
| `get_file_log(local_path, file_path, since_commit)` | Git log for a specific file with `--follow`. Returns list of `{hash, author_name, author_email, date, message}` |
| `get_changed_files(local_path, since_commit)` | List changed `.md` files since a commit (or all tracked `.md` files) |
| `is_git_repo(path)` | Check if path is inside a git repo |
| `add_remote(local_path, name, url)` | Add a named git remote |
| `fork_repo(owner, repo, token)` | Fork a repo on GitHub via the REST API (uses `httpx`). Returns `(success, response_dict)` |
| `parse_github_url(url)` | Parse HTTPS or SSH GitHub URLs into `(owner, repo)` tuple |

Internal helpers: `_inject_token` injects OAuth tokens into HTTPS URLs, `_sanitize_output` strips tokens from error messages.

### `RepoService`

Initialized with `PyriteConfig`, `PyriteDB`, and optional `GitService` / `UserService` instances.

| Method | Description |
|--------|-------------|
| `subscribe(remote_url, name, branch)` | Clone a repo (shallow), discover KBs via `kb.yaml`, register in DB, index with git attribution, add to user workspace as read-only. Returns `{success, repo, path, kbs, entries_indexed}` |
| `fork_and_subscribe(remote_url)` | Fork on GitHub, then clone the fork (full depth), set upstream remote, register as contributor role |
| `sync(repo_name)` | Pull changes for one or all repos, detect changed `.md` files since last sync, re-index only affected KBs with attribution. Returns per-repo results |
| `unsubscribe(repo_name, delete_files)` | Remove repo from workspace: unregister KBs, delete DB records, optionally delete local files |
| `list_repos(user_id)` | List repos, optionally filtered by user workspace |
| `get_repo_status(repo_name)` | Detailed status: branch, head, KB count, entry count, contributors |
| `discover_kbs(repo_path)` | Find KBs in a repo via `auto_discover_kbs` or fallback `kb.yaml` parsing |

## Design Notes

- **Subprocess-based git.** GitService deliberately avoids `gitpython` or `pygit2`, using `subprocess.run` with timeouts (120s for clone, 60s for pull, 30s for log/diff) for simplicity and reliability.
- **Token security.** OAuth tokens are injected into URLs only for the subprocess call and stripped from error output via `_sanitize_output`. Pull uses `GIT_ASKPASS` environment variables instead of URL injection.
- **Read-only subscriptions.** When subscribing (as opposed to forking), KBs are marked `read_only = True` and the workspace role is "subscriber". Forking sets the role to "contributor" and clones with full history.
- **Incremental sync.** The `sync` method tracks `last_synced_commit` per repo, uses `git diff --name-only` to find changed `.md` files, and only re-indexes KBs with affected subpaths.
- **KB discovery.** `discover_kbs` delegates to `auto_discover_kbs` (scans for `kb.yaml` files) with a fallback that checks the repo root directly.

## Consumers

- **CLI `pyrite repo` commands** — subscribe, fork, sync, unsubscribe, list, status
- **REST API repo endpoints** — expose collaboration workflows to the web frontend
- **MCP server** — repo management tools

## Related

- [[storage-layer]] — `PyriteDB` stores repo, KB, workspace, and contributor records
- [[plugin-system]] — KB type discovery uses plugin-registered types
- [[rest-api]] — repo endpoints delegate to `RepoService`
