# `tm.task_comments`

Comments on a task (threaded).

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.task_comments.create(body: TaskCommentCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Comment on a task.

- **HTTP:** `POST /v1/task-comments`
- **operationId:** `task-comments.create`
- **Token scope:** `tasks:write`
- **Returns:** `TaskCommentInDB`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.task_comments.list(task_id: str, search: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a task's comments (threaded).

- **HTTP:** `GET /v1/task-comments`
- **operationId:** `task-comments.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[TaskCommentInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.task_comments.reply(body: ReplyCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Reply to a comment.

- **HTTP:** `POST /v1/task-comments/reply`
- **operationId:** `task-comments.reply`
- **Token scope:** `tasks:write`
- **Returns:** `TaskCommentInDB`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.task_comments.read(comment_id: str, if_none_match: str | None = None)`

Read a comment.

- **HTTP:** `GET /v1/task-comments/{comment_id}`
- **operationId:** `task-comments.read`
- **Token scope:** `tasks:read`
- **Returns:** `TaskCommentInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.task_comments.update(comment_id: str, body: TaskCommentUpdate | Mapping[str, Any], if_match: str | None = None)`

Edit your comment.

- **HTTP:** `PUT /v1/task-comments/{comment_id}`
- **operationId:** `task-comments.update`
- **Token scope:** `tasks:write`
- **Returns:** `TaskCommentInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.task_comments.delete(comment_id: str, if_match: str | None = None)`

Delete a comment.

- **HTTP:** `DELETE /v1/task-comments/{comment_id}`
- **operationId:** `task-comments.delete`
- **Token scope:** `tasks:write`
- **Returns:** `Acknowledgement`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.
