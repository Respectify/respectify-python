"""
Mocked tests for error handling and response parsing.

These tests mock httpx responses to simulate server error responses and verify
that the SDK correctly extracts error messages and throws the right exception
types. No real API calls are made.
"""
from typing import Dict, Optional
from unittest.mock import patch, MagicMock
from uuid import UUID
import httpx
import pytest
from respectify.client import RespectifyClient
from respectify.exceptions import (
    RespectifyError,
    AuthenticationError,
    BadRequestError,
    ArticleContextNotFoundError,
    PaymentRequiredError,
    FreeAllowanceExhaustedError,
    RevisionLimitReachedError,
    RateLimitedError,
    UnsupportedMediaTypeError,
    ServerError,
    FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE,
    REVISION_LIMIT_REACHED_ERROR_CODE,
    FREE_RATE_LIMITED_ERROR_CODE,
)


def make_mock_response(
    status_code: int, json_body: dict, headers: Optional[Dict[str, str]] = None
) -> MagicMock:
    """Create a mock httpx.Response with the given status, JSON body and headers."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.reason_phrase = {
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        409: "Conflict",
        415: "Unsupported Media Type",
        429: "Too Many Requests",
        500: "Internal Server Error",
    }.get(status_code, "Unknown")
    resp.json.return_value = json_body
    resp.headers = httpx.Headers(headers or {})
    resp.is_success = 200 <= status_code < 300
    return resp


def mock_httpx_post(mock_response):
    """Create a context manager that mocks httpx.Client to return mock_response on post()."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return patch("httpx.Client", return_value=mock_client)


@pytest.fixture
def client():
    return RespectifyClient(
        email="test@example.com",
        api_key="test-api-key",
    )


