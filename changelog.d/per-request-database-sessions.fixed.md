- **The API returned 500s under ordinary concurrent read load: one SQLAlchemy
  `Session` was shared by every request.** `PyriteDB` created a single
  `Session` in its constructor and the server cached one `PyriteDB` on app
  state, so the ~117 plain `def` handlers — which FastAPI runs on anyio's
  40-thread worker pool — all drove one session at once, with
  `check_same_thread=False` silencing SQLite's own guard. The result was
  corrupted result state rather than a clean error, surfacing as
  `IndexError: tuple index out of range`, `InvalidRequestError: This session is
  provisioning a new connection`, `SystemError`, and in CI `This session is in
  'prepared' state` — four messages, one cause. Measured at **75% of 240
  concurrent reads failing** in-process and **9 of 96 requests returning 500**
  at concurrency 8 against a live server; both are now **0**. Each request gets
  its own session via a per-request handle onto the shared engine, closed on
  every exit path, and the connection pool is sized to the threadpool
  (`pool_size=40, max_overflow=20`) so per-request sessions cannot trade the
  corruption for `QueuePool limit ... reached`. `verify_api_key` no longer runs
  synchronous DB work on the event-loop thread, and the shared raw sqlite3
  connection now hands out a private cursor under a lock instead of sharing an
  implicit one. Query results and every endpoint's behaviour are unchanged.
  Fixes #131.

