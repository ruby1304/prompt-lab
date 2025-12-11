"""Core data models for the Agent Template Parser system."""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum


# Constants for template structure management
STANDARD_FILE_NAMES = {
    'system_prompt': 'system_prompt',
    'user_input': 'user_input', 
    'test_case': 'case'
}

REQUIRED_FILES = ['system_prompt', 'user_input', 'case']

FOLDER_STRUCTURE_HELP = """
Expected folder structure:
templates/{agent_name}/
├── system_prompt    (text file with system prompt)
├── user_input      (text file with user input template)
└── case           (JSON file with test case)

Example:
templates/my_agent/
├── system_prompt
├── user_input  
└── case
"""


@dataclass
class TemplateData:
    """Represents the input template data for agent generation."""
    
    system_prompt: str
    user_input: str
    test_case: Dict[str, Any]
    variables: List[str]
    agent_name: str
    
    def __post_init__(self):
        """Validate the template data after initialization."""
        if not self.agent_name:
            raise ValueError("Agent name cannot be empty")
        if not self.system_prompt:
            raise ValueError("System prompt cannot be empty")


@dataclass
class ParsedTemplate:
    """Represents parsed template information with extracted variables and mappings."""
    
    system_variables: List[str]
    user_variables: List[str]
    test_structure: Dict[str, Any]
    variable_mappings: Dict[str, str]
    
    # 添加原始内容字段
    system_content: str = ""
    user_content: str = ""
    test_case_data: Dict[str, Any] = None
    
    def get_all_variables(self) -> List[str]:
        """Get all unique variables from system and user templates."""
        return list(set(self.system_variables + self.user_variables))
    
    def has_variables(self) -> bool:
        """Check if any variables were found in the templates."""
        return len(self.system_variables) > 0 or len(self.user_variables) > 0


class TemplateStructure(Enum):
    """Enum representing different template structure types."""
    FOLDER = "folder"      # New agent-folder structure
    LEGACY = "legacy"      # Existing file-based structure
    MIXED = "mixed"        # Both structures present


@dataclass
class TemplateLocation:
    """Information about template file locations and structure type."""
    structure_type: TemplateStructure
    agent_name: str
    system_prompt_path: Path
    user_input_path: Path
    test_case_path: Path
    base_path: Path


@dataclass
class GeneratedConfig:
    """Represents the generated agent configuration with validation results."""
    
    agent_config: Dict[str, Any]
    prompt_config: Dict[str, Any]
    validation_errors: List[str]
    needs_llm_enhancement: bool
    agent_name: str
    
    def is_valid(self) -> bool:
        """Check if the generated configuration is valid."""
        return len(self.validation_errors) == 0
    
    def has_critical_errors(self) -> bool:
        """Check if there are critical errors that prevent usage."""
        critical_keywords = ['missing', 'required', 'invalid format']
        return any(
            any(keyword in error.lower() for keyword in critical_keywords)
            for error in self.validation_errors
        )
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the generated configuration."""
        return {
            'agent_name': self.agent_name,
            'has_agent_config': bool(self.agent_config),
            'has_prompt_config': bool(self.prompt_config),
            'is_valid': self.is_valid(),
            'needs_enhancement': self.needs_llm_enhancement,
            'error_count': len(self.validation_errors)
        }