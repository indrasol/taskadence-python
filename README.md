# taskadence: the TasKadence API for Python

[![PyPI version](https://img.shields.io/pypi/v/taskadence)](https://pypi.org/project/taskadence/)
[![Python versions](https://img.shields.io/pypi/pyversions/taskadence)](https://pypi.org/project/taskadence/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/indrasol/taskadence-python/blob/main/LICENSE)

[TasKadence](https://taskadence.com) is task and project management for teams. This package lets your Python code
read and change your organization's tasks, projects and teams, and it adds `tm`, a command line for the same things.

> **Stable since 1.0.** The SDK follows [semantic versioning](https://semver.org/) and the API's
> [versioning policy](https://docs.taskadence.com/guides/versioning/): no breaking change within `1.x`. Read the
> [changelog](https://github.com/indrasol/taskadence-python/blob/main/CHANGELOG.md) before upgrading.

**Documentation:** [docs.taskadence.com](https://docs.taskadence.com/sdks/python/) ·
**Source:** [github.com/indrasol/taskadence-python](https://github.com/indrasol/taskadence-python) ·
**Issues:** [GitHub issues](https://github.com/indrasol/taskadence-python/issues)

## Get started in 3 steps

You need Python 3.10 or later and a TasKadence account. This takes about five minutes.

### 1. Get a token

A token is a password for programs: it lets this package act for you in one organization.

1. In TasKadence, open **Developers** in the sidebar, stay on the **Tokens** tab and click **Create token**.
2. Give it a name you will recognise later (for example "My laptop").
3. Under **Scopes**, tick what the token may do:
   - **To read** (enough for this guide): **Read** on the **Tasks** row. Add **Read** on **Projects** and **Teams** if
     you will read those too.
   - **To create and change things:** **Write** on the same rows. Write includes Read.
4. Click **Create token** and copy it (it starts with `tkd_live_`). **It is shown once.** If you lose it, create a
   new one and revoke the old one.

### 2. Install

```bash
pip install taskadence            # the Python client
pip install "taskadence[cli]"     # the client plus the `tm` command line
```

### 3. Make your first call

Put the token in the `TASKADENCE_TOKEN` environment variable, in the terminal you will run Python from.

macOS or Linux:

```bash
export TASKADENCE_TOKEN="tkd_live_paste_your_token_here"
```

Windows PowerShell:

```powershell
$env:TASKADENCE_TOKEN = "tkd_live_paste_your_token_here"
```

Save this as `hello.py` and run `python hello.py`:

```python
from taskadence import Taskadence

tm = Taskadence()                                   # reads TASKADENCE_TOKEN from the environment
org = tm.me().organizations[0]                      # the organization your token belongs to
print(f"Organization: {org.name} ({org.org_id})")
for task in tm.tasks.list(org_id=org.org_id, limit=5).data:   # your first 5 tasks
    print(task.task_id, task.status, task.title)
```

You should see your organization, then up to five tasks (yours will have different names and ids):

```text
Organization: Acme Inc (O123456)
T123456 in_progress Write the launch announcement
T123457 not_started Book the venue
T123458 completed Draft the budget
```

No tasks yet? Only the first line prints. Create one in the app, or see Create and change tasks below.

The same with the command line (it reads the same `TASKADENCE_TOKEN`):

```bash
tm me
tm tasks list --limit 5
```

```text
ada (user) <ada@example.com>
                   Organizations
┏━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ org_id  ┃ name     ┃ role  ┃ designation         ┃
┡━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ O123456 │ Acme Inc │ owner │ Engineering Manager │
└─────────┴──────────┴───────┴─────────────────────┘
1 row
```

`tm tasks list` prints a table of `task_id`, `title`, `status`, `priority`, `assignee`, `due_date` and `project_id`.
Prefer not to keep the token in an environment variable? `tm auth login` asks for it once and stores it in your
operating system's keyring.

Something went wrong? See Troubleshooting near the end of this page.

## Key ideas

Four things that make the rest of this page easier to read.

- **Organization.** Everything in TasKadence (tasks, projects, teams) belongs to an organization, your company's
  workspace. Most calls need its id, `org_id`. A token works in exactly one organization.
- **Token and scopes.** The token proves who you are; its scopes say what it may do. `tasks:read` reads tasks,
  `tasks:write` also creates and changes them, and the same pattern holds for `projects`, `teams` and `webhooks`.
  A call your token's scopes do not cover fails with a clear error naming the scope it needs. Each method's
  docstring names its scope too. A test token (`tkd_test_…`) can only read. Scopes are fixed when the token is
  created: to add one, create a new token. All scopes are listed in
  [Authentication](https://docs.taskadence.com/guides/authentication/).
- **IDs.** Every object has a short id with a letter in front: tasks `T123456`, projects `P123456`, organizations
  `O123456`, saved views `V123456`, webhooks `WH123456`. Find them with `tm.me()` (your organization), with any
  list (`tm.tasks.list(...)`, `tm tasks list`, `tm projects list`), or in the app's address bar: a task's page is
  `https://taskadence.com/tasks/T123456`, and `org_id=O123456` in the address names the organization.
- **Versions.** The SDK follows [semantic versioning](https://semver.org/) and the API's
  [versioning policy](https://docs.taskadence.com/guides/versioning/): a `1.x` release never breaks your code,
  and anything deprecated warns first. Pin a major version if you like (`pip install "taskadence>=1,<2"`).

## Using the client

Every snippet below runs as it is after step 3. They start the same way: make a client and look up your
organization's id.

### Create and change tasks

You create, read, change and delete tasks with `tm.tasks`; every other kind of object works the same way.

```python
import datetime as dt

from taskadence import Taskadence
from taskadence.models import TaskCreate, TaskUpdate

tm = Taskadence()
org_id = tm.me().organizations[0].org_id

task = tm.tasks.create(TaskCreate(org_id=org_id, title="Try the TasKadence SDK", priority="high",
                                  due_date=dt.date(2027, 1, 15)))
print("created", task.task_id)
tm.tasks.update(task.task_id, TaskUpdate(status="in_progress"))   # changes only the fields you set
tm.tasks.update(task.task_id, {"due_date": None})                 # None clears a field; a plain dict works too
print(tm.tasks.get(task.task_id).status)                          # in_progress
tm.tasks.delete(task.task_id)                                     # tidy up
```

Needs `tasks:write`. `update` sends only the fields you pass and leaves the others alone (the API calls this a JSON
merge-patch). `tm.tasks.replace` (PUT) replaces the whole task instead.

There is a method for every public operation of the API, named `tm.<resource>.<verb>`: `tasks.create`, `tasks.list`,
`tasks.get` (also `read`), `tasks.update`, `tasks.replace`, `tasks.delete`, `tasks.move` (also `set_project`),
`projects.list`, `views.rows`, `webhooks.test`, and so on. The full list is in the
[API reference](https://github.com/indrasol/taskadence-python/blob/main/docs/api/README.md). Every answer is a typed
model from `taskadence.models` with `to_dict()` and `from_dict()`.

### Lists and pagination

A list can be long, so the API sends it in pages; looping over the result fetches every page for you.

```python
from taskadence import Taskadence

tm = Taskadence()
org_id = tm.me().organizations[0].org_id

page = tm.tasks.list(org_id=org_id, filter={"status": ["in_progress", "blocked"]}, sort_by="due_date", limit=100)
print(len(page.data), "on the first page; more follow:", page.next_cursor is not None)
for task in page:                    # every matching task, page after page
    print(task.task_id, task.title)
for p in page.pages():               # or page by page
    print(len(p.data))
```

`filter={key: value}` narrows the list (a list of values means "any of these"); an unknown key raises `ValueError`
naming the allowed ones. A page may be short, or even empty, while more follow; the loop handles it. `page.envelope`
is the full answer, for the lists that carry totals beside `data`.

### Errors

When the API says no, you get an exception that says why, with the `request_id` support needs to find it.

```python
from taskadence import InsufficientScopeError, NotFoundError, Taskadence, TaskadenceError

tm = Taskadence()

try:
    tm.tasks.get("T000000")                             # an id that does not exist
except NotFoundError as exc:
    print("not found:", exc.detail)
except InsufficientScopeError as exc:
    print("this token needs", exc.required_scope)       # for example tasks:read
except TaskadenceError as exc:                          # every other API error
    print(exc.status, exc.detail, "request_id:", exc.request_id)
```

Every error is a subclass of `taskadence.TaskadenceError` with `.status`, `.type`, `.title`, `.detail`, `.request_id`
and `.errors`:

| Status | Exceptions |
|---|---|
| 400 | `BadRequestError` · `InvalidParameterError` · `IdempotencyKeyInvalidError` |
| 401 | `AuthenticationError` · `TokenInvalidError` · `TokenExpiredError` · `TokenRevokedError` |
| 403 | `ForbiddenError` · `InsufficientScopeError` · `TestTokenReadOnlyError` · `TokenPolicyError` (also 422) |
| 404 · 409 · 412 | `NotFoundError` · `ConflictError` (`IdempotencyKeyInFlightError`) · `PreconditionFailedError` |
| 422 | `UnprocessableEntityError` · `ValidationError` (`InvalidValueError`) · `IdempotencyKeyReusedError` · `UrlRefusedError` |
| 429 · 5xx | `RateLimitedError` (`.retry_after`) · `InternalError` |
| none | `APIConnectionError` / `APITimeoutError` (no answer from the server) · `ResponseValidationError` (an answer this SDK version cannot read: upgrade) |

The API sends every error as `application/problem+json`; see
[Errors](https://docs.taskadence.com/guides/errors/) for each `type`.

### Uploading files

Attach files to tasks and projects: up to 100 MB each, sent straight to storage, with a progress callback if you
want one.

```python
from pathlib import Path

from taskadence import Taskadence

tm = Taskadence()
org_id = tm.me().organizations[0].org_id

Path("notes.txt").write_text("Hello from the SDK\n")
task = tm.tasks.create({"org_id": org_id, "title": "Has an attachment"})
tm.task_attachments.create(task_id=task.task_id, file="notes.txt", title="Notes",   # a path, bytes or an open file
                           progress=lambda sent, total: print(f"{sent * 100 // total}%"))
print(len(tm.task_attachments.list(task_id=task.task_id).data), "attachment")
tm.tasks.delete(task.task_id)
```

Needs `tasks:write`. `tm.project_resources.upload(project_id=..., file=...)` does the same for a project (with
`projects:write`). How uploads work: [Uploading files](https://github.com/indrasol/taskadence-python/blob/main/docs/uploading-files.md).

### pandas

Turn any list into a pandas DataFrame, one row per item, for analysis or a CSV. Needs `pip install "taskadence[pandas]"`.

```python
from taskadence import Taskadence

tm = Taskadence()
org_id = tm.me().organizations[0].org_id

frame = tm.tasks.list(org_id=org_id).to_dataframe()   # every page; to_dataframe(all_pages=False) for one
print(frame[["task_id", "title", "status"]].head())
```

Columns keep the API's field names: a nested object becomes dotted columns (`type_data.severity`), a list becomes one
comma-separated string, `*_at` columns are timezone-aware datetimes and `*_date` columns are dates. A saved view
works the same way: `tm.views.rows("V123456").to_dataframe()`. Without the extra installed you get an `ImportError`
saying so.

### Async

For asyncio code, `AsyncTaskadence` has the same methods; you `await` them.

```python
import asyncio

from taskadence import AsyncTaskadence


async def main() -> None:
    async with AsyncTaskadence() as tm:
        org_id = (await tm.me()).organizations[0].org_id
        async for task in await tm.tasks.list(org_id=org_id, filter={"status": ["blocked"]}):
            print(task.task_id, task.title)


asyncio.run(main())
```

### Webhooks

A webhook is TasKadence calling your server when something changes (a task is created, a comment is added). These
two functions check that a call really came from TasKadence and read it.

```python
from taskadence import webhooks

SECRET = "whsec_your_webhook_secret"     # shown when you create the webhook


def receive(headers, raw_body: bytes) -> int:
    """Call this from your web framework's handler with the request's headers and its raw body."""
    if not webhooks.verify(SECRET, headers, raw_body):   # the RAW body, not re-serialized JSON
        return 400
    event = webhooks.parse(raw_body)                      # .id .type_ .org_id .data.resource_id …
    print(event.type_, event.data.resource_id)            # deliveries can repeat: skip an event.id you have seen
    return 200
```

`verify` checks the signature (HMAC-SHA256 over `id.timestamp.body`, the Standard Webhooks scheme), refuses a call
older than 5 minutes (`tolerance`, in seconds), and accepts two secrets during the 24 hours after you rotate one
(`verify([new, old], ...)`). `raise_on_failure=True` raises `WebhookVerificationError` with the reason instead of
returning `False`. Events and payloads: [Webhooks](https://docs.taskadence.com/guides/webhooks/).

## The command line

`tm` does the everyday things from a terminal. Install it with `pip install "taskadence[cli]"`.

```bash
tm auth login                     # asks for the token (hidden), checks it, stores it
tm me                             # who you are, and your organization
tm tasks list --status in_progress --status blocked
tm tasks create --title "Try the TasKadence CLI" --due 2027-01-15
tm projects list
tm storage                        # how much file storage your organization uses
tm --version
```

Commands that take an id use `T123456`, `P123456`, `V123456` and `WH123456` below as placeholders: copy a real one
from `tm tasks list`, `tm projects list`, `tm webhooks list` or the app's address bar.

```bash
tm tasks get T123456 --json
tm tasks update T123456 --status completed       # refuses to overwrite a change someone made since you read it
tm tasks attach T123456 ./report.pdf --title "Q3 report"   # straight to storage, with a progress bar
tm projects upload P123456 ./plan.xlsx
tm views rows V123456 --csv > rows.csv
tm webhooks test WH123456
tm webhooks deliveries WH123456
tm tokens list
```

- **Output:** a table by default, `--json` for the raw objects.
- **Organization:** `--org` falls back to `TASKADENCE_ORG`, then to your organization when you have exactly one.
- **Token:** from `TASKADENCE_TOKEN`, else the OS keyring, else `~/.config/taskadence/config.toml` (mode 600, written
  only when no keyring is available or with `--no-keyring`). `tm` only ever prints the token's first 12 characters.
- **Names:** `tm` and `taskadence` are the same command.
- **Exit codes:** 0 success, 1 an API or connection error (printed with its `request_id`), 2 a usage error.

## AI assistants (MCP)

To let an AI assistant (Claude, Cursor, VS Code and others) work with your tasks, connect it to the TasKadence MCP
server. If your assistant can add a server by URL, do that: it signs in with OAuth and needs no token. See
[Connect](https://docs.taskadence.com/mcp/connect/).

For assistants that can only start a local program, two small packages from this repository do the job, the same
thing in two languages:

| Package | Run | Set-up guide |
|---|---|---|
| `taskadence-mcp` (PyPI) | `uvx taskadence-mcp` | [packages/taskadence-mcp](https://github.com/indrasol/taskadence-python/tree/main/packages/taskadence-mcp) |
| `@taskadence/mcp` (npm) | `npx -y @taskadence/mcp` | [packages/mcp-node](https://github.com/indrasol/taskadence-python/tree/main/packages/mcp-node) |

## Advanced

Most people never need this section. It explains what the SDK already does for you and how to tune it.

### Configuration

`Taskadence(token=None, base_url=None, *, timeout=30, max_retries=3, api_version=None, max_retry_after=60,
headers=None, http_client=None)`. With no `token`, it reads `TASKADENCE_TOKEN`; with no `base_url`, it reads
`TASKADENCE_API_URL` (default `https://api.taskadence.com`). Use it as a context manager (`with Taskadence() as tm:`)
or call `tm.close()` when you are done.

### Retries

What this means for you: a brief network blip, or the API asking you to slow down, does not crash your script. The
SDK waits and tries again, when trying again is safe.

It retries up to `max_retries` times (default 3) on 429 (waiting as long as `Retry-After` says), 502, 503, 504 and
connection failures, waiting a little longer each time (exponential backoff with jitter). Safe means: GET, HEAD,
DELETE and PUT; PATCH only with `if_match`; POST only with an `Idempotency-Key`. A `Retry-After` longer than
`max_retry_after` seconds (default 60) is not waited out: the `RateLimitedError` is raised at once.

### Idempotent creates

What this means for you: if the connection drops while you create something, the retry does not create a second copy.

Every create sends an `Idempotency-Key` (a fresh random id per call, reused by that call's retries), so the API
recognises a repeat. Pass your own with `idempotency_key="..."` (the API replays the first answer for 24 hours), or
`idempotency_key=None` for none (and then no retries).

### ETags and conditional requests

What this means for you: you can say "save my change only if nobody changed this since I read it", so you never
overwrite a teammate's edit by accident, and you can check cheaply whether something changed.

A model read by a single GET carries `.etag`, a fingerprint of that version:

```python
from taskadence import NotModified, PreconditionFailedError, Taskadence

tm = Taskadence()
org_id = tm.me().organizations[0].org_id

task = tm.tasks.create({"org_id": org_id, "title": "ETag demo"})
read = tm.tasks.get(task.task_id)                        # read.etag: this version's fingerprint
tm.tasks.update(task.task_id, {"status": "in_progress"}, if_match=read.etag)   # saved: nothing changed since the read
try:
    tm.tasks.update(task.task_id, {"status": "blocked"}, if_match=read.etag)   # the old fingerprint: refused (412)
except PreconditionFailedError:
    print("it changed since we read it: read it again, then retry")
latest = tm.tasks.get(task.task_id)
print(tm.tasks.get(task.task_id, if_none_match=latest.etag) is NotModified)   # True (304): unchanged, no body sent
tm.tasks.delete(task.task_id)
```

### Deprecations

When the API marks an operation as going away (`Deprecation` and `Sunset` headers), the SDK emits one
`DeprecationWarning` per operation per process, naming the date and what replaces it. `taskadence.API_VERSION` names
the API version the SDK was built against (sent as the `Taskadence-Version` header).

### Logging

The SDK logs to the `taskadence` logger at DEBUG level: one line per request (method, path, status, time, attempt,
`request_id`). It never logs the token or any header. An upload URL is logged without its query string.

```python
import logging

logging.basicConfig()
logging.getLogger("taskadence").setLevel(logging.DEBUG)
```

### OAuth apps

If you are building an app that other TasKadence users sign in to, run the OAuth 2.1 authorization flow
(`/oauth/authorize`, `/oauth/token`) with any OAuth library; this SDK does not wrap it. The access token you get works
like any other: `Taskadence(token=...)`.

## Troubleshooting

Most problems are the token, its scopes or an id. Every error carries a `request_id`; keep it if you ask for help.

- **401 (`AuthenticationError`, `TokenInvalidError`, `TokenExpiredError`, `TokenRevokedError`):** the token is wrong,
  expired or revoked. Check that `TASKADENCE_TOKEN` is set in the same terminal you run Python from (`tm auth status`
  shows where `tm` finds it, and only its first 12 characters). If in doubt, create a new token in **Developers >
  Tokens**.
- **403 insufficient scope (`InsufficientScopeError`):** the token is valid but may not do this. `exc.required_scope`
  (and the error message) names the scope it needs, for example `tasks:write`. Scopes cannot be added to a token:
  create a new one with that scope ticked. A `tkd_test_…` token can never write (`TestTokenReadOnlyError`).
- **404 (`NotFoundError`):** the id is wrong, belongs to another organization than your token's, or is in a project
  you cannot see. Copy the id again from `tm tasks list` or the app's address bar.
- **`tm: command not found`:** install the extra, `pip install "taskadence[cli]"`, in the Python you are using.
- **Finding the `request_id`:** `exc.request_id` on any `TaskadenceError`; `tm` prints it with every error.
- **Still stuck?** Open a [GitHub issue](https://github.com/indrasol/taskadence-python/issues) with the `request_id`,
  the SDK version (`tm --version`) and what you ran. Never paste a live token; its first 12 characters are enough.

## Examples

- [`examples/quickstart.py`](https://github.com/indrasol/taskadence-python/blob/main/examples/quickstart.py): a full
  round trip (create, conditional update, filtered list, DataFrame, delete) that leaves nothing behind.
- [`examples/streamlit_dashboard`](https://github.com/indrasol/taskadence-python/tree/main/examples/streamlit_dashboard):
  an organization dashboard that needs nothing but `TASKADENCE_TOKEN`.

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
