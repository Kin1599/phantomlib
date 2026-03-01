"""Tests for the code analyzer module."""

import pytest
from vibe_import.analyzer import CodeAnalyzer, ImportVisitor, UsageVisitor
from vibe_import.models import ImportInfo, ArgType


class TestImportVisitor:
    """Tests for ImportVisitor."""
    
    def test_simple_import(self):
        """Test parsing simple import statement."""
        source = "import mypackage"
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.imports) == 1
        assert result.imports[0].module_name == "mypackage"
        assert result.imports[0].is_from_import is False
        assert result.imports[0].alias is None
    
    def test_import_with_alias(self):
        """Test parsing import with alias."""
        source = "import mypackage as mp"
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.imports) == 1
        assert result.imports[0].module_name == "mypackage"
        assert result.imports[0].alias == "mp"
    
    def test_from_import(self):
        """Test parsing from import statement."""
        source = "from mypackage import func1, func2"
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.imports) == 1
        assert result.imports[0].module_name == "mypackage"
        assert result.imports[0].is_from_import is True
        assert "func1" in result.imports[0].imported_names
        assert "func2" in result.imports[0].imported_names
    
    def test_from_import_submodule(self):
        """Test parsing from import with submodule."""
        source = "from mypackage.submodule import MyClass"
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.imports) == 1
        assert result.imports[0].module_name == "mypackage.submodule"
        assert result.imports[0].top_level_module == "mypackage"
    
    def test_multiple_imports(self):
        """Test parsing multiple import statements."""
        source = """
import os
import mypackage
from another_package import something
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.imports) == 3


class TestMissingImportDetection:
    """Tests for detecting missing imports."""
    
    def test_stdlib_not_missing(self):
        """Test that stdlib imports are not marked as missing."""
        source = """
import os
import sys
import json
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.missing_imports) == 0
    
    def test_nonexistent_package_is_missing(self):
        """Test that non-existent packages are marked as missing."""
        source = "import this_package_definitely_does_not_exist_12345"
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.missing_imports) == 1
        assert result.missing_imports[0].module_name == "this_package_definitely_does_not_exist_12345"
    
    def test_mixed_imports(self):
        """Test mix of existing and missing imports."""
        source = """
import os
import nonexistent_package
from json import loads
from another_missing import something
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        missing_names = [imp.module_name for imp in result.missing_imports]
        assert "nonexistent_package" in missing_names
        assert "another_missing" in missing_names
        assert "os" not in missing_names
        assert "json" not in missing_names


class TestUsageAnalysis:
    """Tests for analyzing how imports are used."""
    
    def test_function_call_detection(self):
        """Test detecting function calls on imported modules."""
        source = """
from missing_utils import calculate

result = calculate(42, mode="fast")
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.module_usages) == 1
        usage = result.module_usages[0]
        
        assert len(usage.functions) == 1
        func = usage.functions[0]
        assert func.name == "calculate"
        assert len(func.args) == 1  # 42
        assert "mode" in func.kwargs
    
    def test_class_instantiation_detection(self):
        """Test detecting class instantiation."""
        source = """
from missing_utils import DataProcessor

processor = DataProcessor(config={"threads": 4})
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.module_usages) == 1
        usage = result.module_usages[0]
        
        assert len(usage.classes) == 1
        cls = usage.classes[0]
        assert cls.name == "DataProcessor"
        assert "config" in cls.init_kwargs
    
    def test_argument_type_inference(self):
        """Test inferring argument types from values."""
        source = """
from missing_utils import process

process(42, 3.14, "hello", True, [1, 2], {"key": "value"})
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        usage = result.module_usages[0]
        func = usage.functions[0]
        
        assert func.args[0].inferred_type == ArgType.INT
        assert func.args[1].inferred_type == ArgType.FLOAT
        assert func.args[2].inferred_type == ArgType.STR
        assert func.args[3].inferred_type == ArgType.BOOL
        assert func.args[4].inferred_type == ArgType.LIST
        assert func.args[5].inferred_type == ArgType.DICT


class TestCodeAnalyzer:
    """Tests for the main CodeAnalyzer class."""
    
    def test_analyze_source_with_syntax_error(self):
        """Test handling of syntax errors."""
        source = "def broken("
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.errors) > 0
        assert "Syntax error" in result.errors[0]
    
    def test_analyze_empty_source(self):
        """Test analyzing empty source code."""
        source = ""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.imports) == 0
        assert len(result.missing_imports) == 0
        assert len(result.errors) == 0
    
    def test_complex_usage_pattern(self):
        """Test analyzing complex usage patterns."""
        source = """
from magic_utils import calculate_magic, MagicProcessor

# Function call with return value usage
result = calculate_magic(42, mode="fast")
print(result.value)
print(result.metadata["key"])

# Class instantiation and method calls
processor = MagicProcessor(config={"threads": 4})
processed = processor.process(data=[1, 2, 3])
processor.save("output.json")
"""
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_source(source)
        
        assert len(result.missing_imports) == 1
        assert len(result.module_usages) == 1
        
        usage = result.module_usages[0]
        assert usage.name == "magic_utils"
        
        # Check function
        func_names = [f.name for f in usage.functions]
        assert "calculate_magic" in func_names
        
        # Check class
        class_names = [c.name for c in usage.classes]
        assert "MagicProcessor" in class_names