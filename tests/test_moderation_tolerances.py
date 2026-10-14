"""Offline tests for moderation tolerances and finding severity in the shared schemas. No API calls."""

import pytest
from pydantic import ValidationError

from respectify import (
    FLOORED_MODERATION_CATEGORIES,
    CommentAssessment,
    CommentScore,
    HealthItemScore,
    ModerationCategory,
    ModerationTolerances,
    ToleranceLevel,
)
from respectify.schemas import FINDING_SEVERITY_MAX, NegativeTonePhrase, SpamDetectionResult


def _assessment_fields() -> dict:
    return {
        "logical_fallacies": [],
        "objectionable_phrases": [],
        "negative_tone_phrases": [],
        "appears_low_effort": False,
        "overall_score": 3,
        "toxicity_score": 0.1,
        "toxicity_explanation": "",
    }


class TestModerationTolerances:

    def test_every_category_defaults_to_standard(self):
        tolerances = ModerationTolerances()
        for category in ModerationCategory:
            assert tolerances.level_for(category) == ToleranceLevel.STANDARD, f"{category.value} should default to standard"
        assert tolerances.quality == ToleranceLevel.STANDARD, "Quality is a health item too, standard by default"


    def test_tunable_items_may_be_turned_off(self):
        tolerances = ModerationTolerances(logical_fallacy=ToleranceLevel.OFF, quality=ToleranceLevel.OFF)
        assert tolerances.level_for(ModerationCategory.LOGICAL_FALLACY) == ToleranceLevel.OFF
        assert tolerances.quality == ToleranceLevel.OFF


    @pytest.mark.parametrize("category", sorted(FLOORED_MODERATION_CATEGORIES, key=lambda c: c.value))
    def test_floored_categories_cannot_be_turned_off(self, category):
        with pytest.raises(ValidationError, match="stricter but not relaxed or turned off"):
            ModerationTolerances(**{category.value: ToleranceLevel.OFF})


    def test_tunable_categories_may_be_relaxed(self):
        tolerances = ModerationTolerances(insult=ToleranceLevel.RELAXED, low_effort=ToleranceLevel.RELAXED)
        assert tolerances.level_for(ModerationCategory.INSULT) == ToleranceLevel.RELAXED
        assert tolerances.level_for(ModerationCategory.LOW_EFFORT) == ToleranceLevel.RELAXED


    @pytest.mark.parametrize("category", sorted(FLOORED_MODERATION_CATEGORIES, key=lambda c: c.value))
    def test_floored_categories_reject_relaxed(self, category):
        with pytest.raises(ValidationError, match="stricter but not relaxed"):
            ModerationTolerances(**{category.value: ToleranceLevel.RELAXED})


    @pytest.mark.parametrize("category", sorted(FLOORED_MODERATION_CATEGORIES, key=lambda c: c.value))
    def test_floored_categories_reject_permissive(self, category):
        with pytest.raises(ValidationError, match="stricter but not relaxed"):
            ModerationTolerances(**{category.value: ToleranceLevel.PERMISSIVE})


    def test_tunable_categories_and_quality_may_be_permissive(self):
        tolerances = ModerationTolerances(insult=ToleranceLevel.PERMISSIVE, quality=ToleranceLevel.PERMISSIVE)
        assert tolerances.level_for(ModerationCategory.INSULT) == ToleranceLevel.PERMISSIVE
        assert tolerances.quality == ToleranceLevel.PERMISSIVE
        assert ModerationTolerances.model_validate({"profanity": "permissive"}).profanity == ToleranceLevel.PERMISSIVE


    def test_levels_run_from_loosest_to_strictest(self):
        assert [level.value for level in ToleranceLevel] == ["off", "permissive", "relaxed", "standard", "strict", "zero_tolerance"]


    @pytest.mark.parametrize("level", [ToleranceLevel.STANDARD, ToleranceLevel.STRICT, ToleranceLevel.ZERO_TOLERANCE])
    def test_floored_categories_accept_standard_or_stricter(self, level):
        tolerances = ModerationTolerances(threat=level, sexual_content=level)
        assert tolerances.level_for(ModerationCategory.THREAT) == level


    def test_floors_are_threats_identity_sexual_and_harassment(self):
        assert FLOORED_MODERATION_CATEGORIES == {
            ModerationCategory.THREAT, ModerationCategory.IDENTITY_ATTACK,
            ModerationCategory.SEXUAL_CONTENT, ModerationCategory.HARASSMENT,
        }


    def test_unknown_categories_are_rejected(self):
        with pytest.raises(ValidationError):
            ModerationTolerances.model_validate({"insults": "relaxed"})


    def test_round_trips_through_json(self):
        tolerances = ModerationTolerances(insult=ToleranceLevel.RELAXED, threat=ToleranceLevel.ZERO_TOLERANCE)
        assert ModerationTolerances.model_validate(tolerances.model_dump(mode="json")) == tolerances


