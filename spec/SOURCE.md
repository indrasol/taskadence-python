# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasksMate API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/Tasks-Mate-Backend`, branch `feature/roadmap-removal/rithin` |
| Backend commit | `b8385de` — "fix(mcp,tasks): 5.5 fix round 2 part A - creating token cannot review; reviewed actor; org counts; scope challenge follows groups" (task 5.5 fix round 2: `TaskInDB.created_by_token_id` — the access token that created a task, which cannot review it; `OrganizationInDB.member_count`, and `GET /v1/organizations/{org_id}` reports the list's counts) |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-09-28 — the same document `tasksmate-docs/scripts/sync-spec.sh` writes, byte for byte |
| `info.version` | `2026-09-25` |
| Size | 108 paths · 170 operations (164 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 209 component schemas · 92 `webhooks` (91 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `1ac7750a312698650b42ce6347868c502736de1eb187ef2dd1f7cb66b0114c3d` |

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
