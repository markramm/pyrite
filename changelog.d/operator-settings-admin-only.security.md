- **Operator settings are admin-only, and secret settings are never read
  back.** The settings API let any write-tier caller change instance-wide
  operator settings -- the AI provider, model, base URL and API key -- and
  returned stored credentials such as `ai.apiKey` in plain text to every
  caller who could read settings, including the anonymous tier. Changing an
  `ai.*` setting, or any setting whose name marks it as a credential
  (`apiKey`, `token`, `secret`, `password`, `credential`), now requires the
  admin tier; `GET /api/settings` and `GET /api/settings/{key}` return a
  fixed mask for a secret that is set (listed under `masked`), to every
  caller including admins, and writing the mask back leaves the stored value
  unchanged. The web settings page shows the key as "set on the server".
  **Operators:** if your instance allowed anonymous or write-tier access and
  an AI API key was stored through the settings page, treat that key as
  exposed and rotate it with your provider, then set the new one as an
  admin. Check that `ai.baseUrl` and `ai.provider` hold the values you
  expect.
