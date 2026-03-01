# Vibe-Import 🚀

**Automatically generate missing Python packages based on how you use them.**

Vibe-Import analyzes your Python code to find imports that don't exist yet, infers what the package should do based on how you use it, and generates a complete implementation using LLM.

## ✨ Features

- **Smart Analysis**: Uses AST parsing to understand how you're using missing imports
- **Type Inference**: Automatically infers parameter types and return types from usage
- **LLM-Powered Generation**: Uses OpenRouter (with free models), OpenAI, or Anthropic
- **Automatic Retry**: Handles rate limits (429 errors) with exponential backoff
- **Documentation**: Automatically generates README and API documentation
- **CLI Interface**: Easy-to-use command-line interface with rich output
- **.env Support**: Configure via environment variables or .env file

## 📦 Installation

```bash
# Using pip
pip install vibe-import

# Or install from source
git clone https://github.com/vibe-import/vibe-import.git
cd vibe-import
pip install -e .
```

## 🚀 Quick Start

### 1. Write code with imports that don't exist yet

```python
# my_app.py
from magic_utils import calculate_magic, MagicProcessor

# Use the functions as if they existed
result = calculate_magic(42, mode="fast")
print(result.value)

processor = MagicProcessor(config={"threads": 4})
processed = processor.process(data=[1, 2, 3])
processor.save("output.json")
```

### 2. Configure API Key

Create a `.env` file in your project:

```bash
# Copy the example
cp .env.example .env

# Edit .env and add your OpenRouter API key
# Get your free key at: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Or set environment variable:

```bash
export OPENROUTER_API_KEY="sk-or-v1-your-key-here"
```

### 3. Run Vibe-Import

```bash
# Analyze your code
vibe-import analyze my_app.py

# Generate the missing packages (uses OpenRouter with free model by default)
vibe-import generate my_app.py --output ./generated
```

### 3. Use the generated package

```python
# The magic_utils package is now available!
from magic_utils import calculate_magic, MagicProcessor

# Everything works as expected
result = calculate_magic(42, mode="fast")
```

## 📖 Usage

### Analyze Code

```bash
# Analyze a single file
vibe-import analyze my_app.py

# Analyze a directory recursively
vibe-import analyze ./src --recursive

# Show detailed usage information
vibe-import analyze my_app.py --show-usage
```

### Generate Packages

```bash
# Generate with OpenRouter (default, has free models)
vibe-import generate my_app.py

# Use a specific free model
vibe-import generate my_app.py --model google/gemma-2-9b-it:free

# Use ANY model from OpenRouter (not just free ones!)
vibe-import generate my_app.py --model meta-llama/llama-3.1-70b-instruct
vibe-import generate my_app.py --model anthropic/claude-3.5-sonnet
vibe-import generate my_app.py --model openai/gpt-4o

# Use OpenAI
vibe-import generate my_app.py --provider openai

# Use Anthropic
vibe-import generate my_app.py --provider anthropic

# Specify output directory
vibe-import generate my_app.py --output ./packages

# Dry run (show what would be generated)
vibe-import generate my_app.py --dry-run

# Skip documentation generation
vibe-import generate my_app.py --no-docs

# Show detailed progress (verbose mode)
vibe-import generate my_app.py --verbose
```

### Speed Up Generation

If generation is taking too long, try:

1. **Use a faster model**
```bash
# Fastest free model
vibe-import generate my_app.py --model meta-llama/llama-3.2-3b-instruct:free

# Or another fast model
vibe-import generate my_app.py --model huggingfaceh4/zephyr-7b-beta:free
```

2. **Use verbose mode to track progress**
```bash
vibe-import generate my_app.py --verbose
```

3. **Check your internet connection** - generation speed depends on API response time

### List Available Models

```bash
# List free models for OpenRouter
vibe-import list-models --provider openrouter

# List models for OpenAI
vibe-import list-models --provider openai

