# @tasksmate/mcp — TasksMate's MCP server over stdio

For MCP clients that **start a local process** instead of calling a URL. `npx -y @tasksmate/mcp` speaks the Model
Context Protocol over stdio to your client and forwards every message to TasksMate's **remote** MCP server
(`<api>/mcp`, Streamable HTTP) with your access token. It is a proxy, not a second server: the tools, the read-only and
tool-group enforcement, and the audit trail are the remote server's — the same tools, by construction.

> **`0.x` is a pre-release**, and **not on npm yet** (TasksMate's stability gate). Until then, from a checkout:
> `npm ci && npm run build` in `packages/mcp-node`, then run `node packages/mcp-node/dist/cli.js`.

If your client can add a remote server by URL (Claude, Claude Code, Cursor, VS Code, …), use the URL instead — it signs
in with OAuth and needs no token: [Connect](https://developers.tasksmate.indrasol.com/mcp/connect/). The Python twin is
`uvx tasksmate-mcp` (same variables, same flags).

## Configure

| Variable | Flag | |
|---|---|---|
| `TASKSMATE_TOKEN` | — | **Required.** An access token (`tm_live_…`; a `tm_test_…` token reads only) from TasksMate → **Developers → Tokens**. Its scopes decide which tools the server lists. |
| `TASKSMATE_API_URL` | `--api-url` | The API's origin. Default: production. `/mcp` is added. |
| `TASKSMATE_MCP_READONLY` | `--readonly` / `--no-readonly` | `1` → only read tools, enforced by the server (`?readonly=1`). |
| `TASKSMATE_MCP_GROUPS` | `--groups` | e.g. `tasks,projects` → only those tool groups (`?groups=…`). Default: every group except `admin`; `me` is always on. |

Flags win over the environment. There is no token flag: a command line is visible to every process on the machine.
The names are `TASKSMATE_*` on purpose — the packages' (and the `tm` CLI's) environment; the `…_TM` suffix is the API
server's own convention, not this one's.

## Add it to your client

```json
{
  "mcpServers": {
    "tasksmate": {
      "command": "npx",
      "args": ["-y", "@tasksmate/mcp"],
      "env": { "TASKSMATE_TOKEN": "tm_live_…", "TASKSMATE_MCP_READONLY": "1" }
    }
  }
}
```

Claude Code: `claude mcp add --env TASKSMATE_TOKEN=tm_live_… --transport stdio tasksmate -- npx -y @tasksmate/mcp`.
TasksMate's **Developers → MCP** tab writes this for your client, with a token scoped to your choice.

## What it does, exactly

- stdin → the remote server, unchanged (`initialize` included; the server is stateless); the server's answers →
  stdout, unchanged. stdout carries JSON-RPC and nothing else; diagnostics go to stderr, never the token.
- A refused token (401) is answered with a JSON-RPC error naming `TASKSMATE_TOKEN` (code `-32001`), any other HTTP
  refusal with its status and the server's detail (`-32002` — an unknown group is a 400), an unreachable server with
  `-32003`; each also writes one line to stderr.
- It holds no tool of its own and reaches nothing but `<api>/mcp`.

Node ≥ 20, ESM. Depends on `@modelcontextprotocol/sdk` (the official SDK). Apache-2.0.
