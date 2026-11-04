"""Exception classes for the Respectify Python client library."""

from typing import Any, Dict, Optional

from beartype import beartype


def _error_code_from(response_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return the machine-readable ``error_code`` from an error body, if it carries one."""
    if not isinstance(response_data, dict):
        return None
    error_code = response_data.get("error_code")
    return error_code if isinstance(error_code, str) and error_code else None


class RespectifyError(Exception):
    """Base exception for all Respectify API errors."""

    @beartype
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ) -> None:
        """Initialize a Respectify error.

        Args:
            message: Human-readable error description
            status_code: HTTP status code if applicable
            response_data: Raw response data from the API
            error_code: Machine-readable error code; taken from the response body's
                ``error_code`` field when not given. Most errors have none.
        """
        super().__init__(message)
        self.message: str = message
        self.status_code: Optional[int] = status_code
        self.response_data: Optional[Dict[str, Any]] = response_data
        self.error_code: Optional[str] = (
            error_code if error_code is not None else _error_code_from(response_data)
        )


class AuthenticationError(RespectifyError):
    """Raised when API authentication fails (401 Unauthorized)."""

    @beartype
    def __init__(
        self,
        message: str = "Authentication failed. Check your email and API key.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=401, response_data=response_data)


class BadRequestError(RespectifyError):
    """Raised when the request is malformed or invalid (400 Bad Request)."""

    @beartype
    def __init__(
        self,
        message: str = "Bad request. Check your request parameters.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=400, response_data=response_data)


class PaymentRequiredError(RespectifyError):
    """Raised when the account's credit balance does not cover the call (402 Payment Required).

    Respectify bills each call against a prepaid credit balance; there are no
    subscriptions or plans. Add funds to the account, then retry.

    A free-plan account that has used up its free comments raises the subclass
    :class:`FreeAllowanceExhaustedError` instead, which carries the upgrade URL.
    """

    @beartype
    def __init__(
        self,
        message: str = "Payment required. Your credit balance does not cover this call. Add funds to continue.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=402, response_data=response_data)


class UnsupportedMediaTypeError(RespectifyError):
    """Raised when the request content type is not supported (415 Unsupported Media Type)."""

    @beartype
    def __init__(
        self,
        message: str = "Unsupported media type. Use application/json.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=415, response_data=response_data)


class ServerError(RespectifyError):
    """Raised when the server encounters an internal error (500 Internal Server Error)."""

    @beartype
    def __init__(
        self,
        message: str = "Internal server error. Please try again later.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=500, response_data=response_data)


# Stable substring present (case-insensitively) in the server's 400 error body when
# an article context id is well-formed but cannot be resolved for the account/API key.
# Cross-SDK contract shared with the backend constant ARTICLE_CONTEXT_NOT_FOUND_MESSAGE;
# do not change without coordinating across the backend and the other SDKs.
ARTICLE_CONTEXT_NOT_FOUND_MARKER: str = "Article context not found"


class ArticleContextNotFoundError(BadRequestError):
    """Raised when an article context id was well-formed but could not be resolved (HTTP 400).

    Article contexts are scoped to the user AND the specific API key, so this usually
    means the context was created under a different key (or never existed / expired).
    Regenerate the article context (init_topic_from_text / init_topic_from_url) and retry.

    Subclasses BadRequestError so existing code catching bad requests still works, while
    new code can catch this specifically to trigger a regenerate-and-retry.
    """

    @beartype
    def __init__(
        self,
        message: str = "Article context not found - it may need to be regenerated",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, response_data=response_data)


# Machine-readable ``error_code`` values the server sends for free-plan errors.
# Cross-SDK contract shared with the backend; do not change without coordinating
# across the backend and the other SDKs.
FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE: str = "free_allowance_exhausted"
REVISION_LIMIT_REACHED_ERROR_CODE: str = "revision_limit_reached"
FREE_RATE_LIMITED_ERROR_CODE: str = "free_rate_limited"


class FreeAllowanceExhaustedError(PaymentRequiredError):
    """Raised when a free-plan account has used all its free comments (HTTP 402).

    Moderation has stopped for the account until credit is added; the same API key
    keeps working once it is. ``upgrade_url`` is the billing page where that happens.

    Subclasses PaymentRequiredError so existing code that treats 402 as "let the
    comment through and tell the site owner" keeps working, while new code can catch
    this specifically and show the upgrade URL.
    """

    @beartype
    def __init__(
        self,
        message: str = "Free comment allowance used up. Add credit to continue moderating.",
        response_data: Optional[Dict[str, Any]] = None,
        upgrade_url: Optional[str] = None
    ) -> None:
        super().__init__(message, response_data=response_data)
        if upgrade_url is None and isinstance(response_data, dict):
            candidate = response_data.get("upgrade_url")
            upgrade_url = candidate if isinstance(candidate, str) and candidate else None
        self.upgrade_url: Optional[str] = upgrade_url


class RevisionLimitReachedError(RespectifyError):
    """Raised when a free-plan comment has had all the attempts the plan allows (HTTP 409).

    On the free plan each comment may be assessed a limited number of times (the first
    assessment plus revisions sent with the same revision token). Once that limit is
    reached the comment cannot be assessed again; accept or reject it as it stands.
    """

    @beartype
    def __init__(
        self,
        message: str = "This comment has used all the revision attempts the free plan allows.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=409, response_data=response_data)


class RateLimitedError(RespectifyError):
    """Raised when the server refuses a request because of a rate limit (HTTP 429).

    ``retry_after_seconds`` is taken from the ``Retry-After`` response header when the
    server sends one in seconds; it is None otherwise. Free-plan keys have a per-minute
    cap and carry ``error_code == FREE_RATE_LIMITED_ERROR_CODE``.
    """

    @beartype
    def __init__(
        self,
        message: str = "Too many requests. Slow down and retry later.",
        response_data: Optional[Dict[str, Any]] = None,
        retry_after_seconds: Optional[int] = None
    ) -> None:
        super().__init__(message, status_code=429, response_data=response_data)
        self.retry_after_seconds: Optional[int] = retry_after_seconds


class RequestTimeoutError(RespectifyError):
    """Raised when a request to the API times out before a response arrives.

    Wraps ``httpx.TimeoutException`` (connect, read, write or pool timeouts) so callers
    only need to handle RespectifyError. The original exception is available as
    ``__cause__``. No HTTP status applies, so ``status_code`` is None.
    """

    @beartype
    def __init__(
        self,
        message: str = "The request to Respectify timed out.",
        timeout_seconds: Optional[float] = None
    ) -> None:
        super().__init__(message, status_code=None, response_data=None)
        self.timeout_seconds: Optional[float] = timeout_seconds
