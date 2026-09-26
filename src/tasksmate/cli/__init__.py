"""`tm` — the TasksMate command line (the `cli` extra: `pip install "tasksmate[cli]"`).

    tm auth login                      # prompts for a tm_live_ token (hidden), verifies it, stores it
    tm me
    tm tasks list --org O0020 --status in_progress --table
    tm tasks create --org O0020 --title "Ship the SDK" --project P96441
    tm tasks update T123456 --status completed
    tm views rows V123456 --csv > rows.csv

Output: a table by default, `--json` for the raw API objects. Exit codes: 0 success; 1 an API or connection error (the
problem is printed with its `request_id`); 2 a usage error. The token is never printed — only its 12-character prefix.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections.abc import Callable, Iterable, Sequence
from typing import Annotated, Any, TypeVar

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError as exc:  # pragma: no cover - the extra is not installed
    raise SystemExit('The tm CLI needs the cli extra: pip install "tasksmate[cli]"') from exc

from .. import __version__, errors
from .._client import TasksMate
from .._core import ConfigurationError
from . import _config

app = typer.Typer(
    name="tm",
    help="The TasksMate API from the command line.",
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
    typer.Option("--org", envvar="TASKSMATE_ORG", help="Organization id (default: yours, when you have exactly one)."),
]


class _State:
    api_url: str | None = None


state = _State()


def _version(value: bool) -> None:
    if value:
        out.print(f"tasksmate {__version__}")
        raise typer.Exit()


@app.callback()
def main_options(
    api_url: Annotated[
        str | None,
        typer.Option("--api-url", help="API base URL (else TASKSMATE_API_URL, the saved one, or the SDK default)."),
    ] = None,
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    state.api_url = api_url


# ---------------------------------------------------------------------------
# plumbing
# ---------------------------------------------------------------------------


def _client() -> TasksMate:
    creds = _config.load(state.api_url)
    if not creds.token:
        err.print("[red]Not signed in.[/red] Run [bold]tm auth login[/bold] or set TASKSMATE_TOKEN.")
        raise typer.Exit(1)
    return TasksMate(token=creds.token, base_url=creds.api_url)


def _run(call: Callable[[TasksMate], T]) -> T:
    """Call the API; an API / connection / configuration error is printed and exits 1."""
    try:
        with _client() as tm:
            return call(tm)
    except errors.TasksMateError as exc:
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


def _resolve_org(tm: TasksMate, org: str | None) -> str:
    if org:
        return org
    orgs = [o.org_id for o in tm.me().organizations or []]
    if len(orgs) == 1:
        return orgs[0]
    err.print(
        f"[red]--org is required[/red] (you belong to: {', '.join(orgs) or 'no organization'}; or set TASKSMATE_ORG)"
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
    """Store an access token (OS keyring, else ~/.config/tasksmate/config.toml, mode 600). Never echoed."""
    value = token or typer.prompt("Access token (tm_live_…)", hide_input=True)
    value = value.strip()
    if not value.startswith(("tm_live_", "tm_test_")):
        err.print("[red]That is not a TasksMate access token[/red] (they start with tm_live_ or tm_test_).")
        raise typer.Exit(2)
    if not no_verify:
        try:
            with TasksMate(token=value, base_url=_config.load(state.api_url).api_url) as tm:
                me = tm.me()
        except errors.TasksMateError as exc:
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
        out.print("Not signed in (no TASKSMATE_TOKEN, no stored token).")
        raise typer.Exit(1)
    source = {"env": "TASKSMATE_TOKEN", "keyring": "the OS keyring", "file": str(_config.config_path())}[creds.source]
    out.print(f"Token {_config.shown(creds.token)} from {source}")
    with TasksMate(token=creds.token, base_url=creds.api_url) as tm:
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

    def call(tm: TasksMate) -> list[Any]:
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

    def call(tm: TasksMate) -> Any:
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

    def call(tm: TasksMate) -> Any:
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
    app()


__all__ = ["app", "main"]
