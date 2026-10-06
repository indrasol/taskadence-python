# Contributing

Thanks for helping improve the TasKadence Python SDK and MCP packages. Bug reports and small, focused pull requests
are welcome. For anything larger, please open an issue first so we can agree on the approach.

## Ground rules

- **Never commit a token or secret**, not even an expired one. Fixtures use made-up values.
- **Security issues** go to private reporting, not issues or pull requests: see [SECURITY.md](SECURITY.md).
- The generated code is not edited by hand. `src/taskadence/_generated/`, `src/taskadence/_operations.py`,
  `src/taskadence/resources.py` and `docs/api/` come from `spec/openapi.public.json` through `scripts/generate.py`.
  Change the generator (or report a spec problem in an issue) instead.
- Prose says **TasKadence**; package names, imports, environment variables and URLs stay `taskadence` / `Taskadence`.

## Setup and checks

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                          # Python 3.11+ to regenerate; the SDK itself runs on 3.10+
python scripts/generate.py && git diff --stat    # must be empty unless you changed the generator
pytest && mypy && ruff check . && ruff format --check .

cd packages/taskadence-mcp && pip install -e ".[dev]" && pytest && mypy   # the Python MCP proxy
cd ../mcp-node && npm ci && npm run check                                  # the Node MCP proxy
```

Optional: `pip install pre-commit && pre-commit install` runs the same gitleaks secret scan as CI on each commit.

## Pull requests

Keep each pull request to one change, with tests, and add a line to `CHANGELOG.md` under `[Unreleased]`. CI must be
green (lint, tests on Python 3.10 to 3.13 and Node 20 / 22, regeneration, secret scan, workflow lint). By contributing
you agree that your contribution is licensed under the Apache License 2.0.
