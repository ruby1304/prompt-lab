"""Template management system for organizing and managing input template files."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from .models import TemplateData, TemplateStructure, TemplateLocation
from .error_handler import InvalidFolderStructureError, MissingAgentFolderError, AmbiguousTemplateStructureError


# Constants for folder structure
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

REQUIRED_FOLDER_FILES = ['system_prompt', 'user_input', 'case']


logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages template files and directory structure for agent generation."""
    
    def __init__(self, template_dir: str = "templates"):
        """Initialize the template manager with the specified directory.
        
        Args:
            template_dir: Base directory for storing template files
        """
        self.template_dir = Path(template_dir)
        self.system_prompt_dir = self.template_dir / "system_prompts"
        self.user_input_dir = self.template_dir / "user_inputs"
        self.test_cases_dir = self.template_dir / "test_cases"
        
        # Create directory structure on initialization
        self.create_directory_structure()
    
    def create_directory_structure(self) -> None:
        """Create the template directory structure if it doesn't exist."""
        directories = [
            self.template_dir,
            self.system_prompt_dir,
            self.user_input_dir,
            self.test_cases_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def save_template_files(
        self, 
        system_prompt: str, 
        user_input: str, 
        test_case: str, 
        agent_name: str
    ) -> Dict[str, Path]:
        """Save template files to their respective directories.
        
        Args:
            system_prompt: System prompt template content
            user_input: User input template content
            test_case: Test case JSON content
            agent_name: Name of the agent (used for file naming)
            
        Returns:
            Dictionary mapping file types to their saved paths
            
        Raises:
            ValueError: If agent_name is empty or invalid
            IOError: If files cannot be written
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        
        # Sanitize agent name for file system
        safe_agent_name = self._sanitize_filename(agent_name)
        
        # Define file paths
        system_prompt_path = self.system_prompt_dir / f"{safe_agent_name}_system.txt"
        user_input_path = self.user_input_dir / f"{safe_agent_name}_user.txt"
        test_case_path = self.test_cases_dir / f"{safe_agent_name}_test.json"
        
        # Save files
        try:
            system_prompt_path.write_text(system_prompt, encoding='utf-8')
            user_input_path.write_text(user_input, encoding='utf-8')
            test_case_path.write_text(test_case, encoding='utf-8')
            
            logger.info(f"Saved template files for agent: {agent_name}")
            
            return {
                'system_prompt': system_prompt_path,
                'user_input': user_input_path,
                'test_case': test_case_path
            }
            
        except IOError as e:
            logger.error(f"Failed to save template files for {agent_name}: {e}")
            raise
    
    def load_agent_folder_templates(self, agent_name: str) -> Dict[str, str]:
        """Load template files from agent folder structure.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary containing the loaded template contents
            
        Raises:
            InvalidFolderStructureError: If folder structure is invalid
            ValueError: If agent_name is invalid
            IOError: If files cannot be read
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        
        safe_agent_name = self._sanitize_filename(agent_name)
        agent_folder = self.template_dir / safe_agent_name
        
        # Validate folder structure first
        is_valid, missing_files = self.validate_agent_folder_structure(agent_name)
        if not is_valid:
            raise InvalidFolderStructureError(
                f"Invalid folder structure for agent '{agent_name}'. "
                f"Missing or invalid files: {', '.join(missing_files)}. "
                f"{FOLDER_STRUCTURE_HELP}",
                agent_name=agent_name,
                missing_files=missing_files
            )
        
        # Load files from folder
        try:
            system_prompt_path = agent_folder / "system_prompt"
            user_input_path = agent_folder / "user_input"
            test_case_path = agent_folder / "case"
            
            system_prompt = system_prompt_path.read_text(encoding='utf-8')
            user_input = user_input_path.read_text(encoding='utf-8')
            test_case = test_case_path.read_text(encoding='utf-8')
            
            logger.info(f"Loaded template files from folder for agent: {agent_name}")
            
            return {
                'system_prompt': system_prompt,
                'user_input': user_input,
                'test_case': test_case
            }
            
        except IOError as e:
            logger.error(f"Failed to load template files from folder for {agent_name}: {e}")
            raise
    
    def load_template_files(self, agent_name: str) -> Dict[str, str]:
        """Load template files for the specified agent.
        
        This method tries folder structure first, then falls back to legacy structure.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary containing the loaded template contents
            
        Raises:
            FileNotFoundError: If template files don't exist in either structure
            ValueError: If agent_name is invalid
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        
        try:
            # Try to detect structure type
            structure_type = self.get_template_structure_type(agent_name)
            
            if structure_type == TemplateStructure.FOLDER:
                return self.load_agent_folder_templates(agent_name)
            elif structure_type == TemplateStructure.MIXED:
                # Prefer folder structure over legacy
                logger.info(f"Mixed structure detected for {agent_name}, preferring folder structure")
                return self.load_agent_folder_templates(agent_name)
            elif structure_type == TemplateStructure.LEGACY:
                return self._load_legacy_template_files(agent_name)
                
        except MissingAgentFolderError:
            # Neither structure exists, provide helpful error message
            safe_agent_name = self._sanitize_filename(agent_name)
            folder_path = self.template_dir / safe_agent_name
            
            error_msg = (
                f"No template files found for agent '{agent_name}'. "
                f"Expected either:\n"
                f"1. Folder structure: {folder_path}/ with files: {', '.join(REQUIRED_FOLDER_FILES)}\n"
                f"2. Legacy structure: separate files in system_prompts/, user_inputs/, test_cases/ directories\n"
                f"{FOLDER_STRUCTURE_HELP}"
            )
            raise FileNotFoundError(error_msg)
        
        except Exception as e:
            logger.error(f"Unexpected error loading templates for {agent_name}: {e}")
            raise
    
    def _load_legacy_template_files(self, agent_name: str) -> Dict[str, str]:
        """Load template files from legacy structure.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary containing the loaded template contents
            
        Raises:
            FileNotFoundError: If template files don't exist
            IOError: If files cannot be read
        """
        safe_agent_name = self._sanitize_filename(agent_name)
        
        # Define file paths
        system_prompt_path = self.system_prompt_dir / f"{safe_agent_name}_system.txt"
        user_input_path = self.user_input_dir / f"{safe_agent_name}_user.txt"
        test_case_path = self.test_cases_dir / f"{safe_agent_name}_test.json"
        
        # Check if files exist
        missing_files = []
        for name, path in [
            ('system_prompt', system_prompt_path),
            ('user_input', user_input_path),
            ('test_case', test_case_path)
        ]:
            if not path.exists():
                missing_files.append(f"{name}: {path}")
        
        if missing_files:
            raise FileNotFoundError(
                f"Missing legacy template files for agent '{agent_name}': {', '.join(missing_files)}"
            )
        
        # Load files
        try:
            system_prompt = system_prompt_path.read_text(encoding='utf-8')
            user_input = user_input_path.read_text(encoding='utf-8')
            test_case = test_case_path.read_text(encoding='utf-8')
            
            logger.info(f"Loaded legacy template files for agent: {agent_name}")
            
            return {
                'system_prompt': system_prompt,
                'user_input': user_input,
                'test_case': test_case
            }
            
        except IOError as e:
            logger.error(f"Failed to load legacy template files for {agent_name}: {e}")
            raise
    
    def create_template_data(self, agent_name: str) -> TemplateData:
        """Create a TemplateData object from loaded template files.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            TemplateData object with loaded content
            
        Raises:
            FileNotFoundError: If template files don't exist
            json.JSONDecodeError: If test case JSON is invalid
        """
        templates = self.load_template_files(agent_name)
        
        # Parse test case JSON
        try:
            test_case_data = json.loads(templates['test_case'])
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in test case for {agent_name}: {e}")
            raise
        
        return TemplateData(
            system_prompt=templates['system_prompt'],
            user_input=templates['user_input'],
            test_case=test_case_data,
            variables=[],  # Will be populated by parser
            agent_name=agent_name
        )
    
    def list_available_agents(self) -> List[str]:
        """List all agents that have template files available.
        
        Returns:
            List of agent names that have complete template sets
        """
        agents = set()
        
        # Find all system prompt files
        for system_file in self.system_prompt_dir.glob("*_system.txt"):
            agent_name = system_file.stem.replace("_system", "")
            
            # Check if corresponding user input and test case files exist
            user_file = self.user_input_dir / f"{agent_name}_user.txt"
            test_file = self.test_cases_dir / f"{agent_name}_test.json"
            
            if user_file.exists() and test_file.exists():
                agents.add(agent_name)
        
        return sorted(list(agents))
    
    def validate_template_files(self, agent_name: str) -> Tuple[bool, List[str]]:
        """Validate that template files exist and are readable for both structures.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # First, try to detect what structure exists
            structure_type = self.get_template_structure_type(agent_name)
            
            # Validate based on structure type
            if structure_type == TemplateStructure.FOLDER:
                return self._validate_folder_structure(agent_name)
            elif structure_type == TemplateStructure.LEGACY:
                return self._validate_legacy_structure(agent_name)
            elif structure_type == TemplateStructure.MIXED:
                # Validate both structures and report any issues
                folder_valid, folder_errors = self._validate_folder_structure(agent_name)
                legacy_valid, legacy_errors = self._validate_legacy_structure(agent_name)
                
                if folder_valid:
                    # Folder structure is valid, prefer it
                    return True, []
                elif legacy_valid:
                    # Legacy structure is valid, use it but warn about mixed structure
                    return True, ["Mixed structure detected - consider migrating to folder structure"]
                else:
                    # Both have issues
                    all_errors = [f"Folder structure errors: {', '.join(folder_errors)}"]
                    all_errors.extend([f"Legacy structure errors: {', '.join(legacy_errors)}"])
                    return False, all_errors
                    
        except MissingAgentFolderError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_folder_structure(self, agent_name: str) -> Tuple[bool, List[str]]:
        """Validate folder-based template structure.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # First validate folder structure completeness
            is_valid, missing_files = self.validate_agent_folder_structure(agent_name)
            if not is_valid:
                errors.extend(missing_files)
                return False, errors
            
            # Load and validate content
            templates = self.load_agent_folder_templates(agent_name)
            
            # Validate system prompt
            if not templates['system_prompt'].strip():
                errors.append("System prompt is empty")
            
            # Validate user input
            if not templates['user_input'].strip():
                errors.append("User input template is empty")
            
            # Validate test case JSON
            try:
                test_data = json.loads(templates['test_case'])
                if not isinstance(test_data, dict):
                    errors.append("Test case must be a JSON object")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in test case: {e}")
                
        except Exception as e:
            errors.append(f"Error validating folder structure: {e}")
        
        return len(errors) == 0, errors
    
    def _validate_legacy_structure(self, agent_name: str) -> Tuple[bool, List[str]]:
        """Validate legacy template structure.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            templates = self._load_legacy_template_files(agent_name)
            
            # Validate system prompt
            if not templates['system_prompt'].strip():
                errors.append("System prompt is empty")
            
            # Validate user input
            if not templates['user_input'].strip():
                errors.append("User input template is empty")
            
            # Validate test case JSON
            try:
                test_data = json.loads(templates['test_case'])
                if not isinstance(test_data, dict):
                    errors.append("Test case must be a JSON object")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in test case: {e}")
                
        except FileNotFoundError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Error validating legacy structure: {e}")
        
        return len(errors) == 0, errors
    
    def get_template_structure_type(self, agent_name: str) -> TemplateStructure:
        """Detect the template structure type for the specified agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            TemplateStructure enum indicating the structure type
            
        Raises:
            MissingAgentFolderError: If neither structure exists
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be empty")
        
        safe_agent_name = self._sanitize_filename(agent_name)
        
        # Check for folder structure
        folder_path = self.template_dir / safe_agent_name
        has_folder_structure = folder_path.exists() and folder_path.is_dir()
        
        # Check for legacy structure
        system_prompt_path = self.system_prompt_dir / f"{safe_agent_name}_system.txt"
        user_input_path = self.user_input_dir / f"{safe_agent_name}_user.txt"
        test_case_path = self.test_cases_dir / f"{safe_agent_name}_test.json"
        
        has_legacy_structure = (
            system_prompt_path.exists() and 
            user_input_path.exists() and 
            test_case_path.exists()
        )
        
        if has_folder_structure and has_legacy_structure:
            return TemplateStructure.MIXED
        elif has_folder_structure:
            return TemplateStructure.FOLDER
        elif has_legacy_structure:
            return TemplateStructure.LEGACY
        else:
            raise MissingAgentFolderError(
                f"No template structure found for agent '{agent_name}'. "
                f"Expected either folder structure at '{folder_path}' or legacy structure.",
                agent_name=agent_name,
                expected_path=str(folder_path)
            )
    
    def validate_agent_folder_structure(self, agent_name: str) -> Tuple[bool, List[str]]:
        """Validate that agent folder structure contains all required files.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Tuple of (is_valid, list_of_missing_files)
        """
        if not agent_name or not agent_name.strip():
            return False, ["Agent name cannot be empty"]
        
        safe_agent_name = self._sanitize_filename(agent_name)
        folder_path = self.template_dir / safe_agent_name
        
        if not folder_path.exists():
            return False, [f"Agent folder does not exist: {folder_path}"]
        
        if not folder_path.is_dir():
            return False, [f"Path exists but is not a directory: {folder_path}"]
        
        missing_files = []
        for required_file in REQUIRED_FOLDER_FILES:
            file_path = folder_path / required_file
            if not file_path.exists():
                missing_files.append(required_file)
            elif not file_path.is_file():
                missing_files.append(f"{required_file} (exists but is not a file)")
        
        return len(missing_files) == 0, missing_files
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for file system.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for file system
        """
        # Replace unsafe characters with underscores
        unsafe_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in unsafe_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = 'unnamed_agent'
        
        return sanitized