# Batch Testset Format Guide

## Overview

This guide describes the enhanced testset format that supports batch processing and pipeline-level testing. The format is backward compatible with existing simple testsets while adding powerful new capabilities.

## Testset Format Versions

### 1. Simple Format (Backward Compatible)

The simplest format where all fields in the JSON object are treated as inputs:

```jsonl
{"id": "test_1", "tags": ["simple"], "text": "Hello world", "expected_output": "HELLO WORLD"}
```

**Fields:**
- `id` (required): Unique test case identifier
- `tags` (optional): List of tags for filtering
- All other fields are treated as inputs to the pipeline

### 2. Explicit Format

Clearly separates inputs from expected outputs:

```jsonl
{
  "id": "test_2",
  "tags": ["explicit"],
  "inputs": {
    "text": "Hello world",
    "language": "en"
  },
  "expected_outputs": {
    "result": "HELLO WORLD",
    "language_detected": "en"
  }
}
```

**Fields:**
- `inputs`: Dictionary of input values for the pipeline
- `expected_outputs`: Dictionary of expected output values (for validation)

### 3. Step-Specific Format

Provides different inputs for different pipeline steps:

```jsonl
{
  "id": "test_3",
  "tags": ["step-specific"],
  "inputs": {
    "initial_text": "Start here"
  },
  "step_inputs": {
    "step1": {
      "param1": "value1",
      "mode": "strict"
    },
    "step2": {
      "param2": "value2",
      "depth": "deep"
    }
  },
  "expected_outputs": {
    "step1_output": "result1",
    "step2_output": "result2"
  }
}
```

**Fields:**
- `step_inputs`: Dictionary mapping step IDs to their specific input parameters
- Each step can have its own set of inputs in addition to the global inputs

### 4. Batch Format

Supports batch processing with multiple items:

```jsonl
{
  "id": "test_4",
  "tags": ["batch"],
  "batch_items": [
    {"text": "Item 1", "score": 8.5},
    {"text": "Item 2", "score": 7.2},
    {"text": "Item 3", "score": 9.0}
  ],
  "expected_aggregation": {
    "total_items": 3,
    "average_score": 8.23,
    "high_score_count": 2
  }
}
```

**Fields:**
- `batch_items`: List of items to process in batch
- `expected_aggregation`: Expected result after aggregating all batch items

### 5. Combined Format

Uses all features together for complex pipeline testing:

```jsonl
{
  "id": "test_5",
  "tags": ["combined", "complex"],
  "inputs": {
    "context": "global context",
    "threshold": 0.7
  },
  "step_inputs": {
    "preprocess": {
      "mode": "strict",
      "normalize": true
    },
    "analyze": {
      "depth": "deep",
      "include_metadata": true
    }
  },
  "batch_items": [
    {"text": "Review 1", "rating": 5},
    {"text": "Review 2", "rating": 3},
    {"text": "Review 3", "rating": 4}
  ],
  "expected_outputs": {
    "preprocessed_context": "GLOBAL CONTEXT",
    "analysis_complete": true
  },
  "expected_aggregation": {
    "total_reviews": 3,
    "average_rating": 4.0,
    "sentiment": "positive"
  }
}
```

## Field Reference

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for the test case |
| `tags` | string[] | No | Tags for filtering and categorization |

### Input Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inputs` | object | No | Global inputs for the pipeline |
| `step_inputs` | object | No | Step-specific inputs (key: step_id, value: inputs) |
| `batch_items` | array | No | List of items for batch processing |

### Output Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `expected_outputs` | object | No | Expected outputs from pipeline steps |
| `expected_aggregation` | any | No | Expected result after batch aggregation |

### Backward Compatibility

Any field not in the above list is automatically treated as an input field for backward compatibility with existing testsets.

## Usage Examples

### Example 1: Simple Sentiment Analysis

```jsonl
{"id": "sentiment_1", "tags": ["sentiment"], "text": "I love this product!", "expected_sentiment": "positive"}
```

### Example 2: Multi-Step Pipeline

```jsonl
{
  "id": "multi_step_1",
  "tags": ["multi-step"],
  "inputs": {
    "raw_text": "  Hello World  "
  },
  "step_inputs": {
    "clean": {"trim": true, "lowercase": true},
    "translate": {"target_lang": "es"}
  },
  "expected_outputs": {
    "cleaned_text": "hello world",
    "translated_text": "hola mundo"
  }
}
```

