"""
Property-Based Tests for Code Node Configuration Parsing

These tests use Hypothesis to verify universal properties that should hold
across all valid code node configurations.

Feature: project-production-readiness
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from hypothesis import given, strategies as st, settings
from hypothesis import assume

from src.models import CodeNodeConfig, StepConfig, PipelineConfig
from src.pipeline_config import validate_code_node_config, validate_yaml_schema
from src.code_executor import CodeExecutor, ExecutionResult


# Custom strategies for generating valid code node configurations
@st.composite
def code_node_config_dict(draw):
    """Generate a valid code node configuration dictionary"""
    language = draw(st.sampled_from(["javascript", "python"]))
    
    # Choose between inline code or code file (not both)
    use_inline_code = draw(st.booleans())
    
    config = {
        "language": language,
        "timeout": draw(st.integers(min_value=1, max_value=300)),
        "env_vars": draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ_'),
            values=st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789-_./'),
            max_size=5
        ))
    }
    
    if use_inline_code:
        # Generate simple inline code based on language
        if language == "javascript":
            config["code"] = "module.exports = (inputs) => ({ result: inputs.value });"
        else:  # python
            config["code"] = "def transform(inputs):\n    return {'result': inputs['value']}"
    else:
        # Generate a code file path
        config["code_file"] = draw(st.text(
            min_size=5,
            max_size=50,
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-/.py.js'
        ))
        # Ensure it has a proper extension
        if language == "javascript" and not config["code_file"].endswith('.js'):
            config["code_file"] += '.js'
        elif language == "python" and not config["code_file"].endswith('.py'):
            config["code_file"] += '.py'
    
    return config


@st.composite
def step_config_with_code_node_dict(draw):
    """Generate a valid step configuration with code node"""
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
    
    # Choose between nested code_config or flat structure
    use_nested_config = draw(st.booleans())
    
    step_config = {
        "id": step_id,
        "type": "code_node",
        "output_key": output_key,
        "input_mapping": draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            values=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            max_size=3
        ))
    }
    
    code_config = draw(code_node_config_dict())
    
    if use_nested_config:
        # Use nested code_config structure
        step_config["code_config"] = code_config
    else:
        # Use flat structure (backward compatibility)
        # Only copy fields that StepConfig directly supports
        step_config["language"] = code_config["language"]
        if "code" in code_config:
            step_config["code"] = code_config["code"]
        if "code_file" in code_config:
            step_config["code_file"] = code_config["code_file"]
        # Note: env_vars and timeout are not directly supported in flat structure
        # They should be in code_config
    
    return step_config


@st.composite
def pipeline_config_with_code_nodes_dict(draw):
    """Generate a valid pipeline configuration with code nodes"""
    pipeline_id = draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ))
    if not pipeline_id[0].isalpha():
        pipeline_id = 'pipeline_' + pipeline_id
    
    # Generate 1-3 code node steps
    num_steps = draw(st.integers(min_value=1, max_value=3))
    steps = []
    
    for i in range(num_steps):
        step = draw(step_config_with_code_node_dict())
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


@st.composite
def python_code_and_inputs(draw):
    """Generate valid Python code and corresponding inputs for testing execution"""
    # Generate input data
    input_value = draw(st.one_of(
        st.integers(min_value=-1000, max_value=1000),
        st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10)
    ))
    
    # Choose a transformation type
    transform_type = draw(st.sampled_from([
        "identity",      # Return input as-is
        "double",        # Double numeric values
        "uppercase",     # Uppercase strings
        "length",        # Return length
        "sum",          # Sum lists
        "type_info"     # Return type information
    ]))
    
    # Generate appropriate code based on transform type
    if transform_type == "identity":
        code = """
def transform(inputs):
    return inputs
"""
        expected_output = {"value": input_value}
        
    elif transform_type == "double":
        code = """
def transform(inputs):
    value = inputs.get('value')
    if isinstance(value, (int, float)):
        return {'result': value * 2}
    return {'result': value}
"""
        if isinstance(input_value, (int, float)):
            expected_output = {"result": input_value * 2}
        else:
            expected_output = {"result": input_value}
    
    elif transform_type == "uppercase":
        code = """
def transform(inputs):
    value = inputs.get('value')
    if isinstance(value, str):
        return {'result': value.upper()}
    return {'result': str(value)}
"""
        if isinstance(input_value, str):
            expected_output = {"result": input_value.upper()}
        else:
            expected_output = {"result": str(input_value)}
    
    elif transform_type == "length":
        code = """
def transform(inputs):
    value = inputs.get('value')
    if isinstance(value, (str, list)):
        return {'length': len(value)}
    return {'length': 0}
"""
        if isinstance(input_value, (str, list)):
            expected_output = {"length": len(input_value)}
        else:
            expected_output = {"length": 0}
    
    elif transform_type == "sum":
        code = """
def transform(inputs):
    value = inputs.get('value')
    if isinstance(value, list):
        return {'sum': sum(value)}
    return {'sum': 0}
"""
        if isinstance(input_value, list):
            expected_output = {"sum": sum(input_value)}
        else:
            expected_output = {"sum": 0}
    
    else:  # type_info
        code = """
def transform(inputs):
    value = inputs.get('value')
    return {
        'type': type(value).__name__,
        'value': value
    }
