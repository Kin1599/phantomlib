"""
Factory for creating LLM providers.
"""

from vibe_import.llm.base import LLMProvider
from vibe_import.llm.openai_provider import OpenAIProvider
from vibe_import.llm.anthropic_provider import AnthropicProvider
from vibe_import.llm.openrouter_provider import OpenRouterProvider


def create_provider(
    provider: str = "openrouter",
    api_key: str | None = None,
    model: str | None = None,
    **kwargs,
) -> LLMProvider:
    """
    Create an LLM provider instance.
    
    Args:
        provider: Provider name ("openai", "anthropic", or "openrouter")
        api_key: API key for the provider
        model: Model name to use
        **kwargs: Additional provider-specific arguments
        
    Returns:
        LLMProvider instance
        
    Raises:
        ValueError: If provider is not supported
        
    Examples:
        # Use OpenRouter with free model (default)
        provider = create_provider()
        
        # Use OpenRouter with specific model
        provider = create_provider("openrouter", model="google/gemma-2-9b-it:free")
        
        # Use OpenAI
        provider = create_provider("openai", api_key="sk-...")
    """
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "openrouter": OpenRouterProvider,
    }
    
    provider_lower = provider.lower()
    
    if provider_lower not in providers:
        available = ", ".join(providers.keys())
        raise ValueError(
            f"Unknown provider: {provider}. Available providers: {available}"
        )
    
    provider_class = providers[provider_lower]
    return provider_class(api_key=api_key, model=model, **kwargs)


def list_free_models() -> list[str]:
    """List available free models from OpenRouter."""
    return OpenRouterProvider.list_free_models()