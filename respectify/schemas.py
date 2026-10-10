"""Pydantic schemas for Respectify API responses."""

from enum import Enum
from typing import Dict, FrozenSet, List, Optional
from uuid import UUID

from beartype import beartype
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ModerationCategory(str, Enum):
    """The kinds of problem a comment can have, each with its own customer tolerance.

    The first four are floored (see FLOORED_MODERATION_CATEGORIES): a customer may
    make them stricter than standard, never more relaxed.
    """

    THREAT = "threat"                    # threats of violence or harm, urging self-harm
    IDENTITY_ATTACK = "identity_attack"  # hostility toward an identity, slurs, dehumanising a group
    SEXUAL_CONTENT = "sexual_content"    # explicit or crude sexual language
    HARASSMENT = "harassment"            # sustained or targeted demeaning of a person, othering
    INSULT = "insult"                    # a one-off insult or put-down of a person
    PROFANITY = "profanity"              # swearing and crude language not aimed at an identity
    DISMISSIVE_TONE = "dismissive_tone"  # sarcasm or dismissal toward someone in the discussion
    LOGICAL_FALLACY = "logical_fallacy"
    LOW_EFFORT = "low_effort"            # empty posts such as "me too" or "+1"


FLOORED_MODERATION_CATEGORIES: FrozenSet[ModerationCategory] = frozenset({
    ModerationCategory.THREAT,
    ModerationCategory.IDENTITY_ATTACK,
    ModerationCategory.SEXUAL_CONTENT,
    ModerationCategory.HARASSMENT,
})


class ToleranceLevel(str, Enum):
    """How much of one kind of problem a site accepts. STANDARD is the default and Respectify's normal behaviour."""

    RELAXED = "relaxed"                # minor instances are not reported
    STANDARD = "standard"
    STRICT = "strict"                  # borderline comments always get a full assessment
    ZERO_TOLERANCE = "zero_tolerance"  # any sign of it gets a full assessment


class ModerationTolerances(BaseModel):
    """A site's tolerance for each kind of problem. Omitted categories are STANDARD.

    Floored categories (threats, identity attacks, sexual content, harassment)
    reject RELAXED: tolerance there can only be raised, never lowered.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    threat: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Threats of violence or harm. Floored: standard or stricter.")
    identity_attack: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Identity attacks and slurs. Floored: standard or stricter.")
    sexual_content: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Explicit or crude sexual content. Floored: standard or stricter.")
    harassment: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Targeted or sustained harassment. Floored: standard or stricter.")
    insult: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="One-off insults and put-downs")
    profanity: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Swearing and crude language")
    dismissive_tone: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Sarcasm or dismissal toward someone in the discussion")
    logical_fallacy: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Logical fallacies")
    low_effort: ToleranceLevel = Field(ToleranceLevel.STANDARD, description="Empty posts such as 'me too' or '+1'")

    @model_validator(mode="after")
    def _floored_categories_are_never_relaxed(self) -> "ModerationTolerances":
        relaxed_floors = sorted(category.value for category in FLOORED_MODERATION_CATEGORIES
                                if self.level_for(category) == ToleranceLevel.RELAXED)
        if relaxed_floors:
            raise ValueError(f"These categories can be made stricter but not relaxed: {', '.join(relaxed_floors)}")
        return self

    def level_for(self, category: ModerationCategory) -> ToleranceLevel:
        return getattr(self, category.value)


# Severity of one finding: 1 minor, 2 clear, 3 severe
FINDING_SEVERITY_MIN = 1
FINDING_SEVERITY_MAX = 3


class LogicalFallacy(BaseModel):
    """Represents a logical fallacy identified in a comment."""

    model_config = ConfigDict(frozen=True)

    fallacy_name: str = Field(..., description="The name of the logical fallacy, e.g., 'straw man'")
    quoted_logical_fallacy_example: str = Field(..., description="The part of the comment that contains the logical fallacy")
    explanation: str = Field(..., description="Explanation of the fallacy and suggestions for improvement")
    suggested_rewrite: str = Field(..., description="Suggested rewrite (only provided when comment appears good-faith; otherwise empty)")
    severity: int = Field(..., ge=FINDING_SEVERITY_MIN, le=FINDING_SEVERITY_MAX,
                          description="1 minor, 2 clear, 3 severe")


class ObjectionablePhrase(BaseModel):
    """Represents an objectionable phrase identified in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    quoted_objectionable_phrase: str = Field(..., description="The objectionable phrase found in the comment")
    explanation: str = Field(..., description="Explanation of why this phrase is objectionable")
    suggested_rewrite: str = Field(..., description="Suggested rewrite (only provided when comment appears good-faith; otherwise empty)")
    category: ModerationCategory = Field(..., description="What kind of problem the phrase is")
    severity: int = Field(..., ge=FINDING_SEVERITY_MIN, le=FINDING_SEVERITY_MAX,
                          description="1 minor, 2 clear, 3 severe")


