# Code Node Examples

This directory contains example code node implementations that can be referenced from pipeline configurations.

## Files

### transform.js
JavaScript code node for data transformation and filtering.

**Features**:
- Filters items based on threshold
- Transforms and normalizes data
- Calculates statistics
- Categorizes items

**Usage in Pipeline**:
```yaml
- id: "transform"
  type: "code_node"
  language: "javascript"
  code_file: "examples/code_nodes/transform.js"
  input_mapping:
    items: "input_data"
    threshold: "min_threshold"
  output_key: "transformed_data"
```

**Input Format**:
```json
{
  "items": [
    {"id": 1, "score": 85},
    {"id": 2, "score": 45}
  ],
  "threshold": 50
}
```

**Output Format**:
```json
{
  "items": [
    {
      "id": 1,
      "score": 85,
      "normalized": 0.85,
      "category": "high",
      "processed_at": "2025-12-15T10:30:00.000Z"
    }
  ],
  "stats": {
    "total": 2,
    "filtered": 1,
    "removed": 1,
    "average_score": 85,
    "threshold_used": 50
  }
}
```

### aggregate.py
Python code node for data aggregation with multiple strategies.

**Features**:
- Concat strategy: Concatenate all items
- Stats strategy: Calculate statistics
- Summary strategy: Generate text summary
- Metadata tracking

**Usage in Pipeline**:
```yaml
- id: "aggregate"
  type: "code_node"
  language: "python"
  code_file: "examples/code_nodes/aggregate.py"
  input_mapping:
    items: "processed_items"
    strategy: "aggregation_strategy"
  output_key: "aggregated_result"
```

**Input Format**:
```json
{
  "items": [
    {"id": 1, "score": 85, "category": "high"},
    {"id": 2, "score": 67, "category": "medium"}
  ],
  "strategy": "stats"
}
```

**Output Format** (stats strategy):
```json
{
  "type": "stats",
  "count": 2,
  "scores": {
    "min": 67,
    "max": 85,
    "avg": 76,
    "total": 152
  },
  "categories": {
    "high": 1,
    "medium": 1
  },
  "metadata": {
    "strategy": "stats",
    "item_count": 2,
    "aggregated_at": "2025-12-15T10:30:00.000000",
    "version": "1.0.0"
  }
}
```

## Testing

### Test JavaScript Code
```bash
# Run the transform.js file directly
node examples/code_nodes/transform.js
```

### Test Python Code
```bash
# Run the aggregate.py file directly
python examples/code_nodes/aggregate.py
```

This will execute the test cases defined in the `if __name__ == '__main__'` block.

## Creating Your Own Code Nodes

### JavaScript Template
```javascript
/**
 * Description of what this code node does
 * 
 * @param {Object} inputs - Input parameters
 * @param {Type} inputs.param1 - Description
 * @returns {Type} Description of return value
 */
function myFunction(inputs) {
  const { param1, param2 } = inputs;
  
  // Validate inputs
  if (!param1) {
    throw new Error('param1 is required');
  }
  
  // Process data
  const result = processData(param1, param2);
  
  return result;
}

module.exports = myFunction;
```

### Python Template
```python
"""
Description of what this code node does
"""

from typing import Any, Dict


def execute(param1: Any, param2: Any) -> Dict[str, Any]:
    """
    Function description
    
    Args:
        param1: Description
        param2: Description
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When validation fails
    """
    # Validate inputs
    if not param1:
        raise ValueError('param1 is required')
    
    # Process data
    result = process_data(param1, param2)
    
    return result


if __name__ == '__main__':
    # Test cases
    test_result = execute(test_param1, test_param2)
    print(test_result)
```

## Best Practices

1. **Validation**: Always validate inputs at the start
2. **Error Handling**: Provide clear error messages
3. **Documentation**: Add docstrings and comments
4. **Testing**: Include test cases in the file
5. **Type Hints**: Use type hints (Python) or JSDoc (JavaScript)
6. **Single Responsibility**: Each code node should do one thing well
7. **JSON Serializable**: Ensure outputs can be serialized to JSON

## See Also

- [Code Node Configuration Guide](../../docs/reference/code-node-config-guide.md)
- [Code Node Quick Reference](../../docs/reference/code-node-quick-reference.md)
- [Example Pipeline](../pipelines/code_node_demo.yaml)
