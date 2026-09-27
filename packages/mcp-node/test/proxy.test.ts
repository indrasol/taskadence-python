/**
 * @tasksmate/mcp (task 5.3): the stdio ↔ Streamable HTTP proxy.
 *
 * An MCP client (the SDK's `Client` over an in-memory pair — what stdio carries) → `bridge` → a fake remote server
 * (the SDK's low-level `Server` behind a stateless, JSON-response `StreamableHTTPServerTransport` on a local port). The
 * fake enforces `readonly` / `groups` and the bearer itself, as the real server does: the proxy only forwards. Plus:
 * 401 / 400 / unreachable become JSON-RPC errors, the process writes nothing but JSON-RPC to stdout and never the
 * token, and the package holds no tool code.
 */
import { spawnSync } from 'node:child_process';
import { readdirSync, readFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type Server as HttpServer, type ServerResponse } from 'node:http';
import type { AddressInfo } from 'node:net';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { CallToolRequestSchema, ListToolsRequestSchema, McpError } from '@modelcontextprotocol/sdk/types.js';
import { afterEach, describe, expect, it } from 'vitest';
import { loadConfig, mcpUrl, type Config } from '../src/config.js';
import { bridge, HTTP_ERROR, remoteTransport, UNAUTHORIZED, UNREACHABLE } from '../src/proxy.js';
import { VERSION } from '../src/version.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const TOKEN = `tm_live_${'S3cret'.repeat(7)}x`;
const TOOLS: Record<string, [group: string, readOnly: boolean]> = {
  whoami: ['me', true],
  list_my_tasks: ['tasks', true],
  create_task: ['tasks', false],
  list_projects: ['projects', true],
};

type Seen = { auth?: string; query: string; ua?: string; method?: string };

/** The remote server's contract, in miniature: bearer required, `?readonly=1` and `?groups=` enforced. */
async function fakeRemote(): Promise<{ url: string; seen: Seen[]; close: () => Promise<void> }> {
  const seen: Seen[] = [];
  const enabled = (query: URLSearchParams) => {
    const readonly = query.get('readonly') === '1';
    const groups = new Set([...(query.get('groups') ?? 'tasks,projects').split(','), 'me']);
    return new Set(Object.entries(TOOLS).filter(([, [g, ro]]) => groups.has(g) && (ro || !readonly)).map(([n]) => n));
  };
  const problem = (res: ServerResponse, status: number, body: Record<string, unknown>) => {
    res.writeHead(status, { 'content-type': 'application/problem+json' }).end(JSON.stringify({ status, ...body }));
  };
  const http: HttpServer = createServer(async (req: IncomingMessage, res: ServerResponse) => {
    const url = new URL(req.url ?? '/', 'http://x');
    seen.push({ auth: req.headers.authorization, query: url.search.slice(1), ua: req.headers['user-agent'], method: req.method });
    if (req.headers.authorization !== `Bearer ${TOKEN}`) {
      problem(res, 401, { type: 'about:blank', title: 'Unauthorized', detail: 'The access token is not valid', request_id: 'r-1' });
      return;
    }
    const groups = url.searchParams.get('groups');
    if (groups && !groups.split(',').every((g) => ['tasks', 'projects', 'me', 'admin'].includes(g))) {
      problem(res, 400, { type: 'urn:tasksmate:problem:invalid-parameter', title: 'Bad Request', detail: `groups must be a comma-separated list of: tasks, projects; got ${groups}` });
      return;
    }
    const names = enabled(url.searchParams);
    const server = new Server({ name: 'tasksmate', version: '0' }, { capabilities: { tools: {} } });
    server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: Object.keys(TOOLS).filter((n) => names.has(n)).map((name) => ({ name, inputSchema: { type: 'object' as const } })),
    }));
    server.setRequestHandler(CallToolRequestSchema, async (request) =>
      names.has(request.params.name)
        ? { content: [{ type: 'text' as const, text: `${request.params.name} ok` }] }
        : { content: [{ type: 'text' as const, text: `Read-only connection: \`${request.params.name}\` writes` }], isError: true });
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    await server.connect(transport);
    res.on('close', () => void transport.close());
    await transport.handleRequest(req, res);
  });
  await new Promise<void>((r) => http.listen(0, '127.0.0.1', r));
  const { port } = http.address() as AddressInfo;
  const close = () => new Promise<void>((r) => {
    http.close(() => r());
    http.closeAllConnections();   // the proxy's fetch keeps sockets alive
  });
  return { url: `http://127.0.0.1:${port}`, seen, close };
}

const cleanups: (() => Promise<void>)[] = [];
afterEach(async () => {
  for (const c of cleanups.splice(0).reverse()) await c();   // the proxy first, then the fake server
});

