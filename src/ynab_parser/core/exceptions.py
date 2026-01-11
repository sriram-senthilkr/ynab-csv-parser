"""
Custom exception hierarchy for YNAB Parser.

Provides structured error handling for:
- Configuration errors
- API errors
- Parsing errors
- Validation errors
"""

from typing import Optional, Dict, Any


class YNABParserError(Exception):
    """Base exception for all YNAB Parser errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details for debugging
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            details_str = " | ".join(f"{k}={v}" for k, v in self.details.items())
            return f"[{self.error_code}] {self.message} ({details_str})"
        return f"[{self.error_code}] {self.message}"


class ConfigurationError(YNABParserError):
    """Raised when configuration is invalid or missing."""

    pass


class ValidationError(YNABParserError):
    """Raised when data validation fails."""

    pass


class ParserError(YNABParserError):
    """Raised when CSV parsing fails."""

    pass


class APIError(YNABParserError):
    """Base exception for YNAB API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: API response data
            error_code: YNAB error code
            details: Additional details
        """
        self.status_code = status_code
        self.response_data = response_data or {}
        details = details or {}
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, error_code, details)


class YNABAuthError(APIError):
    """Raised when authentication fails (401)."""

    pass


class YNABRateLimitError(APIError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            details: Additional details
        """
        self.retry_after = retry_after or 60
        details = details or {}
        details["retry_after"] = self.retry_after
        super().__init__(message, status_code=429, details=details)


class NotFoundError(APIError):
    """Raised when a resource is not found (404)."""

    pass
