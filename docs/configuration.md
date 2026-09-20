# Configuration

Pyrite reads `~/.pyrite/config.yaml` (or `$PYRITE_CONFIG_DIR/config.yaml`), then
applies `PYRITE_*` environment variables on top. An environment variable always
wins when it is set. Nothing here is required: a fresh install works with no
config file at all.

## Where things live

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_CONFIG_DIR` | `~/.pyrite` | Directory holding `config.yaml`. When unset, a `.pyrite/config.yaml` found in the current directory or any parent is used instead of `~/.pyrite` — a repo-local registry, so a checkout's `kb/` resolves to that checkout. |
| `PYRITE_DATA_DIR` | `~/.pyrite` | Directory for the index (`index.db`) and cloned repos (`repos/`). Set this in containers and point a volume at it. |
| `PYRITE_STATIC_DIR` | `<checkout>/web/dist` | Built web UI to serve at `/`. Needed when the package is installed into site-packages rather than run from a checkout. |
| `PYRITE_BRANDING_DIR` | built-in | Folder of white-label branding assets (see `deploy/branding-examples/`) |

## Server

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_HOST` | `127.0.0.1` | Bind address. Containers need `0.0.0.0`. |
| `PYRITE_PORT` | `8088` | Port |
| `PYRITE_CORS_ORIGINS` | localhost dev ports | Comma-separated allowed origins |
| `PYRITE_API_KEY` | unset | Single admin API key (legacy single-key mode). Prefer `api_keys` in `config.yaml` — hashed keys with a role each. |

`config.yaml`:

```yaml
settings:
  host: 127.0.0.1
  port: 8088
  api_keys:
    - key_hash: "<sha256 of the key>"
      role: read          # read | write | admin
      label: "Reader"
```

## Authentication (multi-user)

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_AUTH_ENABLED` | `false` | Turn on user accounts and per-KB permissions |
| `PYRITE_AUTH_ANONYMOUS_TIER` | unset | What an unauthenticated request may do when auth is enabled (`read`, `write`, `admin`, or `none` for nothing). Unset falls back to the API-key role. |
| `PYRITE_AUTH_ALLOW_REGISTRATION` | `false` | Let people create accounts |
| `PYRITE_GITHUB_CLIENT_ID` / `PYRITE_GITHUB_CLIENT_SECRET` | unset | GitHub OAuth login |
| `PYRITE_ENCRYPTION_KEY` | unset | If set, stored GitHub access tokens are encrypted at rest with it. Set it on any shared instance. |

Per-KB access: each KB in `config.yaml` may carry `default_role: read` (public
to any authenticated user), `write`, or `none` (private: explicit grants only).
Grants are managed over the REST API by an admin
(`GET`/`POST /api/kbs/{name}/permissions`) or in the web UI's KB settings; there
is no CLI command for them yet.

## Search and embeddings

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_SEARCH_MODE` | `keyword` | Default search mode: `keyword`, `semantic`, `hybrid` |
| `PYRITE_AUTO_EMBED` | `true` | Embed entries when they are written. `0`/`false` turns it off: keyword search only, no torch import and no model download on the write path. `pyrite index embed` backfills later. |
| `PYRITE_PREWARM_EMBEDDINGS` | `false` | Load the embedding model at server start instead of on the first write or semantic search |

`config.yaml` also sets `embedding_model` (default `all-MiniLM-L6-v2`, ~90 MB,
downloaded on first use) and `search_backend` (`sqlite` or `postgres`, with
`database_url` for the latter).

## Bounded reads (MCP)

Every MCP read that returns a body is bounded, so one call cannot exceed what
its caller can hold (ADR-0034). Tune these when your clients' context windows
are smaller or larger than the defaults assume; the MCP tool descriptions
report whatever values are in force, so an agent reads the numbers that
actually apply.

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_BODY_CHUNK_DEFAULT` | `8000` | Body characters returned when the caller passed no `body_limit`. 79% of measured bodies arrive whole at this size. |
| `PYRITE_BODY_CHUNK_MAX` | `20000` | Per-body ceiling. A caller's `body_limit` above this is clamped to it, on every read path including `fields`. |
| `PYRITE_BODY_RESPONSE_BUDGET` | `40000` | Total body characters one response may carry across all of its entries (`kb_batch_read`, `kb_search` with `include_body` or `fields`, `kb_list_entries`, `kb_recent`). Bodies fill in request order; entries past the budget return an empty body with `body_truncated` and their true `body_length`. |

All three are read at server start. A value that is not a positive integer, or
a `PYRITE_BODY_CHUNK_DEFAULT` above `PYRITE_BODY_CHUNK_MAX`, stops the server
with a message naming the variable rather than silently falling back — a
deployment that ignores its own tuning is worse than one that will not boot.

Continue a truncated body with `kb_read_body` (offset-based); see
[json-contracts.md](json-contracts.md) for the marker keys.

## AI features

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_AI_PROVIDER` | unset | `openai` or `anthropic` |
| `PYRITE_AI_MODEL` | provider default | Model name |

API keys for providers are the providers' own variables (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`); Pyrite is bring-your-own-key.

## Plugins

| Variable | Default | Meaning |
|---|---|---|
| `PYRITE_STRICT_PLUGINS` | `false` | Fail startup if any installed plugin fails to load, instead of skipping it. Recommended in CI. |

## Seeing the effective configuration

```bash
pyrite-admin config show    # merged config with secrets masked
pyrite kb list              # registered KBs and their paths
curl localhost:8088/health  # server: index path, embedding readiness
```
