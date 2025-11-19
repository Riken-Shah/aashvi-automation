"""API-related exceptions."""

from typing import Optional, Dict, Any
from .base import AashviError, RetryableError, NonRetryableError


class APIError(AashviError):
    """Base exception for API-related errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Initialize API error.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            response_data: Response data from API
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_data = response_data or {}
        
        if status_code:
            self.context['status_code'] = status_code
        if response_data:
            self.context['response_data'] = response_data


class OpenAIError(APIError):
    """Exception raised for OpenAI API errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="OPENAI_API_ERROR", **kwargs)


class OpenAIRateLimitError(OpenAIError, RetryableError):
    """Exception raised when OpenAI API rate limit is exceeded."""
    
    def __init__(self, message: str = "OpenAI API rate limit exceeded", **kwargs):
        super().__init__(
            message,
            error_code="OPENAI_RATE_LIMIT",
            retry_after_seconds=60,
            **kwargs
        )


class OpenAIAuthenticationError(OpenAIError, NonRetryableError):
    """Exception raised for OpenAI authentication errors."""
    
    def __init__(self, message: str = "OpenAI API authentication failed", **kwargs):
        super().__init__(message, error_code="OPENAI_AUTH_ERROR", **kwargs)


class StableDiffusionError(APIError):
    """Exception raised for Stable Diffusion API errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="STABLE_DIFFUSION_ERROR", **kwargs)


class StableDiffusionUnavailableError(StableDiffusionError, RetryableError):
    """Exception raised when Stable Diffusion API is unavailable."""
    
    def __init__(self, message: str = "Stable Diffusion API is unavailable", **kwargs):
        super().__init__(
            message,
            error_code="STABLE_DIFFUSION_UNAVAILABLE",
            retry_after_seconds=300,  # 5 minutes
            **kwargs
        )


class GoogleSheetsError(APIError):
    """Exception raised for Google Sheets API errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="GOOGLE_SHEETS_ERROR", **kwargs)


class GoogleSheetsQuotaError(GoogleSheetsError, RetryableError):
    """Exception raised when Google Sheets API quota is exceeded."""
    
    def __init__(self, message: str = "Google Sheets API quota exceeded", **kwargs):
        super().__init__(
            message,
            error_code="GOOGLE_SHEETS_QUOTA",
            retry_after_seconds=3600,  # 1 hour
            **kwargs
        )


class GoogleDriveError(APIError):
    """Exception raised for Google Drive API errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="GOOGLE_DRIVE_ERROR", **kwargs)


class GoogleDriveQuotaError(GoogleDriveError, RetryableError):
    """Exception raised when Google Drive API quota is exceeded."""
    
    def __init__(self, message: str = "Google Drive API quota exceeded", **kwargs):
        super().__init__(
            message,
            error_code="GOOGLE_DRIVE_QUOTA",
            retry_after_seconds=3600,  # 1 hour
            **kwargs
        )


class TelegramError(APIError):
    """Exception raised for Telegram API errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="TELEGRAM_ERROR", **kwargs)


class TelegramRateLimitError(TelegramError, RetryableError):
    """Exception raised when Telegram API rate limit is exceeded."""
    
    def __init__(self, message: str = "Telegram API rate limit exceeded", **kwargs):
        super().__init__(
            message,
            error_code="TELEGRAM_RATE_LIMIT",
            retry_after_seconds=30,
            **kwargs
        )