"""`tm` (also installed as `taskadence`) — the Taskadence command line (`pip install "taskadence[cli]"`).

    tm auth login                      # prompts for a tkd_live_ token (hidden), verifies it, stores it
    tm me
    tm tasks list --org O0020 --status in_progress --table
    tm tasks create --org O0020 --title "Ship the SDK" --project P96441
    tm tasks update T123456 --status completed
    tm views rows V123456 --csv > rows.csv
    tm storage --org O0020             # the storage meter: used of 1 TB, status, by kind, top projects and files

Output: a table by default, `--json` for the raw API objects. Exit codes: 0 success; 1 an API or connection error (the
problem is printed with its `request_id`); 2 a usage error. The token is never printed — only its 12-character prefix.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import warnings
from collections.abc import Callable, Iterable, Sequence
from typing import Annotated, Any, TypeVar

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError as exc:  # pragma: no cover - the extra is not installed
    raise SystemExit('The tm CLI needs the cli extra: pip install "taskadence[cli]"') from exc

from .. import __version__, errors
from .._brand import BRAND_NAME, LEGACY_ENV_PREFIX, SLUG, getenv, is_access_token
from .._client import Taskadence
from .._core import ConfigurationError
from . import _config

app = typer.Typer(
    name="tm",
    help=f"The {BRAND_NAME} API from the command line.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
auth_app = typer.Typer(help="Store, check and remove your access token.", no_args_is_help=True)
tasks_app = typer.Typer(help="Tasks: list (the filter grammar), get, create, update.", no_args_is_help=True)
projects_app = typer.Typer(help="Projects.", no_args_is_help=True)
views_app = typer.Typer(help="Saved views.", no_args_is_help=True)
webhooks_app = typer.Typer(help="Webhooks (owner / admin).", no_args_is_help=True)
tokens_app = typer.Typer(help="Access tokens.", no_args_is_help=True)
for sub, name in (
    (auth_app, "auth"),
    (tasks_app, "tasks"),
    (projects_app, "projects"),
    (views_app, "views"),
    (webhooks_app, "webhooks"),
    (tokens_app, "tokens"),
):
    app.add_typer(sub, name=name)

out = Console(soft_wrap=False)
err = Console(stderr=True)
T = TypeVar("T")

JsonOpt = Annotated[bool, typer.Option("--json", help="Print the raw API objects as JSON.")]
TableOpt = Annotated[bool, typer.Option("--table", help="Print a table (the default).")]
OrgOpt = Annotated[
    str | None,
    typer.Option("--org", envvar="TASKADENCE_ORG", help="Organization id (default: yours, when you have exactly one)."),
]


class _State:
    api_url: str | None = None


state = _State()


def _version(value: bool) -> None:
    if value:
        out.print(f"{SLUG} {__version__}")
        raise typer.Exit()


@app.callback()
def main_options(
    api_url: Annotated[
        str | None,
        typer.Option("--api-url", help="API base URL (else TASKADENCE_API_URL, the saved one, or the SDK default)."),
    ] = None,
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    state.api_url = api_url


# ---------------------------------------------------------------------------
# plumbing
# ---------------------------------------------------------------------------


def _client() -> Taskadence:
    creds = _config.load(state.api_url)
    if not creds.token:
        err.print("[red]Not signed in.[/red] Run [bold]tm auth login[/bold] or set TASKADENCE_TOKEN.")
        raise typer.Exit(1)
    return Taskadence(token=creds.token, base_url=creds.api_url)


def _run(call: Callable[[Taskadence], T]) -> T:
    """Call the API; an API / connection / configuration error is printed and exits 1."""
    try:
        with _client() as tm:
            return call(tm)
    except errors.TaskadenceError as exc:
        err.print(f"[red]Error:[/red] {exc.status} {exc.title}: {exc.detail}")
        if exc.errors:
            err.print(f"  errors: {json.dumps(exc.errors, default=str)}")
        err.print(f"  type: {exc.type}   request_id: {exc.request_id or '-'}")
        raise typer.Exit(1) from None
    except (errors.APIError, ConfigurationError) as exc:
        err.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None


def _plain(item: Any) -> Any:
    return item.to_dict() if hasattr(item, "to_dict") else item


def _print_json(value: Any) -> None:
    if isinstance(value, list):
        value = [_plain(v) for v in value]
    out.print_json(json.dumps(_plain(value), default=str))


_TIMESTAMP = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})[\d:.]*(Z|[+-]00:00)$")


def _cell(value: Any) -> str:
    if value is None or type(value).__name__ == "Unset":
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    text = str(value)
    stamp = _TIMESTAMP.match(text)  # a UTC timestamp, to the minute: 2026-09-28 04:10Z
    return f"{stamp.group(1)} {stamp.group(2)}Z" if stamp else text


def _table(rows: Iterable[Any], columns: Sequence[str], title: str | None = None) -> None:
    table = Table(title=title, show_lines=False, header_style="bold")
    for column in columns:
        table.add_column(column, overflow="fold")
    count = 0
    for row in rows:
        data = _plain(row)
        table.add_row(*(_cell(data.get(c)) for c in columns))
        count += 1
    out.print(table)
    out.print(f"{count} row{'s' if count != 1 else ''}", style="dim")


def _resolve_org(tm: Taskadence, org: str | None) -> str:
    org = org or getenv("ORG")  # TASKADENCE_ORG comes via --org's envvar; this reads the pre-rename name
    if org:
        return org
    orgs = [o.org_id for o in tm.me().organizations or []]
    if len(orgs) == 1:
        return orgs[0]
    err.print(
        f"[red]--org is required[/red] (you belong to: {', '.join(orgs) or 'no organization'}; or set TASKADENCE_ORG)"
    )
    raise typer.Exit(2)


def _take(items: Iterable[T], limit: int | None) -> list[T]:
    taken: list[T] = []
    for item in items:
        if limit is not None and len(taken) >= limit:
            break
        taken.append(item)
    return taken


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


@auth_app.command("login")
def auth_login(
    token: Annotated[
        str | None, typer.Option("--token", help="The access token (prompted, hidden, when omitted).")
    ] = None,
    no_keyring: Annotated[
        bool, typer.Option("--no-keyring", help="Use the config file even if a keyring exists.")
    ] = False,
    no_verify: Annotated[bool, typer.Option("--no-verify", help="Store without calling GET /v1/me first.")] = False,
) -> None:
    """Store an access token (OS keyring, else ~/.config/taskadence/config.toml, mode 600). Never echoed."""
    value = token or typer.prompt("Access token (tkd_live_…)", hide_input=True)
    value = value.strip()
    if not is_access_token(value):  # tkd_live_ / tkd_test_, or a pre-rename tm_live_ / tm_test_ token
        err.print(f"[red]That is not a {BRAND_NAME} access token[/red] (they start with tkd_live_ or tkd_test_).")
        raise typer.Exit(2)
    if not no_verify:
        try:
            with Taskadence(token=value, base_url=_config.load(state.api_url).api_url) as tm:
                me = tm.me()
        except errors.TaskadenceError as exc:
            err.print(
                f"[red]The API refused this token:[/red] {exc.status} {exc.detail} (request_id {exc.request_id or '-'})"
            )
            raise typer.Exit(1) from None
        except errors.APIError as exc:
            err.print(f"[red]Could not reach the API:[/red] {exc}")
            raise typer.Exit(1) from None
        who = getattr(me.principal, "username", None) or getattr(me.principal, "id", "?")
        orgs = ", ".join(o.org_id for o in me.organizations or [])
        out.print(f"Token {_config.shown(value)} is valid: {who} ({orgs or 'no organization'})")
    where = _config.save(value, state.api_url, use_keyring=not no_keyring)
    out.print(f"Saved {_config.shown(value)} to {where}.")


@auth_app.command("logout")
def auth_logout() -> None:
    """Remove the stored token (keyring and config file)."""
    removed = _config.forget()
    out.print(f"Removed the token from {' and '.join(removed)}." if removed else "No stored token.")


@auth_app.command("status")
def auth_status() -> None:
    """Where the token comes from (its prefix only) and which API it talks to."""
    creds = _config.load(state.api_url)
    if not creds.token:
        out.print("Not signed in (no TASKADENCE_TOKEN, no stored token).")
        raise typer.Exit(1)
    source = {"env": "TASKADENCE_TOKEN", "keyring": "the OS keyring", "file": str(_config.config_path())}[creds.source]
    out.print(f"Token {_config.shown(creds.token)} from {source}")
    with Taskadence(token=creds.token, base_url=creds.api_url) as tm:
        out.print(f"API {tm.base_url} (API version {tm.api_version})")


# ---------------------------------------------------------------------------
# me
# ---------------------------------------------------------------------------


@app.command("me")
def me(json_: JsonOpt = False) -> None:
    """Who the token acts as, and its organizations."""
    result = _run(lambda tm: tm.me())
    if json_:
        _print_json(result)
        return
    principal = _plain(result.principal)
    out.print(
        f"[bold]{principal.get('username') or principal.get('id')}[/bold] ({principal.get('type')})"
        + (f" <{principal['email']}>" if principal.get("email") else "")
    )
    _table(result.organizations or [], ["org_id", "name", "role", "designation"], title="Organizations")


# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------


def _bytes(n: Any) -> str:
    """Decimal units, like the bill: 1 GB = 10^9 bytes."""
    value = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1000 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1000
    return f"{value:.2f} TB"  # pragma: no cover - the loop returns


@app.command("storage")
def storage(org: OrgOpt = None, json_: JsonOpt = False) -> None:
    """The organization's storage: used of the included 1 TB, the status, by kind, top projects, largest files."""
    result = _run(lambda tm: tm.organizations.storage(_resolve_org(tm, org)))
    if json_:
        _print_json(result)
        return
    data = _plain(result)
    status = str(data.get("status"))
    out.print(
        f"[bold]{_bytes(data.get('bytes_used'))}[/bold] of {_bytes(data.get('included_bytes'))} included "
        f"({data.get('percent')}%), {data.get('file_count')} files - status [bold]{status}[/bold]"
        + (" (internal org, not billed)" if data.get("billing_exempt") else "")
    )
    if status == "blocked":
        out.print("New uploads are paused until an owner or admin adds a payment method.", style="red")
    breakdown = data.get("breakdown") or {}
    kinds = breakdown.get("by_kind") or {}
    _table(
        [{"kind": k, "size": _bytes(kinds.get(k))} for k in ("task", "project", "bug")],
        ["kind", "size"],
        title="By kind",
    )
    if breakdown.get("by_project"):
        _table(
            [{**p, "size": _bytes(p.get("bytes"))} for p in breakdown["by_project"]],
            ["project_id", "name", "size"],
            title="Top projects",
        )
    if data.get("top_files"):
        _table(
            [{**f, "size": _bytes(f.get("bytes"))} for f in data["top_files"]],
            ["kind", "id", "name", "size"],
            title="Largest files",
        )


