"""Application settings and configuration management.

This module provides a centralized, type-safe configuration system using Pydantic.
All environment variables and configuration values should be defined here.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseSettings, validator, Field
import os


class DatabaseConfig(BaseSettings):
    """Google Sheets and Drive configuration."""
    
    gspread_key: str = Field(..., env="GSPREED_KEY")
    google_credentials_path: str = Field(..., env="GOOGLE_CREDENTIALS_PATH")
    drive_folder_ids: dict = Field(
        default_factory=lambda: {
            "images": "1rEysVX6M0vEZFYGbdDVc96G4ZBXYhDDs",
            "raw_images": "1JZNYd_Q30ouTDx76YX4DmEiSb6KI9UFh",
            "masks": "1aEJg4sPOyUS63OiaBIjHPeeLnXaJizu2",
            "skin_masks": "1VCaEG3Rs6ZujBFwi1oMn7rbQlR9LlH5I",
            "processed": "1xiEh0AGKjtPhztcqwY27IUC_t0xMzph_",
            "final": "1rEysVX6M0vEZFYGbdDVc96G4ZBXYhDDs",
            "archived_raw": "10PtowEawQ-81V4lSkM4K3-r-xQ-T7dW7",
            "archived_masks": "1wVXqsunwblNZDBEMz63_alrdgPWbtA5k",
            "archived_skin_masks": "1JZWascB8Pgv1klKWh3lFOY4-46o3xsX6"
        }
    )

    @validator('google_credentials_path')
    def validate_credentials_path(cls, v):
        """Ensure Google credentials file exists."""
        if not os.path.exists(v):
            raise ValueError(f"Google credentials file not found: {v}")
        return v


class AIConfig(BaseSettings):
    """AI service configuration."""
    
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(None, env="OPENAI_ORGANIZATION")
    
    # Model settings
    gpt_model: str = Field(default="gpt-3.5-turbo")
    gpt_temperature: float = Field(default=0.9, ge=0.0, le=2.0)
    gpt_max_tokens: int = Field(default=400, gt=0)
    
    # Stable Diffusion settings
    automatic1111_url_file: str = Field(
        default="automatic1111_url.txt",
        env="AUTOMATIC1111_URL_FILE"
    )
    sd_default_steps: int = Field(default=120, ge=1, le=150)
    sd_default_cfg_scale: float = Field(default=3.5, ge=1.0, le=30.0)
    sd_default_width: int = Field(default=512, ge=256, le=2048)
    sd_default_height: int = Field(default=512, ge=256, le=2048)


class InstagramConfig(BaseSettings):
    """Instagram automation configuration."""
    
    username: str = Field(..., env="INSTAGRAM_USERNAME")
    profile_name: str = Field(default="aashvithemodel")
    
    # Content settings
    default_hashtags: List[str] = Field(
        default=[
            "#digitalmodel", "#fashionista", "#fashiongram", "#styleblogger",
            "#fashionblogger", "#fashionmodel", "#modelling", "#modelswanted",
            "#modelsearch", "#modelphotography", "#modelpose", "#modelstatus",
            "#modelsofinstagram", "#modelife", "#digitalinfluencer",
            "#VirtualModel", "#DigitalFashion"
        ]
    )
    max_hashtags: int = Field(default=30, ge=1, le=30)
    default_mentions: List[str] = Field(
        default=["@thevarunmayya", "@acknowledge.ai", "@eluna.ai"]
    )
    
    # Posting limits
    max_images_per_post: int = Field(default=6, ge=1, le=10)
    max_story_posts_per_batch: int = Field(default=4, ge=1, le=10)


class NotificationConfig(BaseSettings):
    """Notification service configuration."""
    
    telegram_webhook_url: str = Field(..., env="TELEGRAM_WEBHOOK_URL")
    telegram_chat_id: str = Field(..., env="TELEGRAM_CHAT_ID")
    
    # Notification settings
    enable_error_notifications: bool = Field(default=True)
    enable_success_notifications: bool = Field(default=True)
    notification_retry_attempts: int = Field(default=3, ge=1, le=10)


class PathConfig(BaseSettings):
    """File system path configuration."""
    
    base_path: str = Field(
        default="/Users/rikenshah/Desktop/Fun/insta-model",
        env="AASHVI_BASE_PATH"
    )
    
    @property
    def base_dir(self) -> Path:
        """Get base directory as Path object."""
        return Path(self.base_path)
    
    @property
    def raw_images_dir(self) -> Path:
        """Directory for raw input images."""
        return self.base_dir / "raw"
    
    @property
    def masks_dir(self) -> Path:
        """Directory for face masks."""
        return self.base_dir / "mask"
    
    @property
    def skin_masks_dir(self) -> Path:
        """Directory for skin masks."""
        return self.base_dir / "skin_masks"
    
    @property
    def final_images_dir(self) -> Path:
        """Directory for final processed images."""
        return self.base_dir / "final"
    
    @property
    def processed_images_dir(self) -> Path:
        """Directory for processed images."""
        return self.base_dir / "processed"
    
    @property
    def temp_dir(self) -> Path:
        """Directory for temporary files."""
        return self.base_dir / "temp"
    
    @property
    def chrome_profile_dir(self) -> Path:
        """Chrome profile directory for Selenium."""
        return self.base_dir / "profile-2"
    
    @property
    def location_file(self) -> Path:
        """File containing current location."""
        return self.base_dir / "location.txt"
    
    @property
    def running_lock_file(self) -> Path:
        """Lock file to prevent concurrent runs."""
        return self.base_dir / "is_running.txt"
    
    def ensure_directories(self) -> None:
        """Create all necessary directories if they don't exist."""
        directories = [
            self.raw_images_dir,
            self.masks_dir,
            self.skin_masks_dir,
            self.final_images_dir,
            self.processed_images_dir,
            self.temp_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Timing settings
    automation_interval_minutes: int = Field(default=30, ge=1, le=1440)
    story_interval_minutes: int = Field(default=180, ge=1, le=1440)
    posting_interval_minutes: int = Field(default=720, ge=1, le=1440)
    approval_check_interval_minutes: int = Field(default=30, ge=1, le=1440)
    
    # Content generation limits
    max_non_posted_instagram_posts: int = Field(default=5, ge=1, le=50)
    max_non_posted_stories: int = Field(default=5, ge=1, le=50)
    
    # Retry settings
    max_retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay_seconds: int = Field(default=5, ge=1, le=300)
    
    # Selenium settings
    selenium_timeout_seconds: int = Field(default=30, ge=5, le=120)
    page_load_timeout_seconds: int = Field(default=60, ge=10, le=300)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class Settings:
    """Central settings container."""
    
    def __init__(self):
        """Initialize all configuration sections."""
        self.app = AppConfig()
        self.database = DatabaseConfig()
        self.ai = AIConfig()
        self.instagram = InstagramConfig()
        self.notifications = NotificationConfig()
        self.paths = PathConfig()
        
        # Ensure directories exist
        self.paths.ensure_directories()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment.lower() == "development"


# Global settings instance
settings = Settings()