class TestServerApiErrorFormat:
    """Test the server's {error, message, code} JSON error format."""

    def test_400_bad_request_extracts_error_and_message(self, client):
        mock_resp = make_mock_response(400, {
            "error": "Missing Parameter",
            "message": "A comment to evaluate is required, but was missing or empty",
            "code": 400,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "A comment to evaluate is required, but was missing or empty"
            assert err.status_code == 400
            assert err.response_data["error"] == "Missing Parameter"
            assert err.response_data["message"] == "A comment to evaluate is required, but was missing or empty"

    def test_400_article_context_not_found_maps_to_dedicated_error(self, client):
        """A 400 carrying the stable not-found marker maps to ArticleContextNotFoundError,
        which is also a BadRequestError so existing handlers keep working."""
        mock_resp = make_mock_response(400, {
            "error": "Article Context Not Found",
            "message": "Article context not found - it may need to be regenerated",
            "code": 400,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(ArticleContextNotFoundError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert isinstance(err, BadRequestError)
            assert err.status_code == 400

    def test_401_unauthorized(self, client):
        mock_resp = make_mock_response(401, {
            "error": "Unauthorized",
            "message": "Invalid user ID or API key.",
            "code": 401,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(AuthenticationError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "Invalid user ID or API key."
            assert err.status_code == 401

    def test_402_payment_required(self, client):
        mock_resp = make_mock_response(402, {
            "error": "Insufficient balance",
            "message": "Your balance is $0.00. This call costs $0.007. Add funds to continue.",
            "code": 402,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(PaymentRequiredError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "Your balance is $0.00. This call costs $0.007. Add funds to continue."
            assert err.status_code == 402

    def test_415_unsupported_media_type(self, client):
        mock_resp = make_mock_response(415, {
            "error": "Unsupported Media Type",
            "message": "Content type must be application/json",
            "code": 415,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(UnsupportedMediaTypeError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "Content type must be application/json"

    def test_429_too_many_requests(self, client):
        mock_resp = make_mock_response(429, {
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please slow down.",
            "code": 429,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(RespectifyError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "Rate limit exceeded. Please slow down."
            assert err.status_code == 429

    def test_errors_without_error_code_have_none(self, client):
        mock_resp = make_mock_response(401, {
            "error": "Unauthorized",
            "message": "Invalid user ID or API key.",
            "code": 401,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(AuthenticationError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            assert exc_info.value.error_code is None

    def test_500_internal_server_error(self, client):
        mock_resp = make_mock_response(500, {
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
            "code": 500,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(ServerError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "An unexpected error occurred."


ARTICLE_ID = UUID("00000000-0000-0000-0000-000000000000")
UPGRADE_URL = "https://respectify.ai/dashboard/billing"


class TestFreePlanErrors:
    """The free plan's errors are told apart by the body's machine-readable error_code."""

    def test_402_free_allowance_exhausted_maps_to_dedicated_error(self, client):
        mock_resp = make_mock_response(402, {
            "error": "Free comment allowance used up",
            "message": f"This account has used all 100 free comments. Add credit: {UPGRADE_URL}",
            "code": 402,
            "error_code": FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE,
            "upgrade_url": UPGRADE_URL,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(FreeAllowanceExhaustedError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            err = exc_info.value
            assert err.status_code == 402
            assert err.error_code == "free_allowance_exhausted"
            assert err.upgrade_url == UPGRADE_URL
            assert UPGRADE_URL in err.message

    def test_free_allowance_exhausted_is_a_payment_required_error(self, client):
        """Existing handlers that let the comment through on 402 keep working."""
        mock_resp = make_mock_response(402, {
            "error": "Free comment allowance used up",
            "message": "Used up.",
            "code": 402,
            "error_code": FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE,
            "upgrade_url": UPGRADE_URL,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(PaymentRequiredError) as exc_info:
                client.check_spam("test", ARTICLE_ID)
            assert isinstance(exc_info.value, FreeAllowanceExhaustedError)

    def test_402_without_error_code_stays_payment_required(self, client):
        """The pre-existing insufficient-balance 402 has no error_code and must not change."""
        mock_resp = make_mock_response(402, {
            "error": "Insufficient balance",
            "message": "Your balance is $0.00. This call costs $0.007. Add funds to continue.",
            "code": 402,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(PaymentRequiredError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            err = exc_info.value
            assert type(err) is PaymentRequiredError
            assert not isinstance(err, FreeAllowanceExhaustedError)
            assert err.error_code is None

    def test_free_allowance_exhausted_without_upgrade_url_field(self, client):
        mock_resp = make_mock_response(402, {
            "error": "Free comment allowance used up",
            "message": "Used up.",
            "code": 402,
            "error_code": FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(FreeAllowanceExhaustedError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            assert exc_info.value.upgrade_url is None

    def test_409_revision_limit_reached(self, client):
        mock_resp = make_mock_response(409, {
            "error": "Revision limit reached",
            "message": "This comment has had all 5 attempts the free plan allows.",
            "code": 409,
            "error_code": REVISION_LIMIT_REACHED_ERROR_CODE,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(RevisionLimitReachedError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            err = exc_info.value
            assert err.status_code == 409
            assert err.error_code == "revision_limit_reached"
            assert err.message == "This comment has had all 5 attempts the free plan allows."

    def test_409_without_error_code_is_a_plain_respectify_error(self, client):
        mock_resp = make_mock_response(409, {
            "error": "Conflict",
            "message": "Something else conflicted.",
            "code": 409,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(RespectifyError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            err = exc_info.value
            assert type(err) is RespectifyError
            assert err.status_code == 409

    def test_429_free_rate_limited_with_retry_after(self, client):
        mock_resp = make_mock_response(429, {
            "error": "Too Many Requests",
            "message": "Free keys may make 10 requests a minute. Retry in 37 seconds.",
            "code": 429,
            "error_code": FREE_RATE_LIMITED_ERROR_CODE,
        }, headers={"Retry-After": "37"})
        with mock_httpx_post(mock_resp):
            with pytest.raises(RateLimitedError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            err = exc_info.value
            assert err.status_code == 429
            assert err.error_code == "free_rate_limited"
            assert err.retry_after_seconds == 37

    def test_any_429_maps_to_rate_limited_error(self, client):
        """A 429 without the free-plan code is still a RateLimitedError (and a RespectifyError)."""
        mock_resp = make_mock_response(429, {
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please slow down.",
            "code": 429,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(RateLimitedError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            err = exc_info.value
            assert err.error_code is None
            assert err.retry_after_seconds is None

    def test_429_with_http_date_retry_after_yields_none(self, client):
        mock_resp = make_mock_response(429, {
            "error": "Too Many Requests",
            "message": "Slow down.",
            "code": 429,
        }, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
        with mock_httpx_post(mock_resp):
            with pytest.raises(RateLimitedError) as exc_info:
                client.evaluate_comment("test", ARTICLE_ID)
            assert exc_info.value.retry_after_seconds is None

    def test_free_plan_errors_reach_the_perspective_client_too(self, client):
        mock_resp = make_mock_response(429, {
            "error": "Too Many Requests",
            "message": "Slow down.",
            "code": 429,
            "error_code": FREE_RATE_LIMITED_ERROR_CODE,
        }, headers={"Retry-After": "5"})
        with mock_httpx_post(mock_resp):
            with pytest.raises(RateLimitedError) as exc_info:
                client.perspective.analyze_comment({"comment": {"text": "x"}})
            assert exc_info.value.retry_after_seconds == 5


class TestInitTopicFromUrlFetchFailures:
    """Test error handling when the server fails to fetch an external URL."""

    def test_target_site_returns_403(self, client):
        mock_resp = make_mock_response(400, {
            "error": "URL Fetch Error",
            "message": "Could not fetch URL: HTTP 403 from https://www.example.com/article",
            "code": 400,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.init_topic_from_url("https://www.example.com/article")
            err = exc_info.value
            assert "Could not fetch URL" in err.message
            assert "403" in err.message
            assert err.status_code == 400

    def test_target_site_returns_429(self, client):
        mock_resp = make_mock_response(400, {
            "error": "URL Fetch Error",
            "message": "Could not fetch URL: HTTP 429 from https://aeon.co/essays/some-article",
            "code": 400,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.init_topic_from_url("https://aeon.co/essays/some-article")
            err = exc_info.value
            assert "Could not fetch URL" in err.message
            assert "429" in err.message

    def test_target_site_returns_500(self, client):
        mock_resp = make_mock_response(400, {
            "error": "URL Fetch Error",
            "message": "Could not fetch URL: HTTP 500 from https://broken-site.example.com",
            "code": 400,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.init_topic_from_url("https://broken-site.example.com")
            err = exc_info.value
            assert "Could not fetch URL" in err.message
            assert "500" in err.message


class TestFallbackFieldHandling:
    """Test fallback to other error field formats."""

    def test_falls_back_to_description_field(self, client):
        """Raw Falcon format without custom error handler."""
        mock_resp = make_mock_response(400, {
            "title": "Bad Request",
            "description": "Some raw Falcon error description",
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "Some raw Falcon error description"

    def test_falls_back_to_http_status_when_no_known_fields(self, client):
        mock_resp = make_mock_response(400, {
            "unknown_field": "something",
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "HTTP 400: Bad Request"

    def test_handles_message_field_without_error_field(self, client):
        mock_resp = make_mock_response(400, {
            "message": "Just a message, no error title",
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(BadRequestError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "Just a message, no error title"
