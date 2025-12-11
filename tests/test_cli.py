"""Tests for the CLI interface."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest

from src.agent_template_parser.cli import AgentTemplateParserCLI


class TestAgentTemplateParserCLI:
    """Test cases for AgentTemplateParserCLI."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cli = AgentTemplateParserCLI()
    
    def test_init(self):
        """Test CLI initialization."""
        assert self.cli.template_manager is not None
        assert self.cli.template_parser is not None
        assert self.cli.config_generator is not None
        assert self.cli.llm_enhancer is not None
        assert self.cli.batch_processor is not None
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('builtins.print')
    def test_create_agent_from_templates_success(self, mock_print, mock_exists, mock_file):
        """Test successful agent creation from templates."""
        # Setup mocks
        mock_exists.return_value = True
        mock_file.return_value.read.side_effect = [
            "System prompt content",
            "User input content", 
            '{"test": "case"}'
        ]
        
        # Mock all the processing methods
        self.cli.template_manager.create_directory_structure = Mock()
        self.cli.template_manager.save_template_files = Mock(return_value={
            'system': Path('test_system.txt'),
            'user': Path('test_user.txt'),
            'test': Path('test_case.json')
        })
        
        self.cli.template_parser.parse_system_prompt = Mock(return_value={'variables': []})
        self.cli.template_parser.parse_user_input = Mock(return_value={'variables': []})
        self.cli.template_parser.parse_test_case = Mock(return_value={'structure': {}})
        
        self.cli.config_generator.generate_agent_yaml = Mock(return_value={'name': 'test_agent'})
        self.cli.config_generator.generate_prompt_yaml = Mock(return_value={'prompt': 'test'})
        self.cli.config_generator.validate_config_format = Mock(return_value=[])
        self.cli.config_generator.save_config_files = Mock()
        
        # Test the method
        self.cli.create_agent_from_templates(
            'system.txt', 'user.txt', 'test.json', 'test_agent'
        )
        
        # Verify calls
        self.cli.template_manager.create_directory_structure.assert_called_once()
        self.cli.template_manager.save_template_files.assert_called_once()
        self.cli.config_generator.save_config_files.assert_called_once()
        
        # Check success message was printed
        mock_print.assert_any_call("✅ Agent 'test_agent' created successfully!")
    
    @patch('pathlib.Path.exists')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_create_agent_from_templates_file_not_found(self, mock_exit, mock_print, mock_exists):
        """Test agent creation with missing template file."""
        mock_exists.return_value = False
        
        self.cli.create_agent_from_templates(
            'missing.txt', 'user.txt', 'test.json', 'test_agent'
        )
        
        mock_print.assert_any_call("❌ Error creating agent: Template file not found: missing.txt")
        mock_exit.assert_called_once_with(1)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.exists')
    @patch('builtins.print')
    def test_batch_create_testsets_success(self, mock_print, mock_exists, mock_file):
        """Test successful testset creation."""
        # Setup mocks
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = '{"test": "data"}'
        
        self.cli.batch_processor.validate_agent_exists = Mock(return_value=True)
        self.cli.batch_processor.process_json_inputs = Mock(return_value=[{'processed': 'data'}])
        self.cli.batch_processor.convert_to_testset_format = Mock(return_value=[{'testset': 'data'}])
        self.cli.batch_processor.save_testset = Mock(return_value=Path('output.jsonl'))
        
        # Test the method
        self.cli.batch_create_testsets(['data1.json', 'data2.json'], 'test_agent', 'output.jsonl')
        
        # Verify calls
        self.cli.batch_processor.validate_agent_exists.assert_called_once_with('test_agent')
        self.cli.batch_processor.process_json_inputs.assert_called_once()
        self.cli.batch_processor.save_testset.assert_called_once()
        
        # Check success message
        mock_print.assert_any_call("✅ Testset created successfully!")
    
    @patch('builtins.print')
    @patch('sys.exit')
    def test_batch_create_testsets_agent_not_exists(self, mock_exit, mock_print):
        """Test testset creation with non-existent agent."""
        self.cli.batch_processor.validate_agent_exists = Mock(return_value=False)
        
        self.cli.batch_create_testsets(['data.json'], 'nonexistent_agent', 'output.jsonl')
        
        mock_print.assert_any_call("❌ Error creating testset: Target agent 'nonexistent_agent' does not exist")
        mock_exit.assert_called_once_with(1)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    @patch('builtins.print')
    def test_list_templates_with_files(self, mock_print, mock_glob, mock_exists):
        """Test listing templates when files exist."""
        # Setup mocks
        mock_exists.return_value = True
        mock_glob.return_value = [Path('test_system.txt'), Path('test_user.txt')]
        
        self.cli.list_templates()
        
        mock_print.assert_any_call("Available templates:")
        mock_print.assert_any_call("\n📝 System Prompt Templates:")
        mock_print.assert_any_call("  - test_system.txt")
    
    @patch('pathlib.Path.exists')
    @patch('builtins.print')
    def test_list_templates_no_directory(self, mock_print, mock_exists):
        """Test listing templates when directory doesn't exist."""
        mock_exists.return_value = False
        
        self.cli.list_templates()
        
        mock_print.assert_any_call("No templates directory found. Run create command first to initialize.")
    
    @patch('builtins.print')
    def test_validate_templates_success(self, mock_print):
        """Test successful template validation."""
        # Mock template manager and parser
        self.cli.template_manager.load_template_files = Mock(return_value={
            'system_prompt': 'System content',
            'user_input': 'User content',
            'test_case': '{"test": "case"}'
        })
        
        self.cli.template_parser.parse_system_prompt = Mock(return_value={'variables': []})
        self.cli.template_parser.parse_user_input = Mock(return_value={'variables': []})
        self.cli.template_parser.parse_test_case = Mock(return_value={'structure': {}})
        
        self.cli.validate_templates('test_agent')
        
        mock_print.assert_any_call("✅ Template files loaded successfully")
        mock_print.assert_any_call("✅ System prompt template is valid")
        mock_print.assert_any_call("✅ User input template is valid")
        mock_print.assert_any_call("✅ Test case template is valid")
    
    @patch('builtins.print')
    def test_validate_templates_missing_files(self, mock_print):
        """Test template validation with missing files."""
        self.cli.template_manager.load_template_files = Mock(
            side_effect=FileNotFoundError("Template file not found")
        )
        
        self.cli.validate_templates('test_agent')
        
        mock_print.assert_any_call("❌ Template file missing: Template file not found")
    
    @patch('builtins.print')
    def test_create_agent_simple_success(self, mock_print):
        """Test successful agent creation using simplified command."""
        # Mock template manager to return folder-based templates
        self.cli.template_manager.load_template_files = Mock(return_value={
            'system_prompt': 'System prompt content',
            'user_input': 'User input content',
            'test_case': '{"test": "case"}'
        })
        
        # Mock all the processing methods
        self.cli.template_parser.parse_system_prompt = Mock(return_value={'variables': []})
        self.cli.template_parser.parse_user_input = Mock(return_value={'variables': []})
        self.cli.template_parser.parse_test_case = Mock(return_value={'structure': {}})
        
        self.cli.config_generator.generate_agent_yaml = Mock(return_value={'name': 'test_agent'})
        self.cli.config_generator.generate_prompt_yaml = Mock(return_value={'prompt': 'test'})
        self.cli.config_generator.validate_config_format = Mock(return_value=[])
        self.cli.config_generator.save_config_files = Mock()
        
        # Test the simplified method
        self.cli.create_agent_simple('test_agent')
        
        # Verify calls
        self.cli.template_manager.load_template_files.assert_called_once_with('test_agent')
        self.cli.config_generator.save_config_files.assert_called_once()
        
        # Check success message was printed
        mock_print.assert_any_call("✅ Agent 'test_agent' created successfully!")
    
    @patch('builtins.print')
    @patch('sys.exit')
    def test_create_agent_simple_missing_folder(self, mock_exit, mock_print):
        """Test simplified agent creation with missing template folder."""
        from src.agent_template_parser.error_handler import MissingAgentFolderError
        
        # Mock template manager to raise MissingAgentFolderError
        self.cli.template_manager.load_template_files = Mock(
            side_effect=FileNotFoundError("No template files found for agent 'test_agent'")
        )
        
        # Mock the helper methods
        self.cli._provide_helpful_error_guidance = Mock()
        self.cli._suggest_common_fixes = Mock()
        
        self.cli.create_agent_simple('test_agent')
        
        # Verify error handling methods were called
        self.cli._provide_helpful_error_guidance.assert_called_once()
        self.cli._suggest_common_fixes.assert_called_once_with('test_agent')
        mock_exit.assert_called_once_with(1)
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('builtins.print')
    def test_suggest_common_fixes_missing_directory(self, mock_print, mock_stat, mock_exists):
        """Test _suggest_common_fixes with missing directory."""
        mock_exists.return_value = False
        
        self.cli._suggest_common_fixes('test_agent')
        
        mock_print.assert_any_call("\n🔍 Checking for common issues...")
        mock_print.assert_any_call("  ❌ Directory missing: templates/test_agent")
        mock_print.assert_any_call("  💡 Fix: mkdir -p templates/test_agent")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('builtins.print')
    def test_suggest_common_fixes_empty_files(self, mock_print, mock_stat, mock_exists):
        """Test _suggest_common_fixes with empty files."""
        # Mock directory and files exist
        mock_exists.return_value = True
        
        # Mock file size as 0 (empty)
        mock_stat_obj = Mock()
        mock_stat_obj.st_size = 0
        mock_stat.return_value = mock_stat_obj
        
        self.cli._suggest_common_fixes('test_agent')
        
        mock_print.assert_any_call("  ✅ Directory exists: templates/test_agent")
        mock_print.assert_any_call("  ⚠️  File empty: templates/test_agent/system_prompt")
        mock_print.assert_any_call("  💡 Fix: Add content to templates/test_agent/system_prompt")
    
    @patch('builtins.print')
    def test_provide_helpful_error_guidance_folder_structure(self, mock_print):
        """Test _provide_helpful_error_guidance with folder structure error."""
        from src.agent_template_parser.error_handler import InvalidFolderStructureError
        
        error = InvalidFolderStructureError("Invalid folder structure", "test_agent", ["system_prompt"])
        
        self.cli._provide_helpful_error_guidance(error, 'test_agent')
        
        mock_print.assert_any_call("❌ Error creating agent 'test_agent': Invalid folder structure")
        mock_print.assert_any_call("\n📁 Folder Structure Issue:")
    
    @patch('builtins.print')
    def test_provide_helpful_error_guidance_missing_folder(self, mock_print):
        """Test _provide_helpful_error_guidance with missing agent folder."""
        from src.agent_template_parser.error_handler import MissingAgentFolderError
        
        error = MissingAgentFolderError("Agent folder not found", "test_agent", "templates/test_agent")
        
        self.cli._provide_helpful_error_guidance(error, 'test_agent')
        
        mock_print.assert_any_call("❌ Error creating agent 'test_agent': Agent folder not found")
        mock_print.assert_any_call("\n📂 Agent Templates Not Found:")
    
    @patch('builtins.print')
    def test_provide_helpful_error_guidance_json_error(self, mock_print):
        """Test _provide_helpful_error_guidance with JSON error."""
        error = Exception("Invalid JSON format in test case")
        
        self.cli._provide_helpful_error_guidance(error, 'test_agent')
        
        mock_print.assert_any_call("❌ Error creating agent 'test_agent': Invalid JSON format in test case")
        mock_print.assert_any_call("\n🔧 JSON Format Issue:")