"""
        expected_output = {
            "type": type(input_value).__name__,
            "value": input_value
        }
    
    inputs = {"value": input_value}
    
    return {
        "code": code,
        "inputs": inputs,
        "expected_output": expected_output,
        "transform_type": transform_type
    }


class TestCodeNodeConfigurationProperties:
    """Property-Based Tests for Code Node Configuration Parsing"""
    
    # Feature: project-production-readiness, Property 5: Code node configuration parsing
    @settings(max_examples=100)
    @given(code_config=code_node_config_dict())
    def test_code_node_config_parsing_from_dict(self, code_config):
        """
        Property 5: Code node configuration parsing
        
        For any valid code node configuration dictionary (inline or file-based),
        the system should successfully parse the configuration into a CodeNodeConfig object.
        
        Validates: Requirements 3.1
        """
        # Property: Valid code node config should parse without errors
        try:
            config = CodeNodeConfig.from_dict(code_config)
            
            # Verify all fields are correctly parsed
            assert config.language == code_config["language"]
            assert config.language in ["javascript", "python"]
            
            assert config.timeout == code_config["timeout"]
            assert config.timeout > 0
            
            assert config.env_vars == code_config.get("env_vars", {})
            
            # Verify exactly one of code or code_file is set
            if "code" in code_config:
                assert config.code == code_config["code"]
                assert config.code is not None
                assert config.code_file is None
            else:
                assert config.code_file == code_config["code_file"]
                assert config.code_file is not None
                assert config.code is None
            
            # Property: Validation should pass for valid configs
            validation_errors = config.validate()
            assert len(validation_errors) == 0, \
                f"Valid config should not have validation errors: {validation_errors}"
            
            # Property: Round-trip conversion should preserve data
            config_dict = config.to_dict()
            assert config_dict["language"] == code_config["language"]
            assert config_dict["timeout"] == code_config["timeout"]
            
            if "code" in code_config:
                assert config_dict["code"] == code_config["code"]
                assert "code_file" not in config_dict or config_dict["code_file"] is None
            else:
                assert config_dict["code_file"] == code_config["code_file"]
                assert "code" not in config_dict or config_dict["code"] is None
            
        except Exception as e:
            pytest.fail(f"Failed to parse valid code node config: {e}\nConfig: {code_config}")
    
    @settings(max_examples=100)
    @given(step_config=step_config_with_code_node_dict())
    def test_step_config_with_code_node_parsing(self, step_config):
        """
        Property 5: Code node configuration parsing (Step level)
        
        For any valid step configuration containing a code node (nested or flat),
        the system should successfully parse it into a StepConfig object.
        
        Validates: Requirements 3.1
        """
        # Property: Valid step config with code node should parse without errors
        try:
            config = StepConfig.from_dict(step_config)
            
            # Verify basic step fields
            assert config.id == step_config["id"]
            assert config.type == "code_node"
            assert config.output_key == step_config["output_key"]
            assert config.input_mapping == step_config.get("input_mapping", {})
            
            # Verify code node configuration is parsed correctly
            if "code_config" in step_config:
                # Nested structure
                assert config.code_config is not None
                assert isinstance(config.code_config, CodeNodeConfig)
                assert config.code_config.language == step_config["code_config"]["language"]
                assert config.code_config.timeout == step_config["code_config"]["timeout"]
            else:
                # Flat structure (backward compatibility)
                assert config.language == step_config["language"]
                if "code" in step_config:
                    assert config.code == step_config["code"]
                else:
                    assert config.code_file == step_config["code_file"]
            
            # Property: Validation should pass for valid configs
            validation_errors = config.validate()
            assert len(validation_errors) == 0, \
                f"Valid step config should not have validation errors: {validation_errors}"
            
            # Property: Round-trip conversion should preserve data
            config_dict = config.to_dict()
            assert config_dict["id"] == step_config["id"]
            assert config_dict["type"] == "code_node"
            assert config_dict["output_key"] == step_config["output_key"]
            
        except Exception as e:
            pytest.fail(f"Failed to parse valid step config with code node: {e}\nConfig: {step_config}")
    
    @settings(max_examples=100)
    @given(pipeline_config=pipeline_config_with_code_nodes_dict())
    def test_pipeline_config_with_code_nodes_parsing(self, pipeline_config):
        """
        Property 5: Code node configuration parsing (Pipeline level)
        
        For any valid pipeline configuration containing code node steps,
        the system should successfully parse it into a PipelineConfig object.
        
        Validates: Requirements 3.1
        """
        # Property: Valid pipeline config with code nodes should parse without errors
        try:
            config = PipelineConfig.from_dict(pipeline_config)
            
            # Verify basic pipeline fields
            assert config.id == pipeline_config["id"]
            assert config.name == pipeline_config["name"]
            assert len(config.steps) == len(pipeline_config["steps"])
            
            # Verify each code node step is parsed correctly
            for i, step in enumerate(config.steps):
                original_step = pipeline_config["steps"][i]
                
                assert step.id == original_step["id"]
                assert step.type == "code_node"
                assert step.output_key == original_step["output_key"]
                
                # Verify code node configuration
                if "code_config" in original_step:
                    assert step.code_config is not None
                    assert step.code_config.language == original_step["code_config"]["language"]
                else:
                    assert step.language == original_step["language"]
            
            # Property: Validation should pass for valid configs
            validation_errors = config.validate()
            assert len(validation_errors) == 0, \
                f"Valid pipeline config should not have validation errors: {validation_errors}"
            
            # Property: Round-trip conversion should preserve data
            config_dict = config.to_dict()
            assert config_dict["id"] == pipeline_config["id"]
            assert config_dict["name"] == pipeline_config["name"]
            assert len(config_dict["steps"]) == len(pipeline_config["steps"])
            
        except Exception as e:
            pytest.fail(f"Failed to parse valid pipeline config with code nodes: {e}\nConfig: {pipeline_config}")
    
    @settings(max_examples=100)
    @given(step_config=step_config_with_code_node_dict())
    def test_yaml_schema_validation_for_code_nodes(self, step_config):
        """
        Property 5: Code node configuration parsing (YAML schema validation)
        
        For any valid code node step configuration, the YAML schema validation
        should pass without errors.
        
        Validates: Requirements 3.1
        """
        # Create a minimal pipeline config with the code node step
        pipeline_config = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [step_config],
            "outputs": [{"key": step_config["output_key"]}]
        }
        
        # Property: YAML schema validation should pass for valid code node configs
        validation_errors = validate_yaml_schema(pipeline_config)
        
        # Filter out errors not related to code node configuration
        code_node_errors = [
            err for err in validation_errors
            if "code" in err.lower() or "language" in err.lower() or step_config["id"] in err
        ]
        
        assert len(code_node_errors) == 0, \
            f"Valid code node config should pass YAML schema validation. Errors: {code_node_errors}"
    
    @settings(max_examples=100)
    @given(
        language=st.sampled_from(["javascript", "python"]),
        has_code=st.booleans(),
        has_code_file=st.booleans()
    )
    def test_code_node_validation_mutual_exclusivity(self, language, has_code, has_code_file):
        """
        Property 5: Code node configuration parsing (Mutual exclusivity)
        
        For any code node configuration, exactly one of 'code' or 'code_file'
        must be specified (not both, not neither).
        
        Validates: Requirements 3.1
        """
        config_dict = {
            "language": language,
            "timeout": 30
        }
        
        if has_code:
            config_dict["code"] = "function test() { return true; }"
        if has_code_file:
            config_dict["code_file"] = "test.js"
        
        config = CodeNodeConfig.from_dict(config_dict)
        validation_errors = config.validate()
        
        # Property: Validation should enforce mutual exclusivity
        if has_code and has_code_file:
            # Both specified - should have error
            assert len(validation_errors) > 0
            assert any("不能同时指定" in err or "both" in err.lower() for err in validation_errors)
        elif not has_code and not has_code_file:
            # Neither specified - should have error
            assert len(validation_errors) > 0
            assert any("必须指定" in err or "must specify" in err.lower() for err in validation_errors)
        else:
            # Exactly one specified - should be valid
            assert len(validation_errors) == 0, \
                f"Config with exactly one of code/code_file should be valid. Errors: {validation_errors}"
    
    @settings(max_examples=100)
    @given(
        language=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz'),
        timeout=st.integers()
    )
    def test_code_node_validation_constraints(self, language, timeout):
        """
        Property 5: Code node configuration parsing (Validation constraints)
        
        For any code node configuration, validation should enforce:
        - Language must be 'javascript' or 'python'
        - Timeout must be positive
        
        Validates: Requirements 3.1
        """
        # Assume language is not one of the valid options
        assume(language not in ["javascript", "python"])
        
        config_dict = {
            "language": language,
            "code": "test code",
            "timeout": timeout
        }
        
        config = CodeNodeConfig.from_dict(config_dict)
        validation_errors = config.validate()
        
        # Property: Invalid language should produce validation error
        assert len(validation_errors) > 0
        has_language_error = any(
            "language" in err.lower() or "不支持的代码语言" in err
            for err in validation_errors
        )
        assert has_language_error, \
            f"Invalid language '{language}' should produce validation error. Errors: {validation_errors}"
        
        # Property: Non-positive timeout should produce validation error if timeout <= 0
        if timeout <= 0:
            has_timeout_error = any(
                "timeout" in err.lower() or "超时" in err
                for err in validation_errors
            )
            assert has_timeout_error, \
                f"Non-positive timeout {timeout} should produce validation error. Errors: {validation_errors}"


@st.composite
def javascript_code_and_inputs(draw):
    """Generate valid JavaScript code and corresponding inputs for testing execution"""
    # Generate input data
    input_value = draw(st.one_of(
        st.integers(min_value=-1000, max_value=1000),
        st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10)
    ))
    
    # Choose a transformation type
    transform_type = draw(st.sampled_from([
        "identity",      # Return input as-is
        "double",        # Double numeric values
        "uppercase",     # Uppercase strings
        "length",        # Return length
        "sum",          # Sum arrays
        "type_info"     # Return type information
    ]))
    
    # Generate appropriate code based on transform type
    if transform_type == "identity":
        code = """
module.exports = (inputs) => {
    return inputs;
};
"""
        expected_output = {"value": input_value}
        
    elif transform_type == "double":
        code = """
module.exports = (inputs) => {
    const value = inputs.value;
    if (typeof value === 'number') {
        return { result: value * 2 };
    }
    return { result: value };
};
"""
        if isinstance(input_value, (int, float)):
            expected_output = {"result": input_value * 2}
        else:
            expected_output = {"result": input_value}
    
    elif transform_type == "uppercase":
        code = """
module.exports = (inputs) => {
    const value = inputs.value;
    if (typeof value === 'string') {
        return { result: value.toUpperCase() };
    }
    return { result: String(value) };
};
"""
        if isinstance(input_value, str):
            expected_output = {"result": input_value.upper()}
        elif isinstance(input_value, list):
            # JavaScript String([1,2,3]) returns "1,2,3"
            expected_output = {"result": ",".join(str(x) for x in input_value)}
        elif isinstance(input_value, float):
            # JavaScript String(0.0) returns "0", not "0.0"
            # JavaScript removes trailing zeros
            if input_value == int(input_value):
                expected_output = {"result": str(int(input_value))}
            else:
                expected_output = {"result": str(input_value)}
        else:
            expected_output = {"result": str(input_value)}
    
    elif transform_type == "length":
        code = """
module.exports = (inputs) => {
    const value = inputs.value;
    if (typeof value === 'string' || Array.isArray(value)) {
        return { length: value.length };
    }
    return { length: 0 };
};
"""
        if isinstance(input_value, (str, list)):
            expected_output = {"length": len(input_value)}
        else:
            expected_output = {"length": 0}
    
    elif transform_type == "sum":
        code = """
module.exports = (inputs) => {
    const value = inputs.value;
    if (Array.isArray(value)) {
        return { sum: value.reduce((a, b) => a + b, 0) };
    }
    return { sum: 0 };
};
"""
        if isinstance(input_value, list):
            expected_output = {"sum": sum(input_value)}
        else:
            expected_output = {"sum": 0}
    
    else:  # type_info
        code = """
