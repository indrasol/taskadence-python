/**
 * @taskadence/mcp — Taskadence's MCP server for clients that start a local process. A PROXY, not a second server: MCP
 * over stdio to the client, every JSON-RPC message forwarded to the remote Taskadence MCP server
 * (`<TASKADENCE_API_URL>/mcp`, Streamable HTTP) with `Authorization: Bearer $TASKADENCE_TOKEN`. The tools, the
 * read-only / tool-group enforcement and the audit trail are the remote server's; this package has no tool of its own.
 */
export { ConfigError, DEFAULT_API_URL, loadConfig, mcpUrl, redact, type Config, type Flags } from './config.js';
export { bridge, HTTP_ERROR, problemFetch, remoteTransport, UNAUTHORIZED, UNREACHABLE } from './proxy.js';
export { VERSION } from './version.js';
