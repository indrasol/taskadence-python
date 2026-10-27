"""Release 10, step 4 (API `origin/dev` 2695ecb, PR #270): comment reactions and attachments, `include=subscribers` on
the task list, illustrated avatars, `member-not-linked`, the OAuth `resource` — through `respx`, bodies from the
spec's examples."""

from __future__ import annotations

import json
from typing import get_args

import pytest
import respx

import taskadence
from taskadence import (
    AsyncTaskadence,
    ConflictError,
    MemberNotLinked,
    MemberNotLinkedError,
    Taskadence,
    models,
    webhooks,
)

from .conftest import SPEC, card, example, operation, problem
from .test_webhooks_dataframe_async import BODY

REACTIONS = "/v1/tasks/T1/comments/C1/reactions"
THUMBS = "\N{THUMBS UP SIGN}"


def reactions(emoji: str = THUMBS, count: int = 1, mine: bool = True) -> dict[str, object]:
    return {
        "reactions": [
            {"emoji": emoji, "count": count, "reacted_by_me": mine, "people": [{"user_id": "U1", "name": "Ada"}]}
        ]
    }


def comment(**fields: object) -> dict[str, object]:
    body = example("task-comments.read") | {"comment_id": "C1", "task_id": "T1"}
    return body | fields


# ---------------------------------------------------------------------------
# reactions
# ---------------------------------------------------------------------------