class NegativeTonePhrase(BaseModel):
    """Represents a phrase with negative tone identified in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    quoted_negative_tone_phrase: str = Field(..., description="The phrase with negative tone")
    explanation: str = Field(..., description="Explanation of the negative tone")
    suggested_rewrite: str = Field(..., description="Suggested rewrite (only provided when comment appears good-faith; otherwise empty)")
    category: ModerationCategory = Field(..., description="What kind of problem the phrase is")
    severity: int = Field(..., ge=FINDING_SEVERITY_MIN, le=FINDING_SEVERITY_MAX,
                          description="1 minor, 2 clear, 3 severe")


class CommentAssessment(BaseModel):
    """The judgment of a comment's quality and toxicity: everything an evaluator assesses.

    CommentScore adds what Respectify computes from it for a particular site.
    """

    model_config = ConfigDict(frozen=True)
    
    logical_fallacies: List[LogicalFallacy] = Field(default_factory=list, description="List of logical fallacies found")
    objectionable_phrases: List[ObjectionablePhrase] = Field(default_factory=list, description="List of objectionable phrases found") 
    negative_tone_phrases: List[NegativeTonePhrase] = Field(default_factory=list, description="List of phrases with negative tone")
    appears_low_effort: bool = Field(..., description="Whether the comment appears to be low effort")
    overall_score: int = Field(..., ge=1, le=5, description="Overall quality score (1=poor, 5=excellent)")
    toxicity_score: float = Field(..., ge=0.0, le=1.0, description="Toxicity score (0.0=not toxic, 1.0=highly toxic)")
    toxicity_explanation: str = Field(..., description="Educational explanation of toxicity issues found")


class CommentScore(CommentAssessment):
    """Represents the comprehensive evaluation of a comment's quality and toxicity, under the site's tolerances.

    Findings below the site's tolerance have already been removed.
    """

    exceeds_tolerance: bool = Field(..., description="True when the comment has a problem the site's tolerances do not accept. "
                                                      "Use this, rather than toxicity_score alone, to decide whether to coach.")
    tolerances: ModerationTolerances = Field(default_factory=ModerationTolerances, description="The tolerances this score was judged under")


class SpamDetectionResult(BaseModel):
    """Represents the result of spam detection analysis."""
    
    model_config = ConfigDict(frozen=True)
    
    reasoning: str = Field(..., description="Explanation of the spam analysis")
    is_spam: bool = Field(..., description="Whether the comment is detected as spam")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict (0.0=uncertain, 1.0=certain the verdict is correct)")


class OnTopicResult(BaseModel):
    """Represents whether a comment is on-topic."""

    model_config = ConfigDict(frozen=True)

    reasoning: str = Field(..., description="Explanation of the relevance analysis")
    on_topic: bool = Field(..., description="Whether the comment is on-topic")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict (0.0=uncertain, 1.0=certain the verdict is correct)")


class BannedTopicsResult(BaseModel):
    """Represents analysis of banned topics in a comment."""

    model_config = ConfigDict(frozen=True)

    reasoning: str = Field(..., description="Explanation of the banned topics analysis")
    banned_topics: List[str] = Field(default_factory=list, description="List of banned topics detected")
    quantity_on_banned_topics: float = Field(..., ge=0.0, le=1.0, description="Proportion discussing banned topics (0.0=none, 1.0=entirely)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict (0.0=uncertain, 1.0=certain the verdict is correct)")


class CommentRelevanceResult(BaseModel):
    """Represents the result of comment relevance analysis."""
    
    model_config = ConfigDict(frozen=True)
    
    on_topic: OnTopicResult = Field(..., description="On-topic analysis result") 
    banned_topics: BannedTopicsResult = Field(..., description="Banned topics analysis result")


class DogwhistleDetection(BaseModel):
    """Represents the detection aspect of dogwhistle analysis."""
    
    model_config = ConfigDict(frozen=True)
    
    reasoning: str = Field(..., description="Explanation of the dogwhistle analysis")
    dogwhistles_detected: bool = Field(..., description="Whether dogwhistles were detected")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict (0.0=uncertain, 1.0=certain the verdict is correct)")


class DogwhistleDetails(BaseModel):
    """Represents detailed information about detected dogwhistles."""
    
    model_config = ConfigDict(frozen=True)
    
    dogwhistle_terms: List[str] = Field(default_factory=list, description="Specific dogwhistle terms detected")
    categories: List[str] = Field(default_factory=list, description="Categories of dogwhistles detected")
    subtlety_level: float = Field(..., ge=0.0, le=1.0, description="Subtlety level (0.0=obvious, 1.0=very subtle)")
    harm_potential: float = Field(..., ge=0.0, le=1.0, description="Potential harm level (0.0=low, 1.0=high)")


class DogwhistleResult(BaseModel):
    """Represents the result of dogwhistle detection analysis."""
    
    model_config = ConfigDict(frozen=True)
    
    detection: DogwhistleDetection = Field(..., description="Dogwhistle detection analysis")
    details: Optional[DogwhistleDetails] = Field(None, description="Optional detailed information about detected dogwhistles")


class PerspectiveScore(BaseModel):
    """Google-style score object used in Perspective compatibility responses."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Probability-style score between 0.0 and 1.0. Higher numbers mean "
            "more of the requested attribute."
        ),
    )
    type: str = Field(
        ...,
        description=(
            "Score type. Respectify currently returns `PROBABILITY`, meaning the "
            "value is a 0 to 1 probability-style score."
        ),
    )


