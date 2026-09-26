- `GET /api/entries/types` and `GET /api/entries/type-schemas` now require read
  access to any `kb` they are asked about, refusing an unreadable KB exactly as
  every other entries route does; with no `kb` named, `/api/entries/types`
  reports only the entry types found in the caller's own readable KBs.
