# Security policy

## Reporting a vulnerability

Please report security issues **privately**, never in a public issue, pull request or discussion. Either:

- use GitHub's **private vulnerability reporting** on this repository
  ([Security > Report a vulnerability](https://github.com/indrasol/taskadence-python/security/advisories/new)), or
- email **srvcs.infra@indrasol.com** (the contact in [taskadence.com/.well-known/security.txt](https://taskadence.com/.well-known/security.txt)).

Include a description, the affected package and version (`python -c "import taskadence; print(taskadence.__version__)"`,
`taskadence-mcp --version` or `npx -y @taskadence/mcp --version`) and steps to reproduce. Please do not include live
access tokens; a token prefix (`tkd_live_ab12…`) is enough.

We acknowledge a report within **3 business days**, send an assessment within **10 business days**, and credit reporters
who want to be credited once a fix is released. Please give us a reasonable window to fix before any disclosure.

## Supported versions

| Version | Supported |
|---|---|
| `1.x` | The latest `1.x` release. Fixes ship as a new `1.x`; semver applies (no breaking change within `1.x`). |
| `0.x` (pre-release) | Not supported. Upgrade to `1.x`. |

## Update cadence

- Security fixes are released as soon as they are ready, outside any schedule.
- Dependencies are watched by Dependabot and `pip-audit` in CI; a High or Critical advisory in a runtime dependency
  blocks the build until it is fixed or documented as not reachable.
- The SDK is regenerated whenever the public API's OpenAPI changes; the API's own security fixes need no SDK release
  unless the contract changes.

## Handling credentials

The SDK never logs the access token (a test asserts it), never writes it anywhere except where you ask the CLI to
(`tm auth login`: the OS keyring, else `~/.config/taskadence/config.toml` with mode `600`), and sends it only in the
`Authorization` header to the base URL you configured. Webhook secrets are yours: `taskadence.webhooks.verify` reads
the one you pass and never stores it.

## Secrets in this repository

The SDK repository holds no credentials. The examples in `spec/openapi.public.json` and the generated models are
made-up values copied from the API's OpenAPI document. The `secrets` job in `.github/workflows/ci.yml` runs gitleaks
on every pull request and over the full history on pushes to `main`. Locally, `pre-commit install` enables the same
check on each commit (opt-in). `.gitleaks.toml` allowlists only those spec examples, by path and value shape. How
TasKadence handles security for the service itself is described at [taskadence.com/security](https://taskadence.com/security).
