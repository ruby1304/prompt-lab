"""Error handling and recovery mechanisms for Agent Template Parser."""

import json
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

from .template_parser import TemplateParsingError
from .config_generator import ConfigGenerationError
from .llm_enhancer import LLMEnhancementError


class BatchProcessingError(Exception):
    """Exception raised during batch processing operations."""
    
    def __init__(self, message: str, failed_items: Optional[List[str]] = None):
        super().__init__(message)
        self.failed_items = failed_items or []


class FileOperationError(Exception):
    """Exception raised during file operations."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        super().__init__(message)
        self.file_path = file_path


class ValidationError(Exception):
    """Exception raised during validation operations."""
    
    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        super().__init__(message)
        self.validation_errors = validation_errors or []


class InvalidFolderStructureError(Exception):
    """Exception raised when agent folder exists but missing required files."""
    
    def __init__(self, message: str, agent_name: str, missing_files: Optional[List[str]] = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.missing_files = missing_files or []


class MissingAgentFolderError(Exception):
    """Exception raised when specified agent folder doesn't exist."""
    
    def __init__(self, message: str, agent_name: str, expected_path: Optional[str] = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.expected_path = expected_path


class AmbiguousTemplateStructureError(Exception):
    """Exception raised when both folder and legacy structures exist."""
    
    def __init__(self, message: str, agent_name: str, conflicting_paths: Optional[List[str]] = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.conflicting_paths = conflicting_paths or []


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    agent_name: Optional[str] = None
    file_path: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
    success: bool
    recovered_data: Optional[Dict[str, Any]] = None
    fallback_used: bool = False
    warnings: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None


class ErrorRecovery:
    """Error recovery and handling mechanisms."""
    
    def __init__(self):
        self.recovery_strategies = {
            TemplateParsingError: self._recover_from_parsing_error,
            ConfigGenerationError: self._recover_from_config_error,
            LLMEnhancementError: self._recover_from_llm_error,
            BatchProcessingError: self._recover_from_batch_error,
            FileOperationError: self._recover_from_file_error,
            ValidationError: self._recover_from_validation_error,
            json.JSONDecodeError: self._recover_from_json_error
        }
    
    def handle_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Handle an error and attempt recovery.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            
        Returns:
            RecoveryResult with recovery information
        """
        error_type = type(error)
        context.error_type = error_type.__name__
        context.stack_trace = traceback.format_exc()
        
        # Try specific recovery strategy
        if error_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[error_type](error, context)
            except Exception as recovery_error:
                # Recovery itself failed, return generic failure
                return RecoveryResult(
                    success=False,
                    warnings=[f"Recovery strategy failed: {recovery_error}"],
                    suggestions=self._get_generic_suggestions(error, context)
                )
        
        # No specific strategy, return generic handling
        return self._handle_generic_error(error, context)
    
    def _recover_from_parsing_error(
        self, 
        error: TemplateParsingError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from template parsing errors."""
        suggestions = []
        warnings = []
        
        error_msg = str(error).lower()
        
        if "variable" in error_msg:
            suggestions.extend([
                "Check that all variables use the correct ${} format",
                "Ensure variable names are valid identifiers",
                "Verify that special variables like {user} and {role} are preserved"
            ])
        
        if "json" in error_msg:
            suggestions.extend([
                "Validate JSON syntax in test case files",
                "Check for missing commas or brackets",
                "Ensure proper string escaping"
            ])
        
        if "encoding" in error_msg:
            suggestions.extend([
                "Check file encoding (should be UTF-8)",
                "Look for special characters that might cause issues"
            ])
        
        # Try to create a minimal fallback template
        fallback_data = None
        if context.agent_name:
            fallback_data = self._create_fallback_template(context.agent_name)
            warnings.append("Using fallback template due to parsing error")
        
        return RecoveryResult(
            success=fallback_data is not None,
            recovered_data=fallback_data,
            fallback_used=True,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _recover_from_config_error(
        self, 
        error: ConfigGenerationError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from configuration generation errors."""
        suggestions = [
            "Check that all required template fields are present",
            "Verify variable mappings are correct",
            "Ensure agent name follows naming conventions",
            "Try using LLM enhancement to fix format issues"
        ]
        
        # Try to create a basic config structure
        fallback_config = None
        if context.agent_name:
            fallback_config = self._create_basic_config(context.agent_name)
        
        return RecoveryResult(
            success=fallback_config is not None,
            recovered_data=fallback_config,
            fallback_used=True,
            warnings=["Using basic configuration template"],
            suggestions=suggestions
        )
    
    def _recover_from_llm_error(
        self, 
        error: LLMEnhancementError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from LLM enhancement errors."""
        suggestions = [
            "Check your OpenAI API key configuration",
            "Verify internet connectivity",
            "Try again later if the service is temporarily unavailable",
            "Consider using the --no-llm-enhancement flag as fallback"
        ]
        
        warnings = [
            "LLM enhancement failed, proceeding with basic configuration",
            "Generated configuration may need manual review"
        ]
        
        return RecoveryResult(
            success=True,  # Can continue without LLM enhancement
            recovered_data=context.input_data,  # Use original data
            fallback_used=True,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _recover_from_batch_error(
        self, 
        error: BatchProcessingError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from batch processing errors."""
        suggestions = [
            "Check that all JSON files have valid format",
            "Verify target agent exists",
            "Ensure sufficient disk space for output files",
            "Try processing files individually to identify problematic ones"
        ]
        
        warnings = []
        if hasattr(error, 'failed_items') and error.failed_items:
            warnings.append(f"Failed to process {len(error.failed_items)} items")
            suggestions.append(f"Review failed items: {', '.join(error.failed_items[:5])}")
        
        return RecoveryResult(
            success=False,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _recover_from_file_error(
        self, 
        error: FileOperationError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from file operation errors."""
        suggestions = []
        
        error_msg = str(error).lower()
        
        if "permission" in error_msg:
            suggestions.extend([
                "Check file and directory permissions",
                "Ensure you have write access to the target directory",
                "Try running with appropriate permissions"
            ])
        
        if "not found" in error_msg:
            suggestions.extend([
                "Verify file paths are correct",
                "Check that input files exist",
                "Ensure directory structure is properly created"
            ])
        
        if "space" in error_msg:
            suggestions.extend([
                "Check available disk space",
                "Clean up temporary files",
                "Choose a different output location"
            ])
        
        # Try to create directory if it doesn't exist
        recovery_success = False
        if hasattr(error, 'file_path') and error.file_path:
            try:
                file_path = Path(error.file_path)
                if not file_path.parent.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    recovery_success = True
            except Exception:
                pass
        
        return RecoveryResult(
            success=recovery_success,
            warnings=["Attempted to create missing directories"] if recovery_success else [],
            suggestions=suggestions
        )
    
    def _recover_from_validation_error(
        self, 
        error: ValidationError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from validation errors."""
        suggestions = [
            "Review the validation errors and fix the issues",
            "Check configuration format against project standards",
            "Use LLM enhancement to automatically fix format issues"
        ]
        
        if hasattr(error, 'validation_errors') and error.validation_errors:
            suggestions.append("Specific validation issues:")
            suggestions.extend([f"  - {err}" for err in error.validation_errors[:5]])
        
        return RecoveryResult(
            success=False,
            suggestions=suggestions
        )
    
    def _recover_from_json_error(
        self, 
        error: json.JSONDecodeError, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Recover from JSON parsing errors."""
        suggestions = [
            f"JSON syntax error at line {error.lineno}, column {error.colno}",
            "Check for missing commas, brackets, or quotes",
            "Validate JSON format using a JSON validator",
            "Ensure proper escaping of special characters"
        ]
        
        # Try to suggest specific fixes based on error message
        if "Expecting ',' delimiter" in str(error):
            suggestions.append("Add missing comma between JSON elements")
        elif "Expecting ':' delimiter" in str(error):
            suggestions.append("Add missing colon after JSON key")
        elif "Unterminated string" in str(error):
            suggestions.append("Close unterminated string with quote")
        
        return RecoveryResult(
            success=False,
            suggestions=suggestions
        )
    
    def _handle_generic_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> RecoveryResult:
        """Handle generic errors without specific recovery strategy."""
        suggestions = [
            f"Unexpected error of type {type(error).__name__}",
            "Check the error message for specific details",
            "Verify input data and file formats",
            "Try the operation again with different parameters"
        ]
        
        return RecoveryResult(
            success=False,
            suggestions=suggestions
        )
    
    def _create_fallback_template(self, agent_name: str) -> Dict[str, Any]:
        """Create a minimal fallback template structure."""
        return {
            'system_prompt': {
                'content': f"You are {agent_name}, a helpful AI assistant.",
                'variables': []
            },
            'user_input': {
                'content': "Please help me with: {{user_input}}",
                'variables': ['user_input']
            },
            'test_case': {
                'structure': {
                    'user_input': 'string'
                }
            },
            'agent_name': agent_name
        }
    
    def _create_basic_config(self, agent_name: str) -> Dict[str, Any]:
        """Create a basic configuration structure."""
        return {
            'agent_config': {
                'name': agent_name,
                'flows': {
                    'default': {
                        'prompt': f'{agent_name}_v1'
                        # 不指定model，使用系统默认配置
                    }
                },
                'evaluation': {
                    'case_fields': ['user_input'],
                    'output_field': 'response'
                }
            },
            'prompt_config': {
                'system_prompt': f"You are {agent_name}, a helpful AI assistant.",
                'user_template': "{{user_input}}",
                'defaults': {}
            }
        }
    
    def _get_generic_suggestions(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> List[str]:
        """Get generic suggestions for any error."""
        return [
            "Check input data format and validity",
            "Verify file paths and permissions",
            "Review error message for specific details",
            "Try with simpler input to isolate the issue",
            "Check system requirements and dependencies"
        ]
    
    def suggest_fixes(self, errors: List[str]) -> List[str]:
        """Generate fix suggestions for a list of errors.
        
        Args:
            errors: List of error messages
            
        Returns:
            List of suggested fixes
        """
        suggestions = []
        
        for error in errors:
            error_lower = error.lower()
            
            if "yaml" in error_lower or "format" in error_lower:
                suggestions.append("Check YAML syntax and indentation")
            
            if "variable" in error_lower:
                suggestions.append("Verify variable names and format")
            
            if "required" in error_lower or "missing" in error_lower:
                suggestions.append("Add missing required fields")
            
            if "type" in error_lower:
                suggestions.append("Check data types match expected format")
            
            if "path" in error_lower or "file" in error_lower:
                suggestions.append("Verify file paths and directory structure")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions or ["Review error messages and check input data"]


def create_error_context(
    operation: str,
    agent_name: Optional[str] = None,
    file_path: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None
) -> ErrorContext:
    """Create an error context for error handling.
    
    Args:
        operation: Description of the operation being performed
        agent_name: Name of the agent being processed
        file_path: Path of the file being processed
        input_data: Input data being processed
        
    Returns:
        ErrorContext instance
    """
    return ErrorContext(
        operation=operation,
        agent_name=agent_name,
        file_path=file_path,
        input_data=input_data
    )


def handle_error_with_recovery(
    error: Exception,
    context: ErrorContext,
    recovery_handler: Optional[ErrorRecovery] = None
) -> RecoveryResult:
    """Handle an error with recovery attempt.
    
    Args:
        error: The exception that occurred
        context: Context information about the error
        recovery_handler: Optional custom recovery handler
        
    Returns:
        RecoveryResult with recovery information
    """
    if recovery_handler is None:
        recovery_handler = ErrorRecovery()
    
    return recovery_handler.handle_error(error, context)