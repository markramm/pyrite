---
id: bug-from-markdown-splits-on-body-triple-dash-parsing-prose-as-frontmatter-yaml
type: backlog_item
title: "PARSER ROBUSTNESS BUG (re-filed from cascade-research; the data-instance was fixed but the underlying pyrite defect was"
kind: bug
status: proposed
priority: high
effort: S
tags: [bug, conductor-filed, cli, task-system]
rank: 1030
---

PARSER ROBUSTNESS BUG (re-filed from cascade-research; the data-instance was fixed but the underlying pyrite defect was never filed against pyrite). pyrite's from_markdown splits on '---' and, when a file's frontmatter block is missing/malformed, mistakes a BODY '---' divider for the frontmatter delimiter — then parses body prose as YAML. Concrete failure: '**Whipple Building**' in body prose parsed as YAML alias '*Whipple' -> ruamel.yaml ComposerError: found undefined alias -> 'index sync' returns Added:0/Updated:0 and SILENTLY no-ops (the bug_pyrite_silent_index_failure family). Two workers independently hit YAML ScannerErrors on different files in one session — recurring, not a one-off. ROOT CAUSE (confirmed in original work log): 5 files lacked frontmatter blocks entirely; from_markdown had no guard. PROPOSED: (a) only treat the FIRST '---...---' at file head as frontmatter (require it to start at line 1); (b) if frontmatter parse fails, FALL BACK to treating the file as bodyless-frontmatter or emit a NAMED error with the file path rather than a raw ruamel alias error; (c) index sync must NOT report success (Added:0/Updated:0 clean exit) when a parse error occurred — surface a non-zero/error count. Owner: pyrite repo. Re-filed from cascade-research/notes/fix-yaml-frontmatter-parse-error...ruamel-undefined-alias-whipple. Related: bug_pyrite_silent_index_failure.
