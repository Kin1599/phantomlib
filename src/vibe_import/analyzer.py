"""
Code Analyzer module for Vibe-Import.

This module provides AST-based analysis of Python source code to:
1. Extract all import statements
2. Identify which imports are missing (don't exist)
3. Track how imported names are used throughout the code
"""

import ast
import sys
import importlib.util
import urllib.request
import urllib.error
import json
from pathlib import Path
from typing import Any

from vibe_import.models import (
    ImportInfo,
    Location,
    ArgInfo,
    ArgType,
    FunctionUsage,
    ClassUsage,
    MethodUsage,
    ReturnUsageInfo,
    ModuleUsage,
    AnalysisResult,
    PyPIPackage,
)


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract import statements."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: list[ImportInfo] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' and 'import x as y' statements."""
        for alias in node.names:
            self.imports.append(ImportInfo(
                module_name=alias.name,
                alias=alias.asname,
                is_from_import=False,
                line_number=node.lineno,
                file_path=self.file_path,
            ))
        self.generic_visit(node)
    
    def visit_FromImport(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        if node.module is None:
            # Relative import like 'from . import x'
            return
        
        imported_names = []
        for alias in node.names:
            if alias.name == "*":
                # Star import - we'll need special handling
                imported_names.append("*")
            else:
                imported_names.append(alias.asname or alias.name)
        
        self.imports.append(ImportInfo(
            module_name=node.module,
            imported_names=imported_names,
            is_from_import=True,
            line_number=node.lineno,
            file_path=self.file_path,
        ))
        self.generic_visit(node)
    
    # Alias for the actual AST node name
    visit_ImportFrom = visit_FromImport


class UsageVisitor(ast.NodeVisitor):
    """AST visitor to track how imported names are used."""
    
    def __init__(self, file_path: str, import_names: dict[str, ImportInfo]):
        self.file_path = file_path
        self.import_names = import_names  # Maps local names to ImportInfo
        self.function_usages: dict[str, FunctionUsage] = {}
        self.class_usages: dict[str, ClassUsage] = {}
        self.attribute_accesses: dict[str, list[str]] = {}  # module -> [attrs]
        self._current_assignment_target: str | None = None
    
    def _get_location(self, node: ast.AST) -> Location:
        """Create a Location from an AST node."""
        return Location(
            file_path=self.file_path,
            line_number=node.lineno,
            column=node.col_offset,
            end_line_number=getattr(node, 'end_lineno', None),
            end_column=getattr(node, 'end_col_offset', None),
        )
    
    def _infer_type_from_value(self, node: ast.AST) -> ArgType:
        """Infer the type of a value from its AST node."""
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, bool):
                return ArgType.BOOL
            elif isinstance(value, int):
                return ArgType.INT
            elif isinstance(value, float):
                return ArgType.FLOAT
            elif isinstance(value, str):
                return ArgType.STR
            elif value is None:
                return ArgType.NONE
        elif isinstance(node, ast.List):
            return ArgType.LIST
        elif isinstance(node, ast.Dict):
            return ArgType.DICT
        elif isinstance(node, ast.Tuple):
            return ArgType.TUPLE
        elif isinstance(node, ast.Set):
            return ArgType.SET
        elif isinstance(node, (ast.Lambda, ast.FunctionDef)):
            return ArgType.CALLABLE
        return ArgType.UNKNOWN
    
    def _get_value_repr(self, node: ast.AST) -> str | None:
        """Get string representation of a literal value."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.List):
            return "[...]"
        elif isinstance(node, ast.Dict):
            return "{...}"
        elif isinstance(node, ast.Tuple):
            return "(...)"
        elif isinstance(node, ast.Set):
            return "{...}"
        return None
    
    def _extract_args(self, node: ast.Call) -> tuple[list[ArgInfo], dict[str, ArgInfo]]:
        """Extract argument information from a Call node."""
        args = []
        kwargs = {}
        
        for i, arg in enumerate(node.args):
            args.append(ArgInfo(
                name=None,
                value_repr=self._get_value_repr(arg),
                inferred_type=self._infer_type_from_value(arg),
                is_keyword=False,
            ))
        
        for keyword in node.keywords:
            if keyword.arg is not None:
                kwargs[keyword.arg] = ArgInfo(
                    name=keyword.arg,
                    value_repr=self._get_value_repr(keyword.value),
                    inferred_type=self._infer_type_from_value(keyword.value),
                    is_keyword=True,
                )
        
        return args, kwargs
    
    def _get_full_attribute_chain(self, node: ast.AST) -> list[str] | None:
        """Get the full chain of attribute access (e.g., ['module', 'submodule', 'func'])."""
        chain = []
        current = node
        
        while isinstance(current, ast.Attribute):
            chain.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            chain.append(current.id)
            chain.reverse()
            return chain
        
        return None
    
    def _is_imported_name(self, name: str) -> bool:
        """Check if a name is from our tracked imports."""
        return name in self.import_names
    
    def visit_Call(self, node: ast.Call) -> None:
        """Handle function/method calls."""
        # Direct function call: func()
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if self._is_imported_name(name):
                args, kwargs = self._extract_args(node)
                if name not in self.function_usages:
                    self.function_usages[name] = FunctionUsage(
                        name=name,
                        args=args,
                        kwargs=kwargs,
                        call_locations=[],
                    )
                self.function_usages[name].call_locations.append(self._get_location(node))
                # Merge args if we have more info
                self._merge_args(self.function_usages[name], args, kwargs)
        
        # Attribute call: module.func() or obj.method()
        elif isinstance(node.func, ast.Attribute):
            chain = self._get_full_attribute_chain(node.func)
            if chain and len(chain) >= 2:
                root = chain[0]
                if self._is_imported_name(root):
                    # This is a call on an imported module/object
                    if len(chain) == 2:
                        # module.func() - could be function or class
                        func_name = chain[1]
                        args, kwargs = self._extract_args(node)
                        
                        # Check if it looks like a class (starts with uppercase)
                        if func_name[0].isupper():
                            if func_name not in self.class_usages:
                                self.class_usages[func_name] = ClassUsage(
                                    name=func_name,
                                    init_args=args,
                                    init_kwargs=kwargs,
                                    instantiation_locations=[],
                                )
                            self.class_usages[func_name].instantiation_locations.append(
                                self._get_location(node)
                            )
                            self._merge_class_init(self.class_usages[func_name], args, kwargs)
                        else:
                            if func_name not in self.function_usages:
                                self.function_usages[func_name] = FunctionUsage(
                                    name=func_name,
                                    args=args,
                                    kwargs=kwargs,
                                    call_locations=[],
                                )
                            self.function_usages[func_name].call_locations.append(
                                self._get_location(node)
                            )
                            self._merge_args(self.function_usages[func_name], args, kwargs)
        
        # Also check if this is a method call on a previously instantiated class
        self._check_method_call(node)
        
        self.generic_visit(node)
    
    def _check_method_call(self, node: ast.Call) -> None:
        """Check if this is a method call on a class instance we're tracking."""
        if isinstance(node.func, ast.Attribute):
            # Get the object the method is called on
            if isinstance(node.func.value, ast.Name):
                # Simple case: obj.method()
                # We'd need to track variable assignments to know the class
                pass
    
    def _merge_args(
        self, 
        usage: FunctionUsage, 
        new_args: list[ArgInfo], 
        new_kwargs: dict[str, ArgInfo]
    ) -> None:
        """Merge new argument information with existing."""
        # Update positional args if we have more
        if len(new_args) > len(usage.args):
            usage.args = new_args
        else:
            # Update types if we have better info
            for i, (old, new) in enumerate(zip(usage.args, new_args)):
                if old.inferred_type == ArgType.UNKNOWN and new.inferred_type != ArgType.UNKNOWN:
                    usage.args[i] = new
        
        # Merge kwargs
        for name, arg in new_kwargs.items():
            if name not in usage.kwargs:
                usage.kwargs[name] = arg
            elif usage.kwargs[name].inferred_type == ArgType.UNKNOWN:
                usage.kwargs[name] = arg
    
    def _merge_class_init(
        self,
        usage: ClassUsage,
        new_args: list[ArgInfo],
        new_kwargs: dict[str, ArgInfo]
    ) -> None:
        """Merge new init argument information with existing."""
        if len(new_args) > len(usage.init_args):
            usage.init_args = new_args
        
        for name, arg in new_kwargs.items():
            if name not in usage.init_kwargs:
                usage.init_kwargs[name] = arg
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Handle attribute access: module.attr or obj.attr."""
        chain = self._get_full_attribute_chain(node)
        if chain and len(chain) >= 2:
            root = chain[0]
            if self._is_imported_name(root):
                # Track attribute access on imported module
                if root not in self.attribute_accesses:
                    self.attribute_accesses[root] = []
                attr_path = ".".join(chain[1:])
                if attr_path not in self.attribute_accesses[root]:
                    self.attribute_accesses[root].append(attr_path)
        
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Track assignments to understand return value usage."""
        # Track what the result is assigned to
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            self._current_assignment_target = node.targets[0].id
        
        self.generic_visit(node)
        self._current_assignment_target = None
    
    def visit_With(self, node: ast.With) -> None:
        """Track context manager usage."""
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                # Check if this is a call to an imported class
                if isinstance(item.context_expr.func, ast.Name):
                    name = item.context_expr.func.id
                    if name in self.class_usages:
                        self.class_usages[name].used_as_context_manager = True
                elif isinstance(item.context_expr.func, ast.Attribute):
                    chain = self._get_full_attribute_chain(item.context_expr.func)
                    if chain and len(chain) >= 2:
                        class_name = chain[-1]
                        if class_name in self.class_usages:
                            self.class_usages[class_name].used_as_context_manager = True
        
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For) -> None:
        """Track iteration usage."""
        if isinstance(node.iter, ast.Name):
            name = node.iter.id
            if name in self.class_usages:
                self.class_usages[name].used_as_iterable = True
        
        self.generic_visit(node)


