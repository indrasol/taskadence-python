# `tm.webhooks`

Signed HTTP callbacks for audit events: subscriptions, the signing secret (shown once, rotated with a 24 h grace), test sends, the delivery log and replay. Standard-Webhooks signatures; at-least-once with retries.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.webhooks.events(limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

The event vocabulary a webhook can subscribe to.

- **HTTP:** `GET /v1/webhooks/events`
- **operationId:** `webhooks.events`
- **Returns:** `Page[WebhookEventType]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.webhooks.create(body: WebhookCreate | Mapping[str, Any])`

Create a webhook (the signing secret is shown once).

- **HTTP:** `POST /v1/webhooks`
- **operationId:** `webhooks.create`
- **Token scope:** `webhooks:write`
- **Returns:** `WebhookCreated`

## `tm.webhooks.list(org_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

An organization's webhooks (owner / admin).

- **HTTP:** `GET /v1/webhooks`
- **operationId:** `webhooks.list`
- **Token scope:** `webhooks:read`
- **Returns:** `Page[WebhookOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.webhooks.read(subscription_id: str, if_none_match: str | None = None)`

Read a webhook (never its secret).

- **HTTP:** `GET /v1/webhooks/{subscription_id}`
- **operationId:** `webhooks.read`
- **Token scope:** `webhooks:read`
- **Returns:** `WebhookOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.webhooks.update(subscription_id: str, body: WebhookUpdate | Mapping[str, Any], if_match: str | None = None)`

Change, pause, resume or re-enable a webhook.

- **HTTP:** `PATCH /v1/webhooks/{subscription_id}`
- **operationId:** `webhooks.update`
- **Token scope:** `webhooks:write`
- **Returns:** `WebhookOut`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.webhooks.delete(subscription_id: str, if_match: str | None = None)`

Delete a webhook.

- **HTTP:** `DELETE /v1/webhooks/{subscription_id}`
- **operationId:** `webhooks.delete`
- **Token scope:** `webhooks:write`
- **Returns:** `WebhookOut`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.webhooks.rotate_secret(subscription_id: str)`

Rotate the signing secret; the old one signs too for 24 h.

- **HTTP:** `POST /v1/webhooks/{subscription_id}/rotate-secret`
- **operationId:** `webhooks.rotate_secret`
- **Token scope:** `webhooks:write`
- **Returns:** `WebhookCreated`

## `tm.webhooks.test(subscription_id: str)`

Send a test delivery now and return the endpoint's response.

- **HTTP:** `POST /v1/webhooks/{subscription_id}/test`
- **operationId:** `webhooks.test`
- **Token scope:** `webhooks:write`
- **Returns:** `DeliveryDetail`

## `tm.webhooks.deliveries(subscription_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

A webhook's delivery log.

- **HTTP:** `GET /v1/webhooks/{subscription_id}/deliveries`
- **operationId:** `webhooks.deliveries`
- **Token scope:** `webhooks:read`
- **Returns:** `Page[DeliveryOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.webhooks.delivery(subscription_id: str, delivery_id: str, if_none_match: str | None = None)`

One delivery: body, headers, response, attempts.

- **HTTP:** `GET /v1/webhooks/{subscription_id}/deliveries/{delivery_id}`
- **operationId:** `webhooks.delivery`
- **Token scope:** `webhooks:read`
- **Returns:** `DeliveryDetail`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.webhooks.replay(subscription_id: str, delivery_id: str)`

Send a delivery again as a new delivery.

- **HTTP:** `POST /v1/webhooks/{subscription_id}/deliveries/{delivery_id}/replay`
- **operationId:** `webhooks.replay`
- **Token scope:** `webhooks:write`
- **Returns:** `DeliveryOut`
