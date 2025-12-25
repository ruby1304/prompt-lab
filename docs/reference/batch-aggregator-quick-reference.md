# Batch Aggregator Quick Reference

## Overview

The `BatchAggregator` provides aggregation capabilities for batch processing in pipelines. It supports multiple strategies for combining and transforming batch results.

## Basic Usage

```python
from src.batch_aggregator import BatchAggregator

aggregator = BatchAggregator()
```

## Aggregation Strategies

### 1. Concat (拼接聚合)

Concatenate items into a single string.

```python
# Simple usage
items = ["hello", "world", "test"]
result = aggregator.aggregate_concat(items, separator=" ")
# Result: "hello world test"

# With dict items
items = [
    {"text": "First result"},
    {"text": "Second result"}
]
result = aggregator.aggregate_concat(items, separator="\n")
# Result: "First result\nSecond result"

# Using aggregate method
result = aggregator.aggregate(items, strategy="concat", separator=", ")
print(result.success)  # True
print(result.result)   # "First result, Second result"
```

**Supported dict fields**: `text`, `output`, `result`

### 2. Stats (统计聚合)

Calculate statistics on numeric fields.

```python
items = [
    {"score": 85, "time": 1.2},
    {"score": 90, "time": 1.5},
    {"score": 78, "time": 1.1}
]

result = aggregator.aggregate_stats(items, fields=["score", "time"])

# Access statistics
print(result["total_items"])           # 3
print(result["fields"]["score"]["mean"])   # 84.33
print(result["fields"]["score"]["min"])    # 78
print(result["fields"]["score"]["max"])    # 90
print(result["fields"]["score"]["median"]) # 85
print(result["fields"]["score"]["stdev"])  # 6.03
```

**Available statistics**: count, sum, mean, min, max, median, stdev

### 3. Filter (过滤聚合)

Filter items based on a condition.

```python
items = [
    {"score": 85, "passed": True},
    {"score": 45, "passed": False},
    {"score": 90, "passed": True}
]

# Filter by boolean field
result = aggregator.aggregate_filter(
    items,
    condition=lambda x: x.get("passed", False)
)
# Result: [{"score": 85, "passed": True}, {"score": 90, "passed": True}]

# Filter by numeric condition
result = aggregator.aggregate_filter(
    items,
    condition=lambda x: x.get("score", 0) >= 80
)
# Result: [{"score": 85, ...}, {"score": 90, ...}]
```

### 4. Custom (自定义聚合)

Execute custom aggregation code (Coming in Task 57).

```python
# Will be implemented with CodeExecutor integration
result = aggregator.aggregate_custom(
    items,
    code="def aggregate(items): return sum(item['score'] for item in items)",
    language="python"
)
```

## Using the Aggregate Method

The `aggregate()` method provides a unified interface:

```python
result = aggregator.aggregate(
    items,
    strategy="concat",  # or "stats", "filter", "custom"
    separator="\n",     # strategy-specific parameters
    fields=["score"],
    condition=lambda x: x["passed"]
)

# Check result
if result.success:
    print(f"Result: {result.result}")
    print(f"Strategy: {result.strategy}")
    print(f"Items processed: {result.item_count}")
else:
    print(f"Error: {result.error}")
```

## AggregationResult

All aggregation operations return an `AggregationResult`:

```python
@dataclass
class AggregationResult:
    success: bool           # Whether aggregation succeeded
    result: Any            # The aggregated result
    error: Optional[str]   # Error message if failed
    strategy: Optional[str] # Strategy used
    item_count: int        # Number of items processed
```

## Pipeline Configuration

Use in pipeline YAML:

```yaml
steps:
  - id: "aggregate_results"
    type: "batch_aggregator"
    aggregation_strategy: "concat"  # or "stats", "filter", "custom"
    separator: "\n"                 # for concat
    fields: ["score", "time"]       # for stats
    condition: "lambda x: x['passed']"  # for filter
    input_mapping:
      items: "previous_step_output"
    output_key: "aggregated_result"
```

## Error Handling

```python
# Empty items
result = aggregator.aggregate([], strategy="concat")
assert result.success == True
assert result.result is None

# Invalid strategy
result = aggregator.aggregate(items, strategy="invalid")
assert result.success == False
assert "Unsupported aggregation strategy" in result.error

# Missing required parameters
try:
    result = aggregator.aggregate_stats(items, fields=[])
except ValueError as e:
    print(f"Error: {e}")  # "No fields specified for stats aggregation"
```

## Best Practices

1. **Choose the right strategy**:
   - Use `concat` for combining text outputs
   - Use `stats` for analyzing numeric metrics
   - Use `filter` for selecting specific items
   - Use `custom` for complex transformations

2. **Handle empty results**:
   ```python
   result = aggregator.aggregate(items, strategy="concat")
   if result.success and result.result:
       # Process result
       pass
   ```

3. **Check field availability for stats**:
   ```python
   result = aggregator.aggregate_stats(items, fields=["score"])
   if "error" not in result["fields"]["score"]:
       mean = result["fields"]["score"]["mean"]
   ```

4. **Use structured results**:
   ```python
   result = aggregator.aggregate(items, strategy="filter", condition=my_condition)
   if result.success:
       filtered_items = result.result
       print(f"Filtered {result.item_count} items to {len(filtered_items)}")
   ```

## Common Patterns

### Combining Multiple Strategies

```python
# First filter, then calculate stats
filtered = aggregator.aggregate_filter(items, condition=lambda x: x["passed"])
stats = aggregator.aggregate_stats(filtered, fields=["score"])
```

### Processing Pipeline Results

```python
# Collect results from multiple test cases
test_results = [
    {"test_id": 1, "output": "Result 1", "score": 85},
    {"test_id": 2, "output": "Result 2", "score": 90},
    {"test_id": 3, "output": "Result 3", "score": 78}
]

# Concatenate outputs
combined_output = aggregator.aggregate_concat(
    test_results,
    separator="\n---\n"
)

# Calculate statistics
stats = aggregator.aggregate_stats(
    test_results,
    fields=["score"]
)

print(f"Combined output:\n{combined_output}")
print(f"Average score: {stats['fields']['score']['mean']}")
```

## See Also

- [Batch Processing Config Guide](batch-processing-config-guide.md)
- [Pipeline Guide](pipeline-guide.md)
- [Code Node Guide](code-node-quick-reference.md)
