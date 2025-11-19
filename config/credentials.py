"""Secure credential management for the Aashvi automation system.

This module provides secure handling of sensitive credentials and API keys,
with validation and encryption capabilities.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from google.oauth2.service_account import Credentials
from cryptography.fernet import Fernet
import base64
import logging

from .settings import settings

logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Exception raised for credential-related errors."""
    pass


class SecureCredentialManager:
    """Manages secure loading and validation of credentials."""
    
    def __init__(self):
        self._google_credentials: Optional[Credentials] = None
        self._encryption_key: Optional[bytes] = None
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for sensitive data."""
        if self._encryption_key is None:
            # In production, this should come from a secure key management service
            key_env = os.getenv("ENCRYPTION_KEY")
            if key_env:
                self._encryption_key = base64.urlsafe_b64decode(key_env.encode())
            else:
                # Generate a key for development (not recommended for production)
                self._encryption_key = Fernet.generate_key()
                logger.warning(
                    "Generated temporary encryption key. "
                    "Set ENCRYPTION_KEY environment variable for production."
                )
        return self._encryption_key
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(data.encode()).decode()
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data.encode()).decode()
    
    def validate_required_env_vars(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            "OPENAI_API_KEY",
            "GSPREED_KEY",
            "TELEGRAM_WEBHOOK_URL",
            "TELEGRAM_CHAT_ID",
            "GOOGLE_CREDENTIALS_PATH"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise CredentialError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    def get_google_credentials(self) -> Credentials:
        """Get Google service account credentials with validation."""
        if self._google_credentials is None:
            credentials_path = settings.database.google_credentials_path
            
            if not os.path.exists(credentials_path):
                raise CredentialError(
                    f"Google credentials file not found: {credentials_path}"
                )
            
            try:
                # Validate JSON structure
                with open(credentials_path, 'r') as f:
                    cred_data = json.load(f)
                
                # Check for required fields
                required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in cred_data]
                if missing_fields:
                    raise CredentialError(
                        f"Google credentials missing required fields: {', '.join(missing_fields)}"
                    )
                
                # Create credentials with proper scopes
                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
                
                self._google_credentials = Credentials.from_service_account_file(
                    credentials_path, scopes=scopes
                )
                
                logger.info("Google credentials loaded successfully")
                
            except json.JSONDecodeError as e:
                raise CredentialError(f"Invalid Google credentials JSON: {e}")
            except Exception as e:
                raise CredentialError(f"Failed to load Google credentials: {e}")
        
        return self._google_credentials
    
    def validate_openai_credentials(self) -> bool:
        """Validate OpenAI API credentials."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise CredentialError("OpenAI API key not found in environment variables")
        
        if not api_key.startswith("sk-"):
            raise CredentialError("Invalid OpenAI API key format")
        
        # Basic length validation (OpenAI keys are typically 51 characters)
        if len(api_key) < 40:
            raise CredentialError("OpenAI API key appears to be incomplete")
        
        return True
    
    def validate_telegram_credentials(self) -> bool:
        """Validate Telegram webhook credentials."""
        webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not webhook_url:
            raise CredentialError("Telegram webhook URL not found")
        
        if not chat_id:
            raise CredentialError("Telegram chat ID not found")
        
        if not webhook_url.startswith(("http://", "https://")):
            raise CredentialError("Invalid Telegram webhook URL format")
        
        try:
            int(chat_id)
        except ValueError:
            raise CredentialError("Telegram chat ID must be a valid integer")
        
        return True
    
    def get_safe_config_dict(self) -> Dict[str, Any]:
        """Get configuration dictionary with sensitive values masked."""
        safe_config = {
            "environment": settings.app.environment,
            "debug": settings.app.debug,
            "openai_api_key": "***masked***" if os.getenv("OPENAI_API_KEY") else None,
            "telegram_configured": bool(os.getenv("TELEGRAM_WEBHOOK_URL")),
            "google_credentials_exists": os.path.exists(settings.database.google_credentials_path),
            "base_path": str(settings.paths.base_path),
        }
        return safe_config
    
    def validate_all_credentials(self) -> bool:
        """Validate all application credentials."""
        try:
            self.validate_required_env_vars()
            self.validate_openai_credentials()
            self.validate_telegram_credentials()
            self.get_google_credentials()  # This validates Google credentials
            
            logger.info("All credentials validated successfully")
            return True
            
        except CredentialError as e:
            logger.error(f"Credential validation failed: {e}")
            raise


class SecureFileManager:
    """Manages secure file operations and path validation."""
    
    @staticmethod
    def validate_file_path(file_path: str) -> Path:
        """Validate and sanitize file paths to prevent path traversal attacks."""
        try:
            # Convert to Path object and resolve
            path = Path(file_path).resolve()
            
            # Check if path is within allowed directories
            base_path = settings.paths.base_dir.resolve()
            project_path = Path(__file__).parent.parent.resolve()
            
            allowed_parents = [base_path, project_path]
            
            if not any(str(path).startswith(str(parent)) for parent in allowed_parents):
                raise ValueError(f"Path access denied: {path}")
            
            return path
            
        except Exception as e:
            raise ValueError(f"Invalid file path: {file_path} - {e}")
    
    @staticmethod
    def safe_file_read(file_path: str, max_size: int = 10 * 1024 * 1024) -> str:
        """Safely read file with size and path validation."""
        validated_path = SecureFileManager.validate_file_path(file_path)
        
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {validated_path}")
        
        if validated_path.stat().st_size > max_size:
            raise ValueError(f"File too large: {validated_path} ({validated_path.stat().st_size} bytes)")
        
        try:
            with open(validated_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try reading as binary for non-text files
            with open(validated_path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
    
    @staticmethod
    def safe_file_write(file_path: str, content: str, create_dirs: bool = True) -> None:
        """Safely write file with path validation."""
        validated_path = SecureFileManager.validate_file_path(file_path)
        
        if create_dirs:
            validated_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(validated_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def safe_remove_files(pattern: str, base_dir: str) -> int:
        """Safely remove files matching pattern within validated base directory."""
        base_path = SecureFileManager.validate_file_path(base_dir)
        
        if not base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {base_path}")
        
        removed_count = 0
        for file_path in base_path.glob(pattern):
            if file_path.is_file():
                file_path.unlink()
                removed_count += 1
        
        return removed_count


# Global credential manager instance
credential_manager = SecureCredentialManager()


def get_google_credentials() -> Credentials:
    """Get validated Google credentials."""
    return credential_manager.get_google_credentials()


def validate_startup_credentials() -> None:
    """Validate all credentials at application startup."""
    credential_manager.validate_all_credentials()