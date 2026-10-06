# @taskadence/mcp: the TasKadence MCP server over stdio

For MCP clients that **start a local process** instead of calling a URL. `npx -y @taskadence/mcp` speaks the Model Context Protocol
over stdio to your client and forwards every message to the TasKadence **remote** MCP server (`<api>/mcp`, Streamable
HTTP) with your access token. It is a proxy, not a second server: the tools, the read-only and tool-group enforcement,
and the audit trail are the remote server's.

> **`0.x` is a pre-release.** Any `0.x` release may change anything; pin a version in production configs.

**Documentation:** [docs.taskadence.com](https://docs.taskadence.com) ·
**Source:** [GitHub](https://github.com/indrasol/taskadence-python) · **Issues:** [GitHub issues](https://github.com/indrasol/taskadence-python/issues)

## Install and run

```bash
npx -y @taskadence/mcp               # run it without installing
npm install -g @taskadence/mcp       # or install it, then run `taskadence-mcp`
npx -y @taskadence/mcp --help
```

The twin package is `uvx taskadence-mcp` (PyPI): same variables, same flags.

**Prefer the URL when your client supports it.** If your client can add a remote MCP server by URL (Claude, Claude
Code, Cursor, VS Code, …), use the URL instead: it signs in with OAuth and needs no token. See
[Connect](https://docs.taskadence.com/mcp/connect/).

## Authentication

Create a personal access token in TasKadence under **Settings > Developers** (it is shown once) and pass it as
`TASKADENCE_TOKEN`. Its scopes decide which tools the server lists; a `tkd_test_…` token reads only.

## Configure

| Variable | Flag | |
|---|---|---|
| `TASKADENCE_TOKEN` | none | **Required.** A personal access token (`tkd_live_…`). |
| `TASKADENCE_API_URL` | `--api-url` | The API's origin. Default: `https://api.taskadence.com`. `/mcp` is added. |
| `TASKADENCE_MCP_READONLY` | `--readonly` / `--no-readonly` | `1`: only read tools, enforced by the server. |
| `TASKADENCE_MCP_GROUPS` | `--groups` | e.g. `tasks,projects`: only those tool groups. Default: every group except `admin`; `me` is always on. |

Flags win over the environment. There is no token flag: a command line is visible to every process on the machine.

## Add it to your client

```json
{
  "mcpServers": {
    "taskadence": {
      "command": "npx",
      "args": ["-y", "@taskadence/mcp"],
      "env": { "TASKADENCE_TOKEN": "tkd_live_…", "TASKADENCE_MCP_READONLY": "1" }
    }
  }
}
```

Claude Code: `claude mcp add --env TASKADENCE_TOKEN=tkd_live_… --transport stdio taskadence -- npx -y @taskadence/mcp`.
In TasKadence, **Settings > Developers > MCP** writes this for your client, with a token scoped to your choice.

## What it does, exactly

- stdin goes to the remote server unchanged (`initialize` included; the server is stateless), and the server's answers
  go to stdout unchanged. stdout carries JSON-RPC and nothing else; diagnostics go to stderr, never the token.
- A refused token (401) is answered with a JSON-RPC error naming `TASKADENCE_TOKEN` (code `-32001`), any other HTTP
  refusal with its status and the server's detail (`-32002`; an unknown group is a 400), an unreachable server with
  `-32003`. Each also writes one line to stderr.
- It holds no tool of its own and reaches nothing but `<api>/mcp`.

Node 20 or later, ESM. Depends on `@modelcontextprotocol/sdk` (the official MCP SDK).

## Support and security

Bugs and questions: [GitHub issues](https://github.com/indrasol/taskadence-python/issues); never paste a live token. Vulnerabilities: report them privately as
described in [SECURITY.md](https://github.com/indrasol/taskadence-python/blob/main/SECURITY.md) (GitHub private vulnerability reporting, or
srvcs.infra@indrasol.com).

## License

Apache License 2.0. The license grants no right to use the TasKadence or Indrasol names or marks.