# ---------------------------------------------------------------------------
# tasks
# ---------------------------------------------------------------------------

TASK_COLUMNS = ["task_id", "title", "status", "priority", "assignee", "due_date", "project_id"]


@tasks_app.command("list")
def tasks_list(
    org: OrgOpt = None,
    status: Annotated[list[str] | None, typer.Option("--status", help="Repeatable: in_progress, blocked, …")] = None,
    priority: Annotated[list[str] | None, typer.Option("--priority", help="Repeatable.")] = None,
    project: Annotated[list[str] | None, typer.Option("--project", help="Repeatable project id.")] = None,
    assignee: Annotated[list[str] | None, typer.Option("--assignee", help="Repeatable username.")] = None,
    search: Annotated[str | None, typer.Option("--search", help="filter[search]")] = None,
    sort_by: Annotated[str | None, typer.Option("--sort-by")] = None,
    limit: Annotated[
        int | None, typer.Option("--limit", min=1, help="At most this many rows (default: every page).")
    ] = None,
    json_: JsonOpt = False,
    table: TableOpt = False,
) -> None:
    """List tasks — the list grammar's filters, every page unless --limit."""
    filters = {"status": status, "priority": priority, "project": project, "assignee": assignee, "search": search}

    def call(tm: Taskadence) -> list[Any]:
        page = tm.tasks.list(
            org_id=_resolve_org(tm, org),
            filter={k: v for k, v in filters.items() if v},
            sort_by=sort_by,
            limit=min(limit, 1000) if limit else None,
        )
        return _take(page, limit)

    rows = _run(call)
    _print_json(rows) if json_ else _table(rows, TASK_COLUMNS)


