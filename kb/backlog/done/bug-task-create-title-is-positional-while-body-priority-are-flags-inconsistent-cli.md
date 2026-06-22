---
id: bug-task-create-title-is-positional-while-body-priority-are-flags-inconsistent-cli
title: "CLI ERGONOMICS BUG (investigation-conductor session 2026-06-10)"
type: backlog_item
tags: [bug, conductor-filed, cli, task-system]
importance: 5
kind: bug
status: done
priority: low
effort: S
rank: 0
---

CLI ERGONOMICS BUG (investigation-conductor session 2026-06-10). 'pyrite task create' takes TITLE as a positional argument but body/priority/parent as flags. Tried 'pyrite task create --title X --body Y' -> error 'No such option: --title'. Correct form is 'pyrite task create "X" --body Y --priority N'. Inconsistent: either TITLE should also be a --title flag, OR the error should hint 'TITLE is positional: pyrite task create <title> [--body ...]'. Low severity, repeated friction. Owner: pyrite repo CLI.

## Resolution (2026-06-22)

`pyrite task create` now accepts the title EITHER positionally
(`task create "X"`) OR via `--title`/`-t` (`task create --title X`).
Supplying both is a clear error; supplying neither prints a helpful hint
naming both forms. Regression test: tests/test_task_cli_create_title.py.
