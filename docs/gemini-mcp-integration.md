# Connecting Gemini CLI to Pyrite MCP

Pyrite exposes an MCP (Model Context Protocol) server that Google's Gemini CLI can use to search, read, and write your knowledge bases.

## Prerequisites

- Pyrite installed (`pip install pyrite` or `pip install pyrite-mcp` for the standalone MCP package)
- At least one knowledge base initialized (`pyrite init`)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed

## Gemini CLI Configuration

Gemini CLI reads MCP server config from `~/.gemini/settings.json`.

### Stdio transport (local)

Add a `pyrite` entry under `mcpServers` in `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp"]
    }
  }
}
```

For read-only access:

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp", "--tier", "read"]
    }
  }
}
```

### HTTP/SSE transport (remote Pyrite instance)

If you're running `pyrite serve --mcp` on a remote server:

```json
{
  "mcpServers": {
    "pyrite": {
      "url": "http://localhost:8088/mcp"
    }
  }
}
```

### Optional settings

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp"],
      "timeout": 30000,
      "trust": true,
      "includeTools": ["kb_search", "kb_get", "kb_list"]
    }
  }
}
```

- `timeout`: Request timeout in milliseconds (default: 600000)
- `trust`: Skip tool confirmation prompts (default: false)
- `includeTools` / `excludeTools`: Allowlist or blocklist specific tools

See the [Gemini CLI MCP docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md) for all supported fields.

## Gemini Code Assist (VS Code)

Gemini Code Assist in VS Code also supports MCP servers. Add the following to your VS Code `settings.json`:

```json
{
  "geminicodeassist.mcpServers": {
    "pyrite": {
      "command": "pyrite",
      "args": ["mcp"]
    }
  }
}
```

See the [Gemini Code Assist MCP docs](https://developers.google.com/gemini-code-assist/docs/use-agentic-chat-pair-programmer) for details.

## Verification

Start Gemini CLI and ask it to use a Pyrite tool:

```
gemini "List all knowledge bases using the pyrite MCP tools"
```

You should see Gemini call `kb_list` and return your knowledge bases.

## Troubleshooting

**"Server failed to start"** -- Verify `pyrite mcp` runs successfully on its own in a terminal. Ensure the `pyrite` command is on your PATH.

**"Command not found"** -- If you installed Pyrite in a virtualenv, use the full path:

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "/path/to/.venv/bin/pyrite",
      "args": ["mcp"]
    }
  }
}
```

Or use the standalone MCP package entry point:

```json
{
  "mcpServers": {
    "pyrite": {
      "command": "pyrite-mcp"
    }
  }
}
```

**Tools not showing up** -- Restart Gemini CLI after editing `settings.json`. The config is read at startup.

**Tool not available** -- Check the tier. The default tier is `write`. Use `--tier admin` if you need index and git operations.
