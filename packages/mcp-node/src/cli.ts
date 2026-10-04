#!/usr/bin/env node
/** `taskadence-mcp` — the bin (`npx -y @taskadence/mcp`). Diagnostics go to stderr; stdout is JSON-RPC only. */
import { parseArgs } from 'node:util';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { BRAND_NAME, ConfigError, GROUPS_ENV, loadConfig, mcpUrl, READONLY_ENV, redact, SLUG, TOKEN_ENV, URL_ENV } from './config.js';
import { bridge, remoteTransport, stderrLog } from './proxy.js';
import { VERSION } from './version.js';

const HELP = `usage: ${SLUG}-mcp [--api-url URL] [--readonly | --no-readonly] [--groups a,b] [--version]

${BRAND_NAME}'s MCP server over stdio: a proxy to the remote server (<api>/mcp).
The token is read from ${TOKEN_ENV}, never from a flag.

Environment: ${TOKEN_ENV} (required), ${URL_ENV}, ${READONLY_ENV}, ${GROUPS_ENV}. Flags win.
`;

export async function main(argv = process.argv.slice(2)): Promise<number> {
  let values;
  try {
    ({ values } = parseArgs({
      args: argv,
      options: {
        'api-url': { type: 'string' },
        readonly: { type: 'boolean' },
        'no-readonly': { type: 'boolean' },
        groups: { type: 'string' },
        version: { type: 'boolean' },
        help: { type: 'boolean', short: 'h' },
      },
      strict: true,
    }));
  } catch (err) {
    stderrLog((err as Error).message);
    process.stderr.write(HELP);
    return 2;
  }
  if (values.help) {
    process.stderr.write(HELP);
    return 0;
  }
  if (values.version) {
    process.stderr.write(`${SLUG}-mcp ${VERSION}\n`);
    return 0;
  }
  let config;
  try {
    config = loadConfig({
      apiUrl: values['api-url'],
      readonly: values['no-readonly'] ? false : values.readonly ? true : undefined,
      groups: values.groups,
    });
  } catch (err) {
    if (err instanceof ConfigError) {
      stderrLog(err.message);
      return 2;
    }
    throw err;
  }
  stderrLog(`proxying stdio to ${redact(mcpUrl(config))}`);
  const stdio = new StdioServerTransport();
  const { endOfInput, closed } = await bridge(stdio, remoteTransport(config));
  process.stdin.on('end', endOfInput);
  await closed;
  return 0;
}

main().then(
  (code) => process.exit(code),
  (err: unknown) => {
    stderrLog(`fatal: ${String(err)}`);
    process.exit(1);
  },
);
