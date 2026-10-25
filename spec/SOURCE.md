# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasKadence API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/taskadence-api`, branch `feature/ia-redesign` (release 10, cut from `dev`; NOT yet on `main`) |
| Backend commit | `7aa25c4` - release 10: sprints belong to projects; teams, sections and test sprints removed. Against the previous pin (`9b7e748`): 19 operations removed (`teams.*` 11, `sections.*` 5, `tasks.set_section`, `view-pins.pin_team` / `unpin_team`), 4 added (`sprints.list_org`, `sprints.read`, `availability.mark_mine`, `workload.read`), 8 moved (`sprints.*` from `/v1/teams/{team_id}/sprints` to `/v1/projects/{project_id}/sprints` and `/v1/sprints/{sprint_id}`, `sprints.update` PUT → PATCH; `availability.*` from `/v1/teams/{team_id}` to `/v1/organizations/{org_id}`); 22 schemas removed, 5 added; `team_id` / `section_id` / `tracker_id` / `bug_id` fields removed; `position` on sprints and `ProjectUpdate`; 10 `team.*` / `project.team_*` webhooks removed; problem type `sprint-project-mismatch` |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-10-24, from a detached worktree of `7aa25c4` with **placeholder** production settings (`env -i`; no `.env.production` read: only `BASE_API_URL`, a random `WEBHOOK_SECRET_KEK_TM` and a random `ACCESS_CONNECTOR_KEK_TM`). `servers` unchanged |
| `info.version` | `2026-10-24` (was `2026-09-25`) |
| Size | 111 paths · 167 operations (161 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 229 component schemas · 90 `webhooks` (89 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `a16c6df00c8b0d17666299addc9c1d410ee3cc156165247e31643448cbbf5700` |

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
