---
id: create-body-file-nested-yaml-bug
title: "pyrite create --body-file Doesn't Merge Nested YAML into Frontmatter"
type: backlog_item
kind: bug
status: proposed
priority: medium
effort: S
tags: [bug, cli, metadata]
---

# pyrite create --body-file Doesn't Merge Nested YAML into Frontmatter

## Problem

When using `pyrite create --body-file` with content that starts with a YAML frontmatter block (`---\nkind: ...\n---`), the metadata stays in the body instead of being merged into the entry's actual frontmatter. This means component fields like `kind`, `path`, `owner`, `dependencies` aren't indexed and don't appear in `pyrite sw components`.

## Reproduction

```bash
cat > /tmp/component.md << 'EOF'
---
kind: service
path: pyrite/services/foo.py
owner: core
dependencies: [kb-service]
---

Service description here.
EOF

pyrite create -k pyrite -t component --title "Foo Service" --body-file /tmp/component.md
# Result: the kind/path/owner/dependencies are in the body, not in frontmatter
```

## Expected Behavior

When `--body-file` content starts with a YAML frontmatter block, merge those fields into the entry's frontmatter metadata. The remaining content after the second `---` becomes the body.

## Location

`pyrite/cli/__init__.py` or wherever the `create` command processes `--body-file` input.
