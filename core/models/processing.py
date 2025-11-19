"""Image processing related data models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from config.constants import ContentType


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageProcessingRequest(BaseModel):
    """Request for image processing operations."""
    
    source_image_path: str = Field(..., description="Path to source image")
    mask_image_path: Optional[str] = Field(None, description="Path to mask image")
    output_path: str = Field(..., description="Output path for processed image")
    
    # Processing configuration
    processing_type: str = Field(..., description="Type of processing (face_fix, skin_processing)")
    prompt: str = Field(..., description="AI prompt for processing")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    
    # AI parameters
    denoising_strength: float = Field(default=0.8, ge=0.0, le=1.0, description="Denoising strength")
    cfg_scale: float = Field(default=7.0, ge=1.0, le=30.0, description="CFG scale")
    steps: int = Field(default=50, ge=1, le=150, description="Number of steps")
    mask_blur: int = Field(default=4, ge=0, le=64, description="Mask blur radius")
    
    # ControlNet settings
    controlnet_model: Optional[str] = Field(None, description="ControlNet model to use")
    controlnet_module: Optional[str] = Field(None, description="ControlNet module")
    
    @validator('processing_type')
    def validate_processing_type(cls, v):
        """Validate processing type."""
        allowed_types = ['face_fix', 'skin_processing', 'img2img', 'txt2img']
        if v not in allowed_types:
            raise ValueError(f"Invalid processing type: {v}. Allowed: {allowed_types}")
        return v


class ImageProcessingResult(BaseModel):
    """Result of image processing operation."""
    
    success: bool = Field(..., description="Whether processing was successful")
    output_path: Optional[str] = Field(None, description="Path to output image")
    output_url: Optional[str] = Field(None, description="URL to output image")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    
    # Processing metrics
    processing_time: Optional[float] = Field(None, ge=0, description="Processing time in seconds")
    memory_used: Optional[int] = Field(None, ge=0, description="Memory used in bytes")
    gpu_time: Optional[float] = Field(None, ge=0, description="GPU processing time")
    
    # Metadata
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    model_used: Optional[str] = Field(None, description="AI model used")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    
    @classmethod
    def success_result(
        cls,
        output_path: str,
        output_url: Optional[str] = None,
        processing_time: Optional[float] = None,
        **kwargs
    ) -> "ImageProcessingResult":
        """Create a successful processing result."""
        return cls(
            success=True,
            output_path=output_path,
            output_url=output_url,
            processing_time=processing_time,
            **kwargs
        )
    
    @classmethod
    def failure_result(
        cls,
        error_message: str,
        processing_time: Optional[float] = None,
        **kwargs
    ) -> "ImageProcessingResult":
        """Create a failed processing result."""
        return cls(
            success=False,
            error_message=error_message,
            processing_time=processing_time,
            **kwargs
        )


class FaceProcessingConfig(BaseModel):
    """Configuration for face processing operations."""
    
    # Detection settings
    face_confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    max_faces: int = Field(default=1, ge=1, le=10)
    
    # Processing settings
    denoising_strength: float = Field(default=0.8, ge=0.0, le=1.0)
    mask_blur: int = Field(default=18, ge=0, le=64)
    steps: int = Field(default=140, ge=1, le=150)
    cfg_scale: float = Field(default=3.0, ge=1.0, le=30.0)
    
    # Quality settings
    restore_faces: bool = Field(default=True)
    enhance_details: bool = Field(default=True)
    
    @classmethod
    def for_excel_images(cls) -> "FaceProcessingConfig":
        """Get configuration optimized for Excel-generated images."""
        return cls(
            denoising_strength=0.8,
            mask_blur=18,
            steps=140,
            cfg_scale=3.0
        )
    
    @classmethod
    def for_regular_images(cls) -> "FaceProcessingConfig":
        """Get configuration optimized for regular images."""
        return cls(
            denoising_strength=0.85,
            mask_blur=15,
            steps=180,
            cfg_scale=3.0
        )


class SkinProcessingConfig(BaseModel):
    """Configuration for skin processing operations."""
    
    # Processing settings
    denoising_strength: float = Field(default=0.4, ge=0.0, le=1.0)
    mask_blur: int = Field(default=18, ge=0, le=64)
    steps: int = Field(default=150, ge=1, le=150)
    cfg_scale: float = Field(default=12.0, ge=1.0, le=30.0)
    
    # Skin enhancement settings
    skin_smoothing: float = Field(default=0.3, ge=0.0, le=1.0)
    color_correction: bool = Field(default=True)
    preserve_details: bool = Field(default=True)
    
    # Quality settings
    restore_faces: bool = Field(default=False)  # Usually disabled for skin processing
    enhance_skin_texture: bool = Field(default=True)


class StableDiffusionConfig(BaseModel):
    """Configuration for Stable Diffusion API requests."""
    
    # Model settings
    model: Optional[str] = Field(None, description="Model checkpoint to use")
    sampler_name: str = Field(default="DPM++ 2M", description="Sampling method")
    
    # Generation parameters
    prompt: str = Field(..., description="Positive prompt")
    negative_prompt: str = Field(default="", description="Negative prompt")
    steps: int = Field(default=50, ge=1, le=150, description="Number of sampling steps")
    cfg_scale: float = Field(default=7.0, ge=1.0, le=30.0, description="CFG scale")
    denoising_strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Denoising strength for img2img")
    
    # Image settings
    width: int = Field(default=512, ge=64, le=2048, description="Image width")
    height: int = Field(default=512, ge=64, le=2048, description="Image height")
    batch_size: int = Field(default=1, ge=1, le=10, description="Batch size")
    n_iter: int = Field(default=1, ge=1, le=10, description="Number of iterations")
    
    # Quality settings
    restore_faces: bool = Field(default=True, description="Restore faces")
    seed: int = Field(default=-1, description="Random seed (-1 for random)")
    
    # Advanced settings
    mask_blur: Optional[int] = Field(None, ge=0, le=64, description="Mask blur for inpainting")
    enable_hr: bool = Field(default=False, description="Enable high-res fix")
    hr_scale: Optional[float] = Field(None, ge=1.0, le=4.0, description="High-res scale factor")
    hr_upscaler: Optional[str] = Field(None, description="High-res upscaler")
    
    # ControlNet settings
    controlnet_args: Optional[Dict[str, Any]] = Field(None, description="ControlNet arguments")
    
    @classmethod
    def for_content_type(cls, content_type: ContentType, prompt: str, negative_prompt: str = "") -> "StableDiffusionConfig":
        """Create configuration for specific content type."""
        from config.constants import STABLE_DIFFUSION_MODELS
        
        model_config = STABLE_DIFFUSION_MODELS.get(content_type, STABLE_DIFFUSION_MODELS[ContentType.POST])
        
        return cls(
            prompt=prompt,
            negative_prompt=negative_prompt,
            **model_config
        )
    
    def to_api_payload(self, include_controlnet: bool = False) -> Dict[str, Any]:
        """Convert configuration to API payload."""
        payload = {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "steps": self.steps,
            "sampler_name": self.sampler_name,
            "cfg_scale": self.cfg_scale,
            "width": self.width,
            "height": self.height,
            "batch_size": self.batch_size,
            "n_iter": self.n_iter,
            "restore_faces": self.restore_faces,
            "seed": self.seed,
            "send_images": True,
            "save_images": False
        }
        
        # Add optional parameters
        if self.denoising_strength is not None:
            payload["denoising_strength"] = self.denoising_strength
        
        if self.mask_blur is not None:
            payload["mask_blur"] = self.mask_blur
        
        if self.enable_hr:
            payload["enable_hr"] = True
            if self.hr_scale:
                payload["hr_scale"] = self.hr_scale
            if self.hr_upscaler:
                payload["hr_upscaler"] = self.hr_upscaler
        
        if include_controlnet and self.controlnet_args:
            payload["alwayson_scripts"] = {
                "controlnet": {
                    "args": [self.controlnet_args]
                }
            }
        
        return payload