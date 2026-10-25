# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasKadence API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/taskadence-api`, branch `feature/ia-redesign` (release 10, cut from `dev`; NOT yet on `main`) |
| Backend commit | `b403694` - release 10 step 5: storage and billing at the account level. Against the previous pin (`7aa25c4`): 3 operations added (`account.read` `GET /v1/account`, `account.people` `GET /v1/account/people`, `account.storage` `GET /v1/storage`; scope `account:read`), none removed or moved; 11 schemas added (`Account*`, `PersonOrg`, `MeAccount`, `WorkloadSprint`); `MeOut.account`; `WorkloadPerson.active_sprint`; `team_members` → `members` on the project models and `ProjectStatsInDB`; `ProjectInDB.position`; `StorageUsage` gains `account_id`, `account_used_bytes`, `account_quota_bytes`, `account_percent`, `exempt_message` and loses `billing_exempt`; problem types `email-in-other-account` (409) and `removed-in-release-10` (410). Billing and support routes are internal (not in the public spec). Earlier, `7aa25c4` against `9b7e748`: teams, sections and test sprints removed, sprints project-owned |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-10-24, from a detached worktree of `b403694` with **placeholder** production settings (`env -i`; no `.env.production` read: only `BASE_API_URL`, a random `WEBHOOK_SECRET_KEK_TM` and a random `ACCESS_CONNECTOR_KEK_TM`). `servers` unchanged |
| `info.version` | `2026-10-24` (unchanged since `7aa25c4`; was `2026-09-25` before release 10) |
| Size | 114 paths · 170 operations (164 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 240 component schemas · 90 `webhooks` (89 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `9c7c8fd40cb086fb62c2cb74827dc072b8b45274ba6b609f1608b6101c6b62bf` |

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
