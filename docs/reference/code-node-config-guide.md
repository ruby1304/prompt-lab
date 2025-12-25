# Code Node Configuration Guide

## Overview

Code Nodes are special pipeline steps that execute custom JavaScript or Python code for data transformation, preprocessing, and aggregation. This guide defines the complete configuration format for Code Nodes in Pipeline YAML files.

## Configuration Structure

### Basic Code Node Configuration

```yaml
steps:
  - id: "transform_data"
    type: "code_node"
    language: "javascript"  # or "python"
    code: |
      // Inline code here
      function transform(inputs) {
        return inputs.map(item => ({
          ...item,
          processed: true
        }));
      }
      module.exports = transform;
    input_mapping:
      inputs: "previous_step_output"
    output_key: "transformed_data"
    timeout: 30  # seconds (optional, default: 30)
    description: "Transform data using custom logic"
    required: true  # optional, default: true
```

### External File Reference

```yaml
steps:
  - id: "aggregate_results"
    type: "code_node"
    language: "python"
    code_file: "scripts/aggregate.py"  # Path relative to project root
    input_mapping:
      data: "transformed_data"
      config: "pipeline_config"
    output_key: "aggregated_result"
    timeout: 60
    env_vars:  # optional environment variables
      DEBUG: "false"
      MAX_ITEMS: "1000"
```

## Field Definitions

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the step within the pipeline |
| `type` | string | Must be `"code_node"` for code execution steps |
| `language` | string | Programming language: `"javascript"` or `"python"` |
| `output_key` | string | Key name for storing the step's output |

### Code Source (One Required)

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Inline code to execute (multiline string) |
| `code_file` | string | Path to external code file (relative to project root) |

**Note**: You must specify either `code` or `code_file`, but not both.

### Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `input_mapping` | dict | `{}` | Maps parameter names to data sources |
| `timeout` | integer | `30` | Maximum execution time in seconds |
| `description` | string | `""` | Human-readable description of the step |
| `required` | boolean | `true` | Whether step failure should halt pipeline |
| `env_vars` | dict | `{}` | Environment variables for code execution |

## Language-Specific Requirements

### JavaScript Code Nodes

**Requirements**:
- Node.js runtime must be available
- Code must export a function using `module.exports`
- Function receives inputs as a single object parameter
- Function must return the output value or a Promise

**Example**:

```javascript
// Inline JavaScript code
function processData(inputs) {
  const { items, threshold } = inputs;
  
  return items
    .filter(item => item.score > threshold)
    .map(item => ({
      id: item.id,
      score: item.score,
      normalized: item.score / 100
    }));
}

module.exports = processData;
```

**External File Example** (`scripts/process.js`):

```javascript
/**
 * Process and filter items based on threshold
 * @param {Object} inputs - Input parameters
 * @param {Array} inputs.items - Items to process
 * @param {number} inputs.threshold - Minimum score threshold
 * @returns {Array} Processed items
 */
function processData(inputs) {
  const { items, threshold } = inputs;
  
  if (!Array.isArray(items)) {
    throw new Error('items must be an array');
  }
  
  return items
    .filter(item => item.score > threshold)
    .map(item => ({
      id: item.id,
      score: item.score,
      normalized: item.score / 100
    }));
}

module.exports = processData;
```

### Python Code Nodes

**Requirements**:
- Python interpreter must be available
- Code must define a main function (default name: `execute`)
- Function receives inputs as keyword arguments
- Function must return the output value
- Output must be JSON-serializable

**Example**:

```python
# Inline Python code
def execute(items, threshold):
    """
    Process and filter items based on threshold
    
    Args:
        items: List of items to process
        threshold: Minimum score threshold
    
    Returns:
        List of processed items
    """
    if not isinstance(items, list):
        raise ValueError('items must be a list')
    
    return [
        {
            'id': item['id'],
            'score': item['score'],
            'normalized': item['score'] / 100
        }
        for item in items
        if item['score'] > threshold
    ]
```

**External File Example** (`scripts/process.py`):

