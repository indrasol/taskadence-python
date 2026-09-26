# `tm.tasks`

Tasks, the filter grammar and search (`GET /v1/tasks` with `filter[search]` IS search), and a task's links.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.tasks.create(body: TaskCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Create a task.

- **HTTP:** `POST /v1/tasks`
- **operationId:** `tasks.create`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.tasks.list(org_id: str | None = None, project_id: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None, include_inaccessible: bool | None = None, section_scope: str | None = None, filter: Mapping[str, Any] | None = None)`

List / search tasks (the filter grammar; `filter[search]` is search).

- **HTTP:** `GET /v1/tasks`
- **operationId:** `tasks.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[TaskCardView]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.
- **`filter=` keys:** `status`, `priority`, `assignee`, `project`, `tags`, `due_after`, `due_before`, `created_after`, `created_before`, `overdue`, `search`, `search_fields`, `team`, `task_type`

## `tm.tasks.read(task_id: str, if_none_match: str | None = None)`

Read a task.

- **HTTP:** `GET /v1/tasks/{task_id}`
- **operationId:** `tasks.read`
- **Token scope:** `tasks:read`
- **Returns:** `TaskInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.tasks.replace(task_id: str, body: TaskUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a task (PUT; partial).

- **HTTP:** `PUT /v1/tasks/{task_id}`
- **operationId:** `tasks.replace`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.tasks.update(task_id: str, body: TaskUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a task (JSON merge-patch).

- **HTTP:** `PATCH /v1/tasks/{task_id}`
- **operationId:** `tasks.update`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.tasks.delete(task_id: str, if_match: str | None = None)`

Delete a task.

- **HTTP:** `DELETE /v1/tasks/{task_id}`
- **operationId:** `tasks.delete`
- **Token scope:** `tasks:write`
- **Returns:** `Acknowledgement`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.tasks.set_project(task_id: str, body: TaskProjectSet | Mapping[str, Any])`

Move a task to another project (or unfile it).

- **HTTP:** `POST /v1/tasks/{task_id}/project`
- **operationId:** `tasks.set_project`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`

## `tm.tasks.set_sprint(task_id: str, body: TaskSprintSet | Mapping[str, Any])`

File a task in a team sprint (or none).

- **HTTP:** `PUT /v1/tasks/{task_id}/sprint`
- **operationId:** `tasks.set_sprint`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`

## `tm.tasks.set_milestone(task_id: str, body: TaskMilestoneSet | Mapping[str, Any])`

Attach a task to a team milestone (or none).

- **HTTP:** `PUT /v1/tasks/{task_id}/milestone`
- **operationId:** `tasks.set_milestone`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`

## `tm.tasks.set_section(task_id: str, body: TaskSectionSet | Mapping[str, Any])`

Place a task in a section.

- **HTTP:** `PUT /v1/tasks/{task_id}/section`
- **operationId:** `tasks.set_section`
- **Token scope:** `tasks:write`
- **Returns:** `TaskSectionOut`

## `tm.tasks.add_subtask(task_id: str, body: SubtaskLink | Mapping[str, Any])`

Add a subtask link.

- **HTTP:** `POST /v1/tasks/{task_id}/subtasks`
- **operationId:** `tasks.add_subtask`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`

## `tm.tasks.remove_subtask(task_id: str, subtask_id: str)`

Remove a subtask link.

- **HTTP:** `DELETE /v1/tasks/{task_id}/subtasks/{subtask_id}`
- **operationId:** `tasks.remove_subtask`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`

## `tm.tasks.add_dependency(task_id: str, body: DependencyLink | Mapping[str, Any])`

Add a dependency.

- **HTTP:** `POST /v1/tasks/{task_id}/dependencies`
- **operationId:** `tasks.add_dependency`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`

## `tm.tasks.remove_dependency(task_id: str, dependency_id: str)`

Remove a dependency.

- **HTTP:** `DELETE /v1/tasks/{task_id}/dependencies/{dependency_id}`
- **operationId:** `tasks.remove_dependency`
- **Token scope:** `tasks:write`
- **Returns:** `TaskInDB`
