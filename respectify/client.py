"""Synchronous client for the Respectify API."""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import httpx
from beartype import beartype

from respectify._base import BaseRespectifyClient, RespectifyResponse
from respectify.perspective import RespectifyPerspectiveClient
from respectify.schemas import (
    CommentRelevanceResult,
    CommentScore,
    ModerationTolerances,
    DogwhistleResult,
    InitTopicResponse,
    MegaCallResult,
    SpamDetectionResult,
    UserCheckResponse,
)


class RespectifyClient(BaseRespectifyClient):
    """Synchronous client for the Respectify API.

    Each method that assesses a comment (``check_spam``, ``check_relevance``,
    ``evaluate_comment``, ``check_dogwhistle``, ``megacall``) takes an optional
    ``revision_token`` and has a ``*_response`` twin that returns a
    :class:`~respectify._base.RespectifyResponse` carrying the parsed result and the
    revision token the server issued. Free-plan accounts need the token to re-assess a
    revised comment without it counting as a new one; paid accounts never receive one.
    """

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
        self.perspective = RespectifyPerspectiveClient(self)

    @beartype
    def _post_json(
        self,
        endpoint: str,
        data: Dict[str, Any],
        revision_token: Optional[str] = None
    ) -> httpx.Response:
        """POST a JSON body to an endpoint and return the successful response.

        Args:
            endpoint: The API endpoint (e.g. 'commentscore')
            data: The JSON body
            revision_token: Optional free-plan revision token to send back in its header

        Raises:
            RequestTimeoutError: If the request times out
            RespectifyError: If the server answers with an error status
        """
        url: str = self._build_url(endpoint)
        headers: Dict[str, str] = self._build_headers(revision_token)

        with self._timeout_guard(), httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.post(url, json=data, headers=headers)

        if response.status_code != 200:
            self._handle_error_response(response)

        return response

    @beartype
    def _get(self, endpoint: str) -> httpx.Response:
        """GET an endpoint and return the successful response.

        Raises:
            RequestTimeoutError: If the request times out
            RespectifyError: If the server answers with an error status
        """
        url: str = self._build_url(endpoint)
        headers: Dict[str, str] = self._build_headers()

        with self._timeout_guard(), httpx.Client(timeout=self.timeout) as client:
            response: httpx.Response = client.get(url, headers=headers)

        if response.status_code != 200:
            self._handle_error_response(response)

        return response

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
        data: Dict[str, str] = {"text": text}
        if topic_description:
            data["topic_description"] = topic_description

        response: httpx.Response = self._post_json("inittopic", data)
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
        data: Dict[str, str] = {"url": url}
        if topic_description:
            data["topic_description"] = topic_description

        response: httpx.Response = self._post_json("inittopic", data)
        return self._parse_response(response, InitTopicResponse)

    # --- Spam -------------------------------------------------------------------------

    @beartype
    def check_spam_response(
        self,
        comment: str,
        article_id: Optional[UUID] = None,
        revision_token: Optional[str] = None
    ) -> RespectifyResponse[SpamDetectionResult]:
        """Check if a comment is spam, returning the result with its revision token.

        Args:
            comment: The comment text to check
            article_id: Optional UUID of the article/topic for context
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            RespectifyResponse whose ``result`` is the SpamDetectionResult and whose
            ``revision_token`` is the server's token for this comment, or None

        Raises:
            RespectifyError: If the request fails
        """
        data: Dict[str, str] = {
            "comment": comment,
        }
        if article_id is not None:
            data["article_context_id"] = str(article_id)

        response: httpx.Response = self._post_json("antispam", data, revision_token)
        return self._parse_response_with_token(response, SpamDetectionResult)

    @beartype
    def check_spam(
        self,
        comment: str,
        article_id: Optional[UUID] = None,
        revision_token: Optional[str] = None
    ) -> SpamDetectionResult:
        """Check if a comment is spam.

        Args:
            comment: The comment text to check
            article_id: Optional UUID of the article/topic for context
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            SpamDetectionResult containing spam analysis

        Raises:
            RespectifyError: If the request fails
        """
        return self.check_spam_response(comment, article_id, revision_token).result

    # --- Relevance --------------------------------------------------------------------

    @beartype
    def check_relevance_response(
        self,
        comment: str,
        article_id: UUID,
        banned_topics: Optional[List[str]] = None,
        revision_token: Optional[str] = None
    ) -> RespectifyResponse[CommentRelevanceResult]:
        """Check if a comment is relevant to the topic, returning the result with its revision token.

        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic
            banned_topics: Optional list of banned topics to check against
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            RespectifyResponse whose ``result`` is the CommentRelevanceResult and whose
            ``revision_token`` is the server's token for this comment, or None

        Raises:
            RespectifyError: If the request fails
        """
        data: Dict[str, Union[str, List[str]]] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        if banned_topics:
            data["banned_topics"] = banned_topics

        response: httpx.Response = self._post_json("commentrelevance", data, revision_token)
        return self._parse_response_with_token(response, CommentRelevanceResult)

    @beartype
    def check_relevance(
        self,
        comment: str,
        article_id: UUID,
        banned_topics: Optional[List[str]] = None,
        revision_token: Optional[str] = None
    ) -> CommentRelevanceResult:
        """Check if a comment is relevant to the topic.

        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic
            banned_topics: Optional list of banned topics to check against
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            CommentRelevanceResult containing relevance analysis

        Raises:
            RespectifyError: If the request fails
        """
        return self.check_relevance_response(comment, article_id, banned_topics, revision_token).result

    # --- Comment score ----------------------------------------------------------------

    @beartype
    def evaluate_comment_response(
        self,
        comment: str,
        article_id: UUID,
        reply_to_comment: Optional[str] = None,
        tolerances: Optional[ModerationTolerances] = None,
        revision_token: Optional[str] = None
    ) -> RespectifyResponse[CommentScore]:
        """Evaluate a comment's quality and toxicity, returning the result with its revision token.

        Args:
            comment: The comment text to evaluate
            article_id: UUID of the article/topic
            reply_to_comment: Optional text of the comment being replied to, for context
            tolerances: Optional comment-health levels for this call; items not named are standard
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            RespectifyResponse whose ``result`` is the CommentScore and whose
            ``revision_token`` is the server's token for this comment, or None

        Raises:
            RespectifyError: If the request fails
        """
        data: Dict[str, Union[str, Dict[str, str]]] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        if reply_to_comment is not None:
            data["reply_to_comment"] = reply_to_comment
        if tolerances is not None:
            data["tolerances"] = tolerances.model_dump(mode="json", exclude_unset=True)

        response: httpx.Response = self._post_json("commentscore", data, revision_token)
        return self._parse_response_with_token(response, CommentScore)

    @beartype
    def evaluate_comment(
        self,
        comment: str,
        article_id: UUID,
        reply_to_comment: Optional[str] = None,
        tolerances: Optional[ModerationTolerances] = None,
        revision_token: Optional[str] = None
    ) -> CommentScore:
        """Evaluate a comment's quality and toxicity.

        Args:
            comment: The comment text to evaluate
            article_id: UUID of the article/topic
            reply_to_comment: Optional text of the comment being replied to, for context
            tolerances: Optional comment-health levels for this call; items not named are standard
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            CommentScore containing comprehensive evaluation

        Raises:
            RespectifyError: If the request fails
        """
        return self.evaluate_comment_response(
            comment, article_id, reply_to_comment, tolerances, revision_token
        ).result

    # --- Dogwhistle -------------------------------------------------------------------

    @beartype
    def check_dogwhistle_response(
        self,
        comment: str,
        article_id: UUID,
        sensitive_topics: Optional[List[str]] = None,
        dogwhistle_examples: Optional[List[str]] = None,
        revision_token: Optional[str] = None
    ) -> RespectifyResponse[DogwhistleResult]:
        """Check if a comment contains dogwhistle language, returning the result with its revision token.

        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic for context
            sensitive_topics: Optional list of sensitive topics to check against
            dogwhistle_examples: Optional list of known dogwhistle examples
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            RespectifyResponse whose ``result`` is the DogwhistleResult and whose
            ``revision_token`` is the server's token for this comment, or None

        Raises:
            RespectifyError: If the request fails
        """
        data: Dict[str, Union[str, List[str]]] = {
            "comment": comment,
            "article_context_id": str(article_id)
        }
        if sensitive_topics:
            data["sensitive_topics"] = sensitive_topics
        if dogwhistle_examples:
            data["dogwhistle_examples"] = dogwhistle_examples

        response: httpx.Response = self._post_json("dogwhistle", data, revision_token)
        return self._parse_response_with_token(response, DogwhistleResult)

    @beartype
    def check_dogwhistle(
        self,
        comment: str,
        article_id: UUID,
        sensitive_topics: Optional[List[str]] = None,
        dogwhistle_examples: Optional[List[str]] = None,
        revision_token: Optional[str] = None
    ) -> DogwhistleResult:
        """Check if a comment contains dogwhistle language.

        Args:
            comment: The comment text to check
            article_id: UUID of the article/topic for context
            sensitive_topics: Optional list of sensitive topics to check against
            dogwhistle_examples: Optional list of known dogwhistle examples
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            DogwhistleResult containing dogwhistle analysis

        Raises:
            RespectifyError: If the request fails
        """
        return self.check_dogwhistle_response(
            comment, article_id, sensitive_topics, dogwhistle_examples, revision_token
        ).result

    # --- Megacall ---------------------------------------------------------------------

    @beartype
    def megacall_response(
        self,
        comment: str,
        article_id: Optional[UUID] = None,
        include_spam: bool = False,
        include_relevance: bool = False,
        include_comment_score: bool = False,
        include_dogwhistle: bool = False,
        include_perspective_analyze_comment: bool = False,
        banned_topics: Optional[List[str]] = None,
        sensitive_topics: Optional[List[str]] = None,
        dogwhistle_examples: Optional[List[str]] = None,
        reply_to_comment: Optional[str] = None,
        context_comments: Optional[List[str]] = None,
        tolerances: Optional[ModerationTolerances] = None,
        revision_token: Optional[str] = None
    ) -> RespectifyResponse[MegaCallResult]:
        """Perform multiple analysis types in a single API call, returning the result with its revision token.

        Args:
            comment: The comment text to analyze
            article_id: UUID of the article/topic (required for comment_score, relevance, dogwhistle)
            include_spam: Include spam detection analysis
            include_relevance: Include relevance analysis
            include_comment_score: Include comment quality scoring
            include_dogwhistle: Include dogwhistle detection
            include_perspective_analyze_comment: Include Perspective-compatible analyzeComment scoring
            banned_topics: Optional list of banned topics for relevance check
            sensitive_topics: Optional list of sensitive topics for dogwhistle check
            dogwhistle_examples: Optional list of dogwhistle examples
            reply_to_comment: Optional text of the comment being replied to, for comment score context
            context_comments: Optional prior comments for perspective context
            tolerances: Optional comment-health levels for the comment score; items not named are standard
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            RespectifyResponse whose ``result`` is the MegaCallResult and whose
            ``revision_token`` is the server's token for this comment, or None

        Raises:
            RespectifyError: If the request fails
        """
        data: Dict[str, Union[str, bool, List[str], Dict[str, str]]] = {
            "comment": comment,
            "run_spam_check": include_spam,
            "run_relevance_check": include_relevance,
            "run_comment_score": include_comment_score,
            "run_dogwhistle_check": include_dogwhistle,
            "run_perspective": include_perspective_analyze_comment,
        }

        if article_id:
            data["article_context_id"] = str(article_id)
        if banned_topics:
            data["banned_topics"] = banned_topics
        if sensitive_topics:
            data["sensitive_topics"] = sensitive_topics
        if dogwhistle_examples:
            data["dogwhistle_examples"] = dogwhistle_examples
        if reply_to_comment is not None:
            data["reply_to_comment"] = reply_to_comment
        if context_comments:
            data["context_comments"] = context_comments
        if tolerances is not None:
            data["tolerances"] = tolerances.model_dump(mode="json", exclude_unset=True)

        response: httpx.Response = self._post_json("megacall", data, revision_token)
        return self._parse_response_with_token(response, MegaCallResult)

    @beartype
    def megacall(
        self,
        comment: str,
        article_id: Optional[UUID] = None,
        include_spam: bool = False,
        include_relevance: bool = False,
        include_comment_score: bool = False,
        include_dogwhistle: bool = False,
        include_perspective_analyze_comment: bool = False,
        banned_topics: Optional[List[str]] = None,
        sensitive_topics: Optional[List[str]] = None,
        dogwhistle_examples: Optional[List[str]] = None,
        reply_to_comment: Optional[str] = None,
        context_comments: Optional[List[str]] = None,
        tolerances: Optional[ModerationTolerances] = None,
        revision_token: Optional[str] = None
    ) -> MegaCallResult:
        """Perform multiple analysis types in a single API call.

        Args:
            comment: The comment text to analyze
            article_id: UUID of the article/topic (required for comment_score, relevance, dogwhistle)
            include_spam: Include spam detection analysis
            include_relevance: Include relevance analysis
            include_comment_score: Include comment quality scoring
            include_dogwhistle: Include dogwhistle detection
            include_perspective_analyze_comment: Include Perspective-compatible analyzeComment scoring
            banned_topics: Optional list of banned topics for relevance check
            sensitive_topics: Optional list of sensitive topics for dogwhistle check
            dogwhistle_examples: Optional list of dogwhistle examples
            reply_to_comment: Optional text of the comment being replied to, for comment score context
            context_comments: Optional prior comments for perspective context
            tolerances: Optional comment-health levels for the comment score; items not named are standard
            revision_token: Token from an earlier assessment of this same comment (free plan)

        Returns:
            MegaCallResult containing requested analysis results

        Raises:
            RespectifyError: If the request fails
        """
        return self.megacall_response(
            comment,
            article_id,
            include_spam,
            include_relevance,
            include_comment_score,
            include_dogwhistle,
            include_perspective_analyze_comment,
            banned_topics,
            sensitive_topics,
            dogwhistle_examples,
            reply_to_comment,
            context_comments,
            tolerances,
            revision_token,
        ).result

    @beartype
    def check_user_credentials(self) -> UserCheckResponse:
        """Verify user credentials and check the account's credit balance.

        Returns:
            UserCheckResponse describing the credit balance (active, status, plan_name, etc.)

        Raises:
            AuthenticationError: If credentials are invalid (401)
            RespectifyError: If the request fails for other reasons
        """
        response: httpx.Response = self._get("usercheck")
        return self._parse_response(response, UserCheckResponse)
