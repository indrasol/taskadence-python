"""TasksMate for Python.

    from tasksmate import TasksMate

    tm = TasksMate(token="tm_live_…")              # or set TASKSMATE_TOKEN
    for task in tm.tasks.list(org_id="O0020"):
        print(task.task_id, task.title)
    tm.views.rows("V…").to_dataframe()             # pip install "tasksmate[pandas]"

`tm.<resource>.<verb>(…)` exists for every public operation of the API (`tm.tasks.list`, `tm.projects.read`, …); the
models are in `tasksmate.models`, the exceptions in `tasksmate.errors`, webhook verification in `tasksmate.webhooks`.
`0.x` is a pre-release: no compatibility promise until 1.0.
"""

from . import errors, models, webhooks
from ._client import AsyncTasksMate, TasksMate
from ._core import AUTO, ConfigurationError, FileInput, NotModified, NotModifiedType, Operation
from ._operations import API_VERSION, DEFAULT_BASE_URL, OPERATIONS
from ._version import __version__
from .errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    IdempotencyKeyInFlightError,
    IdempotencyKeyInvalidError,
    IdempotencyKeyReusedError,
    InsufficientScopeError,
    InternalError,
    InvalidParameterError,
    NotFoundError,
    PreconditionFailedError,
    RateLimitedError,
    ResponseValidationError,
    TasksMateError,
    TestTokenReadOnlyError,
    TokenExpiredError,
    TokenInvalidError,
    TokenPolicyError,
    TokenRevokedError,
    UnprocessableEntityError,
    UrlRefusedError,
    ValidationError,
)
from .pagination import AsyncPage, Page

__all__ = [
    "API_VERSION",
    "AUTO",
    "DEFAULT_BASE_URL",
    "OPERATIONS",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AsyncPage",
    "AsyncTasksMate",
    "AuthenticationError",
    "BadRequestError",
    "ConfigurationError",
    "ConflictError",
    "FileInput",
    "ForbiddenError",
    "IdempotencyKeyInFlightError",
    "IdempotencyKeyInvalidError",
    "IdempotencyKeyReusedError",
    "InsufficientScopeError",
    "InternalError",
    "InvalidParameterError",
    "NotFoundError",
    "NotModified",
    "NotModifiedType",
    "Operation",
    "Page",
    "PreconditionFailedError",
    "RateLimitedError",
    "ResponseValidationError",
    "TasksMate",
    "TasksMateError",
    "TestTokenReadOnlyError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenPolicyError",
    "TokenRevokedError",
    "UnprocessableEntityError",
    "UrlRefusedError",
    "ValidationError",
    "__version__",
    "errors",
    "models",
    "webhooks",
]
