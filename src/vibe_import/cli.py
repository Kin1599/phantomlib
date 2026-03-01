"""
Command-line interface for Vibe-Import.

This module provides the CLI for analyzing code and generating packages.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from vibe_import.analyzer import CodeAnalyzer
from vibe_import.extractor import UsageExtractor
from vibe_import.generator import PackageGenerator
from vibe_import.docs_generator import DocumentationGenerator
from vibe_import.models import GenerationConfig, AnalysisResult, PyPIPackage


console = Console()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]Warning:[/yellow] {message}")


@click.group()
@click.version_option(version="0.1.0", prog_name="vibe-import")
def main():
    """
    Vibe-Import: Automatically generate missing Python packages.
    
    Analyze your code to find imports that don't exist, then generate
    complete implementations using LLM.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--recursive", "-r",
    is_flag=True,
    default=False,
    help="Recursively analyze directories"
)
@click.option(
    "--show-usage", "-u",
    is_flag=True,
    default=False,
    help="Show detailed usage information"
)
@click.option(
    "--ignore-pypi",
    is_flag=True,
    default=False,
    help="Ignore PyPI and treat all non-stdlib packages as missing"
)
def analyze(path: str, recursive: bool, show_usage: bool, ignore_pypi: bool):
    """
    Analyze Python code for missing imports.
    
    PATH can be a Python file or directory.
    """
    path_obj = Path(path)
    analyzer = CodeAnalyzer(check_pypi=not ignore_pypi)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing code...", total=None)
        
        if path_obj.is_file():
            results = [analyzer.analyze_file(path_obj)]
        else:
            results = analyzer.analyze_directory(path_obj, recursive=recursive)
    
    # Display results
    _display_analysis_results(results, show_usage)


