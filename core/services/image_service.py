"""Image processing and generation service."""

import base64
from pathlib import Path
from typing import Optional, List
import time

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from config.constants import STABLE_DIFFUSION_MODELS, NEGATIVE_PROMPTS, STANDARD_PROMPTS
from core.models.content import ContentItem, ImageData
from core.models.processing import (
    ImageProcessingRequest,
    ImageProcessingResult,
    StableDiffusionConfig,
    FaceProcessingConfig,
    SkinProcessingConfig
)
from core.exceptions import ImageProcessingError, ImageGenerationError, FaceProcessingError
from infrastructure.apis.stable_diffusion_client import StableDiffusionClient
from infrastructure.storage.drive_storage import DriveStorageService

logger = get_logger(__name__)


class ImageProcessingService:
    """Service for AI image generation and processing."""
    
    def __init__(
        self,
        stable_diffusion_client: StableDiffusionClient,
        storage_service: DriveStorageService
    ):
        """Initialize image processing service.
        
        Args:
            stable_diffusion_client: Stable Diffusion API client
            storage_service: Storage service for file operations
        """
        self.sd_client = stable_diffusion_client
        self.storage_service = storage_service
    
    async def generate_image_for_content(self, content_item: ContentItem) -> ImageData:
        """Generate image for content item.
        
        Args:
            content_item: Content item with prompt data
            
        Returns:
            Generated image data
            
        Raises:
            ImageGenerationError: If image generation fails
        """
        with PerformanceLogger(logger, f"generate_image({content_item.content_type})"):
            try:
                if not content_item.prompt:
                    raise ImageGenerationError("Content item missing prompt data")
                
                # Create Stable Diffusion configuration
                config = StableDiffusionConfig.for_content_type(
                    content_type=content_item.content_type,
                    prompt=content_item.prompt.text,
                    negative_prompt=NEGATIVE_PROMPTS["default"]
                )
                
                if content_item.seed:
                    config.seed = content_item.seed
                
                # Generate image
                result = await self.sd_client.text_to_image(config)
                
                if not result.success:
                    raise ImageGenerationError(
                        f"Stable Diffusion generation failed: {result.error_message}",
                        prompt=content_item.prompt.text
                    )
                
                # Save and upload image
                filename = f"{content_item.index}-aashvi.png"
                image_url = await self._save_and_upload_image(
                    base64_data=result.output_data,
                    filename=filename,
                    folder_id=settings.database.drive_folder_ids["images"]
                )
                
                image_data = ImageData(
                    url=image_url,
                    file_path=str(settings.paths.temp_dir / filename),
                    width=config.width,
                    height=config.height,
                    format="PNG"
                )
                
                logger.info(
                    f"Generated image for content {content_item.index}",
                    extra={
                        'content_id': str(content_item.id),
                        'content_type': content_item.content_type,
                        'image_url': image_url,
                        'processing_time': result.processing_time
                    }
                )
                
                return image_data
                
            except Exception as e:
                logger.error(
                    f"Image generation failed for content {content_item.index}: {e}",
                    extra={'content_id': str(content_item.id)},
                    exc_info=True
                )
                raise ImageGenerationError(
                    f"Failed to generate image: {e}",
                    prompt=content_item.prompt.text if content_item.prompt else None
                )
    
    async def process_face_images(self, batch_size: int = 5) -> List[ImageProcessingResult]:
        """Process face images from raw folder.
        
        Args:
            batch_size: Number of images to process in batch
            
        Returns:
            List of processing results
        """
        with PerformanceLogger(logger, "process_face_images"):
            try:
                # Download images from Drive
                await self._download_processing_images()
                
                # Get list of raw images
                raw_images = list(settings.paths.raw_images_dir.glob("*.png"))
                raw_images.extend(list(settings.paths.raw_images_dir.glob("*.jpg")))
                
                if not raw_images:
                    logger.info("No raw images found for processing")
                    return []
                
                results = []
                
                # Process images in batches
                for i in range(0, len(raw_images), batch_size):
                    batch = raw_images[i:i + batch_size]
                    batch_results = await self._process_face_batch(batch)
                    results.extend(batch_results)
                
                logger.info(
                    f"Processed {len(raw_images)} face images",
                    extra={'total_images': len(raw_images), 'successful': sum(1 for r in results if r.success)}
                )
                
                return results
                
            except Exception as e:
                logger.error(f"Face processing batch failed: {e}", exc_info=True)
                raise ImageProcessingError(f"Face processing failed: {e}")
    
    async def _process_face_batch(self, image_paths: List[Path]) -> List[ImageProcessingResult]:
        """Process a batch of face images."""
        results = []
        
        for image_path in image_paths:
            try:
                result = await self._process_single_face_image(image_path)
                results.append(result)
                
                # Small delay between requests to avoid overwhelming the API
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                results.append(ImageProcessingResult.failure_result(str(e)))
        
        return results
    
    async def _process_single_face_image(self, image_path: Path) -> ImageProcessingResult:
        """Process a single face image."""
        start_time = time.time()
        
        try:
            # Determine if this is an Excel-generated image
            is_excel_image = image_path.stem.isdigit()
            
            # Get corresponding mask
            mask_path = settings.paths.masks_dir / image_path.name
            if not mask_path.exists():
                raise FaceProcessingError(f"Mask not found for {image_path.name}")
            
            # Get processing configuration
            config = (FaceProcessingConfig.for_excel_images() 
                     if is_excel_image else FaceProcessingConfig.for_regular_images())
            
            # Create processing request
            request = ImageProcessingRequest(
                source_image_path=str(image_path),
                mask_image_path=str(mask_path),
                output_path=str(settings.paths.final_images_dir / image_path.name),
                processing_type="face_fix",
                prompt=STANDARD_PROMPTS["face_fix"],
                negative_prompt=NEGATIVE_PROMPTS["face_processing"],
                denoising_strength=config.denoising_strength,
                cfg_scale=config.cfg_scale,
                steps=config.steps,
                mask_blur=config.mask_blur,
                controlnet_model="control_v11p_sd15_openpose [cab727d4]",
                controlnet_module="openpose_face"
            )
            
            # Process image
            result = await self._execute_image_processing(request)
            
            if result.success and is_excel_image:
                # Update Google Sheet for Excel images
                await self._update_sheet_for_processed_image(image_path.stem, result.output_url)
            
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            raise FaceProcessingError(f"Face processing failed for {image_path.name}: {e}")
    
    async def _execute_image_processing(self, request: ImageProcessingRequest) -> ImageProcessingResult:
        """Execute image processing request."""
        try:
            # Read source image and mask
            with open(request.source_image_path, "rb") as f:
                source_image_b64 = base64.b64encode(f.read()).decode()
            
            mask_image_b64 = None
            if request.mask_image_path:
                with open(request.mask_image_path, "rb") as f:
                    mask_image_b64 = base64.b64encode(f.read()).decode()
            
            # Create Stable Diffusion configuration for img2img
            config = StableDiffusionConfig(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                steps=request.steps,
                cfg_scale=request.cfg_scale,
                denoising_strength=request.denoising_strength,
                mask_blur=request.mask_blur,
                width=512,
                height=512,
                restore_faces=True
            )
            
            # Add ControlNet configuration
            if request.controlnet_model and request.controlnet_module:
                config.controlnet_args = {
                    "input_image": source_image_b64,
                    "module": request.controlnet_module,
                    "model": request.controlnet_model
                }
            
            # Process with Stable Diffusion
            result = await self.sd_client.image_to_image(
                config=config,
                init_image=source_image_b64,
                mask_image=mask_image_b64
            )
            
            if not result.success:
                return ImageProcessingResult.failure_result(result.error_message)
            
            # Save processed image
            output_path = Path(request.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(result.output_data))
            
            # Upload to Drive
            output_url = await self.storage_service.upload_file(
                file_path=str(output_path),
                folder_id=settings.database.drive_folder_ids["final"],
                filename=output_path.name
            )
            
            return ImageProcessingResult.success_result(
                output_path=str(output_path),
                output_url=output_url,
                processing_time=result.processing_time
            )
            
        except Exception as e:
            return ImageProcessingResult.failure_result(str(e))
    
    async def _save_and_upload_image(
        self,
        base64_data: str,
        filename: str,
        folder_id: str
    ) -> str:
        """Save image locally and upload to Google Drive."""
        # Decode and save locally
        image_data = base64.b64decode(base64_data)
        local_path = settings.paths.temp_dir / filename
        
        with open(local_path, 'wb') as f:
            f.write(image_data)
        
        # Upload to Google Drive
        image_url = await self.storage_service.upload_file(
            file_path=str(local_path),
            folder_id=folder_id,
            filename=filename
        )
        
        return image_url
    
    async def _download_processing_images(self) -> None:
        """Download images for processing from Google Drive."""
        try:
            # Clear existing directories
            await self._clear_processing_directories()
            
            # Download raw images
            await self.storage_service.download_folder_contents(
                folder_id=settings.database.drive_folder_ids["raw_images"],
                local_path=str(settings.paths.raw_images_dir)
            )
            
            # Download masks
            await self.storage_service.download_folder_contents(
                folder_id=settings.database.drive_folder_ids["masks"],
                local_path=str(settings.paths.masks_dir)
            )
            
            # Download skin masks
            await self.storage_service.download_folder_contents(
                folder_id=settings.database.drive_folder_ids["skin_masks"],
                local_path=str(settings.paths.skin_masks_dir)
            )
            
        except Exception as e:
            logger.error(f"Failed to download processing images: {e}")
            raise
    
    async def _clear_processing_directories(self) -> None:
        """Clear processing directories."""
        from config.credentials import SecureFileManager
        
        directories = [
            settings.paths.raw_images_dir,
            settings.paths.masks_dir,
            settings.paths.skin_masks_dir,
            settings.paths.final_images_dir,
            settings.paths.processed_images_dir
        ]
        
        for directory in directories:
            if directory.exists():
                SecureFileManager.safe_remove_files("*", str(directory))
    
    async def _update_sheet_for_processed_image(self, image_index: str, image_url: str) -> None:
        """Update Google Sheet with processed image URL."""
        try:
            from core.repositories.content_repository import ContentRepository
            
            # This would update the sheet - implementation depends on repository
            logger.info(f"Would update sheet for image {image_index} with URL {image_url}")
            
        except Exception as e:
            logger.error(f"Failed to update sheet for image {image_index}: {e}")