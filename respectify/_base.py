"""Base client functionality shared between sync and async clients."""

from contextlib import contextmanager
from dataclasses import dataclass
from html import escape as html_escape, unescape as html_unescape
from typing import Any, Dict, Generic, Iterator, Optional, Type, TypeVar
from urllib.parse import urljoin

import httpx
from beartype import beartype
from pydantic import BaseModel

from respectify.exceptions import (
    ArticleContextNotFoundError,
    ARTICLE_CONTEXT_NOT_FOUND_MARKER,
    AuthenticationError,
    BadRequestError,
    FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE,
    FreeAllowanceExhaustedError,
    PaymentRequiredError,
    RateLimitedError,
    RequestTimeoutError,
    RespectifyError,
    REVISION_LIMIT_REACHED_ERROR_CODE,
    RevisionLimitReachedError,
    ServerError,
    UnsupportedMediaTypeError,
)

T = TypeVar('T', bound=BaseModel)

# Response header carrying the free plan's revision token for an assessed comment, and the
# request header a revision of that comment must send it back in. Cross-SDK contract shared
# with the backend constant REVISION_TOKEN_HEADER; do not change without coordinating.
REVISION_TOKEN_HEADER: str = "X-Respectify-Revision-Token"


@dataclass(frozen=True)
class RespectifyResponse(Generic[T]):
    """A parsed API result together with the response metadata the body does not carry.

    The result models in :mod:`respectify.schemas` are shared with the server and its docs,
    so they only describe the JSON body. The free plan's revision token travels in a header,
    and this wrapper is how the ``*_response`` client methods hand it to the caller.

    Attributes:
        result: The parsed response body (CommentScore, SpamDetectionResult, ...).
        revision_token: The ``X-Respectify-Revision-Token`` header. Set only when a
            free-plan request assessed a comment; None for paid accounts and for endpoints
            that never issue one. Send it back as ``revision_token=`` when the writer revises
            the same comment, so the revision is not counted as a new comment.
    """

    result: T
    revision_token: Optional[str] = None


def _revision_token_from(response: httpx.Response) -> Optional[str]:
    """Return the revision token header value, or None when absent or empty."""
    raw = response.headers.get(REVISION_TOKEN_HEADER)
    if not isinstance(raw, str):
        return None
    token = raw.strip()
    return token or None