module.exports = (inputs) => {
    const value = inputs.value;
    let type;
    if (Array.isArray(value)) {
        type = 'list';
    } else if (value === null) {
        type = 'NoneType';
    } else {
        type = typeof value;
    }
    return {
        type: type,
        value: value
    };
};
"""
        # Map JavaScript types to Python types for comparison
        if isinstance(input_value, list):
            js_type = "list"
        elif isinstance(input_value, bool):
            js_type = "boolean"
        elif isinstance(input_value, int):
            js_type = "number"
        elif isinstance(input_value, float):
            js_type = "number"
        elif isinstance(input_value, str):
            js_type = "string"
        else:
            js_type = "object"
        
        expected_output = {
            "type": js_type,
            "value": input_value
        }
    
    inputs = {"value": input_value}
    
    return {
        "code": code,
        "inputs": inputs,
        "expected_output": expected_output,
        "transform_type": transform_type
    }


class TestJavaScriptExecutionProperties:
    """Property-Based Tests for JavaScript Code Node Execution Correctness"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=10)
    
    # Feature: project-production-readiness, Property 6: JavaScript execution correctness
    @settings(max_examples=100, deadline=None)
    @given(test_case=javascript_code_and_inputs())
    def test_javascript_execution_correctness(self, test_case):
        """
        Property 6: JavaScript execution correctness
        
        For any valid JavaScript code and input data, executing the code node
        should return the expected output or a proper error.
        
        This property verifies that:
        1. Valid JavaScript code executes successfully
        2. The output matches the expected transformation
        3. Input data is correctly passed to the code
        4. Output data is correctly captured and parsed
        
        Validates: Requirements 3.2
        """
        code = test_case["code"]
        inputs = test_case["inputs"]
        expected_output = test_case["expected_output"]
        transform_type = test_case["transform_type"]
        
        # Execute the JavaScript code
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Valid JavaScript code should execute successfully
        assert result.success, \
            f"Valid JavaScript code should execute successfully.\n" \
            f"Transform type: {transform_type}\n" \
            f"Code: {code}\n" \
            f"Inputs: {inputs}\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Stack trace: {result.stack_trace}"
        
        # Property: Execution should not timeout
        assert not result.timeout, \
            f"Execution should not timeout for simple transformations.\n" \
            f"Transform type: {transform_type}"
        
        # Property: Exit code should be 0 for successful execution
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution, got {result.exit_code}"
        
        # Property: Output should match expected transformation
        assert result.output == expected_output, \
            f"Output should match expected transformation.\n" \
            f"Transform type: {transform_type}\n" \
            f"Expected: {expected_output}\n" \
            f"Got: {result.output}\n" \
            f"Inputs: {inputs}"
        
        # Property: Execution time should be reasonable (< 5 seconds for simple operations)
        assert result.execution_time < 5.0, \
            f"Execution time should be reasonable, got {result.execution_time}s"
        
        # Property: No stderr output for successful execution
        if result.stderr:
            # Node.js may have some warnings, so we just check it's not an error
            assert "Error" not in result.stderr and "at " not in result.stderr, \
                f"Stderr should not contain errors for successful execution: {result.stderr}"
    
    @settings(max_examples=50, deadline=None)
    @given(
        input_value=st.one_of(
            st.integers(min_value=-1000, max_value=1000),
            st.text(min_size=0, max_size=50),
            # Limit integers to JavaScript's safe integer range
            st.lists(st.integers(min_value=-(2**53-1), max_value=2**53-1), min_size=0, max_size=10)
        )
    )
    def test_javascript_execution_with_json_serializable_data(self, input_value):
        """
        Property 6: JavaScript execution correctness (JSON serialization)
        
        For any JSON-serializable input data, the JavaScript code should be able
        to receive and process it correctly.
        
        Validates: Requirements 3.2
        """
        code = """
module.exports = (inputs) => {
    // Echo back the input with type information
    const value = inputs.value;
    let type;
    if (Array.isArray(value)) {
        type = 'array';
    } else if (value === null) {
        type = 'null';
    } else {
        type = typeof value;
    }
    return {
        received: value,
        type: type
    };
};
"""
        
        inputs = {"value": input_value}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for JSON-serializable data.\n" \
            f"Input: {input_value}\n" \
            f"Error: {result.error}"
        
        # Property: Output should contain the received value
        assert "received" in result.output, \
            f"Output should contain 'received' key"
        
        # Property: Received value should match input (for JSON-serializable types)
        assert result.output["received"] == input_value, \
            f"Received value should match input.\n" \
            f"Expected: {input_value}\n" \
            f"Got: {result.output['received']}"
    
    @settings(max_examples=50, deadline=None)
    @given(
        error_type=st.sampled_from([
            "Error",
            "TypeError",
            "ReferenceError",
            "RangeError",
            "SyntaxError"
        ]),
        error_message=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz ')
    )
    def test_javascript_execution_error_handling(self, error_type, error_message):
        """
        Property 6: JavaScript execution correctness (Error handling)
        
        For any JavaScript code that throws an error, the executor should:
        1. Capture the error
        2. Return success=False
        3. Provide error details including stack trace
        4. Have a non-zero exit code
        
        Validates: Requirements 3.2
        """
        code = f"""
module.exports = (inputs) => {{
    throw new {error_type}("{error_message}");
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail when code throws an error"
        
        # Property: Error should be captured
        assert result.error is not None, \
            f"Error should be captured"
        
        # Property: Stack trace should be available
        assert result.stack_trace is not None or result.stderr is not None, \
            f"Stack trace or stderr should be available for errors"
        
        # Property: Error information should contain error type or message
        error_info = (result.stack_trace or "") + (result.stderr or "") + (result.error or "")
        assert error_type in error_info or error_message in error_info, \
            f"Error information should contain error type '{error_type}' or message '{error_message}'.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Error: {result.error}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for failed execution, got {result.exit_code}"
        
        # Property: Should not timeout
        assert not result.timeout, \
            f"Error execution should not timeout"
    
    @settings(max_examples=30, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3)
    )
    def test_javascript_execution_timeout_enforcement(self, timeout_seconds):
        """
        Property 6: JavaScript execution correctness (Timeout enforcement)
        
        For any JavaScript code that runs longer than the timeout,
        the executor should:
        1. Terminate the execution
        2. Return timeout=True
        3. Return success=False
        4. Provide timeout error message
        
        Validates: Requirements 3.2, 10.6
        """
        # Code that sleeps longer than the timeout
        sleep_time = (timeout_seconds + 2) * 1000  # Convert to milliseconds
        code = f"""
