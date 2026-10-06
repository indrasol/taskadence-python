# Changelog

All notable changes to `taskadence` (the TasKadence Python SDK), `taskadence-mcp` and `@taskadence/mcp`, which are
released together from one tag. The format follows [Keep a Changelog](https://keepachangelog.com/). Versions follow
semver, and **`0.x` is a pre-release with no compatibility promise** until 1.0.

## [Unreleased]

### Changed
- READMEs (S.23b): the PyPI and npm pages open with "Get started in 3 steps" (token, install, first call with its
  expected output) and "Key ideas"; the MCP READMEs with "Set up in 3 steps" (copy-paste configs for Claude Desktop,
  Claude Code, Cursor and VS Code), "Check it works" and Troubleshooting. Retries, idempotency, ETags, deprecations
  and logging moved under "Advanced". Every link is absolute and checked in CI (`scripts/check_readme_links.py`); a
  test keeps the two MCP READMEs in sync. Examples use placeholder ids (`O123456`, `T123456`) and future dates.
- Uploads go straight to storage: `task_attachments.create` and `project_resources.upload` (sync and async) create an
  upload (`POST /v1/uploads`), stream the file to its upload URL (1 MB chunks, never read whole; retried on 5xx and
  connection failures) and complete it (`POST /v1/uploads/{upload_id}/complete`), returning the same models as before.
  The limit is 100 MB per file. Every argument (`is_inline`, `project_name`, `title`) goes through the direct flow. An
  API without direct uploads (its router's plain 404, or a 405) gets multipart as before, so the switch is automatic; a
  404 about the task / project itself is raised as `NotFoundError`. Signatures are unchanged apart from a new optional
  `progress(sent, total)` argument.
- The spec is pinned to API `dev` `af56676` (release 2): the upload limit is 100 MB, the included storage 10 GB, the
  wordmark is TasKadence, `organization_invites.mine` takes `status`, and `sso-required` (403) is a problem type.
- `TaskAttachmentInDB` and `ProjectResourceInDB` carry `size_bytes`, the stored file's size in bytes, on every response
  that returns them (create, read, list, update); it is null when nothing is stored (a link resource).

### Added
- `tm.uploads.create` / `tm.uploads.complete` (`POST /v1/uploads`, `POST /v1/uploads/{upload_id}/complete`), the
  direct-upload operations; the upload methods use them for you.
- CLI `tm tasks attach TASK_ID FILE` and `tm projects upload PROJECT_ID FILE` (`--title`, `--json`), with a progress bar.
- `taskadence.BlobUploadError`: the storage `PUT` failed after its retries (`.status`, `.code`; the URL is redacted).
- `taskadence.UploadProgress`: the type of the `progress` callback.

### Security
- The signed upload URL never reaches a log line or an exception: the SDK logs it without its query string, and a
  filter on the `httpx` logger strips the query from signed storage URLs.

## [0.1.0] - 2026-10-05

The first public release of TasKadence's Python SDK, command line and local MCP packages.

### Added
- `taskadence` on PyPI: `Taskadence` / `AsyncTaskadence` with `tm.<resource>.<verb>(…)` for every public operation of
  API `2026-09-25` (166 operations in 30 resources), generated from the public OpenAPI contract.
- Auto-paging lists, typed problem+json exceptions with `request_id`, retries with backoff and `Retry-After`,
  automatic `Idempotency-Key` on creates, `ETag` / `If-Match` / `If-None-Match`, deprecation warnings.
- `to_dataframe()` on pages (`pip install "taskadence[pandas]"`) and `taskadence.webhooks.verify` / `parse`
  (Standard Webhooks signatures, rotation aware).
- The `tm` command line (`pip install "taskadence[cli]"`, also installed as `taskadence`): `auth`, `me`, `tasks`,
  `projects`, `views`, `webhooks`, `tokens`, `storage`.
- `taskadence-mcp` on PyPI (`uvx taskadence-mcp`) and `@taskadence/mcp` on npm (`npx -y @taskadence/mcp`): stdio
  proxies to the TasKadence remote MCP server for clients that start a local process.
- Releases are built in GitHub Actions with trusted publishing (no long-lived tokens), a CycloneDX SBOM per artefact,
  and npm provenance.

### Changed
- Prose, help text and messages use the TasKadence wordmark. Package names, imports, environment variables and URLs
  are unchanged (`taskadence`, `Taskadence`, `TASKADENCE_*`).

## Development history before 0.1.0 (never published)

### Added (B.2: the storage meter)
- (B.2) `tm.organizations.storage(org_id)` → `StorageUsage`: bytes used of the included 1 TB, `status`
  (`ok` / `warning` / `blocked` / `metered` / `exempt`), the breakdown by kind and project, the largest files, the 30-day trend.
- (B.2) CLI `tm storage [--org O…] [--json]` (also `taskadence storage`).
- (B.3) Problem type `urn:taskadence:problem:storage-limit-reached` (402 on an upload when the organization is full with no
  payment method on file).

### Fixed (spec from backend `5fa0aa4`)
- `ProjectStatusEnum` no longer lists `active`: the API never stored it (a create / update with it was a 500). A project
  being worked on is `in_progress`. A status outside the list is now a 422 `invalid-parameter` problem whose
  `errors[].allowed` names the accepted values, raised as the new `InvalidValueError`. It subclasses both
  `ValidationError` (what the same request raised before, so `except ValidationError` still catches it) and
  `InvalidParameterError`.

### Changed (5.8: the product is TasKadence; nothing was published under the old names, so there is no shim)
- (5.8) Distributions `taskadence` / `taskadence-mcp` (PyPI) and `@taskadence/mcp` (npm); was `tasksmate` / `tasksmate-mcp` / `@tasksmate/mcp`.
- (5.8) Import `taskadence` (`Taskadence`, `AsyncTaskadence`, `TaskadenceError`); was `tasksmate` (`TasksMate`, …). No `tasksmate` import shim.
- (5.8) CLI: `tm` stays, plus a `taskadence` entry point; MCP binary `taskadence-mcp`. Default API `https://api.taskadence.com`.
- (5.8) Environment `TASKADENCE_*`; a `TASKSMATE_*` variable still works when the new one is unset, with a DeprecationWarning.
- (5.8) Problem types `urn:taskadence:problem:*`; `urn:tasksmate:problem:*` maps to the same exceptions.
- (5.8) Tokens are minted as `tkd_live_` / `tkd_test_`; `tm_live_` / `tm_test_` tokens keep working (CLI login, redaction).
- (5.8) The CLI still reads a token stored under keyring service `tasksmate` or in `~/.config/tasksmate/`; logout clears both.
- Spec from backend `b34364d`: + `audit.export_json` (`GET /v1/audit.json`, `AuditExportRow`), MFA / upload problem types (mapped by status), access-review MFA and projects; 165 operations (was 164).
- (5.8) Request header `Taskadence-Version` (was `TasksMate-Version`; informational, the API ignores it).

### Added
- `Taskadence` / `AsyncTaskadence`: `tm.<resource>.<verb>(…)` for all 152 public operations of API `2026-09-25`,
  generated from `spec/openapi.public.json` (openapi-python-client 0.29.1 + a generated facade).
- Auto-paging lists (`Page` / `AsyncPage`), typed problem+json exceptions with `request_id`, retries with backoff and
  `Retry-After`, automatic `Idempotency-Key` on creates, `ETag` / `If-Match` / `If-None-Match`, deprecation warnings.
- `to_dataframe()` on pages (the `pandas` extra).
- `taskadence.webhooks.verify` / `parse` (Standard Webhooks signatures, rotation aware).
- The `tm` CLI (the `cli` extra): `auth`, `me`, `tasks`, `projects`, `views`, `webhooks`, `tokens`.
- `examples/streamlit_dashboard`.

### Changed (5.9: spec from backend `cc02a20`: milestones are project-scoped)
- **0.x: `milestones` is replaced, not deprecated** (pre-release). A milestone now belongs to a PROJECT (Project →
  Milestone → Task, like goals): `milestones.list(project_id)`, `create(project_id, {title, target_date, …})`,
  `update` / `replace(project_id, milestone_id, …)` (the milestone's owner may send `status` alone), `delete`,
  `reorder(project_id, {milestone_ids})`, `move(project_id, milestone_id, {project_id})` (with its tasks,
  all-or-nothing), `file_tasks(project_id, milestone_id, {task_ids})`, `unfile_task(…)`. The team routes are gone
  (`list(team_id)` / `create(team_id, …)` no longer exist).
- `milestones.list_org(org_id=…)` returns `OrgMilestonesOut`, grouped by project, the shape of `goals.list_org`, each
  milestone with `project_name` and each group with `milestones_tasks_total` / `_completed` (not a `Page`); narrow it
  with `filter={"project": …, "status": "open" | "closed"}`, sort with `sort_by` (`project_name` orders the groups).
- `tasks.set_milestone` takes a milestone of the task's own PROJECT (422 otherwise); moving a task to another project
  clears it. `milestones.create` sends an `Idempotency-Key` like every create.
- Webhooks: `milestone.*` payloads carry `project_id` (they carried `team_id`); + `milestone.reordered` / `milestone.moved`.
- 164 operations (was 159).

### Removed (5.7: spec from backend `ef1e262`: the Roadmap removed before release)
- **0.x: the `roadmap` resource is gone before any release**: the Roadmap was not shipped (it overlapped with
  milestones). `tm.roadmap.org / project / team / task_stops`, the `Roadmap*` / `TaskRoadmapStop*` models,
  `MilestoneOut.stop_id` and the ten `roadmap_journey.*` / `roadmap_stop.*` webhook events are removed; the task list
  never had a `stop` filter in the SDK, and the API now answers `filter[stop]` with a 400.
- 159 operations (was 162).

### Added (5.7)
- `milestones.list_org(org_id=…)`: every milestone you can read across the organization's teams (`GET /v1/milestones`),
  each a `MilestoneOrgOut` (the team milestone plus `team_name`); the API narrows it with `filter[team]` /
  `filter[status]` and sorts by `target_date`, `title`, `closed_at`, `created_at` or `team_name`.

### Changed (5.5: spec from backend `7de395c`: 5.2 registration, 5.4 agent-task review, 5.3 MCP clients)
- 162 operations (was 160): `tasks.review(task_id, {"decision": "accept" | "reject"})` (accept or reject a task an agent
  created) and `mcp.clients()` (the MCP server's clients table). `tasks.list` takes `filter={"created_via": …,
  "review": …}`; tasks carry `created_via` / `review_state` / `proposed_project_id`; organization settings carry
  `agent_task_review`; the `task.reviewed` webhook event.
- `TaskTypeEnum` is `task` · `bug`; `agent` is retired (who made a task is `created_via`).
- `POST /oauth/register` (RFC 7591, `x-kind: oauth`) is protocol, not a method, like the other `/oauth/*` routes.

### Added (5.3: the stdio MCP packages, `packages/`)
- `taskadence-mcp` (Python, `uvx taskadence-mcp`) and `@taskadence/mcp` (Node, `npx -y @taskadence/mcp`): stdio ↔
  Streamable HTTP proxies to TasKadence's remote MCP server, with no tool code of their own. `TASKADENCE_TOKEN` (required),
  `TASKADENCE_API_URL`, `TASKADENCE_MCP_READONLY`, `TASKADENCE_MCP_GROUPS` (or `--api-url`, `--readonly`, `--groups`). A
  refused token / an HTTP refusal / an unreachable server is a JSON-RPC error (`-32001` / `-32002` / `-32003`) and one
  stderr line, never the token.
- CI tests both (Python 3.10–3.13, Node 20 / 22); `release.yml` builds, checks and SBOMs all three artefacts from one
  tag, TestPyPI for both Python distributions, npm behind the same S.23 gate as PyPI. Nothing published.

### Changed (4.7: spec from backend `8b86aa0`: 4.8 OAuth apps, 4.9 views of projects)
- 160 operations (was 152): `oauth_clients.*` (list, create, read, update, delete, rotate_secret) and
  `connected_apps.list` / `connected_apps.delete`. The five OAuth 2.1 protocol operations (`x-kind: oauth`:
  `/oauth/authorize`, `/oauth/token`, `/oauth/revoke`, the two `/.well-known/*` documents) are **not** methods: the
  generator drops them; an app's access token is used as `Taskadence(token=…)` like any other.
- `views.create` / `views.update` / `views.list` know `resource` (`ViewResourceEnum`: `task` | `project`).

### Changed (4.1b: licence)
- Licensed under **Apache-2.0** (was MIT): an explicit patent grant and no trademark rights; `NOTICE` added.

### Changed (4.1b: spec from backend `6b75d01`)
- `webhooks.parse` returns the **generated** `WebhookEvent` (the spec now describes the webhook body and has a `webhooks`
  map); the event type is `event.type_`, extra fields land in `additional_properties`, and a body that is not an event
  raises `webhooks.WebhookParseError`. `pydantic` is no longer a dependency.
- `tasks.add_subtask` / `tasks.add_dependency` take the named `SubtaskLink` / `DependencyLink` bodies.
- `project_resources.upload` sends `project_id` once (the query); the API no longer declares it as a form field.
- The generator no longer strips update-body defaults (the API stopped advertising them) and reads list / create from
  the spec's `x-kind`; it refuses a spec that regresses on either.
