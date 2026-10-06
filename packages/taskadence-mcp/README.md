# taskadence-mcp: TasKadence for AI assistants that start a local program

[![PyPI version](https://img.shields.io/pypi/v/taskadence-mcp)](https://pypi.org/project/taskadence-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/taskadence-mcp)](https://pypi.org/project/taskadence-mcp/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](https://github.com/indrasol/taskadence-python/blob/main/LICENSE)

[TasKadence](https://taskadence.com) is task and project management for teams. `taskadence-mcp` lets an AI assistant
(Claude Desktop, Claude Code, Cursor, VS Code and others) read and update your TasKadence tasks, projects and teams,
through the Model Context Protocol (MCP).

**Do I need this, or the URL?** If your assistant can add an MCP server by URL (often called a remote server or a
custom connector), use the URL `https://api.taskadence.com/mcp` instead: you sign in with OAuth and there is no token
to manage. See [Connect](https://docs.taskadence.com/mcp/connect/). Use this package when your assistant can only start
a local program (a "stdio" server), or when you want it to use a token you created yourself.

Its twin on npm, `npx -y @taskadence/mcp`, does exactly the same with Node.js; pick whichever runtime you have.

> **`0.x` is a pre-release.** Any `0.x` release may change anything; pin a version in configs you depend on.

**Documentation:** [docs.taskadence.com](https://docs.taskadence.com/mcp/) ·
**Source:** [GitHub](https://github.com/indrasol/taskadence-python) · **Issues:** [GitHub issues](https://github.com/indrasol/taskadence-python/issues)

## Set up in 3 steps

You need a TasKadence account and about five minutes.

### 1. Get a token

A token is a password for programs: the assistant uses it to act for you in one organization.

1. In TasKadence, open **Developers** in the sidebar, stay on the **Tokens** tab and click **Create token**.
2. Give it a name you will recognise later (for example "Claude Desktop").
3. Under **Scopes**, tick what the assistant may do. For an assistant that only looks: **Read** on the **Tasks**,
   **Projects** and **Teams** rows. To let it create and change things too: **Write** on those rows (Write includes
   Read). The scopes decide which tools the assistant sees.
4. Click **Create token** and copy it (it starts with `tkd_live_`). **It is shown once.**

Shortcut: **Developers > MCP** in TasKadence writes the configuration for your client, with a new token already in it.

### 2. Install uv

`uvx` comes with [uv](https://docs.astral.sh/uv/getting-started/installation/), a Python tool runner. It downloads and
runs `taskadence-mcp` (and a suitable Python, if you have none) the first time your client starts it. Skip this step
if `uvx --version` already prints a version.

macOS or Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Prefer pip? `pip install taskadence-mcp` installs a `taskadence-mcp` command; then use `"command": "taskadence-mcp"`
and `"args": []` below. `taskadence-mcp --help` lists the options.

### 3. Add it to your client

Paste your token where the examples say `tkd_live_your_token_here`, then restart the client.

**Claude Desktop.** Open **Settings > Developer > Edit Config**. That opens `claude_desktop_config.json`, which lives
at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS and
`%APPDATA%\Claude\claude_desktop_config.json` on Windows. Add the `taskadence` entry (keep any other servers already
under `mcpServers`), save, then quit Claude Desktop completely and open it again.

```json
{
  "mcpServers": {
    "taskadence": {
      "command": "uvx",
      "args": ["taskadence-mcp"],
      "env": { "TASKADENCE_TOKEN": "tkd_live_your_token_here" }
    }
  }
}
```

**Claude Code.** One command (add `--scope user` to use it in every project):

```bash
claude mcp add --env TASKADENCE_TOKEN=tkd_live_your_token_here --transport stdio taskadence -- uvx taskadence-mcp
```

**Cursor.** Put the same JSON as Claude Desktop in `~/.cursor/mcp.json` for every project
(`%USERPROFILE%\.cursor\mcp.json` on Windows), or in `.cursor/mcp.json` inside one project.

**VS Code.** Put this in `.vscode/mcp.json` in your workspace, or, for every workspace, run **MCP: Open User
Configuration** from the Command Palette. VS Code uses `servers` and `"type": "stdio"`:

```json
{
  "servers": {
    "taskadence": {
      "type": "stdio",
      "command": "uvx",
      "args": ["taskadence-mcp"],
      "env": { "TASKADENCE_TOKEN": "tkd_live_your_token_here" }
    }
  }
}
```

Keep tokens out of git: a project file (`.cursor/mcp.json`, `.vscode/mcp.json`) is easy to commit by mistake, so
prefer the user-level file for a config that holds a token.

## Check it works

Ask your assistant: *"Which TasKadence account and organization are you connected to?"* It should call the `whoami`
tool (your client may ask you to allow it first) and answer with your name and your organization. Then try *"List my
tasks that are in progress."*

Your client also lists its MCP servers: `taskadence` should be there, connected, with its tools (in Claude Code, type
`/mcp`). An error or an empty tool list means one of the problems below.

## Troubleshooting

- **"TASKADENCE_TOKEN is not set":** the `env` block is missing or the name is misspelled. Fix the config and restart
  the client.
- **Token refused (401):** the error says "TasKadence refused the access token in TASKADENCE_TOKEN (401)". The token
  was copied wrong, has expired or was revoked. Create a new one in **Developers > Tokens**, replace it in the config,
  and restart the client.
- **A tool is missing, or "insufficient scope":** the token's scopes decide which tools appear. Create a token with
  **Write** ticked to let the assistant change things (scopes cannot be added to an existing token).
  `TASKADENCE_MCP_READONLY=1` hides every tool that writes, and `TASKADENCE_MCP_GROUPS` limits the tool groups (see
  Configure below).
- **`uvx` not found (`spawn uvx ENOENT`):** install it (step 2), then restart the client. On macOS an app
  opened from the Dock may not see your terminal's `PATH`: put the full path in `"command"` (find it with
  `which uvx`; on Windows, `where uvx`).
- **Wrong Python 3.10 version:** `taskadence-mcp` needs Python 3.10 or later. Check with `python --version`.
- **"MCP server unreachable":** the computer cannot reach the TasKadence API. Check the network, and
  `TASKADENCE_API_URL` if you set it.

Still stuck? Open a [GitHub issue](https://github.com/indrasol/taskadence-python/issues) with the error message and your client's name; never paste a live
token.

## Configure

Everything is optional except the token. Set these in the `env` block of your client's config, or pass the flags in
`args`.

| Variable | Flag | |
|---|---|---|
| `TASKADENCE_TOKEN` | none | **Required.** A personal access token (`tkd_live_…`). |
| `TASKADENCE_API_URL` | `--api-url` | The API's origin. Default: `https://api.taskadence.com`. `/mcp` is added. |
| `TASKADENCE_MCP_READONLY` | `--readonly` / `--no-readonly` | `1`: only tools that read, enforced by the server. |
| `TASKADENCE_MCP_GROUPS` | `--groups` | For example `tasks,projects`: only those tool groups. Default: every group except `admin`; `me` is always on. |

Flags win over the environment. There is no token flag: a command line is visible to every process on the machine.
The tools and groups are listed in [Tools](https://docs.taskadence.com/mcp/tools/).

## What it does, exactly

`taskadence-mcp` is a proxy, not a second server: it speaks MCP over stdio to your client and forwards every message to the
TasKadence remote MCP server (`<api>/mcp`, Streamable HTTP) with your token. The tools, the read-only and tool-group
enforcement, and the audit trail are the remote server's.

- stdin goes to the remote server unchanged (`initialize` included; the server is stateless), and the server's answers
  go to stdout unchanged. stdout carries JSON-RPC and nothing else; diagnostics go to stderr, never the token.
- A refused token (401) is answered with a JSON-RPC error naming `TASKADENCE_TOKEN` (code `-32001`), any other HTTP
  refusal with its status and the server's detail (`-32002`; an unknown group is a 400), an unreachable server with
  `-32003`. Each also writes one line to stderr.
- It holds no tool of its own and reaches nothing but `<api>/mcp`.

## Requirements

Python 3.10 or later. Depends on `mcp` (the official MCP SDK, `<2`) and `httpx`.

## Support and security

Bugs and questions: [GitHub issues](https://github.com/indrasol/taskadence-python/issues); never paste a live token. Vulnerabilities: report them privately as
described in [SECURITY.md](https://github.com/indrasol/taskadence-python/blob/main/SECURITY.md) (GitHub private vulnerability reporting, or
srvcs.infra@indrasol.com).

## License

Apache License 2.0. See [LICENSE](https://github.com/indrasol/taskadence-python/blob/main/LICENSE). The license grants no right to use the TasKadence or
Indrasol names or marks.
