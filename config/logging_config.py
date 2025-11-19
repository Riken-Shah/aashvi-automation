"""Logging configuration for the Aashvi automation system.

This module provides centralized logging configuration with structured logging,
multiple handlers, and production-ready features like log rotation and filtering.
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .settings import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Add exception information
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add process and thread info
        log_data['process_id'] = record.process
        log_data['thread_id'] = record.thread
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Build formatted message
        formatted_message = (
            f"{color}[{timestamp}] {record.levelname:8} "
            f"{record.name}:{record.lineno} - {record.getMessage()}{reset}"
        )
        
        # Add exception information
        if record.exc_info:
            formatted_message += f"\n{self.formatException(record.exc_info)}"
        
        return formatted_message


class SecurityFilter(logging.Filter):
    """Filter to prevent sensitive information from being logged."""
    
    SENSITIVE_PATTERNS = [
        'api_key', 'password', 'token', 'secret', 'credential',
        'authorization', 'bearer', 'key', 'private'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out log records containing sensitive information."""
        message = record.getMessage().lower()
        
        # Check if message contains sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                record.msg = "[REDACTED - Contains sensitive information]"
                break
        
        return True


class PerformanceFilter(logging.Filter):
    """Filter to track performance metrics."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add performance context to log records."""
        if hasattr(record, 'duration'):
            if record.duration > 5.0:  # Log slow operations
                record.msg = f"[SLOW OPERATION] {record.msg} (took {record.duration:.2f}s)"
        
        return True


def setup_logging() -> None:
    """Set up logging configuration for the application."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.app.debug else logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler for development
    if settings.is_development:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ColoredConsoleFormatter())
        console_handler.addFilter(SecurityFilter())
        root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "aashvi_automation.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    file_handler.addFilter(SecurityFilter())
    file_handler.addFilter(PerformanceFilter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler.addFilter(SecurityFilter())
    root_logger.addHandler(error_handler)
    
    # Performance log handler
    perf_handler = logging.handlers.RotatingFileHandler(
        log_dir / "performance.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=2,
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(JSONFormatter())
    perf_filter = logging.Filter()
    perf_filter.filter = lambda record: hasattr(record, 'duration')
    perf_handler.addFilter(perf_filter)
    root_logger.addHandler(perf_handler)
    
    # Configure specific loggers
    configure_third_party_loggers()
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging system initialized",
        extra={
            'environment': settings.app.environment,
            'debug_mode': settings.app.debug,
            'log_level': logging.getLevelName(root_logger.level)
        }
    )


def configure_third_party_loggers() -> None:
    """Configure logging for third-party libraries."""
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('requests.packages.urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding structured logging context."""
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None
    
    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.extra = getattr(record, 'extra', {})
            record.extra.update(self.context)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)


class PerformanceLogger:
    """Logger for tracking performance metrics."""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                f"Operation failed: {self.operation}",
                extra={'duration': duration, 'operation': self.operation},
                exc_info=(exc_type, exc_val, exc_tb)
            )
        else:
            self.logger.info(
                f"Operation completed: {self.operation}",
                extra={'duration': duration, 'operation': self.operation}
            )


def log_function_call(func):
    """Decorator to log function calls with performance metrics."""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        start_time = time.time()
        try:
            logger.debug(
                f"Calling function: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'module': func.__module__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
            )
            
            result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            logger.debug(
                f"Function completed: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'module': func.__module__,
                    'duration': duration
                }
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Function failed: {func.__name__}",
                extra={
                    'function': func.__name__,
                    'module': func.__module__,
                    'duration': duration,
                    'error': str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper


# Initialize logging when module is imported
setup_logging()