class TestCLIMain:
    """Test cases for CLI main function."""
    
    @patch('sys.argv', ['cli.py', 'create-agent', 
                       '--system-prompt', 'system.txt',
                       '--user-input', 'user.txt', 
                       '--test-case', 'test.json',
                       '--agent-name', 'test_agent'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_create_agent_legacy_command(self, mock_cli_class):
        """Test main function with legacy create-agent command."""
        from src.agent_template_parser.cli import main
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli.create_agent_from_templates.assert_called_once_with(
            'system.txt', 'user.txt', 'test.json', 'test_agent', use_llm_enhancement=True
        )
    
    @patch('sys.argv', ['cli.py', 'create-agent', 'test_agent'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_create_agent_simplified_command(self, mock_cli_class):
        """Test main function with simplified create-agent command."""
        from src.agent_template_parser.cli import main
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli.create_agent_simple.assert_called_once_with(
            'test_agent', use_llm_enhancement=True
        )
    
    @patch('sys.argv', ['cli.py', 'create-agent', '--agent-name', 'test_agent'])
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_create_agent_invalid_flag_only(self, mock_exit, mock_print):
        """Test main function with invalid --agent-name flag only (should fail)."""
        from src.agent_template_parser.cli import main
        
        main()
        
        mock_print.assert_any_call("❌ Invalid arguments for create-agent command.")
        mock_exit.assert_called_once_with(1)
    
    @patch('sys.argv', ['cli.py', 'create-agent', '--system-prompt', 'system.txt'])
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_create_agent_invalid_args(self, mock_exit, mock_print):
        """Test main function with invalid create-agent arguments."""
        from src.agent_template_parser.cli import main
        
        main()
        
        mock_print.assert_any_call("❌ Invalid arguments for create-agent command.")
        mock_print.assert_any_call("\n🚀 RECOMMENDED USAGE:")
        mock_exit.assert_called_once_with(1)
    
    @patch('sys.argv', ['cli.py', 'create-testset',
                       '--json-files', 'data1.json', 'data2.json',
                       '--target-agent', 'test_agent',
                       '--output-filename', 'output.jsonl'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_create_testset_command(self, mock_cli_class):
        """Test main function with create-testset command."""
        from src.agent_template_parser.cli import main
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli.batch_create_testsets.assert_called_once_with(
            ['data1.json', 'data2.json'], 'test_agent', 'output.jsonl'
        )
    
    @patch('sys.argv', ['cli.py', 'list-templates'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_list_templates_command(self, mock_cli_class):
        """Test main function with list-templates command."""
        from src.agent_template_parser.cli import main
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli.list_templates.assert_called_once()
    
    @patch('sys.argv', ['cli.py', 'validate-templates', '--agent-name', 'test_agent'])
    @patch('src.agent_template_parser.cli.AgentTemplateParserCLI')
    def test_main_validate_templates_command(self, mock_cli_class):
        """Test main function with validate-templates command."""
        from src.agent_template_parser.cli import main
        
        mock_cli = Mock()
        mock_cli_class.return_value = mock_cli
        
        main()
        
        mock_cli.validate_templates.assert_called_once_with('test_agent')
    
    @patch('sys.argv', ['cli.py'])
    @patch('argparse.ArgumentParser.print_help')
    def test_main_no_command(self, mock_print_help):
        """Test main function with no command."""
        from src.agent_template_parser.cli import main
        
        main()
        
        mock_print_help.assert_called_once()