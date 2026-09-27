# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasksMate API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/Tasks-Mate-Backend`, branch `feature/main/rithin` |
| Backend commit | `7de395c` — "feat(mcp): 5.3 - CLIENTS table (one source: app/mcp/clients.py → docs/api/mcp-clients.json, GET /v1/mcp/clients), health names the packages" (task 5.5; the public spec moved at 5.2 `f3cf68e` — `/oauth/register`, 5.4 `89d4d52` — the review step, `created_via` / `review` filters, `agent` type retired, and 5.3 — `GET /v1/mcp/clients`) |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-09-27 — the same document `tasksmate-docs/scripts/sync-spec.sh` writes, byte for byte |
| `info.version` | `2026-09-25` |
| Size | 107 paths · 168 operations (162 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 206 component schemas · 100 `webhooks` (99 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `6300e915d95126ee6dfd89d76aecf109a7c06cb8c25db97f850ae0ceb7cb18b2` |

`servers` in the snapshot come from the backend's `BASE_API_URL` / `BASE_API_DEV_URL` settings of the environment that
served it. From 4.6b it is served with **production settings**: `servers` is the production API alone (no localhost).
The first one is the SDK's default base URL (`tasksmate.DEFAULT_BASE_URL`) — the same URL as before, now labelled
correctly — and the rule for a release (S.23) holds: take the snapshot from production settings.

## Refreshing it

```bash
curl -s http://localhost:8000/openapi.public.json | python -m json.tool --indent 2 > spec/openapi.public.json
python scripts/generate.py          # regenerates src/tasksmate/_generated, the facade and docs/api
pytest && mypy                      # the drift test fails if an operationId has no facade method
```

Update the table above (commit, date, counts, SHA-256) in the same commit. CI regenerates from this file and fails on
any difference, so a spec change and its generated code always land together and are reviewed together.
