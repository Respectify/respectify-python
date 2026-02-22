"""
Mocked tests for response sanitization (XSS prevention).

These tests mock httpx responses to verify that all string values in API
responses are HTML-encoded before being returned to callers. No real API
calls are made.
"""
from unittest.mock import MagicMock, patch
from uuid import UUID

import httpx
import pytest

from respectify.client import RespectifyClient
from respectify._base import _sanitize_data, _sanitize_string


def make_mock_response(status_code: int, json_body: dict) -> MagicMock:
    """Create a mock httpx.Response with the given status and JSON body."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.reason_phrase = "OK"
    resp.json.return_value = json_body
    resp.is_success = 200 <= status_code < 300
    resp.text = str(json_body)
    return resp


def mock_httpx_post(mock_response):
    """Create a context manager that mocks httpx.Client to return mock_response."""
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return patch("httpx.Client", return_value=mock_client)


ARTICLE_ID = UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def client():
    return RespectifyClient(email="test@example.com", api_key="test-key")


class TestSanitizeStringFunction:
    """Test the low-level _sanitize_string function."""

    def test_encodes_angle_brackets(self):
        assert _sanitize_string("<script>alert('xss')</script>") == (
            "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        )

    def test_encodes_ampersand(self):
        assert _sanitize_string("a & b") == "a &amp; b"

    def test_encodes_double_quotes(self):
        assert _sanitize_string('say "hello"') == "say &quot;hello&quot;"

    def test_encodes_single_quotes(self):
        assert _sanitize_string("it's") == "it&#x27;s"

    def test_preserves_safe_text(self):
        assert _sanitize_string("normal text") == "normal text"

    def test_handles_empty_string(self):
        assert _sanitize_string("") == ""

    def test_encodes_all_special_chars_together(self):
        result = _sanitize_string('<img onerror="alert(\'xss\')" src=x>')
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert "'" not in result


class TestSanitizeDataFunction:
    """Test the recursive _sanitize_data function."""

    def test_sanitizes_string(self):
        assert _sanitize_data("<b>bold</b>") == "&lt;b&gt;bold&lt;/b&gt;"

    def test_preserves_int(self):
        assert _sanitize_data(42) == 42

    def test_preserves_float(self):
        assert _sanitize_data(0.85) == 0.85

    def test_preserves_bool(self):
        assert _sanitize_data(True) is True
        assert _sanitize_data(False) is False

    def test_preserves_none(self):
        assert _sanitize_data(None) is None

    def test_sanitizes_list_of_strings(self):
        result = _sanitize_data(["<a>", "safe", "<b>"])
        assert result == ["&lt;a&gt;", "safe", "&lt;b&gt;"]

    def test_sanitizes_dict_values(self):
        result = _sanitize_data({"key": "<script>bad</script>", "num": 5})
        assert result["key"] == "&lt;script&gt;bad&lt;/script&gt;"
        assert result["num"] == 5

    def test_sanitizes_nested_dict(self):
        data = {
            "outer": {
                "inner": '<img onerror="alert(1)">',
                "count": 3,
            }
        }
        result = _sanitize_data(data)
        assert "&lt;img" in result["outer"]["inner"]
        assert result["outer"]["count"] == 3

    def test_sanitizes_list_of_dicts(self):
        data = [{"text": "<b>hi</b>"}, {"text": "safe"}]
        result = _sanitize_data(data)
        assert result[0]["text"] == "&lt;b&gt;hi&lt;/b&gt;"
        assert result[1]["text"] == "safe"


class TestSpamCheckSanitization:
    """Test sanitization through the actual SDK spam check endpoint."""

    def test_sanitizes_reasoning_field(self, client):
        mock_resp = make_mock_response(200, {
            "is_spam": False,
            "confidence": 0.95,
            "reasoning": 'Comment contains <script>alert("xss")</script>',
        })
        with mock_httpx_post(mock_resp):
            result = client.check_spam("test", ARTICLE_ID)
        assert "<script>" not in result.reasoning
        assert "&lt;script&gt;" in result.reasoning

    def test_preserves_numbers_and_booleans(self, client):
        mock_resp = make_mock_response(200, {
            "is_spam": True,
            "confidence": 0.85,
            "reasoning": "Spam detected",
        })
        with mock_httpx_post(mock_resp):
            result = client.check_spam("test", ARTICLE_ID)
        assert result.is_spam is True
        assert result.confidence == 0.85


class TestCommentScoreSanitization:
    """Test sanitization of nested comment score responses."""

    def test_sanitizes_logical_fallacy_fields(self, client):
        mock_resp = make_mock_response(200, {
            "logical_fallacies": [{
                "fallacy_name": "straw man",
                "quoted_logical_fallacy_example": '<img onerror="alert(1)">',
                "explanation": "Normal text",
                "suggested_rewrite": "Normal <b>rewrite</b>",
            }],
            "objectionable_phrases": [],
            "negative_tone_phrases": [],
            "appears_low_effort": False,
            "overall_score": 3,
            "toxicity_score": 0.2,
            "toxicity_explanation": "Low toxicity",
        })
        with mock_httpx_post(mock_resp):
            result = client.evaluate_comment("test", ARTICLE_ID)
        fallacy = result.logical_fallacies[0]
        assert "<img" not in fallacy.quoted_logical_fallacy_example
        assert "&lt;img" in fallacy.quoted_logical_fallacy_example
        assert "<b>" not in fallacy.suggested_rewrite
        assert "&lt;b&gt;" in fallacy.suggested_rewrite

    def test_sanitizes_objectionable_phrases(self, client):
        mock_resp = make_mock_response(200, {
            "logical_fallacies": [],
            "objectionable_phrases": [{
                "quoted_objectionable_phrase": '<script>alert("xss")</script>',
                "explanation": "Explanation with <b>html</b>",
                "suggested_rewrite": "Clean rewrite",
            }],
            "negative_tone_phrases": [],
            "appears_low_effort": False,
            "overall_score": 2,
            "toxicity_score": 0.5,
            "toxicity_explanation": "Some issues",
        })
        with mock_httpx_post(mock_resp):
            result = client.evaluate_comment("test", ARTICLE_ID)
        phrase = result.objectionable_phrases[0]
        assert "<script>" not in phrase.quoted_objectionable_phrase
        assert "&lt;script&gt;" in phrase.quoted_objectionable_phrase
        assert "<b>" not in phrase.explanation

    def test_preserves_score_values(self, client):
        mock_resp = make_mock_response(200, {
            "logical_fallacies": [],
            "objectionable_phrases": [],
            "negative_tone_phrases": [],
            "appears_low_effort": True,
            "overall_score": 1,
            "toxicity_score": 0.9,
            "toxicity_explanation": "Highly toxic",
        })
        with mock_httpx_post(mock_resp):
            result = client.evaluate_comment("test", ARTICLE_ID)
        assert result.overall_score == 1
        assert result.toxicity_score == 0.9
        assert result.appears_low_effort is True


class TestRelevanceSanitization:
    """Test sanitization of relevance check responses."""

    def test_sanitizes_banned_topics_list(self, client):
        mock_resp = make_mock_response(200, {
            "on_topic": {
                "on_topic": True,
                "confidence": 0.8,
                "reasoning": "On topic",
            },
            "banned_topics": {
                "banned_topics": ['<script>topic</script>', "safe topic"],
                "quantity_on_banned_topics": 0.5,
                "confidence": 0.9,
                "reasoning": "Contains <b>banned</b> content",
            },
        })
        with mock_httpx_post(mock_resp):
            result = client.check_relevance("test", ARTICLE_ID, ["politics"])
        assert "<script>" not in result.banned_topics.banned_topics[0]
        assert "&lt;script&gt;" in result.banned_topics.banned_topics[0]
        assert result.banned_topics.banned_topics[1] == "safe topic"
        assert "<b>" not in result.banned_topics.reasoning


class TestMegacallSanitization:
    """Test sanitization of megacall nested structures."""

    def test_sanitizes_all_nested_results(self, client):
        mock_resp = make_mock_response(200, {
            "spam_check": {
                "is_spam": False,
                "confidence": 0.9,
                "reasoning": '<b>Bold</b> reasoning',
            },
            "relevance_check": {
                "on_topic": {
                    "on_topic": True,
                    "confidence": 0.8,
                    "reasoning": "On topic",
                },
                "banned_topics": {
                    "banned_topics": ['<script>topic</script>'],
                    "quantity_on_banned_topics": 0,
                    "confidence": 0.9,
                    "reasoning": "No banned topics",
                },
            },
            "comment_score": {
                "logical_fallacies": [],
                "objectionable_phrases": [],
                "negative_tone_phrases": [],
                "appears_low_effort": False,
                "overall_score": 4,
                "toxicity_score": 0.1,
                "toxicity_explanation": "Good <i>comment</i>",
            },
            "dogwhistle_check": {
                "detection": {
                    "reasoning": "No dogwhistles <b>found</b>",
                    "dogwhistles_detected": False,
                    "confidence": 0.95,
                },
                "details": None,
            },
        })
        with mock_httpx_post(mock_resp):
            result = client.megacall("test", ARTICLE_ID,
                                     include_spam=True, include_relevance=True,
                                     include_comment_score=True, include_dogwhistle=True)

        assert "&lt;b&gt;" in result.spam_check.reasoning
        assert "&lt;script&gt;" in result.relevance_check.banned_topics.banned_topics[0]
        assert "&lt;i&gt;" in result.comment_score.toxicity_explanation
        assert "&lt;b&gt;" in result.dogwhistle_check.detection.reasoning

    def test_handles_null_optional_fields(self, client):
        mock_resp = make_mock_response(200, {
            "spam_check": {
                "is_spam": False,
                "confidence": 0.9,
                "reasoning": "Not spam",
            },
            "relevance_check": None,
            "comment_score": None,
            "dogwhistle_check": None,
        })
        with mock_httpx_post(mock_resp):
            result = client.megacall("test", ARTICLE_ID, include_spam=True)
        assert result.spam_check is not None
        assert result.relevance_check is None
        assert result.comment_score is None
        assert result.dogwhistle_check is None
