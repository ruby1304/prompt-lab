"""Tests for TemplateManager enhancements - folder structure support and new methods."""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

from src.agent_template_parser.template_manager import TemplateManager, FOLDER_STRUCTURE_HELP, REQUIRED_FOLDER_FILES
from src.agent_template_parser.models import TemplateStructure, TemplateData
from src.agent_template_parser.error_handler import (
    InvalidFolderStructureError, 
    MissingAgentFolderError, 
    AmbiguousTemplateStructureError
)


class TestTemplateManagerEnhancements:
    """Test the enhanced TemplateManager functionality."""
    
    def setup_method(self):
        """Set up test environment with fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_manager = TemplateManager(self.temp_dir)
        
        # Set up fixtures path
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "templates"
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _copy_fixture_to_temp(self, fixture_name: str, target_name: str = None):
        """Copy a fixture to the temp directory."""
        if target_name is None:
            target_name = fixture_name
        
        source = self.fixtures_dir / fixture_name
        target = Path(self.temp_dir)
        
        if source.is_dir():
            # For mixed structures, copy both legacy directories and folder files
            if "mixed" in fixture_name:
                # Copy legacy structure directories to the templates root
                for item in source.iterdir():
                    if item.is_dir():
                        target_dir = target / item.name
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        shutil.copytree(item, target_dir)
                
                # Copy folder structure files to agent folder
                agent_folder = target / target_name
                agent_folder.mkdir(exist_ok=True)
                for item in source.iterdir():
                    if item.is_file():
                        shutil.copy2(item, agent_folder / item.name)
            
            # For legacy structures, copy the contents to the templates directory
            elif "legacy" in fixture_name:
                # Copy the legacy structure directories to the templates root
                for item in source.iterdir():
                    if item.is_dir():
                        target_dir = target / item.name
                        if target_dir.exists():
                            shutil.rmtree(target_dir)
                        shutil.copytree(item, target_dir)
            else:
                # For folder structures, copy to templates/{agent_name}
                final_target = target / target_name
                if final_target.exists():
                    shutil.rmtree(final_target)
                shutil.copytree(source, final_target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    
    def test_get_template_structure_type_folder(self):
        """Test detecting folder structure type."""
        # Copy folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        structure_type = self.template_manager.get_template_structure_type("folder_structure_agent")
        assert structure_type == TemplateStructure.FOLDER
    
    def test_get_template_structure_type_legacy(self):
        """Test detecting legacy structure type."""
        # Copy legacy structure fixture
        self._copy_fixture_to_temp("legacy_structure_agent")
        
        structure_type = self.template_manager.get_template_structure_type("legacy_structure_agent")
        assert structure_type == TemplateStructure.LEGACY
    
    def test_get_template_structure_type_mixed(self):
        """Test detecting mixed structure type."""
        # Copy mixed structure fixture
        self._copy_fixture_to_temp("mixed_structure_agent")
        
        structure_type = self.template_manager.get_template_structure_type("mixed_structure_agent")
        assert structure_type == TemplateStructure.MIXED
    
    def test_get_template_structure_type_missing(self):
        """Test detecting missing structure."""
        with pytest.raises(MissingAgentFolderError) as exc_info:
            self.template_manager.get_template_structure_type("nonexistent_agent")
        
        assert "nonexistent_agent" in str(exc_info.value)
        assert exc_info.value.agent_name == "nonexistent_agent"
    
    def test_get_template_structure_type_empty_name(self):
        """Test structure detection with empty agent name."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            self.template_manager.get_template_structure_type("")
        
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            self.template_manager.get_template_structure_type("   ")
    
    def test_validate_agent_folder_structure_valid(self):
        """Test validating a valid agent folder structure."""
        # Copy valid folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure("folder_structure_agent")
        assert is_valid is True
        assert missing_files == []
    
    def test_validate_agent_folder_structure_missing_files(self):
        """Test validating folder structure with missing files."""
        # Copy incomplete folder structure fixture
        self._copy_fixture_to_temp("incomplete_folder_agent")
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure("incomplete_folder_agent")
        assert is_valid is False
        assert "user_input" in missing_files
        assert "case" in missing_files
        assert "system_prompt" not in missing_files
    
    def test_validate_agent_folder_structure_no_folder(self):
        """Test validating non-existent folder structure."""
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure("nonexistent_agent")
        assert is_valid is False
        assert len(missing_files) == 1
        assert "does not exist" in missing_files[0]
    
    def test_validate_agent_folder_structure_not_directory(self):
        """Test validating when path exists but is not a directory."""
        # Copy the not-a-directory fixture
        self._copy_fixture_to_temp("not_a_directory_agent")
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure("not_a_directory_agent")
        assert is_valid is False
        assert len(missing_files) == 1
        assert "not a directory" in missing_files[0]
    
    def test_validate_agent_folder_structure_empty_name(self):
        """Test folder validation with empty agent name."""
        is_valid, errors = self.template_manager.validate_agent_folder_structure("")
        assert is_valid is False
        assert "Agent name cannot be empty" in errors
        
        is_valid, errors = self.template_manager.validate_agent_folder_structure("   ")
        assert is_valid is False
        assert "Agent name cannot be empty" in errors
    
    def test_load_agent_folder_templates_valid(self):
        """Test loading templates from valid folder structure."""
        # Copy valid folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        templates = self.template_manager.load_agent_folder_templates("folder_structure_agent")
        
        assert "system_prompt" in templates
        assert "user_input" in templates
        assert "test_case" in templates
        assert "helpful assistant" in templates["system_prompt"]
        assert "analyze the following request" in templates["user_input"]
        assert "weather" in templates["test_case"]
    
    def test_load_agent_folder_templates_invalid_structure(self):
        """Test loading templates from invalid folder structure."""
        # Copy incomplete folder structure fixture
        self._copy_fixture_to_temp("incomplete_folder_agent")
        
        with pytest.raises(InvalidFolderStructureError) as exc_info:
            self.template_manager.load_agent_folder_templates("incomplete_folder_agent")
        
        assert "incomplete_folder_agent" in str(exc_info.value)
        assert "user_input" in str(exc_info.value)
        assert "case" in str(exc_info.value)
        assert exc_info.value.agent_name == "incomplete_folder_agent"
    
    def test_load_agent_folder_templates_empty_name(self):
        """Test loading folder templates with empty agent name."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            self.template_manager.load_agent_folder_templates("")
    
    def test_load_template_files_folder_structure_preference(self):
        """Test loading templates with folder structure preference."""
        # Copy valid folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        templates = self.template_manager.load_template_files("folder_structure_agent")
        
        # Should load from folder structure
        assert "helpful assistant specialized in folder structure testing" in templates["system_prompt"]
        assert "analyze the following request" in templates["user_input"]
        assert "weather" in templates["test_case"]
    
    def test_load_template_files_legacy_structure_fallback(self):
        """Test loading templates with legacy structure fallback."""
        # Copy legacy structure fixture
        self._copy_fixture_to_temp("legacy_structure_agent")
        
        templates = self.template_manager.load_template_files("legacy_structure_agent")
        
        # Should load from legacy structure
        assert "legacy structure testing assistant" in templates["system_prompt"]
        assert "Legacy template request" in templates["user_input"]
        assert "legacy structure functionality" in templates["test_case"]
    
    def test_load_template_files_mixed_structure_prefers_folder(self):
        """Test loading templates with mixed structure prefers folder."""
        # Copy mixed structure fixture
        self._copy_fixture_to_temp("mixed_structure_agent")
        
        templates = self.template_manager.load_template_files("mixed_structure_agent")
        
        # Should prefer folder structure over legacy
        assert "folder version" in templates["system_prompt"]
        assert "should be preferred" in templates["user_input"]
        assert "folder" in templates["test_case"]
        assert "should_be_preferred" in templates["test_case"]
        
        # Parse JSON to verify structure
        test_data = json.loads(templates["test_case"])
        assert test_data["structure_type"] == "folder"
        assert test_data["should_be_preferred"] is True
    
    def test_load_template_files_no_structure_helpful_error(self):
        """Test loading templates with no structure provides helpful error."""
        with pytest.raises(FileNotFoundError) as exc_info:
            self.template_manager.load_template_files("nonexistent_agent")
        
        error_msg = str(exc_info.value)
        assert "No template files found" in error_msg
        assert "Folder structure" in error_msg
        assert "Legacy structure" in error_msg
        assert "Expected folder structure" in error_msg
    
    def test_validate_template_files_folder_structure(self):
        """Test validating template files with folder structure."""
        # Copy valid folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        is_valid, errors = self.template_manager.validate_template_files("folder_structure_agent")
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_template_files_folder_structure_empty_content(self):
        """Test validating folder structure with empty content."""
        # Copy empty content fixture
        self._copy_fixture_to_temp("empty_content_agent")
        
        is_valid, errors = self.template_manager.validate_template_files("empty_content_agent")
        assert is_valid is False
        assert any("System prompt is empty" in error for error in errors)
    
    def test_validate_template_files_folder_structure_invalid_json(self):
        """Test validating folder structure with invalid JSON."""
        # Copy invalid JSON fixture
        self._copy_fixture_to_temp("invalid_json_agent")
        
        is_valid, errors = self.template_manager.validate_template_files("invalid_json_agent")
        assert is_valid is False
        assert any("Invalid JSON" in error for error in errors)
    
    def test_validate_template_files_legacy_structure(self):
        """Test validating template files with legacy structure."""
        # Copy legacy structure fixture
        self._copy_fixture_to_temp("legacy_structure_agent")
        
        is_valid, errors = self.template_manager.validate_template_files("legacy_structure_agent")
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_template_files_mixed_structure_folder_valid(self):
        """Test validating mixed structure when folder structure is valid."""
        # Copy mixed structure fixture (folder structure is valid)
        self._copy_fixture_to_temp("mixed_structure_agent")
        
        is_valid, errors = self.template_manager.validate_template_files("mixed_structure_agent")
        assert is_valid is True
        assert len(errors) == 0  # Should prefer valid folder structure
    
    def test_validate_template_files_mixed_structure_legacy_valid(self):
        """Test validating mixed structure when only legacy structure is valid."""
        # Create a mixed structure where folder is invalid but legacy is valid
        agent_name = "mixed_legacy_valid"
        
        # Create valid legacy structure
        self.template_manager.save_template_files(
            "Valid legacy system prompt", 
            "Valid legacy user input", 
            '{"valid": "legacy json"}', 
            agent_name
        )
        
        # Create invalid folder structure (missing files)
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("Valid system prompt")
        # Missing user_input and case files
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is True  # Should use valid legacy structure
        assert len(errors) == 1  # Warning about mixed structure
        assert "Mixed structure detected" in errors[0]
    
    def test_validate_template_files_mixed_structure_both_invalid(self):
        """Test validating mixed structure when both structures are invalid."""
        agent_name = "mixed_both_invalid"
        
        # Create invalid legacy structure (empty system prompt)
        self.template_manager.save_template_files(
            "",  # Empty system prompt
            "Valid user input", 
            '{"valid": "json"}', 
            agent_name
        )
        
        # Create invalid folder structure (missing files)
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("Valid system prompt")
        # Missing user_input and case files
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is False
        assert len(errors) >= 2  # Should report errors from both structures
        assert any("Folder structure errors" in error for error in errors)
        assert any("Legacy structure errors" in error for error in errors)
    
    def test_validate_template_files_incomplete_legacy(self):
        """Test validating incomplete legacy structure."""
        # Copy incomplete legacy structure fixture
        self._copy_fixture_to_temp("incomplete_legacy_agent")
        
        is_valid, errors = self.template_manager.validate_template_files("incomplete_legacy_agent")
        assert is_valid is False
        assert len(errors) > 0
        assert any("No template structure found" in error for error in errors)
    
    def test_create_template_data_folder_structure(self):
        """Test creating TemplateData from folder structure."""
        # Copy valid folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        template_data = self.template_manager.create_template_data("folder_structure_agent")
        
        assert isinstance(template_data, TemplateData)
        assert template_data.agent_name == "folder_structure_agent"
        assert "helpful assistant" in template_data.system_prompt
        assert "analyze the following request" in template_data.user_input
        assert isinstance(template_data.test_case, dict)
        assert "weather" in template_data.test_case["input"]
    
    def test_create_template_data_legacy_structure(self):
        """Test creating TemplateData from legacy structure."""
        # Copy legacy structure fixture
        self._copy_fixture_to_temp("legacy_structure_agent")
        
        template_data = self.template_manager.create_template_data("legacy_structure_agent")
        
        assert isinstance(template_data, TemplateData)
        assert template_data.agent_name == "legacy_structure_agent"
        assert "legacy structure testing assistant" in template_data.system_prompt
        assert "Legacy template request" in template_data.user_input
        assert isinstance(template_data.test_case, dict)
        assert "legacy structure functionality" in template_data.test_case["input"]
    
    def test_create_template_data_invalid_json(self):
        """Test creating TemplateData with invalid JSON in test case."""
        # Copy invalid JSON fixture
        self._copy_fixture_to_temp("invalid_json_agent")
        
        with pytest.raises(json.JSONDecodeError):
            self.template_manager.create_template_data("invalid_json_agent")
    
    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        unsafe_name = "test<>agent/with\\unsafe:chars"
        safe_name = self.template_manager._sanitize_filename(unsafe_name)
        
        assert "<" not in safe_name
        assert ">" not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert ":" not in safe_name
        assert safe_name == "test__agent_with_unsafe_chars"
    
    def test_sanitize_filename_empty(self):
        """Test sanitizing empty filename."""
        empty_safe = self.template_manager._sanitize_filename("")
        assert empty_safe == "unnamed_agent"
        
        whitespace_safe = self.template_manager._sanitize_filename("   ")
        assert whitespace_safe == "unnamed_agent"
    
    def test_sanitize_filename_dots_and_spaces(self):
        """Test sanitizing filename with dots and spaces."""
        dotted_name = "...test agent..."
        safe_name = self.template_manager._sanitize_filename(dotted_name)
        assert not safe_name.startswith(".")
        assert not safe_name.endswith(".")
        assert safe_name == "test agent"
    
    def test_error_handling_file_read_errors(self):
        """Test error handling for file read errors."""
        # Create a folder structure but make files unreadable
        agent_name = "unreadable_agent"
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        
        # Create files
        system_file = agent_folder / "system_prompt"
        user_file = agent_folder / "user_input"
        case_file = agent_folder / "case"
        
        system_file.write_text("System prompt")
        user_file.write_text("User input")
        case_file.write_text('{"test": true}')
        
        # Mock file reading to raise IOError
        with patch("pathlib.Path.read_text", side_effect=IOError("Permission denied")):
            with pytest.raises(IOError, match="Permission denied"):
                self.template_manager.load_agent_folder_templates(agent_name)
    
    def test_error_handling_directory_creation_failure(self):
        """Test error handling when directory creation fails."""
        # Mock mkdir to raise OSError
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                TemplateManager("/invalid/path/that/cannot/be/created")
    
    def test_load_template_files_with_logging(self):
        """Test that loading template files produces appropriate log messages."""
        # Copy valid folder structure fixture
        self._copy_fixture_to_temp("folder_structure_agent")
        
        with patch("src.agent_template_parser.template_manager.logger") as mock_logger:
            self.template_manager.load_template_files("folder_structure_agent")
            
            # Check that info log was called
            mock_logger.info.assert_called()
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("Loaded template files from folder" in call for call in log_calls)
    
    def test_save_template_files_with_logging(self):
        """Test that saving template files produces appropriate log messages."""
        with patch("src.agent_template_parser.template_manager.logger") as mock_logger:
            self.template_manager.save_template_files(
                "System prompt", "User input", '{"test": true}', "test_agent"
            )
            
            # Check that info log was called
            mock_logger.info.assert_called_with("Saved template files for agent: test_agent")
    
    def test_constants_and_help_messages(self):
        """Test that constants and help messages are properly defined."""
        assert FOLDER_STRUCTURE_HELP is not None
        assert "templates/{agent_name}/" in FOLDER_STRUCTURE_HELP
        assert "system_prompt" in FOLDER_STRUCTURE_HELP
        assert "user_input" in FOLDER_STRUCTURE_HELP
        assert "case" in FOLDER_STRUCTURE_HELP
        
        assert REQUIRED_FOLDER_FILES == ['system_prompt', 'user_input', 'case']
    
    def test_template_manager_initialization_with_custom_path(self):
        """Test TemplateManager initialization with custom template directory."""
        custom_path = Path(self.temp_dir) / "custom_templates"
        manager = TemplateManager(str(custom_path))
        
        assert manager.template_dir == custom_path
        assert manager.system_prompt_dir == custom_path / "system_prompts"
        assert manager.user_input_dir == custom_path / "user_inputs"
        assert manager.test_cases_dir == custom_path / "test_cases"
        
        # Check that directories were created
        assert custom_path.exists()
        assert manager.system_prompt_dir.exists()
        assert manager.user_input_dir.exists()
        assert manager.test_cases_dir.exists()


class TestTemplateManagerErrorScenarios:
    """Test error scenarios and edge cases for TemplateManager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_manager = TemplateManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_invalid_folder_structure_error_attributes(self):
        """Test InvalidFolderStructureError has correct attributes."""
        agent_name = "test_agent"
        missing_files = ["user_input", "case"]
        
        error = InvalidFolderStructureError(
            "Test error message", 
            agent_name=agent_name, 
            missing_files=missing_files
        )
        
        assert error.agent_name == agent_name
        assert error.missing_files == missing_files
        assert "Test error message" in str(error)
    
    def test_missing_agent_folder_error_attributes(self):
        """Test MissingAgentFolderError has correct attributes."""
        agent_name = "test_agent"
        expected_path = "/path/to/agent"
        
        error = MissingAgentFolderError(
            "Test error message", 
            agent_name=agent_name, 
            expected_path=expected_path
        )
        
        assert error.agent_name == agent_name
        assert error.expected_path == expected_path
        assert "Test error message" in str(error)
    
    def test_ambiguous_template_structure_error_attributes(self):
        """Test AmbiguousTemplateStructureError has correct attributes."""
        agent_name = "test_agent"
        conflicting_paths = ["/path1", "/path2"]
        
        error = AmbiguousTemplateStructureError(
            "Test error message", 
            agent_name=agent_name, 
            conflicting_paths=conflicting_paths
        )
        
        assert error.agent_name == agent_name
        assert error.conflicting_paths == conflicting_paths
        assert "Test error message" in str(error)
    
    def test_load_template_files_io_error_handling(self):
        """Test handling of IO errors during template loading."""
        agent_name = "io_error_agent"
        
        # Create valid folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("System prompt")
        (agent_folder / "user_input").write_text("User input")
        (agent_folder / "case").write_text('{"test": true}')
        
        # Mock read_text to raise IOError
        with patch("pathlib.Path.read_text", side_effect=IOError("Disk error")):
            with pytest.raises(IOError, match="Disk error"):
                self.template_manager.load_agent_folder_templates(agent_name)
    
    def test_save_template_files_io_error_handling(self):
        """Test handling of IO errors during template saving."""
        # Mock write_text to raise IOError
        with patch("pathlib.Path.write_text", side_effect=IOError("Disk full")):
            with pytest.raises(IOError, match="Disk full"):
                self.template_manager.save_template_files(
                    "System prompt", "User input", '{"test": true}', "test_agent"
                )
    
    def test_validate_template_files_exception_handling(self):
        """Test exception handling in validate_template_files."""
        agent_name = "exception_agent"
        
        # Mock get_template_structure_type to raise unexpected exception
        with patch.object(
            self.template_manager, 
            'get_template_structure_type', 
            side_effect=RuntimeError("Unexpected error")
        ):
            is_valid, errors = self.template_manager.validate_template_files(agent_name)
            assert is_valid is False
            assert len(errors) == 1
            assert "Unexpected error" in errors[0]
    
    def test_edge_case_very_long_agent_name(self):
        """Test handling of very long agent names."""
        long_name = "a" * 300  # Very long name
        safe_name = self.template_manager._sanitize_filename(long_name)
        
        # Should still be a valid filename (though potentially truncated by OS)
        assert len(safe_name) > 0
        assert safe_name == long_name  # Our sanitizer doesn't truncate
    
    def test_edge_case_unicode_agent_name(self):
        """Test handling of unicode characters in agent names."""
        unicode_name = "测试代理_🤖_agent"
        safe_name = self.template_manager._sanitize_filename(unicode_name)
        
        # Should preserve unicode characters
        assert safe_name == unicode_name
    
    def test_edge_case_only_unsafe_characters(self):
        """Test sanitizing name with only unsafe characters."""
        unsafe_name = "<>:\"/\\|?*"
        safe_name = self.template_manager._sanitize_filename(unsafe_name)
        
        # Should become underscores since all characters are replaced
        assert safe_name == "_________"