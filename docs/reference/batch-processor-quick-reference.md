# BatchProcessor Quick Reference

## Overview

The `BatchProcessor` class provides batch processing capabilities for handling large datasets efficiently. It supports configurable batch sizes, concurrent processing, and robust error handling.

**Location**: `src/batch_aggregator.py`  
**Requirements**: 4.2

## Quick Start

```python
from src.batch_aggregator import BatchProcessor

# Initialize processor
processor = BatchProcessor(max_workers=4)

# Process items in batches
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
results = processor.process_in_batches(
    items,
    lambda x: x * 2,
    batch_size=3,
    concurrent=True
)
# Results: [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
```

## Class Reference

### BatchProcessor

```python
class BatchProcessor:
    def __init__(self, max_workers: int = 4)
```

**Parameters**:
- `max_workers`: Maximum number of concurrent workers (default: 4)

### Methods

#### process_in_batches()

Process items in batches with optional concurrency.

```python
def process_in_batches(
    self,
    items: List[Any],
    processor: Callable,
    batch_size: int = 10,
    concurrent: bool = True
) -> List[Any]
```

**Parameters**:
- `items`: List of items to process
- `processor`: Function to process each item (must accept single item)
- `batch_size`: Number of items per batch (default: 10)
- `concurrent`: Whether to process batches concurrently (default: True)

**Returns**: List of processed results (None for failed items)

**Raises**:
- `ValueError`: If batch_size < 1 or processor is not callable

**Example**:
```python
processor = BatchProcessor()
items = [1, 2, 3, 4, 5]

def square(x):
    return x ** 2

results = processor.process_in_batches(items, square, batch_size=2)
# Results: [1, 4, 9, 16, 25]
```

#### process_in_batches_detailed()

Process items with detailed result information.

```python
def process_in_batches_detailed(
    self,
    items: List[Any],
    processor: Callable,
    batch_size: int = 10,
    concurrent: bool = True
) -> BatchProcessingResult
```

**Parameters**: Same as `process_in_batches()`

**Returns**: `BatchProcessingResult` object with detailed information

**Example**:
```python
result = processor.process_in_batches_detailed(items, square, batch_size=2)

print(f"Success: {result.success}")
print(f"Total items: {result.total_items}")
print(f"Batch count: {result.batch_count}")
print(f"Failed items: {result.failed_items}")
print(f"Execution time: {result.execution_time}s")
```

## Data Classes

### BatchProcessingResult

```python
@dataclass
class BatchProcessingResult:
    success: bool                    # Overall success status
    results: List[Any]               # List of processed results
    total_items: int                 # Total number of items
    batch_count: int                 # Number of batches created
    failed_items: List[int] = []     # Indices of failed items
    execution_time: float = 0.0      # Total execution time (seconds)
    error: Optional[str] = None      # Error message if failed
```

**Methods**:
- `to_dict()`: Convert to dictionary format

## Usage Patterns

### Sequential Processing

```python
processor = BatchProcessor()
results = processor.process_in_batches(
    items,
    processor_func,
    batch_size=10,
    concurrent=False  # Sequential processing
)
```

### Concurrent Processing

```python
processor = BatchProcessor(max_workers=8)
results = processor.process_in_batches(
    items,
    processor_func,
    batch_size=10,
    concurrent=True  # Concurrent processing
)
```

### Error Handling

```python
# Items that fail will return None
items = [10, 5, 0, 8]  # 0 will cause division error

def divide_100_by(x):
    return 100 / x

results = processor.process_in_batches(items, divide_100_by)
# Results: [10.0, 20.0, None, 12.5]

# Check for failures
failed_indices = [i for i, r in enumerate(results) if r is None]
print(f"Failed items at indices: {failed_indices}")
```

### Processing Dictionaries

