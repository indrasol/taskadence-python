# Where `openapi.public.json` came from

`spec/openapi.public.json` is **the only input** the SDK is generated from (`python scripts/generate.py`). It is a
snapshot of the public contract the TasksMate API serves at `/openapi.public.json`, pretty-printed
(`python -m json.tool --indent 2`), committed so that a regeneration never depends on a live server.

| | |
|---|---|
| Backend repo | `indrasol/Tasks-Mate-Backend`, branch `feature/main/rithin` |
| Backend commit | `71a97a4` — "fix(webhooks): KEK env is WEBHOOK_SECRET_KEK_TM; docs(api): 4.4 workflow + 4.5 spec typing" (task 4.5 A0) |
| Served by | `uvicorn app.main:app` on `http://localhost:8000` (`ENV=dev`, supabase-dev), 2026-09-25 |
| `info.version` | `2026-09-25` |
| Size | 94 paths · 152 operations · 177 component schemas |
| SHA-256 | `1acfedc840539456deb8f3e6467f426651e6f562d0e45e0cea3b0a61490ef9a4` |

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
