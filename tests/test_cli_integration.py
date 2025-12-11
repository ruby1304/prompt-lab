"""Integration tests for CLI workflow - end-to-end testing of enhanced functionality."""

import json
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from src.agent_template_parser.cli import AgentTemplateParserCLI, main
from src.agent_template_parser.error_handler import (
    InvalidFolderStructureError, 
    MissingAgentFolderError
)


class TestCLIIntegrationWorkflow:
    """Integration tests for the complete CLI workflow."""
    
    def setup_method(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Change to temp directory for tests
        import os
        os.chdir(self.temp_dir)
        
        # Set up fixtures path
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "templates"
        
        # Initialize CLI
        self.cli = AgentTemplateParserCLI()
    
    def teardown_method(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _copy_fixture_to_temp(self, fixture_name: str, target_name: str = None):
        """Copy a fixture to the temp directory."""
        if target_name is None:
            target_name = fixture_name
        
        source = self.fixtures_dir / fixture_name
        target = Path(self.temp_dir) / "templates" / target_name
        
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    
    def _create_agent_folder(self, agent_name: str, system_content: str, user_content: str, case_content: str):
        """Create a complete agent folder structure."""
        agent_dir = Path(self.temp_dir) / "templates" / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        (agent_dir / "system_prompt").write_text(system_content)
        (agent_dir / "user_input").write_text(user_content)
        (agent_dir / "case").write_text(case_content)
        
        return agent_dir
    
    def _create_legacy_structure(self, agent_name: str, system_content: str, user_content: str, case_content: str):
        """Create a complete legacy structure."""
        templates_dir = Path(self.temp_dir) / "templates"
        
        # Create directories
        (templates_dir / "system_prompts").mkdir(parents=True, exist_ok=True)
        (templates_dir / "user_inputs").mkdir(parents=True, exist_ok=True)
        (templates_dir / "test_cases").mkdir(parents=True, exist_ok=True)
        
        # Create files
        (templates_dir / "system_prompts" / f"{agent_name}_system.txt").write_text(system_content)
        (templates_dir / "user_inputs" / f"{agent_name}_user.txt").write_text(user_content)
        (templates_dir / "test_cases" / f"{agent_name}_test.json").write_text(case_content)
    
    def test_end_to_end_folder_structure_workflow(self):
        """Test complete end-to-end workflow using folder structure."""
        agent_name = "test_folder_agent"
        
        # Create folder structure
        system_content = "You are a helpful test assistant for folder structure testing."
        user_content = "Please help with: ${input}"
        case_content = '{"input": "test request", "expected": "helpful response"}'
        
        self._create_agent_folder(agent_name, system_content, user_content, case_content)
        
        # Mock the config generation and saving to avoid file system dependencies
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch('builtins.print') as mock_print:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name, "flows": {}}
            mock_prompt_gen.return_value = {"system_prompt": system_content}
            mock_validate.return_value = []  # No validation errors
            
            # Execute the simplified workflow
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=False)
            
            # Verify the workflow executed successfully
            mock_agent_gen.assert_called_once()
            mock_prompt_gen.assert_called_once()
            mock_save.assert_called_once()
            
            # Check success message was printed
            mock_print.assert_any_call(f"✅ Agent '{agent_name}' created successfully!")
    
    def test_end_to_end_legacy_structure_workflow(self):
        """Test complete end-to-end workflow using legacy structure."""
        agent_name = "test_legacy_agent"
        
        # Create legacy structure
        system_content = "You are a helpful test assistant for legacy structure testing."
        user_content = "Please help with: ${input}"
        case_content = '{"input": "test request", "expected": "helpful response"}'
        
        self._create_legacy_structure(agent_name, system_content, user_content, case_content)
        
        # Mock the config generation and saving
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch('builtins.print') as mock_print:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name, "flows": {}}
            mock_prompt_gen.return_value = {"system_prompt": system_content}
            mock_validate.return_value = []  # No validation errors
            
            # Execute the simplified workflow (should detect and use legacy structure)
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=False)
            
            # Verify the workflow executed successfully
            mock_agent_gen.assert_called_once()
            mock_prompt_gen.assert_called_once()
            mock_save.assert_called_once()
            
            # Check success message was printed
            mock_print.assert_any_call(f"✅ Agent '{agent_name}' created successfully!")
    
    def test_end_to_end_mixed_structure_prefers_folder(self):
        """Test end-to-end workflow with mixed structure prefers folder."""
        agent_name = "test_mixed_agent"
        
        # Create both structures
        folder_system = "You are a folder structure assistant (preferred)."
        folder_user = "Folder input: ${input}"
        folder_case = '{"input": "folder test", "structure": "folder"}'
        
        legacy_system = "You are a legacy structure assistant (not preferred)."
        legacy_user = "Legacy input: ${input}"
        legacy_case = '{"input": "legacy test", "structure": "legacy"}'
        
        self._create_agent_folder(agent_name, folder_system, folder_user, folder_case)
        self._create_legacy_structure(agent_name, legacy_system, legacy_user, legacy_case)
        
        # Mock the config generation and saving
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch('builtins.print') as mock_print:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name, "flows": {}}
            mock_prompt_gen.return_value = {"system_prompt": "mocked"}
            mock_validate.return_value = []
            
            # Execute the workflow
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=False)
            
            # Verify it used folder structure (check the parsed data passed to config generator)
            call_args = mock_agent_gen.call_args[0][0]  # First argument to generate_agent_yaml
            assert "folder structure assistant" in call_args['system_prompt']['content']
            assert "Folder input" in call_args['user_input']['content']
            
            # Check success message
            mock_print.assert_any_call(f"✅ Agent '{agent_name}' created successfully!")
    
    def test_backward_compatibility_legacy_command(self):
        """Test backward compatibility with legacy create-agent command."""
        agent_name = "test_legacy_command"
        
        # Create template files in temp directory
        system_file = Path(self.temp_dir) / "system.txt"
        user_file = Path(self.temp_dir) / "user.txt"
        case_file = Path(self.temp_dir) / "case.json"
        
        system_content = "You are a legacy command test assistant."
        user_content = "Legacy command input: ${input}"
        case_content = '{"input": "legacy command test"}'
        
        system_file.write_text(system_content)
        user_file.write_text(user_content)
        case_file.write_text(case_content)
        
        # Mock the config generation and saving
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch('builtins.print') as mock_print:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name, "flows": {}}
            mock_prompt_gen.return_value = {"system_prompt": system_content}
            mock_validate.return_value = []
            
            # Execute the legacy workflow
            self.cli.create_agent_from_templates(
                str(system_file), str(user_file), str(case_file), agent_name, use_llm_enhancement=False
            )
            
            # Verify the workflow executed successfully
            mock_agent_gen.assert_called_once()
            mock_prompt_gen.assert_called_once()
            mock_save.assert_called_once()
            
            # Check success message
            mock_print.assert_any_call(f"✅ Agent '{agent_name}' created successfully!")
    
    def test_error_handling_missing_agent_folder(self):
        """Test error handling when agent folder doesn't exist."""
        agent_name = "nonexistent_agent"
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            self.cli.create_agent_simple(agent_name)
            
            # Verify error handling
            mock_exit.assert_called_once_with(1)
            
            # Check that helpful error messages were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("No template files found" in call for call in print_calls)
            assert any("Expected folder structure" in call for call in print_calls)
    
    def test_error_handling_invalid_folder_structure(self):
        """Test error handling with invalid folder structure."""
        agent_name = "invalid_structure_agent"
        
        # Create folder with missing files
        agent_dir = Path(self.temp_dir) / "templates" / agent_name
        agent_dir.mkdir(parents=True)
        (agent_dir / "system_prompt").write_text("Valid system prompt")
        # Missing user_input and case files
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            self.cli.create_agent_simple(agent_name)
            
            # Verify error handling
            mock_exit.assert_called_once_with(1)
            
            # Check that helpful error messages were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Invalid folder structure" in call for call in print_calls)
    
    def test_error_handling_empty_template_files(self):
        """Test error handling with empty template files."""
        agent_name = "empty_files_agent"
        
        # Create folder with empty files
        self._create_agent_folder(agent_name, "", "Valid user input", '{"valid": "json"}')
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            self.cli.create_agent_simple(agent_name)
            
            # Verify error handling
            mock_exit.assert_called_once_with(1)
            
            # Check that parsing error was handled
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Error creating agent" in call for call in print_calls)
    
    def test_error_handling_invalid_json(self):
        """Test error handling with invalid JSON in test case."""
        agent_name = "invalid_json_agent"
        
        # Create folder with invalid JSON
        self._create_agent_folder(
            agent_name, 
            "Valid system prompt", 
            "Valid user input", 
            '{"invalid": json, "missing": "quotes"}'
        )
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            self.cli.create_agent_simple(agent_name)
            
            # Verify error handling
            mock_exit.assert_called_once_with(1)
            
            # Check that JSON error guidance was provided
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("JSON Format Issue" in call for call in print_calls)
    
    def test_helpful_error_guidance_and_suggestions(self):
        """Test that helpful error guidance and suggestions are provided."""
        agent_name = "guidance_test_agent"
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            self.cli.create_agent_simple(agent_name)
            
            # Verify error handling
            mock_exit.assert_called_once_with(1)
            
            # Check that comprehensive guidance was provided
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            
            # Should include error message
            assert any("Error creating agent" in call for call in print_calls)
            
            # Should include folder structure help
            assert any("Expected folder structure" in call for call in print_calls)
            
            # Should include common fixes suggestions
            assert any("Checking for common issues" in call for call in print_calls)
            assert any("Directory missing" in call for call in print_calls)
            assert any("mkdir -p" in call for call in print_calls)
    
    def test_llm_enhancement_integration(self):
        """Test integration with LLM enhancement for config fixing."""
        agent_name = "llm_enhancement_agent"
        
        # Create valid folder structure
        self._create_agent_folder(
            agent_name,
            "You are a test assistant.",
            "Help with: ${input}",
            '{"input": "test"}'
        )
        
        # Mock config generation with validation errors
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch.object(self.cli.llm_enhancer, 'fix_config_format') as mock_llm_fix, \
             patch('builtins.print') as mock_print:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name, "invalid": "format"}
            mock_prompt_gen.return_value = {"system_prompt": "test"}
            mock_validate.side_effect = [["Format error"], []]  # Agent config has error, prompt is fine
            mock_llm_fix.return_value = {"name": agent_name, "flows": {}}  # Fixed config
            
            # Execute with LLM enhancement enabled
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=True)
            
            # Verify LLM enhancement was called
            mock_llm_fix.assert_called_once()
            mock_save.assert_called_once()
            
            # Check enhancement message was printed
            mock_print.assert_any_call("Configuration has format issues, applying LLM enhancement...")
            mock_print.assert_any_call("LLM enhancement completed successfully")
    
    def test_llm_enhancement_failure_handling(self):
        """Test handling of LLM enhancement failures."""
        agent_name = "llm_failure_agent"
        
        # Create valid folder structure
        self._create_agent_folder(
            agent_name,
            "You are a test assistant.",
            "Help with: ${input}",
            '{"input": "test"}'
        )
        
        # Mock LLM enhancement failure
        from src.agent_template_parser.llm_enhancer import LLMEnhancementError
        
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch.object(self.cli.llm_enhancer, 'fix_config_format') as mock_llm_fix, \
             patch('builtins.print') as mock_print:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name, "invalid": "format"}
            mock_prompt_gen.return_value = {"system_prompt": "test"}
            mock_validate.return_value = ["Format error"]
            mock_llm_fix.side_effect = LLMEnhancementError("API key not configured")
            
            # Execute with LLM enhancement enabled
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=True)
            
            # Verify LLM enhancement was attempted but failed gracefully
            mock_llm_fix.assert_called_once()
            mock_save.assert_called_once()  # Should still save despite LLM failure
            
            # Check warning messages were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("LLM enhancement failed" in call for call in print_calls)
            assert any("Check your OpenAI API key" in call for call in print_calls)
    
    def test_validation_workflow_integration(self):
        """Test integration of template validation workflow."""
        agent_name = "validation_test_agent"
        
        # Create valid folder structure
        self._create_agent_folder(
            agent_name,
            "You are a validation test assistant.",
            "Help with: ${input}",
            '{"input": "validation test"}'
        )
        
        with patch('builtins.print') as mock_print:
            # Test validation
            self.cli.validate_templates(agent_name)
            
            # Check validation messages
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Template files loaded successfully" in call for call in print_calls)
            assert any("System prompt template is valid" in call for call in print_calls)
            assert any("User input template is valid" in call for call in print_calls)
            assert any("Test case template is valid" in call for call in print_calls)
    
    def test_list_templates_integration(self):
        """Test integration of list templates functionality."""
        # Create some template structures
        self._create_agent_folder("agent1", "System 1", "User 1", '{"test": 1}')
        self._create_legacy_structure("agent2", "System 2", "User 2", '{"test": 2}')
        
        with patch('builtins.print') as mock_print:
            self.cli.list_templates()
            
            # Check that templates were listed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Available templates" in call for call in print_calls)


