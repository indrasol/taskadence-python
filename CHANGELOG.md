# Changelog

All notable changes to `tasksmate` (the Python SDK). The format follows [Keep a Changelog](https://keepachangelog.com/);
versions follow semver, and **`0.x` is a pre-release with no compatibility promise** until 1.0 (task S.23).

## [Unreleased] — 0.1.0.dev0

### Added
- `TasksMate` / `AsyncTasksMate`: `tm.<resource>.<verb>(…)` for all 152 public operations of API `2026-09-25`,
  generated from `spec/openapi.public.json` (openapi-python-client 0.29.1 + a generated facade).
- Auto-paging lists (`Page` / `AsyncPage`), typed problem+json exceptions with `request_id`, retries with backoff and
  `Retry-After`, automatic `Idempotency-Key` on creates, `ETag` / `If-Match` / `If-None-Match`, deprecation warnings.
- `to_dataframe()` on pages (the `pandas` extra).
- `tasksmate.webhooks.verify` / `parse` (Standard Webhooks signatures, rotation aware).
- The `tm` CLI (the `cli` extra): `auth`, `me`, `tasks`, `projects`, `views`, `webhooks`, `tokens`.
- `examples/streamlit_dashboard`.

### Changed (4.1b — licence)
- Licensed under **Apache-2.0** (was MIT): an explicit patent grant and no trademark rights; `NOTICE` added.

### Changed (4.1b — spec from backend `6b75d01`)
- `webhooks.parse` returns the **generated** `WebhookEvent` (the spec now describes the webhook body and has a `webhooks`
  map); the event type is `event.type_`, extra fields land in `additional_properties`, and a body that is not an event
  raises `webhooks.WebhookParseError`. `pydantic` is no longer a dependency.
- `tasks.add_subtask` / `tasks.add_dependency` take the named `SubtaskLink` / `DependencyLink` bodies.
- `project_resources.upload` sends `project_id` once (the query); the API no longer declares it as a form field.
- The generator no longer strips update-body defaults (the API stopped advertising them) and reads list / create from
  the spec's `x-kind`; it refuses a spec that regresses on either.
