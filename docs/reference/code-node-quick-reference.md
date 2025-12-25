# Code Node Quick Reference

## Minimal Configuration

### JavaScript (Inline)
```yaml
- id: "my_transform"
  type: "code_node"
  language: "javascript"
  code: |
    function transform(inputs) {
      return inputs.data.map(x => x * 2);
    }
    module.exports = transform;
  input_mapping:
    data: "previous_output"
  output_key: "result"
```

### Python (Inline)
```yaml
- id: "my_transform"
  type: "code_node"
  language: "python"
  code: |
    def execute(data):
      return [x * 2 for x in data]
  input_mapping:
    data: "previous_output"
  output_key: "result"
```

### External File
```yaml
- id: "my_transform"
  type: "code_node"
  language: "python"
  code_file: "scripts/transform.py"
  input_mapping:
    data: "previous_output"
  output_key: "result"
```

## Field Reference

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `id` | ✅ | string | - | Unique step identifier |
| `type` | ✅ | string | - | Must be `"code_node"` |
| `language` | ✅ | string | - | `"javascript"` or `"python"` |
| `code` | ⚠️ | string | - | Inline code (or use `code_file`) |
| `code_file` | ⚠️ | string | - | External file path (or use `code`) |
| `input_mapping` | ❌ | object | `{}` | Parameter to source mapping |
| `output_key` | ✅ | string | - | Output storage key |
| `timeout` | ❌ | integer | `30` | Timeout in seconds |
| `description` | ❌ | string | `""` | Step description |
| `required` | ❌ | boolean | `true` | Halt pipeline on failure |
| `env_vars` | ❌ | object | `{}` | Environment variables |

⚠️ = Either `code` or `code_file` required (not both)

## Language Requirements

### JavaScript
- **Runtime**: Node.js
- **Export**: `module.exports = function`
- **Input**: Single object parameter
- **Output**: Value or Promise

```javascript
function myFunction(inputs) {
  const { param1, param2 } = inputs;
  return result;
}
module.exports = myFunction;
```

### Python
- **Runtime**: Python 3.x
- **Function**: `def execute(...)`
- **Input**: Keyword arguments
- **Output**: JSON-serializable value

```python
def execute(param1, param2):
    return result
```

## Common Patterns

### Data Filtering
```yaml
- id: "filter"
  type: "code_node"
  language: "javascript"
  code: |
    function filter(inputs) {
      return inputs.items.filter(x => x.score > inputs.threshold);
    }
    module.exports = filter;
  input_mapping:
    items: "data"
    threshold: "min_score"
  output_key: "filtered"
```

### Data Transformation
```yaml
- id: "transform"
  type: "code_node"
  language: "python"
  code: |
    def execute(items):
      return [{'id': i['id'], 'value': i['value'] * 2} for i in items]
  input_mapping:
    items: "raw_data"
  output_key: "transformed"
```

### Aggregation
```yaml
- id: "aggregate"
  type: "code_node"
  language: "javascript"
  code: |
    function aggregate(inputs) {
      const sum = inputs.items.reduce((a, b) => a + b.value, 0);
      return {
        total: sum,
        count: inputs.items.length,
        average: sum / inputs.items.length
      };
    }
    module.exports = aggregate;
  input_mapping:
    items: "processed_data"
  output_key: "stats"
```

### Validation
```yaml
- id: "validate"
  type: "code_node"
  language: "python"
  code: |
    def execute(data):
      if not isinstance(data, list):
        raise ValueError('Data must be a list')
      if len(data) == 0:
        raise ValueError('Data cannot be empty')
      return {'valid': True, 'count': len(data)}
  input_mapping:
    data: "input_data"
  output_key: "validation"
  required: false  # Don't halt pipeline on validation failure
```

## Error Handling

### Timeout
```yaml
- id: "long_task"
  type: "code_node"
  language: "python"
  code: "..."
  timeout: 120  # 2 minutes
  output_key: "result"
```

### Optional Step
```yaml
- id: "optional_enrichment"
  type: "code_node"
  language: "javascript"
  code: "..."
  required: false  # Continue pipeline even if this fails
  output_key: "enriched"
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "error_type": "RuntimeError",
  "stderr": "Stack trace...",
  "execution_time": 1.23
}
```

## Environment Variables

```yaml
- id: "api_call"
  type: "code_node"
  language: "python"
  code: |
    import os
    def execute(query):
      api_key = os.getenv('API_KEY')
      return call_api(query, api_key)
  env_vars:
    API_KEY: "${EXTERNAL_API_KEY}"
    DEBUG: "false"
  input_mapping:
    query: "search_query"
  output_key: "results"
```

## Best Practices

✅ **DO**:
- Keep code simple and focused
- Validate inputs
- Handle errors gracefully
- Use external files for complex logic (>50 lines)
- Set appropriate timeouts
- Add descriptions
- Test code independently

❌ **DON'T**:
- Perform heavy computations
- Access arbitrary files
- Use blocking operations
- Hardcode sensitive data
- Ignore error handling
- Mix multiple concerns

## Validation Errors

Common validation errors and fixes:

| Error | Fix |
|-------|-----|
| "Missing required field: language" | Add `language: "javascript"` or `"python"` |
| "Either code or code_file required" | Specify one (not both) |
| "Invalid language" | Use `"javascript"` or `"python"` |
| "Output key must be unique" | Change `output_key` to unique value |
| "Code file not found" | Check file path is correct |
| "Timeout must be positive" | Set `timeout` > 0 |

## Testing

### Test JavaScript Code
```bash
node examples/code_nodes/transform.js
```

### Test Python Code
```bash
python examples/code_nodes/aggregate.py
```

### Test in Pipeline
```bash
python -m src run-pipeline code_node_demo --testset test.jsonl
```

## See Also

- [Code Node Configuration Guide](./code-node-config-guide.md) - Complete documentation
- [Pipeline Guide](./pipeline-guide.md) - Pipeline configuration
- [Examples](../../examples/code_nodes/) - Code node examples
