"""TasKadence for Python.

    from taskadence import Taskadence

    tm = Taskadence(token="tkd_live_…")              # or set TASKADENCE_TOKEN
    for task in tm.tasks.list(org_id="O123456"):
        print(task.task_id, task.title)
    tm.views.rows("V…").to_dataframe()             # pip install "taskadence[pandas]"

`tm.<resource>.<verb>(…)` exists for every public operation of the API (`tm.tasks.list`, `tm.projects.read`, …); the
models are in `taskadence.models`, the exceptions in `taskadence.errors`, webhook verification in `taskadence.webhooks`.
Versions follow semver and the API's versioning policy (https://docs.taskadence.com/guides/versioning/).
"""

from . import errors, models, webhooks
from ._client import AsyncTaskadence, Taskadence
from ._core import AUTO, ConfigurationError, FileInput, NotModified, NotModifiedType, Operation
from ._legal import LegalNotice
from ._operations import API_VERSION, DEFAULT_BASE_URL, OPERATIONS
from ._uploads import UploadProgress
from ._version import __version__
from .errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    BillingOwnerMustHandOverError,
    BlobUploadError,
    ConflictError,
    ForbiddenError,
    GoneError,
    IdempotencyKeyInFlightError,
    IdempotencyKeyInvalidError,
    IdempotencyKeyReusedError,
    InsufficientScopeError,
    InternalError,
    InvalidParameterError,
    InvalidValueError,
    MemberNotLinked,
    MemberNotLinkedError,
    NotFoundError,
    OrganizationLockedError,
    OrganizationReadOnlyError,
    OrganizationRestrictedError,
    OrganizationSuspendedError,
    PaymentRequiredError,
    PreconditionFailedError,
    RateLimitedError,
    RemovedInRelease10,
    RemovedInRelease10Error,
    RemovedInRelease11Error,
    ResponseValidationError,
    SprintProjectMismatch,
    SprintProjectMismatchError,
    StorageLimitReachedError,
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
    "BillingOwnerMustHandOverError",
    "BlobUploadError",
    "ConfigurationError",
    "ConflictError",
    "FileInput",
    "ForbiddenError",
    "GoneError",
    "IdempotencyKeyInFlightError",
    "IdempotencyKeyInvalidError",
    "IdempotencyKeyReusedError",
    "InsufficientScopeError",
    "InternalError",
    "InvalidParameterError",
    "InvalidValueError",
    "LegalNotice",
    "MemberNotLinked",
    "MemberNotLinkedError",
    "NotFoundError",
    "NotModified",
    "NotModifiedType",
    "Operation",
    "OrganizationLockedError",
    "OrganizationReadOnlyError",
    "OrganizationRestrictedError",
    "OrganizationSuspendedError",
    "Page",
    "PaymentRequiredError",
    "PreconditionFailedError",
    "RateLimitedError",
    "RemovedInRelease10",
    "RemovedInRelease10Error",
    "RemovedInRelease11Error",
    "ResponseValidationError",
    "SprintProjectMismatch",
    "SprintProjectMismatchError",
    "StorageLimitReachedError",
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
