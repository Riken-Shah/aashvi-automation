"""Storage-related exceptions."""

from typing import Optional
from .base import AashviError, NonRetryableError, RetryableError


class StorageError(AashviError):
    """Base exception for storage-related errors."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        """Initialize storage error.
        
        Args:
            message: Human-readable error message
            file_path: Path to the file that caused the error
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.file_path = file_path
        if file_path:
            self.context['file_path'] = file_path


class FileNotFoundError(StorageError, NonRetryableError):
    """Exception raised when a required file is not found."""
    
    def __init__(self, file_path: str, **kwargs):
        message = f"Required file not found: {file_path}"
        super().__init__(
            message,
            file_path=file_path,
            error_code="FILE_NOT_FOUND",
            **kwargs
        )


class FileAccessError(StorageError, NonRetryableError):
    """Exception raised when file access is denied."""
    
    def __init__(self, file_path: str, operation: str = "access", **kwargs):
        message = f"File {operation} denied: {file_path}"
        super().__init__(
            message,
            file_path=file_path,
            error_code="FILE_ACCESS_DENIED",
            **kwargs
        )
        self.operation = operation
        self.context['operation'] = operation


class DirectoryError(StorageError, NonRetryableError):
    """Exception raised for directory-related errors."""
    
    def __init__(self, directory_path: str, operation: str = "access", **kwargs):
        message = f"Directory {operation} failed: {directory_path}"
        super().__init__(
            message,
            file_path=directory_path,
            error_code="DIRECTORY_ERROR",
            **kwargs
        )
        self.operation = operation
        self.context['operation'] = operation


class DiskSpaceError(StorageError, RetryableError):
    """Exception raised when disk space is insufficient."""
    
    def __init__(self, required_space: Optional[int] = None, **kwargs):
        message = "Insufficient disk space"
        if required_space:
            message += f" (required: {required_space} bytes)"
        
        super().__init__(
            message,
            error_code="INSUFFICIENT_DISK_SPACE",
            retry_after_seconds=1800,  # 30 minutes
            **kwargs
        )
        self.required_space = required_space
        if required_space:
            self.context['required_space'] = required_space


class FileCorruptionError(StorageError, NonRetryableError):
    """Exception raised when a file is corrupted or invalid."""
    
    def __init__(self, file_path: str, corruption_type: str = "unknown", **kwargs):
        message = f"File corrupted ({corruption_type}): {file_path}"
        super().__init__(
            message,
            file_path=file_path,
            error_code="FILE_CORRUPTION",
            **kwargs
        )
        self.corruption_type = corruption_type
        self.context['corruption_type'] = corruption_type


class FileSizeError(StorageError, NonRetryableError):
    """Exception raised when file size exceeds limits."""
    
    def __init__(
        self,
        file_path: str,
        actual_size: int,
        max_size: int,
        **kwargs
    ):
        message = (
            f"File size exceeds limit: {file_path} "
            f"(actual: {actual_size}, max: {max_size})"
        )
        super().__init__(
            message,
            file_path=file_path,
            error_code="FILE_SIZE_EXCEEDED",
            **kwargs
        )
        self.actual_size = actual_size
        self.max_size = max_size
        self.context.update({
            'actual_size': actual_size,
            'max_size': max_size
        })