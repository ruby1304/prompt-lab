"""
Unit tests for CodeExecutor

Tests the core functionality of code execution including:
- JavaScript execution
- Python execution
- Input/output handling
- Timeout control
- Error handling
"""

import pytest
import json
from pathlib import Path
from src.code_executor import CodeExecutor, ExecutionResult


class TestCodeExecutor:
    """Test suite for CodeExecutor"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=5)
    
    # Basic JavaScript execution tests
    
    def test_javascript_simple_function(self):
        """Test executing a simple JavaScript function"""
        code = """
        function transform(inputs) {
            return { result: inputs.value * 2 };
        }
        module.exports = transform;
        """
        
        inputs = {"value": 21}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert result.success
        assert result.output == {"result": 42}
        assert result.error is None
        assert not result.timeout
    
    def test_javascript_arrow_function(self):
        """Test executing JavaScript with arrow function"""
        code = """
        module.exports = (inputs) => {
            return { doubled: inputs.x * 2, tripled: inputs.x * 3 };
        };
        """
        
        inputs = {"x": 10}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert result.success
        assert result.output == {"doubled": 20, "tripled": 30}
    
    def test_javascript_async_function(self):
        """Test executing async JavaScript function"""
        code = """
        module.exports = async (inputs) => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({ message: inputs.text.toUpperCase() });
                }, 100);
            });
        };
        """
        
        inputs = {"text": "hello"}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert result.success
        assert result.output == {"message": "HELLO"}
    
    def test_javascript_array_processing(self):
        """Test JavaScript array processing"""
        code = """
        function transform(inputs) {
            return {
                items: inputs.items.map(x => x * 2),
                sum: inputs.items.reduce((a, b) => a + b, 0)
            };
        }
        module.exports = transform;
        """
        
        inputs = {"items": [1, 2, 3, 4, 5]}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert result.success
        assert result.output["items"] == [2, 4, 6, 8, 10]
        assert result.output["sum"] == 15
    
    # Basic Python execution tests
    
    def test_python_simple_function(self):
        """Test executing a simple Python function"""
        code = """
def transform(inputs):
    return {"result": inputs["value"] * 2}
"""
        
        inputs = {"value": 21}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert result.success
        assert result.output == {"result": 42}
        assert result.error is None
        assert not result.timeout
    
    def test_python_list_comprehension(self):
        """Test Python with list comprehension"""
        code = """
def transform(inputs):
    return {
        "doubled": [x * 2 for x in inputs["numbers"]],
        "sum": sum(inputs["numbers"])
    }
"""
        
        inputs = {"numbers": [1, 2, 3, 4, 5]}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert result.success
        assert result.output["doubled"] == [2, 4, 6, 8, 10]
        assert result.output["sum"] == 15
    
    def test_python_string_processing(self):
        """Test Python string processing"""
        code = """
def process_data(inputs):
    text = inputs["text"]
    return {
        "upper": text.upper(),
        "lower": text.lower(),
        "length": len(text)
    }
"""
        
        inputs = {"text": "Hello World"}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert result.success
        assert result.output["upper"] == "HELLO WORLD"
        assert result.output["lower"] == "hello world"
        assert result.output["length"] == 11
    
    # Input/output handling tests
    
    def test_javascript_complex_input(self):
        """Test JavaScript with complex nested input"""
        code = """
        module.exports = (inputs) => {
            return {
                user: inputs.user.name,
                total: inputs.items.reduce((sum, item) => sum + item.price, 0)
            };
        };
        """
        
        inputs = {
            "user": {"name": "Alice", "id": 123},
            "items": [
                {"name": "item1", "price": 10},
                {"name": "item2", "price": 20}
            ]
        }
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert result.success
        assert result.output["user"] == "Alice"
        assert result.output["total"] == 30
    
    def test_python_complex_input(self):
        """Test Python with complex nested input"""
        code = """
def main(inputs):
    return {
        "user": inputs["user"]["name"],
        "total": sum(item["price"] for item in inputs["items"])
    }
"""
        
        inputs = {
            "user": {"name": "Bob", "id": 456},
            "items": [
                {"name": "item1", "price": 15},
                {"name": "item2", "price": 25}
            ]
        }
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert result.success
        assert result.output["user"] == "Bob"
        assert result.output["total"] == 40
    
    # Timeout tests
    
    def test_javascript_timeout(self):
        """Test JavaScript execution timeout"""
        code = """
        module.exports = (inputs) => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({ done: true });
                }, 10000);  // 10 seconds - will timeout
            });
        };
        """
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=1)
        
        assert not result.success
        assert result.timeout
        assert "timed out" in result.error.lower()
    
    def test_python_timeout(self):
        """Test Python execution timeout"""
        code = """
import time

