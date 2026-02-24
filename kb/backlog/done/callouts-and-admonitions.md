---
type: backlog_item
title: "Callouts and Admonitions"
kind: feature
status: done
priority: medium
effort: S
tags: [web, editor, markdown]
---

Styled callout blocks in the editor and rendered views:

**Syntax (Obsidian-compatible):**
```markdown
> [!info] Title
> Content here

> [!warning] Caution
> Important warning

> [!tip] Pro tip
> Helpful advice
```

**Types:** info, warning, tip, note, danger, quote, example, bug, question, success, failure, abstract

**Implementation:**
- Markdown parser extension to recognize `> [!type]` syntax
- CodeMirror decoration for styled rendering in live preview
- CSS styling with type-specific icons and colors (dark/light mode)
- Tiptap custom node for WYSIWYG mode

Small effort — mostly CSS + a Lezer grammar extension. High value for research notes (warnings, key findings, open questions).
