"""
Configuration management for Vibe-Import.

This module handles loading and saving configuration from various sources:
- Configuration files (vibe-import.toml, pyproject.toml)
- Environment variables
- .env file
- Command-line arguments
"""

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


CONFIG_FILE_NAMES = [
    "vibe-import.toml",
    ".vibe-import.toml",
]


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openrouter"  # Default to openrouter (has free models)
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 8192
    base_url: Optional[str] = None  # For custom endpoints
    
    def __post_init__(self):
        # Load API key from environment if not set
        if self.api_key is None:
            if self.provider == "openai":
                self.api_key = os.environ.get("OPENAI_API_KEY")
            elif self.provider == "anthropic":
                self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            elif self.provider == "openrouter":
                self.api_key = os.environ.get("OPENROUTER_API_KEY")


@dataclass
class OutputConfig:
    """Output configuration."""
    directory: str = "."
    include_docs: bool = True
    include_tests: bool = False
    docstring_style: str = "google"  # google, numpy, sphinx
    overwrite: bool = False


@dataclass
class AnalysisConfig:
    """Code analysis configuration."""
    recursive: bool = True
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "**/venv/**",
        "**/.venv/**",
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/.*/**",
    ])
    include_stdlib: bool = False  # Whether to analyze stdlib imports


@dataclass
class Config:
    """Main configuration class."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from file and environment.
        
        Args:
            config_path: Optional explicit path to config file
            
        Returns:
            Config instance
        """
        config_data: dict[str, Any] = {}
        
        # Try to find config file
        if config_path:
            if config_path.exists():
                config_data = cls._load_toml(config_path)
        else:
            # Search for config file
            for name in CONFIG_FILE_NAMES:
                path = Path(name)
                if path.exists():
                    config_data = cls._load_toml(path)
                    break
            
            # Also check pyproject.toml
            if not config_data:
                pyproject = Path("pyproject.toml")
                if pyproject.exists():
                    data = cls._load_toml(pyproject)
                    config_data = data.get("tool", {}).get("vibe-import", {})
        
        # Create config from data
        return cls._from_dict(config_data)
    
    @classmethod
    def _load_toml(cls, path: Path) -> dict[str, Any]:
        """Load a TOML file."""
        with open(path, "rb") as f:
            return tomllib.load(f)
    
    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        llm_data = data.get("llm", {})
        output_data = data.get("output", {})
        analysis_data = data.get("analysis", {})
        
        return cls(
            llm=LLMConfig(**llm_data) if llm_data else LLMConfig(),
            output=OutputConfig(**output_data) if output_data else OutputConfig(),
            analysis=AnalysisConfig(**analysis_data) if analysis_data else AnalysisConfig(),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "llm": asdict(self.llm),
            "output": asdict(self.output),
            "analysis": asdict(self.analysis),
        }
    
    def save(self, path: Path) -> None:
        """
        Save configuration to a TOML file.
        
        Args:
            path: Path to save to
        """
        try:
            import tomli_w
        except ImportError:
            raise ImportError(
                "tomli_w is required to save config. Install with: pip install tomli-w"
            )
        
        with open(path, "wb") as f:
            tomli_w.dump(self.to_dict(), f)
    
    def merge_cli_args(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        output_dir: Optional[str] = None,
        no_docs: bool = False,
        recursive: Optional[bool] = None,
    ) -> "Config":
        """
        Merge CLI arguments into config (CLI takes precedence).
        
        Returns:
            New Config instance with merged values
        """
        # Create copies of sub-configs
        llm = LLMConfig(
            provider=provider or self.llm.provider,
            model=model or self.llm.model,
            api_key=api_key or self.llm.api_key,
            temperature=temperature if temperature is not None else self.llm.temperature,
            max_tokens=self.llm.max_tokens,
            base_url=self.llm.base_url,
        )
        
        output = OutputConfig(
            directory=output_dir or self.output.directory,
            include_docs=not no_docs and self.output.include_docs,
            include_tests=self.output.include_tests,
            docstring_style=self.output.docstring_style,
            overwrite=self.output.overwrite,
        )
        
        analysis = AnalysisConfig(
            recursive=recursive if recursive is not None else self.analysis.recursive,
            exclude_patterns=self.analysis.exclude_patterns,
            include_stdlib=self.analysis.include_stdlib,
        )
        
        return Config(llm=llm, output=output, analysis=analysis)


def get_default_config() -> Config:
    """Get the default configuration."""
    return Config()


def generate_sample_config() -> str:
    """Generate a sample configuration file content."""
    return '''# Vibe-Import Configuration
# Save as vibe-import.toml or add to pyproject.toml under [tool.vibe-import]

[llm]
# LLM provider: "openai" or "anthropic"
provider = "openai"

# Model name (optional, uses provider default if not set)
# model = "gpt-4o"

# API key (optional, can also use environment variables)
# api_key = "sk-..."

# Generation temperature (0-1, lower = more deterministic)
temperature = 0.2

# Maximum tokens in response
max_tokens = 8192

# Custom API endpoint (optional)
# base_url = "https://api.example.com/v1"

[output]
# Output directory for generated packages
directory = "."

# Include documentation (README.md)
include_docs = true

# Include test files
include_tests = false

# Docstring style: "google", "numpy", or "sphinx"
docstring_style = "google"

# Overwrite existing files
overwrite = false

[analysis]
# Recursively analyze directories
recursive = true

# Patterns to exclude from analysis
exclude_patterns = [
    "**/venv/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/__pycache__/**",
    "**/.*/**",
]

# Include standard library imports in analysis
include_stdlib = false
'''