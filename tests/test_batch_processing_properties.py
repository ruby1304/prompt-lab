"""
Property-Based Tests for Batch Processing Configuration Parsing

These tests use Hypothesis to verify universal properties that should hold
across all valid batch processing configurations.

Feature: project-production-readiness
Property 22: Batch step configuration parsing
Validates: Requirements 4.1
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import assume

from src.models import StepConfig, PipelineConfig, CodeNodeConfig
from src.pipeline_config import validate_yaml_schema


# Custom strategies for generating valid batch processing configurations
@st.composite
def batch_mode_config_dict(draw):
    """Generate a valid batch mode configuration dictionary"""
    return {
        "batch_mode": True,
        "batch_size": draw(st.integers(min_value=1, max_value=100)),
        "concurrent": draw(st.booleans()),
        "max_workers": draw(st.integers(min_value=1, max_value=16))
    }


@st.composite
def aggregation_strategy_config_dict(draw):
    """Generate a valid aggregation strategy configuration"""
    strategy = draw(st.sampled_from(["concat", "stats", "filter", "group", "summary", "custom"]))
    
    config = {
        "aggregation_strategy": strategy
    }
    
    # Add strategy-specific required fields
    if strategy == "concat":
        config["separator"] = draw(st.sampled_from(["\n", ", ", " | ", "-", " "]))
    
    elif strategy == "stats":
        # Generate 1-5 field names
        num_fields = draw(st.integers(min_value=1, max_value=5))
        config["fields"] = [
            draw(st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'))
            for _ in range(num_fields)
        ]
    
    elif strategy == "filter":
        # Generate a simple filter condition
        config["condition"] = draw(st.sampled_from([
            "item.score > 0.5",
            "item.passed == True",
            "item.value >= 10",
            "item.status == 'success'"
        ]))
    
    elif strategy == "group":
        config["group_by"] = draw(st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'))
    
    elif strategy == "summary":
        # Generate 1-5 summary field names
        num_fields = draw(st.integers(min_value=1, max_value=5))
        config["summary_fields"] = [
            draw(st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'))
            for _ in range(num_fields)
        ]
    
    elif strategy == "custom":
        language = draw(st.sampled_from(["python", "javascript"]))
        config["language"] = language
        
        # Choose between inline code, aggregation_code, or code_file
        code_type = draw(st.sampled_from(["code", "aggregation_code", "code_file"]))
        
        if code_type == "code_file":
            config["code_file"] = draw(st.text(
                min_size=5,
                max_size=30,
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-/.py.js'
            ))
            # Ensure proper extension
            if language == "javascript" and not config["code_file"].endswith('.js'):
                config["code_file"] += '.js'
            elif language == "python" and not config["code_file"].endswith('.py'):
                config["code_file"] += '.py'
        else:
            # Generate simple inline code
            if language == "python":
                code = "def aggregate(items):\n    return {'count': len(items)}"
            else:  # javascript
                code = "function aggregate(items) { return {count: items.length}; }\nmodule.exports = aggregate;"
            
            config[code_type] = code
    
    return config


@st.composite
def batch_step_config_dict(draw):
    """Generate a valid batch processing step configuration"""
    step_id = draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ))
    # Ensure it starts with a letter
    if not step_id[0].isalpha():
        step_id = 'step_' + step_id
    
    output_key = draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ))
    if not output_key[0].isalpha():
        output_key = 'output_' + output_key
    
    # Choose step type: agent_flow with batch_mode or batch_aggregator
    step_type = draw(st.sampled_from(["agent_flow_batch", "batch_aggregator"]))
    
    if step_type == "agent_flow_batch":
        # Agent flow step with batch mode enabled
        step_config = {
            "id": step_id,
            "type": "agent_flow",
            "agent": draw(st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_')),
            "flow": draw(st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_')),
            "output_key": output_key,
            "input_mapping": draw(st.dictionaries(
                keys=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
                values=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
                max_size=3
            ))
        }
        # Add batch mode configuration
        batch_config = draw(batch_mode_config_dict())
        step_config.update(batch_config)
    
    else:  # batch_aggregator
        step_config = {
            "id": step_id,
            "type": "batch_aggregator",
            "output_key": output_key,
            "input_mapping": draw(st.dictionaries(
                keys=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
                values=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
                max_size=3
            ))
        }
        # Add aggregation strategy configuration
        agg_config = draw(aggregation_strategy_config_dict())
        step_config.update(agg_config)
    
    return step_config


@st.composite
def pipeline_with_batch_steps_dict(draw):
    """Generate a valid pipeline configuration with batch processing steps"""
    pipeline_id = draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ))
    if not pipeline_id[0].isalpha():
        pipeline_id = 'pipeline_' + pipeline_id
    
    # Generate 1-3 batch processing steps
    num_steps = draw(st.integers(min_value=1, max_value=3))
    steps = []
    
    for i in range(num_steps):
        step = draw(batch_step_config_dict())
        # Ensure unique step IDs
        step["id"] = f"step_{i}"
        step["output_key"] = f"output_{i}"
        steps.append(step)
    
    return {
        "id": pipeline_id,
        "name": draw(st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ')),
        "description": draw(st.text(min_size=0, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz ')),
        "inputs": [{"name": "input_data"}],
        "steps": steps,
        "outputs": [{"key": steps[-1]["output_key"]}]
    }


# Property 22: Batch step configuration parsing
# Feature: project-production-readiness, Property 22: Batch step configuration parsing
# Validates: Requirements 4.1
@settings(max_examples=100, deadline=None)
@given(batch_step=batch_step_config_dict())
def test_property_batch_step_config_parsing(batch_step):
    """
    Property 22: Batch step configuration parsing
    
    For any valid batch processing step configuration (either agent_flow with batch_mode
    or batch_aggregator), the system should successfully parse the configuration without errors.
    
    This property ensures that:
    1. All valid batch mode configurations are accepted
    2. All valid aggregation strategies are accepted
    3. Required fields for each strategy are properly validated
    4. The configuration can be converted to a StepConfig object
    
    Validates: Requirements 4.1
    """
    # Create a minimal pipeline config with the batch step
    pipeline_data = {
        "id": "test_pipeline",
        "name": "Test Pipeline",
        "steps": [batch_step],
        "inputs": [{"name": "input"}],
        "outputs": [{"key": batch_step["output_key"]}]
    }
    
    # Validate the YAML schema
    errors = validate_yaml_schema(pipeline_data)
    
    # The configuration should be valid (no errors)
    assert errors == [], f"Valid batch step configuration should not produce errors. Got: {errors}"
    
    # The configuration should be parseable into a PipelineConfig object
    try:
        config = PipelineConfig.from_dict(pipeline_data)
        assert config is not None, "Should successfully create PipelineConfig"
        assert len(config.steps) == 1, "Should have exactly one step"
        
        step = config.steps[0]
        assert step.id == batch_step["id"], "Step ID should match"
        assert step.output_key == batch_step["output_key"], "Output key should match"
        
        # Verify batch mode configuration if present
        if batch_step.get("batch_mode"):
            assert step.batch_mode is True, "Batch mode should be enabled"
            assert step.batch_size == batch_step["batch_size"], "Batch size should match"
            assert step.concurrent == batch_step["concurrent"], "Concurrent flag should match"
            assert step.max_workers == batch_step["max_workers"], "Max workers should match"
        
        # Verify aggregation strategy if present
        if batch_step.get("aggregation_strategy"):
            assert step.aggregation_strategy == batch_step["aggregation_strategy"], "Aggregation strategy should match"
            
            # Verify strategy-specific fields
            if batch_step["aggregation_strategy"] == "stats":
                assert step.fields == batch_step["fields"], "Stats fields should match"
            elif batch_step["aggregation_strategy"] == "filter":
                assert step.condition == batch_step["condition"], "Filter condition should match"
            elif batch_step["aggregation_strategy"] == "group":
                assert step.group_by == batch_step["group_by"], "Group by field should match"
            elif batch_step["aggregation_strategy"] == "summary":
                assert step.summary_fields == batch_step["summary_fields"], "Summary fields should match"
            elif batch_step["aggregation_strategy"] == "custom":
                assert step.language == batch_step["language"], "Language should match"
                # Check that at least one code field is present
                has_code = step.code or step.aggregation_code or step.code_file
                assert has_code, "Custom aggregation should have code"
        
    except Exception as e:
        pytest.fail(f"Failed to parse valid batch step configuration: {e}")


# Property 22.1: Batch mode field validation
# Feature: project-production-readiness, Property 22.1: Batch mode field validation
# Validates: Requirements 4.1
@settings(max_examples=100, deadline=None)
@given(batch_config=batch_mode_config_dict())
def test_property_batch_mode_field_validation(batch_config):
    """
    Property 22.1: Batch mode field validation
    
    For any valid batch mode configuration, all batch-related fields should be
    properly validated and accepted.
    
    This ensures that:
    1. batch_size must be a positive integer
    2. max_workers must be a positive integer
    3. concurrent must be a boolean
    
    Validates: Requirements 4.1
    """
    # Create a step with batch mode configuration
    step_data = {
        "id": "test_step",
        "type": "agent_flow",
        "agent": "test_agent",
        "flow": "test_flow",
        "output_key": "output",
        "input_mapping": {"text": "input"}
    }
    step_data.update(batch_config)
    
    pipeline_data = {
        "id": "test_pipeline",
        "name": "Test Pipeline",
        "steps": [step_data],
        "inputs": [{"name": "input"}],
        "outputs": [{"key": "output"}]
    }
    
    # Validate the configuration
    errors = validate_yaml_schema(pipeline_data)
    
    # Should have no errors for valid batch configuration
    assert errors == [], f"Valid batch mode configuration should not produce errors. Got: {errors}"
    
    # Verify the values are within expected ranges
    assert batch_config["batch_size"] >= 1, "Batch size should be positive"
    assert batch_config["max_workers"] >= 1, "Max workers should be positive"
    assert isinstance(batch_config["concurrent"], bool), "Concurrent should be boolean"


# Property 22.2: Aggregation strategy validation
# Feature: project-production-readiness, Property 22.2: Aggregation strategy validation
# Validates: Requirements 4.1
@settings(max_examples=100, deadline=None)
@given(agg_config=aggregation_strategy_config_dict())
def test_property_aggregation_strategy_validation(agg_config):
    """
    Property 22.2: Aggregation strategy validation
    
    For any valid aggregation strategy configuration, the system should accept
    the configuration and properly validate strategy-specific required fields.
    
    This ensures that:
    1. All supported aggregation strategies are accepted
    2. Strategy-specific required fields are present
    3. The configuration is internally consistent
    
    Validates: Requirements 4.1
    """
    # Create a batch aggregator step with the aggregation configuration
    step_data = {
        "id": "aggregator",
        "type": "batch_aggregator",
        "output_key": "aggregated",
        "input_mapping": {"items": "input"}
    }
    step_data.update(agg_config)
    
    pipeline_data = {
        "id": "test_pipeline",
        "name": "Test Pipeline",
        "steps": [step_data],
        "inputs": [{"name": "input"}],
        "outputs": [{"key": "aggregated"}]
    }
    
    # Validate the configuration
    errors = validate_yaml_schema(pipeline_data)
    
    # Should have no errors for valid aggregation configuration
    assert errors == [], f"Valid aggregation strategy configuration should not produce errors. Got: {errors}"
    
    # Verify strategy-specific fields are present
    strategy = agg_config["aggregation_strategy"]
    
    if strategy == "stats":
        assert "fields" in agg_config, "Stats strategy should have fields"
        assert len(agg_config["fields"]) > 0, "Stats fields should not be empty"
    
    elif strategy == "filter":
        assert "condition" in agg_config, "Filter strategy should have condition"
        assert agg_config["condition"], "Filter condition should not be empty"
    
    elif strategy == "group":
        assert "group_by" in agg_config, "Group strategy should have group_by"
        assert agg_config["group_by"], "Group by field should not be empty"
    
    elif strategy == "summary":
        assert "summary_fields" in agg_config, "Summary strategy should have summary_fields"
        assert len(agg_config["summary_fields"]) > 0, "Summary fields should not be empty"
    
    elif strategy == "custom":
        assert "language" in agg_config, "Custom strategy should have language"
        # Should have at least one of: code, aggregation_code, or code_file
        has_code = ("code" in agg_config or 
                   "aggregation_code" in agg_config or 
                   "code_file" in agg_config)
        assert has_code, "Custom strategy should have code"


# Property 22.3: Complete pipeline with batch steps parsing
# Feature: project-production-readiness, Property 22.3: Complete pipeline with batch steps parsing
# Validates: Requirements 4.1
@settings(max_examples=50, deadline=None)
@given(pipeline_data=pipeline_with_batch_steps_dict())
def test_property_complete_pipeline_with_batch_steps(pipeline_data):
    """
    Property 22.3: Complete pipeline with batch steps parsing
    
    For any valid pipeline configuration containing batch processing steps,
    the system should successfully parse the entire pipeline configuration.
    
    This ensures that:
    1. Multiple batch steps can coexist in a pipeline
    2. The pipeline structure remains valid with batch steps
    3. All batch configurations are properly preserved
    
    Validates: Requirements 4.1
    """
    # Validate the YAML schema
    errors = validate_yaml_schema(pipeline_data)
    
    # Should have no errors for valid pipeline with batch steps
    assert errors == [], f"Valid pipeline with batch steps should not produce errors. Got: {errors}"
    
    # Parse into PipelineConfig object
    try:
        config = PipelineConfig.from_dict(pipeline_data)
        assert config is not None, "Should successfully create PipelineConfig"
        assert config.id == pipeline_data["id"], "Pipeline ID should match"
        assert len(config.steps) == len(pipeline_data["steps"]), "Number of steps should match"
        
        # Verify each step is properly parsed
        for i, step in enumerate(config.steps):
            original_step = pipeline_data["steps"][i]
            assert step.id == original_step["id"], f"Step {i} ID should match"
            assert step.output_key == original_step["output_key"], f"Step {i} output key should match"
            
            # Verify batch-specific fields if present
            if original_step.get("batch_mode"):
                assert step.batch_mode is True, f"Step {i} should have batch mode enabled"
            
            if original_step.get("aggregation_strategy"):
                assert step.aggregation_strategy == original_step["aggregation_strategy"], \
                    f"Step {i} aggregation strategy should match"
        
        # Verify the configuration is valid
        validation_errors = config.validate()
        assert validation_errors == [], \
            f"Parsed pipeline configuration should be valid. Got errors: {validation_errors}"
        
    except Exception as e:
        pytest.fail(f"Failed to parse valid pipeline with batch steps: {e}")


# Property 23: Batch output collection
# Feature: project-production-readiness, Property 23: Batch output collection
# Validates: Requirements 4.2
@settings(max_examples=100, deadline=None)
@given(
    num_items=st.integers(min_value=1, max_value=20),
    batch_size=st.integers(min_value=1, max_value=10)
)
def test_property_batch_output_collection(num_items, batch_size):
    """
    Property 23: Batch output collection
    
    For any batch processing step, the system should collect all outputs from
    the batch execution, regardless of batch size or number of items.
    
    This property ensures that:
    1. All batch items are processed
    2. All outputs are collected
    3. No outputs are lost during batch processing
    4. The number of outputs matches the number of inputs
    5. Token usage is correctly aggregated across all batch items
    
    Validates: Requirements 4.2
    """
    from src.batch_aggregator import BatchProcessor
    
    # Create a BatchProcessor
    processor = BatchProcessor()
    
    # Create test input items
    input_items = [{"id": i, "value": f"item_{i}"} for i in range(num_items)]
    
    # Track how many times the processor function is called
    call_count = [0]
    collected_inputs = []
    
    def mock_processor(item):
        """Mock processor that returns a processed version of the item"""
        call_count[0] += 1
        collected_inputs.append(item)
        return {
            "processed_id": item["id"],
            "processed_value": f"processed_{item['value']}",
            "token_usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
        }
    
    # Process items in batches
    results = processor.process_in_batches(
        items=input_items,
        processor=mock_processor,
        batch_size=batch_size,
        concurrent=False  # Sequential for deterministic testing
    )
    
    # Verify all outputs were collected
    assert len(results) == num_items, \
        f"Should collect {num_items} outputs, but got {len(results)}"
    
    # Verify the processor was called for each item
    assert call_count[0] == num_items, \
        f"Processor should be called {num_items} times, but was called {call_count[0]} times"
    
    # Verify all inputs were processed
    assert len(collected_inputs) == num_items, \
        f"Should have processed {num_items} inputs, but got {len(collected_inputs)}"
    
    # Verify outputs match expected format and order
    for i, result in enumerate(results):
        assert result["processed_id"] == i, \
            f"Result {i} should have processed_id={i}, but got {result['processed_id']}"
        assert result["processed_value"] == f"processed_item_{i}", \
            f"Result {i} should have processed_value='processed_item_{i}', but got '{result['processed_value']}'"
    
    # Verify no outputs are lost - check that all input IDs are present in outputs
    output_ids = {result["processed_id"] for result in results}
    expected_ids = set(range(num_items))
    assert output_ids == expected_ids, \
        f"Output IDs {output_ids} should match expected IDs {expected_ids}"
    
    # Verify token usage can be aggregated
    total_tokens = sum(result.get("token_usage", {}).get("total_tokens", 0) for result in results)
    expected_total_tokens = num_items * 20
    assert total_tokens == expected_total_tokens, \
        f"Total tokens should be {expected_total_tokens}, but got {total_tokens}"


# Property 24: Batch aggregation correctness
# Feature: project-production-readiness, Property 24: Batch aggregation correctness
# Validates: Requirements 4.3
@settings(max_examples=100, deadline=None)
@given(
    num_items=st.integers(min_value=1, max_value=50),
    strategy=st.sampled_from(["concat", "stats", "filter"])
)
def test_property_batch_aggregation_correctness(num_items, strategy):
    """
    Property 24: Batch aggregation correctness
    
    For any batch aggregation with a defined strategy (concat, stats, filter),
    the aggregated result should match the expected output format and be correct.
    
    This property ensures that:
    1. Concat strategy produces a string with all items
    2. Stats strategy produces correct statistics for numeric fields
    3. Filter strategy produces a subset of items matching the condition
    4. The aggregation result is deterministic and reproducible
    5. The aggregation handles edge cases (empty items, missing fields, etc.)
    
    Validates: Requirements 4.3
    """
    from src.batch_aggregator import BatchAggregator
    
    aggregator = BatchAggregator()
    
    # Generate test items based on strategy
    if strategy == "concat":
        # Generate items with text content
        items = [{"text": f"item_{i}", "id": i} for i in range(num_items)]
        separator = " | "
        
        # Perform aggregation
        result = aggregator.aggregate(items, strategy="concat", separator=separator)
        
        # Verify result
        assert result.success, f"Concat aggregation should succeed, but got error: {result.error}"
        assert isinstance(result.result, str), "Concat result should be a string"
        assert result.strategy == "concat", "Strategy should be 'concat'"
        assert result.item_count == num_items, f"Item count should be {num_items}"
        
        # Verify all items are present in the result
        for i in range(num_items):
            assert f"item_{i}" in result.result, f"Result should contain 'item_{i}'"
        
        # Verify separator is used correctly (should appear num_items - 1 times)
        if num_items > 1:
            separator_count = result.result.count(separator)
            assert separator_count == num_items - 1, \
                f"Separator should appear {num_items - 1} times, but appeared {separator_count} times"
        
        # Verify the result is reproducible
        result2 = aggregator.aggregate(items, strategy="concat", separator=separator)
        assert result.result == result2.result, "Concat aggregation should be deterministic"
    
    elif strategy == "stats":
        # Generate items with numeric fields
        items = [
            {
                "score": 50 + i,
                "time": 1.0 + (i * 0.1),
                "count": i + 1,
                "id": i
            }
            for i in range(num_items)
        ]
        fields = ["score", "time", "count"]
        
        # Perform aggregation
        result = aggregator.aggregate(items, strategy="stats", fields=fields)
        
        # Verify result
        assert result.success, f"Stats aggregation should succeed, but got error: {result.error}"
        assert isinstance(result.result, dict), "Stats result should be a dictionary"
        assert result.strategy == "stats", "Strategy should be 'stats'"
        assert result.item_count == num_items, f"Item count should be {num_items}"
        
        # Verify result structure
        assert "total_items" in result.result, "Result should have 'total_items'"
        assert result.result["total_items"] == num_items, "Total items should match"
        assert "fields" in result.result, "Result should have 'fields'"
        
        # Verify statistics for each field
        for field in fields:
            assert field in result.result["fields"], f"Result should have stats for field '{field}'"
            field_stats = result.result["fields"][field]
            
            # Verify required statistics are present
            assert "count" in field_stats, f"Field '{field}' should have 'count'"
            assert "sum" in field_stats, f"Field '{field}' should have 'sum'"
            assert "mean" in field_stats, f"Field '{field}' should have 'mean'"
            assert "min" in field_stats, f"Field '{field}' should have 'min'"
            assert "max" in field_stats, f"Field '{field}' should have 'max'"
            
            # Verify count is correct
            assert field_stats["count"] == num_items, \
                f"Field '{field}' count should be {num_items}"
            
            # Verify statistics are mathematically correct
            expected_values = [items[i][field] for i in range(num_items)]
            expected_sum = sum(expected_values)
            expected_mean = expected_sum / len(expected_values)
            
            # Use approximate equality for floating-point comparisons
            assert abs(field_stats["sum"] - expected_sum) < 1e-9, \
                f"Field '{field}' sum should be approximately {expected_sum}, got {field_stats['sum']}"
            assert abs(field_stats["mean"] - expected_mean) < 1e-9, \
                f"Field '{field}' mean should be approximately {expected_mean}, got {field_stats['mean']}"
            assert field_stats["min"] == min(expected_values), \
                f"Field '{field}' min should be {min(expected_values)}"
            assert field_stats["max"] == max(expected_values), \
                f"Field '{field}' max should be {max(expected_values)}"
            
            # Verify median and stdev are present for multiple items
            if num_items >= 2:
                assert "median" in field_stats, f"Field '{field}' should have 'median' for multiple items"
                assert "stdev" in field_stats, f"Field '{field}' should have 'stdev' for multiple items"
        
        # Verify the result is reproducible
        result2 = aggregator.aggregate(items, strategy="stats", fields=fields)
        assert result.result == result2.result, "Stats aggregation should be deterministic"
    
    elif strategy == "filter":
        # Generate items with boolean field for filtering
        items = [
            {
                "value": i,
                "passed": i % 2 == 0,  # Even numbers pass
                "id": i
            }
            for i in range(num_items)
        ]
        
        # Define filter condition
        condition = lambda item: item.get("passed", False)
        
        # Perform aggregation
        result = aggregator.aggregate(items, strategy="filter", condition=condition)
        
        # Verify result
        assert result.success, f"Filter aggregation should succeed, but got error: {result.error}"
        assert isinstance(result.result, list), "Filter result should be a list"
        assert result.strategy == "filter", "Strategy should be 'filter'"
        assert result.item_count == num_items, f"Item count should be {num_items}"
        
        # Verify all filtered items match the condition
        for item in result.result:
            assert condition(item), "All filtered items should match the condition"
        
        # Verify no items that don't match the condition are included
        expected_count = sum(1 for item in items if condition(item))
        assert len(result.result) == expected_count, \
            f"Filter should return {expected_count} items, but returned {len(result.result)}"
        
        # Verify the filtered items are the correct ones
        expected_items = [item for item in items if condition(item)]
        assert result.result == expected_items, "Filter should return the correct items"
        
        # Verify the result is reproducible
        result2 = aggregator.aggregate(items, strategy="filter", condition=condition)
        assert result.result == result2.result, "Filter aggregation should be deterministic"


# Property 24.1: Concat aggregation with different separators
# Feature: project-production-readiness, Property 24.1: Concat aggregation with different separators
# Validates: Requirements 4.3
@settings(max_examples=100, deadline=None)
@given(
    num_items=st.integers(min_value=1, max_value=30),
    separator=st.sampled_from(["\n", ", ", " | ", " - ", " ", "\t", "---"])
)
def test_property_concat_aggregation_separators(num_items, separator):
    """
    Property 24.1: Concat aggregation with different separators
    
    For any list of items and any separator, concat aggregation should
    correctly join all items with the specified separator.
    
    Validates: Requirements 4.3
    """
    from src.batch_aggregator import BatchAggregator
    
    aggregator = BatchAggregator()
    
    # Generate items with text content
    items = [f"text_{i}" for i in range(num_items)]
    
    # Perform aggregation
    result = aggregator.aggregate(items, strategy="concat", separator=separator)
    
    # Verify result
    assert result.success, f"Concat aggregation should succeed"
    assert isinstance(result.result, str), "Result should be a string"
    
    # Verify the result matches manual concatenation
    expected = separator.join(items)
    assert result.result == expected, \
        f"Result should match manual concatenation. Expected: {expected}, Got: {result.result}"


# Property 24.2: Stats aggregation with missing fields
# Feature: project-production-readiness, Property 24.2: Stats aggregation with missing fields
# Validates: Requirements 4.3
@settings(max_examples=100, deadline=None)
@given(
    num_items=st.integers(min_value=2, max_value=30),
    missing_ratio=st.floats(min_value=0.0, max_value=0.5)
)
def test_property_stats_aggregation_missing_fields(num_items, missing_ratio):
    """
    Property 24.2: Stats aggregation with missing fields
    
    For any list of items where some items may have missing fields,
    stats aggregation should correctly calculate statistics only on
    items that have the field.
    
    Validates: Requirements 4.3
    """
    from src.batch_aggregator import BatchAggregator
    import random
    
    aggregator = BatchAggregator()
    
    # Generate items with some missing fields
    items = []
    for i in range(num_items):
        item = {"id": i}
        # Randomly include or exclude the score field
        if random.random() > missing_ratio:
            item["score"] = 50 + i
        items.append(item)
    
    # Perform aggregation
    result = aggregator.aggregate(items, strategy="stats", fields=["score"])
    
    # Verify result
    assert result.success, f"Stats aggregation should succeed even with missing fields"
    assert isinstance(result.result, dict), "Result should be a dictionary"
    
    # Count how many items actually have the score field
    items_with_score = [item for item in items if "score" in item]
    
    if items_with_score:
        # If some items have the field, verify statistics
        field_stats = result.result["fields"]["score"]
        assert field_stats["count"] == len(items_with_score), \
            f"Count should match number of items with the field"
        
        # Verify statistics are correct for items that have the field
        expected_values = [item["score"] for item in items_with_score]
        expected_sum = sum(expected_values)
        expected_mean = expected_sum / len(expected_values)
        
        # Use approximate equality for floating-point comparisons
        assert abs(field_stats["sum"] - expected_sum) < 1e-9, "Sum should be correct"
        assert abs(field_stats["mean"] - expected_mean) < 1e-9, "Mean should be correct"
        assert field_stats["min"] == min(expected_values), "Min should be correct"
        assert field_stats["max"] == max(expected_values), "Max should be correct"
    else:
        # If no items have the field, verify error is reported
        field_stats = result.result["fields"]["score"]
        assert field_stats["count"] == 0, "Count should be 0 for missing field"
        assert "error" in field_stats, "Should report error for missing field"


# Property 24.3: Filter aggregation preserves item order
# Feature: project-production-readiness, Property 24.3: Filter aggregation preserves item order
# Validates: Requirements 4.3
@settings(max_examples=100, deadline=None)
@given(
    num_items=st.integers(min_value=5, max_value=50),
    threshold=st.integers(min_value=0, max_value=100)
)
def test_property_filter_aggregation_order_preservation(num_items, threshold):
    """
    Property 24.3: Filter aggregation preserves item order
    
    For any list of items and any filter condition, filter aggregation
    should preserve the relative order of items that pass the filter.
    
    Validates: Requirements 4.3
    """
    from src.batch_aggregator import BatchAggregator
    
    aggregator = BatchAggregator()
    
    # Generate items with sequential IDs
    items = [{"id": i, "value": i * 2} for i in range(num_items)]
    
    # Define filter condition
    condition = lambda item: item["value"] >= threshold
    
    # Perform aggregation
    result = aggregator.aggregate(items, strategy="filter", condition=condition)
    
    # Verify result
    assert result.success, f"Filter aggregation should succeed"
    assert isinstance(result.result, list), "Result should be a list"
    
    # Verify order is preserved
    if len(result.result) > 1:
        for i in range(len(result.result) - 1):
            assert result.result[i]["id"] < result.result[i + 1]["id"], \
                "Filter should preserve the original order of items"
    
    # Verify all items in result match the condition
    for item in result.result:
        assert condition(item), "All filtered items should match the condition"
    
    # Verify no items that match the condition are missing
    expected_items = [item for item in items if condition(item)]
    assert len(result.result) == len(expected_items), \
        "Filter should return all items that match the condition"


# Property 24.4: Empty items list handling
# Feature: project-production-readiness, Property 24.4: Empty items list handling
# Validates: Requirements 4.3
@settings(max_examples=50, deadline=None)
@given(strategy=st.sampled_from(["concat", "stats", "filter"]))
def test_property_empty_items_handling(strategy):
    """
    Property 24.4: Empty items list handling
    
    For any aggregation strategy, when given an empty items list,
    the aggregation should handle it gracefully without errors.
    
    Validates: Requirements 4.3
    """
    from src.batch_aggregator import BatchAggregator
    
    aggregator = BatchAggregator()
    
    # Empty items list
    items = []
    
    # Perform aggregation with appropriate parameters
    if strategy == "concat":
        result = aggregator.aggregate(items, strategy="concat", separator="\n")
    elif strategy == "stats":
        result = aggregator.aggregate(items, strategy="stats", fields=["score"])
    elif strategy == "filter":
        result = aggregator.aggregate(items, strategy="filter", condition=lambda x: True)
    
    # Verify result
    assert result.success, f"Aggregation should succeed even with empty items list"
    assert result.item_count == 0, "Item count should be 0 for empty list"
    assert result.strategy == strategy, f"Strategy should be '{strategy}'"
    
    # Verify result is None or appropriate empty value
    assert result.result is None or result.result == "" or result.result == [], \
        "Result should be None or empty for empty items list"


# Property 25: Aggregation result passing
# Feature: project-production-readiness, Property 25: Aggregation result passing
# Validates: Requirements 4.4
@settings(max_examples=100, deadline=None)
@given(
    num_items=st.integers(min_value=2, max_value=20),
    aggregation_strategy=st.sampled_from(["concat", "stats", "filter"])
)
def test_property_aggregation_result_passing(num_items, aggregation_strategy):
    """
    Property 25: Aggregation result passing
    
    For any batch aggregation step followed by an agent step, the aggregated
    result should be correctly passed as input to the subsequent step.
    
    This property ensures that:
    1. The aggregation result is stored in the pipeline context
    2. The subsequent step can access the aggregation result through input_mapping
    3. The aggregation result maintains its structure and content
    4. The data flow from aggregation to next step is correct
    
    Validates: Requirements 4.4
    """
    from src.pipeline_runner import PipelineRunner
    from src.models import PipelineConfig, StepConfig
    
    # Generate test items based on strategy
    if aggregation_strategy == "concat":
        items = [f"text_{i}" for i in range(num_items)]
        separator = " | "
        expected_result = separator.join(items)
        
        # Create aggregation step
        agg_step = StepConfig(
            id="aggregator",
            type="batch_aggregator",
            aggregation_strategy="concat",
            separator=separator,
            input_mapping={"items": "input_items"},
            output_key="aggregated_output"
        )
    
    elif aggregation_strategy == "stats":
        items = [{"score": 50 + i, "value": i * 2} for i in range(num_items)]
        fields = ["score", "value"]
        
        # Create aggregation step
        agg_step = StepConfig(
            id="aggregator",
            type="batch_aggregator",
            aggregation_strategy="stats",
            fields=fields,
            input_mapping={"items": "input_items"},
            output_key="aggregated_output"
        )
        
        # Expected result structure
        expected_result = {
            "total_items": num_items,
            "fields": {
                "score": {
                    "count": num_items,
                    "sum": sum(item["score"] for item in items),
                    "mean": sum(item["score"] for item in items) / num_items,
                    "min": min(item["score"] for item in items),
                    "max": max(item["score"] for item in items)
                },
                "value": {
                    "count": num_items,
                    "sum": sum(item["value"] for item in items),
                    "mean": sum(item["value"] for item in items) / num_items,
                    "min": min(item["value"] for item in items),
                    "max": max(item["value"] for item in items)
                }
            }
        }
    
    elif aggregation_strategy == "filter":
        items = [{"id": i, "value": i * 2, "passed": i % 2 == 0} for i in range(num_items)]
        condition = lambda item: item.get("passed", False)
        
        # Create aggregation step
        agg_step = StepConfig(
            id="aggregator",
            type="batch_aggregator",
            aggregation_strategy="filter",
            condition=condition,
            input_mapping={"items": "input_items"},
            output_key="aggregated_output"
        )
        
        # Expected result
        expected_result = [item for item in items if condition(item)]
    
    # Create a mock "next step" that captures its input
    captured_input = {}
    
    def mock_next_step_processor(input_data):
        """Mock processor that captures the input it receives"""
        captured_input["received"] = input_data
        return {"processed": True, "input_received": input_data}
    
    # Create a code node step that will receive the aggregation result
    # The code node will transform the aggregated data
    next_step = StepConfig(
        id="next_step",
        type="code_node",
        code_config=CodeNodeConfig(
            language="python",
            code="""