@tasks_app.command("get")
def tasks_get(task_id: str, json_: JsonOpt = False) -> None:
    """One task."""
    result = _run(lambda tm: tm.tasks.read(task_id))
    if json_:
        _print_json(result)
        return
    data = _plain(result)
    for key in [*TASK_COLUMNS, "task_type", "description", "tags", "created_at", "updated_at"]:
        out.print(f"[bold]{key:>12}[/bold]  {_cell(data.get(key))}")


def _task_fields(**values: Any) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


@tasks_app.command("create")
def tasks_create(
    title: Annotated[str, typer.Option("--title", help="The task's title.")],
    org: OrgOpt = None,
    project: Annotated[str | None, typer.Option("--project", help="Project id (omit for an unfiled task).")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
    priority: Annotated[str | None, typer.Option("--priority")] = None,
    assignee: Annotated[str | None, typer.Option("--assignee")] = None,
    due: Annotated[str | None, typer.Option("--due", help="YYYY-MM-DD")] = None,
    json_: JsonOpt = False,
) -> None:
    """Create a task (sent with an Idempotency-Key, so a retry never duplicates it)."""

    def call(tm: Taskadence) -> Any:
        body = _task_fields(
            org_id=_resolve_org(tm, org),
            title=title,
            project_id=project,
            description=description,
            status=status,
            priority=priority,
            assignee=assignee,
            due_date=due,
        )
        return tm.tasks.create(body)

    result = _run(call)
    _print_json(result) if json_ else out.print(f"Created {result.task_id}: {result.title}")


@tasks_app.command("update")
def tasks_update(
    task_id: str,
    status: Annotated[str | None, typer.Option("--status")] = None,
    priority: Annotated[str | None, typer.Option("--priority")] = None,
    title: Annotated[str | None, typer.Option("--title")] = None,
    assignee: Annotated[str | None, typer.Option("--assignee")] = None,
    due: Annotated[str | None, typer.Option("--due", help="YYYY-MM-DD")] = None,
    json_: JsonOpt = False,
) -> None:
    """Change a task (PATCH with the ETag just read, so a concurrent change is a 412, never a silent overwrite)."""
    fields = _task_fields(status=status, priority=priority, title=title, assignee=assignee, due_date=due)
    if not fields:
        err.print(
            "[red]Nothing to change[/red]: pass at least one of --status, --priority, --title, --assignee, --due."
        )
        raise typer.Exit(2)

    def call(tm: Taskadence) -> Any:
        current = tm.tasks.read(task_id)
        return tm.tasks.update(task_id, fields, if_match=current.etag)

    result = _run(call)
    _print_json(result) if json_ else out.print(
        f"Updated {result.task_id}: " + ", ".join(f"{k}={v}" for k, v in fields.items())
    )


# ---------------------------------------------------------------------------
# projects / views / webhooks / tokens
# ---------------------------------------------------------------------------


@projects_app.command("list")
def projects_list(org: OrgOpt = None, json_: JsonOpt = False, table: TableOpt = False) -> None:
    """Projects you can read in the organization."""
    rows = _run(lambda tm: list(tm.projects.list(_resolve_org(tm, org))))
    _print_json(rows) if json_ else _table(
        rows,
        ["project_id", "name", "status", "priority", "tasks_completed", "tasks_total", "progress_percent", "owner"],
    )


@views_app.command("rows")
def views_rows(
    view_id: str,
    csv_: Annotated[bool, typer.Option("--csv", help="Print CSV (flattened like to_dataframe).")] = False,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = None,
    json_: JsonOpt = False,
    table: TableOpt = False,
) -> None:
    """The tasks a saved view shows, with the caller's visibility."""
    rows = _run(lambda tm: _take(tm.views.rows(view_id, limit=min(limit, 1000) if limit else None), limit))
    if json_:
        _print_json(rows)
    elif csv_:
        from ..dataframe import _row

        flat = [_row(r) for r in rows]
        columns = list(dict.fromkeys(k for r in flat for k in r))
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)
        sys.stdout.write(buffer.getvalue())
    else:
        _table(rows, TASK_COLUMNS)


