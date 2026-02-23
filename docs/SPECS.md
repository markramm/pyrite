
# Functional Specs & Interfaces

## Entities
**Note**: { id, title, body, summary, tags[], links[{to,type}], status, timestamps }

## Storage
- Files: `{id}.md` with YAML frontmatter (includes summary field).
- DB: tables `zettel` (with summary column), `tag`, `zettel_tag`, `link`, and FTS `zettel_fts` (indexes title, body, summary).

## CLI
- `new "Title" -c "Body" -t tag1,tag2`
- `show ID`
- `update ID --title --content --tags`
- `delete ID`
- `search "query" [--tag TAG]`
- `link SRC TGT TYPE`
- `ceqrc ID`

## API
- `POST /notes` {title, body, summary?, tags} - auto-generates summary if not provided
- `GET /notes/{id}` - returns note with summary field
- `PUT /notes/{id}` - updates note, regenerates summary if body changed
- `DELETE /notes/{id}`
- `GET /search?q=...&tag=...` - searches title, body, and summary fields
- `POST /generate-summary` {text} - generates summary within character limit
- `GET /notes/{id}/backlinks`
- `POST /notes/{id}/links` {target_id, type}
- `POST /notes/{id}/ceqrc`

## MCP Tools (examples)
- `zk_create_note` → create seed note
- `zk_search` → FTS search
- `zk_run_ceqrc` → probe + crystallize + connect