```python
"""
Data processing module for pipeline
"""
import json
from typing import List, Dict, Any


def execute(items: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
    """
    Process and filter items based on threshold
    
    Args:
        items: List of items to process
        threshold: Minimum score threshold
    
    Returns:
        List of processed items
    
    Raises:
        ValueError: If items is not a list
    """
    if not isinstance(items, list):
        raise ValueError('items must be a list')
    
    processed = []
    for item in items:
        if item.get('score', 0) > threshold:
            processed.append({
                'id': item['id'],
                'score': item['score'],
                'normalized': item['score'] / 100
            })
    
    return processed


if __name__ == '__main__':
    # For testing
    test_items = [
        {'id': 1, 'score': 85},
        {'id': 2, 'score': 45},
        {'id': 3, 'score': 92}
    ]
    result = execute(test_items, 50)
    print(json.dumps(result, indent=2))
```

## Input Mapping

The `input_mapping` field maps parameter names to data sources. Data sources can be:

1. **Pipeline inputs**: Reference global pipeline inputs
2. **Previous step outputs**: Reference output keys from previous steps
3. **Literal values**: Inline constant values (future feature)

**Example**:

```yaml
steps:
  - id: "step1"
    type: "agent_flow"
    agent: "processor"
    flow: "process_v1"
    input_mapping:
      text: "input_text"  # From pipeline input
    output_key: "processed_text"
  
  - id: "step2"
    type: "code_node"
    language: "python"
    code: |
      def execute(text, config):
        return {
          'length': len(text),
          'words': len(text.split()),
          'config': config
        }
    input_mapping:
      text: "processed_text"  # From step1 output
      config: "pipeline_config"  # From pipeline input
    output_key: "text_stats"
```

## Timeout and Error Handling

### Timeout Configuration

- Default timeout: 30 seconds
- Configurable per code node
- Execution is forcefully terminated if timeout is exceeded
- Timeout error includes execution time and partial output (if any)

**Example**:

```yaml
steps:
  - id: "long_running_task"
    type: "code_node"
    language: "python"
    code: |
      import time
      def execute(data):
        # Long-running operation
        time.sleep(45)  # Will timeout with default 30s
        return data
    timeout: 60  # Increase timeout to 60 seconds
    output_key: "result"
```

### Error Handling

Code nodes can fail in several ways:

1. **Syntax errors**: Code has invalid syntax
2. **Runtime errors**: Code throws an exception during execution
3. **Timeout errors**: Execution exceeds timeout limit
4. **Output errors**: Output is not JSON-serializable (Python only)

**Error Response Format**:

```json
{
  "success": false,
  "error": "Error message",
  "error_type": "SyntaxError|RuntimeError|TimeoutError|OutputError",
  "stderr": "Standard error output",
  "execution_time": 1.23,
  "stack_trace": "Full stack trace..."
}
```

### Required vs Optional Steps

Use the `required` field to control pipeline behavior on failure:

```yaml
steps:
  - id: "critical_transform"
    type: "code_node"
    language: "javascript"
    code: "..."
    required: true  # Pipeline stops if this fails
    output_key: "result"
  
  - id: "optional_enrichment"
    type: "code_node"
    language: "python"
    code: "..."
    required: false  # Pipeline continues if this fails
    output_key: "enriched_data"
```

## Environment Variables

Pass environment variables to code execution:

```yaml
steps:
  - id: "api_call"
    type: "code_node"
    language: "python"
    code: |
      import os
      import requests
      
      def execute(query):
        api_key = os.getenv('API_KEY')
        api_url = os.getenv('API_URL')
        
        response = requests.get(
          f"{api_url}/search",
          params={'q': query},
          headers={'Authorization': f'Bearer {api_key}'}
        )
        return response.json()
    env_vars:
      API_KEY: "${EXTERNAL_API_KEY}"  # From system environment
      API_URL: "https://api.example.com"
    input_mapping:
      query: "search_query"
    output_key: "api_results"
```

## Complete Example

Here's a complete pipeline with multiple code nodes:

