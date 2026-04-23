"""Pydantic schemas for Respectify API responses."""

from typing import Dict, List, Optional
from uuid import UUID

from beartype import beartype
from pydantic import BaseModel, Field, ConfigDict


class LogicalFallacy(BaseModel):
    """Represents a logical fallacy identified in a comment."""

    model_config = ConfigDict(frozen=True)

    fallacy_name: str = Field(..., description="The name of the logical fallacy, e.g., 'straw man'")
    quoted_logical_fallacy_example: str = Field(..., description="The part of the comment that contains the logical fallacy")
    explanation: str = Field(..., description="Explanation of the fallacy and suggestions for improvement")
    suggested_rewrite: str = Field(..., description="Suggested rewrite (only provided when comment appears good-faith; otherwise empty)")


class ObjectionablePhrase(BaseModel):
    """Represents an objectionable phrase identified in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    quoted_objectionable_phrase: str = Field(..., description="The objectionable phrase found in the comment")
    explanation: str = Field(..., description="Explanation of why this phrase is objectionable")
    suggested_rewrite: str = Field(..., description="Suggested rewrite (only provided when comment appears good-faith; otherwise empty)")


class NegativeTonePhrase(BaseModel):
    """Represents a phrase with negative tone identified in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    quoted_negative_tone_phrase: str = Field(..., description="The phrase with negative tone")
    explanation: str = Field(..., description="Explanation of the negative tone")
    suggested_rewrite: str = Field(..., description="Suggested rewrite (only provided when comment appears good-faith; otherwise empty)")


class CommentScore(BaseModel):
    """Represents the comprehensive evaluation of a comment's quality and toxicity."""
    
    model_config = ConfigDict(frozen=True)
    
    logical_fallacies: List[LogicalFallacy] = Field(default_factory=list, description="List of logical fallacies found")
    objectionable_phrases: List[ObjectionablePhrase] = Field(default_factory=list, description="List of objectionable phrases found") 
    negative_tone_phrases: List[NegativeTonePhrase] = Field(default_factory=list, description="List of phrases with negative tone")
    appears_low_effort: bool = Field(..., description="Whether the comment appears to be low effort")
    overall_score: int = Field(..., ge=1, le=5, description="Overall quality score (1=poor, 5=excellent)")
    toxicity_score: float = Field(..., ge=0.0, le=1.0, description="Toxicity score (0.0=not toxic, 1.0=highly toxic)")
    toxicity_explanation: str = Field(..., description="Educational explanation of toxicity issues found")


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
