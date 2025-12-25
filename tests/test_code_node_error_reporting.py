"""
Property-Based Tests for Code Node Error Reporting (Property 11)

These tests use Hypothesis to verify that code node execution failures
provide detailed error information including stack traces.

Feature: project-production-readiness, Property 11: Code node error reporting
Validates: Requirements 10.7
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import assume

from src.code_executor import CodeExecutor, ExecutionResult


class TestCodeNodeErrorReportingProperties:
    """Property-Based Tests for Code Node Error Reporting"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=10)
    
    # Feature: project-production-readiness, Property 11: Code node error reporting
    @settings(max_examples=100)
    @given(
        error_type=st.sampled_from([
            "ValueError",
            "TypeError", 
            "KeyError",
            "IndexError",
            "RuntimeError",
            "AttributeError",
            "ZeroDivisionError"
        ]),
        error_message=st.text(
            min_size=1,
            max_size=100,
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '
        )
    )
    def test_python_error_stack_trace_completeness(self, error_type, error_message):
        """
        Property 11: Code node error reporting (Python - stack trace completeness)
        
        For any failed Python code node execution, the system should provide:
        1. Detailed stack trace
        2. Error type information
        3. Error message
        4. Line number information
        5. success=False flag
        6. Non-zero exit code
        
        This property verifies that all error information is captured and
        available for debugging.
        
        Validates: Requirements 10.7
        """
        # Create Python code that raises a specific error
        code = f"""
def transform(inputs):
    # This will raise an error
    raise {error_type}("{error_message}")
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail when code raises {error_type}"
        
        # Property: Stack trace should be present and non-empty
        assert result.stack_trace is not None, \
            f"Stack trace should be present for {error_type}"
        assert len(result.stack_trace.strip()) > 0, \
            f"Stack trace should not be empty for {error_type}"
        
        # Property: Stack trace should contain error type
        assert error_type in result.stack_trace or error_type in result.stderr, \
            f"Stack trace should contain error type '{error_type}'.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Error message should be captured
        assert result.error is not None, \
            f"Error message should be captured"
        
        # Property: Error message or stack trace should contain the custom message
        error_found = (
            (result.error and error_message in result.error) or
            (result.stack_trace and error_message in result.stack_trace) or
            (result.stderr and error_message in result.stderr)
        )
        assert error_found, \
            f"Custom error message '{error_message}' should be in error info.\n" \
            f"Error: {result.error}\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for failed execution, got {result.exit_code}"
        
        # Property: Stderr should be captured
        assert result.stderr is not None, \
            f"Stderr should be captured for error reporting"
    
    @settings(max_examples=100, deadline=500)
    @given(
        error_message=st.text(
            min_size=1,
            max_size=100,
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789 '
        )
    )
    def test_javascript_error_stack_trace_completeness(self, error_message):
        """
        Property 11: Code node error reporting (JavaScript - stack trace completeness)
        
        For any failed JavaScript code node execution, the system should provide:
        1. Detailed stack trace
        2. Error message
        3. success=False flag
        4. Non-zero exit code
        5. Stderr output
        
        This property verifies that all error information is captured and
        available for debugging.
        
        Validates: Requirements 10.7
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
        
        # Property: Error information should be present
        has_error_info = (
            (result.stack_trace is not None and result.stack_trace.strip()) or
            (result.stderr is not None and result.stderr.strip()) or
            (result.error is not None and result.error.strip())
        )
        assert has_error_info, \
            f"At least one error field should contain information.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}\n" \
            f"Error: {result.error}"
        
        # Property: Error message should be captured somewhere
        error_found = (
            (result.error and error_message in result.error) or
            (result.stack_trace and error_message in result.stack_trace) or
            (result.stderr and error_message in result.stderr)
        )
        assert error_found, \
            f"Error message '{error_message}' should be captured.\n" \
            f"Error: {result.error}\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for failed execution, got {result.exit_code}"
        
        # Property: Stderr should be captured
        assert result.stderr is not None, \
            f"Stderr should be captured for error reporting"
    
    @settings(max_examples=50)
    @given(
        line_number=st.integers(min_value=5, max_value=20),
        error_message=st.text(
            min_size=5,
            max_size=50,
            alphabet='abcdefghijklmnopqrstuvwxyz '
        )
    )
    def test_python_error_line_number_reporting(self, line_number, error_message):
        """
        Property 11: Code node error reporting (Python - line number reporting)
        
        For any Python code that fails at a specific line, the stack trace
        should include line number information to help with debugging.
        
        This property verifies that:
        1. Line numbers are included in stack traces
        2. The error location can be identified
        3. Stack trace provides context for debugging
        
        Validates: Requirements 10.7
        """
        # Create Python code with error at specific line
        padding_lines = "\n".join([f"    # Line {i}" for i in range(1, line_number)])
        code = f"""
def transform(inputs):
{padding_lines}
    raise RuntimeError("{error_message}")
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail"
        
        # Property: Stack trace should be present
        assert result.stack_trace is not None, \
            f"Stack trace should be present"
        
        # Property: Stack trace should contain line number information
        # Look for "line" keyword in stack trace (case insensitive)
        has_line_info = (
            "line" in result.stack_trace.lower() or
            "line" in result.stderr.lower() if result.stderr else False
        )
        assert has_line_info, \
            f"Stack trace should contain line number information.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Error message should be present
        assert error_message in result.stack_trace or error_message in result.stderr, \
            f"Error message should be in stack trace or stderr"
    
    @settings(max_examples=50)
    @given(
        function_name=st.text(
            min_size=3,
            max_size=20,
            alphabet='abcdefghijklmnopqrstuvwxyz_'
        ),
        error_message=st.text(
            min_size=5,
            max_size=50,
            alphabet='abcdefghijklmnopqrstuvwxyz '
        )
    )
    def test_python_error_function_context_reporting(self, function_name, error_message):
        """
        Property 11: Code node error reporting (Python - function context)
        
        For any Python code with nested functions that fail, the stack trace
        should include function names and call context.
        
        This property verifies that:
        1. Function names appear in stack traces
        2. Call stack is preserved
        3. Context helps identify error location
        
        Validates: Requirements 10.7
        """
        # Ensure function name starts with a letter
        if not function_name[0].isalpha():
            function_name = 'func_' + function_name
        
        # Create Python code with nested function
        code = f"""
