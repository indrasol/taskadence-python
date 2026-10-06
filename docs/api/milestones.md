# `tm.milestones`

Milestones: titled dates a project commits to, holding its tasks - one project's, or every project's you can read at once (`GET /v1/milestones`).

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.milestones.list_org(org_id: str, sort_by: str | None = None, sort_order: str | None = None, filter: Mapping[str, Any] | None = None, if_none_match: str | None = None)`

Every milestone you can read in an organization, grouped by project.

- **HTTP:** `GET /v1/milestones`
- **operationId:** `milestones.list_org`
- **Token scope:** `projects:read`
- **Returns:** `OrgMilestonesOut`
- **`filter=` keys:** `project`, `status`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.milestones.list(project_id: str, include_tasks: bool | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a project's milestones.

- **HTTP:** `GET /v1/projects/{project_id}/milestones`
- **operationId:** `milestones.list`
- **Token scope:** `projects:read`
- **Returns:** `Page[MilestoneOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.milestones.create(project_id: str, body: MilestoneCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Create a milestone in a project.

- **HTTP:** `POST /v1/projects/{project_id}/milestones`
- **operationId:** `milestones.create`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneOut`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.milestones.reorder(project_id: str, body: MilestoneOrder | Mapping[str, Any])`

Reorder a project's milestones.

- **HTTP:** `POST /v1/projects/{project_id}/milestones/reorder`
- **operationId:** `milestones.reorder`
- **Token scope:** `projects:write`
- **Returns:** `MilestonesReordered`

## `tm.milestones.replace(project_id: str, milestone_id: str, body: MilestoneUpdate | Mapping[str, Any])`

Update / close a milestone (PUT; partial).

- **HTTP:** `PUT /v1/projects/{project_id}/milestones/{milestone_id}`
- **operationId:** `milestones.replace`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneOut`

## `tm.milestones.update(project_id: str, milestone_id: str, body: MilestoneUpdate | Mapping[str, Any])`

Update / close a milestone (JSON merge-patch).

- **HTTP:** `PATCH /v1/projects/{project_id}/milestones/{milestone_id}`
- **operationId:** `milestones.update`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneOut`

## `tm.milestones.delete(project_id: str, milestone_id: str, reason: str | None = None)`

Delete a milestone (its tasks are unfiled).

- **HTTP:** `DELETE /v1/projects/{project_id}/milestones/{milestone_id}`
- **operationId:** `milestones.delete`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneDeleted`

## `tm.milestones.move(project_id: str, milestone_id: str, body: MilestoneMove | Mapping[str, Any])`

Move a milestone and its tasks to another project.

- **HTTP:** `POST /v1/projects/{project_id}/milestones/{milestone_id}/move`
- **operationId:** `milestones.move`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneMoved`

## `tm.milestones.file_tasks(project_id: str, milestone_id: str, body: MilestoneTasksFile | Mapping[str, Any])`

File tasks under a milestone.

- **HTTP:** `POST /v1/projects/{project_id}/milestones/{milestone_id}/tasks`
- **operationId:** `milestones.file_tasks`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneTasksFiled`

## `tm.milestones.unfile_task(project_id: str, milestone_id: str, task_id: str)`

Take a task out of a milestone.

- **HTTP:** `DELETE /v1/projects/{project_id}/milestones/{milestone_id}/tasks/{task_id}`
- **operationId:** `milestones.unfile_task`
- **Token scope:** `projects:write`
- **Returns:** `MilestoneTaskUnfiled`
