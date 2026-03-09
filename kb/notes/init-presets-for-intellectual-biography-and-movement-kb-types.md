---
id: init-templates-for-intellectual-biography-and-movement-kb-types
title: Init templates for intellectual-biography and movement KB types
type: backlog_item
tags:
- cli
- templates
- agent
status: done
assignee: agent-a
kind: feature
priority: high
effort: S
links:
- target: epic-agent-cli-feature-requests-for-kb-workflows
  relation: subtask_of
  kb: pyrite
---

## Problem

Of 26 planned KBs, 20 are intellectual-biography type and 3 are movement type. Existing templates (software, zettelkasten, research, empty) don't match. Every new KB requires starting from research template and manually adding types, configuring intent layer.

## Proposed Solution

Add two new built-in templates to \`pyrite init\`.

### intellectual-biography template types

- \`note\` — Core concept or idea (subdirectory: notes/)
- \`writing\` — Published work by the subject. Fields: writing_type (book, paper, talk, blog-post, report), date, url
- \`era\` — Biographical period. Fields: date_range
- \`event\` — Key moment or milestone. Fields: date, importance
- \`person\` — People in the subject's network. Fields: role, affiliation
- \`source\` — Reference material. Fields: source_type (book, paper, article, documentary, interview), author, date, url
- \`organization\` — Institutions involved. Fields: org_type, jurisdiction

### movement template

Same as intellectual-biography plus:
- \`practice\` — Method, framework, or technique. Fields: origin, status (active, deprecated, evolved)
- Adjusted description/guidelines for movement-level scope

## Impacted Files

- \`pyrite/cli/init_command.py\` — add to BUILTIN_TEMPLATES

## Acceptance Criteria

- \`pyrite init --template intellectual-biography\` creates KB with all 7 entry types
- \`pyrite init --template movement\` creates KB with all 8 entry types
- Templates match schemas already proven in Boyd, Wardley, Blank KBs
- \`pyrite init --list-templates\` shows both new options
