"""Content generation service implementation."""

import uuid
from typing import List, Optional
from datetime import datetime

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from core.models.content import ContentRequest, ContentItem, PromptData, CaptionData, LocationData
from core.models.processing import StableDiffusionConfig
from core.exceptions import ContentGenerationError, PromptGenerationError, CaptionGenerationError
from infrastructure.apis.openai_client import OpenAIClient
from infrastructure.apis.stable_diffusion_client import StableDiffusionClient

logger = get_logger(__name__)


class ContentGenerationService:
    """Service for generating AI-powered content including prompts and captions."""
    
    def __init__(
        self,
        openai_client: OpenAIClient,
        stable_diffusion_client: StableDiffusionClient
    ):
        """Initialize content generation service.
        
        Args:
            openai_client: OpenAI API client for text generation
            stable_diffusion_client: Stable Diffusion client for image generation
        """
        self.openai_client = openai_client
        self.stable_diffusion_client = stable_diffusion_client
    
    async def generate_content_batch(self, request: ContentRequest) -> List[ContentItem]:
        """Generate a batch of content items based on request.
        
        Args:
            request: Content generation request
            
        Returns:
            List of generated content items
            
        Raises:
            ContentGenerationError: If content generation fails
        """
        with PerformanceLogger(logger, f"generate_content_batch({request.content_type})"):
            try:
                # Generate group ID for related content
                group_id = uuid.uuid4()
                content_items = []
                
                # Generate prompts for the location
                prompts = await self._generate_location_prompts(
                    location=request.location,
                    content_type=request.content_type,
                    count=request.count,
                    style=request.style
                )
                
                # Create content items
                for i, prompt_text in enumerate(prompts):
                    prompt_data = PromptData(
                        text=prompt_text,
                        location=request.location,
                        content_type=request.content_type
                    )
                    
                    content_item = ContentItem(
                        index=0,  # Will be set by repository
                        content_type=request.content_type,
                        group_id=group_id,
                        prompt=prompt_data,
                        location=request.location,
                        seed=request.seed
                    )
                    
                    content_items.append(content_item)
                
                logger.info(
                    f"Generated {len(content_items)} content items",
                    extra={
                        'content_type': request.content_type,
                        'location': request.location.name,
                        'count': len(content_items)
                    }
                )
                
                return content_items
                
            except Exception as e:
                logger.error(
                    f"Content generation failed: {e}",
                    extra={'request': request.dict()},
                    exc_info=True
                )
                raise ContentGenerationError(
                    f"Failed to generate content: {e}",
                    content_type=request.content_type.value,
                    context={'location': request.location.name}
                )
    
    async def _generate_location_prompts(
        self,
        location: LocationData,
        content_type: str,
        count: int = 4,
        style: Optional[str] = None
    ) -> List[str]:
        """Generate prompts for a specific location.
        
        Args:
            location: Location data
            content_type: Type of content (posts/story)
            count: Number of prompts to generate
            style: Optional style modifier
            
        Returns:
            List of generated prompts
            
        Raises:
            PromptGenerationError: If prompt generation fails
        """
        try:
            if content_type == "posts":
                return await self._generate_post_prompts(location, count, style)
            else:
                return await self._generate_story_prompts(location, count)
                
        except Exception as e:
            raise PromptGenerationError(
                f"Failed to generate prompts for {location.name}: {e}",
                location=location.name
            )
    
    async def _generate_post_prompts(
        self,
        location: LocationData,
        count: int = 4,
        style: Optional[str] = None
    ) -> List[str]:
        """Generate Instagram post prompts."""
        prompt = f"""Fashion and lifestyle influencer traveling to {location.full_name}, give me {count} list of places to go wearing different 
        stylish clothes to wear, describe it in details. describe background in details. as a prompt you give to stable 
        diffusion, describe the background, scene in as much details as you can, use the following format "Place Name: ... 
        Description: ..." """
        
        if style:
            prompt += f"\n\nStyle preference: {style}"
        
        response = await self.openai_client.generate_completion(
            prompt=prompt,
            system_message="You are instagram influencer and prompt engineer. Respond in third person in the list which was asked, nothing else.",
            temperature=0.9
        )
        
        return self._parse_post_prompts(response, location)
    
    async def _generate_story_prompts(
        self,
        location: LocationData,
        count: int = 2
    ) -> List[str]:
        """Generate Instagram story prompts."""
        prompt = f"Give me {count} prompts describing the beauty of {location.full_name}. Doing different activity, Be very descriptive for background."
        
        response = await self.openai_client.generate_completion(
            prompt=prompt,
            system_message="You are instagram influencer and prompt engineer",
            temperature=0.71,
            max_tokens=400
        )
        
        return self._parse_story_prompts(response)
    
    def _parse_post_prompts(self, response_text: str, location: LocationData) -> List[str]:
        """Parse post prompts from OpenAI response."""
        final_prompts = []
        starting_prompt = "a beautiful and cute aashvi-500, single girl,"
        ending_prompt = "long haircut, light skin, (high detailed skin:1.3), 8k UHD DSLR, bokeh effect, soft lighting, high quality"
        
        current_location = ""
        
        for line in response_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            if "Place Name" in line:
                _, current_location = line.split(":", 1)
                current_location = current_location.strip()
            elif "Description" in line:
                _, description = line.split(":", 1)
                description = description.strip()
                
                full_prompt = f"{starting_prompt} at {current_location}, {description}, {ending_prompt}"
                final_prompts.append(full_prompt)
        
        return final_prompts
    
    def _parse_story_prompts(self, response_text: str) -> List[str]:
        """Parse story prompts from OpenAI response."""
        final_prompts = []
        
        for line in response_text.split("\n"):
            line = line.strip()
            if line and not line.startswith(("1.", "2.", "3.", "4.")):
                # Remove numbering if present
                if "." in line[:5]:
                    line = line[line.find(".") + 1:].strip()
                final_prompts.append(line)
        
        return final_prompts[:2]  # Limit to 2 for stories
    
    async def generate_caption(
        self,
        content_item: ContentItem,
        background: Optional[str] = None
    ) -> CaptionData:
        """Generate caption for content item.
        
        Args:
            content_item: Content item to generate caption for
            background: Optional background description
            
        Returns:
            Generated caption data
            
        Raises:
            CaptionGenerationError: If caption generation fails
        """
        try:
            if content_item.content_type.value == "posts":
                return await self._generate_post_caption(content_item, background)
            else:
                return await self._generate_story_caption(content_item, background)
                
        except Exception as e:
            raise CaptionGenerationError(f"Failed to generate caption: {e}")
    
    async def _generate_post_caption(
        self,
        content_item: ContentItem,
        background: Optional[str] = None
    ) -> CaptionData:
        """Generate Instagram post caption."""
        location_name = background or content_item.location.name
        
        prompt = f"generate a instagram caption for this prompt 'a beautiful woman at a {location_name} background.' it should be creative, cute and funny. Feel Good. Use Emojis. In first person. Also add relevant hashtags."
        
        response = await self.openai_client.generate_completion(
            prompt=prompt,
            system_message="",
            temperature=0.7
        )
        
        # Parse caption and hashtags
        caption_text = response.replace('"', "").strip()
        
        # Extract hashtags
        hashtags = []
        if '#' in caption_text:
            hashtag_part = caption_text[caption_text.find('#'):]
            hashtags = [tag.strip() for tag in hashtag_part.split() if tag.startswith('#')]
            caption_text = caption_text[:caption_text.find('#')].strip()
        
        return CaptionData(
            text=caption_text,
            hashtags=hashtags,
            mentions=settings.instagram.default_mentions
        )
    
    async def _generate_story_caption(
        self,
        content_item: ContentItem,
        background: Optional[str] = None
    ) -> CaptionData:
        """Generate Instagram story caption."""
        location_name = background or content_item.location.name
        
        prompt = f"generate a instagram story caption for the scene of {location_name} it should be creative, cute and funny. Feel Good. Use Emojis. In first person. Also add relevant hashtags. keep it only to few words"
        
        response = await self.openai_client.generate_completion(
            prompt=prompt,
            system_message="",
            temperature=0.7
        )
        
        caption_text = response.replace('"', "").strip()
        
        return CaptionData(
            text=caption_text,
            hashtags=[],  # Stories typically have fewer hashtags
            mentions=[]
        )
    
    async def get_random_travel_location(self) -> LocationData:
        """Get a random travel location for content generation.
        
        Returns:
            Random location data
        """
        try:
            # This would ideally use a location API
            # For now, using a simple implementation
            import requests
            import json
            import random
            
            response = requests.get("https://www.randomlists.com/data/world-cities-3.json")
            cities_data = json.loads(response.text)["RandL"]["items"]
            city = random.choice(cities_data)
            
            return LocationData(
                name=city["name"],
                country=city["detail"]
            )
            
        except Exception as e:
            logger.warning(f"Failed to get random location, using default: {e}")
            return LocationData(name="Paris", country="France")