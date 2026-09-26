"""Receiving TasksMate webhooks: verify the signature, then parse the event.

    from tasksmate import webhooks

    def handle(request):                         # any framework: you need the headers and the RAW body bytes
        if not webhooks.verify(SECRET, request.headers, request.body):
            return 400
        event = webhooks.parse(request.body)     # a typed WebhookEvent
        if event.type == "task.updated":
            ...
        return 200

The recipe is `Tasks-Mate-Backend/docs/api/WEBHOOKS_WORKFLOW.md` (Standard Webhooks): the signed message is
`"{webhook-id}.{webhook-timestamp}.{raw body}"`, the HMAC-SHA256 key is the base64-DECODED part of the secret after
`whsec_`, and `webhook-signature` holds one or more space-separated `v1,<base64>` values.

ROTATION, both ways. After "rotate secret" TasksMate signs with the old AND the new secret for 24 h (two values in the
header), so a receiver still holding the old secret keeps verifying; and a receiver may pass BOTH secrets
(`verify([new, old], …)`) while it switches over. A timestamp further than `tolerance` seconds from now is refused
(a replayed capture). Compare in constant time; verify the raw bytes — never a re-serialized JSON.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

SECRET_PREFIX = "whsec_"  # noqa: S105 - the prefix, not a secret
DEFAULT_TOLERANCE = 300


class WebhookVerificationError(ValueError):
    """Raised by `verify(..., raise_on_failure=True)`; the message says which check failed (never the secret)."""


class WebhookActor(BaseModel):
    """Who caused the event: a person, a service account (4.2), or the system."""

    model_config = ConfigDict(extra="allow")

    kind: str
    id: str | None = None
    username: str | None = None


class WebhookEventData(BaseModel):
    """What changed: the audit row's scrubbed `before` / `after` diffs — never a whole resource, never a secret."""

    model_config = ConfigDict(extra="allow")

    resource_type: str
    resource_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class WebhookEvent(BaseModel):
    """One delivery's body. `id` is the delivery id (`WD…`), the same as the `webhook-id` header: dedupe on it —
    delivery is at-least-once. Fetch the full resource with the API (`tm.tasks.read(event.data.resource_id)`)."""

    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    api_version: str | None = None
    created_at: datetime
    org_id: str
    project_id: str | None = None
    actor: WebhookActor | None = None
    data: WebhookEventData
    request_id: str | None = None


def _header(headers: Mapping[str, str], name: str) -> str | None:
    getter = getattr(headers, "get", None)
    value = getter(name) if getter else None
    if value is None:
        value = next((v for k, v in headers.items() if k.lower() == name), None)
    return value


def _key(secret: str) -> bytes:
    try:
        return base64.b64decode(secret.removeprefix(SECRET_PREFIX), validate=True)
    except (binascii.Error, ValueError):
        raise WebhookVerificationError("the secret is not a TasksMate webhook secret (`whsec_` + base64)") from None


def sign(secret: str, msg_id: str, timestamp: int, body: bytes) -> str:
    """The `v1,<base64>` signature TasksMate sends — for tests of your own receiver."""
    digest = hmac.new(_key(secret), f"{msg_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def verify(
    secret: str | Sequence[str],
    headers: Mapping[str, str],
    body: bytes | str,
    tolerance: int = DEFAULT_TOLERANCE,
    *,
    now: float | None = None,
    raise_on_failure: bool = False,
) -> bool:
    """True when `body` was signed by TasksMate with `secret` (or any of several secrets) within `tolerance` seconds.

    `headers`: the request's headers (any mapping; names are matched case-insensitively). `body`: the RAW request body.
    """

    def fail(reason: str) -> bool:
        if raise_on_failure:
            raise WebhookVerificationError(reason)
        return False

    msg_id = _header(headers, "webhook-id")
    stamp = _header(headers, "webhook-timestamp")
    signatures = _header(headers, "webhook-signature")
    if not (msg_id and stamp and signatures):
        return fail("missing webhook-id, webhook-timestamp or webhook-signature")
    try:
        timestamp = int(stamp)
    except ValueError:
        return fail("webhook-timestamp is not an integer")
    if abs((time.time() if now is None else now) - timestamp) > tolerance:
        return fail(f"webhook-timestamp is more than {tolerance} s away from now (a replay, or a skewed clock)")
    raw = body.encode() if isinstance(body, str) else bytes(body)
    secrets = [secret] if isinstance(secret, str) else list(secret)
    offered = [s for s in signatures.split(" ") if s.startswith("v1,")]
    for candidate in secrets:
        expected = sign(candidate, msg_id, timestamp, raw)
        if any(hmac.compare_digest(expected, sig) for sig in offered):
            return True
    return fail("no signature matches the secret")


def parse(body: bytes | str | Mapping[str, Any]) -> WebhookEvent:
    """The event, typed. Parse only a body `verify` accepted."""
    data = dict(body) if isinstance(body, Mapping) else json.loads(body)
    return WebhookEvent.model_validate(data)


__all__ = [
    "DEFAULT_TOLERANCE",
    "WebhookActor",
    "WebhookEvent",
    "WebhookEventData",
    "WebhookVerificationError",
    "parse",
    "sign",
    "verify",
]
