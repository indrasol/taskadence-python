# Changelog

All notable changes to `taskadence` (the TasKadence Python SDK), `taskadence-mcp` and `@taskadence/mcp`, which are
released together from one tag. The format follows [Keep a Changelog](https://keepachangelog.com/). From 1.0.0 the
versions follow semver and the API's [versioning policy](https://docs.taskadence.com/guides/versioning/); the `0.x`
entries below were pre-releases with no compatibility promise.

## [Unreleased]

## [2.0.0] - 2026-10-24

Release 10: sprints belong to projects, teams, sections and test sprints have left TasKadence, and organizations belong
to an account (one per email) that shares one storage pool, and the project roles are owner, member and viewer.
Re-generated from the API contract at `taskadence-api` `e124d44` (branch `feature/ia-redesign`); the API version is
now `2026-10-24` (was `2026-09-25`), so every request sends `TasKadence-Version: 2026-10-24`. A major version because
methods, models and fields are removed (the 1.0 promise: a breaking change needs a 2.0). The API stopped serving the removed routes in the same release, so 1.x calls to them now
answer 410 Gone (in 2.0, `RemovedInRelease10Error`). `taskadence-mcp` and `@taskadence/mcp` have no generated code and
change only their shared version.

### Removed
- **Teams:** `tm.teams` (`list`, `create`, `read` / `get`, `update`, `replace`, `delete`, `list_tasks`, `add_member`,
  `update_member`, `replace_member`, `remove_member`) and the models `TeamCreate`, `TeamUpdate`, `TeamOut`,
  `TeamDetail`, `TeamDeleted`, `TeamListPage`, `TeamListSummary`, `TeamMemberCreate`, `TeamMemberUpdate`,
  `TeamMemberOut`, `TeamRoleEnum`, `TeamTagOut`. `tm.view_pins.pin_team` / `unpin_team`.
- **Sections:** `tm.sections` (`list`, `create`, `update`, `delete`, `reorder`), `tm.tasks.set_section`, and the
  models `SectionCreate`, `SectionUpdate`, `SectionOut`, `PageSectionOut`, `SectionReorder`, `SectionScopeEnum`,
  `SectionsForScopes`, `ScopeRef`, `TaskSectionOut`, `TaskSectionSet`.
- **Test sprints:** the `tracker_id` and `bug_id` fields (the `bug` task type stays; list bugs with
  `filter={"task_type": "bug"}`).
- **Fields:** `team_id` on `TaskInDB`, `TaskCreate`, `TaskUpdate`, `TaskCardView`, the `TaskBatch*` models,
  `ProjectInDB`, `ProjectCard`, `ProjectCreate`, `ProjectUpdate` and `SprintOut`; `section_id` (and
  `TaskCardView.section_position`) on the task models; `AvailabilityRange.team_id` (now `org_id`) and
  `AvailabilityMember.team_role` (now `org_role`); `PinOut.logo_url`.
- **Task list:** the `team` filter key (`filter={"team": ...}` raises `ValueError`) and the `section_scope` argument.
- **Storage:** `StorageUsage.billing_exempt` (`tm.organizations.storage`): read `exempt_message` instead. The
  per-organization billing routes are gone (410); billing is the account owner's, in the web app, and not in the SDK.
- **Webhooks:** `team.created`, `team.updated`, `team.deleted`, `team.member_added`, `team.member_removed`,
  `team.member_role_changed`, `team.leads_changed`, `team.managers_changed`, `project.team_linked`,
  `project.team_unlinked`.
- **Project role `editor`:** `ProjectRoleEnum` is `owner | member | viewer` (was `owner | editor | viewer`); see
  Changed.
- The `teams:read` / `teams:write` scopes are retired by the API (a token that carries them keeps working; the scope
  is ignored). The SDK had no scope helper naming them.

### Changed
- **Sprints belong to a project.** `tm.sprints.list(project_id)` and `tm.sprints.create(project_id, body)` (were
  `team_id`); `tm.sprints.update(sprint_id, body)` is now a PATCH (JSON merge-patch) and `tm.sprints.delete(sprint_id)`
  takes the sprint id alone (both were `(team_id, sprint_id, ...)`). `SprintOut` has `project_id` and `position`;
  `SprintCreate` takes `position`; `SprintUpdate` takes `position` (reorder) and `project_id` (move an empty sprint;
  one holding tasks is a 409 `ConflictError`).
- **Capacity is organization-wide.** `tm.availability.range` / `create` / `update` / `delete` take `org_id` (were
  `team_id`): `GET|POST /v1/organizations/{org_id}/availability`, `PUT|DELETE .../availability/{entry_id}`.
- `tm.tasks.set_sprint(task_id, {"sprint_id": ...})` accepts only a sprint of the task's own project.
- **Projects say `members`.** `ProjectCreate`, `ProjectUpdate`, `ProjectInDB` and `ProjectCard` have `members` (was
  `team_members`; on a read, the members' user ids), and `ProjectStatsInDB.members` counts them. The SDK sends only
  `members` (the API still accepts `team_members` for one release).
- **Storage is the account's.** `tm.organizations.storage(org_id)` gains `account_id`, `account_used_bytes`,
  `account_quota_bytes`, `account_percent` and `exempt_message`; `included_bytes`, `overage_bytes` and `status` are
  the account's, and `percent` is the organization's share of the account's free storage.
- `tm storage` (the CLI) prints the account's totals and the exempt message.
- **Project roles are `owner`, `member` and `viewer`.** `editor` is now `member` (`ProjectMemberCreate`,
  `ProjectMemberUpdate`, `ProjectMemberInDB`, `ReviewProject.role`); the SDK sends `member`. For one release the API
  still accepts `editor` on input and always answers `member`, so a 1.x caller that sends `editor` keeps working.
- `ProjectInDB.members_can_add_people` (set with `ProjectUpdate`, by the project owner or an org admin): when true,
  the project's members may add and remove people and change their roles. `editors_can_add_members` is its
  deprecated old name (the same value, still answered; the API drops it in the next release).
- **Org owners and admins are owners of every project** of their organization without being added. Project member
  lists include them: `ProjectMemberInDB.source` is `member` (added to the project), `org_owner` or `org_admin`, and
  `removable` is False for the last two.
- **Ids grow past 6 digits.** The API widens a prefix's ids by itself as they fill up (`T1234567`, up to 12 digits).
  The SDK never checked an id's shape; it now has tests that ids of 6 to 12 digits pass through paths, models and
  webhook events unchanged. Do not assume six digits in your own code.

### Added
- `tm.projects.sprints(project_id)`: a project's sprints (the same call as `tm.sprints.list`).
- `tm.sprints.list_org(org_id=...)`: every sprint you can read in an organization, for Planning (`GET /v1/sprints`).
- `tm.sprints.read(sprint_id)` (also `get`).
- `tm.organizations.availability(org_id, from_=, to=)` (the same call as `tm.availability.range`) and
  `tm.me.set_availability(body)` (`PUT /v1/me/availability`, also `tm.availability.mark_mine`; model
  `MyAvailabilitySet`).
- `tm.organizations.workload(org_id, project_id=None)` (also `tm.workload.read`): open work per person, heaviest first.
  Models `WorkloadOut` (`people`, `totals`, `mean`, `as_of`, `truncated`), `WorkloadPerson` (`open_`, `in_progress`,
  `blocked`, `not_started`, `overdue`, `due_this_week`, `heavy`, `top`), `WorkloadCounts` and `WorkloadTask`.
  `open` is a Python builtin, so the generated attribute is `open_` (the JSON key stays `open`).
- `SprintProjectMismatchError` (also importable as `SprintProjectMismatch`), a `ConflictError`: the 409
  `urn:taskadence:problem:sprint-project-mismatch` when a task is filed in a sprint of another project.
  `errors[0]` names both projects.
- **The account (read-only, scope `account:read`).** `tm.account.get()` (also `read`; `GET /v1/account`): the
  account's organizations with their member counts and storage, the caller's `my_role`, `owner`, `can_create_orgs`,
  the storage pool and `billing.exempt_message` (set only for an exempt account; there is no exempt flag).
  `tm.account.people()` (`GET /v1/account/people`, account owners and admins): everyone in the account with their
  role in each organization. `tm.storage.get()` (also `tm.account.storage()`; `GET /v1/storage`): the account's
  `bytes_used`, `quota_bytes`, `available_bytes`, `overage_bytes`, `percent`, `status` (`ok` · `warning` · `blocked` ·
  `metered` · `exempt`), `payment_method_on_file` and the per-organization `orgs`. Models `AccountOut`, `AccountOrg`,
  `AccountOwner`, `AccountBillingBrief`, `AccountPeople`, `AccountPerson`, `PersonOrg`, `AccountStorage`,
  `AccountStorageOrg`. Writes on `/v1/account*` and billing are the web app's (session only) and not in the SDK.
- `tm.me()` / `tm.me.get()` has `account` (`MeAccount`: `account_id`, `name`, `role`; None for a principal without
  one).
- `WorkloadPerson.active_sprint` (`WorkloadSprint`: `sprint_id`, `name`, `done`, `total`): the person's current
  sprint (active, today inside its dates; the one ending soonest when several), or None.
- `EmailInOtherAccountError` (also `EmailInOtherAccount`), a `ConflictError`: the 409
  `urn:taskadence:problem:email-in-other-account` when an invitee's email already belongs to another account
  (`errors[0]["code"]` is `email_in_other_account`).
- `GoneError` (410) and `RemovedInRelease10Error` (also `RemovedInRelease10`): the 410
  `urn:taskadence:problem:removed-in-release-10` of a route release 10 removed; `.successor` names what to call
  instead (or None), `.changelog` links the docs changelog, and the message ends with that link. A 410 is never
  retried.
- Not in the SDK: support tickets (internal routes) and the MCP tool `contact_support`.
- **Batch members.** `tm.projects.members.add_many(project_id, [{"user_id", "project_role"}, ...])` (also
  `tm.project_members.create_batch`; `POST /v1/projects/{project_id}/members/batch`, scope `projects:write`): up to 50
  people, each with their own role, all or nothing. Returns `ProjectMembersBatchAdded`: `added` (the
  `ProjectMemberInDB` rows, in the order asked) and `skipped` (`ProjectMemberSkipped`: `user_id`, `reason`
  `already_member`). Models `ProjectMembersBatchAdd`, `ProjectMemberBatchItem`.
- **Task subscribers** get a task's assignment, comment and status emails (its creator and assignee are subscribed
  automatically). `tm.tasks.subscribers(task_id)` (also `list_subscribers`; scope `tasks:read`),
  `tm.tasks.set_subscribers(task_id, user_ids)` (the FULL list, up to 100), `tm.tasks.subscribe(task_id)` and
  `tm.tasks.unsubscribe(task_id)` (yourself; `tasks:write`); each returns `TaskSubscribers` (`subscribers`
  (`TaskSubscriber`), `subscriber_ids`, `is_subscribed`). `TaskInDB.subscriber_ids` and `is_subscribed` are set on
  single-task reads.
- `ProjectInDB.implicit_members` (`ProjectImplicitMember`: `user_id`, `username`, `project_role` owner, `source`
  `org_owner` / `org_admin`, `removable` False): the organization's owners and admins, on the single-project read.
- `tm.projects.list(org_id, scope="all" | "mine")`: `mine` is the projects you are in (every project for an org owner
  or admin), `all` (the default) every project you can read; the same as `show_all=False` / `True`.
- `OrganizationSettingsOut.only_admins_create_projects` (and on `OrganizationSettingsUpdate`): when true, only org
  owners and admins create projects.
- The generator: a body that is one array is taken as that array (`set_subscribers(task_id, user_ids)`,
  `add_many(project_id, members)`; a bare string or mapping is a `TypeError`), and a resource can carry a nested
  namespace (`tm.projects.members`).
- The README has Project members and roles and Task subscribers sections.
- `ProjectUpdate.position`: a project's place in the organization's order (owners and admins); `ProjectInDB.position`
  (the single-project read, `tm.projects.read`). `ProjectCard.position` is unchanged.
- Sub-projects (N.3, not released before): `ProjectCreate` / `ProjectUpdate` / `ProjectCard` / `ProjectInDB` carry
  `parent_project_id`; `ProjectCard.child_count`; `ProjectInDB.parent` (`ProjectRef`) and `children`
  (`ProjectChildOut`); `tm.projects.delete` returns `ProjectDeleted` (`children_detached`); `tm.tasks.list` takes
  `include_children`. Webhooks `project.parent_changed` and `project.children_detached`.
- Also not released before: `tm.tasks.create_batch` / `update_batch`, `tm.tasks.list_dependents`, `tm.tasks.reopen`,
  and their models; webhooks `member.admin_grants_changed` and `project.managers_changed`.
- `ProblemType` includes `urn:taskadence:problem:database-unavailable` (503: the database did not answer after
  retries, nothing was applied; retry after `Retry-After` seconds), `sprint-project-mismatch`, `sprint-not-empty`,
  `email-in-other-account` and `removed-in-release-10`.
- The quickstart (`examples/quickstart.py`) creates a project and a sprint, files its task in the sprint, and deletes
  them at the end; the README has a Sprints, capacity and workload section.

### Migrating from 1.x
- `tm.teams.*`, `tm.sections.*`: no replacement; group tasks with the list's `sort_by` / filters instead.
- `tm.sprints.list(team_id)` → `tm.projects.sprints(project_id)`, or `tm.sprints.list_org(org_id=...)` for all.
- `tm.availability.range(team_id, ...)` → `tm.organizations.availability(org_id, ...)`.
- `tm.sprints.update(team_id, sprint_id, body)` → `tm.sprints.update(sprint_id, body)`; the same for `delete`.
- `team_members=` on a project → `members=`; `storage.billing_exempt` → `storage.exempt_message is not None`.
- `except NotFoundError` around a removed route → `except RemovedInRelease10Error` (a 410 now, not a 404).
- `project_role="editor"` → `"member"` (and compare answers against `"member"`); `editors_can_add_members` →
  `members_can_add_people`.

## [1.0.0] - 2026-10-08

First stable release: the public API is /v1 and follows docs.taskadence.com/guides/versioning.

Re-generated from the API contract at `taskadence-api` `b3b5f14` (API version `2026-09-25`, unchanged). Additive only:
no public operation, model or field was removed since 0.1.1. `@taskadence/mcp` and `taskadence-mcp` have no generated
code and do not change beyond the shared version. This section was prepared as 0.1.2, which was never published.

### Stable
- `taskadence`, `taskadence-mcp` and `@taskadence/mcp` follow semver from here: a breaking change to a public method,
  model, field, CLI command or flag needs a 2.0, and anything deprecated warns first (the SDK issues a
  `DeprecationWarning` when the API answers with a `Deprecation` or `Sunset` header).
- The included storage is 10 GB per organization, as the API reports it (`included_bytes`); the SDK and `tm storage`
  show the API's figure rather than a constant of their own.
- The `tm` command line (`pip install "taskadence[cli]"`): `auth`, `me`, `tasks` (with `attach`), `projects` (with
  `upload`), `views`, `webhooks`, `tokens` and `storage`. Its commands, flags, `--json` output and exit codes
  (0, 1, 2) are covered by the same promise.

### Added
- `tm.organizations.storage_projects(org_id)`: every project holding files, largest first, with its file count and
  biggest file (`GET /v1/organizations/{org_id}/storage/projects`; one `PageStorageProject`, `limit` / `cursor`).
- `tm.organizations.storage_files(org_id)`: every counted file of the organization, largest first
  (`GET /v1/organizations/{org_id}/storage/files`; one `PageStorageFile`, `limit` / `cursor`).
- `StorageUsage.project_count`: projects holding at least one counted file.
- `StorageProject.file_count` and `StorageProject.largest` (a new `StorageFileBrief`: `kind`, `id`, `name`, `bytes`,
  `parent_id`, `project_id`), the project's biggest file.
- New models `StorageFileBrief`, `PageStorageProject`, `PageStorageFile`, and the `StorageFileBriefKind` literal
  (`task`, `project`, `bug`).

### Changed
- Docstrings state the upload limits in decimal bytes (100 MB = 100,000,000 bytes; an avatar 2 MB = 2,000,000 bytes),
  like the bill. The limits themselves are unchanged.
- Example `org_id` values in docstrings read `O123456`.

## [0.1.1] - 2026-10-06

First release published entirely through trusted publishing on PyPI and npm (with npm provenance). No API or
behaviour changes.

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

The items below were listed under Unreleased until 0.1.1; the `v0.1.0` tag was moved to the commit that has them,
so they shipped in 0.1.0.

### Also in 0.1.0: Changed
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

### Also in 0.1.0: Added
- `tm.uploads.create` / `tm.uploads.complete` (`POST /v1/uploads`, `POST /v1/uploads/{upload_id}/complete`), the
  direct-upload operations; the upload methods use them for you.
- CLI `tm tasks attach TASK_ID FILE` and `tm projects upload PROJECT_ID FILE` (`--title`, `--json`), with a progress bar.
- `taskadence.BlobUploadError`: the storage `PUT` failed after its retries (`.status`, `.code`; the URL is redacted).
- `taskadence.UploadProgress`: the type of the `progress` callback.

### Also in 0.1.0: Security
- The signed upload URL never reaches a log line or an exception: the SDK logs it without its query string, and a
  filter on the `httpx` logger strips the query from signed storage URLs.

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
