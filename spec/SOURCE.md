# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasksMate API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/Tasks-Mate-Backend`, branch `feature/main/rithin` |
| Backend commit | `6b75d01` — "fix(api): 4.1b B-D - spec hygiene (auth params, examples, uploads, named bodies, update defaults), webhooks in the spec" (task 4.1b; on `ef0e127`, 4.1b A) |
| Served by | `uvicorn app.main:app` on `http://localhost:8000` (`ENV=dev`, supabase-dev), 2026-09-26 |
| `info.version` | `2026-09-25` |
| Size | 94 paths · 152 operations · 180 component schemas · 99 `webhooks` (98 events + `webhook.test`) |
| SHA-256 | `41a61eb3587f40474d4b568472c46a9565cc4fa4f0d96e7c5a416c46e214a496` |

`servers` in the snapshot come from the backend's `BASE_API_URL` / `BASE_API_DEV_URL` settings of the environment that
served it (here: the deployed dev API first, then `http://localhost:8000`). The first one is the SDK's default base URL
(`tasksmate.DEFAULT_BASE_URL`), so **the snapshot for a release (S.23) must be taken from production settings**.

## Refreshing it

```bash
curl -s http://localhost:8000/openapi.public.json | python -m json.tool --indent 2 > spec/openapi.public.json
python scripts/generate.py          # regenerates src/tasksmate/_generated, the facade and docs/api
pytest && mypy                      # the drift test fails if an operationId has no facade method
```

Update the table above (commit, date, counts, SHA-256) in the same commit. CI regenerates from this file and fails on
any difference, so a spec change and its generated code always land together and are reviewed together.
