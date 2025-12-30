"""Base client functionality shared between sync and async clients."""

from typing import Any, Dict, Optional, Type, TypeVar, Union
from urllib.parse import urljoin

import httpx
from beartype import beartype
from pydantic import BaseModel

from respectify.exceptions import (
    AuthenticationError,
    BadRequestError, 
    PaymentRequiredError,
    RespectifyError,
    ServerError,
    UnsupportedMediaTypeError,
)

T = TypeVar('T', bound=BaseModel)


class BaseRespectifyClient:
    """Base client with shared functionality for authentication and error handling."""
    
    DEFAULT_BASE_URL: str = "https://app.respectify.ai"
    DEFAULT_VERSION: str = "0.2"
    
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
        """Initialize the base client.
        
        Args:
            email: User email address for authentication
            api_key: API key for authentication
            base_url: Base URL for the Respectify API (defaults to production)
            version: API version to use (defaults to 0.2)
            timeout: Request timeout in seconds
            website: Optional website domain for license tracking
        """
        self.email: str = email
        self.api_key: str = api_key
        self.base_url: str = (base_url or self.DEFAULT_BASE_URL).rstrip('/')
        self.version: str = version or self.DEFAULT_VERSION
        self.timeout: float = timeout
        self.website: Optional[str] = website
        
    @beartype
    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for an API endpoint.
        
        Args:
            endpoint: The API endpoint (e.g., 'antispam', 'dogwhistle')
            
        Returns:
            The full URL for the endpoint
        """
        versioned_endpoint: str = f"v{self.version}/{endpoint}"
        return urljoin(f"{self.base_url}/", versioned_endpoint)
        
    @beartype
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests.
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": self.email,
            "X-API-Key": self.api_key,
        }
        if self.website:
            headers["X-Website"] = self.website
        return headers
        
    @beartype
    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle HTTP error responses by raising appropriate exceptions.
        
        Args:
            response: The HTTP response object
            
        Raises:
            Appropriate RespectifyError subclass based on status code
        """
        status_code: int = response.status_code
        
        # Try to parse error response as JSON
        response_data: Optional[Dict[str, Any]] = None
        try:
            response_data = response.json()
        except Exception:
            pass  # Response may not be JSON
            
        # Extract error message
        error_message: str
        if response_data and isinstance(response_data, dict):
            error_message = response_data.get('message', response_data.get('detail', f"HTTP {status_code}: {response.reason_phrase}"))
        else:
            error_message = f"HTTP {status_code}: {response.reason_phrase}"
        
        # Raise appropriate exception based on status code
        if status_code == 400:
            raise BadRequestError(error_message, response_data)
        elif status_code == 401:
            raise AuthenticationError(error_message, response_data)
        elif status_code == 402:
            raise PaymentRequiredError(error_message, response_data)
        elif status_code == 415:
            raise UnsupportedMediaTypeError(error_message, response_data)
        elif status_code >= 500:
            raise ServerError(error_message, response_data)
        else:
            raise RespectifyError(error_message, status_code, response_data)
            
    @beartype
    def _parse_response(self, response: httpx.Response, schema_class: Type[T]) -> T:
        """Parse a successful HTTP response using the provided Pydantic schema.
        
        Args:
            response: The HTTP response object
            schema_class: Pydantic model class to parse the response
            
        Returns:
            Parsed response object
            
        Raises:
            RespectifyError: If the response cannot be parsed
        """
        try:
            response_data: Dict[str, Any] = response.json()
            return schema_class.model_validate(response_data)
        except Exception as e:
            raise RespectifyError(
                f"Failed to parse response: {str(e)}",
                response.status_code,
                {"raw_response": response.text}
            ) from e