def transform(inputs):
    aggregated_data = inputs.get('aggregated_data')
    return {
        "processed": True,
        "data": aggregated_data,
        "data_type": type(aggregated_data).__name__
    }
""",
            timeout=30
        ),
        input_mapping={"aggregated_data": "aggregated_output"},
        output_key="final_output"
    )
    
    # Create pipeline configuration
    pipeline_config = PipelineConfig(
        id="test_pipeline",
        name="Test Aggregation Result Passing",
        description="Test that aggregation results are correctly passed to next step",
        inputs=[{"name": "input_items"}],
        steps=[agg_step, next_step],
        outputs=[{"key": "final_output"}]
    )
    
    # Create pipeline runner
    runner = PipelineRunner(pipeline_config)
    
    # Execute the pipeline
    result = runner.execute_sample(
        sample={"id": "test_sample", "input_items": items}
    )
    
    # Verify the pipeline executed successfully
    assert result.error is None, f"Pipeline should execute successfully, but got error: {result.error}"
    assert len(result.step_results) == 2, "Should have results for both steps"
    
    # Verify the aggregation step executed successfully
    agg_result = result.step_results[0]
    assert agg_result.step_id == "aggregator", "First step should be aggregator"
    assert agg_result.success, f"Aggregation step should succeed, but got error: {agg_result.error}"
    assert agg_result.output_key == "aggregated_output", "Aggregation output key should match"
    
    # Verify the aggregation result is correct
    if aggregation_strategy == "concat":
        assert agg_result.output_value == expected_result, \
            f"Aggregation result should match expected. Expected: {expected_result}, Got: {agg_result.output_value}"
    
    elif aggregation_strategy == "stats":
        assert isinstance(agg_result.output_value, dict), "Stats result should be a dictionary"
        assert agg_result.output_value["total_items"] == expected_result["total_items"], \
            "Total items should match"
        
        # Verify field statistics (with tolerance for floating point)
        for field in fields:
            assert field in agg_result.output_value["fields"], f"Field '{field}' should be in result"
            actual_stats = agg_result.output_value["fields"][field]
            expected_stats = expected_result["fields"][field]
            
            assert actual_stats["count"] == expected_stats["count"], \
                f"Field '{field}' count should match"
            assert abs(actual_stats["sum"] - expected_stats["sum"]) < 1e-9, \
                f"Field '{field}' sum should match"
            assert abs(actual_stats["mean"] - expected_stats["mean"]) < 1e-9, \
                f"Field '{field}' mean should match"
            assert actual_stats["min"] == expected_stats["min"], \
                f"Field '{field}' min should match"
            assert actual_stats["max"] == expected_stats["max"], \
                f"Field '{field}' max should match"
    
    elif aggregation_strategy == "filter":
        assert isinstance(agg_result.output_value, list), "Filter result should be a list"
        assert agg_result.output_value == expected_result, \
            f"Filter result should match expected. Expected: {expected_result}, Got: {agg_result.output_value}"
    
    # Verify the aggregation result was stored in context
    assert "aggregated_output" in runner.context, \
        "Aggregation result should be stored in pipeline context"
    assert runner.context["aggregated_output"] == agg_result.output_value, \
        "Context should contain the aggregation result"
    
    # Verify the next step executed successfully
    next_result = result.step_results[1]
    assert next_result.step_id == "next_step", "Second step should be next_step"
    assert next_result.success, f"Next step should succeed, but got error: {next_result.error}"
    assert next_result.output_key == "final_output", "Next step output key should match"
    
    # Verify the next step received the aggregation result
    assert next_result.output_value is not None, "Next step should produce output"
    assert isinstance(next_result.output_value, dict), "Next step output should be a dictionary"
    assert next_result.output_value.get("processed") is True, \
        "Next step should indicate it processed the data"
    
    # Verify the data passed to next step matches the aggregation result
    # The code node should have received the aggregation result through input_mapping
    assert "data" in next_result.output_value, "Next step output should contain 'data' field"
    
    # The data field should match the aggregation result
    if aggregation_strategy == "concat":
        assert next_result.output_value["data"] == expected_result, \
            "Next step should receive the correct aggregation result"
    elif aggregation_strategy == "stats":
        assert isinstance(next_result.output_value["data"], dict), \
            "Next step should receive stats as dictionary"
        assert next_result.output_value["data"]["total_items"] == expected_result["total_items"], \
            "Next step should receive correct total_items"
    elif aggregation_strategy == "filter":
        assert isinstance(next_result.output_value["data"], list), \
            "Next step should receive filter result as list"
        assert len(next_result.output_value["data"]) == len(expected_result), \
            "Next step should receive correct number of filtered items"
    
    # Verify the final output is available
    assert "final_output" in result.final_outputs, "Final output should be available"
    assert result.final_outputs["final_output"] == next_result.output_value, \
        "Final output should match next step output"


# Property 25.1: Aggregation result passing with multiple subsequent steps
# Feature: project-production-readiness, Property 25.1: Aggregation result passing with multiple steps
# Validates: Requirements 4.4
@settings(max_examples=50, deadline=None)
@given(
    num_items=st.integers(min_value=2, max_value=15),
    num_subsequent_steps=st.integers(min_value=2, max_value=4)
)
def test_property_aggregation_result_passing_multiple_steps(num_items, num_subsequent_steps):
    """
    Property 25.1: Aggregation result passing with multiple subsequent steps
    
    For any batch aggregation step followed by multiple subsequent steps,
    all subsequent steps should be able to access the aggregation result.
    
    This ensures that:
    1. The aggregation result remains available in context for all subsequent steps
    2. Multiple steps can independently access the same aggregation result
    3. The aggregation result is not modified or lost during pipeline execution
    
    Validates: Requirements 4.4
    """
    from src.pipeline_runner import PipelineRunner
    from src.models import PipelineConfig, StepConfig
    
    # Generate test items
    items = [f"item_{i}" for i in range(num_items)]
    separator = " | "
    expected_result = separator.join(items)
    
    # Create aggregation step
    agg_step = StepConfig(
        id="aggregator",
        type="batch_aggregator",
        aggregation_strategy="concat",
        separator=separator,
        input_mapping={"items": "input_items"},
        output_key="aggregated_output"
    )
    
    # Create multiple subsequent steps that all use the aggregation result
    subsequent_steps = []
    for i in range(num_subsequent_steps):
        step = StepConfig(
            id=f"step_{i}",
            type="code_node",
            code_config=CodeNodeConfig(
                language="python",
                code=f"""
