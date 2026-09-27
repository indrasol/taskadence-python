/**
 * Where the proxy connects, as whom, and with which options — flags first, then the environment. The same names as
 * the Python twin (`uvx tasksmate-mcp`):
 *
 *   TASKSMATE_TOKEN         required — a `tm_live_…` / `tm_test_…` access token (Developers → Tokens)
 *   TASKSMATE_API_URL       the API's origin (default: production); `/mcp` is added here
 *   TASKSMATE_MCP_READONLY  `1` / `true` → `?readonly=1`: the SERVER lists and allows only read tools
 *   TASKSMATE_MCP_GROUPS    `tasks,projects` → `?groups=…`: the SERVER enables only those groups (`me` is always on)
 *
 * `TASKSMATE_*` on purpose — the packages' (and the `tm` CLI's) environment; `…_TM` is the API server's own convention,
 * not this one's. Flags `--api-url`, `--readonly` / `--no-readonly`, `--groups` win. No `--token`: argv is public.
 */
export const TOKEN_ENV = 'TASKSMATE_TOKEN';
export const URL_ENV = 'TASKSMATE_API_URL';
export const READONLY_ENV = 'TASKSMATE_MCP_READONLY';
export const GROUPS_ENV = 'TASKSMATE_MCP_GROUPS';

/** The production API — the Python SDK's DEFAULT_BASE_URL (the backend's clients table names the same one). */
export const DEFAULT_API_URL = 'https://tasksmate-fdfsarhnf5gacfb7.eastus-01.azurewebsites.net';
export const MCP_PATH = '/mcp';

const TRUE = new Set(['1', 'true', 'yes', 'on']);
const FALSE = new Set(['0', 'false', 'no', 'off', '']);
const TOKEN_SHAPED = /tm_(?:live|test)_[A-Za-z0-9_-]*/g;

export class ConfigError extends Error {}

export interface Config {
  token: string;
  apiUrl: string;
  readonly: boolean;
  groups: string[] | null;
}

export interface Flags {
  apiUrl?: string;
  readonly?: boolean;
  groups?: string;
}

/** Anything token-shaped becomes `tm_…` — a belt for every line this package writes. */
export const redact = (text: string): string => text.replace(TOKEN_SHAPED, 'tm_…');

/** `<api>/mcp[?readonly=1][&groups=a,b]` — the remote server's own URL contract (5.1). */
export function mcpUrl(config: Pick<Config, 'apiUrl' | 'readonly' | 'groups'>): string {
  const query: string[] = [];
  if (config.readonly) query.push('readonly=1');
  if (config.groups) query.push(`groups=${config.groups.map(encodeURIComponent).join(',')}`);
  return `${config.apiUrl}${MCP_PATH}${query.length ? `?${query.join('&')}` : ''}`;
}

function bool(name: string, value: string): boolean {
  const v = value.trim().toLowerCase();
  if (TRUE.has(v)) return true;
  if (FALSE.has(v)) return false;
  throw new ConfigError(`${name} must be 1 or 0 (got ${JSON.stringify(value)})`);
}

function groupsOf(value: string): string[] {
  const groups = [...new Set(value.split(',').map((g) => g.trim().toLowerCase()).filter(Boolean))];
  if (!groups.length) throw new ConfigError('groups is empty: name at least one group (e.g. tasks,projects), or leave it unset for the default');
  return groups;
}

function apiUrlOf(value: string): string {
  let url = value.trim().replace(/\/+$/, '');
  for (const suffix of [MCP_PATH, '/v1']) if (url.endsWith(suffix)) url = url.slice(0, -suffix.length);
  url = url.replace(/\/+$/, '');
  if (!/^https?:\/\//.test(url)) throw new ConfigError(`${URL_ENV} / --api-url must start with http:// or https:// (got ${JSON.stringify(redact(value))})`);
  return url;
}

export function loadConfig(flags: Flags = {}, env: Record<string, string | undefined> = process.env): Config {
  const token = (env[TOKEN_ENV] ?? '').trim();
  if (!token) {
    throw new ConfigError(`${TOKEN_ENV} is not set: create an access token in TasksMate (Developers → Tokens) and put it in the client's MCP config as ${TOKEN_ENV}`);
  }
  const apiUrl = apiUrlOf(flags.apiUrl ?? (env[URL_ENV] || DEFAULT_API_URL));
  const readonly = flags.readonly ?? bool(READONLY_ENV, env[READONLY_ENV] ?? '');
  const rawGroups = flags.groups ?? (env[GROUPS_ENV] || undefined);   // an empty variable = unset
  return { token, apiUrl, readonly, groups: rawGroups === undefined ? null : groupsOf(rawGroups) };
}
