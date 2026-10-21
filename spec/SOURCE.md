# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasKadence API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/taskadence-api`, branch `feat/sub-projects` (cut from `batch/2026-10-post-release8`; NOT yet on `main`) |
| Backend commit | `9b7e748` - N.3 sub-projects (MCP commit on top of the API commit `c93c5ad`): `parent_project_id` on the project models, `ProjectCard.child_count`, `ProjectInDB.parent` / `children`, `ProjectDeleted`, `include_children` on `GET /v1/tasks`, webhooks `project.parent_changed` / `project.children_detached`. Against the previous pin (`5069093`) it also carries the batch branch's additions: 6 operations (task batch create / update, task dependents, reopen, team view pins) and their schemas, 6 more webhooks, `TaskTypeEnum` + `access`. Nothing removed |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-10-21, from the feature worktree with **placeholder** production settings (`env -i`; no `.env.production` read: only `BASE_API_URL`, a random `WEBHOOK_SECRET_KEK_TM` and a random `ACCESS_CONNECTOR_KEK_TM`). `servers` unchanged |
| `info.version` | `2026-09-25` |
| Size | 118 paths · 182 operations (176 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 246 component schemas · 100 `webhooks` (99 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `99bf7b459d0b6618798844b152d4e383c03e47a6ceb073ea63b7543be03488cd` |

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
