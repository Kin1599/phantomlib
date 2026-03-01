"""
Usage Extractor module for Vibe-Import.

This module takes the raw analysis results and extracts structured
specifications that can be used to generate package code.
"""

from dataclasses import dataclass, field
from typing import Any

from vibe_import.models import (
    AnalysisResult,
    ModuleUsage,
    FunctionUsage,
    ClassUsage,
    MethodUsage,
    ArgInfo,
    ArgType,
)


@dataclass
class FunctionSpec:
    """Specification for a function to be generated."""
    name: str
    parameters: list[tuple[str, str]]  # (name, type_hint)
    return_type: str
    is_async: bool = False
    docstring: str = ""
    
    def to_signature(self) -> str:
        """Generate the function signature."""
        params = ", ".join(f"{name}: {type_hint}" for name, type_hint in self.parameters)
        async_prefix = "async " if self.is_async else ""
        return f"{async_prefix}def {self.name}({params}) -> {self.return_type}:"


@dataclass
class MethodSpec:
    """Specification for a class method."""
    name: str
    parameters: list[tuple[str, str]]  # (name, type_hint) - excluding self
    return_type: str
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    docstring: str = ""


@dataclass
class ClassSpec:
    """Specification for a class to be generated."""
    name: str
    init_parameters: list[tuple[str, str]]  # (name, type_hint)
    methods: list[MethodSpec] = field(default_factory=list)
    attributes: list[tuple[str, str]] = field(default_factory=list)  # (name, type_hint)
    is_context_manager: bool = False
    is_iterable: bool = False
    docstring: str = ""
    
    def get_required_methods(self) -> list[str]:
        """Get list of required dunder methods based on usage."""
        methods = ["__init__"]
        if self.is_context_manager:
            methods.extend(["__enter__", "__exit__"])
        if self.is_iterable:
            methods.extend(["__iter__", "__next__"])
        return methods


@dataclass
class ConstantSpec:
    """Specification for a module-level constant."""
    name: str
    inferred_type: str
    suggested_value: Any = None