class TestCLIMainIntegration:
    """Integration tests for CLI main function with argument parsing."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Change to temp directory for tests
        import os
        os.chdir(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_agent_folder(self, agent_name: str):
        """Create a test agent folder."""
        agent_dir = Path(self.temp_dir) / "templates" / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        (agent_dir / "system_prompt").write_text("You are a test assistant.")
        (agent_dir / "user_input").write_text("Help with: ${input}")
        (agent_dir / "case").write_text('{"input": "test"}')
        
        return agent_dir
    
    @patch('sys.argv', ['cli.py', 'create-agent', 'test_agent'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_simplified_command_integration(self, mock_cli_class):
        """Test main function integration with simplified command."""
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        # Verify simplified method was called
        mock_cli.create_agent_simple.assert_called_once_with('test_agent', use_llm_enhancement=True)
    
    @patch('sys.argv', ['cli.py', 'create-agent', 'test_agent', '--no-llm-enhancement'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_simplified_command_no_llm(self, mock_cli_class):
        """Test main function with simplified command and no LLM enhancement."""
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        # Verify LLM enhancement was disabled
        mock_cli.create_agent_simple.assert_called_once_with('test_agent', use_llm_enhancement=False)
    
    @patch('sys.argv', ['cli.py', 'create-agent', 
                       '--system-prompt', 'system.txt',
                       '--user-input', 'user.txt',
                       '--test-case', 'case.json',
                       '--agent-name', 'legacy_agent'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_legacy_command_integration(self, mock_cli_class):
        """Test main function integration with legacy command."""
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        # Verify legacy method was called
        mock_cli.create_agent_from_templates.assert_called_once_with(
            'system.txt', 'user.txt', 'case.json', 'legacy_agent', use_llm_enhancement=True
        )
    
    @patch('sys.argv', ['cli.py', 'create-agent', '--system-prompt', 'system.txt'])
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_invalid_arguments_integration(self, mock_exit, mock_print):
        """Test main function with invalid argument combinations."""
        main()
        
        # Verify error handling
        mock_exit.assert_called_once_with(1)
        
        # Check error messages
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("Invalid arguments" in call for call in print_calls)
        assert any("RECOMMENDED USAGE" in call for call in print_calls)
    
    @patch('sys.argv', ['cli.py', 'validate-templates', '--agent-name', 'test_agent'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_validate_command_integration(self, mock_cli_class):
        """Test main function integration with validate command."""
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        # Verify validate method was called
        mock_cli.validate_templates.assert_called_once_with('test_agent')
    
    @patch('sys.argv', ['cli.py', 'list-templates'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_list_command_integration(self, mock_cli_class):
        """Test main function integration with list command."""
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        # Verify list method was called
        mock_cli.list_templates.assert_called_once()
    
    @patch('sys.argv', ['cli.py'])
    @patch('argparse.ArgumentParser.print_help')
    def test_main_no_command_integration(self, mock_print_help):
        """Test main function with no command shows help."""
        main()
        
        mock_print_help.assert_called_once()


class TestCLIErrorRecoveryIntegration:
    """Integration tests for error recovery mechanisms in CLI."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        import os
        os.chdir(self.temp_dir)
        
        self.cli = AgentTemplateParserCLI()
    
    def teardown_method(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_recovery_with_fallback_template(self):
        """Test error recovery using fallback template."""
        agent_name = "recovery_test_agent"
        
        # Create folder with problematic content that will cause parsing errors
        agent_dir = Path(self.temp_dir) / "templates" / agent_name
        agent_dir.mkdir(parents=True)
        (agent_dir / "system_prompt").write_text("Invalid ${unclosed variable")
        (agent_dir / "user_input").write_text("Valid user input")
        (agent_dir / "case").write_text('{"valid": "json"}')
        
        # Mock error recovery to return fallback data
        with patch.object(self.cli.error_recovery, 'handle_error') as mock_recovery, \
             patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save, \
             patch('builtins.print') as mock_print:
            
            # Set up recovery mock
            from src.agent_template_parser.error_handler import RecoveryResult
            mock_recovery.return_value = RecoveryResult(
                success=True,
                recovered_data={
                    'system_prompt': {'content': 'Fallback system prompt', 'variables': []},
                    'user_input': {'content': 'Fallback user input', 'variables': []},
                    'test_case': {'structure': {}},
                    'agent_name': agent_name
                },
                fallback_used=True,
                warnings=["Using fallback template due to parsing error"]
            )
            
            # Set up config generation mocks
            mock_agent_gen.return_value = {"name": agent_name}
            mock_prompt_gen.return_value = {"system_prompt": "fallback"}
            mock_validate.return_value = []
            
            # Execute the workflow
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=False)
            
            # Verify recovery was used
            mock_recovery.assert_called()
            mock_save.assert_called_once()
            
            # Check warning was printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Using fallback template" in call for call in print_calls)
    
    def test_error_recovery_suggestions_integration(self):
        """Test that error recovery suggestions are properly integrated."""
        agent_name = "suggestions_test_agent"
        
        with patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit, \
             patch.object(self.cli.error_recovery, 'handle_error') as mock_recovery:
            
            # Set up recovery mock with suggestions
            from src.agent_template_parser.error_handler import RecoveryResult
            mock_recovery.return_value = RecoveryResult(
                success=False,
                warnings=["Template structure is incomplete"],
                suggestions=[
                    "Create the missing template directory",
                    "Add required template files",
                    "Check file permissions"
                ]
            )
            
            # Execute the workflow
            self.cli.create_agent_simple(agent_name)
            
            # Verify error handling
            mock_exit.assert_called_once_with(1)
            
            # Check that suggestions were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Additional suggestions" in call for call in print_calls)
            assert any("Create the missing template directory" in call for call in print_calls)