@webhooks_app.command("list")
def webhooks_list(org: OrgOpt = None, json_: JsonOpt = False, table: TableOpt = False) -> None:
    """The organization's webhooks (never their secrets)."""
    rows = _run(lambda tm: list(tm.webhooks.list(org_id=_resolve_org(tm, org))))
    _print_json(rows) if json_ else _table(
        rows, ["subscription_id", "name", "url", "status", "events", "consecutive_failures", "last_delivery_status"]
    )


@webhooks_app.command("test")
def webhooks_test(subscription_id: str, json_: JsonOpt = False) -> None:
    """Send a test delivery now and show the endpoint's answer."""
    result = _run(lambda tm: tm.webhooks.test(subscription_id))
    if json_:
        _print_json(result)
        return
    data = _plain(result)
    out.print(f"{data.get('delivery_id')}: {data.get('status')} (HTTP {data.get('response_status') or '-'})")


@webhooks_app.command("deliveries")
def webhooks_deliveries(
    subscription_id: str,
    limit: Annotated[int | None, typer.Option("--limit", min=1)] = 50,
    json_: JsonOpt = False,
    table: TableOpt = False,
) -> None:
    """A webhook's delivery log, newest first."""
    rows = _run(lambda tm: _take(tm.webhooks.deliveries(subscription_id, limit=min(limit or 50, 1000)), limit))
    _print_json(rows) if json_ else _table(
        rows, ["delivery_id", "event_type", "status", "response_status", "attempts", "created_at"]
    )


@tokens_app.command("list")
def tokens_list(org: OrgOpt = None, json_: JsonOpt = False, table: TableOpt = False) -> None:
    """Your access tokens (an owner / admin: the organization's). Prefixes only — never a token."""
    rows = _run(lambda tm: list(tm.tokens.list(org_id=_resolve_org(tm, org))))
    _print_json(rows) if json_ else _table(
        rows,
        [
            "token_id",
            "name",
            "token_prefix",
            "principal_display",
            "kind",
            "scopes",
            "status",
            "expires_at",
            "last_used_at",
        ],
    )


def main() -> None:
    # A pre-rename variable (`_brand.getenv`) warns once on stderr (DeprecationWarning is hidden outside __main__).
    warnings.filterwarnings("default", category=DeprecationWarning, message=LEGACY_ENV_PREFIX)
    app()


__all__ = ["app", "main"]