```python
items = [
    {"name": "Alice", "score": 85},
    {"name": "Bob", "score": 90},
    {"name": "Charlie", "score": 78}
]

def calculate_grade(student):
    score = student["score"]
    grade = "A" if score >= 90 else "B" if score >= 80 else "C"
    return {"name": student["name"], "grade": grade}

results = processor.process_in_batches(items, calculate_grade, batch_size=2)
```

### Large Dataset Processing

```python
# Process 1000 items in batches of 50
large_dataset = list(range(1000))

results = processor.process_in_batches(
    large_dataset,
    lambda x: x * 2,
    batch_size=50,
    concurrent=True
)
```

## Performance Considerations

### Batch Size Selection

- **Small batches (5-10)**: More overhead, better for quick operations
- **Medium batches (10-50)**: Balanced approach, good for most cases
- **Large batches (50-100)**: Less overhead, better for I/O-bound operations

### Concurrency

- **Concurrent=True**: Best for I/O-bound operations (API calls, file I/O)
- **Concurrent=False**: Best for CPU-bound operations or when order matters
- **Max Workers**: Set based on available CPU cores and operation type

### Memory Usage

- Larger batch sizes use more memory
- Concurrent processing may use more memory due to parallel execution
- Consider memory constraints when processing large datasets

## Error Handling

### Individual Item Failures

```python
# Failed items return None
results = processor.process_in_batches(items, risky_function)

# Filter successful results
successful = [r for r in results if r is not None]
failed_count = len([r for r in results if r is None])
```

### Detailed Error Information

```python
result = processor.process_in_batches_detailed(items, risky_function)

if not result.success:
    print(f"Processing failed: {result.error}")
else:
    print(f"Failed {len(result.failed_items)} out of {result.total_items} items")
    print(f"Failed indices: {result.failed_items}")
```

## Integration Examples

### With Pipeline

```python
# In a pipeline step
def process_pipeline_batch(pipeline_outputs):
    processor = BatchProcessor(max_workers=4)
    
    # Extract data from pipeline outputs
    items = [output["data"] for output in pipeline_outputs]
    
    # Process in batches
    results = processor.process_in_batches(
        items,
        transform_function,
        batch_size=10,
        concurrent=True
    )
    
    return results
```

### With Aggregation

```python
from src.batch_aggregator import BatchProcessor, BatchAggregator

# Process items
processor = BatchProcessor()
results = processor.process_in_batches(items, process_func, batch_size=10)

# Aggregate results
aggregator = BatchAggregator()
aggregated = aggregator.aggregate(results, strategy="concat", separator="\n")
```

## Best Practices

1. **Choose appropriate batch size**: Balance between overhead and memory usage
2. **Use concurrent processing for I/O**: Significant speedup for network/disk operations
3. **Handle errors gracefully**: Check for None results and log failures
4. **Monitor performance**: Use `process_in_batches_detailed()` to track execution time
5. **Validate inputs**: Ensure processor function can handle all item types
6. **Consider memory constraints**: Adjust batch size for large datasets

## Common Pitfalls

1. **Too small batch size**: Excessive overhead from batch management
2. **Too large batch size**: Memory issues with large datasets
3. **Ignoring failed items**: Always check for None results
4. **Wrong concurrency mode**: CPU-bound tasks may not benefit from concurrency
5. **Not handling exceptions**: Processor function should handle expected errors

## Testing

```python
import pytest
from src.batch_aggregator import BatchProcessor

def test_batch_processing():
    processor = BatchProcessor()
    items = [1, 2, 3, 4, 5]
    
    results = processor.process_in_batches(
        items,
        lambda x: x * 2,
        batch_size=2,
        concurrent=False
    )
    
    assert results == [2, 4, 6, 8, 10]
```

## See Also

- [Batch Aggregator Quick Reference](batch-aggregator-quick-reference.md)
- [Batch Processing Config Guide](batch-processing-config-guide.md)
- [Custom Aggregation Guide](custom-aggregation-guide.md)
- Demo: `examples/batch_data_processor_demo.py`
