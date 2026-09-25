---
id: block-service
title: Block Service
type: component
tags:
- core
- blocks
importance: 5
kind: service
path: pyrite/services/block_service.py
owner: core
---

Reads the blocks the indexer extracted from an entry's body (the block table): list_blocks (body order, filtered by heading, block_type, block_id) and find_block (the first block matching a wikilink #heading or ^block-id fragment). GET /api/entries/{id}/blocks and GET /api/entries/resolve use it (#380). Provided by get_block_service in server/api.py.
