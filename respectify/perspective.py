"""Synchronous Perspective compatibility sub-client."""

from typing import Any, Dict

import httpx
from beartype import beartype

from respectify.schemas import (
    PerspectiveAnalyzeCommentResponse,
    PerspectiveSuggestCommentScoreResponse,
)


class RespectifyPerspectiveClient:
    """Thin wrapper over Respectify's public Perspective compatibility endpoints."""

    @beartype
    def __init__(self, parent_client: Any) -> None:
        self._parent = parent_client

    @beartype
    def analyze_comment(
        self,
        request: Dict[str, Any],
    ) -> PerspectiveAnalyzeCommentResponse:
        """Call the public Perspective-compatible analyzeComment endpoint."""
        url = self._parent._build_url("perspective-compat/analyse")
        headers = self._parent._build_headers()

        with httpx.Client(timeout=self._parent.timeout) as client:
            response = client.post(url, json=request, headers=headers)

            if response.status_code != 200:
                self._parent._handle_error_response(response)

            return self._parent._parse_response(
                response, PerspectiveAnalyzeCommentResponse
            )

    @beartype
    def suggest_comment_score(
        self,
        request: Dict[str, Any],
    ) -> PerspectiveSuggestCommentScoreResponse:
        """Call the public Perspective-compatible suggestCommentScore endpoint."""
        url = self._parent._build_url("perspective-compat/suggestscore")
        headers = self._parent._build_headers()

        with httpx.Client(timeout=self._parent.timeout) as client:
            response = client.post(url, json=request, headers=headers)

            if response.status_code != 200:
                self._parent._handle_error_response(response)

            return self._parent._parse_response(
                response, PerspectiveSuggestCommentScoreResponse
            )
