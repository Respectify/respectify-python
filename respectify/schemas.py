"""Pydantic schemas for Respectify API responses."""

from typing import List, Optional, Union
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


class PerspectiveSpanScore(BaseModel):
    """A score for a specific span of text within the comment."""

    model_config = ConfigDict(frozen=True)

    begin: int = Field(..., ge=0, description="Start character position in the original comment")
    end: int = Field(..., ge=0, description="End character position in the original comment")
    score: float = Field(..., ge=0.0, le=1.0, description="Score for this span (0.0-1.0)")
    quoted_text: str = Field(..., description="The quoted text from the comment for this span")


class PerspectiveAttributeScore(BaseModel):
    """Score for a single Perspective attribute, with optional span-level detail."""

    model_config = ConfigDict(frozen=True)

    score: float = Field(..., ge=0.0, le=1.0, description="Summary score (0.0-1.0 probability)")
    span_scores: List[PerspectiveSpanScore] = Field(default_factory=list, description="Per-span scores identifying which parts of the comment triggered this attribute")


class PerspectiveResult(BaseModel):
    """Perspective-compatible comment analysis result.
    Scores represent the probability (0.0-1.0) that a reader would perceive
    the comment as having each attribute. Compatible with Google's Perspective API
    response format for easy migration.
    """

    model_config = ConfigDict(frozen=True)

    # All attribute fields are Optional so unrequested attributes can be None.
    # When all attributes are requested (the default), all will be populated.

    # Toxicity attributes (Perspective API core)
    toxicity: Optional[PerspectiveAttributeScore] = Field(None, description="Rude, disrespectful, or unreasonable content likely to make people leave a discussion")
    severe_toxicity: Optional[PerspectiveAttributeScore] = Field(None, description="Very hateful, aggressive, or disrespectful content; higher threshold than toxicity")
    identity_attack: Optional[PerspectiveAttributeScore] = Field(None, description="Negative or hateful content targeting someone because of their identity")
    insult: Optional[PerspectiveAttributeScore] = Field(None, description="Insulting, inflammatory, or negative comment towards a person or group")
    profanity: Optional[PerspectiveAttributeScore] = Field(None, description="Swear words, curse words, or other obscene language")
    threat: Optional[PerspectiveAttributeScore] = Field(None, description="Intention to inflict pain, injury, or violence")

    # Content attributes (Perspective API experimental)
    sexually_explicit: Optional[PerspectiveAttributeScore] = Field(None, description="References to sexual acts or body parts in sexual context")
    incoherent: Optional[PerspectiveAttributeScore] = Field(None, description="Difficult to understand, nonsensical, or poorly written")
    inflammatory: Optional[PerspectiveAttributeScore] = Field(None, description="Intended to provoke or inflame rather than discuss")
    spam: Optional[PerspectiveAttributeScore] = Field(None, description="Irrelevant, promotional, or nonsensical content")

    # Bridging/constructive attributes (Perspective API bridging + Respectify additions)
    reasoning: Optional[PerspectiveAttributeScore] = Field(None, description="Demonstrates logical reasoning or evidence-based arguments")
    curiosity: Optional[PerspectiveAttributeScore] = Field(None, description="Shows genuine curiosity, asks thoughtful questions")
    nuance: Optional[PerspectiveAttributeScore] = Field(None, description="Demonstrates nuanced thinking, acknowledges complexity")
    compassion: Optional[PerspectiveAttributeScore] = Field(None, description="Shows empathy, understanding, or concern for others")
    constructiveness: Optional[PerspectiveAttributeScore] = Field(None, description="Contributes constructively, adds to the conversation")
    respect: Optional[PerspectiveAttributeScore] = Field(None, description="Treats others and their views with dignity")
    personal_story: Optional[PerspectiveAttributeScore] = Field(None, description="Includes a personal experience as support for statements made")
    affinity: Optional[PerspectiveAttributeScore] = Field(None, description="References shared interests, motivations, or outlooks with others")

    # Summary
    summary: str = Field(..., description="One-sentence plain-language summary of the comment's character")


