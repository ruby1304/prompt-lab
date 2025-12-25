# Custom Aggregation Guide

## Overview

The BatchAggregator supports custom aggregation through user-provided Python or JavaScript code. This allows for flexible and powerful data transformations that go beyond the built-in aggregation strategies (concat, stats, filter).

## Basic Usage

### Python Custom Aggregation

```python
from src.batch_aggregator import BatchAggregator

aggregator = BatchAggregator()
items = [{"score": 85}, {"score": 90}, {"score": 78}]

code = """
def aggregate(items):
    scores = [item["score"] for item in items]
    return {
        "average": sum(scores) / len(scores),
        "count": len(scores),
        "max": max(scores),
        "min": min(scores)
    }
"""

result = aggregator.aggregate_custom(items, code, language="python")
print(result)
# Output: {"average": 84.33, "count": 3, "max": 90, "min": 78}
```

### JavaScript Custom Aggregation

```python
from src.batch_aggregator import BatchAggregator

aggregator = BatchAggregator()
items = [{"value": 10}, {"value": 20}, {"value": 30}]

code = """
function aggregate(items) {
    const sum = items.reduce((acc, item) => acc + item.value, 0);
    const avg = sum / items.length;
    
    return {
        sum: sum,
        average: avg,
        count: items.length
    };
}

module.exports = aggregate;
"""

result = aggregator.aggregate_custom(items, code, language="javascript")
print(result)
# Output: {"sum": 60, "average": 20, "count": 3}
```

## Function Signatures

### Python

Your Python code should define an `aggregate` function that takes a list of items and returns the aggregated result:

```python
def aggregate(items):
    # Your aggregation logic here
    return result
```

Alternative function names are also supported:
- `transform(items)`
- `process_data(items)`
- `main(items)`

### JavaScript

Your JavaScript code should export an `aggregate` function:

```javascript
function aggregate(items) {
    // Your aggregation logic here
    return result;
}

module.exports = aggregate;
```

Alternative patterns:
- `exports = aggregate`
- `function transform(items) { ... }`
- `function process_data(items) { ... }`
- `function main(items) { ... }`

## Advanced Examples

### Complex Python Aggregation

```python
code = """
def aggregate(items):
    # Separate passed and failed items
    passed = [item for item in items if item.get("passed", False)]
    failed = [item for item in items if not item.get("passed", False)]
    
    # Calculate statistics
    total = len(items)
    pass_rate = (len(passed) / total * 100) if total > 0 else 0
    
    # Calculate average scores
    avg_passed = sum(item["score"] for item in passed) / len(passed) if passed else 0
    avg_failed = sum(item["score"] for item in failed) / len(failed) if failed else 0
    
    return {
        "total": total,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "pass_rate": pass_rate,
        "avg_passed_score": avg_passed,
        "avg_failed_score": avg_failed
    }
"""

items = [
    {"score": 85, "passed": True},
    {"score": 45, "passed": False},
    {"score": 90, "passed": True},
    {"score": 60, "passed": False}
]

result = aggregator.aggregate_custom(items, code, language="python")
```

### Complex JavaScript Aggregation

```javascript
code = """
function aggregate(items) {
    // Group items by category
    const grouped = items.reduce((acc, item) => {
        const category = item.category || 'uncategorized';
        if (!acc[category]) {
            acc[category] = [];
        }
        acc[category].push(item);
        return acc;
    }, {});
    
    // Calculate statistics per category
    const stats = {};
    for (const [category, categoryItems] of Object.entries(grouped)) {
        const values = categoryItems.map(item => item.value);
        const sum = values.reduce((a, b) => a + b, 0);
        
        stats[category] = {
            count: categoryItems.length,
            sum: sum,
            average: sum / categoryItems.length,
            max: Math.max(...values),
            min: Math.min(...values)
        };
    }
    
    return {
        total_items: items.length,
        categories: Object.keys(grouped),
        stats: stats
    };
}

module.exports = aggregate;
"""
```

## Configuration Options