def _display_analysis_results(results: list[AnalysisResult], show_usage: bool) -> None:
    """Display analysis results in a formatted way."""
    total_missing = 0
    total_pypi = 0
    
    for result in results:
        if result.errors:
            for error in result.errors:
                print_error(f"{result.file_path}: {error}")
            continue
        
        # Show PyPI packages first
        if result.pypi_packages:
            total_pypi += len(result.pypi_packages)
            console.print(f"\n[bold]{result.file_path}[/bold]")
            console.print("[yellow]Packages available on PyPI (not installed):[/yellow]")
            
            pypi_table = Table(show_header=True, header_style="bold yellow")
            pypi_table.add_column("Package")
            pypi_table.add_column("Install Command")
            pypi_table.add_column("Import")
            
            for pkg in result.pypi_packages:
                pypi_table.add_row(
                    f"[bold]{pkg.name}[/bold]",
                    f"[cyan]{pkg.install_command}[/cyan]",
                    str(pkg.import_info),
                )
            
            console.print(pypi_table)
            console.print("[dim]Tip: Run the install command above to install these packages.[/dim]\n")
        
        if not result.missing_imports:
            continue
        
        total_missing += len(result.missing_imports)
        
        # Create a panel for each file with missing imports
        console.print(f"\n[bold]{result.file_path}[/bold]")
        
        # Missing imports table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Import Statement")
        table.add_column("Line")
        table.add_column("Type")
        
        for imp in result.missing_imports:
            import_str = str(imp)
            import_type = "from import" if imp.is_from_import else "import"
            table.add_row(import_str, str(imp.line_number), import_type)
        
        console.print(table)
        
        # Show usage details if requested
        if show_usage and result.module_usages:
            for usage in result.module_usages:
                tree = Tree(f"[bold blue]{usage.name}[/bold blue]")
                
                if usage.functions:
                    func_branch = tree.add("[green]Functions[/green]")
                    for func in usage.functions:
                        sig = func.get_signature()
                        func_branch.add(f"[cyan]{sig}[/cyan]")
                
                if usage.classes:
                    class_branch = tree.add("[yellow]Classes[/yellow]")
                    for cls in usage.classes:
                        cls_node = class_branch.add(f"[cyan]{cls.name}[/cyan]")
                        if cls.methods_called:
                            for method in cls.methods_called:
                                cls_node.add(f".{method.name}()")
                        if cls.attributes_accessed:
                            for attr in cls.attributes_accessed:
                                cls_node.add(f".{attr}")
                
                console.print(tree)
    
    # Summary
    if total_pypi > 0:
        console.print(f"\n[bold yellow]Packages available on PyPI:[/bold yellow] {total_pypi}")
        console.print("[dim]Install them with the commands shown above.[/dim]")
    
    if total_missing == 0 and total_pypi == 0:
        print_success("No missing imports found!")
    elif total_missing > 0:
        console.print(f"\n[bold]Total missing imports (to generate):[/bold] {total_missing}")


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=".",
    help="Output directory for generated packages"
)
@click.option(
    "--provider", "-p",
    type=click.Choice(["openai", "anthropic", "openrouter"]),
    default="openrouter",
    help="LLM provider to use (openrouter has free models)"
)
@click.option(
    "--model", "-m",
    type=str,
    default=None,
    help="Model name (defaults to provider's default)"
)
@click.option(
    "--api-key", "-k",
    type=str,
    default=None,
    help="API key (or set via environment variable)"
)
@click.option(
    "--temperature", "-t",
    type=float,
    default=0.2,
    help="Generation temperature (0-1)"
)
@click.option(
    "--no-docs",
    is_flag=True,
    default=False,
    help="Skip documentation generation"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Analyze and show what would be generated without actually generating"
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    default=False,
    help="Recursively analyze directories"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed progress information"
)
@click.option(
    "--ignore-pypi",
    is_flag=True,
    default=False,
    help="Ignore PyPI and generate packages even if they exist there"
)
def generate(
    path: str,
    output: str,
    provider: str,
    model: Optional[str],
    api_key: Optional[str],
    temperature: float,
    no_docs: bool,
    dry_run: bool,
    recursive: bool,
    verbose: bool,
    ignore_pypi: bool,
):
    """
    Generate missing packages from Python code.
    
    PATH can be a Python file or directory.
    """
    path_obj = Path(path)
    output_path = Path(output)
    
    # Step 1: Analyze
    console.print("[bold]Step 1:[/bold] Analyzing code...")
    analyzer = CodeAnalyzer(check_pypi=not ignore_pypi)
    
    if path_obj.is_file():
        results = [analyzer.analyze_file(path_obj)]
        source_code = path_obj.read_text()
    else:
        results = analyzer.analyze_directory(path_obj, recursive=recursive)
        source_code = ""  # Could concatenate all files if needed
    
    # Check for PyPI packages first
    all_pypi_packages: list[PyPIPackage] = []
    for result in results:
        all_pypi_packages.extend(result.pypi_packages)
    
    if all_pypi_packages:
        console.print("\n[bold yellow]Packages available on PyPI:[/bold yellow]")
        console.print("[dim]These packages exist on PyPI but are not installed.[/dim]\n")
        
        pypi_table = Table(show_header=True, header_style="bold yellow")
        pypi_table.add_column("Package")
        pypi_table.add_column("Install Command")
        
        for pkg in all_pypi_packages:
            pypi_table.add_row(
                f"[bold]{pkg.name}[/bold]",
                f"[cyan]{pkg.install_command}[/cyan]",
            )
        
        console.print(pypi_table)
        console.print("\n[dim]Tip: Install these packages first:[/dim]")
        for pkg in all_pypi_packages:
            console.print(f"  [dim]  {pkg.install_command}[/dim]")
        console.print()
    
    # Check for missing imports
    all_missing = []
    for result in results:
        all_missing.extend(result.module_usages)
    
    if not all_missing:
        if all_pypi_packages:
            console.print("[yellow]Only PyPI packages found. Install them and run again.[/yellow]")
        else:
            print_success("No missing imports found. Nothing to generate.")
        return
    
    # Step 2: Extract specifications
    console.print("[bold]Step 2:[/bold] Extracting specifications...")
    extractor = UsageExtractor()
    specs = extractor.extract_from_results(results)
    
    # Display what will be generated
    console.print("\n[bold]Packages to generate:[/bold]")
    for spec in specs:
        console.print(Panel(
            spec.to_prompt_context(),
            title=f"[bold blue]{spec.name}[/bold blue]",
            border_style="blue",
        ))
    
    if dry_run:
        console.print("\n[yellow]Dry run - no packages generated.[/yellow]")
        return
    
    # Step 3: Generate packages
    console.print("\n[bold]Step 3:[/bold] Generating packages...")
    
    # Load config to get default model
    from vibe_import.config import Config
    loaded_config = Config.load()
    
    # Determine model (priority: CLI > config > default)
    if model:
        default_model = model
    elif loaded_config.llm.model:
        default_model = loaded_config.llm.model
    elif provider == "openai":
        default_model = "gpt-4o"
    elif provider == "anthropic":
        default_model = "claude-sonnet-4-20250514"
    else:  # openrouter
        default_model = "qwen/qwen3-coder:free"
    
    # Show configuration
    console.print(Panel(
        f"[bold]Provider:[/bold] {provider}\n"
        f"[bold]Model:[/bold] {default_model}\n"
        f"[bold]Temperature:[/bold] {temperature}\n"
        f"[bold]Output:[/bold] {output_path}\n"
        f"[bold]Verbose:[/bold] {verbose}",
        title="[bold cyan]Configuration[/bold cyan]",
        border_style="cyan",
    ))
    
    config = GenerationConfig(
        output_dir=str(output_path),
        llm_provider=provider,
        llm_model=default_model,
        temperature=temperature,
    )
    
    # Create provider with API key if provided
    from vibe_import.llm.factory import create_provider
    try:
        llm_provider = create_provider(
            provider=provider,
            api_key=api_key,
            model=config.llm_model,
        )
    except ValueError as e:
        print_error(str(e))
        console.print("\n[bold]Hint:[/bold] Set your API key:")
        if provider == "openrouter":
            console.print("  export OPENROUTER_API_KEY='your-key-here'")
            console.print("  Get free key at: https://openrouter.ai/keys")
        elif provider == "openai":
            console.print("  export OPENAI_API_KEY='your-key-here'")
        elif provider == "anthropic":
            console.print("  export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    generator = PackageGenerator(config=config, provider=llm_provider)
    docs_generator = DocumentationGenerator() if not no_docs else None
    
    total_tokens = 0
    total_packages = len(specs)
    
    for idx, spec in enumerate(specs, 1):
        console.print(f"\n[bold cyan][{idx}/{total_packages}][/bold cyan] Generating [bold]{spec.name}[/bold]...")
        
        if verbose:
            console.print(f"  Functions: {len(spec.functions)}")
            console.print(f"  Classes: {len(spec.classes)}")
            console.print(f"  Constants: {len(spec.constants)}")
        
        # Use a more detailed progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
            disable=not verbose,
        ) as progress:
            task = progress.add_task(
                f"Calling {default_model}...",
                total=100,
            )
            
            # Update progress to show activity
            for i in range(0, 101, 10):
                progress.update(task, advance=10)
                import time
                time.sleep(0.1)  # Small delay to show progress
            
            result = generator.generate(spec, context=source_code)
            progress.update(task, completed=100)
        
        total_tokens += result.tokens_used
        
        if verbose and result.tokens_used:
            console.print(f"  [dim]Tokens used: {result.tokens_used}[/dim]")
        
        if not result.success:
            print_error(f"Failed to generate {spec.name}")
            for error in result.errors:
                print_error(f"  {error}")
            continue
        
        # Add documentation
        if docs_generator:
            if verbose:
                console.print("  Adding documentation...")
            docs_generator.add_documentation_to_package(
                result.package,
                spec,
                original_code=source_code,
            )
        
        # Save package
        if verbose:
            console.print("  Saving package...")
        package_path = generator.save_package(result.package, output_path)
        print_success(f"Generated {spec.name} at {package_path}")
        
        # Show warnings
        for warning in result.warnings:
            print_warning(warning)
        
        # Show generated files
        console.print(f"\n[bold]Generated files for {spec.name}:[/bold]")
        for file in result.package.files:
            console.print(f"  📄 {file.path}")
    
    # Summary
    console.print(f"\n[bold]Generation complete![/bold]")
    console.print(f"Total packages: {total_packages}")
    console.print(f"Total tokens used: {total_tokens}")
    
    if verbose:
        console.print(f"\n[dim]Tip: Use --model to try a faster model:[/dim]")
        console.print(f"  [dim]  vibe-import generate {path} --model meta-llama/llama-3.2-3b-instruct:free[/dim]")


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format", "-f",
    type=click.Choice(["json", "yaml", "text"]),
    default="text",
    help="Output format"
)
def inspect(path: str, format: str):
    """
    Inspect a Python file and show its structure.
    
    Useful for understanding what the analyzer sees.
    """
    import ast
    import json
    
    path_obj = Path(path)
    
    if not path_obj.is_file():
        print_error("Path must be a file")
        return
    
    source = path_obj.read_text()
    
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print_error(f"Syntax error: {e}")
        return
    
    # Extract structure
    structure = {
        "imports": [],
        "functions": [],
        "classes": [],
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                structure["imports"].append({
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names = [a.name for a in node.names]
                structure["imports"].append({
                    "type": "from",
                    "module": node.module,
                    "names": names,
                    "line": node.lineno,
                })
        elif isinstance(node, ast.FunctionDef):
            structure["functions"].append({
                "name": node.name,
                "args": [a.arg for a in node.args.args],
                "line": node.lineno,
            })
        elif isinstance(node, ast.ClassDef):
            methods = [
                n.name for n in node.body 
                if isinstance(n, ast.FunctionDef)
            ]
            structure["classes"].append({
                "name": node.name,
                "methods": methods,
                "line": node.lineno,
            })
    
    # Output
    if format == "json":
        console.print(json.dumps(structure, indent=2))
    elif format == "yaml":
        try:
            import yaml
            console.print(yaml.dump(structure, default_flow_style=False))
        except ImportError:
            print_error("PyYAML not installed. Use --format json instead.")
    else:
        # Text format
        console.print("[bold]Imports:[/bold]")
        for imp in structure["imports"]:
            if imp["type"] == "import":
                alias = f" as {imp['alias']}" if imp["alias"] else ""
                console.print(f"  import {imp['module']}{alias} (line {imp['line']})")
            else:
                names = ", ".join(imp["names"])
                console.print(f"  from {imp['module']} import {names} (line {imp['line']})")
        
        console.print("\n[bold]Functions:[/bold]")
        for func in structure["functions"]:
            args = ", ".join(func["args"])
            console.print(f"  def {func['name']}({args}) (line {func['line']})")
        
        console.print("\n[bold]Classes:[/bold]")
        for cls in structure["classes"]:
            console.print(f"  class {cls['name']} (line {cls['line']})")
            for method in cls["methods"]:
                console.print(f"    - {method}()")


@main.command()
@click.argument("source", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output file (defaults to stdout)"
)
def spec(source: str, output: Optional[str]):
    """
    Generate a specification file from source code.
    
    This creates a JSON specification that can be edited
    and used for generation.
    """
    import json
    
    path_obj = Path(source)
    analyzer = CodeAnalyzer()
    extractor = UsageExtractor()
    
    if path_obj.is_file():
        results = [analyzer.analyze_file(path_obj)]
    else:
        results = analyzer.analyze_directory(path_obj)
    
    specs = extractor.extract_from_results(results)
    
    # Convert to JSON-serializable format
    spec_data = []
    for spec in specs:
        spec_dict = {
            "name": spec.name,
            "functions": [
                {
                    "name": f.name,
                    "parameters": f.parameters,
                    "return_type": f.return_type,
                }
                for f in spec.functions
            ],
            "classes": [
                {
                    "name": c.name,
                    "init_parameters": c.init_parameters,
                    "methods": [
                        {
                            "name": m.name,
                            "parameters": m.parameters,
                            "return_type": m.return_type,
                        }
                        for m in c.methods
                    ],
                    "attributes": c.attributes,
                    "is_context_manager": c.is_context_manager,
                    "is_iterable": c.is_iterable,
                }
                for c in spec.classes
            ],
            "constants": [
                {"name": c.name, "type": c.inferred_type}
                for c in spec.constants
            ],
        }
        spec_data.append(spec_dict)
    
    json_output = json.dumps(spec_data, indent=2)
    
    if output:
        Path(output).write_text(json_output)
        print_success(f"Specification written to {output}")
    else:
        console.print(json_output)

@main.command()
@click.option(
    "--provider", "-p",
    type=click.Choice(["openrouter", "openai", "anthropic"]),
    default="openrouter",
    help="Provider to list models for"
)
def list_models(provider: str):
    """
    List available models for a provider.
    
    Shows free models for OpenRouter and default models for other providers.
    """
    from vibe_import.llm.factory import create_provider
    
    console.print(f"\n[bold]Available models for {provider}:[/bold]\n")
    
    if provider == "openrouter":
        from vibe_import.llm.openrouter_provider import OpenRouterProvider
        models = OpenRouterProvider.list_free_models()
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Model")
        table.add_column("Description")
        
        descriptions = {
            "meta-llama/llama-3.2-3b-instruct:free": "Llama 3.2 3B - Small, fast",
            "google/gemma-2-9b-it:free": "Gemma 2 9B - Good balance",
            "mistralai/mistral-7b-instruct:free": "Mistral 7B - Popular",
            "huggingfaceh4/zephyr-7b-beta:free": "Zephyr 7B - Chat focused",
            "openchat/openchat-7b:free": "OpenChat 7B - Conversational",
            "qwen/qwen3-coder:free": "Qwen 3 Coder - Code focused (default)",
        }
        
        for model in models:
            desc = descriptions.get(model, "")
            table.add_row(model, desc)
        
        console.print(table)
        console.print("\n[yellow]Note:[/yellow] Free models may have rate limits. "
                     "Vibe-Import automatically retries on 429 errors.")
    elif provider == "openai":
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Model")
        table.add_column("Description")
        
        table.add_row("gpt-4o", "Latest GPT-4 model")
        table.add_row("gpt-4o-mini", "Smaller, faster GPT-4")
        table.add_row("gpt-4-turbo", "GPT-4 Turbo")
        table.add_row("gpt-3.5-turbo", "GPT-3.5 Turbo")
        
        console.print(table)
    elif provider == "anthropic":
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Model")
        table.add_column("Description")
        
        table.add_row("claude-sonnet-4-20250514", "Claude Sonnet 4 (default)")
        table.add_row("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet")
        table.add_row("claude-3-opus-20240229", "Claude 3 Opus")
        table.add_row("claude-3-haiku-20240307", "Claude 3 Haiku (fast)")
        
        console.print(table)



@main.command()
def config():
    """
    Show current configuration.
    
    Displays the loaded configuration from vibe-import.toml, .env, and defaults.
    """
    from vibe_import.config import Config
    
    loaded_config = Config.load()
    
    console.print("\n[bold]Current Configuration:[/bold]\n")
    
    # LLM section
    console.print("[bold cyan]LLM Settings:[/bold cyan]")
    console.print(f"  Provider: {loaded_config.llm.provider}")
    console.print(f"  Model: {loaded_config.llm.model or '(default)'}")
    console.print(f"  Temperature: {loaded_config.llm.temperature}")
    console.print(f"  Max Tokens: {loaded_config.llm.max_tokens}")
    if loaded_config.llm.base_url:
        console.print(f"  Base URL: {loaded_config.llm.base_url}")
    
    # Output section
    console.print("\n[bold cyan]Output Settings:[/bold cyan]")
    console.print(f"  Directory: {loaded_config.output.directory}")
    console.print(f"  Include Docs: {loaded_config.output.include_docs}")
    console.print(f"  Include Tests: {loaded_config.output.include_tests}")
    console.print(f"  Docstring Style: {loaded_config.output.docstring_style}")
    console.print(f"  Overwrite: {loaded_config.output.overwrite}")
    
    # Analysis section
    console.print("\n[bold cyan]Analysis Settings:[/bold cyan]")
    console.print(f"  Recursive: {loaded_config.analysis.recursive}")
    console.print(f"  Include Stdlib: {loaded_config.analysis.include_stdlib}")
    console.print(f"  Exclude Patterns: {len(loaded_config.analysis.exclude_patterns)} patterns")
    
    # API Keys status
    console.print("\n[bold cyan]API Keys Status:[/bold cyan]")
    import os
    if loaded_config.llm.provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        status = "[green]✓ Set[/green]" if key else "[red]✗ Not set[/red]"
        console.print(f"  OPENROUTER_API_KEY: {status}")
    elif loaded_config.llm.provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        status = "[green]✓ Set[/green]" if key else "[red]✗ Not set[/red]"
        console.print(f"  OPENAI_API_KEY: {status}")
    elif loaded_config.llm.provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        status = "[green]✓ Set[/green]" if key else "[red]✗ Not set[/red]"
        console.print(f"  ANTHROPIC_API_KEY: {status}")
    
    console.print()


if __name__ == "__main__":
    main()