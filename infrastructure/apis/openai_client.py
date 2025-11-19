"""OpenAI API client for content generation."""

import asyncio
from typing import Optional, Dict, Any
import openai

from config.logging_config import get_logger, PerformanceLogger
from config.settings import settings
from core.exceptions import OpenAIError, OpenAIRateLimitError, OpenAIAuthenticationError

logger = get_logger(__name__)


class OpenAIClient:
    """Async client for OpenAI API operations."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        openai.organization = settings.ai.openai_organization
        openai.api_key = settings.ai.openai_api_key
        self._rate_limit_delay = 1.0  # Start with 1 second delay
    
    async def generate_completion(
        self,
        prompt: str,
        system_message: str = "",
        temperature: float = 0.7,
        max_tokens: int = 400,
        model: Optional[str] = None
    ) -> str:
        """Generate text completion using GPT.
        
        Args:
            prompt: User prompt text
            system_message: System message for context
            temperature: Randomness in generation (0-2)
            max_tokens: Maximum tokens to generate
            model: Model to use (defaults to config)
            
        Returns:
            Generated text completion
            
        Raises:
            OpenAIError: If API call fails
            OpenAIRateLimitError: If rate limit exceeded
            OpenAIAuthenticationError: If authentication fails
        """
        with PerformanceLogger(logger, f"openai_completion({len(prompt)} chars)"):
            try:
                if model is None:
                    model = settings.ai.gpt_model
                
                # Apply rate limiting
                await asyncio.sleep(self._rate_limit_delay)
                
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})
                
                response = await self._make_api_call(
                    openai.ChatCompletion.acreate,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Reset rate limit delay on success
                self._rate_limit_delay = max(0.5, self._rate_limit_delay * 0.9)
                
                content = response.choices[0].message["content"]
                
                logger.debug(
                    f"Generated {len(content)} characters of text",
                    extra={
                        'model': model,
                        'prompt_length': len(prompt),
                        'response_length': len(content),
                        'temperature': temperature
                    }
                )
                
                return content.strip()
                
            except openai.error.RateLimitError as e:
                # Exponential backoff on rate limit
                self._rate_limit_delay = min(60.0, self._rate_limit_delay * 2)
                logger.warning(f"OpenAI rate limit hit, backing off to {self._rate_limit_delay}s")
                raise OpenAIRateLimitError(str(e))
                
            except openai.error.AuthenticationError as e:
                logger.error(f"OpenAI authentication failed: {e}")
                raise OpenAIAuthenticationError(str(e))
                
            except openai.error.InvalidRequestError as e:
                logger.error(f"Invalid OpenAI request: {e}")
                raise OpenAIError(f"Invalid request: {e}")
                
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}", exc_info=True)
                raise OpenAIError(f"API call failed: {e}")
    
    async def _make_api_call(self, api_func, **kwargs) -> Any:
        """Make an API call with retry logic.
        
        Args:
            api_func: API function to call
            **kwargs: Arguments for the API function
            
        Returns:
            API response
        """
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Convert sync call to async using asyncio
                return await asyncio.get_event_loop().run_in_executor(
                    None, lambda: api_func(**kwargs)
                )
                
            except openai.error.RateLimitError:
                if attempt == max_retries - 1:
                    raise
                
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                await asyncio.sleep(delay)
                
            except (openai.error.APIError, openai.error.Timeout) as e:
                if attempt == max_retries - 1:
                    raise OpenAIError(f"API error after {max_retries} attempts: {e}")
                
                delay = base_delay * (2 ** attempt)
                logger.warning(f"API error, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
    
    async def validate_connection(self) -> bool:
        """Validate OpenAI API connection and credentials.
        
        Returns:
            True if connection is valid
        """
        try:
            # Simple test call
            await self.generate_completion(
                prompt="Test",
                max_tokens=1,
                temperature=0
            )
            return True
            
        except OpenAIAuthenticationError:
            return False
        except Exception as e:
            logger.warning(f"OpenAI connection validation failed: {e}")
            return False
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics (if available).
        
        Returns:
            Dictionary with usage stats
        """
        try:
            # Note: OpenAI doesn't provide usage stats via API
            # This would need to be tracked internally
            return {
                'current_rate_limit_delay': self._rate_limit_delay,
                'model': settings.ai.gpt_model,
                'organization': settings.ai.openai_organization[:10] + "..." if settings.ai.openai_organization else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get OpenAI usage stats: {e}")
            return {'error': str(e)}