### Timeout

You can specify a custom timeout for code execution (default is 30 seconds):

```python
result = aggregator.aggregate_custom(
    items,
    code,
    language="python",
    timeout=60  # 60 seconds
)
```

### Via Main Aggregate Method

You can also use custom aggregation through the main `aggregate` method:

```python
result = aggregator.aggregate(
    items,
    strategy="custom",
    code=code,
    language="python",
    timeout=30
)

if result.success:
    print(result.result)
    print(f"Processed {result.item_count} items")
else:
    print(f"Error: {result.error}")
```

## Error Handling

The custom aggregation provides comprehensive error handling:

### Empty Code

```python
try:
    result = aggregator.aggregate_custom(items, "", language="python")
except ValueError as e:
    print(f"Error: {e}")
    # Output: Error: Custom aggregation code cannot be empty
```

### Unsupported Language

```python
try:
    result = aggregator.aggregate_custom(items, code, language="ruby")
except ValueError as e:
    print(f"Error: {e}")
    # Output: Error: Unsupported language: ruby. Supported languages: python, javascript
```

### Syntax Errors

```python
code = """
def aggregate(items):
    return items[  # Syntax error: unclosed bracket
"""

try:
    result = aggregator.aggregate_custom(items, code, language="python")
except RuntimeError as e:
    print(f"Error: {e}")
    # Output includes full stack trace
```

### Runtime Errors

```python
code = """
def aggregate(items):
    return items[100]  # IndexError
"""

try:
    result = aggregator.aggregate_custom(items, code, language="python")
except RuntimeError as e:
    print(f"Error: {e}")
    # Output includes full stack trace
```

## Best Practices

1. **Keep it Simple**: Custom aggregation code should focus on aggregation logic, not complex business logic.

2. **Handle Edge Cases**: Always check for empty lists, missing fields, and invalid data.

3. **Return Structured Data**: Return dictionaries/objects with clear field names for easy consumption.

4. **Use Appropriate Language**: Choose Python for data science operations, JavaScript for web-like transformations.

5. **Test Thoroughly**: Test your custom aggregation code with various inputs before using in production.

6. **Set Reasonable Timeouts**: For complex aggregations, increase the timeout to avoid premature termination.

7. **Document Your Code**: Add comments to explain complex aggregation logic.

## Common Patterns

### Filtering and Aggregating

```python
code = """
def aggregate(items):
    # Filter items based on criteria
    filtered = [item for item in items if item.get("active", False)]
    
    # Aggregate filtered items
    total = sum(item["value"] for item in filtered)
    
    return {
        "filtered_count": len(filtered),
        "total_value": total,
        "average_value": total / len(filtered) if filtered else 0
    }
"""
```

### Grouping and Summarizing

```python
code = """
def aggregate(items):
    from collections import defaultdict
    
    # Group by category
    groups = defaultdict(list)
    for item in items:
        groups[item["category"]].append(item)
    
    # Summarize each group
    summary = {}
    for category, group_items in groups.items():
        summary[category] = {
            "count": len(group_items),
            "total": sum(item["value"] for item in group_items)
        }
    
    return summary
"""
```

### Statistical Analysis

```python
code = """
def aggregate(items):
    import statistics
    
    values = [item["value"] for item in items]
    
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0,
        "min": min(values),
        "max": max(values)
    }
"""
```

## Limitations

1. **No External Dependencies**: Custom code cannot import external packages (except Python standard library).

2. **Execution Timeout**: Long-running aggregations will be terminated after the timeout period.

3. **Memory Limits**: Very large datasets may cause memory issues.

4. **No Side Effects**: Custom code should not perform I/O operations or modify external state.

5. **Security**: Code is executed in a subprocess but should still be treated as potentially unsafe.

## See Also

- [Batch Aggregator Quick Reference](batch-aggregator-quick-reference.md)
- [Batch Processing Config Guide](batch-processing-config-guide.md)
- [Code Node Quick Reference](code-node-quick-reference.md)
