"""
Unit tests for CodeExecutor enhancements (Task 22)

Tests the enhanced functionality including:
- Process tree termination on timeout
- Detailed error stack trace capture
- Resource cleanup
- Logging
- Exit code tracking
"""

import pytest
import time
import tempfile
from pathlib import Path
from src.code_executor import CodeExecutor, ExecutionResult


class TestCodeExecutorEnhancements:
    """Test suite for CodeExecutor enhancements"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.executor = CodeExecutor(default_timeout=5)
    
    # Stack trace capture tests
    
    def test_javascript_stack_trace_on_error(self):
        """Test that JavaScript errors include stack traces"""
        code = """
        function causeError() {
            throw new Error("Test error message");
        }
        
        module.exports = (inputs) => {
            causeError();
            return { result: "should not reach here" };
        };
        """
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=5)
        
        assert not result.success
        assert result.error is not None
        assert result.stack_trace is not None
        assert "Error: Test error message" in result.stack_trace or "Test error message" in result.stderr
        assert result.exit_code != 0
    
    def test_python_stack_trace_on_error(self):
        """Test that Python errors include stack traces"""
        code = """
def cause_error():
    raise ValueError("Test error message")

def transform(inputs):
    cause_error()
    return {"result": "should not reach here"}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert not result.success
        assert result.error is not None
        assert result.stack_trace is not None
        assert "Traceback" in result.stack_trace or "ValueError" in result.stderr
        assert result.exit_code != 0
    
    def test_python_detailed_traceback(self):
        """Test that Python tracebacks include function names and line info"""
        code = """
def level_three():
    raise RuntimeError("Deep error")

def level_two():
    level_three()

def level_one():
    level_two()

def transform(inputs):
    level_one()
    return {}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert not result.success
        assert result.stack_trace is not None
        # Check that the stack trace includes function names
        assert "level_one" in result.stderr or "level_two" in result.stderr or "level_three" in result.stderr
    
    # Exit code tests
    
    def test_successful_execution_exit_code(self):
        """Test that successful execution has exit code 0"""
        code = """
def transform(inputs):
    return {"result": "success"}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert result.success
        assert result.exit_code == 0
    
    def test_failed_execution_exit_code(self):
        """Test that failed execution has non-zero exit code"""
        code = """
def transform(inputs):
    raise Exception("Failure")
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert not result.success
        assert result.exit_code != 0
    
    # Timeout and process termination tests
    
    def test_timeout_includes_exit_code(self):
        """Test that timeout results include exit code"""
        code = """
import time

