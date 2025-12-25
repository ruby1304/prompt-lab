# Configuration API Property Test Quick Reference

## Overview
Property-based tests for Configuration API read-write round-trip functionality.

**Property 34**: Configuration API read-write  
**Validates**: Requirements 8.4  
**Test File**: `tests/test_config_api_properties.py`

## Test Classes

### TestAgentConfigRoundTrip
Tests agent configuration read-write operations.

#### test_agent_config_read_write_round_trip
```python
# Property: For any agent configuration, read → update → read produces updated config
@given(agent_id, original_config, updated_config)
def test_agent_config_read_write_round_trip(...)
```
- Generates random agent configurations
- Tests complete read-update-read cycle
- Verifies all fields persist correctly
- Runs 100 examples

#### test_agent_config_preserves_all_fields
```python
# Property: Arbitrary fields (including custom) are preserved
@given(agent_id, config)
def test_agent_config_preserves_all_fields(...)
```
- Tests custom field preservation
- Verifies nested objects and lists
- Ensures no data loss
- Runs 100 examples

### TestPipelineConfigRoundTrip
Tests pipeline configuration read-write operations.

#### test_pipeline_config_read_write_round_trip
```python
# Property: For any pipeline configuration, read → update → read produces updated config
@given(pipeline_id, original_config, updated_config)
def test_pipeline_config_read_write_round_trip(...)
```
- Generates random pipeline configurations
- Tests complete read-update-read cycle
- Verifies complex step structures
- Runs 100 examples

#### test_pipeline_config_preserves_step_details
```python
# Property: Complex step configurations are preserved
@given(pipeline_id, config)
def test_pipeline_config_preserves_step_details(...)
```
- Tests step detail preservation
- Verifies agent_flow and code_node fields
- Ensures step modifications persist
- Runs 100 examples

### TestConfigAPIConsistency
Tests consistency properties of configuration API.

#### test_multiple_reads_return_same_config
```python
# Property: Multiple reads without updates return identical results
@given(agent_id, config)
def test_multiple_reads_return_same_config(...)
```
- Reads configuration 3 times
- Verifies all reads return identical data
- Runs 50 examples

#### test_read_after_write_is_idempotent
```python
# Property: Read-after-write returns exact written configuration
@given(agent_id, config)
def test_read_after_write_is_idempotent(...)
```
- Writes configuration
- Immediately reads it back
- Verifies exact match
- Runs 50 examples

## Custom Strategies

### yaml_safe_text
```python
yaml_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
        blacklist_characters='...'  # Control characters excluded
    ),
    min_size=1
)
```
Generates YAML-safe strings without control characters.

### agent_config_strategy
```python
@st.composite
def agent_config_strategy(draw):
    return {
        "name": draw(yaml_safe_text),
        "model": draw(st.sampled_from([...])),
        "temperature": draw(st.floats(...)),
        "prompts": {...},
        # Optional fields
    }
```
Generates valid agent configurations.

### pipeline_config_strategy
```python
@st.composite
def pipeline_config_strategy(draw):
    return {
        "name": draw(yaml_safe_text),
        "description": draw(yaml_safe_text),
        "version": "1.x.0",
        "inputs": [...],
        "outputs": [...],
        "steps": [...]  # 1-5 steps
    }
```
Generates valid pipeline configurations with multiple steps.

## Running Tests

### Run all config API property tests
```bash
pytest tests/test_config_api_properties.py -v
```

### Run specific test class
```bash
pytest tests/test_config_api_properties.py::TestAgentConfigRoundTrip -v
```

### Run specific test
```bash
pytest tests/test_config_api_properties.py::TestAgentConfigRoundTrip::test_agent_config_read_write_round_trip -v
```

### Run with more examples
```bash
pytest tests/test_config_api_properties.py --hypothesis-seed=12345 -v
```

## Test Configuration

### Hypothesis Settings
```python
@settings(
    max_examples=100,  # or 50 for consistency tests
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
```

### Fixtures Used
- `temp_workspace`: Creates temporary agent/pipeline directories
- `test_client`: FastAPI TestClient instance
- `monkeypatch`: For mocking AgentRegistry and file lookups

## Common Patterns

### Agent Config Test Pattern
```python
# 1. Create test agent with config
agent_dir = create_test_agent(workspace, agent_id, config)

# 2. Mock agent registry
monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)

# 3. Read via API
response = test_client.get(f"/api/v1/config/agents/{agent_id}")

# 4. Update via API
response = test_client.put(
    f"/api/v1/config/agents/{agent_id}",
    json={"config": updated_config}
)

# 5. Read again and verify
response = test_client.get(f"/api/v1/config/agents/{agent_id}")
assert response.json()["config"] == updated_config
```

### Pipeline Config Test Pattern
```python
# 1. Create test pipeline with config
config_file = create_test_pipeline(workspace, pipeline_id, config)

# 2. Mock find_pipeline_config_file
monkeypatch.setattr(config_module, "find_pipeline_config_file", mock_func)

# 3. Read via API
response = test_client.get(f"/api/v1/config/pipelines/{pipeline_id}")

# 4. Update via API
response = test_client.put(
    f"/api/v1/config/pipelines/{pipeline_id}",
    json={"config": updated_config}
)

# 5. Read again and verify
response = test_client.get(f"/api/v1/config/pipelines/{pipeline_id}")
assert response.json()["config"] == updated_config
```

## Validation Checklist

✅ Agent configuration round-trip  
✅ Pipeline configuration round-trip  
✅ Custom field preservation  
✅ Complex structure preservation  
✅ Read consistency  
✅ Write idempotency  
✅ YAML-safe string generation  
✅ 100 examples per round-trip test  
✅ 50 examples per consistency test  

## Related Documentation
- [API Design Specification](./api-design-specification.md)
- [Config API Quick Reference](./config-api-quick-reference.md)
- [API Unit Tests Quick Reference](./api-unit-tests-quick-reference.md)
- [Model Serialization Guide](./model-serialization-guide.md)

## Property Definition

**Property 34: Configuration API read-write**
> For any configuration file, the system should support reading and writing through API endpoints with round-trip consistency.

This property ensures that:
1. Any configuration can be read via GET endpoint
2. Any configuration can be written via PUT endpoint
3. Reading after writing returns the exact written configuration
4. All fields (including custom fields) are preserved
5. Complex nested structures are preserved
6. Multiple reads return consistent results
