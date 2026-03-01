"""
LLM Integration module for Vibe-Import.

This module provides interfaces to various LLM providers for generating
package code based on extracted specifications.

Supported providers:
- OpenRouter (default, has free models)
- OpenAI
- Anthropic
"""

from vibe_import.llm.base import LLMProvider, LLMResponse
from vibe_import.llm.openai_provider import OpenAIProvider
from vibe_import.llm.anthropic_provider import AnthropicProvider
from vibe_import.llm.openrouter_provider import OpenRouterProvider
from vibe_import.llm.factory import create_provider, list_free_models

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "OpenAIProvider",
    "AnthropicProvider",
    "OpenRouterProvider",
    "create_provider",
    "list_free_models",
]