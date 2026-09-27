# `tm.mcp`

The MCP server's clients table: how to add `/mcp` to each AI client (remote URL or local package), the tool groups and the scopes each needs. The server itself is `/mcp` (Streamable HTTP), outside this API.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.mcp.clients(if_none_match: str | None = None)`

How to add the MCP server to each client: the clients table, tool groups and scopes.

- **HTTP:** `GET /v1/mcp/clients`
- **operationId:** `mcp.clients`
- **Returns:** `McpClientsOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
