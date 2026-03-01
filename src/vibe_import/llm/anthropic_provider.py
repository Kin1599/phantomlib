"""
Anthropic LLM provider implementation.
"""

import os
from typing import Any

from vibe_import.llm.base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic API provider for code generation."""
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self._api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set it via ANTHROPIC_API_KEY environment variable or pass api_key parameter.\n"
                "Get your API key at: https://console.anthropic.com/settings/keys"
            )
        
        self._client: Any = None
        self._async_client: Any = None
        super().__init__(api_key=self._api_key, model=model)
    
    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    def _get_client(self) -> Any:
        """Get or create the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "Anthropic package is required. Install it with: pip install anthropic"
                )
            
            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            
            self._client = Anthropic(**kwargs)
        
        return self._client
    
    def _get_async_client(self) -> Any:
        """Get or create the async Anthropic client."""
        if self._async_client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError(
                    "Anthropic package is required. Install it with: pip install anthropic"
                )
            
            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            
            self._async_client = AsyncAnthropic(**kwargs)
        
        return self._async_client
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using Anthropic's API (async)."""
        client = self._get_async_client()
        
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        # Anthropic uses 0-1 scale for temperature
        if temperature > 0:
            kwargs["temperature"] = temperature
        
        response = await client.messages.create(**kwargs)
        
        content = ""
        if response.content:
            content = response.content[0].text
        
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            raw_response=response,
        )
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using Anthropic's API (sync)."""
        client = self._get_client()
        
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        if temperature > 0:
            kwargs["temperature"] = temperature
        
        response = client.messages.create(**kwargs)
        
        content = ""
        if response.content:
            content = response.content[0].text
        
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }
        
        return LLMResponse(
            content=content,
            model=response.model,
            usage=usage,
            raw_response=response,
        )