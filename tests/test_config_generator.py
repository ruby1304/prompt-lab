"""Tests for the AgentConfigGenerator class."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from src.agent_template_parser.config_generator import AgentConfigGenerator, ConfigGenerationError
from src.agent_template_parser.models import ParsedTemplate, GeneratedConfig


class TestAgentConfigGenerator:
    """Test cases for AgentConfigGenerator."""
    
    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary agents directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def generator(self, temp_agents_dir):
        """Create an AgentConfigGenerator instance for testing."""
        return AgentConfigGenerator(agents_dir=temp_agents_dir)
    
    @pytest.fixture
    def sample_parsed_template(self):
        """Create a sample ParsedTemplate for testing."""
        return ParsedTemplate(
            system_variables=["${input}", "{user}", "{role}"],
            user_variables=["{query}"],
            test_structure={"sys": {"user_input": "test data"}},
            variable_mappings={
                "${input}": "input",
                "{user}": "{user}",
                "{role}": "{role}",
                "{query}": "query"
            }
        )
    
    def test_init(self, temp_agents_dir):
        """Test AgentConfigGenerator initialization."""
        generator = AgentConfigGenerator(agents_dir=temp_agents_dir)
        
        assert generator.agents_dir == Path(temp_agents_dir)
        assert generator.default_judge_agent == "judge_default"
        assert generator.default_judge_flow == "judge_v2"
        assert generator.default_model == "doubao-1-5-pro-32k-250115"
    
    def test_generate_agent_yaml_success(self, generator, sample_parsed_template):
        """Test successful agent YAML generation."""
        agent_name = "test_agent"
        
        config = generator.generate_agent_yaml(sample_parsed_template, agent_name)
        
        # Check required fields
        assert config["id"] == agent_name
        assert config["name"] == "Test Agent"
        assert config["type"] == "task"
        assert "description" in config
        assert "business_goal" in config
        assert "expectations" in config
        assert config["default_testset"] == f"{agent_name}.jsonl"
        
        # Check flows
        assert "flows" in config
        assert len(config["flows"]) == 1
        assert config["flows"][0]["name"] == f"{agent_name}_v1"
        assert config["flows"][0]["file"] == f"{agent_name}_v1.yaml"
        
        # Check evaluation
        assert "evaluation" in config
        eval_config = config["evaluation"]
        assert eval_config["judge_agent_id"] == "judge_default"
        assert eval_config["judge_flow"] == "judge_v2"
        assert eval_config["scale"]["min"] == 0
        assert eval_config["scale"]["max"] == 10
        
        # Check case fields
        assert "case_fields" in config
        assert len(config["case_fields"]) > 0
    
    def test_generate_agent_yaml_empty_name(self, generator, sample_parsed_template):
        """Test agent YAML generation with empty name."""
        with pytest.raises(ConfigGenerationError, match="Agent name cannot be empty"):
            generator.generate_agent_yaml(sample_parsed_template, "")
    
    def test_generate_agent_yaml_none_parsed_data(self, generator):
        """Test agent YAML generation with None parsed data."""
        with pytest.raises(ConfigGenerationError, match="Parsed data cannot be None"):
            generator.generate_agent_yaml(None, "test_agent")
    
    def test_generate_prompt_yaml_success(self, generator, sample_parsed_template):
        """Test successful prompt YAML generation."""
        agent_name = "test_agent"
        
        config = generator.generate_prompt_yaml(sample_parsed_template, agent_name)
        
        # Check required fields
        assert config["name"] == f"flow_{agent_name}_v1"
        assert "description" in config
        assert "system_prompt" in config
        assert "user_template" in config
        assert "defaults" in config
        
        # Check defaults contain expected variables
        defaults = config["defaults"]
        assert "user" in defaults
        assert "role" in defaults
        assert defaults["user"] == "{user}"
        assert defaults["role"] == "{role}"
    
    def test_generate_prompt_yaml_empty_name(self, generator, sample_parsed_template):
        """Test prompt YAML generation with empty name."""
        with pytest.raises(ConfigGenerationError, match="Agent name cannot be empty"):
            generator.generate_prompt_yaml(sample_parsed_template, "")
    
    def test_generate_prompt_yaml_none_parsed_data(self, generator):
        """Test prompt YAML generation with None parsed data."""
        with pytest.raises(ConfigGenerationError, match="Parsed data cannot be None"):
            generator.generate_prompt_yaml(None, "test_agent")
    
    def test_generate_prompt_yaml_with_original_content(self, generator, sample_parsed_template):
        """Test prompt YAML generation with original template content."""
        agent_name = "test_agent"
        original_system = "You are a specialized assistant. Process: ${input}"
        original_user = "Please analyze: {query}"
        
        config = generator.generate_prompt_yaml(
            sample_parsed_template, 
            agent_name, 
            original_system, 
            original_user
        )
        
        # Check that original content is used
        assert config["system_prompt"] == original_system
        assert config["user_template"] == original_user
        assert config["name"] == f"flow_{agent_name}_v1"
    
    def test_validate_config_format_valid_agent(self, generator):
        """Test validation of valid agent configuration."""
        valid_agent_config = {
            "id": "test_agent",
            "name": "Test Agent",
            "type": "task",
            "flows": [{"name": "test_v1", "file": "test_v1.yaml"}],
            "evaluation": {
                "judge_agent_id": "judge_default",
                "scale": {"min": 0, "max": 10}
            }
        }
        
        errors = generator.validate_config_format(valid_agent_config)
        assert len(errors) == 0
    
    def test_validate_config_format_valid_prompt(self, generator):
        """Test validation of valid prompt configuration."""
        valid_prompt_config = {
            "name": "test_flow",
            "system_prompt": "You are a helpful assistant.",
            "user_template": "Process this: {input}",
            "defaults": {"input": "default"}
        }
        
        errors = generator.validate_config_format(valid_prompt_config)
        assert len(errors) == 0
    
    def test_validate_config_format_invalid_agent(self, generator):
        """Test validation of invalid agent configuration."""
        invalid_agent_config = {
            "id": "test_agent",
            # Missing required fields
        }
        
        errors = generator.validate_config_format(invalid_agent_config)
        assert len(errors) > 0
        assert any("Missing required field" in error for error in errors)
    
    def test_validate_config_format_invalid_prompt(self, generator):
        """Test validation of invalid prompt configuration."""
        invalid_prompt_config = {
            "name": "test_flow",
            # Missing system_prompt
        }
        
        errors = generator.validate_config_format(invalid_prompt_config)
        assert len(errors) > 0
        assert any("Missing required field" in error for error in errors)
    
    def test_validate_config_format_not_dict(self, generator):
        """Test validation of non-dictionary configuration."""
        errors = generator.validate_config_format("not a dict")
        assert len(errors) == 1
        assert "Configuration must be a dictionary" in errors[0]
    
    def test_save_config_files_success(self, generator, sample_parsed_template):
        """Test successful configuration file saving."""
        agent_name = "test_agent"
        agent_config = generator.generate_agent_yaml(sample_parsed_template, agent_name)
        prompt_config = generator.generate_prompt_yaml(sample_parsed_template, agent_name)
        
        # Save files
        generator.save_config_files(agent_config, prompt_config, agent_name)
        
        # Check that directories were created
        agent_dir = generator.agents_dir / agent_name
        assert agent_dir.exists()
        assert (agent_dir / "prompts").exists()
        assert (agent_dir / "testsets").exists()
        
        # Check that files were created
        agent_yaml_path = agent_dir / "agent.yaml"
        prompt_yaml_path = agent_dir / "prompts" / f"{agent_name}_v1.yaml"
        
        assert agent_yaml_path.exists()
        assert prompt_yaml_path.exists()
        
        # Verify file contents
        with open(agent_yaml_path, 'r', encoding='utf-8') as f:
            saved_agent_config = yaml.safe_load(f)
            assert saved_agent_config["id"] == agent_name
        
        with open(prompt_yaml_path, 'r', encoding='utf-8') as f:
            saved_prompt_config = yaml.safe_load(f)
            assert saved_prompt_config["name"] == f"flow_{agent_name}_v1"
    
    def test_save_config_files_empty_name(self, generator):
        """Test configuration file saving with empty name."""
        with pytest.raises(ConfigGenerationError, match="Agent name cannot be empty"):
            generator.save_config_files({}, {}, "")
    
    def test_generate_complete_config_success(self, generator, sample_parsed_template):
        """Test complete configuration generation."""
        agent_name = "test_agent"
        
        result = generator.generate_complete_config(sample_parsed_template, agent_name)
        
        assert isinstance(result, GeneratedConfig)
        assert result.agent_name == agent_name
        assert result.agent_config is not None
        assert result.prompt_config is not None
        assert isinstance(result.validation_errors, list)
        assert isinstance(result.needs_llm_enhancement, bool)
        
        # Should be valid if no errors
        if len(result.validation_errors) == 0:
            assert result.is_valid()
    
    def test_generate_display_name(self, generator):
        """Test display name generation."""
        assert generator._generate_display_name("test_agent") == "Test Agent"
        assert generator._generate_display_name("my-cool-agent") == "My Cool Agent"
        assert generator._generate_display_name("simple") == "Simple"
    
    def test_generate_case_fields(self, generator, sample_parsed_template):
        """Test case fields generation."""
        case_fields = generator._generate_case_fields(sample_parsed_template)
        
        assert isinstance(case_fields, list)
        assert len(case_fields) > 0
        
        # Check that all case fields have required properties
        for field in case_fields:
            assert "key" in field
            assert "label" in field
            assert "section" in field
            assert "required" in field
    
    def test_variable_to_field_name(self, generator):
        """Test variable to field name conversion."""
        assert generator._variable_to_field_name("${input}") == "input"
        assert generator._variable_to_field_name("{user}") == "user"
        assert generator._variable_to_field_name("${sys.user_input}") == "sys_user_input"
    
    def test_generate_field_label(self, generator):
        """Test field label generation."""
        assert generator._generate_field_label("${input}") == "Input"
        assert generator._generate_field_label("{user_name}") == "User Name"
        assert generator._generate_field_label("${sys.user_input}") == "Sys User Input"
    
    def test_determine_field_section(self, generator):
        """Test field section determination."""
        assert generator._determine_field_section("{user}") == "context"
        assert generator._determine_field_section("{role}") == "context"
        assert generator._determine_field_section("${input}") == "primary_input"
        assert generator._determine_field_section("${query}") == "primary_input"
        assert generator._determine_field_section("${other}") == "context"
    
    def test_is_required_field(self, generator):
        """Test required field determination."""
        assert generator._is_required_field("${input}") == True
        assert generator._is_required_field("${query}") == True
        assert generator._is_required_field("${data}") == True
        assert generator._is_required_field("{user}") == False
        assert generator._is_required_field("{role}") == False
    
    def test_needs_enhancement(self, generator):
        """Test enhancement need determination."""
        # Simple template - no enhancement needed
        simple_template = ParsedTemplate(
            system_variables=["{user}"],
            user_variables=[],
            test_structure={},
            variable_mappings={"{user}": "{user}"}
        )
        assert not generator._needs_enhancement(simple_template)
        
        # Complex template - enhancement needed
        complex_template = ParsedTemplate(
            system_variables=["${var1}", "${var2}", "${var3}", "${var4}", "${var5}", "${var6}"],
            user_variables=[],
            test_structure={"a": 1, "b": 2, "c": 3, "d": 4},
            variable_mappings={}
        )
        assert generator._needs_enhancement(complex_template)


class TestConfigGenerationIntegration:
    """Integration tests for configuration generation."""
    
    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary agents directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def generator(self, temp_agents_dir):
        """Create an AgentConfigGenerator instance for testing."""
        return AgentConfigGenerator(agents_dir=temp_agents_dir)
    
    def test_end_to_end_config_generation(self, generator):
        """Test end-to-end configuration generation and saving."""
        # Create sample parsed template
        parsed_template = ParsedTemplate(
            system_variables=["${fullContent}", "{user}", "{role}"],
            user_variables=[],
            test_structure={"sys": {"user_input": ["conversation data"]}},
            variable_mappings={
                "${fullContent}": "fullContent",
                "{user}": "{user}",
                "{role}": "{role}"
            }
        )
        
        agent_name = "integration_test_agent"
        
        # Generate complete configuration
        result = generator.generate_complete_config(parsed_template, agent_name)
        
        # Verify result
        assert result.agent_name == agent_name
        assert result.agent_config is not None
        assert result.prompt_config is not None
        
        # Save configuration files
        generator.save_config_files(
            result.agent_config,
            result.prompt_config,
            agent_name
        )
        
        # Verify files exist and are valid YAML
        agent_dir = generator.agents_dir / agent_name
        agent_yaml_path = agent_dir / "agent.yaml"
        prompt_yaml_path = agent_dir / "prompts" / f"{agent_name}_v1.yaml"
        
        assert agent_yaml_path.exists()
        assert prompt_yaml_path.exists()
        
        # Load and verify YAML files
        with open(agent_yaml_path, 'r', encoding='utf-8') as f:
            loaded_agent_config = yaml.safe_load(f)
            assert loaded_agent_config["id"] == agent_name
            assert "flows" in loaded_agent_config
            assert "evaluation" in loaded_agent_config
        
        with open(prompt_yaml_path, 'r', encoding='utf-8') as f:
            loaded_prompt_config = yaml.safe_load(f)
            assert "system_prompt" in loaded_prompt_config
            assert "defaults" in loaded_prompt_config