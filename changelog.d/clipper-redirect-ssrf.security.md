- **The web clipper re-validates every redirect hop, not just the URL it was
  handed (#219).** `_check_url_safe` refused loopback, link-local, RFC1918 and
  reserved addresses for the first request, and httpx then followed
  `follow_redirects=True` without checking where it landed: a public host could
  answer `302 Location: http://127.0.0.1:8000/api/kbs`, or the cloud metadata
  address, and the clipper returned the internal response to the caller. A
  request hook now runs the same check for every request in the chain, and the
  refusal is the same `ClipperBlockedHostError` a directly blocked URL raises,
  so the two cannot be told apart.
