# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasKadence API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/taskadence-api`, branch `feature/ia-redesign` (release 10, cut from `dev`; NOT yet on `main`) |
| Backend commit | `e124d44` - release 10 step 8: id generators, task subscribers, transfer follow-ups, roles. Against the previous pin (`b403694`): 5 operations added (`project-members.create_batch` `POST /v1/projects/{project_id}/members/batch`, scope `projects:write`; `tasks.list_subscribers` `GET`, `tasks.set_subscribers` `PUT /v1/tasks/{task_id}/subscribers`, `tasks.subscribe` `POST`, `tasks.unsubscribe` `DELETE .../subscribers/me`; scopes `tasks:read` / `tasks:write`), none removed or moved; 8 schemas added (`ProjectImplicitMember`, `ProjectMemberBatchItem`, `ProjectMemberSkipped`, `ProjectMembersBatchAdd`, `ProjectMembersBatchAdded`, `TaskSubscriber`, `TaskSubscribers`, `TaskSubscribersSet`); `ProjectRoleEnum` `owner | member | viewer` (was `editor`); `ProjectMemberInDB.source` / `removable`; `ProjectInDB.members_can_add_people` (deprecated `editors_can_add_members`) and `implicit_members`; `TaskInDB.subscriber_ids` / `is_subscribed`; `OrganizationSettings*.only_admins_create_projects`; `projects.list` query `scope` (`all` | `mine`); the 402 `storage-limit-reached` text says "account"; no id `pattern` (ids are 6-12 digits). Earlier, `b403694` against `7aa25c4`: the account (read-only) and account storage; `7aa25c4` against `9b7e748`: teams, sections and test sprints removed, sprints project-owned |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-10-25, from a detached worktree of `e124d44` with **placeholder** production settings (`env -i`; no `.env.production` read: only `BASE_API_URL`, a random `WEBHOOK_SECRET_KEK_TM` and a random `ACCESS_CONNECTOR_KEK_TM`). `servers` unchanged |
| `info.version` | `2026-10-24` (unchanged since `7aa25c4`; was `2026-09-25` before release 10) |
| Size | 117 paths · 175 operations (169 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 248 component schemas · 90 `webhooks` (89 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `be0b9b77c2d5c3042ca28e8616ffb9919921610726b6c97c54f597f82e452ef5` |

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
