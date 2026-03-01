"""
Data models for Vibe-Import.

This module contains all the data structures used throughout the application
for representing imports, usage patterns, and generated packages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArgType(Enum):
    """Inferred argument type."""
    UNKNOWN = "unknown"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    TUPLE = "tuple"
    SET = "set"
    NONE = "None"
    CALLABLE = "Callable"
    ANY = "Any"


@dataclass
class Location:
    """Source code location."""
    file_path: str
    line_number: int
    column: int = 0
    end_line_number: int | None = None
    end_column: int | None = None
    
    def __str__(self) -> str:
        return f"{self.file_path}:{self.line_number}"


@dataclass
class ArgInfo:
    """Information about a function/method argument."""
    name: str | None  # None for positional args without name
    value_repr: str | None  # String representation of the value if literal
    inferred_type: ArgType = ArgType.UNKNOWN
    is_keyword: bool = False
    
    def to_type_hint(self) -> str:
        """Convert to Python type hint string."""
        type_map = {
            ArgType.UNKNOWN: "Any",
            ArgType.INT: "int",
            ArgType.FLOAT: "float",
            ArgType.STR: "str",
            ArgType.BOOL: "bool",
            ArgType.LIST: "list",
            ArgType.DICT: "dict",
            ArgType.TUPLE: "tuple",
            ArgType.SET: "set",
            ArgType.NONE: "None",
            ArgType.CALLABLE: "Callable",
            ArgType.ANY: "Any",
        }
        return type_map.get(self.inferred_type, "Any")


@dataclass
class ReturnUsageInfo:
    """Information about how a return value is used."""
    attributes_accessed: list[str] = field(default_factory=list)
    methods_called: list[str] = field(default_factory=list)
    used_as_iterable: bool = False
    used_as_context_manager: bool = False
    used_in_comparison: bool = False
    assigned_to: str | None = None
    inferred_type: ArgType = ArgType.UNKNOWN


@dataclass
class MethodUsage:
    """Information about a method call on a class instance."""
    name: str
    args: list[ArgInfo] = field(default_factory=list)
    kwargs: dict[str, ArgInfo] = field(default_factory=dict)
    return_usage: ReturnUsageInfo | None = None
    call_locations: list[Location] = field(default_factory=list)


@dataclass
class FunctionUsage:
    """Information about how a function is used."""
    name: str
    args: list[ArgInfo] = field(default_factory=list)
    kwargs: dict[str, ArgInfo] = field(default_factory=dict)
    return_usage: ReturnUsageInfo | None = None
    call_locations: list[Location] = field(default_factory=list)
    
    def get_signature(self) -> str:
        """Generate a function signature string."""
        params = []
        for i, arg in enumerate(self.args):
            if arg.name:
                params.append(f"{arg.name}: {arg.to_type_hint()}")
            else:
                params.append(f"arg{i}: {arg.to_type_hint()}")
        
        for name, arg in self.kwargs.items():
            params.append(f"{name}: {arg.to_type_hint()} = ...")
        
        return_type = "Any"
        if self.return_usage:
            return_type = self.return_usage.inferred_type.value
            if return_type == "unknown":
                return_type = "Any"
        
        return f"def {self.name}({', '.join(params)}) -> {return_type}"


@dataclass
class ClassUsage:
    """Information about how a class is used."""
    name: str
    init_args: list[ArgInfo] = field(default_factory=list)
    init_kwargs: dict[str, ArgInfo] = field(default_factory=dict)
    methods_called: list[MethodUsage] = field(default_factory=list)
    attributes_accessed: list[str] = field(default_factory=list)
    instantiation_locations: list[Location] = field(default_factory=list)
    used_as_context_manager: bool = False
    used_as_iterable: bool = False


@dataclass
class ImportInfo:
    """Information about an import statement."""
    module_name: str  # e.g., "mypackage" or "mypackage.submodule"
    imported_names: list[str] = field(default_factory=list)  # e.g., ["func1", "Class1"]
    alias: str | None = None  # e.g., "mp" for "import mypackage as mp"
    is_from_import: bool = False  # True for "from x import y"
    line_number: int = 0
    file_path: str = ""
    
    @property
    def top_level_module(self) -> str:
        """Get the top-level module name."""
        return self.module_name.split(".")[0]
    
    def __str__(self) -> str:
        if self.is_from_import:
            names = ", ".join(self.imported_names)
            return f"from {self.module_name} import {names}"
        elif self.alias:
            return f"import {self.module_name} as {self.alias}"
        else:
            return f"import {self.module_name}"


@dataclass
class ModuleUsage:
    """Aggregated usage information for a module."""
    name: str
    import_info: ImportInfo
    functions: list[FunctionUsage] = field(default_factory=list)
    classes: list[ClassUsage] = field(default_factory=list)
    constants_accessed: list[str] = field(default_factory=list)
    submodules_accessed: list[str] = field(default_factory=list)
    
    def get_all_names(self) -> list[str]:
        """Get all names that need to be exported from this module."""
        names = []
        names.extend(f.name for f in self.functions)
        names.extend(c.name for c in self.classes)
        names.extend(self.constants_accessed)
        return names


@dataclass
class GeneratedFile:
    """A generated source file."""
    path: str  # Relative path within the package
    content: str
    
    @property
    def filename(self) -> str:
        """Get just the filename."""
        return self.path.split("/")[-1]


@dataclass
class GeneratedPackage:
    """A complete generated package."""
    name: str
    files: list[GeneratedFile] = field(default_factory=list)
    documentation: str = ""
    
    def get_file(self, path: str) -> GeneratedFile | None:
        """Get a file by its path."""
        for f in self.files:
            if f.path == path:
                return f
        return None
    
    def add_file(self, path: str, content: str) -> None:
        """Add a file to the package."""
        self.files.append(GeneratedFile(path=path, content=content))


@dataclass
class PyPIPackage:
    """Information about a package available on PyPI."""
    name: str
    install_command: str
    import_info: ImportInfo


@dataclass
class AnalysisResult:
    """Result of analyzing source code."""
    file_path: str
    imports: list[ImportInfo] = field(default_factory=list)
    missing_imports: list[ImportInfo] = field(default_factory=list)
    module_usages: list[ModuleUsage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pypi_packages: list[PyPIPackage] = field(default_factory=list)


@dataclass
class GenerationConfig:
    """Configuration for package generation."""
    output_dir: str = "."
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4"
    temperature: float = 0.2
    include_tests: bool = True
    include_type_hints: bool = True
    docstring_style: str = "google"  # "google", "numpy", or "sphinx"
    max_retries: int = 3