class PerspectiveRawScores(BaseModel):
    """Internal schema for LLM output before span resolution.
    The LLM returns quoted_text for spans; Python code then resolves to character positions.
    Every attribute has a corresponding _span field for the most relevant quote (4-25 words)."""

    # Toxicity attributes — each with a span quote
    toxicity: float = Field(..., ge=0.0, le=1.0)
    toxicity_span: str = Field(default="", description="Quoted text from the comment most relevant to toxicity")
    severe_toxicity: float = Field(..., ge=0.0, le=1.0)
    severe_toxicity_span: str = Field(default="", description="Quoted text for severe toxicity")
    identity_attack: float = Field(..., ge=0.0, le=1.0)
    identity_attack_span: str = Field(default="", description="Quoted text for identity attack")
    insult: float = Field(..., ge=0.0, le=1.0)
    insult_span: str = Field(default="", description="Quoted text for insult")
    profanity: float = Field(..., ge=0.0, le=1.0)
    profanity_span: str = Field(default="", description="Quoted text for profanity")
    threat: float = Field(..., ge=0.0, le=1.0)
    threat_span: str = Field(default="", description="Quoted text for threat")

    # Content attributes — each with a span quote
    sexually_explicit: float = Field(..., ge=0.0, le=1.0)
    sexually_explicit_span: str = Field(default="", description="Quoted text for sexually explicit")
    incoherent: float = Field(..., ge=0.0, le=1.0)
    incoherent_span: str = Field(default="", description="Quoted text for incoherent")
    inflammatory: float = Field(..., ge=0.0, le=1.0)
    inflammatory_span: str = Field(default="", description="Quoted text for inflammatory")
    spam: float = Field(..., ge=0.0, le=1.0)
    spam_span: str = Field(default="", description="Quoted text for spam")

    # Bridging attributes — each with a span quote
    reasoning: float = Field(..., ge=0.0, le=1.0)
    reasoning_span: str = Field(default="", description="Quoted text for reasoning")
    curiosity: float = Field(..., ge=0.0, le=1.0)
    curiosity_span: str = Field(default="", description="Quoted text for curiosity")
    nuance: float = Field(..., ge=0.0, le=1.0)
    nuance_span: str = Field(default="", description="Quoted text for nuance")
    compassion: float = Field(..., ge=0.0, le=1.0)
    compassion_span: str = Field(default="", description="Quoted text for compassion")
    constructiveness: float = Field(..., ge=0.0, le=1.0)
    constructiveness_span: str = Field(default="", description="Quoted text for constructiveness")
    respect: float = Field(..., ge=0.0, le=1.0)
    respect_span: str = Field(default="", description="Quoted text for respect")
    personal_story: float = Field(..., ge=0.0, le=1.0)
    personal_story_span: str = Field(default="", description="Quoted text for personal story")
    affinity: float = Field(..., ge=0.0, le=1.0)
    affinity_span: str = Field(default="", description="Quoted text for affinity")

    # Summary
    summary: str = Field(..., description="One-sentence summary")


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


class FeedbackResponse(BaseModel):
    """Response from submitting feedback/score corrections."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(..., description="'ok' if feedback was recorded successfully")
    message: str = Field(..., description="Human-readable confirmation message")


class MegaCallResult(BaseModel):
    """Represents the result of a mega call containing multiple analysis types."""

    # Note: Not frozen - server mutates fields after creation

    comment_score: Optional[CommentScore] = Field(None, description="Comment score result. Null unless requested via include_comment_score (Python) or 'commentscore' service (PHP).")
    spam_check: Optional[SpamDetectionResult] = Field(None, description="Spam detection result. Null unless requested via include_spam (Python) or 'spam' service (PHP).")
    relevance_check: Optional[CommentRelevanceResult] = Field(None, description="Comment relevance result. Null unless requested via include_relevance (Python) or 'relevance' service (PHP).")
    dogwhistle_check: Optional[DogwhistleResult] = Field(None, description="Dogwhistle detection result. Null unless requested via include_dogwhistle (Python) or 'dogwhistle' service (PHP).")
    perspective: Optional[PerspectiveResult] = Field(None, description="Perspective-compatible attribute scores. Null unless requested via include_perspective (Python) or 'perspective' service (PHP).")
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


