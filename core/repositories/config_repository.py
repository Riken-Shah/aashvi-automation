"""Repository for configuration data persistence."""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from config.logging_config import get_logger
from config.settings import settings
from config.credentials import SecureFileManager
from core.models.content import LocationData
from core.exceptions import FileNotFoundError, FileAccessError, ValidationError

logger = get_logger(__name__)


class ConfigRepository:
    """Repository for managing configuration files and persistent settings."""
    
    def __init__(self):
        """Initialize config repository."""
        self.base_path = settings.paths.base_dir
    
    async def get_current_location(self) -> LocationData:
        """Get the current travel location.
        
        Returns:
            Current location data
            
        Raises:
            FileNotFoundError: If location file doesn't exist
            ValidationError: If location data is invalid
        """
        try:
            location_file = settings.paths.location_file
            
            if not location_file.exists():
                # Create default location file
                await self.set_current_location(LocationData(name="Paris", country="France"))
                
            content = SecureFileManager.safe_file_read(str(location_file))
            location_name = content.strip()
            
            if not location_name:
                raise ValidationError("Location file is empty")
            
            # Parse location (handle "City, Country" format)
            if ',' in location_name:
                parts = location_name.split(',', 1)
                name = parts[0].strip()
                country = parts[1].strip()
            else:
                name = location_name
                country = None
            
            location = LocationData(name=name, country=country)
            
            logger.debug(f"Retrieved current location: {location.full_name}")
            return location
            
        except Exception as e:
            logger.error(f"Failed to get current location: {e}")
            raise FileNotFoundError(str(settings.paths.location_file))
    
    async def set_current_location(self, location: LocationData) -> None:
        """Set the current travel location.
        
        Args:
            location: Location data to set
            
        Raises:
            FileAccessError: If unable to write location file
            ValidationError: If location data is invalid
        """
        try:
            if not location.name:
                raise ValidationError("Location name cannot be empty")
            
            location_file = settings.paths.location_file
            
            # Write location to file
            SecureFileManager.safe_file_write(
                str(location_file),
                location.full_name,
                create_dirs=True
            )
            
            logger.info(f"Set current location to: {location.full_name}")
            
        except Exception as e:
            logger.error(f"Failed to set current location: {e}")
            raise FileAccessError(str(settings.paths.location_file), "write")
    
    async def get_stable_diffusion_url(self) -> Optional[str]:
        """Get the Stable Diffusion API URL.
        
        Returns:
            API URL if available, None otherwise
        """
        try:
            url_file = self.base_path / settings.ai.automatic1111_url_file
            
            if not url_file.exists():
                logger.debug("Stable Diffusion URL file not found")
                return None
            
            content = SecureFileManager.safe_file_read(str(url_file))
            url = content.strip()
            
            if not url:
                return None
            
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                logger.warning(f"Invalid URL format in config file: {url}")
                return None
            
            logger.debug(f"Retrieved Stable Diffusion URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to get Stable Diffusion URL: {e}")
            return None
    
    async def set_stable_diffusion_url(self, url: str) -> None:
        """Set the Stable Diffusion API URL.
        
        Args:
            url: API URL to set
            
        Raises:
            ValidationError: If URL format is invalid
            FileAccessError: If unable to write URL file
        """
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                raise ValidationError(f"Invalid URL format: {url}")
            
            url_file = self.base_path / settings.ai.automatic1111_url_file
            
            SecureFileManager.safe_file_write(
                str(url_file),
                url,
                create_dirs=True
            )
            
            logger.info(f"Set Stable Diffusion URL: {url}")
            
        except Exception as e:
            logger.error(f"Failed to set Stable Diffusion URL: {e}")
            raise FileAccessError(str(url_file), "write")
    
    async def is_process_running(self) -> bool:
        """Check if automation process is currently running.
        
        Returns:
            True if process is running
        """
        try:
            lock_file = settings.paths.running_lock_file
            
            if not lock_file.exists():
                return False
            
            content = SecureFileManager.safe_file_read(str(lock_file))
            status = content.strip().lower()
            
            return status == "yep"
            
        except Exception as e:
            logger.error(f"Failed to check process status: {e}")
            return False
    
    async def set_process_running(self, is_running: bool) -> None:
        """Set the process running status.
        
        Args:
            is_running: Whether process is currently running
            
        Raises:
            FileAccessError: If unable to write lock file
        """
        try:
            lock_file = settings.paths.running_lock_file
            
            status = "yep" if is_running else "nope"
            
            SecureFileManager.safe_file_write(
                str(lock_file),
                status,
                create_dirs=True
            )
            
            logger.debug(f"Set process running status: {is_running}")
            
        except Exception as e:
            logger.error(f"Failed to set process status: {e}")
            raise FileAccessError(str(lock_file), "write")
    
    async def get_application_state(self) -> Dict[str, Any]:
        """Get current application state information.
        
        Returns:
            Dictionary with application state data
        """
        try:
            state = {
                'current_location': None,
                'stable_diffusion_url': None,
                'process_running': False,
                'last_updated': datetime.utcnow().isoformat(),
                'config_files_exist': {}
            }
            
            # Get current location
            try:
                location = await self.get_current_location()
                state['current_location'] = location.dict()
            except Exception:
                pass
            
            # Get Stable Diffusion URL
            state['stable_diffusion_url'] = await self.get_stable_diffusion_url()
            
            # Check process status
            state['process_running'] = await self.is_process_running()
            
            # Check config file existence
            config_files = {
                'location_file': settings.paths.location_file,
                'url_file': self.base_path / settings.ai.automatic1111_url_file,
                'lock_file': settings.paths.running_lock_file,
                'credentials_file': Path(settings.database.google_credentials_path)
            }
            
            for name, file_path in config_files.items():
                state['config_files_exist'][name] = file_path.exists()
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to get application state: {e}")
            return {'error': str(e)}
    
    async def backup_config_files(self, backup_path: Optional[str] = None) -> Dict[str, str]:
        """Create backup of important configuration files.
        
        Args:
            backup_path: Optional custom backup path
            
        Returns:
            Dictionary mapping file names to backup paths
        """
        try:
            if backup_path is None:
                backup_dir = self.base_path / "backups" / f"config_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            else:
                backup_dir = Path(backup_path)
            
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Files to backup
            files_to_backup = {
                'location.txt': settings.paths.location_file,
                'automatic1111_url.txt': self.base_path / settings.ai.automatic1111_url_file,
                'is_running.txt': settings.paths.running_lock_file
            }
            
            backed_up = {}
            
            for backup_name, source_file in files_to_backup.items():
                if source_file.exists():
                    backup_file = backup_dir / backup_name
                    
                    # Copy file content securely
                    try:
                        content = SecureFileManager.safe_file_read(str(source_file))
                        SecureFileManager.safe_file_write(str(backup_file), content)
                        backed_up[backup_name] = str(backup_file)
                        
                    except Exception as e:
                        logger.warning(f"Failed to backup {source_file}: {e}")
                        continue
            
            logger.info(f"Backed up {len(backed_up)} config files to {backup_dir}")
            return backed_up
            
        except Exception as e:
            logger.error(f"Failed to backup config files: {e}")
            return {}
    
    async def restore_config_files(self, backup_path: str) -> Dict[str, bool]:
        """Restore configuration files from backup.
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            Dictionary mapping file names to restore success status
        """
        try:
            backup_dir = Path(backup_path)
            
            if not backup_dir.exists():
                raise FileNotFoundError(f"Backup directory not found: {backup_path}")
            
            # Files to restore
            restore_mapping = {
                'location.txt': settings.paths.location_file,
                'automatic1111_url.txt': self.base_path / settings.ai.automatic1111_url_file,
                'is_running.txt': settings.paths.running_lock_file
            }
            
            restored = {}
            
            for backup_name, target_file in restore_mapping.items():
                backup_file = backup_dir / backup_name
                
                if backup_file.exists():
                    try:
                        content = SecureFileManager.safe_file_read(str(backup_file))
                        SecureFileManager.safe_file_write(str(target_file), content, create_dirs=True)
                        restored[backup_name] = True
                        
                    except Exception as e:
                        logger.error(f"Failed to restore {backup_name}: {e}")
                        restored[backup_name] = False
                else:
                    restored[backup_name] = False
            
            success_count = sum(1 for success in restored.values() if success)
            logger.info(f"Restored {success_count}/{len(restored)} config files from {backup_dir}")
            
            return restored
            
        except Exception as e:
            logger.error(f"Failed to restore config files: {e}")
            return {}
    
    async def validate_config_integrity(self) -> Dict[str, Any]:
        """Validate integrity of configuration files.
        
        Returns:
            Dictionary with validation results
        """
        try:
            validation_results = {
                'overall_status': 'valid',
                'file_checks': {},
                'errors': [],
                'warnings': []
            }
            
            # Check location file
            try:
                location = await self.get_current_location()
                validation_results['file_checks']['location'] = {
                    'exists': True,
                    'valid': True,
                    'value': location.full_name
                }
            except Exception as e:
                validation_results['file_checks']['location'] = {
                    'exists': settings.paths.location_file.exists(),
                    'valid': False,
                    'error': str(e)
                }
                validation_results['errors'].append(f"Location file invalid: {e}")
            
            # Check Stable Diffusion URL
            sd_url = await self.get_stable_diffusion_url()
            url_file_exists = (self.base_path / settings.ai.automatic1111_url_file).exists()
            validation_results['file_checks']['stable_diffusion_url'] = {
                'exists': url_file_exists,
                'valid': sd_url is not None,
                'value': sd_url
            }
            
            if url_file_exists and sd_url is None:
                validation_results['warnings'].append("Stable Diffusion URL file exists but contains invalid URL")
            
            # Check process lock
            lock_exists = settings.paths.running_lock_file.exists()
            is_running = await self.is_process_running()
            validation_results['file_checks']['process_lock'] = {
                'exists': lock_exists,
                'valid': True,  # Lock file format is simple
                'value': 'running' if is_running else 'stopped'
            }
            
            # Check credentials
            cred_path = Path(settings.database.google_credentials_path)
            validation_results['file_checks']['credentials'] = {
                'exists': cred_path.exists(),
                'valid': cred_path.exists(),  # Basic check
                'value': 'present' if cred_path.exists() else 'missing'
            }
            
            if not cred_path.exists():
                validation_results['errors'].append("Google credentials file missing")
            
            # Set overall status
            if validation_results['errors']:
                validation_results['overall_status'] = 'invalid'
            elif validation_results['warnings']:
                validation_results['overall_status'] = 'warning'
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate config integrity: {e}")
            return {
                'overall_status': 'error',
                'error': str(e)
            }