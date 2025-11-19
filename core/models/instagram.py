"""Instagram-related data models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID

from .content import ContentItem, ImageData, CaptionData, LocationData


class PostMetadata(BaseModel):
    """Metadata for Instagram posts."""
    
    alt_text: Optional[str] = Field(None, description="Alt text for accessibility")
    location_tag: Optional[str] = Field(None, description="Location tag")
    collaboration_users: List[str] = Field(default_factory=list, description="Collaboration users")
    branded_content_tags: List[str] = Field(default_factory=list, description="Branded content tags")
    
    @validator('alt_text')
    def validate_alt_text(cls, v):
        """Validate alt text length."""
        if v and len(v) > 100:
            raise ValueError("Alt text must be 100 characters or less")
        return v


class InstagramPost(BaseModel):
    """Instagram post data model."""
    
    content_items: List[ContentItem] = Field(..., description="List of content items for the post")
    caption: CaptionData = Field(..., description="Post caption")
    images: List[ImageData] = Field(..., description="Post images")
    location: LocationData = Field(..., description="Post location")
    metadata: PostMetadata = Field(default_factory=PostMetadata, description="Post metadata")
    
    # Posting configuration
    max_images: int = Field(default=6, ge=1, le=10, description="Maximum images per post")
    
    @validator('content_items')
    def validate_content_items(cls, v):
        """Validate content items."""
        if not v:
            raise ValueError("At least one content item is required")
        
        # Check that all items have the same group_id
        group_ids = {item.group_id for item in v}
        if len(group_ids) > 1:
            raise ValueError("All content items must have the same group_id")
        
        return v
    
    @validator('images')
    def validate_images(cls, v, values):
        """Validate images."""
        if not v:
            raise ValueError("At least one image is required")
        
        max_images = values.get('max_images', 6)
        if len(v) > max_images:
            raise ValueError(f"Too many images (max: {max_images})")
        
        # Validate that all images have URLs
        for image in v:
            if not image.url:
                raise ValueError("All images must have URLs")
        
        return v
    
    @property
    def group_id(self) -> UUID:
        """Get the group ID for this post."""
        return self.content_items[0].group_id
    
    @property
    def image_urls(self) -> List[str]:
        """Get list of image URLs."""
        return [img.url for img in self.images if img.url]
    
    @property
    def formatted_caption(self) -> str:
        """Get formatted caption for Instagram."""
        return self.caption.formatted_caption
    
    @property
    def alt_text(self) -> str:
        """Get alt text for the post."""
        if self.metadata.alt_text:
            return self.metadata.alt_text
        return f"Aashvi at {self.location.name}"


class InstagramStory(BaseModel):
    """Instagram story data model."""
    
    content_item: ContentItem = Field(..., description="Content item for the story")
    image: ImageData = Field(..., description="Story image")
    caption: Optional[CaptionData] = Field(None, description="Story caption (optional)")
    
    # Story-specific settings
    duration: int = Field(default=24, ge=1, le=24, description="Story duration in hours")
    highlight_name: Optional[str] = Field(None, description="Highlight collection name")
    
    @validator('image')
    def validate_story_image(cls, v):
        """Validate story image."""
        if not v.url:
            raise ValueError("Story image must have a URL")
        return v
    
    @property
    def image_url(self) -> str:
        """Get story image URL."""
        return self.image.url
    
    @property
    def formatted_caption(self) -> str:
        """Get formatted caption for story."""
        if self.caption:
            return self.caption.text  # Stories use simpler captions
        return ""


class PostingResult(BaseModel):
    """Result of Instagram posting operation."""
    
    success: bool = Field(..., description="Whether posting was successful")
    post_id: Optional[str] = Field(None, description="Instagram post ID")
    error_message: Optional[str] = Field(None, description="Error message if posting failed")
    posted_at: Optional[datetime] = Field(None, description="Timestamp when posted")
    
    # Metrics
    processing_time: Optional[float] = Field(None, ge=0, description="Time taken to process")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    
    @classmethod
    def success_result(
        cls,
        post_id: Optional[str] = None,
        processing_time: Optional[float] = None
    ) -> "PostingResult":
        """Create a successful posting result."""
        return cls(
            success=True,
            post_id=post_id,
            posted_at=datetime.utcnow(),
            processing_time=processing_time
        )
    
    @classmethod
    def failure_result(
        cls,
        error_message: str,
        retry_count: int = 0,
        processing_time: Optional[float] = None
    ) -> "PostingResult":
        """Create a failed posting result."""
        return cls(
            success=False,
            error_message=error_message,
            retry_count=retry_count,
            processing_time=processing_time
        )


class InstagramMetrics(BaseModel):
    """Instagram account metrics and statistics."""
    
    # Content metrics
    total_posts: int = Field(default=0, ge=0, description="Total number of posts")
    total_stories: int = Field(default=0, ge=0, description="Total number of stories")
    pending_approvals: int = Field(default=0, ge=0, description="Pending approvals")
    
    # Posting frequency
    posts_today: int = Field(default=0, ge=0, description="Posts published today")
    stories_today: int = Field(default=0, ge=0, description="Stories published today")
    
    # Error tracking
    recent_errors: int = Field(default=0, ge=0, description="Recent posting errors")
    last_successful_post: Optional[datetime] = Field(None, description="Last successful post timestamp")
    
    @property
    def posting_health(self) -> str:
        """Get posting health status."""
        if self.recent_errors > 5:
            return "unhealthy"
        elif self.recent_errors > 2:
            return "warning"
        else:
            return "healthy"
    
    @property
    def needs_content(self) -> bool:
        """Check if new content is needed."""
        return self.pending_approvals < 3