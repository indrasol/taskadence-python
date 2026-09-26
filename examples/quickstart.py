"""The quickstart, end to end — and the CI integration check (`pytest -m integration` runs it).

    export TASKSMATE_TOKEN=tm_live_… TASKSMATE_ORG=O0020      # + TASKSMATE_API_URL=http://localhost:8000 for dev
    python examples/quickstart.py

The three lines everyone starts with, then a round trip that leaves nothing behind: create a task → update it with
the ETag it was read with (If-Match) → list with a filter → `to_dataframe()` → delete it. A saved view is created for
`tm.views.rows(...)` and deleted too. Needs a token with `tasks:write`.
"""

from __future__ import annotations

import os
import sys

from tasksmate import NotModified, PreconditionFailedError, TasksMate


def main() -> int:
    org_id = os.environ["TASKSMATE_ORG"]

    # --- the three lines ----------------------------------------------------------------------------------------
    tm = TasksMate()  # token from TASKSMATE_TOKEN
    for t in tm.tasks.list(org_id=org_id):
        print(f"  {t.task_id}  {t.status:<12} {t.title}")
    # (tm.views.rows(view_id).to_dataframe() is below, once there is a view to read)

    # --- the round trip -----------------------------------------------------------------------------------------
    me = tm.me()
    print(f"me: {me.principal.username} ({me.principal.type_}); API {tm.base_url}, version {tm.api_version}")
    created = tm.tasks.create({"org_id": org_id, "title": "4.5 SDK quickstart (deleted at the end)", "priority": "low"})
    print(f"created {created.task_id}: status={created.status} priority={created.priority}")
    view_id = None
    try:
        current = tm.tasks.get(created.task_id)
        print(f"read {current.task_id} with ETag {current.etag}")
        assert tm.tasks.get(created.task_id, if_none_match=current.etag) is NotModified
        print("read again with If-None-Match: NotModified (304)")

        updated = tm.tasks.update(created.task_id, {"status": "in_progress"}, if_match=current.etag)
        print(f"updated with If-Match: status={updated.status} priority={updated.priority} (priority untouched)")
        try:
            tm.tasks.update(created.task_id, {"status": "blocked"}, if_match=current.etag)
        except PreconditionFailedError as exc:
            print(
                f"a second write with the stale ETag: {type(exc).__name__} {exc.status} (request_id {exc.request_id})"
            )
        else:
            raise AssertionError("a write with a stale ETag must be refused (412)")

        page = tm.tasks.list(org_id=org_id, filter={"status": ["in_progress"], "search": "4.5 SDK quickstart"})
        found = [t.task_id for t in page]
        print(f"list filter[status]=in_progress & filter[search]: {found}")
        assert created.task_id in found

        frame = tm.tasks.list(org_id=org_id).to_dataframe()
        print(f"tm.tasks.list(org_id=…).to_dataframe().shape = {frame.shape}")

        view = tm.views.create(
            {"org_id": org_id, "name": "4.5 SDK quickstart", "query": {"filter[status]": "in_progress"}}
        )
        view_id = view.view_id
        rows = tm.views.rows(view_id).to_dataframe()
        print(f"tm.views.rows({view_id}).to_dataframe().shape = {rows.shape}")
    finally:
        tm.tasks.delete(created.task_id)
        print(f"deleted {created.task_id}")
        if view_id:
            tm.views.delete(view_id)
            print(f"deleted view {view_id}")
    tm.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
