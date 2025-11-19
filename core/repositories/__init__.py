"""Repository pattern implementations for data access."""

from .content_repository import ContentRepository
from .config_repository import ConfigRepository

__all__ = [
    'ContentRepository',
    'ConfigRepository',
]