"""
Mocked tests for the free plan's revision token header round trip.

A free-plan request that assesses a comment gets ``X-Respectify-Revision-Token`` back; a
revision of that comment must send the same header. These tests mock httpx so no real
API calls are made, and check both directions on every assessing method, sync and async,
plus that the perspective endpoints and paid-style responses never involve the token.
"""
from typing import Any, Dict, Optional
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import UUID

import httpx
import pytest

from respectify import (
    RespectifyClient,
    RespectifyAsyncClient,
    RespectifyResponse,
    REVISION_TOKEN_HEADER,
    CommentScore,
    SpamDetectionResult,
    CommentRelevanceResult,
    DogwhistleResult,
    MegaCallResult,
    PerspectiveAnalyzeCommentResponse,
)

ARTICLE_ID = UUID("00000000-0000-0000-0000-000000000000")
TOKEN = "a" * 43
OTHER_TOKEN = "b" * 43

SPAM_BODY: Dict[str, Any] = {"reasoning": "Looks fine", "is_spam": False, "confidence": 0.9}

SCORE_BODY: Dict[str, Any] = {
    "logical_fallacies": [],
    "objectionable_phrases": [],
    "negative_tone_phrases": [],
    "appears_low_effort": False,
    "overall_score": 4,
    "toxicity_score": 0.1,
    "toxicity_explanation": "None found",
    "exceeds_tolerance": False,
}

RELEVANCE_BODY: Dict[str, Any] = {
    "on_topic": {"reasoning": "On topic", "on_topic": True, "confidence": 0.8},
    "banned_topics": {
        "reasoning": "None",
        "banned_topics": [],
        "quantity_on_banned_topics": 0.0,
        "confidence": 0.9,
    },
}

DOGWHISTLE_BODY: Dict[str, Any] = {
    "detection": {"reasoning": "None", "dogwhistles_detected": False, "confidence": 0.95},
    "details": None,
}

MEGACALL_BODY: Dict[str, Any] = {"spam_check": SPAM_BODY, "comment_score": SCORE_BODY}

PERSPECTIVE_BODY: Dict[str, Any] = {
    "attributeScores": {
        "TOXICITY": {
            "summaryScore": {"value": 0.1, "type": "PROBABILITY"},
            "spanScores": [],
        }
    },
    "languages": ["en"],
}