def transform(inputs):
    time.sleep(10)  # 10 seconds - will timeout
    return {"done": True}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=1)
        
        assert not result.success
        assert result.timeout
        assert "timed out" in result.error.lower()
    
    # Error handling tests
    
    def test_javascript_syntax_error(self):
        """Test JavaScript syntax error handling"""
        code = """
        module.exports = (inputs) => {
            return { result: inputs.value * 2  // Missing closing brace
        };
        """
        
        inputs = {"value": 10}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert not result.success
        assert result.error is not None
        assert result.stderr is not None
    
    def test_python_syntax_error(self):
        """Test Python syntax error handling"""
        code = """
def transform(inputs):
    return {"result": inputs["value"] * 2  # Missing closing brace
"""
        
        inputs = {"value": 10}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert not result.success
        assert result.error is not None
    
    def test_javascript_runtime_error(self):
        """Test JavaScript runtime error handling"""
        code = """
        module.exports = (inputs) => {
            return { result: inputs.nonexistent.value };
        };
        """
        
        inputs = {"value": 10}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert not result.success
        assert result.error is not None
    
    def test_python_runtime_error(self):
        """Test Python runtime error handling"""
        code = """
def transform(inputs):
    return {"result": inputs["nonexistent"]["value"]}
"""
        
        inputs = {"value": 10}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert not result.success
        assert result.error is not None
    
    # Generic execute method tests
    
    def test_execute_javascript_via_generic_method(self):
        """Test executing JavaScript via generic execute method"""
        code = """
        module.exports = (inputs) => ({ result: inputs.x + inputs.y });
        """
        
        inputs = {"x": 10, "y": 20}
        result = self.executor.execute(code, "javascript", inputs, timeout=5)
        
        assert result.success
        assert result.output == {"result": 30}
    
    def test_execute_python_via_generic_method(self):
        """Test executing Python via generic execute method"""
        code = """
def transform(inputs):
    return {"result": inputs["x"] + inputs["y"]}
"""
        
        inputs = {"x": 10, "y": 20}
        result = self.executor.execute(code, "python", inputs, timeout=5)
        
        assert result.success
        assert result.output == {"result": 30}
    
    def test_execute_unsupported_language(self):
        """Test executing unsupported language"""
        code = "print('hello')"
        inputs = {}
        result = self.executor.execute(code, "ruby", inputs, timeout=5)
        
        assert not result.success
        assert "Unsupported language" in result.error
    
    # File execution tests
    
    def test_execute_from_file_javascript(self, tmp_path):
        """Test executing JavaScript from file"""
        code_file = tmp_path / "test.js"
        code_file.write_text("""
        module.exports = (inputs) => ({ result: inputs.value * 3 });
        """)
        
        inputs = {"value": 7}
        result = self.executor.execute_from_file(code_file, "javascript", inputs, timeout=5)
        
        assert result.success
        assert result.output == {"result": 21}
    
    def test_execute_from_file_python(self, tmp_path):
        """Test executing Python from file"""
        code_file = tmp_path / "test.py"
        code_file.write_text("""
def transform(inputs):
    return {"result": inputs["value"] * 3}
""")
        
        inputs = {"value": 7}
        result = self.executor.execute_from_file(code_file, "python", inputs, timeout=5)
        
        assert result.success
        assert result.output == {"result": 21}
    
    def test_execute_from_nonexistent_file(self):
        """Test executing from nonexistent file"""
        result = self.executor.execute_from_file(
            Path("/nonexistent/file.js"),
            "javascript",
            {},
            timeout=5
        )
        
        assert not result.success
        assert "not found" in result.error.lower()
    
    # ExecutionResult tests
    
    def test_execution_result_to_dict(self):
        """Test ExecutionResult to_dict conversion"""
        result = ExecutionResult(
            success=True,
            output={"key": "value"},
            error=None,
            stderr=None,
            execution_time=1.5,
            timeout=False
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["output"] == {"key": "value"}
        assert result_dict["execution_time"] == 1.5
        assert result_dict["timeout"] is False
    
    def test_execution_result_from_dict(self):
        """Test ExecutionResult from_dict conversion"""
        data = {
            "success": False,
            "output": None,
            "error": "Test error",
            "stderr": "Test stderr",
            "execution_time": 2.5,
            "timeout": True
        }
        
        result = ExecutionResult.from_dict(data)
        
        assert result.success is False
        assert result.output is None
        assert result.error == "Test error"
        assert result.stderr == "Test stderr"
        assert result.execution_time == 2.5
        assert result.timeout is True
    
    # Edge cases
    
    def test_empty_inputs(self):
        """Test execution with empty inputs"""
        code = """
        module.exports = (inputs) => ({ count: Object.keys(inputs).length });
        """
        
        result = self.executor.execute_javascript(code, {}, timeout=5)
        
        assert result.success
        assert result.output == {"count": 0}
    
    def test_execution_time_tracking(self):
        """Test that execution time is tracked"""
        code = """
        module.exports = (inputs) => {
            return new Promise((resolve) => {
                setTimeout(() => resolve({ done: true }), 100);
            });
        };
        """
        
        result = self.executor.execute_javascript(code, {}, timeout=5)
        
        assert result.success
        assert result.execution_time > 0.1  # Should take at least 100ms
        assert result.execution_time < 5.0  # Should not timeout