# List models for Anthropic
vibe-import list-models --provider anthropic
```

### How to Specify a Model

You can specify the model in 4 ways (priority: CLI > .env > env var > config):

**1. CLI parameter (highest priority)**
```bash
vibe-import generate my_app.py --model google/gemma-2-9b-it:free
```

**2. .env file**
```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-...
VIBE_IMPORT_MODEL=google/gemma-2-9b-it:free
```

**3. Environment variable**
```bash
export VIBE_IMPORT_MODEL=google/gemma-2-9b-it:free
vibe-import generate my_app.py
```

**4. Configuration file**
```toml
# vibe-import.toml
[llm]
provider = "openrouter"
model = "google/gemma-2-9b-it:free"
```

**Note:** You can use ANY model from OpenRouter, not just the free ones listed in `list-models`. See all models at: https://openrouter.ai/models

### Inspect Code Structure

```bash
# Show code structure
vibe-import inspect my_app.py

# Output as JSON
vibe-import inspect my_app.py --format json
```

### Generate Specification

```bash
# Generate a spec file that can be edited
vibe-import spec my_app.py --output spec.json
```

### Show Configuration

```bash
# Show current configuration
vibe-import config
```

This displays:
- LLM settings (provider, model, temperature)
- Output settings (directory, documentation)
- Analysis settings (recursive, exclusions)
- API key status

## ⚙️ Configuration

Create a `vibe-import.toml` file in your project root:

```toml
[llm]
provider = "openrouter"
model = "qwen/qwen3-coder:free"
temperature = 0.2

[output]
directory = "./generated"
include_docs = true
docstring_style = "google"

[analysis]
recursive = true
exclude_patterns = ["**/venv/**", "**/.venv/**"]
```

Or add to your `pyproject.toml`:

```toml
[tool.vibe-import]
[tool.vibe-import.llm]
provider = "openai"
model = "gpt-4o"
```

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# .env file
OPENROUTER_API_KEY=sk-or-v1-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
VIBE_IMPORT_PROVIDER=openrouter
VIBE_IMPORT_MODEL=qwen/qwen3-coder:free
VIBE_IMPORT_TEMPERATURE=0.2
```

Or export in your shell:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 🔧 How It Works

1. **Parse**: Vibe-Import parses your Python code using AST to find all import statements
2. **Detect**: It identifies which imports don't exist (aren't installed or in stdlib)
3. **Analyze**: For missing imports, it tracks how they're used:
   - Function calls and their arguments
   - Class instantiations and method calls
   - Attribute access patterns
   - Return value usage
4. **Infer**: From usage patterns, it infers:
   - Function signatures (parameters and types)
   - Class structures (init params, methods, attributes)
   - Return types
5. **Generate**: Using LLM, it generates complete, working Python code
6. **Document**: It creates README and API documentation

## 📝 Example

### Input Code

```python
from data_processor import DataPipeline, transform_data

# Create a pipeline
pipeline = DataPipeline(
    source="database",
    batch_size=100,
    parallel=True
)

# Process data
with pipeline:
    raw_data = pipeline.fetch()
    cleaned = transform_data(raw_data, remove_nulls=True)
    pipeline.save(cleaned, format="parquet")
```

### Generated Package

```
data_processor/
├── __init__.py
├── pipeline.py
├── transforms.py
└── README.md
```

### Generated Code (pipeline.py)

```python
"""Data pipeline implementation."""

from typing import Any, Self


class DataPipeline:
    """A data processing pipeline with batch support.
    
    Args:
        source: Data source identifier
        batch_size: Number of records per batch
        parallel: Enable parallel processing
    """
    
    def __init__(
        self,
        source: str,
        batch_size: int = 100,
        parallel: bool = False
    ) -> None:
        self.source = source
        self.batch_size = batch_size
        self.parallel = parallel
        self._connection = None
    
    def __enter__(self) -> Self:
        """Enter context manager."""
        self._connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self._disconnect()
    
    def fetch(self) -> list[dict[str, Any]]:
        """Fetch data from the source.
        
        Returns:
            List of data records
        """
        # Implementation here
        ...
    
    def save(self, data: list[dict[str, Any]], format: str = "json") -> None:
        """Save processed data.
        
        Args:
            data: Data to save
            format: Output format (json, parquet, csv)
        """
        # Implementation here
        ...
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Built with [OpenRouter](https://openrouter.ai/), [OpenAI](https://openai.com/) and [Anthropic](https://anthropic.com/) APIs
- CLI powered by [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)

## 📚 Documentation

For detailed usage instructions in Russian, see [USAGE_RU.md](USAGE_RU.md)