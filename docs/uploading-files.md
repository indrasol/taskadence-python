# Uploading files

`tm.task_attachments.create(...)` and `tm.project_resources.upload(...)` (and `tm tasks attach` /
`tm projects upload` on the command line) send the file **straight to storage**, not through the API. The SDK asks the
API for an upload (`POST /v1/uploads`: the API checks your permission, the size, the file type and your organization's
storage before a byte is sent), receives a short-lived upload URL for one pending file (write-only, 15 minutes), streams
the file there with `PUT` in 1 MB chunks (never reading it whole into memory, retried with backoff on a server error or
a dropped connection), then calls `POST /v1/uploads/{upload_id}/complete`, where the API inspects and malware-scans the
file and attaches it. You get back the same model as always (`TaskAttachmentInDB`, `ProjectResourceInDB`), and a
refusal is the same typed error as always (`upload-too-large` 413, `upload-type-not-allowed` / `upload-type-mismatch`
415, `upload-rejected` 422, `storage-limit-reached` 402). **Limit: 100 MB per file.** Against an API without direct
uploads (it answers 404 to `POST /v1/uploads`), the SDK sends the file the old way, as multipart to the operation's own
route, so nothing changes for you either way. `is_inline=` and `project_name=` are only carried by that multipart route,
so passing one of them sends the file that way.

```python
from taskadence import Taskadence

with Taskadence() as tm:
    tm.task_attachments.create(task_id="T123456", file="report.pdf", title="Q3 report")
    with open("plan.xlsx", "rb") as handle:                      # a path, bytes, or a binary file object
        tm.project_resources.upload(
            project_id="P96441", file=handle, progress=lambda sent, total: print(f"{sent}/{total}")
        )
```

The upload URL is a credential: the SDK never logs it or puts it in an exception (both show the URL without its query
string). A storage failure after the retries is `taskadence.BlobUploadError` (`.status`, `.code`, e.g. 403
`AuthenticationFailed` when the URL expired); nothing was attached, so calling the method again starts a fresh upload.
