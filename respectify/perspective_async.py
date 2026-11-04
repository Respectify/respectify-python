"""Async Perspective compatibility sub-client."""

from typing import Any, Dict

import httpx
from beartype import beartype

from respectify.schemas import (
    PerspectiveAnalyzeCommentResponse,
    PerspectiveSuggestCommentScoreResponse,
)


class RespectifyAsyncPerspectiveClient:
    """Thin async wrapper over Respectify's public Perspective compatibility endpoints.

    Requests go through the parent client's ``_post_json``, so they share its timeout
    handling and error mapping. These endpoints never use revision tokens.
    """

    @beartype
    def __init__(self, parent_client: Any) -> None:
        self._parent = parent_client

    @beartype
    async def analyze_comment(
        self,
        request: Dict[str, Any],
    ) -> PerspectiveAnalyzeCommentResponse:
        """Call the public Perspective-compatible analyzeComment endpoint."""
        response: httpx.Response = await self._parent._post_json("perspective-compat/analyse", request)
        return self._parent._parse_response(response, PerspectiveAnalyzeCommentResponse)

    @beartype
    async def suggest_comment_score(
        self,
        request: Dict[str, Any],
    ) -> PerspectiveSuggestCommentScoreResponse:
        """Call the public Perspective-compatible suggestCommentScore endpoint."""
        response: httpx.Response = await self._parent._post_json("perspective-compat/suggestscore", request)
        return self._parent._parse_response(response, PerspectiveSuggestCommentScoreResponse)