class TestFindingsAndScores:

    def test_extreme_is_severity_4(self):
        phrase = NegativeTonePhrase(quoted_negative_tone_phrase="x", explanation="", suggested_rewrite="",
                                    category=ModerationCategory.INSULT, severity=4)
        assert phrase.severity == 4
        assert FINDING_SEVERITY_MAX == 4


    def test_findings_need_a_severity_in_range(self):
        for severity in (0, 5):
            with pytest.raises(ValidationError):
                NegativeTonePhrase(quoted_negative_tone_phrase="x", explanation="", suggested_rewrite="",
                                   category=ModerationCategory.INSULT, severity=severity)


    def test_assessment_has_no_tolerance_verdict(self):
        """The evaluator assesses; only Respectify decides against a site's tolerances."""
        assert "exceeds_tolerance" not in CommentAssessment.model_fields


    def test_comment_score_requires_the_verdict_and_records_its_tolerances(self):
        with pytest.raises(ValidationError):
            CommentScore(**_assessment_fields())
        score = CommentScore(**_assessment_fields(), exceeds_tolerance=False)
        assert score.tolerances == ModerationTolerances(), "Without tolerances given, the score was judged at standard"
        assert score.health_items == {} and score.health_score is None, "Health fields are optional for older servers"


    def test_health_items_round_trip(self):
        score = CommentScore(**_assessment_fields(), exceeds_tolerance=True, health_score=2.9,
                             health_items={"insult": HealthItemScore(score=2, minimum=4, is_acceptable=False),
                                           "quality": HealthItemScore(score=3, minimum=3, is_acceptable=True)})
        assert CommentScore.model_validate_json(score.model_dump_json()) == score


    def test_health_item_scores_are_on_the_one_to_five_scale(self):
        for bad in (0, 6):
            with pytest.raises(ValidationError):
                HealthItemScore(score=bad, minimum=3, is_acceptable=False)


class TestClientsSendOnlyNamedCategories:
    """A call sends only the levels its caller named; the server treats the rest as standard."""

    _SCORE_JSON = {**_assessment_fields(), "exceeds_tolerance": False}

    def _capture(self, monkeypatch, client_attribute: str):
        import json
        import httpx
        import respectify.client as client_module
        import respectify.client_async as async_client_module

        sent: list = []

        def handler(request: httpx.Request) -> httpx.Response:
            sent.append(json.loads(request.content))
            return httpx.Response(200, json=self._SCORE_JSON)

        real_client = getattr(httpx, client_attribute)
        module = client_module if client_attribute == "Client" else async_client_module
        monkeypatch.setattr(module.httpx, client_attribute,
                            lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
        return sent


    def test_sync_client_sends_only_named_categories(self, monkeypatch):
        from uuid import uuid4
        from respectify import RespectifyClient
        sent = self._capture(monkeypatch, "Client")
        RespectifyClient("user@example.com", "key").evaluate_comment(
            "A comment", uuid4(), tolerances=ModerationTolerances(insult=ToleranceLevel.RELAXED))
        assert sent[0]["tolerances"] == {"insult": "relaxed"}, "Only the category the caller named is sent"


    def test_explicit_standard_is_sent(self, monkeypatch):
        from uuid import uuid4
        from respectify import RespectifyClient
        sent = self._capture(monkeypatch, "Client")
        RespectifyClient("user@example.com", "key").evaluate_comment(
            "A comment", uuid4(), tolerances=ModerationTolerances(insult=ToleranceLevel.STANDARD))
        assert sent[0]["tolerances"] == {"insult": "standard"}, "Naming standard is an override, not an omission"


    def test_async_megacall_sends_only_named_categories(self, monkeypatch):
        import asyncio
        from respectify import RespectifyAsyncClient
        sent = self._capture(monkeypatch, "AsyncClient")
        asyncio.run(RespectifyAsyncClient("user@example.com", "key").megacall(
            "A comment", include_spam=True, tolerances=ModerationTolerances(low_effort=ToleranceLevel.STRICT)))
        assert sent[0]["tolerances"] == {"low_effort": "strict"}, "Only the category the caller named is sent"


class TestSuspectedSpam:
    """Spam has three outcomes: spam (deleted), suspected spam (sent back with a suggestion), and not spam."""

    def test_suspected_spam_carries_a_suggestion(self):
        result = SpamDetectionResult.model_validate({"reasoning": "", "is_spam": False, "confidence": 0.3, "suspected_spam": True,
                                                     "suggestion": "This looks like spam. How about removing the link?"})
        assert result.suspected_spam is True
        assert result.suggestion == "This looks like spam. How about removing the link?"
        assert result.is_spam is False, "Suspected spam is not spam: it is never deleted"


    def test_an_older_server_without_the_fields_still_parses(self):
        result = SpamDetectionResult.model_validate({"reasoning": "", "is_spam": False, "confidence": 0.9})
        assert result.suspected_spam is False
        assert result.suggestion == ""