def transform(inputs):
    time.sleep(10)
    return {"done": True}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=1)
        
        assert not result.success
        assert result.timeout
        assert result.exit_code is not None
    
    def test_javascript_timeout_process_cleanup(self):
        """Test that JavaScript timeout properly cleans up processes"""
        code = """
        module.exports = async (inputs) => {
            // Spawn child processes
            const { spawn } = require('child_process');
            const child = spawn('sleep', ['100']);
            
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({ done: true });
                }, 10000);
            });
        };
        """
        
        inputs = {}
        result = self.executor.execute_javascript(code, inputs, timeout=1)
        
        assert not result.success
        assert result.timeout
        # Process should be terminated
        # We can't easily verify process cleanup in unit tests,
        # but we verify the timeout was handled
    
    # Resource cleanup tests
    
    def test_temp_file_cleanup_on_success(self):
        """Test that temporary files are cleaned up after successful execution"""
        code = """
def transform(inputs):
    return {"result": "success"}
"""
        
        inputs = {}
        
        # Get temp directory before execution
        temp_dir = Path(tempfile.gettempdir())
        before_files = set(temp_dir.glob("tmp*.py"))
        
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        # Give a moment for cleanup
        time.sleep(0.1)
        
        after_files = set(temp_dir.glob("tmp*.py"))
        
        assert result.success
        # No new temp files should remain
        assert len(after_files - before_files) == 0
    
    def test_temp_file_cleanup_on_error(self):
        """Test that temporary files are cleaned up even after errors"""
        code = """
def transform(inputs):
    raise Exception("Error")
"""
        
        inputs = {}
        
        temp_dir = Path(tempfile.gettempdir())
        before_files = set(temp_dir.glob("tmp*.py"))
        
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        time.sleep(0.1)
        
        after_files = set(temp_dir.glob("tmp*.py"))
        
        assert not result.success
        # No new temp files should remain
        assert len(after_files - before_files) == 0
    
    def test_temp_file_cleanup_on_timeout(self):
        """Test that temporary files are cleaned up after timeout"""
        code = """
import time

def transform(inputs):
    time.sleep(10)
    return {}
"""
        
        inputs = {}
        
        temp_dir = Path(tempfile.gettempdir())
        before_files = set(temp_dir.glob("tmp*.py"))
        
        result = self.executor.execute_python(code, inputs, timeout=1)
        
        time.sleep(0.1)
        
        after_files = set(temp_dir.glob("tmp*.py"))
        
        assert result.timeout
        # No new temp files should remain
        assert len(after_files - before_files) == 0
    
    # File execution error handling tests
    
    def test_file_not_found_includes_stack_trace(self):
        """Test that file not found errors include stack trace"""
        result = self.executor.execute_from_file(
            Path("/nonexistent/file.py"),
            "python",
            {},
            timeout=5
        )
        
        assert not result.success
        assert "not found" in result.error.lower()
        assert result.stack_trace is not None
        assert "FileNotFoundError" in result.stack_trace
    
    def test_permission_error_handling(self):
        """Test handling of permission errors when reading files"""
        # Create a temporary file with no read permissions
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_file = Path(f.name)
            f.write("def transform(inputs): return {}")
        
        try:
            # Remove read permissions
            temp_file.chmod(0o000)
            
            result = self.executor.execute_from_file(
                temp_file,
                "python",
                {},
                timeout=5
            )
            
            assert not result.success
            assert "permission" in result.error.lower() or "denied" in result.error.lower()
        finally:
            # Restore permissions and clean up
            try:
                temp_file.chmod(0o644)
                temp_file.unlink()
            except:
                pass
    
    # ExecutionResult serialization tests with new fields
    
    def test_execution_result_to_dict_with_stack_trace(self):
        """Test ExecutionResult.to_dict includes stack_trace and exit_code"""
        result = ExecutionResult(
            success=False,
            output=None,
            error="Test error",
            stderr="Error output",
            execution_time=1.5,
            timeout=False,
            stack_trace="Traceback...",
            exit_code=1
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] == False
        assert result_dict["error"] == "Test error"
        assert result_dict["stack_trace"] == "Traceback..."
        assert result_dict["exit_code"] == 1
    
    def test_execution_result_from_dict_with_stack_trace(self):
        """Test ExecutionResult.from_dict handles stack_trace and exit_code"""
        data = {
            "success": False,
            "output": None,
            "error": "Test error",
            "stderr": "Error output",
            "execution_time": 1.5,
            "timeout": False,
            "stack_trace": "Traceback...",
            "exit_code": 1
        }
        
        result = ExecutionResult.from_dict(data)
        
        assert result.success == False
        assert result.error == "Test error"
        assert result.stack_trace == "Traceback..."
        assert result.exit_code == 1
    
    # Edge cases
    
    def test_empty_stderr_no_stack_trace(self):
        """Test that empty stderr doesn't create a stack trace"""
        code = """
def transform(inputs):
    return {"result": "success"}
"""
        
        inputs = {}
        result = self.executor.execute_python(code, inputs, timeout=5)
        
        assert result.success
        # Stack trace should be None for successful execution
        assert result.stack_trace is None or result.stack_trace == ""
    
    def test_execution_time_tracked_on_timeout(self):
        """Test that execution time is tracked even on timeout"""
        code = """
import time

def transform(inputs):
    time.sleep(10)
    return {}
"""
        
        inputs = {}
        start = time.time()
        result = self.executor.execute_python(code, inputs, timeout=1)
        elapsed = time.time() - start
        
        assert result.timeout
        assert result.execution_time > 0
        # Execution time should be close to timeout value
        assert 0.8 < result.execution_time < 2.0
