"""
Base classes for LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any = None
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.usage.get("total_tokens", 0)


@dataclass
class GenerationRequest:
    """Request for code generation."""
    module_name: str
    specification: str  # The module spec as a string
    context: str = ""  # Additional context (e.g., original source code)
    style_guide: str = ""  # Style preferences
    
    def to_prompt(self) -> str:
        """Convert to a prompt string."""
        parts = [
            "Generate a Python module based on the following specification.",
            "",
            "## Module Specification",
            self.specification,
        ]
        
        if self.context:
            parts.extend([
                "",
                "## Usage Context",
                "The module will be used in code like this:",
                self.context,
            ])
        
        if self.style_guide:
            parts.extend([
                "",
                "## Style Guide",
                self.style_guide,
            ])
        
        parts.extend([
            "",
            "## Requirements",
            "1. Generate complete, working Python code",
            "2. Include comprehensive docstrings (Google style)",
            "3. Add type hints to all functions and methods",
            "4. Handle edge cases and errors appropriately",
            "5. Follow PEP 8 style guidelines",
            "6. Make the code production-ready",
            "",
            "## Output Format",
            "Provide the code in a markdown code block with the filename as a comment at the top.",
            "If multiple files are needed, provide each in a separate code block.",
            "",
            "Example:",
            "```python",
            "# filename: module_name/__init__.py",
            "...",
            "```",
        ])
        
        return "\n".join(parts)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.default_model
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Get the default model for this provider."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            LLMResponse with the generated content
        """
        pass
    
    @abstractmethod
    def generate_sync(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Synchronous version of generate.
        """
        pass
    
    def generate_code(
        self,
        request: GenerationRequest,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """
        Generate code based on a generation request.
        
        Args:
            request: The generation request with specifications
            temperature: Sampling temperature
            
        Returns:
            LLMResponse with generated code
        """
        system_prompt = self._get_code_generation_system_prompt()
        prompt = request.to_prompt()
        
        return self.generate_sync(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=8192,  # Allow longer responses for code
        )
    
    def _get_code_generation_system_prompt(self) -> str:
        """Get the system prompt for code generation."""
        return """You are an expert Python developer tasked with generating high-quality Python packages.

Your code should be:
- Clean, readable, and well-documented
- Following PEP 8 style guidelines
- Using modern Python features (3.10+)
- Including comprehensive type hints
- Production-ready with proper error handling

When generating code:
1. Create a proper package structure with __init__.py
2. Include docstrings for all public functions, classes, and methods
3. Add type hints to all function signatures
4. Handle edge cases and potential errors
5. Use descriptive variable and function names
6. Keep functions focused and single-purpose

Output only the code in markdown code blocks with filenames as comments."""