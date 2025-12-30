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
    suggested_rewrite: str = Field(..., description="Suggested rewrite of the fallacious content")


class ObjectionablePhrase(BaseModel):
    """Represents an objectionable phrase identified in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    quoted_objectionable_phrase: str = Field(..., description="The objectionable phrase found in the comment")
    explanation: str = Field(..., description="Explanation of why this phrase is objectionable")
    suggested_rewrite: str = Field(..., description="Suggested rewrite of the objectionable content")


class NegativeTonePhrase(BaseModel):
    """Represents a phrase with negative tone identified in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    quoted_negative_tone_phrase: str = Field(..., description="The phrase with negative tone")
    explanation: str = Field(..., description="Explanation of the negative tone")
    suggested_rewrite: str = Field(..., description="Suggested rewrite with more positive tone")


class CommentScore(BaseModel):
    """Represents the comprehensive evaluation of a comment's quality and toxicity."""
    
    model_config = ConfigDict(frozen=True)
    
    logical_fallacies: List[LogicalFallacy] = Field(default_factory=list, description="List of logical fallacies found")
    objectionable_phrases: List[ObjectionablePhrase] = Field(default_factory=list, description="List of objectionable phrases found") 
    negative_tone_phrases: List[NegativeTonePhrase] = Field(default_factory=list, description="List of phrases with negative tone")
    appears_low_effort: bool = Field(..., description="Whether the comment appears to be low effort")
    overall_score: int = Field(..., ge=1, le=5, description="Overall quality score from 1 to 5")
    toxicity_score: float = Field(..., ge=0.0, le=1.0, description="Toxicity score from 0.0 to 1.0")
    toxicity_explanation: str = Field(..., description="Educational explanation of toxicity issues found")


class SpamDetectionResult(BaseModel):
    """Represents the result of spam detection analysis."""
    
    model_config = ConfigDict(frozen=True)
    
    reasoning: str = Field(..., description="Explanation of the spam analysis")
    is_spam: bool = Field(..., description="Whether the comment is detected as spam")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of spam detection")


class OnTopicResult(BaseModel):
    """Represents whether a comment is on-topic."""
    
    model_config = ConfigDict(frozen=True)
    
    reasoning: str = Field(..., description="Explanation of the relevance analysis")
    on_topic: bool = Field(..., description="Whether the comment is on-topic") 
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of relevance detection")


class BannedTopicsResult(BaseModel):
    """Represents analysis of banned topics in a comment."""
    
    model_config = ConfigDict(frozen=True)
    
    reasoning: str = Field(..., description="Explanation of the banned topics analysis")
    banned_topics: List[str] = Field(default_factory=list, description="List of banned topics detected")
    quantity_on_banned_topics: float = Field(..., ge=0.0, le=1.0, description="Proportion of comment discussing banned topics")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of banned topics detection")


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
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of detection")


class DogwhistleDetails(BaseModel):
    """Represents detailed information about detected dogwhistles."""
    
    model_config = ConfigDict(frozen=True)
    
    dogwhistle_terms: List[str] = Field(default_factory=list, description="Specific dogwhistle terms detected")
    categories: List[str] = Field(default_factory=list, description="Categories of dogwhistles detected")
    subtlety_level: float = Field(..., ge=0.0, le=1.0, description="How subtle the dogwhistles are")
    harm_potential: float = Field(..., ge=0.0, le=1.0, description="Potential harm level of the dogwhistles")


class DogwhistleResult(BaseModel):
    """Represents the result of dogwhistle detection analysis."""
    
    model_config = ConfigDict(frozen=True)
    
    detection: DogwhistleDetection = Field(..., description="Dogwhistle detection analysis")
    details: Optional[DogwhistleDetails] = Field(None, description="Optional detailed information about detected dogwhistles")


class MegaCallResult(BaseModel):
    """Represents the result of a mega call containing multiple analysis types."""

    # Note: Not frozen - server mutates fields after creation

    comment_score: Optional[CommentScore] = Field(None, description="Comment score result, if requested")
    spam_check: Optional[SpamDetectionResult] = Field(None, description="Spam detection result, if requested")
    relevance_check: Optional[CommentRelevanceResult] = Field(None, description="Comment relevance result, if requested")
    dogwhistle_check: Optional[DogwhistleResult] = Field(None, description="Dogwhistle detection result, if requested")

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


class UserSubscriptionStatus(BaseModel):
    """Information about a user's subscription status."""

    # Note: Not frozen - server needs to mutate this object

    active: bool = Field(..., description="Whether the subscription is active")
    status: Optional[str] = Field(None, description="Current subscription status")
    expires: Optional[str] = Field(None, description="Subscription expiration date")
    plan_name: Optional[str] = Field(None, description="Name of the subscription plan (e.g., 'Personal', 'Professional', 'Anti-Spam Only')")
    allowed_endpoints: Optional[List[str]] = Field(None, description="List of API endpoints allowed for this plan (e.g., ['antispam', 'commentscore'])")
    error: Optional[str] = Field(None, description="Error message if any")


class UserCheckResponse(BaseModel):
    """Represents the response from checking user credentials."""
    
    # Note: Not frozen - server constructs this directly
    
    # Standard production response fields
    success: Optional[str] = Field(None, description="Success status as string")
    info: Optional[str] = Field(None, description="Information message about the check")
    subscription: Optional[UserSubscriptionStatus] = Field(None, description="User subscription information")
    
    # Alternative staging response fields (when subscription required)
    title: Optional[str] = Field(None, description="Error title when subscription required")
    description: Optional[str] = Field(None, description="Error description when subscription required")


