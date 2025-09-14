"""Exception classes for the Respectify Python client library."""

from typing import Any, Dict, Optional

from beartype import beartype


class RespectifyError(Exception):
    """Base exception for all Respectify API errors."""

    @beartype
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None, 
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize a Respectify error.
        
        Args:
            message: Human-readable error description
            status_code: HTTP status code if applicable
            response_data: Raw response data from the API
        """
        super().__init__(message)
        self.message: str = message
        self.status_code: Optional[int] = status_code
        self.response_data: Optional[Dict[str, Any]] = response_data


class AuthenticationError(RespectifyError):
    """Raised when API authentication fails (401 Unauthorized)."""
    
    @beartype
    def __init__(
        self, 
        message: str = "Authentication failed. Check your email and API key.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=401, response_data=response_data)


class BadRequestError(RespectifyError):
    """Raised when the request is malformed or invalid (400 Bad Request)."""
    
    @beartype
    def __init__(
        self, 
        message: str = "Bad request. Check your request parameters.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=400, response_data=response_data)


class PaymentRequiredError(RespectifyError):
    """Raised when the account lacks subscription for the requested endpoint (402 Payment Required)."""
    
    @beartype
    def __init__(
        self, 
        message: str = "Payment required. Your plan does not include access to this endpoint.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=402, response_data=response_data)


class UnsupportedMediaTypeError(RespectifyError):
    """Raised when the request content type is not supported (415 Unsupported Media Type)."""
    
    @beartype
    def __init__(
        self, 
        message: str = "Unsupported media type. Use application/json.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=415, response_data=response_data)


class ServerError(RespectifyError):
    """Raised when the server encounters an internal error (500 Internal Server Error)."""
    
    @beartype
    def __init__(
        self, 
        message: str = "Internal server error. Please try again later.",
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, status_code=500, response_data=response_data)