async function throughProxy(config: Config, options: { fetch?: typeof fetch; logs?: string[] } = {}) {
  const [clientSide, proxySide] = InMemoryTransport.createLinkedPair();
  const logs = options.logs ?? [];
  const { endOfInput, closed } = await bridge(proxySide, remoteTransport(config, { fetch: options.fetch, log: (l) => logs.push(l) }), (l) => logs.push(l));
  const client = new Client({ name: 'test', version: '0' });
  cleanups.push(async () => {
    endOfInput();
    await closed;
  });
  return { client, clientSide, logs };
}

const cfg = (apiUrl: string, extra: Partial<Config> = {}): Config => ({ token: TOKEN, apiUrl, readonly: false, groups: null, ...extra });

describe('forwarding', () => {
  it('initialize, tools/list and tools/call are the remote server\'s, with the bearer', async () => {
    const remote = await fakeRemote();
    cleanups.push(remote.close);
    const { client, clientSide } = await throughProxy(cfg(remote.url));
    await client.connect(clientSide);
    expect(client.getServerVersion()?.name).toBe('tasksmate');
    expect((await client.listTools()).tools.map((t) => t.name)).toEqual(['whoami', 'list_my_tasks', 'create_task', 'list_projects']);
    const called = await client.callTool({ name: 'create_task', arguments: { title: 'x' } });
    expect(called.isError).toBeFalsy();
    const posts = remote.seen.filter((s) => s.method === 'POST');
    expect(posts.length).toBeGreaterThan(0);
    expect(posts.every((s) => s.auth === `Bearer ${TOKEN}` && s.query === '' && s.ua?.startsWith('tasksmate-mcp/'))).toBe(true);
  });

  it('readonly and groups are forwarded as the query, and the SERVER refuses the write', async () => {
    const remote = await fakeRemote();
    cleanups.push(remote.close);
    const { client, clientSide } = await throughProxy(cfg(remote.url, { readonly: true, groups: ['tasks'] }));
    await client.connect(clientSide);
    expect((await client.listTools()).tools.map((t) => t.name)).toEqual(['whoami', 'list_my_tasks']);
    const called = await client.callTool({ name: 'create_task', arguments: { title: 'x' } });
    expect(called.isError).toBe(true);
    expect(new Set(remote.seen.filter((s) => s.method === 'POST').map((s) => s.query))).toEqual(new Set(['readonly=1&groups=tasks']));
  });

  it('a refused token is a JSON-RPC error naming the variable, never the value', async () => {
    const remote = await fakeRemote();
    cleanups.push(remote.close);
    const wrong = `tm_live_${'W'.repeat(43)}`;
    const logs: string[] = [];
    const { client, clientSide } = await throughProxy({ ...cfg(remote.url), token: wrong }, { logs });
    const error = await client.connect(clientSide).then(() => null, (e: unknown) => e);
    expect(error).toBeInstanceOf(McpError);
    expect((error as McpError).code).toBe(UNAUTHORIZED);
    expect((error as McpError).message).toContain('TASKSMATE_TOKEN');
    expect((error as McpError).message).toContain('not valid');
    expect(((error as McpError).data as { request_id: string }).request_id).toBe('r-1');
    expect(logs).toContain('the server refused TASKSMATE_TOKEN (401): The access token is not valid');
    expect(JSON.stringify([String(error), (error as McpError).data, logs])).not.toContain(wrong);
  });

  it('a 400 carries the server\'s detail', async () => {
    const remote = await fakeRemote();
    cleanups.push(remote.close);
    const { client, clientSide } = await throughProxy(cfg(remote.url, { groups: ['nope'] }));
    const error = (await client.connect(clientSide).then(() => null, (e: unknown) => e)) as McpError;
    expect(error.code).toBe(HTTP_ERROR);
    expect(error.message).toContain('got nope');
    expect((error.data as { type: string }).type).toBe('urn:tasksmate:problem:invalid-parameter');
  });

  it('an unreachable server is a JSON-RPC error, not a hang', async () => {
    const down = (async () => { throw new TypeError('fetch failed'); }) as unknown as typeof fetch;
    const logs: string[] = [];
    const { client, clientSide } = await throughProxy(cfg('http://api.test'), { fetch: down, logs });
    const error = (await client.connect(clientSide).then(() => null, (e: unknown) => e)) as McpError;
    expect(error.code).toBe(UNREACHABLE);
    expect(error.message).toContain('http://api.test');
    expect(logs.some((l) => l.startsWith('cannot reach http://api.test'))).toBe(true);
  });
});

