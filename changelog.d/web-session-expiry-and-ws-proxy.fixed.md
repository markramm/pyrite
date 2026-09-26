- Web: an expired session is now noticed. A 401 on an authenticated request
  clears the signed-in user, which moves the live-update socket's identity
  to anonymous or none as appropriate; the existing `/login` redirect then
  takes over. A 401 from `login`/`getMe` or while already signed out does not
  trigger this, and a 403 never clears the user. (#420)
- Web: `npm run dev`'s Vite proxy now forwards `/ws` to the backend, so the
  live-update socket works under the dev server the way it already did in
  production and in the auth e2e world. (#421)
