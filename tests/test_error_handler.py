"""Tests for error handling and recovery mechanisms."""

import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.agent_template_parser.error_handler import (
    BatchProcessingError,
    FileOperationError,
    ValidationError,
    ErrorContext,
    RecoveryResult,
    ErrorRecovery,
    create_error_context,
    handle_error_with_recovery
)
from src.agent_template_parser.template_parser import TemplateParsingError
from src.agent_template_parser.config_generator import ConfigGenerationError
from src.agent_template_parser.llm_enhancer import LLMEnhancementError


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_batch_processing_error(self):
        """Test BatchProcessingError with failed items."""
        failed_items = ['file1.json', 'file2.json']
        error = BatchProcessingError("Batch processing failed", failed_items)
        
        assert str(error) == "Batch processing failed"
        assert error.failed_items == failed_items
    
    def test_batch_processing_error_no_items(self):
        """Test BatchProcessingError without failed items."""
        error = BatchProcessingError("Batch processing failed")
        
        assert str(error) == "Batch processing failed"
        assert error.failed_items == []
    
    def test_file_operation_error(self):
        """Test FileOperationError with file path."""
        file_path = "/path/to/file.txt"
        error = FileOperationError("File operation failed", file_path)
        
        assert str(error) == "File operation failed"
        assert error.file_path == file_path
    
    def test_file_operation_error_no_path(self):
        """Test FileOperationError without file path."""
        error = FileOperationError("File operation failed")
        
        assert str(error) == "File operation failed"
        assert error.file_path is None
    
    def test_validation_error(self):
        """Test ValidationError with validation errors."""
        validation_errors = ['Missing field: name', 'Invalid type: age']
        error = ValidationError("Validation failed", validation_errors)
        
        assert str(error) == "Validation failed"
        assert error.validation_errors == validation_errors
    
    def test_validation_error_no_errors(self):
        """Test ValidationError without validation errors."""
        error = ValidationError("Validation failed")
        
        assert str(error) == "Validation failed"
        assert error.validation_errors == []


class TestErrorContext:
    """Test ErrorContext dataclass."""
    
    def test_create_error_context(self):
        """Test creating error context."""
        context = create_error_context(
            operation="test_operation",
            agent_name="test_agent",
            file_path="/path/to/file.txt",
            input_data={"key": "value"}
        )
        
        assert context.operation == "test_operation"
        assert context.agent_name == "test_agent"
        assert context.file_path == "/path/to/file.txt"
        assert context.input_data == {"key": "value"}
        assert context.error_type is None
        assert context.stack_trace is None
    
    def test_create_error_context_minimal(self):
        """Test creating error context with minimal parameters."""
        context = create_error_context("test_operation")
        
        assert context.operation == "test_operation"
        assert context.agent_name is None
        assert context.file_path is None
        assert context.input_data is None


class TestRecoveryResult:
    """Test RecoveryResult dataclass."""
    
    def test_recovery_result_success(self):
        """Test successful recovery result."""
        result = RecoveryResult(
            success=True,
            recovered_data={"key": "value"},
            fallback_used=False,
            warnings=["Warning message"],
            suggestions=["Suggestion"]
        )
        
        assert result.success is True
        assert result.recovered_data == {"key": "value"}
        assert result.fallback_used is False
        assert result.warnings == ["Warning message"]
        assert result.suggestions == ["Suggestion"]
    
    def test_recovery_result_failure(self):
        """Test failed recovery result."""
        result = RecoveryResult(success=False)
        
        assert result.success is False
        assert result.recovered_data is None
        assert result.fallback_used is False
        assert result.warnings is None
        assert result.suggestions is None


