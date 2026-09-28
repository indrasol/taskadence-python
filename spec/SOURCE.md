# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasksMate API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/Tasks-Mate-Backend`, branch `feature/roadmap-removal/rithin` |
| Backend commit | `ef1e262` — "feat(db): 5.7 - drop the roadmap tables and team_milestones.stop_id (dev; backup in docs/backups)" (task 5.7; the public spec moved at `81952fd` — `GET /v1/milestones`, `milestones.list_org` — and `87a632d` — the four roadmap reads, their schemas, `MilestoneOut.stop_id` and the ten roadmap webhook events removed) |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-09-28 — the same document `tasksmate-docs/scripts/sync-spec.sh` writes, byte for byte |
| `info.version` | `2026-09-25` |
| Size | 104 paths · 165 operations (159 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 201 component schemas · 90 `webhooks` (89 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `f593f0c887eae8105a3d70bd9e0c7afd3eab9d76db4ac9f4f5ae14a9e6b1d93c` |

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