def {function_name}():
    raise ValueError("{error_message}")

def transform(inputs):
    {function_name}()
    return {{"result": "success"}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail"
        
        # Property: Stack trace should be present
        assert result.stack_trace is not None, \
            f"Stack trace should be present"
        
        # Property: Stack trace should contain function name
        # The function name should appear in the stack trace
        has_function_context = (
            function_name in result.stack_trace or
            function_name in result.stderr if result.stderr else False
        )
        assert has_function_context, \
            f"Stack trace should contain function name '{function_name}'.\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Error message should be present
        assert error_message in result.stack_trace or error_message in result.stderr, \
            f"Error message should be in stack trace or stderr"
    
    @settings(max_examples=50)
    @given(
        syntax_error_type=st.sampled_from([
            "missing_paren",
            "invalid_syntax",
            "indentation_error"
        ])
    )
    def test_python_syntax_error_reporting(self, syntax_error_type):
        """
        Property 11: Code node error reporting (Python - syntax errors)
        
        For any Python code with syntax errors, the system should provide
        clear error messages indicating the syntax problem.
        
        This property verifies that:
        1. Syntax errors are detected
        2. Error messages are descriptive
        3. Execution fails appropriately
        
        Validates: Requirements 10.7
        """
        # Create Python code with syntax error
        if syntax_error_type == "missing_paren":
            code = """
def transform(inputs):
    result = {"value": 42
    return result
"""
        elif syntax_error_type == "invalid_syntax":
            code = """
def transform(inputs):
    if True
        return {"value": 42}
"""
        else:  # indentation_error
            code = """
def transform(inputs):
    if True:
    return {"value": 42}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail for syntax error: {syntax_error_type}"
        
        # Property: Error information should be present
        has_error_info = (
            (result.error is not None and result.error.strip()) or
            (result.stack_trace is not None and result.stack_trace.strip()) or
            (result.stderr is not None and result.stderr.strip())
        )
        assert has_error_info, \
            f"Error information should be present for syntax error.\n" \
            f"Error: {result.error}\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Error should indicate syntax problem
        error_text = (result.error or "") + (result.stack_trace or "") + (result.stderr or "")
        has_syntax_indicator = (
            "syntax" in error_text.lower() or
            "indentation" in error_text.lower() or
            "invalid" in error_text.lower() or
            "error" in error_text.lower()
        )
        assert has_syntax_indicator, \
            f"Error should indicate syntax problem.\n" \
            f"Error text: {error_text}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for syntax error"
    
    @settings(max_examples=50, deadline=500)
    @given(
        syntax_error_type=st.sampled_from([
            "missing_brace",
            "unclosed_string",
            "invalid_token"
        ])
    )
    def test_javascript_syntax_error_reporting(self, syntax_error_type):
        """
        Property 11: Code node error reporting (JavaScript - syntax errors)
        
        For any JavaScript code with syntax errors, the system should provide
        clear error messages indicating the syntax problem.
        
        This property verifies that:
        1. Syntax errors are detected
        2. Error messages are descriptive
        3. Execution fails appropriately
        
        Validates: Requirements 10.7
        """
        # Create JavaScript code with syntax error
        if syntax_error_type == "missing_brace":
            code = """
module.exports = (inputs) => {
    const result = {value: 42;
    return result;
};
"""
        elif syntax_error_type == "unclosed_string":
            code = """
module.exports = (inputs) => {
    const result = "unclosed string;
    return result;
};
"""
        else:  # invalid_token
            code = """
module.exports = (inputs) => {
    const result = @invalid;
    return result;
};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail for syntax error: {syntax_error_type}"
        
        # Property: Error information should be present
        has_error_info = (
            (result.error is not None and result.error.strip()) or
            (result.stack_trace is not None and result.stack_trace.strip()) or
            (result.stderr is not None and result.stderr.strip())
        )
        assert has_error_info, \
            f"Error information should be present for syntax error.\n" \
            f"Error: {result.error}\n" \
            f"Stack trace: {result.stack_trace}\n" \
            f"Stderr: {result.stderr}"
        
        # Property: Error should indicate syntax problem
        error_text = (result.error or "") + (result.stack_trace or "") + (result.stderr or "")
        has_syntax_indicator = (
            "syntax" in error_text.lower() or
            "unexpected" in error_text.lower() or
            "invalid" in error_text.lower() or
            "error" in error_text.lower()
        )
        assert has_syntax_indicator, \
            f"Error should indicate syntax problem.\n" \
            f"Error text: {error_text}"
        
        # Property: Exit code should be non-zero
        assert result.exit_code != 0, \
            f"Exit code should be non-zero for syntax error"
    
    @settings(max_examples=50)
    @given(
        variable_name=st.text(
            min_size=3,
            max_size=20,
            alphabet='abcdefghijklmnopqrstuvwxyz_'
        )
    )
    def test_python_undefined_variable_error_reporting(self, variable_name):
        """
        Property 11: Code node error reporting (Python - undefined variables)
        
        For any Python code that references undefined variables, the system
        should provide clear error messages with the variable name.
        
        This property verifies that:
        1. NameError is properly reported
        2. Variable name is included in error message
        3. Stack trace is complete
        
        Validates: Requirements 10.7
        """
        # Ensure variable name starts with a letter
        if not variable_name[0].isalpha():
            variable_name = 'var_' + variable_name
        
        # Exclude Python keywords
        python_keywords = {
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'false', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'none', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'true', 'try', 'while', 'with', 'yield'
        }
        assume(variable_name.lower() not in python_keywords)
        
        # Create Python code that references undefined variable
        code = f"""
def transform(inputs):
    return {{"result": {variable_name}}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail for undefined variable"
        
        # Property: Stack trace should be present
        assert result.stack_trace is not None, \
            f"Stack trace should be present"
        
        # Property: Error should mention NameError
        error_text = (result.error or "") + (result.stack_trace or "") + (result.stderr or "")
        assert "NameError" in error_text, \
            f"Error should mention NameError.\n" \
            f"Error text: {error_text}"
        
        # Property: Variable name should be in error message
        assert variable_name in error_text, \
            f"Variable name '{variable_name}' should be in error message.\n" \
            f"Error text: {error_text}"
    
    @settings(max_examples=50, deadline=500)
    @given(
        variable_name=st.text(
            min_size=3,
            max_size=20,
            alphabet='abcdefghijklmnopqrstuvwxyz_'
        )
    )
    def test_javascript_undefined_variable_error_reporting(self, variable_name):
        """
        Property 11: Code node error reporting (JavaScript - undefined variables)
        
        For any JavaScript code that references undefined variables, the system
        should provide clear error messages with the variable name.
        
        This property verifies that:
        1. ReferenceError is properly reported
        2. Variable name is included in error message
        3. Error information is complete
        
        Validates: Requirements 10.7
        """
        # Ensure variable name starts with a letter
        if not variable_name[0].isalpha():
            variable_name = 'var_' + variable_name
        
        # Exclude JavaScript keywords and literals
        js_keywords = {
            'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
            'default', 'delete', 'do', 'else', 'export', 'extends', 'false',
            'finally', 'for', 'function', 'if', 'import', 'in', 'instanceof',
            'let', 'new', 'null', 'return', 'super', 'switch', 'this', 'throw',
            'true', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield',
            'undefined', 'nan', 'infinity'
        }
        assume(variable_name.lower() not in js_keywords)
        
        # Create JavaScript code that references undefined variable
        code = f"""
module.exports = (inputs) => {{
    return {{result: {variable_name}}};
}};
"""
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail for undefined variable"
        
        # Property: Error information should be present
        has_error_info = (
            (result.error is not None and result.error.strip()) or
            (result.stack_trace is not None and result.stack_trace.strip()) or
            (result.stderr is not None and result.stderr.strip())
        )
        assert has_error_info, \
            f"Error information should be present"
        
        # Property: Error should mention ReferenceError or indicate undefined
        error_text = (result.error or "") + (result.stack_trace or "") + (result.stderr or "")
        has_reference_error = (
            "ReferenceError" in error_text or
            "not defined" in error_text or
            "undefined" in error_text.lower()
        )
        assert has_reference_error, \
            f"Error should mention ReferenceError or undefined.\n" \
            f"Error text: {error_text}"
        
        # Property: Variable name should be in error message
        assert variable_name in error_text, \
            f"Variable name '{variable_name}' should be in error message.\n" \
            f"Error text: {error_text}"
    
    @settings(max_examples=50)
    @given(
        divisor=st.just(0)  # Always divide by zero
    )
    def test_python_runtime_error_with_context(self, divisor):
        """
        Property 11: Code node error reporting (Python - runtime errors with context)
        
        For any Python code that encounters runtime errors (like division by zero),
        the system should provide detailed context about the error.
        
        This property verifies that:
        1. Runtime errors are properly captured
        2. Error type is clearly indicated
        3. Stack trace provides context
        
        Validates: Requirements 10.7
        """
        # Create Python code that divides by zero
        code = f"""
def transform(inputs):
    numerator = 100
    denominator = {divisor}
    result = numerator / denominator
    return {{"result": result}}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail for division by zero"
        
        # Property: Stack trace should be present
        assert result.stack_trace is not None, \
            f"Stack trace should be present"
        
        # Property: Error should mention ZeroDivisionError
        error_text = (result.error or "") + (result.stack_trace or "") + (result.stderr or "")
        assert "ZeroDivisionError" in error_text, \
            f"Error should mention ZeroDivisionError.\n" \
            f"Error text: {error_text}"
        
        # Property: Stack trace should contain function name
        assert "transform" in result.stack_trace or "transform" in result.stderr, \
            f"Stack trace should contain function context"
    
    @settings(max_examples=50)
    @given(
        nested_level=st.integers(min_value=2, max_value=5)
    )
    def test_python_nested_error_stack_trace(self, nested_level):
        """
        Property 11: Code node error reporting (Python - nested call stacks)
        
        For any Python code with nested function calls that fail, the stack
        trace should show the complete call chain.
        
        This property verifies that:
        1. Full call stack is preserved
        2. All function levels are shown
        3. Error propagation is traceable
        
        Validates: Requirements 10.7
        """
        # Create nested function calls
        functions = []
        for i in range(nested_level):
            if i == nested_level - 1:
                # Last function raises error
                func = f"""
def level_{i}():
    raise RuntimeError("Error at level {i}")
"""
            else:
                # Intermediate functions call next level
                func = f"""
def level_{i}():
    return level_{i+1}()
"""
            functions.append(func)
        
        code = "\n".join(functions) + """
def transform(inputs):
    return {"result": level_0()}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=10)
        
        # Property: Execution should fail
        assert not result.success, \
            f"Execution should fail"
        
        # Property: Stack trace should be present
        assert result.stack_trace is not None, \
            f"Stack trace should be present"
        
        # Property: Stack trace should contain multiple function levels
        # At least some of the nested functions should appear
        error_text = result.stack_trace + (result.stderr or "")
        level_count = sum(1 for i in range(nested_level) if f"level_{i}" in error_text)
        
        assert level_count >= 2, \
            f"Stack trace should show nested function calls.\n" \
            f"Expected at least 2 levels, found {level_count}\n" \
            f"Stack trace: {result.stack_trace}"
