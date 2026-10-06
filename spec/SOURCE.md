# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasKadence API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/taskadence-api`, branch `fix/mcp-project-status` |
| Backend commit | `5fa0aa4` — fix(mcp): `ProjectStatusEnum` loses `active` (never a `project_status_enum` value: create / update with it was a 500); `invalid-parameter` is documented for 422 too (a body field outside its fixed set of values, `errors[].allowed`) |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-10-04 — the same document `taskadence-docs/scripts/sync-spec.sh` writes, byte for byte |
| `info.version` | `2026-09-25` |
| Size | 110 paths · 172 operations (166 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 222 component schemas · 92 `webhooks` (91 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `7db026e13dc5afaffdc12a4166c60e7e9e8df2d4119e66d477c23c064b41fc6c` |

`servers` in the snapshot come from the backend's `BASE_API_URL` / `BASE_API_DEV_URL` settings of the environment that
served it. From 4.6b it is served with **production settings**: `servers` is the production API alone (no localhost).
The first one is the SDK's default base URL (`taskadence.DEFAULT_BASE_URL`) — the same URL as before, now labelled
correctly — and the rule for a release (S.23) holds: take the snapshot from production settings.

## Refreshing it

```bash
curl -s http://localhost:8000/openapi.public.json | python -m json.tool --indent 2 > spec/openapi.public.json
python scripts/generate.py          # regenerates src/taskadence/_generated, the facade and docs/api
pytest && mypy                      # the drift test fails if an operationId has no facade method
```

Update the table above (commit, date, counts, SHA-256) in the same commit. CI regenerates from this file and fails on
any difference, so a spec change and its generated code always land together and are reviewed together.