def transform(inputs):
    data = inputs.get('data')
    return {{
        "step_id": {i},
        "received_data": data,
        "data_length": len(str(data))
    }}
""",
                timeout=30
            ),
            input_mapping={"data": "aggregated_output"},
            output_key=f"output_{i}"
        )
        subsequent_steps.append(step)
    
    # Create pipeline configuration
    pipeline_config = PipelineConfig(
        id="test_pipeline",
        name="Test Multiple Steps Accessing Aggregation Result",
        description="Test that multiple steps can access the same aggregation result",
        inputs=[{"name": "input_items"}],
        steps=[agg_step] + subsequent_steps,
        outputs=[{"key": f"output_{num_subsequent_steps - 1}"}]
    )
    
    # Create pipeline runner
    runner = PipelineRunner(pipeline_config)
    
    # Execute the pipeline
    result = runner.execute_sample(
        sample={"id": "test_sample", "input_items": items}
    )
    
    # Verify the pipeline executed successfully
    assert result.error is None, f"Pipeline should execute successfully, but got error: {result.error}"
    assert len(result.step_results) == 1 + num_subsequent_steps, \
        f"Should have results for aggregator + {num_subsequent_steps} subsequent steps"
    
    # Verify the aggregation step executed successfully
    agg_result = result.step_results[0]
    assert agg_result.success, "Aggregation step should succeed"
    assert agg_result.output_value == expected_result, "Aggregation result should be correct"
    
    # Verify all subsequent steps executed successfully and received the aggregation result
    for i in range(num_subsequent_steps):
        step_result = result.step_results[i + 1]
        assert step_result.step_id == f"step_{i}", f"Step {i} ID should match"
        assert step_result.success, f"Step {i} should succeed, but got error: {step_result.error}"
        
        # Verify the step received the aggregation result
        assert isinstance(step_result.output_value, dict), f"Step {i} output should be a dictionary"
        assert step_result.output_value.get("step_id") == i, f"Step {i} should have correct step_id"
        assert "received_data" in step_result.output_value, f"Step {i} should have received_data"
        
        # Verify the received data matches the aggregation result
        assert step_result.output_value["received_data"] == expected_result, \
            f"Step {i} should receive the correct aggregation result"
        
        # Verify data length is correct
        expected_length = len(expected_result)
        assert step_result.output_value["data_length"] == expected_length, \
            f"Step {i} should calculate correct data length"
    
    # Verify the aggregation result is still in context after all steps
    assert "aggregated_output" in runner.context, \
        "Aggregation result should remain in context after all steps"
    assert runner.context["aggregated_output"] == expected_result, \
        "Context should still contain the original aggregation result"


# Property 26: Aggregation strategy parsing
# Feature: project-production-readiness, Property 26: Aggregation strategy parsing
# Validates: Requirements 4.5
@settings(max_examples=100, deadline=None)
@given(
    strategy=st.sampled_from(["concat", "stats", "filter", "custom"]),
    num_items=st.integers(min_value=1, max_value=30)
)
def test_property_aggregation_strategy_parsing(strategy, num_items):
    """
    Property 26: Aggregation strategy parsing
    
    For any batch aggregation configuration with a strategy (concat, stats, filter, 
    group, summary, custom), the system should correctly parse and apply the strategy.
    
    This property ensures that:
    1. All supported aggregation strategies are correctly parsed from configuration
    2. Strategy-specific parameters are correctly extracted
    3. The parsed strategy is correctly applied to batch data
    4. The aggregation produces results in the expected format for each strategy
    5. The strategy name is preserved in the aggregation result
    
    Validates: Requirements 4.5
    """
    from src.batch_aggregator import BatchAggregator
    from src.models import StepConfig
    from src.pipeline_config import validate_yaml_schema
    
    aggregator = BatchAggregator()
    
    # Generate test items and configuration based on strategy
    if strategy == "concat":
        items = [f"text_{i}" for i in range(num_items)]
        separator = " | "
        
        # Create step configuration
        step_config = {
            "id": "aggregator",
            "type": "batch_aggregator",
            "aggregation_strategy": "concat",
            "separator": separator,
            "input_mapping": {"items": "input"},
            "output_key": "output"
        }
        
        # Validate configuration parsing
        pipeline_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [step_config],
            "inputs": [{"name": "input"}],
            "outputs": [{"key": "output"}]
        }
        
        errors = validate_yaml_schema(pipeline_data)
        assert errors == [], f"Configuration should be valid for strategy '{strategy}', but got errors: {errors}"
        
        # Parse into StepConfig
        step = StepConfig.from_dict(step_config)
        assert step.aggregation_strategy == "concat", "Strategy should be parsed as 'concat'"
        assert step.separator == separator, "Separator should be parsed correctly"
        
        # Apply the strategy
        result = aggregator.aggregate(items, strategy="concat", separator=separator)
        
        # Verify result
        assert result.success, f"Aggregation should succeed for strategy '{strategy}'"
        assert result.strategy == "concat", "Result should preserve strategy name"
        assert isinstance(result.result, str), "Concat result should be a string"
        assert result.result == separator.join(items), "Concat result should match expected"
    
    elif strategy == "stats":
        items = [{"score": 50 + i, "value": i * 2} for i in range(num_items)]
        fields = ["score", "value"]
        
        # Create step configuration
        step_config = {
            "id": "aggregator",
            "type": "batch_aggregator",
            "aggregation_strategy": "stats",
            "fields": fields,
            "input_mapping": {"items": "input"},
            "output_key": "output"
        }
        
        # Validate configuration parsing
        pipeline_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [step_config],
            "inputs": [{"name": "input"}],
            "outputs": [{"key": "output"}]
        }
        
        errors = validate_yaml_schema(pipeline_data)
        assert errors == [], f"Configuration should be valid for strategy '{strategy}', but got errors: {errors}"
        
        # Parse into StepConfig
        step = StepConfig.from_dict(step_config)
        assert step.aggregation_strategy == "stats", "Strategy should be parsed as 'stats'"
        assert step.fields == fields, "Fields should be parsed correctly"
        
        # Apply the strategy
        result = aggregator.aggregate(items, strategy="stats", fields=fields)
        
        # Verify result
        assert result.success, f"Aggregation should succeed for strategy '{strategy}'"
        assert result.strategy == "stats", "Result should preserve strategy name"
        assert isinstance(result.result, dict), "Stats result should be a dictionary"
        assert "total_items" in result.result, "Stats result should have 'total_items'"
        assert "fields" in result.result, "Stats result should have 'fields'"
        
        # Verify all requested fields are present
        for field in fields:
            assert field in result.result["fields"], f"Stats result should have field '{field}'"
    
    elif strategy == "filter":
        items = [{"id": i, "value": i * 2, "passed": i % 2 == 0} for i in range(num_items)]
        condition = lambda item: item.get("passed", False)
        
        # Create step configuration
        step_config = {
            "id": "aggregator",
            "type": "batch_aggregator",
            "aggregation_strategy": "filter",
            "condition": "item.get('passed', False)",
            "input_mapping": {"items": "input"},
            "output_key": "output"
        }
        
        # Validate configuration parsing
        pipeline_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [step_config],
            "inputs": [{"name": "input"}],
            "outputs": [{"key": "output"}]
        }
        
        errors = validate_yaml_schema(pipeline_data)
        assert errors == [], f"Configuration should be valid for strategy '{strategy}', but got errors: {errors}"
        
        # Parse into StepConfig
        step = StepConfig.from_dict(step_config)
        assert step.aggregation_strategy == "filter", "Strategy should be parsed as 'filter'"
        assert step.condition is not None, "Condition should be parsed"
        
        # Apply the strategy
        result = aggregator.aggregate(items, strategy="filter", condition=condition)
        
        # Verify result
        assert result.success, f"Aggregation should succeed for strategy '{strategy}'"
        assert result.strategy == "filter", "Result should preserve strategy name"
        assert isinstance(result.result, list), "Filter result should be a list"
        
        # Verify all items match the condition
        for item in result.result:
            assert condition(item), "All filtered items should match the condition"
    
    elif strategy == "custom":
        items = [{"id": i, "value": i * 2} for i in range(num_items)]
        
        # Create custom aggregation code
        custom_code = """
