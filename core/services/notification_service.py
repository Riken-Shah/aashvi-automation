"""Notification service for system alerts and updates."""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any

from config.logging_config import get_logger
from config.settings import settings
from core.exceptions import TelegramError
from infrastructure.messaging.telegram_client import TelegramClient

logger = get_logger(__name__)


class NotificationService:
    """Service for sending notifications via various channels."""
    
    def __init__(self, telegram_client: TelegramClient):
        """Initialize notification service.
        
        Args:
            telegram_client: Telegram client for sending messages
        """
        self.telegram_client = telegram_client
        self._notification_queue = asyncio.Queue()
        self._is_processing = False
    
    async def send_success_notification(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a success notification.
        
        Args:
            message: Success message to send
            context: Additional context information
            
        Returns:
            True if notification was sent successfully
        """
        if not settings.notifications.enable_success_notifications:
            return True
        
        try:
            formatted_message = f"✅ {message}"
            return await self.telegram_client.send_message(formatted_message)
            
        except Exception as e:
            logger.error(f"Failed to send success notification: {e}")
            return False
    
    async def send_error_notification(
        self,
        message: str,
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send an error notification.
        
        Args:
            message: Error message to send
            error: Optional exception object
            context: Additional context information
            
        Returns:
            True if notification was sent successfully
        """
        if not settings.notifications.enable_error_notifications:
            return True
        
        try:
            formatted_message = f"🚨 ERROR: {message}"
            
            if error:
                formatted_message += f"\n\nError: {str(error)}"
            
            if context:
                formatted_message += f"\n\nContext: {context}"
            
            return await self.telegram_client.send_message(formatted_message)
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
            return False
    
    async def send_warning_notification(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a warning notification.
        
        Args:
            message: Warning message to send
            context: Additional context information
            
        Returns:
            True if notification was sent successfully
        """
        try:
            formatted_message = f"⚠️ WARNING: {message}"
            
            if context:
                formatted_message += f"\n\nContext: {context}"
            
            return await self.telegram_client.send_message(formatted_message)
            
        except Exception as e:
            logger.error(f"Failed to send warning notification: {e}")
            return False
    
    async def send_info_notification(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send an informational notification.
        
        Args:
            message: Info message to send
            context: Additional context information
            
        Returns:
            True if notification was sent successfully
        """
        try:
            formatted_message = f"ℹ️ {message}"
            
            if context:
                formatted_message += f"\n\nContext: {context}"
            
            return await self.telegram_client.send_message(formatted_message)
            
        except Exception as e:
            logger.error(f"Failed to send info notification: {e}")
            return False
    
    async def send_approval_notification(
        self,
        content_type: str,
        count: int,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification about content needing approval.
        
        Args:
            content_type: Type of content (posts/stories)
            count: Number of items needing approval
            context: Additional context information
            
        Returns:
            True if notification was sent successfully
        """
        try:
            if count >= 2:  # Only notify if there are multiple items
                message = f"👀 Hey! You have {count} non-approved {content_type} waiting for review."
                return await self.send_info_notification(message, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")
            return False
    
    async def send_story_nudge(
        self,
        images: List[str],
        location: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send story nudge with images.
        
        Args:
            images: List of image URLs for stories
            location: Current location
            context: Additional context information
            
        Returns:
            True if notification was sent successfully
        """
        try:
            if not images:
                return await self.send_info_notification(
                    "No stories available to post. Please check the content sheet.",
                    context
                )
            
            message = f"📱 Hey! It's been 3 hours, time to post a story for {location}!"
            
            # Send message with images
            return await self.telegram_client.send_media_group(
                message=message,
                media_urls=images
            )
            
        except Exception as e:
            logger.error(f"Failed to send story nudge: {e}")
            return False
    
    async def send_system_status(
        self,
        status: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send system status notification.
        
        Args:
            status: System status (healthy/warning/error)
            metrics: Optional system metrics
            
        Returns:
            True if notification was sent successfully
        """
        try:
            emoji = {
                'healthy': '💚',
                'warning': '⚠️',
                'error': '🚨'
            }.get(status, 'ℹ️')
            
            message = f"{emoji} System Status: {status.upper()}"
            
            if metrics:
                message += "\n\nMetrics:"
                for key, value in metrics.items():
                    message += f"\n• {key}: {value}"
            
            message += f"\n\nTimestamp: {datetime.utcnow().isoformat()}Z"
            
            return await self.send_info_notification(message)
            
        except Exception as e:
            logger.error(f"Failed to send system status: {e}")
            return False
    
    async def send_processing_update(
        self,
        operation: str,
        status: str,
        progress: Optional[int] = None,
        total: Optional[int] = None
    ) -> bool:
        """Send processing update notification.
        
        Args:
            operation: Name of the operation
            status: Status (started/in_progress/completed/failed)
            progress: Current progress count
            total: Total items to process
            
        Returns:
            True if notification was sent successfully
        """
        try:
            emoji = {
                'started': '🚀',
                'in_progress': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(status, 'ℹ️')
            
            message = f"{emoji} {operation}: {status.replace('_', ' ').title()}"
            
            if progress is not None and total is not None:
                percentage = round((progress / total) * 100)
                message += f"\n\nProgress: {progress}/{total} ({percentage}%)"
            
            # Only send for important updates to avoid spam
            if status in ['started', 'completed', 'failed']:
                return await self.send_info_notification(message)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send processing update: {e}")
            return False
    
    async def start_notification_processor(self) -> None:
        """Start the background notification processor."""
        if self._is_processing:
            return
        
        self._is_processing = True
        
        try:
            while self._is_processing:
                try:
                    # Process queued notifications
                    notification = await asyncio.wait_for(
                        self._notification_queue.get(),
                        timeout=60.0
                    )
                    
                    await self._process_queued_notification(notification)
                    
                except asyncio.TimeoutError:
                    # No notifications in queue, continue
                    continue
                except Exception as e:
                    logger.error(f"Error processing notification: {e}")
                    await asyncio.sleep(5)  # Brief delay before retrying
                    
        except Exception as e:
            logger.error(f"Notification processor failed: {e}")
        finally:
            self._is_processing = False
    
    async def stop_notification_processor(self) -> None:
        """Stop the notification processor."""
        self._is_processing = False
    
    async def queue_notification(
        self,
        notification_type: str,
        message: str,
        **kwargs
    ) -> None:
        """Queue a notification for background processing.
        
        Args:
            notification_type: Type of notification
            message: Message to send
            **kwargs: Additional arguments
        """
        notification = {
            'type': notification_type,
            'message': message,
            'timestamp': datetime.utcnow(),
            'kwargs': kwargs
        }
        
        await self._notification_queue.put(notification)
    
    async def _process_queued_notification(self, notification: Dict[str, Any]) -> None:
        """Process a queued notification.
        
        Args:
            notification: Notification data to process
        """
        try:
            notification_type = notification['type']
            message = notification['message']
            kwargs = notification.get('kwargs', {})
            
            if notification_type == 'success':
                await self.send_success_notification(message, **kwargs)
            elif notification_type == 'error':
                await self.send_error_notification(message, **kwargs)
            elif notification_type == 'warning':
                await self.send_warning_notification(message, **kwargs)
            elif notification_type == 'info':
                await self.send_info_notification(message, **kwargs)
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                
        except Exception as e:
            logger.error(f"Failed to process queued notification: {e}")
    
    async def send_batch_notification(
        self,
        notifications: List[Dict[str, Any]]
    ) -> List[bool]:
        """Send multiple notifications in batch.
        
        Args:
            notifications: List of notification data
            
        Returns:
            List of success/failure results
        """
        results = []
        
        for notification in notifications:
            try:
                notification_type = notification['type']
                message = notification['message']
                kwargs = notification.get('kwargs', {})
                
                if notification_type == 'success':
                    result = await self.send_success_notification(message, **kwargs)
                elif notification_type == 'error':
                    result = await self.send_error_notification(message, **kwargs)
                elif notification_type == 'warning':
                    result = await self.send_warning_notification(message, **kwargs)
                elif notification_type == 'info':
                    result = await self.send_info_notification(message, **kwargs)
                else:
                    result = False
                    logger.warning(f"Unknown notification type: {notification_type}")
                
                results.append(result)
                
                # Brief delay between notifications to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                results.append(False)
        
        return results