### Example 3: Batch Processing with Aggregation

```jsonl
{
  "id": "batch_reviews_1",
  "tags": ["batch", "reviews"],
  "batch_items": [
    {"review": "Great product!", "rating": 5},
    {"review": "Not bad", "rating": 3},
    {"review": "Excellent!", "rating": 5},
    {"review": "Could be better", "rating": 2}
  ],
  "expected_aggregation": {
    "total_reviews": 4,
    "average_rating": 3.75,
    "positive_count": 2,
    "negative_count": 1,
    "neutral_count": 1
  }
}
```

### Example 4: Conditional Batch Processing

```jsonl
{
  "id": "batch_filter_1",
  "tags": ["batch", "filter"],
  "batch_items": [
    {"score": 8.5, "status": "approved"},
    {"score": 3.2, "status": "rejected"},
    {"score": 7.8, "status": "approved"},
    {"score": 4.1, "status": "rejected"},
    {"score": 9.0, "status": "approved"}
  ],
  "filter_threshold": 7.0,
  "expected_aggregation": {
    "approved_count": 3,
    "rejected_count": 2,
    "high_score_items": [
      {"score": 8.5},
      {"score": 7.8},
      {"score": 9.0}
    ]
  }
}
```

## Loading Testsets

### Using the TestsetLoader

```python
from pathlib import Path
from src.testset_loader import TestsetLoader, TestCase

# Load testset
testset_path = Path("examples/testsets/batch_processing_demo.jsonl")
test_cases = TestsetLoader.load_testset(testset_path)

# Access test case data
for tc in test_cases:
    print(f"Test ID: {tc.id}")
    print(f"Tags: {tc.tags}")
    print(f"Has batch data: {tc.has_batch_data()}")
    print(f"Has step inputs: {tc.has_step_inputs()}")
    
    # Get input values
    text = tc.get_input("text", default="")
    
    # Get step-specific input
    mode = tc.get_step_input("preprocess", "mode", default="normal")
    
    # Access batch items
    if tc.has_batch_data():
        for item in tc.batch_items:
            print(f"  Batch item: {item}")
```

### Filtering by Tags

```python
from src.testset_loader import filter_by_tags

# Filter test cases
batch_tests = filter_by_tags(test_cases, include_tags=["batch"])
simple_tests = filter_by_tags(test_cases, exclude_tags=["batch", "complex"])
```

### Validation

```python
from src.testset_loader import validate_testset

# Validate testset
errors = validate_testset(test_cases)
if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Testset is valid!")
```

## Best Practices

### 1. Use Descriptive IDs

```jsonl
{"id": "sentiment_positive_short_1", ...}
{"id": "sentiment_negative_long_1", ...}
```

### 2. Tag Consistently

```jsonl
{"tags": ["batch", "sentiment", "production"], ...}
{"tags": ["simple", "smoke-test"], ...}
```

### 3. Provide Expected Outputs

Always include expected outputs for validation:

```jsonl
{
  "id": "test_1",
  "inputs": {...},
  "expected_outputs": {
    "result": "expected value",
    "status": "success"
  }
}
```

### 4. Document Complex Test Cases

Use a `description` field for complex test cases:

```jsonl
{
  "id": "complex_1",
  "description": "Tests edge case where input contains special characters",
  ...
}
```

### 5. Keep Batch Sizes Reasonable

For batch processing, keep batch_items to a reasonable size (10-100 items) for faster test execution:

```jsonl
{
  "id": "batch_1",
  "batch_items": [...],  // 10-100 items recommended
  ...
}
```

## Migration from Old Format

### Old Format

```jsonl
{"id": "test_1", "text": "Hello", "expected": "HELLO"}
```

### New Format (Backward Compatible)

The old format still works! But you can enhance it:

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Hello"},
  "expected_outputs": {"result": "HELLO"}
}
```

## See Also

- [Batch Processing Config Guide](batch-processing-config-guide.md)
- [Batch Aggregator Quick Reference](batch-aggregator-quick-reference.md)
- [Pipeline Guide](pipeline-guide.md)
