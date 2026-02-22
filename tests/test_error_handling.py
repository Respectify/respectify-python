"""
Mocked tests for error handling and response parsing.

These tests mock httpx responses to simulate server error responses and verify
that the SDK correctly extracts error messages and throws the right exception
types. No real API calls are made.
"""
from unittest.mock import patch, MagicMock
from uuid import UUID
import httpx
import pytest
from respectify.client import RespectifyClient
from respectify.exceptions import (
    RespectifyError,
    AuthenticationError,
    BadRequestError,
    PaymentRequiredError,
    UnsupportedMediaTypeError,
    ServerError,
)


def make_mock_response(status_code: int, json_body: dict) -> MagicMock:
    """Create a mock httpx.Response with the given status and JSON body."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.reason_phrase = {
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        415: "Unsupported Media Type",
        429: "Too Many Requests",
        500: "Internal Server Error",
    }.get(status_code, "Unknown")
    resp.json.return_value = json_body
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
            "error": "Payment Required",
            "message": "An active subscription is required to access this API.",
            "code": 402,
        })
        with mock_httpx_post(mock_resp):
            with pytest.raises(PaymentRequiredError) as exc_info:
                client.evaluate_comment("test", UUID("00000000-0000-0000-0000-000000000000"))
            err = exc_info.value
            assert err.message == "An active subscription is required to access this API."
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
