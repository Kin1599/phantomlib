"""
Package Generator module for Vibe-Import.

This module handles the generation of Python packages from specifications
using LLM providers.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field

from vibe_import.models import GeneratedPackage, GeneratedFile, GenerationConfig
from vibe_import.extractor import ModuleSpec
from vibe_import.llm.base import LLMProvider, GenerationRequest
from vibe_import.llm.factory import create_provider


@dataclass
class GenerationResult:
    """Result of package generation."""
    package: GeneratedPackage
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tokens_used: int = 0


class CodeParser:
    """Parser for extracting code blocks from LLM responses."""
    
    # Pattern to match code blocks with optional filename
    CODE_BLOCK_PATTERN = re.compile(
        r'```(?:python)?\s*\n'
        r'(?:#\s*filename:\s*([^\n]+)\n)?'
        r'(.*?)'
        r'```',
        re.DOTALL
    )
    
    # Alternative pattern for filename in comments
    FILENAME_COMMENT_PATTERN = re.compile(
        r'^#\s*(?:filename|file):\s*(.+)$',
        re.MULTILINE | re.IGNORECASE
    )
    
    def parse_response(self, response: str, default_module: str) -> list[GeneratedFile]:
        """
        Parse LLM response to extract generated files.
        
        Args:
            response: The LLM response text
            default_module: Default module name if not specified
            
        Returns:
            List of GeneratedFile objects
        """
        files = []
        
        # Find all code blocks
        matches = self.CODE_BLOCK_PATTERN.findall(response)
        
        if not matches:
            # Try to extract code without proper blocks
            return self._parse_unstructured(response, default_module)
        
        for filename, code in matches:
            filename = filename.strip() if filename else None
            code = code.strip()
            
            if not code:
                continue
            
            # Try to extract filename from code if not in block header
            if not filename:
                filename_match = self.FILENAME_COMMENT_PATTERN.search(code)
                if filename_match:
                    filename = filename_match.group(1).strip()
                    # Remove the filename comment from code
                    code = self.FILENAME_COMMENT_PATTERN.sub('', code, count=1).strip()
            
            # Generate default filename if still not found
            if not filename:
                filename = self._generate_filename(code, default_module, len(files))
            
            # Normalize the filename
            filename = self._normalize_filename(filename, default_module)
            
            files.append(GeneratedFile(path=filename, content=code))
        
        # Ensure we have an __init__.py
        files = self._ensure_init_file(files, default_module)
        
        return files
    
    def _parse_unstructured(self, response: str, default_module: str) -> list[GeneratedFile]:
        """Parse response that doesn't have proper code blocks."""
        # Try to find Python code
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Heuristic: lines that look like Python code
            if line.strip().startswith(('import ', 'from ', 'def ', 'class ', '@', '#')):
                in_code = True
            
            if in_code:
                code_lines.append(line)
        
        if code_lines:
            code = '\n'.join(code_lines)
            return [GeneratedFile(
                path=f"{default_module}/__init__.py",
                content=code
            )]
        
        return []
    
    def _generate_filename(self, code: str, module: str, index: int) -> str:
        """Generate a filename based on code content."""
        # Check if code defines a class
        class_match = re.search(r'^class\s+(\w+)', code, re.MULTILINE)
        if class_match:
            class_name = class_match.group(1)
            return f"{module}/{self._to_snake_case(class_name)}.py"
        
        # Check if code has a main function
        if re.search(r'^def\s+main\s*\(', code, re.MULTILINE):
            return f"{module}/__main__.py"
        
        # Default to __init__.py for first file, otherwise numbered
        if index == 0:
            return f"{module}/__init__.py"
        else:
            return f"{module}/module_{index}.py"
    
    def _normalize_filename(self, filename: str, module: str) -> str:
        """Normalize filename to be within the module directory."""
        # Remove leading slashes
        filename = filename.lstrip('/')
        
        # If filename doesn't start with module name, add it
        if not filename.startswith(module):
            if filename.startswith('__'):
                filename = f"{module}/{filename}"
            elif '/' not in filename:
                filename = f"{module}/{filename}"
        
        # Ensure .py extension
        if not filename.endswith('.py'):
            filename += '.py'
        
        return filename
    
    def _ensure_init_file(
        self, 
        files: list[GeneratedFile], 
        module: str
    ) -> list[GeneratedFile]:
        """Ensure the package has an __init__.py file."""
        init_path = f"{module}/__init__.py"
        
        has_init = any(f.path == init_path for f in files)
        
        if not has_init and files:
            # Generate __init__.py with exports
            exports = self._extract_exports(files)
            init_content = self._generate_init_content(module, files, exports)
            files.insert(0, GeneratedFile(path=init_path, content=init_content))
        
        return files
    
    def _extract_exports(self, files: list[GeneratedFile]) -> list[str]:
        """Extract public names from generated files."""
        exports = []
        
        for file in files:
            if file.path.endswith('__init__.py'):
                continue
            
            # Find class definitions
            for match in re.finditer(r'^class\s+(\w+)', file.content, re.MULTILINE):
                name = match.group(1)
                if not name.startswith('_'):
                    exports.append(name)
            
            # Find function definitions
            for match in re.finditer(r'^def\s+(\w+)', file.content, re.MULTILINE):
                name = match.group(1)
                if not name.startswith('_'):
                    exports.append(name)
        
        return exports
    
    def _generate_init_content(
        self, 
        module: str, 
        files: list[GeneratedFile],
        exports: list[str]
    ) -> str:
        """Generate __init__.py content."""
        lines = [
            f'"""',
            f'{module} - Auto-generated package by Vibe-Import',
            f'"""',
            '',
        ]
        
        # Add imports from submodules
        for file in files:
            if file.path.endswith('__init__.py'):
                continue
            
            # Get module name from path
            submodule = Path(file.path).stem
            
            # Find exports in this file
            file_exports = []
            for match in re.finditer(r'^(?:class|def)\s+(\w+)', file.content, re.MULTILINE):
                name = match.group(1)
                if not name.startswith('_'):
                    file_exports.append(name)
            
            if file_exports:
                names = ', '.join(file_exports)
                lines.append(f'from .{submodule} import {names}')
        
        if exports:
            lines.extend([
                '',
                '__all__ = [',
            ])
            for name in exports:
                lines.append(f'    "{name}",')
            lines.append(']')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class PackageGenerator:
    """
    Main class for generating Python packages from specifications.
    """
    
    def __init__(
        self,
        config: GenerationConfig | None = None,
        provider: LLMProvider | None = None,
    ):
        self.config = config or GenerationConfig()
        self.provider = provider or create_provider(
            provider=self.config.llm_provider,
            model=self.config.llm_model,
        )
        self.parser = CodeParser()
    
    def generate(
        self,
        spec: ModuleSpec,
        context: str = "",
    ) -> GenerationResult:
        """
        Generate a package from a module specification.
        
        Args:
            spec: The module specification
            context: Optional context (e.g., original source code)
            
        Returns:
            GenerationResult with the generated package
        """
        errors = []
        warnings = []
        
        # Create the generation request
        request = GenerationRequest(
            module_name=spec.name,
            specification=spec.to_prompt_context(),
            context=context,
            style_guide=self._get_style_guide(),
        )
        
        # Generate code using LLM
        try:
            response = self.provider.generate_code(
                request=request,
                temperature=self.config.temperature,
            )
        except Exception as e:
            return GenerationResult(
                package=GeneratedPackage(name=spec.name),
                success=False,
                errors=[f"LLM generation failed: {e}"],
            )
        
        # Parse the response
        files = self.parser.parse_response(response.content, spec.name)
        
        if not files:
            errors.append("No code was generated from the LLM response")
            return GenerationResult(
                package=GeneratedPackage(name=spec.name),
                success=False,
                errors=errors,
            )
        
        # Validate generated code
        validation_errors, validation_warnings = self._validate_files(files, spec)
        errors.extend(validation_errors)
        warnings.extend(validation_warnings)
        
        # Create the package
        package = GeneratedPackage(
            name=spec.name,
            files=files,
        )
        
        return GenerationResult(
            package=package,
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            tokens_used=response.total_tokens,
        )
    
    def generate_multiple(
        self,
        specs: list[ModuleSpec],
        context: str = "",
    ) -> list[GenerationResult]:
        """
        Generate multiple packages from specifications.
        
        Args:
            specs: List of module specifications
            context: Optional context
            
        Returns:
            List of GenerationResult for each spec
        """
        results = []
        for spec in specs:
            result = self.generate(spec, context)
            results.append(result)
        return results
    
    def save_package(
        self,
        package: GeneratedPackage,
        output_dir: str | Path | None = None,
    ) -> Path:
        """
        Save a generated package to disk.
        
        Args:
            package: The generated package
            output_dir: Output directory (defaults to config.output_dir)
            
        Returns:
            Path to the created package directory
        """
        output_dir = Path(output_dir or self.config.output_dir)
        package_dir = output_dir / package.name
        
        # Create package directory
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Write all files
        for file in package.files:
            file_path = output_dir / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content, encoding='utf-8')
        
        # Write documentation if present
        if package.documentation:
            readme_path = package_dir / "README.md"
            readme_path.write_text(package.documentation, encoding='utf-8')
        
        return package_dir
    
    def _get_style_guide(self) -> str:
        """Get the style guide for code generation."""
        guides = {
            "google": "Use Google-style docstrings",
            "numpy": "Use NumPy-style docstrings",
            "sphinx": "Use Sphinx-style docstrings (reStructuredText)",
        }
        
        style = guides.get(self.config.docstring_style, guides["google"])
        
        return f"""
{style}
- Use type hints for all function parameters and return values
- Follow PEP 8 naming conventions
- Keep functions focused and single-purpose
- Add inline comments for complex logic
"""
    
    def _validate_files(
        self,
        files: list[GeneratedFile],
        spec: ModuleSpec,
    ) -> tuple[list[str], list[str]]:
        """
        Validate generated files against the specification.
        
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check for syntax errors
        for file in files:
            try:
                compile(file.content, file.path, 'exec')
            except SyntaxError as e:
                errors.append(f"Syntax error in {file.path}: {e}")
        
        # Check that required functions exist
        all_content = '\n'.join(f.content for f in files)
        
        for func in spec.functions:
            if f"def {func.name}" not in all_content:
                warnings.append(f"Function '{func.name}' not found in generated code")
        
        for cls in spec.classes:
            if f"class {cls.name}" not in all_content:
                warnings.append(f"Class '{cls.name}' not found in generated code")
        
        return errors, warnings