class PerspectiveAnalyzeCommentSpanScore(BaseModel):
    """Google-style span score for a specific part of the comment."""

    model_config = ConfigDict(frozen=True)

    begin: int = Field(..., ge=0, description="Start offset for the span in UTF-16 code units")
    end: int = Field(..., ge=0, description="End offset for the span in UTF-16 code units")
    score: PerspectiveScore = Field(..., description="Score for this specific span")


class PerspectiveAnalyzeCommentAttributeScore(BaseModel):
    """Google-style attribute score entry returned by analyzeComment."""

    model_config = ConfigDict(frozen=True)

    summaryScore: PerspectiveScore = Field(
        ...,
        description=(
            "Overall score for the attribute. This is the main score most "
            "integrations use for thresholds and moderation decisions."
        ),
    )
    spanScores: Optional[List[PerspectiveAnalyzeCommentSpanScore]] = Field(
        None,
        description=(
            "Optional scores for specific spans of text that contributed to the "
            "attribute. Returned only when span annotations were requested."
        ),
    )


class PerspectiveAnalyzeCommentResponse(BaseModel):
    """Response returned by Respectify's public Perspective-compatible analyse endpoint."""

    model_config = ConfigDict(frozen=True)

    attributeScores: Dict[str, PerspectiveAnalyzeCommentAttributeScore] = Field(
        default_factory=dict,
        description=(
            "Map of requested Perspective attribute names, such as `TOXICITY` or "
            "`INSULT`, to their score objects. Each value contains a "
            "`summaryScore` and, when requested, optional `spanScores`."
        ),
    )
    languages: List[str] = Field(
        default_factory=list,
        description=(
            "Requested or effective language context for this response, as language "
            "codes such as `en`, `es`, or `fr`."
        ),
    )
    detectedLanguages: Optional[List[str]] = Field(
        None,
        description=(
            "Present only if Respectify actually detected languages, as language "
            "codes such as `en`, `es`, or `fr`."
        ),
    )
    clientToken: Optional[str] = Field(
        None,
        description=(
            "Caller-provided correlation token, echoed back unchanged when "
            "supplied. Use this if you want to match the response to your own "
            "request ID."
        ),
    )