```yaml
id: "data_processing_pipeline"
name: "Data Processing with Code Nodes"
description: "Example pipeline demonstrating code node usage"

inputs:
  - name: "raw_data"
    desc: "Raw input data to process"
    required: true
  - name: "threshold"
    desc: "Filtering threshold"
    required: false

steps:
  # Step 1: Clean data with Python
  - id: "clean_data"
    type: "code_node"
    language: "python"
    code: |
      def execute(raw_data):
        """Remove null values and normalize"""
        cleaned = []
        for item in raw_data:
          if item and 'value' in item:
            cleaned.append({
              'id': item.get('id', ''),
              'value': float(item['value']),
              'timestamp': item.get('timestamp', '')
            })
        return cleaned
    input_mapping:
      raw_data: "raw_data"
    output_key: "cleaned_data"
    timeout: 30
    description: "Clean and normalize input data"
  
  # Step 2: Process with Agent
  - id: "analyze"
    type: "agent_flow"
    agent: "analyzer"
    flow: "analyze_v1"
    input_mapping:
      data: "cleaned_data"
    output_key: "analysis_result"
  
  # Step 3: Transform results with JavaScript
  - id: "transform_results"
    type: "code_node"
    language: "javascript"
    code: |
      function transform(inputs) {
        const { analysis, threshold } = inputs;
        
        return {
          summary: {
            total: analysis.items.length,
            passed: analysis.items.filter(i => i.score > threshold).length,
            average: analysis.items.reduce((sum, i) => sum + i.score, 0) / analysis.items.length
          },
          items: analysis.items.map(item => ({
            ...item,
            passed: item.score > threshold
          }))
        };
      }
      module.exports = transform;
    input_mapping:
      analysis: "analysis_result"
      threshold: "threshold"
    output_key: "final_result"
    timeout: 15
    description: "Transform and summarize analysis results"

outputs:
  - key: "final_result"
    label: "Processed Results"
```

## Best Practices

### 1. Code Organization

- **Keep code simple**: Code nodes should perform single, focused tasks
- **Use external files**: For complex logic (>50 lines), use external files
- **Add documentation**: Include docstrings and comments
- **Error handling**: Always validate inputs and handle edge cases

### 2. Performance

- **Set appropriate timeouts**: Based on expected execution time
- **Avoid heavy operations**: Use code nodes for transformation, not heavy computation
- **Consider caching**: For expensive operations, cache results externally

### 3. Security

- **Validate inputs**: Always validate and sanitize inputs
- **Limit file access**: Avoid reading/writing arbitrary files
- **Use environment variables**: For sensitive data like API keys
- **Review code**: All production code nodes should be reviewed

### 4. Testing

- **Test independently**: Test code node functions outside the pipeline
- **Use test data**: Create test cases with various input scenarios
- **Handle errors gracefully**: Return meaningful error messages

### 5. Debugging

- **Use logging**: Print debug information to stderr
- **Return intermediate results**: For complex transformations
- **Test with small data**: Start with small datasets for debugging

## Migration from Agent-Only Pipelines

If you have existing pipelines that use agents for data transformation, consider migrating to code nodes:

**Before** (using agent for simple transformation):

```yaml
steps:
  - id: "transform"
    type: "agent_flow"
    agent: "transformer"
    flow: "simple_transform"
    input_mapping:
      data: "input_data"
    output_key: "transformed"
```

**After** (using code node):

```yaml
steps:
  - id: "transform"
    type: "code_node"
    language: "javascript"
    code: |
      function transform(inputs) {
        return inputs.data.map(item => ({
          ...item,
          processed: true
        }));
      }
      module.exports = transform;
    input_mapping:
      data: "input_data"
    output_key: "transformed"
```

**Benefits**:
- Faster execution (no LLM call)
- More predictable results
- Lower cost
- Easier to test and debug

## Validation

The system validates code node configurations:

1. **Required fields**: `id`, `type`, `language`, `output_key`
2. **Code source**: Either `code` or `code_file` must be specified
3. **Language**: Must be `"javascript"` or `"python"`
4. **Timeout**: Must be positive integer
5. **Input mapping**: All referenced sources must exist
6. **Output key**: Must be unique within pipeline

**Validation errors** are reported with detailed messages and suggestions for fixes.

## See Also

- [Pipeline Configuration Guide](./pipeline-guide.md)
- [Batch Processing Guide](./batch-processing-guide.md)
- [Concurrent Execution Guide](./concurrent-execution-guide.md)
- [Error Handling Guide](./error-handling-guide.md)