def make_ok_response(json_body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> MagicMock:
    """Create a mock 200 httpx.Response with the given JSON body and headers."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.reason_phrase = "OK"
    resp.json.return_value = json_body
    resp.headers = httpx.Headers(headers or {})
    resp.is_success = True
    return resp


class SyncHarness:
    """Patches httpx.Client; records the request headers the client sent."""

    def __init__(self, response: MagicMock) -> None:
        self.mock_client = MagicMock()
        self.mock_client.__enter__ = MagicMock(return_value=self.mock_client)
        self.mock_client.__exit__ = MagicMock(return_value=False)
        self.mock_client.post.return_value = response
        self._patch = patch("httpx.Client", return_value=self.mock_client)

    def __enter__(self) -> "SyncHarness":
        self._patch.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._patch.stop()

    @property
    def sent_headers(self) -> Dict[str, str]:
        return self.mock_client.post.call_args.kwargs["headers"]


class AsyncHarness:
    """Patches httpx.AsyncClient; records the request headers the client sent."""

    def __init__(self, response: MagicMock) -> None:
        self.mock_client = MagicMock()
        self.mock_client.__aenter__ = AsyncMock(return_value=self.mock_client)
        self.mock_client.__aexit__ = AsyncMock(return_value=False)
        self.mock_client.post = AsyncMock(return_value=response)
        self._patch = patch("httpx.AsyncClient", return_value=self.mock_client)

    def __enter__(self) -> "AsyncHarness":
        self._patch.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._patch.stop()

    @property
    def sent_headers(self) -> Dict[str, str]:
        return self.mock_client.post.call_args.kwargs["headers"]


@pytest.fixture
def client() -> RespectifyClient:
    return RespectifyClient(email="test@example.com", api_key="test-api-key")


@pytest.fixture
def async_client() -> RespectifyAsyncClient:
    return RespectifyAsyncClient(email="test@example.com", api_key="test-api-key")


class TestRespectifyResponse:
    def test_header_constant_matches_the_backend_contract(self):
        assert REVISION_TOKEN_HEADER == "X-Respectify-Revision-Token"

    def test_wrapper_is_immutable(self):
        wrapped = RespectifyResponse(result=SpamDetectionResult(**SPAM_BODY), revision_token=TOKEN)
        with pytest.raises(AttributeError):
            wrapped.revision_token = OTHER_TOKEN  # type: ignore[misc]

    def test_revision_token_defaults_to_none(self):
        wrapped = RespectifyResponse(result=SpamDetectionResult(**SPAM_BODY))
        assert wrapped.revision_token is None


class TestSyncResponseMethodsExposeTheToken:
    """Each *_response method returns the parsed body and the token header."""

    def test_evaluate_comment_response(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = client.evaluate_comment_response("hello", ARTICLE_ID)
        assert isinstance(wrapped, RespectifyResponse)
        assert isinstance(wrapped.result, CommentScore)
        assert wrapped.result.overall_score == 4
        assert wrapped.revision_token == TOKEN

    def test_check_spam_response(self, client):
        with SyncHarness(make_ok_response(SPAM_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = client.check_spam_response("hello", ARTICLE_ID)
        assert isinstance(wrapped.result, SpamDetectionResult)
        assert wrapped.revision_token == TOKEN

    def test_check_relevance_response(self, client):
        with SyncHarness(make_ok_response(RELEVANCE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = client.check_relevance_response("hello", ARTICLE_ID)
        assert isinstance(wrapped.result, CommentRelevanceResult)
        assert wrapped.revision_token == TOKEN

    def test_check_dogwhistle_response(self, client):
        with SyncHarness(make_ok_response(DOGWHISTLE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = client.check_dogwhistle_response("hello", ARTICLE_ID)
        assert isinstance(wrapped.result, DogwhistleResult)
        assert wrapped.revision_token == TOKEN

    def test_megacall_response(self, client):
        with SyncHarness(make_ok_response(MEGACALL_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = client.megacall_response(
                "hello", ARTICLE_ID, include_spam=True, include_comment_score=True
            )
        assert isinstance(wrapped.result, MegaCallResult)
        assert wrapped.result.spam_check is not None
        assert wrapped.revision_token == TOKEN

    def test_header_name_is_matched_case_insensitively(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY, {"x-respectify-revision-token": TOKEN})):
            wrapped = client.evaluate_comment_response("hello", ARTICLE_ID)
        assert wrapped.revision_token == TOKEN

    def test_paid_account_response_has_no_token(self, client):
        """Paid accounts never get the header; the wrapper says None rather than failing."""
        with SyncHarness(make_ok_response(SCORE_BODY)):
            wrapped = client.evaluate_comment_response("hello", ARTICLE_ID)
        assert wrapped.revision_token is None

    def test_blank_header_counts_as_no_token(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: "   "})):
            wrapped = client.evaluate_comment_response("hello", ARTICLE_ID)
        assert wrapped.revision_token is None


class TestSyncPlainMethodsKeepTheirReturnTypes:
    """The existing methods still return the bare model; the token is simply not exposed."""

    def test_evaluate_comment_returns_comment_score(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            score = client.evaluate_comment("hello", ARTICLE_ID)
        assert isinstance(score, CommentScore)
        assert not isinstance(score, RespectifyResponse)

    def test_check_spam_returns_spam_result(self, client):
        with SyncHarness(make_ok_response(SPAM_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            result = client.check_spam("hello")
        assert isinstance(result, SpamDetectionResult)

    def test_megacall_returns_megacall_result(self, client):
        with SyncHarness(make_ok_response(MEGACALL_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            result = client.megacall("hello", ARTICLE_ID, include_spam=True)
        assert isinstance(result, MegaCallResult)


class TestSyncRequestsSendTheToken:
    """A revision sends the token back in the request header, and only then."""

    def test_no_header_when_no_token_given(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY)) as harness:
            client.evaluate_comment("hello", ARTICLE_ID)
            assert REVISION_TOKEN_HEADER not in harness.sent_headers

    def test_evaluate_comment_sends_token(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY)) as harness:
            client.evaluate_comment("hello again", ARTICLE_ID, revision_token=TOKEN)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    def test_evaluate_comment_response_sends_token(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY)) as harness:
            client.evaluate_comment_response("hello again", ARTICLE_ID, revision_token=TOKEN)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    def test_check_spam_sends_token(self, client):
        with SyncHarness(make_ok_response(SPAM_BODY)) as harness:
            client.check_spam("hello again", ARTICLE_ID, revision_token=TOKEN)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    def test_check_relevance_sends_token(self, client):
        with SyncHarness(make_ok_response(RELEVANCE_BODY)) as harness:
            client.check_relevance("hello again", ARTICLE_ID, revision_token=TOKEN)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    def test_check_dogwhistle_sends_token(self, client):
        with SyncHarness(make_ok_response(DOGWHISTLE_BODY)) as harness:
            client.check_dogwhistle("hello again", ARTICLE_ID, revision_token=TOKEN)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    def test_megacall_sends_token(self, client):
        with SyncHarness(make_ok_response(MEGACALL_BODY)) as harness:
            client.megacall("hello again", ARTICLE_ID, include_spam=True, revision_token=TOKEN)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    def test_token_does_not_leak_into_the_body(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY)) as harness:
            client.evaluate_comment("hello again", ARTICLE_ID, revision_token=TOKEN)
            body = harness.mock_client.post.call_args.kwargs["json"]
            assert TOKEN not in str(body)

    def test_other_auth_headers_are_still_sent(self, client):
        with SyncHarness(make_ok_response(SCORE_BODY)) as harness:
            client.evaluate_comment("hello again", ARTICLE_ID, revision_token=TOKEN)
            sent = harness.sent_headers
            assert sent["X-User-Email"] == "test@example.com"
            assert sent["X-API-Key"] == "test-api-key"
            assert sent["Content-Type"] == "application/json"

    def test_round_trip_first_assessment_then_revision(self, client):
        """The token from the first response is what the revision sends."""
        with SyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            first = client.evaluate_comment_response("first try", ARTICLE_ID)
        with SyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})) as harness:
            second = client.evaluate_comment_response(
                "second try", ARTICLE_ID, revision_token=first.revision_token
            )
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN
        assert second.revision_token == TOKEN


class TestEndpointsThatNeverUseTheToken:
    def test_perspective_analyze_comment_never_sends_the_header(self, client):
        with SyncHarness(make_ok_response(PERSPECTIVE_BODY)) as harness:
            result = client.perspective.analyze_comment({"comment": {"text": "x"}})
            assert REVISION_TOKEN_HEADER not in harness.sent_headers
        assert isinstance(result, PerspectiveAnalyzeCommentResponse)

    def test_perspective_suggest_comment_score_never_sends_the_header(self, client):
        with SyncHarness(make_ok_response({})) as harness:
            client.perspective.suggest_comment_score({"comment": {"text": "x"}})
            assert REVISION_TOKEN_HEADER not in harness.sent_headers

    def test_init_topic_never_sends_the_header(self, client):
        with SyncHarness(make_ok_response({"article_id": str(ARTICLE_ID)})) as harness:
            client.init_topic_from_text("article")
            assert REVISION_TOKEN_HEADER not in harness.sent_headers

    def test_perspective_client_has_no_revision_token_parameter(self, client):
        import inspect
        for method in (client.perspective.analyze_comment, client.perspective.suggest_comment_score):
            assert "revision_token" not in inspect.signature(method).parameters


class TestAsyncRevisionToken:
    async def test_evaluate_comment_response_exposes_token(self, async_client):
        with AsyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = await async_client.evaluate_comment_response("hello", ARTICLE_ID)
        assert isinstance(wrapped.result, CommentScore)
        assert wrapped.revision_token == TOKEN

    async def test_check_spam_response_exposes_token(self, async_client):
        with AsyncHarness(make_ok_response(SPAM_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = await async_client.check_spam_response("hello")
        assert isinstance(wrapped.result, SpamDetectionResult)
        assert wrapped.revision_token == TOKEN

    async def test_check_relevance_response_exposes_token(self, async_client):
        with AsyncHarness(make_ok_response(RELEVANCE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = await async_client.check_relevance_response("hello", ARTICLE_ID)
        assert isinstance(wrapped.result, CommentRelevanceResult)
        assert wrapped.revision_token == TOKEN

    async def test_check_dogwhistle_response_exposes_token(self, async_client):
        with AsyncHarness(make_ok_response(DOGWHISTLE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = await async_client.check_dogwhistle_response("hello", ARTICLE_ID)
        assert isinstance(wrapped.result, DogwhistleResult)
        assert wrapped.revision_token == TOKEN

    async def test_megacall_response_exposes_token(self, async_client):
        with AsyncHarness(make_ok_response(MEGACALL_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            wrapped = await async_client.megacall_response("hello", ARTICLE_ID, include_spam=True)
        assert isinstance(wrapped.result, MegaCallResult)
        assert wrapped.revision_token == TOKEN

    async def test_plain_method_keeps_its_return_type(self, async_client):
        with AsyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            score = await async_client.evaluate_comment("hello", ARTICLE_ID)
        assert isinstance(score, CommentScore)

    async def test_no_header_when_no_token_given(self, async_client):
        with AsyncHarness(make_ok_response(SCORE_BODY)) as harness:
            await async_client.evaluate_comment("hello", ARTICLE_ID)
            assert REVISION_TOKEN_HEADER not in harness.sent_headers

    @pytest.mark.parametrize(
        "method_name, body, kwargs",
        [
            ("check_spam", SPAM_BODY, {}),
            ("check_relevance", RELEVANCE_BODY, {}),
            ("evaluate_comment", SCORE_BODY, {}),
            ("check_dogwhistle", DOGWHISTLE_BODY, {}),
            ("megacall", MEGACALL_BODY, {"include_spam": True}),
        ],
    )
    async def test_each_assessing_method_sends_token(self, async_client, method_name, body, kwargs):
        with AsyncHarness(make_ok_response(body)) as harness:
            method = getattr(async_client, method_name)
            await method("hello again", ARTICLE_ID, revision_token=TOKEN, **kwargs)
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN

    async def test_perspective_never_sends_the_header(self, async_client):
        with AsyncHarness(make_ok_response(PERSPECTIVE_BODY)) as harness:
            await async_client.perspective.analyze_comment({"comment": {"text": "x"}})
            assert REVISION_TOKEN_HEADER not in harness.sent_headers

    async def test_round_trip_first_assessment_then_revision(self, async_client):
        with AsyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})):
            first = await async_client.evaluate_comment_response("first try", ARTICLE_ID)
        with AsyncHarness(make_ok_response(SCORE_BODY, {REVISION_TOKEN_HEADER: TOKEN})) as harness:
            await async_client.evaluate_comment(
                "second try", ARTICLE_ID, revision_token=first.revision_token
            )
            assert harness.sent_headers[REVISION_TOKEN_HEADER] == TOKEN
