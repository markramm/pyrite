- **CLI commands now include knowledge bases added with `pyrite kb add` (#363).** Search and named schema commands resolve database-registered KBs when they are absent from config.yaml. Named lookups use config.yaml first; if index lookup fails, the command warns and continues with the YAML config.

- **Behavior note:** bare `kb validate` also checks `kb add` registrations, so a registration whose directory was deleted now makes it fail. For a registered KB whose directory is missing, `kb schema add-type` and `search -k` can still proceed; `pyrite create` already works this way.