class TestCLIPerformanceIntegration:
    """Integration tests for CLI performance and resource usage."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        import os
        os.chdir(self.temp_dir)
        
        self.cli = AgentTemplateParserCLI()
    
    def teardown_method(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_large_template_file_handling(self):
        """Test handling of large template files."""
        agent_name = "large_template_agent"
        
        # Create large template content
        large_system_content = "You are a test assistant. " * 1000  # ~25KB
        large_user_content = "Process this input: ${input}. " * 500  # ~12KB
        case_content = '{"input": "test with large templates"}'
        
        # Create folder structure
        agent_dir = Path(self.temp_dir) / "templates" / agent_name
        agent_dir.mkdir(parents=True)
        (agent_dir / "system_prompt").write_text(large_system_content)
        (agent_dir / "user_input").write_text(large_user_content)
        (agent_dir / "case").write_text(case_content)
        
        # Mock config generation to avoid actual file operations
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": agent_name}
            mock_prompt_gen.return_value = {"system_prompt": "large"}
            mock_validate.return_value = []
            
            # Execute workflow - should handle large files without issues
            self.cli.create_agent_simple(agent_name, use_llm_enhancement=False)
            
            # Verify successful execution
            mock_save.assert_called_once()
    
    def test_multiple_agents_workflow(self):
        """Test workflow with multiple agents to ensure no state leakage."""
        agent_names = ["agent1", "agent2", "agent3"]
        
        # Create multiple agent folders
        for i, agent_name in enumerate(agent_names):
            agent_dir = Path(self.temp_dir) / "templates" / agent_name
            agent_dir.mkdir(parents=True)
            (agent_dir / "system_prompt").write_text(f"You are {agent_name}.")
            (agent_dir / "user_input").write_text(f"Input for {agent_name}: ${{input}}")
            (agent_dir / "case").write_text(f'{{"input": "test for {agent_name}"}}')
        
        # Mock config generation
        with patch.object(self.cli.config_generator, 'generate_agent_yaml') as mock_agent_gen, \
             patch.object(self.cli.config_generator, 'generate_prompt_yaml') as mock_prompt_gen, \
             patch.object(self.cli.config_generator, 'validate_config_format') as mock_validate, \
             patch.object(self.cli.config_generator, 'save_config_files') as mock_save:
            
            # Set up mocks
            mock_agent_gen.return_value = {"name": "test"}
            mock_prompt_gen.return_value = {"system_prompt": "test"}
            mock_validate.return_value = []
            
            # Process each agent
            for agent_name in agent_names:
                self.cli.create_agent_simple(agent_name, use_llm_enhancement=False)
            
            # Verify each agent was processed
            assert mock_save.call_count == len(agent_names)
            
            # Verify no state leakage by checking call arguments
            for i, call in enumerate(mock_agent_gen.call_args_list):
                parsed_data = call[0][0]  # First argument
                expected_agent = agent_names[i]
                assert expected_agent in parsed_data['system_prompt']['content']