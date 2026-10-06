# `tm.task_attachments`

Files attached to a task.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.task_attachments.create(task_id: str, file: FileInput, project_id: str | None = None, title: str | None = None, is_inline: bool | None = None)`

Upload an attachment to a task (multipart).

- **HTTP:** `POST /v1/task-attachments`
- **operationId:** `task-attachments.create`
- **Token scope:** `tasks:write`
- **Returns:** `TaskAttachmentInDB`

## `tm.task_attachments.list(task_id: str, inline: bool | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a task's attachments.

- **HTTP:** `GET /v1/task-attachments`
- **operationId:** `task-attachments.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[TaskAttachmentInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.task_attachments.read(attachment_id: str, if_none_match: str | None = None)`

Read an attachment's metadata.

- **HTTP:** `GET /v1/task-attachments/{attachment_id}`
- **operationId:** `task-attachments.read`
- **Token scope:** `tasks:read`
- **Returns:** `TaskAttachmentInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.task_attachments.update(attachment_id: str, body: TaskAttachmentUpdate | Mapping[str, Any], if_match: str | None = None)`

Rename an attachment.

- **HTTP:** `PUT /v1/task-attachments/{attachment_id}`
- **operationId:** `task-attachments.update`
- **Token scope:** `tasks:write`
- **Returns:** `TaskAttachmentInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.task_attachments.delete(attachment_id: str, if_match: str | None = None)`

Delete an attachment.

- **HTTP:** `DELETE /v1/task-attachments/{attachment_id}`
- **operationId:** `task-attachments.delete`
- **Token scope:** `tasks:write`
- **Returns:** `None`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.
