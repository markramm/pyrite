---
id: bug-task-create-title-is-positional-while-body-priority-are-flags-inconsistent-cli
type: backlog_item
title: "CLI ERGONOMICS BUG (investigation-conductor session 2026-06-10)"
kind: bug
status: proposed
priority: low
effort: S
tags: [bug, conductor-filed, cli, task-system]
---

CLI ERGONOMICS BUG (investigation-conductor session 2026-06-10). 'pyrite task create' takes TITLE as a positional argument but body/priority/parent as flags. Tried 'pyrite task create --title X --body Y' -> error 'No such option: --title'. Correct form is 'pyrite task create "X" --body Y --priority N'. Inconsistent: either TITLE should also be a --title flag, OR the error should hint 'TITLE is positional: pyrite task create <title> [--body ...]'. Low severity, repeated friction. Owner: pyrite repo CLI.
