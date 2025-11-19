"""Content-related data models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4

from config.constants import ContentType, ApprovalStatus, PostingStatus


class LocationData(BaseModel):
    """Location information for content generation."""
    
    name: str = Field(..., description="Location name")
    country: Optional[str] = Field(None, description="Country name")
    description: Optional[str] = Field(None, description="Location description")
    
    @property
    def full_name(self) -> str:
        """Get full location name with country."""
        if self.country and self.country not in self.name:
            return f"{self.name}, {self.country}"
        return self.name


class PromptData(BaseModel):
    """AI prompt data for content generation."""
    
    text: str = Field(..., description="The prompt text")
    location: LocationData = Field(..., description="Location for the prompt")
    content_type: ContentType = Field(..., description="Type of content")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt for AI generation")
    
    @validator('text')
    def validate_prompt_text(cls, v):
        """Validate prompt text."""
        if len(v.strip()) < 10:
            raise ValueError("Prompt text must be at least 10 characters")
        return v.strip()


class CaptionData(BaseModel):
    """Caption data for social media posts."""
    
    text: str = Field(..., description="Caption text")
    hashtags: List[str] = Field(default_factory=list, description="List of hashtags")
    mentions: List[str] = Field(default_factory=list, description="List of mentions")
    
    @validator('text')
    def validate_caption_text(cls, v):
        """Validate caption text."""
        if len(v.strip()) < 1:
            raise ValueError("Caption text cannot be empty")
        return v.strip()
    
    @validator('hashtags')
    def validate_hashtags(cls, v):
        """Validate hashtags format."""
        validated = []
        for tag in v:
            if not tag.startswith('#'):
                tag = f"#{tag}"
            validated.append(tag.lower())
        return validated
    
    @validator('mentions')
    def validate_mentions(cls, v):
        """Validate mentions format."""
        validated = []
        for mention in v:
            if not mention.startswith('@'):
                mention = f"@{mention}"
            validated.append(mention.lower())
        return validated
    
    @property
    def formatted_caption(self) -> str:
        """Get formatted caption with hashtags and mentions."""
        parts = [self.text]
        
        if self.hashtags:
            parts.append(" ".join(self.hashtags))
        
        if self.mentions:
            parts.append(" ".join(self.mentions))
        
        return "\n\n".join(parts)


class ImageData(BaseModel):
    """Image data and metadata."""
    
    url: Optional[str] = Field(None, description="Image URL")
    file_path: Optional[str] = Field(None, description="Local file path")
    drive_id: Optional[str] = Field(None, description="Google Drive file ID")
    width: Optional[int] = Field(None, ge=1, description="Image width")
    height: Optional[int] = Field(None, ge=1, description="Image height")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    format: Optional[str] = Field(None, description="Image format (PNG, JPEG, etc.)")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate image URL."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Image URL must start with http:// or https://")
        return v


class ContentRequest(BaseModel):
    """Request for content generation."""
    
    content_type: ContentType = Field(..., description="Type of content to generate")
    location: LocationData = Field(..., description="Location for content")
    count: int = Field(default=1, ge=1, le=10, description="Number of content items to generate")
    style: Optional[str] = Field(None, description="Content style or theme")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    
    class Config:
        use_enum_values = True


class ContentItem(BaseModel):
    """Individual content item with all associated data."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique content ID")
    index: int = Field(..., ge=0, description="Content index in sheet")
    content_type: ContentType = Field(..., description="Type of content")
    group_id: UUID = Field(..., description="Group ID for related content")
    
    # Content data
    prompt: Optional[PromptData] = Field(None, description="AI prompt data")
    caption: Optional[CaptionData] = Field(None, description="Caption data")
    image: Optional[ImageData] = Field(None, description="Image data")
    location: LocationData = Field(..., description="Content location")
    
    # Status tracking
    approval_status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Approval status"
    )
    posting_status: PostingStatus = Field(
        default=PostingStatus.NOT_POSTED,
        description="Posting status"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    posted_at: Optional[datetime] = Field(None, description="Posting timestamp")
    
    # Processing metadata
    seed: Optional[int] = Field(None, description="AI generation seed")
    processing_time: Optional[float] = Field(None, ge=0, description="Processing time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        use_enum_values = True
    
    @property
    def is_approved(self) -> bool:
        """Check if content is approved."""
        return self.approval_status == ApprovalStatus.APPROVED
    
    @property
    def is_posted(self) -> bool:
        """Check if content is posted."""
        return self.posting_status == PostingStatus.POSTED
    
    @property
    def is_ready_for_posting(self) -> bool:
        """Check if content is ready for posting."""
        return (
            self.is_approved and
            not self.is_posted and
            self.image is not None and
            self.caption is not None
        )
    
    def to_sheet_row(self) -> List[Any]:
        """Convert content item to Google Sheets row format."""
        return [
            self.index,
            self.content_type.value,
            self.prompt.text if self.prompt else "",
            self.location.full_name,
            str(self.group_id),
            self.seed if self.seed is not None else "",
            f'=IMAGE("{self.image.url}", 4, 120, 120)' if self.image and self.image.url else "",
            self.generated_at.strftime("%d/%m/%Y %H:%M:%S") if self.generated_at else "",
            self.caption.formatted_caption if self.caption else "",
            self.approval_status.value,
            self.posted_at.strftime("%Y-%m-%d %H:%M") if self.posted_at else "",
            f'=HYPERLINK("{self.image.url}", "Link")' if self.image and self.image.url else ""
        ]
    
    @classmethod
    def from_sheet_row(cls, row: Dict[str, Any], index: int) -> "ContentItem":
        """Create content item from Google Sheets row."""
        # Parse image URL from IMAGE formula
        image_url = None
        image_formula = row.get('image', '')
        if image_formula and 'IMAGE(' in image_formula:
            start = image_formula.find('"') + 1
            end = image_formula.find('"', start)
            if start > 0 and end > start:
                image_url = image_formula[start:end]
        
        # Parse location
        location_str = row.get('location', '')
        location_parts = location_str.split(', ', 1)
        location = LocationData(
            name=location_parts[0] if location_parts else location_str,
            country=location_parts[1] if len(location_parts) > 1 else None
        )
        
        # Parse timestamps
        generated_at = None
        if row.get('generated_on'):
            try:
                generated_at = datetime.strptime(row['generated_on'], "%d/%m/%Y %H:%M:%S")
            except (ValueError, TypeError):
                pass
        
        posted_at = None
        if row.get('posted_on_instagram'):
            try:
                posted_at = datetime.strptime(row['posted_on_instagram'], "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass
        
        return cls(
            index=index,
            content_type=ContentType(row.get('type', 'posts')),
            group_id=UUID(row.get('group_id', str(uuid4()))),
            prompt=PromptData(
                text=row.get('prompt', ''),
                location=location,
                content_type=ContentType(row.get('type', 'posts'))
            ) if row.get('prompt') else None,
            caption=CaptionData(text=row.get('caption', '')) if row.get('caption') else None,
            image=ImageData(url=image_url) if image_url else None,
            location=location,
            approval_status=ApprovalStatus(row.get('approved', '')),
            posting_status=PostingStatus.POSTED if row.get('posted_on_instagram') else PostingStatus.NOT_POSTED,
            generated_at=generated_at,
            posted_at=posted_at,
            seed=int(row.get('seed', -1)) if row.get('seed') and str(row.get('seed')).isdigit() else None
        )