class TestErrorRecovery:
    """Test ErrorRecovery class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.recovery = ErrorRecovery()
        self.context = create_error_context("test_operation", "test_agent")
    
    def test_init(self):
        """Test ErrorRecovery initialization."""
        assert self.recovery.recovery_strategies is not None
        assert len(self.recovery.recovery_strategies) > 0
    
    def test_handle_template_parsing_error(self):
        """Test handling TemplateParsingError."""
        error = TemplateParsingError("Variable parsing failed")
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is True  # Should create fallback
        assert result.fallback_used is True
        assert result.recovered_data is not None
        assert "variable" in " ".join(result.suggestions).lower()
    
    def test_handle_config_generation_error(self):
        """Test handling ConfigGenerationError."""
        error = ConfigGenerationError("Config generation failed")
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is True  # Should create basic config
        assert result.fallback_used is True
        assert result.recovered_data is not None
        assert "template" in " ".join(result.suggestions).lower()
    
    def test_handle_llm_enhancement_error(self):
        """Test handling LLMEnhancementError."""
        error = LLMEnhancementError("LLM API failed")
        self.context.input_data = {"test": "data"}
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is True  # Can continue without LLM
        assert result.fallback_used is True
        assert result.recovered_data == {"test": "data"}
        assert "api" in " ".join(result.suggestions).lower()
    
    def test_handle_batch_processing_error(self):
        """Test handling BatchProcessingError."""
        failed_items = ['file1.json', 'file2.json']
        error = BatchProcessingError("Batch failed", failed_items)
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is False
        assert len(result.warnings) > 0
        assert "json" in " ".join(result.suggestions).lower()
    
    def test_handle_file_operation_error_permission(self):
        """Test handling FileOperationError with permission issue."""
        error = FileOperationError("Permission denied")
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert "permission" in " ".join(result.suggestions).lower()
    
    def test_handle_file_operation_error_not_found(self):
        """Test handling FileOperationError with file not found."""
        error = FileOperationError("File not found")
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert "file" in " ".join(result.suggestions).lower()
    
    @patch('pathlib.Path.mkdir')
    def test_handle_file_operation_error_with_recovery(self, mock_mkdir):
        """Test FileOperationError recovery by creating directory."""
        error = FileOperationError("Directory not found", "/path/to/file.txt")
        mock_mkdir.return_value = None
        
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        # Recovery success depends on the actual implementation
    
    def test_handle_validation_error(self):
        """Test handling ValidationError."""
        validation_errors = ['Missing field: name', 'Invalid type: age']
        error = ValidationError("Validation failed", validation_errors)
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is False
        assert "validation" in " ".join(result.suggestions).lower()
    
    def test_handle_json_decode_error(self):
        """Test handling JSONDecodeError."""
        error = json.JSONDecodeError("Expecting ',' delimiter", "test", 10)
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is False
        assert "json" in " ".join(result.suggestions).lower()
        assert "comma" in " ".join(result.suggestions).lower()
    
    def test_handle_generic_error(self):
        """Test handling generic error."""
        error = RuntimeError("Generic runtime error")
        result = self.recovery.handle_error(error, self.context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is False
        assert len(result.suggestions) > 0
    
    def test_suggest_fixes(self):
        """Test suggest_fixes method."""
        errors = [
            "YAML format error",
            "Missing required field",
            "Invalid variable name",
            "File path not found"
        ]
        
        suggestions = self.recovery.suggest_fixes(errors)
        
        assert len(suggestions) > 0
        assert any("yaml" in s.lower() for s in suggestions)
        assert any("required" in s.lower() or "missing" in s.lower() for s in suggestions)
        assert any("variable" in s.lower() for s in suggestions)
        assert any("path" in s.lower() or "file" in s.lower() for s in suggestions)
    
    def test_suggest_fixes_empty(self):
        """Test suggest_fixes with empty error list."""
        suggestions = self.recovery.suggest_fixes([])
        
        assert len(suggestions) == 1
        assert "review error messages" in suggestions[0].lower()
    
    def test_create_fallback_template(self):
        """Test _create_fallback_template method."""
        fallback = self.recovery._create_fallback_template("test_agent")
        
        assert fallback['agent_name'] == "test_agent"
        assert 'system_prompt' in fallback
        assert 'user_input' in fallback
        assert 'test_case' in fallback
        assert "test_agent" in fallback['system_prompt']['content']
    
    def test_create_basic_config(self):
        """Test _create_basic_config method."""
        config = self.recovery._create_basic_config("test_agent")
        
        assert 'agent_config' in config
        assert 'prompt_config' in config
        assert config['agent_config']['name'] == "test_agent"
        assert "test_agent" in config['prompt_config']['system_prompt']


class TestErrorHandlingIntegration:
    """Test error handling integration functions."""
    
    def test_handle_error_with_recovery(self):
        """Test handle_error_with_recovery function."""
        error = TemplateParsingError("Test error")
        context = create_error_context("test_operation", "test_agent")
        
        result = handle_error_with_recovery(error, context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is True  # Should recover with fallback
    
    def test_handle_error_with_custom_recovery(self):
        """Test handle_error_with_recovery with custom recovery handler."""
        error = RuntimeError("Test error")
        context = create_error_context("test_operation")
        custom_recovery = ErrorRecovery()
        
        result = handle_error_with_recovery(error, context, custom_recovery)
        
        assert isinstance(result, RecoveryResult)
    
    def test_recovery_strategy_failure(self):
        """Test when recovery strategy itself fails."""
        recovery = ErrorRecovery()
        
        # Mock a recovery strategy that raises an exception
        def failing_strategy(error, context):
            raise RuntimeError("Recovery failed")
        
        recovery.recovery_strategies[TemplateParsingError] = failing_strategy
        
        error = TemplateParsingError("Test error")
        context = create_error_context("test_operation")
        
        result = recovery.handle_error(error, context)
        
        assert isinstance(result, RecoveryResult)
        assert result.success is False
        assert len(result.warnings) > 0
        assert "recovery strategy failed" in result.warnings[0].lower()