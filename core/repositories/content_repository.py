"""Repository for content data access via Google Sheets."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from config.constants import SHEET_COLUMNS, ContentType, ApprovalStatus, PostingStatus
from core.models.content import ContentItem, LocationData
from core.models.instagram import InstagramMetrics
from core.exceptions import GoogleSheetsError, ValidationError
from infrastructure.apis.sheets_client import GoogleSheetsClient

logger = get_logger(__name__)


class ContentRepository:
    """Repository for managing content data in Google Sheets."""
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """Initialize content repository.
        
        Args:
            sheets_client: Google Sheets API client
        """
        self.sheets_client = sheets_client
        self._cache = {}
        self._cache_timestamp = None
    
    async def get_all_content(self, use_cache: bool = True) -> List[ContentItem]:
        """Get all content items from the sheet.
        
        Args:
            use_cache: Whether to use cached data if available
            
        Returns:
            List of content items
            
        Raises:
            GoogleSheetsError: If sheet access fails
        """
        with PerformanceLogger(logger, "get_all_content"):
            try:
                # Check cache first
                if use_cache and self._is_cache_valid():
                    logger.debug("Using cached content data")
                    return self._cache.get('all_content', [])
                
                # Fetch from Google Sheets
                sheet_data = await self.sheets_client.get_all_records()
                
                content_items = []
                for i, row in enumerate(sheet_data):
                    if not row.get('index', ''):  # Skip empty rows
                        continue
                    
                    try:
                        content_item = ContentItem.from_sheet_row(row, i)
                        content_items.append(content_item)
                    except Exception as e:
                        logger.warning(f"Failed to parse row {i}: {e}")
                        continue
                
                # Update cache
                self._cache['all_content'] = content_items
                self._cache_timestamp = datetime.utcnow()
                
                logger.info(f"Loaded {len(content_items)} content items from sheet")
                return content_items
                
            except Exception as e:
                logger.error(f"Failed to get content from sheet: {e}", exc_info=True)
                raise GoogleSheetsError(f"Failed to retrieve content: {e}")
    
    async def get_content_by_status(
        self,
        approval_status: ApprovalStatus,
        posting_status: Optional[PostingStatus] = None,
        content_type: Optional[ContentType] = None
    ) -> List[ContentItem]:
        """Get content items filtered by status.
        
        Args:
            approval_status: Approval status to filter by
            posting_status: Optional posting status filter
            content_type: Optional content type filter
            
        Returns:
            Filtered list of content items
        """
        with PerformanceLogger(logger, "get_content_by_status"):
            all_content = await self.get_all_content()
            
            filtered_content = []
            for item in all_content:
                # Check approval status
                if item.approval_status != approval_status:
                    continue
                
                # Check posting status if specified
                if posting_status is not None and item.posting_status != posting_status:
                    continue
                
                # Check content type if specified
                if content_type is not None and item.content_type != content_type:
                    continue
                
                filtered_content.append(item)
            
            logger.debug(
                f"Filtered {len(filtered_content)} items by status",
                extra={
                    'approval_status': approval_status.value,
                    'posting_status': posting_status.value if posting_status else None,
                    'content_type': content_type.value if content_type else None
                }
            )
            
            return filtered_content
    
    async def get_approved_posts_for_posting(self) -> List[ContentItem]:
        """Get approved posts ready for Instagram posting.
        
        Returns:
            List of approved post content items grouped by group_id
        """
        approved_posts = await self.get_content_by_status(
            approval_status=ApprovalStatus.APPROVED,
            posting_status=PostingStatus.NOT_POSTED,
            content_type=ContentType.POST
        )
        
        # Filter out items missing required data
        ready_posts = []
        for item in approved_posts:
            if (item.image and item.image.url and 
                item.caption and item.location and item.group_id):
                ready_posts.append(item)
        
        return ready_posts
    
    async def get_approved_stories_for_posting(self) -> List[ContentItem]:
        """Get approved stories ready for Instagram posting.
        
        Returns:
            List of approved story content items
        """
        approved_stories = await self.get_content_by_status(
            approval_status=ApprovalStatus.APPROVED,
            posting_status=PostingStatus.NOT_POSTED,
            content_type=ContentType.STORY
        )
        
        # Filter out items missing required data
        ready_stories = []
        for item in approved_stories:
            if item.image and item.image.url:
                ready_stories.append(item)
        
        return ready_stories[:4]  # Limit to 4 stories
    
    async def create_content_batch(self, content_items: List[ContentItem]) -> List[ContentItem]:
        """Create a batch of content items in the sheet.
        
        Args:
            content_items: List of content items to create
            
        Returns:
            List of created content items with updated indices
            
        Raises:
            GoogleSheetsError: If creation fails
        """
        with PerformanceLogger(logger, f"create_content_batch({len(content_items)})"):
            try:
                if not content_items:
                    return []
                
                # Get current last index
                last_index = await self._get_last_index()
                
                # Prepare rows for insertion
                rows_to_insert = []
                for i, item in enumerate(content_items):
                    item.index = last_index + i + 1
                    rows_to_insert.append(item.to_sheet_row())
                
                # Insert rows into sheet
                await self.sheets_client.append_rows(rows_to_insert)
                
                # Clear cache to force refresh
                self._invalidate_cache()
                
                logger.info(
                    f"Created {len(content_items)} content items in sheet",
                    extra={'start_index': last_index + 1, 'count': len(content_items)}
                )
                
                return content_items
                
            except Exception as e:
                logger.error(f"Failed to create content batch: {e}", exc_info=True)
                raise GoogleSheetsError(f"Failed to create content: {e}")
    
    async def update_content_item(self, content_item: ContentItem) -> ContentItem:
        """Update a content item in the sheet.
        
        Args:
            content_item: Content item to update
            
        Returns:
            Updated content item
            
        Raises:
            GoogleSheetsError: If update fails
        """
        with PerformanceLogger(logger, f"update_content_item({content_item.index})"):
            try:
                # Prepare row data
                row_data = content_item.to_sheet_row()
                
                # Update specific row
                await self.sheets_client.update_row(
                    row_index=content_item.index + 1,  # +1 for header row
                    values=row_data
                )
                
                # Clear cache to force refresh
                self._invalidate_cache()
                
                logger.debug(f"Updated content item {content_item.index}")
                return content_item
                
            except Exception as e:
                logger.error(f"Failed to update content item {content_item.index}: {e}")
                raise GoogleSheetsError(f"Failed to update content: {e}")
    
    async def mark_content_as_posted(
        self,
        content_items: List[ContentItem],
        posted_at: Optional[datetime] = None
    ) -> None:
        """Mark content items as posted on Instagram.
        
        Args:
            content_items: List of content items to mark as posted
            posted_at: Timestamp when posted (defaults to now)
        """
        with PerformanceLogger(logger, f"mark_content_as_posted({len(content_items)})"):
            try:
                if posted_at is None:
                    posted_at = datetime.utcnow()
                
                # Update each content item
                for item in content_items:
                    item.posting_status = PostingStatus.POSTED
                    item.posted_at = posted_at
                    
                    # Update the posting timestamp in the sheet
                    await self.sheets_client.update_cell(
                        row=item.index + 1,  # +1 for header row
                        col=SHEET_COLUMNS.index("posted_on_instagram") + 1,  # +1 for 1-based indexing
                        value=posted_at.strftime("%Y-%m-%d %H:%M")
                    )
                
                # Clear cache
                self._invalidate_cache()
                
                logger.info(f"Marked {len(content_items)} items as posted")
                
            except Exception as e:
                logger.error(f"Failed to mark content as posted: {e}")
                raise GoogleSheetsError(f"Failed to update posting status: {e}")
    
    async def update_image_data(
        self,
        content_item: ContentItem,
        image_url: str,
        hyperlink_url: Optional[str] = None
    ) -> None:
        """Update image data for a content item.
        
        Args:
            content_item: Content item to update
            image_url: URL of the generated image
            hyperlink_url: Optional hyperlink URL
        """
        with PerformanceLogger(logger, f"update_image_data({content_item.index})"):
            try:
                # Update image cell with IMAGE formula
                image_formula = f'=IMAGE("{image_url}", 4, 120, 120)'
                await self.sheets_client.update_cell(
                    row=content_item.index + 1,
                    col=SHEET_COLUMNS.index("image") + 1,
                    value=image_formula
                )
                
                # Update hyperlink cell if provided
                if hyperlink_url:
                    hyperlink_formula = f'=HYPERLINK("{hyperlink_url}", "Link")'
                    await self.sheets_client.update_cell(
                        row=content_item.index + 1,
                        col=SHEET_COLUMNS.index("hyperlink_image") + 1,
                        value=hyperlink_formula
                    )
                
                # Update generated timestamp
                await self.sheets_client.update_cell(
                    row=content_item.index + 1,
                    col=SHEET_COLUMNS.index("generated_on") + 1,
                    value=datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
                )
                
                # Update content item object
                if content_item.image:
                    content_item.image.url = image_url
                content_item.generated_at = datetime.utcnow()
                
                # Clear cache
                self._invalidate_cache()
                
                logger.debug(f"Updated image data for content {content_item.index}")
                
            except Exception as e:
                logger.error(f"Failed to update image data: {e}")
                raise GoogleSheetsError(f"Failed to update image: {e}")
    
    async def update_caption_data(self, content_item: ContentItem, caption: str) -> None:
        """Update caption for a content item.
        
        Args:
            content_item: Content item to update
            caption: Generated caption text
        """
        with PerformanceLogger(logger, f"update_caption_data({content_item.index})"):
            try:
                # Update caption cell
                await self.sheets_client.update_cell(
                    row=content_item.index + 1,
                    col=SHEET_COLUMNS.index("caption") + 1,
                    value=caption
                )
                
                # Update content item object
                if content_item.caption:
                    content_item.caption.text = caption
                
                # Clear cache
                self._invalidate_cache()
                
                logger.debug(f"Updated caption for content {content_item.index}")
                
            except Exception as e:
                logger.error(f"Failed to update caption: {e}")
                raise GoogleSheetsError(f"Failed to update caption: {e}")
    
    async def get_content_metrics(self) -> InstagramMetrics:
        """Get content metrics for monitoring.
        
        Returns:
            Instagram metrics based on content data
        """
        with PerformanceLogger(logger, "get_content_metrics"):
            try:
                all_content = await self.get_all_content()
                
                # Calculate metrics
                total_posts = len([c for c in all_content if c.content_type == ContentType.POST])
                total_stories = len([c for c in all_content if c.content_type == ContentType.STORY])
                
                pending_approvals = len([
                    c for c in all_content 
                    if c.approval_status == ApprovalStatus.PENDING and c.image
                ])
                
                # Today's posts
                today = datetime.utcnow().date()
                posts_today = len([
                    c for c in all_content 
                    if (c.posted_at and c.posted_at.date() == today and 
                        c.content_type == ContentType.POST)
                ])
                
                stories_today = len([
                    c for c in all_content 
                    if (c.posted_at and c.posted_at.date() == today and 
                        c.content_type == ContentType.STORY)
                ])
                
                # Last successful post
                posted_items = [
                    c for c in all_content 
                    if c.posting_status == PostingStatus.POSTED and c.posted_at
                ]
                last_successful_post = None
                if posted_items:
                    last_successful_post = max(posted_items, key=lambda x: x.posted_at).posted_at
                
                metrics = InstagramMetrics(
                    total_posts=total_posts,
                    total_stories=total_stories,
                    pending_approvals=pending_approvals,
                    posts_today=posts_today,
                    stories_today=stories_today,
                    recent_errors=0,  # Would need error tracking
                    last_successful_post=last_successful_post
                )
                
                return metrics
                
            except Exception as e:
                logger.error(f"Failed to get content metrics: {e}")
                return InstagramMetrics()  # Return empty metrics on error
    
    async def get_non_posted_content_counts(self) -> Dict[str, int]:
        """Get counts of non-posted content by type.
        
        Returns:
            Dictionary with content type counts
        """
        try:
            all_content = await self.get_all_content()
            
            counts = {
                'posts': 0,
                'stories': 0,
                'approved_posts': 0,
                'approved_stories': 0
            }
            
            # Count unique group IDs for posts
            post_group_ids = set()
            approved_post_group_ids = set()
            
            for item in all_content:
                if item.posting_status == PostingStatus.NOT_POSTED:
                    if item.content_type == ContentType.POST:
                        post_group_ids.add(item.group_id)
                        if item.approval_status == ApprovalStatus.APPROVED and item.image:
                            approved_post_group_ids.add(item.group_id)
                    
                    elif item.content_type == ContentType.STORY:
                        counts['stories'] += 1
                        if item.approval_status == ApprovalStatus.APPROVED and item.image:
                            counts['approved_stories'] += 1
            
            counts['posts'] = len(post_group_ids)
            counts['approved_posts'] = len(approved_post_group_ids)
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to get content counts: {e}")
            return {'posts': 0, 'stories': 0, 'approved_posts': 0, 'approved_stories': 0}
    
    async def _get_last_index(self) -> int:
        """Get the last used index in the sheet.
        
        Returns:
            Last index number
        """
        try:
            all_content = await self.get_all_content(use_cache=False)
            if not all_content:
                return 0
            
            return max(item.index for item in all_content)
            
        except Exception as e:
            logger.error(f"Failed to get last index: {e}")
            return 0
    
    def _is_cache_valid(self, max_age_seconds: int = 300) -> bool:
        """Check if cache is still valid.
        
        Args:
            max_age_seconds: Maximum cache age in seconds
            
        Returns:
            True if cache is valid
        """
        if not self._cache_timestamp:
            return False
        
        age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
        return age < max_age_seconds
    
    def _invalidate_cache(self) -> None:
        """Invalidate the current cache."""
        self._cache.clear()
        self._cache_timestamp = None