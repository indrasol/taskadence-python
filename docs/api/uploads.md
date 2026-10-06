# `tm.uploads`

Direct uploads: ask for a URL, PUT the file straight to storage, then finish. The standard way to upload a file, and the only one that is practical at 100 MB. The multipart routes under `task-attachments` and `project-resources` still work for clients that cannot PUT.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.uploads.create(body: UploadCreateIn | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Start a direct upload: a short-lived URL to PUT the file to, and the id to finish with.

- **HTTP:** `POST /v1/uploads`
- **operationId:** `uploads.create`
- **Returns:** `UploadCreateOut`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.uploads.complete(upload_id: str, body: UploadCompleteIn | Mapping[str, Any] | None = None, idempotency_key: str | None = AUTO)`

Finish a direct upload: the file is checked and becomes an attachment or a project file.

- **HTTP:** `POST /v1/uploads/{upload_id}/complete`
- **operationId:** `uploads.complete`
- **Returns:** `TaskAttachmentInDB | ProjectResourceInDB`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.
