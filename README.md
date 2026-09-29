# tasksmate — the TasksMate API for Python

A typed Python client for the [TasksMate](https://tasksmate.indrasol.com) public API, generated from its OpenAPI
contract so it cannot drift from the API, with a small hand-written layer for what generators get wrong: pagination,
retries, typed errors, ETags, idempotency and pandas. Plus a `tm` command line and a Streamlit example.

> **`0.x` is a pre-release.** There is no compatibility promise until 1.0 (TasksMate's stability gate). Pin an exact
> version, and read the [changelog](CHANGELOG.md) before upgrading.

## Install

```bash
pip install tasksmate                  # the client (Python 3.10+)
pip install "tasksmate[pandas]"        # + DataFrames
pip install "tasksmate[cli]"           # + the `tm` command line
```

_Not on PyPI yet: until the first release, install from a checkout — `pip install -e ".[pandas,cli]"` — or from a
built wheel (`python -m build`, then `pip install "dist/tasksmate-<version>-py3-none-any.whl[pandas]"`)._

## Quickstart

```python
from tasksmate import TasksMate

tm = TasksMate(token="tm_live_…")                   # or set TASKSMATE_TOKEN and call TasksMate()
for task in tm.tasks.list(org_id="O0020"):           # every task, page after page
    print(task.task_id, task.status, task.title)
tm.views.rows("V123456").to_dataframe()               # a saved view as a pandas DataFrame
```

- **Token:** mint it in TasksMate → **Developers → Tokens** (it is shown once).
- **OAuth apps:** the authorization flow (`/oauth/authorize`, `/oauth/token`, `/.well-known/*`) is not wrapped here —
  run it with any OAuth 2.1 library; the access token it returns is a token like any other: `TasksMate(token=…)`.
  `/oauth/register` (dynamic client registration, what an MCP client calls) is protocol too, not a method.
- **Reach:** a token belongs to one organization and carries **scopes** (`tasks:read`, `tasks:write`,
  `projects:read`, …); each method's docstring names the scope it needs.
- **Try it:** [`examples/quickstart.py`](examples/quickstart.py) runs a full round trip — create, conditional update,
  filtered list, DataFrame, delete — and leaves nothing behind.

## The client

`tm.<resource>.<verb>(…)` exists for **every** public operation of the API (162 today — all but the OAuth
authorization-flow routes, see above), named after its
`operationId`: `tasks.create`, `tasks.list`, `tasks.read` (alias `get`), `tasks.update` (PATCH), `tasks.replace` (PUT),
`tasks.delete`, `tasks.set_project` (alias `move`), `projects.list`, `views.rows`, `webhooks.test`, … The full list,
generated from the spec, is in [`docs/api/`](docs/api/README.md).

```python
from tasksmate import TasksMate
from tasksmate.models import TaskCreate, TaskUpdate

tm = TasksMate()                                      # TASKSMATE_TOKEN; TASKSMATE_API_URL to change the server
me = tm.me()                                          # who the token acts as: me.principal, me.organizations
task = tm.tasks.create(TaskCreate(org_id="O0020", title="Ship the SDK", priority="high"))
task = tm.tasks.create({"org_id": "O0020", "title": "Ship the SDK"})   # a plain dict works too
tm.tasks.update(task.task_id, TaskUpdate(status="in_progress"))       # sends ONLY the fields you set
tm.tasks.update(task.task_id, {"due_date": None})                     # null clears a field (JSON merge-patch)
```

Every response is a typed model (`tasksmate.models`, generated `attrs` classes with `to_dict()` / `from_dict()`).
Configuration: `TasksMate(token=None, base_url=None, *, timeout=30, max_retries=3, api_version=None,
max_retry_after=60, headers=None, http_client=None)`; use it as a context manager or call `tm.close()`.
`AsyncTasksMate` has the same namespaces with `await`:

```python
import asyncio
from tasksmate import AsyncTasksMate

async def main() -> None:
    async with AsyncTasksMate() as tm:
        async for task in await tm.tasks.list(org_id="O0020", filter={"status": ["blocked"]}):
            print(task.task_id)

asyncio.run(main())
```

### Lists and pagination

Every list returns a `Page`: `.data` (this page), `.next_cursor`, and iteration over **every** item, following the
cursor until it is `None` (a page may be short, or even empty, while more follow — iteration handles it).

```python
page = tm.tasks.list(org_id="O0020", filter={"status": ["in_progress", "blocked"], "search": "invoice"},
                     sort_by="due_date", limit=200)
page.data, page.next_cursor          # the first page
for task in page: ...                # all of them
for p in page.pages(): ...           # page by page
page.envelope                        # the full response model (some lists carry sums beside `data`)
```

`filter={key: value}` becomes `filter[key]=value` (a list is comma-joined); an unknown key raises `ValueError`
naming the allowed ones. The grammar — keys, sorts, limits — is the API's
[list grammar](https://github.com/indrasol/Tasks-Mate-Backend/blob/dev/docs/api/list-grammar.md).

### Errors

Every API error is `application/problem+json`, and every problem type is its own exception, all subclasses of
`tasksmate.TasksMateError` (itself an `APIError`) with `.status`, `.type`, `.title`, `.detail`, `.request_id`,
`.errors`:

```python
from tasksmate import InsufficientScopeError, NotFoundError, PreconditionFailedError, TasksMateError

try:
    tm.tasks.update("T123456", {"status": "completed"})
except InsufficientScopeError as exc:
    print("this token needs", exc.required_scope)          # e.g. tasks:write
except NotFoundError:
    ...
except TasksMateError as exc:
    print(exc.status, exc.detail, "— quote request_id", exc.request_id)
```

| Status | Exceptions |
|---|---|
| 400 | `BadRequestError` · `InvalidParameterError` · `IdempotencyKeyInvalidError` |
| 401 | `AuthenticationError` · `TokenInvalidError` · `TokenExpiredError` · `TokenRevokedError` |
| 403 | `ForbiddenError` · `InsufficientScopeError` · `TestTokenReadOnlyError` · `TokenPolicyError` (also 422) |
| 404 · 409 · 412 | `NotFoundError` · `ConflictError` (`IdempotencyKeyInFlightError`) · `PreconditionFailedError` |
| 422 | `UnprocessableEntityError` · `ValidationError` · `IdempotencyKeyReusedError` · `UrlRefusedError` |
| 429 · 5xx | `RateLimitedError` (`.retry_after`) · `InternalError` |
| — | `APIConnectionError` / `APITimeoutError` (no HTTP answer) · `ResponseValidationError` (a 2xx this SDK version cannot read — upgrade) |

### Retries

Safe requests are retried up to `max_retries` times (default 3) on **429** (waiting what `Retry-After` says),
**502 / 503 / 504** and connection failures, with exponential backoff and jitter. Safe means: GET, HEAD, DELETE, PUT;
PATCH only with `if_match`; POST only with an `Idempotency-Key`. A `Retry-After` longer than `max_retry_after` seconds
(default 60) is not waited out — the `RateLimitedError` is raised at once.

### Idempotent creates

Every create operation (`tasks.create`, `projects.create`, `goals.create`, `task-comments.create` / `reply`) sends an
`Idempotency-Key` — a fresh uuid4 per call, reused by that call's retries — so a retried create never makes two.
Pass your own with `idempotency_key="…"` (the API replays the first answer for 24 h), or `idempotency_key=None` for
none (and no retries).

### ETags and conditional requests

A model read by a single GET carries `.etag` (it is never serialized):

```python
from tasksmate import NotModified, PreconditionFailedError

task = tm.tasks.get("T123456")
tm.tasks.update("T123456", {"status": "completed"}, if_match=task.etag)   # 412 if someone changed it since
if tm.tasks.get("T123456", if_none_match=task.etag) is NotModified:      # 304: nothing changed, no body
    ...
```

### Deprecations

When the API answers with `Deprecation` / `Sunset` headers, the SDK emits one `DeprecationWarning` per operation per
process, naming the sunset date and the successor.

### pandas

```python
tm.tasks.list(org_id="O0020").to_dataframe()             # every page; to_dataframe(all_pages=False) for one
tm.views.rows("V123456").to_dataframe()
```

One row per item, with the API's own field names:

- a nested object becomes dotted columns (`type_data.severity`);
- a list of scalars becomes one comma-separated string (`tags` → `"api, backend"`);
- `*_at` columns are timezone-aware datetimes, `*_date` columns `datetime.date` (missing → `None`).

Needs the `pandas` extra — without it you get an `ImportError` saying so.

### Webhooks

```python
from tasksmate import webhooks

def receive(headers, raw_body: bytes):
    if not webhooks.verify(SECRET, headers, raw_body):     # the RAW body, not re-serialized JSON
        return 400
    event = webhooks.parse(raw_body)                         # WebhookEvent: .id .type_ .org_id .data.resource_id …
    ...                                                      # dedupe on event.id — delivery is at-least-once
    return 200
```

`verify` implements the Standard Webhooks recipe TasksMate signs with:

- **Signature:** `v1,` HMAC-SHA256 over `id.timestamp.body`, keyed by the base64-decoded part of the `whsec_…` secret.
- **Replay window:** timestamps more than `tolerance` seconds (300) away are refused.
- **Rotation, both ways:** during the 24 h after a secret rotation TasksMate sends two signatures, and you may pass
  both secrets — `verify([new, old], …)` — while you switch over.
- **Errors:** `raise_on_failure=True` raises `WebhookVerificationError` with the reason instead of returning `False`.

### Logging

The SDK logs to the `tasksmate` logger at DEBUG: one line per request (method, path, status, time, attempt,
`request_id`). It never logs the token, and never logs headers.

## The command line

```bash
tm auth login                                   # asks for the token (hidden), checks it, stores it
tm me
tm tasks list --org O0020 --status in_progress --status blocked
tm tasks get T123456 --json
tm tasks create --org O0020 --title "Ship the SDK" --project P96441 --due 2026-10-01
tm tasks update T123456 --status completed      # reads the ETag first: a concurrent change is a 412, not an overwrite
tm projects list --org O0020
tm views rows V123456 --csv > rows.csv
tm webhooks list --org O0020 · tm webhooks test WH123456 · tm webhooks deliveries WH123456
tm tokens list --org O0020
tm --version
```

- **Output:** a table by default, `--json` for raw objects.
- **Organization:** `--org` falls back to `TASKSMATE_ORG`, or to your organization when you have exactly one.
- **Token:** from `TASKSMATE_TOKEN`, else the OS keyring, else `~/.config/tasksmate/config.toml` (mode 600, written
  only when no keyring is available or with `--no-keyring`); `tm` only ever prints its 12-character prefix.
- **Exit codes:** **0** success, **1** an API or connection error (the problem is printed with its `request_id`),
  **2** a usage error.

## Streamlit example

[`examples/streamlit_dashboard`](examples/streamlit_dashboard/README.md) — an organization dashboard (tasks, charts,
project drill-down, my open tasks) that needs nothing but `TASKSMATE_TOKEN`.

## MCP server for local clients (`packages/`)

Two more packages live in this repo — the same thing in two languages, for MCP clients that start a **local process**
instead of calling a URL:

| | Run | Source |
|---|---|---|
| `tasksmate-mcp` (PyPI) | `uvx tasksmate-mcp` | [`packages/tasksmate-mcp`](packages/tasksmate-mcp/README.md) |
| `@tasksmate/mcp` (npm) | `npx -y @tasksmate/mcp` | [`packages/mcp-node`](packages/mcp-node/README.md) |

Both are **proxies** to TasksMate's remote MCP server (`<api>/mcp`), not a second server: stdio in, Streamable HTTP out,
with `Authorization: Bearer $TASKSMATE_TOKEN` — so they expose exactly the remote server's tools, and its read-only
and tool-group enforcement and audit trail apply. Configuration (identical in both; flags win):

| Variable | Flag | |
|---|---|---|
| `TASKSMATE_TOKEN` | — | required: an access token from **Developers → Tokens** |
| `TASKSMATE_API_URL` | `--api-url` | the API's origin; default production (`/mcp` is added) |
| `TASKSMATE_MCP_READONLY` | `--readonly` | `1` → `?readonly=1` (only read tools, enforced by the server) |
| `TASKSMATE_MCP_GROUPS` | `--groups` | `tasks,projects` → `?groups=…` (default: all but `admin`) |

```json
{ "mcpServers": { "tasksmate": { "command": "uvx", "args": ["tasksmate-mcp"], "env": { "TASKSMATE_TOKEN": "tm_live_…" } } } }
```

`TASKSMATE_*`, not `…_TM`: these are the packages' (and `tm`'s) variables; the `_TM` suffix is the API server's own
convention. Clients that can add a remote server by URL should use the URL instead (OAuth, no token) — TasksMate's
**Developers → MCP** tab writes the right artefact for each client. **Not published yet** (npm and PyPI wait for the
stability gate, S.23); `release.yml` builds and verifies both with the SDK.

## How it is built

- [`spec/openapi.public.json`](spec/SOURCE.md) — a committed snapshot of the API's public contract; the **only** input.
- `python scripts/generate.py` regenerates `src/tasksmate/_generated/` ([openapi-python-client](https://github.com/openapi-generators/openapi-python-client)
  0.29.1), the facade's operation table and methods (`_operations.py`, `resources.py`) and `docs/api/`. It is
  idempotent; CI runs it and fails on any difference, so a spec change and its code are always reviewed together.
  Nothing under `_generated/` is edited by hand.
- The hand-written layer: `_core.py` (requests, retries, errors, ETags), `pagination.py`, `errors.py`,
  `dataframe.py`, `webhooks.py`, `cli/`.
- `tasksmate._generated` stays importable as a low-level client, but it is private: its names may change between
  `0.x` releases.

```bash
pip install -e ".[dev]"                 # Python 3.11+ to regenerate (the SDK itself runs on 3.10+)
python scripts/generate.py && git diff --stat
pytest && mypy && ruff check . && ruff format --check .
```

## Versioning

`0.x` releases are pre-releases: any release may change anything, and each is tagged `v0.x.y` and published to
TestPyPI only. The first PyPI release waits for TasksMate's stability gate; from 1.0 on, the SDK follows semver and
`tasksmate.API_VERSION` names the API date it was generated from (sent as `TasksMate-Version`).

0.x: the `roadmap` resource was removed before release (5.7) — TasksMate did not ship the Roadmap. Milestones are the
way to track dated commitments; since 5.9 they belong to a project (`tm.milestones.list(project_id)`, `list_org` for
every project at once) — the team-scoped milestone methods were replaced before release.

## Security

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately; never paste a live token into an issue.

Contributors: `pre-commit install` (after `pip install pre-commit`) enables the gitleaks check from
`.pre-commit-config.yaml` on each commit. CI runs the same scan (the `secrets` job). Nothing installs the hook for you.

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). The licence grants no right to use the TasksMate or Indrasol names or marks (§6).