module.exports = (inputs) => {{
    const start = Date.now();
    while (Date.now() - start < {sleep_time}) {{
        // Busy wait
    }}
    return {{ done: true }};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail on timeout"
        
        # Property: Timeout flag should be set
        assert result.timeout, \
            f"Timeout flag should be set when execution exceeds timeout"
        
        # Property: Error message should mention timeout
        assert result.error is not None, \
            f"Error message should be present"
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), \
            f"Error message should mention timeout: {result.error}"
        
        # Property: Execution time should be close to timeout value
        assert result.execution_time >= timeout_seconds * 0.8, \
            f"Execution time should be at least 80% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time <= timeout_seconds * 1.5, \
            f"Execution time should not exceed 150% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
    
    @settings(max_examples=50, deadline=None)
    @given(
        code_variant=st.sampled_from([
            "arrow_function",
            "regular_function",
            "async_function",
            "function_expression"
        ])
    )
    def test_javascript_execution_function_variants(self, code_variant):
        """
        Property 6: JavaScript execution correctness (Function variants)
        
        For any JavaScript code with different function definition styles,
        the executor should correctly execute the function.
        
        Validates: Requirements 3.2
        """
        test_value = 42
        expected_result = test_value * 2
        
        if code_variant == "arrow_function":
            code = """
module.exports = (inputs) => {
    return { result: inputs.value * 2 };
};
"""
        
        elif code_variant == "regular_function":
            code = """
module.exports = function(inputs) {
    return { result: inputs.value * 2 };
};
"""
        
        elif code_variant == "async_function":
            code = """
module.exports = async (inputs) => {
    return { result: inputs.value * 2 };
};
"""
        
        else:  # function_expression
            code = """
const transform = function(inputs) {
    return { result: inputs.value * 2 };
};
module.exports = transform;
"""
        
        inputs = {"value": test_value}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for code variant '{code_variant}'.\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Output should be correct
        assert result.output.get("result") == expected_result, \
            f"Output should match expected result for '{code_variant}'.\n" \
            f"Expected: {expected_result}\n" \
            f"Got: {result.output.get('result')}"


class TestCodeNodeExecutionProperties:
    """Property-Based Tests for Code Node Execution Correctness"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=10)
    
    # Feature: project-production-readiness, Property 7: Python execution correctness
    @settings(max_examples=100, deadline=None)
    @given(test_case=python_code_and_inputs())
    def test_python_execution_correctness(self, test_case):
        """
        Property 7: Python execution correctness
        
        For any valid Python code and input data, executing the code node
        should return the expected output or a proper error.
        
        This property verifies that:
        1. Valid Python code executes successfully
        2. The output matches the expected transformation
        3. Input data is correctly passed to the code
        4. Output data is correctly captured and parsed
        
        Validates: Requirements 3.2
        """
        code = test_case["code"]
        inputs = test_case["inputs"]
        expected_output = test_case["expected_output"]
        transform_type = test_case["transform_type"]
        
        # Execute the Python code
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Valid Python code should execute successfully
        assert result.success, \
            f"Valid Python code should execute successfully.\n" \
            f"Transform type: {transform_type}\n" \
            f"Code: {code}\n" \
            f"Inputs: {inputs}\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Stack trace: {result.stack_trace}"
        
        # Property: Execution should not timeout
        assert not result.timeout, \
            f"Execution should not timeout for simple transformations.\n" \
            f"Transform type: {transform_type}"
        
        # Property: Exit code should be 0 for successful execution
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution, got {result.exit_code}"
        
        # Property: Output should match expected transformation
        assert result.output == expected_output, \
            f"Output should match expected transformation.\n" \
            f"Transform type: {transform_type}\n" \
            f"Expected: {expected_output}\n" \
            f"Got: {result.output}\n" \
            f"Inputs: {inputs}"
        
        # Property: Execution time should be reasonable (< 5 seconds for simple operations)
        assert result.execution_time < 5.0, \
            f"Execution time should be reasonable, got {result.execution_time}s"
        
        # Property: No stderr output for successful execution
        # (Some Python versions may have warnings, so we just check it's not an error)
        if result.stderr:
            assert "Error" not in result.stderr and "Traceback" not in result.stderr, \
                f"Stderr should not contain errors for successful execution: {result.stderr}"
    
    @settings(max_examples=50)
    @given(
        input_value=st.one_of(
            st.integers(min_value=-1000, max_value=1000),
            st.text(min_size=0, max_size=50),
            st.lists(st.integers(), min_size=0, max_size=10)
        )
    )
    def test_python_execution_with_json_serializable_data(self, input_value):
        """
        Property 7: Python execution correctness (JSON serialization)
        
        For any JSON-serializable input data, the Python code should be able
        to receive and process it correctly.
        
        Validates: Requirements 3.2
        """
        code = """
def transform(inputs):
    # Echo back the input with type information
    value = inputs.get('value')
    return {
        'received': value,
        'type': type(value).__name__
    }
"""
        
        inputs = {"value": input_value}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for JSON-serializable data.\n" \
            f"Input: {input_value}\n" \
            f"Error: {result.error}"
        
        # Property: Output should contain the received value
        assert "received" in result.output, \
            f"Output should contain 'received' key"
        
        # Property: Received value should match input (for JSON-serializable types)
        assert result.output["received"] == input_value, \
            f"Received value should match input.\n" \
            f"Expected: {input_value}\n" \
            f"Got: {result.output['received']}"
    
    @settings(max_examples=50)
    @given(
        error_type=st.sampled_from([
            "ValueError",
            "TypeError",
            "KeyError",
            "IndexError",
            "RuntimeError"
        ]),
        error_message=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz ')
    )
    def test_python_execution_error_handling(self, error_type, error_message):
        """
        Property 7: Python execution correctness (Error handling)
        
        For any Python code that raises an error, the executor should:
        1. Capture the error
        2. Return success=False
        3. Provide error details including stack trace
        4. Have a non-zero exit code
        
        Validates: Requirements 3.2
        """
        code = f"""
def transform(inputs):
    raise {error_type}("{error_message}")
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail when code raises an error"
        
        # Property: Error should be captured
        assert result.error is not None, \
            f"Error should be captured"
        
        # Property: Stack trace should be available
        assert result.stack_trace is not None, \
            f"Stack trace should be available for errors"
        
        # Property: Stack trace should contain error type
        assert error_type in result.stack_trace or error_type in result.stderr, \
            f"Stack trace should contain error type '{error_type}'.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for failed execution, got {result.exit_code}"
        
        # Property: Should not timeout
        assert not result.timeout, \
            f"Error execution should not timeout"
    
    @settings(max_examples=30, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3)
    )
    def test_python_execution_timeout_enforcement(self, timeout_seconds):
        """
        Property 7: Python execution correctness (Timeout enforcement)
        
        For any Python code that runs longer than the timeout,
        the executor should:
        1. Terminate the execution
        2. Return timeout=True
        3. Return success=False
        4. Provide timeout error message
        
        Validates: Requirements 3.2, 10.6
        """
        # Code that sleeps longer than the timeout
        sleep_time = timeout_seconds + 2
        code = f"""
import time

def transform(inputs):
    time.sleep({sleep_time})
    return {{"done": True}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail on timeout"
        
        # Property: Timeout flag should be set
        assert result.timeout, \
            f"Timeout flag should be set when execution exceeds timeout"
        
        # Property: Error message should mention timeout
        assert result.error is not None, \
            f"Error message should be present"
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), \
            f"Error message should mention timeout: {result.error}"
        
        # Property: Execution time should be close to timeout value
        assert result.execution_time >= timeout_seconds * 0.8, \
            f"Execution time should be at least 80% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time <= timeout_seconds * 1.5, \
            f"Execution time should not exceed 150% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
    
    @settings(max_examples=50)
    @given(
        code_variant=st.sampled_from([
            "function_named_transform",
            "function_named_process_data",
            "function_named_main",
            "no_function"
        ])
    )
    def test_python_execution_function_discovery(self, code_variant):
        """
        Property 7: Python execution correctness (Function discovery)
        
        For any Python code with different function naming conventions,
        the executor should correctly discover and call the function.
        
        Validates: Requirements 3.2
        """
        test_value = 42
        
        if code_variant == "function_named_transform":
            code = f"""
def transform(inputs):
    return {{"result": inputs.get('value') * 2}}
"""
            expected_result = test_value * 2
        
        elif code_variant == "function_named_process_data":
            code = f"""
def process_data(inputs):
    return {{"result": inputs.get('value') * 2}}
"""
            expected_result = test_value * 2
        
        elif code_variant == "function_named_main":
            code = f"""
def main(inputs):
    return {{"result": inputs.get('value') * 2}}
"""
            expected_result = test_value * 2
        
        else:  # no_function
            code = f"""
