---
id: spike-plugins-out-of-tree-import-inventory-and-the-public-plugin-contract
title: 'Spike: plugins out of tree — import inventory and the public plugin contract'
type: backlog_item
tags:
- architecture
- plugin
importance: 5
kind: spike
status: proposed
priority: medium
effort: M
rank: 0
---

Maintainer direction, 2026-09-26: the plugins defined what core needs. Now move journalism-investigation (the pilot), cascade, social, encyclopedia and maybe zettelkasten out of tree as separate projects, to show how plugins are built and to allow a wider ecosystem. software-kb stays in tree.

Deliverables:
- The inventory: every pyrite.* symbol each plugin imports. The union is the de facto plugin API; the internals it contains are layer violations to fix first.
- A proposed ADR: 'Extensions live out of tree; the plugin contract is the public API'. It covers the entry-point group, protocols, conformance tests plugins run in their own CI, a compatibility policy, and the trust model (P-K1).
- A template repo outline.
