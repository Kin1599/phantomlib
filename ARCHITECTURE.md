# Vibe-Import Architecture

## Overview

Vibe-Import is a tool that automatically generates missing Python packages based on how they are used in your code. When you import a package that doesn't exist and use it in your code, Vibe-Import analyzes the usage patterns and generates a complete implementation along with documentation.

## Core Components

### 1. Code Analyzer (`analyzer/`)
- **AST Parser**: Parses Python source files to extract:
  - Import statements (both `import x` and `from x import y`)
  - Usage patterns of imported modules/functions/classes
  - Function calls with arguments and return value expectations
  - Class instantiations and method calls
  - Type hints if available

### 2. Usage Extractor (`extractor/`)
- Collects all usage information for missing imports:
  - Function signatures (inferred from calls)
  - Class structures (inferred from instantiation and method calls)
  - Expected return types (inferred from how results are used)
  - Constants and variables accessed

### 3. LLM Integration (`llm/`)
- Interfaces with LLM APIs (OpenAI, Anthropic, etc.)
- Constructs prompts with:
  - Extracted usage patterns
  - Context from surrounding code
  - Style preferences
- Handles response parsing and validation

### 4. Package Generator (`generator/`)
- Creates package directory structure
- Generates Python files with proper `__init__.py`
- Ensures generated code matches inferred signatures
- Adds type hints and docstrings

### 5. Documentation Generator (`docs/`)
- Generates README.md for the package
- Creates API documentation
- Includes usage examples based on original code

### 6. CLI Interface (`cli/`)
- Command-line interface for running the tool
- Configuration options
- Interactive mode for reviewing generated code

## Workflow

```
┌─────────────────┐
│  Source Code    │
│  (with missing  │
│   imports)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Code Analyzer  │
│  (AST Parsing)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Usage Extractor │
│ (Infer specs)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Integration │
│ (Generate code) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Package Generator│
│ (Create files)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Documentation  │
│   Generator     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generated Pkg   │
│ + Documentation │
└─────────────────┘
```

## Data Structures

### ImportInfo
```python
@dataclass
class ImportInfo:
    module_name: str           # e.g., "mypackage"
    imported_names: list[str]  # e.g., ["func1", "Class1"]
    alias: str | None          # e.g., "mp" for "import mypackage as mp"
    is_from_import: bool       # True for "from x import y"
    line_number: int
```

### UsageInfo
```python
@dataclass
class FunctionUsage:
    name: str
    args: list[ArgInfo]
    kwargs: dict[str, ArgInfo]
    return_usage: ReturnUsageInfo | None
    call_locations: list[Location]

@dataclass
class ClassUsage:
    name: str
    init_args: list[ArgInfo]
    methods_called: list[MethodUsage]
    attributes_accessed: list[str]
    instantiation_locations: list[Location]

@dataclass
class ModuleUsage:
    name: str
    functions: list[FunctionUsage]
    classes: list[ClassUsage]
    constants: list[str]
    submodules: list[str]
```

### GeneratedPackage
```python
@dataclass
class GeneratedFile:
    path: str
    content: str
    
@dataclass
class GeneratedPackage:
    name: str
    files: list[GeneratedFile]
    documentation: str
```

## Example

### Input Code
```python
from magic_utils import calculate_magic, MagicProcessor

result = calculate_magic(42, mode="fast")
print(result.value)

processor = MagicProcessor(config={"threads": 4})
processed = processor.process(data=[1, 2, 3])
processor.save("output.json")
```

### Inferred Specifications
```
Module: magic_utils

Function: calculate_magic
  - Args: (int, mode: str)
  - Returns: object with .value attribute

Class: MagicProcessor
  - __init__(config: dict)
  - Methods:
    - process(data: list) -> Any
    - save(path: str) -> None
```

### Generated Package
```
magic_utils/
├── __init__.py
├── calculator.py
├── processor.py
└── README.md