/**
 * The bridge: MCP over stdio on one side, the remote server over Streamable HTTP on the other.
 *
 * Every JSON-RPC message the client writes goes to the server unchanged (`initialize` included — the server is
 * stateless), and every message the server answers comes back unchanged; `tools/list` is the server's list. The SDK's
 * own transports do the protocol work (`StdioServerTransport`, `StreamableHTTPClientTransport`).
 *
 * One thing is added: an HTTP refusal becomes a JSON-RPC error. `problemFetch` (the transport's `fetch`) answers a
 * refused or failed POST of a request itself with a JSON-RPC error for THAT id: a 401 names `TASKADENCE_TOKEN` (never
 * its value), a 400 carries the server's problem detail (an unknown group), anything else the status and detail; an
 * unreachable server says so. Each also writes one line to stderr. stdout carries JSON-RPC only.
 */
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import type { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { isJSONRPCErrorResponse, isJSONRPCRequest, isJSONRPCResultResponse, type JSONRPCMessage } from '@modelcontextprotocol/sdk/types.js';
import { BRAND_NAME, mcpUrl, redact, SLUG, TOKEN_ENV, type Config } from './config.js';
import { VERSION } from './version.js';

export const UNAUTHORIZED = -32001; // JSON-RPC implementation-defined server errors: -32000 … -32099
export const HTTP_ERROR = -32002;
export const UNREACHABLE = -32003;
export const DRAIN_MS = 30_000; // after stdin closes: how long answers still in flight are waited for

export type Log = (line: string) => void;
export const stderrLog: Log = (line) => process.stderr.write(`${SLUG}-mcp: ${redact(line)}\n`);

type Fetch = typeof fetch;

const jsonrpcError = (id: unknown, code: number, message: string, data: Record<string, unknown>) =>
  new Response(JSON.stringify({ jsonrpc: '2.0', id, error: { code, message: redact(message), data } }), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });

function rpcOf(init?: RequestInit): Record<string, unknown> | null {
  if ((init?.method ?? 'GET').toUpperCase() !== 'POST' || typeof init?.body !== 'string') return null;
  try {
    const body: unknown = JSON.parse(init.body);
    return body && typeof body === 'object' && !Array.isArray(body) ? (body as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

/** A notification (or a response) that is refused gets a bare 202: nothing waits for an answer. */
const answer = (rpc: Record<string, unknown>, code: number, message: string, data: Record<string, unknown>) =>
  'id' in rpc && 'method' in rpc ? jsonrpcError(rpc.id, code, message, data) : new Response(null, { status: 202 });

/** Wraps `inner`: a refused or failed POST of a request is answered with a JSON-RPC error. */
export function problemFetch(inner: Fetch, log: Log = stderrLog): Fetch {
  return async (input, init) => {
    const rpc = rpcOf(init);
    let response: Response;
    try {
      response = await inner(input, init);
    } catch (err) {
      // no answer to make: not a JSON-RPC POST, or the transport itself aborted it (closing) — that is not "unreachable"
      if (!rpc || init?.signal?.aborted) throw err;
      const url = new URL(input instanceof Request ? input.url : String(input));
      log(`cannot reach ${url.origin} (${(err as Error)?.name ?? 'Error'}) — check TASKADENCE_API_URL and the network`);
      return answer(rpc, UNREACHABLE, `${BRAND_NAME} MCP server unreachable at ${url.origin}`, { url: url.origin });
    }
    if (!rpc || response.status < 400) return response;
    let problem: Record<string, unknown> = {};
    try {
      const body: unknown = JSON.parse(await response.text());
      if (body && typeof body === 'object') problem = body as Record<string, unknown>;
    } catch {
      /* not JSON: the status speaks */
    }
    const detail = String(problem.detail ?? problem.title ?? response.statusText ?? '');
    const data: Record<string, unknown> = { status: response.status };
    for (const k of ['type', 'title', 'detail', 'errors', 'request_id']) if (k in problem) data[k] = problem[k];
    if (response.status === 401) {
      log(`the server refused ${TOKEN_ENV} (401): ${detail}`);
      return answer(rpc, UNAUTHORIZED, `${BRAND_NAME} refused the access token in ${TOKEN_ENV} (401): ${detail}. Create one in Developers → Tokens.`, data);
    }
    log(`the server answered ${response.status}: ${detail}`);
    return answer(rpc, HTTP_ERROR, `${BRAND_NAME} MCP server: ${response.status} ${detail}`, data);
  };
}

export function remoteTransport(config: Config, options: { fetch?: Fetch; log?: Log } = {}): StreamableHTTPClientTransport {
  return new StreamableHTTPClientTransport(new URL(mcpUrl(config)), {
    fetch: problemFetch(options.fetch ?? fetch, options.log),
    requestInit: { headers: { Authorization: `Bearer ${config.token}`, 'User-Agent': `${SLUG}-mcp/${VERSION} (node)` } },
  });
}

/**
 * Forward both ways until `local` closes (stdin EOF: the caller calls `endOfInput`); then answer what is still in flight
 * (at most `DRAIN_MS`) and close both sides. Resolves when done.
 */
export async function bridge(local: Transport, remote: Transport, log: Log = stderrLog): Promise<{ endOfInput: () => void; closed: Promise<void> }> {
  const pending = new Set<string | number>();
  let closing = false;
  let resolveClosed!: () => void;
  const closed = new Promise<void>((r) => (resolveClosed = r));
  const close = async () => {
    if (closing) return;
    closing = true;
    await remote.close().catch(() => undefined);
    await local.close().catch(() => undefined);
    resolveClosed();
  };

  local.onmessage = (message: JSONRPCMessage) => {
    if (isJSONRPCRequest(message)) pending.add(message.id);
    remote.send(message).catch((err: unknown) => log(`could not forward ${isJSONRPCRequest(message) ? message.method : 'a message'}: ${String(err)}`));
  };
  remote.onmessage = (message: JSONRPCMessage) => {
    if (isJSONRPCResultResponse(message) || isJSONRPCErrorResponse(message)) {
      if (message.id !== undefined) pending.delete(message.id);
      const version = isJSONRPCResultResponse(message) ? (message.result as { protocolVersion?: unknown }).protocolVersion : undefined;
      if (typeof version === 'string' && remote instanceof StreamableHTTPClientTransport) remote.setProtocolVersion(version);
    }
    local.send(message).catch((err: unknown) => log(`could not write to stdout: ${String(err)}`));
  };
  local.onerror = (err) => log(`stdin: ${err.message}`);
  remote.onerror = (err) => log(`transport: ${err.message}`);
  local.onclose = () => void close();

  await remote.start();
  await local.start();

  const endOfInput = () => {
    const started = Date.now();
    const wait = () => {
      if (!pending.size || Date.now() - started > DRAIN_MS) void close();
      else setTimeout(wait, 20);
    };
    wait();
  };
  return { endOfInput, closed };
}