class PerspectiveSuggestCommentScoreResponse(BaseModel):
    """Response returned by Respectify's public Perspective-compatible suggestscore endpoint."""

    model_config = ConfigDict(frozen=True)

    requestedLanguages: Optional[List[str]] = Field(
        None,
        description=(
            "Echoed requested languages when the caller supplied them, as language "
            "codes such as `en`, `es`, or `fr`."
        ),
    )
    clientToken: Optional[str] = Field(
        None,
        description=(
            "Caller-provided correlation token, echoed back unchanged when "
            "supplied. Use this if you want to match the response to your own "
            "request ID."
        ),
    )


class LlmDetectionSignal(BaseModel):
    """A specific signal indicating LLM-generated text."""

    model_config = ConfigDict(frozen=True)

    signal_type: str = Field(..., description="Category: 'word_frequency', 'structural', 'stylistic', 'epistemic'")
    description: str = Field(..., description="What was detected")
    quoted_text: str = Field(default="", description="The text that triggered this signal, if applicable")


class LlmDetectionResult(BaseModel):
    """Result of LLM-likeness detection for a comment."""

    model_config = ConfigDict(frozen=True)

    llm_likelihood: float = Field(..., ge=0.0, le=1.0, description="Probability the text was generated by an LLM (0.0=human, 1.0=certainly LLM)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the verdict")
    signals_detected: List[LlmDetectionSignal] = Field(default_factory=list, description="Specific signals that contributed to the score")
    reasoning: str = Field(..., description="Explanation of the analysis")


class MegaCallResult(BaseModel):
    """Represents the result of a mega call containing multiple analysis types."""

    # Note: Not frozen - server mutates fields after creation

    comment_score: Optional[CommentScore] = Field(None, description="Comment score result. Null unless requested via include_comment_score (Python) or 'commentscore' service (PHP).")
    spam_check: Optional[SpamDetectionResult] = Field(None, description="Spam detection result. Null unless requested via include_spam (Python) or 'spam' service (PHP).")
    relevance_check: Optional[CommentRelevanceResult] = Field(None, description="Comment relevance result. Null unless requested via include_relevance (Python) or 'relevance' service (PHP).")
    dogwhistle_check: Optional[DogwhistleResult] = Field(None, description="Dogwhistle detection result. Null unless requested via include_dogwhistle (Python) or 'dogwhistle' service (PHP).")
    perspective: Optional[PerspectiveAnalyzeCommentResponse] = Field(
        None,
        description="Perspective-compatible analyzeComment response. Null unless requested via include_perspective_analyze_comment (Python) or 'perspectiveAnalyzeComment' service (PHP).",
    )
    llm_detection: Optional[LlmDetectionResult] = Field(None, description="LLM-likeness detection result. Null unless requested via include_llm_detection.")

    @property
    def spam(self) -> Optional[SpamDetectionResult]:
        """Alias for spam_check - provides cleaner API access."""
        return self.spam_check

    @property
    def relevance(self) -> Optional[CommentRelevanceResult]:
        """Alias for relevance_check - provides cleaner API access."""
        return self.relevance_check

    @property
    def dogwhistle(self) -> Optional[DogwhistleResult]:
        """Alias for dogwhistle_check - provides cleaner API access."""
        return self.dogwhistle_check


class InitTopicResponse(BaseModel):
    """Represents the response from initializing a topic."""
    
    model_config = ConfigDict(frozen=True)
    
    article_id: UUID = Field(..., description="UUID of the initialized article/topic")


class UserCheckResponse(BaseModel):
    """Response from the usercheck endpoint containing subscription status.

    This is returned directly as the API response - no wrapper needed since
    HTTP 200 indicates success and HTTP 4xx indicates errors.
    """

    # Note: Not frozen - server needs to mutate this object

    active: bool = Field(..., description="Whether the subscription is active")
    status: Optional[str] = Field(None, description="Current subscription status")
    expires: Optional[str] = Field(None, description="Subscription expiration date")
    plan_name: Optional[str] = Field(None, description="Name of the subscription plan (e.g., 'Personal', 'Professional', 'Anti-Spam Only')")
    allowed_endpoints: Optional[List[str]] = Field(None, description="List of API endpoints allowed for this plan (e.g., ['antispam', 'commentscore'])")
    error: Optional[str] = Field(None, description="Error message if subscription check failed")


# Backwards compatibility alias
UserSubscriptionStatus = UserCheckResponse