describe('shutdown', () => {
  it('a request the transport aborts (closing) is not reported as an unreachable server', async () => {
    const { problemFetch } = await import('../src/proxy.js');
    const logs: string[] = [];
    const controller = new AbortController();
    const hang = ((_: unknown, init?: RequestInit) => new Promise<Response>((_r, reject) => init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))))) as unknown as typeof fetch;
    const pending = problemFetch(hang, (l) => logs.push(l))('http://api.test/mcp', { method: 'POST', body: '{"jsonrpc":"2.0","id":7,"method":"tools/list"}', signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toThrow('aborted');
    expect(logs).toEqual([]);
  });
});

describe('configuration', () => {
  it('flags win over the environment, and the URL is the server\'s contract', () => {
    const env = { TASKSMATE_TOKEN: TOKEN, TASKSMATE_API_URL: 'https://dev.example/v1/', TASKSMATE_MCP_READONLY: 'true', TASKSMATE_MCP_GROUPS: 'Tasks, projects' };
    const c = loadConfig({}, env);
    expect([c.apiUrl, c.readonly, c.groups]).toEqual(['https://dev.example', true, ['tasks', 'projects']]);
    expect(mcpUrl(c)).toBe('https://dev.example/mcp?readonly=1&groups=tasks,projects');
    expect(mcpUrl(loadConfig({ apiUrl: 'http://localhost:8000/mcp', readonly: false, groups: 'views' }, env))).toBe('http://localhost:8000/mcp?groups=views');
    expect(mcpUrl(loadConfig({}, { TASKSMATE_TOKEN: TOKEN }))).toBe('https://tasksmate-fdfsarhnf5gacfb7.eastus-01.azurewebsites.net/mcp');
    expect(loadConfig({}, { TASKSMATE_TOKEN: TOKEN, TASKSMATE_MCP_GROUPS: '' }).groups).toBeNull();
  });

  it.each([
    [{}, 'TASKSMATE_TOKEN is not set'],
    [{ TASKSMATE_TOKEN: TOKEN, TASKSMATE_MCP_READONLY: 'maybe' }, 'TASKSMATE_MCP_READONLY must be 1 or 0'],
    [{ TASKSMATE_TOKEN: TOKEN, TASKSMATE_API_URL: 'ftp://x' }, 'must start with http'],
  ])('a bad configuration is refused, naming no token (%j)', (env, message) => {
    expect(() => loadConfig({}, env)).toThrow(message);
  });

  it('the version is package.json\'s', () => {
    expect(VERSION).toBe(JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8')).version);
  });
});

describe('the process', () => {
  const run = (args: string[], input: string, env: Record<string, string>) => {
    const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('TASKSMATE_')));
    return spawnSync(process.execPath, [join(ROOT, 'dist', 'cli.js'), ...args], { input, env: { ...base, ...env }, encoding: 'utf8', timeout: 30_000 });
  };

  it('writes only JSON-RPC to stdout and never the token', async () => {
    const probe = createServer();
    await new Promise<void>((r) => probe.listen(0, '127.0.0.1', r));
    const { port } = probe.address() as AddressInfo;
    await new Promise((r) => probe.close(r));
    const init = { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '0' } } };
    const done = run(['--api-url', `http://127.0.0.1:${port}`, '--readonly'], `${JSON.stringify(init)}\n`, { TASKSMATE_TOKEN: TOKEN });
    const lines = done.stdout.split('\n').filter((l) => l.trim());
    expect(lines.length, done.stderr).toBeGreaterThan(0);
    const messages = lines.map((l) => JSON.parse(l) as { jsonrpc: string; id: number; error: { code: number } });
    expect(messages.every((m) => m.jsonrpc === '2.0')).toBe(true);
    expect(messages[0]?.id).toBe(1);
    expect(messages[0]?.error.code).toBe(UNREACHABLE);
    expect(done.stderr).toContain('cannot reach http://127.0.0.1');
    expect(done.stderr).toContain('proxying stdio to');
    expect(done.stdout + done.stderr).not.toContain(TOKEN);
    expect(done.status).toBe(0);
  });

  it('without a token exits 2, saying so on stderr', () => {
    const done = run([], '', {});
    expect(done.status).toBe(2);
    expect(done.stdout).toBe('');
    expect(done.stderr).toContain('TASKSMATE_TOKEN is not set');
  });
});

describe('a proxy only', () => {
  it('holds no tool definitions and imports no server framework', () => {
    for (const name of readdirSync(join(ROOT, 'src'))) {
      const text = readFileSync(join(ROOT, 'src', name), 'utf8');
      expect(text, name).not.toMatch(/sdk\/server\/(mcp|index)\.js|ListToolsRequestSchema|CallToolRequestSchema|registerTool|\.tool\(/);
    }
    expect(readFileSync(join(ROOT, 'src', 'proxy.ts'), 'utf8')).toContain('StreamableHTTPClientTransport');
  });
});
