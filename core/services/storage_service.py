"""Storage service for file and cloud operations."""

from pathlib import Path
from typing import List, Optional, Dict, Any
import shutil
import asyncio

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from config.credentials import SecureFileManager
from core.exceptions import StorageError, FileNotFoundError, FileAccessError
from infrastructure.storage.drive_storage import DriveStorageService
from infrastructure.storage.local_storage import LocalStorageService

logger = get_logger(__name__)


class StorageService:
    """Unified storage service for local and cloud operations."""
    
    def __init__(
        self,
        drive_service: DriveStorageService,
        local_service: LocalStorageService
    ):
        """Initialize storage service.
        
        Args:
            drive_service: Google Drive storage service
            local_service: Local file storage service
        """
        self.drive_service = drive_service
        self.local_service = local_service
    
    async def save_image_with_backup(
        self,
        image_data: bytes,
        filename: str,
        drive_folder_id: str,
        local_backup: bool = True
    ) -> Dict[str, str]:
        """Save image locally and to cloud with backup.
        
        Args:
            image_data: Image binary data
            filename: Name of the file
            drive_folder_id: Google Drive folder ID
            local_backup: Whether to keep local backup
            
        Returns:
            Dictionary with local_path and cloud_url
            
        Raises:
            StorageError: If storage operation fails
        """
        with PerformanceLogger(logger, f"save_image_with_backup({filename})"):
            try:
                results = {}
                
                # Save locally first
                local_path = await self.local_service.save_file(
                    data=image_data,
                    filename=filename,
                    directory=settings.paths.temp_dir
                )
                results['local_path'] = local_path
                
                # Upload to cloud
                cloud_url = await self.drive_service.upload_file(
                    file_path=local_path,
                    folder_id=drive_folder_id,
                    filename=filename
                )
                results['cloud_url'] = cloud_url
                
                # Clean up local file if not needed for backup
                if not local_backup:
                    await self.local_service.delete_file(local_path)
                    results['local_path'] = None
                
                logger.info(
                    f"Saved image successfully",
                    extra={
                        'filename': filename,
                        'local_backup': local_backup,
                        'cloud_url': cloud_url
                    }
                )
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to save image {filename}: {e}", exc_info=True)
                raise StorageError(f"Failed to save image: {e}", file_path=filename)
    
    async def download_and_sync_images(
        self,
        drive_folder_id: str,
        local_directory: str,
        clean_local: bool = True
    ) -> List[str]:
        """Download images from Drive and sync with local directory.
        
        Args:
            drive_folder_id: Google Drive folder ID
            local_directory: Local directory path
            clean_local: Whether to clean local directory first
            
        Returns:
            List of downloaded file paths
            
        Raises:
            StorageError: If sync operation fails
        """
        with PerformanceLogger(logger, f"download_and_sync({drive_folder_id})"):
            try:
                local_dir = Path(local_directory)
                
                # Clean local directory if requested
                if clean_local and local_dir.exists():
                    await self._clean_directory_safely(local_dir)
                
                # Ensure directory exists
                local_dir.mkdir(parents=True, exist_ok=True)
                
                # Download from Drive
                downloaded_files = await self.drive_service.download_folder_contents(
                    folder_id=drive_folder_id,
                    local_path=str(local_dir)
                )
                
                logger.info(
                    f"Downloaded {len(downloaded_files)} files from Drive",
                    extra={
                        'folder_id': drive_folder_id,
                        'local_directory': str(local_dir),
                        'file_count': len(downloaded_files)
                    }
                )
                
                return downloaded_files
                
            except Exception as e:
                logger.error(f"Failed to download and sync images: {e}", exc_info=True)
                raise StorageError(f"Failed to sync images: {e}")
    
    async def backup_processed_images(
        self,
        source_directory: str,
        backup_folder_id: str,
        move_files: bool = True
    ) -> List[str]:
        """Backup processed images to archive folder.
        
        Args:
            source_directory: Local source directory
            backup_folder_id: Google Drive backup folder ID
            move_files: Whether to move (true) or copy (false) files
            
        Returns:
            List of backed up file URLs
            
        Raises:
            StorageError: If backup operation fails
        """
        with PerformanceLogger(logger, "backup_processed_images"):
            try:
                source_dir = Path(source_directory)
                if not source_dir.exists():
                    return []
                
                backed_up_urls = []
                
                # Get all image files
                image_files = []
                for pattern in ['*.png', '*.jpg', '*.jpeg']:
                    image_files.extend(source_dir.glob(pattern))
                
                if not image_files:
                    logger.info("No images found to backup")
                    return []
                
                # Process files in batches to avoid overwhelming the API
                batch_size = 5
                for i in range(0, len(image_files), batch_size):
                    batch = image_files[i:i + batch_size]
                    
                    for file_path in batch:
                        try:
                            # Upload to backup folder
                            backup_url = await self.drive_service.upload_file(
                                file_path=str(file_path),
                                folder_id=backup_folder_id,
                                filename=file_path.name
                            )
                            backed_up_urls.append(backup_url)
                            
                            # Remove local file if moving
                            if move_files:
                                file_path.unlink()
                            
                        except Exception as e:
                            logger.error(f"Failed to backup {file_path}: {e}")
                            continue
                    
                    # Brief delay between batches
                    await asyncio.sleep(2)
                
                logger.info(
                    f"Backed up {len(backed_up_urls)} images",
                    extra={
                        'source_directory': source_directory,
                        'backup_folder_id': backup_folder_id,
                        'move_files': move_files
                    }
                )
                
                return backed_up_urls
                
            except Exception as e:
                logger.error(f"Failed to backup images: {e}", exc_info=True)
                raise StorageError(f"Failed to backup images: {e}")
    
    async def organize_content_files(
        self,
        content_items: List[Any],
        organize_by: str = "date"
    ) -> Dict[str, List[str]]:
        """Organize content files by specified criteria.
        
        Args:
            content_items: List of content items with file paths
            organize_by: Organization method (date, type, status)
            
        Returns:
            Dictionary mapping organization keys to file paths
            
        Raises:
            StorageError: If organization fails
        """
        try:
            organized = {}
            
            for item in content_items:
                if not hasattr(item, 'image') or not item.image or not item.image.file_path:
                    continue
                
                # Determine organization key
                if organize_by == "date":
                    key = item.created_at.strftime("%Y-%m-%d") if hasattr(item, 'created_at') else "unknown"
                elif organize_by == "type":
                    key = item.content_type.value if hasattr(item, 'content_type') else "unknown"
                elif organize_by == "status":
                    key = item.approval_status.value if hasattr(item, 'approval_status') else "unknown"
                else:
                    key = "all"
                
                if key not in organized:
                    organized[key] = []
                
                organized[key].append(item.image.file_path)
            
            return organized
            
        except Exception as e:
            raise StorageError(f"Failed to organize files: {e}")
    
    async def cleanup_old_files(
        self,
        directories: List[str],
        max_age_days: int = 7,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Clean up old files from specified directories.
        
        Args:
            directories: List of directory paths to clean
            max_age_days: Maximum age of files to keep
            dry_run: If True, only report what would be deleted
            
        Returns:
            Dictionary with cleanup statistics
            
        Raises:
            StorageError: If cleanup operation fails
        """
        with PerformanceLogger(logger, "cleanup_old_files"):
            try:
                import time
                from datetime import datetime, timedelta
                
                cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
                stats = {'directories_processed': 0, 'files_deleted': 0, 'space_freed': 0}
                
                for directory in directories:
                    dir_path = Path(directory)
                    if not dir_path.exists():
                        continue
                    
                    stats['directories_processed'] += 1
                    
                    for file_path in dir_path.rglob('*'):
                        if not file_path.is_file():
                            continue
                        
                        # Check file age
                        if file_path.stat().st_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            
                            if not dry_run:
                                try:
                                    file_path.unlink()
                                    stats['files_deleted'] += 1
                                    stats['space_freed'] += file_size
                                except Exception as e:
                                    logger.warning(f"Failed to delete {file_path}: {e}")
                            else:
                                stats['files_deleted'] += 1
                                stats['space_freed'] += file_size
                
                action = "Would delete" if dry_run else "Deleted"
                logger.info(
                    f"{action} {stats['files_deleted']} old files, "
                    f"freed {stats['space_freed']} bytes",
                    extra=stats
                )
                
                return stats
                
            except Exception as e:
                logger.error(f"Failed to cleanup old files: {e}", exc_info=True)
                raise StorageError(f"Failed to cleanup files: {e}")
    
    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage usage metrics.
        
        Returns:
            Dictionary with storage metrics
        """
        try:
            metrics = {}
            
            # Local storage metrics
            for path_name, path_obj in [
                ('temp', settings.paths.temp_dir),
                ('raw_images', settings.paths.raw_images_dir),
                ('final_images', settings.paths.final_images_dir),
                ('processed_images', settings.paths.processed_images_dir)
            ]:
                if path_obj.exists():
                    size = await self._calculate_directory_size(path_obj)
                    file_count = await self._count_files_in_directory(path_obj)
                    metrics[f'local_{path_name}'] = {
                        'size_bytes': size,
                        'file_count': file_count
                    }
                else:
                    metrics[f'local_{path_name}'] = {'size_bytes': 0, 'file_count': 0}
            
            # Add timestamp
            metrics['timestamp'] = datetime.utcnow().isoformat()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            return {'error': str(e)}
    
    async def _clean_directory_safely(self, directory: Path) -> None:
        """Safely clean a directory using security checks."""
        try:
            # Use secure file manager to remove files
            removed_count = SecureFileManager.safe_remove_files("*", str(directory))
            logger.debug(f"Removed {removed_count} files from {directory}")
            
        except Exception as e:
            logger.error(f"Failed to clean directory {directory}: {e}")
            raise
    
    async def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory contents."""
        try:
            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to calculate directory size: {e}")
            return 0
    
    async def _count_files_in_directory(self, directory: Path) -> int:
        """Count number of files in directory."""
        try:
            count = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    count += 1
            return count
            
        except Exception as e:
            logger.error(f"Failed to count files in directory: {e}")
            return 0