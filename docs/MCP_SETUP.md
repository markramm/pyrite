# MCP Integration Guide for Zettelkasten Assistant

## Overview

The Zettelkasten Assistant provides a comprehensive Model Context Protocol (MCP) server that exposes your knowledge management system to AI assistants like Claude Desktop, enabling intelligent interaction with your note collection.

## Features

- **Atomic Note Creation**: Create well-structured notes with AI-generated summaries
- **Intelligent Search**: Full-text search across titles, bodies, and summaries with FTS5 support
- **CEQRC Workflow**: Run the complete Capture→Explain→Question→Refine→Connect workflow
- **Link Discovery**: Find and create typed relationships between notes
- **Knowledge Retrieval**: Access specific notes with complete metadata and backlinks

## Quick Setup

### 1. Install Dependencies

```bash
# Install main project
pip install -r requirements.txt

# Install MCP server dependencies
pip install -r mcp-requirements.txt
```

### 2. Configure Environment

Ensure your `.env` file contains:

```bash
ZK_NOTES_DIR=./data/notes
ZK_DB_PATH=./data/db/zettelkasten.db
OPENAI_API_KEY=your_openai_key_here
ZK_LLM_PROVIDER=openai
```

### 3. Initialize Data

```bash
mkdir -p data/notes data/db
```

## Claude Desktop Configuration

Add this to your Claude Desktop MCP configuration:

### Windows
Edit: `%APPDATA%\Claude\claude_desktop_config.json`

### macOS
Edit: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Configuration JSON

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "python",
      "args": ["/path/to/your/zettelkasten/mcp_server.py"],
      "env": {
        "ZK_NOTES_DIR": "/path/to/your/data/notes",
        "ZK_DB_PATH": "/path/to/your/data/db/zettelkasten.db",
        "OPENAI_API_KEY": "your_openai_key_here",
        "ZK_LLM_PROVIDER": "openai"
      }
    }
  }
}
```

### Alternative: Using pipx/uvx (Recommended)

If you've packaged the project:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "uvx",
      "args": ["zettelkasten-mcp"],
      "env": {
        "OPENAI_API_KEY": "your_openai_key_here"
      }
    }
  }
}
```

## Available Tools

Once configured, Claude will have access to these tools:

### `zk_create_note`
Create a new atomic note with AI-generated summary
- **title**: The note title
- **body**: Main content
- **tags**: Array of categorization tags
- **generate_summary**: Auto-generate AI summary (default: true)

### `zk_search_notes`
Search your knowledge base with full-text search
- **query**: Search query (supports FTS5 syntax like `NEAR/5`, quotes for phrases)
- **tag**: Optional tag filter
- **limit**: Maximum results (default: 10)

### `zk_get_note`
Retrieve a specific note with complete metadata
- **note_id**: The unique note identifier
- **include_backlinks**: Include notes linking to this one (default: true)

### `zk_run_ceqrc_workflow`
Execute the AI-powered CEQRC workflow on a note
- **note_id**: Target note ID
- **steps**: Workflow steps to run (default: all)

### `zk_suggest_links`
Find potential connections between notes
- **note_id**: Note to find connections for
- **max_suggestions**: Maximum suggestions (default: 5)

### `zk_create_link`
Create typed relationships between notes
- **source_id**: Source note ID
- **target_id**: Target note ID
- **link_type**: Relationship type (`supports`, `refines`, `extends`, `contradicts`, `is_example_of`, `related`)
- **description**: Optional relationship description

### `zk_generate_summary`
Generate AI summaries for text content
- **text**: Content to summarize
- **max_length**: Character limit (default: 280)

## Example Usage Prompts

Once configured, you can interact with your Zettelkasten naturally:

```
"Create a note about machine learning fundamentals with tags ai, learning, algorithms"

"Search for notes about 'neural networks' and show me the top 5 results"

"Get the note with ID 20250915064516 and show me what links to it"

"Run the CEQRC workflow on my machine learning note to help me refine it"

"Find connections between my note on neural networks and other AI concepts"

"Create a 'supports' relationship between my deep learning note and the neural networks note"
```

## Troubleshooting

### Server Won't Start
- Verify Python path in configuration
- Check that all dependencies are installed
- Ensure data directories exist
- Validate environment variables

### No Tools Available
- Restart Claude Desktop after configuration changes
- Check the MCP server logs for errors
- Verify JSON configuration syntax

### Search Not Working
- Initialize the database by creating at least one note
- Check that FTS5 is enabled in your SQLite installation

### AI Features Disabled
- Verify `OPENAI_API_KEY` is set correctly
- Check API key permissions and quota
- Ensure `ZK_LLM_PROVIDER=openai`

## Advanced Configuration

### Custom Data Paths
```bash
export ZK_NOTES_DIR="/custom/path/to/notes"
export ZK_DB_PATH="/custom/path/to/database.db"
```

### Alternative LLM Providers
Set `ZK_LLM_PROVIDER=stub` for testing without API costs.

### Logging
Enable debug logging:
```bash
export ZK_LOG_LEVEL=DEBUG
```

## Integration Examples

### Research Workflow
1. **Capture**: "Create a note about quantum computing principles"
2. **Search**: "Find all notes tagged with 'quantum' or 'physics'"
3. **Enhance**: "Run the CEQRC workflow on my quantum computing note"
4. **Connect**: "Suggest links between quantum computing and cryptography notes"

### Content Creation
1. **Brainstorm**: Create seed notes for article ideas
2. **Organize**: Use link suggestions to build argument structure
3. **Research**: Search existing notes for supporting evidence
4. **Refine**: Use CEQRC workflow to polish key concepts

This MCP integration transforms your Zettelkasten into an active AI-powered thinking partner, accessible directly through your favorite AI assistant.
