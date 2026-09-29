# Security policy

## Reporting a vulnerability

Please report security issues **privately** — never in a public issue, pull request or discussion.

- Use GitHub's **private vulnerability reporting** on this repository (Security → Report a vulnerability) with a
  description, the affected version (`python -c "import tasksmate; print(tasksmate.__version__)"`) and steps to
  reproduce. Please do not include live access tokens; a token prefix (`tm_live_ab12…`) is enough.
- A security email address joins this file with TasksMate's `security.txt` (task S.16).

We acknowledge a report within **3 business days**, send an assessment within **10 business days**, and credit reporters
who want to be credited once a fix is released. Please give us a reasonable window to fix before any disclosure.

## Supported versions

| Version | Supported |
|---|---|
| `0.x` (pre-release) | The latest `0.x` release only. `0.x` carries no compatibility promise; fixes ship as a new `0.x`. |
| `1.x` | Not released yet (task S.23, the stability gate). |

## Update cadence

- Security fixes are released as soon as they are ready, outside any schedule.
- Dependencies are watched by Dependabot and `pip-audit` in CI; a High or Critical advisory in a runtime dependency
  blocks the build until it is fixed or documented as not reachable.
- The SDK is regenerated whenever the public API's OpenAPI changes; the API's own security fixes need no SDK release
  unless the contract changes.

## Handling credentials

The SDK never logs the access token (a test asserts it), never writes it anywhere except where you ask the CLI to
(`tm auth login`: the OS keyring, else `~/.config/tasksmate/config.toml` with mode `600`), and sends it only in the
`Authorization` header to the base URL you configured. Webhook secrets are yours: `tasksmate.webhooks.verify` reads
the one you pass and never stores it.

## Secrets in this repository

The SDK repository holds no credentials. The examples in `spec/openapi.public.json` and the generated models are
made-up values copied from the API's OpenAPI document. The `secrets` job in `.github/workflows/ci.yml` runs gitleaks
on every pull request and over the full history on pushes to `main`. Locally, `pre-commit install` enables the same
check on each commit (opt-in). `.gitleaks.toml` allowlists only those spec examples, by path and value shape. How
TasksMate handles its own secrets, and how they are rotated, is in the API's security policy
(`Tasks-Mate-Backend/SECURITY.md`).
