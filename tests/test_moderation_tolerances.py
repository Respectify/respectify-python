"""Offline tests for moderation tolerances and finding severity in the shared schemas. No API calls."""

import pytest
from pydantic import ValidationError

from respectify import (
    FLOORED_MODERATION_CATEGORIES,
    CommentAssessment,
    CommentScore,
    ModerationCategory,
    ModerationTolerances,
    ToleranceLevel,
)
from respectify.schemas import NegativeTonePhrase


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


    def test_tunable_categories_may_be_relaxed(self):
        tolerances = ModerationTolerances(insult=ToleranceLevel.RELAXED, low_effort=ToleranceLevel.RELAXED)
        assert tolerances.level_for(ModerationCategory.INSULT) == ToleranceLevel.RELAXED
        assert tolerances.level_for(ModerationCategory.LOW_EFFORT) == ToleranceLevel.RELAXED


    @pytest.mark.parametrize("category", sorted(FLOORED_MODERATION_CATEGORIES, key=lambda c: c.value))
    def test_floored_categories_reject_relaxed(self, category):
        with pytest.raises(ValidationError, match="stricter but not relaxed"):
            ModerationTolerances(**{category.value: ToleranceLevel.RELAXED})


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

    def test_findings_need_a_severity_in_range(self):
        for severity in (0, 4):
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
