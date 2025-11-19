"""Base exception classes for the Aashvi automation system."""

from typing import Optional, Dict, Any


class AashviError(Exception):
    """Base exception for all Aashvi automation errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional context information
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.original_error = original_error
    
    def __str__(self) -> str:
        """String representation of the error."""
        return f"[{self.error_code}] {self.message}"
    
    def __repr__(self) -> str:
        """Developer representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"context={self.context})"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'original_error': str(self.original_error) if self.original_error else None
        }


class RetryableError(AashviError):
    """Base class for errors that can be retried."""
    
    def __init__(
        self,
        message: str,
        retry_after_seconds: int = 60,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize retryable error.
        
        Args:
            message: Human-readable error message
            retry_after_seconds: Seconds to wait before retry
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.retry_after_seconds = retry_after_seconds
        self.max_retries = max_retries


class NonRetryableError(AashviError):
    """Base class for errors that should not be retried."""
    pass


class ConfigurationError(NonRetryableError):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        """Initialize configuration error.
        
        Args:
            message: Human-readable error message
            config_key: Configuration key that caused the error
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.config_key = config_key
        if config_key:
            self.context['config_key'] = config_key