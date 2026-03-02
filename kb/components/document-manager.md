---
id: document-manager
title: Document Manager
type: component
kind: module
path: pyrite/storage/document_manager.py
owner: core
dependencies:
- pyrite.storage.repository
- pyrite.storage.database
- pyrite.storage.index
tags:
- core
- storage
---

Write-path coordination for KB entries. Consolidates the save-register-index pattern into a single class, completing the ODM abstraction layer.

## Pattern

```
KBRepository.save() → PyriteDB.register_kb() → IndexManager.index_entry()
```

## Key Methods

- `save_entry(entry, kb_name, kb_config)` — save to disk, register KB, index
- `delete_entry(entry_id, kb_name, kb_config)` — delete from disk and index
- `index_entry(entry, kb_name, file_path)` — re-index from existing file

## Consumers

- `KBService.create_entry()`, `update_entry()`, `delete_entry()` — all write paths go through DocumentManager

## Related

- [[storage-layer]] — PyriteDB and IndexManager
- [[kb-service]] — business logic layer that uses DocumentManager
