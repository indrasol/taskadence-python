# taskadence: the TasKadence API for Python

The official Python SDK for [TasKadence](https://taskadence.com). A typed client generated from the public OpenAPI
contract, so it cannot drift from the API, with a small hand-written layer for pagination, retries, typed errors,
ETags, idempotency and pandas. It also ships the `tm` command line.

> **`0.x` is a pre-release.** Any `0.x` release may change anything. Pin an exact version and read the
> [changelog](https://github.com/indrasol/taskadence-python/blob/main/CHANGELOG.md) before upgrading.

**Documentation:** [docs.taskadence.com](https://docs.taskadence.com) ·
**Source:** [github.com/indrasol/taskadence-python](https://github.com/indrasol/taskadence-python) ·
**Issues:** [GitHub issues](https://github.com/indrasol/taskadence-python/issues)

## Install

```bash
pip install taskadence                  # the client (Python 3.10+)
pip install "taskadence[cli]"           # + the `tm` command line
pip install "taskadence[pandas]"        # + DataFrames
```

For AI assistants, the TasKadence MCP server runs locally with either of:

```bash
uvx taskadence-mcp                      # Python
npx -y @taskadence/mcp                  # Node 20+
```

## Quick start

```python
from taskadence import Taskadence

tm = Taskadence()                                       # reads TASKADENCE_TOKEN
org_id = tm.me().organizations[0].org_id                # a token belongs to one organization
for task in tm.tasks.list(org_id=org_id, filter={"status": ["in_progress"]}):
    print(task.task_id, task.title)
```

Or from the shell: `tm auth login`, then `tm tasks list --status in_progress`.

## Authentication

- **Personal access token:** in TasKadence, open **Settings > Developers** and create a token. It is shown once.
  Pass it as `Taskadence(token="tkd_live_…")` or set `TASKADENCE_TOKEN`. `TASKADENCE_API_URL` changes the server
  (default `https://api.taskadence.com`).
- **Scopes:** a token belongs to one organization and carries scopes (`tasks:read`, `tasks:write`,
  `projects:read`, …). Each method's docstring names the scope it needs. A `tkd_test_…` token is read-only.
- **MCP over OAuth needs no token:** if your AI client can add a remote MCP server by URL (Claude, Claude Code, Cursor,
  VS Code, …), connect it by URL and sign in with OAuth. See [Connect](https://docs.taskadence.com/mcp/connect/).
  The local packages (`uvx taskadence-mcp`, `npx -y @taskadence/mcp`) are for clients that only start a process.
- **OAuth apps:** the authorization flow (`/oauth/authorize`, `/oauth/token`, `/.well-known/*`) is not wrapped here.
  Run it with any OAuth 2.1 library; the access token it returns works like any other: `Taskadence(token=…)`.

## The client

`tm.<resource>.<verb>(…)` exists for every public operation of the API (all but the OAuth authorization-flow routes),
named after its `operationId`: `tasks.create`, `tasks.list`, `tasks.read` (alias `get`), `tasks.update` (PATCH),
`tasks.replace` (PUT), `tasks.delete`, `tasks.set_project` (alias `move`), `projects.list`, `views.rows`,
`webhooks.test`, … The full list is in the
[API reference](https://github.com/indrasol/taskadence-python/blob/main/docs/api/README.md).

```python
from taskadence import Taskadence
from taskadence.models import TaskCreate, TaskUpdate

tm = Taskadence()
me = tm.me()                                          # who the token acts as: me.principal, me.organizations
task = tm.tasks.create(TaskCreate(org_id="O0020", title="Ship the SDK", priority="high"))
task = tm.tasks.create({"org_id": "O0020", "title": "Ship the SDK"})   # a plain dict works too
tm.tasks.update(task.task_id, TaskUpdate(status="in_progress"))       # sends ONLY the fields you set
tm.tasks.update(task.task_id, {"due_date": None})                     # null clears a field (JSON merge-patch)
```

Every response is a typed model (`taskadence.models`, `attrs` classes with `to_dict()` / `from_dict()`).
Configuration: `Taskadence(token=None, base_url=None, *, timeout=30, max_retries=3, api_version=None,
max_retry_after=60, headers=None, http_client=None)`. Use it as a context manager or call `tm.close()`.
`AsyncTaskadence` has the same namespaces with `await`:

```python
import asyncio
from taskadence import AsyncTaskadence

async def main() -> None:
    async with AsyncTaskadence() as tm:
        async for task in await tm.tasks.list(org_id="O0020", filter={"status": ["blocked"]}):
            print(task.task_id)

asyncio.run(main())
```

### Lists and pagination

Every list returns a `Page`: `.data` (this page), `.next_cursor`, and iteration over every item, following the cursor
until it is `None`. A page may be short, or even empty, while more follow; iteration handles it.

```python
page = tm.tasks.list(org_id="O0020", filter={"status": ["in_progress", "blocked"], "search": "invoice"},
                     sort_by="due_date", limit=200)
page.data, page.next_cursor          # the first page
for task in page: ...                # all of them
for p in page.pages(): ...           # page by page
page.envelope                        # the full response model (some lists carry sums beside `data`)
```

`filter={key: value}` becomes `filter[key]=value` (a list is comma-joined). An unknown key raises `ValueError` naming
the allowed ones.

### Errors

Every API error is `application/problem+json`, and every problem type is its own exception. All are subclasses of
`taskadence.TaskadenceError` (itself an `APIError`) with `.status`, `.type`, `.title`, `.detail`, `.request_id` and
`.errors`:

```python
from taskadence import InsufficientScopeError, NotFoundError, TaskadenceError

try:
    tm.tasks.update("T123456", {"status": "completed"})
except InsufficientScopeError as exc:
    print("this token needs", exc.required_scope)          # e.g. tasks:write
except NotFoundError:
    ...
except TaskadenceError as exc:
    print(exc.status, exc.detail, "request_id:", exc.request_id)
```

| Status | Exceptions |
|---|---|
| 400 | `BadRequestError` · `InvalidParameterError` · `IdempotencyKeyInvalidError` |
| 401 | `AuthenticationError` · `TokenInvalidError` · `TokenExpiredError` · `TokenRevokedError` |
| 403 | `ForbiddenError` · `InsufficientScopeError` · `TestTokenReadOnlyError` · `TokenPolicyError` (also 422) |
| 404 · 409 · 412 | `NotFoundError` · `ConflictError` (`IdempotencyKeyInFlightError`) · `PreconditionFailedError` |
| 422 | `UnprocessableEntityError` · `ValidationError` (`InvalidValueError`) · `IdempotencyKeyReusedError` · `UrlRefusedError` |
| 429 · 5xx | `RateLimitedError` (`.retry_after`) · `InternalError` |
| none | `APIConnectionError` / `APITimeoutError` (no HTTP answer) · `ResponseValidationError` (a 2xx this SDK version cannot read: upgrade) |

### Retries

Safe requests are retried up to `max_retries` times (default 3) on 429 (waiting what `Retry-After` says), 502 / 503 /
504 and connection failures, with exponential backoff and jitter. Safe means: GET, HEAD, DELETE, PUT; PATCH only with
`if_match`; POST only with an `Idempotency-Key`. A `Retry-After` longer than `max_retry_after` seconds (default 60) is
not waited out: the `RateLimitedError` is raised at once.

### Idempotent creates

Every create operation sends an `Idempotency-Key` (a fresh uuid4 per call, reused by that call's retries), so a retried
create never makes two. Pass your own with `idempotency_key="…"` (the API replays the first answer for 24 h), or
`idempotency_key=None` for none (and no retries).

### ETags and conditional requests

A model read by a single GET carries `.etag` (it is never serialized):

```python
from taskadence import NotModified

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

One row per item, with the API's own field names: a nested object becomes dotted columns (`type_data.severity`), a
list of scalars becomes one comma-separated string, `*_at` columns are timezone-aware datetimes and `*_date` columns
`datetime.date`. Needs the `pandas` extra; without it you get an `ImportError` saying so.

### Webhooks

```python
from taskadence import webhooks

def receive(headers, raw_body: bytes):
    if not webhooks.verify(SECRET, headers, raw_body):     # the RAW body, not re-serialized JSON
        return 400
    event = webhooks.parse(raw_body)                         # WebhookEvent: .id .type_ .org_id .data.resource_id …
    ...                                                      # dedupe on event.id: delivery is at-least-once
    return 200
```

`verify` implements the Standard Webhooks recipe TasKadence signs with: a `v1,` HMAC-SHA256 signature over
`id.timestamp.body`, a replay window (`tolerance`, 300 s), and secret rotation (pass both secrets,
`verify([new, old], …)`, during the 24 h after a rotation). `raise_on_failure=True` raises `WebhookVerificationError`
with the reason instead of returning `False`.

### Logging

The SDK logs to the `taskadence` logger at DEBUG: one line per request (method, path, status, time, attempt,
`request_id`). It never logs the token, and never logs headers.

## The command line

```bash
pip install "taskadence[cli]"
tm auth login                                   # asks for the token (hidden), checks it, stores it
tm me
tm tasks list --status in_progress --status blocked
tm tasks get T123456 --json
tm tasks create --title "Ship the SDK" --project P96441 --due 2026-10-01
tm tasks update T123456 --status completed      # reads the ETag first: a concurrent change is a 412, not an overwrite
tm projects list
tm views rows V123456 --csv > rows.csv
tm webhooks list · tm webhooks test WH123456 · tm webhooks deliveries WH123456
tm tokens list
tm storage
tm --version
```

- **Output:** a table by default, `--json` for raw objects.
- **Organization:** `--org` falls back to `TASKADENCE_ORG`, or to your organization when you have exactly one.
- **Token:** from `TASKADENCE_TOKEN`, else the OS keyring, else `~/.config/taskadence/config.toml` (mode 600, written
  only when no keyring is available or with `--no-keyring`). `tm` only ever prints its 12-character prefix.
- **Names:** `tm` and `taskadence` are the same command.
- **Exit codes:** 0 success, 1 an API or connection error (printed with its `request_id`), 2 a usage error.

## MCP server for local clients

Two more packages are built from this repository, the same thing in two languages, for MCP clients that start a
**local process** instead of calling a URL:

| Package | Run | Read more |
|---|---|---|
| `taskadence-mcp` (PyPI) | `uvx taskadence-mcp` | [packages/taskadence-mcp](https://github.com/indrasol/taskadence-python/tree/main/packages/taskadence-mcp) |
| `@taskadence/mcp` (npm) | `npx -y @taskadence/mcp` | [packages/mcp-node](https://github.com/indrasol/taskadence-python/tree/main/packages/mcp-node) |

Both are proxies to the TasKadence remote MCP server, not a second server, so they expose exactly the remote server's
tools, and its read-only and tool-group enforcement and audit trail apply. They read `TASKADENCE_TOKEN` (required),
`TASKADENCE_API_URL`, `TASKADENCE_MCP_READONLY` and `TASKADENCE_MCP_GROUPS`.

```json
{ "mcpServers": { "taskadence": { "command": "uvx", "args": ["taskadence-mcp"], "env": { "TASKADENCE_TOKEN": "tkd_live_…" } } } }
```

## Examples

- [`examples/quickstart.py`](https://github.com/indrasol/taskadence-python/blob/main/examples/quickstart.py): a full
  round trip (create, conditional update, filtered list, DataFrame, delete) that leaves nothing behind.
- [`examples/streamlit_dashboard`](https://github.com/indrasol/taskadence-python/tree/main/examples/streamlit_dashboard):
  an organization dashboard that needs nothing but `TASKADENCE_TOKEN`.

## Versioning

`0.x` releases are pre-releases: any release may change anything. From 1.0 on, the SDK follows semver.
`taskadence.API_VERSION` names the API date the SDK was generated from (sent as the `Taskadence-Version` header).

## Support and security

- Questions and bugs: [GitHub issues](https://github.com/indrasol/taskadence-python/issues). Please never paste a live
  token; a prefix (`tkd_live_ab12…`) is enough.
- Vulnerabilities: report them privately, as described in
  [SECURITY.md](https://github.com/indrasol/taskadence-python/blob/main/SECURITY.md) (GitHub private vulnerability
  reporting, or srvcs.infra@indrasol.com).
- Contributing: see [CONTRIBUTING.md](https://github.com/indrasol/taskadence-python/blob/main/CONTRIBUTING.md).

## License

Apache License 2.0. See [LICENSE](https://github.com/indrasol/taskadence-python/blob/main/LICENSE) and
[NOTICE](https://github.com/indrasol/taskadence-python/blob/main/NOTICE). The license grants no right to use the
TasKadence or Indrasol names or marks.
