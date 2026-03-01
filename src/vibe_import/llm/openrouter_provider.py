"""
OpenRouter LLM provider implementation.

OpenRouter provides access to many models including free ones.
Get your API key at: https://openrouter.ai/keys
"""

import asyncio
import os
import time
from typing import Any

from vibe_import.llm.base import LLMProvider, LLMResponse


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter API provider for code generation.
    
    OpenRouter provides access to many models, including free options:
    - meta-llama/llama-3.2-3b-instruct:free (free)
    - google/gemma-2-9b-it:free (free)
    - mistralai/mistral-7b-instruct:free (free)
    - And many paid models like GPT-4, Claude, etc.
    
    Get your API key at: https://openrouter.ai/keys
    """
    
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Free models available on OpenRouter
    FREE_MODELS = [
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-2-9b-it:free", 
        "mistralai/mistral-7b-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "openchat/openchat-7b:free",
        "qwen/qwen3-coder:free",
    ]
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        site_url: str | None = None,
        site_name: str | None = None,
        max_retries: int = 5,
        retry_delay: float = 2.0,
    ):
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        
        if not self._api_key:
            raise ValueError(
                "OpenRouter API key is required. "
                "Set it via OPENROUTER_API_KEY environment variable or pass api_key parameter.\n"
                "Get your free API key at: https://openrouter.ai/keys"
            )
        
        self._site_url = site_url or "https://github.com/vibe-import/vibe-import"
        self._site_name = site_name or "Vibe-Import"
        self._client: Any = None
        self._async_client: Any = None
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        super().__init__(api_key=self._api_key, model=model)
    
    @property
    def default_model(self) -> str:
        # Use a free model by default
        return "qwen/qwen3-coder:free"
    
    @property
    def provider_name(self) -> str:
        return "openrouter"
    
    def _get_client(self) -> Any:
        """Get or create the OpenRouter client (uses OpenAI SDK)."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI package is required for OpenRouter. Install it with: pip install openai"
                )
            
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self.OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": self._site_url,
                    "X-Title": self._site_name,
                }
            )
        
        return self._client
    
    def _get_async_client(self) -> Any:
        """Get or create the async OpenRouter client."""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI package is required for OpenRouter. Install it with: pip install openai"
                )
            
            self._async_client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self.OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": self._site_url,
                    "X-Title": self._site_name,
                }
            )
        
        return self._async_client
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using OpenRouter's API (async) with retry on rate limit."""
        client = self._get_async_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        last_error = None
        for attempt in range(self._max_retries):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                content = response.choices[0].message.content or ""
                usage = {}
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                
                return LLMResponse(
                    content=content,
                    model=response.model,
                    usage=usage,
                    raw_response=response,
                )
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check for rate limit error (429)
                if "429" in error_str or "rate limit" in error_str.lower():
                    if attempt < self._max_retries - 1:
                        # Exponential backoff
                        delay = self._retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                
                # For other errors, don't retry
                raise
        
        # If we exhausted retries
        raise RuntimeError(
            f"Max retries ({self._max_retries}) exceeded. Last error: {last_error}"
        ) from last_error
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using OpenRouter's API (sync) with retry on rate limit."""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        last_error = None
        for attempt in range(self._max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                content = response.choices[0].message.content or ""
                usage = {}
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                
                return LLMResponse(
                    content=content,
                    model=response.model,
                    usage=usage,
                    raw_response=response,
                )
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Check for rate limit error (429)
                if "429" in error_str or "rate limit" in error_str.lower():
                    if attempt < self._max_retries - 1:
                        # Exponential backoff
                        delay = self._retry_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                
                # For other errors, don't retry
                raise
        
        # If we exhausted retries
        raise RuntimeError(
            f"Max retries ({self._max_retries}) exceeded. Last error: {last_error}"
        ) from last_error
    
    @classmethod
    def list_free_models(cls) -> list[str]:
        """List available free models."""
        return cls.FREE_MODELS.copy()