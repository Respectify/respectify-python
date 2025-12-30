"""Respectify Python Client Library.

A Python client library for the Respectify API, providing both synchronous and 
asynchronous interfaces for comment moderation, spam detection, toxicity analysis,
and dogwhistle detection.
"""

__version__ = "0.2.1"

from respectify.client import RespectifyClient
from respectify.client_async import RespectifyAsyncClient
from respectify.schemas import (
    CommentScore,
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
)
from respectify.exceptions import (
    RespectifyError,
    AuthenticationError,
    BadRequestError,
    PaymentRequiredError,
    UnsupportedMediaTypeError,
    ServerError,
)

__all__ = [
    # Clients
    "RespectifyClient",
    "RespectifyAsyncClient",
    # Schemas
    "CommentScore",
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
    # Exceptions
    "RespectifyError",
    "AuthenticationError",
    "BadRequestError",
    "PaymentRequiredError",
    "UnsupportedMediaTypeError",
    "ServerError",
]