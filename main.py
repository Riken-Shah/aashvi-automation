"""
Main entry point for the refactored Aashvi Automation.
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from config.logging_config import get_logger, setup_logging
from config.settings import settings
from config.credentials import validate_startup_credentials
from core.services.content_service import ContentGenerationService
from core.services.image_service import ImageProcessingService
from core.services.notification_service import NotificationService
from core.repositories.content_repository import ContentRepository
from core.repositories.config_repository import ConfigRepository
from infrastructure.apis.openai_client import OpenAIClient
from infrastructure.apis.stable_diffusion_client import StableDiffusionClient
from application.workflows.content_workflow import ContentGenerationWorkflow

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def create_application() -> AsyncGenerator[ContentGenerationWorkflow, None]:
    """Create and configure the application with dependency injection.
    
    Yields:
        Configured content generation workflow
    """
    logger.info("Initializing Aashvi automation system...")
    
    try:
        # Validate credentials at startup
        validate_startup_credentials()
        logger.info("✅ Credentials validated")
        
        # Initialize repositories
        config_repo = ConfigRepository()
        # Note: Content repository would need Google Sheets client
        # content_repo = ContentRepository(sheets_client)
        
        # Initialize API clients
        openai_client = OpenAIClient()
        sd_client = StableDiffusionClient(config_repo)
        
        # Validate API connections
        if await openai_client.validate_connection():
            logger.info("✅ OpenAI API connection validated")
        else:
            logger.warning("⚠️ OpenAI API connection failed")
        
        # Initialize services
        # Note: These would need proper clients injected
        # content_service = ContentGenerationService(openai_client, sd_client)
        # image_service = ImageProcessingService(sd_client, storage_service)
        # notification_service = NotificationService(telegram_client)
        
        # Initialize workflow
        # workflow = ContentGenerationWorkflow(
        #     content_service=content_service,
        #     image_service=image_service,
        #     notification_service=notification_service,
        #     content_repository=content_repo,
        #     config_repository=config_repo
        # )
        
        logger.info("🚀 Application initialized successfully")
        
        # For now, create a placeholder workflow
        workflow = None  # Would be the actual workflow
        
        yield workflow
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}", exc_info=True)
        raise
    finally:
        # Cleanup resources
        logger.info("🧹 Cleaning up application resources...")
        try:
            await sd_client.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def run_content_generation():
    """Run the content generation workflow."""
    async with create_application() as workflow:
        if workflow is None:
            logger.error("❌ Workflow not properly initialized")
            return False
        
        try:
            success = await workflow.run_full_content_generation()
            
            if success:
                logger.info("✅ Content generation completed successfully")
            else:
                logger.error("❌ Content generation failed")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Content generation workflow error: {e}", exc_info=True)
            return False


async def run_image_processing():
    """Run the image processing workflow."""
    async with create_application() as workflow:
        if workflow is None:
            logger.error("❌ Workflow not properly initialized")
            return False
        
        try:
            # This would run the image processing workflow
            logger.info("🎨 Starting image processing workflow...")
            
            # Placeholder for actual implementation
            await asyncio.sleep(1)
            
            logger.info("✅ Image processing completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Image processing workflow error: {e}", exc_info=True)
            return False


async def run_posting_workflow():
    """Run the Instagram posting workflow."""
    async with create_application() as workflow:
        if workflow is None:
            logger.error("❌ Workflow not properly initialized")
            return False
        
        try:
            logger.info("📱 Starting Instagram posting workflow...")
            
            # Placeholder for actual implementation
            await asyncio.sleep(1)
            
            logger.info("✅ Instagram posting completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Instagram posting workflow error: {e}", exc_info=True)
            return False


async def main():
    """Main application entry point."""
    logger.info("🌟 Starting Aashvi Automation System")
    logger.info(f"Environment: {settings.app.environment}")
    logger.info(f"Debug mode: {settings.app.debug}")
    
    try:
        # For now, just run content generation
        # In a full implementation, this would handle command line arguments
        # or run different workflows based on configuration
        
        success = await run_content_generation()
        
        if success:
            logger.info("🎉 Application completed successfully")
            sys.exit(0)
        else:
            logger.error("💥 Application completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Unexpected application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Set up asyncio for Python 3.7+
    if sys.version_info >= (3, 7):
        asyncio.run(main())
    else:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()