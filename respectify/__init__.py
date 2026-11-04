"""Respectify Python Client Library.

A Python client library for the Respectify API, providing both synchronous and 
asynchronous interfaces for comment moderation, spam detection, toxicity analysis,
and dogwhistle detection.
"""

__version__ = "0.9.0"

from respectify._base import RespectifyResponse, REVISION_TOKEN_HEADER
from respectify.client import RespectifyClient
from respectify.client_async import RespectifyAsyncClient
from respectify.perspective import RespectifyPerspectiveClient
from respectify.perspective_async import RespectifyAsyncPerspectiveClient
from respectify.schemas import (
    CommentAssessment,
    CommentScore,
    FINDING_SEVERITY_MAX,
    FINDING_SEVERITY_MIN,
    FLOORED_MODERATION_CATEGORIES,
    QUALITY_HEALTH_ITEM,
    HealthItemScore,
    ModerationCategory,
    ModerationTolerances,
    ToleranceLevel,
    DogwhistleResult,
    LogicalFallacy,
    MegaCallResult,
    NegativeTonePhrase,
    ObjectionablePhrase,
    SpamDetectionResult,
    CommentRelevanceResult,
    OnTopicResult,
    BannedTopicsResult,
    DogwhistleDetection,
    DogwhistleDetails,
    InitTopicResponse,
    UserCheckResponse,
    UserSubscriptionStatus,
    PerspectiveScore,
    PerspectiveAnalyzeCommentSpanScore,
    PerspectiveAnalyzeCommentAttributeScore,
    PerspectiveAnalyzeCommentResponse,
    PerspectiveSuggestCommentScoreResponse,
)
from respectify.exceptions import (
    RespectifyError,
    AuthenticationError,
    BadRequestError,
    ArticleContextNotFoundError,
    PaymentRequiredError,
    FreeAllowanceExhaustedError,
    RevisionLimitReachedError,
    RateLimitedError,
    RequestTimeoutError,
    UnsupportedMediaTypeError,
    ServerError,
    FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE,
    REVISION_LIMIT_REACHED_ERROR_CODE,
    FREE_RATE_LIMITED_ERROR_CODE,
)

__all__ = [
    # Clients
    "RespectifyClient",
    "RespectifyAsyncClient",
    "RespectifyPerspectiveClient",
    "RespectifyAsyncPerspectiveClient",
    # Response wrapper (body + revision token header)
    "RespectifyResponse",
    "REVISION_TOKEN_HEADER",
    # Schemas
    "CommentAssessment",
    "CommentScore",
    "FINDING_SEVERITY_MAX",
    "FINDING_SEVERITY_MIN",
    "FLOORED_MODERATION_CATEGORIES",
    "QUALITY_HEALTH_ITEM",
    "HealthItemScore",
    "ModerationCategory",
    "ModerationTolerances",
    "ToleranceLevel",
    "DogwhistleResult",
    "LogicalFallacy",
    "MegaCallResult", 
    "NegativeTonePhrase",
    "ObjectionablePhrase",
    "SpamDetectionResult",
    "CommentRelevanceResult",
    "OnTopicResult",
    "BannedTopicsResult", 
    "DogwhistleDetection",
    "DogwhistleDetails",
    "InitTopicResponse",
    "UserCheckResponse",
    "UserSubscriptionStatus",
    "PerspectiveScore",
    "PerspectiveAnalyzeCommentSpanScore",
    "PerspectiveAnalyzeCommentAttributeScore",
    "PerspectiveAnalyzeCommentResponse",
    "PerspectiveSuggestCommentScoreResponse",
    # Exceptions
    "RespectifyError",
    "AuthenticationError",
    "BadRequestError",
    "ArticleContextNotFoundError",
    "PaymentRequiredError",
    "FreeAllowanceExhaustedError",
    "RevisionLimitReachedError",
    "RateLimitedError",
    "RequestTimeoutError",
    "UnsupportedMediaTypeError",
    "ServerError",
    "FREE_ALLOWANCE_EXHAUSTED_ERROR_CODE",
    "REVISION_LIMIT_REACHED_ERROR_CODE",
    "FREE_RATE_LIMITED_ERROR_CODE",
]
