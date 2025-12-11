"""Tests for the Agent Template Parser core components."""

import json
import pytest
from pathlib import Path
import tempfile
import shutil

from src.agent_template_parser.models import TemplateData, ParsedTemplate, GeneratedConfig
from src.agent_template_parser.template_manager import TemplateManager
from src.agent_template_parser.template_parser import TemplateParser, TemplateParsingError, VARIABLE_MAPPINGS


class TestTemplateData:
    """Test the TemplateData model."""
    
    def test_template_data_creation(self):
        """Test creating a valid TemplateData object."""
        template_data = TemplateData(
            system_prompt="You are a helpful assistant",
            user_input="Please help with: {input}",
            test_case={"input": "test"},
            variables=["input"],
            agent_name="test_agent"
        )
        
        assert template_data.agent_name == "test_agent"
        assert template_data.system_prompt == "You are a helpful assistant"
        assert template_data.variables == ["input"]
    
    def test_template_data_validation(self):
        """Test TemplateData validation."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            TemplateData(
                system_prompt="test",
                user_input="test",
                test_case={},
                variables=[],
                agent_name=""
            )
        
        with pytest.raises(ValueError, match="System prompt cannot be empty"):
            TemplateData(
                system_prompt="",
                user_input="test",
                test_case={},
                variables=[],
                agent_name="test"
            )


class TestParsedTemplate:
    """Test the ParsedTemplate model."""
    
    def test_parsed_template_creation(self):
        """Test creating a ParsedTemplate object."""
        parsed = ParsedTemplate(
            system_variables=["var1", "var2"],
            user_variables=["var2", "var3"],
            test_structure={"key": "value"},
            variable_mappings={"var1": "field1"}
        )
        
        assert set(parsed.get_all_variables()) == {"var1", "var2", "var3"}
        assert parsed.has_variables() is True
    
    def test_no_variables(self):
        """Test ParsedTemplate with no variables."""
        parsed = ParsedTemplate(
            system_variables=[],
            user_variables=[],
            test_structure={},
            variable_mappings={}
        )
        
        assert parsed.get_all_variables() == []
        assert parsed.has_variables() is False


class TestGeneratedConfig:
    """Test the GeneratedConfig model."""
    
    def test_valid_config(self):
        """Test a valid GeneratedConfig."""
        config = GeneratedConfig(
            agent_config={"name": "test"},
            prompt_config={"prompt": "test"},
            validation_errors=[],
            needs_llm_enhancement=False,
            agent_name="test_agent"
        )
        
        assert config.is_valid() is True
        assert config.has_critical_errors() is False
        
        summary = config.get_config_summary()
        assert summary["agent_name"] == "test_agent"
        assert summary["is_valid"] is True
    
    def test_invalid_config(self):
        """Test an invalid GeneratedConfig."""
        config = GeneratedConfig(
            agent_config={},
            prompt_config={},
            validation_errors=["Missing required field", "Invalid format"],
            needs_llm_enhancement=True,
            agent_name="test_agent"
        )
        
        assert config.is_valid() is False
        assert config.has_critical_errors() is True


class TestTemplateManager:
    """Test the TemplateManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_manager = TemplateManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_directory_creation(self):
        """Test that directories are created correctly."""
        assert self.template_manager.template_dir.exists()
        assert self.template_manager.system_prompt_dir.exists()
        assert self.template_manager.user_input_dir.exists()
        assert self.template_manager.test_cases_dir.exists()
    
    def test_save_and_load_template_files(self):
        """Test saving and loading template files."""
        system_prompt = "You are a test assistant"
        user_input = "Process: {input}"
        test_case = '{"input": "test data"}'
        agent_name = "test_agent"
        
        # Save files
        saved_paths = self.template_manager.save_template_files(
            system_prompt, user_input, test_case, agent_name
        )
        
        assert len(saved_paths) == 3
        assert all(path.exists() for path in saved_paths.values())
        
        # Load files
        loaded = self.template_manager.load_template_files(agent_name)
        
        assert loaded['system_prompt'] == system_prompt
        assert loaded['user_input'] == user_input
        assert loaded['test_case'] == test_case
    
    def test_create_template_data(self):
        """Test creating TemplateData from files."""
        system_prompt = "You are a test assistant"
        user_input = "Process: {input}"
        test_case = '{"input": "test data"}'
        agent_name = "test_agent"
        
        # Save files first
        self.template_manager.save_template_files(
            system_prompt, user_input, test_case, agent_name
        )
        
        # Create TemplateData
        template_data = self.template_manager.create_template_data(agent_name)
        
        assert template_data.agent_name == agent_name
        assert template_data.system_prompt == system_prompt
        assert template_data.user_input == user_input
        assert template_data.test_case == {"input": "test data"}
    
    def test_list_available_agents(self):
        """Test listing available agents."""
        # Initially empty
        assert self.template_manager.list_available_agents() == []
        
        # Add complete template set
        self.template_manager.save_template_files(
            "system", "user", '{"test": true}', "agent1"
        )
        
        # Add incomplete template set (missing test case)
        (self.template_manager.system_prompt_dir / "agent2_system.txt").write_text("system")
        (self.template_manager.user_input_dir / "agent2_user.txt").write_text("user")
        
        agents = self.template_manager.list_available_agents()
        assert agents == ["agent1"]  # Only complete sets
    
    def test_validate_template_files(self):
        """Test template file validation."""
        agent_name = "test_agent"
        
        # Test with missing files
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert not is_valid
        assert len(errors) > 0
        
        # Test with valid files
        self.template_manager.save_template_files(
            "Valid system prompt", "Valid user input", '{"valid": "json"}', agent_name
        )
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid
        assert len(errors) == 0
        
        # Test with invalid JSON
        (self.template_manager.test_cases_dir / f"{agent_name}_test.json").write_text("invalid json")
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert not is_valid
        assert any("Invalid JSON" in error for error in errors)
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        unsafe_name = "test<>agent/with\\unsafe:chars"
        safe_name = self.template_manager._sanitize_filename(unsafe_name)
        
        assert "<" not in safe_name
        assert ">" not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert ":" not in safe_name
        
        # Test empty name
        empty_safe = self.template_manager._sanitize_filename("")
        assert empty_safe == "unnamed_agent"
    
    def test_get_template_structure_type_folder(self):
        """Test detecting folder structure type."""
        agent_name = "test_agent"
        
        # Create folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("System prompt")
        (agent_folder / "user_input").write_text("User input")
        (agent_folder / "case").write_text('{"test": true}')
        
        from src.agent_template_parser.models import TemplateStructure
        structure_type = self.template_manager.get_template_structure_type(agent_name)
        assert structure_type == TemplateStructure.FOLDER
    
    def test_get_template_structure_type_legacy(self):
        """Test detecting legacy structure type."""
        agent_name = "test_agent"
        
        # Create legacy structure
        self.template_manager.save_template_files(
            "System prompt", "User input", '{"test": true}', agent_name
        )
        
        from src.agent_template_parser.models import TemplateStructure
        structure_type = self.template_manager.get_template_structure_type(agent_name)
        assert structure_type == TemplateStructure.LEGACY
    
    def test_get_template_structure_type_mixed(self):
        """Test detecting mixed structure type."""
        agent_name = "test_agent"
        
        # Create both structures
        # Legacy structure
        self.template_manager.save_template_files(
            "System prompt", "User input", '{"test": true}', agent_name
        )
        
        # Folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("System prompt")
        (agent_folder / "user_input").write_text("User input")
        (agent_folder / "case").write_text('{"test": true}')
        
        from src.agent_template_parser.models import TemplateStructure
        structure_type = self.template_manager.get_template_structure_type(agent_name)
        assert structure_type == TemplateStructure.MIXED
    
    def test_get_template_structure_type_missing(self):
        """Test detecting missing structure."""
        agent_name = "nonexistent_agent"
        
        from src.agent_template_parser.error_handler import MissingAgentFolderError
        with pytest.raises(MissingAgentFolderError) as exc_info:
            self.template_manager.get_template_structure_type(agent_name)
        
        assert agent_name in str(exc_info.value)
        assert exc_info.value.agent_name == agent_name
    
    def test_get_template_structure_type_empty_name(self):
        """Test structure detection with empty agent name."""
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            self.template_manager.get_template_structure_type("")
        
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            self.template_manager.get_template_structure_type("   ")
    
    def test_validate_agent_folder_structure_valid(self):
        """Test validating a valid agent folder structure."""
        agent_name = "test_agent"
        
        # Create valid folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("System prompt")
        (agent_folder / "user_input").write_text("User input")
        (agent_folder / "case").write_text('{"test": true}')
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure(agent_name)
        assert is_valid is True
        assert missing_files == []
    
    def test_validate_agent_folder_structure_missing_files(self):
        """Test validating folder structure with missing files."""
        agent_name = "test_agent"
        
        # Create folder with only some files
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("System prompt")
        # Missing user_input and case files
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure(agent_name)
        assert is_valid is False
        assert "user_input" in missing_files
        assert "case" in missing_files
        assert "system_prompt" not in missing_files
    
    def test_validate_agent_folder_structure_no_folder(self):
        """Test validating non-existent folder structure."""
        agent_name = "nonexistent_agent"
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure(agent_name)
        assert is_valid is False
        assert len(missing_files) == 1
        assert "does not exist" in missing_files[0]
    
    def test_validate_agent_folder_structure_not_directory(self):
        """Test validating when path exists but is not a directory."""
        agent_name = "test_agent"
        
        # Create a file instead of directory
        agent_path = Path(self.temp_dir) / agent_name
        agent_path.write_text("This is a file, not a directory")
        
        is_valid, missing_files = self.template_manager.validate_agent_folder_structure(agent_name)
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
        agent_name = "test_agent"
        system_content = "You are a test assistant"
        user_content = "Process: {input}"
        case_content = '{"input": "test data"}'
        
        # Create folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text(system_content)
        (agent_folder / "user_input").write_text(user_content)
        (agent_folder / "case").write_text(case_content)
        
        # Load templates
        templates = self.template_manager.load_agent_folder_templates(agent_name)
        
        assert templates['system_prompt'] == system_content
        assert templates['user_input'] == user_content
        assert templates['test_case'] == case_content
    
    def test_load_agent_folder_templates_invalid_structure(self):
        """Test loading templates from invalid folder structure."""
        agent_name = "test_agent"
        
        # Create folder with missing files
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("System prompt")
        # Missing user_input and case files
        
        from src.agent_template_parser.error_handler import InvalidFolderStructureError
        with pytest.raises(InvalidFolderStructureError) as exc_info:
            self.template_manager.load_agent_folder_templates(agent_name)
        
        assert agent_name in str(exc_info.value)
        assert "user_input" in str(exc_info.value)
        assert "case" in str(exc_info.value)
    
    def test_load_template_files_folder_structure(self):
        """Test loading templates with folder structure preference."""
        agent_name = "test_agent"
        system_content = "Folder system prompt"
        user_content = "Folder user input"
        case_content = '{"folder": "test"}'
        
        # Create folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text(system_content)
        (agent_folder / "user_input").write_text(user_content)
        (agent_folder / "case").write_text(case_content)
        
        # Load templates (should use folder structure)
        templates = self.template_manager.load_template_files(agent_name)
        
        assert templates['system_prompt'] == system_content
        assert templates['user_input'] == user_content
        assert templates['test_case'] == case_content
    
    def test_load_template_files_legacy_structure(self):
        """Test loading templates with legacy structure."""
        agent_name = "test_agent"
        system_content = "Legacy system prompt"
        user_content = "Legacy user input"
        case_content = '{"legacy": "test"}'
        
        # Create legacy structure only
        self.template_manager.save_template_files(
            system_content, user_content, case_content, agent_name
        )
        
        # Load templates (should use legacy structure)
        templates = self.template_manager.load_template_files(agent_name)
        
        assert templates['system_prompt'] == system_content
        assert templates['user_input'] == user_content
        assert templates['test_case'] == case_content
    
    def test_load_template_files_mixed_structure_prefers_folder(self):
        """Test loading templates with mixed structure prefers folder."""
        agent_name = "test_agent"
        
        # Create legacy structure
        legacy_system = "Legacy system prompt"
        legacy_user = "Legacy user input"
        legacy_case = '{"legacy": "test"}'
        self.template_manager.save_template_files(
            legacy_system, legacy_user, legacy_case, agent_name
        )
        
        # Create folder structure (should be preferred)
        folder_system = "Folder system prompt"
        folder_user = "Folder user input"
        folder_case = '{"folder": "test"}'
        
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text(folder_system)
        (agent_folder / "user_input").write_text(folder_user)
        (agent_folder / "case").write_text(folder_case)
        
        # Load templates (should prefer folder structure)
        templates = self.template_manager.load_template_files(agent_name)
        
        assert templates['system_prompt'] == folder_system  # Not legacy
        assert templates['user_input'] == folder_user      # Not legacy
        assert templates['test_case'] == folder_case       # Not legacy
    
    def test_load_template_files_no_structure_helpful_error(self):
        """Test loading templates with no structure provides helpful error."""
        agent_name = "nonexistent_agent"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            self.template_manager.load_template_files(agent_name)
        
        error_msg = str(exc_info.value)
        assert "No template files found" in error_msg
        assert "Folder structure" in error_msg
        assert "Legacy structure" in error_msg
        assert "Expected folder structure" in error_msg
    
    def test_validate_template_files_folder_structure(self):
        """Test validating template files with folder structure."""
        agent_name = "test_agent"
        
        # Create valid folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("Valid system prompt")
        (agent_folder / "user_input").write_text("Valid user input")
        (agent_folder / "case").write_text('{"valid": "json"}')
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_template_files_folder_structure_empty_content(self):
        """Test validating folder structure with empty content."""
        agent_name = "test_agent"
        
        # Create folder structure with empty content
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("")  # Empty
        (agent_folder / "user_input").write_text("Valid user input")
        (agent_folder / "case").write_text('{"valid": "json"}')
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is False
        assert "System prompt is empty" in errors
    
    def test_validate_template_files_folder_structure_invalid_json(self):
        """Test validating folder structure with invalid JSON."""
        agent_name = "test_agent"
        
        # Create folder structure with invalid JSON
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("Valid system prompt")
        (agent_folder / "user_input").write_text("Valid user input")
        (agent_folder / "case").write_text('{"invalid": json}')  # Invalid JSON
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is False
        assert any("Invalid JSON" in error for error in errors)
    
    def test_validate_template_files_legacy_structure(self):
        """Test validating template files with legacy structure."""
        agent_name = "test_agent"
        
        # Create valid legacy structure
        self.template_manager.save_template_files(
            "Valid system prompt", "Valid user input", '{"valid": "json"}', agent_name
        )
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_template_files_mixed_structure_folder_valid(self):
        """Test validating mixed structure when folder structure is valid."""
        agent_name = "test_agent"
        
        # Create legacy structure (with issues)
        self.template_manager.save_template_files(
            "", "Valid user input", '{"valid": "json"}', agent_name  # Empty system prompt
        )
        
        # Create valid folder structure
        agent_folder = Path(self.temp_dir) / agent_name
        agent_folder.mkdir()
        (agent_folder / "system_prompt").write_text("Valid system prompt")
        (agent_folder / "user_input").write_text("Valid user input")
        (agent_folder / "case").write_text('{"valid": "json"}')
        
        is_valid, errors = self.template_manager.validate_template_files(agent_name)
        assert is_valid is True  # Should prefer valid folder structure
        assert len(errors) == 0
    
    def test_validate_template_files_mixed_structure_legacy_valid(self):
        """Test validating mixed structure when only legacy structure is valid."""
        agent_name = "test_agent"
        
        # Create valid legacy structure
        self.template_manager.save_template_files(
            "Valid system prompt", "Valid user input", '{"valid": "json"}', agent_name
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
        agent_name = "test_agent"
        
        # Create invalid legacy structure
        self.template_manager.save_template_files(
            "", "Valid user input", '{"valid": "json"}', agent_name  # Empty system prompt
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


class TestTemplateParser:
    """Test the TemplateParser class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = TemplateParser()
    
    def test_extract_variables_dollar_format(self):
        """Test extracting ${} format variables."""
        text = "Process ${input} with ${context} and ${data}"
        variables = self.parser.extract_variables(text)
        
        expected = ["${context}", "${data}", "${input}"]  # Sorted
        assert variables == expected
    
    def test_extract_variables_simple_format(self):
        """Test extracting {} format variables."""
        text = "Hello {user}, your {role} is important"
        variables = self.parser.extract_variables(text)
        
        expected = ["{role}", "{user}"]  # Sorted
        assert variables == expected
    
    def test_extract_variables_mixed_format(self):
        """Test extracting mixed variable formats."""
        text = "Process ${sys.user_input} for {user} with {role}"
        variables = self.parser.extract_variables(text)
        
        expected = ["${sys.user_input}", "{role}", "{user}"]  # Sorted
        assert variables == expected
    
    def test_extract_variables_no_variables(self):
        """Test extracting from text with no variables."""
        text = "This is plain text with no variables"
        variables = self.parser.extract_variables(text)
        
        assert variables == []
    
    def test_extract_variables_empty_text(self):
        """Test extracting from empty text."""
        variables = self.parser.extract_variables("")
        assert variables == []
        
        variables = self.parser.extract_variables(None)
        assert variables == []
    
    def test_parse_system_prompt_basic(self):
        """Test parsing a basic system prompt."""
        content = "You are a helpful assistant. Process ${input} for the user."
        result = self.parser.parse_system_prompt(content)
        
        assert result['content'] == content
        assert result['variables'] == ["${input}"]
        assert result['has_variables'] is True
        assert result['line_count'] == 1
        assert result['non_empty_line_count'] == 1
    
    def test_parse_system_prompt_multiline(self):
        """Test parsing a multiline system prompt."""
        content = """You are a helpful assistant.
        
Process ${input} with ${context}.
Always be polite to {user}."""
        
        result = self.parser.parse_system_prompt(content)
        
        assert result['variables'] == ["${context}", "${input}", "{user}"]
        assert result['has_variables'] is True
        assert result['line_count'] == 4
        assert result['non_empty_line_count'] == 3
    
    def test_parse_system_prompt_empty(self):
        """Test parsing empty system prompt."""
        with pytest.raises(TemplateParsingError, match="System prompt content cannot be empty"):
            self.parser.parse_system_prompt("")
        
        with pytest.raises(TemplateParsingError, match="System prompt content cannot be empty"):
            self.parser.parse_system_prompt("   ")
    
    def test_parse_user_input_basic(self):
        """Test parsing basic user input template."""
        content = "Please process: {input}"
        result = self.parser.parse_user_input(content)
        
        assert result['content'] == content
        assert result['variables'] == ["{input}"]
        assert result['has_variables'] is True
        assert result['is_simple_template'] is True
    
    def test_parse_user_input_complex(self):
        """Test parsing complex user input template."""
        content = """Please analyze the following data:
Input: ${sys.user_input}
Context: ${context}
User: {user}
Role: {role}"""
        
        result = self.parser.parse_user_input(content)
        
        assert result['variables'] == ["${context}", "${sys.user_input}", "{role}", "{user}"]
        assert result['has_variables'] is True
        assert result['is_simple_template'] is False
    
    def test_parse_user_input_empty(self):
        """Test parsing empty user input."""
        with pytest.raises(TemplateParsingError, match="User input content cannot be empty"):
            self.parser.parse_user_input("")
    
    def test_parse_test_case_basic(self):
        """Test parsing basic test case JSON."""
        content = '{"input": "test data", "expected": "result"}'
        result = self.parser.parse_test_case(content)
        
        assert result['data'] == {"input": "test data", "expected": "result"}
        assert result['has_sys_structure'] is False
        assert result['has_user_input'] is True  # 'input' key detected
        assert "input" in result['json_variables']
        assert "expected" in result['json_variables']
    
    def test_parse_test_case_with_sys_structure(self):
        """Test parsing test case with sys structure."""
        content = '{"sys": {"user_input": ["message1", "message2"]}, "other": "data"}'
        result = self.parser.parse_test_case(content)
        
        assert result['has_sys_structure'] is True
        assert result['has_user_input'] is True
        assert "sys" in result['json_variables']
        assert "sys.user_input" in result['json_variables']
        assert "other" in result['json_variables']
    
    def test_parse_test_case_invalid_json(self):
        """Test parsing invalid JSON."""
        content = '{"invalid": json, "missing": quote}'
        
        with pytest.raises(TemplateParsingError, match="Invalid JSON in test case"):
            self.parser.parse_test_case(content)
    
    def test_parse_test_case_empty(self):
        """Test parsing empty test case."""
        with pytest.raises(TemplateParsingError, match="Test case content cannot be empty"):
            self.parser.parse_test_case("")
    
    def test_map_variables_to_config_predefined(self):
        """Test mapping predefined variables."""
        variables = ["${sys.user_input}", "{user}", "{role}"]
        mappings = self.parser.map_variables_to_config(variables)
        
        assert mappings["${sys.user_input}"] == VARIABLE_MAPPINGS["${sys.user_input}"]
        assert mappings["{user}"] == VARIABLE_MAPPINGS["{user}"]
        assert mappings["{role}"] == VARIABLE_MAPPINGS["{role}"]
    
    def test_map_variables_to_config_custom(self):
        """Test mapping custom variables."""
        variables = ["${custom_var}", "{another.var}", "${sys.special}"]
        mappings = self.parser.map_variables_to_config(variables)
        
        # Should generate field names for unmapped variables
        assert "custom_var" in mappings["${custom_var}"]
        assert "another_var" in mappings["{another.var}"]
        assert "sys_special" in mappings["${sys.special}"]
    
    def test_create_parsed_template(self):
        """Test creating ParsedTemplate from parsed information."""
        system_info = {
            'variables': ["${input}", "{user}"],
            'content': "System prompt with ${input} for {user}"
        }
        user_info = {
            'variables': ["{role}", "${context}"],
            'content': "User input with {role} and ${context}"
        }
        test_info = {
            'data': {"input": "test", "context": "test context"},
            'json_variables': ["input", "context"]
        }
        
        parsed = self.parser.create_parsed_template(system_info, user_info, test_info)
        
        assert set(parsed.system_variables) == {"${input}", "{user}"}
        assert set(parsed.user_variables) == {"{role}", "${context}"}
        assert parsed.test_structure == {"input": "test", "context": "test context"}
        assert len(parsed.variable_mappings) == 4  # All unique variables mapped
    
    def test_variable_positions(self):
        """Test finding variable positions in text."""
        text = "Start ${var1} middle {user} end ${var1} final"
        variables = ["${var1}", "{user}"]
        
        positions = self.parser._find_variable_positions(text, variables)
        
        assert len(positions["${var1}"]) == 2  # Appears twice
        assert len(positions["{user}"]) == 1   # Appears once
        assert positions["${var1}"][0] == 6    # First occurrence
        assert positions["{user}"][0] == 21    # User position
    
    def test_analyze_template_structure(self):
        """Test analyzing template structure."""
        content = """Line 1
Line 2 is longer
Short
"""
        structure = self.parser._analyze_template_structure(content)
        
        assert structure['total_lines'] == 4  # Including empty line
        assert structure['non_empty_lines'] == 3
        assert structure['has_multiline'] is True
        assert structure['max_line_length'] == 16  # "Line 2 is longer"
    
    def test_analyze_json_structure(self):
        """Test analyzing JSON structure."""
        data = {
            "level1": {
                "level2": {
                    "level3": "value"
                },
                "simple": "value"
            },
            "list": [1, 2, 3]
        }
        
        structure = self.parser._analyze_json_structure(data)
        
        assert structure['type'] == 'dict'
        assert structure['is_dict'] is True
        assert structure['is_list'] is False
        assert structure['nested_levels'] == 3
        assert structure['total_keys'] == 2
        assert structure['has_nested_objects'] is True
    
    def test_extract_json_variables_nested(self):
        """Test extracting variables from nested JSON."""
        data = {
            "sys": {
                "user_input": ["msg1", "msg2"],
                "context": "test"
            },
            "metadata": {
                "id": 1,
                "tags": ["tag1"]
            }
        }
        
        variables = self.parser._extract_json_variables(data)
        
        expected_vars = ["sys", "sys.user_input", "sys.context", "metadata", "metadata.id", "metadata.tags"]
        assert all(var in variables for var in expected_vars)
    
    def test_has_user_input_structure(self):
        """Test detecting user input structure."""
        # Test with sys.user_input
        data1 = {"sys": {"user_input": ["message"]}}
        assert self.parser._has_user_input_structure(data1) is True
        
        # Test with direct input key
        data2 = {"input": "test", "other": "data"}
        assert self.parser._has_user_input_structure(data2) is True
        
        # Test with query key
        data3 = {"query": "test query"}
        assert self.parser._has_user_input_structure(data3) is True
        
        # Test without user input structure
        data4 = {"config": "value", "settings": "data"}
        assert self.parser._has_user_input_structure(data4) is False
    
    def test_get_data_types(self):
        """Test getting data types from JSON."""
        data = {
            "string_field": "text",
            "int_field": 42,
            "list_field": [1, 2, 3],
            "nested": {
                "bool_field": True,
                "float_field": 3.14
            }
        }
        
        types = self.parser._get_data_types(data)
        
        assert types["string_field"] == "str"
        assert types["int_field"] == "int"
        assert types["list_field"] == "list"
        assert types["nested"] == "dict"
        assert types["nested.bool_field"] == "bool"
        assert types["nested.float_field"] == "float"
    
    def test_is_simple_template(self):
        """Test detecting simple templates."""
        # Simple template
        simple = "Process {input}"
        assert self.parser._is_simple_template(simple) is True
        
        # Complex template (too many lines)
        complex_lines = """Line 1
Line 2
Line 3
Line 4"""
        assert self.parser._is_simple_template(complex_lines) is False
        
        # Complex template (too many variables)
        complex_vars = "Process {var1} {var2} {var3} {var4}"
        assert self.parser._is_simple_template(complex_vars) is False
    
    def test_generate_field_mapping(self):
        """Test generating field mappings for variables."""
        # Test ${} format
        assert self.parser._generate_field_mapping("${sys.user_input}") == "sys_user_input"
        
        # Test {} format
        assert self.parser._generate_field_mapping("{user.name}") == "user_name"
        
        # Test with special characters
        assert self.parser._generate_field_mapping("${field-with@special#chars}") == "field_with_special_chars"
        
        # Test empty/invalid
        assert self.parser._generate_field_mapping("${}") == "unknown_field"
        assert self.parser._generate_field_mapping("") == "unknown_field"
    
    def test_integration_full_parsing_flow(self):
        """Test the complete parsing flow with all components."""
        # Sample templates
        system_prompt = """You are a helpful assistant specialized in data analysis.
Process the user input: ${sys.user_input}
Always address the user as {user} and respect their {role}."""
        
        user_input = "Please analyze: ${input} with context: ${context}"
        
        test_case = """{
    "sys": {
        "user_input": ["Analyze this data", "What are the trends?"]
    },
    "input": "sample data",
    "context": "financial analysis",
    "user": "John",
    "role": "analyst"
}"""
        
        # Parse each component
        system_info = self.parser.parse_system_prompt(system_prompt)
        user_info = self.parser.parse_user_input(user_input)
        test_info = self.parser.parse_test_case(test_case)
        
        # Create parsed template
        parsed = self.parser.create_parsed_template(system_info, user_info, test_info)
        
        # Verify results
        assert parsed.has_variables() is True
        assert len(parsed.get_all_variables()) > 0
        assert "${sys.user_input}" in parsed.system_variables
        assert "{user}" in parsed.system_variables
        assert "{role}" in parsed.system_variables
        assert "${input}" in parsed.user_variables
        assert "${context}" in parsed.user_variables
        
        # Verify mappings
        assert "${sys.user_input}" in parsed.variable_mappings
        assert parsed.variable_mappings["${sys.user_input}"] == "chat_round_30"
        assert parsed.variable_mappings["{user}"] == "{user}"
        assert parsed.variable_mappings["{role}"] == "{role}"
        
        # Verify test structure
        assert parsed.test_structure["sys"]["user_input"] == ["Analyze this data", "What are the trends?"]
        assert parsed.test_structure["user"] == "John"
        assert parsed.test_structure["role"] == "analyst"