"""`tasksmate-mcp` — the console script (`uvx tasksmate-mcp`). Diagnostics go to stderr; stdout is JSON-RPC only."""

from __future__ import annotations

import argparse
import sys

import anyio

from ._version import __version__
from .config import GROUPS_ENV, READONLY_ENV, TOKEN_ENV, URL_ENV, ConfigError, load_config, redact
from .proxy import run_proxy, stderr_log


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tasksmate-mcp",
        description="TasksMate's MCP server over stdio: a proxy to the remote server (<api>/mcp). "
        f"The token is read from {TOKEN_ENV}, never from a flag.",
        epilog=f"Environment: {TOKEN_ENV} (required), {URL_ENV}, {READONLY_ENV}, {GROUPS_ENV}. Flags win.",
    )
    p.add_argument("--api-url", help=f"the API's origin (else {URL_ENV}, else production)")
    p.add_argument(
        "--readonly",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"only read tools, enforced by the server (else {READONLY_ENV})",
    )
    p.add_argument(
        "--groups", help=f"comma-separated tool groups, e.g. tasks,projects (else {GROUPS_ENV}; default: all but admin)"
    )
    p.add_argument("--version", action="version", version=f"tasksmate-mcp {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    ns = parser().parse_args(argv)
    try:
        config = load_config(api_url=ns.api_url, readonly=ns.readonly, groups=ns.groups)
    except ConfigError as exc:
        stderr_log(str(exc))
        return 2
    stderr_log(f"proxying stdio to {redact(config.mcp_url)}")
    try:
        anyio.run(run_proxy, config)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