# No function defined, should return inputs as-is
pass
"""
            expected_result = None  # Will return inputs as-is
        
        inputs = {"value": test_value}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for code variant '{code_variant}'.\n" \
            f"Error: {result.error}"
        
        # Property: Output should be correct based on variant
        if code_variant != "no_function":
            assert result.output.get("result") == expected_result, \
                f"Output should match expected result for '{code_variant}'.\n" \
                f"Expected: {expected_result}\n" \
                f"Got: {result.output.get('result')}"
        else:
            # When no function is defined, inputs are returned as-is
            assert result.output == inputs, \
                f"When no function is defined, inputs should be returned as-is.\n" \
                f"Expected: {inputs}\n" \
                f"Got: {result.output}"


class TestCodeNodeInputPassingProperties:
    """Property-Based Tests for Code Node Input Passing"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=10)
    
    # Feature: project-production-readiness, Property 8: Code node input passing
    @settings(max_examples=100)
    @given(
        input_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            values=st.one_of(
                st.integers(min_value=-1000, max_value=1000),
                st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '),
                st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10),
                st.none()
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_python_input_data_passing(self, input_data):
        """
        Property 8: Code node input passing (Python)
        
        For any code node with input data, the input data should be correctly
        passed to the Python code as parameters. The code should be able to
        access all input fields and their values.
        
        This property verifies that:
        1. All input fields are accessible in the code
        2. Input values are correctly preserved (no corruption)
        3. Input types are correctly maintained
        4. The code can iterate over all input fields
        
        Validates: Requirements 10.4
        """
        # Create Python code that echoes back all inputs with metadata
        code = """
def transform(inputs):
    # Echo back all inputs with type information
    result = {}
    for key, value in inputs.items():
        result[key] = {
            'value': value,
            'type': type(value).__name__,
            'received': True
        }
    result['_input_count'] = len(inputs)
    result['_input_keys'] = list(inputs.keys())
    return result
"""
        
        # Execute the code
        result = self.executor.execute_python(code, input_data, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for input passing test.\n" \
            f"Input data: {input_data}\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: All input keys should be present in output
        for key in input_data.keys():
            assert key in result.output, \
                f"Input key '{key}' should be present in output.\n" \
                f"Input keys: {list(input_data.keys())}\n" \
                f"Output keys: {list(result.output.keys())}"
        
        # Property: All input values should be correctly passed
        for key, expected_value in input_data.items():
            received_data = result.output[key]
            assert received_data['received'] is True, \
                f"Input field '{key}' should be marked as received"
            
            actual_value = received_data['value']
            assert actual_value == expected_value, \
                f"Input value for '{key}' should be correctly passed.\n" \
                f"Expected: {expected_value} (type: {type(expected_value).__name__})\n" \
                f"Got: {actual_value} (type: {type(actual_value).__name__})"
        
        # Property: Input count should match
        assert result.output['_input_count'] == len(input_data), \
            f"Input count should match.\n" \
            f"Expected: {len(input_data)}\n" \
            f"Got: {result.output['_input_count']}"
        
        # Property: Input keys should match
        assert set(result.output['_input_keys']) == set(input_data.keys()), \
            f"Input keys should match.\n" \
            f"Expected: {set(input_data.keys())}\n" \
            f"Got: {set(result.output['_input_keys'])}"
    
    @settings(max_examples=100, deadline=500)  # Increase deadline for Node.js startup time
    @given(
        input_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            values=st.one_of(
                st.integers(min_value=-1000, max_value=1000),
                st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '),
                st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10),
                st.none()
            ),
            min_size=1,
            max_size=5
        )
    )
    def test_javascript_input_data_passing(self, input_data):
        """
        Property 8: Code node input passing (JavaScript)
        
        For any code node with input data, the input data should be correctly
        passed to the JavaScript code as parameters. The code should be able to
        access all input fields and their values.
        
        This property verifies that:
        1. All input fields are accessible in the code
        2. Input values are correctly preserved (no corruption)
        3. Input types are correctly maintained (within JSON limitations)
        4. The code can iterate over all input fields
        
        Validates: Requirements 10.4
        """
        # Create JavaScript code that echoes back all inputs with metadata
        code = """
module.exports = (inputs) => {
    // Echo back all inputs with type information
    const result = {};
    for (const [key, value] of Object.entries(inputs)) {
        result[key] = {
            value: value,
            type: typeof value,
            isNull: value === null,
            isArray: Array.isArray(value),
            received: true
        };
    }
    result._input_count = Object.keys(inputs).length;
    result._input_keys = Object.keys(inputs);
    return result;
};
"""
        
        # Execute the code
        result = self.executor.execute_javascript(code, input_data, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for input passing test.\n" \
            f"Input data: {input_data}\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: All input keys should be present in output
        for key in input_data.keys():
            assert key in result.output, \
                f"Input key '{key}' should be present in output.\n" \
                f"Input keys: {list(input_data.keys())}\n" \
                f"Output keys: {list(result.output.keys())}"
        
        # Property: All input values should be correctly passed
        for key, expected_value in input_data.items():
            received_data = result.output[key]
            assert received_data['received'] is True, \
                f"Input field '{key}' should be marked as received"
            
            actual_value = received_data['value']
            
            # Note: JavaScript has different type handling than Python
            # None becomes null, which is fine
            # Floats and ints may be treated the same in JavaScript
            if expected_value is None:
                assert actual_value is None, \
                    f"None value for '{key}' should be passed as null.\n" \
                    f"Expected: None\n" \
                    f"Got: {actual_value}"
            elif isinstance(expected_value, bool):
                # Booleans should be preserved
                assert actual_value == expected_value, \
                    f"Boolean value for '{key}' should be correctly passed.\n" \
                    f"Expected: {expected_value}\n" \
                    f"Got: {actual_value}"
            elif isinstance(expected_value, (int, float)):
                # Numbers should be equal (JavaScript doesn't distinguish int/float)
                assert abs(actual_value - expected_value) < 1e-10, \
                    f"Numeric value for '{key}' should be correctly passed.\n" \
                    f"Expected: {expected_value}\n" \
                    f"Got: {actual_value}"
            else:
                # Strings, lists, etc. should be equal
                assert actual_value == expected_value, \
                    f"Input value for '{key}' should be correctly passed.\n" \
                    f"Expected: {expected_value}\n" \
                    f"Got: {actual_value}"
        
        # Property: Input count should match
        assert result.output['_input_count'] == len(input_data), \
            f"Input count should match.\n" \
            f"Expected: {len(input_data)}\n" \
            f"Got: {result.output['_input_count']}"
        
        # Property: Input keys should match
        assert set(result.output['_input_keys']) == set(input_data.keys()), \
            f"Input keys should match.\n" \
            f"Expected: {set(input_data.keys())}\n" \
            f"Got: {set(result.output['_input_keys'])}"
    
    @settings(max_examples=50)
    @given(
        nested_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            values=st.dictionaries(
                keys=st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'),
                values=st.one_of(
                    st.integers(min_value=0, max_value=100),
                    st.text(min_size=0, max_size=20)
                ),
                min_size=1,
                max_size=3
            ),
            min_size=1,
            max_size=3
        )
    )
    def test_python_nested_input_data_passing(self, nested_data):
        """
        Property 8: Code node input passing (Python - nested data)
        
        For any code node with nested input data (dictionaries within dictionaries),
        the nested structure should be correctly preserved and accessible.
        
        This property verifies that:
        1. Nested data structures are correctly passed
        2. Nested values are accessible
        3. Structure is preserved
        
        Validates: Requirements 10.4
        """
        code = """
def transform(inputs):
    # Access nested data and flatten it
    result = {'nested_values': []}
    for outer_key, inner_dict in inputs.items():
        for inner_key, value in inner_dict.items():
            result['nested_values'].append({
                'outer_key': outer_key,
                'inner_key': inner_key,
                'value': value
            })
    result['outer_keys'] = list(inputs.keys())
    return result
"""
        
        result = self.executor.execute_python(code, nested_data, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for nested input data.\n" \
            f"Error: {result.error}"
        
        # Property: All outer keys should be present
        assert set(result.output['outer_keys']) == set(nested_data.keys()), \
            f"All outer keys should be accessible.\n" \
            f"Expected: {set(nested_data.keys())}\n" \
            f"Got: {set(result.output['outer_keys'])}"
        
        # Property: All nested values should be accessible
        expected_count = sum(len(inner_dict) for inner_dict in nested_data.values())
        actual_count = len(result.output['nested_values'])
        assert actual_count == expected_count, \
            f"All nested values should be accessible.\n" \
            f"Expected count: {expected_count}\n" \
            f"Got count: {actual_count}"
        
        # Property: Nested values should match
        for item in result.output['nested_values']:
            outer_key = item['outer_key']
            inner_key = item['inner_key']
            actual_value = item['value']
            
            assert outer_key in nested_data, \
                f"Outer key '{outer_key}' should exist in input"
            assert inner_key in nested_data[outer_key], \
                f"Inner key '{inner_key}' should exist in input['{outer_key}']"
            
            expected_value = nested_data[outer_key][inner_key]
            assert actual_value == expected_value, \
                f"Nested value should match.\n" \
                f"Path: {outer_key}.{inner_key}\n" \
                f"Expected: {expected_value}\n" \
                f"Got: {actual_value}"
    
    @settings(max_examples=50, deadline=500)  # Increase deadline for Node.js startup time
    @given(
        list_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz_'),
            values=st.lists(
                st.one_of(
                    st.integers(min_value=0, max_value=100),
                    st.text(min_size=0, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz')
                ),
                min_size=1,
                max_size=5
            ),
            min_size=1,
            max_size=3
        )
    )
    def test_javascript_list_input_data_passing(self, list_data):
        """
        Property 8: Code node input passing (JavaScript - list data)
        
        For any code node with list/array input data, the lists should be
        correctly passed and accessible with all elements preserved.
        
        This property verifies that:
        1. Lists/arrays are correctly passed
        2. List elements are accessible
        3. List order is preserved
        4. List length is correct
        
        Validates: Requirements 10.4
        """
        code = """
module.exports = (inputs) => {
    const result = {
        list_info: {},
        total_elements: 0
    };
    
    for (const [key, list] of Object.entries(inputs)) {
        result.list_info[key] = {
            length: list.length,
            first: list[0],
            last: list[list.length - 1],
            all_elements: list
        };
        result.total_elements += list.length;
    }
    
    return result;
};
"""
        
        result = self.executor.execute_javascript(code, list_data, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for list input data.\n" \
            f"Error: {result.error}"
        
        # Property: All list keys should be present
        for key in list_data.keys():
            assert key in result.output['list_info'], \
                f"List key '{key}' should be present in output"
        
        # Property: List lengths should match
        for key, expected_list in list_data.items():
            actual_length = result.output['list_info'][key]['length']
            expected_length = len(expected_list)
            assert actual_length == expected_length, \
                f"List length for '{key}' should match.\n" \
                f"Expected: {expected_length}\n" \
                f"Got: {actual_length}"
        
        # Property: List elements should match
        for key, expected_list in list_data.items():
            actual_list = result.output['list_info'][key]['all_elements']
            assert actual_list == expected_list, \
                f"List elements for '{key}' should match.\n" \
                f"Expected: {expected_list}\n" \
                f"Got: {actual_list}"
        
        # Property: Total element count should match
        expected_total = sum(len(lst) for lst in list_data.values())
        actual_total = result.output['total_elements']
        assert actual_total == expected_total, \
            f"Total element count should match.\n" \
            f"Expected: {expected_total}\n" \
            f"Got: {actual_total}"
    
    @settings(max_examples=50)
    @given(
        empty_inputs=st.just({})
    )
    def test_empty_input_data_passing(self, empty_inputs):
        """
        Property 8: Code node input passing (Edge case - empty inputs)
        
        For any code node with empty input data, the code should still execute
        successfully and handle the empty input gracefully.
        
        This property verifies that:
        1. Empty inputs don't cause errors
        2. Code can detect empty inputs
        3. Execution completes successfully
        
        Validates: Requirements 10.4
        """
        python_code = """
def transform(inputs):
    return {
        'is_empty': len(inputs) == 0,
        'input_count': len(inputs),
        'keys': list(inputs.keys())
    }
"""
        
        result = self.executor.execute_python(python_code, empty_inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for empty inputs.\n" \
            f"Error: {result.error}"
        
        # Property: Should detect empty inputs
        assert result.output['is_empty'] is True, \
            f"Code should detect empty inputs"
        assert result.output['input_count'] == 0, \
            f"Input count should be 0"
        assert result.output['keys'] == [], \
            f"Keys list should be empty"


class TestCodeNodeOutputCaptureProperties:
    """Property-Based Tests for Code Node Output Capture"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=10)
    
    # Feature: project-production-readiness, Property 9: Code node output capture
    @settings(max_examples=100)
    @given(
        output_data=st.one_of(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_'),
                values=st.one_of(
                    st.integers(min_value=-1000, max_value=1000),
                    st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '),
                    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                    st.booleans(),
                    st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10)
                ),
                min_size=1,
                max_size=5
            ),
            st.lists(
                st.integers(min_value=0, max_value=100),
                min_size=1,
                max_size=10
            ),
            st.text(min_size=1, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 ')
        )
    )
    def test_python_stdout_output_capture(self, output_data):
        """
        Property 9: Code node output capture (Python - stdout)
        
        For any Python code node execution that produces output to stdout,
        the system should capture and return the output data correctly.
        
        This property verifies that:
        1. Stdout output is captured
        2. Output is correctly parsed as JSON
        3. Output data structure is preserved
        4. Output matches what the code intended to produce
        
        Validates: Requirements 10.5
        """
        # Create Python code that outputs the data
        code = f"""
import json

def transform(inputs):
    # Return the output data
    return {repr(output_data)}

# The wrapper will print this as JSON to stdout
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for stdout output capture.\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Output should be captured
        assert result.output is not None, \
            f"Output should be captured from stdout"
        
        # Property: Output should match the expected data
        assert result.output == output_data, \
            f"Captured output should match expected data.\n" \
            f"Expected: {output_data}\n" \
            f"Got: {result.output}"
        
        # Property: Exit code should be 0 for successful execution
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution, got {result.exit_code}"
    
    @settings(max_examples=100, deadline=500)
    @given(
        output_data=st.one_of(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz_'),
                values=st.one_of(
                    st.integers(min_value=-1000, max_value=1000),
                    st.text(min_size=0, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '),
                    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                    st.booleans(),
                    st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=10)
                ),
                min_size=1,
                max_size=5
            ),
            st.lists(
                st.integers(min_value=0, max_value=100),
                min_size=1,
                max_size=10
            ),
            st.text(min_size=1, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 ')
        )
    )
    def test_javascript_stdout_output_capture(self, output_data):
        """
        Property 9: Code node output capture (JavaScript - stdout)
        
        For any JavaScript code node execution that produces output to stdout,
        the system should capture and return the output data correctly.
        
        This property verifies that:
        1. Stdout output is captured
        2. Output is correctly parsed as JSON
        3. Output data structure is preserved
        4. Output matches what the code intended to produce
        
        Validates: Requirements 10.5
        """
        # Convert Python data to JavaScript literal
        import json
        output_json = json.dumps(output_data)
        
        # Create JavaScript code that outputs the data
        code = f"""
module.exports = (inputs) => {{
    // Return the output data
    return {output_json};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for stdout output capture.\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Output should be captured
        assert result.output is not None, \
            f"Output should be captured from stdout"
        
        # Property: Output should match the expected data
        assert result.output == output_data, \
            f"Captured output should match expected data.\n" \
            f"Expected: {output_data}\n" \
            f"Got: {result.output}"
        
        # Property: Exit code should be 0 for successful execution
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution, got {result.exit_code}"
    
    @settings(max_examples=50)
    @given(
        error_message=st.text(min_size=1, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 ')
    )
    def test_python_stderr_error_capture(self, error_message):
        """
        Property 9: Code node output capture (Python - stderr)
        
        For any Python code node execution that produces errors to stderr,
        the system should capture and return the error information correctly.
        
        This property verifies that:
        1. Stderr output is captured
        2. Error messages are preserved
        3. Stack traces are captured
        4. Execution is marked as failed
        
        Validates: Requirements 10.5
        """
        # Create Python code that raises an error
        code = f"""
def transform(inputs):
    raise RuntimeError("{error_message}")
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail when code raises an error"
        
        # Property: Stderr should be captured
        assert result.stderr is not None, \
            f"Stderr should be captured when code raises an error"
        
        # Property: Error message should be in stderr or stack trace
        error_found = (
            (result.stderr and error_message in result.stderr) or
            (result.stack_trace and error_message in result.stack_trace) or
            (result.error and error_message in result.error)
        )
        assert error_found, \
            f"Error message should be captured in stderr or stack trace.\n" \
            f"Expected message: {error_message}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Error: {result.error}"
        
        # Property: Stack trace should be available
        assert result.stack_trace is not None, \
            f"Stack trace should be available for errors"
        
        # Property: Stack trace should contain "RuntimeError"
        assert "RuntimeError" in result.stack_trace or "RuntimeError" in result.stderr, \
            f"Stack trace should contain error type.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for failed execution, got {result.exit_code}"
    
    @settings(max_examples=50, deadline=500)
    @given(
        error_message=st.text(min_size=1, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz0123456789 ')
    )
    def test_javascript_stderr_error_capture(self, error_message):
        """
        Property 9: Code node output capture (JavaScript - stderr)
        
        For any JavaScript code node execution that produces errors to stderr,
        the system should capture and return the error information correctly.
        
        This property verifies that:
        1. Stderr output is captured
        2. Error messages are preserved
        3. Stack traces are captured
        4. Execution is marked as failed
        
        Validates: Requirements 10.5
        """
        # Create JavaScript code that throws an error
        code = f"""
module.exports = (inputs) => {{
    throw new Error("{error_message}");
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail when code throws an error"
        
        # Property: Stderr should be captured
        assert result.stderr is not None, \
            f"Stderr should be captured when code throws an error"
        
        # Property: Error message should be in stderr or stack trace
        error_found = (
            (result.stderr and error_message in result.stderr) or
            (result.stack_trace and error_message in result.stack_trace) or
            (result.error and error_message in result.error)
        )
        assert error_found, \
            f"Error message should be captured in stderr or stack trace.\n" \
            f"Expected message: {error_message}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Error: {result.error}"
        
        # Property: Stack trace or stderr should contain error information
        # Note: For edge cases like whitespace-only errors, stack_trace may be None
        # but stderr should still be captured
        has_error_info = (
            (result.stack_trace is not None and result.stack_trace.strip()) or
            (result.stderr is not None and result.stderr.strip()) or
            (result.error is not None and result.error.strip())
        )
        assert has_error_info, \
            f"At least one of stack_trace, stderr, or error should contain information.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Error: {result.error}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for failed execution, got {result.exit_code}"
    
    @settings(max_examples=50)
    @given(
        output_value=st.integers(min_value=1, max_value=1000),
        warning_message=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz ')
    )
    def test_python_stdout_and_stderr_capture(self, output_value, warning_message):
        """
        Property 9: Code node output capture (Python - both stdout and stderr)
        
        For any Python code node execution that produces both stdout output
        and stderr warnings/messages, the system should capture both correctly.
        
        This property verifies that:
        1. Both stdout and stderr are captured simultaneously
        2. Stdout output is correctly parsed
        3. Stderr warnings are preserved
        4. Execution can succeed even with stderr output (warnings)
        
        Validates: Requirements 10.5
        """
        # Create Python code that writes to both stdout and stderr
        code = f"""
import sys

def transform(inputs):
    # Write a warning to stderr
    print("{warning_message}", file=sys.stderr)
    
    # Return normal output
    return {{"result": {output_value}, "status": "success"}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should succeed (warnings don't cause failure)
        assert result.success, \
            f"Execution should succeed even with stderr warnings.\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Stdout output should be captured and parsed
        assert result.output is not None, \
            f"Stdout output should be captured"
        assert result.output.get("result") == output_value, \
            f"Stdout output should be correctly parsed.\n" \
            f"Expected result: {output_value}\n" \
            f"Got: {result.output.get('result')}"
        
        # Property: Stderr should be captured
        assert result.stderr is not None, \
            f"Stderr should be captured even for successful execution"
        
        # Property: Warning message should be in stderr
        assert warning_message in result.stderr, \
            f"Warning message should be captured in stderr.\n" \
            f"Expected: {warning_message}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Exit code should be 0 (success despite warnings)
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution with warnings, got {result.exit_code}"
    
    @settings(max_examples=50, deadline=500)
    @given(
        output_value=st.integers(min_value=1, max_value=1000),
        log_message=st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz ')
    )
    def test_javascript_stdout_and_stderr_capture(self, output_value, log_message):
        """
        Property 9: Code node output capture (JavaScript - both stdout and stderr)
        
        For any JavaScript code node execution that produces both stdout output
        and stderr messages, the system should capture both correctly.
        
        This property verifies that:
        1. Both stdout and stderr are captured simultaneously
        2. Stdout output is correctly parsed
        3. Stderr messages are preserved
        4. Execution can succeed even with stderr output
        
        Validates: Requirements 10.5
        """
        # Create JavaScript code that writes to both stdout and stderr
        code = f"""
module.exports = (inputs) => {{
    // Write a message to stderr
    console.error("{log_message}");
    
    // Return normal output
    return {{result: {output_value}, status: "success"}};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should succeed (stderr messages don't cause failure)
        assert result.success, \
            f"Execution should succeed even with stderr messages.\n" \
            f"Error: {result.error}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Stdout output should be captured and parsed
        assert result.output is not None, \
            f"Stdout output should be captured"
        assert result.output.get("result") == output_value, \
            f"Stdout output should be correctly parsed.\n" \
            f"Expected result: {output_value}\n" \
            f"Got: {result.output.get('result')}"
        
        # Property: Stderr should be captured
        assert result.stderr is not None, \
            f"Stderr should be captured even for successful execution"
        
        # Property: Log message should be in stderr
        assert log_message in result.stderr, \
            f"Log message should be captured in stderr.\n" \
            f"Expected: {log_message}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Exit code should be 0 (success despite stderr output)
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution with stderr output, got {result.exit_code}"
    
    @settings(max_examples=30)
    @given(
        output_size=st.integers(min_value=10, max_value=100)
    )
    def test_python_large_output_capture(self, output_size):
        """
        Property 9: Code node output capture (Python - large output)
        
        For any Python code node execution that produces large output,
        the system should capture the entire output without truncation.
        
        This property verifies that:
        1. Large outputs are fully captured
        2. No data is lost or truncated
        3. Output structure is preserved
        
        Validates: Requirements 10.5
        """
        # Create Python code that generates large output
        code = f"""
def transform(inputs):
    # Generate a large list
    return {{"data": list(range({output_size})), "size": {output_size}}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for large output.\n" \
            f"Error: {result.error}"
        
        # Property: Output should be captured completely
        assert result.output is not None, \
            f"Output should be captured"
        assert "data" in result.output, \
            f"Output should contain 'data' field"
        assert "size" in result.output, \
            f"Output should contain 'size' field"
        
        # Property: Output size should match
        assert result.output["size"] == output_size, \
            f"Output size should match.\n" \
            f"Expected: {output_size}\n" \
            f"Got: {result.output['size']}"
        
        # Property: All data should be captured
        assert len(result.output["data"]) == output_size, \
            f"All data should be captured without truncation.\n" \
            f"Expected length: {output_size}\n" \
            f"Got length: {len(result.output['data'])}"
        
        # Property: Data should be correct
        expected_data = list(range(output_size))
        assert result.output["data"] == expected_data, \
            f"Data should be correctly captured.\n" \
            f"Expected: {expected_data[:5]}... (first 5)\n" \
            f"Got: {result.output['data'][:5]}... (first 5)"
    
    @settings(max_examples=30, deadline=500)
    @given(
        output_size=st.integers(min_value=10, max_value=100)
    )
    def test_javascript_large_output_capture(self, output_size):
        """
        Property 9: Code node output capture (JavaScript - large output)
        
        For any JavaScript code node execution that produces large output,
        the system should capture the entire output without truncation.
        
        This property verifies that:
        1. Large outputs are fully captured
        2. No data is lost or truncated
        3. Output structure is preserved
        
        Validates: Requirements 10.5
        """
        # Create JavaScript code that generates large output
        code = f"""
module.exports = (inputs) => {{
    // Generate a large array
    const data = Array.from({{length: {output_size}}}, (_, i) => i);
    return {{data: data, size: {output_size}}};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed for large output.\n" \
            f"Error: {result.error}"
        
        # Property: Output should be captured completely
        assert result.output is not None, \
            f"Output should be captured"
        assert "data" in result.output, \
            f"Output should contain 'data' field"
        assert "size" in result.output, \
            f"Output should contain 'size' field"
        
        # Property: Output size should match
        assert result.output["size"] == output_size, \
            f"Output size should match.\n" \
            f"Expected: {output_size}\n" \
            f"Got: {result.output['size']}"
        
        # Property: All data should be captured
        assert len(result.output["data"]) == output_size, \
            f"All data should be captured without truncation.\n" \
            f"Expected length: {output_size}\n" \
            f"Got length: {len(result.output['data'])}"
        
        # Property: Data should be correct
        expected_data = list(range(output_size))
        assert result.output["data"] == expected_data, \
            f"Data should be correctly captured.\n" \
            f"Expected: {expected_data[:5]}... (first 5)\n" \
            f"Got: {result.output['data'][:5]}... (first 5)"



class TestCodeNodeTimeoutEnforcementProperties:
    """Property-Based Tests for Code Node Timeout Enforcement"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=10)
    
    # Feature: project-production-readiness, Property 10: Code node timeout enforcement
    @settings(max_examples=30, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3),
        sleep_multiplier=st.floats(min_value=1.5, max_value=3.0)
    )
    def test_python_timeout_enforcement(self, timeout_seconds, sleep_multiplier):
        """
        Property 10: Code node timeout enforcement (Python)
        
        For any Python code node with timeout configuration, if execution
        exceeds the timeout, the system should:
        1. Terminate the execution
        2. Return timeout=True
        3. Return success=False
        4. Provide timeout error message
        5. Execution time should be close to timeout value
        
        This property verifies that timeout enforcement works correctly
        for Python code nodes across different timeout values.
        
        Validates: Requirements 10.6
        """
        # Code that sleeps longer than the timeout
        sleep_time = timeout_seconds * sleep_multiplier
        code = f"""
import time

def transform(inputs):
    time.sleep({sleep_time})
    return {{"done": True}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail on timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time}s"
        
        # Property: Timeout flag should be set
        assert result.timeout, \
            f"Timeout flag should be set when execution exceeds timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time}s"
        
        # Property: Error message should mention timeout
        assert result.error is not None, \
            f"Error message should be present for timeout"
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), \
            f"Error message should mention timeout: {result.error}"
        
        # Property: Execution time should be close to timeout value
        # Allow some tolerance for process termination overhead
        assert result.execution_time >= timeout_seconds * 0.8, \
            f"Execution time should be at least 80% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time <= timeout_seconds * 1.5, \
            f"Execution time should not exceed 150% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        
        # Property: Output should be None or empty (execution was terminated)
        assert result.output is None or result.output == {}, \
            f"Output should be None or empty for timed out execution.\n" \
            f"Got: {result.output}"
    
    @settings(max_examples=30, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3),
        sleep_multiplier=st.floats(min_value=1.5, max_value=3.0)
    )
    def test_javascript_timeout_enforcement(self, timeout_seconds, sleep_multiplier):
        """
        Property 10: Code node timeout enforcement (JavaScript)
        
        For any JavaScript code node with timeout configuration, if execution
        exceeds the timeout, the system should:
        1. Terminate the execution
        2. Return timeout=True
        3. Return success=False
        4. Provide timeout error message
        5. Execution time should be close to timeout value
        
        This property verifies that timeout enforcement works correctly
        for JavaScript code nodes across different timeout values.
        
        Validates: Requirements 10.6
        """
        # Code that sleeps longer than the timeout
        sleep_time_ms = int(timeout_seconds * sleep_multiplier * 1000)
        code = f"""
module.exports = (inputs) => {{
    // Sleep using a busy loop (setTimeout won't work in sync context)
    const start = Date.now();
    while (Date.now() - start < {sleep_time_ms}) {{
        // Busy wait
    }}
    return {{done: true}};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail on timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time_ms}ms"
        
        # Property: Timeout flag should be set
        assert result.timeout, \
            f"Timeout flag should be set when execution exceeds timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time_ms}ms"
        
        # Property: Error message should mention timeout
        assert result.error is not None, \
            f"Error message should be present for timeout"
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), \
            f"Error message should mention timeout: {result.error}"
        
        # Property: Execution time should be close to timeout value
        # Allow some tolerance for process termination overhead
        assert result.execution_time >= timeout_seconds * 0.8, \
            f"Execution time should be at least 80% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time <= timeout_seconds * 1.5, \
            f"Execution time should not exceed 150% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        
        # Property: Output should be None or empty (execution was terminated)
        assert result.output is None or result.output == {}, \
            f"Output should be None or empty for timed out execution.\n" \
            f"Got: {result.output}"
    
    @settings(max_examples=50, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=2, max_value=5),
        execution_fraction=st.floats(min_value=0.1, max_value=0.8)
    )
    def test_python_no_timeout_when_within_limit(self, timeout_seconds, execution_fraction):
        """
        Property 10: Code node timeout enforcement (Python - no timeout)
        
        For any Python code node that completes within the timeout limit,
        the system should:
        1. Complete successfully
        2. Return timeout=False
        3. Return success=True
        4. Return the expected output
        
        This property verifies that timeout enforcement doesn't interfere
        with normal execution that completes within the timeout.
        
        Validates: Requirements 10.6
        """
        # Code that sleeps less than the timeout
        sleep_time = timeout_seconds * execution_fraction
        expected_value = 42
        code = f"""
import time

def transform(inputs):
    time.sleep({sleep_time})
    return {{"result": {expected_value}, "slept": {sleep_time}}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed when within timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time}s\n" \
            f"Error: {result.error}"
        
        # Property: Timeout flag should not be set
        assert not result.timeout, \
            f"Timeout flag should not be set when execution completes within timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time}s"
        
        # Property: Output should be present and correct
        assert result.output is not None, \
            f"Output should be present for successful execution"
        assert result.output.get("result") == expected_value, \
            f"Output should contain expected result.\n" \
            f"Expected: {expected_value}\n" \
            f"Got: {result.output.get('result')}"
        
        # Property: Execution time should be close to sleep time
        assert result.execution_time >= sleep_time * 0.8, \
            f"Execution time should be at least 80% of sleep time.\n" \
            f"Sleep time: {sleep_time}s, Execution time: {result.execution_time}s"
        assert result.execution_time < timeout_seconds, \
            f"Execution time should be less than timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        
        # Property: Exit code should be 0
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution, got {result.exit_code}"
    
    @settings(max_examples=50, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=2, max_value=5),
        execution_fraction=st.floats(min_value=0.1, max_value=0.8)
    )
    def test_javascript_no_timeout_when_within_limit(self, timeout_seconds, execution_fraction):
        """
        Property 10: Code node timeout enforcement (JavaScript - no timeout)
        
        For any JavaScript code node that completes within the timeout limit,
        the system should:
        1. Complete successfully
        2. Return timeout=False
        3. Return success=True
        4. Return the expected output
        
        This property verifies that timeout enforcement doesn't interfere
        with normal execution that completes within the timeout.
        
        Validates: Requirements 10.6
        """
        # Code that sleeps less than the timeout
        sleep_time_ms = int(timeout_seconds * execution_fraction * 1000)
        expected_value = 42
        code = f"""
module.exports = (inputs) => {{
    // Sleep using a busy loop
    const start = Date.now();
    while (Date.now() - start < {sleep_time_ms}) {{
        // Busy wait
    }}
    return {{result: {expected_value}, slept_ms: {sleep_time_ms}}};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should succeed
        assert result.success, \
            f"Execution should succeed when within timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time_ms}ms\n" \
            f"Error: {result.error}"
        
        # Property: Timeout flag should not be set
        assert not result.timeout, \
            f"Timeout flag should not be set when execution completes within timeout.\n" \
            f"Timeout: {timeout_seconds}s, Sleep time: {sleep_time_ms}ms"
        
        # Property: Output should be present and correct
        assert result.output is not None, \
            f"Output should be present for successful execution"
        assert result.output.get("result") == expected_value, \
            f"Output should contain expected result.\n" \
            f"Expected: {expected_value}\n" \
            f"Got: {result.output.get('result')}"
        
        # Property: Execution time should be close to sleep time
        sleep_time_seconds = sleep_time_ms / 1000.0
        assert result.execution_time >= sleep_time_seconds * 0.8, \
            f"Execution time should be at least 80% of sleep time.\n" \
            f"Sleep time: {sleep_time_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time < timeout_seconds, \
            f"Execution time should be less than timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        
        # Property: Exit code should be 0
        assert result.exit_code == 0, \
            f"Exit code should be 0 for successful execution, got {result.exit_code}"
    
    @settings(max_examples=30, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3)
    )
    def test_python_timeout_with_infinite_loop(self, timeout_seconds):
        """
        Property 10: Code node timeout enforcement (Python - infinite loop)
        
        For any Python code node with an infinite loop, the timeout
        mechanism should terminate the execution after the timeout period.
        
        This property verifies that timeout enforcement can handle
        infinite loops and other non-terminating code.
        
        Validates: Requirements 10.6
        """
        # Code with an infinite loop
        code = """
def transform(inputs):
    # Infinite loop
    while True:
        pass
    return {"done": True}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail on timeout for infinite loop"
        
        # Property: Timeout flag should be set
        assert result.timeout, \
            f"Timeout flag should be set for infinite loop"
        
        # Property: Error message should mention timeout
        assert result.error is not None, \
            f"Error message should be present"
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), \
            f"Error message should mention timeout: {result.error}"
        
        # Property: Execution time should be close to timeout
        assert result.execution_time >= timeout_seconds * 0.8, \
            f"Execution time should be at least 80% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time <= timeout_seconds * 1.5, \
            f"Execution time should not exceed 150% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
    
    @settings(max_examples=30, deadline=None)
    @given(
        timeout_seconds=st.integers(min_value=1, max_value=3)
    )
    def test_javascript_timeout_with_infinite_loop(self, timeout_seconds):
        """
        Property 10: Code node timeout enforcement (JavaScript - infinite loop)
        
        For any JavaScript code node with an infinite loop, the timeout
        mechanism should terminate the execution after the timeout period.
        
        This property verifies that timeout enforcement can handle
        infinite loops and other non-terminating code.
        
        Validates: Requirements 10.6
        """
        # Code with an infinite loop
        code = """
module.exports = (inputs) => {
    // Infinite loop
    while (true) {
        // Keep looping
    }
    return {done: true};
};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=timeout_seconds)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail on timeout for infinite loop"
        
        # Property: Timeout flag should be set
        assert result.timeout, \
            f"Timeout flag should be set for infinite loop"
        
        # Property: Error message should mention timeout
        assert result.error is not None, \
            f"Error message should be present"
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), \
            f"Error message should mention timeout: {result.error}"
        
        # Property: Execution time should be close to timeout
        assert result.execution_time >= timeout_seconds * 0.8, \
            f"Execution time should be at least 80% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
        assert result.execution_time <= timeout_seconds * 1.5, \
            f"Execution time should not exceed 150% of timeout.\n" \
            f"Timeout: {timeout_seconds}s, Execution time: {result.execution_time}s"
    
    @settings(max_examples=20, deadline=None)
    @given(
        short_timeout=st.integers(min_value=1, max_value=2),
        long_timeout=st.integers(min_value=5, max_value=10)
    )
    def test_python_different_timeout_values(self, short_timeout, long_timeout):
        """
        Property 10: Code node timeout enforcement (Python - different timeouts)
        
        For any Python code node, different timeout values should result
        in different timeout behaviors. A shorter timeout should cause
        timeout earlier than a longer timeout for the same code.
        
        This property verifies that timeout values are correctly applied
        and enforced.
        
        Validates: Requirements 10.6
        """
        # Assume short_timeout < long_timeout
        assume(short_timeout < long_timeout)
        
        # Code that sleeps between the two timeouts
        sleep_time = (short_timeout + long_timeout) / 2.0
        code = f"""
import time

def transform(inputs):
    time.sleep({sleep_time})
    return {{"done": True}}
"""
        
        inputs = {}
        
        # Execute with short timeout - should timeout
        result_short = self.executor.execute_python(code, inputs, timeout=short_timeout)
        
        # Execute with long timeout - should succeed
        result_long = self.executor.execute_python(code, inputs, timeout=long_timeout)
        
        # Property: Short timeout should fail
        assert not result_short.success, \
            f"Execution should fail with short timeout.\n" \
            f"Short timeout: {short_timeout}s, Sleep time: {sleep_time}s"
        assert result_short.timeout, \
            f"Timeout flag should be set with short timeout"
        
        # Property: Long timeout should succeed
        assert result_long.success, \
            f"Execution should succeed with long timeout.\n" \
            f"Long timeout: {long_timeout}s, Sleep time: {sleep_time}s\n" \
            f"Error: {result_long.error}"
        assert not result_long.timeout, \
            f"Timeout flag should not be set with long timeout"
        
        # Property: Execution times should reflect the timeout behavior
        assert result_short.execution_time < result_long.execution_time, \
            f"Short timeout execution should terminate earlier.\n" \
            f"Short execution time: {result_short.execution_time}s\n" \
            f"Long execution time: {result_long.execution_time}s"
    
    @settings(max_examples=20, deadline=None)
    @given(
        short_timeout=st.integers(min_value=1, max_value=2),
        long_timeout=st.integers(min_value=5, max_value=10)
    )
    def test_javascript_different_timeout_values(self, short_timeout, long_timeout):
        """
        Property 10: Code node timeout enforcement (JavaScript - different timeouts)
        
        For any JavaScript code node, different timeout values should result
        in different timeout behaviors. A shorter timeout should cause
        timeout earlier than a longer timeout for the same code.
        
        This property verifies that timeout values are correctly applied
        and enforced.
        
        Validates: Requirements 10.6
        """
        # Assume short_timeout < long_timeout
        assume(short_timeout < long_timeout)
        
        # Code that sleeps between the two timeouts
        sleep_time_ms = int((short_timeout + long_timeout) / 2.0 * 1000)
        code = f"""
module.exports = (inputs) => {{
    const start = Date.now();
    while (Date.now() - start < {sleep_time_ms}) {{
        // Busy wait
    }}
    return {{done: true}};
}};
"""
        
        inputs = {}
        
        # Execute with short timeout - should timeout
        result_short = self.executor.execute_javascript(code, inputs, timeout=short_timeout)
        
        # Execute with long timeout - should succeed
        result_long = self.executor.execute_javascript(code, inputs, timeout=long_timeout)
        
        # Property: Short timeout should fail
        assert not result_short.success, \
            f"Execution should fail with short timeout.\n" \
            f"Short timeout: {short_timeout}s, Sleep time: {sleep_time_ms}ms"
        assert result_short.timeout, \
            f"Timeout flag should be set with short timeout"
        
        # Property: Long timeout should succeed
        assert result_long.success, \
            f"Execution should succeed with long timeout.\n" \
            f"Long timeout: {long_timeout}s, Sleep time: {sleep_time_ms}ms\n" \
            f"Error: {result_long.error}"
        assert not result_long.timeout, \
            f"Timeout flag should not be set with long timeout"
        
        # Property: Execution times should reflect the timeout behavior
        assert result_short.execution_time < result_long.execution_time, \
            f"Short timeout execution should terminate earlier.\n" \
            f"Short execution time: {result_short.execution_time}s\n" \
            f"Long execution time: {result_long.execution_time}s"
