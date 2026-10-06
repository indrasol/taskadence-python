"""TasKadence for Python.

    from taskadence import Taskadence

    tm = Taskadence(token="tkd_live_…")              # or set TASKADENCE_TOKEN
    for task in tm.tasks.list(org_id="O0020"):
        print(task.task_id, task.title)
    tm.views.rows("V…").to_dataframe()             # pip install "taskadence[pandas]"

`tm.<resource>.<verb>(…)` exists for every public operation of the API (`tm.tasks.list`, `tm.projects.read`, …); the
models are in `taskadence.models`, the exceptions in `taskadence.errors`, webhook verification in `taskadence.webhooks`.
`0.x` is a pre-release: no compatibility promise until 1.0.
"""

from . import errors, models, webhooks
from ._client import AsyncTaskadence, Taskadence
from ._core import AUTO, ConfigurationError, FileInput, NotModified, NotModifiedType, Operation
from ._operations import API_VERSION, DEFAULT_BASE_URL, OPERATIONS
from ._uploads import UploadProgress
from ._version import __version__
from .errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    BlobUploadError,
    ConflictError,
    ForbiddenError,
    IdempotencyKeyInFlightError,
    IdempotencyKeyInvalidError,
    IdempotencyKeyReusedError,
    InsufficientScopeError,
    InternalError,
    InvalidParameterError,
    InvalidValueError,
    NotFoundError,
    PreconditionFailedError,
    RateLimitedError,
    ResponseValidationError,
    TaskadenceError,
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
    "AsyncTaskadence",
    "AuthenticationError",
    "BadRequestError",
    "BlobUploadError",
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
    "InvalidValueError",
    "NotFoundError",
    "NotModified",
    "NotModifiedType",
    "Operation",
    "Page",
    "PreconditionFailedError",
    "RateLimitedError",
    "ResponseValidationError",
    "Taskadence",
    "TaskadenceError",
    "TestTokenReadOnlyError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenPolicyError",
    "TokenRevokedError",
    "UnprocessableEntityError",
    "UploadProgress",
    "UrlRefusedError",
    "ValidationError",
    "__version__",
    "errors",
    "models",
    "webhooks",
]
