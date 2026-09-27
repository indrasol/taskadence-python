# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasksMate API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/Tasks-Mate-Backend`, branch `feature/main/rithin` |
| Backend commit | `8b86aa0` — "feat(security): 4.7 - ALLOWED_HOSTS_TM: a Host header allowlist (the OAuth issuer is derived from it)" (task 4.7; the public spec is byte-identical to `28fb27b`'s — 4.8 OAuth apps and 4.9 views of projects moved it from `073e120`) |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`), 2026-09-27 — the same document `tasksmate-docs/scripts/sync-spec.sh` writes, byte for byte |
| `info.version` | `2026-09-25` |
| Size | 104 paths · 165 operations (160 SDK methods: the 5 `x-kind: oauth` protocol operations are not generated) · 195 component schemas · 99 `webhooks` (98 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `0ef4181629983f77504005e59d527490ef8d237bcb67c66f5c5ac64891a50b3a` |

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
