
# Architecture & Design

## Storage
- **Markdown + YAML** is the source of truth.
- **SQLite** mirrors metadata & content for search and link analytics.
- **FTS5** virtual table indexes title/body/summary with triggers for sync.

## Services
- **LLMClient**: pluggable; OpenAI or stub. Used for summarization, probing, refining, and metadata suggestions.
- **CEQRC** workflow: orchestrates note evolution from SEED to PERMANENT.

## Links
Typed semantic ontology with inverses (e.g., `supports` ↔ `is_supported_by`).

## API & UI
- **FastAPI** for REST endpoints.
- **Typer** CLI for power users.
- **Streamlit** for a lightweight UI.

## MCP
- `server/mcp_server.py` exposes example tools using a hypothetical `fastmcp` library.
- If MCP libs are not present, the API/CLI remain usable. See `docs/MCP_INTEGRATION.md`.
