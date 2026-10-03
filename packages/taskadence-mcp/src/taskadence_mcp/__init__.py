"""taskadence-mcp — Taskadence's MCP server for clients that start a local process.

A PROXY, not a second server: it speaks MCP over stdio to the client and forwards every JSON-RPC message to the
remote Taskadence MCP server (`<TASKADENCE_API_URL>/mcp`, Streamable HTTP) with
`Authorization: Bearer $TASKADENCE_TOKEN`.
The tools, the read-only / tool-group enforcement and the audit trail are the remote server's; this package has no
tool of its own (a test fails if it grows one).
"""

from ._version import __version__
from .config import Config, ConfigError, load_config
from .proxy import run_proxy

__all__ = ["Config", "ConfigError", "__version__", "load_config", "run_proxy"]
