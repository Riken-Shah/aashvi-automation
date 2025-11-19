"""Workflow and business logic exceptions."""

from typing import Optional, Dict, Any
from .base import AashviError, RetryableError, NonRetryableError


class WorkflowError(AashviError):
    """Base exception for workflow-related errors."""
    
    def __init__(
        self,
        message: str,
        workflow_step: Optional[str] = None,
        **kwargs
    ):
        """Initialize workflow error.
        
        Args:
            message: Human-readable error message
            workflow_step: Name of the workflow step that failed
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.workflow_step = workflow_step
        if workflow_step:
            self.context['workflow_step'] = workflow_step


class ContentGenerationError(WorkflowError):
    """Exception raised during content generation."""
    
    def __init__(self, message: str, content_type: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="CONTENT_GENERATION_ERROR",
            workflow_step="content_generation",
            **kwargs
        )
        self.content_type = content_type
        if content_type:
            self.context['content_type'] = content_type


class PromptGenerationError(ContentGenerationError):
    """Exception raised during prompt generation."""
    
    def __init__(self, message: str, location: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="PROMPT_GENERATION_ERROR",
            **kwargs
        )
        self.location = location
        if location:
            self.context['location'] = location


class CaptionGenerationError(ContentGenerationError):
    """Exception raised during caption generation."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_code="CAPTION_GENERATION_ERROR",
            **kwargs
        )


class ImageProcessingError(WorkflowError):
    """Exception raised during image processing."""
    
    def __init__(
        self,
        message: str,
        processing_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="IMAGE_PROCESSING_ERROR",
            workflow_step="image_processing",
            **kwargs
        )
        self.processing_type = processing_type
        if processing_type:
            self.context['processing_type'] = processing_type


class ImageGenerationError(ImageProcessingError):
    """Exception raised during AI image generation."""
    
    def __init__(self, message: str, prompt: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            processing_type="generation",
            error_code="IMAGE_GENERATION_ERROR",
            **kwargs
        )
        self.prompt = prompt
        if prompt:
            # Store truncated prompt for logging
            self.context['prompt'] = prompt[:200] + "..." if len(prompt) > 200 else prompt


class FaceProcessingError(ImageProcessingError):
    """Exception raised during face processing."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            processing_type="face_processing",
            error_code="FACE_PROCESSING_ERROR",
            **kwargs
        )


class PostingError(WorkflowError):
    """Exception raised during content posting."""
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="POSTING_ERROR",
            workflow_step="posting",
            **kwargs
        )
        self.platform = platform
        if platform:
            self.context['platform'] = platform


class InstagramPostingError(PostingError):
    """Exception raised during Instagram posting."""
    
    def __init__(self, message: str, post_type: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            platform="instagram",
            error_code="INSTAGRAM_POSTING_ERROR",
            **kwargs
        )
        self.post_type = post_type
        if post_type:
            self.context['post_type'] = post_type


class SeleniumError(PostingError, RetryableError):
    """Exception raised for Selenium automation errors."""
    
    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message,
            platform="web",
            error_code="SELENIUM_ERROR",
            retry_after_seconds=60,
            **kwargs
        )
        self.selector = selector
        if selector:
            self.context['selector'] = selector


class ValidationError(WorkflowError, NonRetryableError):
    """Exception raised for data validation errors."""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            **kwargs
        )
        self.field_name = field_name
        self.field_value = field_value
        
        if field_name:
            self.context['field_name'] = field_name
        if field_value is not None:
            # Convert to string and truncate if too long
            str_value = str(field_value)
            self.context['field_value'] = str_value[:100] + "..." if len(str_value) > 100 else str_value


class ContentValidationError(ValidationError):
    """Exception raised for content validation errors."""
    
    def __init__(self, message: str, content_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            error_code="CONTENT_VALIDATION_ERROR",
            **kwargs
        )
        self.content_id = content_id
        if content_id:
            self.context['content_id'] = content_id


class ApprovalError(WorkflowError, NonRetryableError):
    """Exception raised for content approval errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_code="APPROVAL_ERROR",
            workflow_step="approval",
            **kwargs
        )


class ContentNotApprovedError(ApprovalError):
    """Exception raised when content is not approved for posting."""
    
    def __init__(self, content_id: Optional[str] = None, **kwargs):
        message = "Content not approved for posting"
        if content_id:
            message += f": {content_id}"
        
        super().__init__(
            message,
            error_code="CONTENT_NOT_APPROVED",
            **kwargs
        )
        self.content_id = content_id
        if content_id:
            self.context['content_id'] = content_id