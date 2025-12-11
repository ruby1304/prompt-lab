"""Agent Template Parser module for generating agent configurations from templates."""

from .models import TemplateData, ParsedTemplate, GeneratedConfig
from .template_manager import TemplateManager
from .template_parser import TemplateParser, TemplateParsingError, VARIABLE_MAPPINGS
from .config_generator import AgentConfigGenerator, ConfigGenerationError
from .llm_enhancer import LLMEnhancer, LLMEnhancementError
from .batch_data_processor import BatchDataProcessor, ProcessedJsonData
from .cli import AgentTemplateParserCLI
from .error_handler import (
    BatchProcessingError, 
    FileOperationError, 
    ValidationError,
    ErrorContext, 
    RecoveryResult, 
    ErrorRecovery,
    create_error_context,
    handle_error_with_recovery
)

__all__ = [
    'TemplateData',
    'ParsedTemplate', 
    'GeneratedConfig',
    'TemplateManager',
    'TemplateParser',
    'TemplateParsingError',
    'VARIABLE_MAPPINGS',
    'AgentConfigGenerator',
    'ConfigGenerationError',
    'LLMEnhancer',
    'LLMEnhancementError',
    'BatchDataProcessor',
    'ProcessedJsonData',
    'AgentTemplateParserCLI',
    'BatchProcessingError',
    'FileOperationError',
    'ValidationError',
    'ErrorContext',
    'RecoveryResult',
    'ErrorRecovery',
    'create_error_context',
    'handle_error_with_recovery'
]