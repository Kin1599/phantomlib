"""Tests for the usage extractor module."""

import pytest
from vibe_import.extractor import (
    UsageExtractor,
    FunctionSpec,
    ClassSpec,
    ModuleSpec,
)
from vibe_import.analyzer import CodeAnalyzer


class TestUsageExtractor:
    """Tests for UsageExtractor."""
    
    def test_extract_function_spec(self):
        """Test extracting function specifications."""
        source = """
from missing_utils import calculate

result = calculate(42, name="test", enabled=True)
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        extractor = UsageExtractor()
        specs = extractor.extract_from_result(result)
        
        assert len(specs) == 1
        spec = specs[0]
        
        assert spec.name == "missing_utils"
        assert len(spec.functions) == 1
        
        func = spec.functions[0]
        assert func.name == "calculate"
        assert len(func.parameters) >= 1
    
    def test_extract_class_spec(self):
        """Test extracting class specifications."""
        source = """
from missing_utils import DataProcessor

processor = DataProcessor(config={"threads": 4}, name="main")
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        extractor = UsageExtractor()
        specs = extractor.extract_from_result(result)
        
        assert len(specs) == 1
        spec = specs[0]
        
        assert len(spec.classes) == 1
        cls = spec.classes[0]
        assert cls.name == "DataProcessor"
        
        # Check init parameters
        param_names = [p[0] for p in cls.init_parameters]
        assert "config" in param_names
        assert "name" in param_names
    
    def test_extract_context_manager_class(self):
        """Test extracting class used as context manager."""
        source = """
from missing_utils import FileHandler

with FileHandler(path="test.txt") as handler:
    handler.write("data")
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        extractor = UsageExtractor()
        specs = extractor.extract_from_result(result)
        
        # Note: Context manager detection requires tracking variable assignments
        # This is a simplified test
        assert len(specs) == 1
    
    def test_type_inference_from_name(self):
        """Test type inference based on parameter names."""
        extractor = UsageExtractor()
        
        # Test various naming patterns
        assert extractor._infer_type_from_name("count") == "int"
        assert extractor._infer_type_from_name("num_items") == "int"
        assert extractor._infer_type_from_name("name") == "str"
        assert extractor._infer_type_from_name("path") == "str"
        assert extractor._infer_type_from_name("config") == "dict"
        assert extractor._infer_type_from_name("is_enabled") == "bool"
        assert extractor._infer_type_from_name("items") == "list"
    
    def test_module_spec_to_prompt_context(self):
        """Test generating prompt context from module spec."""
        spec = ModuleSpec(
            name="test_module",
            functions=[
                FunctionSpec(
                    name="process",
                    parameters=[("data", "list"), ("count", "int")],
                    return_type="dict",
                )
            ],
            classes=[
                ClassSpec(
                    name="Processor",
                    init_parameters=[("config", "dict")],
                    is_context_manager=True,
                )
            ],
        )
        
        context = spec.to_prompt_context()
        
        assert "test_module" in context
        assert "process" in context
        assert "Processor" in context
        assert "context manager" in context.lower()


class TestFunctionSpec:
    """Tests for FunctionSpec."""
    
    def test_to_signature(self):
        """Test generating function signature."""
        spec = FunctionSpec(
            name="calculate",
            parameters=[("x", "int"), ("y", "float")],
            return_type="float",
        )
        
        sig = spec.to_signature()
        
        assert "def calculate" in sig
        assert "x: int" in sig
        assert "y: float" in sig
        assert "-> float" in sig
    
    def test_async_signature(self):
        """Test generating async function signature."""
        spec = FunctionSpec(
            name="fetch_data",
            parameters=[("url", "str")],
            return_type="dict",
            is_async=True,
        )
        
        sig = spec.to_signature()
        
        assert "async def fetch_data" in sig


class TestClassSpec:
    """Tests for ClassSpec."""
    
    def test_get_required_methods(self):
        """Test getting required dunder methods."""
        spec = ClassSpec(
            name="MyClass",
            init_parameters=[],
        )
        
        methods = spec.get_required_methods()
        assert "__init__" in methods
    
    def test_context_manager_methods(self):
        """Test required methods for context manager."""
        spec = ClassSpec(
            name="MyClass",
            init_parameters=[],
            is_context_manager=True,
        )
        
        methods = spec.get_required_methods()
        assert "__enter__" in methods
        assert "__exit__" in methods
    
    def test_iterable_methods(self):
        """Test required methods for iterable."""
        spec = ClassSpec(
            name="MyClass",
            init_parameters=[],
            is_iterable=True,
        )
        
        methods = spec.get_required_methods()
        assert "__iter__" in methods
        assert "__next__" in methods