def test_react_puts_the_emoji_in_the_path(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.put(f"{REACTIONS}/%F0%9F%91%8D").respond(json=reactions())
    got = tm.tasks.comments.react("T1", "C1", THUMBS)
    assert route.called and route.calls.last.request.content == b""
    assert isinstance(got, models.CommentReactions)
    (first,) = got.reactions
    assert (first.emoji, first.count, first.reacted_by_me) == (THUMBS, 1, True)
    assert first.people[0].user_id == "U1" and first.people[0].name == "Ada"


def test_unreact_deletes_your_reaction(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.delete(f"{REACTIONS}/%F0%9F%91%8D").respond(json={"reactions": []})
    assert tm.tasks.comments.unreact("T1", "C1", THUMBS).reactions == []
    assert route.called


def test_who_reacted_is_a_page_of_people(tm: Taskadence, api: respx.MockRouter) -> None:
    page = {"data": [{"user_id": "U1", "name": "Ada"}, {"user_id": "U2", "name": None}], "next_cursor": None}
    route = api.get(f"{REACTIONS}/%F0%9F%8E%89").respond(json=page)
    people = list(tm.tasks.comments.reactions("T1", "C1", "\N{PARTY POPPER}", limit=50))
    assert [p.user_id for p in people] == ["U1", "U2"] and isinstance(people[0], models.ReactionPerson)
    assert route.calls.last.request.url.params["limit"] == "50"


def test_the_nested_names_are_the_generated_methods(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.put(f"{REACTIONS}/%E2%9C%85").respond(json=reactions("\N{WHITE HEAVY CHECK MARK}"))
    tm.task_comments.add_reaction("T1", "C1", "\N{WHITE HEAVY CHECK MARK}")
    tm.tasks.comments.react("T1", "C1", "\N{WHITE HEAVY CHECK MARK}")
    assert route.call_count == 2
    assert taskadence.resources.RESOURCE_METHODS["task-comments.add_reaction"] == ("task_comments", "add_reaction")


def test_reaction_scopes() -> None:
    for op_id, scope in [
        ("task-comments.add_reaction", "tasks:write"),
        ("task-comments.remove_reaction", "tasks:write"),
        ("task-comments.list_reactions", "tasks:read"),
    ]:
        assert operation(op_id)[2]["x-scopes"] == [scope], op_id


def test_a_comment_carries_its_reactions_and_attachments(tm: Taskadence, api: respx.MockRouter) -> None:
    files = [
        {"attachment_id": "A1", "name": "plan.pdf", "size": 2048, "content_type": "application/pdf", "thumb": None}
    ]
    api.get("/v1/task-comments/C1").respond(json=comment(attachments=files, reactions=reactions()["reactions"]))
    got = tm.task_comments.read("C1")
    assert isinstance(got, models.TaskCommentInDB)
    assert got.attachments[0].attachment_id == "A1" and got.attachments[0].size == 2048
    assert isinstance(got.attachments[0], models.CommentAttachment)
    assert got.reactions[0].emoji == THUMBS and got.reactions[0].reacted_by_me is True


def test_a_reaction_webhook_parses() -> None:
    for name in ("task.comment_reaction_added", "task.comment_reaction_removed"):
        assert name in SPEC["webhooks"]
        body = json.loads(BODY) | {"type": name}
        body["data"] = {"resource_type": "task", "resource_id": "T1", "before": None}
        body["data"]["after"] = {"comment_id": "C1", "emoji": THUMBS}
        event = webhooks.parse(body)
        assert event.type_ == name and event.data.after is not None
        assert event.data.after["emoji"] == THUMBS


# ---------------------------------------------------------------------------
# comment attachments
# ---------------------------------------------------------------------------


def test_a_comment_links_up_to_five_uploaded_files(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/task-comments").respond(201, json=comment())
    tm.task_comments.create(models.TaskCommentCreate(task_id="T1", content="See the plan", attachment_ids=["A1", "A2"]))
    assert json.loads(route.calls.last.request.content)["attachment_ids"] == ["A1", "A2"]
    for name in ("TaskCommentCreate", "TaskCommentUpdate", "ReplyCreate"):
        ids = SPEC["components"]["schemas"][name]["properties"]["attachment_ids"]["anyOf"][0]
        assert ids["maxItems"] == 5, name


def test_an_edit_replaces_the_files_and_a_reply_takes_them_too(tm: Taskadence, api: respx.MockRouter) -> None:
    edit = api.put("/v1/task-comments/C1").respond(json=comment())
    tm.task_comments.update("C1", {"attachment_ids": []})
    assert json.loads(edit.calls.last.request.content) == {"attachment_ids": []}
    reply = api.post("/v1/task-comments/reply").respond(201, json=comment())
    tm.task_comments.reply({"comment_id": "C1", "content": "Here", "attachment_ids": ["A3"]})
    assert json.loads(reply.calls.last.request.content)["attachment_ids"] == ["A3"]


def test_an_attachment_says_which_comment_holds_it(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("task-attachments.read") | {"attachment_id": "A1", "comment_id": "C1", "purpose": "comment"}
    api.get("/v1/task-attachments/A1").respond(json=body)
    got = tm.task_attachments.read("A1")
    assert (got.comment_id, got.purpose) == ("C1", "comment")
    assert SPEC["components"]["schemas"]["UploadCreateIn"]["properties"]["purpose"]["anyOf"][0]["const"] == "comment"


# ---------------------------------------------------------------------------
# task list: include=subscribers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("include", [["subscribers"], "subscribers"])
def test_the_task_list_includes_subscribers_when_asked(
    tm: Taskadence, api: respx.MockRouter, include: list[str] | str
) -> None:
    row = card("T1", subscriber_count=4, subscribers_preview=[{"user_id": "U1", "name": "Ada"}])
    route = api.get("/v1/tasks").respond(json={"data": [row], "next_cursor": None})
    (got,) = list(tm.tasks.list(org_id="O1", include=include))
    assert route.calls.last.request.url.params["include"] == "subscribers"
    assert got.subscriber_count == 4 and got.subscribers_preview[0].user_id == "U1"
    assert isinstance(got.subscribers_preview[0], models.TaskSubscriberPreview)


def test_the_task_list_sends_no_include_unless_asked(tm: Taskadence, api: respx.MockRouter) -> None:
    row = card("T1")
    row.pop("subscriber_count", None)
    row.pop("subscribers_preview", None)
    route = api.get("/v1/tasks").respond(json={"data": [row], "next_cursor": None})
    (got,) = list(tm.tasks.list(org_id="O1"))
    assert "include" not in route.calls.last.request.url.params
    assert not got.subscriber_count and not got.subscribers_preview


# ---------------------------------------------------------------------------
# avatars, linked members, member-not-linked
# ---------------------------------------------------------------------------


def test_me_and_members_carry_the_avatar_preset(tm: Taskadence, api: respx.MockRouter) -> None:
    me = example("me.read")
    me["principal"] = me["principal"] | {"avatar_preset": "fox"}
    api.get("/v1/me").respond(json=me)
    assert tm.me().principal.avatar_preset == "fox"
    member = example("organization-members.read") | {"avatar_preset": "owl", "linked": False}
    api.get("/v1/organization-members/U1/O1").respond(json=member)
    got = tm.organization_members.read("U1", "O1")
    assert (got.avatar_preset, got.linked) == ("owl", False)
    assert "avatar_preset" in SPEC["components"]["schemas"]["ProjectMemberInDB"]["properties"]


def test_a_member_who_must_sign_in_again_is_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    body = problem(
        409,
        "urn:taskadence:problem:member-not-linked",
        "This member must sign in again before they can be subscribed.",
        errors=[{"code": "member_not_linked", "user_ids": ["U2", "U3"]}],
    )
    route = api.put("/v1/tasks/T1/subscribers").respond(409, json=body)
    with pytest.raises(MemberNotLinkedError) as caught:
        tm.tasks.set_subscribers("T1", ["U1", "U2", "U3"])
    err = caught.value
    assert isinstance(err, ConflictError) and MemberNotLinked is MemberNotLinkedError
    assert err.slug == "member-not-linked" and err.user_ids == ["U2", "U3"]
    assert route.call_count == 1
    assert "urn:taskadence:problem:member-not-linked" in get_args(models.ProblemType)
    types = {p["type"]: p["statuses"] for p in SPEC["x-problem-types"]}
    assert types["urn:taskadence:problem:member-not-linked"] == [409]


def test_member_not_linked_without_ids_names_nobody(tm: Taskadence, api: respx.MockRouter) -> None:
    api.put(f"{REACTIONS}/%F0%9F%91%8D").respond(409, json=problem(409, "urn:taskadence:problem:member-not-linked"))
    with pytest.raises(MemberNotLinkedError) as caught:
        tm.tasks.comments.react("T1", "C1", THUMBS)
    assert caught.value.user_ids == []


def test_rename_and_avatar_preset_are_not_sdk_methods() -> None:
    """`PATCH /v1/me/username` and `PUT /v1/me/avatar-preset` are internal (a signed-in session in the web app)."""
    assert not any(p in SPEC["paths"] for p in ("/v1/me/username", "/v1/me/avatar-preset"))
    assert not hasattr(taskadence.resources.MeResource, "rename_username")


# ---------------------------------------------------------------------------
# OAuth resource, the account's pending actions
# ---------------------------------------------------------------------------


def test_me_says_which_resource_an_oauth_token_is_bound_to(tm: Taskadence, api: respx.MockRouter) -> None:
    me = example("me.read")
    me["auth"] = {"token_id": "TK1", "scopes": ["tasks:read"], "resource": "https://api.taskadence.com/mcp"}
    api.get("/v1/me").respond(json=me)
    auth = tm.me().auth
    assert isinstance(auth, models.MeAuth) and auth.resource == "https://api.taskadence.com/mcp"


def test_the_account_counts_its_pending_actions(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("account.read") | {"pending_actions": {"incoming_transfers": 2}}
    api.get("/v1/account").respond(json=body)
    pending = tm.account.get().pending_actions
    assert isinstance(pending, models.AccountPendingActions)
    assert pending.incoming_transfers == 2


# ---------------------------------------------------------------------------
# async
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_reactions(atm: AsyncTaskadence, api: respx.MockRouter) -> None:
    api.put(f"{REACTIONS}/%F0%9F%91%8D").respond(json=reactions())
    api.delete(f"{REACTIONS}/%F0%9F%91%8D").respond(json={"reactions": []})
    api.get(f"{REACTIONS}/%F0%9F%91%8D").respond(json={"data": [{"user_id": "U1"}], "next_cursor": None})
    assert (await atm.tasks.comments.react("T1", "C1", THUMBS)).reactions[0].count == 1
    assert (await atm.tasks.comments.unreact("T1", "C1", THUMBS)).reactions == []
    assert [p.user_id async for p in await atm.tasks.comments.reactions("T1", "C1", THUMBS)] == ["U1"]
