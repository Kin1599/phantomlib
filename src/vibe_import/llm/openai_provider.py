"""
OpenAI LLM provider implementation.
"""

import os
from typing import Any

from vibe_import.llm.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for code generation."""
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self._api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set it via OPENAI_API_KEY environment variable or pass api_key parameter.\n"
                "Get your API key at: https://platform.openai.com/api-keys"
            )
        
        self._base_url = base_url
        self._client: Any = None
        self._async_client: Any = None
        super().__init__(api_key=self._api_key, model=model)
    
    @property
    def default_model(self) -> str:
        return "gpt-4o"
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def _get_client(self) -> Any:
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI package is required. Install it with: pip install openai"
                )
            
            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self._base_url:
                kwargs["base_url"] = self._base_url
            
            self._client = OpenAI(**kwargs)
        
        return self._client
    
    def _get_async_client(self) -> Any:
        """Get or create the async OpenAI client."""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI package is required. Install it with: pip install openai"
                )
            
            kwargs: dict[str, Any] = {}
            if self._api_key:
                kwargs["api_key"] = self._api_key
            if self._base_url:
                kwargs["base_url"] = self._base_url
            
            self._async_client = AsyncOpenAI(**kwargs)
        
        return self._async_client
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using OpenAI's API (async)."""
        client = self._get_async_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
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
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response using OpenAI's API (sync)."""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
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