class CodeAnalyzer:
    """
    Main analyzer class that coordinates import extraction and usage analysis.
    """
    
    def __init__(self, check_pypi: bool = True):
        """
        Initialize the analyzer.
        
        Args:
            check_pypi: If True, check PyPI for existing packages. If False,
                       treat all non-stdlib packages as missing.
        """
        self.check_pypi = check_pypi
        self.stdlib_modules = self._get_stdlib_modules()
    
    def _get_stdlib_modules(self) -> set[str]:
        """Get a set of standard library module names."""
        stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
        # Add some common ones that might be missing
        stdlib.update({
            'os', 'sys', 'io', 're', 'json', 'math', 'random', 'datetime',
            'collections', 'itertools', 'functools', 'typing', 'pathlib',
            'subprocess', 'threading', 'multiprocessing', 'asyncio',
            'unittest', 'logging', 'argparse', 'configparser',
        })
        return stdlib
    
    def _check_pypi(self, package_name: str) -> bool:
        """Check if a package exists on PyPI."""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return False
    
    def _module_exists(self, module_name: str) -> tuple[bool, str | None]:
        """
        Check if a module exists and can be imported.
        
        Returns:
            Tuple of (exists, install_command) where install_command is the pip install
            command if the package exists on PyPI but is not installed.
        """
        # Check stdlib first
        top_level = module_name.split(".")[0]
        if top_level in self.stdlib_modules:
            return True, None
        
        # Try to find the module spec
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                return True, None
        except (ModuleNotFoundError, ValueError, ImportError):
            pass
        
        # Check if package exists on PyPI
        if self._check_pypi(top_level):
            return False, f"pip install {top_level}"
        
        return False, None
    
    def analyze_file(self, file_path: str | Path) -> AnalysisResult:
        """
        Analyze a Python file for imports and their usage.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            AnalysisResult containing imports, missing imports, and usage info
        """
        file_path = Path(file_path)
        result = AnalysisResult(file_path=str(file_path))
        
        if not file_path.exists():
            result.errors.append(f"File not found: {file_path}")
            return result
        
        try:
            source = file_path.read_text(encoding='utf-8')
        except Exception as e:
            result.errors.append(f"Error reading file: {e}")
            return result
        
        return self.analyze_source(source, str(file_path))
    
    def analyze_source(self, source: str, file_path: str = "<string>") -> AnalysisResult:
        """
        Analyze Python source code for imports and their usage.
        
        Args:
            source: Python source code as a string
            file_path: Optional file path for error reporting
            
        Returns:
            AnalysisResult containing imports, missing imports, and usage info
        """
        result = AnalysisResult(file_path=file_path)
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            result.errors.append(f"Syntax error: {e}")
            return result
        
        # Extract imports
        import_visitor = ImportVisitor(file_path)
        import_visitor.visit(tree)
        result.imports = import_visitor.imports
        
        # Find missing imports
        for imp in result.imports:
            exists, install_cmd = self._module_exists(imp.module_name)
            if not exists:
                if install_cmd and self.check_pypi:
                    # Package exists on PyPI but not installed
                    result.pypi_packages.append(PyPIPackage(
                        name=imp.top_level_module,
                        install_command=install_cmd,
                        import_info=imp,
                    ))
                else:
                    # Package doesn't exist anywhere - needs generation
                    result.missing_imports.append(imp)
        
        # Build a map of local names to their imports (for missing imports only)
        import_names: dict[str, ImportInfo] = {}
        for imp in result.missing_imports:
            if imp.is_from_import:
                for name in imp.imported_names:
                    import_names[name] = imp
            elif imp.alias:
                import_names[imp.alias] = imp
            else:
                import_names[imp.module_name.split(".")[0]] = imp
        
        # Analyze usage of missing imports
        usage_visitor = UsageVisitor(file_path, import_names)
        usage_visitor.visit(tree)
        
        # Build ModuleUsage objects
        module_usages: dict[str, ModuleUsage] = {}
        
        for imp in result.missing_imports:
            module_name = imp.top_level_module
            if module_name not in module_usages:
                module_usages[module_name] = ModuleUsage(
                    name=module_name,
                    import_info=imp,
                )
        
        # Add function usages
        for func_name, func_usage in usage_visitor.function_usages.items():
            # Find which module this function belongs to
            if func_name in import_names:
                imp = import_names[func_name]
                module_name = imp.top_level_module
                if module_name in module_usages:
                    module_usages[module_name].functions.append(func_usage)
        
        # Add class usages
        for class_name, class_usage in usage_visitor.class_usages.items():
            if class_name in import_names:
                imp = import_names[class_name]
                module_name = imp.top_level_module
                if module_name in module_usages:
                    module_usages[module_name].classes.append(class_usage)
        
        # Add attribute accesses as constants
        for local_name, attrs in usage_visitor.attribute_accesses.items():
            if local_name in import_names:
                imp = import_names[local_name]
                module_name = imp.top_level_module
                if module_name in module_usages:
                    for attr in attrs:
                        if "." not in attr:  # Simple attribute, likely a constant
                            if attr not in module_usages[module_name].constants_accessed:
                                module_usages[module_name].constants_accessed.append(attr)
        
        result.module_usages = list(module_usages.values())
        
        return result
    
    def analyze_directory(
        self, 
        directory: str | Path, 
        recursive: bool = True,
        exclude_patterns: list[str] | None = None
    ) -> list[AnalysisResult]:
        """
        Analyze all Python files in a directory.
        
        Args:
            directory: Path to the directory
            recursive: Whether to search recursively
            exclude_patterns: Glob patterns to exclude
            
        Returns:
            List of AnalysisResult for each file
        """
        directory = Path(directory)
        exclude_patterns = exclude_patterns or ["**/venv/**", "**/.venv/**", "**/node_modules/**"]
        
        results = []
        pattern = "**/*.py" if recursive else "*.py"
        
        for py_file in directory.glob(pattern):
            # Check exclusions
            skip = False
            for exclude in exclude_patterns:
                if py_file.match(exclude):
                    skip = True
                    break
            
            if not skip:
                results.append(self.analyze_file(py_file))
        
        return results