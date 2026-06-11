---
id: admin-plugin-info-endpoint-should-expose-has-errors-error-list-when-partial-aggregation-occurred
title: Admin plugin-info endpoint should expose has_errors / error list when partial aggregation occurred
type: backlog_item
tags:
- reliability
- plugins
- error-handling
- api
importance: 5
status: proposed
priority: medium
rank: 0
---

Follow-up from r1000 (plugin-registry-silent-failures). The registry's _aggregate_dict / _aggregate_list / _aggregate_dict_of_lists already log at ERROR with plugin name + method when an aggregation method raises (regression-locked by TestPluginRegistryFailureVisibility). But the GET /admin/plugins endpoint, and any other API that surfaces aggregated plugin data, still cannot tell the caller whether the result is partial — it returns a dict with no flag. Acceptance: (a) _aggregate_dict/list/dict_of_lists return (result, errors) where errors is a list of {plugin, method, error} dicts; (b) admin/plugins response includes errors list when non-empty + a has_errors bool; (c) CLI sw command surfaces a partial-data warning when has_errors is true. Effort: M (interface change rippling through public registry methods).
