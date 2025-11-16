"""Synchronous client for the Respectify API."""

from typing import Dict, List, Optional, Union
from uuid import UUID

import httpx
from beartype import beartype

from respectify._base import BaseRespectifyClient
from respectify.schemas import (
    CommentRelevanceResult,
    CommentScore,
    DogwhistleResult,
    InitTopicResponse,
    MegaCallResult,
    SpamDetectionResult,
    UserCheckResponse,
)


class RespectifyClient(BaseRespectifyClient):
    """Synchronous client for the Respectify API."""
    
    @beartype
    def __init__(
        self,
        email: str,
        api_key: str,
        base_url: Optional[str] = None,
        version: Optional[str] = None,
        timeout: float = 30.0,
        website: Optional[str] = None
    ) -> None:
        """Initialize the synchronous Respectify client.
        
        Args:
            email: User email address for authentication
            api_key: API key for authentication
            base_url: Base URL for the Respectify API (defaults to production)
            version: API version to use (defaults to 0.2)
            timeout: Request timeout in seconds
            website: Optional website domain for license tracking
        """
        super().__init__(email, api_key, base_url, version, timeout, website)
        
    @beartype
    def init_topic_from_text(
        self, 
        text: str, 
        topic_description: Optional[str] = None
    ) -> InitTopicResponse:
        """Initialize a topic from text content.
        
        Args:
            text: The text content to initialize the topic from
            topic_description: Optional description of the topic
            
        Returns:
            InitTopicResponse containing the article ID
            
        Raises:
            RespectifyError: If the request fails
        """
        url: str = self._build_url("inittopic")
        headers: Dict[str, str] = self._build_headers()
        
        data: Dict[str, str] = {"text": text}
        if topic_description:
            data["topic_description"] = topic_description
            
        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                self._handle_error_response(response)
                
            return self._parse_response(response, InitTopicResponse)
    
    @beartype
    def init_topic_from_url(
        self, 
        url: str, 
        topic_description: Optional[str] = None
    ) -> InitTopicResponse:
        """Initialize a topic from a URL.
        
        Args:
            url: The URL to initialize the topic from
            topic_description: Optional description of the topic
            
        Returns:
            InitTopicResponse containing the article ID
            
        Raises:
            RespectifyError: If the request fails
        """
        api_url: str = self._build_url("inittopic")
        headers: Dict[str, str] = self._build_headers()
        
        data: Dict[str, str] = {"url": url}
        if topic_description:
            data["topic_description"] = topic_description
            
        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(api_url, json=data, headers=headers)
            
            if response.status_code != 200:
                self._handle_error_response(response)
                
            return self._parse_response(response, InitTopicResponse)
    
    @beartype
    def check_spam(self, comment: str, article_id: UUID) -> SpamDetectionResult:
        """Check if a comment is spam.
        
        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic
            
        Returns:
            SpamDetectionResult containing spam analysis
            
        Raises:
            RespectifyError: If the request fails
        """
        url: str = self._build_url("antispam")
        headers: Dict[str, str] = self._build_headers()
        
        data: Dict[str, str] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                self._handle_error_response(response)
                
            return self._parse_response(response, SpamDetectionResult)
    
    @beartype
    def check_relevance(
        self, 
        comment: str, 
        article_id: UUID,
        banned_topics: Optional[List[str]] = None
    ) -> CommentRelevanceResult:
        """Check if a comment is relevant to the topic.
        
        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic
            banned_topics: Optional list of banned topics to check against
            
        Returns:
            CommentRelevanceResult containing relevance analysis
            
        Raises:
            RespectifyError: If the request fails
        """
        url: str = self._build_url("commentrelevance")
        headers: Dict[str, str] = self._build_headers()
        
        data: Dict[str, Union[str, List[str]]] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        if banned_topics:
            data["banned_topics"] = banned_topics
            
        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                self._handle_error_response(response)
                
            return self._parse_response(response, CommentRelevanceResult)
    
    @beartype
    def evaluate_comment(self, comment: str, article_id: UUID) -> CommentScore:
        """Evaluate a comment's quality and toxicity.
        
        Args:
            comment: The comment text to evaluate
            article_id: UUID of the article/topic
            
        Returns:
            CommentScore containing comprehensive evaluation
            
        Raises:
            RespectifyError: If the request fails
        """
        url: str = self._build_url("commentscore")
        headers: Dict[str, str] = self._build_headers()
        
        data: Dict[str, str] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        
        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                self._handle_error_response(response)
                
            return self._parse_response(response, CommentScore)
    
    @beartype
    def check_dogwhistle(
        self,
        comment: str,
        article_id: UUID,
        sensitive_topics: Optional[List[str]] = None,
        dogwhistle_examples: Optional[List[str]] = None
    ) -> DogwhistleResult:
        """Check if a comment contains dogwhistle language.

        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic for context
            sensitive_topics: Optional list of sensitive topics to check against
            dogwhistle_examples: Optional list of known dogwhistle examples

        Returns:
            DogwhistleResult containing dogwhistle analysis

        Raises:
            RespectifyError: If the request fails
        """
        url: str = self._build_url("dogwhistle")
        headers: Dict[str, str] = self._build_headers()

        data: Dict[str, Union[str, List[str]]] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        if sensitive_topics:
            data["sensitive_topics"] = sensitive_topics
        if dogwhistle_examples:
            data["dogwhistle_examples"] = dogwhistle_examples

        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)

            if response.status_code != 200:
                self._handle_error_response(response)

            return self._parse_response(response, DogwhistleResult)
    
    @beartype
    def megacall(
        self,
        comment: str,
        article_id: UUID,
        include_spam: bool = False,
        include_relevance: bool = False,
        include_comment_score: bool = False,
        include_dogwhistle: bool = False,
        banned_topics: Optional[List[str]] = None,
        sensitive_topics: Optional[List[str]] = None,
        dogwhistle_examples: Optional[List[str]] = None
    ) -> MegaCallResult:
        """Perform multiple analysis types in a single API call.

        Args:
            comment: The comment text to analyze
            article_id: UUID of the article/topic
            include_spam: Include spam detection analysis
            include_relevance: Include relevance analysis
            include_comment_score: Include comment quality scoring
            include_dogwhistle: Include dogwhistle detection
            banned_topics: Optional list of banned topics for relevance check
            sensitive_topics: Optional list of sensitive topics for dogwhistle check
            dogwhistle_examples: Optional list of dogwhistle examples

        Returns:
            MegaCallResult containing requested analysis results

        Raises:
            RespectifyError: If the request fails
        """
        url: str = self._build_url("megacall")
        headers: Dict[str, str] = self._build_headers()

        data: Dict[str, Union[str, bool, List[str]]] = {
            "comment": comment,
            "article_context_id": str(article_id),
            "run_spam_check": include_spam,
            "run_relevance_check": include_relevance,
            "run_comment_score": include_comment_score,
            "run_dogwhistle_check": include_dogwhistle
        }

        if banned_topics:
            data["banned_topics"] = banned_topics
        if sensitive_topics:
            data["sensitive_topics"] = sensitive_topics
        if dogwhistle_examples:
            data["dogwhistle_examples"] = dogwhistle_examples

        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)

            if response.status_code != 200:
                self._handle_error_response(response)

            return self._parse_response(response, MegaCallResult)
    
    @beartype
    def check_user_credentials(self) -> UserCheckResponse:
        """Verify user credentials and check account status.
        
        Returns:
            UserCheckResponse containing authentication result
            
        Raises:
            RespectifyError: If the request fails with invalid credentials
        """
        url: str = self._build_url("usercheck")
        headers: Dict[str, str] = self._build_headers()

        with httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.get(url, headers=headers)

            # Accept both 200 (valid with subscription) and 402 (valid without subscription)
            if response.status_code not in [200, 402]:
                self._handle_error_response(response)

            return self._parse_response(response, UserCheckResponse)