def aggregate(items):
    return {
        "count": len(items),
        "total": sum(item.get("value", 0) for item in items),
        "ids": [item.get("id") for item in items]
    }
"""
        
        # Create step configuration
        step_config = {
            "id": "aggregator",
            "type": "batch_aggregator",
            "aggregation_strategy": "custom",
            "language": "python",
            "aggregation_code": custom_code,
            "input_mapping": {"items": "input"},
            "output_key": "output"
        }
        
        # Validate configuration parsing
        pipeline_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [step_config],
            "inputs": [{"name": "input"}],
            "outputs": [{"key": "output"}]
        }
        
        errors = validate_yaml_schema(pipeline_data)
        assert errors == [], f"Configuration should be valid for strategy '{strategy}', but got errors: {errors}"
        
        # Parse into StepConfig
        step = StepConfig.from_dict(step_config)
        assert step.aggregation_strategy == "custom", "Strategy should be parsed as 'custom'"
        assert step.language == "python", "Language should be parsed correctly"
        assert step.aggregation_code is not None, "Aggregation code should be parsed"
        
        # Apply the strategy
        result = aggregator.aggregate(
            items, 
            strategy="custom", 
            language="python",
            code=custom_code
        )
        
        # Verify result
        assert result.success, f"Aggregation should succeed for strategy '{strategy}'"
        assert result.strategy == "custom", "Result should preserve strategy name"
        assert isinstance(result.result, dict), "Custom result should be a dictionary"
        
        # Verify custom aggregation logic was applied correctly
        assert result.result.get("count") == num_items, "Custom aggregation should count items correctly"
        expected_total = sum(i * 2 for i in range(num_items))
        assert result.result.get("total") == expected_total, "Custom aggregation should sum values correctly"
        assert result.result.get("ids") == list(range(num_items)), "Custom aggregation should collect IDs correctly"


# Property 26.1: Strategy parsing with invalid configurations
# Feature: project-production-readiness, Property 26.1: Strategy parsing with invalid configurations
# Validates: Requirements 4.5
@settings(max_examples=50, deadline=None)
@given(strategy=st.sampled_from(["concat", "stats", "filter", "custom"]))
def test_property_aggregation_strategy_parsing_invalid_configs(strategy):
    """
    Property 26.1: Strategy parsing with invalid configurations
    
    For any aggregation strategy, when required parameters are missing,
    the system should detect the invalid configuration during parsing.
    
    This ensures that:
    1. Missing required parameters are detected
    2. Appropriate error messages are provided
    3. The system fails gracefully with invalid configurations
    
    Validates: Requirements 4.5
    """
    from src.pipeline_config import validate_yaml_schema
    
    # Create step configuration WITHOUT required strategy-specific parameters
    step_config = {
        "id": "aggregator",
        "type": "batch_aggregator",
        "aggregation_strategy": strategy,
        "input_mapping": {"items": "input"},
        "output_key": "output"
        # Intentionally missing strategy-specific parameters
    }
    
    pipeline_data = {
        "id": "test_pipeline",
        "name": "Test Pipeline",
        "steps": [step_config],
        "inputs": [{"name": "input"}],
        "outputs": [{"key": "output"}]
    }
    
    # Validate configuration
    errors = validate_yaml_schema(pipeline_data)
    
    # For strategies that require specific parameters, validation should fail
    if strategy == "stats":
        # Stats requires 'fields' parameter
        assert len(errors) > 0, "Stats strategy without 'fields' should produce validation errors"
        assert any("fields" in str(error).lower() for error in errors), \
            "Error should mention missing 'fields' parameter"
    
    elif strategy == "filter":
        # Filter requires 'condition' parameter
        assert len(errors) > 0, "Filter strategy without 'condition' should produce validation errors"
        assert any("condition" in str(error).lower() for error in errors), \
            "Error should mention missing 'condition' parameter"
    
    elif strategy == "custom":
        # Custom requires 'language' and code (code/aggregation_code/code_file)
        assert len(errors) > 0, "Custom strategy without 'language' and code should produce validation errors"
        assert any("language" in str(error).lower() or "code" in str(error).lower() for error in errors), \
            "Error should mention missing 'language' or code parameter"
    
    # Concat strategy has optional parameters, so it might not produce errors
    # We don't assert errors for concat


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
