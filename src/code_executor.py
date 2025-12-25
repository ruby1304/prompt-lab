"""
Code Node Executor

Provides execution capabilities for code nodes in pipelines.
Supports JavaScript (Node.js) and Python code execution with:
- Input/output handling
- Timeout control with process tree termination
- Detailed error capture and stack trace reporting
- Comprehensive resource cleanup
- Detailed logging
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
import logging
import traceback
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, List
import signal
import os

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class ExecutionResult:
    """
    Code execution result with detailed error information.
    
    Attributes:
        success: Whether execution completed successfully
        output: The output data from the code execution
        error: Error message if execution failed
        stderr: Standard error output from the process
        execution_time: Time taken for execution in seconds
        timeout: Whether execution was terminated due to timeout
        stack_trace: Detailed stack trace for errors (if available)
        exit_code: Process exit code (if available)
    """
    success: bool
    output: Any
    error: Optional[str] = None
    stderr: Optional[str] = None
    execution_time: float = 0.0
    timeout: bool = False
    stack_trace: Optional[str] = None
    exit_code: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "stderr": self.stderr,
            "execution_time": self.execution_time,
            "timeout": self.timeout,
            "stack_trace": self.stack_trace,
            "exit_code": self.exit_code
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionResult:
        """Create ExecutionResult from dictionary"""
        return cls(
            success=data.get("success", False),
            output=data.get("output"),
            error=data.get("error"),
            stderr=data.get("stderr"),
            execution_time=data.get("execution_time", 0.0),
            timeout=data.get("timeout", False),
            stack_trace=data.get("stack_trace"),
            exit_code=data.get("exit_code")
        )


class CodeExecutor:
    """
    Code node executor for JavaScript and Python code.
    
    Provides safe execution of code with:
    - Input parameter passing
    - Output capture
    - Timeout enforcement with process tree termination
    - Detailed error handling and stack trace reporting
    - Comprehensive resource cleanup
    """
    
    def __init__(self, default_timeout: int = 30):
        """
        Initialize CodeExecutor.
        
        Args:
            default_timeout: Default timeout in seconds for code execution
        """
        self.default_timeout = default_timeout
        logger.info(f"CodeExecutor initialized with default timeout: {default_timeout}s")
    
    def _terminate_process_tree(self, process: subprocess.Popen) -> None:
        """
        Terminate a process and all its child processes.
        
        This ensures complete cleanup when a timeout occurs, preventing
        orphaned processes from continuing to run.
        
        Args:
            process: The subprocess.Popen object to terminate
        """
        try:
            if PSUTIL_AVAILABLE:
                # Use psutil for comprehensive process tree termination
                try:
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    
                    # Terminate children first
                    for child in children:
                        try:
                            logger.debug(f"Terminating child process {child.pid}")
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    
                    # Terminate parent
                    logger.debug(f"Terminating parent process {process.pid}")
                    parent.terminate()
                    
                    # Wait for graceful termination
                    gone, alive = psutil.wait_procs(
                        [parent] + children, 
                        timeout=3
                    )
                    
                    # Force kill any remaining processes
                    for p in alive:
                        try:
                            logger.warning(f"Force killing process {p.pid}")
                            p.kill()
                        except psutil.NoSuchProcess:
                            pass
                            
                except psutil.NoSuchProcess:
                    logger.debug(f"Process {process.pid} already terminated")
            else:
                # Fallback to basic termination without psutil
                logger.debug(f"Terminating process {process.pid} (psutil not available)")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing process {process.pid}")
                    process.kill()
                    process.wait()
                    
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
            # Last resort: try to kill the process
            try:
                process.kill()
                process.wait()
            except Exception:
                pass
    
    def _cleanup_temp_file(self, temp_file: Path) -> None:
        """
        Safely clean up a temporary file.
        
        Args:
            temp_file: Path to the temporary file to delete
        """
        try:
            if temp_file.exists():
                temp_file.unlink()
                logger.debug(f"Cleaned up temporary file: {temp_file}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
    
    def _extract_stack_trace(self, stderr: str, language: str) -> Optional[str]:
        """
        Extract and format stack trace from stderr output.
        
        Args:
            stderr: Standard error output
            language: Programming language ("javascript" or "python")
            
        Returns:
            Formatted stack trace or None if not found
        """
        if not stderr:
            return None
        
        try:
            if language.lower() in ("python", "py"):
                # Python stack traces typically start with "Traceback"
                if "Traceback" in stderr:
                    return stderr
                    
            elif language.lower() in ("javascript", "js", "node"):
                # JavaScript stack traces typically contain "at " lines
                if "Error:" in stderr or "    at " in stderr:
                    return stderr
            
            # Return stderr as-is if it contains error information
            if stderr.strip():
                return stderr
                
        except Exception as e:
            logger.warning(f"Error extracting stack trace: {e}")
        
        return None
    
    def execute(
        self,
        code: str,
        language: str,
        inputs: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute code in the specified language.
        
        Args:
            code: Code to execute
            language: Programming language ("javascript" or "python")
            inputs: Input data to pass to the code
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            ExecutionResult with output or error information
        """
        if timeout is None:
            timeout = self.default_timeout
        
        if language.lower() in ("javascript", "js", "node"):
            return self.execute_javascript(code, inputs, timeout)
        elif language.lower() in ("python", "py"):
            return self.execute_python(code, inputs, timeout)
        else:
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Unsupported language: {language}. Supported: javascript, python"
            )
    
    def execute_javascript(
        self,
        code: str,
        inputs: Dict[str, Any],
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Execute JavaScript code using Node.js with comprehensive error handling.
        
        Args:
            code: JavaScript code to execute
            inputs: Input data to pass to the code
            timeout: Timeout in seconds
            
        Returns:
            ExecutionResult with output or detailed error information
        """
        start_time = time.time()
        temp_file = None
        process = None
        
        logger.info(f"Starting JavaScript execution (timeout: {timeout}s)")
        logger.debug(f"Input data: {inputs}")
        
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.js',
                delete=False,
                encoding='utf-8'
            ) as f:
                temp_file = Path(f.name)
                
                # Wrap the code to handle input/output
                wrapped_code = self._wrap_javascript_code(code, inputs)
                f.write(wrapped_code)
            
            logger.debug(f"Created temporary file: {temp_file}")
            
            try:
                # Execute the code using Node.js
                process = subprocess.Popen(
                    ['node', str(temp_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                logger.debug(f"Started Node.js process (PID: {process.pid})")
                
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    execution_time = time.time() - start_time
                    exit_code = process.returncode
                    
                    logger.info(f"JavaScript execution completed in {execution_time:.2f}s (exit code: {exit_code})")
                    
                    if exit_code == 0:
                        # Parse the output
                        try:
                            output = json.loads(stdout.strip())
                            logger.debug(f"Successfully parsed output: {type(output)}")
                            return ExecutionResult(
                                success=True,
                                output=output,
                                stderr=stderr if stderr else None,
                                execution_time=execution_time,
                                exit_code=exit_code
                            )
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON output: {e}")
                            stack_trace = self._extract_stack_trace(stderr, "javascript")
                            return ExecutionResult(
                                success=False,
                                output=None,
                                error=f"Failed to parse output as JSON: {e}",
                                stderr=stderr,
                                execution_time=execution_time,
                                stack_trace=stack_trace,
                                exit_code=exit_code
                            )
                    else:
                        logger.error(f"JavaScript execution failed with exit code {exit_code}")
                        stack_trace = self._extract_stack_trace(stderr, "javascript")
                        return ExecutionResult(
                            success=False,
                            output=None,
                            error=f"Code execution failed with exit code {exit_code}",
                            stderr=stderr,
                            execution_time=execution_time,
                            stack_trace=stack_trace,
                            exit_code=exit_code
                        )
                
                except subprocess.TimeoutExpired:
                    execution_time = time.time() - start_time
                    logger.warning(f"JavaScript execution timed out after {timeout}s")
                    
                    # Terminate the process tree
                    self._terminate_process_tree(process)
                    
                    # Try to get any partial output
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                    except:
                        stdout, stderr = "", ""
                    
                    return ExecutionResult(
                        success=False,
                        output=None,
                        error=f"Execution timed out after {timeout} seconds",
                        stderr=stderr if stderr else None,
                        timeout=True,
                        execution_time=execution_time,
                        exit_code=process.returncode if process.returncode is not None else -1
                    )
            
            finally:
                # Clean up temporary file
                if temp_file:
                    self._cleanup_temp_file(temp_file)
        
        except FileNotFoundError:
            logger.error("Node.js not found in system PATH")
            return ExecutionResult(
                success=False,
                output=None,
                error="Node.js not found. Please install Node.js to execute JavaScript code.",
                stack_trace="FileNotFoundError: 'node' command not found in PATH"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error during JavaScript execution: {e}", exc_info=True)
            
            # Capture full stack trace
            stack_trace = traceback.format_exc()
            
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Unexpected error during JavaScript execution: {str(e)}",
                execution_time=execution_time,
                stack_trace=stack_trace
            )
    
    def execute_python(
        self,
        code: str,
        inputs: Dict[str, Any],
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Execute Python code using subprocess with comprehensive error handling.
        
        Args:
            code: Python code to execute
            inputs: Input data to pass to the code
            timeout: Timeout in seconds
            
        Returns:
            ExecutionResult with output or detailed error information
        """
        start_time = time.time()
        temp_file = None
        process = None
        
        logger.info(f"Starting Python execution (timeout: {timeout}s)")
        logger.debug(f"Input data: {inputs}")
        
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as f:
                temp_file = Path(f.name)
                
                # Wrap the code to handle input/output
                wrapped_code = self._wrap_python_code(code, inputs)
                f.write(wrapped_code)
            
            logger.debug(f"Created temporary file: {temp_file}")
            
            try:
                # Execute the code using Python
                process = subprocess.Popen(
                    ['python', str(temp_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                logger.debug(f"Started Python process (PID: {process.pid})")
                
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    execution_time = time.time() - start_time
                    exit_code = process.returncode
                    
                    logger.info(f"Python execution completed in {execution_time:.2f}s (exit code: {exit_code})")
                    
                    if exit_code == 0:
                        # Parse the output
                        try:
                            output = json.loads(stdout.strip())
                            logger.debug(f"Successfully parsed output: {type(output)}")
                            return ExecutionResult(
                                success=True,
                                output=output,
                                stderr=stderr if stderr else None,
                                execution_time=execution_time,
                                exit_code=exit_code
                            )
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON output: {e}")
                            stack_trace = self._extract_stack_trace(stderr, "python")
                            return ExecutionResult(
                                success=False,
                                output=None,
                                error=f"Failed to parse output as JSON: {e}",
                                stderr=stderr,
                                execution_time=execution_time,
                                stack_trace=stack_trace,
                                exit_code=exit_code
                            )
                    else:
                        logger.error(f"Python execution failed with exit code {exit_code}")
                        stack_trace = self._extract_stack_trace(stderr, "python")
                        return ExecutionResult(
                            success=False,
                            output=None,
                            error=f"Code execution failed with exit code {exit_code}",
                            stderr=stderr,
                            execution_time=execution_time,
                            stack_trace=stack_trace,
                            exit_code=exit_code
                        )
                
                except subprocess.TimeoutExpired:
                    execution_time = time.time() - start_time
                    logger.warning(f"Python execution timed out after {timeout}s")
                    
                    # Terminate the process tree
                    self._terminate_process_tree(process)
                    
                    # Try to get any partial output
                    try:
                        stdout, stderr = process.communicate(timeout=1)
                    except:
                        stdout, stderr = "", ""
                    
                    return ExecutionResult(
                        success=False,
                        output=None,
                        error=f"Execution timed out after {timeout} seconds",
                        stderr=stderr if stderr else None,
                        timeout=True,
                        execution_time=execution_time,
                        exit_code=process.returncode if process.returncode is not None else -1
                    )
            
            finally:
                # Clean up temporary file
                if temp_file:
                    self._cleanup_temp_file(temp_file)
        
        except FileNotFoundError:
            logger.error("Python not found in system PATH")
            return ExecutionResult(
                success=False,
                output=None,
                error="Python not found. Please ensure Python is installed and in PATH.",
                stack_trace="FileNotFoundError: 'python' command not found in PATH"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Unexpected error during Python execution: {e}", exc_info=True)
            
            # Capture full stack trace
            stack_trace = traceback.format_exc()
            
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Unexpected error during Python execution: {str(e)}",
                execution_time=execution_time,
                stack_trace=stack_trace
            )
    
    def execute_from_file(
        self,
        file_path: Path,
        language: str,
        inputs: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Execute code from a file with error handling.
        
        Args:
            file_path: Path to the code file
            language: Programming language ("javascript" or "python")
            inputs: Input data to pass to the code
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            ExecutionResult with output or detailed error information
        """
        logger.info(f"Executing code from file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            logger.debug(f"Successfully read {len(code)} characters from {file_path}")
            return self.execute(code, language, inputs, timeout)
        
        except FileNotFoundError:
            logger.error(f"Code file not found: {file_path}")
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Code file not found: {file_path}",
                stack_trace=f"FileNotFoundError: {file_path}"
            )
        except PermissionError as e:
            logger.error(f"Permission denied reading file: {file_path}")
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Permission denied reading file: {file_path}",
                stack_trace=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to read code file: {e}", exc_info=True)
            stack_trace = traceback.format_exc()
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Failed to read code file: {str(e)}",
                stack_trace=stack_trace
            )
    
    def _wrap_javascript_code(self, code: str, inputs: Dict[str, Any]) -> str:
        """
        Wrap JavaScript code to handle input/output.
        
        Args:
            code: Original JavaScript code
            inputs: Input data
            
        Returns:
            Wrapped JavaScript code
        """
        inputs_json = json.dumps(inputs)
        
        return f"""
// Input data
const inputs = {inputs_json};

// User code
{code}

// Output handling
(async function() {{
    try {{
        let result;
        
        // Check if the code exports a function
        if (typeof module !== 'undefined' && module.exports) {{
            if (typeof module.exports === 'function') {{
                // Always pass full inputs object to module.exports
                result = await module.exports(inputs);
            }} else {{
                result = module.exports;
            }}
        }} else if (typeof exports !== 'undefined') {{
            if (typeof exports === 'function') {{
                result = await exports(inputs);
            }} else {{
                result = exports;
            }}
        }} else if (typeof aggregate === 'function') {{
            // For aggregate function, pass items directly (special case for batch aggregation)
            result = await aggregate(inputs.items !== undefined ? inputs.items : inputs);
        }} else if (typeof transform === 'function') {{
            result = await transform(inputs);
        }} else if (typeof process_data === 'function') {{
            result = await process_data(inputs);
        }} else if (typeof main === 'function') {{
            result = await main(inputs);
        }} else {{
            // If no function is exported, return the inputs as-is
            result = inputs;
        }}
        
        console.log(JSON.stringify(result));
    }} catch (error) {{
        console.error(error.message);
        process.exit(1);
    }}
}})();
"""
    
    def _wrap_python_code(self, code: str, inputs: Dict[str, Any]) -> str:
        """
        Wrap Python code to handle input/output.
        
        Args:
            code: Original Python code
            inputs: Input data
            
        Returns:
            Wrapped Python code
        """
        # Use repr() instead of json.dumps() to get valid Python literals
        # This ensures booleans are True/False, not true/false
        inputs_repr = repr(inputs)
        
        return f"""
import json
import sys
import traceback

# Input data
inputs = {inputs_repr}

# User code
{code}

# Output handling
try:
    result = None
    
    # Check if the code defines common function names
    # For aggregate function, pass items directly (special case for batch aggregation)
    if 'aggregate' in dir():
        result = aggregate(inputs.get('items', inputs))
    elif 'transform' in dir():
        result = transform(inputs)
    elif 'process_data' in dir():
        result = process_data(inputs)
    elif 'main' in dir():
        result = main(inputs)
    else:
        # If no function is defined, return the inputs as-is
        result = inputs
    
    print(json.dumps(result))
except Exception as e:
    # Print full traceback to stderr
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
