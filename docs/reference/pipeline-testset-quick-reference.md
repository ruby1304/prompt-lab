# Pipeline Testset Format - Quick Reference

## Basic Structure

```json
{
  "id": "test_case_id",                    // Required: unique identifier
  "tags": ["tag1", "tag2"],                // Optional: for filtering
  "inputs": {...},                         // Optional: global inputs
  "step_inputs": {...},                    // Optional: step-specific inputs
  "batch_items": [...],                    // Optional: batch data
  "expected_outputs": {...},               // Optional: expected final output
  "expected_aggregation": {...},           // Optional: expected aggregation
  "intermediate_expectations": {...},      // Optional: intermediate outputs
  "evaluation_config": {...}               // Optional: evaluation settings
}
```

## Field Quick Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ Yes | Unique test case identifier |
| `tags` | string[] | ❌ No | Tags for categorization |
| `inputs` | object | ❌ No | Global pipeline inputs |
| `step_inputs` | object | ❌ No | Step-specific inputs |
| `batch_items` | object[] | ❌ No | Batch processing data |
| `expected_outputs` | object | ❌ No | Expected final outputs |
| `expected_aggregation` | any | ❌ No | Expected aggregation result |
| `intermediate_expectations` | object | ❌ No | Expected intermediate outputs |
| `evaluation_config` | object | ❌ No | Evaluation configuration |

## Common Patterns

### Simple Test Case
```json
{"id": "test_1", "text": "input", "expected_output": "result"}
```

### Multi-Step Test
```json
{
  "id": "multi_1",
  "inputs": {"data": "..."},
  "step_inputs": {
    "step1": {"param": "value"},
    "step2": {"param": "value"}
  },
  "expected_outputs": {"result": "..."}
}
```

### Batch Processing Test
```json
{
  "id": "batch_1",
  "batch_items": [
    {"item": "A"},
    {"item": "B"}
  ],
  "expected_aggregation": {"count": 2}
}
```

### Complete Pipeline Test
```json
{
  "id": "complete_1",
  "inputs": {...},
  "step_inputs": {...},
  "batch_items": [...],
  "intermediate_expectations": {...},
  "expected_aggregation": {...},
  "expected_outputs": {...},
  "evaluation_config": {...}
}
```

## Evaluation Config Options

```json
{
  "evaluation_config": {
    "evaluate_intermediate": false,      // Evaluate intermediate steps
    "evaluate_final": true,              // Evaluate final output
    "evaluate_aggregation": true,        // Evaluate aggregation
    "strict_mode": false,                // Exact vs partial match
    "tolerance": 0.01,                   // Numerical tolerance
    "ignore_fields": ["timestamp"]       // Fields to ignore
  }
}
```

## Tags Best Practices

**Functional Tags:**
- `"sentiment"`, `"summarization"`, `"translation"`

**Type Tags:**
- `"unit"`, `"integration"`, `"performance"`

**Complexity Tags:**
- `"simple"`, `"complex"`, `"multi-step"`

**Priority Tags:**
- `"critical"`, `"important"`, `"optional"`

**Feature Tags:**
- `"batch"`, `"aggregation"`, `"concurrent"`

## File Format

- **Format:** JSONL (JSON Lines)
- **Extension:** `.jsonl`
- **Encoding:** UTF-8
- **One test case per line**

## Loading Test Cases

```python
from src.testset_loader import load_testset

# Load test cases
test_cases = load_testset(Path("testsets/my_tests.jsonl"))

# Filter by tags
from src.testset_loader import filter_by_tags
filtered = filter_by_tags(test_cases, include_tags=["critical"])

# Validate test cases
from src.testset_loader import validate_testset
errors = validate_testset(test_cases)
```

## Common Use Cases

### 1. Testing Sentiment Analysis
```json
{
  "id": "sentiment_positive",
  "tags": ["sentiment", "positive"],
  "inputs": {"text": "I love this!"},
  "expected_outputs": {"sentiment": "positive", "confidence": 0.9}
}
```

### 2. Testing Multi-Step Pipeline
```json
{
  "id": "pipeline_preprocess_analyze",
  "tags": ["multi-step"],
  "inputs": {"raw_text": "..."},
  "step_inputs": {
    "preprocess": {"lowercase": true},
    "analyze": {"model": "advanced"}
  },
  "intermediate_expectations": {
    "preprocess": {"cleaned_text": "..."}
  },
  "expected_outputs": {"result": "..."}
}
```

### 3. Testing Batch Aggregation
```json
{
  "id": "batch_stats",
  "tags": ["batch", "stats"],
  "batch_items": [
    {"score": 8.5},
    {"score": 7.2}
  ],
  "expected_aggregation": {
    "average": 7.85,
    "count": 2
  }
}
```

### 4. Testing with Intermediate Validation
```json
{
  "id": "debug_pipeline",
  "tags": ["debugging"],
  "inputs": {"data": "..."},
  "intermediate_expectations": {
    "step1": {"output": "..."},
    "step2": {"output": "..."}
  },
  "expected_outputs": {"final": "..."},
  "evaluation_config": {
    "evaluate_intermediate": true
  }
}
```

## Validation Rules

✅ **Valid:**
- Unique `id` within testset
- `tags` is array of strings
- `batch_items` is array of objects
- `step_inputs` is nested object

❌ **Invalid:**
- Duplicate `id`
- `tags` as string (should be array)
- `batch_items` as object (should be array)
- Missing `id` field

## Schema Validation

JSON Schema available at: `config/schemas/pipeline_testset.schema.json`

```python
import json
import jsonschema

# Load schema
with open("config/schemas/pipeline_testset.schema.json") as f:
    schema = json.load(f)

# Validate test case
test_case = {"id": "test_1", ...}
jsonschema.validate(test_case, schema)
```

## Examples

See example files in `examples/testsets/`:
- `pipeline_multi_step_examples.jsonl`
- `pipeline_batch_aggregation_examples.jsonl`
- `pipeline_intermediate_evaluation_examples.jsonl`
- `pipeline_complex_scenarios.jsonl`

## Related Documentation

- [Full Specification](./pipeline-testset-format-specification.md)
- [Batch Processing Guide](./batch-processing-config-guide.md)
- [Testset Loader Guide](./testset-loader-quick-reference.md)
