# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasKadence API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/taskadence-api`, branch `dev` |
| Backend commit | `af56676` — Merge #201 (the stored file's `size_bytes` in the attachment and project-resource responses), after #199 / #198 (release 2: direct uploads `uploads.create` / `uploads.complete` public, 100 MB uploads, 10 GB included storage, A.3 SSO, the TasKadence wordmark) |
| Served by | `app.main:app` via `TestClient` (`ENV=production`, `ALLOWED_HOSTS_TM=testserver`, `BASE_API_URL` = the production API), 2026-10-06, from a detached worktree with **placeholder** production settings (no `.env.production` read: only `BASE_API_URL` and a random `WEBHOOK_SECRET_KEK_TM`). Against the previous pin the only difference is `size_bytes` on `TaskAttachmentInDB` and `ProjectResourceInDB` (and the response examples that carry them); paths, operations, schemas and `servers` are unchanged |
| `info.version` | `2026-09-25` |
| Size | 112 paths · 174 operations (168 SDK methods: the 6 `x-kind: oauth` protocol operations are not generated) · 225 component schemas · 92 `webhooks` (91 events + `webhook.test`) · `x-problem-types`, `x-scope-descriptions`, `x-limits` (the docs site's tables) |
| SHA-256 | `ca56ccaf8fe57dd912b90ee1fcec0f13e52aaf3e34adf7e1af00adac89bcabf2` |

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
