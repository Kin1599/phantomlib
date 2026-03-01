"""
Example file demonstrating Vibe-Import usage.

This file contains imports that don't exist yet. Running vibe-import
on this file will analyze the usage patterns and generate the missing
packages.

Usage:
    vibe-import analyze examples/example_usage.py --show-usage
    vibe-import generate examples/example_usage.py --output ./generated --dry-run
"""

# These imports don't exist - Vibe-Import will generate them!
from magic_utils import calculate_magic, MagicProcessor, MAGIC_CONSTANT
from data_helpers import DataPipeline, transform_records, validate_schema


def main():
    """Main function demonstrating usage of non-existent packages."""
    
    # Using a function with positional and keyword arguments
    result = calculate_magic(42, mode="fast", precision=0.001)
    print(f"Magic result: {result.value}")
    print(f"Confidence: {result.confidence}")
    
    # Using a constant
    threshold = MAGIC_CONSTANT * 2
    
    # Using a class with various features
    processor = MagicProcessor(
        config={"threads": 4, "cache_size": 1000},
        name="main_processor",
        verbose=True
    )
    
    # Method calls
    processor.initialize()
    processed_data = processor.process(data=[1, 2, 3, 4, 5])
    processor.save("output.json")
    
    # Accessing attributes
    print(f"Processor status: {processor.status}")
    print(f"Items processed: {processor.count}")
    
    # Using as context manager
    with DataPipeline(source="database", batch_size=100) as pipeline:
        # Fetch data
        raw_data = pipeline.fetch()
        
        # Transform using a function
        cleaned = transform_records(raw_data, remove_nulls=True, normalize=True)
        
        # Validate
        is_valid = validate_schema(cleaned, schema_name="user_data")
        
        if is_valid:
            pipeline.save(cleaned, format="parquet")
        else:
            print("Validation failed!")
    
    # Using iteration
    for batch in processor:
        print(f"Processing batch: {batch}")


if __name__ == "__main__":
    main()