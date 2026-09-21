---
id: generic-nested-metadata
title: Generic entry with an explicit nested metadata block
type: design
status: draft
metadata:
  owner: team
---

Body text for the generic-nested-metadata fixture. The explicit `metadata:`
block must stay nested while the undeclared top-level `status` key is promoted,
byte-identically, after a no-op load and save (#149).