def _retry_after_seconds(response: httpx.Response) -> Optional[int]:
    """Read the ``Retry-After`` header as a whole number of seconds.

    The header may also be an HTTP date; that form is not converted and yields None,
    as does a missing or malformed header.
    """
    raw = response.headers.get("Retry-After")
    if not isinstance(raw, str):
        return None
    try:
        seconds = int(raw.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def _sanitize_string(value: str) -> str:
    """HTML-encode a string to prevent XSS.

    API responses echo back user-submitted comment text (in quoted fallacies,
    objectionable phrases, etc.) which must be encoded to prevent XSS when
    rendered in HTML.

    Uses stdlib html.escape with quote=True to encode &, <, >, ", and '.
    """
    return html_escape(html_unescape(value), quote=True)


def _sanitize_data(data: Any) -> Any:
    """Recursively HTML-encode all string values in API response data."""
    if isinstance(data, str):
        return _sanitize_string(data)
    if isinstance(data, list):
        return [_sanitize_data(item) for item in data]
    if isinstance(data, dict):
        return {key: _sanitize_data(value) for key, value in data.items()}
    return data


class BaseRespectifyClient:
    """Base client with shared functionality for authentication and error handling."""
    
    DEFAULT_BASE_URL: str = "https://app.respectify.ai"
    DEFAULT_VERSION: str = "0.2"
    
    @beartype
    def __init__(
        self, 
        email: str, 
        api_key: str, 
        base_url: Optional[str] = None,
        version: Optional[str] = None,
        timeout: float = 30.0,
        website: Optional[str] = None
    ) -> None:
        """Initialize the base client.
        
        Args:
            email: User email address for authentication
            api_key: API key for authentication
            base_url: Base URL for the Respectify API (defaults to production)
            version: API version to use (defaults to 0.2)
            timeout: Request timeout in seconds
            website: Optional website domain for license tracking
        """
        self.email: str = email
        self.api_key: str = api_key
        self.base_url: str = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.version: str = version or self.DEFAULT_VERSION
        self.timeout: float = timeout
        self.website: Optional[str] = website
        
    @beartype
    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for an API endpoint.
        
        Args:
            endpoint: The API endpoint (e.g., 'antispam', 'dogwhistle')
            
        Returns:
            The full URL for the endpoint
        """
        versioned_endpoint: str = f"v{self.version}/{endpoint}"
        return urljoin(f"{self.base_url}/", versioned_endpoint)
        
    @beartype
    def _build_headers(self, revision_token: Optional[str] = None) -> Dict[str, str]:
        """Build HTTP headers for API requests.

        Args:
            revision_token: Free-plan revision token from an earlier assessment of the
                same comment, sent back in ``X-Respectify-Revision-Token``; omitted when None

        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": self.email,
            "X-API-Key": self.api_key,
        }
        if self.website:
            headers["X-Website"] = self.website
        if revision_token:
            headers[REVISION_TOKEN_HEADER] = revision_token
        return headers
        
    @contextmanager
    def _timeout_guard(self) -> Iterator[None]:
        """Re-raise any httpx timeout raised inside the block as RequestTimeoutError.

        Works around both ``with httpx.Client(...)`` and ``async with httpx.AsyncClient(...)``
        blocks, so callers of this library only ever see RespectifyError subclasses.
        """
        try:
            yield
        except httpx.TimeoutException as e:
            raise RequestTimeoutError(
                f"The request to Respectify timed out after {self.timeout} seconds.",
                timeout_seconds=self.timeout,
            ) from e

    @beartype
    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle HTTP error responses by raising appropriate exceptions.
        
        Args:
            response: The HTTP response object
            
        Raises:
            Appropriate RespectifyError subclass based on status code
        """
        status_code: int = response.status_code
        
        # Try to parse error response as JSON
        response_data: Optional[Dict[str, Any]] = None
        try:
            response_data = response.json()
        except Exception:
            pass  # Response may not be JSON
            
        # Extract error message
        error_message: str
        if response_data and isinstance(response_data, dict):
            # The server's error handler sends {error, message, code} for API routes.
            # Use 'message' as the primary error text (human-readable detail).
            # The 'error' field (category title) is available via response_data.
            # Also check 'description' (raw Falcon format) and 'detail' as fallbacks.
            error_message = (
                response_data.get('message')
                or response_data.get('description')
                or response_data.get('detail')
                or f"HTTP {status_code}: {response.reason_phrase}"
            )
        else:
            error_message = f"HTTP {status_code}: {response.reason_phrase}"
        
        # The server adds a machine-readable 'error_code' to the free-plan errors only;
        # every other error body (including the insufficient-balance 402) has none.
        error_code: Optional[str] = None
        if isinstance(response_data, dict) and isinstance(response_data.get("error_code"), str):
            error_code = response_data["error_code"]

        # Raise appropriate exception based on status code
        if status_code == 400:
            # A well-formed-but-unresolvable article context returns a 400 with a stable
            # message. Surface it as the dedicated (BadRequestError subclass) exception so
            # callers can regenerate the article context and retry.
            haystack = " ".join(
                str(response_data.get(field, ""))
                for field in ("message", "error", "description", "title")
            ) if isinstance(response_data, dict) else error_message
            if ARTICLE_CONTEXT_NOT_FOUND_MARKER.lower() in (haystack or error_message).lower():
                raise ArticleContextNotFoundError(error_message, response_data)
            raise BadRequestError(error_message, response_data)
        elif status_code == 401:
            raise AuthenticationError(error_message, response_data)
        elif status_code == 402:
            if error_code == FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE:
                raise FreeAllowanceExhaustedError(error_message, response_data)
            raise PaymentRequiredError(error_message, response_data)
        elif status_code == 409 and error_code == REVISION_LIMIT_REACHED_ERROR_CODE:
            raise RevisionLimitReachedError(error_message, response_data)
        elif status_code == 415:
            raise UnsupportedMediaTypeError(error_message, response_data)
        elif status_code == 429:
            raise RateLimitedError(
                error_message, response_data, retry_after_seconds=_retry_after_seconds(response)
            )
        elif status_code >= 500:
            raise ServerError(error_message, response_data)
        else:
            raise RespectifyError(error_message, status_code, response_data)
            
    @beartype
    def _parse_response(self, response: httpx.Response, schema_class: Type[T]) -> T:
        """Parse a successful HTTP response using the provided Pydantic schema.
        
        Args:
            response: The HTTP response object
            schema_class: Pydantic model class to parse the response
            
        Returns:
            Parsed response object
            
        Raises:
            RespectifyError: If the response cannot be parsed
        """
        try:
            response_data: Dict[str, Any] = response.json()
            response_data = _sanitize_data(response_data)
            return schema_class.model_validate(response_data)
        except Exception as e:
            raise RespectifyError(
                f"Failed to parse response: {str(e)}",
                response.status_code,
                {"raw_response": response.text}
            ) from e

    @beartype
    def _parse_response_with_token(
        self, response: httpx.Response, schema_class: Type[T]
    ) -> RespectifyResponse[T]:
        """Parse a successful response and pair it with its revision token header, if any.

        Args:
            response: The HTTP response object
            schema_class: Pydantic model class to parse the response body

        Returns:
            RespectifyResponse holding the parsed body and the revision token (or None)

        Raises:
            RespectifyError: If the response cannot be parsed
        """
        return RespectifyResponse(
            result=self._parse_response(response, schema_class),
            revision_token=_revision_token_from(response),
        )