@dataclass
class ModuleSpec:
    """Complete specification for a module to be generated."""
    name: str
    functions: list[FunctionSpec] = field(default_factory=list)
    classes: list[ClassSpec] = field(default_factory=list)
    constants: list[ConstantSpec] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
    imports_needed: list[str] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Generate a context string for LLM prompts."""
        lines = [f"Module: {self.name}", ""]
        
        if self.functions:
            lines.append("Functions:")
            for func in self.functions:
                lines.append(f"  - {func.to_signature()}")
                if func.docstring:
                    lines.append(f"    Description: {func.docstring}")
            lines.append("")
        
        if self.classes:
            lines.append("Classes:")
            for cls in self.classes:
                init_params = ", ".join(f"{n}: {t}" for n, t in cls.init_parameters)
                lines.append(f"  - class {cls.name}:")
                lines.append(f"      __init__({init_params})")
                for method in cls.methods:
                    params = ", ".join(f"{n}: {t}" for n, t in method.parameters)
                    lines.append(f"      {method.name}({params}) -> {method.return_type}")
                if cls.attributes:
                    lines.append(f"      Attributes: {', '.join(n for n, _ in cls.attributes)}")
                if cls.is_context_manager:
                    lines.append("      [Used as context manager]")
                if cls.is_iterable:
                    lines.append("      [Used as iterable]")
            lines.append("")
        
        if self.constants:
            lines.append("Constants:")
            for const in self.constants:
                lines.append(f"  - {const.name}: {const.inferred_type}")
            lines.append("")
        
        return "\n".join(lines)


class UsageExtractor:
    """
    Extracts structured specifications from analysis results.
    
    This class transforms raw usage information into clean specifications
    that can be used to generate package code.
    """
    
    def __init__(self):
        self._type_inference_rules: dict[str, str] = {
            # Common naming patterns
            "count": "int",
            "num": "int",
            "size": "int",
            "length": "int",
            "index": "int",
            "id": "int",
            "name": "str",
            "path": "str",
            "url": "str",
            "text": "str",
            "message": "str",
            "data": "Any",
            "items": "list",
            "values": "list",
            "keys": "list",
            "config": "dict",
            "options": "dict",
            "settings": "dict",
            "enabled": "bool",
            "is_": "bool",
            "has_": "bool",
            "should_": "bool",
        }
    
    def extract_from_results(self, results: list[AnalysisResult]) -> list[ModuleSpec]:
        """
        Extract module specifications from multiple analysis results.
        
        Args:
            results: List of AnalysisResult from code analysis
            
        Returns:
            List of ModuleSpec for each missing module
        """
        # Aggregate all module usages by module name
        module_usages: dict[str, list[ModuleUsage]] = {}
        
        for result in results:
            for usage in result.module_usages:
                if usage.name not in module_usages:
                    module_usages[usage.name] = []
                module_usages[usage.name].append(usage)
        
        # Convert to specs
        specs = []
        for module_name, usages in module_usages.items():
            spec = self._extract_module_spec(module_name, usages)
            specs.append(spec)
        
        return specs
    
    def extract_from_result(self, result: AnalysisResult) -> list[ModuleSpec]:
        """
        Extract module specifications from a single analysis result.
        
        Args:
            result: AnalysisResult from code analysis
            
        Returns:
            List of ModuleSpec for each missing module
        """
        return self.extract_from_results([result])
    
    def _extract_module_spec(
        self, 
        module_name: str, 
        usages: list[ModuleUsage]
    ) -> ModuleSpec:
        """Extract a complete module specification from usage information."""
        spec = ModuleSpec(name=module_name)
        
        # Aggregate all functions
        functions: dict[str, FunctionUsage] = {}
        for usage in usages:
            for func in usage.functions:
                if func.name not in functions:
                    functions[func.name] = func
                else:
                    # Merge usage information
                    self._merge_function_usage(functions[func.name], func)
        
        # Convert to function specs
        for func_usage in functions.values():
            spec.functions.append(self._extract_function_spec(func_usage))
        
        # Aggregate all classes
        classes: dict[str, ClassUsage] = {}
        for usage in usages:
            for cls in usage.classes:
                if cls.name not in classes:
                    classes[cls.name] = cls
                else:
                    self._merge_class_usage(classes[cls.name], cls)
        
        # Convert to class specs
        for class_usage in classes.values():
            spec.classes.append(self._extract_class_spec(class_usage))
        
        # Aggregate constants
        constants: set[str] = set()
        for usage in usages:
            constants.update(usage.constants_accessed)
        
        for const_name in constants:
            spec.constants.append(self._extract_constant_spec(const_name))
        
        # Determine needed imports
        spec.imports_needed = self._determine_imports(spec)
        
        return spec
    
    def _extract_function_spec(self, usage: FunctionUsage) -> FunctionSpec:
        """Extract a function specification from usage information."""
        parameters = []
        
        # Process positional args
        for i, arg in enumerate(usage.args):
            param_name = arg.name or f"arg{i}"
            param_type = self._infer_parameter_type(param_name, arg)
            parameters.append((param_name, param_type))
        
        # Process keyword args
        for name, arg in usage.kwargs.items():
            param_type = self._infer_parameter_type(name, arg)
            # Add default indicator for kwargs
            parameters.append((name, param_type))
        
        # Determine return type
        return_type = self._infer_return_type(usage)
        
        return FunctionSpec(
            name=usage.name,
            parameters=parameters,
            return_type=return_type,
        )
    
    def _extract_class_spec(self, usage: ClassUsage) -> ClassSpec:
        """Extract a class specification from usage information."""
        # Extract init parameters
        init_parameters = []
        for i, arg in enumerate(usage.init_args):
            param_name = arg.name or f"arg{i}"
            param_type = self._infer_parameter_type(param_name, arg)
            init_parameters.append((param_name, param_type))
        
        for name, arg in usage.init_kwargs.items():
            param_type = self._infer_parameter_type(name, arg)
            init_parameters.append((name, param_type))
        
        # Extract methods
        methods = []
        for method_usage in usage.methods_called:
            method_spec = self._extract_method_spec(method_usage)
            methods.append(method_spec)
        
        # Extract attributes
        attributes = []
        for attr_name in usage.attributes_accessed:
            attr_type = self._infer_type_from_name(attr_name)
            attributes.append((attr_name, attr_type))
        
        return ClassSpec(
            name=usage.name,
            init_parameters=init_parameters,
            methods=methods,
            attributes=attributes,
            is_context_manager=usage.used_as_context_manager,
            is_iterable=usage.used_as_iterable,
        )
    
    def _extract_method_spec(self, usage: MethodUsage) -> MethodSpec:
        """Extract a method specification from usage information."""
        parameters = []
        
        for i, arg in enumerate(usage.args):
            param_name = arg.name or f"arg{i}"
            param_type = self._infer_parameter_type(param_name, arg)
            parameters.append((param_name, param_type))
        
        for name, arg in usage.kwargs.items():
            param_type = self._infer_parameter_type(name, arg)
            parameters.append((name, param_type))
        
        return_type = "Any"
        if usage.return_usage:
            return_type = self._infer_return_type_from_usage(usage.return_usage)
        
        return MethodSpec(
            name=usage.name,
            parameters=parameters,
            return_type=return_type,
        )
    
    def _extract_constant_spec(self, name: str) -> ConstantSpec:
        """Extract a constant specification from its name."""
        inferred_type = self._infer_type_from_name(name)
        return ConstantSpec(name=name, inferred_type=inferred_type)
    
    def _infer_parameter_type(self, name: str, arg: ArgInfo) -> str:
        """Infer the type of a parameter from its name and usage."""
        # First, use the inferred type from the argument if available
        if arg.inferred_type != ArgType.UNKNOWN:
            return arg.to_type_hint()
        
        # Fall back to name-based inference
        return self._infer_type_from_name(name)
    
    def _infer_type_from_name(self, name: str) -> str:
        """Infer a type from a parameter/variable name."""
        name_lower = name.lower()
        
        # Check exact matches
        if name_lower in self._type_inference_rules:
            return self._type_inference_rules[name_lower]
        
        # Check prefix matches
        for prefix, type_hint in self._type_inference_rules.items():
            if prefix.endswith("_") and name_lower.startswith(prefix):
                return type_hint
        
        # Check suffix patterns
        if name_lower.endswith("_list") or name_lower.endswith("s"):
            return "list"
        if name_lower.endswith("_dict") or name_lower.endswith("_map"):
            return "dict"
        if name_lower.endswith("_count") or name_lower.endswith("_num"):
            return "int"
        if name_lower.endswith("_flag"):
            return "bool"
        
        return "Any"
    
    def _infer_return_type(self, usage: FunctionUsage) -> str:
        """Infer the return type of a function from its usage."""
        if usage.return_usage:
            return self._infer_return_type_from_usage(usage.return_usage)
        
        # Infer from function name
        name_lower = usage.name.lower()
        
        if name_lower.startswith("get_") or name_lower.startswith("fetch_"):
            return "Any"
        if name_lower.startswith("is_") or name_lower.startswith("has_"):
            return "bool"
        if name_lower.startswith("count_") or name_lower.startswith("num_"):
            return "int"
        if name_lower.startswith("list_") or name_lower.startswith("find_all"):
            return "list"
        if name_lower.startswith("create_") or name_lower.startswith("build_"):
            return "Any"
        if name_lower in ("save", "write", "delete", "remove", "clear"):
            return "None"
        
        return "Any"
    
    def _infer_return_type_from_usage(self, usage: Any) -> str:
        """Infer return type from how the return value is used."""
        from vibe_import.models import ReturnUsageInfo
        
        if not isinstance(usage, ReturnUsageInfo):
            return "Any"
        
        # If used as iterable, likely returns a collection
        if usage.used_as_iterable:
            return "Iterable"
        
        # If used as context manager, likely returns self or a context
        if usage.used_as_context_manager:
            return "ContextManager"
        
        # If attributes are accessed, it returns an object
        if usage.attributes_accessed or usage.methods_called:
            return "Any"  # Could be more specific with a custom class
        
        # Use the inferred type if available
        if usage.inferred_type != ArgType.UNKNOWN:
            return usage.inferred_type.value
        
        return "Any"
    
    def _merge_function_usage(self, target: FunctionUsage, source: FunctionUsage) -> None:
        """Merge source function usage into target."""
        # Merge args - take the longer list
        if len(source.args) > len(target.args):
            target.args = source.args
        
        # Merge kwargs
        for name, arg in source.kwargs.items():
            if name not in target.kwargs:
                target.kwargs[name] = arg
        
        # Merge call locations
        target.call_locations.extend(source.call_locations)
    
    def _merge_class_usage(self, target: ClassUsage, source: ClassUsage) -> None:
        """Merge source class usage into target."""
        # Merge init args
        if len(source.init_args) > len(target.init_args):
            target.init_args = source.init_args
        
        # Merge init kwargs
        for name, arg in source.init_kwargs.items():
            if name not in target.init_kwargs:
                target.init_kwargs[name] = arg
        
        # Merge methods
        existing_methods = {m.name for m in target.methods_called}
        for method in source.methods_called:
            if method.name not in existing_methods:
                target.methods_called.append(method)
        
        # Merge attributes
        existing_attrs = set(target.attributes_accessed)
        for attr in source.attributes_accessed:
            if attr not in existing_attrs:
                target.attributes_accessed.append(attr)
        
        # Merge flags
        target.used_as_context_manager = target.used_as_context_manager or source.used_as_context_manager
        target.used_as_iterable = target.used_as_iterable or source.used_as_iterable
        
        # Merge locations
        target.instantiation_locations.extend(source.instantiation_locations)
    
    def _determine_imports(self, spec: ModuleSpec) -> list[str]:
        """Determine what imports the generated module will need."""
        imports = set()
        
        # Always need typing for type hints
        imports.add("from typing import Any")
        
        # Check for specific types used
        all_types = []
        
        for func in spec.functions:
            all_types.append(func.return_type)
            all_types.extend(t for _, t in func.parameters)
        
        for cls in spec.classes:
            all_types.extend(t for _, t in cls.init_parameters)
            all_types.extend(t for _, t in cls.attributes)
            for method in cls.methods:
                all_types.append(method.return_type)
                all_types.extend(t for _, t in method.parameters)
        
        # Add imports based on types used
        type_imports = {
            "Iterable": "from typing import Iterable",
            "Iterator": "from typing import Iterator",
            "Callable": "from typing import Callable",
            "Optional": "from typing import Optional",
            "Union": "from typing import Union",
            "ContextManager": "from contextlib import contextmanager",
            "Path": "from pathlib import Path",
        }
        
        for type_name in all_types:
            if type_name in type_imports:
                imports.add(type_imports[type_name])
        
        # Check for context manager
        for cls in spec.classes:
            if cls.is_context_manager:
                imports.add("from typing import Self")
        
        return sorted(imports)