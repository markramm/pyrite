- **`/ws` now authenticates its handshake and sends each socket only the KBs its
  owner may read (#218).** Before this, anyone who could reach the server could
  open `/ws` with no credential and receive the *names* of private KBs and the
  ids of entries created in them, as they happened (no titles or bodies). The
  handshake now accepts the same credentials as the REST API (an operator API
  key as a header or `?api_key=`, the `pyrite_session` cookie, or the
  anonymous tier when one is configured) and is refused otherwise; a handshake
  whose `Origin` is neither the server's own host nor in `cors_origins` is
  refused too. A socket's readable KBs are fixed when it connects, so a revoked
  grant or a logout takes effect on reconnect. A default local install (auth
  off, no API keys) still needs no credential, but the `Origin` check applies
  there too, so another site open in the same browser can no longer read the
  event stream. If the web UI is served from an origin other than the API's
  host, or a reverse proxy rewrites the `Host` header, add the UI's origin to
  `cors_origins`; a refused handshake is logged as a warning naming both. An
  event that names no KB reaches a scoped socket only if it is a global event
  (`kb_synced`).
