# Data Model Serialization Guide

## Overview

All data models in the Prompt Lab project support comprehensive serialization capabilities, enabling seamless conversion between Python dataclasses, JSON, and Pydantic models.

## Serialization Methods

Every data model provides four core serialization methods:

### 1. to_dict()
Converts a model instance to a Python dictionary.

```python
from src.models import PipelineConfig, InputSpec, OutputSpec, StepConfig

pipeline = PipelineConfig(
    id="my_pipeline",
    name="My Pipeline",
    inputs=[InputSpec(name="input1")],
    outputs=[OutputSpec(key="output1")],
    steps=[
        StepConfig(
            id="step1",
            type="agent_flow",
            agent="agent1",
            flow="flow1",
            input_mapping={"x": "input1"},
            output_key="output1"
        )
    ]
)

# Convert to dictionary
pipeline_dict = pipeline.to_dict()
```

### 2. from_dict()
Creates a model instance from a Python dictionary.

```python
# Create from dictionary
pipeline = PipelineConfig.from_dict(pipeline_dict)
```

### 3. to_json()
Converts a model instance to a JSON string.

```python
# Convert to JSON string
json_str = pipeline.to_json()
print(json_str)
```

Output:
```json
{
  "id": "my_pipeline",
  "name": "My Pipeline",
  "description": "",
  "default_testset": "",
  "inputs": [
    {
      "name": "input1",
      "desc": "",
      "required": true
    }
  ],
  "steps": [
    {
      "id": "step1",
      "type": "agent_flow",
      "agent": "agent1",
      "flow": "flow1",
      "input_mapping": {
        "x": "input1"
      },
      "output_key": "output1"
    }
  ],
  "outputs": [
    {
      "key": "output1",
      "label": ""
    }
  ]
}
```

### 4. from_json()
Creates a model instance from a JSON string.

```python
# Create from JSON string
pipeline = PipelineConfig.from_json(json_str)
```

## Supported Models

### Core Configuration Models
- `OutputParserConfig` - Output parser configuration
- `InputSpec` - Pipeline input specifications
- `OutputSpec` - Pipeline output specifications
- `CodeNodeConfig` - Code node configuration

### Pipeline Models
- `StepConfig` - Pipeline step configuration
- `BaselineStepConfig` - Baseline step configuration
- `BaselineConfig` - Baseline configuration
- `VariantStepOverride` - Variant step override
- `VariantConfig` - Variant configuration
- `PipelineConfig` - Complete pipeline configuration

### Evaluation Models
- `RuleConfig` - Rule-based evaluation
- `CaseFieldConfig` - Test case field configuration
- `EvaluationConfig` - Evaluation configuration
- `EvaluationResult` - Evaluation results
- `RegressionCase` - Regression test case
- `ComparisonReport` - Comparison report

### Agent Registry Models
- `AgentMetadata` - Agent metadata
- `SyncResult` - Registry sync results
- `ReloadEvent` - Registry reload events

## Pydantic Conversion

The `src/model_converters.py` module provides utilities for converting between dataclass models and Pydantic models used in the API layer.

### Converting Dataclass to Pydantic

```python
from src.model_converters import dataclass_pipeline_config_to_pydantic
from src.models import PipelineConfig

# Create dataclass pipeline
dc_pipeline = PipelineConfig(...)

# Convert to Pydantic for API response
pydantic_pipeline = dataclass_pipeline_config_to_pydantic(dc_pipeline)
```

### Converting Pydantic to Dataclass

```python
from src.model_converters import pydantic_pipeline_config_to_dataclass
from src.api.models import PipelineConfigResponse

# Receive Pydantic model from API
pydantic_pipeline = PipelineConfigResponse(...)

# Convert to dataclass for internal processing
dc_pipeline = pydantic_pipeline_config_to_dataclass(pydantic_pipeline)
```

### Available Converters

#### InputSpec
- `dataclass_input_spec_to_pydantic()`
- `pydantic_input_spec_to_dataclass()`

#### OutputSpec
- `dataclass_output_spec_to_pydantic()`
- `pydantic_output_spec_to_dataclass()`

