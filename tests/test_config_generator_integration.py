"""Integration tests for the complete configuration generation workflow."""

import pytest
import tempfile
import yaml
from pathlib import Path

from src.agent_template_parser import (
    TemplateManager, 
    TemplateParser, 
    AgentConfigGenerator,
    TemplateData
)


class TestConfigGenerationWorkflow:
    """Test the complete workflow from templates to configuration files."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            templates_dir = temp_path / "templates"
            agents_dir = temp_path / "agents"
            yield {
                'templates': str(templates_dir),
                'agents': str(agents_dir)
            }
    
    @pytest.fixture
    def sample_templates(self):
        """Sample template content for testing."""
        return {
            'system_prompt': """You are a conversation summarizer.
Your task is to summarize conversations between {user} and {role}.

Input data:
{fullContent}

Requirements:
- Generate 4-10 sentences
- Use third person perspective
- Replace user references with {user}
- Replace role references with {role}""",
            
            'user_input': "Begin summarization.",
            
            'test_case': """{
    "sys": {
        "user_input": [
            "User: Hello, how are you?",
            "Assistant: I'm doing well, thank you!"
        ]
    },
    "fullContent": "2024-01-01 Morning: User greeted Assistant warmly.",
    "user": "{user}",
    "role": "{role}"
}"""
        }
    
    def test_complete_workflow(self, temp_dirs, sample_templates):
        """Test the complete workflow from templates to saved configuration files."""
        # Initialize components
        template_manager = TemplateManager(template_dir=temp_dirs['templates'])
        template_parser = TemplateParser()
        config_generator = AgentConfigGenerator(agents_dir=temp_dirs['agents'])
        
        agent_name = "conversation_summarizer"
        
        # Step 1: Create template directory structure
        template_manager.create_directory_structure()
        
        # Step 2: Save template files
        template_paths = template_manager.save_template_files(
            system_prompt=sample_templates['system_prompt'],
            user_input=sample_templates['user_input'],
            test_case=sample_templates['test_case'],
            agent_name=agent_name
        )
        
        # Verify template files were saved
        assert template_paths['system_prompt'].exists()
        assert template_paths['user_input'].exists()
        assert template_paths['test_case'].exists()
        
        # Step 3: Parse templates
        system_info = template_parser.parse_system_prompt(sample_templates['system_prompt'])
        user_info = template_parser.parse_user_input(sample_templates['user_input'])
        test_info = template_parser.parse_test_case(sample_templates['test_case'])
        
        # Create parsed template object
        parsed_template = template_parser.create_parsed_template(system_info, user_info, test_info)
        
        # Verify parsing results
        assert len(parsed_template.system_variables) > 0
        assert '{user}' in parsed_template.system_variables
        assert '{role}' in parsed_template.system_variables
        assert '{fullContent}' in parsed_template.system_variables
        
        # Step 4: Generate configurations
        generated_config = config_generator.generate_complete_config(
            parsed_template, 
            agent_name,
            original_system_prompt=sample_templates['system_prompt'],
            original_user_template=sample_templates['user_input']
        )
        
        # Verify configuration generation
        assert generated_config.agent_name == agent_name
        assert generated_config.agent_config is not None
        assert generated_config.prompt_config is not None
        
        # Check that original content is preserved
        assert generated_config.prompt_config['system_prompt'] == sample_templates['system_prompt']
        assert generated_config.prompt_config['user_template'] == sample_templates['user_input']
        
        # Step 5: Save configuration files
        config_generator.save_config_files(
            generated_config.agent_config,
            generated_config.prompt_config,
            agent_name
        )
        
        # Step 6: Verify saved files
        agents_path = Path(temp_dirs['agents'])
        agent_dir = agents_path / agent_name
        
        # Check directory structure
        assert agent_dir.exists()
        assert (agent_dir / "prompts").exists()
        assert (agent_dir / "testsets").exists()
        
        # Check configuration files
        agent_yaml_path = agent_dir / "agent.yaml"
        prompt_yaml_path = agent_dir / "prompts" / f"{agent_name}_v1.yaml"
        
        assert agent_yaml_path.exists()
        assert prompt_yaml_path.exists()
        
        # Step 7: Verify file contents
        with open(agent_yaml_path, 'r', encoding='utf-8') as f:
            saved_agent_config = yaml.safe_load(f)
            
        with open(prompt_yaml_path, 'r', encoding='utf-8') as f:
            saved_prompt_config = yaml.safe_load(f)
        
        # Verify agent configuration
        assert saved_agent_config['id'] == agent_name
        assert saved_agent_config['name'] == "Conversation Summarizer"
        assert saved_agent_config['type'] == "task"
        assert 'flows' in saved_agent_config
        assert 'evaluation' in saved_agent_config
        assert 'case_fields' in saved_agent_config
        
        # Verify prompt configuration
        assert saved_prompt_config['name'] == f"flow_{agent_name}_v1"
        assert saved_prompt_config['system_prompt'] == sample_templates['system_prompt']
        assert saved_prompt_config['user_template'] == sample_templates['user_input']
        assert 'defaults' in saved_prompt_config
        
        # Verify defaults contain expected variables
        defaults = saved_prompt_config['defaults']
        assert 'user' in defaults
        assert 'role' in defaults
        assert defaults['user'] == '{user}'
        assert defaults['role'] == '{role}'
    
    def test_workflow_with_validation_errors(self, temp_dirs):
        """Test workflow handling when there are validation errors."""
        config_generator = AgentConfigGenerator(agents_dir=temp_dirs['agents'])
        template_parser = TemplateParser()
        
        # Create a minimal parsed template that might cause validation issues
        parsed_template = template_parser.create_parsed_template(
            system_info={'variables': [], 'content': 'Simple prompt'},
            user_info={'variables': [], 'content': 'Simple input'},
            test_info={'data': {}}
        )
        
        agent_name = "simple_agent"
        
        # Generate configuration
        generated_config = config_generator.generate_complete_config(
            parsed_template, 
            agent_name
        )
        
        # Should still generate valid configuration even with simple input
        assert generated_config.agent_name == agent_name
        assert generated_config.agent_config is not None
        assert generated_config.prompt_config is not None
        
        # Should be able to save even if there are minor validation issues
        config_generator.save_config_files(
            generated_config.agent_config,
            generated_config.prompt_config,
            agent_name
        )
        
        # Verify files were created
        agents_path = Path(temp_dirs['agents'])
        agent_dir = agents_path / agent_name
        assert (agent_dir / "agent.yaml").exists()
        assert (agent_dir / "prompts" / f"{agent_name}_v1.yaml").exists()
    
    def test_workflow_with_complex_variables(self, temp_dirs):
        """Test workflow with complex variable structures."""
        template_parser = TemplateParser()
        config_generator = AgentConfigGenerator(agents_dir=temp_dirs['agents'])
        
        # Complex template with multiple variable types
        complex_system_prompt = """
        Process the following data:
        - User input: ${sys.user_input}
        - Context: ${context}
        - Query: {query}
        - User reference: {user}
        - Role reference: {role}
        - Additional data: ${additional_data}
        """
        
        complex_user_input = "Analyze: {input_data} with context {context_info}"
        
        complex_test_case = """{
            "sys": {
                "user_input": ["complex", "data", "structure"]
            },
            "context": "test context",
            "query": "test query",
            "input_data": "sample input",
            "context_info": "sample context"
        }"""
        
        # Parse templates
        system_info = template_parser.parse_system_prompt(complex_system_prompt)
        user_info = template_parser.parse_user_input(complex_user_input)
        test_info = template_parser.parse_test_case(complex_test_case)
        
        parsed_template = template_parser.create_parsed_template(system_info, user_info, test_info)
        
        agent_name = "complex_agent"
        
        # Generate and save configuration
        generated_config = config_generator.generate_complete_config(
            parsed_template, 
            agent_name,
            original_system_prompt=complex_system_prompt,
            original_user_template=complex_user_input
        )
        
        config_generator.save_config_files(
            generated_config.agent_config,
            generated_config.prompt_config,
            agent_name
        )
        
        # Verify complex configuration was handled correctly
        agents_path = Path(temp_dirs['agents'])
        agent_yaml_path = agents_path / agent_name / "agent.yaml"
        
        with open(agent_yaml_path, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        
        # Should have case fields for all the variables
        case_fields = saved_config['case_fields']
        field_keys = [field['key'] for field in case_fields]
        
        # Check that major variables are represented
        assert any('input' in key for key in field_keys)
        assert any('context' in key for key in field_keys)
        assert any('query' in key for key in field_keys)