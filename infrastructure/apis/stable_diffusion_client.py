"""Stable Diffusion API client for image generation."""

import asyncio
import httpx
from typing import Optional, Dict, Any

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from core.models.processing import StableDiffusionConfig, ImageProcessingResult
from core.repositories.config_repository import ConfigRepository
from core.exceptions import StableDiffusionError, StableDiffusionUnavailableError

logger = get_logger(__name__)


class StableDiffusionClient:
    """Async client for Stable Diffusion API operations."""
    
    def __init__(self, config_repository: ConfigRepository):
        """Initialize Stable Diffusion client.
        
        Args:
            config_repository: Repository for getting API URL
        """
        self.config_repo = config_repository
        self._base_url: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    async def ensure_connection(self) -> bool:
        """Ensure connection to Stable Diffusion API.
        
        Returns:
            True if connection is available
            
        Raises:
            StableDiffusionUnavailableError: If API is not available
        """
        try:
            # Get API URL from config
            api_url = await self.config_repo.get_stable_diffusion_url()
            
            if not api_url:
                raise StableDiffusionUnavailableError("No Stable Diffusion URL configured")
            
            self._base_url = api_url.rstrip('/')
            
            # Test connection
            if not await self._test_connection():
                raise StableDiffusionUnavailableError("Stable Diffusion API is not responding")
            
            logger.info(f"Connected to Stable Diffusion API: {self._base_url}")
            return True
            
        except StableDiffusionUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Stable Diffusion API: {e}")
            raise StableDiffusionUnavailableError(f"Connection failed: {e}")
    
    async def text_to_image(self, config: StableDiffusionConfig) -> ImageProcessingResult:
        """Generate image from text prompt.
        
        Args:
            config: Stable Diffusion configuration
            
        Returns:
            Image processing result with generated image data
            
        Raises:
            StableDiffusionError: If generation fails
        """
        with PerformanceLogger(logger, "stable_diffusion_txt2img"):
            try:
                await self.ensure_connection()
                
                payload = config.to_api_payload()
                
                async with self._get_client() as client:
                    response = await client.post(
                        f"{self._base_url}/sdapi/v1/txt2img",
                        json=payload,
                        timeout=900.0  # 15 minutes timeout
                    )
                    
                    if response.status_code != 200:
                        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                        raise StableDiffusionError(
                            f"Text-to-image generation failed: {response.status_code}",
                            status_code=response.status_code,
                            response_data=error_data
                        )
                    
                    result_data = response.json()
                    
                    if not result_data.get('images'):
                        raise StableDiffusionError("No images returned from API")
                    
                    logger.info(
                        f"Generated image successfully",
                        extra={
                            'prompt_length': len(config.prompt),
                            'steps': config.steps,
                            'cfg_scale': config.cfg_scale,
                            'size': f"{config.width}x{config.height}"
                        }
                    )
                    
                    return ImageProcessingResult.success_result(
                        output_path="",  # No local path for txt2img
                        processing_time=None,  # Would need to track this
                        model_used=config.model,
                        parameters=payload
                    ).copy(update={'output_data': result_data['images'][0]})
                    
            except StableDiffusionError:
                raise
            except Exception as e:
                logger.error(f"Text-to-image generation failed: {e}", exc_info=True)
                raise StableDiffusionError(f"Generation failed: {e}")
    
    async def image_to_image(
        self,
        config: StableDiffusionConfig,
        init_image: str,
        mask_image: Optional[str] = None
    ) -> ImageProcessingResult:
        """Generate image from existing image.
        
        Args:
            config: Stable Diffusion configuration
            init_image: Base64 encoded initial image
            mask_image: Optional base64 encoded mask image
            
        Returns:
            Image processing result
            
        Raises:
            StableDiffusionError: If generation fails
        """
        with PerformanceLogger(logger, "stable_diffusion_img2img"):
            try:
                await self.ensure_connection()
                
                payload = config.to_api_payload(include_controlnet=True)
                payload['init_images'] = [init_image]
                payload['include_init_images'] = True
                
                if mask_image:
                    payload['mask'] = mask_image
                
                async with self._get_client() as client:
                    response = await client.post(
                        f"{self._base_url}/sdapi/v1/img2img",
                        json=payload,
                        timeout=900.0
                    )
                    
                    if response.status_code != 200:
                        error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                        raise StableDiffusionError(
                            f"Image-to-image generation failed: {response.status_code}",
                            status_code=response.status_code,
                            response_data=error_data
                        )
                    
                    result_data = response.json()
                    
                    if not result_data.get('images'):
                        raise StableDiffusionError("No images returned from API")
                    
                    logger.info(
                        f"Processed image successfully",
                        extra={
                            'denoising_strength': config.denoising_strength,
                            'steps': config.steps,
                            'has_mask': mask_image is not None,
                            'has_controlnet': config.controlnet_args is not None
                        }
                    )
                    
                    return ImageProcessingResult.success_result(
                        output_path="",
                        processing_time=None,
                        model_used=config.model,
                        parameters=payload
                    ).copy(update={'output_data': result_data['images'][0]})
                    
            except StableDiffusionError:
                raise
            except Exception as e:
                logger.error(f"Image-to-image generation failed: {e}", exc_info=True)
                raise StableDiffusionError(f"Generation failed: {e}")
    
    async def get_models(self) -> Dict[str, Any]:
        """Get available models from the API.
        
        Returns:
            Dictionary with available models
        """
        try:
            await self.ensure_connection()
            
            async with self._get_client() as client:
                response = await client.get(f"{self._base_url}/sdapi/v1/sd-models")
                
                if response.status_code == 200:
                    models = response.json()
                    logger.debug(f"Retrieved {len(models)} available models")
                    return {'models': models}
                else:
                    logger.warning(f"Failed to get models: {response.status_code}")
                    return {'error': f"API returned {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {'error': str(e)}
    
    async def get_memory_info(self) -> Dict[str, Any]:
        """Get memory usage information from the API.
        
        Returns:
            Dictionary with memory info
        """
        try:
            await self.ensure_connection()
            
            async with self._get_client() as client:
                response = await client.get(f"{self._base_url}/sdapi/v1/memory")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {'error': f"API returned {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Failed to get memory info: {e}")
            return {'error': str(e)}
    
    async def interrupt_generation(self) -> bool:
        """Interrupt current generation if running.
        
        Returns:
            True if interrupt was successful
        """
        try:
            await self.ensure_connection()
            
            async with self._get_client() as client:
                response = await client.post(f"{self._base_url}/sdapi/v1/interrupt")
                
                if response.status_code == 200:
                    logger.info("Interrupted Stable Diffusion generation")
                    return True
                else:
                    logger.warning(f"Failed to interrupt generation: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to interrupt generation: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """Test connection to Stable Diffusion API.
        
        Returns:
            True if connection is working
        """
        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self._base_url}/sdapi/v1/memory",
                    timeout=10.0
                )
                return response.status_code == 200
                
        except Exception:
            return False
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for API calls.
        
        Returns:
            Configured HTTP client
        """
        return httpx.AsyncClient(
            timeout=httpx.Timeout(900.0),  # 15 minutes
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1)
        )
    
    async def close(self) -> None:
        """Close any open connections."""
        if self._client:
            await self._client.aclose()
            self._client = None