#### StepConfig
- `dataclass_step_config_to_pydantic()`
- `pydantic_step_config_to_dataclass()`

#### PipelineConfig
- `dataclass_pipeline_config_to_pydantic()`
- `pydantic_pipeline_config_to_dataclass()`

### Generic Helpers

```python
from src.model_converters import (
    dataclass_to_pydantic_dict,
    pydantic_to_dataclass_dict
)

# Convert any dataclass to dict suitable for Pydantic
pydantic_dict = dataclass_to_pydantic_dict(my_dataclass)

# Convert any Pydantic model to dict suitable for dataclass
dataclass_dict = pydantic_to_dataclass_dict(my_pydantic_model)
```

## Round-Trip Guarantees

All serialization methods guarantee round-trip consistency:

```python
# Dictionary round-trip
original = PipelineConfig(...)
dict_data = original.to_dict()
restored = PipelineConfig.from_dict(dict_data)
assert restored.id == original.id
assert restored.name == original.name

# JSON round-trip
json_str = original.to_json()
restored = PipelineConfig.from_json(json_str)
assert restored.id == original.id
assert restored.name == original.name

# Pydantic round-trip
pydantic = dataclass_pipeline_config_to_pydantic(original)
restored = pydantic_pipeline_config_to_dataclass(pydantic)
assert restored.id == original.id
assert restored.name == original.name
```

## Best Practices

### 1. Use JSON for Persistence
```python
# Save to file
with open("pipeline.json", "w") as f:
    f.write(pipeline.to_json())

# Load from file
with open("pipeline.json", "r") as f:
    pipeline = PipelineConfig.from_json(f.read())
```

### 2. Use Pydantic for API Validation
```python
from fastapi import APIRouter
from src.api.models import PipelineConfigResponse
from src.model_converters import dataclass_pipeline_config_to_pydantic

router = APIRouter()

@router.get("/pipelines/{pipeline_id}")
def get_pipeline(pipeline_id: str) -> PipelineConfigResponse:
    # Load internal dataclass model
    dc_pipeline = load_pipeline(pipeline_id)
    
    # Convert to Pydantic for API response
    return dataclass_pipeline_config_to_pydantic(dc_pipeline)
```

### 3. Handle Nested Models
```python
# Nested models are automatically serialized
pipeline = PipelineConfig(
    id="nested_example",
    name="Nested Example",
    inputs=[InputSpec(name="input1")],
    steps=[
        StepConfig(
            id="step1",
            type="code_node",
            code_config=CodeNodeConfig(
                language="python",
                code="return x * 2"
            ),
            input_mapping={"x": "input1"},
            output_key="result"
        )
    ],
    outputs=[OutputSpec(key="result")]
)

# All nested models are included in serialization
json_str = pipeline.to_json()
```

### 4. Handle Optional Fields
```python
# Optional fields are omitted from to_dict() if None
config = CodeNodeConfig(
    language="python",
    code="print('hello')",
    timeout=30
    # code_file is None, will be omitted
)

result = config.to_dict()
# result = {"language": "python", "code": "print('hello')", "timeout": 30}
# "code_file" is not included
```

## Error Handling

### Invalid JSON
```python
try:
    pipeline = PipelineConfig.from_json(invalid_json)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

### Missing Required Fields
```python
try:
    pipeline = PipelineConfig.from_dict({"id": "test"})  # Missing required fields
except TypeError as e:
    print(f"Missing required fields: {e}")
```

### Type Validation with Pydantic
```python
from pydantic import ValidationError

try:
    pydantic_pipeline = PipelineConfigResponse(**invalid_data)
except ValidationError as e:
    print(f"Validation errors: {e}")
```

## Testing

All serialization methods are thoroughly tested:

```bash
# Run serialization tests
pytest tests/test_model_serialization.py -v

# Run converter tests
pytest tests/test_model_converters.py -v
```

## See Also

- [API Design Specification](./api-design-specification.md)
- [Data Structure Guide](./data-structure-guide.md)
- [Pipeline Guide](./pipeline-guide.md)
