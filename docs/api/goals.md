# `tm.goals`

Goals: named containers of a project's tasks.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.goals.org(org_id: str, if_none_match: str | None = None)`

Every goal you can read in an organization, grouped by project.

- **HTTP:** `GET /v1/goals`
- **operationId:** `goals.org`
- **Token scope:** `projects:read`
- **Returns:** `OrgGoalsOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.goals.list(project_id: str, include_tasks: bool | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a project's goals.

- **HTTP:** `GET /v1/projects/{project_id}/goals`
- **operationId:** `goals.list`
- **Token scope:** `projects:read`
- **Returns:** `Page[GoalOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.goals.create(project_id: str, body: GoalCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Create a goal in a project.

- **HTTP:** `POST /v1/projects/{project_id}/goals`
- **operationId:** `goals.create`
- **Token scope:** `projects:write`
- **Returns:** `GoalOut`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.goals.reorder(project_id: str, body: GoalOrder | Mapping[str, Any])`

Reorder a project's goals.

- **HTTP:** `POST /v1/projects/{project_id}/goals/reorder`
- **operationId:** `goals.reorder`
- **Token scope:** `projects:write`
- **Returns:** `GoalsReordered`

## `tm.goals.replace(project_id: str, goal_id: str, body: GoalUpdate | Mapping[str, Any])`

Update a goal (PUT; partial).

- **HTTP:** `PUT /v1/projects/{project_id}/goals/{goal_id}`
- **operationId:** `goals.replace`
- **Token scope:** `projects:write`
- **Returns:** `GoalOut`

## `tm.goals.update(project_id: str, goal_id: str, body: GoalUpdate | Mapping[str, Any])`

Update a goal (JSON merge-patch).

- **HTTP:** `PATCH /v1/projects/{project_id}/goals/{goal_id}`
- **operationId:** `goals.update`
- **Token scope:** `projects:write`
- **Returns:** `GoalOut`

## `tm.goals.delete(project_id: str, goal_id: str, reason: str | None = None)`

Delete a goal (its tasks are unfiled).

- **HTTP:** `DELETE /v1/projects/{project_id}/goals/{goal_id}`
- **operationId:** `goals.delete`
- **Token scope:** `projects:write`
- **Returns:** `GoalDeleted`

## `tm.goals.move(project_id: str, goal_id: str, body: GoalMove | Mapping[str, Any])`

Move a goal and its tasks to another project.

- **HTTP:** `POST /v1/projects/{project_id}/goals/{goal_id}/move`
- **operationId:** `goals.move`
- **Token scope:** `projects:write`
- **Returns:** `GoalMoved`

## `tm.goals.file_tasks(project_id: str, goal_id: str, body: GoalTasksFile | Mapping[str, Any])`

File tasks under a goal.

- **HTTP:** `POST /v1/projects/{project_id}/goals/{goal_id}/tasks`
- **operationId:** `goals.file_tasks`
- **Token scope:** `projects:write`
- **Returns:** `GoalTasksFiled`

## `tm.goals.unfile_task(project_id: str, goal_id: str, task_id: str)`

Take a task out of a goal.

- **HTTP:** `DELETE /v1/projects/{project_id}/goals/{goal_id}/tasks/{task_id}`
- **operationId:** `goals.unfile_task`
- **Token scope:** `projects:write`
- **Returns:** `GoalTaskUnfiled`
