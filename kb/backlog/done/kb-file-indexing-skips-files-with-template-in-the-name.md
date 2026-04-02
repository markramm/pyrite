---
id: kb-file-indexing-skips-files-with-template-in-the-name
title: KB file indexing skips files with template in the name
type: backlog_item
tags:
- bug
- indexing
kind: bug
status: done
priority: high
assignee: claude
effort: XS
---

KBRepository.list_files() skips any file whose name contains template. This is too broad -- it should only skip _template prefix files, not entries that happen to have template in the title. Discovered when init-templates backlog item was silently excluded from index. Workaround: rename file. Fix: narrow the filter in pyrite/storage/repository.py list_files().
