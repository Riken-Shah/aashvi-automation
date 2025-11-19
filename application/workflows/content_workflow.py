"""Content generation workflow orchestrator."""

import asyncio
from datetime import datetime
from typing import List, Optional

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from core.models.content import ContentRequest, ContentItem, LocationData
from core.models.processing import StableDiffusionConfig
from core.services.content_service import ContentGenerationService
from core.services.image_service import ImageProcessingService
from core.services.notification_service import NotificationService
from core.repositories.content_repository import ContentRepository
from core.repositories.config_repository import ConfigRepository
from core.exceptions import WorkflowError, ContentGenerationError

logger = get_logger(__name__)


class ContentGenerationWorkflow:
    """Orchestrates the complete content generation workflow."""
    
    def __init__(
        self,
        content_service: ContentGenerationService,
        image_service: ImageProcessingService,
        notification_service: NotificationService,
        content_repository: ContentRepository,
        config_repository: ConfigRepository
    ):
        """Initialize content workflow.
        
        Args:
            content_service: Service for content generation
            image_service: Service for image processing
            notification_service: Service for notifications
            content_repository: Repository for content data
            config_repository: Repository for configuration
        """
        self.content_service = content_service
        self.image_service = image_service
        self.notification_service = notification_service
        self.content_repo = content_repository
        self.config_repo = config_repository
    
    async def run_full_content_generation(
        self,
        location: Optional[LocationData] = None,
        post_count: int = 4,
        story_count: int = 2
    ) -> bool:
        """Run complete content generation workflow.
        
        Args:
            location: Optional location (uses current if None)
            post_count: Number of posts to generate
            story_count: Number of stories to generate
            
        Returns:
            True if workflow completed successfully
        """
        with PerformanceLogger(logger, "content_generation_workflow"):
            try:
                # Check if already running
                if await self.config_repo.is_process_running():
                    logger.info("Content generation already running, skipping")
                    return True
                
                # Set running status
                await self.config_repo.set_process_running(True)
                
                try:
                    await self.notification_service.send_processing_update(
                        operation="Content Generation",
                        status="started"
                    )
                    
                    # Get current location if not provided
                    if location is None:
                        location = await self.config_repo.get_current_location()
                    
                    # Check if we need more content
                    content_counts = await self.content_repo.get_non_posted_content_counts()
                    
                    # Generate posts if needed
                    if content_counts['posts'] < settings.app.max_non_posted_instagram_posts:
                        await self._generate_posts(location, post_count)
                    else:
                        logger.info(f"Enough posts available ({content_counts['posts']}), skipping generation")
                    
                    # Generate stories if needed  
                    if content_counts['stories'] < settings.app.max_non_posted_stories:
                        await self._generate_stories(location, story_count)
                    else:
                        logger.info(f"Enough stories available ({content_counts['stories']}), skipping generation")
                    
                    await self.notification_service.send_processing_update(
                        operation="Content Generation",
                        status="completed"
                    )
                    
                    return True
                    
                finally:
                    # Always clear running status
                    await self.config_repo.set_process_running(False)
                    
            except Exception as e:
                logger.error(f"Content generation workflow failed: {e}", exc_info=True)
                await self.notification_service.send_error_notification(
                    f"Content generation failed: {e}"
                )
                return False
    
    async def _generate_posts(self, location: LocationData, count: int = 4) -> None:
        """Generate Instagram posts."""
        try:
            logger.info(f"Generating {count} posts for {location.full_name}")
            
            # Create content request
            request = ContentRequest(
                content_type="posts",
                location=location,
                count=count
            )
            
            # Generate content items
            content_items = await self.content_service.generate_content_batch(request)
            
            # Save to repository
            saved_items = await self.content_repo.create_content_batch(content_items)
            
            # Generate images for content
            await self._generate_images_for_content(saved_items)
            
            # Generate captions for first item in each group
            await self._generate_captions_for_content(saved_items)
            
            logger.info(f"Successfully generated {len(saved_items)} posts")
            
        except Exception as e:
            logger.error(f"Failed to generate posts: {e}")
            raise WorkflowError(f"Post generation failed: {e}", workflow_step="post_generation")
    
    async def _generate_stories(self, location: LocationData, count: int = 2) -> None:
        """Generate Instagram stories."""
        try:
            logger.info(f"Generating {count} stories for {location.full_name}")
            
            # Create content request
            request = ContentRequest(
                content_type="story",
                location=location,
                count=count
            )
            
            # Generate content items
            content_items = await self.content_service.generate_content_batch(request)
            
            # Auto-approve stories
            for item in content_items:
                item.approval_status = "y"
            
            # Save to repository
            saved_items = await self.content_repo.create_content_batch(content_items)
            
            # Generate images for stories
            await self._generate_images_for_content(saved_items)
            
            logger.info(f"Successfully generated {len(saved_items)} stories")
            
        except Exception as e:
            logger.error(f"Failed to generate stories: {e}")
            raise WorkflowError(f"Story generation failed: {e}", workflow_step="story_generation")
    
    async def _generate_images_for_content(self, content_items: List[ContentItem]) -> None:
        """Generate images for content items."""
        try:
            for item in content_items:
                if not item.prompt:
                    continue
                
                try:
                    # Generate image
                    image_data = await self.image_service.generate_image_for_content(item)
                    
                    # Update item with image data
                    item.image = image_data
                    item.generated_at = datetime.utcnow()
                    
                    # Update in repository
                    await self.content_repo.update_image_data(
                        content_item=item,
                        image_url=image_data.url,
                        hyperlink_url=image_data.url
                    )
                    
                    logger.debug(f"Generated image for content {item.index}")
                    
                    # Brief delay between generations
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed to generate image for content {item.index}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to generate images: {e}")
            raise WorkflowError(f"Image generation failed: {e}", workflow_step="image_generation")
    
    async def _generate_captions_for_content(self, content_items: List[ContentItem]) -> None:
        """Generate captions for content items."""
        try:
            # Group by group_id and generate caption for first item in each group
            group_items = {}
            for item in content_items:
                if item.group_id not in group_items:
                    group_items[item.group_id] = []
                group_items[item.group_id].append(item)
            
            for group_id, items in group_items.items():
                first_item = items[0]  # Generate caption for first item only
                
                if first_item.content_type.value == "posts":
                    try:
                        # Generate caption
                        caption_data = await self.content_service.generate_caption(
                            content_item=first_item,
                            background=first_item.location.name
                        )
                        
                        # Update item
                        first_item.caption = caption_data
                        
                        # Update in repository
                        await self.content_repo.update_caption_data(
                            content_item=first_item,
                            caption=caption_data.formatted_caption
                        )
                        
                        logger.debug(f"Generated caption for content group {group_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate caption for group {group_id}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to generate captions: {e}")
            # Don't raise here as captions are not critical