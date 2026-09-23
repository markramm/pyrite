- **A containerised Pyrite now binds `0.0.0.0` and honours the platform's
  `$PORT`, so a Docker or Railway deploy passes its healthcheck (#20).** The
  server defaulted to `127.0.0.1:8088` and ignored `PORT`, so it came up on an
  interface nothing outside the container could reach and the platform killed
  it as unhealthy. Port precedence is now `PYRITE_PORT` > `PORT` >
  config/default, and a non-integer value raises an error naming the variable
  it came from instead of a bare `int()` traceback. Only the image sets
  `PYRITE_HOST=0.0.0.0` — a local `pyrite serve` still binds loopback, so
  nothing on your machine starts listening on every interface because of this
  change. Railway's one-click deploy still needs a volume mounted at `/data`.
