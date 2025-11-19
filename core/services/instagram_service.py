"""Instagram automation service."""

import asyncio
from datetime import datetime
from typing import List, Optional, Tuple
from pathlib import Path

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from config.constants import SUCCESS_MESSAGES, ERROR_MESSAGES
from core.models.content import ContentItem
from core.models.instagram import InstagramPost, InstagramStory, PostingResult, InstagramMetrics
from core.exceptions import InstagramPostingError, ContentNotApprovedError, ValidationError
from infrastructure.web.selenium_automation import SeleniumInstagramClient
from infrastructure.messaging.notification_service import NotificationService

logger = get_logger(__name__)


class InstagramService:
    """Service for Instagram posting automation."""
    
    def __init__(
        self,
        selenium_client: SeleniumInstagramClient,
        notification_service: NotificationService
    ):
        """Initialize Instagram service.
        
        Args:
            selenium_client: Selenium client for web automation
            notification_service: Service for sending notifications
        """
        self.selenium_client = selenium_client
        self.notification_service = notification_service
    
    async def post_approved_content(self) -> List[PostingResult]:
        """Post all approved content to Instagram.
        
        Returns:
            List of posting results
        """
        with PerformanceLogger(logger, "post_approved_content"):
            try:
                # Get approved posts and stories
                approved_posts = await self._get_approved_posts()
                approved_stories = await self._get_approved_stories()
                
                results = []
                
                # Post Instagram posts
                for post in approved_posts:
                    try:
                        result = await self.post_instagram_post(post)
                        results.append(result)
                        
                        if result.success:
                            await self._mark_content_as_posted(post.content_items)
                        
                        # Delay between posts to avoid rate limiting
                        await asyncio.sleep(30)
                        
                    except Exception as e:
                        logger.error(f"Failed to post Instagram post: {e}")
                        results.append(PostingResult.failure_result(str(e)))
                
                # Post Instagram stories
                for story in approved_stories:
                    try:
                        result = await self.post_instagram_story(story)
                        results.append(result)
                        
                        if result.success:
                            await self._mark_content_as_posted([story.content_item])
                        
                        # Delay between stories
                        await asyncio.sleep(15)
                        
                    except Exception as e:
                        logger.error(f"Failed to post Instagram story: {e}")
                        results.append(PostingResult.failure_result(str(e)))
                
                # Send summary notification
                successful_posts = sum(1 for r in results if r.success)
                total_posts = len(results)
                
                if successful_posts > 0:
                    await self.notification_service.send_success_notification(
                        f"Successfully posted {successful_posts}/{total_posts} items to Instagram. "
                        f"Check out {settings.instagram.profile_name}"
                    )
                else:
                    await self.notification_service.send_error_notification(
                        "No content was posted to Instagram. Please check the system."
                    )
                
                return results
                
            except Exception as e:
                logger.error(f"Instagram posting batch failed: {e}", exc_info=True)
                await self.notification_service.send_error_notification(
                    f"Instagram posting failed: {e}"
                )
                raise InstagramPostingError(f"Posting batch failed: {e}")
    
    async def post_instagram_post(self, post: InstagramPost) -> PostingResult:
        """Post content to Instagram feed.
        
        Args:
            post: Instagram post data
            
        Returns:
            Posting result
        """
        with PerformanceLogger(logger, f"post_instagram_post({post.group_id})"):
            try:
                # Validate post data
                await self._validate_post_data(post)
                
                # Download images locally
                local_image_paths = await self._download_images_for_posting(post.image_urls)
                
                # Post to Instagram using Selenium
                result = await self.selenium_client.post_to_instagram(
                    image_paths=local_image_paths,
                    caption=post.formatted_caption,
                    location=post.location.name,
                    alt_text=post.alt_text
                )
                
                if result.success:
                    logger.info(
                        f"Successfully posted to Instagram",
                        extra={
                            'group_id': str(post.group_id),
                            'images_count': len(post.images),
                            'location': post.location.name
                        }
                    )
                else:
                    logger.error(
                        f"Instagram posting failed: {result.error_message}",
                        extra={'group_id': str(post.group_id)}
                    )
                
                # Clean up temporary files
                await self._cleanup_temp_files(local_image_paths)
                
                return result
                
            except Exception as e:
                logger.error(
                    f"Instagram post failed: {e}",
                    extra={'group_id': str(post.group_id)},
                    exc_info=True
                )
                raise InstagramPostingError(
                    f"Failed to post to Instagram: {e}",
                    post_type="post"
                )
    
    async def post_instagram_story(self, story: InstagramStory) -> PostingResult:
        """Post content to Instagram story.
        
        Args:
            story: Instagram story data
            
        Returns:
            Posting result
        """
        with PerformanceLogger(logger, f"post_instagram_story({story.content_item.id})"):
            try:
                # Download story image
                local_image_path = await self._download_single_image(story.image_url)
                
                # Post story using Selenium
                result = await self.selenium_client.post_story_to_instagram(
                    image_path=local_image_path,
                    caption=story.formatted_caption
                )
                
                if result.success:
                    logger.info(
                        f"Successfully posted story to Instagram",
                        extra={'content_id': str(story.content_item.id)}
                    )
                
                # Clean up temporary file
                await self._cleanup_temp_files([local_image_path])
                
                return result
                
            except Exception as e:
                logger.error(
                    f"Instagram story post failed: {e}",
                    extra={'content_id': str(story.content_item.id)},
                    exc_info=True
                )
                raise InstagramPostingError(
                    f"Failed to post story: {e}",
                    post_type="story"
                )
    
    async def get_instagram_metrics(self) -> InstagramMetrics:
        """Get Instagram account metrics.
        
        Returns:
            Instagram metrics data
        """
        try:
            # This would typically query the content repository
            # For now, return placeholder metrics
            return InstagramMetrics(
                total_posts=100,
                total_stories=50,
                pending_approvals=5,
                posts_today=2,
                stories_today=1,
                recent_errors=0,
                last_successful_post=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to get Instagram metrics: {e}")
            return InstagramMetrics()  # Return empty metrics
    
    async def _get_approved_posts(self) -> List[InstagramPost]:
        """Get approved Instagram posts ready for posting.
        
        Returns:
            List of approved Instagram posts
        """
        try:
            # This would query the content repository
            # Implementation depends on the repository pattern
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get approved posts: {e}")
            return []
    
    async def _get_approved_stories(self) -> List[InstagramStory]:
        """Get approved Instagram stories ready for posting.
        
        Returns:
            List of approved Instagram stories
        """
        try:
            # This would query the content repository
            # Implementation depends on the repository pattern
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get approved stories: {e}")
            return []
    
    async def _validate_post_data(self, post: InstagramPost) -> None:
        """Validate post data before posting.
        
        Args:
            post: Instagram post to validate
            
        Raises:
            ValidationError: If validation fails
            ContentNotApprovedError: If content is not approved
        """
        # Check if all content items are approved
        for item in post.content_items:
            if not item.is_approved:
                raise ContentNotApprovedError(str(item.id))
        
        # Check if images are available
        if not post.images:
            raise ValidationError("Post must have at least one image")
        
        for image in post.images:
            if not image.url:
                raise ValidationError("All images must have valid URLs")
        
        # Check caption
        if not post.caption or not post.caption.text:
            raise ValidationError("Post must have a caption")
        
        # Check image count
        if len(post.images) > settings.instagram.max_images_per_post:
            raise ValidationError(
                f"Too many images: {len(post.images)} (max: {settings.instagram.max_images_per_post})"
            )
    
    async def _download_images_for_posting(self, image_urls: List[str]) -> List[str]:
        """Download images locally for posting.
        
        Args:
            image_urls: List of image URLs to download
            
        Returns:
            List of local file paths
        """
        import httpx
        
        local_paths = []
        temp_dir = settings.paths.temp_dir
        temp_dir.mkdir(exist_ok=True)
        
        async with httpx.AsyncClient() as client:
            for i, url in enumerate(image_urls):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    filename = f"temp_post_{i}.png"
                    local_path = temp_dir / filename
                    
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    
                    local_paths.append(str(local_path))
                    
                except Exception as e:
                    logger.error(f"Failed to download image {url}: {e}")
                    raise
        
        return local_paths
    
    async def _download_single_image(self, image_url: str) -> str:
        """Download a single image for posting.
        
        Args:
            image_url: Image URL to download
            
        Returns:
            Local file path
        """
        paths = await self._download_images_for_posting([image_url])
        return paths[0] if paths else ""
    
    async def _cleanup_temp_files(self, file_paths: List[str]) -> None:
        """Clean up temporary files.
        
        Args:
            file_paths: List of file paths to delete
        """
        for file_path in file_paths:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {file_path}: {e}")
    
    async def _mark_content_as_posted(self, content_items: List[ContentItem]) -> None:
        """Mark content items as posted.
        
        Args:
            content_items: List of content items to mark as posted
        """
        try:
            # This would update the content repository
            # Implementation depends on the repository pattern
            for item in content_items:
                item.posted_at = datetime.utcnow()
                # Update in repository
                
        except Exception as e:
            logger.error(f"Failed to mark content as posted: {e}")