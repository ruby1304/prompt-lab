# Testset Loader Quick Reference

## Import

```python
from src.testset_loader import (
    TestCase, TestsetLoader, 
    load_testset, validate_testset, filter_by_tags
)
```

## Loading Testsets

```python
from pathlib import Path

# Load testset
test_cases = load_testset(Path("testset.jsonl"))

# Load as dict (backward compatible)
test_dicts = TestsetLoader.load_testset_dict(Path("testset.jsonl"))
```

## TestCase Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique test case identifier |
| `tags` | List[str] | Tags for filtering |
| `inputs` | Dict | Global inputs |
| `step_inputs` | Dict[str, Dict] | Step-specific inputs |
| `batch_items` | List[Dict] | Batch processing items |
| `expected_outputs` | Dict | Expected outputs |
| `expected_aggregation` | Any | Expected aggregation result |

## Accessing Data

```python
# Get input value
text = tc.get_input("text", default="")

# Get step-specific input
mode = tc.get_step_input("step1", "mode", default="normal")

# Check for batch data
if tc.has_batch_data():
    for item in tc.batch_items:
        process(item)

# Check for step inputs
if tc.has_step_inputs():
    for step_id, inputs in tc.step_inputs.items():
        configure_step(step_id, inputs)

# Check for expected aggregation
if tc.has_expected_aggregation():
    validate(result, tc.expected_aggregation)
```

## Validation

```python
# Validate testset
errors = validate_testset(test_cases)

if errors:
    for error in errors:
        print(f"Error: {error}")
else:
    print("Valid!")
```

## Filtering

```python
# Include tags (any match)
batch_tests = filter_by_tags(test_cases, include_tags=["batch"])

# Exclude tags (any match)
simple_tests = filter_by_tags(test_cases, exclude_tags=["complex"])

# Combine include and exclude
filtered = filter_by_tags(
    test_cases,
    include_tags=["batch", "production"],
    exclude_tags=["slow"]
)
```

## Getting Specific Types

```python
# Get batch test cases
batch_cases = TestsetLoader.get_batch_test_cases(test_cases)

# Get step input test cases
step_cases = TestsetLoader.get_step_input_test_cases(test_cases)
```

## Testset Format Examples

### Simple Format
```jsonl
{"id": "test_1", "text": "Hello", "expected": "HELLO"}
```

### Explicit Format
```jsonl
{
  "id": "test_2",
  "inputs": {"text": "Hello"},
  "expected_outputs": {"result": "HELLO"}
}
```

### Step-Specific Format
```jsonl
{
  "id": "test_3",
  "inputs": {"text": "Hello"},
  "step_inputs": {
    "step1": {"mode": "strict"},
    "step2": {"depth": "deep"}
  }
}
```

### Batch Format
```jsonl
{
  "id": "test_4",
  "batch_items": [
    {"text": "Item 1"},
    {"text": "Item 2"}
  ],
  "expected_aggregation": {"total": 2}
}
```

### Combined Format
```jsonl
{
  "id": "test_5",
  "inputs": {"context": "global"},
  "step_inputs": {"step1": {"mode": "strict"}},
  "batch_items": [{"item": 1}],
  "expected_outputs": {"result": "done"},
  "expected_aggregation": {"count": 1}
}
```

## Common Patterns

### Load and Validate
```python
test_cases = load_testset(Path("testset.jsonl"))
errors = validate_testset(test_cases)
assert not errors, f"Validation failed: {errors}"
```

### Filter and Process
```python
test_cases = load_testset(Path("testset.jsonl"))
batch_tests = filter_by_tags(test_cases, include_tags=["batch"])

for tc in batch_tests:
    if tc.has_batch_data():
        process_batch(tc.batch_items)
```

### Pipeline Integration
```python
test_cases = load_testset(Path("testset.jsonl"))

for tc in test_cases:
    # Get global inputs
    inputs = tc.inputs
    
    # Execute pipeline steps
    for step in pipeline.steps:
        # Get step-specific inputs
        step_inputs = tc.step_inputs.get(step.id, {})
        
        # Execute step
        result = execute_step(step, inputs, step_inputs)
        
        # Validate expected output
        if step.output_key in tc.expected_outputs:
            expected = tc.expected_outputs[step.output_key]
            assert result == expected
```

## Error Handling

```python
from pathlib import Path

try:
    test_cases = load_testset(Path("testset.jsonl"))
except FileNotFoundError:
    print("Testset file not found")
except ValueError as e:
    print(f"Invalid testset format: {e}")
```

## See Also

- [Batch Testset Format Guide](batch-testset-format-guide.md) - Complete format documentation
- [Batch Processing Config Guide](batch-processing-config-guide.md) - Batch processing configuration
- [Pipeline Guide](pipeline-guide.md) - Pipeline configuration
