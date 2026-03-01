"""Tests for the package generator module."""

import pytest
from vibe_import.generator import CodeParser, PackageGenerator, GenerationResult
from vibe_import.extractor import ModuleSpec, FunctionSpec, ClassSpec
from vibe_import.models import GeneratedPackage, GeneratedFile, GenerationConfig


class TestCodeParser:
    """Tests for CodeParser."""
    
    def test_parse_single_code_block(self):
        """Test parsing a single code block."""
        response = '''Here's the generated code:

```python
# filename: mypackage/__init__.py
def hello():
    return "Hello, World!"
```
'''
        parser = CodeParser()
        files = parser.parse_response(response, "mypackage")
        
        assert len(files) == 1
        assert files[0].path == "mypackage/__init__.py"
        assert "def hello" in files[0].content
    
    def test_parse_multiple_code_blocks(self):
        """Test parsing multiple code blocks."""
        response = '''Here are the generated files:

```python
# filename: mypackage/__init__.py
from .utils import helper
```

```python
# filename: mypackage/utils.py
def helper():
    pass
```
'''
        parser = CodeParser()
        files = parser.parse_response(response, "mypackage")
        
        assert len(files) == 2
        paths = [f.path for f in files]
        assert "mypackage/__init__.py" in paths
        assert "mypackage/utils.py" in paths
    
    def test_parse_without_filename_comment(self):
        """Test parsing code block without filename comment."""
        response = '''```python
def calculate(x, y):
    return x + y
```
'''
        parser = CodeParser()
        files = parser.parse_response(response, "mypackage")
        
        assert len(files) == 1
        # Should generate a default filename
        assert files[0].path.startswith("mypackage/")
        assert files[0].path.endswith(".py")
    
    def test_ensure_init_file(self):
        """Test that __init__.py is ensured."""
        response = '''```python
# filename: mypackage/utils.py
def helper():
    pass
```
'''
        parser = CodeParser()
        files = parser.parse_response(response, "mypackage")
        
        paths = [f.path for f in files]
        assert "mypackage/__init__.py" in paths
    
    def test_to_snake_case(self):
        """Test CamelCase to snake_case conversion."""
        assert CodeParser._to_snake_case("MyClass") == "my_class"
        assert CodeParser._to_snake_case("HTTPServer") == "http_server"
        assert CodeParser._to_snake_case("SimpleXMLParser") == "simple_xml_parser"
    
    def test_extract_exports(self):
        """Test extracting exports from files."""
        files = [
            GeneratedFile(
                path="mypackage/utils.py",
                content='''
class MyClass:
    pass

def public_func():
    pass

def _private_func():
    pass
'''
            )
        ]
        
        parser = CodeParser()
        exports = parser._extract_exports(files)
        
        assert "MyClass" in exports
        assert "public_func" in exports
        assert "_private_func" not in exports


class TestPackageGenerator:
    """Tests for PackageGenerator."""
    
    def test_validate_files_syntax_error(self):
        """Test validation catches syntax errors."""
        files = [
            GeneratedFile(
                path="mypackage/__init__.py",
                content="def broken("
            )
        ]
        
        spec = ModuleSpec(name="mypackage")
        generator = PackageGenerator()
        
        errors, warnings = generator._validate_files(files, spec)
        
        assert len(errors) > 0
        assert "Syntax error" in errors[0]
    
    def test_validate_files_missing_function(self):
        """Test validation warns about missing functions."""
        files = [
            GeneratedFile(
                path="mypackage/__init__.py",
                content="# Empty file"
            )
        ]
        
        spec = ModuleSpec(
            name="mypackage",
            functions=[FunctionSpec(name="expected_func", parameters=[], return_type="Any")]
        )
        generator = PackageGenerator()
        
        errors, warnings = generator._validate_files(files, spec)
        
        assert any("expected_func" in w for w in warnings)
    
    def test_validate_files_valid_code(self):
        """Test validation passes for valid code."""
        files = [
            GeneratedFile(
                path="mypackage/__init__.py",
                content='''
def calculate(x: int) -> int:
    return x * 2
'''
            )
        ]
        
        spec = ModuleSpec(
            name="mypackage",
            functions=[FunctionSpec(name="calculate", parameters=[("x", "int")], return_type="int")]
        )
        generator = PackageGenerator()
        
        errors, warnings = generator._validate_files(files, spec)
        
        assert len(errors) == 0


class TestGeneratedPackage:
    """Tests for GeneratedPackage."""
    
    def test_get_file(self):
        """Test getting a file by path."""
        package = GeneratedPackage(
            name="mypackage",
            files=[
                GeneratedFile(path="mypackage/__init__.py", content="# init"),
                GeneratedFile(path="mypackage/utils.py", content="# utils"),
            ]
        )
        
        init_file = package.get_file("mypackage/__init__.py")
        assert init_file is not None
        assert init_file.content == "# init"
        
        missing = package.get_file("mypackage/missing.py")
        assert missing is None
    
    def test_add_file(self):
        """Test adding a file to package."""
        package = GeneratedPackage(name="mypackage")
        
        package.add_file("mypackage/__init__.py", "# content")
        
        assert len(package.files) == 1
        assert package.files[0].path == "mypackage/__init__.py"


class TestGeneratedFile:
    """Tests for GeneratedFile."""
    
    def test_filename_property(self):
        """Test getting filename from path."""
        file = GeneratedFile(
            path="mypackage/subdir/utils.py",
            content=""
        )
        
        assert file.filename == "utils.py"