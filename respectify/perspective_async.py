"""Async Perspective compatibility sub-client."""

from typing import Any, Dict

import httpx
from beartype import beartype

from respectify.schemas import (
    PerspectiveAnalyzeCommentResponse,
    PerspectiveSuggestCommentScoreResponse,
)


class RespectifyAsyncPerspectiveClient:
    """Thin async wrapper over Respectify's public Perspective compatibility endpoints."""

    @beartype
    def __init__(self, parent_client: Any) -> None:
        self._parent = parent_client

    @beartype
    async def analyze_comment(
        self,
        request: Dict[str, Any],
    ) -> PerspectiveAnalyzeCommentResponse:
        """Call the public Perspective-compatible analyzeComment endpoint."""
        url = self._parent._build_url("perspective-compat/analyse")
        headers = self._parent._build_headers()

        async with httpx.AsyncClient(timeout=self._parent.timeout) as client:
            response = await client.post(url, json=request, headers=headers)

            if response.status_code != 200:
                self._parent._handle_error_response(response)

            return self._parent._parse_response(
                response, PerspectiveAnalyzeCommentResponse
            )

    @beartype
    async def suggest_comment_score(
        self,
        request: Dict[str, Any],
    ) -> PerspectiveSuggestCommentScoreResponse:
        """Call the public Perspective-compatible suggestCommentScore endpoint."""
        url = self._parent._build_url("perspective-compat/suggestscore")
        headers = self._parent._build_headers()

        async with httpx.AsyncClient(timeout=self._parent.timeout) as client:
            response = await client.post(url, json=request, headers=headers)

            if response.status_code != 200:
                self._parent._handle_error_response(response)

            return self._parent._parse_response(
                response, PerspectiveSuggestCommentScoreResponse
            )
